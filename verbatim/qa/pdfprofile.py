"""
verbatim.qa.pdfprofile — how likely a PDF is to extract badly, from its own
structure, before anything is extracted.

This runs before any OCR and costs milliseconds. Its purpose is to decide which
files deserve expensive treatment:

    has a text layer   -> a free deterministic reference exists; diff it
    no text layer      -> no free reference exists
      + low geometry risk  -> a single recognition pass is probably fine
      + high geometry risk -> a second, independent pass is justified

Ported from the txtqa package off PyMuPDF onto pdfplumber. That is not
cosmetic: PyMuPDF is AGPL, and this project is MIT. pdfplumber also happens to
expose ruling lines directly as page edges, which PyMuPDF made us reconstruct
from drawing operators.
"""

from __future__ import annotations

import math

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:                                  # pragma: no cover
    PDF_AVAILABLE = False


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def _text_angle(char) -> int:
    """Reading angle of one character, from its text matrix."""
    m = char.get("matrix")
    if not m:
        return 0
    a, b = m[0], m[1]
    if a == 0 and b == 0:
        return 0
    return int(round(math.degrees(math.atan2(b, a)) / 90.0) * 90) % 360


def _has_type3_font(path: str) -> bool:
    """Type 3 fonts carry glyph programs rather than a standard encoding, and
    are a common source of text layers that extract as confident garbage."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        for page in reader.pages:
            fonts = (page.get("/Resources") or {}).get("/Font") or {}
            try:
                fonts = fonts.get_object()
            except AttributeError:
                pass
            for ref in list(fonts.values()):
                try:
                    obj = ref.get_object()
                except AttributeError:
                    obj = ref
                if str(obj.get("/Subtype", "")) == "/Type3":
                    return True
    except Exception:
        pass
    return False


def profile_pdf(path: str, config: dict | None = None) -> dict[str, object]:
    """Structural risk profile of one PDF.

    Returns raw signals plus a composite `susceptibility` in [0, 1].
    On failure returns {"pdf_error": "..."} so the caller can carry on.
    """
    from .config import CONFIG as _DEFAULT

    cfg = config or _DEFAULT

    if not PDF_AVAILABLE:
        return {"pdf_error": "pdfplumber not installed"}

    try:
        pdf = pdfplumber.open(str(path))
    except Exception as exc:
        return {"pdf_error": f"{type(exc).__name__}: {exc}"}

    try:
        n_pages = len(pdf.pages)
        if n_pages == 0:
            return {"pdf_error": "zero pages", "n_pages": 0}

        font_sizes: list[float] = []
        small_glyphs = total_glyphs = 0
        rotated_lines = total_lines = 0
        pages_no_text = pages_landscape = pages_rotated = 0
        pages_low_dpi = pages_with_images = 0
        ruling_lines_total = col_edges_total = 0
        total_chars = 0
        total_area_in2 = 0.0
        aspect_ratios: list[float] = []

        for page in pdf.pages:
            w, h = float(page.width), float(page.height)
            if w <= 0 or h <= 0:
                continue
            total_area_in2 += (w / 72.0) * (h / 72.0)
            aspect_ratios.append(max(w, h) / min(w, h))
            if w > h:
                pages_landscape += 1
            if (getattr(page, "rotation", 0) or 0) % 360 != 0:
                pages_rotated += 1

            # ---- text layer --------------------------------------------
            try:
                plain = (page.extract_text() or "").strip()
            except Exception:
                plain = ""
            total_chars += len(plain)
            if len(plain) < 20:
                pages_no_text += 1

            # ---- glyph sizes and reading angle -------------------------
            for ch in page.chars:
                if not (ch.get("text") or "").strip():
                    continue
                total_glyphs += 1
                size = float(ch.get("size", 0.0) or 0.0)
                if len(font_sizes) < 200000:
                    font_sizes.append(size)
                if 0 < size < cfg["SMALL_FONT_PT"]:
                    small_glyphs += 1

            try:
                lines = page.extract_text_lines()
            except Exception:
                lines = []
            left_edges = set()
            for ln in lines:
                total_lines += 1
                left_edges.add(round(ln["x0"] / 3.0))          # ~3pt buckets
                chars = ln.get("chars") or []
                if chars and any(_text_angle(c) != 0 or not c.get("upright", True)
                                 for c in chars[:8]):
                    rotated_lines += 1
            col_edges_total += len(left_edges)

            # ---- ruling lines (table gridlines) ------------------------
            rules = 0
            for e in page.edges:
                if e.get("orientation") == "h":
                    if abs(e["x1"] - e["x0"]) > 0.25 * w:
                        rules += 1
                elif e.get("orientation") == "v":
                    if abs(e["bottom"] - e["top"]) > 0.25 * h:
                        rules += 1
            ruling_lines_total += rules

            # ---- raster resolution on image pages ----------------------
            imgs = page.images or []
            if imgs:
                pages_with_images += 1
                best_dpi = 0.0
                for info in imgs:
                    src = info.get("srcsize") or (info.get("width"), info.get("height"))
                    px = (src or [0])[0] or 0
                    disp_in = (float(info.get("x1", 0)) - float(info.get("x0", 0))) / 72.0
                    if px and disp_in > 0.5:
                        best_dpi = max(best_dpi, px / disp_in)
                if best_dpi and best_dpi < cfg["LOW_DPI"]:
                    pages_low_dpi += 1
    finally:
        try:
            pdf.close()
        except Exception:
            pass

    p = float(n_pages)
    prof: dict[str, object] = {
        "n_pages": n_pages,
        "pdf_total_chars": total_chars,
        "frac_pages_no_text": pages_no_text / p,
        "frac_pages_landscape": pages_landscape / p,
        "frac_pages_rotated": pages_rotated / p,
        "frac_lines_rotated": (rotated_lines / total_lines) if total_lines else 0.0,
        "frac_small_text": (small_glyphs / total_glyphs) if total_glyphs else 0.0,
        "p10_font_size": _percentile(font_sizes, 10.0),
        "median_font_size": _percentile(font_sizes, 50.0),
        "max_aspect_ratio": max(aspect_ratios) if aspect_ratios else 0.0,
        "ruling_lines_per_page": ruling_lines_total / p,
        "col_edges_per_page": col_edges_total / p,
        "frac_pages_low_dpi": pages_low_dpi / p,
        "has_type3_font": 1.0 if _has_type3_font(str(path)) else 0.0,
        "chars_per_in2": (total_chars / total_area_in2) if total_area_in2 else 0.0,
        "is_scanned": (pages_no_text / p) > 0.5,
    }

    prof["table_density"] = min(
        1.0,
        (prof["ruling_lines_per_page"] / 20.0) * 0.6
        + (prof["col_edges_per_page"] / 25.0) * 0.4,
    )
    prof["text_density"] = min(1.0, prof["chars_per_in2"] / 400.0)

    spec = cfg["SUSCEPT_SPEC"]

    def _weighted(keys) -> float:
        total_w = sum(spec[k] for k in keys)
        if not total_w:
            return 0.0
        acc = 0.0
        for k in keys:
            try:
                acc += spec[k] * min(1.0, max(0.0, float(prof.get(k, 0.0))))
            except (TypeError, ValueError):
                continue
        return acc / total_w

    prof["susceptibility"] = _weighted(list(spec.keys()))

    # Geometry risk deliberately EXCLUDES frac_pages_no_text. When choosing
    # among scanned files, "it is scanned" is true of all of them and would
    # dominate every score equally, flattening the distinction being measured.
    geom_keys = [k for k in spec if k != "frac_pages_no_text"]
    prof["geometry_risk"] = _weighted(geom_keys)

    if not prof["is_scanned"]:
        # A text layer exists, so an independent deterministic reference is
        # available for free. Never pay for sampling here.
        prof["recommended_check"] = "diff_vs_text_layer"
    elif prof["geometry_risk"] >= cfg["SELFCHECK_GEOMETRY_MIN"]:
        prof["recommended_check"] = "self_consistency"
    else:
        prof["recommended_check"] = "intrinsic_only"

    return prof
