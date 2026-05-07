"""`chaoschain library ...` — aggregate views across the card collection."""

from __future__ import annotations

import typer

from ._common import STATE, OutputFormat, emit_data, emit_info, open_repo, run_command

library_app = typer.Typer(no_args_is_help=True, add_completion=False)


@library_app.command("stats", help="Library health: counts and connectivity ratio.")
def library_stats() -> None:
    run_command(_stats_impl)


def _stats_impl() -> None:
    repo = open_repo()
    s = repo.coverage_stats()
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value=s)
    else:
        for k, v in s.items():
            emit_data(f"{k}: {v}")


@library_app.command("chains", help="Surface candidate cascade chains.")
def library_chains(
    max_hops: int = typer.Option(2, "--max-hops", help="Maximum chain length."),
) -> None:
    run_command(_chains_impl, max_hops)


def _chains_impl(max_hops: int) -> None:
    repo = open_repo()
    found = repo.find_chains(max_hops=max_hops)
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value={"chains": [[c.id for c in ch] for ch in found]})
    else:
        for ch in found:
            emit_data(" -> ".join(f"{c.id}({c.name})" for c in ch))
        emit_info(f"{len(found)} candidate chain(s)")


@library_app.command("search", help="Search cards by predicate or text.")
def library_search(
    emits: str | None = typer.Option(None, "--emits", help="Card emits this predicate."),
    observes: str | None = typer.Option(None, "--observes", help="Card observes this predicate."),
    text: str | None = typer.Option(None, "--text", help="Substring in name + mechanism."),
) -> None:
    run_command(_search_impl, emits, observes, text)


def _search_impl(emits: str | None, observes: str | None, text: str | None) -> None:
    repo = open_repo()
    hits = repo.search(emits_predicate=emits, requires_predicate=observes, text=text)
    rows = [
        {"id": lc.card.id, "class": lc.card.defect.class_.value, "name": lc.card.name}
        for lc in hits
    ]
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value={"matches": rows})
    else:
        for r in rows:
            emit_data(f"{r['id']}\t{r['class']}\t{r['name']}")
        emit_info(f"{len(rows)} match(es)")
