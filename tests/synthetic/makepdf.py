"""
A minimal PDF writer, for test fixtures only.

Test PDFs need to place a specific word at a specific point — a heading that
crosses a two-column gutter, a justified line whose word gaps mimic table
cells, a table row printed sideways. A layout library fights that; writing the
content stream directly does not, and it keeps the test suite free of a
dependency that the tool itself does not need.

Only what the fixtures use is implemented: the standard-14 fonts, text runs at
an explicit position and angle, and straight lines for table rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

A4 = (595.0, 842.0)


def _esc(s: str) -> bytes:
    """PDF string literal, WinAnsi-encoded."""
    out = s.encode("cp1252", errors="replace")
    for a, b in ((b"\\", b"\\\\"), (b"(", b"\\("), (b")", b"\\)")):
        out = out.replace(a, b)
    return out


@dataclass
class Text:
    x: float
    y: float                     # from the BOTTOM of the page, as PDF counts
    s: str
    size: float = 10.0
    bold: bool = False
    angle: int = 0               # 0 or 90; 90 prints the run sideways

    def ops(self) -> bytes:
        font = b"/F2" if self.bold else b"/F1"
        if self.angle == 90:
            m = b"0 1 -1 0"
        elif self.angle == 180:
            m = b"-1 0 0 -1"
        elif self.angle == 270:
            m = b"0 -1 1 0"
        else:
            m = b"1 0 0 1"
        return (b"BT " + font + b" " + f"{self.size:g}".encode() + b" Tf "
                + m + b" " + f"{self.x:g} {self.y:g}".encode() + b" Tm ("
                + _esc(self.s) + b") Tj ET\n")


@dataclass
class Rule:
    x0: float
    y0: float
    x1: float
    y1: float
    width: float = 0.75

    def ops(self) -> bytes:
        return (f"{self.width:g} w {self.x0:g} {self.y0:g} m "
                f"{self.x1:g} {self.y1:g} l S\n").encode()


@dataclass
class Page:
    width: float = A4[0]
    height: float = A4[1]
    items: list = field(default_factory=list)

    def text(self, x, y, s, size=10.0, bold=False, angle=0):
        self.items.append(Text(x, y, s, size, bold, angle))
        return self

    def rule(self, x0, y0, x1, y1, width=0.75):
        self.items.append(Rule(x0, y0, x1, y1, width))
        return self

    def lines(self, x, top, texts, size=10.0, leading=None, bold=False):
        """Successive lines going down the page, y measured from the top."""
        leading = leading if leading is not None else size * 1.3
        for i, t in enumerate(texts):
            self.text(x, self.height - top - i * leading, t, size, bold)
        return self

    def stream(self) -> bytes:
        return b"".join(i.ops() for i in self.items)


def write_pdf(path: Path, pages: list) -> Path:
    """Assemble the objects, the page tree and a correct xref table."""
    objs: list[bytes] = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)              # 1-based object number

    font_r = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                 b"/Encoding /WinAnsiEncoding >>")
    font_b = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                 b"/Encoding /WinAnsiEncoding >>")
    pages_no = add(b"")               # reserved: filled in once kids are known

    kids = []
    for pg in pages:
        data = pg.stream()
        content = add(b"<< /Length " + str(len(data)).encode() + b" >>\nstream\n"
                      + data + b"\nendstream")
        page_no = add(
            b"<< /Type /Page /Parent " + str(pages_no).encode() + b" 0 R "
            b"/MediaBox [0 0 " + f"{pg.width:g} {pg.height:g}".encode() + b"] "
            b"/Resources << /Font << /F1 " + str(font_r).encode() + b" 0 R /F2 "
            + str(font_b).encode() + b" 0 R >> >> /Contents "
            + str(content).encode() + b" 0 R >>")
        kids.append(page_no)

    objs[pages_no - 1] = (
        b"<< /Type /Pages /Count " + str(len(kids)).encode() + b" /Kids ["
        + b" ".join(str(k).encode() + b" 0 R" for k in kids) + b"] >>")
    root = add(b"<< /Type /Catalog /Pages " + str(pages_no).encode() + b" 0 R >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root "
            + str(root).encode() + b" 0 R >>\nstartxref\n"
            + str(xref_at).encode() + b"\n%%EOF\n")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path
