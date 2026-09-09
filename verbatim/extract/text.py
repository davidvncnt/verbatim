"""
verbatim.extract.text — text hygiene and the patterns the layout code shares.

Everything here is word-preserving. `clean()` normalises encoding artefacts
(ligatures, soft hyphens, non-breaking spaces) but never changes, adds or
removes a word: that guarantee is what the fidelity checks in verbatim.qa
rely on when they assert that every output word came from the source.
"""

from __future__ import annotations

import re
import unicodedata

LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
    "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st", "ĳ": "ij",
}
HYPHENS = ("-", "‐", "‑")

_ROMAN = r"(?=[ivxlcdm])m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"
_NUM = rf"(?:\d{{1,4}}|{_ROMAN})"
PAGE_NUM_RE = re.compile(
    rf"""^[\s\[\(\-–—]*
         (?:(?:page|p|pp|pag|pág|seite|str)\.?\s*)?
         {_NUM}
         (?:\s*(?:/|\||of|de|sur|von|out\s+of)\s*{_NUM})?
         [\s\]\)\-–—\.]*$""",
    re.I | re.X,
)
BULLET_RE = re.compile(
    r"^\s*(?:[•·▪◦⁃∙*]\s+"
    r"|[–—\-]\s+"
    r"|\(?\d{1,3}[.)]\s+"
    r"|\(?[a-zA-Z][.)]\s+"
    r"|\(?[ivxlcdm]{1,5}[.)]\s+)"
)
TERMINAL_RE = re.compile(r"[.!?:;…][\"'”’»\)\]]?\s*$")
LOWER_START_RE = re.compile(r"^[a-zà-ÿœ\(“\"']")


def clean(s: str) -> str:
    """Normalise unicode. Never changes the words themselves."""
    s = unicodedata.normalize("NFC", s)
    for bad, good in LIGATURES.items():
        s = s.replace(bad, good)
    s = s.replace("­", "")                            # soft hyphen
    s = s.replace(" ", " ").replace(" ", " ")    # non-breaking spaces
    s = "".join(c for c in s if c == "\t" or unicodedata.category(c) != "Cc")
    return re.sub(r"[ \t]+", " ", s).strip()


def squeeze(s: str) -> str:
    return re.sub(r"\s+", "", s)


def signature(s: str) -> str:
    """Fingerprint of a line, digits blurred, used to spot running heads."""
    t = re.sub(r"\d+", "#", s.lower())
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"^\W+|\W+$", "", t, flags=re.UNICODE)


def alnum_count(s: str) -> int:
    """Letters and digits only.

    Retention measured over every non-whitespace character is distorted by
    anything the formatter legitimately adds: rendering a table inserts "|"
    and "-+-" that were never in the source, which pushed the old ratio to
    1.26 on a single-table page. Counting only letters and digits measures
    what actually has to be preserved.
    """
    return sum(1 for c in s if c.isalnum())
