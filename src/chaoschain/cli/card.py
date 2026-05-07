"""`chaoschain card ...` — CRUD + history for individual fault cards."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError

from .. import exit_codes
from ..schemas import FaultCard
from ..store import versioning
from ..validators.registry import resolve_schema
from ._common import (
    STATE,
    CLIError,
    OutputFormat,
    assert_writable,
    emit_data,
    emit_info,
    open_repo,
    require_yes,
    run_command,
)

card_app = typer.Typer(no_args_is_help=True, add_completion=False)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _display_path(p: Path) -> str:
    """Render a Path relative to cwd if possible; otherwise absolute."""
    try:
        return str(p.relative_to(Path.cwd()))
    except ValueError:
        return str(p)


def _load_yaml(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise CLIError(
            f"file not found: {path}", exit_code=exit_codes.NOT_FOUND, type="not_found"
        ) from e
    except yaml.YAMLError as e:
        raise CLIError(
            f"{path}: yaml parse error: {e}",
            exit_code=exit_codes.VALIDATION,
            type="yaml_parse_error",
        ) from e


def _validate_one(path: Path, cards_root: Path) -> list[str]:
    try:
        model_cls = resolve_schema(path, cards_root)
    except ValueError as e:
        return [f"{path}: {e}"]
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"{path}: yaml parse error: {e}"]
    if not isinstance(raw, dict):
        return [f"{path}: top-level YAML must be a mapping, got {type(raw).__name__}"]
    try:
        model_cls.model_validate(raw)
    except ValidationError as e:
        return [
            f"{path}: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()
        ]
    return []


def _require_card(card_id: str) -> object:
    repo = open_repo()
    lc = repo.get(card_id)
    if lc is None:
        raise CLIError(
            f"no card with id {card_id}",
            exit_code=exit_codes.NOT_FOUND,
            type="not_found",
        )
    return lc


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


@card_app.command("list", help="List every card in the library.")
def card_list() -> None:
    run_command(_card_list_impl)


def _card_list_impl() -> None:
    repo = open_repo()
    rows = [
        {
            "id": lc.card.id,
            "name": lc.card.name,
            "class": lc.card.defect.class_.value,
            "path": _display_path(lc.path),
        }
        for lc in repo.load_all()
    ]
    if STATE.format is OutputFormat.JSON:
        emit_data(json_value={"cards": rows})
    else:
        for r in rows:
            emit_data(f"{r['id']}\t{r['class']}\t{r['name']}")


@card_app.command("get", help="Print one card. With --at, show its content at a commit.")
def card_get(
    card_id: str = typer.Argument(..., help="Card id, e.g. FC-0001"),
    at: str | None = typer.Option(None, "--at", help="Show the card at a git commit."),
) -> None:
    run_command(_card_get_impl, card_id, at)


def _card_get_impl(card_id: str, at: str | None) -> None:
    lc = _require_card(card_id)
    if at is not None:
        try:
            text = versioning.show_at(lc.path, at)  # type: ignore[attr-defined]
        except versioning.GitError as e:
            raise CLIError(str(e), exit_code=exit_codes.GIT, type="git_error") from e
        if STATE.format is OutputFormat.JSON:
            try:
                payload = yaml.safe_load(text)
            except yaml.YAMLError as e:
                raise CLIError(str(e), exit_code=exit_codes.GIT, type="git_error") from e
            emit_data(
                json_value={
                    "id": card_id,
                    "card": payload,
                    "path": str(lc.path),  # type: ignore[attr-defined]
                    "at": at,
                }
            )
        else:
            emit_data(text)
        return

    if STATE.format is OutputFormat.JSON:
        emit_data(
            json_value={
                "id": card_id,
                "card": lc.card.model_dump(by_alias=True, exclude_none=True),  # type: ignore[attr-defined]
                "path": str(lc.path),  # type: ignore[attr-defined]
            }
        )
    else:
        emit_data(
            yaml.safe_dump(
                lc.card.model_dump(by_alias=True, exclude_none=True),  # type: ignore[attr-defined]
                sort_keys=False,
                allow_unicode=True,
            )
        )


@card_app.command("validate", help="Schema-check one card or a directory of cards.")
def card_validate(
    target: Path = typer.Argument(..., help="File or directory."),
) -> None:
    run_command(_card_validate_impl, target)


def _card_validate_impl(target: Path) -> None:
    if not target.exists():
        raise CLIError(
            f"path not found: {target}",
            exit_code=exit_codes.NOT_FOUND,
            type="not_found",
        )
    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.yaml")) + sorted(target.rglob("*.yml"))
    if not files:
        raise CLIError(
            f"no YAML files found under {target}",
            exit_code=exit_codes.NOT_FOUND,
            type="not_found",
        )

    per_file: list[dict[str, object]] = []
    total_errors = 0
    for f in files:
        errs = _validate_one(f, STATE.cards_root)
        per_file.append({"path": str(f), "ok": not errs, "errors": errs})
        if errs:
            total_errors += len(errs)
            for e in errs:
                emit_info(e)
        else:
            emit_info(f"ok: {f}")

    if STATE.format is OutputFormat.JSON:
        emit_data(
            json_value={
                "files": per_file,
                "total": len(files),
                "errors": total_errors,
            }
        )
    else:
        emit_data(f"{total_errors} error(s) across {len(files)} file(s)")
    if total_errors:
        raise CLIError(
            f"{total_errors} validation error(s)",
            exit_code=exit_codes.VALIDATION,
            type="validation_error",
        )


@card_app.command("add", help="Validate + write a card (or a directory of cards).")
def card_add(
    path: Path = typer.Argument(..., help="YAML file or directory of YAML files."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing id."),
    no_commit: bool = typer.Option(False, "--no-commit", help="Skip git commit."),
    strict: bool = typer.Option(
        False, "--strict", help="Abort batch on first failure (directory mode)."
    ),
) -> None:
    run_command(_card_add_impl, path, force, no_commit, strict)


def _card_add_one(file: Path, *, force: bool, no_commit: bool) -> dict[str, object]:
    """Process a single file. Returns a result dict; raises CLIError only
    for things the caller wants to surface as a hard exit (write under
    --read-only)."""
    raw = _load_yaml(file)
    if not isinstance(raw, dict):
        return {
            "path": str(file),
            "ok": False,
            "error": "top-level YAML must be a mapping",
            "exit_code": exit_codes.VALIDATION,
        }
    try:
        card = FaultCard.model_validate(raw)
    except ValidationError as e:
        return {
            "path": str(file),
            "ok": False,
            "error": str(e),
            "exit_code": exit_codes.VALIDATION,
        }

    repo = open_repo()
    existed = repo.get(card.id) is not None
    target_dir = repo.root / card.defect.class_.value
    target = target_dir / f"{card.id}.yaml"
    action = "update" if existed else "add"

    if STATE.dry_run:
        return {
            "path": str(file),
            "ok": True,
            "action": action,
            "id": card.id,
            "would_write": str(target),
            "conflicts": [card.id] if existed and not force else [],
        }

    if existed and not force:
        return {
            "path": str(file),
            "ok": False,
            "error": f"card {card.id} already exists; pass --force",
            "exit_code": exit_codes.CONFLICT,
            "id": card.id,
        }

    assert_writable()
    written = repo.write(card)
    emit_info(f"wrote {written}")
    committed = False
    commit_sha: str | None = None
    if not no_commit:
        try:
            versioning.commit_file(written, f"{action} {card.id}: {card.name}")
            committed = True
            emit_info(f"committed: {action} {card.id}")
        except versioning.GitError as e:
            emit_info(f"warning: skipped auto-commit ({e})")
    return {
        "path": str(file),
        "ok": True,
        "action": action,
        "id": card.id,
        "written": str(written),
        "committed": committed,
        "commit": commit_sha,
    }


def _card_add_impl(path: Path, force: bool, no_commit: bool, strict: bool) -> None:
    if not path.exists():
        raise CLIError(
            f"path not found: {path}",
            exit_code=exit_codes.NOT_FOUND,
            type="not_found",
        )
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.rglob("*.yaml")) + sorted(path.rglob("*.yml"))
    if not files:
        raise CLIError(
            f"no YAML files found under {path}",
            exit_code=exit_codes.NOT_FOUND,
            type="not_found",
        )

    results: list[dict[str, object]] = []
    for f in files:
        r = _card_add_one(f, force=force, no_commit=no_commit)
        results.append(r)
        if strict and not r["ok"]:
            break

    # Pick the worst exit code among failures: 10 > 5 > 11.
    priority = {exit_codes.VALIDATION: 3, exit_codes.CONFLICT: 2, exit_codes.GIT: 1}
    failure_codes: list[int] = [
        int(r["exit_code"])  # type: ignore[call-overload]
        for r in results
        if not r["ok"]
    ]
    worst: int | None = None
    if failure_codes:
        worst = max(failure_codes, key=lambda c: priority.get(c, 0))

    # Single-file shortcut for the JSON success case (matches the
    # contract shape in docs/cli-contract.md).
    if STATE.format is OutputFormat.JSON:
        if len(results) == 1 and results[0]["ok"]:
            r = results[0]
            if STATE.dry_run:
                emit_data(
                    json_value={
                        "action": r["action"],
                        "id": r["id"],
                        "would_write": r["would_write"],
                        "conflicts": r["conflicts"],
                    }
                )
            else:
                emit_data(
                    json_value={
                        "action": r["action"],
                        "id": r["id"],
                        "path": r["written"],
                        "committed": r["committed"],
                        "commit": r["commit"],
                    }
                )
        else:
            emit_data(json_value={"results": results})
    else:
        for r in results:
            if r["ok"]:
                if STATE.dry_run:
                    emit_data(f"would {r['action']} {r['id']} -> {r['would_write']}")
                else:
                    emit_data(f"{r['action']} {r['id']} -> {r['written']}")
            else:
                emit_data(f"FAIL {r['path']}: {r.get('error', '')}")

    if worst is not None:
        type_for = {
            exit_codes.VALIDATION: "validation_error",
            exit_codes.CONFLICT: "conflict",
            exit_codes.GIT: "git_error",
        }
        raise CLIError(
            "one or more files failed",
            exit_code=int(worst),
            type=type_for.get(int(worst), "error"),
        )


@card_app.command("rm", help="Delete a card by id. Destructive: requires --yes.")
def card_rm(
    card_id: str = typer.Argument(..., help="Card id."),
    no_commit: bool = typer.Option(False, "--no-commit", help="Skip git commit."),
) -> None:
    run_command(_card_rm_impl, card_id, no_commit)


def _card_rm_impl(card_id: str, no_commit: bool) -> None:
    require_yes("card rm")
    lc = _require_card(card_id)

    if STATE.dry_run:
        if STATE.format is OutputFormat.JSON:
            emit_data(
                json_value={
                    "action": "remove",
                    "id": card_id,
                    "would_delete": str(lc.path),  # type: ignore[attr-defined]
                }
            )
        else:
            emit_data(f"would remove {card_id} ({lc.path})")  # type: ignore[attr-defined]
        return

    assert_writable()
    committed = False
    if no_commit:
        lc.path.unlink()  # type: ignore[attr-defined]
        emit_info(f"deleted {lc.path}")  # type: ignore[attr-defined]
    else:
        try:
            versioning.remove_file(lc.path, f"remove {card_id}: {lc.card.name}")  # type: ignore[attr-defined]
            committed = True
            emit_info(f"deleted and committed {card_id}")
        except versioning.GitError as e:
            lc.path.unlink(missing_ok=True)  # type: ignore[attr-defined]
            emit_info(f"deleted {lc.path}; skipped commit ({e})")  # type: ignore[attr-defined]

    if STATE.format is OutputFormat.JSON:
        emit_data(json_value={"action": "remove", "id": card_id, "committed": committed})
    else:
        emit_data(f"removed {card_id}")


@card_app.command("history", help="Show git revision history for one card.")
def card_history(
    card_id: str = typer.Argument(...),
    limit: int = typer.Option(50, "--limit", help="Max revisions."),
) -> None:
    run_command(_card_history_impl, card_id, limit)


def _card_history_impl(card_id: str, limit: int) -> None:
    lc = _require_card(card_id)
    try:
        revs = versioning.history(lc.path, limit=limit)  # type: ignore[attr-defined]
    except versioning.GitError as e:
        raise CLIError(str(e), exit_code=exit_codes.GIT, type="git_error") from e
    if STATE.format is OutputFormat.JSON:
        emit_data(
            json_value={
                "id": card_id,
                "revisions": [
                    {
                        "commit": r.commit,
                        "short": r.commit[:10],
                        "author": r.author,
                        "date": r.date,
                        "subject": r.subject,
                    }
                    for r in revs
                ],
            }
        )
    else:
        for r in revs:
            emit_data(f"{r.commit[:10]}\t{r.date}\t{r.author}\t{r.subject}")
        emit_info(f"{len(revs)} revision(s)")


@card_app.command("show-at", help="Print a card's content at a git commit.")
def card_show_at(
    card_id: str = typer.Argument(...),
    commit: str = typer.Argument(..., help="Git commit (full or short SHA)."),
) -> None:
    run_command(_card_get_impl, card_id, commit)


@card_app.command("rollback", help="Restore a card to its content at a commit. Destructive.")
def card_rollback(
    card_id: str = typer.Argument(...),
    commit: str = typer.Argument(...),
    no_commit: bool = typer.Option(False, "--no-commit", help="Skip git commit."),
) -> None:
    run_command(_card_rollback_impl, card_id, commit, no_commit)


def _card_rollback_impl(card_id: str, commit: str, no_commit: bool) -> None:
    require_yes("card rollback")
    lc = _require_card(card_id)

    if STATE.dry_run:
        if STATE.format is OutputFormat.JSON:
            emit_data(
                json_value={"action": "rollback", "id": card_id, "to": commit, "would_apply": True}
            )
        else:
            emit_data(f"would rollback {card_id} to {commit[:10]}")
        return

    assert_writable()
    msg = None if no_commit else f"rollback {card_id} to {commit[:10]}"
    try:
        versioning.rollback(lc.path, commit, commit_message=msg)  # type: ignore[attr-defined]
    except versioning.GitError as e:
        raise CLIError(str(e), exit_code=exit_codes.GIT, type="git_error") from e
    emit_info(f"rolled back {card_id} to {commit[:10]}")
    if STATE.format is OutputFormat.JSON:
        emit_data(
            json_value={
                "action": "rollback",
                "id": card_id,
                "to": commit,
                "committed": not no_commit,
            }
        )
    else:
        emit_data(f"rolled back {card_id} to {commit[:10]}")
