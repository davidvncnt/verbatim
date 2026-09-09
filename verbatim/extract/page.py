"""verbatim.extract.page — one pdfplumber page into a PageData."""

from __future__ import annotations

from .model import PageData
from .tables import read_tables
from .text import alnum_count, clean, squeeze


def read_page(page, pno, args) -> PageData:
    pd = PageData(pno, float(page.width), float(page.height))
    try:
        raw = (page.extract_text() or "").replace("\n", " ")
        pd.raw_text = raw
        pd.raw_chars = len(squeeze(clean(raw)))
        pd.raw_alnum = alnum_count(raw)
    except Exception:
        pd.raw_chars = 0
        pd.raw_alnum = 0

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
    pd.sideways_alnum = sum(alnum_count(w["text"]) for w in sideways)
    if not args.keep_sideways:
        pd.dropped_lines += [w["text"] for w in sideways]
    if args.keep_sideways and sideways:
        txt = clean(" ".join(w["text"] for w in
                             sorted(sideways, key=lambda w: (-w["bottom"], w["x0"]))))
        if txt:
            pd.tables.append((1e9, txt))
            pd.sideways_chars = 0
            pd.sideways_alnum = 0

    pd.words = [w for w in words if w.get("upright", True) and not in_table(w)]
    pd.chars = [c for c in page.chars
                if c.get("text", "").strip() and c.get("upright", True)]

    if len(pd.words) < 3:
        imgs = getattr(page, "images", []) or []
        area = sum(abs((i["x1"] - i["x0"]) * (i["bottom"] - i["top"])) for i in imgs)
        if area > 0.4 * pd.width * pd.height:
            pd.looks_scanned = True
    return pd
