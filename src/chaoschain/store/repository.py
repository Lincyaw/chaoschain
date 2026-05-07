"""CardRepository — file-backed CRUD + search over fault cards.

The repository is the boundary between agents and storage. Agents call:
  - `load_all()`     — enumerate every card
  - `get(id)`        — fetch by stable id
  - `search(...)`    — filter by predicate / class / text
  - `write(card)`    — persist a validated card to its canonical path

Anything that needs raw YAML access bypasses this on its own risk.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..schemas import FaultCard
from ..schemas.predicates import DefectClass


@dataclass(frozen=True)
class LoadedCard:
    card: FaultCard
    path: Path


class CardRepository:
    def __init__(self, cards_root: Path):
        self.root = Path(cards_root).resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"cards root does not exist: {self.root}")

    # ------------------------- read paths -------------------------

    def iter_files(self) -> Iterator[Path]:
        for ext in ("*.yaml", "*.yml"):
            yield from sorted(self.root.rglob(ext))

    def load_all(self) -> list[LoadedCard]:
        out: list[LoadedCard] = []
        for p in self.iter_files():
            with p.open() as f:
                raw = yaml.safe_load(f)
            out.append(LoadedCard(card=FaultCard.model_validate(raw), path=p))
        return out

    def get(self, card_id: str) -> LoadedCard | None:
        for lc in self.load_all():
            if lc.card.id == card_id:
                return lc
        return None

    # ------------------------- search -----------------------------

    def search(
        self,
        *,
        defect_class: DefectClass | None = None,
        emits_predicate: str | None = None,
        requires_predicate: str | None = None,
        text: str | None = None,
    ) -> list[LoadedCard]:
        """Filter cards by structured fields. All filters AND together.

        - emits_predicate: card has this exact predicate in downstream_effects.
        - requires_predicate: card observes this predicate (i.e. matches the
          activation surface — useful for "what could be causing this signal?").
        - text: case-insensitive substring search across name + mechanism.
        """
        results = []
        for lc in self.load_all():
            c = lc.card
            if defect_class is not None and c.defect.class_ != defect_class:
                continue
            if emits_predicate is not None and not any(
                e.predicate == emits_predicate for e in c.downstream_effects
            ):
                continue
            if requires_predicate is not None and not any(
                m.predicate == requires_predicate for m in c.observable.metrics
            ):
                continue
            if text is not None:
                hay = (c.name + "\n" + c.defect.mechanism).lower()
                if text.lower() not in hay:
                    continue
            results.append(lc)
        return results

    def find_chains(self, *, max_hops: int = 2) -> list[list[FaultCard]]:
        """Return all simple chains A -> B (-> C ...) up to `max_hops`.

        Two cards link if any of A's downstream_effects predicates appears
        as one of B's observed metric predicates. This is the v0.1
        "puzzle connector" — naive but useful for surfacing candidate
        chains for human review.
        """
        cards = [lc.card for lc in self.load_all()]
        emit_index: dict[str, list[FaultCard]] = {}
        for c in cards:
            for m in c.observable.metrics:
                emit_index.setdefault(m.predicate, []).append(c)

        chains: list[list[FaultCard]] = []

        def extend(chain: list[FaultCard], hops_left: int) -> None:
            tail = chain[-1]
            for eff in tail.downstream_effects:
                for nxt in emit_index.get(eff.predicate, []):
                    if nxt.id in {x.id for x in chain}:
                        continue
                    new_chain = [*chain, nxt]
                    chains.append(new_chain)
                    if hops_left > 1:
                        extend(new_chain, hops_left - 1)

        for c in cards:
            extend([c], max_hops - 1)
        return chains

    # ------------------------- write paths ------------------------

    def write(self, card: FaultCard, *, subdir: str | None = None) -> Path:
        """Persist a card. Validates by re-parsing through the schema first.

        Default subdir is the card's defect class.
        Filename is derived from the card id.
        """
        FaultCard.model_validate(card.model_dump(by_alias=True))
        target_dir = self.root / (subdir or card.defect.class_.value)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{card.id}.yaml"
        with target.open("w") as f:
            yaml.safe_dump(
                card.model_dump(by_alias=True, exclude_none=True),
                f,
                sort_keys=False,
                allow_unicode=True,
            )
        return target

    def all_predicates_emitted(self) -> set[str]:
        return {e.predicate for lc in self.load_all() for e in lc.card.downstream_effects}

    def all_predicates_observed(self) -> set[str]:
        return {m.predicate for lc in self.load_all() for m in lc.card.observable.metrics}

    def coverage_stats(self) -> dict[str, int | float]:
        cards = self.load_all()
        emitted = self.all_predicates_emitted()
        observed = self.all_predicates_observed()
        bridgeable = emitted & observed
        return {
            "cards": len(cards),
            "predicates_emitted": len(emitted),
            "predicates_observed": len(observed),
            "bridgeable_predicates": len(bridgeable),
            "connectivity_ratio": (
                len(bridgeable) / len(emitted) if emitted else 0.0
            ),
        }


def iter_cards(repo: CardRepository) -> Iterable[FaultCard]:
    """Convenience: iterate cards without paths."""
    for lc in repo.load_all():
        yield lc.card
