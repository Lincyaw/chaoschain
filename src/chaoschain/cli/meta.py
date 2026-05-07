"""`chaoschain version` and `chaoschain dump-schema` — meta commands."""

from __future__ import annotations

import importlib.metadata as md
from typing import Any

from ..schemas import FAULT_CARD_SCHEMA_VERSION
from ._common import STATE, OutputFormat, emit_data, run_command


def _package_version() -> str:
    try:
        return md.version("chaoschain")
    except md.PackageNotFoundError:
        return "0.0.0+unknown"


def version() -> None:
    run_command(_version_impl)


def _version_impl() -> None:
    payload = {
        "name": "chaoschain",
        "version": _package_version(),
        "schema_versions": {"fault_card": FAULT_CARD_SCHEMA_VERSION},
    }
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value=payload)
    else:
        emit_data(f"chaoschain {payload['version']}")
        emit_data(f"  fault_card schema: v{FAULT_CARD_SCHEMA_VERSION}")


def dump_schema() -> None:
    run_command(_dump_schema_impl)


def _dump_schema_impl() -> None:
    """Walk the registered Typer command tree and emit a JSON description.

    We introspect via click (Typer's runtime is built on click). The JSON
    shape is stable: see docs/cli-contract.md.
    """
    from . import app  # local import to avoid circularity

    click_app = _typer_to_click(app)
    commands = list(_walk(click_app, prefix=""))
    payload = {"commands": commands}
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value=payload)
    else:
        for c in commands:
            emit_data(f"{c['name']}\t{c.get('help', '') or ''}")


def _typer_to_click(app: Any) -> Any:
    """Get a click.Group/Command from a typer.Typer instance."""
    import typer.main as tm

    return tm.get_command(app)


def _walk(cmd: Any, prefix: str) -> Any:
    """Yield {name, help, args, options} for each leaf command."""
    import click

    name = (prefix + " " + cmd.name).strip() if prefix else cmd.name
    if isinstance(cmd, click.Group):
        for sub_name in sorted(cmd.commands):
            yield from _walk(cmd.commands[sub_name], prefix=name)
        return

    args: list[dict[str, Any]] = []
    options: list[dict[str, Any]] = []
    for p in cmd.params:
        entry = _param_to_dict(p)
        if isinstance(p, click.Argument):
            args.append(entry)
        else:
            options.append(entry)
    yield {
        "name": name,
        "help": (cmd.help or "").strip() or None,
        "args": args,
        "options": options,
    }


def _param_to_dict(p: Any) -> dict[str, Any]:
    import click

    type_name: str
    choices: list[str] | None = None
    if isinstance(p.type, click.Choice):
        type_name = "enum"
        choices = list(p.type.choices)
    else:
        type_name = getattr(p.type, "name", str(p.type))

    entry: dict[str, Any] = {
        "name": p.opts[0] if p.opts else p.name,
        "type": type_name,
        "required": bool(p.required),
        "default": None if isinstance(p, click.Argument) else _safe_default(p.default),
        "help": getattr(p, "help", None),
    }
    if choices is not None:
        entry["choices"] = choices
    return entry


def _safe_default(v: Any) -> Any:
    from pathlib import Path

    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, Path):
        return str(v)
    return repr(v)
