"""
verbatim.pipeline — one PDF in, one clean document out.

The order of operations is the same as the original script's and is load
bearing: straighten sideways pages first, so that everything downstream sees
upright text; read every page before deciding what the running headers are,
because a header is only recognisable across pages; strip headers before
building paragraphs, so a deleted header cannot be glued onto the paragraph
below it.

Beyond the original, this module records *provenance*: as the finished text is
assembled, every block's spans are given their character range in that text.
That is what lets the reviewer put a suspect passage next to the page it came
from instead of asking a human to find it.
"""

from __future__ import annotations

import re
import statistics
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from . import i18n
from .extract.columns import find_gutter, group_rows, order_columns, rows_to_lines
from .extract.headers import (
    find_running,
    find_running_in_blocks,
    strip_running,
    strip_running_blocks,
)
from .extract.model import RECOGNISED_MODEL, RECOGNISED_TESSERACT, Block, Span
from .extract.page import read_page
from .extract.paragraphs import build_paragraphs, join_lines, metrics
from .extract.pdfio import release, straighten
from .extract.text import BULLET_RE, HYPHENS, LOWER_START_RE, TERMINAL_RE, alnum_count, squeeze
from .ocr.detect import needs_ocr
from .ocr.markdown import markdown_to_blocks
from .ocr.mistral import mistral_ocr
from .ocr.tesseract import _copy_with, auto_language, ocr_tesseract
from .profiles import get as get_profile
from .profiles import opens_structural_unit


class Stopped(Exception):
    """Raised when the user asks the run to stop."""


@dataclass
class BatchResult:
    """What happened across a whole run."""

    converted: list = field(default_factory=list)   # [(txt_path, verdict)]
    failed: list = field(default_factory=list)      # [(pdf_path, message)]
    stopped: bool = False

    @property
    def done(self) -> int:
        return len(self.converted)

    @property
    def needs_review(self) -> list:
        return [p for p, v in self.converted if v in ("review", "reject")]


@dataclass
class PageMeta:
    """What the reviewer needs to render and address one page."""

    number: int
    width: float
    height: float
    source: str = "extracted"
    ocr_conf: float | None = None

    def to_dict(self) -> dict:
        return {"page": self.number, "width": self.width, "height": self.height,
                "source": self.source, "ocr_conf": self.ocr_conf}


@dataclass
class ConversionResult:
    text: str
    stats: dict
    blocks: list = field(default_factory=list)
    pages: list = field(default_factory=list)      # [PageMeta]
    # The source text layer, exactly as the engine saw it, and the text the
    # engine removed on purpose. The QA layer compares against these rather
    # than re-extracting: a second extraction could differ from the first, and
    # then a disagreement between two extractors would look like an invented
    # word.
    raw_text: str = ""
    dropped_text: str = ""

    @property
    def spans(self) -> list:
        return [s for b in self.blocks for s in b.spans]


def _assign_offsets(text: str, blocks: list) -> None:
    """Give every span its character range in the finished document.

    Block texts survive assembly verbatim — only "\\n\\n" is inserted between
    them — so a forward scan locates each one exactly. A block that cannot be
    found (the blank-line collapse rewrote it) simply keeps no offsets rather
    than being given wrong ones.
    """
    cursor = 0
    for b in blocks:
        body = b.text.strip()
        if not body:
            continue
        at = text.find(body, cursor)
        if at < 0:
            at = text.find(body)               # tolerate a reordered block
        if at < 0:
            continue
        cursor = at + len(body)
        if not b.spans:
            b.spans = [Span(page=b.page)]
        # One block can cover several lines on one or two pages. Without
        # per-line offsets the honest thing is to give every span the whole
        # block's range: the reviewer highlights the paragraph, not a word.
        for s in b.spans:
            s.char_start, s.char_end = at, cursor


