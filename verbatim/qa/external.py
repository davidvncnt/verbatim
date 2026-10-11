"""
verbatim.qa.external — check a text file that verbatim did not produce.

The corpus already holds tens of thousands of .txt files made by earlier
scripts, some of them by a model that is known to have invented text. They have
no record of how they were made, so verbatim rebuilds what it needs from the
source PDF:

  * **text layer** — the PDF holds real text, and every passage of the file
    must come from it. Both are compared as sequences of letters (see
    qa.letters), so that how a word is written — spacing, accents, a mangled
    apostrophe, a ligature the PDF cannot decode — is never mistaken for text
    that is not there. Numbers, table rows and repeated passages are checked
    too, and passages of the PDF that never reached the file.

  * **scan** — the PDF is images. Tesseract reads the pages, and the file is
    compared with that reading in the same way, with shorter sequences and a
    longer minimum passage, because the recogniser makes small errors of its
    own.

  * **no PDF** — only the checks that read the text on its own can run:
    repetition loops, scrambled words, garbled characters. A fluent paraphrase
    cannot be detected this way, and the record says so.

Every check runs on every file. Which kinds of finding a reviewer sees is
chosen in the window (qa.categories), not here.

The file itself is never modified. Its passages are anchored onto the pages of
verbatim's own reading (see qa.locate), so the review window can show each one
beside the part of the page it came from.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from ..extract.text import alnum_count
from . import letters
from .audit import read_text
from .categories import worst_by_kind
from .config import CONFIG
from .fidelity import (
    HIGH,
    LOW,
    MEDIUM,
    Finding,
    normalise_reference,
)
from .intrinsic import intrinsic_findings
from .locate import Reference, line_spans, page_of
from .textmetrics import compute_text_metrics

FULL, TEXT_ONLY = "full", "text_only"

# Raised whenever what the checks report changes, so results remembered from
# an earlier version are redone instead of being shown as current.
CHECK_REVISION = 3
REF_TEXT_LAYER, REF_RECOGNISED, REF_NONE = "text_layer", "recognised", "none"

# Markers earlier scripts wrote into their output. Blanked — never removed — so
# every character offset still matches the file as it is displayed.
_MARKERS_RE = re.compile(r"\[/?TABLE\]|\[page \d+\]", re.I)
_NUMBER_RE = re.compile(r"\d+(?:[.,/-]\d+)*")

MAX_PASSAGES = 60           # findings of one kind in one file, at most


def load_text(path: Path) -> str:
    """The file as the review window displays it: decoded tolerantly, with one
    kind of line break, so character offsets agree everywhere."""
    return read_text(Path(path)).replace("\r\n", "\n").replace("\r", "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_stamp(path: Path | None) -> str | None:
    """Cheap identity for a PDF: enough to notice it was replaced."""
    if path is None:
        return None
    try:
        st = Path(path).stat()
    except OSError:
        return None
    return f"{st.st_size}:{st.st_mtime_ns}"


# ---------------------------------------------------------------------------
# finding the PDF
# ---------------------------------------------------------------------------

_pdf_index: dict = {}


def _key(stem: str) -> str:
    return unicodedata.normalize("NFC", stem).casefold()


def find_pdf(txt_path: Path, pdf_folder: Path | None) -> Path | None:
    """The PDF with the same name as the text file.

    Looked for in the PDF folder, then beside the text file. Names are compared
    after Unicode normalisation and without regard to case, because macOS
    reports accented file names in a different form from Windows and from what
    was typed.
    """
    txt_path = Path(txt_path)
    wanted = _key(txt_path.stem)
    for folder in [pdf_folder, txt_path.parent]:
        if not folder:
            continue
        folder = Path(folder)
        try:
            stamp = folder.stat().st_mtime_ns
        except OSError:
            continue
        cached = _pdf_index.get(folder)
        if cached is None or cached[0] != stamp:
            index = {}
            try:
                for entry in folder.iterdir():
                    if entry.suffix.lower() == ".pdf":
                        index.setdefault(_key(entry.stem), entry)
            except OSError:
                index = {}
            _pdf_index[folder] = cached = (stamp, index)
        hit = cached[1].get(wanted)
        if hit is not None:
            return hit
    return None


# ---------------------------------------------------------------------------
# comparisons
# ---------------------------------------------------------------------------

def _passage(tokens: list, group: list, key: str, severity: str,
             sample_words: list | None = None) -> Finding:
    first, last = tokens[group[0]], tokens[group[-1]]
    sample = sample_words if sample_words is not None else \
        [tokens[i][0] for i in group]
    return Finding(kind=key, severity=severity, key=key,
                   params={"n": len(group),
                           "sample": ", ".join(dict.fromkeys(sample[:8]))},
                   char_start=first[1], char_end=last[2],
                   detail=" ".join(tokens[i][0] for i in group[:50]))


def _group(positions: list, gap: int) -> list:
    groups: list = []
    for p in positions:
        if groups and p - groups[-1][-1] <= gap:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups


def exact_findings(text: str, raw_text: str, removed: str, ref: Reference,
                   pages: list | None = None) -> list:
    """Comparison against a PDF text layer, as sequences of letters.

    See qa.letters for why the comparison is not word by word. Each finding
    is placed where it is: a passage of the text at its own characters, a
    passage of the PDF at its own lines on the page.
    """
    decoded = letters.decode_cids(raw_text, text)
    known = letters.shingles(decoded)
    if not known:
        return []
    pdf_letters, _ = letters.fold(decoded)
    findings: list = []

    invented = letters.unmatched(text, known)
    findings += _invented_passages(text, invented)
    rows, row_ranges = _unfound_rows(text, known, pdf_letters, invented)
    findings += rows
    taken = invented + row_ranges
    findings += _absent_numbers(text, decoded, taken)
    findings += _repeated_passages(text, pdf_letters)
    findings += _spelling_variants(text, decoded, pdf_letters, taken)
    findings += _missing_text(text, ref, pages or [])
    return findings


def _quote(text: str, start: int, end: int, limit: int = 120) -> str:
    quote = " ".join(text[start:end].split())
    return quote if len(quote) <= limit else quote[:limit].rstrip() + "…"


def _inside(start: int, end: int, ranges: list) -> bool:
    return any(a <= start and end <= b for a, b, *_ in ranges)


def _invented_passages(text: str, runs: list, kind: str = "invented_text",
                       keys: tuple = ("invented_text", "invented_text_repeated")) -> list:
    """One finding per passage; the same passage invented again and again —
    a model caught in a loop — is one finding that says how many times."""
    seen: dict = {}
    order: list = []
    for a, b, n in runs:
        key = letters.fold(text[a:b])[0]
        if key in seen:
            seen[key][1] += 1
            continue
        seen[key] = [(a, b, n), 1]
        order.append(key)
    findings = []
    for key in order[:MAX_PASSAGES]:
        (a, b, n), times = seen[key]
        findings.append(Finding(
            kind=kind, severity=HIGH, key=keys[0] if times == 1 else keys[1],
            params={"n": n, "times": times, "sample": _quote(text, a, b)},
            char_start=a, char_end=b, detail=text[a:b][:400]))
    return findings


def _unfound_rows(text: str, known: set, pdf_letters: str,
                  invented: list) -> tuple:
    """Table rows of the text whose cells are not in the PDF's text at all.

    Most often the PDF prints that table as a picture: the text was read from
    the picture, and nothing in the PDF's text can confirm or contradict it.
    Reported once per table, not once per number in it.
    """
    rows = []
    pos = 0
    for line in text.split("\n"):
        start, pos = pos, pos + len(line) + 1
        if "\t" not in line and "|" not in line:
            continue
        cells = [c for c in re.split(r"[\t|]", line) if letters.fold(c)[0]]
        if len(cells) < 2:
            continue
        unfound = sum(1 for c in cells
                      if not letters.found_in(c, known, pdf_letters))
        if unfound >= max(2, 0.5 * len(cells)):
            rows.append((start, start + len(line)))
    groups: list = []
    for a, b in rows:
        if _inside(a, b, invented):
            continue
        if groups and a - groups[-1][1] <= 2:
            groups[-1] = (groups[-1][0], b, groups[-1][2] + 1)
        else:
            groups.append((a, b, 1))
    findings = [Finding(kind="unfound_table", severity=MEDIUM, key="unfound_table",
                        params={"n": n, "sample": _quote(text, a, b, 80)},
                        char_start=a, char_end=b)
                for a, b, n in groups[:MAX_PASSAGES]]
    return findings, [(a, b) for a, b, _ in groups]


# Digits joined across the separators numbers are written with, so that
# "1 000", "1,000" and "1000" are one number, and a number the PDF's text
# layer glued to its neighbours ("Forestry87,471–481") is still found.
_DIGIT_RUN_RE = re.compile(r"\d+(?:[.,/'’\s  ]+\d+)*")


def _digit_runs(raw_text: str) -> str:
    return "|".join(re.sub(r"\D", "", m) for m in _DIGIT_RUN_RE.findall(raw_text))


def _absent_numbers(text: str, raw_text: str, taken: list, *,
                    severity: str = HIGH, misread: bool = False) -> list:
    """Numbers of the text that the PDF does not contain, one finding per line.

    Compared on digits alone, by value rather than by count. Measured on 90
    files, nine in ten numbers that a stricter comparison reported were in
    the PDF, written with other spacing or glued to a neighbouring word.
    Against a scan, `misread` also accepts a number one digit away from one
    the recogniser read: that digit is far more often its error than the
    text's.
    """
    runs = _digit_runs(letters.ascii_digits(normalise_reference(raw_text)))
    known = set(runs.split("|"))

    def present(digits: str) -> bool:
        if digits in runs:
            return True
        return misread and len(digits) >= 2 and any(
            len(r) == len(digits) and sum(x != y for x, y in zip(r, digits)) <= 1
            for r in known)

    blanked = letters.ascii_digits(
        _MARKERS_RE.sub(lambda m: " " * len(m.group(0)), text))
    by_line: dict = {}
    for m in _NUMBER_RE.finditer(blanked):
        # A range or a reference ("165-171", "11/41") is checked bound by bound:
        # the PDF may join them with another dash, or with none.
        parts = [re.sub(r"\D", "", x) for x in re.split(r"[-/]", m.group(0))]
        if all(present(x) for x in parts if x) or _inside(m.start(), m.end(), taken):
            continue
        line = text.rfind("\n", 0, m.start())
        by_line.setdefault(line, []).append((text[m.start():m.end()], m.start(), m.end()))
    findings = []
    for found in list(by_line.values())[:MAX_PASSAGES]:
        values = ", ".join(dict.fromkeys(v for v, _, _ in found[:8]))
        findings.append(Finding(
            kind="invented_numbers", severity=severity,
            key="invented_number" if len(found) == 1 else "invented_numbers_line",
            params={"value": values, "n": len(found)},
            char_start=found[0][1], char_end=found[-1][2]))
    return findings


REPEAT_MIN_LETTERS = 40


def _repeated_passages(text: str, pdf_letters: str) -> list:
    """Lines the text holds more often than the PDF does: every extra copy."""
    occurrences: dict = {}
    for offset, chunk in letters.cells(text):
        key = letters.fold(chunk)[0]
        if len(key) >= REPEAT_MIN_LETTERS:
            occurrences.setdefault(key, []).append((offset, offset + len(chunk)))
    findings = []
    for key, where in occurrences.items():
        if len(where) < 2:
            continue
        in_pdf = pdf_letters.count(key)
        if in_pdf == 0 or len(where) <= in_pdf:
            continue                      # not in the PDF at all: reported as invented
        for a, b in where[in_pdf:]:
            findings.append((a, b, len(where), in_pdf))
    # The lines of one repeated paragraph are one finding, not one per line.
    findings.sort()
    merged: list = []
    for a, b, times, in_pdf in findings:
        if merged and a - merged[-1][1] <= 3:
            merged[-1][1] = b
        else:
            merged.append([a, b, times, in_pdf])
    return [Finding(kind="duplicated_words", severity=MEDIUM, key="repeated_passage",
                    params={"times": times, "in_pdf": in_pdf,
                            "sample": _quote(text, a, b, 80)},
                    char_start=a, char_end=b)
            for a, b, times, in_pdf in merged[:MAX_PASSAGES]]


def _deletions(word: str) -> set:
    return {word[:i] + word[i + 1:] for i in range(len(word))}


def _spelling_variants(text: str, raw_text: str, pdf_letters: str,
                       taken: list) -> list:
    """Words written slightly differently from the PDF: one letter wrong,
    missing, added, or two letters swapped. Real, and nearly always harmless."""
    pdf_words: dict = {}
    for w in re.findall(r"[^\W\d_]+", normalise_reference(raw_text)):
        folded = letters.fold(w)[0]
        if len(folded) >= 4:
            pdf_words.setdefault(folded, w)
    index: dict = {}
    for folded in pdf_words:
        index.setdefault(folded, folded)
        for d in _deletions(folded):
            index.setdefault(d, folded)
    findings = []
    for m in re.finditer(r"[^\W\d_]+", unicodedata.normalize("NFC", text)):
        folded = letters.fold(m.group(0))[0]
        if len(folded) < 4 or folded in pdf_letters or _inside(m.start(), m.end(), taken):
            continue
        near = index.get(folded) or next(
            (index[d] for d in _deletions(folded) if d in index), None)
        if near is None:
            continue
        findings.append(Finding(
            kind="spelling_variants", severity=LOW, key="spelling_variant",
            params={"word": m.group(0), "pdf": pdf_words[near]},
            char_start=m.start(), char_end=m.end()))
        if len(findings) >= MAX_PASSAGES:
            break
    return findings


MISSING_MIN_LETTERS = 60


def _missing_text(text: str, ref: Reference, pages: list,
                  size: int = letters.SHINGLE) -> list:
    """Passages of the PDF with no counterpart in the text, outlined on the page.

    Footnotes and text printed sideways in the margin (licences, journal
    references) are left out: the team leaves them out of the text on purpose.
    """
    known = letters.shingles(text, size=size)
    if not known:
        return []
    skip = _set_aside(ref, pages)
    findings = []
    for a, b, n in letters.unmatched(ref.text, known, size=size,
                                     min_run=MISSING_MIN_LETTERS):
        overlap = sum(max(0, min(b, y) - max(a, x)) for x, y in skip)
        if overlap > 0.5 * (b - a):
            continue
        region = ref.region_between(a, b)
        page = min(region) if region else None
        box = region.get(page) if page is not None else None
        findings.append(Finding(
            kind="missing_from_text", severity=MEDIUM, key="missing_from_text",
            params={"n": n, "sample": _quote(ref.text, a, b)},
            page=page, bbox=tuple(box) if box else None,
            detail=ref.text[a:b][:400]))
        if len(findings) >= MAX_PASSAGES:
            break
    return findings


def _unscramble(findings: list, text: str, pdf_letters: str) -> list:
    """Drop "scrambled" words that the PDF itself contains.

    Read alone, a name such as "LexUriServ", "SafeSeaNet" or "TaKaRa" looks
    like two lines woven together. On the team's files every scrambled-text
    finding was one of these. Text scrambled by a bad reading is not in the
    PDF's own text, so the PDF settles it.
    """
    from .scramble import locate as locate_tokens
    out = []
    for f in findings:
        if f.kind != "scrambled_text":
            out.append(f)
            continue
        words = [w for w in f.detail.split()
                 if letters.fold(w)[0] not in pdf_letters]
        if not words:
            continue
        hits = locate_tokens(text, words)
        out.append(Finding(
            kind=f.kind, severity=HIGH if len(words) >= 2 else MEDIUM, key=f.key,
            params={"n": len(words), "sample": ", ".join(dict.fromkeys(words[:6]))},
            char_start=hits[0][1] if hits else None,
            char_end=hits[0][2] if hits else None, detail=" ".join(words)))
    return out


def _set_aside(ref: Reference, pages: list) -> list:
    """Character ranges of the PDF reading that are footnotes or margin text.

    A footnote is recognised by where it is and how it is set: smaller than
    the body text and below its last line. Margin text is set sideways, so
    its lines are much taller than they are wide.
    """
    from statistics import median
    heights = {p.get("page"): p.get("height") for p in pages}
    by_page: dict = {}
    for sp in ref.spans:
        box = sp.get("bbox")
        if box and sp.get("char_end", 0) > sp.get("char_start", 0):
            by_page.setdefault(sp.get("page"), []).append(sp)
    out = []
    for page, spans in by_page.items():
        flat = []
        for sp in spans:
            x0, top, x1, bottom = sp["bbox"]
            if bottom - top > 2.5 * max(x1 - x0, 1):
                out.append((sp["char_start"], sp["char_end"]))
            else:
                flat.append(sp)
        if len(flat) < 4:
            continue
        body = median(sp["bbox"][3] - sp["bbox"][1] for sp in flat)
        normal = [sp for sp in flat if sp["bbox"][3] - sp["bbox"][1] >= 0.9 * body]
        if not normal:
            continue
        floor = max(sp["bbox"][3] for sp in normal)
        half = 0.5 * (heights.get(page) or 0)
        for sp in flat:
            top, bottom = sp["bbox"][1], sp["bbox"][3]
            if bottom - top < 0.9 * body and top >= floor - 1 and top > half:
                out.append((sp["char_start"], sp["char_end"]))
    return out


# A recogniser misreads a letter every few words, so against a scan the
# sequences looked up are shorter and a passage must be longer to count.
SCAN_SHINGLE = 8
SCAN_MIN_LETTERS = 40


def recognised_findings(text: str, ref: Reference, removed: str,
                        pages: list) -> list:
    """Comparison against a recognised scan, as sequences of letters.

    On the team's scans, comparing word sequences reported 79 passages in a
    54-page file the reviewer accepted; comparing letters reports none, while
    a passage that is not in the scan at all still leaves a long gap.
    """
    known = letters.shingles(ref.text, size=SCAN_SHINGLE)
    total = len(letters.fold(text)[0])
    if not known or not total:
        return []
    runs = letters.unmatched(text, known, size=SCAN_SHINGLE,
                             min_run=SCAN_MIN_LETTERS)
    covered = 1.0 - sum(n for _, _, n in runs) / total
    if covered < 0.6:
        # The text and the reading disagree almost everywhere: the scan was
        # read in the wrong language, or is not this document. One finding
        # says so; a hundred passages would bury it.
        return [Finding(kind="scan_mismatch", severity=HIGH, key="scan_mismatch",
                        params={"pct": covered})]
    findings = _invented_passages(text, runs, kind="not_in_scan",
                                  keys=("not_in_scan_passage", "not_in_scan_repeated"))
    findings += _missing_text(text, ref, pages, size=SCAN_SHINGLE)

    findings += _absent_numbers(text, ref.text, runs, severity=MEDIUM, misread=True)
    return findings


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def check(txt_path: Path, *, pdf_path: Path | None, mode: str = FULL,
          ocr: bool = True, progress=None, profile: str = "decisions",
          config: dict | None = None, crosscheck_conf: float | None = None) -> dict:
    """Check one text file. Returns a record shaped like a sidecar record.

    `crosscheck_conf` is how sure the recogniser must be before its reading of
    a scan is treated as evidence. It is adjustable because the right value
    depends on the scans: too high and a usable comparison is thrown away, too
    low and a bad reading produces false alarms.
    """
    cfg = config or CONFIG
    conf_min = cfg["CROSSCHECK_CONF_MIN"] if crosscheck_conf is None \
        else float(crosscheck_conf)
    txt_path = Path(txt_path)
    text = load_text(txt_path)
    findings, _metrics, _ = intrinsic_findings(text, cfg)
    pages: list = []
    spans: list = []
    reference = REF_NONE
    notice = None

    if mode == TEXT_ONLY:
        notice = "text_only"
    elif pdf_path is None:
        notice = "no_pdf"
    else:
        from ..pipeline import convert
        from ..settings import Settings
        settings = Settings(ocr="off", profile=profile, ocr_engine="tesseract")
        if ocr:
            from ..ocr.detect import check_ocr, resolve_languages
            usable, _note = check_ocr("tesseract")
            if usable:
                settings.ocr = "auto"
                resolve_languages(settings, log=lambda *a, **k: None)
        res = convert(Path(pdf_path), settings, progress=progress,
                      log=lambda *a, **k: None)
        pages = [p.to_dict() for p in res.pages]
        recognised = any(p["source"] != "extracted" for p in pages)
        findings = _unscramble(findings, text, letters.fold(
            letters.decode_cids(res.raw_text + " " + res.text, text))[0])
        usable_ref = alnum_count(res.text) >= 0.2 * max(alnum_count(text), 1)
        unread = res.stats.get("scanned") or []

        confs = [p["ocr_conf"] for p in pages if p.get("ocr_conf")]
        mean_conf = sum(confs) / len(confs) if confs else None
        # Recognition that produced little, or that the recogniser itself had
        # no confidence in, is not evidence. Comparing against it would report
        # every paragraph as missing, and a reviewer shown a hundred false
        # alarms stops reading the real ones.
        poor_reading = mean_conf is not None and (
            mean_conf < conf_min or not usable_ref)

        if recognised and poor_reading:
            reference = REF_NONE
            notice = "scan_unreadable"
            findings.append(Finding(
                kind="scan_unchecked", severity=MEDIUM, key="scan_unreadable",
                params={"pct": mean_conf}))
        elif not usable_ref or (unread and not recognised):
            reference = REF_NONE
            notice = "scan_unchecked"
            findings.append(Finding(
                kind="scan_unchecked", severity=LOW, key="scan_unchecked",
                params={"n": len(unread) or len(pages)}))
        else:
            ref = Reference(res.text, res.spans)
            spans = line_spans(text, ref)
            if recognised:
                reference = REF_RECOGNISED
                found = recognised_findings(text, ref, res.dropped_text, pages)
                if mean_conf is not None and mean_conf < cfg["OCR_CONF_MIN"]:
                    found.append(Finding(
                        kind="ocr_confidence", severity=MEDIUM,
                        key="ocr_low_confidence", params={"pct": mean_conf}))
            else:
                reference = REF_TEXT_LAYER
                found = exact_findings(text, res.raw_text, res.dropped_text, ref,
                                       pages)
            findings += found

    # Place every text-located finding on its page. A passage with no
    # counterpart on a page the recogniser itself struggled to read is more
    # likely recognition noise than invention: still shown, not as a certainty.
    page_conf = {p["page"]: p.get("ocr_conf") for p in pages}
    for f in findings:
        if f.page is None and f.char_start is not None and spans:
            f.page = page_of(spans, f.char_start)
        if f.kind == "not_in_scan" and f.page is not None:
            conf = page_conf.get(f.page)
            if conf is not None and conf < cfg["OCR_CONF_MIN"]:
                f.severity = MEDIUM

    # Where the words cannot be checked against a text layer, ask whether they
    # belong in this material at all. Against a text layer the exact comparison
    # already answers that, precisely.
    if reference != REF_TEXT_LAYER:
        findings += lexical_findings(text)

    order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    findings.sort(key=lambda f: (order.get(f.severity, 3),
                                 f.page if f.page is not None else 10 ** 6,
                                 f.char_start if f.char_start is not None else 0))
    severities = {f.severity for f in findings}
    verdict = "reject" if HIGH in severities else ("review" if findings else "ok")

    return {
        "kind": "external",
        "verbatim_version": __version__,
        "check_revision": CHECK_REVISION,
        "checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "text_file": txt_path.name,
        "text_sha256": sha256_file(txt_path),
        "source_pdf": Path(pdf_path).name if pdf_path else None,
        "source_path": str(Path(pdf_path).resolve()) if pdf_path else None,
        "pdf_stamp": file_stamp(pdf_path),
        "mode": mode,
        "ocr": bool(ocr),
        "crosscheck_conf": round(conf_min, 4),
        "reference": reference,
        "notice": notice,
        "assessment": {"verdict": verdict, "risk_score": None,
                       "findings": [f.to_dict() for f in findings]},
        "pages": pages,
        "spans": spans,
        "review": None,
    }


def lexical_findings(text: str, vocabulary=None) -> list:
    """Words this material would not be expected to contain."""
    from .lexicon import MAX_REPORTED, MIN_SUSPICIOUS, locate, suspicious_words
    words = suspicious_words(text, vocabulary)
    if len(words) < MIN_SUSPICIOUS:
        return []
    start, end = locate(text, set(words))
    return [Finding(kind="unexpected_words", severity=MEDIUM,
                    key="unexpected_words",
                    params={"n": len(words),
                            "sample": ", ".join(words[:MAX_REPORTED])},
                    char_start=start, char_end=end,
                    detail=" ".join(words[:50]))]


def quick_verdict(txt_path: Path, config: dict | None = None) -> dict:
    """Text-only triage for ordering a folder before any file is opened.

    Runs on every file of a folder, so it skips language detection: it costs
    about half the time of everything else here and none of these checks
    depend on it. Over 21,000 files that is minutes of a reviewer's wait, and
    of the processor time the window needs to stay responsive.
    """
    cfg = config or CONFIG
    text = load_text(txt_path)
    metrics = compute_text_metrics(text, config=cfg, language="unknown")
    findings, _, _ = intrinsic_findings(text, cfg, metrics)
    severities = {f.severity for f in findings}
    return {"verdict": "reject" if HIGH in severities else
                       ("review" if findings else "ok"),
            "kinds": sorted({f.kind for f in findings}),
            "severities": worst_by_kind([f.to_dict() for f in findings])}
