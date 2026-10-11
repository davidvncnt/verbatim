"""
verbatim.qa.categories — the kinds of problem a reviewer can choose to look for.

Every check always runs and every finding is kept. What the reviewer chooses
is which of them are *shown*, and which count towards a file's colour in the
list. Changing the choice therefore never means checking a folder again, and
a finding hidden today is still there to be seen tomorrow.

The kinds are grouped by what a reviewer would recognise, not by how they are
detected: someone who does not care about mangled apostrophes should not have
to know that the check for them is called `garbled_characters`.

A kind that belongs to no category is always shown. A new check added later
cannot then be hidden by a choice made before it existed.
"""

from __future__ import annotations

from dataclasses import dataclass

HIGH, MEDIUM, LOW = "high", "medium", "low"


@dataclass(frozen=True)
class Category:
    id: str
    kinds: frozenset
    default: bool


CATEGORIES = (
    Category("invented", frozenset({
        "invented_text", "not_in_scan", "scan_mismatch", "invented_words",
        "inserted_block", "rewritten", "unexpected_words"}), True),
    Category("numbers", frozenset({"invented_numbers"}), True),
    Category("tables", frozenset({"unfound_table", "degenerate_table"}), True),
    Category("repeated", frozenset({"duplicated_words", "repetition_loop"}), True),
    Category("scrambled", frozenset({
        "scrambled_text", "letter_spacing", "mixed_scripts",
        "control_characters"}), True),
    Category("sideways", frozenset({"sideways_page"}), True),
    Category("scan", frozenset({
        "scan_unchecked", "ocr_confidence", "no_text_layer", "model_pages"}), True),
    Category("encoding", frozenset({"garbled_characters"}), False),
    Category("spelling", frozenset({"spelling_variants", "minor_drift"}), False),
    Category("missing", frozenset({
        "missing_from_text", "missing_block", "dropped_words", "retention"}), False),
)

BY_ID = {c.id: c for c in CATEGORIES}


def chosen(saved: dict | None) -> set:
    """Ids of the categories turned on, from what was saved, or the defaults."""
    saved = saved or {}
    return {c.id for c in CATEGORIES if bool(saved.get(c.id, c.default))}


def hidden_kinds(on: set) -> frozenset:
    """Kinds of finding that the categories turned off hide."""
    return frozenset(k for c in CATEGORIES if c.id not in on for k in c.kinds)


def visible(findings: list, hidden: frozenset) -> list:
    return [f for f in findings or [] if f.get("kind") not in hidden]


def verdict_of(findings: list, hidden: frozenset) -> str:
    """The file's verdict counting only the findings that are shown."""
    severities = {f.get("severity") for f in visible(findings, hidden)}
    if HIGH in severities:
        return "reject"
    return "review" if severities else "ok"


def verdict_for(assessment: dict, hidden: frozenset) -> str:
    """A recorded verdict, recomputed only if a finding behind it is hidden.

    A conversion's verdict can also rest on things that are not findings — a
    score against the corpus — and nothing hidden is a reason to keep it.
    """
    findings = (assessment or {}).get("findings") or []
    recorded = (assessment or {}).get("verdict")
    if recorded and not any(f.get("kind") in hidden for f in findings):
        return recorded
    return verdict_of(findings, hidden)


def verdict_from_severities(by_kind: dict, hidden: frozenset) -> str:
    """The same verdict from {kind: worst severity}, as the list keeps it."""
    severities = {s for k, s in (by_kind or {}).items() if k not in hidden}
    if HIGH in severities:
        return "reject"
    return "review" if severities else "ok"


def worst_by_kind(findings: list) -> dict:
    order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    out: dict = {}
    for f in findings or []:
        kind, sev = f.get("kind"), f.get("severity")
        if kind and (kind not in out or order.get(sev, 3) < order.get(out[kind], 3)):
            out[kind] = sev
    return out
