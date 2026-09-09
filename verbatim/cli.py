"""
verbatim.cli — the command line.

`verbatim` on its own opens the window, because most of the people who use this
will never type a command. Everything the window does is also available as a
subcommand, so a batch of twenty thousand files can be run from a shell and the
two paths share one engine.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, i18n, profiles
from .qa.gate import QualityGate
from .settings import (
    COLUMNS,
    INPUT_FOLDER,
    JOIN_PAGES,
    KEEP_BULLETS,
    KEEP_HEADERS,
    KEEP_HYPHENS,
    KEEP_SIDEWAYS,
    MISTRAL_API_KEY,
    MISTRAL_BATCH_PAGES,
    MISTRAL_MODEL,
    OCR,
    OCR_DESKEW,
    OCR_DPI,
    OCR_ENGINE,
    OCR_LANGUAGE,
    OCR_LANGUAGES,
    OCR_MIN_CONF,
    OCR_REMOVE_RULES,
    OCR_RETRY_BELOW,
    OUTPUT_FOLDER,
    PAGE_MARKS,
    PROFILE,
    RECURSIVE,
    STRIP_STRIKETHROUGH,
    TABLE_MARKERS,
    TABLE_WIDTH,
    TABLES,
    VERBOSE,
    Settings,
)

SUBCOMMANDS = ("convert", "check", "review", "audit", "gui")


# argparse cannot tell a default from a value that happens to equal it, so the
# raw argv is consulted: a profile must not override a flag the operator typed.
_FLAG_TO_SETTING = {
    "--keep-headers": "keep_headers", "--keep-sideways": "keep_sideways",
    "--no-join-pages": "join_pages", "--page-marks": "page_marks",
    "--tables": "tables", "--keep-hyphens": "keep_hyphens",
    "--table-markers": "table_markers", "--no-bullets": "keep_bullets",
}


def _explicit_flags(argv) -> set:
    return {setting for flag, setting in _FLAG_TO_SETTING.items()
            if any(a == flag or a.startswith(flag + "=") for a in argv)}


def add_conversion_options(ap):
    """Options shared by the command line and the window's defaults."""
    ap.add_argument("-o", "--out", type=Path, default=None, help="output folder")
    ap.add_argument("-r", "--recursive", action="store_true", default=RECURSIVE)
    ap.add_argument("--profile", choices=["decisions", "agreements"],
                    default=PROFILE, help="output format")
    ap.add_argument("--columns", choices=["auto", "1", "2"], default=COLUMNS)
    ap.add_argument("--tables", choices=["lines", "text", "none"], default=TABLES,
                    help="'lines' reads ruled tables and rebuilds unruled ones "
                         "from their alignment; 'text' is aggressive and should "
                         "only be used on pages that are almost entirely tables")
    ap.add_argument("--table-markers", action="store_true", default=TABLE_MARKERS)
    ap.add_argument("--no-bullets", dest="keep_bullets", action="store_false",
                    default=KEEP_BULLETS,
                    help="drop the leading '- ' from list items in OCR output")
    ap.add_argument("--page-marks", action="store_true", default=PAGE_MARKS)
    ap.add_argument("--keep-hyphens", action="store_true", default=KEEP_HYPHENS)
    ap.add_argument("--keep-headers", action="store_true", default=KEEP_HEADERS)
    ap.add_argument("--keep-sideways", action="store_true", default=KEEP_SIDEWAYS)
    ap.add_argument("--strip-strikethrough", action="store_true",
                    default=STRIP_STRIKETHROUGH,
                    help="remove ~~ markers. Off by default: removing them "
                         "welds struck-out text onto its replacement and "
                         "invents a value that is in no document")
    ap.add_argument("--no-join-pages", dest="join_pages", action="store_false",
                    default=JOIN_PAGES)
    ap.add_argument("--width", type=int, default=TABLE_WIDTH,
                    help="max table width in characters")
    ap.add_argument("--x-tol", type=float, default=None)
    ap.add_argument("--y-tol", type=float, default=3.0)
    ap.add_argument("--ocr", choices=["auto", "off", "always"], default=OCR,
                    help="recognise text on pages that have none")
    ap.add_argument("--ocr-engine", choices=["tesseract", "mistral"],
                    default=OCR_ENGINE)
    ap.add_argument("--ocr-language", default=OCR_LANGUAGE,
                    help='"auto", or a Tesseract code such as fra / eng+fra')
    ap.add_argument("--ocr-languages", default=OCR_LANGUAGES)
    ap.add_argument("--ocr-dpi", type=int, default=OCR_DPI)
    ap.add_argument("--ocr-min-conf", type=float, default=OCR_MIN_CONF)
    ap.add_argument("--ocr-retry-below", type=float, default=OCR_RETRY_BELOW)
    ap.add_argument("--ocr-no-deskew", dest="ocr_deskew", action="store_false",
                    default=OCR_DESKEW)
    ap.add_argument("--ocr-keep-rules", dest="ocr_remove_rules",
                    action="store_false", default=OCR_REMOVE_RULES)
    ap.add_argument("--mistral-key", default=MISTRAL_API_KEY)
    ap.add_argument("--mistral-model", default=MISTRAL_MODEL)
    ap.add_argument("--mistral-batch-pages", type=int, default=MISTRAL_BATCH_PAGES)
    ap.add_argument("--baseline", default=None,
                    help="corpus baseline JSON, from 'verbatim audit'. Without "
                         "one only the absolute quality checks can fire")
    ap.add_argument("--no-record", dest="write_sidecar", action="store_false",
                    default=True,
                    help="do not write the .verbatim.json record beside each .txt")
    ap.add_argument("-v", "--verbose", action="store_true", default=VERBOSE)
    ap.add_argument("--ocr-candidates", default=["eng"], help=argparse.SUPPRESS)
    ap.add_argument("--ocr-trial-language", default="eng", help=argparse.SUPPRESS)
    return ap


