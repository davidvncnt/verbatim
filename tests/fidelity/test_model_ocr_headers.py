"""
Running headers on pages produced by a model.

The original script skipped these pages before the header filter ever ran, so
every running header, footer and page number survived into the middle of the
document. It is visible in the shipped corpus: `24025_rulesprocedureCPM_2013.txt`
carries "Page 43 of 43", "CPM-8" and "International Plant Protection
Convention" in the body, between two rules of procedure.

The markdown below is shaped like that file. The API is not called: the point
is the assembly path, not the network.
"""

from __future__ import annotations

import pytest

from verbatim.extract.headers import find_running_in_blocks, strip_running_blocks
from verbatim.extract.model import Block
from verbatim.pipeline import convert
from verbatim.settings import Settings

# Header, body, footer — as the model returns them, page after page.
PAGES = {
    1: "Report - Appendix 6\n\nCPM-8\n\n"
       "APPENDIX 6 - Proposed amendment to the Rules of Procedure of the "
       "Commission on Phytosanitary Measures\n\n"
       "Rule I: Membership\n\n"
       "Membership of the Commission consists of all contracting parties to "
       "the International Plant Protection Convention.\n\n"
       "Page 41 of 43",
    2: "International Plant Protection Convention\n\nCPM-8\n\n"
       "Rule II: Officers\n\n"
       "The Commission shall elect a Chairperson, a Vice-Chairperson and other "
       "persons from among the delegates to form a Commission Bureau.\n\n"
       "Page 42 of 43",
    3: "International Plant Protection Convention\n\nCPM-8\n\n"
       "Rule IV: Sessions\n\n"
       "The Commission shall hold one regular session each year. Special "
       "sessions shall be held as considered necessary by the Commission.\n\n"
       "Page 43 of 43",
}

FURNITURE = ["CPM-8", "Page 41 of 43", "Page 42 of 43", "Page 43 of 43",
             "International Plant Protection Convention"]
BODY = ["Rule I: Membership", "Rule II: Officers", "Rule IV: Sessions",
        "Membership of the Commission consists", "shall elect a Chairperson",
        "one regular session each year"]


@pytest.fixture
def model_converted(synthetic_dir, monkeypatch):
    """Convert a three-page PDF as though a model had recognised every page."""
    import verbatim.pipeline as pipeline

    def fake_ocr(pdf_path, page_numbers, args, log=print):
        return ({n: PAGES[n] for n in page_numbers if n in PAGES},
                {n: 92.0 for n in page_numbers})

    monkeypatch.setattr(pipeline, "mistral_ocr", fake_ocr)
    args = Settings(ocr="always", ocr_engine="mistral", mistral_key="not-used")
    return convert(synthetic_dir / "simple.pdf", args, log=lambda *a, **k: None)


def test_running_furniture_is_removed_from_model_pages(model_converted):
    """The regression this fix exists for.

    Furniture is checked as a whole line, not as a substring, because the same
    words legitimately occur inside sentences: page 1's body ends "...all
    contracting parties to the International Plant Protection Convention."
    Removing the standalone header while leaving that sentence intact is the
    behaviour wanted, and a substring test would call it a failure.
    """
    lines = [ln.strip() for ln in model_converted.text.splitlines()]
    for junk in FURNITURE:
        assert junk not in lines, f"{junk!r} survived as a line of the body"


def test_the_same_words_inside_a_sentence_are_left_alone(model_converted):
    assert ("contracting parties to the International Plant Protection "
            "Convention." in model_converted.text)


def test_the_body_is_untouched(model_converted):
    text = model_converted.text
    for wanted in BODY:
        assert wanted in text, f"lost body text {wanted!r}"


def test_the_removal_is_reported(model_converted):
    """A silent deletion is indistinguishable from a bug."""
    assert model_converted.stats["dropped"] >= 6      # header + footer, 3 pages
    assert "CPM-8" in model_converted.dropped_text


def test_keep_headers_still_keeps_them(synthetic_dir, monkeypatch):
    import verbatim.pipeline as pipeline
    monkeypatch.setattr(pipeline, "mistral_ocr",
                        lambda p, ns, a, log=print: (
                            {n: PAGES[n] for n in ns if n in PAGES},
                            {n: 92.0 for n in ns}))
    args = Settings(ocr="always", ocr_engine="mistral", mistral_key="x",
                    keep_headers=True)
    res = convert(synthetic_dir / "simple.pdf", args, log=lambda *a, **k: None)
    assert "CPM-8" in res.text


def test_model_pages_are_labelled_as_recognised(model_converted):
    """A reader must never be able to mistake model output for extracted text."""
    assert all(p.source == "recognised_model" for p in model_converted.pages)
    assert all(s.source == "recognised_model"
               for b in model_converted.blocks for s in b.spans)


# --- the detector on its own ----------------------------------------------

def blocks_for(page, texts):
    return [Block("para", t, i, page) for i, t in enumerate(texts)]


def test_repeated_body_text_is_not_mistaken_for_furniture():
    """IEA decisions repeat boilerplate heavily. Only the page edges are
    candidates, so a recurring middle paragraph is safe."""
    boiler = "Recalling decision 5/CP.7 and recalling further decision 17/CP.8,"
    pages = {n: blocks_for(n, ["HEADER", f"Article {n}", boiler,
                               "Some other text here", f"Page {n} of 3"])
             for n in (1, 2, 3)}
    running = find_running_in_blocks(pages)
    assert "header" in running
    assert all(boiler.lower() not in sig for sig in running)
    kept, dropped = strip_running_blocks(pages[2], running)
    assert boiler in [b.text for b in kept]
    assert "HEADER" in dropped and "Page 2 of 3" in dropped


def test_a_long_recurring_paragraph_is_content_not_furniture():
    long_text = ("The Conference of the Parties, recalling its previous "
                 "decisions on this matter and having considered the report "
                 "of the subsidiary body, decides as follows:")
    pages = {n: blocks_for(n, [long_text, f"Body {n}", f"- {n} -"])
             for n in (1, 2, 3)}
    running = find_running_in_blocks(pages)
    kept, dropped = strip_running_blocks(pages[1], running)
    assert long_text in [b.text for b in kept]
    assert "- 1 -" in dropped


def test_a_single_page_document_drops_nothing_by_repetition():
    """With one page there is no repetition to detect, and guessing would risk
    deleting the title."""
    pages = {1: blocks_for(1, ["SOME ORGANISATION", "Body text", "Page 1 of 1"])}
    assert find_running_in_blocks(pages) == set()
