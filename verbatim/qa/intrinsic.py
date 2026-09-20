"""
verbatim.qa.intrinsic — damage visible in the text alone, located.

These checks need no PDF, so they are the only ones available for a text file
whose source cannot be found, and they run first for every file. Each finding
says where in the text to look: a verdict of "problem found" with nothing to
look at sends a reviewer back to reading the whole document.
"""

from __future__ import annotations

import re
from collections import Counter

from .config import CONFIG
from .fidelity import HIGH, MEDIUM, Finding
from .scramble import locate as locate_tokens
from .scramble import scan as scramble_scan
from .textmetrics import (
    _CTRL_RE,
    _MOJIBAKE_RE,
    char_script,
    compute_text_metrics,
    prose_lines,
)

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_ALPHA_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _locate_repetition(text: str, n: int) -> tuple:
    """Where the loop starts to repeat: the second copy of the most repeated
    prose line, or failing that of the most frequent n-word sequence."""
    prose = prose_lines(text)
    lines = [ln.strip() for ln in prose.splitlines() if len(ln.strip()) > 3]
    if lines:
        line, count = Counter(lines).most_common(1)[0]
        if count >= 3:
            first = text.find(line)
            second = text.find(line, first + len(line))
            if second >= 0:
                return second, second + len(line)
    matches = list(_TOKEN_RE.finditer(text))
    words = [m.group(0).casefold() for m in matches]
    if len(words) < 2 * n:
        return None, None
    grams = Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))
    gram, count = grams.most_common(1)[0]
    if count < 2:
        return None, None
    seen = 0
    for i in range(len(words) - n + 1):
        if tuple(words[i:i + n]) == gram:
            seen += 1
            if seen == 2:
                return matches[i].start(), matches[i + n - 1].end()
    return None, None


def _mixed_script_tokens(text: str) -> list:
    out = []
    for m in _ALPHA_RE.finditer(text):
        scripts = {char_script(c) for c in m.group(0)} - {"INHERITED", "COMMON"}
        if len(scripts) > 1:
            out.append((m.group(0), m.start(), m.end()))
    return out


def _longest_letter_run(text: str) -> tuple:
    """Start and end of the longest run of one-letter words: "t h e  t e x t"."""
    best = (0, None, None)
    run, start = 0, None
    last_end = None
    for m in _ALPHA_RE.finditer(prose_lines(text)):
        if len(m.group(0)) == 1:
            if run == 0:
                start = m.start()
            run += 1
            last_end = m.end()
            if run > best[0]:
                best = (run, start, last_end)
        else:
            run = 0
    if best[1] is None:
        return None, None
    snippet = prose_lines(text)[best[1]:best[2]]
    at = text.find(snippet)
    return (at, at + len(snippet)) if at >= 0 else (None, None)


# A presence/absence matrix — ticks, crosses, dashes, Y/N — is an ordinary
# shape in these documents and must not be mistaken for a degenerate one.
_MARKERS = set("✔✓✗✘xX×—–-•■□▪○●+*·.oO0YyNn│┃|‖§\ufe0f")
_TABULAR_LINE = re.compile(r" \| |^-+\+-|^\s*\||\t.*\t|\S {2,}\S.* {2,}\S")
_CELL_SPLIT = re.compile(r"\s*\|\s*|\t+|\s{2,}")


def degenerate_table(text: str, min_cells: int = 12, share: float = 0.6):
    """A table whose cells are nearly all the same value.

    What a model does when asked to read a table it cannot see: it keeps the
    shape and fills every cell with the same token. Measured over the corpus,
    this fires on 3 documents in 21,605 once marker tables are excluded, and
    catches a table whose cells were all filled with "1".

    Returns (value, share of cells, character offset) or None.
    """
    rows = [ln for ln in text.splitlines() if _TABULAR_LINE.search(ln)]
    if len(rows) < 3:
        return None
    cells = [c.strip() for ln in rows for c in _CELL_SPLIT.split(ln.strip()) if c.strip()]
    if len(cells) < min_cells:
        return None
    short = [c for c in cells if len(c) <= 3 and not set(c) <= _MARKERS]
    if not short:
        return None
    value, n = Counter(short).most_common(1)[0]
    if n < share * len(cells):
        return None
    for line in rows:
        if line.count(value) >= 2:
            at = text.find(line)
            if at >= 0:
                return value, n / len(cells), at
    return value, n / len(cells), None


def intrinsic_findings(text: str, config: dict | None = None,
                       metrics: dict | None = None) -> tuple:
    """(findings, metrics, tripped limit names) for one text."""
    cfg = config or CONFIG
    metrics = metrics or compute_text_metrics(text, config=cfg)
    findings: list = []
    tripped: list = []
    limits = cfg["HARD_LIMITS"]

    def over(key):
        val = metrics.get(key)
        if val is not None and float(val) > limits.get(key, float("inf")):
            tripped.append(key)
            return True
        return False

    loop_top, loop_tail = over("top_ngram_coverage"), over("tail_ngram_coverage")
    if loop_top or loop_tail:
        a, b = _locate_repetition(text, cfg["REPEAT_NGRAM_N"])
        findings.append(Finding(
            kind="repetition_loop", severity=HIGH, key="repetition_loop",
            params={"n": cfg["REPEAT_NGRAM_N"]}, char_start=a, char_end=b))

    if over("script_mix_ratio"):
        hits = _mixed_script_tokens(text)
        findings.append(Finding(
            kind="mixed_scripts", severity=HIGH, key="mixed_scripts",
            params={"n": len(hits),
                    "sample": ", ".join(dict.fromkeys(t for t, _, _ in hits[:6]))},
            char_start=hits[0][1] if hits else None,
            char_end=hits[0][2] if hits else None))

    if over("mojibake_rate"):
        m = _MOJIBAKE_RE.search(text)
        findings.append(Finding(
            kind="garbled_characters", severity=HIGH, key="garbled_characters",
            char_start=m.start() if m else None, char_end=m.end() if m else None))

    if over("junk_char_rate"):
        m = _CTRL_RE.search(text)
        at = m.start() if m else text.find("�")
        findings.append(Finding(
            kind="control_characters", severity=MEDIUM, key="control_characters",
            char_start=at if at is not None and at >= 0 else None,
            char_end=at + 1 if at is not None and at >= 0 else None))

    if over("short_token_run"):
        a, b = _longest_letter_run(text)
        findings.append(Finding(
            kind="letter_spacing", severity=MEDIUM, key="letter_spacing",
            char_start=a, char_end=b))

    table = degenerate_table(text)
    if table:
        value, share, at = table
        findings.append(Finding(
            kind="degenerate_table", severity=MEDIUM, key="degenerate_table",
            params={"value": value, "pct": share},
            char_start=at, char_end=(at + 80) if at is not None else None))

    sc = scramble_scan(text)
    if sc["scrambled"]:
        hits = locate_tokens(text, sc["scrambled"])
        # As calibrated in check_txt.py on the real corpus: one interleaved word
        # is worth a look, two or more mean the text layer is scrambled.
        findings.append(Finding(
            kind="scrambled_text",
            severity=HIGH if len(sc["scrambled"]) >= 2 else MEDIUM,
            key="scrambled_text",
            params={"n": len(sc["scrambled"]),
                    "sample": ", ".join(dict.fromkeys(sc["scrambled"][:6]))},
            char_start=hits[0][1] if hits else None,
            char_end=hits[0][2] if hits else None,
            detail=" ".join(sc["scrambled"][:50])))
    return findings, metrics, tripped
