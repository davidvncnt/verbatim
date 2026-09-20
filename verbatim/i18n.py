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
    "missing_from_text": "a passage of {n} words on this page of the PDF is missing from the text: “{sample}…”",
    "not_in_scan": "{n} words here have no equivalent anywhere in the scanned PDF: {sample}",
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
    "review.done_count": "{done} of {total} checked",

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
    "missing_from_text": "un passage de {n} mots de cette page du PDF manque dans le texte : « {sample}… »",
    "not_in_scan": "{n} mots ici n'ont aucun équivalent dans le PDF numérisé : {sample}",
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
    "review.done_count": "{done} sur {total} vérifiés",

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
