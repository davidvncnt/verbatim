"""
verbatim.gui.widgets — small shared pieces.

`Translatable` exists because the language switch has to work on a window that
is already open. Rebuilding the whole window on every switch would lose the
folder someone had chosen and the file they were part way through checking, so
each widget registers how to re-label itself instead.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import i18n

# Colours are defined once. The severity colours are also used for the page
# highlight, so a finding looks the same in the list and on the page.
SEVERITY_COLOUR = {"high": "#b3261e", "medium": "#8a5a00", "low": "#4a4a4a"}
SEVERITY_FILL = {"high": "#ffd9d6", "medium": "#ffeccc", "low": "#e8e8e8"}
VERDICT_COLOUR = {"ok": "#1b6b2f", "review": "#8a5a00", "reject": "#b3261e",
                  "unknown": "#4a4a4a"}
MUTED = "#666666"


class Translatable:
    """Registry of widgets that need re-labelling when the language changes."""

    def __init__(self) -> None:
        self._entries: list = []

    def label(self, widget, key: str, attr: str = "text", **params):
        self._entries.append((widget, key, attr, params))
        widget.configure(**{attr: i18n.t(key, **params)})
        return widget

    def var(self, variable, key: str, **params):
        self._entries.append((variable, key, None, params))
        variable.set(i18n.t(key, **params))
        return variable

    def callback(self, fn):
        """For anything that cannot simply be re-labelled — a rebuilt list."""
        self._entries.append((fn, None, None, None))

    def refresh(self) -> None:
        for widget, key, attr, params in self._entries:
            try:
                if key is None:
                    widget()
                elif attr is None:
                    widget.set(i18n.t(key, **params))
                else:
                    widget.configure(**{attr: i18n.t(key, **params)})
            except tk.TclError:
                pass                      # the widget is gone; harmless


def hint(parent, text_key, tr: Translatable, **grid):
    """A quiet explanatory line under a control."""
    lbl = ttk.Label(parent, foreground=MUTED, wraplength=560, justify="left")
    tr.label(lbl, text_key)
    if grid:
        lbl.grid(**grid)
    return lbl


def scrolled_text(parent, **kwargs):
    """A read-only text area with a scrollbar, in a frame."""
    frame = ttk.Frame(parent)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    text = tk.Text(frame, wrap="word", state="disabled", borderwidth=1,
                   relief="solid", **kwargs)
    text.grid(row=0, column=0, sticky="nsew")
    bar = ttk.Scrollbar(frame, command=text.yview)
    bar.grid(row=0, column=1, sticky="ns")
    text.configure(yscrollcommand=bar.set)
    return frame, text


def set_text(widget, content: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.configure(state="disabled")
