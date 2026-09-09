"""
Profiles set defaults; the operator overrides them.

The agreement rules are provisional (docs/open-questions.md), so the thing worth
protecting is the mechanism: a profile must never silently override a choice
someone made deliberately, because then the control in the window would lie.
"""

from __future__ import annotations

from verbatim import profiles
from verbatim.cli import _explicit_flags
from verbatim.pipeline import convert
from verbatim.settings import Settings


def test_a_profile_sets_its_defaults():
    s = profiles.apply(Settings(profile="agreements"))
    assert s.keep_sideways is True          # annex text is often rotated
    s = profiles.apply(Settings(profile="decisions"))
    assert s.keep_sideways is False


def test_a_profile_never_overrides_an_explicit_choice():
    s = Settings(profile="agreements", keep_sideways=False)
    profiles.apply(s, explicit={"keep_sideways"})
    assert s.keep_sideways is False, "the profile overrode a deliberate choice"


def test_command_line_flags_are_detected_as_explicit():
    assert "keep_headers" in _explicit_flags(["convert", "x/", "--keep-headers"])
    assert "tables" in _explicit_flags(["convert", "x/", "--tables=none"])
    assert _explicit_flags(["convert", "x/"]) == set()


def test_an_unknown_profile_falls_back_rather_than_raising():
    assert profiles.get("nonsense").name == "decisions"


def test_the_agreement_profile_declares_itself_provisional():
    """It implements a reading of the brief, not a confirmed requirement, and
    should not imply more certainty than it has."""
    assert profiles.get("agreements").provisional is True
    assert profiles.get("decisions").provisional is False


def test_structural_openers_are_recognised():
    for text in ("Article 5", "ARTICLE XII", "Annexe I", "Appendix B",
                 "Chapter 3 - Enforcement", "Préambule"):
        assert profiles.opens_structural_unit(text), text
    for text in ("The Conference of the Parties,", "Articles of this kind are",
                 "1. Decides to adopt"):
        assert not profiles.opens_structural_unit(text), text




def _convert(pdf, profile):
    return convert(pdf, Settings(ocr="off", profile=profile),
                   log=lambda *a, **k: None).text


def test_the_agreement_profile_does_not_stitch_across_an_article_break(
        synthetic_dir):
    """A sentence left open at the foot of a page must not swallow the article
    heading that opens the next one.

    The fixture is built so that the stitching rule fires: the last line has no
    terminal punctuation and the next page opens lower-case. Only the article
    rule stops it.
    """
    pdf = synthetic_dir / "article_break.pdf"
    decisions = _convert(pdf, "decisions")
    agreements = _convert(pdf, "agreements")

    def stitched(text):
        return any("beyond the limits of national jurisdiction" in line
                   and "article 5" in line.lower() for line in text.splitlines())

    assert stitched(decisions), (
        "the fixture no longer exercises the stitching rule — the two profiles "
        "cannot differ if nothing would be stitched in either")
    assert not stitched(agreements), (
        "the agreement profile stitched a paragraph across an article break")
    assert "article 5: Cooperation" in agreements


def test_both_profiles_keep_every_word(synthetic_dir):
    """Whatever the profile does with boundaries, it must not lose text."""
    from verbatim.qa.fidelity import compare_words
    pdf = synthetic_dir / "article_break.pdf"
    for profile in ("decisions", "agreements"):
        res = convert(pdf, Settings(ocr="off", profile=profile),
                      log=lambda *a, **k: None)
        findings, _ = compare_words(res.raw_text, res.text, res.dropped_text)
        assert not findings, f"{profile}: {[f.message() for f in findings]}"
