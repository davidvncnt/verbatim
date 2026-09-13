"""
verbatim.qa.external — check a text file that verbatim did not produce.

The corpus already holds tens of thousands of .txt files made by earlier
scripts, some of them by a model that is known to have invented text. They have
no record of how they were made, so verbatim rebuilds what it needs from the
source PDF:

  * **text layer** — the PDF holds real text. Every word in the file must come
    from it, so the comparison is exact: a word or a number that is not in the
    PDF is reported, and so is a passage of the PDF that never reached the file.

  * **scan** — the PDF is images. Tesseract reads the pages, and the file is
    compared with that reading. Recognition makes small errors of its own, so
    this comparison looks for *passages* with no counterpart rather than single
    words: a passage of the file with no equivalent anywhere in the scan is
    where an invented paragraph shows up.

  * **no PDF** — only the checks that read the text on its own can run:
    repetition loops, scrambled words, garbled characters. A fluent paraphrase
    cannot be detected this way, and the record says so.

The file itself is never modified. Its passages are anchored onto the pages of
verbatim's own reading (see qa.locate), so the review window can show each one
beside the part of the page it came from.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from ..extract.text import alnum_count
from .audit import read_text
from .config import CONFIG
from .fidelity import (
    HIGH,
    LOW,
    MEDIUM,
    Finding,
    _segment,
    normalise_reference,
    tokens_with_spans,
    words,
)
from .intrinsic import intrinsic_findings
from .locate import Reference, line_spans, page_of, uncovered_runs

FULL, TEXT_ONLY = "full", "text_only"

# Raised whenever what the checks report changes, so results remembered from
# an earlier version are redone instead of being shown as current.
CHECK_REVISION = 1
REF_TEXT_LAYER, REF_RECOGNISED, REF_NONE = "text_layer", "recognised", "none"

# Markers earlier scripts wrote into their output. Blanked — never removed — so
# every character offset still matches the file as it is displayed.
_MARKERS_RE = re.compile(r"\[/?TABLE\]|\[page \d+\]", re.I)
_NUMBER_RE = re.compile(r"\d+(?:[.,/-]\d+)*")

# A passage shorter than this is not reported: at word level that is ordinary
# recognition noise, not an invented sentence.
INVENTED_GAP = 8            # words apart before two inventions are two passages
SCAN_MIN_RUN = 12           # words of the file with no counterpart in the scan
MISSING_MIN_RUN = 12        # words of the PDF with no counterpart in the file
MAX_PASSAGES = 60


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


def exact_findings(text: str, raw_text: str, removed: str,
                   ref: Reference) -> list:
    """Word-for-word comparison against a PDF text layer, located."""
    findings: list = []
    ref_words = words(normalise_reference(raw_text))
    if not ref_words:
        return findings
    tokens = tokens_with_spans(text)
    ref_counts = Counter(ref_words)
    out_counts = Counter(t for t, _, _ in tokens)
    removed_counts = Counter(words(normalise_reference(removed)))

    extra = out_counts - ref_counts
    lost = ref_counts - out_counts - removed_counts
    for word in list(extra):                      # de-hyphenation joins
        while extra[word] > 0:
            parts = _segment(word, lost)
            if parts is None:
                break
            for part in parts:
                lost[part] -= 1
                if lost[part] <= 0:
                    del lost[part]
            extra[word] -= 1
        if extra[word] <= 0:
            del extra[word]

    # Words that do not exist in the PDF at all, grouped into passages. A word
    # that exists but appears too often is duplication, reported separately.
    # Numbers are left to the numeral check, so a changed date is reported once.
    absent = {w for w in extra if ref_counts.get(w, 0) == 0 and not w.isdigit()}
    positions = [i for i, (t, _, _) in enumerate(tokens) if t in absent]
    groups = _group(positions, INVENTED_GAP)[:MAX_PASSAGES]
    for group in groups:
        findings.append(_passage(tokens, group, "invented_words", HIGH))

    # Duplication is counted outside invented passages. An invented sentence
    # also contains ordinary words — "the", "Parties" — that push their counts
    # past the PDF's, and reporting that again as repetition would send the
    # reviewer to the same place twice under a misleading name.
    near_invention = set()
    for group in groups:
        near_invention.update(range(max(0, group[0] - INVENTED_GAP),
                                    group[-1] + INVENTED_GAP + 1))
    in_passages = Counter(tokens[i][0] for i in near_invention if i < len(tokens))
    surplus = {w: n - in_passages.get(w, 0) for w, n in extra.items()
               if w not in absent and n - in_passages.get(w, 0) > 0}
    if sum(surplus.values()) >= 8:
        top = max(surplus, key=surplus.get)
        seen, at = 0, None
        for t, a, b in tokens:
            if t == top:
                seen += 1
                if seen > ref_counts[top]:
                    at = (a, b)
                    break
        findings.append(Finding(
            kind="duplicated_words", severity=MEDIUM, key="duplicated_words",
            params={"n": sum(surplus.values()),
                    "sample": ", ".join(sorted(surplus, key=surplus.get,
                                               reverse=True)[:8])},
            char_start=at[0] if at else None, char_end=at[1] if at else None))

    findings += _missing_passages(text, ref, removed, min_run=MISSING_MIN_RUN,
                                  lost=lost)
    findings += _absent_numbers(text, raw_text)
    return findings


def _absent_numbers(text: str, raw_text: str) -> list:
    """Numbers the PDF does not contain at all.

    By value, not by count: a number that exists in the PDF but appears once
    more in the file is repetition, which the duplication finding reports, and
    calling it "not in the PDF" would be false.
    """
    present = set(_NUMBER_RE.findall(normalise_reference(raw_text)))
    blanked = _MARKERS_RE.sub(lambda m: " " * len(m.group(0)), text)
    absent = [(m.group(0), m.start(), m.end()) for m in _NUMBER_RE.finditer(blanked)
              if m.group(0) not in present]
    if not absent:
        return []
    return [Finding(
        kind="invented_numbers", severity=HIGH, key="invented_numbers",
        params={"n": len(absent),
                "sample": ", ".join(dict.fromkeys(v for v, _, _ in absent[:8]))},
        char_start=absent[0][1], char_end=absent[0][2])]


def _missing_passages(text: str, ref: Reference, removed: str, *, min_run: int,
                      lost: Counter | None = None, k: int = 3) -> list:
    """Passages of the PDF with no counterpart in the file, placed on the page."""
    ref_words = [t for t, _, _ in ref.tokens]
    file_words = words(text)
    removed_words = set(words(normalise_reference(removed)))
    findings = []
    for a, b in uncovered_runs(ref_words, file_words, k, min_run):
        span = ref_words[a:b]
        # Running headers and page furniture are left out on purpose.
        if sum(1 for w in span if w in removed_words) > 0.6 * len(span):
            continue
        # Against a text layer, insist the words are genuinely absent, not just
        # reordered or re-hyphenated beyond what the sequence test can see.
        if lost is not None and sum(1 for w in span if lost.get(w, 0) > 0) < 0.5 * len(span):
            continue
        region = ref.token_region(a)
        page = next(iter(region), None)
        box = region.get(page) if page is not None else None
        # Quote the passage as the PDF writes it, not as lower-cased tokens.
        quote = ref.text[ref.tokens[a][1]:ref.tokens[min(b, a + 12) - 1][2]]
        findings.append(Finding(
            kind="missing_from_text",
            severity=HIGH if b - a >= CONFIG["BLOCK_RUN_WORDS"] else MEDIUM,
            key="missing_from_text", params={"n": b - a,
                                             "sample": " ".join(quote.split())},
            page=page, bbox=tuple(box) if box else None,
            detail=" ".join(span[:50])))
        if len(findings) >= MAX_PASSAGES:
            break
    return findings


def recognised_findings(text: str, ref: Reference, removed: str,
                        pages: list) -> list:
    """Comparison against a recognised scan: passages, not single words."""
    findings: list = []
    tokens = tokens_with_spans(text)
    file_words = [t for t, _, _ in tokens]
    ref_words = [t for t, _, _ in ref.tokens]
    if not ref_words:
        return findings
    runs = uncovered_runs(file_words, ref_words, 3, SCAN_MIN_RUN)
    covered = 1.0 - sum(b - a for a, b in runs) / max(len(file_words), 1)
    if covered < 0.6:
        findings.append(Finding(kind="scan_mismatch", severity=HIGH,
                                key="scan_mismatch", params={"pct": covered}))
    for a, b in runs[:MAX_PASSAGES]:
        findings.append(_passage(tokens, list(range(a, b)), "not_in_scan", HIGH))
    findings += _missing_passages(text, ref, removed, min_run=20)

    ref_numbers = set(_NUMBER_RE.findall(ref.text))
    blanked = _MARKERS_RE.sub(lambda m: " " * len(m.group(0)), text)
    odd = []
    for m in _NUMBER_RE.finditer(blanked):
        v = m.group(0)
        if len(v) < 2 or v in ref_numbers:
            continue
        near = any(len(r) == len(v) and sum(x != y for x, y in zip(r, v)) <= 1
                   for r in ref_numbers)
        if not near:
            odd.append((v, m.start(), m.end()))
    if odd:
        findings.append(Finding(
            kind="invented_numbers", severity=MEDIUM, key="invented_numbers",
            params={"n": len(odd), "sample": ", ".join(dict.fromkeys(v for v, _, _ in odd[:8]))},
            char_start=odd[0][1], char_end=odd[0][2]))
    return findings


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def check(txt_path: Path, *, pdf_path: Path | None, mode: str = FULL,
          ocr: bool = True, progress=None, profile: str = "decisions",
          config: dict | None = None) -> dict:
    """Check one text file. Returns a record shaped like a sidecar record."""
    cfg = config or CONFIG
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
        settings = Settings(ocr="off", profile=profile)
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
        usable_ref = alnum_count(res.text) >= 0.2 * max(alnum_count(text), 1)
        unread = res.stats.get("scanned") or []

        if not usable_ref or (unread and not recognised):
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
                confs = [p["ocr_conf"] for p in pages if p.get("ocr_conf")]
                if confs and sum(confs) / len(confs) < cfg["OCR_CONF_MIN"]:
                    found.append(Finding(
                        kind="ocr_confidence", severity=MEDIUM,
                        key="ocr_low_confidence",
                        params={"pct": sum(confs) / len(confs)}))
            else:
                reference = REF_TEXT_LAYER
                found = exact_findings(text, res.raw_text, res.dropped_text, ref)
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
        "reference": reference,
        "notice": notice,
        "assessment": {"verdict": verdict, "risk_score": None,
                       "findings": [f.to_dict() for f in findings]},
        "pages": pages,
        "spans": spans,
        "review": None,
    }


def quick_verdict(txt_path: Path, config: dict | None = None) -> dict:
    """Text-only triage for ordering a folder before any file is opened."""
    text = load_text(txt_path)
    findings, _, _ = intrinsic_findings(text, config or CONFIG)
    severities = {f.severity for f in findings}
    return {"verdict": "reject" if HIGH in severities else
                       ("review" if findings else "ok"),
            "findings": len(findings)}
