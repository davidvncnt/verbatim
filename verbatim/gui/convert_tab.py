"""
verbatim.gui.convert_tab — pick two folders, press Convert.

Deliberately the same shape as the script's window, which already worked: the
people who will use this have used that. What is added is the output profile,
a warning next to the paid model option, and an end-of-run summary that hands
the flagged files straight to the review tab, so "which ones do I check?" never
has to be answered by opening them all.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from .. import i18n
from ..pipeline import collect_targets, run_batch
from ..qa.gate import QualityGate
from ..settings import Settings, load_prefs, save_prefs
from .widgets import VERDICT_COLOUR, Translatable, hint


class ConvertTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.tr = Translatable()
        self.msgs: queue.Queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.running = threading.Event()
        self._closing = False

        prefs = load_prefs()
        self.v_in = tk.StringVar(value=prefs.get("input_folder", ""))
        self.v_out = tk.StringVar(value=prefs.get("output_folder", ""))
        self.v_rec = tk.BooleanVar(value=prefs.get("recursive", False))
        self.v_ocr = tk.StringVar(value=prefs.get("ocr", "auto"))
        self.v_engine = tk.StringVar(value=prefs.get("ocr_engine", "tesseract"))
        self.v_lang = tk.StringVar(value=prefs.get("ocr_language", "auto"))
        self.v_key = tk.StringVar(value="")        # never persisted
        self.v_cols = tk.StringVar(value=prefs.get("columns", "auto"))
        self.v_tables = tk.StringVar(value=prefs.get("tables", "lines"))
        self.v_profile = tk.StringVar(value=prefs.get("profile", "decisions"))
        self.v_marks = tk.BooleanVar(value=prefs.get("page_marks", False))
        self.v_heads = tk.BooleanVar(value=prefs.get("keep_headers", False))
        self.v_status = tk.StringVar()
        self.tr.var(self.v_status, "status.ready")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self._build_folders()
        self._build_ocr()
        self._build_layout()
        self._build_actions()
        self._build_log()
        self.after(80, self._pump)

    # -- construction -----------------------------------------------------

    def _build_folders(self):
        box = ttk.LabelFrame(self)
        self.tr.label(box, "group.folders")
        box.grid(row=0, column=0, sticky="ew", pady=4)
        box.columnconfigure(1, weight=1)

        def browse(var, title_key):
            chosen = filedialog.askdirectory(title=i18n.t(title_key),
                                             initialdir=var.get() or None)
            if chosen:
                var.set(chosen)

        for row, (key, var, title) in enumerate((
                ("label.input", self.v_in, "label.input"),
                ("label.output", self.v_out, "label.output"))):
            self.tr.label(ttk.Label(box), key).grid(row=row, column=0, sticky="w",
                                                    padx=6, pady=4)
            box.grid_slaves(row=row, column=0)[0].configure()
            ttk.Entry(box, textvariable=var).grid(row=row, column=1, sticky="ew",
                                                  padx=6)
            btn = ttk.Button(box, command=lambda v=var, t=title: browse(v, t))
            self.tr.label(btn, "button.browse")
            btn.grid(row=row, column=2, padx=6)

        chk = ttk.Checkbutton(box, variable=self.v_rec)
        self.tr.label(chk, "check.recursive")
        chk.grid(row=2, column=1, sticky="w", padx=6, pady=2)
        hint(box, "hint.output", self.tr, row=3, column=1, sticky="w",
             padx=6, pady=(0, 6))

    def _build_ocr(self):
        box = ttk.LabelFrame(self)
        self.tr.label(box, "group.scanned")
        box.grid(row=1, column=0, sticky="ew", pady=4)
        box.columnconfigure(5, weight=1)

        self.tr.label(ttk.Label(box), "label.recognise").grid(
            row=0, column=0, padx=6, pady=6)
        ttk.Combobox(box, textvariable=self.v_ocr, width=8, state="readonly",
                     values=["auto", "off", "always"]).grid(row=0, column=1)
        self.tr.label(ttk.Label(box), "label.using").grid(row=0, column=2, padx=6)
        ttk.Combobox(box, textvariable=self.v_engine, width=10, state="readonly",
                     values=["tesseract", "mistral"]).grid(row=0, column=3)
        self.tr.label(ttk.Label(box), "label.language").grid(row=0, column=4, padx=6)
        ttk.Entry(box, textvariable=self.v_lang, width=10).grid(
            row=0, column=5, sticky="w")
        self.tr.label(ttk.Label(box), "label.key").grid(
            row=1, column=0, padx=6, pady=(0, 4))
        ttk.Entry(box, textvariable=self.v_key, show="*").grid(
            row=1, column=1, columnspan=5, sticky="ew", padx=6, pady=(0, 4))
        hint(box, "hint.model_ocr", self.tr, row=2, column=0, columnspan=6,
             sticky="w", padx=6, pady=(0, 6))

    def _build_layout(self):
        box = ttk.LabelFrame(self)
        self.tr.label(box, "group.layout")
        box.grid(row=2, column=0, sticky="ew", pady=4)

        self.tr.label(ttk.Label(box), "label.profile").grid(row=0, column=0, padx=6,
                                                            pady=6)
        self.profile_box = ttk.Combobox(box, width=18, state="readonly")
        self.profile_box.grid(row=0, column=1)
        self.profile_box.bind("<<ComboboxSelected>>", self._profile_chosen)
        self.tr.callback(self._refresh_profiles)
        self._refresh_profiles()

        self.tr.label(ttk.Label(box), "label.columns").grid(row=0, column=2, padx=6)
        ttk.Combobox(box, textvariable=self.v_cols, width=6, state="readonly",
                     values=["auto", "1", "2"]).grid(row=0, column=3)
        self.tr.label(ttk.Label(box), "label.tables").grid(row=0, column=4, padx=6)
        ttk.Combobox(box, textvariable=self.v_tables, width=8, state="readonly",
                     values=["lines", "text", "none"]).grid(row=0, column=5)
        c1 = ttk.Checkbutton(box, variable=self.v_marks)
        self.tr.label(c1, "check.page_marks")
        c1.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(0, 6))
        c2 = ttk.Checkbutton(box, variable=self.v_heads)
        self.tr.label(c2, "check.keep_headers")
        c2.grid(row=1, column=3, columnspan=3, sticky="w", padx=6, pady=(0, 6))

    def _refresh_profiles(self):
        names = [i18n.t("profile.decisions"), i18n.t("profile.agreements")]
        self.profile_box.configure(values=names)
        self.profile_box.set(names[0 if self.v_profile.get() == "decisions" else 1])

    def _profile_chosen(self, _event=None):
        self.v_profile.set("decisions"
                           if self.profile_box.current() == 0 else "agreements")

    def _build_actions(self):
        bar = ttk.Frame(self)
        bar.grid(row=3, column=0, sticky="ew", pady=4)
        bar.columnconfigure(2, weight=1)
        self.go = ttk.Button(bar, command=self.start)
        self.tr.label(self.go, "button.convert")
        self.go.grid(row=0, column=0)
        self.halt = ttk.Button(bar, state="disabled", command=self.stop)
        self.tr.label(self.halt, "button.stop")
        self.halt.grid(row=0, column=1, padx=6)
        self.bar = ttk.Progressbar(bar, mode="determinate", maximum=1000)
        self.bar.grid(row=0, column=2, sticky="ew", padx=8)

    def _build_log(self):
        self.logbox = tk.Text(self, height=14, wrap="word", state="disabled",
                              borderwidth=1, relief="solid")
        self.logbox.grid(row=4, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self, command=self.logbox.yview)
        scroll.grid(row=4, column=1, sticky="ns")
        self.logbox.configure(yscrollcommand=scroll.set)
        for verdict, colour in VERDICT_COLOUR.items():
            self.logbox.tag_configure(verdict, foreground=colour)
        ttk.Label(self, textvariable=self.v_status).grid(row=5, column=0,
                                                         sticky="w", pady=(4, 0))

    # -- running ----------------------------------------------------------

    def say(self, text, tag=None):
        self.msgs.put(("log", (text, tag)))

    def _settings(self) -> Settings:
        s = Settings()
        s.recursive = self.v_rec.get()
        s.ocr = self.v_ocr.get()
        s.ocr_engine = self.v_engine.get()
        s.ocr_language = self.v_lang.get()
        s.mistral_key = self.v_key.get()
        s.columns = self.v_cols.get()
        s.tables = self.v_tables.get()
        s.profile = self.v_profile.get()
        s.page_marks = self.v_marks.get()
        s.keep_headers = self.v_heads.get()
        s.out = Path(self.v_out.get()) if self.v_out.get().strip() else None
        # Every layout control in the window is an explicit choice, so the
        # profile only fills in what the window does not expose.
        from ..profiles import apply as apply_profile
        return apply_profile(s, explicit={"tables", "page_marks", "keep_headers"})

    def _remember(self):
        prefs = load_prefs()
        prefs.update({"input_folder": self.v_in.get(),
                      "output_folder": self.v_out.get(),
                      "recursive": self.v_rec.get(), "ocr": self.v_ocr.get(),
                      "ocr_engine": self.v_engine.get(),
                      "ocr_language": self.v_lang.get(),
                      "columns": self.v_cols.get(), "tables": self.v_tables.get(),
                      "profile": self.v_profile.get(),
                      "page_marks": self.v_marks.get(),
                      "keep_headers": self.v_heads.get()})
        save_prefs(prefs)

    def start(self):
        if self.running.is_set():
            return
        self.running.set()
        self.stop_flag.clear()
        self._remember()
        self.go.configure(state="disabled")
        self.halt.configure(state="normal")
        self.logbox.configure(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.configure(state="disabled")
        self.bar["value"] = 0
        threading.Thread(target=self._work, daemon=True).start()

    def stop(self):
        self.stop_flag.set()
        self.v_status.set(i18n.t("status.stopping"))

    def _work(self):
        from ..ocr.detect import check_ocr, resolve_languages
        try:
            args = self._settings()
            src = Path(self.v_in.get().strip())
            if not src.exists():
                self.say(i18n.t("log.no_folder", path=src))
                return
            targets = collect_targets([src], args.recursive)
            if not targets:
                self.say(i18n.t("log.no_files", path=src)
                         + ("" if args.recursive
                            else "\n" + i18n.t("log.no_files_hint")))
                return
            if args.out:
                args.out.mkdir(parents=True, exist_ok=True)
            if args.ocr != "off":
                ok, note = check_ocr(args.ocr_engine, args.mistral_key)
                self.say(i18n.t("log.ocr_ready" if ok else "log.ocr_unavailable",
                                note=note))
                if ok and args.ocr_engine == "tesseract":
                    resolve_languages(args, self.say)
                if not ok:
                    args.ocr = "off"
            self.say(i18n.t("log.files_found", n=len(targets)) + "\n")

            def on_file(n, total, name):
                self.msgs.put(("file", (n, total, name)))
                self.say(i18n.t("log.file_line", n=n, total=total, name=name))

            def on_page(n, total, d, t, note):
                self.msgs.put(("page", (n, total, d, t, note)))

            result = run_batch(targets, args, on_file, on_page, self.say,
                               stop=self.stop_flag.is_set,
                               gate=QualityGate(self.app.baseline_path))
            self.msgs.put(("result", result))
        except Exception as exc:
            self.say(i18n.t("log.unexpected", error=f"{type(exc).__name__}: {exc}"))
        finally:
            self.msgs.put(("end", None))

    # -- ui pump ----------------------------------------------------------

    def _pump(self):
        while True:
            try:
                kind, data = self.msgs.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                text, tag = data
                self.logbox.configure(state="normal")
                self.logbox.insert("end", str(text) + "\n", tag or ())
                self.logbox.see("end")
                self.logbox.configure(state="disabled")
            elif kind == "file":
                n, total, name = data
                self.v_status.set(f"{n}/{total}  {name}")
                self.bar["value"] = int(1000 * (n - 1) / max(total, 1))
            elif kind == "page":
                n, total, d, t, note = data
                frac = (n - 1 + (d / t if t else 0)) / max(total, 1)
                self.bar["value"] = int(1000 * frac)
                self.v_status.set(f"{n}/{total}  {note}" if note else f"{n}/{total}")
            elif kind == "result":
                self._finish(data)
            elif kind == "end":
                self.running.clear()
                self.go.configure(state="normal")
                self.halt.configure(state="disabled")
                if not self.stop_flag.is_set():
                    self.bar["value"] = 1000
                self.v_status.set(i18n.t("status.stopped" if self.stop_flag.is_set()
                                         else "status.done"))
        if not self._closing:
            self.after(80, self._pump)

    def _finish(self, result):
        parts = [i18n.t("log.finished", done=result.done)]
        if result.failed:
            parts.append(i18n.t("log.finished_failed", n=len(result.failed)))
        if result.needs_review:
            parts.append(i18n.t("log.finished_review", n=len(result.needs_review)))
        self.logbox.configure(state="normal")
        self.logbox.insert("end", "\n" + ", ".join(parts) + ".\n",
                           "review" if result.needs_review else "ok")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")
        # Hand the flagged files straight to the review tab: the point of
        # flagging them is that somebody looks, and making that a separate
        # navigation step is how it stops happening.
        folder = (Path(self.v_out.get()) if self.v_out.get().strip()
                  else Path(self.v_in.get()))
        if result.converted:
            self.app.load_review(folder)

    def cancel_pending(self):
        """Stop the queue pump and ask any running batch to finish."""
        self._closing = True
        self.stop_flag.set()

    def retranslate(self):
        self.tr.refresh()
