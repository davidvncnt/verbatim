"""
verbatim.qa.lexicon — words that do not belong in this material.

A model asked to read an unreadable scan does not fail; it writes something
plausible. What gives it away is vocabulary: a word like "thief" is perfectly
ordinary English and appears in none of the 21,603 decisions of this corpus.

So the expected vocabulary is learned from the corpus itself rather than
guessed. Measured on that corpus, held back from its own training:

* a clean document has a median of **zero** unexpected words;
* a sentence about a thief, a kitten and a pizza is caught;
* about 8% of documents raise at least three — and several of those are
  genuine damage, not false alarms: `proarammes`, `throught`, `gency`.

Two filters keep it from firing on ordinary rare words. A word must appear in
*lower case* somewhere in the document, which excludes proper nouns — the
people, vessels, places and species that make up most of what a corpus has
never seen before. And it must be absent from the corpus entirely, not merely
rare there.

This is evidence that something is worth reading, never proof of invention, so
it is reported as "worth a look" and never rejects a file on its own. It only
runs where no exact comparison is possible: against a model's output, or with
no PDF at all. Where the words can be checked against a text layer, they are.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

from ..settings import config_dir

TOKEN = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
MIN_LENGTH = 5          # shorter words are too often abbreviations and codes
MIN_SUSPICIOUS = 3      # below this it is one odd word, not a pattern
MAX_REPORTED = 12

_cache: dict = {}


def path() -> Path:
    return config_dir() / "vocabulary.txt"


def words_of(text: str) -> Counter:
    return Counter(unicodedata.normalize("NFC", m.group(0)).casefold()
                   for m in TOKEN.finditer(text))


def build(folder: Path, min_documents: int = 1, out: Path | None = None,
          log=print) -> Path:
    """Learn the expected vocabulary from a folder of accepted text.

    `min_documents` is how many separate documents a word must appear in to
    count as expected. One is deliberate: a larger vocabulary flags less, and
    not crying wolf matters more here than catching every invented word.
    """
    folder = Path(folder)
    documents = Counter()
    total = 0
    for p in sorted(folder.rglob("*.txt")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += 1
        documents.update(set(words_of(text)))
        if total % 5000 == 0:
            log(f"   {total} documents read")
    vocabulary = sorted(w for w, n in documents.items() if n >= min_documents)
    out = Path(out) if out else path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(vocabulary), encoding="utf-8")
    log(f"{len(vocabulary):,} words learned from {total:,} documents -> {out}")
    _cache.clear()
    return out


def load(where: Path | None = None) -> set:
    """The vocabulary, or an empty set when none has been built."""
    where = Path(where) if where else path()
    key = str(where)
    try:
        stamp = where.stat().st_mtime_ns
    except OSError:
        return set()
    if _cache.get("key") != (key, stamp):
        _cache["key"] = (key, stamp)
        _cache["words"] = set(where.read_text(encoding="utf-8").split("\n"))
    return _cache["words"]


def suspicious_words(text: str, vocabulary: set | None = None) -> list:
    """Words of `text` that this material would not be expected to contain."""
    vocabulary = load() if vocabulary is None else vocabulary
    if not vocabulary:
        return []
    candidates, previous = set(), ""
    for m in TOKEN.finditer(text):
        word = unicodedata.normalize("NFC", m.group(0))
        if (word.islower() and len(word) >= MIN_LENGTH
                # A scientific name writes its species in lower case:
                # "Dissostichus mawsoni". The give-away is the word before —
                # capitalised and itself unknown, so not the start of a
                # sentence about something ordinary.
                and not (previous[:1].isupper()
                         and previous.casefold() not in vocabulary)):
            candidates.add(word)
        previous = word
    return sorted(w for w in candidates if w not in vocabulary)


def locate(text: str, words: list) -> tuple:
    """Where the first of them appears, so the reviewer can go and look."""
    for m in TOKEN.finditer(text):
        if unicodedata.normalize("NFC", m.group(0)) in words:
            return m.start(), m.end()
    return None, None
