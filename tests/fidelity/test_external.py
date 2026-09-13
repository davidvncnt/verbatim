"""
Checking text files that verbatim did not make.

Most of the corpus was converted by earlier scripts, one of which is known to
have invented text. These tests use files shaped like that output —
hard-wrapped lines, running headers kept — because a checker that only stays
quiet on verbatim's own formatting would bury a reviewer in false alarms on
exactly the files that need checking.
"""

from __future__ import annotations

import shutil

import pdfplumber
import pytest

from verbatim.pipeline import convert
from verbatim.qa.external import FULL, TEXT_ONLY, check, find_pdf, quick_verdict
from verbatim.settings import Settings


def old_style(pdf):
    with pdfplumber.open(str(pdf)) as doc:
        return "\n\n".join(page.extract_text() or "" for page in doc.pages)


def run(tmp_path, text, pdf, **kw):
    txt = tmp_path / "file.txt"
    txt.write_text(text, encoding="utf-8")
    return check(txt, pdf_path=pdf, ocr=kw.pop("ocr", False), **kw)


def kinds(record):
    return [f["kind"] for f in record["assessment"]["findings"]]


# --- no false alarms ------------------------------------------------------

@pytest.mark.parametrize("style", ["old", "verbatim"])
def test_clean_files_raise_nothing(synthetic_pdfs, tmp_path, style):
    for pdf in synthetic_pdfs:
        if pdf.stem == "sideways" and style == "old":
            continue        # the unstraightened reading is genuinely garbled
        text = old_style(pdf) if style == "old" else convert(
            pdf, Settings(ocr="off"), log=lambda *a, **k: None).text
        record = run(tmp_path, text, pdf)
        assert record["assessment"]["findings"] == [], (
            pdf.name, [f["message_en"] for f in record["assessment"]["findings"]])


def test_a_garbled_old_reading_is_caught(synthetic_dir, tmp_path):
    """Reading a sideways page without straightening it produces reversed
    words — "stimil hctac" for "limits catch". That file is damaged, and
    saying so is the point."""
    record = run(tmp_path, old_style(synthetic_dir / "sideways.pdf"),
                 synthetic_dir / "sideways.pdf")
    assert record["assessment"]["verdict"] == "reject"
    assert "invented_words" in kinds(record)


# --- damage ---------------------------------------------------------------

@pytest.fixture
def simple(synthetic_dir):
    return synthetic_dir / "simple.pdf", old_style(synthetic_dir / "simple.pdf")


def test_an_invented_sentence_is_one_located_finding(simple, tmp_path):
    pdf, text = simple
    damaged = text.replace(
        "information submitted under paragraph 1 above.",
        "information submitted under paragraph 1 above. The Parties further agree "
        "to establish a permanent trust fund administered jointly by the regional "
        "commissions.")
    record = run(tmp_path, damaged, pdf)
    found = record["assessment"]["findings"]
    assert kinds(record) == ["invented_words"], [f["message_en"] for f in found]
    assert found[0]["page"] == 2
    assert "permanent trust fund" in damaged[found[0]["char_start"]:found[0]["char_end"]]


def test_a_changed_date_is_reported_once(simple, tmp_path):
    pdf, text = simple
    record = run(tmp_path, text.replace("5/CP.7", "9/CP.21"), pdf)
    assert kinds(record) == ["invented_numbers"]
    assert record["assessment"]["findings"][0]["page"] == 1


def test_a_dropped_paragraph_is_placed_on_its_page(simple, tmp_path):
    pdf, text = simple
    paragraph = ("3. Also requests the Subsidiary Body for Implementation to consider\n"
                 "the synthesis report at its next session.")
    assert paragraph in text
    record = run(tmp_path, text.replace(paragraph, ""), pdf)
    missing = [f for f in record["assessment"]["findings"]
               if f["kind"] == "missing_from_text"]
    assert missing and missing[0]["page"] == 3
    assert missing[0]["bbox"], "the reviewer needs a rectangle to look at"
    assert "3. Also requests the Subsidiary Body" in missing[0]["message_en"]


def test_a_repeated_paragraph_is_duplication_not_invention(simple, tmp_path):
    pdf, text = simple
    repeated = text + ("\n\n2. Requests the secretariat to prepare a synthesis report "
                       "on the\ninformation submitted under paragraph 1 above.")
    record = run(tmp_path, repeated, pdf)
    assert kinds(record) == ["duplicated_words"]


def test_markers_from_earlier_scripts_are_not_reported(simple, tmp_path):
    pdf, text = simple
    marked = "[page 1]\n" + text.replace("Page 2 of 3", "[page 2]\nPage 2 of 3")
    assert run(tmp_path, marked, pdf)["assessment"]["findings"] == []


def test_lines_are_placed_on_the_right_pages(simple, tmp_path):
    pdf, text = simple
    record = run(tmp_path, text, pdf)
    pages = {text[s["char_start"]:s["char_end"]][:20]: s["page"]
             for s in record["spans"]}
    assert pages["the amendment, subje"] == 2       # continues a page-1 paragraph
    assert pages["3. Also requests the"] == 3


