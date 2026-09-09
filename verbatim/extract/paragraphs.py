"""
verbatim.extract.paragraphs — lines into paragraphs, one paragraph per line.

The paragraph break test is a disjunction of geometric signals rather than a
single rule, because no single signal survives the corpus: line pitch alone
misses headings, indentation alone misses bulleted lists, and a short previous
line alone breaks on justified text.
"""

from __future__ import annotations

import statistics

from .model import Block, Line
from .tables import reconstruct_table
from .text import BULLET_RE, HYPHENS, TERMINAL_RE


def join_lines(a: str, b: str, keep_hyphens: bool) -> str:
    if a.endswith(HYPHENS) and len(a) > 1 and a[-2].isalpha() and b[:1].isalpha():
        if not keep_hyphens and b[:1].islower():
            return a[:-1] + b                 # "mat-" + "ter" -> "matter"
        return a[:-1] + "-" + b               # "Franco-" + "German"
    return a + " " + b


def is_heading(ln: Line, body: float, left: float, right: float) -> bool:
    if len(ln.text) > 90 or ln.tabular:
        return False
    short = ln.x1 < right - 0.2 * max(right - left, 1)
    big = ln.size > body + 0.8
    caps = ln.text.isupper() and len(ln.text) > 3
    return bool(short and (big or ln.bold or caps))


def metrics(lines, body):
    xs1 = sorted(l.x1 for l in lines)
    right = xs1[int(0.9 * (len(xs1) - 1))] if xs1 else 0.0
    left = min((l.x0 for l in lines), default=0.0)
    steps = [lines[i + 1].top - lines[i].top for i in range(len(lines) - 1)
             if 0 < lines[i + 1].top - lines[i].top < 4 * body]
    pitch = statistics.median(steps) if steps else 1.2 * body
    return left, right, pitch


def build_paragraphs(lines, page_no, body, keep_hyphens, m=None, args=None):
    if not lines:
        return []
    left, right, pitch = m if m else metrics(lines, body)
    span = max(right - left, 1.0)

    # pull out runs of consecutive table-like rows and rebuild them
    if args is not None:
        segments, run = [], []
        for l in lines:
            if l.tabular:
                run.append(l)
            else:
                if run:
                    segments.append(("tab", run))
                    run = []
                segments.append(("prose", [l]))
        if run:
            segments.append(("tab", run))
        rebuilt = [(k, v, reconstruct_table(v, body, args))
                   if k == "tab" and len(v) >= 2 else (k, v, None)
                   for k, v in segments]
        if any(r for _, _, r in rebuilt):
            out, buf = [], []
            for _kind, part, rendered in rebuilt:
                if rendered:
                    if buf:
                        out += build_paragraphs(buf, page_no, body, keep_hyphens, m)
                        buf = []
                    out.append(Block("table", rendered, part[0].top, page_no,
                                     spans=_spans_for(part, page_no)))
                else:
                    for l in part:
                        l.tabular = False       # false alarm: ordinary prose
                    buf += part
            if buf:
                out += build_paragraphs(buf, page_no, body, keep_hyphens, m)
            return out
        for _, part, _ in rebuilt:
            for l in part:
                l.tabular = False

    blocks, cur, cur_top, cur_head = [], "", lines[0].top, False
    cur_lines: list = []

    def flush():
        nonlocal cur, cur_lines
        if cur.strip():
            blocks.append(Block("para", cur.strip(), cur_top, page_no, cur_head,
                                spans=_spans_for(cur_lines, page_no)))
        cur = ""
        cur_lines = []

    for i, ln in enumerate(lines):
        head = is_heading(ln, body, left, right)
        if i == 0:
            cur, cur_top, cur_head = ln.text, ln.top, head
            cur_lines = [ln]
            continue
        prev = lines[i - 1]
        gap = ln.top - prev.bottom
        step = ln.top - prev.top
        if (step > 1.45 * pitch or gap > 0.85 * body
                or abs(ln.size - prev.size) > max(0.8, 0.1 * body)
                or head or cur_head
                or ln.tabular or prev.tabular
                or BULLET_RE.match(ln.text)
                or (ln.x0 > prev.x0 + max(0.018 * span, 3)
                    and prev.x1 > right - 0.05 * span)
                or prev.x1 < right - 0.28 * span
                or (prev.x1 < right - 0.10 * span and TERMINAL_RE.search(prev.text))):
            flush()
            cur, cur_top, cur_head = ln.text, ln.top, head
            cur_lines = [ln]
        else:
            cur = join_lines(cur, ln.text, keep_hyphens)
            cur_lines.append(ln)
    flush()
    return blocks


def _spans_for(lines, page_no):
    """One Span per line, so a passage can be located on the page image later.

    Character offsets are filled in during document assembly, once the block's
    place in the finished text is known; here only the geometry is available.
    """
    from .model import EXTRACTED, Span
    return [Span(page=page_no, bbox=ln.bbox, source=EXTRACTED) for ln in lines]
