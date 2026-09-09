"""
verbatim.ocr.tesseract — local, deterministic recognition with word boxes.

Boxes matter: they let recognised pages go through exactly the same paragraph,
column and table logic as pages with a text layer, which is why a clean scan
comes out in the same shape as its born-digital equivalent.

A poor page is retried with heavier cleaning and the two passes are compared by
*confidence mass* (the sum of per-word confidences) rather than mean confidence.
Mean confidence rewards a pass that recognised three words perfectly and missed
the rest; confidence mass does not.
"""

from __future__ import annotations

import statistics

from .detect import LANG_NAMES, detect_language
from .image import prepare_image


def _copy_with(args, **changes):
    """A shallow copy of a Settings or argparse.Namespace with fields changed."""
    if hasattr(args, "replace"):
        return args.replace(**changes)
    import argparse
    copy = argparse.Namespace(**vars(args))
    for k, v in changes.items():
        setattr(copy, k, v)
    return copy


def tess_pass(img, args):
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
    probe = _copy_with(args, ocr_language=args.ocr_trial_language)
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
    words, chars, mean, mass = tess_pass(img, args)

    if mean < args.ocr_retry_below:
        # blurred, speckled or low-resolution scan: denoise, then sharpen
        try:
            harder = (img.filter(ImageFilter.MedianFilter(3))
                         .filter(ImageFilter.UnsharpMask(radius=2, percent=150,
                                                         threshold=3)))
            w2, c2, mean2, mass2 = tess_pass(harder, args)
            if mass2 > mass:            # more text, at comparable confidence
                return w2, c2, mean2
        except Exception:
            pass
    return words, chars, mean
