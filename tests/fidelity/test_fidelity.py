"""
The checks that make the tool trustworthy, tested from both sides.

A quality check has two ways to be useless. It can miss the failure it exists
to catch, and it can fire on clean output until people stop reading it. Both
are tested here: every clean fixture must produce no findings at all, and every
injected failure must be caught and located.

The injected failures are the real ones. Paraphrase, a dropped block, a
duplicated block and a hallucinated date are what the earlier Mistral pipeline
actually did; scrambling is what a broken font encoding does to a text layer
that reports itself as healthy.
"""

from __future__ import annotations

import pytest

from verbatim.pipeline import convert
from verbatim.qa.config import CONFIG
from verbatim.qa.fidelity import (
    align,
    check_document,
    compare_numerals,
    compare_words,
    severity_rank,
)
from verbatim.settings import Settings


def convert_fixture(pdf):
    return convert(pdf, Settings(ocr="off"), log=lambda *a, **k: None)


@pytest.fixture(scope="module")
def converted(synthetic_dir):
    return {p.stem: convert_fixture(p) for p in sorted(synthetic_dir.glob("*.pdf"))}


def findings_for(res, text=None):
    return check_document(text if text is not None else res.text, res.raw_text,
                          CONFIG, removed_on_purpose=res.dropped_text,
                          retention=res.stats["alnum_ratio"])


# --- no false positives ---------------------------------------------------

def test_clean_conversions_produce_no_findings(converted):
    """A checker that cries wolf is a checker nobody reads."""
    noisy = {name: [f.message() for f in findings_for(res)]
             for name, res in converted.items() if findings_for(res)}
    assert not noisy, f"false positives: {noisy}"


def test_dehyphenation_is_recognised_not_reported(converted):
    """The joined word looks invented and its halves look lost. They explain
    each other, and neither should reach the reviewer."""
    _, joins = compare_words(converted["hyphenated"].raw_text,
                             converted["hyphenated"].text,
                             converted["hyphenated"].dropped_text)
    assert joins == 2                       # "matter" and "consideration"
    assert not findings_for(converted["hyphenated"])


def test_dehyphenation_across_a_column_gutter_is_recognised(converted):
    """On a two-column page the text layer reads across the gutter, so the two
    halves of a broken word are never adjacent. Matching must not rely on it."""
    res = converted["two_column"]
    _, joins = compare_words(res.raw_text, res.text, res.dropped_text)
    assert joins == 1                       # "organi" + "zations"
    assert not findings_for(res)


def test_removing_running_headers_is_not_reported_as_loss(converted):
    """Six header and footer lines are deleted on purpose in simple.pdf."""
    res = converted["simple"]
    assert res.stats["dropped"] == 6
    assert not findings_for(res)
    # ...but only because they were declared. Without that, they are losses.
    blind = check_document(res.text, res.raw_text, CONFIG,
                           removed_on_purpose="", retention=None)
    assert any(f.kind == "dropped_words" for f in blind)


# --- catching the real failures -------------------------------------------

def test_paraphrase_is_caught(converted):
    """The failure the tool exists to prevent. A swapped word leaves the
    character count untouched, so only a word-level check can see it."""
    res = converted["simple"]
    damaged = res.text.replace("Decides to adopt", "Resolves to approve")
    assert damaged != res.text
    found = findings_for(res, damaged)
    invented = [f for f in found if f.kind == "invented_words"]
    assert invented, "a paraphrase went unnoticed"
    assert "resolves" in invented[0].detail and "approve" in invented[0].detail
    assert invented[0].severity == "high"


def test_paraphrase_is_located_in_the_text(converted):
    """A finding a reviewer cannot jump to is a finding they will not act on."""
    res = converted["simple"]
    damaged = res.text.replace("Decides to adopt", "Resolves to approve")
    invented = [f for f in findings_for(res, damaged) if f.kind == "invented_words"][0]
    assert invented.char_start is not None
    assert damaged[invented.char_start:invented.char_end].casefold() == "resolves"


def test_a_dropped_paragraph_is_caught(converted):
    res = converted["simple"]
    victim = "2. Requests the secretariat to prepare a synthesis report on the information submitted under paragraph 1 above."
    assert victim in res.text
    damaged = res.text.replace(victim, "")
    found = findings_for(res, damaged)
    assert any(f.kind == "dropped_words" for f in found)


