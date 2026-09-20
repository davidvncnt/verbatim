"""
Words that do not belong in this material.

A model asked to read an unreadable scan writes something plausible; what gives
it away is vocabulary. The expected vocabulary is learned from text the team
already accepts, never guessed, and the check is tuned so that ordinary rare
words and proper nouns do not set it off — a check people stop reading is worse
than no check.
"""

from __future__ import annotations

import pytest

from verbatim.qa import lexicon
from verbatim.qa.external import lexical_findings

TREATY = ("The Conference of the Parties, recalling decision 5/CP.7 on the "
          "guidelines for the preparation of national communications, decides "
          "to adopt the annexed guidelines and requests the secretariat to "
          "prepare a synthesis report on their implementation. The delegation "
          "thanked the working group for the survey of stocks carried out "
          "under the wooden vessel monitoring scheme. ")


@pytest.fixture
def vocabulary(tmp_path):
    folder = tmp_path / "accepted"
    folder.mkdir()
    for i in range(6):
        (folder / f"decision_{i}.txt").write_text(
            TREATY + f" Annex {i} concerns monitoring and compliance.",
            encoding="utf-8")
    out = lexicon.build(folder, out=tmp_path / "vocabulary.txt",
                        log=lambda *a, **k: None)
    return lexicon.load(out)


def test_a_document_of_the_same_kind_raises_nothing(vocabulary):
    assert lexicon.suspicious_words(TREATY, vocabulary) == []


def test_words_from_another_world_are_caught(vocabulary):
    text = TREATY + " The thief hid the stolen pizza inside a wooden hideout."
    found = lexicon.suspicious_words(text, vocabulary)
    assert "thief" in found and "pizza" in found and "hideout" in found


def test_proper_nouns_are_left_alone(vocabulary):
    """Most of what a corpus has never seen is a name: of a person, a vessel,
    a place or a species."""
    text = TREATY + (" The delegation of Chukotka thanked Mr Rüdiger Strempel "
                     "for the survey of Dissostichus mawsoni near Haerbaling.")
    assert lexicon.suspicious_words(text, vocabulary) == []


def test_one_odd_word_is_not_a_finding(vocabulary):
    """One unexpected word is an unusual document; several are a pattern."""
    assert lexical_findings(TREATY + " A quinquennale review.", vocabulary) == []


def test_a_finding_says_which_words_and_where(vocabulary):
    text = TREATY + " The thief hid the pizza in a hideout."
    found = lexical_findings(text, vocabulary)
    assert len(found) == 1
    assert found[0].severity == "medium", "this is a reason to look, not a verdict"
    assert "thief" in found[0].message()
    assert text[found[0].char_start:found[0].char_end] == "thief"


def test_nothing_happens_without_a_vocabulary():
    """Every installation starts without one, and must behave as before."""
    assert lexicon.suspicious_words("The thief took the pizza.", set()) == []
    assert lexical_findings("The thief took the pizza.", set()) == []


def test_building_reports_what_it_learned(tmp_path):
    folder = tmp_path / "txt"
    folder.mkdir()
    (folder / "a.txt").write_text("convention protocol secretariat", encoding="utf-8")
    (folder / "b.txt").write_text("convention annex compliance", encoding="utf-8")
    out = lexicon.build(folder, out=tmp_path / "v.txt", log=lambda *a, **k: None)
    words = lexicon.load(out)
    assert {"convention", "protocol", "annex", "compliance"} <= words


def test_a_word_must_be_common_enough_when_asked(tmp_path):
    folder = tmp_path / "txt"
    folder.mkdir()
    (folder / "a.txt").write_text("convention protocol", encoding="utf-8")
    (folder / "b.txt").write_text("convention annex", encoding="utf-8")
    out = lexicon.build(folder, min_documents=2, out=tmp_path / "v.txt",
                        log=lambda *a, **k: None)
    words = lexicon.load(out)
    assert "convention" in words and "protocol" not in words
