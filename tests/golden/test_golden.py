"""
The port is only safe if it changes nothing. This compares verbatim's output,
character for character, against the frozen script it was split out of.

OCR is off throughout: recognition is not deterministic across runs, so it
cannot be part of a byte-equality test. The deterministic path is the one that
handles the overwhelming majority of the corpus, and it is the one the fidelity
guarantees rest on.
"""

from __future__ import annotations

import pytest

from verbatim.pipeline import convert
from verbatim.settings import Settings

# Settings combinations that exercise the branches most likely to drift apart.
CASES = {
    "defaults": {},
    "page_marks": {"page_marks": True},
    "keep_headers": {"keep_headers": True},
    "keep_hyphens": {"keep_hyphens": True},
    "no_join_pages": {"join_pages": False},
    "one_column": {"columns": "1"},
    "force_two_column": {"columns": "2"},
    "tables_none": {"tables": "none"},
    "tables_text": {"tables": "text"},
    "table_markers": {"table_markers": True},
    "keep_sideways": {"keep_sideways": True},
    "narrow_tables": {"width": 60},
}


def _reference_args(reference, **changes):
    args = reference.make_parser().parse_args([])
    args.ocr = "off"
    for k, v in changes.items():
        setattr(args, k, v)
    return args


@pytest.mark.golden
@pytest.mark.parametrize("case", sorted(CASES))
def test_matches_reference_on_synthetic(reference, synthetic_pdfs, case):
    changes = CASES[case]
    assert synthetic_pdfs, "no synthetic fixtures were built"
    for pdf in synthetic_pdfs:
        expected, _ = reference.convert(pdf, _reference_args(reference, **changes),
                                        log=lambda *a, **k: None)
        got = convert(pdf, Settings(ocr="off", **changes),
                      log=lambda *a, **k: None).text
        assert got == expected, f"{pdf.name} differs under {case}"


@pytest.mark.golden
@pytest.mark.corpus
def test_matches_reference_on_corpus(reference, corpus_pdfs):
    """Runs only when real documents have been placed in tests/corpus/."""
    if not corpus_pdfs:
        pytest.skip("no documents in tests/corpus/ — add the real corpus here")
    for pdf in corpus_pdfs:
        expected, _ = reference.convert(pdf, _reference_args(reference),
                                        log=lambda *a, **k: None)
        got = convert(pdf, Settings(ocr="off"), log=lambda *a, **k: None).text
        assert got == expected, f"{pdf.name} differs from the reference script"


@pytest.mark.golden
def test_stats_match_reference(reference, synthetic_pdfs):
    """The per-file report the operator reads must not drift either."""
    for pdf in synthetic_pdfs:
        _, ref_st = reference.convert(pdf, _reference_args(reference),
                                      log=lambda *a, **k: None)
        st = convert(pdf, Settings(ocr="off"), log=lambda *a, **k: None).stats
        for key in ("pages", "tables", "dropped", "twocol", "scanned",
                    "sideways", "ocr_pages"):
            assert st[key] == ref_st[key], f"{pdf.name}: {key} differs"
        # kept_ratio is deliberately no longer clamped at 1.0, so compare the
        # clamped value against the reference's.
        assert min(st["kept_ratio"], 1.0) == pytest.approx(ref_st["kept_ratio"])
