"""
verbatim.i18n — every string the team reads, in English and French.

The window, the log and the findings all resolve through here. The log
especially: it is where a research assistant learns what happened to their
files, and a French interface reporting its results in English would defeat
the point of having one.

Adding a string means adding it to both catalogues. `check_catalogues()` is
run by the test suite, so a missing translation fails the build rather than
reaching someone as a stray English sentence in a French window.
"""

from __future__ import annotations

from .settings import load_prefs, save_prefs

DEFAULT = "en"
LANGUAGES = {"en": "English", "fr": "Français"}

EN = {
    # ---- findings (shared with verbatim.qa.fidelity) --------------------
    "invented_words": "{n} word(s) in the text do not appear in the PDF: {sample}",
    "dropped_words": "{n} word(s) in the PDF do not appear in the text: {sample}",
    "invented_numbers": "{n} number(s) in the text do not appear in the PDF: {sample}",
    "retention_low": "only {pct:.0%} of the letters and digits in the PDF reached the text",
    "retention_high": "{pct:.0%} of the letters and digits in the PDF reached the text — more came out than went in",
    "scrambled_text": "{n} word(s) look scrambled, as if two lines were interleaved: {sample}",
    "missing_block": "a run of {n} words in the source has no counterpart in the text",
    "inserted_block": "a run of {n} words in the text has no counterpart in the source",
    "rewritten": "the wording differs throughout ({pct:.0%} of words match)",
    "minor_drift": "small differences from the source ({pct:.0%} of words match)",
    "ocr_low_confidence": "the recogniser was only {pct:.0%} confident on this file",
    "scan_unreadable": "the scan could not be read well enough to compare the text with it (recognition was only {pct:.0%} confident), so only the text checks ran",
    "model_pages": "{n} page(s) were produced by a model, not extracted — check them against the PDF",
    "passes_disagree": "the two recognition passes disagree on {n} word(s) here",
    "repetition_loop": "the same {n} words repeat over and over — the recogniser looped",
    "no_text_layer": "{n} page(s) hold no text and were not recognised",
    "mixed_scripts": "{n} word(s) mix alphabets (for example Latin and Cyrillic letters), a sign of recognition errors: {sample}",
    "garbled_characters": "some characters were decoded with the wrong encoding (for example “Ã©” instead of “é”)",
    "control_characters": "the text contains invalid or invisible characters",
    "letter_spacing": "letters are separated by spaces, as in “t h e”",
    "degenerate_table": "a table has {pct:.0%} of its cells filled with the same value ({value}) — a recogniser that could not read the table may have invented its contents",
    "unexpected_words": "{n} word(s) here would not be expected in this kind of document, which can mean text was invented: {sample}",
    "duplicated_words": "{n} word(s) appear more often in the text than in the PDF, as if passages were repeated: {sample}",
    "missing_from_text": "a passage of the PDF, outlined on the page, is not in the text (so it cannot be highlighted there): “{sample}”",
    "invented_text": "this passage of the text has no counterpart in the PDF: “{sample}”",
    "invented_text_repeated": "this passage of the text has no counterpart in the PDF, and the text has it {times} times: “{sample}”",
    "unfound_table": "{n} table row(s) here are not in the PDF's text, often because the PDF prints this table as a picture: check them against the page",
    "invented_number": "the number {value} is not in the PDF",
    "invented_numbers_line": "{n} numbers on this line are not in the PDF: {value}",
    "repeated_passage": "this passage is in the text {times} times but in the PDF {in_pdf} time(s): “{sample}”",
    "spelling_variant": "“{word}” is written “{pdf}” in the PDF",
    "sideways_page": "page {page} is printed sideways, usually a table turned to fit the page: earlier conversions often garbled these, so compare this page with the text",
    "not_in_scan": "{n} words here have no equivalent anywhere in the scanned PDF: {sample}",
    "not_in_scan_passage": "this passage of the text has no counterpart in the scanned PDF: “{sample}”",
    "not_in_scan_repeated": "this passage of the text has no counterpart in the scanned PDF, and the text has it {times} times: “{sample}”",
    "scan_mismatch": "the text differs from the scan almost throughout (only {pct:.0%} of it was found in the scan)",
    "scan_unchecked": "{n} page(s) of the PDF are scans that could not be read, so the text could not be compared with them",

    # ---- verdicts -------------------------------------------------------
    "verdict.ok": "OK",
    "verdict.review": "To check",
    "verdict.reject": "Problem found",
    "verdict.unknown": "Not checked",
    "verdict.ok.long": "Nothing to report",
    "verdict.review.long": "Worth a look",
    "verdict.reject.long": "Needs correcting",

    # ---- window: convert -----------------------------------------------
    "app.title": "verbatim — PDF to text",
    "tab.convert": "Convert",
    "tab.review": "Review",
    "group.folders": "Folders",
    "label.input": "PDFs in",
    "label.output": "TXT out",
    "button.browse": "Browse…",
    "check.recursive": "include sub-folders",
    "hint.output": "Leave the output folder empty to write each .txt next to its PDF.",
    "group.scanned": "Scanned PDFs (no selectable text)",
    "label.recognise": "Recognise text",
    "label.using": "using",
    "label.language": "language",
    "label.key": "Mistral key",
    "hint.model_ocr": "Reading scanned PDFs needs a Mistral key. Mistral is a paid "
                      "service and a model, not a character recogniser: pages it "
                      "produces are marked and always need checking.",
    "group.layout": "Layout",
    "label.columns": "Columns",
    "label.tables": "Tables",
    "check.page_marks": "[page N] markers",
    "check.keep_headers": "keep headers/footers",
    "label.profile": "Output format",
    "profile.decisions": "COP decisions",
    "profile.agreements": "Agreement texts",
    "button.convert": "Convert",
    "button.stop": "Stop",
    "status.ready": "Choose a folder of PDFs, then press Convert.",
    "status.stopping": "Stopping…",
    "status.stopped": "Stopped.",
    "status.done": "Done.",

    # ---- window: review -------------------------------------------------
    "review.queue": "Files to check",
    "review.findings": "What to look at",
    "review.page_of": "page {page} of {total}",
    "review.no_findings": "Nothing was flagged in this file.",
    "review.categories": "Kinds of problem…",
    "review.copy_name": "Copy “{name}”",
    "review.copy_names": "Copy the {n} names in the list",
    "review.copied": "Copied: {name}",
    "review.copied_n": "{n} file names",
    "review.hidden_findings": "{n} finding(s) of other kinds are hidden (see “Kinds of problem…”)",
    "categories.title": "Kinds of problem to look for",
    "categories.intro": "Every check always runs. These choices only decide what is shown, and which problems colour a file in the list, so changing them never means checking again. Click a name to see what it looks like and how it is found.",
    "categories.example": "What it looks like",
    "categories.how": "How verbatim finds it",
    "categories.false": "When it raises false alarms",
    "categories.defaults": "Restore the usual choice",
    "categories.close": "Close",
    "cat.invented.title": "Text not in the PDF (hallucinations)",
    "cat.invented.example": "A sentence, a reference or a sequence that appears nowhere in the PDF: a bibliography entry repeated 23 times, a DNA sequence with letters changed, or a note left by the model such as “No text content to extract, only flowchart”.",
    "cat.invented.how": "The text and the PDF are both reduced to their letters and digits: no spaces, punctuation, accents or capitals. Each stretch of the text is then looked for in the PDF, in any order. A stretch of 25 letters or more found nowhere is reported. A typo, a missing space or a lost accent does not leave such a gap; an invented sentence does. For a scanned PDF the comparison is with the recogniser's reading of the page.",
    "cat.invented.false": "Web addresses and identifiers the PDF only holds as links; text the PDF only has as a picture (logos, diagrams). For scans, a passage the recogniser misread badly.",
    "cat.numbers.title": "Numbers not in the PDF",
    "cat.numbers.example": "The text says 2009 where the PDF says 2008, or a quota of 13,930 that the PDF does not contain.",
    "cat.numbers.how": "Every number in the text is looked for in the PDF by its digits alone, so 1 000, 1,000 and 1000 are the same number. A range such as 165-171 is checked bound by bound. Numbers on one line are reported together.",
    "cat.numbers.false": "Numbers that the PDF prints only as a picture. A number changed into another number that also appears elsewhere in the PDF is not detected.",
    "cat.tables.title": "Tables not found, or filled with one value",
    "cat.tables.example": "Table rows whose cells are not in the PDF's text at all, or a table where every cell holds the same value, such as a column of “1”.",
    "cat.tables.how": "Each cell of a table row is looked for in the PDF. A row where most cells are not found is reported, once per table rather than once per cell.",
    "cat.tables.false": "Very often: the PDF prints the table as a picture, so its text cannot be checked automatically. Compare the table with the page.",
    "cat.repeated.title": "Repeated text",
    "cat.repeated.example": "A paragraph copied several times, or a sentence that loops.",
    "cat.repeated.how": "A line the text holds more often than the PDF does is reported at each extra copy. A loop is recognised in the text alone.",
    "cat.repeated.false": "Rare. Formulas a decision legitimately repeats are only reported if the text repeats them more often than the PDF.",
    "cat.scrambled.title": "Scrambled text",
    "cat.scrambled.example": "“MobIsNeDrFvaUtLio n”, “l e t t e r s   s p a c e d   o u t”, or letters from two alphabets in one word.",
    "cat.scrambled.how": "The text is read on its own, without the PDF, looking for these patterns.",
    "cat.scrambled.false": "Codes, chemical formulas and names written in capitals.",
    "cat.scan.title": "Scans that could not be checked",
    "cat.scan.example": "Pages of the PDF that are pictures the recogniser could not read, or read with low confidence.",
    "cat.scan.how": "verbatim reports where it could not compare the text with the PDF, so that a file is not taken as verified when it was not.",
    "cat.scan.false": "These are not errors in the text: they say where verbatim could not help.",
    "cat.sideways.title": "Pages printed sideways",
    "cat.sideways.example": "A wide table turned a quarter-turn to fit a portrait page. Earlier conversions often read these column by column, or mixed up the rows.",
    "cat.sideways.how": "The direction of the text on each page of the PDF: a page where most of it runs up or down the page is pointed out, with the lines of the text that come from it.",
    "cat.sideways.false": "None as such: the page is sideways. But it is shown even when nothing is wrong with the text, because values put in the wrong row or column cannot be seen by comparing letters. Scanned pages are not detected, only pages with a text layer.",
    "cat.encoding.title": "Encoding errors",
    "cat.encoding.example": "“lâ€™Organisation” instead of “l’Organisation”, or “Ã©” instead of “é”.",
    "cat.encoding.how": "Character sequences typical of a file decoded with the wrong encoding. They do not affect the comparison with the PDF, which reads past them.",
    "cat.encoding.false": "Rare: these are real, but they are mechanical and can be corrected all at once rather than file by file.",
    "cat.spelling.title": "Small spelling differences",
    "cat.spelling.example": "“Starmmer” for “Starmer”, a missing or extra letter, two letters swapped.",
    "cat.spelling.how": "A word of the text that is not in the PDF, but is one letter away from a word that is (two for long words).",
    "cat.spelling.false": "Often the PDF itself is wrong: accents lost or ligatures undecoded in its text layer. Real ones are nearly always harmless.",
    "cat.missing.title": "Text of the PDF missing from the TXT",
    "cat.missing.example": "A paragraph of the PDF that is not in the text.",
    "cat.missing.how": "Each passage of 60 letters or more of the PDF is looked for in the text. Footnotes, text printed sideways in the margins, and running headers and page numbers are left out. The passage is outlined on the page of the PDF: it is not in the text, so it cannot be highlighted there.",
    "cat.missing.false": "Very often when the texts were shortened on purpose — another decision in the same PDF, an annex, a cover page.",
    "review.no_findings_text_only": "The text checks flagged nothing — the text has not been compared with its PDF.",
    "review.open_folder": "Open a folder of text files",
    "review.accept": "Accept",
    "review.needs_work": "Needs work",
    "review.reject": "Reject",
    "review.reviewer": "Checked by",
    "review.note": "Note (optional)",
    "review.decision_hint": "Your name and note are saved with your decision, "
                            "so the team can see who checked each file and why. "
                            "Your name is remembered for next time.",
    # Short names for kinds of problem, for the filter and the summary.
    "kind.invented_words": "Words not in the PDF",
    "kind.invented_text": "Text not in the PDF",
    "kind.unfound_table": "Table not in the PDF's text",
    "kind.spelling_variants": "Small spelling differences",
    "kind.sideways_page": "Page printed sideways",
    "kind.invented_numbers": "Numbers not in the PDF",
    "kind.missing_from_text": "Missing from the text",
    "kind.dropped_words": "Words dropped",
    "kind.duplicated_words": "Repeated passages",
    "kind.not_in_scan": "Not found in the scan",
    "kind.scan_mismatch": "Differs from the scan",
    "kind.scan_unchecked": "Scan could not be read",
    "kind.repetition_loop": "Repetition loop",
    "kind.scrambled_text": "Scrambled words",
    "kind.mixed_scripts": "Mixed alphabets",
    "kind.garbled_characters": "Garbled characters",
    "kind.control_characters": "Invalid characters",
    "kind.letter_spacing": "Spaced-out letters",
    "kind.degenerate_table": "Table filled with one value",
    "kind.unexpected_words": "Unexpected words",
    "kind.retention": "Too little or too much text",
    "kind.model_pages": "Pages made by a model",
    "kind.ocr_confidence": "Low recognition confidence",
    "kind.no_text_layer": "Pages with no text",
    "kind.rewritten": "Wording differs throughout",
    "kind.minor_drift": "Small differences",
    "kind.missing_block": "A block is missing",
    "kind.inserted_block": "A block was added",

    "review.filter": "Show",
    "review.filter.all": "Everything",
    "review.summary": "Summary…",
    "summary.title": "Review summary",
    "summary.folder": "Folder: {path}",
    "summary.files": "{n} text file(s)",
    "summary.decided": "{done} checked by a person, {left} still to check",
    "summary.by_decision": "Decisions",
    "decided.accepted": "Accepted",
    "decided.needs_work": "Needs work",
    "decided.rejected": "Rejected",
    "summary.by_verdict": "What verbatim found",
    "summary.by_problem": "Kinds of problem",
    "summary.reviewers": "Who checked",
    "summary.overruled": "{n} file(s) where the person and the tool disagreed",
    "summary.none": "Nothing has been checked in this folder yet.",
    "summary.export": "Export as CSV…",
    "summary.exported": "Written to {path}",
    "summary.close": "Close",
    "review.pdf_folder": "PDF folder",
    "review.text_only": "Text checks only (no PDF)",
    "review.confidence": "Trust a scan read at least",
    "review.triage": "Sorting the folder: {done} of {total} files read",
    "review.checking": "Checking {name}…",
    "review.checking_pages": "Checking {name}: page {done} of {total}",
    "review.check_failed": "{name} could not be checked: {error}",
    "review.local_only": "The checks and your decision for this file are saved on this computer only.",
    "review.notice.text_only": "Text checks only: the PDF was not used.\n\n"
                               "These checks find repeated, scrambled or garbled "
                               "text. Without the PDF, a passage that reads well "
                               "but is not in the source cannot be detected.",
    "review.notice.no_pdf": "No PDF named {pdf} was found in the PDF folder or "
                            "next to the text file.\n\n"
                            "Only the text checks ran. Without the PDF, a passage "
                            "that reads well but is not in the source cannot be "
                            "detected.\n\n"
                            "Choose the folder that contains the PDFs in "
                            "“PDF folder” above.",
    "review.name_required": "Enter your name in “Checked by” before recording a decision.",
    "review.empty.no_folder": "This folder does not exist:\n{path}",
    "review.empty.no_txt": "This folder contains no .txt files.\n\n"
                           "Open the output folder you chose in the Convert tab.",
    "review.saved": "Saved for {name}: {verdict} ({who}).",
    "review.nothing_loaded": "No converted files loaded yet.",
    "review.extracted": "extracted from the PDF's own text",
    "review.recognised_tesseract": "recognised from an image",
    "review.recognised_model": "produced by a model — check every word",
    "review.jump": "Go to this passage",
    "review.done_count": "Decided: {done} of {total}",
    "review.batch.start": "Analyse",
    "review.batch.stop": "Stop",
    "review.batch.all": "all files",
    "review.batch.n": "the next {n}",
    "review.batch.nothing": "Every file in the list has already been analysed.",
    "review.batch.progress": "Analysing: {done} of {total} files",
    "review.batch.page": "(page {done} of {total})",
    "review.batch.minutes": "about {n} min left",
    "review.batch.hours": "about {n} h left",
    "review.batch.finished": "Analysis finished: {done} files analysed.",
    "review.batch.stopped": "Analysis stopped: {done} of {total} files analysed.",
    "review.batch.failed": "{n} could not be analysed.",
    "review.batch.after_triage": "The analysis will start as soon as the folder is sorted, "
                                 "so that the most suspect files go first.",
    "review.batch.next": "analysis next",
    "review.batch.cancelled": "Analysis cancelled before it started.",

    # ---- log ------------------------------------------------------------
    "log.files_found": "{n} PDF(s) to convert",
    "log.no_files": "No PDF found in {path}",
    "log.no_files_hint": "Tick 'include sub-folders' if they are nested.",
    "log.no_folder": "This folder does not exist: {path}",
    "log.ocr_ready": "Text recognition ready: {note}",
    "log.ocr_unavailable": "Text recognition unavailable, scanned pages will stay empty: {note}",
    "log.file_line": "[{n}/{total}] {name}",
    "log.summary": "{pages} pages, {tables} table(s), {dropped} header/footer line(s) removed",
    "log.twocol": "{n} two-column page(s)",
    "log.ocr_pages": "{n} page(s) recognised",
    "log.ocr_conf": "confidence {pct:.0%}",
    "log.kept": "{pct:.0%} of characters kept",
    "log.failed": "FAILED: {error}",
    "log.finished": "Finished: {done} converted",
    "log.finished_failed": "{n} failed",
    "log.finished_review": "{n} need checking",
    "log.unexpected": "Unexpected error: {error}",
    "log.no_text_pages": "pages {pages} hold no text and recognition is off",
    "log.record_failed": "could not write the record: {error}",

    # ---- setup ----------------------------------------------------------
    "setup.title": "One thing to install",
    "setup.tesseract_missing": "Reading scanned PDFs needs Tesseract, which is "
                               "not installed yet. Everything else works without it.",
    "setup.macos": "On macOS, in Terminal:",
    "setup.windows": "On Windows, download and run the installer:",
    "setup.linux": "On Linux:",
    "setup.recheck": "Check again",
    "setup.skip": "Continue without it",
    "setup.ok": "Tesseract {version} found.",
    "header.no_baseline": "no corpus baseline — absolute checks only",
    "check.summary": "{flagged} of {total} file(s) need attention.",
    "check.no_record": "{name}: no record — convert it with verbatim first",
    "check.no_files": "No .txt files found.",
    "check.no_baseline": "(no corpus baseline: absolute quality checks only — "
                         "run 'verbatim audit' to build one)",
}

