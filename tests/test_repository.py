from pathlib import Path

from chaoschain.schemas.predicates import DefectClass
from chaoschain.store import CardRepository

REPO = Path(__file__).resolve().parents[1]
CARDS = REPO / "cards"


def test_load_all_finds_seed_card():
    repo = CardRepository(CARDS)
    loaded = repo.load_all()
    assert any(lc.card.id == "FC-0001" for lc in loaded)


def test_get_by_id():
    repo = CardRepository(CARDS)
    lc = repo.get("FC-0001")
    assert lc is not None
    assert lc.card.defect.class_ == DefectClass.RESOURCE_LEAK


def test_search_by_emit_predicate():
    repo = CardRepository(CARDS)
    hits = repo.search(emits_predicate="app_resource.connection_pool.exhausted")
    assert any(h.card.id == "FC-0001" for h in hits)


def test_coverage_stats_keys():
    repo = CardRepository(CARDS)
    s = repo.coverage_stats()
    expected = {"cards", "predicates_emitted", "predicates_observed", "bridgeable_predicates"}
    assert expected <= s.keys()
