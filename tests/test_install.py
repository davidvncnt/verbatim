"""
The two ways a correct installation still fails for a non-technical user:
the `verbatim` command is not on PATH, or Tesseract is installed but not on
PATH. Both are the normal case on Windows, not an edge case.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


def test_python_dash_m_verbatim_works():
    """The documented fallback when the `verbatim` command is not found."""
    out = subprocess.run([sys.executable, "-m", "verbatim", "--version"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("verbatim ")


def test_tesseract_is_found_outside_path(tmp_path, monkeypatch):
    pytesseract = pytest.importorskip("pytesseract")
    from verbatim.ocr import detect

    fake = tmp_path / "tesseract"
    fake.write_text("")
    monkeypatch.setattr(detect, "_TESSERACT_CANDIDATES", [str(fake)])
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "no-such-tesseract")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "nowhere"))
    assert detect.locate_tesseract() == str(fake)
    assert pytesseract.pytesseract.tesseract_cmd == str(fake)


def test_a_working_path_setup_is_never_overridden(monkeypatch):
    pytesseract = pytest.importorskip("pytesseract")
    import shutil

    from verbatim.ocr import detect
    if not shutil.which("tesseract"):
        pytest.skip("Tesseract is not on PATH here")
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    monkeypatch.setattr(detect, "_TESSERACT_CANDIDATES", ["/should/not/be/used"])
    assert detect.locate_tesseract() == shutil.which("tesseract")
    assert pytesseract.pytesseract.tesseract_cmd == "tesseract"
