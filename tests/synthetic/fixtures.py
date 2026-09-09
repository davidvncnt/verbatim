"""
Synthetic PDFs covering the cases the brief records as hard-won.

Each fixture isolates one failure the project has already paid for once:
Tesseract losing text inside table rules, a whitespace-corridor gutter test
breaking on a full-width heading, justified prose mimicking table cells, a
recurring section heading being deleted as a running header. They exist so
those fixes cannot regress silently.

Real documents belong in tests/corpus/. These are a floor, not a substitute.
"""

from __future__ import annotations

from pathlib import Path

from makepdf import Page, write_pdf

BODY = 10.0
LEAD = 13.0


def _header(pg: Page, page_no: int, total: int, title="INTERNATIONAL PLANT PROTECTION CONVENTION"):
    """Running header, running footer and a page number, as the corpus has."""
    pg.text(72, pg.height - 40, title, 8)
    pg.text(72, 30, f"Page {page_no} of {total}", 8)
    pg.text(430, 30, "CPM-8", 8)


def simple(dirpath: Path) -> Path:
    """Prose over three pages, with furniture to strip and a paragraph that
    is split across a page break and must be stitched back together."""
    pages = []
    p1 = Page()
    _header(p1, 1, 3)
    p1.lines(72, 80, [
        "The Conference of the Parties,",
    ], size=BODY, leading=LEAD)
    p1.lines(72, 110, [
        "Recalling decision 5/CP.7 on the guidelines for the preparation of",
        "national communications, and recalling further its decision 17/CP.8,",
    ], size=BODY, leading=LEAD)
    p1.lines(72, 160, [
        "1. Decides to adopt the guidelines annexed to the present decision for",
        "the preparation of the reports referred to in paragraph 3 below, which",
        "shall be applied by the Parties from the date of entry into force of",
    ], size=BODY, leading=LEAD)
    pages.append(p1)

    p2 = Page()
    _header(p2, 2, 3)
    # continues the sentence left open on page 1: lower-case start, no
    # terminal punctuation before it
    p2.lines(72, 80, [
        "the amendment, subject to the availability of resources and to the",
        "provisions of paragraph 12 of the annex.",
    ], size=BODY, leading=LEAD)
    p2.lines(72, 140, [
        "2. Requests the secretariat to prepare a synthesis report on the",
        "information submitted under paragraph 1 above.",
    ], size=BODY, leading=LEAD)
    pages.append(p2)

    p3 = Page()
    _header(p3, 3, 3)
    p3.lines(72, 80, [
        "3. Also requests the Subsidiary Body for Implementation to consider",
        "the synthesis report at its next session.",
    ], size=BODY, leading=LEAD)
    pages.append(p3)
    return write_pdf(dirpath / "simple.pdf", pages)


def two_column(dirpath: Path) -> Path:
    """Two columns under a full-width heading that crosses the gutter.

    A whitespace-corridor test fails here: the heading closes the corridor.
    Detecting the gutter from where most rows share one wide internal gap
    does not.
    """
    pg = Page()
    _header(pg, 1, 1, "REPORT OF THE COMMISSION")
    pg.text(72, pg.height - 80, "ANNEX III: SUMMARY OF THE DELIBERATIONS OF THE WORKING GROUP",
            11, bold=True)
    left = [
        "The Working Group considered the",
        "proposal submitted by the delegation",
        "of Argentina concerning the revision",
        "of the standard on wood packaging",
        "material and agreed that further",
        "technical consultation was needed",
        "before any amendment could be",
        "recommended to the Commission.",
    ]
    right = [
        "Several delegations expressed the",
        "view that the existing standard was",
        "adequate and that reopening it would",
        "impose an unreasonable burden on",
        "national plant protection organi-",
        "zations already stretched by the",
        "reporting obligations arising from",
        "the previous biennium.",
    ]
    for i, t in enumerate(left):
        pg.text(72, pg.height - 120 - i * LEAD, t, BODY)
    for i, t in enumerate(right):
        pg.text(330, pg.height - 120 - i * LEAD, t, BODY)
    return write_pdf(dirpath / "two_column.pdf", [pg])