def convert(path: Path, args, progress=None, log=print) -> ConversionResult:
    """progress(done_pages, total_pages, note) is called as work advances."""
    st = {"pages": 0, "tables": 0, "dropped": 0, "twocol": 0,
          "scanned": [], "sideways": 0, "ocr_pages": 0, "ocr_conf": None}

    def tick(done, total, note=""):
        if progress:
            progress(done, total, note)

    with tempfile.TemporaryDirectory() as tmp:
        work = straighten(path, tmp, args.verbose, log)
        pages, pending = [], []
        with pdfplumber.open(str(work)) as pdf:
            total = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                tick(i - 1, total, f"page {i}/{total}")
                pd = read_page(page, i, args)
                if args.ocr != "off" and needs_ocr(pd, args.ocr):
                    if (args.ocr_engine == "tesseract"
                            and args.ocr_language == "auto"):
                        tick(i - 1, total, f"page {i}/{total} (identifying language)")
                        chosen = auto_language(page, args, log)
                        args = _copy_with(args, ocr_language=chosen)
                    if args.ocr_engine == "tesseract":
                        tick(i - 1, total, f"reading page {i}/{total} (OCR)")
                        try:
                            w, c, conf = ocr_tesseract(page, args)
                            if w:
                                pd.words, pd.chars, pd.ocr = w, c, True
                                pd.ocr_conf = conf
                                pd.raw_chars = sum(len(x["text"]) for x in w)
                                pd.raw_alnum = sum(alnum_count(x["text"]) for x in w)
                                pd.looks_scanned = False
                        except Exception as exc:
                            log(f"   ! OCR failed on page {i}: {exc}")
                    else:
                        pending.append(i)
                pages.append(pd)
                release(page)
        if pending:
            if args.ocr == "always":
                log(f"   OCR = always: sending all {len(pending)} page(s) to "
                    "Mistral, ignoring the existing text layer")
            tick(0, total, f"sending {len(pending)} page(s) to Mistral OCR")
            try:
                texts, page_conf = mistral_ocr(work, pending, args, log)
                for pd in pages:
                    if pd.number in texts and texts[pd.number].strip():
                        pd.ocr_text = texts[pd.number]
                        pd.ocr = True
                        pd.ocr_conf = page_conf.get(pd.number, 0.0)
                        pd.looks_scanned = False
                        pd.raw_chars = len(squeeze(pd.ocr_text))
                        pd.raw_alnum = alnum_count(pd.ocr_text)
            except Exception as exc:
                log(f"   ! Mistral OCR failed: {exc}")
        tick(total, total, "")

    st["pages"] = len(pages)
    confs = [pd.ocr_conf for pd in pages if pd.ocr and pd.ocr_conf]
    st["ocr_pages"] = sum(1 for pd in pages if pd.ocr)
    if confs:
        st["ocr_conf"] = statistics.mean(confs) / 100.0
    for pd in pages:
        if pd.ocr_text:
            pd.words = pd.chars = []
            continue
        rows = group_rows(pd.words)
        if args.columns == "1":
            gx = None
        else:
            gx = find_gutter(pd.words, rows, force=(args.columns == "2"))
        pd.two_col = gx is not None
        if pd.two_col:
            st["twocol"] += 1
            if args.verbose:
                log(f"  page {pd.number}: two columns detected")
        pd.lines = rows_to_lines(pd.words, pd.chars, gx, args, rows)
        pd.groups = order_columns(pd.lines, gx)
        pd.words = pd.chars = []               # free memory

    sizes = [l.size for pd in pages for l in pd.lines]
    body = statistics.median(sizes) if sizes else 10.0
    running = set() if args.keep_headers else find_running(pages, body)

    # Pages a model produced carry no geometry, so the detector above cannot
    # see their headers. Build them first and find the recurring furniture
    # textually instead; otherwise every header, footer and page number lands
    # in the middle of the document.
    model_blocks = {pd.number: markdown_to_blocks(pd.ocr_text, pd.number, args)
                    for pd in pages if pd.ocr_text}
    model_running = (set() if args.keep_headers
                     else find_running_in_blocks(model_blocks))

    blocks, on_purpose, on_purpose_alnum = [], 0, 0
    for pd in pages:
        if pd.ocr_text:
            page_blocks = model_blocks[pd.number]
            if not args.keep_headers:
                page_blocks, dropped = strip_running_blocks(page_blocks,
                                                            model_running)
                st["dropped"] += len(dropped)
                pd.dropped_lines += dropped
                on_purpose += sum(len(squeeze(t)) for t in dropped)
                on_purpose_alnum += sum(alnum_count(t) for t in dropped)
            for b in page_blocks:
                b.spans = [Span(page=pd.number, source=RECOGNISED_MODEL)]
            if args.page_marks:
                page_blocks.insert(0, Block("mark", f"[page {pd.number}]",
                                            -1e9, pd.number))
            blocks += page_blocks
            continue
        if pd.looks_scanned:
            st["scanned"].append(pd.number)
        st["tables"] += len(pd.tables)
        st["sideways"] += pd.sideways_chars
        on_purpose += pd.sideways_chars
        on_purpose_alnum += pd.sideways_alnum
        if not args.keep_headers:
            n, ch, al = strip_running(pd, running, body)
            st["dropped"] += n
            on_purpose += ch
            on_purpose_alnum += al

        page_blocks = []
        col_metrics = {}
        for col in (0, 1):
            same = [l for l in pd.lines if l.col == col]
            if len(same) >= 4:
                col_metrics[col] = metrics(same, body)
        for group, col in pd.groups:
            page_blocks += build_paragraphs(
                group, pd.number, body, args.keep_hyphens,
                col_metrics.get(col) if pd.two_col else None, args)
        for top, rendered in pd.tables:
            page_blocks.append(Block("table", rendered, top, pd.number,
                                     spans=[Span(page=pd.number)]))
        if pd.ocr:
            for b in page_blocks:
                for s in b.spans:
                    s.source = RECOGNISED_TESSERACT
        if not pd.two_col:
            page_blocks.sort(key=lambda b: b.top)   # interleave tables by position
        if args.page_marks:
            page_blocks.insert(0, Block("mark", f"[page {pd.number}]", -1e9, pd.number))
        blocks += page_blocks

    profile = get_profile(getattr(args, "profile", None))
    if args.join_pages:
        merged = []
        for b in blocks:
            p = merged[-1] if merged else None
            if (p and b.kind == "para" and p.kind == "para" and b.page != p.page
                    and not p.heading and not b.heading
                    and not TERMINAL_RE.search(p.text)
                    and not BULLET_RE.match(b.text)
                    and not (profile.respect_article_breaks
                             and opens_structural_unit(b.text))
                    and (LOWER_START_RE.match(b.text) or p.text.endswith(HYPHENS))):
                p.text = join_lines(p.text, b.text, args.keep_hyphens)
                p.spans = p.spans + b.spans     # the paragraph now spans two pages
                continue
            merged.append(b)
        blocks = merged

    text = "\n\n".join(b.text for b in blocks if b.text.strip())
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    raw = sum(pd.raw_chars for pd in pages)
    kept = len(squeeze(text)) + on_purpose
    st["kept_ratio"] = min(1.0, kept / raw) if raw else 1.0
    st["raw_chars"] = raw
    st["kept_chars"] = kept

    # Unclamped, and counted over letters and digits only, so that rendering a
    # table cannot inflate it. A value meaningfully above 1.0 here means more
    # text came out than went in, which is what the clamped figure hid.
    raw_alnum = sum(pd.raw_alnum for pd in pages)
    kept_alnum = alnum_count(text) + on_purpose_alnum
    st["alnum_ratio"] = (kept_alnum / raw_alnum) if raw_alnum else 1.0

    _assign_offsets(text, blocks)
    raw_text = " ".join(pd.raw_text for pd in pages if pd.raw_text)
    dropped_text = " ".join(t for pd in pages for t in pd.dropped_lines)
    meta = [PageMeta(pd.number, pd.width, pd.height,
                     source=(RECOGNISED_MODEL if pd.ocr_text else
                             RECOGNISED_TESSERACT if pd.ocr else "extracted"),
                     ocr_conf=(pd.ocr_conf / 100.0 if pd.ocr and pd.ocr_conf else None))
            for pd in pages]
    return ConversionResult(text=text, stats=st, blocks=blocks, pages=meta,
                            raw_text=raw_text, dropped_text=dropped_text)


