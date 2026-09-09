"""
What the extractor is supposed to do, asserted directly.

The golden suite proves verbatim matches the script it came from. That is not
the same as being correct: both could be wrong together. These tests state the
intended behaviour, so a shared regression still fails.

Every case here corresponds to a finding the project already paid to learn,
recorded in docs/brief.md.
"""

from __future__ import annotations

import pytest

from verbatim.pipeline import convert
from verbatim.settings import Settings


def run(pdf, **changes):
    return convert(pdf, Settings(ocr="off", **changes), log=lambda *a, **k: None)


@pytest.fixture(scope="module")
def out(synthetic_dir):
    """Convert every fixture once."""
    return {p.stem: run(p) for p in sorted(synthetic_dir.glob("*.pdf"))}


# --- format ---------------------------------------------------------------

def test_one_paragraph_per_line_no_stray_blank_lines(out):
    for name, res in out.items():
        text = res.text
        assert text.endswith("\n"), name
        assert "\n\n\n" not in text, f"{name}: more than one blank line between paragraphs"
        assert not text.startswith("\n"), name
        for line in text.splitlines():
            assert line == line.rstrip(), f"{name}: trailing whitespace on a line"


def test_output_is_utf8_without_bom(out, tmp_path):
    for name, res in out.items():
        p = tmp_path / f"{name}.txt"
        p.write_text(res.text, encoding="utf-8")
        assert not p.read_bytes().startswith(b"\xef\xbb\xbf"), name


# --- running headers, footers, page numbers -------------------------------

def test_running_furniture_is_removed(out):
    text = out["simple"].text
    assert "INTERNATIONAL PLANT PROTECTION CONVENTION" not in text
    assert "CPM-8" not in text
    assert "Page 1 of 3" not in text and "Page 2 of 3" not in text
    assert out["simple"].stats["dropped"] == 6      # header + footer, three pages


def test_recurring_heading_survives_the_header_filter(out):
    """A section heading recurring at the top of every page is content, not
    furniture. Only the font-size guard tells them apart."""
    res = out["recurring_heading"]
    assert res.text.count("ARTICLE 12: SETTLEMENT OF DISPUTES") == 3
    assert "- 1 -" not in res.text and "- 2 -" not in res.text   # page numbers go


def test_keep_headers_really_keeps_them(synthetic_dir):
    res = run(synthetic_dir / "simple.pdf", keep_headers=True)
    assert "INTERNATIONAL PLANT PROTECTION CONVENTION" in res.text
    assert res.stats["dropped"] == 0


# --- paragraphs -----------------------------------------------------------

def test_paragraph_split_across_a_page_break_is_stitched(out):
    text = out["simple"].text
    joined = [l for l in text.splitlines() if "entry into force of" in l]
    assert len(joined) == 1
    assert "the amendment" in joined[0], "the sentence was not carried over the page break"


def test_no_join_pages_leaves_the_break_alone(synthetic_dir):
    res = run(synthetic_dir / "simple.pdf", join_pages=False)
    assert not [l for l in res.text.splitlines()
                if "entry into force of" in l and "the amendment" in l]


def test_dehyphenation_joins_broken_words_and_keeps_compounds(out):
    text = out["hyphenated"].text
    assert "matter" in text and "mat- ter" not in text and "mat-ter" not in text
    assert "consideration" in text
    assert "Franco-German" in text, "a genuine compound hyphen was destroyed"


def test_keep_hyphens_preserves_the_line_break_hyphen(synthetic_dir):
    res = run(synthetic_dir / "hyphenated.pdf", keep_hyphens=True)
    assert "mat-ter" in res.text


# --- columns --------------------------------------------------------------

def test_two_columns_are_read_in_order_not_interleaved(out):
    res = out["two_column"]
    assert res.stats["twocol"] == 1
    text = res.text
    left_end = text.index("recommended to the Commission")
    right_start = text.index("Several delegations")
    assert left_end < right_start, "columns were interleaved instead of read in turn"


def test_heading_crossing_the_gutter_does_not_break_detection(out):
    """A full-width heading closes a whitespace corridor. The gutter is found
    from where most rows share one wide internal gap, so this still works."""
    text = out["two_column"].text
    assert "ANNEX III: SUMMARY OF THE DELIBERATIONS OF THE WORKING GROUP" in text
    assert out["two_column"].stats["twocol"] == 1


def test_dehyphenation_works_inside_a_column(out):
    assert "organizations" in out["two_column"].text


