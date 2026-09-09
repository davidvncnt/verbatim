"""
The window, without a person clicking it.

These build the real widgets and drive the real callbacks. They skip when
there is no display, so the suite still runs on a build machine.

What they are actually protecting: that the review queue puts the worst file
first, that a finding carries the reader to the right page, that the language
switch reaches every string including the log, and that a person's decision is
written down. Those are the four things the reviewer exists to do.
"""

from __future__ import annotations

import pytest

from verbatim import i18n, sidecar
from verbatim.pipeline import collect_targets, run_batch
from verbatim.settings import Settings

tk = pytest.importorskip("tkinter")


@pytest.fixture(scope="module")
def converted(synthetic_dir, tmp_path_factory):
    """A converted folder with one deliberately damaged file."""
    out = tmp_path_factory.mktemp("reviewable")
    args = Settings(ocr="off")
    args.out = out
    run_batch(collect_targets([synthetic_dir], False), args,
              log=lambda *a, **k: None)

    from verbatim.pipeline import convert
    from verbatim.qa.gate import QualityGate
    pdf = synthetic_dir / "simple.pdf"
    txt = out / "simple.txt"
    damaged = txt.read_text(encoding="utf-8").replace(
        "consider the synthesis report", "examine the collated summary")
    txt.write_text(damaged, encoding="utf-8")
    res = convert(pdf, args, log=lambda *a, **k: None)
    res.text = damaged
    assessment = QualityGate().assess(res, pdf_path=pdf)
    sidecar.write(sidecar.build(res, assessment, pdf_path=pdf, txt_path=txt,
                                settings=args), txt)
    return out


@pytest.fixture(scope="module")
def _window(converted, tmp_path_factory):
    """One Tk root for the whole module, as the application itself runs.

    Not one per test: on macOS, repeatedly creating and destroying Tk roots
    wedges the process partway through. Not a shared root plus a separate App
    either — PhotoImage binds to whichever root came first, so a second root
    makes every page image fail with "image pyimageN doesn't exist". So the
    App's own construction doubles as the display check.
    """
    import verbatim.settings as settings_mod
    prefs_dir = tmp_path_factory.mktemp("prefs")
    original = settings_mod.config_dir
    settings_mod.config_dir = lambda: prefs_dir
    from verbatim.gui.app import App
    try:
        window = App(review_folder=converted, language="en")
    except tk.TclError as exc:            # headless build machine
        settings_mod.config_dir = original
        pytest.skip(f"no display: {exc}")
    window.withdraw()                     # do not steal focus during a test run
    window.update()
    yield window
    window.destroy()
    settings_mod.config_dir = original


@pytest.fixture
def app(_window, converted):
    """A clean starting state for each test: English, first file selected."""
    i18n.set_language("en")
    _window.v_lang.set(i18n.LANGUAGES["en"])
    _window.retranslate()
    _window.review_tab.load(converted)
    _window.update()
    return _window


# --- the queue ------------------------------------------------------------

def test_the_worst_file_is_first(app, converted):
    """Attention is the scarce resource: the queue spends it in order."""
    first = app.review_tab.queue.get(0)
    assert "simple.txt" in first
    assert "✗" in first or "!" in first
    assert app.review_tab.queue.size() == len(list(converted.glob("*.txt")))


def test_clean_files_are_marked_clean(app):
    marks = [app.review_tab.queue.get(i)
             for i in range(1, app.review_tab.queue.size())]
    assert all("✓" in m for m in marks)


# --- findings -------------------------------------------------------------

def test_the_damaged_file_opens_on_its_findings(app):
    entries = [app.review_tab.findings.get(i)
               for i in range(app.review_tab.findings.size())]
    assert entries and "do not appear in the PDF" in entries[0]
    assert "page 3" in entries[0], "the finding does not say where to look"


def test_choosing_a_finding_highlights_it_in_the_text(app):
    tab = app.review_tab
    tab.findings.selection_set(0)
    tab._finding_chosen()
    app.update()
    ranges = tab.text.tag_ranges("finding_high")
    assert ranges, "the flagged passage is not highlighted"
    highlighted = tab.text.get(ranges[0], ranges[1]).casefold()
    assert highlighted in ("examine", "collated", "summary")


