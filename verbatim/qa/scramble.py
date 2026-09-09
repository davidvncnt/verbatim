"""
verbatim.qa.scramble — text whose characters came out interleaved.

Some PDFs report a healthy text layer while the character positions inside it
are wrong, so two runs of text end up woven together letter by letter:

    "vessel monitoring and MobIsNeDrFvaUtLio n"  =  "MINDFUL" + "observation"
    "reporting of vessel NpoOsTiItNioGn"         =  "NOTING"  + "position"

Nothing is added and nothing is lost, so every character-count and word-bag
check passes cleanly. Only the shape of the words gives it away.

The test counts case switches inside a word. Interleaved text switches case at
almost every character; ordinary CamelCase does not. "MobIsNeDrFvaUtLio"
switches 13 times over 17 letters, while "VesselRegister", "McDonald",
"LineString" and "DataType" switch three times at most.

Calibrated on real output: it catches every known scrambled word and none of
the 33 legitimate CamelCase words a fisheries and phytosanitary corpus throws
up (TaqMan, GeoServer, ShareAlike, McPhail, GitHub, VesselPositionMessage).

What it cannot see: two interleaved lowercase runs, e.g.
"Managemeonf tA orft iSctlrea", leave no case signature at all. A file this
check calls clean is not thereby proved clean.
"""

from __future__ import annotations

import re

WORD = re.compile(r"\b(?=\w*[a-z])(?=\w*[A-Z])[A-Za-z]{6,}\b")
NOVOWEL = re.compile(r"\b(?![A-Z]+\b)[bcdfghjklmnpqrstvwxz]{5,}\b", re.I)
TABLE = re.compile(r"( \| |^-+\+-|^\s*\|)")

MIN_SWITCHES = 5        # absolute number of upper/lower changes in one word
MIN_DENSITY = 0.5       # ...and they must fall on at least half the letters
MIN_WORDS = 50          # ignore very short files: too little to judge


def case_switches(token: str) -> int:
    caps = [c.isupper() for c in token]
    return sum(1 for a, b in zip(caps, caps[1:]) if a != b)


def is_interleaved(token: str) -> bool:
    n = case_switches(token)
    return n >= MIN_SWITCHES and n / len(token) >= MIN_DENSITY


def scan(text: str) -> dict:
    """Return {'scrambled': [...], 'unpronounceable': [...], 'words': n}.

    Table rows are excluded: rendered columns put unrelated fragments next to
    each other and generate false positives.
    """
    prose = "\n".join(ln for ln in text.splitlines() if not TABLE.search(ln))
    words = [w for w in prose.split() if any(c.isalpha() for c in w)]
    if len(words) < MIN_WORDS:
        return {"scrambled": [], "unpronounceable": [], "words": len(words),
                "too_short": True}
    hits = [t for t in WORD.findall(prose) if not t.isupper() and is_interleaved(t)]
    novowel = [t for t in NOVOWEL.findall(prose) if len(t) >= 5]
    return {"scrambled": hits, "unpronounceable": novowel,
            "words": len(words), "too_short": False}


def locate(text: str, tokens: list) -> list:
    """Character ranges of the given tokens in the text, first hit each.

    A finding a reviewer cannot jump to is a finding they will not act on.
    """
    out = []
    for tok in dict.fromkeys(tokens):
        at = text.find(tok)
        if at >= 0:
            out.append((tok, at, at + len(tok)))
    return out
