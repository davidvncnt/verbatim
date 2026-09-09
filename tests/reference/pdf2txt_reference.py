#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf2txt.py - Convert PDF files into clean plain-text files.

What it does
    * re-flows each paragraph onto a single line, one blank line between
      paragraphs
    * removes running headers, running footers and page numbers
    * keeps tables and renders them as aligned fixed-width text, including
      tables that have no ruling lines (rebuilt from column alignment)
    * straightens pages whose text is printed sideways
    * reads scanned pages that hold no selectable text (see OCR below)
    * ignores images and charts
    * stitches back together a paragraph split across a page break
    * de-hyphenates words broken at end of line ("mat-" + "ter" -> "matter")
    * detects two-column pages and reads each column in turn

Three ways to use it
    1. Double-click the file, or run "python pdf2txt.py" with no arguments:
       a small window opens where you pick the two folders and press Convert.
    2. Fill in INPUT_FOLDER and OUTPUT_FOLDER in the SETTINGS block below and
       run it: no window, straight to work.
    3. From a terminal, which overrides the settings:
           python pdf2txt.py file.pdf
           python pdf2txt.py my_folder -o texts -r
           python pdf2txt.py my_folder --ocr always --ocr-language fra

Install
    pip install pdfplumber pypdf numpy
    For scanned PDFs, also:
        pip install pytesseract
        plus the Tesseract program itself:
          Windows  https://github.com/UB-Mannheim/tesseract/wiki
          macOS    brew install tesseract
          Linux    sudo apt install tesseract-ocr
        Language packs matter for scans. macOS: brew install tesseract-lang
        (then brew reinstall tesseract if "eng" vanishes from --list-langs).
        Linux: sudo apt install tesseract-ocr-fra tesseract-ocr-spa
    For the Mistral OCR option, also:  pip install requests

Mixed languages
    OCR_LANGUAGE = "auto" identifies the language of each file on its own,
    choosing between the codes in OCR_LANGUAGES, and then recognises the whole
    file with that single language. One language is more accurate than several
    at once, so there is no need to sort your PDFs by language first. Files
    with a text layer are unaffected: language only matters for scans.
    To force one language for a whole run, set OCR_LANGUAGE = "fra".

Scanned PDFs
    Pages with no text layer are recognised automatically (OCR = "auto").
    Before recognising, each page is straightened, deskewed and stripped of
    its table borders, because Tesseract loses text boxed inside ruling
    lines. Pages that come back poorly are retried with heavier cleaning.
    The result is fed through the same paragraph and table logic as ordinary
    text, so scans come out in the same shape as the rest.

    Average confidence is reported per file. Below 75% the file is flagged:
    on genuinely poor scans, set OCR_ENGINE = "mistral" and paste a key.
    That sends the scanned pages to Mistral's OCR API, which handles
    degraded documents far better. It is a paid service, and unlike the
    local path it is a model rather than a character recogniser, so spot
    check its output against the original.

Where words come from
    Except for the optional Mistral path, no language model is involved.
    Text is extracted, recognised, de-hyphenated and re-flowed, never
    rewritten. After each file the script reports how much of the text layer
    reached the .txt; it should say 100%.

If something looks wrong
    columns interleaved ............ --columns 2   (or --columns 1)
    a table read as prose .......... --tables text (only if the page is
                                      almost entirely table)
    a heading swallowed as header .. --keep-headers
    paragraphs wrongly merged ...... --no-join-pages
    hyphens wrongly removed ........ --keep-hyphens
    chart labels wanted ............ --keep-sideways
    page numbers needed for citing . --page-marks
    bad scan, garbled text ......... --ocr always --ocr-dpi 400
    existing text layer is garbage . --ocr always
