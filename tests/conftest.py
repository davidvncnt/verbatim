"""Shared fixtures: the synthetic corpus, and a loader for the frozen script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
sys.path.insert(0, str(TESTS / "synthetic"))


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory):
    """Build the synthetic PDFs once per test session."""
    from fixtures import build_all
    out = tmp_path_factory.mktemp("synthetic")
    build_all(out)
    return out


@pytest.fixture(scope="session")
def synthetic_pdfs(synthetic_dir):
    return sorted(synthetic_dir.glob("*.pdf"))


@pytest.fixture(scope="session")
def corpus_pdfs():
    """Real documents, when the team has supplied them. Empty is not a failure:
    the synthetic set still runs, it just proves less."""
    return sorted((TESTS / "corpus").glob("**/*.pdf"))


@pytest.fixture(scope="session")
def reference():
    """The frozen pdf2txt script, loaded as a module.

    It is the definition of 'no behaviour change' for the port. Registering it
    in sys.modules before execution is required: its dataclasses look their own
    module up by name while being constructed.
    """
    path = TESTS / "reference" / "pdf2txt_reference.py"
    spec = importlib.util.spec_from_file_location("pdf2txt_reference", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pdf2txt_reference"] = mod
    spec.loader.exec_module(mod)
    return mod
