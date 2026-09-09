"""
A French window that reports its results in English is not a bilingual tool.

These tests fail the build on a missing translation rather than letting one
reach a research assistant as a stray English sentence.
"""

from __future__ import annotations

import re

import pytest

from verbatim import i18n
from verbatim.qa import fidelity


def test_both_catalogues_hold_the_same_keys():
    assert i18n.check_catalogues() == []


def test_every_finding_key_is_translated():
    """The keys the quality layer can actually emit, found in its own source
    rather than listed by hand, so a new finding cannot be forgotten."""
    src = (fidelity.__file__.replace(".pyc", ".py"))
    emitted = set(re.findall(r'key="([a-z_]+)"', open(src, encoding="utf-8").read()))
    assert emitted, "no finding keys found — has the pattern changed?"
    for key in emitted:
        for lang in i18n.CATALOGUES:
            assert key in i18n.CATALOGUES[lang], f"{lang} is missing {key!r}"


@pytest.mark.parametrize("lang", sorted(i18n.CATALOGUES))
def test_every_string_formats_without_error(lang):
    """A template whose placeholders do not match its callers would render as
    a raw brace string in the window."""
    sample = {"n": 3, "sample": "a, b", "pct": 0.87, "pages": 4, "tables": 1,
              "dropped": 2, "done": 5, "total": 9, "name": "f.txt", "path": "/tmp",
              "note": "x", "error": "boom", "who": "RA1", "verdict": "ok",
              "page": 2, "version": "5.4.0", "flagged": 2}
    for key in i18n.CATALOGUES[lang]:
        out = i18n.t(key, lang, **sample)
        assert "{" not in out, f"{lang}:{key} left an unfilled placeholder: {out}"


def test_a_finding_speaks_both_languages():
    f = fidelity.Finding(kind="invented_words", severity=fidelity.HIGH,
                         key="invented_words", params={"n": 2, "sample": "x, y"})
    assert "do not appear in the PDF" in f.message("en")
    assert "ne figurent pas dans le PDF" in f.message("fr")
    d = f.to_dict()
    assert d["message_en"] and d["message_fr"] and d["message_en"] != d["message_fr"]


def test_an_unknown_key_does_not_crash_a_conversion():
    """A missing string must be a visible blemish, never an exception thrown
    in the middle of a batch."""
    assert i18n.t("no.such.key") == "no.such.key"


def test_language_choice_is_remembered(tmp_path, monkeypatch):
    monkeypatch.setattr("verbatim.settings.config_dir", lambda: tmp_path)
    i18n.set_language("fr")
    assert i18n.load_language() == "fr"
    i18n.set_language("en")
    assert i18n.load_language() == "en"


def test_an_unknown_language_falls_back_rather_than_raising(tmp_path, monkeypatch):
    """A corrupt preferences file must not stop the tool from opening."""
    monkeypatch.setattr("verbatim.settings.config_dir", lambda: tmp_path)
    assert i18n.set_language("klingon") == "en"