"""

from __future__ import annotations

# ===========================================================================
#  SETTINGS - you can edit this block instead of using the command line.
#  Leave the two folders empty ("") and the script will ask you for them.
# ===========================================================================

# Folder holding the PDFs to convert.
#   Windows example:  INPUT_FOLDER = r"C:\Users\me\Documents\PDFs"
#   macOS example:    INPUT_FOLDER = "/Users/me/Documents/PDFs"
INPUT_FOLDER = ""

# Folder where the .txt files should be written.
# Leave empty to drop each .txt next to its PDF.
OUTPUT_FOLDER = ""

# Also convert PDFs sitting in sub-folders of INPUT_FOLDER?
RECURSIVE = False

# --- text recognition for PDFs that are scans (no selectable text) --------
OCR = "auto"            # "auto"   = recognise only pages with no text layer
                        # "off"    = never, leave those pages empty
                        # "always" = send EVERY page to OCR, even pages that
                        #            already have selectable text. Use this on
                        #            PDFs whose existing text layer is garbled
                        #            (bad embedded fonts, or someone else's OCR).
                        #            With OCR_ENGINE = "mistral" this sends the
                        #            whole document to the API, so every page is
                        #            billed.
OCR_ENGINE = "tesseract"   # "tesseract" = free, local, needs Tesseract installed
                           # "mistral"   = paid API, much better on poor scans
OCR_LANGUAGE = "auto"   # "auto" picks the language per file from the list below.
                        # Or name one directly: "eng", "fra", "spa", "eng+fra"...
OCR_LANGUAGES = "eng,fra,spa"   # candidates that "auto" chooses between
OCR_DPI = 300           # 300 is the sweet spot; 400 helps on small print
OCR_MIN_CONF = 40       # drop words Tesseract is less than this % sure about
OCR_RETRY_BELOW = 75    # under this confidence, retry the page with extra cleanup
OCR_DESKEW = True       # straighten crooked scans before recognising
OCR_REMOVE_RULES = True # erase table borders first (Tesseract loses boxed text)
MISTRAL_API_KEY = ""    # only needed when OCR_ENGINE = "mistral"
MISTRAL_MODEL = "mistral-ocr-latest"
MISTRAL_BATCH_PAGES = 40   # pages per API request; lower it if long files fail

# --- optional, only change these if the output needs fixing ---------------
COLUMNS = "auto"        # "auto", "1" (never split), "2" (always split)
TABLES = "lines"        # "lines" (normal), "text" (pages that are all table),
                        # "none" (read tables as ordinary text)
PAGE_MARKS = False      # insert "[page N]" between pages
TABLE_MARKERS = False   # wrap tables in [TABLE] ... [/TABLE]
KEEP_BULLETS = True     # keep a leading "- " on list items (OCR output only)
STRIP_STRIKETHROUGH = False   # leave "~~2017~~2020/08" alone. Removing the ~~
                        # markers would weld the struck-out text onto its
                        # replacement and invent a number that is in no document.
KEEP_HYPHENS = False    # True = never join "mat-" + "ter" into "matter"
KEEP_HEADERS = False    # True = keep running headers, footers, page numbers
KEEP_SIDEWAYS = False   # True = keep sideways chart labels instead of dropping
JOIN_PAGES = True       # stitch a paragraph split across a page break
TABLE_WIDTH = 100       # widest a rendered table may be, in characters
VERBOSE = False         # print a line per page about what was detected

# ===========================================================================
#  Nothing below this line needs editing.
# ===========================================================================

import argparse
import bisect
import math
import re
import statistics
import sys
import tempfile
import textwrap
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("Missing dependency. Run:  pip install pdfplumber pypdf")

# --------------------------------------------------------------------------
# text hygiene
# --------------------------------------------------------------------------

LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
    "\ufb04": "ffl", "\ufb05": "ft", "\ufb06": "st", "\u0133": "ij",
}
HYPHENS = ("-", "\u2010", "\u2011")

_ROMAN = r"(?=[ivxlcdm])m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"
_NUM = rf"(?:\d{{1,4}}|{_ROMAN})"
PAGE_NUM_RE = re.compile(
    rf"""^[\s\[\(\-\u2013\u2014]*
         (?:(?:page|p|pp|pag|p\u00e1g|seite|str)\.?\s*)?
         {_NUM}
         (?:\s*(?:/|\||of|de|sur|von|out\s+of)\s*{_NUM})?
         [\s\]\)\-\u2013\u2014\.]*$""",
    re.I | re.X,
)
BULLET_RE = re.compile(
    r"^\s*(?:[\u2022\u00b7\u25aa\u25e6\u2043\u2219*]\s+"
    r"|[\u2013\u2014\-]\s+"
    r"|\(?\d{1,3}[.)]\s+"
    r"|\(?[a-zA-Z][.)]\s+"
    r"|\(?[ivxlcdm]{1,5}[.)]\s+)"
)
TERMINAL_RE = re.compile(r"[.!?:;\u2026][\"'\u201d\u2019\u00bb\)\]]?\s*$")
LOWER_START_RE = re.compile(r"^[a-z\u00e0-\u00ff\u0153\(\u201c\"']")


def clean(s: str) -> str:
    """Normalise unicode. Never changes the words themselves."""
    s = unicodedata.normalize("NFC", s)
    for bad, good in LIGATURES.items():
        s = s.replace(bad, good)
    s = s.replace("\u00ad", "")                            # soft hyphen
    s = s.replace("\u00a0", " ").replace("\u202f", " ")    # non-breaking spaces
    s = "".join(c for c in s if c == "\t" or unicodedata.category(c) != "Cc")
    return re.sub(r"[ \t]+", " ", s).strip()


def squeeze(s: str) -> str:
    return re.sub(r"\s+", "", s)


def signature(s: str) -> str:
    """Fingerprint of a line, digits blurred, used to spot running heads."""
    t = re.sub(r"\d+", "#", s.lower())
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"^\W+|\W+$", "", t, flags=re.UNICODE)


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------

@dataclass
class Line:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float = 10.0
    bold: bool = False
    tabular: bool = False      # looks like a row of table cells
    col: int = 0               # column index on the page
    cells: list = field(default_factory=list)   # [(x0, text)] split at wide gaps

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def width(self) -> float:
        return self.x1 - self.x0


@dataclass
class Block:
    kind: str                  # "para" | "table" | "mark"
    text: str
    top: float
    page: int
    heading: bool = False


@dataclass
class PageData:
    number: int
    width: float
    height: float
    words: list = field(default_factory=list)
    chars: list = field(default_factory=list)
    tables: list = field(default_factory=list)      # (top, rendered text)
    lines: list = field(default_factory=list)       # flat, reading order
    groups: list = field(default_factory=list)      # [(lines, col_index)]
    raw_chars: int = 0
    sideways_chars: int = 0
    looks_scanned: bool = False
    two_col: bool = False
    ocr: bool = False
    ocr_conf: float = 0.0
    ocr_text: str = ""


# --------------------------------------------------------------------------
# 1. straighten sideways pages
# --------------------------------------------------------------------------

def text_angle(char) -> int:
    a, b = char["matrix"][0], char["matrix"][1]
    if a == 0 and b == 0:
        return 0
    return int(round(math.degrees(math.atan2(b, a)) / 90.0) * 90) % 360


def _release(page):
    for m in ("flush_cache", "close"):
        try:
            getattr(page, m)()
        except Exception:
            pass


def straighten(path: Path, tmpdir: str, verbose=False, log=print):
    """Rewrite the PDF so that every page reads left to right."""
    angles = {}
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            c = Counter(text_angle(ch) for ch in page.chars)
            if c:
                angle, n = c.most_common(1)[0]
                if angle and n > sum(c.values()) * 0.5:
                    angles[i] = angle
            _release(page)
    if not angles:
        return path
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        log("  ! pypdf missing, sideways pages left as they are "
            "(pip install pypdf)")
        return path
    reader, writer = PdfReader(str(path)), PdfWriter()
    for i, pg in enumerate(reader.pages):
        if i in angles:
            pg.rotate(angles[i])
        writer.add_page(pg)
    out = Path(tmpdir) / (path.stem + "__straight.pdf")
    with open(out, "wb") as fh:
        writer.write(fh)
    if verbose:
        for i, a in sorted(angles.items()):
            log(f"  page {i + 1}: sideways text ({a}\u00b0) -> straightened")
    return out


# --------------------------------------------------------------------------
# 2. tables
# --------------------------------------------------------------------------

def render_table(rows, max_width=100, markers=False) -> str:
    grid = [[clean(str(c)) if c is not None else "" for c in row] for row in rows]
    if not grid:
        return ""
    ncols = max(len(r) for r in grid)
    grid = [r + [""] * (ncols - len(r)) for r in grid]
    keep = [j for j in range(ncols) if any(r[j] for r in grid)]
    grid = [[r[j] for j in keep] for r in grid]
    grid = [r for r in grid if any(r)]
    if not grid or len(grid[0]) < 2:
        return ""
    ncols = len(grid[0])

    widths = [max(len(r[j]) for r in grid) for j in range(ncols)]
    avail = max(max_width - 3 * (ncols - 1), 8 * ncols)
    guard = 0
    while sum(widths) > avail and max(widths) > 8 and guard < 20000:
        widths[widths.index(max(widths))] -= 1
        guard += 1

    def fmt(cells):
        wrapped = [textwrap.wrap(c, w) or [""] for c, w in zip(cells, widths)]
        h = max(len(x) for x in wrapped)
        out = []
        for k in range(h):
            out.append(" | ".join(
                (wrapped[j][k] if k < len(wrapped[j]) else "").ljust(widths[j])
                for j in range(ncols)).rstrip())
        return out

    body = fmt(grid[0])
    if len(grid) > 1:
        body.append("-+-".join("-" * w for w in widths))
        for row in grid[1:]:
            body += fmt(row)
    txt = "\n".join(body)
    return f"[TABLE]\n{txt}\n[/TABLE]" if markers else txt


def read_tables(page, args):
    """Return (list of (top, rendered), list of bboxes)."""
    if args.tables == "none":
        return [], []
    settings = ({"vertical_strategy": "text", "horizontal_strategy": "text"}
                if args.tables == "text" else {})
    try:
        found = page.find_tables(settings) if settings else page.find_tables()
    except Exception:
        return [], []
    out, boxes = [], []
    for t in found:
        try:
            rows = t.extract()
        except Exception:
            continue
        if not rows or len(rows) < 2 or len(rows[0]) < 2:
            continue
        cells = sum(len(r) for r in rows) or 1
        filled = sum(1 for r in rows for c in r if c and str(c).strip())
        if filled / cells < 0.3 or filled < 4:
            continue
        rendered = render_table(rows, args.width, args.table_markers)
        if rendered:
            out.append((t.bbox[1], rendered))
            boxes.append(t.bbox)
    return out, boxes


# --------------------------------------------------------------------------
# 2b. OCR for pages that hold no selectable text
# --------------------------------------------------------------------------

_LANG_HINTS = {
    "eng": "the of and to in that is for with as by this are be on it from which "
           "or an at have has not was were their been will would there",
    "fra": "le la les des du et que qui dans pour sur une est aux par ne pas plus "
           "avec cette son leur sont ete etre ainsi ou tout comme entre lors",
    "spa": "el los las del que para por con una son como este esta sus segun "
           "sobre entre desde tambien todos hacia cuando donde mismo",
    "deu": "der die das und den von zu mit fur im ist des auf dem nicht auch eine "
           "als werden wird sind bei nach oder aus einer",
    "ita": "il lo la gli delle della che per con una non sono nel alla dei come "
           "anche piu essere stato sulla negli quale",
    "por": "os as do da dos nas que para com uma nao por no na se mais como sao "
           "pelo pela seus suas entre quando",
    "nld": "de het een van en dat is op met voor zijn niet aan door worden werd "
           "deze wordt bij ook naar over",
}
_LANG_SETS = {k: set(v.split()) for k, v in _LANG_HINTS.items()}
_LANG_SEEN = Counter(w for v in _LANG_SETS.values() for w in v)
# only words belonging to a single language get a vote, so "de"/"la"/"un" abstain
LANG_MARKERS = {k: {w for w in v if _LANG_SEEN[w] == 1} for k, v in _LANG_SETS.items()}

LANG_NAMES = {"eng": "English", "fra": "French", "spa": "Spanish",
              "deu": "German", "ita": "Italian", "por": "Portuguese",
              "nld": "Dutch"}


def detect_language(text, candidates):
    """Guess the language of a page. Returns (code, score); code is None if
    the text is too short or two languages score too closely."""
    toks = re.findall(r"[a-zA-Z\u00e0-\u00f6\u00f8-\u00ff']+", text.lower())
    if len(toks) < 25:
        return None, 0.0
    scores = {}
    for lang in candidates:
        marks = LANG_MARKERS.get(lang)
        if marks:
            scores[lang] = sum(1 for t in toks if t in marks) / len(toks)
    if not scores:
        return None, 0.0
    best = max(scores, key=scores.get)
    others = [v for k, v in scores.items() if k != best]
    runner = max(others) if others else 0.0
    if scores[best] < 0.02 or scores[best] < runner * 1.6:
        return None, scores[best]
    return best, scores[best]


def installed_languages():
    try:
        import pytesseract
        return set(pytesseract.get_languages(config="")) - {"osd"}
    except Exception:
        return set()


def resolve_languages(args, log=print):
    """Check the requested languages exist; work out the auto candidates."""
    have = installed_languages()
    if not have:
        return
    wanted = ([c.strip() for c in args.ocr_languages.split(",") if c.strip()]
              if args.ocr_language == "auto" else args.ocr_language.split("+"))
    missing = [w for w in wanted if w not in have]
    if missing:
        log("   ! language pack(s) not installed: " + ", ".join(missing)
            + "\n     installed: " + ", ".join(sorted(have))
            + "\n     macOS: brew install tesseract-lang   "
              "Linux: sudo apt install tesseract-ocr-fra")
    keep = [w for w in wanted if w in have] or (["eng"] if "eng" in have
                                                else sorted(have)[:1])
    if args.ocr_language == "auto":
        args.ocr_candidates = keep
        args.ocr_trial_language = "+".join(keep)
    else:
        args.ocr_language = "+".join(keep)


def needs_ocr(pd, mode) -> bool:
    if mode == "off":
        return False
    if mode == "always":
        return True
    return sum(len(w["text"]) for w in pd.words) < 20


def check_ocr(engine, key=""):
    """Return (usable, message). Called once before a run."""
    if engine == "tesseract":
        try:
            import pytesseract
            v = pytesseract.get_tesseract_version()
            return True, f"Tesseract {v}"
        except Exception:
            return False, ("Tesseract is not installed or not on PATH.\n"
                           "  Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
                           "  macOS:   brew install tesseract\n"
                           "  Linux:   sudo apt install tesseract-ocr\n"
                           "  then:    pip install pytesseract")
    if engine == "mistral":
        try:
            import requests  # noqa: F401
        except ImportError:
            return False, "pip install requests"
        if not key.strip():
            return False, "MISTRAL_API_KEY is empty in the SETTINGS block."
        return True, "Mistral OCR API"
    return False, f"unknown OCR engine: {engine}"


def _estimate_skew(img, limit=3.0, step=0.25):
    """Angle, in degrees, that makes the text lines most horizontal."""
    import numpy as np
    from PIL import Image
    small = img.resize((640, max(1, int(640 * img.height / img.width))),
                       Image.BILINEAR)
    best_angle, best_score = 0.0, -1.0
    angle = -limit
    while angle <= limit + 1e-9:
        rot = small.rotate(angle, resample=Image.BILINEAR, fillcolor=255)
        rows = (np.asarray(rot) < 160).sum(axis=1).astype(float)
        score = float(((rows[1:] - rows[:-1]) ** 2).sum())   # sharper lines win
        if score > best_score:
            best_score, best_angle = score, angle
        angle += step
    return best_angle


def _remove_rules(img, h_frac=0.10, v_frac=0.04):
    """Erase table borders and rules: Tesseract loses text boxed inside them."""
    import numpy as np
    from PIL import Image
    a = np.array(img)
    dark = a < 160
    h, w = dark.shape
    out = a.copy()
    for axis, min_len in ((1, int(h_frac * w)), (0, int(v_frac * h))):
        m = dark if axis == 1 else dark.T
        pad = np.zeros((m.shape[0], 1), dtype=np.int8)
        d = np.diff(np.concatenate([pad, m.astype(np.int8), pad], axis=1), axis=1)
        sr, sc = np.nonzero(d == 1)
        er, ec = np.nonzero(d == -1)
        n = min(len(sr), len(er))
        sr, sc, ec = sr[:n], sc[:n], ec[:n]
        keep = (ec - sc) >= min_len
        for r, c0, c1 in zip(sr[keep], sc[keep], ec[keep]):
            if axis == 1:
                out[r, c0:c1] = 255
            else:
                out[c0:c1, r] = 255
    return Image.fromarray(out)


def prepare_image(page, args):
    """Render a page and clean it up before recognition."""
    from PIL import Image, ImageOps
    img = page.to_image(resolution=args.ocr_dpi).original.convert("L")
    img = ImageOps.autocontrast(img)

    # 1. quarter-turns (a page scanned sideways)
    try:
        import pytesseract
        osd = pytesseract.image_to_osd(img)
        turn = int(re.search(r"Rotate: (\d+)", osd).group(1))
        if turn:
            img = img.rotate(-turn, expand=True, resample=Image.BICUBIC,
                             fillcolor=255)
    except Exception:
        pass                                  # best effort only

    # 2. small skew from a crooked scan
    if args.ocr_deskew:
        try:
            angle = _estimate_skew(img)
            if abs(angle) >= 0.2:
                img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
        except Exception:
            pass

    # 3. table borders
    if args.ocr_remove_rules:
        try:
            img = _remove_rules(img)
        except Exception:
            pass
    return img


def _tess_pass(img, args):
    """One recognition pass. Returns (words, chars, mean_conf, confidence mass)."""
    import pytesseract
    from pytesseract import Output
    data = pytesseract.image_to_data(
        img, lang=args.ocr_language, output_type=Output.DICT,
        config="--oem 1 --psm 3")

    scale = 72.0 / args.ocr_dpi          # pixels -> PDF points
    words, chars, confs = [], [], []
    for i, txt in enumerate(data["text"]):
        txt = txt.strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if not txt or conf < args.ocr_min_conf:
            continue
        x0 = data["left"][i] * scale
        top = data["top"][i] * scale
        x1 = x0 + data["width"][i] * scale
        bottom = top + data["height"][i] * scale
        words.append({"text": txt, "x0": x0, "x1": x1, "top": top,
                      "bottom": bottom, "upright": True})
        # one synthetic character per word, so the layout code can judge size
        chars.append({"text": txt[0], "x0": x0, "x1": x1, "top": top,
                      "bottom": bottom, "upright": True, "fontname": "OCR",
                      "size": (bottom - top) * 1.05})
        confs.append(conf)
    mean = statistics.mean(confs) if confs else 0.0
    return words, chars, mean, sum(confs)


def auto_language(page, args, log=print):
    """Recognise one page with every candidate at once, then name the language."""
    probe = argparse.Namespace(**vars(args))
    probe.ocr_language = args.ocr_trial_language
    try:
        words, _, _ = ocr_tesseract(page, probe)
    except Exception:
        return args.ocr_candidates[0]
    code, score = detect_language(" ".join(w["text"] for w in words),
                                  args.ocr_candidates)
    if code:
        log(f"   language detected: {LANG_NAMES.get(code, code)} ({code})")
        return code
    log(f"   language unclear, using {probe.ocr_language}")
    return probe.ocr_language


def ocr_tesseract(page, args):
    """Recognise a page, retrying with heavier cleanup when quality is poor."""
    from PIL import ImageFilter
    img = prepare_image(page, args)
    words, chars, mean, mass = _tess_pass(img, args)

    if mean < args.ocr_retry_below:
        # blurred, speckled or low-resolution scan: denoise, then sharpen
        try:
            harder = (img.filter(ImageFilter.MedianFilter(3))
                         .filter(ImageFilter.UnsharpMask(radius=2, percent=150,
                                                         threshold=3)))
            w2, c2, mean2, mass2 = _tess_pass(harder, args)
            if mass2 > mass:            # more text, at comparable confidence
                return w2, c2, mean2
        except Exception:
            pass
    return words, chars, mean


def _mistral_batch(pdf_path, page_numbers, args, log):
    """Send one batch of pages to the OCR API. Returns ({page: markdown}, scores)."""
    import base64
    import io
    import json
    import requests
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for n in page_numbers:
        writer.add_page(reader.pages[n - 1])
    buf = io.BytesIO()
    writer.write(buf)
    payload = {
        "model": args.mistral_model,
        "document": {
            "type": "document_url",
            "document_url": "data:application/pdf;base64,"
                            + base64.b64encode(buf.getvalue()).decode(),
        },
        "confidence_scores_granularity": "page",
        "include_image_base64": False,
    }
    r = requests.post("https://api.mistral.ai/v1/ocr",
                      headers={"Authorization": f"Bearer {args.mistral_key}",
                               "Content-Type": "application/json"},
                      data=json.dumps(payload), timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"Mistral OCR refused the request "
                           f"({r.status_code}): {r.text[:300]}")
    out, scores = {}, []
    for i, pg in enumerate(r.json().get("pages", [])):
        if i < len(page_numbers):
            out[page_numbers[i]] = pg.get("markdown", "") or ""
            cs = pg.get("confidence_scores") or {}
            if cs.get("average_page_confidence_score") is not None:
                scores.append(float(cs["average_page_confidence_score"]))
    return out, scores


def mistral_ocr(pdf_path, page_numbers, args, log=print):
    """Send the listed pages to the Mistral OCR API. Returns {page_no: text}.

    Long documents are sent in batches, so one oversized request cannot fail
    the whole file and a failed batch only costs the pages inside it.
    """
    size = max(1, int(args.mistral_batch_pages))
    batches = [page_numbers[i:i + size]
               for i in range(0, len(page_numbers), size)]
    texts, scores, failed, per_page = {}, [], [], {}
    for k, batch in enumerate(batches, 1):
        if len(batches) > 1:
            log(f"   Mistral OCR: batch {k}/{len(batches)} "
                f"(pages {batch[0]}-{batch[-1]})")
        try:
            got, sc = _mistral_batch(pdf_path, batch, args, log)
            texts.update(got)
            scores += sc
            for n, v in zip(batch, sc):
                per_page[n] = v * 100.0
        except Exception as exc:
            failed += batch
            log(f"   ! Mistral OCR failed on pages {batch[0]}-{batch[-1]}: {exc}")
    if scores:
        log(f"   Mistral OCR confidence: {statistics.mean(scores):.0%} "
            f"over {len(page_numbers) - len(failed)} page(s)")
    blank = [p for p, t in texts.items() if not t.strip()]
    if blank:
        log(f"   ! Mistral returned nothing for {len(blank)} page(s) "
            f"({_ranges(blank)}); the PDF's own text layer was kept for them")
    return texts, per_page


def _ranges(numbers):
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'"""
    out, nums = [], sorted(set(numbers))
    start = prev = nums[0]
    for n in nums[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        out.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    return ", ".join(out)


MD_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MD_REFLINK_RE = re.compile(r"\[([^\]]*)\]\[[^\]]*\]")
MD_AUTOLINK_RE = re.compile(r"<((?:https?|mailto:)[^>\s]+)>")
MD_FOOTNOTE_RE = re.compile(r"\[\^([^\]]+)\]")
_HTML_TAGS = ("br|sup|sub|b|i|u|em|strong|span|div|p|font|small|big|code|pre"
              "|table|thead|tbody|tr|td|th|ul|ol|li|a|img|hr|h[1-6]")
MD_HTML_RE = re.compile(rf"</?(?:{_HTML_TAGS})\b[^>]*>", re.I)
MD_CODE_RE = re.compile(r"`+([^`]+)`+")
MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.S)
MD_ITAL_RE = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])"
                        r"|(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])")
