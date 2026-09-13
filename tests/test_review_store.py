"""
Review data for files verbatim did not make stays on this computer.

What these protect: the reviewed folder is never written to; a decision
survives the file being checked again; a check is thrown away when the text,
the PDF or the options behind it change.
"""

from __future__ import annotations

from verbatim.review_store import LocalStore


def _record(**over):
    base = {"text_sha256": "abc", "mode": "full", "ocr": True,
            "verbatim_version": __import__("verbatim").__version__,
            "check_revision": __import__("verbatim.qa.external",
                                         fromlist=["CHECK_REVISION"]).CHECK_REVISION,
            "source_path": None, "pdf_stamp": None,
            "assessment": {"verdict": "ok", "findings": []}, "review": None}
    base.update(over)
    return base


def _args(**over):
    base = {"text_sha256": "abc", "pdf_path": None, "pdf_stamp": None,
            "mode": "full", "ocr": True}
    base.update(over)
    return base


def test_nothing_is_written_into_the_reviewed_folder(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    txt = corpus / "20001_rules_2006.txt"
    txt.write_text("text", encoding="utf-8")
    before = sorted(p.name for p in corpus.iterdir())

    store = LocalStore(corpus, root=tmp_path / "prefs")
    store.save_triage({txt.name: {"verdict": "ok"}})
    store.save_check(txt, _record())
    store.record_decision(txt.name, verdict="accepted", reviewer="RA1")

    assert sorted(p.name for p in corpus.iterdir()) == before
    assert any((tmp_path / "prefs").rglob("decisions.json"))


def test_a_check_is_reused_while_nothing_changed(tmp_path):
    store = LocalStore(tmp_path, root=tmp_path / "prefs")
    txt = tmp_path / "a.txt"
    store.save_check(txt, _record())
    assert store.cached_check(txt, **_args()) is not None


def test_a_check_is_discarded_when_its_inputs_change(tmp_path):
    store = LocalStore(tmp_path, root=tmp_path / "prefs")
    txt = tmp_path / "a.txt"
    store.save_check(txt, _record())
    assert store.cached_check(txt, **_args(text_sha256="edited")) is None
    assert store.cached_check(txt, **_args(mode="text_only")) is None
    assert store.cached_check(txt, **_args(ocr=False)) is None
    assert store.cached_check(txt, **_args(pdf_stamp="1:2")) is None


def test_a_decision_survives_the_file_being_checked_again(tmp_path):
    store = LocalStore(tmp_path, root=tmp_path / "prefs")
    txt = tmp_path / "a.txt"
    store.save_check(txt, _record())
    store.record_decision(txt.name, verdict="rejected", reviewer="RA1",
                          note="invented paragraph p.4", tool_said="reject")
    store.save_check(txt, _record(assessment={"verdict": "reject", "findings": []}))
    again = LocalStore(tmp_path, root=tmp_path / "prefs")
    record = again.cached_check(txt, **_args())
    assert record["review"]["verdict"] == "rejected"
    assert record["review"]["note"] == "invented paragraph p.4"


def test_different_folders_do_not_share_decisions(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    LocalStore(tmp_path / "one", root=tmp_path / "prefs").record_decision(
        "same_name.txt", verdict="accepted", reviewer="RA1")
    assert LocalStore(tmp_path / "two", root=tmp_path / "prefs").decision(
        "same_name.txt") is None


def test_a_check_from_older_checking_logic_is_redone(tmp_path, monkeypatch):
    from verbatim.qa import external
    store = LocalStore(tmp_path, root=tmp_path / "prefs")
    txt = tmp_path / "a.txt"
    store.save_check(txt, _record())
    monkeypatch.setattr(external, "CHECK_REVISION", external.CHECK_REVISION + 1)
    assert store.cached_check(txt, **_args()) is None
