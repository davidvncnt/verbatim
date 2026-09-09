"""
verbatim.extract.columns — visual rows, two-column detection, reading order.

The gutter is found from *where most rows share a single wide internal gap*,
not from a whitespace corridor: a corridor test fails as soon as a full-width
heading crosses the gutter. Rows carrying two or more wide gaps are table
rows rather than prose, and are excluded from the vote for the same reason.
"""

from __future__ import annotations

import bisect
import statistics

from .model import Line
from .text import clean


def group_rows(words):
    """Group words into visual rows (same baseline)."""
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        h = w["bottom"] - w["top"]
        for r in reversed(rows[-4:]):
            ov = min(r["bottom"], w["bottom"]) - max(r["top"], w["top"])
            if ov > 0.45 * min(h, r["bottom"] - r["top"]):
                r["ws"].append(w)
                r["top"] = min(r["top"], w["top"])
                r["bottom"] = max(r["bottom"], w["bottom"])
                break
        else:
            rows.append({"ws": [w], "top": w["top"], "bottom": w["bottom"]})
    for r in rows:
        r["ws"].sort(key=lambda w: w["x0"])
    return rows


def wide_gaps(ws, minw):
    return [(ws[i]["x1"], ws[i + 1]["x0"]) for i in range(len(ws) - 1)
            if ws[i + 1]["x0"] - ws[i]["x1"] >= minw]


def find_gutter(words, rows=None, force=False):
    """A two-column gutter is one wide gap shared by most rows at the same x.

    Rows holding two or more wide gaps are table rows, not prose, and are
    ignored so that a wide table is never mistaken for two columns.
    """
    if len(words) < 40:
        return None
    rows = rows if rows is not None else group_rows(words)
    rows = [r for r in rows if len(r["ws"]) >= 2]
    if len(rows) < 6:
        return None
    gaps = [b - a for r in rows for a, b in
            zip([w["x1"] for w in r["ws"]], [w["x0"] for w in r["ws"][1:]]) if b > a]
    unit = statistics.median(gaps) if gaps else 3.0
    minw = max(8.0, 2.5 * unit)

    events = []
    for r in rows:
        wg = wide_gaps(r["ws"], minw)
        if len(wg) == 1:                       # exactly one -> column gutter
            events.append((wg[0][0], 1))
            events.append((wg[0][1], -1))
    if not events:
        return None
    events.sort()
    cur = best = 0
    span = (0.0, 0.0)
    for i, (x, d) in enumerate(events):
        cur += d
        if d == 1 and cur > best:
            nxt = events[i + 1][0] if i + 1 < len(events) else x
            best, span = cur, (x, nxt)
    if best < max(3, int(0.45 * len(rows))) and not force:
        return None
    gx = (span[0] + span[1]) / 2
    x_min = min(w["x0"] for w in words)
    x_max = max(w["x1"] for w in words)
    pos = (gx - x_min) / max(x_max - x_min, 1)
    if not 0.3 <= pos <= 0.7:
        return None
    left = sum(1 for w in words if w["x1"] <= gx)
    right = sum(1 for w in words if w["x0"] >= gx)
    if not force and (left < 0.2 * len(words) or right < 0.2 * len(words)):
        return None
    return gx


def rows_to_lines(words, chars, gx, args, rows=None):
    """Turn visual rows into text lines, splitting them at the column gutter."""
    rows = rows if rows is not None else group_rows(words)

    all_gaps = [ws[i + 1]["x0"] - ws[i]["x1"]
                for r in rows for ws in [r["ws"]]
                for i in range(len(ws) - 1)
                if ws[i + 1]["x0"] - ws[i]["x1"] > 0]
    unit = statistics.median(all_gaps) if all_gaps else 3.0

    def make(ws, col):
        ws = sorted(ws, key=lambda w: w["x0"])
        text = clean(" ".join(w["text"] for w in ws))
        if not text:
            return None
        ln = Line(text=text, x0=min(w["x0"] for w in ws), x1=max(w["x1"] for w in ws),
                  top=min(w["top"] for w in ws), bottom=max(w["bottom"] for w in ws),
                  col=col)
        # a row with several wide internal gaps is a table row, not prose:
        # keep it on its own line instead of folding it into a paragraph
        cut = max(4.0 * unit, 18)
        cells, buf = [], [ws[0]]
        for i in range(len(ws) - 1):
            if ws[i + 1]["x0"] - ws[i]["x1"] > cut:
                cells.append((buf[0]["x0"], " ".join(w["text"] for w in buf)))
                buf = []
            buf.append(ws[i + 1])
        cells.append((buf[0]["x0"], " ".join(w["text"] for w in buf)))
        ln.cells = [(x, clean(t)) for x, t in cells]
        ln.tabular = len(ws) >= 3 and len(cells) >= 3   # candidate only
        return ln

    lines = []
    for r in rows:
        ws = r["ws"]
        if gx is None:
            ln = make(ws, 0)
            if ln:
                lines.append(ln)
            continue
        straddles = any(w["x0"] < gx - 2 and w["x1"] > gx + 2 for w in ws)
        left = [w for w in ws if (w["x0"] + w["x1"]) / 2 < gx]
        right = [w for w in ws if (w["x0"] + w["x1"]) / 2 >= gx]
        if straddles or not left or not right:
            ln = make(ws, -1 if straddles else (0 if left else 1))
            if ln:
                lines.append(ln)
        else:
            for part, col in ((left, 0), (right, 1)):
                ln = make(part, col)
                if ln:
                    lines.append(ln)

    # font size and weight, taken from the underlying characters
    lines.sort(key=lambda l: (l.top, l.x0))
    tops = [l.top for l in lines]
    buckets = [[] for _ in lines]
    for ch in chars:
        cy = (ch["top"] + ch["bottom"]) / 2
        cx = (ch["x0"] + ch["x1"]) / 2
        i = bisect.bisect_right(tops, cy) - 1
        for j in range(max(0, i - 2), min(len(lines), i + 3)):
            l = lines[j]
            if l.top - 0.5 <= cy <= l.bottom + 0.5 and l.x0 - 1 <= cx <= l.x1 + 1:
                buckets[j].append(ch)
                break
    for l, bucket in zip(lines, buckets):
        if bucket:
            l.size = statistics.median(float(c.get("size", 10)) for c in bucket)
            l.bold = sum(1 for c in bucket
                         if "bold" in str(c.get("fontname", "")).lower()) > len(bucket) / 2
    return lines


def order_columns(lines, gx):
    """Reading order for a two-column page: bands separated by full-width lines."""
    if gx is None:
        return [(sorted(lines, key=lambda l: (l.top, l.x0)), 0)]
    spanning = sorted((l for l in lines if l.col == -1), key=lambda l: l.top)
    rest = [l for l in lines if l.col != -1]
    groups, prev = [], -1e9
    for s in spanning + [None]:
        end = s.top if s else 1e9
        band = [l for l in rest if prev <= l.cy < end]
        for col in (0, 1):
            part = sorted([l for l in band if l.col == col], key=lambda l: (l.top, l.x0))
            if part:
                groups.append((part, col))
        if s:
            groups.append(([s], -1))
            prev = s.bottom
    return groups
