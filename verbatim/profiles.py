"""
verbatim.profiles — what "properly formatted" means, per kind of document.

A profile is a set of format rules, not code. That is deliberate: the rules for
agreement texts are not settled (see docs/open-questions.md), and when the
colleagues who publish them confirm what they need, changing it should be
editing a table rather than rewriting the formatter.

Rules here only set *defaults*. Anything the operator chooses explicitly — on
the command line or in the window — wins, because the person looking at the
document knows more about it than the profile does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields

# "Article 5", "Article 5 bis", "ARTICLE XII" — the structural spine of an
# agreement text, and a place a paragraph must never be stitched across.
ARTICLE_RE = re.compile(
    r"^\s*(?:article|art\.|annex|annexe|appendix|appendice|chapter|chapitre|"
    r"section|part(?:ie)?|title|titre|rule|règle|preamble|préambule)\b"
    r"[\s ]*(?:[0-9]+|[ivxlcdm]+\b|[A-Z]\b)?", re.I)


@dataclass
class Profile:
    """Format defaults for one kind of document."""

    name: str
    label_key: str                      # i18n key for the window
    #: Settings defaults this profile applies, unless the operator said otherwise.
    defaults: dict = field(default_factory=dict)
    #: Never stitch a paragraph across a page break when the continuation
    #: opens a numbered structural unit.
    respect_article_breaks: bool = False
    #: Provisional: the rules have not been confirmed by the people who will
    #: publish the output. Surfaced so the tool never implies more certainty
    #: than it has.
    provisional: bool = False
    notes: str = ""


DECISIONS = Profile(
    name="decisions",
    label_key="profile.decisions",
    defaults={
        "keep_headers": False,      # running furniture repeats and pollutes
        "keep_sideways": False,     # chart labels are not decision text
        "join_pages": True,
        "page_marks": False,
        "tables": "lines",
    },
    respect_article_breaks=False,
    notes="Implements the specification in docs/brief.md §2.",
)

AGREEMENTS = Profile(
    name="agreements",
    label_key="profile.agreements",
    defaults={
        "keep_headers": False,      # page furniture is noise either way
        # Marginal and rotated text in a treaty annex is more often substantive
        # (a table printed sideways, a stamp) than decorative.
        "keep_sideways": True,
        "join_pages": True,
        "page_marks": False,
        "tables": "lines",
    },
    respect_article_breaks=True,
    provisional=True,
    notes=(
        "Provisional. No written specification exists for the website format; "
        "these rules are a reading of docs/brief.md §7 on the principle that "
        "for published treaty text, dropping content is the worse error. "
        "See docs/open-questions.md."
    ),
)

PROFILES = {p.name: p for p in (DECISIONS, AGREEMENTS)}
DEFAULT = DECISIONS.name


def get(name: str) -> Profile:
    return PROFILES.get(name or DEFAULT, DECISIONS)


def apply(settings, explicit: set | None = None):
    """Apply a profile's defaults to a Settings, without overriding choices.

    `explicit` names the settings the operator set on purpose. Those are left
    alone: a profile is a sensible starting point, not an override of the
    person who is looking at the document.
    """
    profile = get(getattr(settings, "profile", DEFAULT))
    explicit = explicit or set()
    known = {f.name for f in fields(settings)} if hasattr(settings, "__dataclass_fields__") \
        else set(vars(settings))
    for key, value in profile.defaults.items():
        if key in explicit or key not in known:
            continue
        setattr(settings, key, value)
    return settings


def opens_structural_unit(text: str) -> bool:
    """Does this paragraph begin an article, annex or other numbered unit?"""
    return bool(ARTICLE_RE.match(text or ""))