def make_parser():
    ap = argparse.ArgumentParser(
        prog="verbatim",
        description="Convert PDFs of international environmental agreement "
                    "texts into clean, faithful plain text.")
    ap.add_argument("--version", action="version", version=f"verbatim {__version__}")
    ap.add_argument("--lang", choices=sorted(i18n.CATALOGUES),
                    help="interface language (remembered)")
    sub = ap.add_subparsers(dest="command")

    conv = sub.add_parser("convert", help="convert PDFs to text")
    conv.add_argument("inputs", nargs="*", type=Path,
                      help="PDF files and/or folders")
    add_conversion_options(conv)

    chk = sub.add_parser("check", help="re-check .txt files already converted")
    chk.add_argument("inputs", nargs="+", type=Path,
                     help=".txt files and/or folders")
    chk.add_argument("--baseline", default=None)
    chk.add_argument("--quiet", action="store_true",
                     help="list only the files that need attention")

    rev = sub.add_parser("review", help="open the review window on a folder")
    rev.add_argument("folder", nargs="?", type=Path, default=None)

    aud = sub.add_parser("audit", help="profile a corpus and write a baseline")
    aud.add_argument("folder", type=Path, help="folder of .txt files")
    aud.add_argument("--pdf-dir", type=Path, default=None,
                     help="matching PDFs, to profile the sources too")
    aud.add_argument("--out", type=Path, default=None,
                     help="where to write the baseline JSON")
    aud.add_argument("--limit", type=int, default=None)

    sub.add_parser("gui", help="open the window (the default)")
    return ap


# ---------------------------------------------------------------------------


def _print_batch(result, log=print):
    parts = [i18n.t("log.finished", done=result.done)]
    if result.failed:
        parts.append(i18n.t("log.finished_failed", n=len(result.failed)))
    if result.needs_review:
        parts.append(i18n.t("log.finished_review", n=len(result.needs_review)))
    log("\n" + ", ".join(parts) + ".")
    for path in result.needs_review:
        log(f"  {path.name}")


