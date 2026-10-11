"""
Comparing a text with its PDF as letters.

Every case here was a false alarm on files the team had already checked, or a
real error found among them. The false alarms must stay silent; the real
errors must still be found.
"""

from __future__ import annotations

from verbatim.qa import letters
from verbatim.qa.external import (
    _absent_numbers,
    _repeated_passages,
    _spelling_variants,
    _unfound_rows,
    _unscramble,
)
from verbatim.qa.fidelity import HIGH, Finding


def unmatched(text, pdf):
    return [text[a:b] for a, b, _ in letters.unmatched(text, letters.shingles(pdf))]


PDF = ("The Conference of the Parties, recalling its decision 5/CP.7 on the "
       "guidelines for national communications, decides to adopt the modalities "
       "contained in the annex to the present decision, subject to the "
       "availability of resources.")


# --- how a word is written is not a difference ------------------------------

def test_words_the_pdf_runs_together_are_found():
    pdf = PDF.replace("subject to the availability", "subjecttotheavailability")
    assert unmatched(PDF, pdf) == []


def test_accents_the_pdf_lost_are_found():
    pdf = "Les Ministres ont decide de reviser les resolutions prises a Yaounde."
    text = "Les Ministres ont décidé de réviser les résolutions prises à Yaoundé."
    assert unmatched(text, pdf) == []


def test_mangled_apostrophes_are_read_past():
    pdf = "the Commission’s approval for temporary catch limit adjustments"
    text = "the Commissionâ€™s approval for temporary catch limit adjustments"
    assert unmatched(text, pdf) == []


def test_ligatures_the_pdf_cannot_decode_are_explained_by_the_text():
    pdf = ("posi(cid:31)ve results; nega(cid:31)ve results; the isola(cid:31)on "
           "was repeated; a(cid:29)empt to confirm the posi(cid:31)ve isola(cid:31)on")
    text = ("positive results; negative results; the isolation was repeated; "
            "attempt to confirm the positive isolation")
    decoded = letters.decode_cids(pdf, text)
    assert "positive" in decoded and "isolation" in decoded
    assert unmatched(text, decoded) == []


def test_one_odd_word_cannot_decode_a_glyph():
    """A code explained only once is left alone: an invented word must not be
    able to make itself appear in the PDF."""
    assert "(cid:" not in letters.decode_cids("a (cid:7)b", "axb")
    assert letters.decode_cids("a (cid:7)b", "axb") == "a  b"


def test_a_typo_leaves_no_passage():
    text = PDF.replace("modalities", "modalitties").replace("Parties", "Partise")
    assert unmatched(text, PDF) == []


def test_table_cells_in_another_order_are_found():
    pdf = "Rock salt Salt dome up to 1,000 m Clay Claystone up to 400 m"
    text = "Salt dome\tRock salt\tup to 1,000 m\nClaystone\tClay\tup to 400 m"
    assert unmatched(text, pdf) == []


def test_arabic_digits_are_digits():
    assert letters.fold("١٩٨٨")[0] == "1988"


# --- what is not in the PDF is still found ---------------------------------

def test_an_invented_sentence_is_found_and_starts_on_a_word():
    invented = ("The Parties further agree to establish a permanent trust fund "
                "administered jointly by the regional commissions.")
    found = unmatched(PDF + " " + invented, PDF)
    assert len(found) == 1
    assert "permanent trust fund" in found[0]
    assert found[0][0].isalpha() and not found[0].startswith("ecides")


def test_a_note_left_by_a_model_is_found():
    found = unmatched(PDF + "\n[No text content to extract, only flowchart]", PDF)
    assert found and "No text content" in found[0]


def test_a_changed_dna_sequence_is_found():
    pdf = "Probe COXSOL 1511T (5'-AGGGCATTCCATCCAGCGTAAGCA-3')"
    text = "Probe COX5OL 1511T (5'-AGGGCATTCTCACTCAGCGTAAAGCA-3')"
    assert unmatched(text, pdf)


# --- numbers -------------------------------------------------------------

def test_numbers_are_compared_on_their_digits():
    pdf = "a total of 1 000 tonnes in 2008, see pages 165–171 and Forestry87,471–481"
    text = "a total of 1,000 tonnes in 2008, see pages 165-171 and Forestry 87, 471-481"
    assert _absent_numbers(text, pdf, []) == []


def test_a_changed_year_is_found_where_it_is():
    text = "adopted in 2009 at the session"
    found = _absent_numbers(text, "adopted in 2008 at the session", [])
    assert len(found) == 1
    assert text[found[0].char_start:found[0].char_end] == "2009"


def test_numbers_on_one_line_are_one_finding():
    found = _absent_numbers("Others\t13,930\t15,270\t4,000", "Others 500 100", [])
    assert len(found) == 1 and found[0].params["n"] == 3


# --- tables, repetition, spelling -----------------------------------------

