"""
verbatim.ocr.markdown — turn the OCR model's markdown back into plain text.

The model returns markdown; the corpus wants plain text. Every rule here
removes *mark-up* and keeps the words it was wrapped around, because a
formatter that drops a word is indistinguishable, downstream, from a model
that hallucinated one.

Two cases are deliberately left alone:

* `$100 and $200` is money, not maths, so the `$...$` rule only fires when the
  span looks like an expression rather than running across whitespace.
* `~~2017~~2020/08` keeps its markers by default. Removing them would weld the
  struck-out text onto its replacement and produce `20172020/08`, a number that
  appears in no document.
"""

from __future__ import annotations

import re

from ..extract.model import Block
from ..extract.tables import render_table
from ..extract.text import BULLET_RE, clean
from ..settings import STRIP_STRIKETHROUGH

MD_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MD_REFLINK_RE = re.compile(r"\[([^\]]*)\]\[[^\]]*\]")
MD_AUTOLINK_RE = re.compile(r"<((?:https?|mailto:)[^>\s]+)>")
MD_FOOTNOTE_RE = re.compile(r"\[\^([^\]]+)\]")
_HTML_TAGS = ("br|sup|sub|b|i|u|em|strong|span|div|p|font|small|big|code|pre"
              "|table|thead|tbody|tr|td|th|ul|ol|li|a|img|hr|h[1-6]")
MD_HTML_RE = re.compile(rf"</?(?:{_HTML_TAGS})\b[^>]*>", re.I)
MD_CODE_RE = re.compile(r"`+([^`]+)`+")
MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.S)
MD_ITAL_RE = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])"
                        r"|(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])")
MD_STRIKE_RE = re.compile(r"~~(.+?)~~", re.S)
MD_MATHCMD_RE = re.compile(r"\\(?:text|textrm|mathrm|mathbf|textbf|textit)\{([^{}]*)\}")
MD_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.S)
MD_ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~$%&])")
MD_RULE_RE = re.compile(r"^ {0,3}([-*_])\s*(?:\1\s*){2,}$")
MD_SETEXT_RE = re.compile(r"^ {0,3}(={2,}|-{2,})\s*$")
MD_FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
MD_BULLET_RE = re.compile(r"^ {0,3}[-*+\u2022]\s+")
MD_QUOTE_RE = re.compile(r"^ {0,3}(?:>\s?)+")
_PLACEHOLDER = "\uE000"


def _math_or_money(m):
    """Strip $...$ only when it really is maths; "$100 and $200" is money."""
    if m.group(1) is not None:                     # $$ ... $$ is always maths
        return m.group(1).strip()
    inner = m.group(2) or ""
    # maths looks like "$x_1$" or "$4$"; money looks like "$100 and $200",
    # where the span between the two signs runs across whitespace
    if inner and (re.search(r"[\\^_{}=]", inner) or not re.search(r"\s", inner)):
        return inner.strip()
    return m.group(0)


def strip_markdown(s: str, strip_strikethrough: bool = STRIP_STRIKETHROUGH) -> str:
    """Remove markdown mark-up, keeping every word it was wrapped around."""
    if not s:
        return s
    # protect backslash-escaped characters so \* is not read as emphasis
    escaped = []

    def _hide(m):
        escaped.append(m.group(1))
        return f"{_PLACEHOLDER}{len(escaped) - 1}{_PLACEHOLDER}"

    s = MD_ESCAPE_RE.sub(_hide, s)

    s = MD_IMG_RE.sub("", s)
    s = MD_LINK_RE.sub(r"\1", s)
    s = MD_REFLINK_RE.sub(r"\1", s)
    s = MD_AUTOLINK_RE.sub(r"\1", s)
    s = MD_FOOTNOTE_RE.sub(r"[\1]", s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = MD_HTML_RE.sub("", s)
    s = MD_CODE_RE.sub(r"\1", s)
    s = MD_MATH_RE.sub(_math_or_money, s)     # delimiters first, so that the
    s = MD_MATHCMD_RE.sub(r"\1", s)           # \text{...} test still applies
    for _ in range(2):                       # nested **bold *italic* **
        s = MD_BOLD_RE.sub(lambda m: m.group(1) or m.group(2) or "", s)
        s = MD_ITAL_RE.sub(lambda m: m.group(1) or m.group(2) or "", s)
    if strip_strikethrough:
        s = MD_STRIKE_RE.sub(r"\1", s)

    def _show(m):
        return escaped[int(m.group(1))]

    s = re.sub(f"{_PLACEHOLDER}(\\d+){_PLACEHOLDER}", _show, s)
    return s


def markdown_to_blocks(md, page_no, args):
    """Turn the OCR model's markdown into plain paragraph and table blocks."""
    blocks, buf, table = [], [], []
    in_fence = False
    strike = getattr(args, "strip_strikethrough", STRIP_STRIKETHROUGH)

    def flush_text(heading=False):
        if buf:
            txt = clean(strip_markdown(" ".join(buf), strike))
            if txt:
                blocks.append(Block("para", txt, len(blocks), page_no, heading))
            buf.clear()

    def flush_table():
        if not table:
            return
        rows = []
        for row in table:
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]
            if cells and all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                continue                       # the |---|---| separator row
            rows.append([clean(strip_markdown(c, strike)) for c in cells])
        rendered = render_table(rows, args.width, args.table_markers) if rows else ""
        if rendered:
            blocks.append(Block("table", rendered, len(blocks), page_no))
        elif rows:
            blocks.append(Block("para", clean(" ".join(" ".join(r) for r in rows)),
                                len(blocks), page_no))
        table.clear()

    for raw in md.splitlines():
        stripped = raw.strip()

        if MD_FENCE_RE.match(raw):             # ``` … ``` : drop the fence, keep text
            flush_text()
            in_fence = not in_fence
            continue
        if in_fence:
            if stripped:
                buf.append(stripped)
            else:
                flush_text()
            continue

        if stripped.startswith("|") and stripped.count("|") >= 2:
            flush_text()
            table.append(stripped)
            continue
        flush_table()

        if not stripped:
            flush_text()
            continue

        if MD_SETEXT_RE.match(stripped) and buf:
            flush_text(heading=True)           # underlined heading
            continue
        if MD_RULE_RE.match(stripped):         # --- *** ___
            flush_text()
            continue

        stripped = MD_QUOTE_RE.sub("", stripped) or stripped

        if re.match(r"^#{1,6}\s", stripped):       # "# Heading", not "#3 vessel"
            flush_text()
            buf.append(stripped.lstrip("#").strip().rstrip("#").strip())
            flush_text(heading=True)
            continue

        if MD_BULLET_RE.match(stripped):
            flush_text()
            stripped = MD_BULLET_RE.sub("- " if args.keep_bullets else "", stripped)
        elif BULLET_RE.match(stripped):
            flush_text()

        buf.append(stripped)

    flush_table()
    flush_text()
    return blocks
