"""
Quality assurance: does the .txt actually say what the PDF said?

Two independent families of check live here.

*Intrinsic* checks (textmetrics, scoring, scramble) read the .txt alone and ask
whether it looks like damaged output — repetition loops, mixed scripts,
mojibake, interleaved glyphs. They need no reference and catch the failures
that have a visible signature.

*Reference* checks (fidelity) compare the .txt against an independent
transcription of the same pages and ask whether the words are the same words.
Only these catch paraphrase, because a paraphrase reads perfectly well and has
no intrinsic signature at all. That is precisely the failure that made the
earlier pipeline unusable.
"""

from .config import CONFIG

__all__ = ["CONFIG"]
