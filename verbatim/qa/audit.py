"""
verbatim.qa.audit — measure a whole corpus, and produce the baseline.

Two outputs, and the second is the important one.

The **triage sheet** ranks every file by how likely it is to be damaged, so
review effort goes where it is worth spending. It is deliberately a ranking,
not a pass/fail: the weights behind it are a starting guess until someone
hand-labels a few hundred files and checks which metrics actually separated
good from bad.

The **baseline** records the median and spread of every metric across the
corpus. Without it, every relative check in the quality layer is inert — a
z-score needs a distribution to be a score against, and only the absolute
trip-wires can fire. The IEADB corpus has 21,605 converted files and no
baseline has ever been built from them, so every conversion so far has been
checked with roughly half the available machinery switched off.

Spread is measured with the median absolute deviation rather than the standard
deviation, because the corpus contains the very outliers being hunted and they
would otherwise inflate the scale that is supposed to expose them.
"""

from __future__ import annotations

import csv
import sys
import time
import unicodedata
from pathlib import Path

from .config import CONFIG
from .pdfprofile import profile_pdf
from .scoring import build_baseline, percentile_threshold, save_baseline, score_row
from .scramble import scan as scramble_scan
from .textmetrics import compute_text_metrics


def nfc(name: str) -> str:
    """macOS hands back NFD for accented filenames; everything else uses NFC.

    Every filename comparison goes through here. Skipping it produces phantom
    "missing PDF" mismatches on any file with an accent, which in this corpus
    is a great many of them.
    """
    return unicodedata.normalize("NFC", name)


def read_text(path: Path) -> str:
    """Decode a .txt, tolerating the CP1252 files known to be in the corpus."""
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def index_pdfs(pdf_dir) -> dict:
    if not pdf_dir:
        return {}
    index: dict = {}
    for p in Path(pdf_dir).rglob("*.pdf"):
        index.setdefault(nfc(p.stem), p)
    return index


def measure(txt_dir, pdf_dir=None, limit=None, config=None, log=print) -> list:
    """One row of metrics per .txt file."""
    cfg = config or CONFIG
    files = sorted(Path(txt_dir).rglob("*.txt"))
    if limit:
        files = files[:limit]
    pdfs = index_pdfs(pdf_dir)
    rows: list = []
    t0 = time.time()

    for i, path in enumerate(files, 1):
        if i % 500 == 0:
            log(f"  {i}/{len(files)} files, {time.time() - t0:.0f}s")
        try:
            text = read_text(path)
        except OSError as exc:
            rows.append({"file": path.name, "error": str(exc)})
            continue

        pdf = pdfs.get(nfc(path.stem))
        prof = profile_pdf(str(pdf), cfg) if pdf else {}
        n_pages = prof.get("n_pages")
        row = {"file": path.name, "path": str(path)}
        row.update(compute_text_metrics(text, config=cfg, n_pages=n_pages))
        row.update({k: v for k, v in prof.items() if k != "n_pages"})
        if n_pages:
            row["n_pages"] = n_pages

        sc = scramble_scan(text)
        row["scrambled_words"] = len(sc["scrambled"])
        row["scrambled_sample"] = ", ".join(sc["scrambled"][:5])
        rows.append(row)
    return rows


def run_audit(txt_dir, pdf_dir=None, out=None, limit=None, log=print) -> int:
    """Measure a corpus, write the baseline, write a ranked triage sheet."""
    txt_dir = Path(txt_dir)
    if not txt_dir.exists():
        log(f"No such folder: {txt_dir}")
        return 2

    log(f"Reading {txt_dir}…")
    rows = measure(txt_dir, pdf_dir=pdf_dir, limit=limit, log=log)
    scorable = [r for r in rows if not r.get("error") and not r.get("too_short")]
    log(f"{len(rows)} file(s), {len(scorable)} scorable.")

    baseline = build_baseline(scorable, CONFIG)
    if not baseline:
        log("Not enough scorable files to build a baseline "
            "(each metric needs at least 20 values).")
        return 1

    out_dir = Path(out) if out else txt_dir.parent
    if out_dir.suffix:                       # a file was named, not a folder
        baseline_path = out_dir
        out_dir = out_dir.parent
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        baseline_path = out_dir / "verbatim_baseline.json"
    save_baseline(baseline, str(baseline_path))
    log(f"Baseline: {baseline_path}  ({len(baseline)} metrics)")

    for row in rows:
        if row.get("error") or row.get("too_short"):
            row["risk_score"] = None
            continue
        row.update(score_row(row, baseline, CONFIG))

    scores = [r["risk_score"] for r in rows if r.get("risk_score") is not None]
    threshold = percentile_threshold(scores, CONFIG["REVIEW_PERCENTILE"])
    for row in rows:
        s = row.get("risk_score")
        if row.get("error"):
            row["verdict"] = "error"
        elif row.get("too_short"):
            row["verdict"] = "too_short"
        elif row.get("scrambled_words", 0) >= 2:
            row["verdict"] = "scrambled"
        else:
            row["verdict"] = "review" if s is not None and s >= threshold else "ok"

    report = out_dir / "verbatim_triage.csv"
    write_csv(rows, report)
    flagged = sum(1 for r in rows if r["verdict"] not in ("ok",))
    log(f"Triage sheet: {report}")
    log(f"{flagged} of {len(rows)} file(s) flagged "
        f"(review threshold {threshold:.3f}, "
        f"p{CONFIG['REVIEW_PERCENTILE']:.0f} of the corpus).")
    log("\nThe weights behind that ranking are a starting guess. Sort the "
        "sheet by risk_score, hand-label 150-200 files sampled across the "
        "whole range — not only the top, or the false negatives stay "
        "invisible — and zero the weights of the metrics that did not "
        "separate the two groups. See docs/calibration.md.")
    return 0


def write_csv(rows: list, path: Path) -> None:
    """Worst first, so the sheet opens on what matters."""
    if not rows:
        return
    lead = ["file", "verdict", "risk_score", "risk_reasons", "language",
            "n_chars", "n_pages", "scrambled_words", "scrambled_sample"]
    keys = list(dict.fromkeys(lead + [k for r in rows for k in r
                                      if not k.startswith("_") and k != "path"]))
    ordered = sorted(rows, key=lambda r: (r.get("risk_score") is None,
                                          -(r.get("risk_score") or 0.0)))
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for row in ordered:
            w.writerow({k: row.get(k) for k in keys})


if __name__ == "__main__":
    raise SystemExit(run_audit(*sys.argv[1:2]))
