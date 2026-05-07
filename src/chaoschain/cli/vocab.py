"""`chaoschain vocab ...` — controlled predicate vocabulary."""

from __future__ import annotations

import typer

from ..schemas.predicates import Operation, ResourceClass, parse_predicate
from ._common import STATE, OutputFormat, emit_data, run_command

vocab_app = typer.Typer(no_args_is_help=True, add_completion=False)


@vocab_app.command("list", help="List the controlled vocabulary enums.")
def vocab_list() -> None:
    run_command(_list_impl)


def _list_impl() -> None:
    classes = [r.value for r in ResourceClass]
    ops = [o.value for o in Operation]
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value={"resource_classes": classes, "operations": ops})
    else:
        emit_data("Resource classes:")
        for r in classes:
            emit_data(f"  {r}")
        emit_data("")
        emit_data("Operations:")
        for o in ops:
            emit_data(f"  {o}")


@vocab_app.command("show", help="Parse a predicate and report its components.")
def vocab_show(
    predicate: str = typer.Argument(..., help="e.g. app_resource.connection_pool.exhausted"),
) -> None:
    run_command(_show_impl, predicate)


def _show_impl(predicate: str) -> None:
    try:
        cls, obj, op, modifier = parse_predicate(predicate)
        result: dict[str, object] = {
            "predicate": predicate,
            "valid": True,
            "resource_class": cls.value,
            "object": obj,
            "operation": op.value,
            "modifier": modifier,
        }
        ok = True
        err: str | None = None
    except (ValueError, KeyError) as e:
        ok = False
        err = str(e)
        result = {"predicate": predicate, "valid": False, "error": err}

    if STATE.format is OutputFormat.JSON:
        emit_data(json_value=result)
    else:
        if ok:
            emit_data(f"predicate: {predicate}")
            emit_data("  valid: true")
            emit_data(f"  resource_class: {result['resource_class']}")
            emit_data(f"  object: {result['object']}")
            emit_data(f"  operation: {result['operation']}")
            emit_data(f"  modifier: {result['modifier']}")
        else:
            emit_data(f"predicate: {predicate}")
            emit_data("  valid: false")
            emit_data(f"  error: {err}")
