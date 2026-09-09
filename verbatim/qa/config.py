"""
verbatim.qa.config — tunable thresholds for the quality layer.

Carried over from the txtqa package, minus its hardcoded paths: verbatim
manages its own input and output locations.

The weights below are a starting guess, not a result. Calibrate them against
the corpus before trusting the numbers — see docs/calibration.md.
"""

from __future__ import annotations

CONFIG = {
    # Written by `verbatim audit`; the inline gate reads it so that a file
    # assessed during conversion gets the number it would have got in a
    # corpus audit. Without it, only the absolute trip-wires can fire.
    "BASELINE_JSON": None,          # set at runtime; see verbatim.qa.gate

    # ------------------------------------------------------------------
    # TEXT METRICS
    # ------------------------------------------------------------------
    # Minimum characters before a file is scored at all. Shorter files are
    # flagged "too_short" instead, since the statistics are meaningless.
    "MIN_CHARS": 200,

    "REPEAT_NGRAM_N": 8,
    # Decoder degeneration happens at the END of a generation, so the tail is
    # checked separately at this fraction of the document.
    "TAIL_FRACTION": 0.20,

    # Vowel-less tokens only make sense for vowel-rich orthographies.
    "VOWEL_CHECK_LANGS": {"en", "es", "fr", "it", "pt", "de", "nl"},
    "VOWELLESS_MIN_TOKEN_LEN": 4,

    "SMALL_FONT_PT": 7.0,
    "LOW_DPI": 200.0,

    # ------------------------------------------------------------------
    # COMPOSITE SCORING
    # ------------------------------------------------------------------
    # Each metric becomes a robust z-score against the corpus baseline,
    # clipped, weighted and summed. Weight 0.0 = computed and reported but
    # excluded from the score. direction +1 = high is suspicious, -1 = low is,
    # "abs" = both tails are.
    "METRIC_SPEC": {
        "script_mix_ratio":      {"weight": 1.4, "direction": +1},
        "vowelless_ratio":       {"weight": 1.0, "direction": +1},
        "gzip_ratio":            {"weight": 1.2, "direction": "abs"},
        "chars_per_page":        {"weight": 1.2, "direction": "abs"},
        "top_ngram_coverage":    {"weight": 1.6, "direction": +1},
        "tail_ngram_coverage":   {"weight": 1.6, "direction": +1},
        "dup_line_run":          {"weight": 1.0, "direction": +1},
        "junk_char_rate":        {"weight": 0.8, "direction": +1},
        "mojibake_rate":         {"weight": 0.8, "direction": +1},
        "short_token_run":       {"weight": 0.8, "direction": +1},
        "mean_token_len":        {"weight": 0.6, "direction": "abs"},
    },
    "CLIP": 6.0,

    # ------------------------------------------------------------------
    # PDF SUSCEPTIBILITY
    # ------------------------------------------------------------------
    "SUSCEPT_SPEC": {
        "frac_pages_no_text":    2.0,   # scanned -> no free reference exists
        "frac_small_text":       1.5,
        "frac_lines_rotated":    1.5,
        "frac_pages_landscape":  0.8,
        "table_density":         1.2,
        "text_density":          0.8,
        "frac_pages_low_dpi":    1.5,
        "has_type3_font":        0.6,
    },

    # ------------------------------------------------------------------
    # TRIAGE THRESHOLDS
    # ------------------------------------------------------------------
    "REVIEW_PERCENTILE": 95.0,
    "INLINE_REVIEW_SCORE": 3.0,
    "INLINE_REJECT_SCORE": 6.0,

    # Absolute trip-wires, which fire before any baseline exists. IEA
    # decisions repeat boilerplate heavily, so the n-gram limits are
    # deliberately loose; reset them from the corpus run (roughly p99.5 of
    # each metric) once a baseline exists.
    "HARD_LIMITS": {
        "top_ngram_coverage": 0.45,
        "tail_ngram_coverage": 0.55,
        "script_mix_ratio": 0.02,
        "mojibake_rate": 0.001,
        "junk_char_rate": 0.005,
        "short_token_run": 0.10,
    },
    # An image-only PDF whose GEOMETRY risk clears this bar goes on the
    # self-consistency shortlist. This one number is what the OCR bill is
    # proportional to. Set it from the observed distribution after a corpus
    # run rather than trusting the default.
    "SELFCHECK_GEOMETRY_MIN": 0.20,

    # ------------------------------------------------------------------
    # FIDELITY (verbatim's own checks — see qa/fidelity.py)
    # ------------------------------------------------------------------
    # Retention over letters and digits. Below this, text was lost.
    "RETENTION_MIN": 0.98,
    # Above this, more text came out than went in.
    "RETENTION_MAX": 1.02,
    # A run of this many consecutive words with no counterpart is structural,
    # not ordinary recognition noise.
    "BLOCK_RUN_WORDS": 40,
    # Word-sequence similarity at or above which two texts are the same text.
    "SIMILARITY_OK": 0.97,
    "SIMILARITY_REWRITTEN": 0.95,
    # Recognition confidence below which a file always needs a human.
    "OCR_CONF_MIN": 0.75,
}