def cmd_convert(args) -> int:
    from .ocr.detect import check_ocr, resolve_languages
    from .pipeline import collect_targets, run_batch

    inputs = args.inputs or ([Path(INPUT_FOLDER)] if INPUT_FOLDER.strip() else [])
    if not inputs:
        print("Nothing to convert. Name a PDF or a folder, or run 'verbatim' "
              "with no arguments to open the window.", file=sys.stderr)
        return 2
    missing = [p for p in inputs if not Path(p).exists()]
    if missing:
        for p in missing:
            print(i18n.t("log.no_folder", path=p), file=sys.stderr)
        return 2

    settings = Settings.from_namespace(args)
    settings.inputs = list(inputs)
    # A profile sets defaults; anything named on the command line wins.
    profiles.apply(settings, explicit=_explicit_flags(sys.argv[1:]))
    if settings.out is None and OUTPUT_FOLDER.strip():
        settings.out = Path(OUTPUT_FOLDER.strip())

    targets = collect_targets(inputs, settings.recursive)
    if not targets:
        print(i18n.t("log.no_files", path=", ".join(str(p) for p in inputs)),
              file=sys.stderr)
        return 2

    if settings.ocr != "off":
        ok, note = check_ocr(settings.ocr_engine, settings.mistral_key)
        print(i18n.t("log.ocr_ready" if ok else "log.ocr_unavailable", note=note))
        if ok and settings.ocr_engine == "tesseract":
            resolve_languages(settings)
        if not ok:
            settings.ocr = "off"

    if settings.out:
        Path(settings.out).mkdir(parents=True, exist_ok=True)
    print(i18n.t("log.files_found", n=len(targets)) + "\n")

    gate = QualityGate(baseline_path=getattr(args, "baseline", None))
    if not gate.has_baseline:
        print(i18n.t("check.no_baseline") + "\n")

    def on_file(n, total, name):
        print(i18n.t("log.file_line", n=n, total=total, name=name))

    result = run_batch(targets, settings, on_file=on_file, gate=gate,
                       write_sidecar=args.write_sidecar)
    _print_batch(result)
    return 1 if result.failed else 0


def cmd_check(args) -> int:
    """Re-assess .txt files that were converted earlier.

    Reads the record beside each file rather than re-converting: the point is
    to re-rank an existing corpus, not to spend hours redoing work.
    """
    from . import sidecar

    targets: list = []
    for p in args.inputs:
        p = Path(p)
        targets += sorted(p.glob("*.txt")) if p.is_dir() else [p]
    if not targets:
        print(i18n.t("check.no_files"), file=sys.stderr)
        return 2

    flagged = 0
    for txt in targets:
        record = sidecar.read(txt)
        if record is None:
            if not args.quiet:
                print("  " + i18n.t("check.no_record", name=txt.name))
            continue
        assessment = record.get("assessment", {})
        verdict = assessment.get("verdict", "unknown")
        if verdict != "ok":
            flagged += 1
        if verdict == "ok" and args.quiet:
            continue
        print(f"{i18n.t('verdict.' + verdict):16} {txt.name}")
        for finding in assessment.get("findings", []):
            lang = i18n.language()
            print(f"      - {finding.get('message_' + lang) or finding.get('message_en')}")
    print("\n" + i18n.t("check.summary", flagged=flagged, total=len(targets)))
    return 0


def cmd_review(args) -> int:
    from .gui.app import run
    return run(review_folder=args.folder, language=getattr(args, "lang", None))


def cmd_audit(args) -> int:
    from .qa.audit import run_audit
    return run_audit(args.folder, pdf_dir=args.pdf_dir, out=args.out,
                     limit=args.limit)


def cmd_gui(args) -> int:
    from .gui.app import run
    return run(language=getattr(args, "lang", None))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    i18n.load_language()

    # `verbatim somefile.pdf` should work without typing "convert".
    if argv and not argv[0].startswith("-") and argv[0] not in SUBCOMMANDS:
        argv.insert(0, "convert")

    ap = make_parser()
    args = ap.parse_args(argv)
    if getattr(args, "lang", None):
        i18n.set_language(args.lang)

    handler = {"convert": cmd_convert, "check": cmd_check, "review": cmd_review,
               "audit": cmd_audit, "gui": cmd_gui}.get(args.command)
    if handler is None:
        return cmd_gui(args)
    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
