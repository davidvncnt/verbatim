"""
verbatim.extract.tables — tables found from ruling lines, and tables rebuilt
from column alignment when there are no ruling lines.

`reconstruct_table` returning None is load-bearing: justified prose has wide
inter-word gaps that mimic table cells, and the only thing separating the two
cases is whether cell positions line up across consecutive rows.
"""

from __future__ import annotations

import statistics
import textwrap

from .text import clean


def render_table(rows, max_width=100, markers=False) -> str:
    grid = [[clean(str(c)) if c is not None else "" for c in row] for row in rows]
    if not grid:
        return ""
    ncols = max(len(r) for r in grid)
    grid = [r + [""] * (ncols - len(r)) for r in grid]
    keep = [j for j in range(ncols) if any(r[j] for r in grid)]
    grid = [[r[j] for j in keep] for r in grid]
    grid = [r for r in grid if any(r)]
    if not grid or len(grid[0]) < 2:
        return ""
    ncols = len(grid[0])

    widths = [max(len(r[j]) for r in grid) for j in range(ncols)]
    avail = max(max_width - 3 * (ncols - 1), 8 * ncols)
    guard = 0
    while sum(widths) > avail and max(widths) > 8 and guard < 20000:
        widths[widths.index(max(widths))] -= 1
        guard += 1

    def fmt(cells):
        wrapped = [textwrap.wrap(c, w) or [""] for c, w in zip(cells, widths)]
        h = max(len(x) for x in wrapped)
        out = []
        for k in range(h):
            out.append(" | ".join(
                (wrapped[j][k] if k < len(wrapped[j]) else "").ljust(widths[j])
                for j in range(ncols)).rstrip())
        return out

    body = fmt(grid[0])
    if len(grid) > 1:
        body.append("-+-".join("-" * w for w in widths))
        for row in grid[1:]:
            body += fmt(row)
    txt = "\n".join(body)
    return f"[TABLE]\n{txt}\n[/TABLE]" if markers else txt


def read_tables(page, args):
    """Return (list of (top, rendered), list of bboxes)."""
    if args.tables == "none":
        return [], []
    settings = ({"vertical_strategy": "text", "horizontal_strategy": "text"}
                if args.tables == "text" else {})
    try:
        found = page.find_tables(settings) if settings else page.find_tables()
    except Exception:
        return [], []
    out, boxes = [], []
    for t in found:
        try:
            rows = t.extract()
        except Exception:
            continue
        if not rows or len(rows) < 2 or len(rows[0]) < 2:
            continue
        cells = sum(len(r) for r in rows) or 1
        filled = sum(1 for r in rows for c in r if c and str(c).strip())
        if filled / cells < 0.3 or filled < 4:
            continue
        rendered = render_table(rows, args.width, args.table_markers)
        if rendered:
            out.append((t.bbox[1], rendered))
            boxes.append(t.bbox)
    return out, boxes


def reconstruct_table(lines, body, args):
    """Align a run of table-like rows into columns using their x positions.

    Returns None when the rows do not really line up, which is how justified
    prose with wide word spacing is told apart from a genuine table.
    """
    tol = max(6.0, 0.6 * body)
    xs = sorted(x for l in lines for x, _ in l.cells)
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= tol:
            groups[-1].append(x)
        else:
            groups.append([x])
    centres = [statistics.mean(g) for g in groups]
    widest = max(len(l.cells) for l in lines)
    if len(centres) < 2 or len(centres) > widest + 1:
        return None                     # cells do not line up: not a table
    rows = []
    for l in lines:
        row = [""] * len(centres)
        for x, t in l.cells:
            j = min(range(len(centres)), key=lambda k: abs(centres[k] - x))
            row[j] = (row[j] + " " + t).strip()
        if sum(1 for c in row if c) < 2:
            return None
        rows.append(row)
    return render_table(rows, args.width, args.table_markers) or None
