"""
verbatim — faithful PDF to plain-text conversion for international
environmental agreement texts.

Every word in the output comes from the source document. Text layers are
extracted deterministically and never routed through a language model; a model
is used only where there is genuinely no text to extract, and what it produces
is marked as recognised rather than extracted so that no reader, and no later
process, can mistake the two.
"""

__version__ = "0.1.0"