MD_STRIKE_RE = re.compile(r"~~(.+?)~~", re.S)
MD_MATHCMD_RE = re.compile(r"\\(?:text|textrm|mathrm|mathbf|textbf|textit)\{([^{}]*)\}")
MD_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.S)
MD_ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~$%&])")
MD_RULE_RE = re.compile(r"^ {0,3}([-*_])\s*(?:\1\s*){2,}$")
MD_SETEXT_RE = re.compile(r"^ {0,3}(={2,}|-{2,})\s*$")
MD_FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
MD_BULLET_RE = re.compile(r"^ {0,3}[-*+\u2022]\s+")
MD_QUOTE_RE = re.compile(r"^ {0,3}(?:>\s?)+")
_PLACEHOLDER = "\uE000"


def _math_or_money(m):
    """Strip $...$ only when it really is maths; "$100 and $200" is money."""
    if m.group(1) is not None:                     # $$ ... $$ is always maths
        return m.group(1).strip()
    inner = m.group(2) or ""
    # maths looks like "$x_1$" or "$4$"; money looks like "$100 and $200",
    # where the span between the two signs runs across whitespace
    if inner and (re.search(r"[\\^_{}=]", inner) or not re.search(r"\s", inner)):
        return inner.strip()
    return m.group(0)


def strip_markdown(s: str) -> str:
    """Remove markdown mark-up, keeping every word it was wrapped around."""
    if not s:
        return s
    # protect backslash-escaped characters so \* is not read as emphasis
    escaped = []

    def _hide(m):
        escaped.append(m.group(1))
        return f"{_PLACEHOLDER}{len(escaped) - 1}{_PLACEHOLDER}"

    s = MD_ESCAPE_RE.sub(_hide, s)

    s = MD_IMG_RE.sub("", s)
    s = MD_LINK_RE.sub(r"\1", s)
    s = MD_REFLINK_RE.sub(r"\1", s)
    s = MD_AUTOLINK_RE.sub(r"\1", s)
    s = MD_FOOTNOTE_RE.sub(r"[\1]", s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = MD_HTML_RE.sub("", s)
    s = MD_CODE_RE.sub(r"\1", s)
    s = MD_MATH_RE.sub(_math_or_money, s)     # delimiters first, so that the
    s = MD_MATHCMD_RE.sub(r"\1", s)           # \text{...} test still applies
    for _ in range(2):                       # nested **bold *italic* **
        s = MD_BOLD_RE.sub(lambda m: m.group(1) or m.group(2) or "", s)
        s = MD_ITAL_RE.sub(lambda m: m.group(1) or m.group(2) or "", s)
    if STRIP_STRIKETHROUGH:
        s = MD_STRIKE_RE.sub(r"\1", s)

    def _show(m):
        return escaped[int(m.group(1))]

    s = re.sub(f"{_PLACEHOLDER}(\\d+){_PLACEHOLDER}", _show, s)
    return s


def markdown_to_blocks(md, page_no, args):
    """Turn the OCR model's markdown into plain paragraph and table blocks."""
    blocks, buf, table = [], [], []
    in_fence = False

    def flush_text(heading=False):
        if buf:
            txt = clean(strip_markdown(" ".join(buf)))
            if txt:
                blocks.append(Block("para", txt, len(blocks), page_no, heading))
            buf.clear()

    def flush_table():
        if not table:
            return
        rows = []
        for row in table:
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]
            if cells and all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                continue                       # the |---|---| separator row
            rows.append([clean(strip_markdown(c)) for c in cells])
        rendered = render_table(rows, args.width, args.table_markers) if rows else ""
        if rendered:
            blocks.append(Block("table", rendered, len(blocks), page_no))
        elif rows:
            blocks.append(Block("para", clean(" ".join(" ".join(r) for r in rows)),
                                len(blocks), page_no))
        table.clear()

    for raw in md.splitlines():
        stripped = raw.strip()

        if MD_FENCE_RE.match(raw):             # ``` … ``` : drop the fence, keep text
            flush_text()
            in_fence = not in_fence
            continue
        if in_fence:
            if stripped:
                buf.append(stripped)
            else:
                flush_text()
            continue

        if stripped.startswith("|") and stripped.count("|") >= 2:
            flush_text()
            table.append(stripped)
            continue
        flush_table()

        if not stripped:
            flush_text()
            continue

        if MD_SETEXT_RE.match(stripped) and buf:
            flush_text(heading=True)           # underlined heading
            continue
        if MD_RULE_RE.match(stripped):         # --- *** ___
            flush_text()
            continue

        stripped = MD_QUOTE_RE.sub("", stripped) or stripped

        if re.match(r"^#{1,6}\s", stripped):       # "# Heading", not "#3 vessel"
            flush_text()
            buf.append(stripped.lstrip("#").strip().rstrip("#").strip())
            flush_text(heading=True)
            continue

        if MD_BULLET_RE.match(stripped):
            flush_text()
            stripped = MD_BULLET_RE.sub("- " if args.keep_bullets else "", stripped)
        elif BULLET_RE.match(stripped):
            flush_text()

        buf.append(stripped)

    flush_table()
    flush_text()
    return blocks


