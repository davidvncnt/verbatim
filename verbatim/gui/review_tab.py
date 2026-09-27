"""
verbatim.gui.review_tab — the page on the left, the text on the right.

The problem this solves: a research assistant asked to check a fifty-page
conversion against a fifty-page PDF will read carefully for ten pages and skim
the rest, and a fluent paraphrase reads perfectly well. Attention is the scarce
resource, so the tool spends it: the queue is ordered worst-first, each file
opens on its findings, and choosing a finding jumps both panes to the passage
and outlines it on the page image.

Any folder of .txt files can be reviewed. A file verbatim converted carries its
own record beside it. Any other file is checked when it is opened — against its
PDF when one is found, read by Tesseract when that PDF is a scan — and what is
learned about it is kept on this computer only, never in the folder. Checks run
on a worker thread so a long scan never freezes the window, and choosing another
file abandons the check in progress.

Passages a model produced are shaded wherever they appear, whether or not
anything was flagged in them. Nothing in the document can confirm those words,
and a reviewer should never have to remember which pages those were.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, ttk

from .. import i18n, sidecar
from ..pipeline import Stopped
from ..qa import external
from ..qa.config import CONFIG
from ..review_store import LocalStore, summarise, text_stamp
from ..settings import load_prefs, save_prefs
from .widgets import (
    MUTED,
    SEVERITY_COLOUR,
    SEVERITY_FILL,
    VERDICT_COLOUR,
    Translatable,
    hint,
    scrolled_text,
    set_text,
)

RENDER_DPI = 150            # rendered at this, then scaled for display
MIN_PANE_PX = 240
# "Fit" makes the whole page visible; the fixed steps make it readable. A page
# scaled to fit a half-window pane puts 10pt body text at about 9 pixels, which
# is legible enough to locate a paragraph and not enough to check a word, so
# both have to be available.
ZOOM_STEPS = [("fit", None), ("100%", 1.0), ("150%", 1.5), ("200%", 2.0)]

DECISION_LABEL = {"accepted": "review.accept", "needs_work": "review.needs_work",
                  "rejected": "review.reject"}

VERDICT_MARK = {"ok": "✓", "review": "!", "reject": "✗", "unknown": "?"}
# Text checks found nothing, but the file has not been compared with its PDF
# yet. A tick here would claim a verification that has not happened.
UNCOMPARED_MARK = "○"
RANK = {"reject": 0, "review": 1, "unknown": 2, "ok": 3}

# How many files one press of "Analyse" takes on; None is every file. Scans are
# read by the recogniser at a few seconds a page, so a folder of them can take
# hours, and a reviewer may rather start on the first hundred.
BATCH_SIZES = (None, 25, 100, 500)
# While a folder is being analysed, the list is put back in order this often,
# so that finished files rise to the top without the list jumping constantly.
BATCH_RESORT_SECONDS = 20

DECISION_MARK = {"accepted": ("☑", "#1b6b2f"), "needs_work": ("⊙", "#8a5a00"),
                 "rejected": ("☒", "#b3261e")}

# Scripts whose letters most fixed-width fonts do not carry. Tk then falls back
# font by font, character by character, which costs about a second for a page of
# Arabic — sixty times the same amount of Latin text. Naming a font that holds
# the letters avoids the search entirely.
COMPLEX_SCRIPTS = {"ARABIC", "HEBREW", "SYRIAC", "THAANA", "NKO", "DEVANAGARI"}
COMPLEX_FONTS = ("Geeza Pro", "Arial Unicode MS", "Noto Naskh Arabic",
                 "Segoe UI", "Tahoma")


@dataclass
class Entry:
    """One .txt in the queue."""

    txt: Path
    kind: str                     # "verbatim": has its own record beside it
    record: dict | None = None    # the full check, once there is one
    triage: str = "unknown"       # quick text-only verdict, for ordering
    kinds: list = field(default_factory=list)   # kinds of problem found
    # What the last full check found, without the check itself: enough to
    # colour the row. The full check is read from disk when the file is opened.
    summary: dict | None = None

    @property
    def verdict(self) -> str:
        if self.record is not None:
            return self.record.get("assessment", {}).get("verdict", "unknown")
        if self.summary is not None:
            return self.summary.get("verdict", "unknown")
        return self.triage

    @property
    def analysed(self) -> bool:
        """Has the full check run, rather than only the quick sort?"""
        return (self.kind == "verbatim" or self.record is not None
                or self.summary is not None)

    @property
    def problems(self) -> list:
        """Kinds of problem found, from the full check when there is one."""
        if self.record is not None:
            return sorted({f.get("kind", "")
                           for f in self.record.get("assessment", {}).get("findings", [])
                           if f.get("kind")})
        if self.summary is not None:
            return list(self.summary.get("kinds", []))
        return list(self.kinds)

    @property
    def compared(self) -> bool:
        """Has the text been compared with its PDF? A verbatim record always
        has been; any other file only once a full check found the PDF."""
        if self.kind == "verbatim":
            return True
        if self.record is not None:
            return self.record.get("reference") not in (None, "none")
        return bool(self.summary and self.summary.get("compared"))


class _GiveWay(Stopped):
    """Raised inside a batch check when the reviewer wants a file checked."""


class ReviewTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.tr = Translatable()
        self.folder: Path | None = None
        self.entries: list = []            # [(txt_path, record)]
        self.current: dict | None = None
        self.current_txt: Path | None = None
        self.current_text = ""
        self.page_image = None             # keep a reference or Tk drops it
        self.page_number = 1
        self.px_per_point = 1.0            # set when a page is rendered
        self._last_width = 0
        self._sash_placed = False
        self._rendering = False            # see _canvas_resized
        self._resize_job = None
        # The finding currently being looked at. Held here because the page is
        # re-rendered on resize and on zoom, and losing the outline at that
        # moment loses the one thing the reviewer was pointed at.
        self.current_finding: dict | None = None
        self.current_entry: Entry | None = None
        self.store: LocalStore | None = None
        self._by_name: dict = {}
        self._row_of: dict = {}
        self.shown: list = []
        self._dirty: set = set()

        # Background work. `_generation` changes whenever the file being looked
        # at changes, and a running check stops at its next page when it no
        # longer matches. `_folder_gen` does the same for the folder triage.
        self._jobs: queue.Queue = queue.Queue()
        self._results: queue.Queue = queue.Queue()
        self._generation = 0
        self._folder_gen = 0
        self._worker: threading.Thread | None = None
        self._checking = False
        self._closing = False
        # Analysing many files ahead of the reviewer. The same thread does it,
        # between requests for the file on screen, which always come first:
        # PDFium cannot render two pages at once, and the reviewer should
        # never wait behind a file they have not asked for.
        self._batch_lock = threading.Lock()
        self._batch: tuple | None = None      # (generation, options, files left)
        self._batch_gen = 0
        self._batch_running = False
        # Pressed while the quick sort is still reading the folder: the files
        # to analyse are chosen once it has finished, so that "the next 100"
        # are the worst 100 and not the first 100 in alphabetical order.
        self._batch_after_triage = False
        self._batch_size_asked = None
        self._triaging = False
        self._batch_total = 0
        self._batch_done = 0
        self._batch_failed = 0
        self._batch_started = 0.0
        self._batch_resorted = 0.0

        prefs = load_prefs()
        self.v_pdf_folder = tk.StringVar(value=prefs.get("review_pdf_folder", ""))
        self.v_text_only = tk.BooleanVar(value=prefs.get("review_text_only", False))
        self.v_conf = tk.IntVar(value=int(prefs.get(
            "review_crosscheck_conf", CONFIG["CROSSCHECK_CONF_MIN"] * 100)))
        self.v_busy = tk.StringVar()
        self.v_folder = tk.StringVar(value=prefs.get("review_folder", ""))
        self.v_reviewer = tk.StringVar(value=prefs.get("reviewer", ""))
        self._batch_choice = prefs.get("review_batch_size", None)
        self.v_note = tk.StringVar()
        self.v_progress = tk.StringVar()
        self.v_page = tk.StringVar()

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_top()
        self._build_queue()
        self._build_panes()
        self._build_decision()
        self.tr.callback(self._refresh_queue)
        self.after(100, self._pump)
        if self.v_folder.get():
            self.load(Path(self.v_folder.get()))

    # -- construction -----------------------------------------------------

    def _build_top(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        bar.columnconfigure(1, weight=1)
        btn = ttk.Button(bar, command=self._choose_folder)
        self.tr.label(btn, "review.open_folder")
        btn.grid(row=0, column=0, sticky="ew")
        ttk.Entry(bar, textvariable=self.v_folder).grid(row=0, column=1,
                                                        sticky="ew", padx=8)
        ttk.Label(bar, textvariable=self.v_progress,
                  foreground=MUTED).grid(row=0, column=2, sticky="e", padx=(8, 4))
        summary = ttk.Button(bar, command=self._show_summary)
        self.tr.label(summary, "review.summary")
        summary.grid(row=0, column=3, sticky="e")

        self.tr.label(ttk.Label(bar), "review.pdf_folder").grid(
            row=1, column=0, sticky="e", pady=(4, 0))
        pdf_entry = ttk.Entry(bar, textvariable=self.v_pdf_folder)
        pdf_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(4, 0))
        pdf_entry.bind("<Return>", lambda _e: self._options_changed())
        pdf_entry.bind("<FocusOut>", lambda _e: self._options_changed())
        browse = ttk.Button(bar, command=self._choose_pdf_folder)
        self.tr.label(browse, "button.browse")
        browse.grid(row=1, column=2, pady=(4, 0))
        text_only = ttk.Checkbutton(bar, variable=self.v_text_only,
                                    command=self._options_changed)
        self.tr.label(text_only, "review.text_only")
        text_only.grid(row=1, column=3, padx=(10, 0), pady=(4, 0), sticky="w")

        # How sure the recogniser must be before its reading of a scan counts
        # as evidence. The right value depends on the scans, so it is here
        # rather than buried in a settings file.
        conf = ttk.Frame(bar)
        conf.grid(row=2, column=3, padx=(10, 0), pady=(6, 0), sticky="w")
        self.tr.label(ttk.Label(conf), "review.confidence").pack(side="left")
        spin = ttk.Spinbox(conf, from_=0, to=100, increment=5, width=5,
                           textvariable=self.v_conf, command=self._options_changed)
        spin.pack(side="left", padx=(4, 2))
        spin.bind("<Return>", lambda _e: self._options_changed())
        spin.bind("<FocusOut>", lambda _e: self._options_changed())
        ttk.Label(conf, text="%").pack(side="left")

        self.busy_bar = ttk.Progressbar(bar, mode="determinate", maximum=1000)
        self.busy_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(bar, textvariable=self.v_busy, foreground=MUTED).grid(
            row=2, column=1, columnspan=2, sticky="w", padx=8, pady=(6, 0))

    def _build_queue(self):
        box = ttk.LabelFrame(self)
        self.tr.label(box, "review.queue")
        box.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        box.rowconfigure(1, weight=1)
        box.columnconfigure(0, weight=1)

        # Show one kind of problem at a time: a reviewer who has worked out how
        # to judge garbled encoding gets through forty of them far faster than
        # forty unrelated files.
        top = ttk.Frame(box)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(2, 4))
        top.columnconfigure(1, weight=1)
        self.tr.label(ttk.Label(top), "review.filter").grid(row=0, column=0,
                                                            sticky="w")
        self.filter_box = ttk.Combobox(top, state="readonly", width=20)
        self.filter_box.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.filter_box.bind("<<ComboboxSelected>>", self._filter_chosen)
        self._filter_kind = ""
        self._filter_kinds: list = []

        self.queue = tk.Listbox(box, width=24, exportselection=False,
                                activestyle="none")
        self.queue.grid(row=1, column=0, sticky="nsew")
        bar = ttk.Scrollbar(box, command=self.queue.yview)
        bar.grid(row=1, column=1, sticky="ns")
        self.queue.configure(yscrollcommand=bar.set)
        self.queue.bind("<<ListboxSelect>>", self._file_chosen)

        # Run the full check on many files at once, so that the colours in the
        # list mean something before each file is opened.
        run = ttk.Frame(box)
        run.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2))
        run.columnconfigure(1, weight=1)
        self.batch_button = ttk.Button(run, command=self._batch_clicked)
        self.batch_button.grid(row=0, column=0, sticky="w")
        self.batch_size = ttk.Combobox(run, state="readonly", width=14)
        self.batch_size.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.batch_size.bind("<<ComboboxSelected>>", self._batch_size_chosen)
        self._label_batch()
        self.tr.callback(self._label_batch)

    def _label_batch(self):
        self.batch_button.configure(text=i18n.t(
            "review.batch.stop" if self._batch_running else "review.batch.start"))
        self.batch_size.configure(values=[
            i18n.t("review.batch.all") if n is None
            else i18n.t("review.batch.n", n=i18n.number(n)) for n in BATCH_SIZES])
        choice = self._batch_choice if self._batch_choice in BATCH_SIZES else None
        self.batch_size.current(BATCH_SIZES.index(choice))
        self.batch_size.configure(state="disabled" if self._batch_running
                                  else "readonly")

    def _batch_size_chosen(self, _event=None):
        self._batch_choice = BATCH_SIZES[max(0, self.batch_size.current())]
        prefs = load_prefs()
        prefs["review_batch_size"] = self._batch_choice
        save_prefs(prefs)

    def _refresh_filter_choices(self):
        kinds = sorted({k for e in self.entries for k in e.problems})
        self._filter_kinds = kinds
        labels = [i18n.t("review.filter.all")] + [
            f"{i18n.t('kind.' + k)} ({sum(1 for e in self.entries if k in e.problems)})"
            for k in kinds]
        self.filter_box.configure(values=labels)
        if self._filter_kind in kinds:
            self.filter_box.current(kinds.index(self._filter_kind) + 1)
        else:
            self._filter_kind = ""
            self.filter_box.current(0)

    def _filter_chosen(self, _event=None):
        index = self.filter_box.current()
        self._filter_kind = "" if index <= 0 else self._filter_kinds[index - 1]
        self._refresh_queue()
        if self.shown:
            self.queue.selection_clear(0, "end")
            self.queue.selection_set(0)
            self._file_chosen()

    def _build_panes(self):
        right = ttk.Frame(self)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        findings = ttk.LabelFrame(right)
        self.tr.label(findings, "review.findings")
        findings.grid(row=0, column=0, sticky="ew")
        findings.columnconfigure(0, weight=1)
        self.findings = tk.Listbox(findings, height=4, exportselection=False,
                                   activestyle="none")
        self.findings.grid(row=0, column=0, sticky="ew")
        self.findings.bind("<<ListboxSelect>>", self._finding_chosen)

        panes = ttk.PanedWindow(right, orient="horizontal")
        panes.grid(row=1, column=0, sticky="nsew", pady=6)

        left = ttk.Frame(panes)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        nav = ttk.Frame(left)
        nav.grid(row=0, column=0, sticky="ew")
        ttk.Button(nav, text="‹", width=3,
                   command=lambda: self.show_page(self.page_number - 1)
                   ).pack(side="left")
        ttk.Label(nav, textvariable=self.v_page).pack(side="left", padx=8)
        ttk.Button(nav, text="›", width=3,
                   command=lambda: self.show_page(self.page_number + 1)
                   ).pack(side="left")
        self.v_zoom = tk.StringVar(value=ZOOM_STEPS[0][0])
        zoom = ttk.Combobox(nav, textvariable=self.v_zoom, width=5,
                            state="readonly",
                            values=[label for label, _ in ZOOM_STEPS])
        zoom.pack(side="right")
        zoom.bind("<<ComboboxSelected>>",
                  lambda _e: self.show_page(self.page_number))
        self.canvas = tk.Canvas(left, background="#f4f4f4", highlightthickness=1,
                                highlightbackground="#cccccc")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        # Re-render on resize so the page always fits the pane; a page cut off
        # at the right edge is worse than no page at all, because the reviewer
        # cannot tell whether the missing part is where the problem is.
        self.canvas.bind("<Configure>", self._canvas_resized)
        self._bind_panning(self.canvas)
        cbar = ttk.Scrollbar(left, command=self.canvas.yview)
        cbar.grid(row=1, column=1, sticky="ns")
        hbar = ttk.Scrollbar(left, orient="horizontal", command=self.canvas.xview)
        hbar.grid(row=2, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=cbar.set, xscrollcommand=hbar.set)
        panes.add(left, weight=1)

        textframe = ttk.Frame(panes)
        textframe.rowconfigure(0, weight=1)
        textframe.columnconfigure(0, weight=1)
        self.text = tk.Text(textframe, wrap="word", state="disabled",
                            borderwidth=1, relief="solid", padx=6, pady=6)
        self._default_font = self.text.cget("font")
        self.text.grid(row=0, column=0, sticky="nsew")
        tbar = ttk.Scrollbar(textframe, command=self.text.yview)
        tbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=tbar.set)
        for sev, colour in SEVERITY_FILL.items():
            self.text.tag_configure(f"finding_{sev}", background=colour)
        # Model output is shaded everywhere, flagged or not: nothing in the
        # document can confirm those words.
        self.text.tag_configure("recognised_model", background="#efe6ff")
        self.text.tag_configure("recognised_tesseract", background="#eef4fb")
        # A quiet wash showing which part of the text belongs to the page on
        # the left. Deliberately faint: it is orientation, not a finding.
        self.text.tag_configure("current_page", background="#fdf8ea")
        # Findings must win over every other shading, or the one thing the
        # reviewer was sent here to look at is the one thing they cannot see.
        for sev in SEVERITY_FILL:
            self.text.tag_raise(f"finding_{sev}")
        panes.add(textframe, weight=1)
        self.panes = panes
        # Split the space evenly once the pane actually has a width. Doing it
        # on a timer instead reads winfo_width() before the window is mapped,
        # gets 1, and silently leaves the page in a sliver.
        panes.bind("<Configure>", self._place_sash)

    def _bind_panning(self, canvas):
        """Move around the page with the trackpad, and by dragging it.

        Scrollbars alone make a zoomed page tiring to read: every comparison
        with the text costs two drags on a thin target. Two fingers scroll,
        held sideways they scroll sideways, and the page can be dragged
        directly, which works with a mouse too.
        """
        def scroll(event, axis="y"):
            if event.delta:
                step = -1 if event.delta > 0 else 1
                amount = max(1, int(abs(event.delta) / 6)) if abs(event.delta) > 6 else 1
            else:                                    # X11 sends buttons 4 and 5
                step = -1 if event.num == 4 else 1
                amount = 1
            getattr(canvas, f"{axis}view_scroll")(step * amount, "units")
            return "break"

        canvas.bind("<MouseWheel>", scroll)
        canvas.bind("<Shift-MouseWheel>", lambda e: scroll(e, "x"))
        canvas.bind("<Button-4>", scroll)
        canvas.bind("<Button-5>", scroll)

        def grab(event):
            canvas.scan_mark(event.x, event.y)
            canvas.configure(cursor="fleur")

        def drag(event):
            canvas.scan_dragto(event.x, event.y, gain=1)

        def release(_event):
            canvas.configure(cursor="")

        canvas.bind("<ButtonPress-1>", grab)
        canvas.bind("<B1-Motion>", drag)
        canvas.bind("<ButtonRelease-1>", release)

    def _place_sash(self, _event=None):
        if self._sash_placed:
            return
        try:
            width = self.panes.winfo_width()
            if width > 2 * MIN_PANE_PX:
                self.panes.sashpos(0, int(width * 0.52))
                self._sash_placed = True
        except tk.TclError:
            pass

    def _canvas_resized(self, event):
        """Re-render on resize, without chasing our own tail.

        Rendering sets the canvas scrollregion, which fires <Configure> again,
        which would re-render: the two sizes oscillate as the scrollbar appears
        and disappears and the loop never settles. The guard breaks the cycle
        and the debounce means a drag re-renders once at the end rather than at
        every intermediate width.
        """
        if self._rendering or abs(event.width - self._last_width) < 24:
            return
        self._last_width = event.width
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(150, self._resize_now)

    def _resize_now(self):
        self._resize_job = None
        if self.current:
            self.show_page(self.page_number)

    def _build_decision(self):
        """Who checked it, an optional note, then the decision.

        Laid out in the order it is filled in. The name is what makes the record
        worth keeping: a decision nobody can attribute is not an audit trail.
        """
        bar = ttk.Frame(self)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        bar.columnconfigure(3, weight=1)

        self.tr.label(ttk.Label(bar), "review.reviewer").grid(
            row=0, column=0, sticky="w", padx=(0, 4))
        self.name_entry = ttk.Entry(bar, textvariable=self.v_reviewer, width=16)
        self.name_entry.grid(row=0, column=1, padx=(0, 14))
        self.tr.label(ttk.Label(bar), "review.note").grid(
            row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Entry(bar, textvariable=self.v_note).grid(
            row=0, column=3, sticky="ew", padx=(0, 14))

        self.decision_buttons = []
        for i, (key, verdict) in enumerate((("review.accept", "accepted"),
                                            ("review.needs_work", "needs_work"),
                                            ("review.reject", "rejected"))):
            btn = ttk.Button(bar, command=lambda v=verdict: self._decide(v))
            self.tr.label(btn, key)
            btn.grid(row=0, column=4 + i, padx=(0, 6))
            self.decision_buttons.append(btn)

        hint(bar, "review.decision_hint", self.tr, row=1, column=0, columnspan=7,
             sticky="w", pady=(4, 0))
        self.v_status = tk.StringVar()
        ttk.Label(self, textvariable=self.v_status, foreground=MUTED).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._set_decision_enabled(False)

    def _set_decision_enabled(self, enabled: bool):
        for btn in self.decision_buttons:
            btn.configure(state="normal" if enabled else "disabled")

    # -- loading ----------------------------------------------------------

    def _choose_folder(self):
        chosen = filedialog.askdirectory(title=i18n.t("review.open_folder"),
                                         initialdir=self.v_folder.get() or None)
        if chosen:
            self.load(Path(chosen))

    def _choose_pdf_folder(self):
        chosen = filedialog.askdirectory(title=i18n.t("review.pdf_folder"),
                                         initialdir=self.v_pdf_folder.get() or None)
        if chosen:
            self.v_pdf_folder.set(chosen)
            self._options_changed()

    def _conf_fraction(self) -> float:
        try:
            return max(0, min(100, int(self.v_conf.get()))) / 100.0
        except (TypeError, ValueError, tk.TclError):
            return CONFIG["CROSSCHECK_CONF_MIN"]

    def _pdf_folder(self) -> Path | None:
        value = self.v_pdf_folder.get().strip()
        return Path(value) if value else None

    def _options_changed(self):
        prefs = load_prefs()
        conf = max(0, min(100, int(self.v_conf.get() or 0)))
        if (prefs.get("review_pdf_folder") == self.v_pdf_folder.get().strip()
                and prefs.get("review_text_only") == self.v_text_only.get()
                and prefs.get("review_crosscheck_conf") == conf):
            return
        prefs["review_pdf_folder"] = self.v_pdf_folder.get().strip()
        prefs["review_text_only"] = self.v_text_only.get()
        prefs["review_crosscheck_conf"] = conf
        save_prefs(prefs)
        # Every result in the list was reached under the old options. Show the
        # ones already known under the new ones, and let the rest go grey.
        if self._batch_running:
            self._stop_batch()
        self._attach_checks(self.entries)
        self._resort()
        # The open file was checked under the old options: check it again.
        if self.current_entry is not None and self.current_entry.kind == "external":
            self._open(self.current_entry)

    def load(self, folder: Path):
        """List every .txt in a folder, then order it worst-first.

        Files verbatim converted are ordered by their own record straight away.
        The others are ordered by a quick text-only check that runs in the
        background and is remembered, so a folder of 21,000 files is read once,
        not every time it is opened.
        """
        folder = Path(folder)
        self.folder = folder
        self.v_folder.set(str(folder))
        prefs = load_prefs()
        prefs["review_folder"] = str(folder)
        save_prefs(prefs)
        if self._batch_running:
            self._stop_batch(quiet=True)
        self._folder_gen += 1
        self._generation += 1
        self._triaging = False
        self._clear_file()
        self._busy("", None)

        if not folder.is_dir():
            self.entries = []
            self._refresh_queue()
            self._explain_empty(i18n.t("review.empty.no_folder", path=folder))
            return

        self.store = LocalStore(folder)
        texts = sorted(folder.glob("*.txt"))
        recorded = {p.name for p in folder.glob("*" + sidecar.SUFFIX)}
        triage = self.store.triage()
        entries = []
        for txt in texts:
            if txt.stem + sidecar.SUFFIX in recorded:
                record = sidecar.read(txt)
                if record:
                    entries.append(Entry(txt, "verbatim", record=record))
                    continue
            known = triage.get(txt.name)
            fresh = known and known.get("stamp") == text_stamp(txt)
            entries.append(Entry(
                txt, "external",
                triage=known.get("verdict", "unknown") if fresh else "unknown",
                kinds=list(known.get("kinds", [])) if fresh else []))
        self._attach_checks(entries)

        self.entries = sorted(entries, key=self._sort_key)
        self._by_name = {e.txt.name: e for e in self.entries}
        self._filter_kind = ""
        self._refresh_filter_choices()
        self._refresh_queue()
        if not texts:
            self._explain_empty(i18n.t("review.empty.no_txt"))
            return
        self.queue.selection_clear(0, "end")
        self.queue.selection_set(0)
        self._file_chosen()
        self._start_triage()

    def _decided(self, entry: Entry) -> bool:
        if entry.kind == "verbatim":
            return bool(entry.record and entry.record.get("review"))
        return bool(self.store and self.store.decision(entry.txt.name))

    def _sort_key(self, entry: Entry):
        verdict = entry.verdict
        if not entry.compared and verdict == "ok":
            verdict = "unknown"         # not compared: not as good as verified
        # Files the full check has been through come first, worst first; then
        # the rest, ordered by the quick sort.
        return (self._decided(entry), not entry.analysed,
                RANK.get(verdict, 2), entry.txt.name)

    def _check_options(self) -> tuple:
        """What a check depends on, as chosen in the window right now."""
        text_only = self.v_text_only.get()
        return (None if text_only else self._pdf_folder(),
                external.TEXT_ONLY if text_only else external.FULL,
                self._conf_fraction())

    def _attach_checks(self, entries):
        """Give each file what its last full check found, if that still applies.

        Only the size and date of the files are looked at, so that a folder
        opens at once however large it is. Opening a file compares contents.
        """
        if self.store is None:
            return
        known = self.store.checked_names()
        pdf_folder, mode, conf = self._check_options()
        for entry in entries:
            if entry.kind != "external":
                continue
            entry.record = None
            entry.summary = None
            if entry.txt.name not in known:
                continue
            pdf = None if mode == external.TEXT_ONLY \
                else external.find_pdf(entry.txt, pdf_folder)
            entry.summary = self.store.checked(
                entry.txt, pdf_path=pdf, pdf_stamp=external.file_stamp(pdf),
                mode=mode, ocr=True, crosscheck_conf=conf)

    def _start_triage(self):
        todo = [e.txt for e in self.entries
                if e.kind == "external" and e.record is None and e.triage == "unknown"]
        if not todo or self.store is None:
            return
        self._triaging = True
        gen, store = self._folder_gen, self.store

        def run():
            saved = store.triage()
            for n, txt in enumerate(todo, 1):
                if gen != self._folder_gen or self._closing:
                    break
                try:
                    quick = external.quick_verdict(txt)
                except Exception:
                    quick = {"verdict": "unknown", "kinds": []}
                saved[txt.name] = {"stamp": text_stamp(txt),
                                   "verdict": quick["verdict"],
                                   "kinds": quick.get("kinds", [])}
                self._results.put(("triaged", gen, txt.name, quick["verdict"],
                                   quick.get("kinds", []), n, len(todo)))
                if n % 25 == 0:
                    # Hand the processor back for a moment: this loop competes
                    # with the window for it, and a folder of several thousand
                    # files takes minutes.
                    time.sleep(0.002)
                if n % 500 == 0:
                    store.save_triage(saved)
            try:
                store.save_triage(saved)
            except OSError:
                pass
            self._results.put(("triage_done", gen))

        threading.Thread(target=run, daemon=True).start()

    def _clear_file(self):
        """Forget the previous file, so a new folder never shows stale pages."""
        self.current = self.current_txt = self.current_finding = None
        self.current_text = ""
        self.page_image = None
        self.canvas.delete("all")
        self.v_page.set("")
        self.findings.delete(0, "end")
        set_text(self.text, "")
        self._set_decision_enabled(False)

    def _explain_empty(self, message: str):
        """Put the explanation where the eye goes — the large text pane — and
        not only in the status line along the bottom edge."""
        set_text(self.text, message)
        self.v_status.set(message.split("\n", 1)[0])

    def _decision_of(self, entry: Entry) -> dict | None:
        if entry.kind == "verbatim":
            return (entry.record or {}).get("review")
        return self.store.decision(entry.txt.name) if self.store else None

    def _row(self, entry: Entry) -> tuple:
        decision = self._decision_of(entry)
        if decision:
            # Which way it was decided, not merely that it was: the queue is
            # where a reviewer looks back over what they concluded.
            mark, colour = DECISION_MARK.get(decision.get("verdict"), ("☑", MUTED))
            return f" {mark}  {entry.txt.name}", colour
        verdict = entry.verdict
        if not entry.compared:
            # Only the text was checked. Problems found that way are real, but a
            # clean result is not a verification, so it never gets a tick.
            if verdict in ("reject", "review"):
                return (f" {VERDICT_MARK[verdict]}  {entry.txt.name}",
                        VERDICT_COLOUR[verdict])
            mark = UNCOMPARED_MARK if verdict == "ok" else "?"
            return f" {mark}  {entry.txt.name}", MUTED
        return (f" {VERDICT_MARK.get(verdict, '?')}  {entry.txt.name}",
                VERDICT_COLOUR.get(verdict, MUTED))

    def _refresh_queue(self):
        self.queue.delete(0, "end")
        self._row_of = {}
        self.shown = [e for e in self.entries
                      if not self._filter_kind or self._filter_kind in e.problems]
        for i, entry in enumerate(self.shown):
            label, colour = self._row(entry)
            self.queue.insert("end", label)
            self.queue.itemconfigure(i, foreground=colour)
            self._row_of[entry.txt.name] = i
        self._update_count()

    def _update_count(self, done: int | None = None):
        if done is None:
            done = sum(1 for e in self.entries if self._decided(e))
        self.v_progress.set(i18n.t("review.done_count", done=i18n.number(done),
                                   total=i18n.number(len(self.entries))))

    def _update_row(self, entry: Entry):
        i = self._row_of.get(entry.txt.name)
        if i is None:
            return
        selected = i in self.queue.curselection()
        label, colour = self._row(entry)
        self.queue.delete(i)
        self.queue.insert(i, label)
        self.queue.itemconfigure(i, foreground=colour)
        if selected:
            self.queue.selection_set(i)

    def _resort(self):
        """Put the queue in order again, keeping the open file selected."""
        current = self.current_entry.txt.name if self.current_entry else None
        top = self.queue.nearest(0) if self.queue.size() else 0
        self.entries.sort(key=self._sort_key)
        self._refresh_filter_choices()
        self._refresh_queue()
        if current in self._row_of:
            i = self._row_of[current]
            self.queue.selection_set(i)
            self.queue.see(i)
        elif self.queue.size():
            self.queue.see(top)

    # -- one file ---------------------------------------------------------

    def _file_chosen(self, _event=None):
        sel = self.queue.curselection()
        if not sel or sel[0] >= len(self.shown):
            return
        self._open(self.shown[sel[0]])

    def _open(self, entry: Entry):
        self._generation += 1
        self.current_entry = entry
        self.current_txt, self.current = entry.txt, None
        self.current_finding = None
        self._set_decision_enabled(False)
        try:
            self.current_text = external.load_text(entry.txt)
        except OSError as exc:
            self.current_text = f"({exc})"
        self._apply_font(self.current_text)
        set_text(self.text, self.current_text)
        self.findings.delete(0, "end")
        self.canvas.delete("all")
        self.page_image = None
        self.v_page.set("")
        self.v_note.set("")

        if entry.kind == "verbatim":
            self.v_status.set("")
            self._busy("", None)
            self._show_record(entry.record)
            return

        self.v_status.set(i18n.t("review.local_only"))
        text_only = self.v_text_only.get()
        pdf = None if text_only else external.find_pdf(entry.txt, self._pdf_folder())
        mode = external.TEXT_ONLY if text_only else external.FULL
        cached = None
        if self.store is not None:
            try:
                cached = self.store.cached_check(
                    entry.txt, text_sha256=external.sha256_file(entry.txt),
                    pdf_path=pdf, pdf_stamp=external.file_stamp(pdf),
                    mode=mode, ocr=True,
                    crosscheck_conf=self._conf_fraction())
            except OSError:
                cached = None
        if cached is not None:
            entry.record = cached
            self._update_row(entry)
            self._busy("", None)
            self._show_record(cached)
            return

        self.findings.insert("end", "  " + i18n.t("review.checking", name=entry.txt.name))
        self.findings.itemconfigure(0, foreground=MUTED)
        self._busy(i18n.t("review.checking", name=entry.txt.name), 0.0)
        self._checking = True
        self._ensure_worker()
        self._jobs.put((self._generation, entry.txt, pdf, mode, self.store,
                        self._conf_fraction()))

    def _show_record(self, record: dict):
        self.current = record
        self._set_decision_enabled(True)
        self._shade_recognised()
        self._fill_findings()
        found = record.get("assessment", {}).get("findings") or []
        if not record.get("pages"):
            self._show_notice(record)
            return
        first = found[0] if found else None
        self.show_page((first or {}).get("page") or 1)
        if found:
            self.findings.selection_clear(0, "end")
            self.findings.selection_set(0)
            self._finding_chosen()

    def _show_notice(self, record: dict):
        """Why there is no page to show: the explanation goes in the page pane."""
        notice = record.get("notice")
        if notice == "no_pdf":
            message = i18n.t("review.notice.no_pdf",
                             pdf=Path(record.get("text_file") or "?").stem + ".pdf")
        else:
            message = i18n.t("review.notice.text_only")
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width() - 24, 260)
        self.canvas.create_text(12, 12, anchor="nw", fill=MUTED, width=width,
                                text=message)
        self.v_page.set("")

    # -- background work --------------------------------------------------

    def _ensure_worker(self):
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(target=self._work_loop, daemon=True)
            self._worker.start()

    def _work_loop(self):
        while not self._closing:
            job = self._take_job(wait=not self._batch_waiting())
            if job is not None:
                self._run_check(job)
                continue
            item = self._next_batch_item()
            if item is not None:
                self._run_batch_item(*item)

    def _take_job(self, wait: bool):
        """The newest request for the file on screen, if there is one."""
        try:
            job = self._jobs.get(timeout=0.2) if wait else self._jobs.get_nowait()
        except queue.Empty:
            return None
        while True:                              # only the newest request matters
            try:
                job = self._jobs.get_nowait()
            except queue.Empty:
                return job

    def _run_check(self, job):
        gen, txt, pdf, mode, store, conf = job
        if gen != self._generation:
            return

        def progress(done, total, _note="", _gen=gen, _name=txt.name):
            if _gen != self._generation or self._closing:
                raise Stopped()
            self._results.put(("progress", _gen, _name, done, total))

        try:
            record = external.check(txt, pdf_path=pdf, mode=mode, ocr=True,
                                     progress=progress, crosscheck_conf=conf)
        except Stopped:
            return
        except Exception as exc:
            self._results.put(("failed", gen, txt, f"{type(exc).__name__}: {exc}"))
            return
        if store is not None:
            try:
                store.save_check(txt, record)
            except OSError:
                pass
            record["review"] = store.decision(txt.name)
        self._results.put(("checked", gen, txt, record))

    # -- analysing many files ---------------------------------------------

    def _batch_clicked(self):
        if self._batch_running:
            self._stop_batch()
        else:
            self._start_batch()

    def _start_batch(self):
        if self.store is None:
            return
        # Read now: what was chosen when the button was pressed is what counts.
        self._batch_size_asked = BATCH_SIZES[max(0, self.batch_size.current())]
        if self._triaging:
            self._batch_after_triage = True
            self._batch_running = True
            self._label_batch()
            self.v_status.set(i18n.t("review.batch.after_triage"))
            return
        self._launch_batch()

    def _launch_batch(self):
        self._batch_after_triage = False
        size = self._batch_size_asked
        # In the order of the list, so the files at the top — the worst ones
        # by the quick sort, and those of the kind being filtered on — go first.
        todo = [e.txt for e in self.shown
                if not e.analysed and not self._decided(e)]
        if size:
            todo = todo[:size]
        if not todo:
            self._batch_running = False
            self._label_batch()
            self._busy(i18n.t("review.batch.nothing"), None)
            return
        self.v_status.set("")
        with self._batch_lock:
            self._batch_gen += 1
            self._batch = (self._batch_gen, self._check_options(), self.store,
                           deque(todo))
        self._batch_running = True
        self._batch_total = len(todo)
        self._batch_done = self._batch_failed = 0
        self._batch_started = self._batch_resorted = time.monotonic()
        self._label_batch()
        self._show_batch_progress(None, 0, 0)
        self._ensure_worker()

    def _stop_batch(self, quiet: bool = False):
        with self._batch_lock:
            self._batch_gen += 1
            self._batch = None
        if self._batch_after_triage:
            # Nothing was analysed yet: there is nothing to report but that.
            self._batch_after_triage = False
            self._finish_batch(stopped=True, quiet=True)
            if not quiet:
                self.v_status.set(i18n.t("review.batch.cancelled"))
            return
        self._finish_batch(stopped=True, quiet=quiet)

    def _finish_batch(self, stopped: bool, quiet: bool = False):
        self._batch_running = False
        self._label_batch()
        if self.store is not None:
            try:
                self.store.flush_index()
            except OSError:
                pass
        if quiet:
            return
        key = "review.batch.stopped" if stopped else "review.batch.finished"
        message = i18n.t(key, done=i18n.number(self._batch_done),
                         total=i18n.number(self._batch_total))
        if self._batch_failed:
            message += " " + i18n.t("review.batch.failed",
                                    n=i18n.number(self._batch_failed))
        if not self._checking:
            self._busy(message, None)
        self.v_status.set(message)
        self._resort()

    def _batch_waiting(self) -> bool:
        with self._batch_lock:
            return bool(self._batch and self._batch[3])

    def _next_batch_item(self):
        with self._batch_lock:
            if not self._batch or not self._batch[3]:
                return None
            gen, options, store, files = self._batch
            return gen, options, store, files.popleft()

    def _run_batch_item(self, gen, options, store, txt):
        """Check one file of a batch. Runs on the worker thread."""
        pdf_folder, mode, conf = options

        def alive():
            return gen == self._batch_gen and not self._closing

        if not alive():
            return
        try:
            pdf = None if mode == external.TEXT_ONLY \
                else external.find_pdf(txt, pdf_folder)
            record = store.cached_check(
                txt, text_sha256=external.sha256_file(txt), pdf_path=pdf,
                pdf_stamp=external.file_stamp(pdf), mode=mode, ocr=True,
                crosscheck_conf=conf)
        except OSError:
            record = None
        if record is not None:
            store.note_check(txt, record)
        else:
            def progress(done, total, _note=""):
                if not alive():
                    raise Stopped()
                if not self._jobs.empty():
                    raise _GiveWay()
                self._results.put(("batch_progress", gen, txt.name, done, total))

            try:
                record = external.check(txt, pdf_path=pdf, mode=mode, ocr=True,
                                         progress=progress, crosscheck_conf=conf)
            except _GiveWay:
                # The reviewer opened a file that needs checking. This one
                # starts again afterwards, from its first page.
                with self._batch_lock:
                    if self._batch and self._batch[0] == gen:
                        self._batch[3].appendleft(txt)
                return
            except Stopped:
                return
            except Exception as exc:
                self._results.put(("batch_failed", gen, txt.name,
                                   f"{type(exc).__name__}: {exc}"))
                record = None
            if record is not None:
                try:
                    store.save_check(txt, record, flush=False)
                except OSError:
                    pass
        if record is not None:
            self._results.put(("batch_checked", gen, txt.name,
                               summarise(txt, record)))
        if not self._batch_waiting() and alive():
            try:
                store.flush_index()
            except OSError:
                pass
            self._results.put(("batch_done", gen))

    def _show_batch_progress(self, name, page_done, page_total):
        done, total = self._batch_done, self._batch_total
        fraction = done / total if total else 0.0
        if name and page_total:
            fraction += (page_done / page_total) / total
        message = i18n.t("review.batch.progress", done=i18n.number(done),
                         total=i18n.number(total))
        if name:
            message += " — " + name
            if page_total > 1:
                # Reported as each page begins, so the page being read is
                # one past the pages done.
                message += " " + i18n.t("review.batch.page",
                                        done=min(page_done + 1, page_total),
                                        total=page_total)
        # Only once a few files have gone by: the first file may be a
        # two-hundred-page scan, or a single page of text.
        elapsed = time.monotonic() - self._batch_started
        if done >= 3 and elapsed > 10:
            left = elapsed / done * (total - done)
            minutes = max(1, round(left / 60))
            key = "review.batch.minutes" if minutes < 90 else "review.batch.hours"
            message += " · " + i18n.t(key, n=minutes if minutes < 90
                                      else round(minutes / 60))
        self._busy(message, fraction)

    def _busy(self, message: str, fraction: float | None):
        self.v_busy.set(message)
        self.busy_bar["value"] = 0 if fraction is None else int(1000 * fraction)

    def _pump(self):
        if self._closing:
            return
        deadline = time.monotonic() + 0.05
        triage_progress = None
        batch_progress = None
        resort = False
        while time.monotonic() < deadline:
            try:
                msg = self._results.get_nowait()
            except queue.Empty:
                break
            kind = msg[0]
            if kind == "triaged":
                _, gen, name, verdict, kinds, n, total = msg
                if gen != self._folder_gen:
                    continue
                entry = self._by_name.get(name)
                if entry is not None:
                    entry.kinds = kinds
                    if entry.triage != verdict:
                        entry.triage = verdict
                        self._dirty.add(name)
                triage_progress = (n, total)
            elif kind == "triage_done":
                if msg[1] == self._folder_gen:
                    self._triaging = False
                    resort = True
            elif kind == "progress":
                _, gen, name, done, total = msg
                if gen == self._generation and total:
                    self._busy(i18n.t("review.checking_pages", name=name,
                                      done=done, total=total), done / total)
            elif kind == "checked":
                _, gen, txt, record = msg
                entry = self._by_name.get(txt.name)
                # By path, not by name: a check that finishes after another
                # folder was opened belongs to a file of the same name there.
                if entry is not None and entry.txt == txt:
                    entry.record = record
                    self._dirty.add(txt.name)
                if self.current_entry is not None and txt == self.current_entry.txt:
                    self._checking = False
                    self._busy("", None)
                    if self._batch_running:
                        batch_progress = batch_progress or (None, 0, 0)
                    self._show_record(record)
            elif kind == "batch_progress":
                if msg[1] == self._batch_gen:
                    batch_progress = msg[2:]
            elif kind == "batch_checked":
                _, gen, name, summary = msg
                if gen != self._batch_gen:
                    continue
                self._batch_done += 1
                entry = self._by_name.get(name)
                if entry is not None and entry.record is None:
                    entry.summary = summary
                    self._dirty.add(name)
                batch_progress = batch_progress or (None, 0, 0)
            elif kind == "batch_failed":
                _, gen, name, error = msg
                if gen == self._batch_gen:
                    self._batch_done += 1
                    self._batch_failed += 1
                    batch_progress = batch_progress or (None, 0, 0)
            elif kind == "batch_done":
                if msg[1] == self._batch_gen and self._batch_running:
                    with self._batch_lock:
                        self._batch = None
                    self._finish_batch(stopped=False)
                    batch_progress = None
            elif kind == "failed":
                _, gen, txt, error = msg
                if self.current_entry is not None and txt == self.current_entry.txt:
                    self._checking = False
                    self._busy("", None)
                    if self._batch_running:
                        batch_progress = batch_progress or (None, 0, 0)
                    self.findings.delete(0, "end")
                    self.findings.insert("end", "  " + i18n.t(
                        "review.check_failed", name=txt.name, error=error))
                    self.findings.itemconfigure(0, foreground=SEVERITY_COLOUR["high"])

        for name in list(self._dirty)[:400]:
            self._dirty.discard(name)
            entry = self._by_name.get(name)
            if entry is not None:
                self._update_row(entry)
        if batch_progress and self._batch_running and not self._checking:
            self._show_batch_progress(*batch_progress)
        if (self._batch_running and not resort and time.monotonic()
                - self._batch_resorted > BATCH_RESORT_SECONDS):
            self._batch_resorted = time.monotonic()
            resort = True
        waiting = self._batch_after_triage
        if triage_progress and not self._checking and (
                waiting or not self._batch_running):
            n, total = triage_progress
            message = i18n.t("review.triage", done=i18n.number(n),
                             total=i18n.number(total))
            if waiting:
                message += " · " + i18n.t("review.batch.next")
            self._busy(message, n / total)
        if resort:
            if not self._checking and not self._batch_running:
                self._busy("", None)
            self._resort()
            if self._batch_after_triage and not self._triaging:
                self._launch_batch()
        self.after(100, self._pump)

    def _complex_font(self) -> str | None:
        """A font on this machine that carries the letters of complex scripts."""
        if not hasattr(self, "_complex_font_cached"):
            from tkinter import font as tkfont
            families = set(tkfont.families(self))
            self._complex_font_cached = next(
                (f for f in COMPLEX_FONTS if f in families), None)
        return self._complex_font_cached

    def _apply_font(self, text: str):
        """Fixed width for ordinary text, so rendered tables line up; a font
        that holds the letters when the document is in a complex script, where
        legibility and speed both matter more than column alignment."""
        from ..qa.textmetrics import char_script
        sample = text[:4000]
        complex_chars = sum(1 for c in sample
                            if c.isalpha() and char_script(c) in COMPLEX_SCRIPTS)
        letters = sum(1 for c in sample if c.isalpha())
        wanted = self._default_font
        if letters and complex_chars > 0.05 * letters:
            family = self._complex_font()
            if family:
                wanted = (family, 12)
        self.text.configure(font=wanted)

    def _shade_recognised(self):
        """Mark every passage that was recognised rather than extracted."""
        for tag in ("recognised_model", "recognised_tesseract"):
            self.text.tag_remove(tag, "1.0", "end")
        for span in (self.current or {}).get("spans", []):
            if span["source"] == "extracted":
                continue
            self.text.tag_add(span["source"],
                              f"1.0+{span['char_start']}c",
                              f"1.0+{span['char_end']}c")

    def _fill_findings(self):
        self.findings.delete(0, "end")
        found = (self.current or {}).get("assessment", {}).get("findings") or []
        if not found:
            unchecked = (self.current or {}).get("reference") == "none"
            self.findings.insert("end", "  " + i18n.t(
                "review.no_findings_text_only" if unchecked else "review.no_findings"))
            self.findings.itemconfigure(0, foreground=MUTED)
            return
        lang = i18n.language()
        for f in found:
            message = f.get(f"message_{lang}") or f.get("message_en") or f["kind"]
            page = f.get("page")
            where = f"  ({i18n.t('review.page_of', page=page, total=len(self.current.get('pages', [])))})" if page else ""
            self.findings.insert("end", f"  {message}{where}")
            self.findings.itemconfigure(
                self.findings.size() - 1,
                foreground=SEVERITY_COLOUR.get(f.get("severity"), MUTED))

    def _finding_chosen(self, _event=None):
        sel = self.findings.curselection()
        found = (self.current or {}).get("assessment", {}).get("findings") or []
        if not sel or not found or sel[0] >= len(found):
            return
        finding = found[sel[0]]
        for sev in SEVERITY_FILL:
            self.text.tag_remove(f"finding_{sev}", "1.0", "end")
        start, end = finding.get("char_start"), finding.get("char_end")
        if start is not None and end is not None and end > start:
            tag = f"finding_{finding.get('severity', 'low')}"
            self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
            self.text.see(f"1.0+{start}c")
        if finding.get("page"):
            self.show_page(finding["page"], highlight=finding)

    # -- the page image ---------------------------------------------------

    def show_page(self, number: int, highlight: dict | None = None):
        if highlight is not None:
            self.current_finding = highlight
        elif self.current_finding and self.current_finding.get("page") != number:
            self.current_finding = None
        highlight = highlight or self.current_finding
        pages = (self.current or {}).get("pages") or []
        if self._rendering:
            return
        if not pages:
            if self.current is not None:
                self._show_notice(self.current)
            return
        number = max(1, min(int(number), len(pages)))
        self.page_number = number
        self.v_page.set(i18n.t("review.page_of", page=number, total=len(pages)))
        self._highlight_page_text(number)

        pdf = sidecar.find_source(self.current_txt, self.current) if self.current_txt else None
        self.canvas.delete("all")
        if pdf is None:
            self.page_image = None
            self.canvas.create_text(
                12, 12, anchor="nw", fill=MUTED, width=380,
                text=f"{(self.current or {}).get('source_pdf', '?')}\n\n"
                     "— not found beside the text file —")
            return
        try:
            import pdfplumber
            from PIL import Image, ImageTk

            from ..extract.pdfio import render
            with pdfplumber.open(str(pdf)) as doc:
                page = doc.pages[number - 1]
                img = render(page, RENDER_DPI)
                # Fit the width of the pane. The scale factor is kept so that
                # the rectangles drawn from PDF points land in the right place
                # whatever size the window happens to be.
                available = max(self.canvas.winfo_width() - 4, MIN_PANE_PX)
                chosen = dict(ZOOM_STEPS).get(self.v_zoom.get())
                scale = (available / img.width) if chosen is None else chosen
                if abs(scale - 1.0) > 0.01:
                    img = img.resize((max(1, int(img.width * scale)),
                                      max(1, int(img.height * scale))),
                                     Image.LANCZOS)
                self.px_per_point = img.width / float(page.width)
                self.page_image = ImageTk.PhotoImage(img)
        except Exception as exc:
            self.page_image = None
            self.canvas.create_text(12, 12, anchor="nw", fill=MUTED, width=380,
                                    text=f"{type(exc).__name__}: {exc}")
            return

        self._rendering = True
        try:
            self.canvas.create_image(0, 0, anchor="nw", image=self.page_image)
            self.canvas.configure(scrollregion=(0, 0, self.page_image.width(),
                                                self.page_image.height()))
            self._outline_spans(number, highlight)
        finally:
            self._rendering = False

    def _outline_spans(self, number: int, highlight: dict | None):
        """Draw the rectangles for this page, and pick out the flagged one."""
        spans = [s for s in (self.current or {}).get("spans", [])
                 if s["page"] == number and s.get("bbox")]
        # A passage missing from the text has no place in the text, only on the
        # page: its finding carries the rectangle directly.
        if highlight and highlight.get("bbox") and highlight.get("page") == number:
            x0, top, x1, bottom = (v * self.px_per_point for v in highlight["bbox"])
            colour = SEVERITY_COLOUR.get(highlight.get("severity"), "#b3261e")
            self.canvas.create_rectangle(x0 - 3, top - 3, x1 + 3, bottom + 3,
                                         outline=colour, width=2, dash=(6, 3))
            self.canvas.yview_moveto(
                max(0.0, (top - 80) / max(self.page_image.height(), 1)))
        target = None
        if highlight and highlight.get("char_start") is not None:
            for s in spans:
                if s["char_start"] <= highlight["char_start"] < s["char_end"]:
                    target = s
                    break
        for s in spans:
            x0, top, x1, bottom = (v * self.px_per_point for v in s["bbox"])
            if s is target:
                colour = SEVERITY_COLOUR.get(highlight.get("severity"), "#b3261e")
                self.canvas.create_rectangle(x0 - 2, top - 2, x1 + 2, bottom + 2,
                                             outline=colour, width=2)
                self.canvas.yview_moveto(
                    max(0.0, (top - 80) / max(self.page_image.height(), 1)))
            elif s["source"] != "extracted":
                self.canvas.create_rectangle(x0 - 1, top - 1, x1 + 1, bottom + 1,
                                             outline="#b39ddb", width=1)

    def _highlight_page_text(self, number: int):
        self.text.tag_remove("current_page", "1.0", "end")
        for s in (self.current or {}).get("spans", []):
            if s["page"] == number:
                self.text.tag_add("current_page", f"1.0+{s['char_start']}c",
                                  f"1.0+{s['char_end']}c")

    # -- the decision -----------------------------------------------------

    def _decide(self, verdict: str):
        entry = self.current_entry
        if entry is None or self.current is None:
            return
        who = self.v_reviewer.get().strip()
        if not who:
            # A decision nobody can attribute is not worth recording. The name
            # is remembered, so this only ever asks once per person.
            self.v_status.set(i18n.t("review.name_required"))
            self.name_entry.focus_set()
            return
        prefs = load_prefs()
        prefs["reviewer"] = who
        save_prefs(prefs)
        note = self.v_note.get().strip()

        if entry.kind == "verbatim":
            record = sidecar.record_review(entry.txt, verdict=verdict,
                                           reviewer=who, note=note)
            if record is None:
                return
            entry.record = record
        else:
            decision = self.store.record_decision(
                entry.txt.name, verdict=verdict, reviewer=who, note=note,
                tool_said=self.current.get("assessment", {}).get("verdict"))
            self.current["review"] = decision
            entry.record = self.current
        self.current = entry.record

        self.v_status.set(i18n.t("review.saved", name=entry.txt.name,
                                 verdict=i18n.t(DECISION_LABEL[verdict]),
                                 who=who))
        index = self._row_of.get(entry.txt.name, 0)
        self._update_row(entry)
        self._update_count()
        nxt = index + 1
        if nxt < len(self.shown):
            self.queue.selection_clear(0, "end")
            self.queue.selection_set(nxt)
            self.queue.see(nxt)
            self._file_chosen()

    # -- the summary ------------------------------------------------------

    def _show_summary(self):
        """What came of this folder: read-only, and exportable.

        The decisions exist in the records already; the point here is that
        nobody should have to open two hundred of them to see what the team
        concluded.
        """
        from tkinter import filedialog as fd

        from ..summary import collect, counts, write_csv
        if self.folder is None:
            return
        rows = collect(self.folder, self.store)
        totals = counts(rows)

        window = tk.Toplevel(self)
        window.title(i18n.t("summary.title"))
        window.geometry("560x560")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        ttk.Label(window, text=i18n.t("summary.folder", path=self.folder),
                  foreground=MUTED, wraplength=520).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        frame, body = scrolled_text(window)
        frame.grid(row=1, column=0, sticky="nsew", padx=12)

        lines = [i18n.t("summary.files", n=i18n.number(totals["files"])),
                 i18n.t("summary.decided", done=i18n.number(totals["decided"]),
                        left=i18n.number(totals["undecided"])), ""]
        if not totals["decided"]:
            lines.append(i18n.t("summary.none"))
            lines.append("")

        def section(title_key, counter, label=lambda k: k):
            if not counter:
                return
            lines.append(i18n.t(title_key))
            for key, n in counter.most_common():
                lines.append(f"    {i18n.number(n):>7}   {label(key)}")
            lines.append("")

        section("summary.by_decision", totals["by_decision"],
                lambda k: i18n.t("decided." + k))
        section("summary.by_verdict", totals["by_verdict"],
                lambda k: i18n.t("verdict." + k) if k in VERDICT_MARK else k)
        section("summary.by_problem", totals["by_problem"],
                lambda k: i18n.t("kind." + k))
        section("summary.reviewers", totals["reviewers"])
        if totals["overruled"]:
            lines.append(i18n.t("summary.overruled",
                                n=i18n.number(totals["overruled"])))
        set_text(body, "\n".join(lines))

        status = tk.StringVar()
        ttk.Label(window, textvariable=status, foreground=MUTED,
                  wraplength=520).grid(row=2, column=0, sticky="w", padx=12,
                                       pady=(6, 0))
        buttons = ttk.Frame(window)
        buttons.grid(row=3, column=0, sticky="ew", padx=12, pady=12)
        buttons.columnconfigure(0, weight=1)

        def export():
            path = fd.asksaveasfilename(
                parent=window, defaultextension=".csv",
                initialfile=f"{self.folder.name}-verification.csv",
                filetypes=[("CSV", "*.csv")])
            if path:
                write_csv(rows, Path(path))
                status.set(i18n.t("summary.exported", path=path))

        ttk.Button(buttons, text=i18n.t("summary.export"), command=export).grid(
            row=0, column=0, sticky="w")
        ttk.Button(buttons, text=i18n.t("summary.close"),
                   command=window.destroy).grid(row=0, column=1, sticky="e")

    def cancel_pending(self):
        """Drop scheduled work before the widgets go away."""
        self._closing = True
        self._generation += 1
        self._folder_gen += 1
        with self._batch_lock:
            self._batch_gen += 1
            self._batch = None
        if self.store is not None:
            try:
                self.store.flush_index()
            except OSError:
                pass
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except tk.TclError:
                pass
            self._resize_job = None

    def retranslate(self):
        self.tr.refresh()
        self._update_count()
        if self.current and not self.current.get("pages"):
            self._fill_findings()
            self._show_notice(self.current)
            return
        if self.current:
            self._fill_findings()
            self.v_page.set(i18n.t("review.page_of", page=self.page_number,
                                   total=len(self.current.get("pages", []))))
