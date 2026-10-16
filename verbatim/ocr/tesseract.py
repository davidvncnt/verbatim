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

import re
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
    # The tallest word of each line sets the size of all of them. A word's
    # own box is taller with a capital or a descender ("Conven-" against
    # "tion"), and the layout code reads a change of size as a new paragraph.
    line_height: dict = {}
    for i, txt in enumerate(data["text"]):
        if txt.strip():
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            line_height[key] = max(line_height.get(key, 0), data["height"][i])
    words, chars, confs = [], [], []
    for i, txt in enumerate(data["text"]):
        txt = txt.strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        # A word the recogniser is unsure of is kept: a doubtful word can be
        # checked, a dropped one cannot ("l'Union", read at 24%). Only specks
        # read as one stray mark are left out.
        if not txt or (conf < args.ocr_min_conf
                       and sum(ch.isalnum() for ch in txt) < 2):
            continue
        x0 = data["left"][i] * scale
        top = data["top"][i] * scale
        x1 = x0 + data["width"][i] * scale
        bottom = top + data["height"][i] * scale
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        size = line_height.get(key, data["height"][i]) * scale
        words.append({"text": txt, "x0": x0, "x1": x1, "top": top,
                      "bottom": bottom, "upright": True, "conf": conf})
        # one synthetic character per word, so the layout code can judge size
        chars.append({"text": txt[0], "x0": x0, "x1": x1, "top": top,
                      "bottom": bottom, "upright": True, "fontname": "OCR",
                      "size": size * 1.05})
        if conf >= args.ocr_min_conf:
            confs.append(conf)     # confidence as before, so thresholds hold
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


# Tesseract's script detection names the writing system; the language pack
# that reads it. English is added for the headers such pages usually carry.
SCRIPT_LANGUAGES = {"Cyrillic": "rus", "Arabic": "ara", "Greek": "ell",
                    "Han": "chi_sim", "HanS": "chi_sim", "HanT": "chi_tra",
                    "Japanese": "jpn", "Hangul": "kor", "Korean": "kor",
                    "Hebrew": "heb", "Devanagari": "hin", "Thai": "tha",
                    "Armenian": "hye", "Georgian": "kat"}


def page_script(page) -> str | None:
    """The writing system of a page, as Tesseract sees it, or None."""
    import pytesseract

    from ..extract.pdfio import render
    try:
        img = render(page, 200).convert("L")
        osd = pytesseract.image_to_osd(img)
        found = re.search(r"Script: (\w+)", osd)
        return found.group(1) if found else None
    except Exception:
        return None


def page_language(page, args, layer_text: str, remembered: dict, log=print) -> str:
    """The language to read one page in.

    One language per file was enough while files were in one language, but a
    treaty often prints the same text in French, Finnish and Russian, page
    after page. So: the writing system first, then the words of the page's
    own text layer if it has one, and only then a trial reading, whose answer
    is remembered for the rest of the file.
    """
    from .detect import LANG_MARKERS, detect_language, installed_languages
    have = set(installed_languages())
    script = page_script(page)
    code = SCRIPT_LANGUAGES.get(script or "")
    if code and code in have:
        return f"{code}+eng" if "eng" in have else code
    if layer_text:
        guess, _ = detect_language(layer_text, [c for c in LANG_MARKERS if c in have])
        if guess:
            return guess
    if "latin" not in remembered:
        remembered["latin"] = auto_language(page, args, log)
    return remembered["latin"]