# --------------------------------------------------------------------------
# 3. words -> lines
# --------------------------------------------------------------------------

def read_page(page, pno, args) -> PageData:
    pd = PageData(pno, float(page.width), float(page.height))
    try:
        pd.raw_chars = len(squeeze(clean((page.extract_text() or "").replace("\n", " "))))
    except Exception:
        pd.raw_chars = 0

    pd.tables, boxes = read_tables(page, args)

    kw = dict(keep_blank_chars=False, use_text_flow=False, y_tolerance=args.y_tol)
    if args.x_tol is not None:
        kw["x_tolerance"] = args.x_tol
    try:
        words = page.extract_words(**kw)
    except TypeError:
        words = page.extract_words()

    def in_table(w):
        cx, cy = (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2
        return any(x0 - 1 <= cx <= x1 + 1 and t - 1 <= cy <= b + 1
                   for x0, t, x1, b in boxes)

    sideways = [w for w in words if not w.get("upright", True)]
    pd.sideways_chars = sum(len(w["text"]) for w in sideways)
    if args.keep_sideways and sideways:
        txt = clean(" ".join(w["text"] for w in
                             sorted(sideways, key=lambda w: (-w["bottom"], w["x0"]))))
        if txt:
            pd.tables.append((1e9, txt))
            pd.sideways_chars = 0

    pd.words = [w for w in words if w.get("upright", True) and not in_table(w)]
    pd.chars = [c for c in page.chars
                if c.get("text", "").strip() and c.get("upright", True)]

    if len(pd.words) < 3:
        imgs = getattr(page, "images", []) or []
        area = sum(abs((i["x1"] - i["x0"]) * (i["bottom"] - i["top"])) for i in imgs)
        if area > 0.4 * pd.width * pd.height:
            pd.looks_scanned = True
    return pd


def group_rows(words):
    """Group words into visual rows (same baseline)."""
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        h = w["bottom"] - w["top"]
        for r in reversed(rows[-4:]):
            ov = min(r["bottom"], w["bottom"]) - max(r["top"], w["top"])
            if ov > 0.45 * min(h, r["bottom"] - r["top"]):
                r["ws"].append(w)
                r["top"] = min(r["top"], w["top"])
                r["bottom"] = max(r["bottom"], w["bottom"])
                break
        else:
            rows.append({"ws": [w], "top": w["top"], "bottom": w["bottom"]})
    for r in rows:
        r["ws"].sort(key=lambda w: w["x0"])
    return rows


def wide_gaps(ws, minw):
    return [(ws[i]["x1"], ws[i + 1]["x0"]) for i in range(len(ws) - 1)
            if ws[i + 1]["x0"] - ws[i]["x1"] >= minw]


def find_gutter(words, rows=None, force=False):
    """A two-column gutter is one wide gap shared by most rows at the same x.

    Rows holding two or more wide gaps are table rows, not prose, and are
    ignored so that a wide table is never mistaken for two columns.
    """
    if len(words) < 40:
        return None
    rows = rows if rows is not None else group_rows(words)
    rows = [r for r in rows if len(r["ws"]) >= 2]
    if len(rows) < 6:
        return None
    gaps = [b - a for r in rows for a, b in
            zip([w["x1"] for w in r["ws"]], [w["x0"] for w in r["ws"][1:]]) if b > a]
    unit = statistics.median(gaps) if gaps else 3.0
    minw = max(8.0, 2.5 * unit)

    events = []
    for r in rows:
        wg = wide_gaps(r["ws"], minw)
        if len(wg) == 1:                       # exactly one -> column gutter
            events.append((wg[0][0], 1))
            events.append((wg[0][1], -1))
    if not events:
        return None
    events.sort()
    cur = best = 0
    span = (0.0, 0.0)
    for i, (x, d) in enumerate(events):
        cur += d
        if d == 1 and cur > best:
            nxt = events[i + 1][0] if i + 1 < len(events) else x
            best, span = cur, (x, nxt)
    if best < max(3, int(0.45 * len(rows))) and not force:
        return None
    gx = (span[0] + span[1]) / 2
    x_min = min(w["x0"] for w in words)
    x_max = max(w["x1"] for w in words)
    pos = (gx - x_min) / max(x_max - x_min, 1)
    if not 0.3 <= pos <= 0.7:
        return None
    left = sum(1 for w in words if w["x1"] <= gx)
    right = sum(1 for w in words if w["x0"] >= gx)
    if not force and (left < 0.2 * len(words) or right < 0.2 * len(words)):
        return None
    return gx


def rows_to_lines(words, chars, gx, args, rows=None):
    """Turn visual rows into text lines, splitting them at the column gutter."""
    rows = rows if rows is not None else group_rows(words)

    all_gaps = [ws[i + 1]["x0"] - ws[i]["x1"]
                for r in rows for ws in [r["ws"]]
                for i in range(len(ws) - 1)
                if ws[i + 1]["x0"] - ws[i]["x1"] > 0]
    unit = statistics.median(all_gaps) if all_gaps else 3.0

    def make(ws, col):
        ws = sorted(ws, key=lambda w: w["x0"])
        text = clean(" ".join(w["text"] for w in ws))
        if not text:
            return None
        ln = Line(text=text, x0=min(w["x0"] for w in ws), x1=max(w["x1"] for w in ws),
                  top=min(w["top"] for w in ws), bottom=max(w["bottom"] for w in ws),
                  col=col)
        # a row with several wide internal gaps is a table row, not prose:
        # keep it on its own line instead of folding it into a paragraph
        cut = max(4.0 * unit, 18)
        cells, buf = [], [ws[0]]
        for i in range(len(ws) - 1):
            if ws[i + 1]["x0"] - ws[i]["x1"] > cut:
                cells.append((buf[0]["x0"], " ".join(w["text"] for w in buf)))
                buf = []
            buf.append(ws[i + 1])
        cells.append((buf[0]["x0"], " ".join(w["text"] for w in buf)))
        ln.cells = [(x, clean(t)) for x, t in cells]
        ln.tabular = len(ws) >= 3 and len(cells) >= 3   # candidate only
        return ln

    lines = []
    for r in rows:
        ws = r["ws"]
        if gx is None:
            ln = make(ws, 0)
            if ln:
                lines.append(ln)
            continue
        straddles = any(w["x0"] < gx - 2 and w["x1"] > gx + 2 for w in ws)
        left = [w for w in ws if (w["x0"] + w["x1"]) / 2 < gx]
        right = [w for w in ws if (w["x0"] + w["x1"]) / 2 >= gx]
        if straddles or not left or not right:
            ln = make(ws, -1 if straddles else (0 if left else 1))
            if ln:
                lines.append(ln)
        else:
            for part, col in ((left, 0), (right, 1)):
                ln = make(part, col)
                if ln:
                    lines.append(ln)

    # font size and weight, taken from the underlying characters
    lines.sort(key=lambda l: (l.top, l.x0))
    tops = [l.top for l in lines]
    buckets = [[] for _ in lines]
    for ch in chars:
        cy = (ch["top"] + ch["bottom"]) / 2
        cx = (ch["x0"] + ch["x1"]) / 2
        i = bisect.bisect_right(tops, cy) - 1
        for j in range(max(0, i - 2), min(len(lines), i + 3)):
            l = lines[j]
            if l.top - 0.5 <= cy <= l.bottom + 0.5 and l.x0 - 1 <= cx <= l.x1 + 1:
                buckets[j].append(ch)
                break
    for l, bucket in zip(lines, buckets):
        if bucket:
            l.size = statistics.median(float(c.get("size", 10)) for c in bucket)
            l.bold = sum(1 for c in bucket
                         if "bold" in str(c.get("fontname", "")).lower()) > len(bucket) / 2
    return lines


def order_columns(lines, gx):
    """Reading order for a two-column page: bands separated by full-width lines."""
    if gx is None:
        return [(sorted(lines, key=lambda l: (l.top, l.x0)), 0)]
    spanning = sorted((l for l in lines if l.col == -1), key=lambda l: l.top)
    rest = [l for l in lines if l.col != -1]
    groups, prev = [], -1e9
    for s in spanning + [None]:
        end = s.top if s else 1e9
        band = [l for l in rest if prev <= l.cy < end]
        for col in (0, 1):
            part = sorted([l for l in band if l.col == col], key=lambda l: (l.top, l.x0))
            if part:
                groups.append((part, col))
        if s:
            groups.append(([s], -1))
            prev = s.bottom
    return groups


# --------------------------------------------------------------------------
# 4. running headers / footers
# --------------------------------------------------------------------------

def find_running(pages, body=10.0, band=0.10, ratio=0.45):
    if len(pages) < 2:
        return set()
    counts, spots = Counter(), {}
    for pd in pages:
        seen = set()
        for ln in pd.lines:
            if ln.size > body + 0.5:
                continue                 # bigger than body text: a real heading
            if ln.bottom < band * pd.height or ln.top > (1 - band) * pd.height:
                sig = signature(ln.text)
                if sig and len(sig) < 200 and sig not in seen:
                    seen.add(sig)
                    spots.setdefault(sig, []).append(ln.top)
        counts.update(seen)
    threshold = max(2, int(round(ratio * len(pages))))
    out = set()
    for sig, n in counts.items():
        if n < threshold:
            continue
        ys = spots[sig]
        if len(ys) > 1 and (max(ys) - min(ys)) > 12:
            continue                     # not at a stable height: real content
        out.add(sig)
    return out


def strip_running(pd, running, body=10.0, band=0.10):
    drop, chars = set(), 0
    for ln in pd.lines:
        in_band = ln.bottom < band * pd.height or ln.top > (1 - band) * pd.height
        if (ln.size <= body + 0.5 and signature(ln.text) in running) or (
                in_band and len(ln.text) <= 24 and PAGE_NUM_RE.match(ln.text)):
            drop.add(id(ln))
            chars += len(squeeze(ln.text))
    if drop:
        pd.lines = [l for l in pd.lines if id(l) not in drop]
        pd.groups = [([l for l in g if id(l) not in drop], c) for g, c in pd.groups]
        pd.groups = [(g, c) for g, c in pd.groups if g]
    return len(drop), chars


# --------------------------------------------------------------------------
# 5. lines -> paragraphs
# --------------------------------------------------------------------------

def join_lines(a: str, b: str, keep_hyphens: bool) -> str:
    if a.endswith(HYPHENS) and len(a) > 1 and a[-2].isalpha() and b[:1].isalpha():
        if not keep_hyphens and b[:1].islower():
            return a[:-1] + b                 # "mat-" + "ter" -> "matter"
        return a[:-1] + "-" + b               # "Franco-" + "German"
    return a + " " + b


def is_heading(ln: Line, body: float, left: float, right: float) -> bool:
    if len(ln.text) > 90 or ln.tabular:
        return False
    short = ln.x1 < right - 0.2 * max(right - left, 1)
    big = ln.size > body + 0.8
    caps = ln.text.isupper() and len(ln.text) > 3
    return bool(short and (big or ln.bold or caps))


def metrics(lines, body):
    xs1 = sorted(l.x1 for l in lines)
    right = xs1[int(0.9 * (len(xs1) - 1))] if xs1 else 0.0
    left = min((l.x0 for l in lines), default=0.0)
    steps = [lines[i + 1].top - lines[i].top for i in range(len(lines) - 1)
             if 0 < lines[i + 1].top - lines[i].top < 4 * body]
    pitch = statistics.median(steps) if steps else 1.2 * body
    return left, right, pitch


def reconstruct_table(lines, body, args):
    """Align a run of table-like rows into columns using their x positions.

    Returns None when the rows do not really line up, which is how justified
    prose with wide word spacing is told apart from a genuine table.
    """
    tol = max(6.0, 0.6 * body)
    xs = sorted(x for l in lines for x, _ in l.cells)
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= tol:
            groups[-1].append(x)
        else:
            groups.append([x])
    centres = [statistics.mean(g) for g in groups]
    widest = max(len(l.cells) for l in lines)
    if len(centres) < 2 or len(centres) > widest + 1:
        return None                     # cells do not line up: not a table
    rows = []
    for l in lines:
        row = [""] * len(centres)
        for x, t in l.cells:
            j = min(range(len(centres)), key=lambda k: abs(centres[k] - x))
            row[j] = (row[j] + " " + t).strip()
        if sum(1 for c in row if c) < 2:
            return None
        rows.append(row)
    return render_table(rows, args.width, args.table_markers) or None


def build_paragraphs(lines, page_no, body, keep_hyphens, m=None, args=None):
    if not lines:
        return []
    left, right, pitch = m if m else metrics(lines, body)
    span = max(right - left, 1.0)

    # pull out runs of consecutive table-like rows and rebuild them
    if args is not None:
        segments, run = [], []
        for l in lines:
            if l.tabular:
                run.append(l)
            else:
                if run:
                    segments.append(("tab", run))
                    run = []
                segments.append(("prose", [l]))
        if run:
            segments.append(("tab", run))
        rebuilt = [(k, v, reconstruct_table(v, body, args))
                   if k == "tab" and len(v) >= 2 else (k, v, None)
                   for k, v in segments]
        if any(r for _, _, r in rebuilt):
            out, buf = [], []
            for kind, part, rendered in rebuilt:
                if rendered:
                    if buf:
                        out += build_paragraphs(buf, page_no, body, keep_hyphens, m)
                        buf = []
                    out.append(Block("table", rendered, part[0].top, page_no))
                else:
                    for l in part:
                        l.tabular = False       # false alarm: ordinary prose
                    buf += part
            if buf:
                out += build_paragraphs(buf, page_no, body, keep_hyphens, m)
            return out
        for _, part, _ in rebuilt:
            for l in part:
                l.tabular = False

    blocks, cur, cur_top, cur_head = [], "", lines[0].top, False

    def flush():
        nonlocal cur
        if cur.strip():
            blocks.append(Block("para", cur.strip(), cur_top, page_no, cur_head))
        cur = ""

    for i, ln in enumerate(lines):
        head = is_heading(ln, body, left, right)
        if i == 0:
            cur, cur_top, cur_head = ln.text, ln.top, head
            continue
        prev = lines[i - 1]
        gap = ln.top - prev.bottom
        step = ln.top - prev.top
        if (step > 1.45 * pitch or gap > 0.85 * body
                or abs(ln.size - prev.size) > max(0.8, 0.1 * body)
                or head or cur_head
                or ln.tabular or prev.tabular
                or BULLET_RE.match(ln.text)
                or (ln.x0 > prev.x0 + max(0.018 * span, 3)
                    and prev.x1 > right - 0.05 * span)
                or prev.x1 < right - 0.28 * span
                or (prev.x1 < right - 0.10 * span and TERMINAL_RE.search(prev.text))):
            flush()
            cur, cur_top, cur_head = ln.text, ln.top, head
        else:
            cur = join_lines(cur, ln.text, keep_hyphens)
    flush()
    return blocks


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def convert(path: Path, args, progress=None, log=print):
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
                        args = argparse.Namespace(**vars(args))
                        args.ocr_language = chosen
                    if args.ocr_engine == "tesseract":
                        tick(i - 1, total, f"reading page {i}/{total} (OCR)")
                        try:
                            w, c, conf = ocr_tesseract(page, args)
                            if w:
                                pd.words, pd.chars, pd.ocr = w, c, True
                                pd.ocr_conf = conf
                                pd.raw_chars = sum(len(x["text"]) for x in w)
                                pd.looks_scanned = False
                        except Exception as exc:
                            log(f"   ! OCR failed on page {i}: {exc}")
                    else:
                        pending.append(i)
                pages.append(pd)
                _release(page)
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

    blocks, on_purpose = [], 0
    for pd in pages:
        if pd.ocr_text:
            page_blocks = markdown_to_blocks(pd.ocr_text, pd.number, args)
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
        if not args.keep_headers:
            n, ch = strip_running(pd, running, body)
            st["dropped"] += n
            on_purpose += ch

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
            page_blocks.append(Block("table", rendered, top, pd.number))
        if not pd.two_col:
            page_blocks.sort(key=lambda b: b.top)   # interleave tables by position
        if args.page_marks:
            page_blocks.insert(0, Block("mark", f"[page {pd.number}]", -1e9, pd.number))
        blocks += page_blocks

    if args.join_pages:
        merged = []
        for b in blocks:
            p = merged[-1] if merged else None
            if (p and b.kind == "para" and p.kind == "para" and b.page != p.page
                    and not p.heading and not b.heading
                    and not TERMINAL_RE.search(p.text)
                    and not BULLET_RE.match(b.text)
                    and (LOWER_START_RE.match(b.text) or p.text.endswith(HYPHENS))):
                p.text = join_lines(p.text, b.text, args.keep_hyphens)
                continue
            merged.append(b)
        blocks = merged

    text = "\n\n".join(b.text for b in blocks if b.text.strip())
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    raw = sum(pd.raw_chars for pd in pages)
    kept = len(squeeze(text)) + on_purpose
    st["kept_ratio"] = min(1.0, kept / raw) if raw else 1.0
    return text, st


def bar(fraction, width=24):
    filled = int(round(fraction * width))
    return "#" * filled + "." * (width - filled)


class Progress:
    """One rewritable line: overall file count plus the page being worked on."""

    def __init__(self, total_files, enabled=True):
        self.total = total_files
        self.index = 0
        self.name = ""
        self.enabled = enabled and sys.stdout.isatty()
        self.width = 0

    def start_file(self, index, name):
        self.index, self.name = index, name
        self.draw(0.0, "")

    def page(self, done, total, note=""):
        self.draw(done / total if total else 0.0, note)

    def draw(self, page_fraction, note):
        if not self.enabled:
            return
        overall = (self.index - 1 + page_fraction) / max(self.total, 1)
        line = (f"[{bar(overall)}] {overall:4.0%}  "
                f"file {self.index}/{self.total}  {self.name}"
                + (f"  {note}" if note else ""))
        line = line[:110]
        sys.stdout.write("\r" + line.ljust(self.width))
        sys.stdout.flush()
        self.width = max(self.width, len(line))

    def clear(self):
        if self.enabled and self.width:
            sys.stdout.write("\r" + " " * self.width + "\r")
            sys.stdout.flush()
            self.width = 0


def ask_folders():
    """Ask for the two folders: a dialog if possible, typed paths otherwise."""
    def tidy(p):
        return p.strip().strip('"').strip("'")

    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.update()
        src = filedialog.askdirectory(title="Folder containing the PDFs")
        dst = filedialog.askdirectory(
            title="Folder for the TXT files (Cancel = next to the PDFs)") if src else ""
        root.destroy()
        return tidy(src or ""), tidy(dst or "")
    except Exception:
        print("Tip: you can also write these two folders into the SETTINGS "
              "block at the top of this script.\n")
        src = tidy(input("Folder containing the PDFs: "))
        dst = tidy(input("Folder for the TXT files (Enter = next to the PDFs): "))
        return src, dst


def run_gui(parser):
    """A small window: pick two folders, press Convert."""
    import queue
    import threading
    import tkinter as tk
    from tkinter import ttk, filedialog

    args = parser.parse_args([])          # every setting at its default
    root = tk.Tk()
    root.title("PDF to text")
    root.minsize(680, 520)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(4, weight=1)

    msgs = queue.Queue()
    stop_flag = threading.Event()
    running = threading.Event()

    v_in = tk.StringVar(value=str(args.inputs[0]) if args.inputs else INPUT_FOLDER)
    v_out = tk.StringVar(value=str(args.out) if args.out else OUTPUT_FOLDER)
    v_rec = tk.BooleanVar(value=args.recursive)
    v_ocr = tk.StringVar(value=args.ocr)
    v_engine = tk.StringVar(value=args.ocr_engine)
    v_lang = tk.StringVar(value=args.ocr_language)
    v_key = tk.StringVar(value=args.mistral_key)
    v_cols = tk.StringVar(value=args.columns)
    v_tables = tk.StringVar(value=args.tables)
    v_marks = tk.BooleanVar(value=args.page_marks)
    v_heads = tk.BooleanVar(value=args.keep_headers)
    v_status = tk.StringVar(value="Choose a folder of PDFs, then press Convert.")

    pad = dict(padx=8, pady=4)

    # ---- folders ---------------------------------------------------------
    box = ttk.LabelFrame(root, text="Folders")
    box.grid(row=0, column=0, sticky="ew", **pad)
    box.columnconfigure(1, weight=1)

    def browse(var, title):
        chosen = filedialog.askdirectory(title=title,
                                         initialdir=var.get() or None)
        if chosen:
            var.set(chosen)

    ttk.Label(box, text="PDFs in").grid(row=0, column=0, sticky="w", padx=6, pady=4)
    ttk.Entry(box, textvariable=v_in).grid(row=0, column=1, sticky="ew", padx=6)
    ttk.Button(box, text="Browse...",
               command=lambda: browse(v_in, "Folder containing the PDFs")
               ).grid(row=0, column=2, padx=6)
    ttk.Label(box, text="TXT out").grid(row=1, column=0, sticky="w", padx=6, pady=4)
    ttk.Entry(box, textvariable=v_out).grid(row=1, column=1, sticky="ew", padx=6)
    ttk.Button(box, text="Browse...",
               command=lambda: browse(v_out, "Folder for the TXT files")
               ).grid(row=1, column=2, padx=6)
    ttk.Checkbutton(box, text="include sub-folders", variable=v_rec
                    ).grid(row=2, column=1, sticky="w", padx=6, pady=2)
    ttk.Label(box, text="Leave the output folder empty to write each .txt "
                        "next to its PDF.", foreground="#666"
              ).grid(row=3, column=1, sticky="w", padx=6, pady=(0, 6))

    # ---- scanned PDFs ----------------------------------------------------
    ocr_box = ttk.LabelFrame(root, text="Scanned PDFs (no selectable text)")
    ocr_box.grid(row=1, column=0, sticky="ew", **pad)
    ocr_box.columnconfigure(5, weight=1)
    ttk.Label(ocr_box, text="Recognise text").grid(row=0, column=0, padx=6, pady=6)
    ttk.Combobox(ocr_box, textvariable=v_ocr, width=8, state="readonly",
                 values=["auto", "off", "always"]).grid(row=0, column=1)
    ttk.Label(ocr_box, text="using").grid(row=0, column=2, padx=6)
    ttk.Combobox(ocr_box, textvariable=v_engine, width=10, state="readonly",
                 values=["tesseract", "mistral"]).grid(row=0, column=3)
    ttk.Label(ocr_box, text="language").grid(row=0, column=4, padx=6)
    ttk.Entry(ocr_box, textvariable=v_lang, width=10).grid(row=0, column=5, sticky="w")
    ttk.Label(ocr_box, text="Mistral key").grid(row=1, column=0, padx=6, pady=(0, 6))
    ttk.Entry(ocr_box, textvariable=v_key, show="*").grid(
        row=1, column=1, columnspan=5, sticky="ew", padx=6, pady=(0, 6))

    # ---- layout ----------------------------------------------------------
    lay = ttk.LabelFrame(root, text="Layout")
    lay.grid(row=2, column=0, sticky="ew", **pad)
    ttk.Label(lay, text="Columns").grid(row=0, column=0, padx=6, pady=6)
    ttk.Combobox(lay, textvariable=v_cols, width=6, state="readonly",
                 values=["auto", "1", "2"]).grid(row=0, column=1)
    ttk.Label(lay, text="Tables").grid(row=0, column=2, padx=6)
    ttk.Combobox(lay, textvariable=v_tables, width=8, state="readonly",
                 values=["lines", "text", "none"]).grid(row=0, column=3)
    ttk.Checkbutton(lay, text="[page N] markers", variable=v_marks
                    ).grid(row=0, column=4, padx=10)
    ttk.Checkbutton(lay, text="keep headers/footers", variable=v_heads
                    ).grid(row=0, column=5, padx=10)

    # ---- action ----------------------------------------------------------
    act = ttk.Frame(root)
    act.grid(row=3, column=0, sticky="ew", **pad)
    act.columnconfigure(2, weight=1)
    go = ttk.Button(act, text="Convert")
    go.grid(row=0, column=0)
    halt = ttk.Button(act, text="Stop", state="disabled")
    halt.grid(row=0, column=1, padx=6)
    pbar = ttk.Progressbar(act, mode="determinate", maximum=1000)
    pbar.grid(row=0, column=2, sticky="ew", padx=8)
    ttk.Label(root, textvariable=v_status).grid(row=5, column=0, sticky="w", padx=12)

    logbox = tk.Text(root, height=14, wrap="word")
    logbox.grid(row=4, column=0, sticky="nsew", padx=8)
    scroll = ttk.Scrollbar(root, command=logbox.yview)
    scroll.grid(row=4, column=1, sticky="ns")
    logbox.configure(yscrollcommand=scroll.set, state="disabled")

    def say(text):
        msgs.put(("log", text))

    # ---- worker ----------------------------------------------------------
    def work():
        try:
            for name, var in (("columns", v_cols), ("tables", v_tables),
                              ("ocr", v_ocr), ("ocr_engine", v_engine),
                              ("ocr_language", v_lang), ("mistral_key", v_key)):
                setattr(args, name, var.get())
            args.recursive = v_rec.get()
            args.page_marks = v_marks.get()
            args.keep_headers = v_heads.get()
            args.out = Path(v_out.get()) if v_out.get().strip() else None
            if args.out:
                args.out.mkdir(parents=True, exist_ok=True)

            src = Path(v_in.get().strip())
            if not src.exists():
                say(f"This folder does not exist:\n  {src}")
                return
            targets = collect_targets([src], args.recursive)
            if not targets:
                say(f"No PDF found in {src}"
                    + ("" if args.recursive else
                       "\nTick 'include sub-folders' if they are nested."))
                return
            if args.ocr != "off":
                ok, note = check_ocr(args.ocr_engine, args.mistral_key)
                say(f"OCR ready: {note}" if ok else
                    f"OCR unavailable, scanned pages will stay empty:\n  {note}")
                if ok and args.ocr_engine == "tesseract":
                    resolve_languages(args, say)
                if not ok:
                    args.ocr = "off"
            say(f"{len(targets)} PDF(s) to convert\n")

            def on_file(n, total, name):
                msgs.put(("file", (n, total, name)))
                say(f"[{n}/{total}] {name}")

            def on_page(n, total, d, t, note):
                msgs.put(("page", (n, total, d, t, note)))

            done, failed = run_batch(targets, args, on_file, on_page, say,
                                     stop=stop_flag.is_set)
            say(f"\nFinished: {done} converted"
                + (f", {failed} failed" if failed else "") + ".")
        except Exception as exc:
            say(f"Unexpected error: {type(exc).__name__}: {exc}")
        finally:
            msgs.put(("end", None))

    def start():
        if running.is_set():
            return
        running.set()
        stop_flag.clear()
        go.configure(state="disabled")
        halt.configure(state="normal")
        logbox.configure(state="normal")
        logbox.delete("1.0", "end")
        logbox.configure(state="disabled")
        pbar["value"] = 0
        threading.Thread(target=work, daemon=True).start()

    go.configure(command=start)
    halt.configure(command=lambda: (stop_flag.set(),
                                    v_status.set("Stopping...")))

    # ---- pump ------------------------------------------------------------
    def pump():
        while True:
            try:
                kind, data = msgs.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                logbox.configure(state="normal")
                logbox.insert("end", str(data) + "\n")
                logbox.see("end")
                logbox.configure(state="disabled")
            elif kind == "file":
                n, total, name = data
                v_status.set(f"{n}/{total}  {name}")
                pbar["value"] = int(1000 * (n - 1) / max(total, 1))
            elif kind == "page":
                n, total, d, t, note = data
                frac = (n - 1 + (d / t if t else 0)) / max(total, 1)
                pbar["value"] = int(1000 * frac)
                v_status.set(f"{n}/{total}  {note}" if note else f"{n}/{total}")
            elif kind == "end":
                running.clear()
                go.configure(state="normal")
                halt.configure(state="disabled")
                pbar["value"] = 1000 if not stop_flag.is_set() else pbar["value"]
                v_status.set("Done." if not stop_flag.is_set() else "Stopped.")
        root.after(80, pump)

    root.after(80, pump)
    root.mainloop()


class Stopped(Exception):
    """Raised when the user asks the run to stop."""


def collect_targets(inputs, recursive):
    out = []
    for p in inputs:
        p = Path(p)
        if p.is_dir():
            out += sorted(p.rglob("*.pdf") if recursive else p.glob("*.pdf"))
        elif p.suffix.lower() == ".pdf":
            out.append(p)
    return out


def run_batch(targets, args, on_file=None, on_page=None, log=print, stop=None):
    """Convert every file. Shared by the command line and the window."""
    done = failed = 0
    for n, pdf_path in enumerate(targets, 1):
        if stop is not None and stop():
            log("Stopped.")
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
            text, st = convert(pdf_path, args, progress=page_cb, log=log)
        except Stopped:
            log("Stopped.")
            break
        except Exception as exc:
            log(f"   FAILED: {type(exc).__name__}: {exc}")
            failed += 1
            continue

        dest.write_text(text, encoding="utf-8")
        done += 1
        bits = [f"{st['pages']} pages", f"{st['tables']} table(s)",
                f"{st['dropped']} header/footer line(s) removed"]
        if st["twocol"]:
            bits.append(f"{st['twocol']} two-column page(s)")
        if st["ocr_pages"]:
            b = f"{st['ocr_pages']} page(s) recognised by OCR"
            if st["ocr_conf"]:
                b += f" (confidence {st['ocr_conf']:.0%})"
            bits.append(b)
        else:
            bits.append(f"{st['kept_ratio']:.0%} of characters kept")
        log("   " + ", ".join(bits) + f" -> {dest.name}")
        if st["kept_ratio"] < 0.95 and not st["ocr_pages"]:
            log("   ! fewer characters than the PDF text layer holds; "
                "inspect this one")
        if st["scanned"]:
            log(f"   ! pages {st['scanned']} hold no text and OCR is off or "
                'unavailable: set OCR = "auto" in the SETTINGS block')
        if st["ocr_conf"] is not None and st["ocr_conf"] < 0.75:
            log("   ! low OCR confidence: check this file"
                + ("" if args.ocr_engine == "mistral" else
                   ', and consider OCR_ENGINE = "mistral" for poor scans'))
    return done, failed


def make_parser():
    """Build the option parser. parse_args([]) yields every default."""
    ap = argparse.ArgumentParser(
        description="Convert PDFs into clean text: one line per paragraph, "
                    "blank line between paragraphs.")
    ap.add_argument("inputs", nargs="*", type=Path,
                    help="PDF files and/or folders (optional: see the SETTINGS "
                         "block at the top of the script)")
    ap.add_argument("-o", "--out", type=Path, default=None, help="output folder")
    ap.add_argument("-r", "--recursive", action="store_true", default=RECURSIVE)
    ap.add_argument("--columns", choices=["auto", "1", "2"], default=COLUMNS)
    ap.add_argument("--tables", choices=["lines", "text", "none"], default=TABLES,
                    help="'lines' (default) reads ruled tables and rebuilds unruled "
                         "ones from their alignment; 'text' is aggressive and should "
                         "only be used on pages that are almost entirely tables")
    ap.add_argument("--table-markers", action="store_true", default=TABLE_MARKERS)
    ap.add_argument("--no-bullets", dest="keep_bullets", action="store_false",
                    default=KEEP_BULLETS,
                    help="drop the leading '- ' from list items in OCR output")
    ap.add_argument("--page-marks", action="store_true", default=PAGE_MARKS)
    ap.add_argument("--keep-hyphens", action="store_true", default=KEEP_HYPHENS)
    ap.add_argument("--keep-headers", action="store_true", default=KEEP_HEADERS)
    ap.add_argument("--keep-sideways", action="store_true",
                    default=KEEP_SIDEWAYS,
                    help="keep leftover sideways text (chart labels) instead of dropping it")
    ap.add_argument("--no-join-pages", dest="join_pages", action="store_false",
                    default=JOIN_PAGES)
    ap.add_argument("--width", type=int, default=TABLE_WIDTH,
                    help="max table width in characters")
    ap.add_argument("--x-tol", type=float, default=None)
    ap.add_argument("--y-tol", type=float, default=3.0)
    ap.add_argument("--ocr", choices=["auto", "off", "always"], default=OCR,
                    help="recognise text on pages that have none")
    ap.add_argument("--ocr-engine", choices=["tesseract", "mistral"],
                    default=OCR_ENGINE)
    ap.add_argument("--ocr-language", default=OCR_LANGUAGE,
                    help='"auto", or a Tesseract code such as fra / eng+fra')
    ap.add_argument("--ocr-languages", default=OCR_LANGUAGES,
                    help="candidates that --ocr-language auto chooses between")
    ap.add_argument("--ocr-dpi", type=int, default=OCR_DPI)
    ap.add_argument("--ocr-min-conf", type=float, default=OCR_MIN_CONF)
    ap.add_argument("--ocr-retry-below", type=float, default=OCR_RETRY_BELOW)
    ap.add_argument("--ocr-no-deskew", dest="ocr_deskew", action="store_false",
                    default=OCR_DESKEW)
    ap.add_argument("--ocr-keep-rules", dest="ocr_remove_rules",
                    action="store_false", default=OCR_REMOVE_RULES)
    ap.add_argument("--mistral-key", default=MISTRAL_API_KEY)
    ap.add_argument("--mistral-model", default=MISTRAL_MODEL)
    ap.add_argument("--mistral-batch-pages", type=int, default=MISTRAL_BATCH_PAGES)
    ap.add_argument("-v", "--verbose", action="store_true", default=VERBOSE)
    ap.add_argument("--ocr-candidates", default=["eng"], help=argparse.SUPPRESS)
    ap.add_argument("--ocr-trial-language", default="eng", help=argparse.SUPPRESS)
    ap.add_argument("--gui", action="store_true", help="open the window")
    ap.add_argument("--no-gui", dest="gui_ok", action="store_false", default=True)
    return ap


def main():
    ap = make_parser()
    args = ap.parse_args()

    # no arguments and no folder configured -> open the window if we can
    if args.gui or (not args.inputs and not INPUT_FOLDER.strip() and args.gui_ok):
        try:
            run_gui(ap)
            return
        except Exception as exc:
            if args.gui:
                sys.exit(f"Could not open the window: {exc}")
            print(f"(No window available: {exc})\n")
    launched_bare = not args.inputs

    # where to read from: command line, then SETTINGS, then ask
    if not args.inputs:
        if INPUT_FOLDER.strip():
            args.inputs = [Path(INPUT_FOLDER.strip().strip('"').strip("'"))]
        else:
            src, dst = ask_folders()
            if not src:
                sys.exit("No input folder chosen.")
            args.inputs = [Path(src)]
            if dst:
                args.out = Path(dst)
    if args.out is None and OUTPUT_FOLDER.strip():
        args.out = Path(OUTPUT_FOLDER.strip().strip('"').strip("'"))

    for p in args.inputs:
        if not p.exists():
            msg = (f"This folder or file does not exist:\n  {p}\n"
                   "Check the path in the SETTINGS block at the top of the script.")
            if launched_bare:
                print(msg)
                _pause()
                return
            sys.exit(msg)

    targets = []
    for p in args.inputs:
        if p.is_dir():
            targets += sorted(p.rglob("*.pdf") if args.recursive else p.glob("*.pdf"))
        elif p.suffix.lower() == ".pdf":
            targets.append(p)
        else:
            print(f"skipping {p} (not a PDF)", file=sys.stderr)
    if not targets:
        msg = f"No PDF found in: {', '.join(str(p) for p in args.inputs)}"
        if not args.recursive:
            msg += "\n(Set RECURSIVE = True to look inside sub-folders.)"
        if launched_bare:
            print(msg)
            _pause()
            return
        sys.exit(msg)
    if args.ocr != "off":
        ok, msg = check_ocr(args.ocr_engine, args.mistral_key)
        if ok:
            print(f"OCR ready: {msg}")
            if args.ocr_engine == "tesseract":
                resolve_languages(args, print)
        else:
            print(f"OCR unavailable, scanned pages will be skipped:\n  {msg}\n")
            args.ocr = "off"
    print(f"{len(targets)} PDF(s) to convert"
          + (f", writing to {args.out}" if args.out else "") + "\n")
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)

    prog = Progress(len(targets))

    def on_file(n, total, name):
        prog.start_file(n, name)
        if not prog.enabled:
            print(f"[{n}/{total}] {name}")

    def on_page(n, total, d, t, note):
        prog.page(d, t, note)

    def log(msg):
        prog.clear()
        print(msg)
        if prog.enabled and prog.name:
            prog.draw(1.0, "")

    def log_file(msg):
        prog.clear()
        if prog.enabled:
            print(f"[{prog.index}/{prog.total}] {prog.name}")
        print(msg)

    done, failed = run_batch(targets, args, on_file, on_page, log_file)
    prog.clear()
    print(f"\nFinished: {done} converted"
          + (f", {failed} failed" if failed else "") + ".")
    if launched_bare:
        _pause()


def _pause():
    """Keep the window open when the script was double-clicked."""
    try:
        input("\nPress Enter to close...")
    except Exception:
        pass


if __name__ == "__main__":
    main()
