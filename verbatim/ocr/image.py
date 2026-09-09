"""
verbatim.ocr.image — render a page and clean it before recognition.

Erasing table ruling lines is the single largest quality gain measured on this
corpus: on a test table Tesseract read 2 of 9 cell values with the rules left
in place, and 9 of 9 with them erased. Page-segmentation mode made no useful
difference to that problem; line removal was the fix.
"""

from __future__ import annotations

import re


def estimate_skew(img, limit=3.0, step=0.25):
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


def remove_rules(img, h_frac=0.10, v_frac=0.04):
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
            angle = estimate_skew(img)
            if abs(angle) >= 0.2:
                img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
        except Exception:
            pass

    # 3. table borders
    if args.ocr_remove_rules:
        try:
            img = remove_rules(img)
        except Exception:
            pass
    return img
