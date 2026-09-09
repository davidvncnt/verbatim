# Calibrating the risk score

The weights in `verbatim/qa/config.py` are a starting guess, not a result.
They decide which files reach a reviewer, so leaving them uncalibrated means
review effort is spent on whatever the defaults happened to rank highly.

## Why a baseline is needed at all

Most quality metrics only mean something relative to a corpus. A `gzip_ratio`
of 0.42 is unremarkable in this corpus and would be alarming in another. So
each metric is converted to a robust z-score against the corpus's own
distribution:

```
z = 0.6745 × (x − median) / spread
```

The median absolute deviation is used rather than the standard deviation,
because the corpus contains the very outliers being hunted and they would
otherwise inflate the scale that is supposed to expose them.

Without `verbatim_baseline.json` there is no distribution, so no z-score can be
computed and only the absolute limits in `HARD_LIMITS` can fire. The window
says so in its header rather than letting the numbers look complete.

## Building it

```bash
verbatim audit /path/to/txt --out /somewhere/stable
```

About two minutes for 21,600 files. It writes `verbatim_baseline.json` and a
ranked `verbatim_triage.csv`. Point the tool at the baseline with
`--baseline`, or save its path in the preferences file so the window finds it.

## Calibrating, in order

1. **Sort the triage sheet by `risk_score`.** Hand-label roughly 150–200 files
   as good or bad, sampled **across the whole range**, not only the top. Label
   only the top and the false negatives stay invisible for ever.

   The review window produces exactly these labels as a by-product: every
   accept/reject is written into the file's record along with what the tool had
   predicted. After a few weeks of ordinary work there is a labelled set
   without anyone having done a labelling exercise.

2. **Check which metrics actually separated the two groups.** Expect two or
   three to carry nearly everything. Set the weight of the rest to `0.0` in
   `METRIC_SPEC` — they are still computed and reported, just not scored.

3. **Reset `HARD_LIMITS` from the observed distribution**, around p99.5 of each
   metric. These are the absolute trip-wires that fire without a baseline, so
   they matter most for one-off conversions.

4. **Set `SELFCHECK_GEOMETRY_MIN` from the observed `geometry_risk` spread.**
   That single number is what any paid-OCR bill is proportional to: raise it to
   sample fewer files, lower it to sample more.

5. **Check whether `susceptibility` predicts `risk_score`.** Run the audit with
   `--pdf-dir` so the source PDFs are profiled too. Any PDF signal that does not
   predict text damage should be dropped rather than kept out of plausibility.

## Two corrections already made, and why

Both were found by running the audit over the real corpus and reading what came
out at the top. In each case the ranking was dominated by files that were
entirely correct — which is how a review queue stops being read. They are
recorded here because they are the shape of mistake this exercise is for.

**Repetition metrics counted letters but not digits.** With digits stripped, a
coordinate annex — `S57 55.18:E080 24.42` repeated down the page — collapses to
the token stream `S E S E S E`, which looks exactly like a decoder stuck in a
loop and scored a perfect 1.0. Counting digits drops the same files to 0.0.

**Repetition metrics measured tables.** A printed logbook form carries the same
column headings on every row; a catch-limit annex the same labels. Those are
genuinely repetitive and entirely correct. Repetition is now measured over prose
only, tables excluded — the same treatment the interleaving check already used.

**Zero-inflated metrics divided by a floor.** Most files score exactly 0 for
mojibake, script mixing and duplicate lines, so both the median and the median
absolute deviation are 0, and the fallback floor of 1e-9 gave every non-zero
value the maximum z-score however trivial. `tail_ngram_coverage = 0.01` was
scoring 6.0, above genuinely damaged files. The spread now falls back to the
interquartile range and then to the distance from the median to p99; a metric
that is genuinely constant is left out of the baseline entirely, because it
cannot rank anything, and belongs to `HARD_LIMITS` instead.

## Two real findings from the first full run

Worth keeping as regression cases:

- `47419_iuuvessellist_2023.txt` — `ANNEX I` repeated 23 times as a standalone
  line. A running header that survived because the old pipeline skipped header
  removal on model-recognised pages. Fixed; see
  `tests/fidelity/test_model_ocr_headers.py`.
- `32911_pm9-15(1)_2013.txt` — the line `P. deltoides\tX` repeated **596
  times**. Not legitimate content.
