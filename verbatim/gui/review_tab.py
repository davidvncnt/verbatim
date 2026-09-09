"""
verbatim.gui.review_tab — the page on the left, the text on the right.

The problem this solves: a research assistant asked to check a fifty-page
conversion against a fifty-page PDF will read carefully for ten pages and skim
the rest, and a fluent paraphrase reads perfectly well. Attention is the scarce
resource, so the tool spends it: the queue is ordered worst-first, each file
opens on its findings, and choosing a finding jumps both panes to the passage
and outlines it on the page image.

Passages a model produced are shaded wherever they appear, whether or not
anything was flagged in them. Nothing in the document can confirm those words,
and a reviewer should never have to remember which pages those were.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from .. import i18n, sidecar
from ..settings import load_prefs, save_prefs
from .widgets import (
    MUTED,
    SEVERITY_COLOUR,
    SEVERITY_FILL,
    VERDICT_COLOUR,
    Translatable,
    set_text,
)

RENDER_DPI = 150            # rendered at this, then scaled for display
MIN_PANE_PX = 240
# "Fit" makes the whole page visible; the fixed steps make it readable. A page
# scaled to fit a half-window pane puts 10pt body text at about 9 pixels, which
# is legible enough to locate a paragraph and not enough to check a word, so
# both have to be available.
ZOOM_STEPS = [("fit", None), ("100%", 1.0), ("150%", 1.5), ("200%", 2.0)]

VERDICT_MARK = {"ok": "✓", "review": "!", "reject": "✗",
                "unknown": "?"}


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
        self._pdf_missing = False

        prefs = load_prefs()
        self.v_folder = tk.StringVar(value=prefs.get("review_folder", ""))
        self.v_reviewer = tk.StringVar(value=prefs.get("reviewer", ""))
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
        if self.v_folder.get():
            self.load(Path(self.v_folder.get()))

    # -- construction -----------------------------------------------------

    def _build_top(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        bar.columnconfigure(1, weight=1)
        btn = ttk.Button(bar, command=self._choose_folder)
        self.tr.label(btn, "review.open_folder")
        btn.grid(row=0, column=0)
        ttk.Entry(bar, textvariable=self.v_folder).grid(row=0, column=1,
                                                        sticky="ew", padx=8)
        ttk.Label(bar, textvariable=self.v_progress,
                  foreground=MUTED).grid(row=0, column=2)

    def _build_queue(self):
        box = ttk.LabelFrame(self)
        self.tr.label(box, "review.queue")
        box.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        box.rowconfigure(0, weight=1)
        self.queue = tk.Listbox(box, width=24, exportselection=False,
                                activestyle="none")
        self.queue.grid(row=0, column=0, sticky="nsew")
        bar = ttk.Scrollbar(box, command=self.queue.yview)
        bar.grid(row=0, column=1, sticky="ns")
        self.queue.configure(yscrollcommand=bar.set)
        self.queue.bind("<<ListboxSelect>>", self._file_chosen)

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
        bar = ttk.Frame(self)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        bar.columnconfigure(5, weight=1)
        for i, (key, verdict) in enumerate((("review.accept", "accepted"),
                                            ("review.needs_work", "needs_work"),
                                            ("review.reject", "rejected"))):
            btn = ttk.Button(bar, command=lambda v=verdict: self._decide(v))
            self.tr.label(btn, key)
            btn.grid(row=0, column=i, padx=(0, 6))
        self.tr.label(ttk.Label(bar), "review.reviewer").grid(row=0, column=3,
                                                              padx=(12, 4))
        ttk.Entry(bar, textvariable=self.v_reviewer, width=14).grid(row=0, column=4)
        ttk.Entry(bar, textvariable=self.v_note).grid(row=0, column=5, sticky="ew",
                                                      padx=8)
        self.v_status = tk.StringVar()
        ttk.Label(self, textvariable=self.v_status, foreground=MUTED).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

    # -- loading ----------------------------------------------------------

    def _choose_folder(self):
        chosen = filedialog.askdirectory(title=i18n.t("review.open_folder"),
                                         initialdir=self.v_folder.get() or None)
        if chosen:
            self.load(Path(chosen))

    def load(self, folder: Path):
        """Read every converted file in a folder, worst first."""
        folder = Path(folder)
        self.folder = folder
        self.v_folder.set(str(folder))
        prefs = load_prefs()
        prefs["review_folder"] = str(folder)
        save_prefs(prefs)

        entries = []
        for txt in sorted(folder.glob("*.txt")):
            record = sidecar.read(txt)
            if record:
                entries.append((txt, record))
        rank = {"reject": 0, "review": 1, "unknown": 2, "ok": 3}

        def key(item):
            _txt, rec = item
            a = rec.get("assessment", {})
            reviewed = rec.get("review") is not None
            return (reviewed, rank.get(a.get("verdict"), 4),
                    -(a.get("risk_score") or 0.0))

        self.entries = sorted(entries, key=key)
        self._refresh_queue()
        if self.entries:
            self.queue.selection_clear(0, "end")
            self.queue.selection_set(0)
            self._file_chosen()
        else:
            self.v_status.set(i18n.t("review.nothing_loaded"))

    def _refresh_queue(self):
        self.queue.delete(0, "end")
        done = 0
        for txt, rec in self.entries:
            verdict = rec.get("assessment", {}).get("verdict", "unknown")
            reviewed = rec.get("review") is not None
            done += reviewed
            mark = "☑" if reviewed else VERDICT_MARK.get(verdict, "?")
            self.queue.insert("end", f" {mark}  {txt.name}")
            self.queue.itemconfigure(
                self.queue.size() - 1,
                foreground=(MUTED if reviewed
                            else VERDICT_COLOUR.get(verdict, MUTED)))
        self.v_progress.set(i18n.t("review.done_count", done=done,
                                   total=len(self.entries)))

    # -- one file ---------------------------------------------------------

    def _file_chosen(self, _event=None):
        sel = self.queue.curselection()
        if not sel or sel[0] >= len(self.entries):
            return
        txt, record = self.entries[sel[0]]
        self.current_txt, self.current = txt, record
        try:
            self.current_text = txt.read_text(encoding="utf-8")
        except OSError as exc:
            self.current_text = f"({exc})"
        self.current_finding = None
        set_text(self.text, self.current_text)
        self._shade_recognised()
        self._fill_findings()
        self.v_note.set("")
        first = record.get("assessment", {}).get("findings") or []
        self.show_page(first[0].get("page") or 1 if first else 1)
        if first:
            self.findings.selection_clear(0, "end")
            self.findings.selection_set(0)
            self._finding_chosen()

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
            self.findings.insert("end", "  " + i18n.t("review.no_findings"))
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
        if not pages or self._rendering:
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
            with pdfplumber.open(str(pdf)) as doc:
                page = doc.pages[number - 1]
                img = page.to_image(resolution=RENDER_DPI).original
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
        if not self.current_txt:
            return
        who = self.v_reviewer.get().strip() or "unnamed"
        prefs = load_prefs()
        prefs["reviewer"] = self.v_reviewer.get().strip()
        save_prefs(prefs)
        record = sidecar.record_review(self.current_txt, verdict=verdict,
                                       reviewer=who, note=self.v_note.get().strip())
        if record is None:
            return
        for i, (txt, _rec) in enumerate(self.entries):
            if txt == self.current_txt:
                self.entries[i] = (txt, record)
                break
        self.current = record
        self.v_status.set(i18n.t("review.saved", name=self.current_txt.name,
                                 verdict=verdict, who=who))
        index = self.queue.curselection()
        self._refresh_queue()
        nxt = (index[0] + 1) if index else 0
        if nxt < len(self.entries):
            self.queue.selection_clear(0, "end")
            self.queue.selection_set(nxt)
            self.queue.see(nxt)
            self._file_chosen()

    def cancel_pending(self):
        """Drop scheduled work before the widgets go away."""
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except tk.TclError:
                pass
            self._resize_job = None

    def retranslate(self):
        self.tr.refresh()
        if self.current:
            self._fill_findings()
            self.v_page.set(i18n.t("review.page_of", page=self.page_number,
                                   total=len(self.current.get("pages", []))))