def test_a_duplicated_paragraph_is_caught(converted):
    """Over-extraction: the words all exist in the source, but too many times."""
    res = converted["simple"]
    para = [l for l in res.text.splitlines() if l.startswith("3. Also requests")][0]
    damaged = res.text + "\n\n" + para + "\n"
    found = findings_for(res, damaged)
    assert any(f.kind == "invented_words" for f in found), (
        "a duplicated paragraph was not reported")


def test_a_hallucinated_date_is_caught(converted):
    """A wrong number in a treaty text is worse than a wrong word."""
    res = converted["simple"]
    damaged = res.text.replace("decision 5/CP.7", "decision 9/CP.21")
    found = compare_numerals(res.raw_text, damaged)
    assert found and found[0].kind == "invented_numbers"
    assert found[0].severity == "high"
    assert "21" in found[0].detail or "9" in found[0].detail


def test_numbers_that_are_present_are_not_reported(converted):
    for name, res in converted.items():
        assert not compare_numerals(res.raw_text, res.text), name


def test_interleaved_glyphs_are_caught(converted):
    """A broken font encoding produces confident garbage that every
    character-count check passes."""
    res = converted["simple"]
    damaged = res.text.replace("Decides", "MobIsNeDrFvaUtLio")
    found = findings_for(res, damaged)
    assert any(f.kind == "scrambled_text" for f in found)


def test_retention_below_the_floor_is_reported():
    from verbatim.qa.fidelity import check_retention
    assert check_retention(0.90, CONFIG)[0].key == "retention_low"
    assert check_retention(1.30, CONFIG)[0].key == "retention_high"
    assert not check_retention(1.0, CONFIG)


# --- alignment ------------------------------------------------------------

def test_alignment_calls_identical_text_ok(converted):
    """Alignment compares two transcriptions of the same pages, in the same
    reading order — a second recognition pass, or a hand-corrected reference."""
    for name, res in converted.items():
        a = align(res.text, res.text, CONFIG)
        assert a.verdict == "OK", f"{name}: {a.verdict} {a.similarity:.3f}"


def test_alignment_must_not_be_pointed_at_a_raw_text_layer(converted):
    """The trap this API has to be protected from.

    A two-column text layer reads straight across the gutter. Putting the
    columns into reading order is what the engine is for, so aligning the
    output against the raw layer reports the fix as damage — on this fixture,
    0.62 similarity on text that is word-for-word correct. The multiset checks
    are the ones that belong against a raw layer, and they call it clean.
    """
    res = converted["two_column"]
    misused = align(res.raw_text, res.text, CONFIG, res.dropped_text)
    assert misused.similarity < 0.8            # looks broken, and is not
    correct, _ = compare_words(res.raw_text, res.text, res.dropped_text)
    assert not correct                          # order-blind, and calls it clean


def test_alignment_names_a_missing_block(converted):
    res = converted["simple"]
    words_out = res.text.split()
    damaged = " ".join(words_out[:10] + words_out[70:])
    a = align(res.text, damaged, CONFIG)
    assert a.verdict == "MISSING_BLOCK"
    assert a.findings and a.findings[0].severity == "high"


def test_alignment_names_an_inserted_block(converted):
    res = converted["simple"]
    padding = " ".join(["the Parties shall consider the matter further"] * 12)
    a = align(res.text, res.text + " " + padding, CONFIG)
    assert a.verdict == "INSERTED_BLOCK"
    assert a.findings[0].char_start is not None


def test_alignment_names_a_rewritten_passage(converted):
    """Two recognition passes that disagree throughout, rather than at one
    place: the signature of a paraphrase rather than a dropped block."""
    res = converted["simple"]
    damaged = (res.text.replace("Decides", "Resolves").replace("adopt", "approve")
               .replace("Requests", "Asks").replace("prepare", "produce")
               .replace("consider", "examine").replace("guidelines", "rules"))
    a = align(res.text, damaged, CONFIG)
    assert a.verdict in ("REWRITTEN", "MINOR_DRIFT")
    assert a.similarity < 1.0


# --- ranking --------------------------------------------------------------

def test_severity_rank_orders_a_review_queue(converted):
    res = converted["simple"]
    assert severity_rank(findings_for(res)) == 0
    damaged = res.text.replace("Decides to adopt", "Resolves to approve")
    assert severity_rank(findings_for(res, damaged)) == 3
