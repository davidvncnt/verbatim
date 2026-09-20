"""
verbatim.review_store — review data kept on this computer only.

For text files that verbatim did not produce, nothing is ever written into the
folder being reviewed. Checks and decisions live in the user's own settings
folder instead:

    <settings>/review/<folder id>/
        folder.json         which folder this is, for a human looking in here
        triage.json         quick text-only verdicts, to order the folder
        checks/<name>.json  the full check of one file, reused while unchanged
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
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .settings import config_dir


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


class LocalStore:
    def __init__(self, folder: Path, root: Path | None = None):
        self.folder = Path(folder).resolve()
        ident = hashlib.sha1(str(self.folder).encode("utf-8")).hexdigest()[:16]
        self.dir = (Path(root) if root else config_dir() / "review") / ident
        self._decisions: dict | None = None

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

    def save_check(self, txt: Path, record: dict) -> None:
        self._touch_folder_note()
        stored = dict(record)
        stored["review"] = None           # decisions live in decisions.json
        _write_json(self._check_path(Path(txt).name), stored)

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
