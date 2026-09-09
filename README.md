# verbatim

Faithful PDF → plain text conversion for international environmental agreement
texts.

**Every word in the output comes from the source document.** No paraphrase, no
summary, no silent correction of what looks like a typo, no filled-in gap. PDFs
that contain a text layer are extracted deterministically and never routed
through a language model. A model is used only where there is genuinely no text
to extract, and what it produces is marked as *recognised* rather than
*extracted*, so nothing downstream can mistake the two.

That rule is not a preference. An earlier pipeline built on Mistral OCR
produced hallucinated text — content that was not in the source — which is
disqualifying for a database of treaty texts.

## What is different from a converter

A converter that is merely accurate is not enough, because nobody can tell
whether it was accurate. A paraphrase reads perfectly well, and character-count
checks are blind to it: swap one word for another of the same length and
"100% of characters kept" is still true.

So every conversion is checked as it happens, and every problem is **located**:

| Check | Catches |
| --- | --- |
| Word provenance | A word in the output that is not in the source. Paraphrase, invention. |
| Completeness | A word in the source that never reached the output, discounting what was removed on purpose. |
| Numerals | A number, date or article reference that is in the output and not the source. |
| Retention | Text lost, or more text out than went in. |
| Repetition | A recogniser stuck in a loop. |
| Interleaving | A broken font encoding weaving two lines together (`MobIsNeDrFvaUtLio n`). |
| Two-pass agreement | For scanned pages, where no text layer exists to compare against. |

Each finding carries a page, a rectangle on that page, and a character range in
the `.txt`. The review window uses them to put the suspect paragraph next to the
part of the page it came from, so nobody has to read a fifty-page document to
find a six-word problem.

## Install

```bash
pip install verbatim
```

For scanned PDFs, also install Tesseract:

```bash
brew install tesseract tesseract-lang        # macOS
sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-spa   # Linux
```

On Windows, use the installer at
https://github.com/UB-Mannheim/tesseract/wiki, then `pip install pytesseract`.

## Use

```bash
verbatim                       # opens the window (English/French)
verbatim convert pdfs/ -o txt/ # a folder
verbatim review txt/           # opens the review window on a folder
verbatim check txt/            # re-list what needs attention
verbatim audit txt/            # profile a corpus and build the baseline
```

The window has two tabs. **Convert** picks two folders and runs. **Review**
shows the flagged files worst-first, with the page image beside the text.

## What each conversion writes

Two files. `NAME.txt` is the clean text — nothing is written into it, no
markers, no annotations. `NAME.verbatim.json` beside it holds everything the
tool knows: the settings used, the checks and their findings, the source PDF's
SHA-256, and a span map giving every passage its page, rectangle and character
range. Six months later, "where did this sentence come from?" has an answer.

## Output format

One paragraph per line, one blank line between paragraphs, no page numbers or
running headers, tables as aligned fixed-width columns, words de-hyphenated
across line breaks, paragraphs stitched across page breaks, UTF-8 without BOM.
`--page-marks` adds `[page N]` markers for citation.

Two profiles: `decisions` (COP decisions) and `agreements` (texts for
publication). **The agreement profile is provisional** — see
[docs/open-questions.md](docs/open-questions.md).

## The baseline

Relative quality checks need to know what normal looks like for your corpus.
`verbatim audit` measures every `.txt` in a folder and writes
`verbatim_baseline.json` plus a ranked triage sheet. Without a baseline, only
the absolute checks can fire, and the window says so rather than letting the
numbers look complete.

The weights behind the ranking are a starting guess until they are calibrated
against hand-labelled files — see [docs/calibration.md](docs/calibration.md).
The review window's accept/reject log is designed to produce those labels as a
by-product of normal work.

## Development

```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev,all]"
.venv/bin/python -m pytest -q
```

The suite has four parts. `tests/golden` asserts the output is byte-identical to
the script this was refactored from — that is what made the refactor safe.
`tests/synthetic` asserts the intended behaviour directly, so a shared
regression in both is still caught. `tests/fidelity` tests the quality checks
from both sides: no false positives on clean output, and every injected failure
caught. `tests/gui` drives the real widgets.

Put real documents in `tests/corpus/` and `pytest -m corpus` runs against them.
See [tests/corpus/README.md](tests/corpus/README.md) for what is worth having
there.

## Licence

MIT. pdfplumber (MIT) is used rather than PyMuPDF (AGPL) throughout, including
for the PDF profiler and the review window's page rendering.
