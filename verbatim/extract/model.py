"""
verbatim.extract.model — the objects that carry a page from geometry to text.

`Span` is verbatim's addition to the original script's data model. A Block
knows which page it sits on, but "page 4" is not enough to put a passage in
front of a reviewer: the reviewer needs the rectangle on that page and the
character range in the finished .txt. A Block therefore carries a list of
spans, plural, because a paragraph stitched across a page break belongs to
two pages at once.

`source` records how the words were obtained, so the tool can always answer
"where did this sentence come from?" — extracted from a text layer, or
recognised by a character recogniser, or produced by a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# How the words in a span were obtained. Only EXTRACTED is deterministic;
# the other two are reported to the reviewer as recognised, not extracted.
EXTRACTED = "extracted"
RECOGNISED_TESSERACT = "recognised_tesseract"
RECOGNISED_MODEL = "recognised_model"


@dataclass
class Span:
    """A run of output characters and the place on the page they came from."""

    page: int
    char_start: int = 0            # offset into the finished document text
    char_end: int = 0
    bbox: tuple | None = None      # (x0, top, x1, bottom) in PDF points
    source: str = EXTRACTED

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "bbox": list(self.bbox) if self.bbox else None,
            "source": self.source,
        }


@dataclass
class Line:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float = 10.0
    bold: bool = False
    tabular: bool = False      # looks like a row of table cells
    col: int = 0               # column index on the page
    cells: list = field(default_factory=list)   # [(x0, text)] split at wide gaps

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def bbox(self) -> tuple:
        return (self.x0, self.top, self.x1, self.bottom)


@dataclass
class Block:
    kind: str                  # "para" | "table" | "mark"
    text: str
    top: float
    page: int
    heading: bool = False
    spans: list = field(default_factory=list)   # [Span], filled during assembly

    def bbox_on(self, page: int) -> tuple | None:
        """Union of this block's rectangles on one page, if any."""
        boxes = [s.bbox for s in self.spans if s.page == page and s.bbox]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))


@dataclass
class PageData:
    number: int
    width: float
    height: float
    words: list = field(default_factory=list)
    chars: list = field(default_factory=list)
    tables: list = field(default_factory=list)      # (top, rendered text)
    lines: list = field(default_factory=list)       # flat, reading order
    groups: list = field(default_factory=list)      # [(lines, col_index)]
    raw_chars: int = 0
    raw_alnum: int = 0
    sideways_chars: int = 0
    sideways_alnum: int = 0
    looks_scanned: bool = False
    two_col: bool = False
    ocr: bool = False
    ocr_conf: float = 0.0
    ocr_text: str = ""
    raw_text: str = ""                              # text layer, for fidelity
    dropped_lines: list = field(default_factory=list)  # removed on purpose