# --- modes ----------------------------------------------------------------

def test_text_only_never_opens_the_pdf(simple, tmp_path):
    pdf, text = simple
    record = run(tmp_path, text, pdf, mode=TEXT_ONLY)
    assert record["reference"] == "none" and record["pages"] == []
    assert record["notice"] == "text_only"


def test_no_pdf_still_runs_the_text_checks(tmp_path):
    loop = "the Parties shall consider the matter further at the next session " * 60
    record = run(tmp_path, loop, None, mode=FULL)
    assert record["notice"] == "no_pdf"
    assert "repetition_loop" in kinds(record)
    f = record["assessment"]["findings"][0]
    assert f["char_start"] is not None, "the loop is not located in the text"


def test_quick_verdict_orders_without_a_pdf(tmp_path):
    loop = tmp_path / "loop.txt"
    loop.write_text("the same eight words repeat here again and again " * 60,
                    encoding="utf-8")
    fine = tmp_path / "fine.txt"
    fine.write_text("The Conference of the Parties decides to adopt the annex.",
                    encoding="utf-8")
    assert quick_verdict(loop)["verdict"] == "reject"
    assert quick_verdict(fine)["verdict"] == "ok"


def test_the_pdf_is_matched_by_name_across_unicode_forms(tmp_path):
    """macOS reports accented names decomposed; what was typed is composed."""
    import unicodedata
    pdfs = tmp_path / "pdf"
    pdfs.mkdir()
    (pdfs / unicodedata.normalize("NFD", "20005_décision_2007.PDF")).write_bytes(b"%PDF")
    txt = tmp_path / unicodedata.normalize("NFC", "20005_décision_2007.txt")
    txt.write_text("x", encoding="utf-8")
    assert find_pdf(txt, pdfs) is not None


def test_a_cp1252_file_is_read(simple, tmp_path):
    pdf, text = simple
    txt = tmp_path / "legacy.txt"
    txt.write_bytes(("Décision " + text).encode("cp1252", errors="replace"))
    record = check(txt, pdf_path=pdf, ocr=False)
    assert record["text_sha256"]


# --- scans ----------------------------------------------------------------

def _tesseract():
    try:
        from verbatim.ocr.detect import check_ocr
        return check_ocr("tesseract")[0]
    except Exception:
        return False


@pytest.fixture(scope="module")
def scan(synthetic_dir, tmp_path_factory):
    """simple.pdf with its text layer removed: the pages as images only."""
    out = tmp_path_factory.mktemp("scan") / "simple_scan.pdf"
    with pdfplumber.open(str(synthetic_dir / "simple.pdf")) as doc:
        images = [p.to_image(resolution=200).original.convert("RGB") for p in doc.pages]
    images[0].save(out, save_all=True, append_images=images[1:], resolution=200)
    return out


@pytest.mark.ocr
@pytest.mark.skipif(not _tesseract(), reason="Tesseract is not installed")
def test_a_clean_file_matches_its_scan(synthetic_dir, scan, tmp_path):
    text = convert(synthetic_dir / "simple.pdf", Settings(ocr="off"),
                   log=lambda *a, **k: None).text
    record = run(tmp_path, text, scan, ocr=True)
    assert record["reference"] == "recognised"
    assert record["assessment"]["verdict"] == "ok", kinds(record)


@pytest.mark.ocr
@pytest.mark.skipif(not _tesseract(), reason="Tesseract is not installed")
def test_an_invented_passage_is_found_against_a_scan(synthetic_dir, scan, tmp_path):
    text = convert(synthetic_dir / "simple.pdf", Settings(ocr="off"),
                   log=lambda *a, **k: None).text.replace(
        "information submitted under paragraph 1 above.",
        "information submitted under paragraph 1 above. The Parties further agree "
        "to establish a permanent trust fund administered jointly by the regional "
        "commissions of each continent.")
    record = run(tmp_path, text, scan, ocr=True)
    found = [f for f in record["assessment"]["findings"] if f["kind"] == "not_in_scan"]
    assert found and found[0]["page"] == 2
    assert found[0]["severity"] == "high"


def test_an_unreadable_scan_is_declared_not_passed(synthetic_dir, scan, tmp_path):
    """Without recognition there is nothing to compare, and that must not look
    like a clean result."""
    text = old_style(synthetic_dir / "simple.pdf")
    record = run(tmp_path, text, scan, ocr=False)
    assert record["notice"] == "scan_unchecked"
    assert record["assessment"]["verdict"] != "ok"
    assert record["pages"], "the page images are still worth showing"


def test_the_source_folder_is_not_modified(simple, tmp_path):
    pdf, text = simple
    folder = tmp_path / "pdfs"
    folder.mkdir()
    shutil.copy(pdf, folder / "simple.pdf")
    before = sorted(p.name for p in folder.iterdir())
    txt = tmp_path / "simple.txt"
    txt.write_text(text, encoding="utf-8")
    check(txt, pdf_path=find_pdf(txt, folder), ocr=False)
    assert sorted(p.name for p in folder.iterdir()) == before