def ruled_table(dirpath: Path) -> Path:
    """A table drawn with ruling lines, plus prose above and below it."""
    pg = Page()
    _header(pg, 1, 1)
    pg.lines(72, 80, ["The Commission adopted the following indicators:"], size=BODY)

    cols = [72, 240, 360, 470, 523]
    rows_y = [pg.height - 120 - i * 22 for i in range(5)]
    for y in rows_y:
        pg.rule(cols[0], y, cols[-1], y)
    for x in cols:
        pg.rule(x, rows_y[0], x, rows_y[-1])
    data = [
        ["Indicator", "Baseline 2020", "Target 2030", "Status"],
        ["Protected areas", "17%", "30%", "On track"],
        ["Degraded land", "22%", "10%", "At risk"],
        ["Species index", "0.71", "0.90", "On track"],
    ]
    for r, row in enumerate(data):
        for c, cell in enumerate(row):
            pg.text(cols[c] + 4, rows_y[r] - 15, cell, 9)
    pg.lines(72, 260, ["The Commission requested annual reporting against them."],
             size=BODY)
    return write_pdf(dirpath / "ruled_table.pdf", [pg])


def unruled_table(dirpath: Path) -> Path:
    """The same shape with no ruling lines: rebuilt from column alignment."""
    pg = Page()
    _header(pg, 1, 1)
    pg.lines(72, 80, ["Catch limits for the 2024 season are set out below."], size=BODY)
    cols = [72, 240, 360, 470]
    data = [
        ["Division", "Species", "Limit (t)", "Season"],
        ["58.4.1", "Dissostichus", "1 220", "Dec-Mar"],
        ["58.4.2", "Champsocephalus", "480", "Dec-Feb"],
        ["48.3", "Euphausia", "62 000", "All year"],
    ]
    for r, row in enumerate(data):
        y = pg.height - 130 - r * 20
        for c, cell in enumerate(row):
            pg.text(cols[c], y, cell, 9)
    return write_pdf(dirpath / "unruled_table.pdf", [pg])


def justified(dirpath: Path) -> Path:
    """Justified prose whose stretched word spacing mimics table cells.

    Requiring cell positions to line up across consecutive rows is what keeps
    this out of the table path; without it, this page becomes a table.
    """
    pg = Page()
    _header(pg, 1, 1)
    # word gaps deliberately wide and, crucially, at different x on each row
    runs = [
        [(72, "Each"), (150, "Party"), (250, "shall"), (330, "take"), (430, "the")],
        [(72, "measures"), (190, "necessary"), (300, "to"), (350, "ensure"), (450, "that")],
        [(72, "the"), (130, "provisions"), (260, "of"), (300, "this"), (390, "Convention")],
        [(72, "are"), (140, "applied"), (250, "within"), (340, "its"), (400, "territory.")],
    ]
    for r, row in enumerate(runs):
        y = pg.height - 120 - r * LEAD
        for x, w in row:
            pg.text(x, y, w, BODY)
    return write_pdf(dirpath / "justified.pdf", [pg])


def sideways(dirpath: Path) -> Path:
    """A landscape table printed at 90 degrees on a portrait page."""
    pg = Page()
    rows = [
        "Division   Species          Limit    Season",
        "58.4.1     Dissostichus     1 220    Dec-Mar",
        "58.4.2     Champsocephalus  480      Dec-Feb",
        "48.3       Euphausia        62 000   All year",
    ]
    for i, r in enumerate(rows):
        pg.text(120 + i * 18, 90, r, 10, angle=90)
    pg.text(90, 90, "ANNEX II: CATCH LIMITS", 12, bold=True, angle=90)
    return write_pdf(dirpath / "sideways.pdf", [pg])


