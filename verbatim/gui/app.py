"""
verbatim.gui.app — the window.

Two tabs and a language switch. The switch works on an open window: rebuilding
it would throw away the folder someone had chosen and the file they were part
way through checking, so every label registers how to re-say itself instead.

tkinter rather than a browser: it ships with Python on both macOS and Windows,
needs no extra dependency, no localhost port and no firewall exception, which
matters on managed university machines.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .. import i18n
from ..settings import config_dir, load_prefs, save_prefs
from .convert_tab import ConvertTab
from .review_tab import ReviewTab
from .widgets import MUTED


class App(tk.Tk):
    def __init__(self, review_folder: Path | None = None,
                 language: str | None = None):
        super().__init__()
        # An explicit choice — `verbatim --lang fr` — wins over the remembered
        # one. Reloading unconditionally here would quietly discard it.
        if language:
            i18n.set_language(language)
        else:
            i18n.load_language()
        self.minsize(1000, 680)
        self.title(i18n.t("app.title"))

        self.baseline_path = self._find_baseline()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_header()

        self.tabs = ttk.Notebook(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.convert_tab = ConvertTab(self.tabs, self)
        self.review_tab = ReviewTab(self.tabs, self)
        self.tabs.add(self.convert_tab, text=i18n.t("tab.convert"))
        self.tabs.add(self.review_tab, text=i18n.t("tab.review"))

        if review_folder:
            self.load_review(Path(review_folder))
            self.tabs.select(self.review_tab)

    # -- header ------------------------------------------------------------

    def _build_header(self):
        bar = ttk.Frame(self, padding=(8, 8, 8, 0))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        ttk.Label(bar, text="verbatim", font=("TkDefaultFont", 13, "bold")
                  ).grid(row=0, column=0, sticky="w")
        self.v_lang = tk.StringVar(value=i18n.LANGUAGES[i18n.language()])
        chooser = ttk.Combobox(bar, textvariable=self.v_lang, width=10,
                               state="readonly",
                               values=list(i18n.LANGUAGES.values()))
        chooser.grid(row=0, column=1, sticky="e")
        chooser.bind("<<ComboboxSelected>>", self._language_chosen)
        if not self.baseline_path:
            self.baseline_note = ttk.Label(bar, foreground=MUTED,
                                           text=i18n.t("header.no_baseline"))
            self.baseline_note.grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _language_chosen(self, _event=None):
        for code, name in i18n.LANGUAGES.items():
            if name == self.v_lang.get():
                i18n.set_language(code)
                break
        self.retranslate()

    def retranslate(self):
        self.title(i18n.t("app.title"))
        note = getattr(self, "baseline_note", None)
        if note is not None:
            note.configure(text=i18n.t("header.no_baseline"))
        self.tabs.tab(0, text=i18n.t("tab.convert"))
        self.tabs.tab(1, text=i18n.t("tab.review"))
        self.convert_tab.retranslate()
        self.review_tab.retranslate()

    # -- shared ------------------------------------------------------------

    def _find_baseline(self) -> str | None:
        """A baseline is corpus-specific, so it is looked for rather than
        shipped. Without one only the absolute checks can fire, and the header
        says so rather than letting the quality numbers look complete."""
        remembered = load_prefs().get("baseline_path")
        for candidate in [remembered, config_dir() / "verbatim_baseline.json"]:
            if candidate and Path(candidate).is_file():
                return str(candidate)
        return None

    def load_review(self, folder: Path):
        self.review_tab.load(folder)
        prefs = load_prefs()
        prefs["review_folder"] = str(folder)
        save_prefs(prefs)


    def destroy(self):
        for tab in (getattr(self, "convert_tab", None),
                    getattr(self, "review_tab", None)):
            if tab is not None:
                tab.cancel_pending()
        super().destroy()


def run(review_folder=None, language=None) -> int:
    try:
        app = App(review_folder=review_folder, language=language)
    except tk.TclError as exc:
        print(f"Could not open a window: {exc}\n"
              "Use the command line instead: verbatim convert --help",
              file=sys.stderr)
        return 1
    app.mainloop()
    return 0
