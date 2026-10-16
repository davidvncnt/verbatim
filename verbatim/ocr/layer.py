"""
verbatim.ocr.layer — when a scan's own text layer cannot be trusted.

Many older PDFs are scans that someone ran through a recogniser long ago,
leaving its reading as an invisible text layer over the page images. verbatim
reads a text layer as the document's own text, so a poor layer was copied
faithfully: "infligCs aux prairies Ctablies", "contr6lCs", "L la Convention"
for "à la Convention", Russian read as Latin letters ("ROHBEHIAHR"), words cut
one letter late ("andp revented"). And because the checks compared the copy
with the same layer, they found nothing wrong.

Tesseract settles it. On a page that is a full-page picture with a text layer
over it, it reads the picture, and the words it reads with very high
confidence are taken as the yardstick: a layer that lacks many of them is
worse than the new reading. Measured on 45 scanned PDFs of the corpus, every
layer that lacked 4.7% or more of those words was garbled, every layer that
lacked 2.6% or less was sound (the words it lacked were Tesseract's own
errors), and the threshold sits between the two.

The decision is made for the whole document from its first pages, so a sound
layer costs a few pages of recognition and a garbled one is replaced
throughout.
"""

from __future__ import annotations

import re
import unicodedata

FULL_PAGE = 0.85        # share of the page a picture must cover
CONFIDENT = 90          # Tesseract confidence for a word to count as evidence
POOR = 0.04             # share of those words a layer may lack
SOUND = 0.02            # below this, stop looking: the layer is fine
PROBE_PAGES = 3
MORE_PAGES = 6          # when the first pages are inconclusive
ENOUGH_WORDS = 150
MIN_CONF = 60           # a reading worse than this never replaces a layer

# Accents some PDFs write as a separate character after the letter
# ("Europe´enne"): the same word, which must not count against the layer.
_SPACING_MARKS = {"´": "́", "`": "̀", "¨": "̈",
                  "ˆ": "̂", "˜": "̃", "¸": "̧"}
_WORD_RE = re.compile(r"[^\W\d_]{3,}")


def full_page_picture(page) -> bool:
    area = float(page.width * page.height) or 1.0
    return any(abs((im["x1"] - im["x0"]) * (im["bottom"] - im["top"])) >= FULL_PAGE * area
               for im in (getattr(page, "images", None) or []))


def _normal(text: str) -> str:
    for mark, combining in _SPACING_MARKS.items():
        text = text.replace(mark, combining)
    return unicodedata.normalize("NFC", text).casefold()


def layer_words(words: list) -> set:
    return set(_WORD_RE.findall(_normal(" ".join(w["text"] for w in words))))


def confident_words(words: list) -> list:
    return [_normal(w["text"]) for w in words
            if w.get("conf", 0) >= CONFIDENT and _WORD_RE.fullmatch(w["text"])]


class LayerJudge:
    """Collects the evidence page by page and says when it is enough."""

    def __init__(self):
        self.pages = 0
        self.confident = 0
        self.lacking = 0
        self.verdict: str | None = None       # "sound", "poor", or undecided

    def add(self, layer: set, reading: list) -> None:
        found = confident_words(reading)
        self.pages += 1
        self.confident += len(found)
        self.lacking += sum(1 for w in found if w not in layer)
        self.decide()

    @property
    def share(self) -> float:
        return self.lacking / self.confident if self.confident else 0.0

    def decide(self, final: bool = False) -> None:
        if self.verdict is not None:
            return
        enough = self.confident >= ENOUGH_WORDS or self.pages >= PROBE_PAGES
        if final and self.confident >= 30:
            enough = True
        if not enough:
            return
        if self.share >= POOR:
            self.verdict = "poor"
        elif self.share < SOUND or self.pages >= MORE_PAGES or final:
            self.verdict = "sound"