def test_columns_one_disables_splitting(synthetic_dir):
    assert run(synthetic_dir / "two_column.pdf", columns="1").stats["twocol"] == 0


# --- tables ---------------------------------------------------------------

CELLS = ["Protected areas", "17%", "30%", "On track",
         "Degraded land", "22%", "10%", "At risk",
         "Species index", "0.71", "0.90"]


def test_ruled_table_is_rendered_as_aligned_columns(out):
    res = out["ruled_table"]
    assert res.stats["tables"] == 1
    assert " | " in res.text and "-+-" in res.text
    for cell in CELLS:
        assert cell in res.text, f"lost table cell {cell!r}"


def test_unruled_table_is_rebuilt_from_alignment(out):
    text = out["unruled_table"].text
    assert " | " in text, "a table with no ruling lines was not reconstructed"
    for cell in ["58.4.1", "Dissostichus", "1 220", "Dec-Mar", "Euphausia", "62 000"]:
        assert cell in text


def test_justified_prose_is_not_mistaken_for_a_table(out):
    """Stretched word spacing in justified text mimics table cells. Requiring
    cell positions to align across consecutive rows is what separates them."""
    text = out["justified"].text
    assert " | " not in text and "-+-" not in text
    assert "Each Party shall take the measures necessary" in text


def test_tables_none_reads_a_table_as_prose(synthetic_dir):
    res = run(synthetic_dir / "ruled_table.pdf", tables="none")
    assert res.stats["tables"] == 0
    assert "Protected areas" in res.text


def test_table_markers_wrap_the_table(synthetic_dir):
    res = run(synthetic_dir / "ruled_table.pdf", table_markers=True)
    assert "[TABLE]" in res.text and "[/TABLE]" in res.text


# --- sideways pages -------------------------------------------------------

def test_sideways_page_is_straightened_and_read(out):
    text = out["sideways"].text
    for w in ["Dissostichus", "Champsocephalus", "Euphausia", "62 000",
              "ANNEX II: CATCH LIMITS"]:
        assert w in text, f"lost {w!r} from a page printed at 90 degrees"


# --- encoding -------------------------------------------------------------

def test_accents_and_punctuation_survive(out):
    text = out["accents"].text
    for w in ["Conférence", "décision", "l'établissement", "présente",
              "« sous réserve des ressources disponibles »",
              "Conferencia", "secretaría", "síntesis", "aplicación"]:
        assert w in text, f"lost {w!r}"


# --- fidelity -------------------------------------------------------------

def test_nothing_is_lost_or_invented_on_any_fixture(out):
    """Retention over letters and digits, with deliberate removals added back.

    Below 1.0 means text was dropped; above 1.0 means text appeared that the
    page did not hold. On a deterministic extraction both are bugs.
    """
    for name, res in out.items():
        assert res.stats["alnum_ratio"] == pytest.approx(1.0, abs=0.005), (
            f"{name}: alnum_ratio {res.stats['alnum_ratio']:.3f}")


# --- page marks -----------------------------------------------------------

def test_page_marks_are_off_by_default_and_correct_when_on(out, synthetic_dir):
    assert "[page 1]" not in out["simple"].text
    res = run(synthetic_dir / "simple.pdf", page_marks=True)
    for n in (1, 2, 3):
        assert f"[page {n}]" in res.text


# --- provenance -----------------------------------------------------------

def test_every_block_can_be_located_in_the_pdf(out):
    """The reviewer needs a page, a rectangle and a character range for each
    passage. Without those it cannot put the text beside the page it came from."""
    for name, res in out.items():
        paras = [b for b in res.blocks if b.kind == "para" and b.text.strip()]
        assert paras, name
        for b in paras:
            assert b.spans, f"{name}: a paragraph carries no provenance"
            for s in b.spans:
                assert s.char_end > s.char_start, f"{name}: empty character range"
                assert res.text[s.char_start:s.char_end] == b.text.strip(), (
                    f"{name}: span does not point at the block's own text")
                assert 1 <= s.page <= res.stats["pages"], f"{name}: bad page number"
                assert s.source == "extracted", f"{name}: wrong provenance label"


def test_a_stitched_paragraph_reports_both_its_pages(out):
    """The paragraph carried across the page break belongs to two pages."""
    joined = [b for b in out["simple"].blocks
              if b.kind == "para" and "entry into force of" in b.text]
    assert len(joined) == 1
    assert {s.page for s in joined[0].spans} == {1, 2}
