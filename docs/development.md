# Development

```bash
git clone https://github.com/davidvncnt/verbatim.git
cd verbatim
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev,all]"
.venv/bin/python -m pytest -q
```

The suite has five parts:

- `tests/golden` — output is byte-identical to the script the engine was
  refactored from (`tests/reference/pdf2txt_reference.py`).
- `tests/synthetic` — the intended layout behaviour, asserted directly, on
  generated PDFs.
- `tests/fidelity` — the quality checks, from both sides: no findings on clean
  output, and every injected failure caught and located.
- `tests/gui` — the real widgets, driven through their callbacks. Skipped when
  there is no display.
- `tests/corpus` — real documents, when placed in `tests/corpus/`
  (`pytest -m corpus`).

Lint with `.venv/bin/ruff check verbatim tests`.

See also `docs/calibration.md` for tuning the risk score and
`docs/open-questions.md` for known limitations.
