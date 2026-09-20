"""
A table whose cells are all the same value.

What a recogniser does when it cannot read a table: it keeps the shape and
fills every cell with the same token. Measured over the 21,605-file corpus,
this fires on three documents once presence/absence matrices are excluded —
those are an ordinary shape here and must not be mistaken for damage.
"""

from __future__ import annotations

import pytest

from verbatim.qa.intrinsic import degenerate_table, intrinsic_findings

HEADER = "Indicator | Value | Target | Status\n"


def rows(*values):
    return "\n".join(" | ".join(v) for v in values)


def test_a_table_of_the_same_value_is_caught():
    text = HEADER + rows(*[("1", "1", "1", "1")] * 8)
    found = degenerate_table(text)
    assert found and found[0] == "1"
    assert found[1] > 0.8


def test_the_finding_points_at_the_table():
    text = "Some prose first.\n\n" + HEADER + rows(*[("1", "1", "1", "1")] * 8)
    found = [f for f in intrinsic_findings(text)[0] if f.kind == "degenerate_table"]
    assert found and found[0].severity == "medium"
    assert text[found[0].char_start:].startswith("1 | 1")


@pytest.mark.parametrize("marker", ["X", "✔", "—", "•", "Y", "-", "0"])
def test_presence_matrices_are_left_alone(marker):
    """Ticks, crosses, dashes and Y/N are how these documents write a matrix."""
    text = HEADER + rows(*[(marker, marker, marker, marker)] * 8)
    assert degenerate_table(text) is None


def test_a_real_table_of_zeros_is_left_alone():
    text = ("Division | Catch | Limit\n"
            + rows(*[(f"58.4.{i}", "0", "0") for i in range(1, 9)]))
    assert degenerate_table(text) is None


def test_an_ordinary_table_is_left_alone():
    text = (HEADER + rows(("Protected areas", "17%", "30%", "On track"),
                          ("Degraded land", "22%", "10%", "At risk"),
                          ("Species index", "0.71", "0.90", "On track")))
    assert degenerate_table(text) is None


def test_prose_is_not_a_table():
    assert degenerate_table("The Conference of the Parties decides. " * 40) is None