def hyphenated(dirpath: Path) -> Path:
    """A word broken across a line break, beside a genuine compound hyphen."""
    pg = Page()
    pg.lines(72, 80, [
        "The Committee noted that the mat-",
        "ter had been referred to the Franco-",
        "German working group for further con-",
        "sideration at its next meeting.",
    ], size=BODY, leading=LEAD)
    return write_pdf(dirpath / "hyphenated.pdf", [pg])


def recurring_heading(dirpath: Path) -> Path:
    """A section heading repeated at the top of every page, in a larger font.

    It repeats like a running header and sits in the header band. Only the
    font-size guard keeps it in the output, so this fixture fails loudly if
    that guard is ever removed.
    """
    pages = []
    for n in range(1, 4):
        pg = Page()
        pg.text(72, pg.height - 45, "ARTICLE 12: SETTLEMENT OF DISPUTES", 14, bold=True)
        pg.text(72, 30, f"- {n} -", 8)
        pg.lines(72, 90, [
            f"Paragraph {n}. Any dispute between two or more Parties concerning",
            "the interpretation or application of this Convention shall be settled",
            "by negotiation between the Parties concerned.",
        ], size=BODY, leading=LEAD)
        pages.append(pg)
    return write_pdf(dirpath / "recurring_heading.pdf", pages)


def accents(dirpath: Path) -> Path:
    """French and Spanish text: accents, ligature, guillemets, apostrophes."""
    pg = Page()
    pg.lines(72, 80, [
        "La Conférence des Parties, rappelant la décision 5/CP.7 relative aux",
        "lignes directrices pour l'établissement des communications nationales,",
        "décide d'adopter les modalités figurant en annexe à la présente",
        "décision, « sous réserve des ressources disponibles ».",
    ], size=BODY, leading=LEAD)
    pg.lines(72, 160, [
        "La Conferencia de las Partes, recordando la decisión 17/CP.8, pide a",
        "la secretaría que prepare un informe de síntesis sobre la aplicación.",
    ], size=BODY, leading=LEAD)
    return write_pdf(dirpath / "accents.pdf", [pg])


def article_break(dirpath: Path) -> Path:
    """A sentence left open at the foot of a page, and an article heading at
    the top of the next.

    The page-stitching rule looks for a continuation that starts lower-case and
    follows an unterminated line — which is exactly what an article heading
    does not do, unless the heading happens to be preceded by a hyphen. This
    fixture is here so the agreement profile's article rule has something real
    to act on.
    """
    pages = []
    p1 = Page()
    _header(p1, 1, 2, "CONVENTION ON BIOLOGICAL DIVERSITY")
    p1.lines(72, 90, [
        "Article 4: Jurisdictional Scope",
    ], size=12, bold=True)
    p1.lines(72, 120, [
        "Subject to the rights of other States, and except as otherwise",
        "expressly provided in this Convention, the provisions of this",
        "Convention apply, in relation to each Contracting Party, in the case of",
        "components of biological diversity, in areas within the limits of its",
        "national jurisdiction; and in the case of processes and activities",
        "carried out under its jurisdiction or control, within the area of its",
        "national jurisdiction or beyond the limits of national jurisdiction,",
    ], size=BODY, leading=LEAD)
    pages.append(p1)

    p2 = Page()
    _header(p2, 2, 2, "CONVENTION ON BIOLOGICAL DIVERSITY")
    p2.lines(72, 90, ["article 5: Cooperation"], size=BODY, leading=LEAD)
    p2.lines(72, 120, [
        "Each Contracting Party shall, as far as possible and as appropriate,",
        "cooperate with other Contracting Parties directly or through competent",
        "international organizations.",
    ], size=BODY, leading=LEAD)
    pages.append(p2)
    return write_pdf(dirpath / "article_break.pdf", pages)


BUILDERS = [simple, two_column, ruled_table, unruled_table, justified,
            sideways, hyphenated, recurring_heading, accents, article_break]


def build_all(dirpath: Path) -> list:
    dirpath = Path(dirpath)
    dirpath.mkdir(parents=True, exist_ok=True)
    return [b(dirpath) for b in BUILDERS]


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")
    for p in build_all(target):
        print(p)
