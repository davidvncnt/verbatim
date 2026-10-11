"""
verbatim.qa.letters — compare a text with its PDF as sequences of letters.

Comparing word by word reports every difference in how a word is *written*:
a PDF whose text layer runs words together ("restrictionsinthemanner"), drops
accents ("resolutions" for "résolutions"), or cannot decode a ligature
("posi(cid:31)ve"); a text whose apostrophes were mangled ("lâ€™Organisation");
a single mistyped letter. Measured on 90 files the team had already checked,
word-level comparison reported 4,972 words "not in the PDF". Nearly all of them
were one of these, and none of those is what the review looks for, which is
text that does not come from the document at all.

So both sides are reduced to their letters and digits: no spaces, no
punctuation, no accents, no case. A stretch of the text is accounted for when
the sequences of `SHINGLE` letters it is made of occur somewhere in the PDF, in
any order. A stretch with none of them over `MIN_RUN` letters or more has no
counterpart in the document. A typo leaves a gap of one letter, a missing space
none at all, while an invented sentence leaves a gap the length of the
sentence. On the same 90 files this left 59 passages in 6 files. They include
a reference repeated 23 times, altered DNA probe sequences, and a model's
note to itself ("No text content to extract, only flowchart").

Text is compared one line, and one table cell, at a time. Two readings of the
same table rarely agree on the order of its cells, and letters run together
across cells would never match.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

SHINGLE = 10      # letters per sequence looked up in the PDF
MIN_RUN = 25      # letters with no counterpart before a passage is reported

# UTF-8 read as Windows-1252: "â€™" for "’", "Ã©" for "é". Both readable
# sides are repaired for comparison only; the file is never changed, and the
# encoding itself is reported by the text checks, as its own kind of problem.
_MOJIBAKE_RE = re.compile(
    "[Â-ô][\u0080-¿‘-›€™Œœ"
    "ŠšŸŽžƒˆ˜]+")
_CID_RE = re.compile(r"\(cid:(\d+)\)")
_CID_WORD_RE = re.compile(r"[^\W_]*(?:\(cid:\d+\)[^\W_]*)+")
_WORD_RE = re.compile(r"[^\W_]+")
# Where a line splits into cells: tabs and pipes as earlier scripts wrote
# tables, or two spaces and more between words.
_CELL_RE = re.compile(r"[^\t|\n]+")
_SPACED_RE = re.compile(r"\S(?:.*?\S)?(?= {2,}|$)")


def _repair(chunk: str) -> str:
    try:
        return chunk.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return chunk


def fold(text: str, start: int = 0) -> tuple:
    """(letters, offsets): the letters and digits of `text`, folded, and the
    offset in `text` each one came from, plus `start`."""
    out: list = []
    pos: list = []
    i = 0
    for m in list(_MOJIBAKE_RE.finditer(text)) + [None]:
        end = m.start() if m else len(text)
        _fold_into(text[i:end], i, out, pos, start)
        if m is None:
            break
        _fold_into(_repair(m.group(0)), m.start(), out, pos, start, same=True)
        i = m.end()
    return "".join(out), pos


def _fold_into(chunk: str, at: int, out: list, pos: list, start: int,
               same: bool = False) -> None:
    for k, ch in enumerate(chunk):
        offset = start + at + (0 if same else k)
        for c in unicodedata.normalize("NFKD", ch):
            if unicodedata.combining(c):
                continue
            if c.isdigit():
                c = str(unicodedata.digit(c, c))      # "١٩٨٨" is 1988
            for cc in c.casefold():
                if cc.isalnum():
                    out.append(cc)
                    pos.append(offset)


def decode_cids(raw: str, text: str) -> str:
    """Replace the glyph codes a PDF could not map to letters.

    "posi(cid:31)ve" is "positive" with the "ti" ligature undecoded. A code is
    replaced only when the words of the text explain it the same way at least
    twice and four times in five: the text proposes, but only a consistent
    explanation across the whole document is accepted, so one invented word
    cannot explain a code into existence.
    """
    if "(cid:" not in raw:
        return raw
    vocabulary = {w.casefold() for w in _WORD_RE.findall(unicodedata.normalize("NFC", text))}
    by_length: dict = defaultdict(list)
    for w in vocabulary:
        by_length[len(w)].append(w)
    votes: dict = defaultdict(Counter)
    for m in _CID_WORD_RE.finditer(raw):
        parts = _CID_RE.split(m.group(0))
        letters = sum(len(p) for p in parts[0::2])
        if letters < 2:
            continue
        pattern = re.compile("".join(
            re.escape(p.casefold()) if i % 2 == 0 else r"([^\W\d_]{1,3})"
            for i, p in enumerate(parts)))
        codes = parts[1::2]
        hits = {w for n in range(letters + len(codes), letters + 3 * len(codes) + 1)
                for w in by_length.get(n, ()) if pattern.fullmatch(w)}
        if len(hits) == 1:
            for code, value in zip(codes, pattern.fullmatch(hits.pop()).groups()):
                votes[code][value] += 1
    mapping = {}
    for code, counter in votes.items():
        value, n = counter.most_common(1)[0]
        if n >= 2 and n >= 0.8 * sum(counter.values()):
            mapping[code] = value
    return _CID_RE.sub(lambda m: mapping.get(m.group(1), " "), raw)


def shingles(text: str, size: int = SHINGLE) -> set:
    letters, _ = fold(text)
    return {letters[i:i + size] for i in range(len(letters) - size + 1)}


def cells(text: str):
    """(offset, chunk) for every line, or table cell, of `text`."""
    for line in _CELL_RE.finditer(text):
        chunk = line.group(0)
        if not re.search(r"\S {2,}\S", chunk):
            yield line.start(), chunk
            continue
        for m in _SPACED_RE.finditer(chunk):
            yield line.start() + m.start(), m.group(0)


# A line whose letters are mostly absent is reported whole, even if no single
# gap reaches MIN_RUN: an invented or dropped sentence made of phrases that
# occur elsewhere in the document ("the Subsidiary Body for Implementation")
# is broken into short gaps, but it is still mostly gaps.
LINE_MIN = 30
LINE_SHARE = 0.5


def _covered(letters: str, known: set, size: int) -> list:
    covered = [False] * len(letters)
    for i in range(len(letters) - size + 1):
        if letters[i:i + size] in known:
            for j in range(i, i + size):
                covered[j] = True
    return covered


def _whole_words(chunk: str, offset: int, start: int, end: int) -> tuple:
    """Widen a range to the words it cuts, so a passage never starts mid-word."""
    a, b = start - offset, end - offset
    while a > 0 and chunk[a - 1].isalnum():
        a -= 1
    while b < len(chunk) and chunk[b].isalnum():
        b += 1
    return offset + a, offset + b


def unmatched(text: str, known: set, *, size: int = SHINGLE,
              min_run: int = MIN_RUN) -> list:
    """[(char_start, char_end, letters)] for each stretch of `text` whose
    letters occur nowhere in `known`: runs of `min_run` letters or more, or a
    whole line or cell of which most letters are unaccounted for."""
    found = []
    for offset, chunk in cells(text):
        letters, pos = fold(chunk, offset)
        if len(letters) < min(min_run, LINE_MIN):
            continue
        covered = _covered(letters, known, size)
        missing = len(letters) - sum(covered)
        if len(letters) >= LINE_MIN and missing > LINE_SHARE * len(letters):
            # From the first letter unaccounted for to the last, so that the
            # sound sentence before an invented one is not highlighted with it.
            first = covered.index(False)
            last = len(covered) - 1 - covered[::-1].index(False)
            a, b = _whole_words(chunk, offset, pos[first], pos[last] + 1)
            found.append((a, b, missing))
            continue
        run = None
        for i, ok in enumerate(covered + [True]):
            if not ok and run is None:
                run = i
            elif ok and run is not None:
                if i - run >= min_run:
                    a, b = _whole_words(chunk, offset, pos[run], pos[i - 1] + 1)
                    found.append((a, b, i - run))
                run = None
    return found


def found_in(chunk: str, known: set, pdf_letters: str, *,
             size: int = SHINGLE) -> bool:
    """Is most of `chunk` in the PDF? A short chunk must be there whole; a
    long one may be split up, as a table cell wrapped over several lines is
    in a PDF's text, so most of its letters need only belong to a sequence
    that is."""
    folded, _ = fold(chunk)
    if len(folded) < 2 * size:
        return folded in pdf_letters
    return sum(_covered(folded, known, size)) >= 0.5 * len(folded)


def ascii_digits(text: str) -> str:
    """Digits of any script as 0-9, one for one, so offsets are kept."""
    return "".join(str(unicodedata.digit(c)) if c.isdigit() and not c.isascii()
                   else c for c in text)
