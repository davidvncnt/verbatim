# Real-document test corpus

This folder is empty in the repository on purpose: source PDFs are not
committed. Put real documents here locally and the corpus-marked tests start
running against them automatically.

What is worth having here, from `docs/brief.md` §8:

- a clean born-digital decision
- a two-column page
- a page with a table printed sideways
- a good scan and a genuinely bad one
- one document per language in the corpus (English, French, Spanish)
- **whatever broke the earlier Mistral OCR attempt** — those are the most
  valuable files in the set, because they are the only known instances of the
  failure the tool exists to prevent

Alongside 3–5 of them, a hand-corrected reference `.txt` with the same stem
turns "is this good?" from an opinion into a measurement.

Run them with:

    pytest -m corpus
