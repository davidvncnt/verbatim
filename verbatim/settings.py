"""
verbatim.settings — every tunable default in one place.

The names and values here are the SETTINGS block of the original pdf2txt
script, unchanged, so that anyone who knows that script recognises them. The
command line and the GUI both start from these values.

`Settings` mirrors the argparse namespace field for field. The engine accepts
either one, so the port keeps working exactly as the script did while giving
new code a typed object to hold on to.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

# ===========================================================================
#  SETTINGS
# ===========================================================================

# Folder holding the PDFs to convert. Leave empty to be asked.
INPUT_FOLDER = ""

# Folder where the .txt files should be written.
# Leave empty to drop each .txt next to its PDF.
OUTPUT_FOLDER = ""

# Also convert PDFs sitting in sub-folders of INPUT_FOLDER?
RECURSIVE = False

# --- text recognition for PDFs that are scans (no selectable text) --------
OCR = "auto"            # "auto"   = recognise only pages with no text layer
                        # "off"    = never, leave those pages empty
                        # "always" = send EVERY page to OCR, even pages that
                        #            already have selectable text
OCR_ENGINE = "tesseract"   # "tesseract" = free, local, needs Tesseract
                           # "mistral"   = paid API, better on poor scans
OCR_LANGUAGE = "auto"   # "auto" picks per file from OCR_LANGUAGES, or "fra"...
OCR_LANGUAGES = "eng,fra,spa"
OCR_DPI = 300
OCR_MIN_CONF = 40       # drop words Tesseract is less than this % sure about
OCR_RETRY_BELOW = 75    # under this confidence, retry with extra cleanup
OCR_DESKEW = True
OCR_REMOVE_RULES = True # erase table borders (Tesseract loses boxed text)
MISTRAL_API_KEY = ""
MISTRAL_MODEL = "mistral-ocr-latest"
MISTRAL_BATCH_PAGES = 40

# --- layout ---------------------------------------------------------------
COLUMNS = "auto"        # "auto", "1" (never split), "2" (always split)
TABLES = "lines"        # "lines" (normal), "text" (all-table pages), "none"
PAGE_MARKS = False      # insert "[page N]" between pages
TABLE_MARKERS = False   # wrap tables in [TABLE] ... [/TABLE]
KEEP_BULLETS = True     # keep a leading "- " on list items (OCR output only)
STRIP_STRIKETHROUGH = False   # leave "~~2017~~2020/08" alone. Removing the ~~
                        # markers would weld the struck-out text onto its
                        # replacement and invent a number that is in no document.
KEEP_HYPHENS = False    # True = never join "mat-" + "ter" into "matter"
KEEP_HEADERS = False    # True = keep running headers, footers, page numbers
KEEP_SIDEWAYS = False   # True = keep sideways chart labels instead of dropping
JOIN_PAGES = True       # stitch a paragraph split across a page break
TABLE_WIDTH = 100       # widest a rendered table may be, in characters
VERBOSE = False

# --- output profile -------------------------------------------------------
# "decisions"  = the format used for COP decisions (see docs/brief.md)
# "agreements" = the stricter format for agreement texts published on the site
PROFILE = "decisions"

# ===========================================================================


@dataclass
class Settings:
    """Typed mirror of the argparse namespace the engine consumes."""

    inputs: list = field(default_factory=list)
    out: Path | None = None
    recursive: bool = RECURSIVE

    columns: str = COLUMNS
    tables: str = TABLES
    table_markers: bool = TABLE_MARKERS
    keep_bullets: bool = KEEP_BULLETS
    page_marks: bool = PAGE_MARKS
    keep_hyphens: bool = KEEP_HYPHENS
    keep_headers: bool = KEEP_HEADERS
    keep_sideways: bool = KEEP_SIDEWAYS
    join_pages: bool = JOIN_PAGES
    strip_strikethrough: bool = STRIP_STRIKETHROUGH
    width: int = TABLE_WIDTH
    x_tol: float | None = None
    y_tol: float = 3.0

    ocr: str = OCR
    ocr_engine: str = OCR_ENGINE
    ocr_language: str = OCR_LANGUAGE
    ocr_languages: str = OCR_LANGUAGES
    ocr_dpi: int = OCR_DPI
    ocr_min_conf: float = OCR_MIN_CONF
    ocr_retry_below: float = OCR_RETRY_BELOW
    ocr_deskew: bool = OCR_DESKEW
    ocr_remove_rules: bool = OCR_REMOVE_RULES
    ocr_candidates: list = field(default_factory=lambda: ["eng"])
    ocr_trial_language: str = "eng"

    mistral_key: str = MISTRAL_API_KEY
    mistral_model: str = MISTRAL_MODEL
    mistral_batch_pages: int = MISTRAL_BATCH_PAGES

    profile: str = PROFILE
    verbose: bool = VERBOSE

    @classmethod
    def from_namespace(cls, ns) -> Settings:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in vars(ns).items() if k in known})

    def replace(self, **changes) -> Settings:
        """A copy with some fields changed. Used where the engine needs to
        vary one setting for one page without mutating the shared object."""
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data.update(changes)
        return Settings(**data)


# ---------------------------------------------------------------------------
# persisted user preferences (GUI language, last folders, ...)
# ---------------------------------------------------------------------------

def config_dir() -> Path:
    """Per-user config folder, honouring the platform convention."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "verbatim"


def _prefs_path() -> Path:
    return config_dir() / "settings.json"


def load_prefs() -> dict:
    """Never raises: a corrupt or unreadable file just means no preferences."""
    try:
        return json.loads(_prefs_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_prefs(prefs: dict) -> None:
    try:
        path = _prefs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception:
        pass          # preferences are a convenience, never a reason to fail


def settings_to_dict(args) -> dict:
    """Flatten a Settings or Namespace for the sidecar record."""
    data = asdict(args) if isinstance(args, Settings) else dict(vars(args))
    data.pop("mistral_key", None)          # never write a key to disk
    return {k: (str(v) if isinstance(v, Path) else v)
            for k, v in data.items()
            if not isinstance(v, (list, dict)) or k == "ocr_candidates"}
