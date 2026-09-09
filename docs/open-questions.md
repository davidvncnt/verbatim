# Open questions for the agreement-importation profile

The `decisions` profile implements a written specification (docs/brief.md §2).
The `agreements` profile does not, because no such specification exists yet.
What is built is a reading of the brief, not a confirmed requirement.

**Assumption currently in force:** for text intended for publication, dropping
content is the worse error, so article numbering is preserved and signature
blocks, party lists and footnotes are kept rather than stripped.

The profile is declarative — a set of format rules rather than code — so
changing any of this is editing a profile, not rewriting the formatter.

## What is needed to settle it

The most useful single answer is **a handful of accepted TXT files** from the
colleagues who do the importation. Those function as the specification, and can
be diffed against what verbatim currently produces.

Failing that:

1. **What does "properly formatted" mean concretely for the website?** Is there
   a written convention, or a set of good and bad examples?
2. **Structure.** Agreement texts have preambles, numbered articles,
   sub-paragraphs, annexes, signature blocks and ratification lists. Preserved
   as plain paragraphs, or marked up? Does the website parse the TXT or display
   it as-is?
3. **Completeness.** Are signature blocks, party lists, depositary notes and
   footnotes wanted, or stripped?
4. **Language versions.** Many agreements are authentic in several languages.
   One file per language? How are they named and linked?
5. **File naming.** Decision files follow
   `ID-number_short-title_year-of-adoption`. Is there a parallel convention for
   agreement texts, and should the tool generate it?
6. **Review step.** Is there a human check before publication? If so the tool
   should optimise for making review fast rather than for producing silently
   finished output — which is what it currently does.
7. **Scale and source.** How many agreements, and where do the PDFs come from?

## Known limitations, both profiles

Carried forward from docs/brief.md §6 and still true:

- **Footnotes** stay where they sit on the page rather than being separated or
  moved; they interrupt the body text flow.
- **Two-column pages containing tables** may order the table wrongly relative
  to the columns.
- **Skew beyond a few degrees**, and page-level warping, are not corrected.
- **Document structure is not labelled.** Headings are preserved as their own
  paragraphs but not numbered or made machine-readable.
- **Language is detected once per file**, not per page.
- **Running headers cannot be detected in a single-page document.** There is no
  repetition to detect, and guessing would risk deleting the title. Page
  numbers are still removed, by pattern.
- **A broken font encoding produces confident garbage** that word-provenance
  checks cannot catch, because the output faithfully matches a source that is
  itself wrong. The interleaving check catches the common case; two interleaved
  lowercase runs leave no signature at all.