def test_a_table_the_pdf_prints_as_a_picture_is_one_finding():
    pdf = "Table 2. Contributions of the members, see figure"
    text = "Algeria\t0,11\t0,87\t1.283,62\nMorocco\t0,06\t0,44\t1.000,00\nTunisia\t0,02\t0,15\t1.000,00"
    found, ranges = _unfound_rows(text, letters.shingles(pdf), letters.fold(pdf)[0], [])
    assert len(found) == 1 and found[0].params["n"] == 3


def test_a_wrapped_table_cell_is_found():
    cell = ("Develop and maintain contact networks with appropriate stakeholders "
            "and establish communication procedures.")
    pdf = ("Develop and maintain contact Identify spokespeople networks with "
           "appropriate stakeholders and establish communication procedures.")
    text = "Identify spokespeople\t" + cell
    found, _ = _unfound_rows(text, letters.shingles(pdf), letters.fold(pdf)[0], [])
    assert found == []


def test_a_paragraph_repeated_is_reported_at_the_extra_copies():
    line = "2.1.3. DNA should preferably be stored at approximately -20°C."
    text = "\n".join([line, "Other text here.", line, line])
    found = _repeated_passages(text, letters.fold(line + " Other text here.")[0])
    # The first copy is the PDF's; the two after it are one repeated block.
    assert len(found) == 1
    assert text[found[0].char_start:found[0].char_end] == line + "\n" + line
    assert found[0].params["times"] == 3 and found[0].params["in_pdf"] == 1


def test_a_one_letter_difference_is_a_spelling_variant():
    found = _spelling_variants("Rogers, Starmmer, Castello",
                               "Rogers, Starmer, Castello",
                               letters.fold("Rogers, Starmer, Castello")[0], [])
    assert [(f.params["word"], f.params["pdf"]) for f in found] == [("Starmmer", "Starmer")]


def test_a_name_the_pdf_contains_is_not_scrambled():
    f = Finding(kind="scrambled_text", severity=HIGH, key="scrambled_text",
                params={"n": 2, "sample": "LexUriServ, MobIsNeDrFvaUtLio"},
                detail="LexUriServ MobIsNeDrFvaUtLio")
    kept = _unscramble([f], "see LexUriServ and MobIsNeDrFvaUtLio",
                       letters.fold("eur-lex.europa.eu/LexUriServ/LexUriServ.do")[0])
    assert len(kept) == 1 and kept[0].params["sample"] == "MobIsNeDrFvaUtLio"


# --- what the team leaves out on purpose -----------------------------------

def test_footnotes_are_not_reported_missing(tmp_path):
    """Footnotes are left out of the texts on purpose; a paragraph is not."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "synthetic"))
    from makepdf import Page, write_pdf

    from verbatim.pipeline import convert
    from verbatim.qa.external import Reference, _missing_text
    from verbatim.settings import Settings

    body = ["The Conference of the Parties, recalling its earlier decisions on",
            "the guidelines for national communications, decides to adopt the",
            "modalities contained in the annex to the present decision, subject",
            "to the availability of resources and the provisions of the annex."]
    dropped = ["2. Further requests the secretariat to report on the implementation",
               "of this decision to the Conference of the Parties at its next session."]
    page = Page()
    page.lines(72, 90, body, size=11, leading=14)
    page.lines(72, 170, dropped, size=11, leading=14)
    page.lines(72, 700, ["1 See document FCCC/SBI/2004/19 for the full report of the "
                         "Subsidiary Body for Implementation on its twentieth session."],
               size=7, leading=9)
    pdf = write_pdf(tmp_path / "notes.pdf", [page])
    res = convert(pdf, Settings(ocr="off"), log=lambda *a, **k: None)
    ref = Reference(res.text, res.spans)
    text = " ".join(body)

    found = _missing_text(text, ref, [p.to_dict() for p in res.pages])
    quoted = " ".join(f.params["sample"] for f in found)
    assert "Further requests the secretariat" in quoted
    assert "FCCC/SBI" in res.text, "the footnote is in the reading"
    assert "FCCC/SBI" not in quoted, "a footnote was reported missing"
    assert all(f.bbox for f in found), "each passage is outlined on its page"


def test_text_set_sideways_in_the_margin_is_set_aside():
    """A publisher's licence printed up the margin reads as one tall, narrow
    line: "esneciL snommoC evitaerC" in one journal's text layer."""
    from verbatim.qa.external import Reference, _set_aside
    text = "\n".join([f"Body line number {i} of the decision text." for i in range(6)]
                     + ["esneciL snommoC evitaerC elbacilppa eht yb denrevog"])
    spans, at = [], 0
    for i, line in enumerate(text.split("\n")):
        box = [72, 90 + 14 * i, 500, 101 + 14 * i] if i < 6 else [560, 200, 568, 700]
        spans.append({"page": 1, "char_start": at, "char_end": at + len(line),
                      "bbox": box, "source": "extracted"})
        at += len(line) + 1
    aside = _set_aside(Reference(text, spans), [{"page": 1, "height": 842}])
    assert [text[a:b] for a, b in aside] == [text.split("\n")[-1]]
