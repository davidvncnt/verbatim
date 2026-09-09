"""
The gate turns evidence into a verdict; the sidecar turns a verdict into
something a reviewer can act on.

The test that matters most here is the last one: a finding must carry the page
it is on. "Six invented words somewhere in this file" sends a person back to
reading the whole document, which is the failure mode the tool exists to fix.
"""

from __future__ import annotations

import json

import pytest

from verbatim import sidecar
from verbatim.pipeline import collect_targets, convert, run_batch
from verbatim.qa.gate import QualityGate
from verbatim.settings import Settings


def convert_one(pdf):
    return convert(pdf, Settings(ocr="off"), log=lambda *a, **k: None)


@pytest.fixture(scope="module")
def gate():
    return QualityGate()


# --- verdicts -------------------------------------------------------------

def test_clean_documents_pass(synthetic_pdfs, gate):
    for pdf in synthetic_pdfs:
        a = gate.assess(convert_one(pdf), pdf_path=pdf)
        assert a.verdict == "ok", f"{pdf.name}: {a.verdict} — {a.reasons()}"


def test_a_paraphrase_is_rejected(synthetic_dir, gate):
    res = convert_one(synthetic_dir / "simple.pdf")
    res.text = res.text.replace("Decides to adopt", "Resolves to approve")
    a = gate.assess(res, pdf_path=synthetic_dir / "simple.pdf")
    assert a.verdict == "reject"
    assert any(f.kind == "invented_words" for f in a.findings)


def test_a_repetition_loop_is_rejected(synthetic_dir, gate):
    """The signature of a recogniser that fell into a loop."""
    res = convert_one(synthetic_dir / "simple.pdf")
    loop = "the Parties shall consider the matter further at the next session "
    res.text = res.text + "\n\n" + (loop * 60)
    a = gate.assess(res, pdf_path=synthetic_dir / "simple.pdf")
    assert a.verdict == "reject"
    assert any(f.kind == "repetition_loop" for f in a.findings)


def test_model_produced_pages_always_need_a_person(synthetic_dir, gate):
    """Nothing in the document can confirm a model's words, so they are never
    signed off silently — however clean the text looks."""
    pdf = synthetic_dir / "simple.pdf"
    res = convert_one(pdf)
    for page in res.pages:
        page.source = "recognised_model"
    a = gate.assess(res, pdf_path=pdf)
    assert a.needs_review
    assert any(f.kind == "model_pages" for f in a.findings)


def test_findings_are_ordered_worst_first(synthetic_dir, gate):
    res = convert_one(synthetic_dir / "simple.pdf")
    res.text = res.text.replace("Decides to adopt", "Resolves to approve")
    a = gate.assess(res, pdf_path=synthetic_dir / "simple.pdf")
    severities = [f.severity for f in a.findings]
    assert severities == sorted(severities,
                               key=lambda s: {"high": 0, "medium": 1}.get(s, 2))


def test_without_a_baseline_only_absolute_checks_fire(gate):
    """A z-score needs a corpus to be a score against. Saying so is better than
    silently scoring everything zero."""
    assert gate.has_baseline is False


# --- the sidecar ----------------------------------------------------------

def test_conversion_writes_a_record_beside_the_text(synthetic_dir, tmp_path):
    args = Settings(ocr="off")
    args.out = tmp_path
    targets = collect_targets([synthetic_dir], False)
    res = run_batch(targets, args, log=lambda *a, **k: None)
    assert res.done == len(targets) and not res.failed
    for txt, _verdict in res.converted:
        rec = sidecar.read(txt)
        assert rec is not None, f"no record for {txt.name}"
        assert rec["source_sha256"], "the source PDF is not identified"
        assert rec["text_file"] == txt.name
        assert rec["assessment"]["verdict"] in ("ok", "review", "reject")
        assert rec["review"] is None, "the tool must not sign off for a person"


def test_the_record_never_contains_an_api_key(synthetic_dir, tmp_path):
    args = Settings(ocr="off", mistral_key="sk-secret-value-do-not-write")
    args.out = tmp_path
    run_batch([synthetic_dir / "simple.pdf"], args, log=lambda *a, **k: None)
    raw = (tmp_path / "simple.verbatim.json").read_text(encoding="utf-8")
    assert "sk-secret-value-do-not-write" not in raw
    assert "mistral_key" not in json.loads(raw)["settings"]


def test_spans_cover_the_text_and_point_at_real_pages(synthetic_dir, tmp_path):
    args = Settings(ocr="off")
    args.out = tmp_path
    run_batch([synthetic_dir / "simple.pdf"], args, log=lambda *a, **k: None)
    rec = sidecar.read(tmp_path / "simple.txt")
    text = (tmp_path / "simple.txt").read_text(encoding="utf-8")
    assert rec["spans"]
    for s in rec["spans"]:
        assert 0 <= s["char_start"] < s["char_end"] <= len(text)
        assert 1 <= s["page"] <= rec["stats"]["pages"]
        assert s["bbox"] and len(s["bbox"]) == 4
        assert s["source"] == "extracted"


def test_a_finding_carries_the_page_it_is_on(synthetic_dir, gate):
    """Without this the reviewer is sent back to reading the whole file."""
    pdf = synthetic_dir / "simple.pdf"
    res = convert_one(pdf)
    # damage a sentence that only exists on page 3
    res.text = res.text.replace("consider the synthesis report",
                                "examine the collated summary")
    a = gate.assess(res, pdf_path=pdf)
    sidecar.locate_findings(a.findings, res.blocks)
    located = [f for f in a.findings if f.kind == "invented_words"]
    assert located and located[0].page == 3, (
        f"expected page 3, got {located[0].page if located else 'no finding'}")


def test_a_person_can_record_their_decision(synthetic_dir, tmp_path):
    args = Settings(ocr="off")
    args.out = tmp_path
    run_batch([synthetic_dir / "simple.pdf"], args, log=lambda *a, **k: None)
    txt = tmp_path / "simple.txt"
    rec = sidecar.record_review(txt, verdict="accepted", reviewer="RA1",
                                note="checked against the PDF")
    assert rec["review"]["verdict"] == "accepted"
    assert rec["review"]["reviewer"] == "RA1"
    # the tool's own assessment is kept distinct from the person's judgement
    assert rec["review"]["tool_said"] == rec["assessment"]["verdict"]
    assert sidecar.read(txt)["review"]["note"] == "checked against the PDF"
