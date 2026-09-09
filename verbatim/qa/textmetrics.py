"""
txtqa.textmetrics — intrinsic quality metrics computed from the .txt alone.

Every function here is pure: text in, numbers out. No file I/O, no config
lookups beyond the values passed in. That is what lets the same code back
both the batch auditor and the inline pipeline hook.

Metric conventions
------------------
All ratios are in [0, 1] unless noted. Higher = more suspicious, except
gzip_ratio and mean_token_len where both tails matter (handled in scoring).
"""

from __future__ import annotations

import gzip
import re
import unicodedata
from collections import Counter

# --------------------------------------------------------------------------
# tokenisation
# --------------------------------------------------------------------------

# Alphabetic tokens only: no digits, no underscores, Unicode-aware.
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Tokens including digits. Repetition metrics use this one. With digits
# stripped, a table of coordinates — "S57 55.18:E080 24.42" — collapses to the
# letters "S E S E S E", which reads as a decoder stuck in a loop. On the real
# corpus that single effect put coordinate annexes at the very top of the risk
# ranking, ahead of every genuinely damaged file.
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# A line that is a rendered table row rather than prose: pipe-separated,
# tab-separated, a column rule, or two or more runs of columnar whitespace.
_TABULAR_RE = re.compile(r" \| |^-+\+-|^\s*\||\t.*\t|\S {2,}\S.* {2,}\S")

# Control characters that should never appear in a clean extraction
# (tab, newline and carriage return are excluded).
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Classic UTF-8-read-as-CP1252 signatures. Cheap and very high precision.
_MOJIBAKE_RE = re.compile(
    "Ã[\u0080-\u00ff]"          # UTF-8 two-byte sequence read as CP1252
    "|â€[\u0080-\u00ff\u2018\u2019\u201c\u201d\u2122\u0153\u02dc]"
    "|Â[\u00a0-\u00bf]"
    "|ï¿½"                       # U+FFFD itself round-tripped
    "|â‚¬"
)

_SCRIPT_CACHE: dict[str, str] = {}


def char_script(ch: str) -> str:
    """Unicode script family of a character, e.g. LATIN, CYRILLIC, GREEK.

    Derived from the character's Unicode name, which is stdlib-only and
    accurate enough to catch the confusables that matter (Cyrillic а, е, о,
    р, с and Greek ο, ν substituted into Latin words).
    """
    hit = _SCRIPT_CACHE.get(ch)
    if hit is not None:
        return hit
    try:
        name = unicodedata.name(ch)
    except ValueError:
        script = "UNKNOWN"
    else:
        script = name.split(" ", 1)[0]
        # "LATIN SMALL LETTER A" -> LATIN; but also normalise the handful of
        # multi-word prefixes that would otherwise fragment.
        if script in ("MODIFIER", "COMBINING"):
            script = "INHERITED"
    _SCRIPT_CACHE[ch] = script
    return script


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def tokenize_all(text: str) -> list[str]:
    """Words and numbers. For metrics where a number is a distinguishing value
    rather than noise."""
    return _TOKEN_RE.findall(text)


def prose_lines(text: str) -> str:
    """The document with rendered table rows removed.

    Repetition metrics exist to catch a recogniser looping over prose. A table
    legitimately repeats: a printed logbook form carries the same species
    headings on every row, and a catch-limit annex the same column labels. On
    the real corpus those forms scored a perfect 1.0 for repetition while being
    entirely correct, so measuring them is measuring the wrong thing.
    """
    return "\n".join(ln for ln in text.splitlines() if not _TABULAR_RE.search(ln))


# --------------------------------------------------------------------------
# individual metrics
# --------------------------------------------------------------------------


def script_mix_ratio(tokens: list[str]) -> float:
    """Fraction of alphabetic tokens mixing two or more Unicode scripts.

    A Cyrillic 'а' inside an otherwise Latin word is a hallmark of both
    OCR confusion and certain model artifacts, and essentially never
    occurs in legitimate text.
    """
    if not tokens:
        return 0.0
    mixed = 0
    for tok in tokens:
        scripts = {char_script(c) for c in tok}
        scripts.discard("INHERITED")
        scripts.discard("COMMON")
        if len(scripts) > 1:
            mixed += 1
    return mixed / len(tokens)


def vowelless_ratio(tokens: list[str], min_len: int = 4) -> float:
    """Fraction of longer tokens containing no vowel at all.

    Only meaningful for vowel-rich orthographies; the caller gates this
    on detected language.
    """
    vowels = set("aeiouy")
    considered = 0
    hits = 0
    for tok in tokens:
        if len(tok) < min_len:
            continue
        considered += 1
        base = _strip_accents(tok).lower()
        if not (set(base) & vowels):
            hits += 1
    return hits / considered if considered else 0.0


def gzip_ratio(text: str) -> float:
    """Compressed size over raw size.

    Both tails are informative. Clean prose sits in a fairly narrow band.
    Far below the band means degenerate repetition (the text compresses
    too well); far above means character-level noise with no structure.
    """
    raw = text.encode("utf-8", errors="replace")
    if not raw:
        return 0.0
    return len(gzip.compress(raw, compresslevel=6)) / len(raw)


def ngram_coverage(tokens: list[str], n: int = 8) -> float:
    """Share of the document occupied by its single most frequent n-gram.

    The signature of a repetition loop. A clean document of any length
    sits near zero; a looping one climbs fast.
    """
    if len(tokens) < 2 * n:
        return 0.0
    low = [t.lower() for t in tokens]
    grams = Counter(tuple(low[i : i + n]) for i in range(len(low) - n + 1))
    top_count = grams.most_common(1)[0][1]
    if top_count < 2:
        return 0.0
    return min(1.0, (top_count * n) / len(low))


