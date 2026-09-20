"""
What came of a reviewed folder.

Going through hundreds of files leaves the conclusions scattered across as many
records. These tests cover the one place that gathers them: every file appears,
decided or not, whoever made it, and a decision is never invented for a file
nobody judged.
"""

from __future__ import annotations

import csv

from verbatim import sidecar
from verbatim.pipeline import collect_targets, run_batch
from verbatim.review_store import LocalStore
from verbatim.settings import Settings
from verbatim.summary import collect, counts, write_csv


def converted_folder(synthetic_dir, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    args = Settings(ocr="off")
    args.out = tmp_path
    run_batch(collect_targets([synthetic_dir], False), args, log=lambda *a, **k: None)
    return tmp_path


def test_every_file_appears_decided_or_not(synthetic_dir, tmp_path):
    folder = converted_folder(synthetic_dir, tmp_path)
    sidecar.record_review(folder / "simple.txt", verdict="rejected",
                          reviewer="RA1", note="invented paragraph p.2")
    rows = collect(folder)
    assert len(rows) == len(list(folder.glob("*.txt")))
    simple = next(r for r in rows if r["file"] == "simple.txt")
    assert simple["decision"] == "rejected"
    assert simple["reviewer"] == "RA1"
    assert simple["note"] == "invented paragraph p.2"
    assert simple["checked_against"] == "text_layer"
    assert all(r["decision"] == "" for r in rows if r["file"] != "simple.txt")


def test_what_needs_attention_comes_first(synthetic_dir, tmp_path):
    folder = converted_folder(synthetic_dir, tmp_path)
    sidecar.record_review(folder / "simple.txt", verdict="accepted", reviewer="RA1")
    sidecar.record_review(folder / "accents.txt", verdict="rejected", reviewer="RA1")
    rows = collect(folder)
    assert rows[0]["file"] == "accents.txt"


def test_decisions_made_on_other_tools_files_are_included(tmp_path):
    """Those live on this computer, not beside the file, and must still count."""
    folder = tmp_path / "corpus"
    folder.mkdir()
    (folder / "legacy.txt").write_text("converted elsewhere", encoding="utf-8")
    store = LocalStore(folder, root=tmp_path / "prefs")
    store.record_decision("legacy.txt", verdict="needs_work", reviewer="RA2",
                          note="check page 4", tool_said="review")
    rows = collect(folder, store)
    assert rows[0]["decision"] == "needs_work"
    assert rows[0]["made_by"] == "other"
    assert counts(rows)["by_decision"]["needs_work"] == 1


def test_counts_add_up(synthetic_dir, tmp_path):
    folder = converted_folder(synthetic_dir, tmp_path)
    sidecar.record_review(folder / "simple.txt", verdict="accepted", reviewer="RA1")
    totals = counts(collect(folder))
    assert totals["decided"] + totals["undecided"] == totals["files"]
    assert sum(totals["by_verdict"].values()) == totals["files"]


def test_disagreement_between_person_and_tool_is_counted(synthetic_dir, tmp_path):
    """The number worth looking at: where a human overruled the tool."""
    folder = converted_folder(synthetic_dir, tmp_path)
    sidecar.record_review(folder / "simple.txt", verdict="rejected", reviewer="RA1")
    assert counts(collect(folder))["overruled"] == 1
    sidecar.record_review(folder / "simple.txt", verdict="accepted", reviewer="RA1")
    assert counts(collect(folder))["overruled"] == 0


def test_the_csv_opens_as_a_spreadsheet(synthetic_dir, tmp_path):
    folder = converted_folder(synthetic_dir, tmp_path / "txt")
    sidecar.record_review(folder / "simple.txt", verdict="accepted", reviewer="RA1")
    out = write_csv(collect(folder), tmp_path / "summary.csv")
    with open(out, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["file"] and "decision" in rows[0]
    assert any(r["decision"] == "accepted" for r in rows)
    # utf-8-sig, so Excel shows accented file names correctly
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")


def test_reading_a_summary_changes_nothing(synthetic_dir, tmp_path):
    folder = converted_folder(synthetic_dir, tmp_path)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    collect(folder)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
