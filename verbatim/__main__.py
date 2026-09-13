"""`python -m verbatim` — the same as the `verbatim` command.

The fallback for when the command itself is not found: on Windows that happens
whenever Python was installed without "Add python.exe to PATH", and the
`py -m verbatim` form works regardless.
"""

from .cli import main

raise SystemExit(main())
