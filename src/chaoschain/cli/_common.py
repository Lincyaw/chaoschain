"""Shared CLI plumbing: global options, error handling, output helpers.

The CLI's contract surface is small but strict. Three orthogonal channels:

  * stdout: data only (YAML / JSON / tab-separated rows).
  * stderr: informational messages ("wrote ...", "committed: ...") and
    error reports. Suppressed-info is what `--quiet` silences. Errors
    always print, even under `--quiet`.
  * exit code: see chaoschain.exit_codes.

`--format json` swaps both stdout and stderr to JSON shapes documented in
docs/cli-contract.md.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import typer

from .. import exit_codes


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class CLIError(Exception):
    """An error raised inside command bodies that the top-level handler
    converts into a structured stderr message + matching exit code."""

    def __init__(self, message: str, *, exit_code: int, type: str) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.type = type


@dataclass
class CLIState:
    cards_root: Path = field(default_factory=lambda: Path("cards"))
    format: OutputFormat = OutputFormat.TEXT
    quiet: bool = False
    yes: bool = False
    dry_run: bool = False
    read_only: bool = False


# Single mutable container; Typer callbacks populate it before commands run.
STATE = CLIState()


def resolve_cards_root(cli_value: Path | None) -> Path:
    """CLI flag > env var > default. Returns an unresolved Path so that
    error messages echo what the user asked for."""
    if cli_value is not None:
        return cli_value
    env = os.environ.get("CHAOSCHAIN_CARDS_ROOT")
    if env:
        return Path(env)
    return Path("cards")


def assert_writable() -> None:
    """Gate every disk- or git-mutating code path. Raises CLIError(4) if
    --read-only is in effect."""
    if STATE.read_only:
        raise CLIError(
            "operation refused: --read-only is in effect",
            exit_code=exit_codes.PERMISSION,
            type="read_only",
        )


def require_yes(action: str) -> None:
    """Destructive ops must pass --yes. Dry-run is exempt (no side effect)."""
    if STATE.dry_run:
        return
    if not STATE.yes:
        raise CLIError(
            f"{action} requires --yes for destructive op",
            exit_code=exit_codes.REFUSED,
            type="refused",
        )


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #


def emit_data(text: str = "", *, json_value: Any = None) -> None:
    """Write the command's primary data payload to stdout."""
    if STATE.format is OutputFormat.JSON:
        sys.stdout.write(json.dumps(json_value, ensure_ascii=False, sort_keys=False))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")


def emit_info(message: str) -> None:
    """Informational ('wrote ...', 'committed: ...'). Goes to stderr.
    Suppressed by --quiet. In JSON mode, swallowed entirely (info isn't
    a JSON value; the structured outcome already lives on stdout)."""
    if STATE.quiet or STATE.format is OutputFormat.JSON:
        return
    sys.stderr.write(message)
    if not message.endswith("\n"):
        sys.stderr.write("\n")


def emit_error(err: CLIError) -> None:
    """Errors always print, even under --quiet."""
    if STATE.format is OutputFormat.JSON:
        payload = {
            "error": {
                "type": err.type,
                "message": err.message,
                "exit_code": err.exit_code,
            }
        }
        sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    else:
        sys.stderr.write(f"error: {err.message}\n")


def run_command(fn: Any, *args: Any, **kwargs: Any) -> None:
    """Wrap a command body so CLIError -> structured exit. Typer's own
    UsageError still produces exit 2."""
    try:
        fn(*args, **kwargs)
    except CLIError as e:
        emit_error(e)
        raise typer.Exit(code=e.exit_code) from e


# --------------------------------------------------------------------------- #
# repository helper
# --------------------------------------------------------------------------- #


def open_repo() -> Any:
    """Open CardRepository from STATE.cards_root, mapping FileNotFoundError
    to exit 7 (environment)."""
    from ..store import CardRepository

    try:
        return CardRepository(STATE.cards_root)
    except FileNotFoundError as e:
        raise CLIError(str(e), exit_code=exit_codes.ENVIRONMENT, type="cards_root_missing") from e