def test_choosing_a_finding_turns_to_the_right_page(app):
    tab = app.review_tab
    tab.findings.selection_set(0)
    tab._finding_chosen()
    app.update()
    assert tab.page_number == 3
    assert tab.page_image is not None, "the page image did not render"


def test_the_page_image_fits_the_pane(app):
    """A page cut off at the edge is worse than none: the reviewer cannot tell
    whether the missing part is where the problem is."""
    tab = app.review_tab
    app.update()
    assert tab.page_image.width() <= max(tab.canvas.winfo_width(), 240) + 8


def test_the_highlight_survives_a_re_render(app):
    """The page is redrawn on resize and on zoom; losing the outline there
    loses the one thing the reviewer was pointed at."""
    tab = app.review_tab
    tab.findings.selection_set(0)
    tab._finding_chosen()
    app.update()
    assert tab.current_finding is not None
    tab.show_page(3)                       # a re-render with no highlight given
    assert tab.current_finding is not None


# --- provenance -----------------------------------------------------------

def test_model_output_is_shaded_wherever_it_appears(app, converted):
    """Nothing in the document can confirm a model's words, so a reviewer is
    never left to remember which pages those were."""
    tab = app.review_tab
    record = sidecar.read(converted / "simple.txt")
    for span in record["spans"]:
        span["source"] = "recognised_model"
    tab.current = record
    tab._shade_recognised()
    app.update()
    assert tab.text.tag_ranges("recognised_model")


# --- language -------------------------------------------------------------

def test_the_language_switch_reaches_the_findings(app):
    app.v_lang.set(i18n.LANGUAGES["fr"])
    app._language_chosen()
    app.update()
    entries = [app.review_tab.findings.get(i)
               for i in range(app.review_tab.findings.size())]
    assert entries and "ne figurent pas dans le PDF" in entries[0]
    assert "page 3 sur 3" in entries[0]
    assert app.tabs.tab(0, "text") == "Convertir"


def test_the_language_switch_keeps_the_open_file(app, converted):
    """Rebuilding the window on a switch would throw away the folder someone
    chose and the file they were part way through."""
    before = app.review_tab.current_txt
    count = app.review_tab.queue.size()
    app.v_lang.set(i18n.LANGUAGES["fr"])
    app._language_chosen()
    app.update()
    assert app.review_tab.current_txt == before
    assert app.review_tab.queue.size() == count


# --- the decision ---------------------------------------------------------

def test_a_decision_is_written_down_and_moves_on(app, converted):
    tab = app.review_tab
    tab.v_reviewer.set("RA1")
    tab.v_note.set("checked against the PDF")
    first = tab.current_txt
    tab._decide("needs_work")
    app.update()

    record = sidecar.read(first)
    assert record["review"]["verdict"] == "needs_work"
    assert record["review"]["reviewer"] == "RA1"
    assert record["review"]["tool_said"] == "reject"
    assert tab.current_txt != first, "the queue did not advance"
    assert tab.v_progress.get().startswith("1 of ")


def test_a_reviewed_file_is_marked_as_done(app):
    tab = app.review_tab
    tab.v_reviewer.set("RA1")
    tab._decide("accepted")
    app.update()
    assert any("☑" in tab.queue.get(i) for i in range(tab.queue.size()))


# --- the convert tab ------------------------------------------------------

def test_the_convert_tab_carries_the_settings_it_shows(app):
    tab = app.convert_tab
    tab.v_cols.set("2")
    tab.v_tables.set("none")
    tab.v_marks.set(True)
    settings = tab._settings()
    assert settings.columns == "2"
    assert settings.tables == "none"
    assert settings.page_marks is True


def test_the_api_key_is_never_remembered(app, tmp_path):
    """A key in a preferences file is a key in a backup, and in a support
    ticket the next time someone sends their settings."""
    tab = app.convert_tab
    tab.v_key.set("sk-secret")
    tab._remember()
    from verbatim.settings import load_prefs
    assert "sk-secret" not in str(load_prefs())
