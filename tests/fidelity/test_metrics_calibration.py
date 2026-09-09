"""
Two corrections that the real corpus forced, and must not regress.

Both were found by running the auditor over the 21,605 converted files and
reading what came out on top. In each case the ranking was dominated by files
that were entirely correct, which is the way a review queue stops being read.
"""

from __future__ import annotations

from verbatim.qa.config import CONFIG
from verbatim.qa.scoring import build_baseline, score_row
from verbatim.qa.textmetrics import (
    compute_text_metrics,
    ngram_coverage,
    prose_lines,
    tokenize,
    tokenize_all,
)

# A coordinate annex, shaped like the ones CCAMLR conservation measures carry:
# a short row label and five coordinate pairs, every number different.
COORDINATES = "\n".join(
    "{}{}\t{}".format(
        row, n,
        "\t".join(f"S{58 + k} {k * 7 % 60}.{k * 13 % 90:02d}:"
                  f"E0{80 + (k % 5)} {k * 3 % 60}.{k * 17 % 90:02d}"
                  for k in range(i * 5, i * 5 + 5)))
    for i, (row, n) in enumerate(
        [(r, n) for r in "HIJKLM" for n in (1, 2, 3)])
)

# A printed logbook form: the same column headings on every row.
LOGBOOK = "\n".join(
    "DATE\tPOSITION\tALBACORE  LISTADO  PATUDO\tESTIMATED CATCH" for _ in range(40))

PROSE = ("The Commission shall hold one regular session each year and special "
         "sessions shall be convened as necessary by the Chairperson after "
         "consultation with the Director-General of the Organization. ") * 3


def test_digits_count_when_looking_for_repetition():
    """With digits stripped, a coordinate table collapses to the letters
    "S E S E S E" and reads as a decoder stuck in a loop."""
    alphabetic = tokenize(COORDINATES)
    with_digits = tokenize_all(COORDINATES)
    assert ngram_coverage(alphabetic, 8) > 0.9        # the false alarm
    assert ngram_coverage(with_digits, 8) < 0.1       # the truth


def test_table_rows_are_not_measured_for_repetition():
    """A printed form repeats its headings by design. Digits do not help here;
    only excluding the table does."""
    assert ngram_coverage(tokenize_all(LOGBOOK), 8) > 0.9
    assert prose_lines(LOGBOOK).strip() == ""


def test_a_coordinate_annex_scores_as_clean():
    m = compute_text_metrics(PROSE + "\n\n" + COORDINATES, config=CONFIG)
    assert m["top_ngram_coverage"] < CONFIG["HARD_LIMITS"]["top_ngram_coverage"]
    assert m["tail_ngram_coverage"] < CONFIG["HARD_LIMITS"]["tail_ngram_coverage"]


def test_a_real_repetition_loop_is_still_caught():
    """The fix must not buy its quiet by going blind."""
    loop = "the Parties shall consider the matter further at the next session "
    m = compute_text_metrics(PROSE + "\n\n" + loop * 80, config=CONFIG)
    assert m["top_ngram_coverage"] > CONFIG["HARD_LIMITS"]["top_ngram_coverage"]


def test_prose_lines_keeps_prose_and_drops_tables():
    text = "A normal sentence of prose.\na | b | c\n-+-\nx\ty\tz\nAnother sentence."
    kept = prose_lines(text).splitlines()
    assert "A normal sentence of prose." in kept
    assert "Another sentence." in kept
    assert not any("|" in ln or "\t" in ln for ln in kept)


# --- zero-inflated metrics ------------------------------------------------

def test_a_zero_inflated_metric_gets_a_real_scale():
    """Most files score exactly 0 for mojibake, so the median and the median
    absolute deviation are both 0. Dividing by a 1e-9 floor gave every
    non-zero value the maximum z-score, however trivial — on the real corpus
    that put tail_ngram_coverage=0.01 above genuinely damaged files.
    """
    rows = [{"mojibake_rate": 0.0} for _ in range(970)]
    rows += [{"mojibake_rate": 0.001 * i} for i in range(1, 31)]
    baseline = build_baseline(rows, {"METRIC_SPEC": {"mojibake_rate": {}}})
    assert "mojibake_rate" in baseline
    spread = baseline["mojibake_rate"]["mad"]
    assert spread > 1e-6, "the spread collapsed to the floor again"

    config = {"METRIC_SPEC": {"mojibake_rate": {"weight": 1.0, "direction": +1}},
              "CLIP": 6.0}
    trivial = score_row({"mojibake_rate": 0.0005}, baseline, config)["risk_score"]
    severe = score_row({"mojibake_rate": 0.03}, baseline, config)["risk_score"]
    assert trivial < 1.0, "a trivial value still scores as alarming"
    assert severe > trivial * 3, "a severe value is not separated from a trivial one"


def test_a_constant_metric_is_left_out_rather_than_invented():
    """A metric with no spread cannot rank anything. Giving it a made-up scale
    is worse than admitting it carries no information; rare all-or-nothing
    signals belong to the absolute limits instead."""
    rows = [{"junk_char_rate": 0.0} for _ in range(100)]
    baseline = build_baseline(rows, {"METRIC_SPEC": {"junk_char_rate": {}}})
    assert "junk_char_rate" not in baseline
