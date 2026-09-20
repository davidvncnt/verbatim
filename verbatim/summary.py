"""
verbatim.summary — what came of a folder that has been reviewed.

Going through several hundred files one by one leaves no trace a person can
read: the decisions are in a record beside each file, or in this computer's own
store, and answering "what did we conclude?" should not mean opening them one
at a time. This gathers one row per file — what the tool found, what the
reviewer decided, who decided it — for the summary window and for a CSV that
can go into a spreadsheet or an email.

It only reads. Nothing here re-checks a file or changes a decision.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from . import sidecar
from .review_store import LocalStore

FIELDS = ["file", "made_by", "tool_verdict", "checked_against", "problems",
          "decision", "reviewer", "note", "decided_at"]

# Order a summary reads in: what needs attention first.
DECISION_ORDER = {"rejected": 0, "needs_work": 1, "accepted": 2, "": 3}
VERDICT_ORDER = {"reject": 0, "review": 1, "unknown": 2, "ok": 3, "": 4}


def _checked_against(record: dict) -> str:
    """Against what the text was compared, in one word."""
    if record.get("reference"):
        return record["reference"]
    sources = {p.get("source") for p in record.get("pages") or []}
    if "recognised_model" in sources:
        return "model"
    if "recognised_tesseract" in sources:
        return "recognised"
    return "text_layer" if sources else "none"


def collect(folder: Path, store: LocalStore | None = None) -> list:
    """One row per .txt file in a folder."""
    folder = Path(folder)
    store = store or LocalStore(folder)
    triage = store.triage()
    rows = []
    for txt in sorted(folder.glob("*.txt")):
        record = sidecar.read(txt)
        made_by = "verbatim" if record else "other"
        decision = (record or {}).get("review")
        if record is None:
            record = store.any_check(txt.name) or {}
            decision = store.decision(txt.name)
        assessment = record.get("assessment", {})
        problems = sorted({f.get("kind", "") for f in assessment.get("findings", [])})
        verdict = assessment.get("verdict", "")
        if not record:
            known = triage.get(txt.name) or {}
            verdict = known.get("verdict", "")
            problems = sorted(known.get("kinds", []))
        rows.append({
            "file": txt.name,
            "made_by": made_by,
            "tool_verdict": verdict,
            "checked_against": _checked_against(record) if record else "",
            "problems": ", ".join(p for p in problems if p),
            "decision": (decision or {}).get("verdict", ""),
            "reviewer": (decision or {}).get("reviewer", ""),
            "note": (decision or {}).get("note", ""),
            "decided_at": (decision or {}).get("at_utc", ""),
        })
    rows.sort(key=lambda r: (DECISION_ORDER.get(r["decision"], 3),
                             VERDICT_ORDER.get(r["tool_verdict"], 4), r["file"]))
    return rows


def counts(rows: list) -> dict:
    """The numbers a summary leads with."""
    decided = [r for r in rows if r["decision"]]
    return {
        "files": len(rows),
        "decided": len(decided),
        "undecided": len(rows) - len(decided),
        "by_decision": Counter(r["decision"] for r in decided),
        "by_verdict": Counter(r["tool_verdict"] or "unknown" for r in rows),
        "by_problem": Counter(k for r in rows for k in r["problems"].split(", ") if k),
        "reviewers": Counter(r["reviewer"] for r in decided if r["reviewer"]),
        # Where the tool saw nothing and a person disagreed, or the reverse.
        "overruled": sum(1 for r in decided
                         if (r["tool_verdict"] == "ok") != (r["decision"] == "accepted")),
    }


def write_csv(rows: list, path: Path) -> Path:
    path = Path(path)
    # utf-8-sig so Excel opens accented file names correctly.
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path
