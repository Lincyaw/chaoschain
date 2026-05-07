"""chaoschain CLI — the agent's interface to the fault-card library.

Subcommands:
  validate   schema-check one file or a whole tree
  list       enumerate ids in the library
  get        print one card by id
  add        validate + place a new card into its canonical path
  rm         delete a card by id
  search     filter by predicate / text
  chains     surface candidate cascade chains
  stats      library health (connectivity, counts)
  predicates list the controlled vocabulary
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError

from .schemas import FaultCard
from .store import CardRepository, versioning
from .validators.registry import resolve_schema

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)

_ROOT_OPT = typer.Option(
    Path("cards"),
    "--cards-root",
    help="Root of the cards tree (used to resolve schema by top-level folder).",
)
_TARGET_ARG = typer.Argument(..., exists=True, help="File or directory to validate.")
_EMITS_OPT = typer.Option(None, "--emits", help="filter: card emits this predicate")
_OBSERVES_OPT = typer.Option(None, "--observes", help="filter: card observes this predicate")
_TEXT_OPT = typer.Option(None, "--text", help="substring search in name + mechanism")
_HOPS_OPT = typer.Option(2, "--max-hops", help="maximum chain length")
_ID_ARG = typer.Argument(..., help="Card id, e.g. FC-0001")
_FILE_ARG = typer.Argument(..., exists=True, help="Path to a YAML card to ingest.")
_FORCE_OPT = typer.Option(False, "--force", help="Overwrite if a card with this id exists.")
_NO_COMMIT_OPT = typer.Option(False, "--no-commit", help="Skip the automatic git commit.")
_LIMIT_OPT = typer.Option(50, "--limit", help="Max revisions to show.")
_COMMIT_ARG = typer.Argument(..., help="Git commit (full or short SHA).")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _load_yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_one(path: Path, cards_root: Path) -> list[str]:
    try:
        model_cls = resolve_schema(path, cards_root)
    except ValueError as e:
        return [f"{path}: {e}"]
    try:
        raw = _load_yaml(path)
    except yaml.YAMLError as e:
        return [f"{path}: yaml parse error: {e}"]
    if not isinstance(raw, dict):
        return [f"{path}: top-level YAML must be a mapping, got {type(raw).__name__}"]
    try:
        model_cls.model_validate(raw)
    except ValidationError as e:
        return [
            f"{path}: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in e.errors()
        ]
    return []


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


@app.command()
def validate(target: Path = _TARGET_ARG, cards_root: Path = _ROOT_OPT) -> None:
    """Validate one card or all cards under a directory."""
    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.yaml")) + sorted(target.rglob("*.yml"))
    if not files:
        typer.echo(f"no YAML files found under {target}", err=True)
        raise typer.Exit(code=1)

    total_errors = 0
    for f in files:
        errs = _validate_one(f, cards_root)
        if errs:
            total_errors += len(errs)
            for e in errs:
                typer.echo(e, err=True)
        else:
            typer.echo(f"ok: {f}")
    if total_errors:
        typer.echo(f"\n{total_errors} error(s) across {len(files)} file(s)", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"\nall {len(files)} card(s) valid")


@app.command(name="list")
def list_cards(cards_root: Path = _ROOT_OPT) -> None:
    """List every card id in the library."""
    repo = CardRepository(cards_root)
    for lc in repo.load_all():
        typer.echo(f"{lc.card.id}\t{lc.card.defect.class_.value}\t{lc.card.name}")


@app.command()
def get(card_id: str = _ID_ARG, cards_root: Path = _ROOT_OPT) -> None:
    """Print one card as YAML to stdout."""
    repo = CardRepository(cards_root)
    lc = repo.get(card_id)
    if lc is None:
        typer.echo(f"no card with id {card_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        yaml.safe_dump(
            lc.card.model_dump(by_alias=True, exclude_none=True),
            sort_keys=False,
            allow_unicode=True,
        )
    )


def _maybe_commit(file: Path, message: str, no_commit: bool) -> None:
    if no_commit:
        return
    try:
        versioning.commit_file(file, message)
        typer.echo(f"committed: {message}")
    except versioning.GitError as e:
        typer.echo(f"warning: skipped auto-commit ({e})", err=True)


@app.command()
def add(
    file: Path = _FILE_ARG,
    cards_root: Path = _ROOT_OPT,
    force: bool = _FORCE_OPT,
    no_commit: bool = _NO_COMMIT_OPT,
) -> None:
    """Validate `file` and place it under cards/<defect_class>/<id>.yaml.

    Auto-commits the new card unless --no-commit is passed.
    """
    raw = _load_yaml(file)
    if not isinstance(raw, dict):
        typer.echo(f"{file}: top-level YAML must be a mapping", err=True)
        raise typer.Exit(code=1)
    try:
        card = FaultCard.model_validate(raw)
    except ValidationError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e

    repo = CardRepository(cards_root)
    existed = repo.get(card.id) is not None
    if existed and not force:
        typer.echo(f"card {card.id} already exists; pass --force to overwrite", err=True)
        raise typer.Exit(code=1)
    target = repo.write(card)
    typer.echo(f"wrote {target}")
    verb = "update" if existed else "add"
    _maybe_commit(target, f"{verb} {card.id}: {card.name}", no_commit)


@app.command()
def rm(
    card_id: str = _ID_ARG,
    cards_root: Path = _ROOT_OPT,
    no_commit: bool = _NO_COMMIT_OPT,
) -> None:
    """Delete a card by id. Auto-commits the deletion unless --no-commit."""
    repo = CardRepository(cards_root)
    lc = repo.get(card_id)
    if lc is None:
        typer.echo(f"no card with id {card_id}", err=True)
        raise typer.Exit(code=1)
    if no_commit:
        lc.path.unlink()
        typer.echo(f"deleted {lc.path}")
        return
    try:
        versioning.remove_file(lc.path, f"remove {card_id}: {lc.card.name}")
        typer.echo(f"deleted and committed: {lc.path}")
    except versioning.GitError as e:
        lc.path.unlink(missing_ok=True)
        typer.echo(f"deleted {lc.path}; warning: skipped auto-commit ({e})", err=True)


@app.command()
def history(
    card_id: str = _ID_ARG,
    cards_root: Path = _ROOT_OPT,
    limit: int = _LIMIT_OPT,
) -> None:
    """Show the git revision history of a card."""
    repo = CardRepository(cards_root)
    lc = repo.get(card_id)
    if lc is None:
        typer.echo(f"no card with id {card_id}", err=True)
        raise typer.Exit(code=1)
    try:
        revs = versioning.history(lc.path, limit=limit)
    except versioning.GitError as e:
        typer.echo(f"git error: {e}", err=True)
        raise typer.Exit(code=1) from e
    for r in revs:
        typer.echo(f"{r.commit[:10]}\t{r.date}\t{r.author}\t{r.subject}")
    typer.echo(f"\n{len(revs)} revision(s)")


@app.command(name="show-at")
def show_at(
    card_id: str = _ID_ARG,
    commit: str = _COMMIT_ARG,
    cards_root: Path = _ROOT_OPT,
) -> None:
    """Print a card as it existed at a specific git commit."""
    repo = CardRepository(cards_root)
    lc = repo.get(card_id)
    if lc is None:
        typer.echo(f"no card with id {card_id}", err=True)
        raise typer.Exit(code=1)
    try:
        typer.echo(versioning.show_at(lc.path, commit))
    except versioning.GitError as e:
        typer.echo(f"git error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def rollback(
    card_id: str = _ID_ARG,
    commit: str = _COMMIT_ARG,
    cards_root: Path = _ROOT_OPT,
    no_commit: bool = _NO_COMMIT_OPT,
) -> None:
    """Restore a card to its content at `commit` (and commit the rollback)."""
    repo = CardRepository(cards_root)
    lc = repo.get(card_id)
    if lc is None:
        typer.echo(f"no card with id {card_id}", err=True)
        raise typer.Exit(code=1)
    msg = None if no_commit else f"rollback {card_id} to {commit[:10]}"
    try:
        versioning.rollback(lc.path, commit, commit_message=msg)
    except versioning.GitError as e:
        typer.echo(f"git error: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(f"rolled back {card_id} to {commit[:10]}")


@app.command()
def search(
    cards_root: Path = _ROOT_OPT,
    emits: str | None = _EMITS_OPT,
    observes: str | None = _OBSERVES_OPT,
    text: str | None = _TEXT_OPT,
) -> None:
    """Search cards by predicate / text."""
    repo = CardRepository(cards_root)
    hits = repo.search(emits_predicate=emits, requires_predicate=observes, text=text)
    for lc in hits:
        typer.echo(f"{lc.card.id}\t{lc.card.defect.class_.value}\t{lc.card.name}")
    typer.echo(f"\n{len(hits)} match(es)")


@app.command()
def chains(cards_root: Path = _ROOT_OPT, max_hops: int = _HOPS_OPT) -> None:
    """Surface candidate chains assembled from the current card library."""
    repo = CardRepository(cards_root)
    found = repo.find_chains(max_hops=max_hops)
    for ch in found:
        typer.echo(" -> ".join(f"{c.id}({c.name})" for c in ch))
    typer.echo(f"\n{len(found)} candidate chain(s)")


@app.command()
def stats(cards_root: Path = _ROOT_OPT) -> None:
    """Show coverage / connectivity health metrics for the card library."""
    repo = CardRepository(cards_root)
    for k, v in repo.coverage_stats().items():
        typer.echo(f"{k}: {v}")


@app.command()
def predicates() -> None:
    """List the controlled vocabulary used by predicates."""
    from .schemas.predicates import Operation, ResourceClass

    typer.echo("Resource classes:")
    for r in ResourceClass:
        typer.echo(f"  {r.value}")
    typer.echo("\nOperations:")
    for o in Operation:
        typer.echo(f"  {o.value}")


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
