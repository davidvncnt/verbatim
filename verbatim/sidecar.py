"""
verbatim.sidecar — the record that travels with each converted document.

The .txt stays exactly as clean as it always was: nothing is written into it,
no markers, no annotations. Everything the tool knows about how that text came
to exist lives beside it in `NAME.verbatim.json`.

That file is what makes review fast. It carries, for every passage, the page it
came from, the rectangle on that page, and whether the words were extracted
from a text layer or produced by a recogniser — so the reviewer's window can
put a suspect paragraph next to the part of the page it came from instead of
asking a person to find it.

It is also the audit trail. Six months later, "where did this sentence come
from?" has an answer that does not depend on anyone's memory.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .settings import settings_to_dict

SUFFIX = ".verbatim.json"


def sidecar_path(txt_path: Path) -> Path:
    """`decision.txt` -> `decision.verbatim.json`, beside it."""
    txt_path = Path(txt_path)
    return txt_path.with_name(txt_path.stem + SUFFIX)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def locate_findings(findings: list, blocks: list) -> None:
    """Give each finding the page it falls on, from the block span map.

    A finding knows where it is in the .txt; the spans know which page each
    stretch of .txt came from. Joining the two is what turns "6 invented words"
    into "6 invented words, page 4, this rectangle".
    """
    spans = sorted((s for b in blocks for s in b.spans),
                   key=lambda s: s.char_start)
    if not spans:
        return
    for f in findings:
        if f.page is not None or f.char_start is None:
            continue
        for s in spans:
            if s.char_start <= f.char_start < s.char_end:
                f.page = s.page
                break
        else:
            earlier = [s for s in spans if s.char_start <= f.char_start]
            if earlier:
                f.page = earlier[-1].page


def build(result, assessment, *, pdf_path: Path, txt_path: Path,
          settings) -> dict:
    """Assemble the record. Pure: writing it is a separate step."""
    locate_findings(assessment.findings, result.blocks)
    return {
        "verbatim_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_pdf": Path(pdf_path).name,
        # Absolute at conversion time. The reviewer needs to open the actual
        # page image; the name alone is not enough, and folders get moved, so
        # `find_source` falls back to looking beside the .txt.
        "source_path": str(Path(pdf_path).resolve()),
        "source_sha256": _sha256(Path(pdf_path)),
        "text_file": Path(txt_path).name,
        "settings": settings_to_dict(settings),
        "stats": {k: v for k, v in result.stats.items() if not k.startswith("_")},
        "assessment": assessment.to_dict(),
        "pages": [p.to_dict() for p in result.pages],
        # One entry per line of the source, in output order. This is what the
        # reviewer scrolls with, so it is worth its size.
        "spans": [s.to_dict() for b in result.blocks for s in b.spans
                  if s.char_end > s.char_start],
        # Filled in by a person, in the review window. Never by the tool.
        "review": None,
    }


def write(record: dict, txt_path: Path) -> Path:
    path = sidecar_path(txt_path)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return path


def find_source(txt_path: Path, record: dict | None = None) -> Path | None:
    """Locate the PDF a .txt came from.

    Tries where it was, then beside the .txt, then one folder up — the three
    places it is when a team has moved things around. Returns None rather than
    guessing at a same-named file elsewhere on the disk.
    """
    record = record if record is not None else read(txt_path)
    if not record:
        return None
    name = record.get("source_pdf") or (Path(txt_path).stem + ".pdf")
    candidates = [Path(record["source_path"])] if record.get("source_path") else []
    txt_path = Path(txt_path)
    candidates += [txt_path.with_name(name),
                   txt_path.parent.parent / name,
                   txt_path.parent / "pdf" / name]
    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def read(txt_path: Path) -> dict | None:
    """The record for one .txt, or None when it has not been converted here."""
    path = sidecar_path(txt_path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def record_review(txt_path: Path, *, verdict: str, reviewer: str,
                  note: str = "") -> dict | None:
    """Write a person's decision into the record.

    Kept distinct from the tool's own assessment: one is a measurement, the
    other is a judgement, and conflating them would make the audit trail
    useless. Over time these are also the labelled examples the risk weights
    need in order to be calibrated rather than guessed.
    """
    record = read(txt_path)
    if record is None:
        return None
    record["review"] = {
        "verdict": verdict,
        "reviewer": reviewer,
        "note": note,
        "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool_said": record.get("assessment", {}).get("verdict"),
    }
    write(record, txt_path)
    return record
