"""
verbatim.review_store — review data kept on this computer only.

For text files that verbatim did not produce, nothing is ever written into the
folder being reviewed. Checks and decisions live in the user's own settings
folder instead:

    <settings>/review/<folder id>/
        folder.json         which folder this is, for a human looking in here
        triage.json         quick text-only verdicts, to order the folder
        checks/<name>.json  the full check of one file, reused while unchanged
        checked.json        one line per full check, to show a folder's results
                            as soon as it opens without reading every check
        decisions.json      what the reviewer decided, and who, and when

Decisions are kept apart from checks on purpose: a check is a measurement that
can be thrown away and redone at any time, a decision is a person's judgement
and must survive that. Every write goes through a temporary file and a rename,
so a crash never leaves half a JSON file behind.

The cost of keeping this local, chosen deliberately: two reviewers do not see
each other's decisions.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, settings


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _revision() -> int:
    from .qa.external import CHECK_REVISION
    return CHECK_REVISION


def text_stamp(path: Path) -> str | None:
    """Size and modification time: cheap enough to test 21,000 files."""
    try:
        st = Path(path).stat()
    except OSError:
        return None
    # The revision is part of the stamp, so a sort made by older checks is
    # redone rather than trusted.
    return f"{st.st_size}:{st.st_mtime_ns}:r{_revision()}"


def summarise(txt: Path, record: dict) -> dict:
    """The little of a full check that the list of files needs."""
    findings = record.get("assessment", {}).get("findings") or []
    return {
        "stamp": text_stamp(txt),
        "verbatim_version": record.get("verbatim_version"),
        "mode": record.get("mode"),
        "ocr": bool(record.get("ocr")),
        "crosscheck_conf": record.get("crosscheck_conf"),
        "source_path": record.get("source_path"),
        "pdf_stamp": record.get("pdf_stamp"),
        "verdict": record.get("assessment", {}).get("verdict", "unknown"),
        "kinds": sorted({f.get("kind") for f in findings if f.get("kind")}),
        "compared": record.get("reference") not in (None, "none"),
    }


class LocalStore:
    def __init__(self, folder: Path, root: Path | None = None):
        self.folder = Path(folder).resolve()
        ident = hashlib.sha1(str(self.folder).encode("utf-8")).hexdigest()[:16]
        # Looked up on each use rather than imported, so that the test suite's
        # temporary settings folder is the one used.
        self.dir = (Path(root) if root else settings.config_dir() / "review") / ident
        self._decisions: dict | None = None
        # The index of full checks is written from the checking thread and
        # read from the window, and two writers would race on the same file.
        self._lock = threading.Lock()
        self._index: dict | None = None
        self._index_dirty = False

    def _touch_folder_note(self) -> None:
        note = self.dir / "folder.json"
        if not note.exists():
            _write_json(note, {"folder": str(self.folder)})

    # -- triage ---------------------------------------------------------------

    def triage(self) -> dict:
        return _read_json(self.dir / "triage.json", {})

    def save_triage(self, data: dict) -> None:
        self._touch_folder_note()
        _write_json(self.dir / "triage.json", data)

    # -- full checks ------------------------------------------------------------

    def _check_path(self, name: str) -> Path:
        return self.dir / "checks" / f"{name}.json"

    def cached_check(self, txt: Path, *, text_sha256: str, pdf_path: Path | None,
                     pdf_stamp: str | None, mode: str, ocr: bool,
                     crosscheck_conf: float | None = None) -> dict | None:
        """The saved check, if nothing it depended on has changed since."""
        record = _read_json(self._check_path(Path(txt).name), None)
        if not record:
            return None
        same = (record.get("text_sha256") == text_sha256
                and record.get("mode") == mode
                and bool(record.get("ocr")) == bool(ocr)
                and record.get("verbatim_version") == __version__
                and record.get("check_revision") == _revision()
                and record.get("source_path") == (str(Path(pdf_path).resolve())
                                                  if pdf_path else None)
                and record.get("pdf_stamp") == pdf_stamp
                and (crosscheck_conf is None
                     or record.get("crosscheck_conf") == round(float(crosscheck_conf), 4)))
        if not same:
            return None
        record["review"] = self.decision(Path(txt).name)
        return record

    def any_check(self, name: str) -> dict | None:
        """The saved check whether or not it is still current.

        For the summary, which reports what was decided and why rather than
        re-deciding anything: a check made before the file was edited is still
        the check the reviewer was looking at when they decided.
        """
        return _read_json(self._check_path(name), None)

    def save_check(self, txt: Path, record: dict, *, flush: bool = True) -> None:
        """Keep a check. `flush=False` defers rewriting the index, for a run
        over many files that calls `flush_index()` itself every so often."""
        self._touch_folder_note()
        stored = dict(record)
        stored["review"] = None           # decisions live in decisions.json
        _write_json(self._check_path(Path(txt).name), stored)
        self.note_check(txt, record)
        if flush:
            self.flush_index()

    def note_check(self, txt: Path, record: dict) -> None:
        """Add a check to the index without saving the check itself — for a
        check that was already saved and has just been found still valid."""
        line = summarise(txt, record)
        with self._lock:
            self._load_index()[Path(txt).name] = line
            self._index_dirty = True

    def _load_index(self) -> dict:
        if self._index is None:
            self._index = _read_json(self.dir / "checked.json", {})
        return self._index

    def checked_names(self) -> set:
        with self._lock:
            return set(self._load_index())

    def flush_index(self) -> None:
        with self._lock:
            if not self._index_dirty:
                return
            _write_json(self.dir / "checked.json", self._index)
            self._index_dirty = False

    def checked(self, txt: Path, *, pdf_path: Path | None, pdf_stamp: str | None,
                mode: str, ocr: bool, crosscheck_conf: float) -> dict | None:
        """What the last full check of this file found, if it still applies.

        Tested by size and date rather than by reading the file, so that a
        folder of 21,000 files shows its results the moment it opens. Opening
        a file still goes through `cached_check`, which compares contents.
        """
        with self._lock:
            line = self._load_index().get(Path(txt).name)
        if not line:
            return None
        same = (line.get("stamp") == text_stamp(txt)
                and line.get("verbatim_version") == __version__
                and line.get("mode") == mode
                and line.get("ocr") == bool(ocr)
                and line.get("crosscheck_conf") == round(float(crosscheck_conf), 4)
                and line.get("source_path") == (str(Path(pdf_path).resolve())
                                                if pdf_path else None)
                and line.get("pdf_stamp") == pdf_stamp)
        return line if same else None

    # -- decisions --------------------------------------------------------------

    def decisions(self) -> dict:
        if self._decisions is None:
            self._decisions = _read_json(self.dir / "decisions.json", {})
        return self._decisions

    def decision(self, name: str) -> dict | None:
        return self.decisions().get(name)

    def record_decision(self, name: str, *, verdict: str, reviewer: str,
                        note: str = "", tool_said: str | None = None) -> dict:
        entry = {"verdict": verdict, "reviewer": reviewer, "note": note,
                 "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "tool_said": tool_said}
        data = dict(self.decisions())
        data[name] = entry
        self._touch_folder_note()
        _write_json(self.dir / "decisions.json", data)
        self._decisions = data
        return entry
