"""
txtqa.scoring — turns raw metrics into one comparable risk number.

Design notes
------------
Raw metrics live on wildly different scales (a script-mix ratio of 0.02 is
alarming; a gzip ratio of 0.02 is impossible). So each metric is converted
to a robust z-score against a corpus baseline before being weighted:

    z = 0.6745 * (x - median) / MAD

MAD rather than standard deviation, because the whole point of the exercise
is that the corpus contains outliers, and outliers wreck a mean-based
scale. The 0.6745 factor makes the MAD comparable to a standard deviation
for normally distributed data.

The baseline is computed once over the corpus and saved to JSON. The inline
pipeline hook loads that same JSON, so a file scored during conversion gets
exactly the number it would have got in a batch audit.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Sequence


def _median(values: Sequence[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _mad(values: Sequence[float], med: float) -> float:
    if not values:
        return 0.0
    return _median([abs(v - med) for v in values])


def build_baseline(rows: list[dict[str, object]], config: dict) -> dict[str, dict]:
    """Compute median and MAD for every scored metric across the corpus."""
    baseline: dict[str, dict] = {}
    keys = list(config["METRIC_SPEC"].keys()) + ["chars_per_page"]
    for key in dict.fromkeys(keys):  # dedupe, preserve order
        vals = [
            float(r[key])
            for r in rows
            if r.get(key) is not None and not isinstance(r.get(key), bool)
        ]
        if len(vals) < 20:
            continue
        med = _median(vals)
        mad = _mad(vals, med)
        if mad <= 0:
            # Zero-inflated metric: most files score exactly 0, so both the
            # median and the MAD are 0. Dividing by a floor of 1e-9 would give
            # every non-zero value the maximum z-score, however trivial — on
            # the real corpus that put tail_ngram_coverage=0.01 at maximum
            # risk, ahead of genuinely damaged files. Fall back to the
            # interquartile range, and then to the distance from the median to
            # the 99th percentile, which stays well defined when most of the
            # distribution sits on zero. The 2.33 is the number of standard
            # deviations at p99 for a normal distribution, so the resulting
            # scale stays comparable with the metrics that do have a MAD.
            ordered = sorted(vals)
            q1 = ordered[len(ordered) // 4]
            q3 = ordered[(3 * len(ordered)) // 4]
            mad = (q3 - q1) / 1.35
        if mad <= 0:
            mad = (percentile_threshold(vals, 99.0) - med) / 2.33
        if mad <= 0:
            # Genuinely constant across the corpus. Such a metric cannot rank
            # anything, so it is left out of the baseline rather than given an
            # invented scale; score_row skips what it cannot find. Rare
            # all-or-nothing signals belong to HARD_LIMITS instead, where an
            # absolute threshold is the honest instrument.
            continue
        baseline[key] = {"median": med, "mad": mad, "n": len(vals)}
    return baseline


def save_baseline(baseline: dict[str, dict], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(baseline, fh, indent=2)


def load_baseline(path: str) -> dict[str, dict] | None:
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def score_row(
    row: dict[str, object], baseline: dict[str, dict], config: dict
) -> dict[str, object]:
    """Composite risk score plus the per-metric contributions behind it.

    Contributions are returned alongside the score so that a flagged file
    always comes with a readable reason, rather than an opaque number.
    """
    clip = config["CLIP"]
    total = 0.0
    contributions: dict[str, float] = {}
    reasons: list[str] = []

    for key, spec in config["METRIC_SPEC"].items():
        weight = spec["weight"]
        if weight == 0.0:
            continue
        val = row.get(key)
        stats = baseline.get(key)
        if val is None or stats is None:
            continue
        z = 0.6745 * (float(val) - stats["median"]) / stats["mad"]
        direction = spec["direction"]
        if direction == "abs":
            z = abs(z)
        elif direction == -1:
            z = -z
        z = max(0.0, min(clip, z))  # only suspicious deviations accumulate
        contribution = weight * z
        contributions[key] = round(contribution, 3)
        total += contribution
        if z >= 3.0:
            reasons.append(f"{key}={float(val):.4g} (z={z:.1f})")

    # Normalise by total active weight so the number means the same thing
    # regardless of how many metrics happened to be computable.
    active = sum(
        s["weight"]
        for k, s in config["METRIC_SPEC"].items()
        if s["weight"] > 0 and k in contributions
    )
    score = total / active if active else 0.0

    reasons.sort(key=lambda r: -contributions.get(r.split("=")[0], 0.0))
    return {
        "risk_score": round(score, 4),
        "risk_reasons": "; ".join(reasons[:4]),
        "n_metrics_used": len(contributions),
        "_contributions": contributions,
    }


def percentile_threshold(scores: Sequence[float], pct: float) -> float:
    if not scores:
        return float("inf")
    s = sorted(scores)
    k = (len(s) - 1) * (pct / 100.0)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] * (hi - k) + s[hi] * (k - lo)
