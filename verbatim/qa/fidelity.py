"""
verbatim.qa.fidelity — does the output say what the source said?

The rule this module enforces: **every word in the output must come from the
source document.** No paraphrase, no summary, no silent correction of what
looks like a typo, no filled-in gap.

Why counting characters is not enough
-------------------------------------
The original script reported "100% of characters kept". That figure is a
character *count*, so a model that swapped one word for another word of the
same length scores a perfect 100%. It is blind to exactly the failure that made
the earlier pipeline unusable. Every check here compares *which words*, not how
many characters.

The four checks
---------------
1. **Provenance** — every output word must exist in the source, as a word or as
   the join of two adjacent source fragments (which is what de-hyphenation
   legitimately produces). Anything else was invented.
2. **Completeness** — every source word must reach the output, unless it was
   removed on purpose (a running header, a page number, a dropped chart label).
3. **Numerals** — every number and date in the output must appear in the
   source. Treaty texts are numbers-heavy and a hallucinated date is the worst
   failure this tool can produce, so numerals are checked separately and
   weighted highest.
4. **Alignment** — where an independent transcription of the same pages exists,
   the two word sequences are aligned, which distinguishes a dropped block from
   a rewritten passage from ordinary recognition noise.

Checks 1-3 need a text layer to compare against. For pages that had none, there
is no source text to be faithful to, and the honest answer is to say so: those
pages are marked as recognised rather than extracted, and are checked instead by
running a second, independent recognition pass and aligning the two.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from ..extract.text import clean

# Letters and digits only. Punctuation, quotes and hyphens differ legitimately
# between a text layer and a reflowed paragraph; words do not.
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# A numeral, a year, a date or an article reference — anything a reader would
# check against the source rather than read past.
_NUMERAL_RE = re.compile(r"\d+(?:[.,/-]\d+)*")

HIGH, MEDIUM, LOW = "high", "medium", "low"


@dataclass
class Finding:
    """One located, explainable problem with one document.

    `key` and `params` rather than a finished sentence: the reviewer's window
    is bilingual, and a finding that only exists in English is a finding half
    the team cannot act on. `message()` renders English for the CLI and reports.
    """

    kind: str
    severity: str
    key: str
    params: dict = field(default_factory=dict)
    char_start: int | None = None
    char_end: int | None = None
    page: int | None = None
    detail: str = ""

    def message(self, lang: str | None = None) -> str:
        """Plain language, in the reader's language.

        Findings carry a key and its parameters rather than a finished
        sentence: half the team reads French, and a finding they cannot read
        is a finding they cannot act on.
        """
        from ..i18n import t
        return t(self.key, lang, **self.params)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "severity": self.severity, "key": self.key,
                "params": self.params, "char_start": self.char_start,
                "char_end": self.char_end, "page": self.page,
                "detail": self.detail,
                "message_en": self.message("en"),
                "message_fr": self.message("fr")}


# ---------------------------------------------------------------------------
# tokenising
# ---------------------------------------------------------------------------

def normalise_reference(text: str) -> str:
    """Prepare a raw text layer for comparison.

    Newlines become spaces first. clean() drops control characters, and a
    newline is one, so cleaning multi-line text directly would join the last
    word of every line to the first word of the next and invent words that
    were never there. The engine only ever calls clean() on a single assembled
    line, which is why it never hits this.
    """
    return clean(text.replace("\n", " ").replace("\r", " "))


# A word broken at a line break: "mat- ter". The lower-case requirement is the
# same rule the engine applies, so "Franco- German" is left alone on both sides.
_LINEBREAK_HYPHEN_RE = re.compile(r"(\w)[-\u2010\u2011]\s+([a-zà-öø-ÿ])")


def dehyphenate(text: str) -> str:
    """Rejoin words broken at a line break, by the engine's own rule.

    Only for sequence alignment. The word-level check does not use this: it
    matches leftovers instead, which also catches the case this cannot — on a
    two-column page the text layer reads across the gutter, so the two halves
    of a broken word are separated by a whole column of other text.
    """
    return _LINEBREAK_HYPHEN_RE.sub(r"\1\2", text)


def tokens_with_spans(text: str) -> list:
    """[(normalised token, char_start, char_end)] over the given text."""
    return [(m.group(0).casefold(), m.start(), m.end())
            for m in _TOKEN_RE.finditer(unicodedata.normalize("NFC", text))]


def words(text: str) -> list:
    """Normalised word sequence, for comparison only."""
    return [t for t, _, _ in tokens_with_spans(text)]


def _segment(word: str, available: Counter) -> list | None:
    """Split `word` into two or more fragments that are all unmatched leftovers.

    De-hyphenation is the one transformation that legitimately produces a word
    the source does not contain: "mat-" + "ter" becomes "matter". The obvious
    test — allow the concatenation of two *adjacent* source words — is wrong on
    a two-column page, where the text layer reads straight across the gutter,
    so the two halves of a broken word are never adjacent in it.

    Matching against leftovers instead is order-independent and still tight: an
    invented word would have to coincidentally equal the concatenation of words
    that are themselves unaccounted for. Fragments are consumed as they are
    used, so one leftover cannot excuse two different inventions.
    """
    n = len(word)
    if n < 2:
        return None
    reach: list = [None] * (n + 1)      # reach[i] = fragmentation of word[:i]
    reach[0] = []
    for i in range(n):
        if reach[i] is None:
            continue
        for j in range(i + 1, n + 1):
            if reach[j] is not None:
                continue
            part = word[i:j]
            if available.get(part, 0) - Counter(reach[i]).get(part, 0) > 0:
                reach[j] = reach[i] + [part]
    parts = reach[n]
    return parts if parts and len(parts) >= 2 else None


# ---------------------------------------------------------------------------
# 1 & 2. provenance and completeness
# ---------------------------------------------------------------------------

def compare_words(reference_text: str, output_text: str,
                  removed_on_purpose: str = "", *, max_examples: int = 8) -> tuple:
    """(findings, de-hyphenation joins) for words invented and words lost.

    Both directions are multiset comparisons, so a word duplicated in the
    output is reported even though it does exist in the source: duplication is
    how over-extraction shows up.
    """
    ref = words(normalise_reference(reference_text))
    out_tokens = tokens_with_spans(output_text)
    findings: list = []
    if not ref:
        return findings, 0

    ref_counts = Counter(ref)
    out_counts = Counter(t for t, _, _ in out_tokens)
    removed = Counter(words(normalise_reference(removed_on_purpose)))

    extra = out_counts - ref_counts                  # in the text, not the PDF
    lost = ref_counts - out_counts - removed         # in the PDF, not the text

    # Account for de-hyphenation before judging anything: the joined word looks
    # invented and its two halves look lost, and they explain each other.
    joins = 0
    for word in list(extra):
        while extra[word] > 0:
            parts = _segment(word, lost)
            if parts is None:
                break
            for part in parts:
                lost[part] -= 1
                if lost[part] <= 0:
                    del lost[part]
            extra[word] -= 1
            joins += 1
        if extra[word] <= 0:
            del extra[word]

    if extra:
        first_at = {}
        for tok, start, end in out_tokens:
            if tok in extra and tok not in first_at:
                first_at[tok] = (start, end)
        ordered = sorted(extra, key=lambda t: first_at.get(t, (1 << 30,))[0])
        head = ordered[0]
        findings.append(Finding(
            kind="invented_words", severity=HIGH, key="invented_words",
            params={"n": sum(extra.values()),
                    "sample": ", ".join(ordered[:max_examples])},
            char_start=first_at.get(head, (None, None))[0],
            char_end=first_at.get(head, (None, None))[1],
            detail=" ".join(ordered[:50])))

    if lost:
        ordered = sorted(lost, key=lambda t: -lost[t])
        findings.append(Finding(
            kind="dropped_words", severity=MEDIUM, key="dropped_words",
            params={"n": sum(lost.values()),
                    "sample": ", ".join(ordered[:max_examples])},
            detail=" ".join(ordered[:50])))
    return findings, joins


# ---------------------------------------------------------------------------
# 3. numerals
# ---------------------------------------------------------------------------

def compare_numerals(reference_text: str, output_text: str,
                     *, max_examples: int = 8) -> list:
    """Numbers present in the output but not in the source.

    Separate from the word check and weighted higher: a wrong word in a treaty
    text is bad, a wrong date or catch limit is unusable.
    """
    ref = Counter(_NUMERAL_RE.findall(normalise_reference(reference_text)))
    findings: list = []
    seen: Counter = Counter()
    invented = []
    for m in _NUMERAL_RE.finditer(output_text):
        v = m.group(0)
        seen[v] += 1
        if seen[v] > ref.get(v, 0):
            invented.append((v, m.start(), m.end()))
    if invented:
        sample = ", ".join(dict.fromkeys(v for v, _, _ in invented[:max_examples]))
        findings.append(Finding(
            kind="invented_numbers", severity=HIGH, key="invented_numbers",
            params={"n": len(invented), "sample": sample},
            char_start=invented[0][1], char_end=invented[0][2],
            detail=" ".join(v for v, _, _ in invented[:50])))
    return findings


# ---------------------------------------------------------------------------
# retention
# ---------------------------------------------------------------------------

def check_retention(ratio: float, config: dict) -> list:
    if ratio < config["RETENTION_MIN"]:
        return [Finding(kind="retention", severity=MEDIUM, key="retention_low",
                        params={"pct": ratio})]
    if ratio > config["RETENTION_MAX"]:
        return [Finding(kind="retention", severity=MEDIUM, key="retention_high",
                        params={"pct": ratio})]
    return []


# ---------------------------------------------------------------------------
# 4. alignment against an independent transcription
# ---------------------------------------------------------------------------

@dataclass
class Alignment:
    verdict: str                 # OK | MINOR_DRIFT | REWRITTEN | MISSING_BLOCK | INSERTED_BLOCK
    similarity: float
    ref_words: int
    out_words: int
    length_ratio: float
    findings: list = field(default_factory=list)


def _without(sequence: list, removed: Counter) -> list:
    """Drop the words that were removed on purpose, keeping order.

    Running headers, footers and page numbers are deliberately not in the
    output. Without this the reference is longer than the text by exactly the
    furniture that was supposed to go, and every multi-page document reads as
    though a block went missing.
    """
    if not removed:
        return sequence
    owed = Counter(removed)
    out = []
    for tok in sequence:
        if owed.get(tok, 0) > 0:
            owed[tok] -= 1
            continue
        out.append(tok)
    return out


def align(reference_text: str, output_text: str, config: dict,
          removed_on_purpose: str = "") -> Alignment:
    """Align two word sequences and name how they differ.

    **Both sides must be in the same reading order.** This is order-sensitive
    by design — that is what lets it tell a dropped block from a rewritten
    passage — and it is therefore the wrong tool to point at a raw text layer.
    A two-column page's text layer reads straight across the gutter; putting
    the columns in reading order is one of the things the engine is *for*, so
    aligning the output against the raw layer reports the fix as damage. On the
    two-column fixture that scores 0.62 similarity on text that is word-for-word
    correct.

    Use it against a genuinely comparable transcription:

      * a second, independent recognition pass over the same scanned pages
        (the only check available when there is no text layer at all), or
      * a hand-corrected reference .txt, where one exists.

    To check output against a raw text layer, use `compare_words` and
    `compare_numerals` instead: they are multiset comparisons, so they are
    blind to reading order and see only which words are present.
    """
    ref = words(dehyphenate(normalise_reference(reference_text)))
    ref = _without(ref, Counter(words(normalise_reference(removed_on_purpose))))
    out_tokens = tokens_with_spans(output_text)
    out = [t for t, _, _ in out_tokens]
    if not ref:
        return Alignment("NO_REFERENCE", 0.0, 0, len(out), 0.0)

    sm = difflib.SequenceMatcher(None, ref, out, autojunk=False)
    similarity = sm.ratio()

    longest_deleted = longest_inserted = 0
    del_at = ins_at = None
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and i2 - i1 > longest_deleted:
            longest_deleted = i2 - i1
            del_at = (j1, j2)
        if tag in ("insert", "replace") and j2 - j1 > longest_inserted:
            longest_inserted = j2 - j1
            ins_at = (j1, j2)

    length_ratio = len(out) / len(ref)
    block = config["BLOCK_RUN_WORDS"]
    findings: list = []

    def _span(rng):
        """Character range in the output for a token range."""
        if not rng or rng[0] >= len(out_tokens):
            return None, None
        a = out_tokens[rng[0]][1]
        b = out_tokens[min(rng[1], len(out_tokens)) - 1][2]
        return a, b

    if longest_deleted >= block or length_ratio < 0.85:
        verdict = "MISSING_BLOCK"
        a, b = _span(del_at)
        findings.append(Finding(kind="missing_block", severity=HIGH,
                                key="missing_block", params={"n": longest_deleted},
                                char_start=a, char_end=b))
    elif longest_inserted >= block:
        verdict = "INSERTED_BLOCK"
        a, b = _span(ins_at)
        findings.append(Finding(kind="inserted_block", severity=HIGH,
                                key="inserted_block", params={"n": longest_inserted},
                                char_start=a, char_end=b))
    elif similarity < config["SIMILARITY_REWRITTEN"]:
        verdict = "REWRITTEN"
        findings.append(Finding(kind="rewritten", severity=HIGH, key="rewritten",
                                params={"pct": similarity}))
    elif similarity < config["SIMILARITY_OK"]:
        verdict = "MINOR_DRIFT"
        findings.append(Finding(kind="minor_drift", severity=LOW, key="minor_drift",
                                params={"pct": similarity}))
    else:
        verdict = "OK"

    return Alignment(verdict, similarity, len(ref), len(out), length_ratio, findings)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def check_document(output_text: str, reference_text: str, config: dict, *,
                   removed_on_purpose: str = "", retention: float | None = None,
                   has_text_layer: bool = True) -> list:
    """Every check that applies, given what is available to compare against."""
    findings: list = []
    if has_text_layer and reference_text.strip():
        word_findings, _joins = compare_words(
            reference_text, output_text, removed_on_purpose)
        findings += word_findings
        findings += compare_numerals(reference_text, output_text)
    if retention is not None:
        findings += check_retention(retention, config)

    from .scramble import locate, scan
    sc = scan(output_text)
    if sc["scrambled"]:
        hits = locate(output_text, sc["scrambled"])
        findings.append(Finding(
            kind="scrambled_text", severity=HIGH, key="scrambled_text",
            params={"n": len(sc["scrambled"]),
                    "sample": ", ".join(dict.fromkeys(sc["scrambled"][:6]))},
            char_start=hits[0][1] if hits else None,
            char_end=hits[0][2] if hits else None,
            detail=" ".join(sc["scrambled"][:50])))
    return findings


def severity_rank(findings: list) -> int:
    """0 clean, 1 low, 2 medium, 3 high. Used to sort a review queue."""
    order = {LOW: 1, MEDIUM: 2, HIGH: 3}
    return max((order[f.severity] for f in findings), default=0)
