"""
verbatim.extract.pdfio — opening PDFs and straightening sideways pages.

A page whose text is printed at 90 degrees reads as gibberish unless the page
is rotated first. `straighten()` detects the dominant text angle per page and
rewrites the file with the rotation applied, so everything downstream — table
detection, column detection, OCR — sees an upright page.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import pdfplumber


def text_angle(char) -> int:
    a, b = char["matrix"][0], char["matrix"][1]
    if a == 0 and b == 0:
        return 0
    return int(round(math.degrees(math.atan2(b, a)) / 90.0) * 90) % 360


def release(page):
    """Drop pdfplumber's per-page caches. Large scans exhaust memory without it."""
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
            release(page)
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
            log(f"  page {i + 1}: sideways text ({a}°) -> straightened")
    return out
