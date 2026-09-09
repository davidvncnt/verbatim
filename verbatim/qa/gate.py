"""
verbatim.qa.gate — one verdict per document, with reasons a person can act on.

Merges three independent sources of evidence:

  * **fidelity** — do the output's words come from the source? (qa.fidelity)
  * **intrinsic** — does the output look like damaged text on its own terms?
    (qa.textmetrics, qa.scoring, qa.scramble)
  * **structural** — was this PDF likely to extract badly? (qa.pdfprofile)

They are kept separate because they fail differently. Fidelity needs a source
to compare against and is silent without one. Intrinsic checks always work but
only see damage that has a visible signature. Structural signals see neither,
and predict rather than measure.

The verdict is never a number alone. Every file that is held back names the
finding that held it back, because a reviewer who is not told what to look at
will look at everything, which is how things get missed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import CONFIG
from .fidelity import HIGH, MEDIUM, Finding, check_document, compare_words
from .pdfprofile import profile_pdf
from .scoring import load_baseline, score_row
from .textmetrics import compute_text_metrics

OK, REVIEW, REJECT = "ok", "review", "reject"


@dataclass
class Assessment:
    verdict: str
    findings: list = field(default_factory=list)
    risk_score: float | None = None
    metrics: dict = field(default_factory=dict)
    profile: dict = field(default_factory=dict)
    joins: int = 0

    @property
    def needs_review(self) -> bool:
        return self.verdict in (REVIEW, REJECT)

    def reasons(self, lang: str | None = None) -> list:
        return [f.message(lang) for f in self.findings]

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "risk_score": self.risk_score,
            "joins": self.joins,
            "findings": [f.to_dict() for f in self.findings],
            "metrics": {k: v for k, v in self.metrics.items()
                        if not k.startswith("_")},
            "profile": {k: v for k, v in self.profile.items()
                        if not k.startswith("_")},
        }


class QualityGate:
    """Construct once, call `assess` per document.

    Without a baseline only the absolute checks can fire: a z-score needs a
    corpus to be a score against. That is a real limitation, not a warning to
    be clicked past — `has_baseline` says which mode is in force.
    """

    def __init__(self, baseline_path: str | None = None,
                 config: dict | None = None) -> None:
        self.config = config or CONFIG
        self.baseline = load_baseline(baseline_path) if baseline_path else None
        self.has_baseline = self.baseline is not None

    def assess(self, result, pdf_path: str | None = None,
               profile: bool = True) -> Assessment:
        """Assess one ConversionResult."""
        text = result.text
        n_pages = result.stats.get("pages") or None

        prof: dict = {}
        if profile and pdf_path:
            prof = profile_pdf(str(pdf_path), self.config)

        metrics = compute_text_metrics(text, config=self.config, n_pages=n_pages)

        # --- fidelity -------------------------------------------------------
        model_pages = [p for p in result.pages if p.source == "recognised_model"]
        recognised = [p for p in result.pages if p.source != "extracted"]
        has_layer = len(recognised) < len(result.pages)

        findings = check_document(
            text, result.raw_text, self.config,
            removed_on_purpose=result.dropped_text,
            retention=result.stats.get("alnum_ratio"),
            has_text_layer=has_layer)
        _, joins = (compare_words(result.raw_text, text, result.dropped_text)
                    if has_layer and result.raw_text.strip() else ([], 0))

        # --- pages nothing could be checked against -------------------------
        if model_pages:
            # A model produced these words. Nothing in the document can confirm
            # them, so they are never signed off silently.
            findings.append(Finding(
                kind="model_pages", severity=HIGH, key="model_pages",
                params={"n": len(model_pages)},
                page=model_pages[0].number))
        confs = [p.ocr_conf for p in recognised if p.ocr_conf is not None]
        if confs:
            mean_conf = sum(confs) / len(confs)
            if mean_conf < self.config["OCR_CONF_MIN"]:
                findings.append(Finding(
                    kind="ocr_confidence", severity=MEDIUM,
                    key="ocr_low_confidence", params={"pct": mean_conf}))
        if result.stats.get("scanned"):
            findings.append(Finding(
                kind="no_text_layer", severity=HIGH, key="no_text_layer",
                params={"n": len(result.stats["scanned"])},
                page=result.stats["scanned"][0]))

        # --- intrinsic trip-wires, which fire without a baseline ------------
        labels = {
            "top_ngram_coverage": "repetition_loop",
            "tail_ngram_coverage": "repetition_loop",
        }
        tripped = []
        for key, limit in self.config["HARD_LIMITS"].items():
            val = metrics.get(key)
            if val is not None and float(val) > limit:
                tripped.append(key)
                if key in labels:
                    findings.append(Finding(
                        kind=labels[key], severity=HIGH, key="repetition_loop",
                        params={"n": self.config["REPEAT_NGRAM_N"]},
                        detail=f"{key}={float(val):.3g} > {limit}"))

        # --- relative score, when a corpus baseline exists ------------------
        score = None
        if self.has_baseline:
            merged = {**metrics, **prof}
            score = score_row(merged, self.baseline, self.config)["risk_score"]

        # --- verdict --------------------------------------------------------
        worst = {f.severity for f in findings}
        if HIGH in worst or tripped or (
                score is not None and score >= self.config["INLINE_REJECT_SCORE"]):
            verdict = REJECT
        elif worst or (score is not None
                       and score >= self.config["INLINE_REVIEW_SCORE"]):
            verdict = REVIEW
        else:
            verdict = OK

        findings.sort(key=lambda f: {HIGH: 0, MEDIUM: 1}.get(f.severity, 2))
        return Assessment(verdict=verdict, findings=findings, risk_score=score,
                          metrics=metrics, profile=prof, joins=joins)
