"""Canonical exit codes for the chaoschain CLI.

Stable contract — see docs/cli-contract.md. Do not reuse numbers; do not
collapse categories. Adding a new code is a contract addition.
"""

from __future__ import annotations

OK = 0
USAGE = 2
NOT_FOUND = 3
PERMISSION = 4
CONFLICT = 5
REFUSED = 6
ENVIRONMENT = 7
VALIDATION = 10
GIT = 11
