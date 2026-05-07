"""CLI contract tests.

Each test verifies one piece of the contract documented in
docs/cli-contract.md. The suite is deliberately small — the underlying
model behavior is covered by tests/test_repository.py and friends; these
tests exist to guard the agent-facing surface.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chaoschain import exit_codes
from chaoschain.cli import app

REPO = Path(__file__).resolve().parents[1]
CARDS = REPO / "cards"
FIXTURES = REPO / "tests" / "fixtures"


@pytest.fixture
def cards_dir(tmp_path: Path) -> Path:
    """Per-test copy of cards/ so destructive tests don't pollute the repo."""
    dest = tmp_path / "cards"
    shutil.copytree(CARDS, dest)
    return dest


@pytest.fixture
def runner() -> CliRunner:
    # CliRunner separates stdout/stderr by default in current click.
    return CliRunner()


def _root(cards_dir: Path, *args: str) -> list[str]:
    return ["--cards-root", str(cards_dir), *args]


def test_card_list_text(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "card", "list"))
    assert r.exit_code == 0, r.stderr
    assert "FC-0001" in r.stdout


def test_card_list_json(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "--format", "json", "card", "list"))
    assert r.exit_code == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "cards" in payload
    assert any(c["id"] == "FC-0001" for c in payload["cards"])


def test_card_get_not_found_exit_3(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "card", "get", "FC-9999"))
    assert r.exit_code == exit_codes.NOT_FOUND


def test_card_rm_without_yes_exits_6(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "card", "rm", "FC-0001"))
    assert r.exit_code == exit_codes.REFUSED
    # Card still on disk.
    assert (cards_dir / "resource_leak" / "db-connection-exception-path.yaml").exists()


def test_card_add_dry_run_no_write(runner: CliRunner, cards_dir: Path) -> None:
    fixture = FIXTURES / "dry_run_input.yaml"
    target = cards_dir / "resource_leak" / "FC-9100.yaml"
    assert not target.exists()
    r = runner.invoke(
        app,
        _root(cards_dir, "--format", "json", "--dry-run", "card", "add", str(fixture)),
    )
    assert r.exit_code == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["action"] == "add"
    assert payload["id"] == "FC-9100"
    assert "would_write" in payload
    assert not target.exists()


def test_read_only_blocks_write(runner: CliRunner, cards_dir: Path) -> None:
    target = cards_dir / "resource_leak" / "db-connection-exception-path.yaml"
    assert target.exists()
    r = runner.invoke(
        app,
        _root(cards_dir, "--read-only", "--yes", "card", "rm", "FC-0001"),
    )
    assert r.exit_code == exit_codes.PERMISSION
    assert target.exists()


def test_dump_schema_is_valid_json(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "--format", "json", "dump-schema"))
    assert r.exit_code == 0, r.stderr
    payload = json.loads(r.stdout)
    names = {c["name"] for c in payload["commands"]}
    expected = {
        "card list",
        "card get",
        "card add",
        "card rm",
        "card validate",
        "card history",
        "card show-at",
        "card rollback",
        "library stats",
        "library chains",
        "library search",
        "vocab list",
        "vocab show",
        "version",
        "dump-schema",
    }
    assert expected <= names, f"missing: {expected - names}"


def test_version_json(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "--format", "json", "version"))
    assert r.exit_code == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["name"] == "chaoschain"
    assert "version" in payload
    assert payload["schema_versions"]["fault_card"] == 1


def test_vocab_show_invalid_predicate(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "--format", "json", "vocab", "show", "foo.bar.baz"))
    assert r.exit_code == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["predicate"] == "foo.bar.baz"
    assert payload["valid"] is False
    assert "error" in payload


def test_library_stats_json_schema(runner: CliRunner, cards_dir: Path) -> None:
    r = runner.invoke(app, _root(cards_dir, "--format", "json", "library", "stats"))
    assert r.exit_code == 0, r.stderr
    payload = json.loads(r.stdout)
    for k in (
        "cards",
        "predicates_emitted",
        "predicates_observed",
        "bridgeable_predicates",
        "connectivity_ratio",
    ):
        assert k in payload
