"""
verbatim.extract.headers — running headers, running footers and page numbers.

The font-size guard (`ln.size > body + 0.5`) is what stops a recurring section
heading at the top of every page from being deleted as a running header. The
stable-height test does the same job from the other direction: a signature that
appears at wildly different heights is content, not furniture.
"""

from __future__ import annotations

from collections import Counter

from .text import PAGE_NUM_RE, alnum_count, signature, squeeze


def find_running(pages, body=10.0, band=0.10, ratio=0.45):
    if len(pages) < 2:
        return set()
    counts, spots = Counter(), {}
    for pd in pages:
        seen = set()
        for ln in pd.lines:
            if ln.size > body + 0.5:
                continue                 # bigger than body text: a real heading
            if ln.bottom < band * pd.height or ln.top > (1 - band) * pd.height:
                sig = signature(ln.text)
                if sig and len(sig) < 200 and sig not in seen:
                    seen.add(sig)
                    spots.setdefault(sig, []).append(ln.top)
        counts.update(seen)
    threshold = max(2, int(round(ratio * len(pages))))
    out = set()
    for sig, n in counts.items():
        if n < threshold:
            continue
        ys = spots[sig]
        if len(ys) > 1 and (max(ys) - min(ys)) > 12:
            continue                     # not at a stable height: real content
        out.add(sig)
    return out


def strip_running(pd, running, body=10.0, band=0.10):
    """Returns (lines dropped, characters dropped, alphanumerics dropped).

    The two counts are both reported because retention is measured two ways:
    over every non-whitespace character, and over letters and digits alone.
    Whatever is removed on purpose has to be added back to both, or removing a
    page number reads as losing text.
    """
    drop, chars, alnum = set(), 0, 0
    for ln in pd.lines:
        in_band = ln.bottom < band * pd.height or ln.top > (1 - band) * pd.height
        if (ln.size <= body + 0.5 and signature(ln.text) in running) or (
                in_band and len(ln.text) <= 24 and PAGE_NUM_RE.match(ln.text)):
            drop.add(id(ln))
            chars += len(squeeze(ln.text))
            alnum += alnum_count(ln.text)
            pd.dropped_lines.append(ln.text)
    if drop:
        pd.lines = [l for l in pd.lines if id(l) not in drop]
        pd.groups = [([l for l in g if id(l) not in drop], c) for g, c in pd.groups]
        pd.groups = [(g, c) for g, c in pd.groups if g]
    return len(drop), chars, alnum


# ---------------------------------------------------------------------------
# running furniture on pages that have no geometry
# ---------------------------------------------------------------------------
#
# A page recognised by a model comes back as markdown: no font sizes, no line
# positions, nothing the geometric detector above can use. The original script
# had no answer for this and simply skipped those pages, so every running
# header, footer and page number survived into the middle of the document. It
# is visible in the shipped corpus — "Page 43 of 43", "CPM-8" and
# "International Plant Protection Convention" sit mid-text in
# 24025_rulesprocedureCPM_2013.txt.
#
# Without geometry, two constraints stand in for the font-size guard:
#
#   position — only blocks at the very top or bottom of a page are candidates,
#             so repeated body text is never touched. This matters here more
#             than in most corpora: IEA decisions repeat boilerplate heavily,
#             and a detector that looked at whole pages would delete it.
#   length  — furniture is short. A repeated long paragraph is content.

def find_running_in_blocks(pages_blocks, ratio=0.45, max_len=100, edge=2):
    """Signatures of blocks that recur at the edge of most pages.

    `pages_blocks` maps page number to that page's blocks, in order.
    """
    if len(pages_blocks) < 2:
        return set()
    counts = Counter()
    for blocks in pages_blocks.values():
        edges = blocks[:edge] + blocks[-edge:] if len(blocks) > edge else list(blocks)
        seen = set()
        for b in edges:
            if b.kind != "para" or len(b.text) > max_len:
                continue
            sig = signature(b.text)
            if sig and sig not in seen:
                seen.add(sig)
        counts.update(seen)
    threshold = max(2, int(round(ratio * len(pages_blocks))))
    return {sig for sig, n in counts.items() if n >= threshold}


def strip_running_blocks(blocks, running, max_len=100, edge=2):
    """Drop recurring furniture and page numbers from one page's blocks.

    Returns (kept blocks, dropped texts).
    """
    if not blocks:
        return blocks, []
    n = len(blocks)
    edge_ix = set(range(min(edge, n))) | set(range(max(0, n - edge), n))
    kept, dropped = [], []
    for i, b in enumerate(blocks):
        if i in edge_ix and b.kind == "para" and len(b.text) <= max_len:
            if signature(b.text) in running or (
                    len(b.text) <= 24 and PAGE_NUM_RE.match(b.text)):
                dropped.append(b.text)
                continue
        kept.append(b)
    return kept, dropped
