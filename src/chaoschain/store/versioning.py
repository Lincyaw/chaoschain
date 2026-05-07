"""Thin wrapper over `git` for card-level history and rollback.

Design choice: we do NOT reinvent versioning. Cards live as files; git
already gives us snapshots, diffs, history, and rollback. This module
just exposes the operations we care about scoped to a single card.

Auto-commit is opt-out (default on for CRUD ops) so that the agent's
edits are always recoverable. Group edits can pass --no-commit and
commit themselves at the end.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    """Wraps a non-zero git exit."""


def _run(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} (cwd={cwd}) failed:\n{proc.stderr.strip()}"
        )
    return proc.stdout


def repo_root(start: Path) -> Path:
    """Return the git toplevel for `start`, or raise GitError."""
    out = _run(["rev-parse", "--show-toplevel"], start).strip()
    return Path(out)


@dataclass(frozen=True)
class CardRevision:
    commit: str
    author: str
    date: str
    subject: str


def history(file: Path, *, limit: int = 50) -> list[CardRevision]:
    """Return the revision list (most recent first) for one card file."""
    root = repo_root(file.parent)
    rel = file.resolve().relative_to(root)
    fmt = "%H%x09%an%x09%aI%x09%s"
    out = _run(
        [
            "log",
            f"--max-count={limit}",
            f"--pretty=format:{fmt}",
            "--",
            str(rel),
        ],
        root,
    )
    revs: list[CardRevision] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        commit, author, date, subject = line.split("\t", 3)
        revs.append(CardRevision(commit, author, date, subject))
    return revs


def show_at(file: Path, commit: str) -> str:
    """Return the file's content at `commit` (as text)."""
    root = repo_root(file.parent)
    rel = file.resolve().relative_to(root)
    return _run(["show", f"{commit}:{rel.as_posix()}"], root)


def rollback(file: Path, commit: str, *, commit_message: str | None = None) -> None:
    """Restore `file` to its content at `commit` and (by default) commit it."""
    root = repo_root(file.parent)
    rel = file.resolve().relative_to(root)
    _run(["checkout", commit, "--", str(rel)], root)
    if commit_message is not None:
        _run(["add", str(rel)], root)
        _run(["commit", "-m", commit_message], root)


def commit_file(file: Path, message: str) -> None:
    """Stage and commit a single file. Best-effort: if not in a git repo,
    or if there's nothing to commit, raise GitError so the caller can
    decide whether to ignore or surface."""
    root = repo_root(file.parent)
    rel = file.resolve().relative_to(root)
    _run(["add", str(rel)], root)
    # `commit` returns non-zero if nothing to commit; surface as GitError.
    _run(["commit", "-m", message], root)


def remove_file(file: Path, message: str) -> None:
    """`git rm` + commit."""
    root = repo_root(file.parent)
    rel = file.resolve().relative_to(root)
    _run(["rm", str(rel)], root)
    _run(["commit", "-m", message], root)