def tail_ngram_coverage(tokens: list[str], n: int = 8, tail: float = 0.20) -> float:
    """Same as ngram_coverage but restricted to the end of the document.

    Decoder degeneration overwhelmingly happens at the tail, so a document
    that is clean throughout and loops only in its final pages is caught
    here while the whole-document figure stays diluted and unremarkable.
    """
    if len(tokens) < 4 * n:
        return 0.0
    cut = int(len(tokens) * (1.0 - tail))
    return ngram_coverage(tokens[cut:], n=n)


def dup_line_run(text: str) -> float:
    """Longest run of consecutive identical non-blank lines, normalised.

    Catches header/footer loops and table-row repetition that word n-grams
    can miss when the repeated unit is short.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if len(lines) < 4:
        return 0.0
    best = run = 1
    for i in range(1, len(lines)):
        if lines[i] == lines[i - 1]:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return min(1.0, (best - 1) / len(lines))


def junk_char_rate(text: str) -> float:
    """Replacement characters and stray control codes per character."""
    if not text:
        return 0.0
    n = len(_CTRL_RE.findall(text)) + text.count("\ufffd")
    return n / len(text)


def mojibake_rate(text: str) -> float:
    """Encoding-mismatch signatures per character (the CP1252 problem)."""
    if not text:
        return 0.0
    return len(_MOJIBAKE_RE.findall(text)) / len(text)


def mean_token_len(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    return sum(len(t) for t in tokens) / len(tokens)


def short_token_run(tokens: list[str]) -> float:
    """Longest run of 1-character tokens, normalised.

    Detects letter-spacing failures such as 't h e   t e x t'.
    """
    if len(tokens) < 10:
        return 0.0
    best = run = 0
    for t in tokens:
        if len(t) == 1:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return min(1.0, best / len(tokens))


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------


def detect_language(text: str) -> str:
    """Best-effort language tag.

    Uses langdetect or langid if installed, otherwise a crude English
    stopword test. The corpus is predominantly English and only two
    metrics are language-gated, so a coarse answer is sufficient.
    """
    sample = text[:4000]
    try:
        from langdetect import DetectorFactory, detect  # type: ignore

        DetectorFactory.seed = 0
        return detect(sample)
    except Exception:
        pass
    try:
        import langid  # type: ignore

        return langid.classify(sample)[0]
    except Exception:
        pass
    toks = [t.lower() for t in tokenize(sample)]
    if not toks:
        return "unknown"
    en_stop = {"the", "of", "and", "to", "in", "that", "shall", "for", "on", "by"}
    hit = sum(1 for t in toks if t in en_stop) / len(toks)
    return "en" if hit > 0.08 else "unknown"


def compute_text_metrics(
    text: str,
    *,
    config: dict | None = None,
    language: str | None = None,
    n_pages: int | None = None,
) -> dict[str, object]:
    """Run every intrinsic metric over one document.

    Parameters
    ----------
    text
        Full document text, already decoded.
    language
        Pass a known language tag to skip detection.
    n_pages
        Source PDF page count, if known. Enables chars_per_page.
    """
    from .config import CONFIG as _DEFAULT

    cfg = config or _DEFAULT

    # NFC everywhere. macOS hands back NFD for accented content and the
    # difference silently changes token counts and script decisions.
    text = unicodedata.normalize("NFC", text)

    out: dict[str, object] = {
        "n_chars": len(text),
        "n_lines": text.count("\n") + 1 if text else 0,
    }

    if len(text) < cfg["MIN_CHARS"]:
        out["language"] = language or "unknown"
        out["too_short"] = True
        for key in cfg["METRIC_SPEC"]:
            out[key] = None
        out["chars_per_page"] = None
        return out

    out["too_short"] = False
    tokens = tokenize(text)
    out["n_tokens"] = len(tokens)

    # Structure metrics look at prose only; character-damage metrics look at
    # everything, since damage anywhere counts.
    prose = prose_lines(text)
    prose_tokens = tokenize_all(prose)
    out["n_prose_tokens"] = len(prose_tokens)

    lang = language or detect_language(text)
    out["language"] = lang

    n = cfg["REPEAT_NGRAM_N"]
    out["script_mix_ratio"] = script_mix_ratio(tokens)
    out["gzip_ratio"] = gzip_ratio(text)
    out["top_ngram_coverage"] = ngram_coverage(prose_tokens, n=n)
    out["tail_ngram_coverage"] = tail_ngram_coverage(
        prose_tokens, n=n, tail=cfg["TAIL_FRACTION"]
    )
    out["dup_line_run"] = dup_line_run(prose)
    out["junk_char_rate"] = junk_char_rate(text)
    out["mojibake_rate"] = mojibake_rate(text)
    out["mean_token_len"] = mean_token_len(tokens)
    out["short_token_run"] = short_token_run(tokenize(prose))

    if lang in cfg["VOWEL_CHECK_LANGS"]:
        out["vowelless_ratio"] = vowelless_ratio(
            tokenize(prose), min_len=cfg["VOWELLESS_MIN_TOKEN_LEN"]
        )
    else:
        # Consonant-cluster languages would flood this metric with false
        # positives, so it is left undefined and dropped from the score.
        out["vowelless_ratio"] = None

    if n_pages and n_pages > 0:
        out["chars_per_page"] = len(text) / n_pages
    else:
        out["chars_per_page"] = None

    return out
