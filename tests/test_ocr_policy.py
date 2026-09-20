"""
Tesseract is a cross-check, not a converter.

Measured on real documents: its output is too poor to convert with as soon as a
scan is less than clean. It is kept for one job only — reading a scan
independently so that a passage a model invented can be found — and it is only
believed when it read the page well enough for its reading to be evidence.
"""

from __future__ import annotations

import pdfplumber
import pytest

from verbatim.cli import make_parser
from verbatim.qa.config import CONFIG
from verbatim.qa.external import check
from verbatim.settings import Settings


def test_conversion_defaults_to_the_model():
    assert Settings().ocr_engine == "mistral"


def test_the_command_line_no_longer_offers_a_choice_of_engine():
    text = make_parser().format_help()
    convert = make_parser().parse_args(["convert", "x"])
    assert "--ocr-engine" not in text
    assert getattr(convert, "ocr_engine", "mistral") == "mistral"


def test_the_window_no_longer_offers_a_choice_of_engine():
    source = open("verbatim/gui/convert_tab.py", encoding="utf-8").read()
    assert '"tesseract", "mistral"' not in source


def test_review_still_asks_tesseract_by_name():
    """Review must not inherit the conversion default, or the cross-check
    would quietly try to call a paid API."""
    source = open("verbatim/qa/external.py", encoding="utf-8").read()
    assert 'ocr_engine="tesseract"' in source


def _tesseract():
    try:
        from verbatim.ocr.detect import check_ocr
        return check_ocr("tesseract")[0]
    except Exception:
        return False


@pytest.fixture(scope="module")
def bad_scan(synthetic_dir, tmp_path_factory):
    """A scan too poor to read: low resolution, blurred and speckled."""
    from PIL import ImageFilter
    out = tmp_path_factory.mktemp("bad") / "poor_scan.pdf"
    with pdfplumber.open(str(synthetic_dir / "simple.pdf")) as doc:
        pages = [p.to_image(resolution=70).original.convert("L") for p in doc.pages]
    damaged = []
    for image in pages:
        image = image.filter(ImageFilter.GaussianBlur(1.4))
        small = image.resize((image.width // 2, image.height // 2))
        damaged.append(small.resize(image.size).convert("RGB"))
    damaged[0].save(out, save_all=True, append_images=damaged[1:], resolution=70)
    return out


@pytest.mark.ocr
@pytest.mark.skipif(not _tesseract(), reason="Tesseract is not installed")
def test_an_unreadable_scan_is_not_used_as_evidence(synthetic_dir, bad_scan, tmp_path):
    """Comparing against a bad reading reports every paragraph as missing, and
    a reviewer shown a hundred false alarms stops reading the real ones."""
    from verbatim.pipeline import convert
    text = convert(synthetic_dir / "simple.pdf", Settings(ocr="off"),
                   log=lambda *a, **k: None).text
    txt = tmp_path / "file.txt"
    txt.write_text(text, encoding="utf-8")
    record = check(txt, pdf_path=bad_scan, ocr=True)

    confidences = [p["ocr_conf"] for p in record["pages"] if p.get("ocr_conf")]
    assert confidences, "the scan was not recognised at all"
    assert min(confidences) < CONFIG["CROSSCHECK_CONF_MIN"], (
        "this scan is not poor enough to exercise the gate")
    assert record["notice"] == "scan_unreadable"
    assert record["reference"] == "none"
    kinds = [f["kind"] for f in record["assessment"]["findings"]]
    assert "not_in_scan" not in kinds, "false alarms from an unreadable scan"
    assert "scan_unchecked" in kinds
    assert record["assessment"]["verdict"] != "ok"


@pytest.mark.ocr
@pytest.mark.skipif(not _tesseract(), reason="Tesseract is not installed")
def test_a_readable_scan_is_still_used(synthetic_dir, tmp_path_factory, tmp_path):
    """The gate must not throw away the check that does work."""
    from verbatim.pipeline import convert
    scan = tmp_path_factory.mktemp("good") / "scan.pdf"
    with pdfplumber.open(str(synthetic_dir / "simple.pdf")) as doc:
        images = [p.to_image(resolution=200).original.convert("RGB") for p in doc.pages]
    images[0].save(scan, save_all=True, append_images=images[1:], resolution=200)
    text = convert(synthetic_dir / "simple.pdf", Settings(ocr="off"),
                   log=lambda *a, **k: None).text
    txt = tmp_path / "file.txt"
    txt.write_text(text, encoding="utf-8")
    record = check(txt, pdf_path=scan, ocr=True)
    assert record["reference"] == "recognised"
