"""
verbatim.qa.locate — put a text that verbatim did not produce onto its pages.

A file converted elsewhere has no span map: nothing records which page each
paragraph came from. To show it beside the PDF, verbatim reads the PDF itself
and anchors the file against that reading.

Anchors are word sequences that occur exactly once in verbatim's reading. They
are looked up by content, not position, so they survive what differs between
two conversions of the same PDF: hard-wrapped versus reflowed lines, headers
kept or removed, and — on two-column pages — a different reading order. A line
takes the page most of its anchors point to; a line with no anchors inherits
the page of the line before it.
"""

from __future__ import annotations

import bisect
from collections import Counter, defaultdict

from .fidelity import tokens_with_spans


def _as_dict(span) -> dict:
    return span if isinstance(span, dict) else span.to_dict()


class Reference:
    """verbatim's own reading of a PDF, addressable by character offset."""

    def __init__(self, text: str, spans: list):
        self.text = text
        self.tokens = tokens_with_spans(text)
        regions: dict = defaultdict(dict)
        self.sources: dict = {}
        for sp in map(_as_dict, spans):
            if sp["char_end"] <= sp["char_start"]:
                continue
            key = (sp["char_start"], sp["char_end"])
            page = sp["page"]
            self.sources[page] = sp.get("source", "extracted")
            box = sp.get("bbox")
            have = regions[key].get(page)
            if box and have:
                box = (min(box[0], have[0]), min(box[1], have[1]),
                       max(box[2], have[2]), max(box[3], have[3]))
            regions[key][page] = box or have
        self._ranges = sorted(regions)
        self._starts = [a for a, _ in self._ranges]
        self._regions = regions

    def region_at(self, offset: int) -> dict:
        """{page: bbox} for the paragraph containing a character offset."""
        i = bisect.bisect_right(self._starts, offset) - 1
        if i < 0:
            return {}
        start, end = self._ranges[i]
        return self._regions[(start, end)] if start <= offset < end else {}

    def token_region(self, j: int) -> dict:
        return self.region_at(self.tokens[j][1]) if 0 <= j < len(self.tokens) else {}


def _unique_grams(words: list, k: int) -> dict:
    grams = [tuple(words[i:i + k]) for i in range(len(words) - k + 1)]
    counts = Counter(grams)
    return {g: i for i, g in enumerate(grams) if counts[g] == 1}


def anchor_tokens(text: str, ref: Reference, k: int = 5) -> dict:
    """{token index in text: token index in the reference} for anchored words.

    Falls back to shorter sequences when long ones rarely match, which is what
    happens against a noisy recognised scan.
    """
    words_t = [t for t, _, _ in tokens_with_spans(text)]
    words_r = [t for t, _, _ in ref.tokens]
    best: dict = {}
    for size in (k, 3):
        if len(words_t) < size or len(words_r) < size:
            continue
        uniq = _unique_grams(words_r, size)
        found: dict = {}
        for i in range(len(words_t) - size + 1):
            j = uniq.get(tuple(words_t[i:i + size]))
            if j is not None:
                for d in range(size):
                    found.setdefault(i + d, j + d)
        if len(found) > len(best):
            best = found
        if len(best) >= 0.3 * len(words_t):
            break
    return best


def line_spans(text: str, ref: Reference, default_page: int = 1) -> list:
    """One span per non-empty line of `text`, with its page and rectangle."""
    tokens = tokens_with_spans(text)
    starts = [a for _, a, _ in tokens]
    anchors = anchor_tokens(text, ref)
    out: list = []
    last_page = default_page
    pos = 0
    for raw in text.split("\n"):
        line_start, line_end = pos, pos + len(raw)
        pos = line_end + 1
        if not raw.strip():
            continue
        lo = bisect.bisect_left(starts, line_start)
        hi = bisect.bisect_left(starts, line_end)
        votes: Counter = Counter()
        boxes: dict = {}
        for i in range(lo, hi):
            j = anchors.get(i)
            if j is None:
                continue
            for page, box in ref.token_region(j).items():
                votes[page] += 1
                if box:
                    boxes.setdefault(page, set()).add(tuple(box))
        if votes:
            page = votes.most_common(1)[0][0]
            page_boxes = boxes.get(page) or set()
            bbox = (min(b[0] for b in page_boxes), min(b[1] for b in page_boxes),
                    max(b[2] for b in page_boxes), max(b[3] for b in page_boxes)) \
                if page_boxes else None
            last_page = page
        else:
            page, bbox = last_page, None
        out.append({"page": page, "char_start": line_start, "char_end": line_end,
                    "bbox": list(bbox) if bbox else None,
                    "source": ref.sources.get(page, "extracted")})
    return out


def page_of(spans: list, offset: int | None) -> int | None:
    if offset is None:
        return None
    for sp in spans:
        if sp["char_start"] <= offset < sp["char_end"]:
            return sp["page"]
    earlier = [sp for sp in spans if sp["char_start"] <= offset]
    return earlier[-1]["page"] if earlier else None


def uncovered_runs(words_a: list, words_b: list, k: int, min_run: int) -> list:
    """Runs of words in `a` that belong to no k-word sequence found in `b`.

    Order-blind, so reading-order differences do not count against a text; a
    run of uncovered words means a passage with no counterpart at all.
    Returns [(first index, last index + 1)].
    """
    if len(words_a) < k or len(words_b) < k:
        return [(0, len(words_a))] if len(words_a) >= min_run and not words_b else []
    grams_b = {tuple(words_b[i:i + k]) for i in range(len(words_b) - k + 1)}
    covered = [False] * len(words_a)
    for i in range(len(words_a) - k + 1):
        if tuple(words_a[i:i + k]) in grams_b:
            for d in range(k):
                covered[i + d] = True
    runs, start = [], None
    for i, c in enumerate(covered + [True]):
        if not c and start is None:
            start = i
        elif c and start is not None:
            if i - start >= min_run:
                runs.append((start, i))
            start = None
    return runs


def coverage(words_a: list, words_b: list, k: int = 3) -> float:
    """Share of `a`'s words that sit in a k-word sequence also found in `b`."""
    if not words_a:
        return 1.0
    runs = uncovered_runs(words_a, words_b, k, 1)
    return 1.0 - sum(b - a for a, b in runs) / len(words_a)
