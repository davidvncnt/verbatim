"""
verbatim.ocr.detect — which pages need recognising, in which language.

Language is decided by markers that belong to exactly one candidate language,
so shared words ("de", "la", "un") abstain rather than voting for whichever
language happens to be listed first.
"""

from __future__ import annotations

import re
from collections import Counter

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
    toks = re.findall(r"[a-zAà-öø-ÿ']+", text.lower())
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
            return False, "no Mistral API key was given."
        return True, "Mistral OCR API"
    return False, f"unknown OCR engine: {engine}"