def collect_targets(inputs, recursive):
    out = []
    for p in inputs:
        p = Path(p)
        if p.is_dir():
            out += sorted(p.rglob("*.pdf") if recursive else p.glob("*.pdf"))
        elif p.suffix.lower() == ".pdf":
            out.append(p)
    return out


def run_batch(targets, args, on_file=None, on_page=None, log=print, stop=None,
              gate=None, write_sidecar=True):
    """Convert every file, assess it, and write both outputs.

    Assessment is not optional and not a separate command. The failure this
    tool exists to prevent is a bad conversion that nobody looked at, and a
    check that has to be remembered is a check that gets skipped.
    """
    from .qa.gate import QualityGate

    result = BatchResult()
    if gate is None:
        gate = QualityGate()

    for n, pdf_path in enumerate(targets, 1):
        if stop is not None and stop():
            log("Stopped.")
            result.stopped = True
            break
        dest = (Path(args.out) / (pdf_path.stem + ".txt")) if args.out \
            else pdf_path.with_suffix(".txt")
        if on_file:
            on_file(n, len(targets), pdf_path.name)

        def page_cb(d, t, note="", _n=n):
            if stop is not None and stop():
                raise Stopped()
            if on_page:
                on_page(_n, len(targets), d, t, note)

        try:
            res = convert(pdf_path, args, progress=page_cb, log=log)
        except Stopped:
            log("Stopped.")
            result.stopped = True
            break
        except Exception as exc:
            log("   " + i18n.t("log.failed", error=f"{type(exc).__name__}: {exc}"))
            result.failed.append((pdf_path, f"{type(exc).__name__}: {exc}"))
            continue

        st = res.stats
        dest.write_text(res.text, encoding="utf-8")

        try:
            assessment = gate.assess(res, pdf_path=pdf_path)
        except Exception as exc:                    # never lose a conversion
            log(f"   ! quality check failed: {type(exc).__name__}: {exc}")
            assessment = None

        if write_sidecar and assessment is not None:
            from . import sidecar
            try:
                sidecar.write(sidecar.build(res, assessment, pdf_path=pdf_path,
                                            txt_path=dest, settings=args), dest)
            except Exception as exc:
                log("   ! " + i18n.t("log.record_failed",
                                     error=f"{type(exc).__name__}: {exc}"))

        verdict = assessment.verdict if assessment else "unknown"
        result.converted.append((dest, verdict))

        # Through the catalogue, not an f-string: the log is where a research
        # assistant learns what happened to their files, and a French window
        # reporting its results in English defeats the point of having one.
        bits = [i18n.t("log.summary", pages=st["pages"], tables=st["tables"],
                       dropped=st["dropped"])]
        if st["twocol"]:
            bits.append(i18n.t("log.twocol", n=st["twocol"]))
        if st["ocr_pages"]:
            b = i18n.t("log.ocr_pages", n=st["ocr_pages"])
            if st["ocr_conf"]:
                b += " (" + i18n.t("log.ocr_conf", pct=st["ocr_conf"]) + ")"
            bits.append(b)
        else:
            bits.append(i18n.t("log.kept", pct=st["kept_ratio"]))
        log("   " + ", ".join(bits) + f" -> {dest.name}")

        if assessment is not None and assessment.verdict != "ok":
            log("   " + i18n.t("verdict." + assessment.verdict).upper() + ": "
                + "; ".join(assessment.reasons()[:3]))
        if st["scanned"]:
            log("   ! " + i18n.t("log.no_text_pages",
                                 pages=", ".join(map(str, st["scanned"]))))
    return result