FR = {
    # ---- constats -------------------------------------------------------
    "invented_words": "{n} mot(s) du texte ne figurent pas dans le PDF : {sample}",
    "dropped_words": "{n} mot(s) du PDF ne figurent pas dans le texte : {sample}",
    "invented_numbers": "{n} nombre(s) du texte ne figurent pas dans le PDF : {sample}",
    "retention_low": "seulement {pct:.0%} des lettres et des chiffres du PDF se retrouvent dans le texte",
    "retention_high": "{pct:.0%} des lettres et des chiffres du PDF se retrouvent dans le texte — il en ressort plus qu'il n'en est entré",
    "scrambled_text": "{n} mot(s) semblent brouillés, comme si deux lignes s'étaient entremêlées : {sample}",
    "missing_block": "une suite de {n} mots de la source n'a aucun équivalent dans le texte",
    "inserted_block": "une suite de {n} mots du texte n'a aucun équivalent dans la source",
    "rewritten": "la formulation diffère d'un bout à l'autre ({pct:.0%} des mots concordent)",
    "minor_drift": "légers écarts par rapport à la source ({pct:.0%} des mots concordent)",
    "ocr_low_confidence": "la reconnaissance n'est sûre qu'à {pct:.0%} pour ce fichier",
    "scan_unreadable": "la numérisation n'a pas pu être lue assez bien pour y comparer le texte (reconnaissance sûre à {pct:.0%} seulement) : seules les vérifications du texte ont été faites",
    "model_pages": "{n} page(s) ont été produites par un modèle, non extraites — à vérifier avec le PDF",
    "passes_disagree": "les deux passes de reconnaissance divergent sur {n} mot(s) ici",
    "repetition_loop": "les mêmes {n} mots se répètent sans fin — la reconnaissance a bouclé",
    "no_text_layer": "{n} page(s) ne contiennent aucun texte et n'ont pas été reconnues",
    "mixed_scripts": "{n} mot(s) mélangent des alphabets (par exemple des lettres latines et cyrilliques), signe d'erreurs de reconnaissance : {sample}",
    "garbled_characters": "des caractères ont été décodés avec le mauvais encodage (par exemple « Ã© » au lieu de « é »)",
    "control_characters": "le texte contient des caractères invalides ou invisibles",
    "letter_spacing": "des lettres sont séparées par des espaces, comme dans « l e s »",
    "degenerate_table": "un tableau a {pct:.0%} de ses cellules remplies avec la même valeur ({value}) — une reconnaissance incapable de lire le tableau a pu en inventer le contenu",
    "unexpected_words": "{n} mot(s) ici seraient inattendus dans ce type de document, ce qui peut signaler du texte inventé : {sample}",
    "duplicated_words": "{n} mot(s) apparaissent plus souvent dans le texte que dans le PDF, comme si des passages étaient répétés : {sample}",
    "missing_from_text": "un passage du PDF, encadré sur la page, ne figure pas dans le texte (il ne peut donc pas y être surligné) : « {sample} »",
    "invented_text": "ce passage du texte n'a aucun équivalent dans le PDF : « {sample} »",
    "invented_text_repeated": "ce passage du texte n'a aucun équivalent dans le PDF, et le texte le contient {times} fois : « {sample} »",
    "unfound_table": "{n} ligne(s) de tableau ici ne figurent pas dans le texte du PDF, souvent parce que le PDF imprime ce tableau comme une image : à comparer avec la page",
    "invented_number": "le nombre {value} ne figure pas dans le PDF",
    "invented_numbers_line": "{n} nombres de cette ligne ne figurent pas dans le PDF : {value}",
    "repeated_passage": "ce passage figure {times} fois dans le texte mais {in_pdf} fois dans le PDF : « {sample} »",
    "spelling_variant": "« {word} » s'écrit « {pdf} » dans le PDF",
    "sideways_page": "la page {page} est imprimée à l'horizontale, en général un tableau tourné pour tenir dans la page : les anciennes conversions les ont souvent abîmées, comparez cette page avec le texte",
    "not_in_scan": "{n} mots ici n'ont aucun équivalent dans le PDF numérisé : {sample}",
    "not_in_scan_passage": "ce passage du texte n'a aucun équivalent dans le PDF numérisé : « {sample} »",
    "not_in_scan_repeated": "ce passage du texte n'a aucun équivalent dans le PDF numérisé, et le texte le contient {times} fois : « {sample} »",
    "scan_mismatch": "le texte diffère de la numérisation presque partout (seulement {pct:.0%} y a été retrouvé)",
    "scan_unchecked": "{n} page(s) du PDF sont des numérisations illisibles pour l'outil : le texte n'a pas pu être comparé avec elles",

    # ---- verdicts -------------------------------------------------------
    "verdict.ok": "Correct",
    "verdict.review": "À vérifier",
    "verdict.reject": "Problème détecté",
    "verdict.unknown": "Non vérifié",
    "verdict.ok.long": "Rien à signaler",
    "verdict.review.long": "Mérite un coup d'œil",
    "verdict.reject.long": "À corriger",

    # ---- fenêtre : conversion -------------------------------------------
    "app.title": "verbatim — PDF vers texte",
    "tab.convert": "Convertir",
    "tab.review": "Vérifier",
    "group.folders": "Dossiers",
    "label.input": "PDF dans",
    "label.output": "TXT vers",
    "button.browse": "Parcourir…",
    "check.recursive": "inclure les sous-dossiers",
    "hint.output": "Laissez le dossier de sortie vide pour écrire chaque .txt à côté de son PDF.",
    "group.scanned": "PDF numérisés (sans texte sélectionnable)",
    "label.recognise": "Reconnaître le texte",
    "label.using": "avec",
    "label.language": "langue",
    "label.key": "Clé Mistral",
    "hint.model_ocr": "La lecture des PDF numérisés nécessite une clé Mistral. "
                      "Mistral est un service payant et un modèle, non un lecteur "
                      "de caractères : les pages qu'il produit sont signalées et "
                      "doivent toujours être vérifiées.",
    "group.layout": "Mise en page",
    "label.columns": "Colonnes",
    "label.tables": "Tableaux",
    "check.page_marks": "marqueurs [page N]",
    "check.keep_headers": "conserver en-têtes et pieds de page",
    "label.profile": "Format de sortie",
    "profile.decisions": "Décisions des COP",
    "profile.agreements": "Textes d'accords",
    "button.convert": "Convertir",
    "button.stop": "Arrêter",
    "status.ready": "Choisissez un dossier de PDF, puis cliquez sur Convertir.",
    "status.stopping": "Arrêt en cours…",
    "status.stopped": "Arrêté.",
    "status.done": "Terminé.",

    # ---- fenêtre : vérification -----------------------------------------
    "review.queue": "Fichiers à vérifier",
    "review.findings": "À examiner",
    "review.page_of": "page {page} sur {total}",
    "review.no_findings": "Rien n'a été signalé dans ce fichier.",
    "review.categories": "Types de problèmes…",
    "review.copy_name": "Copier « {name} »",
    "review.copy_names": "Copier les {n} noms de la liste",
    "review.copied": "Copié : {name}",
    "review.copied_n": "{n} noms de fichiers",
    "review.hidden_findings": "{n} signalement(s) d'autres types sont masqués (voir « Types de problèmes… »)",
    "categories.title": "Types de problèmes à rechercher",
    "categories.intro": "Toutes les vérifications sont toujours faites. Ces choix décident seulement de ce qui est affiché et des problèmes qui colorent un fichier dans la liste : les changer ne demande jamais de tout revérifier. Cliquez sur un nom pour voir à quoi il ressemble et comment il est détecté.",
    "categories.example": "À quoi ça ressemble",
    "categories.how": "Comment verbatim le détecte",
    "categories.false": "Quand il y a de fausses alertes",
    "categories.defaults": "Revenir au choix habituel",
    "categories.close": "Fermer",
    "cat.invented.title": "Texte absent du PDF (hallucinations)",
    "cat.invented.example": "Une phrase, une référence ou une séquence qu'on ne trouve nulle part dans le PDF : une référence bibliographique répétée 23 fois, une séquence d'ADN aux lettres changées, ou une remarque laissée par le modèle comme « No text content to extract, only flowchart ».",
    "cat.invented.how": "Le texte et le PDF sont tous deux réduits à leurs lettres et chiffres : sans espaces, ponctuation, accents ni majuscules. Chaque passage du texte est ensuite cherché dans le PDF, dans n'importe quel ordre. Un passage de 25 lettres ou plus introuvable est signalé. Une faute de frappe, une espace manquante ou un accent perdu ne laissent pas un tel trou ; une phrase inventée, si. Pour un PDF numérisé, la comparaison se fait avec la lecture de l'image par l'outil de reconnaissance.",
    "cat.invented.false": "Adresses web et identifiants que le PDF ne contient que sous forme de liens ; texte que le PDF n'a qu'en image (logos, schémas). Pour les numérisations, un passage très mal lu par la reconnaissance.",
    "cat.numbers.title": "Nombres absents du PDF",
    "cat.numbers.example": "Le texte indique 2009 là où le PDF dit 2008, ou un quota de 13 930 que le PDF ne contient pas.",
    "cat.numbers.how": "Chaque nombre du texte est cherché dans le PDF d'après ses seuls chiffres : 1 000, 1,000 et 1000 sont le même nombre. Un intervalle comme 165-171 est vérifié borne par borne. Les nombres d'une même ligne sont signalés ensemble.",
    "cat.numbers.false": "Nombres que le PDF n'imprime qu'en image. Un nombre remplacé par un autre qui figure aussi ailleurs dans le PDF n'est pas détecté.",
    "cat.tables.title": "Tableaux introuvables ou remplis d'une seule valeur",
    "cat.tables.example": "Des lignes de tableau dont les cellules ne figurent pas du tout dans le texte du PDF, ou un tableau dont toutes les cases ont la même valeur, comme une colonne de « 1 ».",
    "cat.tables.how": "Chaque cellule d'une ligne de tableau est cherchée dans le PDF. Une ligne dont la plupart des cellules sont introuvables est signalée, une fois par tableau et non une fois par cellule.",
    "cat.tables.false": "Très souvent : le PDF imprime le tableau comme une image, et son texte ne peut pas être vérifié automatiquement. Comparez le tableau avec la page.",
    "cat.repeated.title": "Texte répété",
    "cat.repeated.example": "Un paragraphe recopié plusieurs fois, ou une phrase qui tourne en boucle.",
    "cat.repeated.how": "Une ligne présente plus souvent dans le texte que dans le PDF est signalée à chaque copie en trop. Une boucle se repère dans le texte seul.",
    "cat.repeated.false": "Rares. Les formules qu'une décision répète légitimement ne sont signalées que si le texte les répète plus souvent que le PDF.",
    "cat.scrambled.title": "Texte brouillé",
    "cat.scrambled.example": "« MobIsNeDrFvaUtLio n », « l e t t r e s   e s p a c é e s », ou des lettres de deux alphabets dans un même mot.",
    "cat.scrambled.how": "Le texte est lu seul, sans le PDF, à la recherche de ces motifs.",
    "cat.scrambled.false": "Codes, formules chimiques et noms écrits en majuscules.",
    "cat.scan.title": "Numérisations impossibles à vérifier",
    "cat.scan.example": "Des pages du PDF qui sont des images que l'outil de reconnaissance n'a pas pu lire, ou a lues avec peu d'assurance.",
    "cat.scan.how": "verbatim indique où il n'a pas pu comparer le texte au PDF, pour qu'un fichier ne passe pas pour vérifié alors qu'il ne l'est pas.",
    "cat.scan.false": "Ce ne sont pas des erreurs du texte : elles disent où verbatim n'a pas pu aider.",
    "cat.sideways.title": "Pages imprimées à l'horizontale",
    "cat.sideways.example": "Un grand tableau tourné d'un quart de tour pour tenir dans une page portrait. Les anciennes conversions les lisaient souvent colonne par colonne, ou mélangeaient les lignes.",
    "cat.sideways.how": "Le sens du texte sur chaque page du PDF : une page dont le texte monte ou descend est signalée, avec les lignes du texte qui en viennent.",
    "cat.sideways.false": "Aucune à proprement parler : la page est bien tournée. Mais elle est signalée même quand le texte est correct, car des valeurs placées dans la mauvaise ligne ou colonne ne se voient pas en comparant les lettres. Seules les pages qui ont une couche texte sont détectées, pas les numérisations.",
    "cat.encoding.title": "Erreurs d'encodage",
    "cat.encoding.example": "« lâ€™Organisation » au lieu de « l’Organisation », ou « Ã© » au lieu de « é ».",
    "cat.encoding.how": "Suites de caractères typiques d'un fichier décodé avec le mauvais encodage. Elles ne gênent pas la comparaison avec le PDF, qui passe outre.",
    "cat.encoding.false": "Rares : ces erreurs sont réelles, mais mécaniques, et peuvent être corrigées toutes à la fois plutôt que fichier par fichier.",
    "cat.spelling.title": "Petites différences d'orthographe",
    "cat.spelling.example": "« Starmmer » au lieu de « Starmer », une lettre en trop ou en moins, deux lettres inversées.",
    "cat.spelling.how": "Un mot du texte absent du PDF, mais à une lettre près d'un mot du PDF (deux pour les mots longs).",
    "cat.spelling.false": "Souvent, c'est le PDF qui est fautif : accents perdus ou ligatures mal décodées dans son texte. Les vraies fautes sont presque toujours sans conséquence.",
    "cat.missing.title": "Texte du PDF absent du TXT",
    "cat.missing.example": "Un paragraphe du PDF qui n'a pas été repris dans le texte.",
    "cat.missing.how": "Chaque passage de 60 lettres ou plus du PDF est cherché dans le texte. Les notes de bas de page, le texte imprimé à la verticale dans les marges, les en-têtes et les numéros de page sont ignorés. Le passage est encadré sur la page du PDF : il n'est pas dans le texte, il ne peut donc pas y être surligné.",
    "cat.missing.false": "Très souvent quand les textes ont été raccourcis volontairement : autre décision du même PDF, annexe, page de couverture.",
    "review.no_findings_text_only": "Les vérifications du texte n'ont rien signalé — le texte n'a pas été comparé à son PDF.",
    "review.open_folder": "Ouvrir un dossier de fichiers texte",
    "review.accept": "Accepter",
    "review.needs_work": "À retravailler",
    "review.reject": "Rejeter",
    "review.reviewer": "Vérifié par",
    "review.note": "Remarque (facultatif)",
    "review.decision_hint": "Votre nom et votre remarque sont enregistrés avec "
                            "votre décision, pour que l'équipe sache qui a vérifié "
                            "chaque fichier et pourquoi. Votre nom est retenu "
                            "pour la prochaine fois.",
    # Noms courts des types de problème, pour le filtre et le résumé.
    "kind.invented_words": "Mots absents du PDF",
    "kind.invented_text": "Texte absent du PDF",
    "kind.unfound_table": "Tableau absent du texte du PDF",
    "kind.spelling_variants": "Petites différences d'orthographe",
    "kind.sideways_page": "Page imprimée à l'horizontale",
    "kind.invented_numbers": "Nombres absents du PDF",
    "kind.missing_from_text": "Manque dans le texte",
    "kind.dropped_words": "Mots perdus",
    "kind.duplicated_words": "Passages répétés",
    "kind.not_in_scan": "Introuvable dans la numérisation",
    "kind.scan_mismatch": "Diffère de la numérisation",
    "kind.scan_unchecked": "Numérisation illisible",
    "kind.repetition_loop": "Répétition en boucle",
    "kind.scrambled_text": "Mots brouillés",
    "kind.mixed_scripts": "Alphabets mélangés",
    "kind.garbled_characters": "Caractères mal décodés",
    "kind.control_characters": "Caractères invalides",
    "kind.letter_spacing": "Lettres espacées",
    "kind.degenerate_table": "Tableau rempli d'une seule valeur",
    "kind.unexpected_words": "Mots inattendus",
    "kind.retention": "Trop peu ou trop de texte",
    "kind.model_pages": "Pages produites par un modèle",
    "kind.ocr_confidence": "Reconnaissance peu fiable",
    "kind.no_text_layer": "Pages sans texte",
    "kind.rewritten": "Formulation différente partout",
    "kind.minor_drift": "Petits écarts",
    "kind.missing_block": "Un bloc manque",
    "kind.inserted_block": "Un bloc a été ajouté",

    "review.filter": "Afficher",
    "review.filter.all": "Tout",
    "review.summary": "Résumé…",
    "summary.title": "Résumé des vérifications",
    "summary.folder": "Dossier : {path}",
    "summary.files": "{n} fichier(s) texte",
    "summary.decided": "{done} vérifiés par une personne, {left} encore à vérifier",
    "summary.by_decision": "Décisions",
    "decided.accepted": "Acceptés",
    "decided.needs_work": "À retravailler",
    "decided.rejected": "Rejetés",
    "summary.by_verdict": "Ce que verbatim a trouvé",
    "summary.by_problem": "Types de problème",
    "summary.reviewers": "Qui a vérifié",
    "summary.overruled": "{n} fichier(s) où la personne et l'outil ne sont pas d'accord",
    "summary.none": "Rien n'a encore été vérifié dans ce dossier.",
    "summary.export": "Exporter en CSV…",
    "summary.exported": "Écrit dans {path}",
    "summary.close": "Fermer",
    "review.pdf_folder": "Dossier des PDF",
    "review.text_only": "Vérifier le texte seulement (sans PDF)",
    "review.confidence": "Fiabilité minimale de la numérisation",
    "review.triage": "Tri du dossier : {done} fichiers lus sur {total}",
    "review.checking": "Vérification de {name}…",
    "review.checking_pages": "Vérification de {name} : page {done} sur {total}",
    "review.check_failed": "{name} n'a pas pu être vérifié : {error}",
    "review.local_only": "Les vérifications et votre décision pour ce fichier sont enregistrées sur cet ordinateur seulement.",
    "review.notice.text_only": "Vérification du texte seulement : le PDF n'a pas été utilisé.\n\n"
                               "Ces contrôles repèrent le texte répété, brouillé "
                               "ou mal décodé. Sans le PDF, un passage qui se lit "
                               "bien mais qui ne figure pas dans la source ne "
                               "peut pas être détecté.",
    "review.notice.no_pdf": "Aucun PDF nommé {pdf} n'a été trouvé dans le dossier "
                            "des PDF ni à côté du fichier texte.\n\n"
                            "Seules les vérifications du texte ont été faites. "
                            "Sans le PDF, un passage qui se lit bien mais qui ne "
                            "figure pas dans la source ne peut pas être détecté.\n\n"
                            "Choisissez le dossier qui contient les PDF dans "
                            "« Dossier des PDF » ci-dessus.",
    "review.name_required": "Inscrivez votre nom dans « Vérifié par » avant d'enregistrer une décision.",
    "review.empty.no_folder": "Ce dossier n'existe pas :\n{path}",
    "review.empty.no_txt": "Ce dossier ne contient aucun fichier .txt.\n\n"
                           "Ouvrez le dossier de sortie choisi dans l'onglet Convertir.",
    "review.saved": "Enregistré pour {name} : {verdict} ({who}).",
    "review.nothing_loaded": "Aucun fichier converti n'est chargé.",
    "review.extracted": "extrait du texte même du PDF",
    "review.recognised_tesseract": "reconnu à partir d'une image",
    "review.recognised_model": "produit par un modèle — vérifier chaque mot",
    "review.jump": "Aller à ce passage",
    "review.done_count": "Décision prise : {done} sur {total}",
    "review.batch.start": "Analyser",
    "review.batch.stop": "Arrêter",
    "review.batch.all": "tous les fichiers",
    "review.batch.n": "les {n} suivants",
    "review.batch.nothing": "Tous les fichiers de la liste sont déjà analysés.",
    "review.batch.progress": "Analyse : {done} fichiers sur {total}",
    "review.batch.page": "(page {done} sur {total})",
    "review.batch.minutes": "environ {n} min restantes",
    "review.batch.hours": "environ {n} h restantes",
    "review.batch.finished": "Analyse terminée : {done} fichiers analysés.",
    "review.batch.stopped": "Analyse arrêtée : {done} fichiers analysés sur {total}.",
    "review.batch.failed": "{n} n'ont pas pu être analysés.",
    "review.batch.after_triage": "L'analyse commencera dès que le dossier sera trié, "
                                 "pour prendre d'abord les fichiers les plus suspects.",
    "review.batch.next": "analyse ensuite",
    "review.batch.cancelled": "Analyse annulée avant d'avoir commencé.",

    # ---- journal --------------------------------------------------------
    "log.files_found": "{n} PDF à convertir",
    "log.no_files": "Aucun PDF trouvé dans {path}",
    "log.no_files_hint": "Cochez « inclure les sous-dossiers » s'ils sont imbriqués.",
    "log.no_folder": "Ce dossier n'existe pas : {path}",
    "log.ocr_ready": "Reconnaissance de texte prête : {note}",
    "log.ocr_unavailable": "Reconnaissance de texte indisponible, les pages numérisées resteront vides : {note}",
    "log.file_line": "[{n}/{total}] {name}",
    "log.summary": "{pages} pages, {tables} tableau(x), {dropped} ligne(s) d'en-tête ou de pied de page retirée(s)",
    "log.twocol": "{n} page(s) à deux colonnes",
    "log.ocr_pages": "{n} page(s) reconnues",
    "log.ocr_conf": "fiabilité {pct:.0%}",
    "log.kept": "{pct:.0%} des caractères conservés",
    "log.failed": "ÉCHEC : {error}",
    "log.finished": "Terminé : {done} converti(s)",
    "log.finished_failed": "{n} en échec",
    "log.finished_review": "{n} à vérifier",
    "log.unexpected": "Erreur inattendue : {error}",
    "log.no_text_pages": "les pages {pages} ne contiennent aucun texte et la reconnaissance est désactivée",
    "log.record_failed": "impossible d'écrire la fiche : {error}",

    # ---- installation ---------------------------------------------------
    "setup.title": "Une chose à installer",
    "setup.tesseract_missing": "La lecture des PDF numérisés nécessite Tesseract, "
                               "qui n'est pas encore installé. Tout le reste "
                               "fonctionne sans lui.",
    "setup.macos": "Sous macOS, dans le Terminal :",
    "setup.windows": "Sous Windows, téléchargez et lancez l'installateur :",
    "setup.linux": "Sous Linux :",
    "setup.recheck": "Vérifier à nouveau",
    "setup.skip": "Continuer sans",
    "setup.ok": "Tesseract {version} trouvé.",
    "header.no_baseline": "aucune référence de corpus — vérifications absolues seulement",
    "check.summary": "{flagged} fichier(s) sur {total} demandent une vérification.",
    "check.no_record": "{name} : aucune fiche — convertissez-le d'abord avec verbatim",
    "check.no_files": "Aucun fichier .txt trouvé.",
    "check.no_baseline": "(aucune référence de corpus : vérifications absolues "
                         "seulement — lancez « verbatim audit » pour en créer une)",
}

