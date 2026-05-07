"""chaoschain CLI — noun-verb command tree.

  card     CRUD + history over individual fault cards
  library  aggregate views (stats, chains, search)
  vocab    controlled predicate vocabulary
  version  build identity
  dump-schema  machine-readable command tree

Run `chaoschain --help` or `chaoschain dump-schema --format json` to
introspect. The full contract — exit codes, JSON shapes, env vars — lives
in docs/cli-contract.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from ._common import STATE, OutputFormat, resolve_cards_root
from .card import card_app
from .library import library_app
from .meta import dump_schema, version
from .vocab import vocab_app

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help=__doc__,
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(card_app, name="card", help="CRUD + history for individual cards.")
app.add_typer(library_app, name="library", help="Aggregate views: stats, chains, search.")
app.add_typer(vocab_app, name="vocab", help="Controlled predicate vocabulary.")
app.command("version", help="Print build identity.")(version)
app.command("dump-schema", help="Emit the full command tree as JSON.")(dump_schema)


@app.callback()
def _root(
    cards_root: Path | None = typer.Option(
        None,
        "--cards-root",
        help=("Root of the cards tree. CLI > env CHAOSCHAIN_CARDS_ROOT > ./cards."),
    ),
    format: OutputFormat | None = typer.Option(
        None,
        "--format",
        case_sensitive=False,
        help="Output format. Defaults to text (or json if explicitly set).",
    ),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress informational stderr."),
    yes: bool = typer.Option(False, "--yes", help="Confirm destructive ops."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Predict, do not execute. Implies no side effects."
    ),
    read_only: bool = typer.Option(
        False,
        "--read-only",
        help="Hard-disable write paths; any write attempt exits 4.",
    ),
) -> None:
    """Populate the global CLIState before any subcommand body runs."""
    STATE.cards_root = resolve_cards_root(cards_root)
    if format is None:
        # TTY default: text. Non-TTY default: still text (humans piping
        # to less / grep get readable output unless they ask for JSON).
        STATE.format = OutputFormat.TEXT
        if not sys.stdout.isatty():
            STATE.format = OutputFormat.TEXT
    else:
        STATE.format = format
    STATE.quiet = quiet
    STATE.yes = yes
    STATE.dry_run = dry_run
    STATE.read_only = read_only


__all__ = ["app"]
