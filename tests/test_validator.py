from pathlib import Path

import pytest
import yaml

from chaoschain.schemas import FaultCard
from chaoschain.validators.registry import resolve_schema

REPO = Path(__file__).resolve().parents[1]
CARDS = REPO / "cards"
FIXTURES = Path(__file__).parent / "fixtures"


def _load(p: Path) -> dict:
    with p.open() as f:
        return yaml.safe_load(f)


def test_seed_card_validates():
    p = CARDS / "resource_leak" / "db-connection-exception-path.yaml"
    FaultCard.model_validate(_load(p))


def test_registry_resolves_known_folder():
    p = CARDS / "resource_leak" / "db-connection-exception-path.yaml"
    assert resolve_schema(p, CARDS) is FaultCard


def test_registry_rejects_unknown_folder(tmp_path: Path):
    bad = tmp_path / "cards" / "not_a_real_kind" / "x.yaml"
    bad.parent.mkdir(parents=True)
    bad.write_text("id: FC-0000")
    with pytest.raises(ValueError, match="unknown schema folder"):
        resolve_schema(bad, tmp_path / "cards")


@pytest.mark.parametrize(
    "fixture,expect_in_message",
    [
        ("invalid_bad_predicate.yaml", "invalid predicate"),
        ("invalid_extra_field.yaml", "Extra inputs are not permitted"),
        ("invalid_missing_evidence.yaml", "at least 1 item"),
    ],
)
def test_invalid_fixtures_rejected(fixture: str, expect_in_message: str):
    with pytest.raises(Exception) as excinfo:
        FaultCard.model_validate(_load(FIXTURES / fixture))
    assert expect_in_message in str(excinfo.value)