CATALOGUES = {"en": EN, "fr": FR}

_current = DEFAULT


def check_catalogues() -> list:
    """Keys present in one language and missing from another."""
    problems = []
    keys = {lang: set(cat) for lang, cat in CATALOGUES.items()}
    every = set().union(*keys.values())
    for lang, have in keys.items():
        for key in sorted(every - have):
            problems.append(f"{lang}: missing {key!r}")
    return problems


def language() -> str:
    return _current


def set_language(lang: str, remember: bool = True) -> str:
    """Switch language. Unknown codes fall back rather than raising: a bad
    preferences file must not stop the tool from opening."""
    global _current
    _current = lang if lang in CATALOGUES else DEFAULT
    if remember:
        prefs = load_prefs()
        prefs["language"] = _current
        save_prefs(prefs)
    return _current


def load_language() -> str:
    """The remembered language, or the default."""
    global _current
    _current = load_prefs().get("language", DEFAULT)
    if _current not in CATALOGUES:
        _current = DEFAULT
    return _current


def number(n: int, lang: str | None = None) -> str:
    """21605 -> "21,605" in English, "21 605" in French."""
    text = f"{int(n):,}"
    return text.replace(",", "\u00a0") if (lang or _current) == "fr" else text


def t(key: str, lang: str | None = None, **params) -> str:
    """Translate. An unknown key returns itself rather than raising, so a
    missing string is a visible blemish and never a crash mid-conversion."""
    cat = CATALOGUES.get(lang or _current, EN)
    template = cat.get(key) or EN.get(key)
    if template is None:
        return key
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template
