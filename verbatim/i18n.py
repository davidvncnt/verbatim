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
    "model_pages": "{n} page(s) were produced by a model, not extracted — check them against the PDF",
    "passes_disagree": "the two recognition passes disagree on {n} word(s) here",
    "repetition_loop": "the same {n} words repeat over and over — the recogniser looped",
    "no_text_layer": "{n} page(s) hold no text and were not recognised",

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
    "hint.model_ocr": "Mistral is a paid service and a model, not a character "
                      "recogniser. Pages it produces are marked and always need checking.",
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
    "review.open_folder": "Open a folder of converted files",
    "review.accept": "Accept",
    "review.needs_work": "Needs work",
    "review.reject": "Reject",
    "review.reviewer": "Your name",
    "review.note": "Note (optional)",
    "review.saved": "Saved: {name} marked {verdict} by {who}.",
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
    "model_pages": "{n} page(s) ont été produites par un modèle, non extraites — à vérifier avec le PDF",
    "passes_disagree": "les deux passes de reconnaissance divergent sur {n} mot(s) ici",
    "repetition_loop": "les mêmes {n} mots se répètent sans fin — la reconnaissance a bouclé",
    "no_text_layer": "{n} page(s) ne contiennent aucun texte et n'ont pas été reconnues",

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
    "hint.model_ocr": "Mistral est un service payant et un modèle, non un "
                      "lecteur de caractères. Les pages qu'il produit sont "
                      "signalées et doivent toujours être vérifiées.",
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
    "review.open_folder": "Ouvrir un dossier de fichiers convertis",
    "review.accept": "Accepter",
    "review.needs_work": "À retravailler",
    "review.reject": "Rejeter",
    "review.reviewer": "Votre nom",
    "review.note": "Remarque (facultatif)",
    "review.saved": "Enregistré : {name} marqué {verdict} par {who}.",
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
