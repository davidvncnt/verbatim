# PDF → TXT conversion for IEA texts — project brief

Brief for a development session on a tool that converts PDFs of international
environmental agreement (IEA) material into clean, faithful plain-text files.

Two related use cases share one engine:

1. **Research use (mine).** Batch-converting IEA documents to readable TXT so
   they can be searched, read and quoted. Tolerant of small imperfections.
2. **Agreement importation (colleagues').** Turning IEA agreement texts into
   properly formatted TXT for publication on the IEADB website. Published
   output, so completeness and fidelity matter more, and the formatting rules
   are stricter. **Their exact requirements are not captured here — see
   "Open questions" below and settle them before building.**

A working single-file script already exists (`pdf2txt.py`). It covers use
case 1 and is a reasonable base for use case 2. Extending it is likely
cheaper than restarting; the sections below record what it does, what was
measured, and what is still unsolved.

---

## 1. The overriding requirement: fidelity

**Every word in the output must come from the source document.** No
paraphrase, no summarisation, no silent "correction" of what looks like a
typo, no filled-in gaps.

This is not a stylistic preference. An earlier attempt at this problem used
Mistral OCR 3 and produced **hallucinated text** — content that was not in
the source document — which is disqualifying for a database of treaty texts.
Any design that routes already-extractable text through a language model
reintroduces that risk.

The rule that follows from this:

- PDFs that contain a text layer are **extracted deterministically**, never
  passed through a model.
- A model or OCR engine is used **only** where there is genuinely no text to
  extract (a scanned image).
- Where a model is used, its output must be **verifiable** against the source
  and flagged as model-derived.

### Anti-hallucination checks that should be part of the tool

These are cheap and catch the failure class directly:

- **Word-bag diff.** Every word in the output must appear in the raw text
  layer. Any word that does not is either a de-hyphenation join (legitimate,
  and identifiable) or an invention (a bug). The current script scores 0
  invented words on a 51-page test document.
- **Character retention.** Compare non-whitespace character count of the
  output against the raw text layer, adding back anything deliberately
  removed (headers, page numbers). Should be 100%; below 95% warrants
  inspection.
- For OCR'd pages neither check is possible against a text layer, so instead:
  report **average recognition confidence per file**, and flag anything below
  a threshold for human review.

A useful principle: the tool should always be able to answer "where did this
sentence come from?" — and for OCR'd content, say plainly that it was
recognised rather than extracted.

---

## 2. Output format

- **One paragraph per line.** No hard-wrapping mid-paragraph.
- **One blank line between paragraphs.** No other blank lines.
- **No page numbers, no running headers or footers.** These repeat on every
  page and pollute the text.
- **No image or chart content.** Captions are text and are kept.
- **Tables kept**, rendered as aligned fixed-width columns, e.g.

  ```
  Indicator           | Baseline 2020 | Target 2030 | Status
  --------------------+---------------+-------------+---------
  Protected areas     | 17%           | 30%         | On track
  ```

- **Words hyphenated across a line break are rejoined** ("mat-" + "ter" →
  "matter"), while genuine compound hyphens are preserved ("Franco-German").
- **A paragraph split across a page break is stitched back together.**
- UTF-8, no BOM.

Optional, off by default: `[page N]` markers between pages, for citation.

---

## 3. Document features that must be handled

Drawn from the real corpus:

| Feature | Requirement |
| --- | --- |
| Length | Single page up to ~50 pages; batches of many files |
| Sideways pages | Text printed at 90° on a portrait page must be read correctly, including any table on it |
| Two-column layout | Each column read in full, in order — not interleaved line by line |
| Tables with ruling lines | Detected and rendered as tables |
| Tables without ruling lines | Reconstructed from column alignment |
| Images and charts | Ignored |
| Scanned pages | Recognised (see §4) |
| Languages | English, French, Spanish, mixed across a corpus |

---

## 4. Scanned documents

A large proportion of the corpus has no selectable text. This is the hardest
part of the problem and the part most likely to need work.

Current approach, local and deterministic by default:

1. Detect pages with no usable text layer.
2. Render at 300 DPI, autocontrast, correct quarter-turns via orientation
   detection, deskew small rotations, **erase table ruling lines**.
3. Recognise with Tesseract, returning **word bounding boxes**, which are fed
   through the same paragraph/column/table logic as digital PDFs. This is why
   a clean scan comes out in the same shape as its digital equivalent.
4. Pages returning low confidence are retried with denoise + sharpen; the
   better of the two passes is kept.
5. Report average confidence; flag files below 75%.

An optional Mistral OCR path exists for degraded scans, off by default,
carrying the hallucination caveat above.

### Measured findings worth not rediscovering

- **Tesseract loses text boxed inside table ruling lines.** On a test table
  it read 2 of 9 expected cell values. Erasing horizontal/vertical rules
  before recognition recovered 9 of 9. This alone was the single largest
  quality gain.
- Page-segmentation mode (`--psm`) made no useful difference to that problem;
  line removal was the fix.
- **Scoring two OCR passes by "confidence mass"** (sum of per-word
  confidences) reliably picks the better pass: identical on clean scans,
  clearly better on degraded ones (+50% relative word recall).
- A **whitespace-corridor test for two-column detection fails** when a
  full-width heading crosses the gutter. Detecting the gutter from *where
  most rows share a single wide internal gap* works, and rows with two or
  more wide gaps can be excluded as table rows rather than prose.
- **Justified text mimics table cells** — stretched word spacing produces
  wide gaps. Requiring cell positions to align across at least two
  consecutive rows separates the two cases.
- **Running-header detection needs a font-size guard**, otherwise a recurring
  section heading at the top of each page gets deleted as a header.
- Quality is bounded by the source: a good OCR layer reflows near-perfectly,
  an old or poor one degrades fast, and a **broken font encoding produces
  confident garbage that character-retention checks will not catch**.

---

## 5. Non-functional requirements

- Runs on macOS (Homebrew available) and ideally Windows, since the team is
  mixed.
- **Usable by non-developers.** The current script has a settings block, a
  small GUI (folder pickers, progress bar, log, stop button), and a command
  line. Colleagues doing importation will need something at least this
  approachable, possibly more.
- **Batch processing** over a folder, with per-file and per-page progress.
- Per-file reporting: pages, tables found, headers removed, OCR pages and
  confidence, retention percentage, warnings.
- Failures should be per-file, not fatal to the batch.
- Minimal dependencies: currently `pdfplumber`, `pypdf`, `numpy`, plus
  `pytesseract` + Tesseract for OCR. pdfplumber was chosen over PyMuPDF
  partly for licensing (MIT vs AGPL).

---

## 6. Known limitations of the current script

Genuine gaps, worth deciding whether to fix:

- **Footnotes** stay where they sit on the page rather than being separated
  or moved; they interrupt the body text flow.
- **Two-column pages containing tables** may order the table wrongly relative
  to the columns.
- **Skew beyond a few degrees**, and page-level warping, are not corrected.
- No handling of **document structure** — headings are preserved as their own
  paragraphs but not labelled, numbered, or made machine-readable.
- No **per-page language switching**; language is detected once per file.
- The Mistral OCR path is written but was never run against the live API.
- No test suite beyond ad-hoc synthetic PDFs; there is no corpus of real IEA
  documents with known-correct output to measure against.

---

## 7. Open questions for the agreement-importation use case

These need answers from the colleagues who do the importation before
building. Nothing here should be assumed.

1. **What does "properly formatted" mean concretely for the website?** Is
   there a written convention, or an existing set of good/bad examples? A
   handful of accepted TXT files would function as a specification.
2. **Structure.** Agreement texts have preambles, numbered articles,
   sub-paragraphs, annexes, signature blocks and ratification lists. Should
   these be preserved as plain paragraphs, or marked up (article numbers,
   heading levels)? Does the website parse the TXT, or display it as-is?
3. **Completeness.** Are signature blocks, party lists, depositary notes and
   footnotes wanted, or stripped?
4. **Language versions.** Many agreements are authentic in several languages.
   One file per language? How are they named and linked? Note that the
   decision-collection codebook asks for names "preferably in the decision's
   initial language" — is there an equivalent rule here?
5. **File naming and metadata.** Decision files follow
   `ID-number_short-title_year-of-adoption`. Is there a parallel convention
   for agreement texts, and should the tool generate it?
6. **Review step.** Is there a human check before publication? If so the tool
   should optimise for making review fast — flagging uncertain pages,
   reporting confidence, and marking OCR'd sections — rather than for
   producing silently finished output.
7. **Scale and source.** How many agreements, and where do the PDFs come
   from? A shared drive, a scrape, per-agreement manual retrieval?
8. **What specifically failed** in the Mistral OCR 3 attempt besides
   hallucination? Keeping those files as regression cases would be valuable.

---

## 8. Suggested approach for the autumn session

1. Collect a **test corpus**: 15–25 real documents spanning the hard cases
   (clean digital, two-column, sideways table, good scan, terrible scan, one
   per language, plus whatever broke the previous attempt).
2. For 3–5 of them, produce **hand-corrected reference TXT** in the target
   format. Without ground truth, "quality" stays a matter of opinion.
3. Answer the §7 questions and write the formatting convention down.
4. Only then extend the tool, measuring each change against the corpus.

The ordering matters: the previous attempt's problem was not that the
technology was too weak, but that nothing was measuring whether the output
was faithful. Fixing that first makes every later decision checkable.
