"""Schema registry — maps directory layout to Pydantic models.

Layout convention:
  cards/<schema_kind>/<...subfolders.../*.yaml>

`<schema_kind>` is matched against the registry. Anything not in the
registry is reported as an unknown kind (loud failure — surface problems
early).

For FaultCard cards, the top-level subfolder under `cards/` is the
defect class (e.g. `resource_leak/`, `concurrency/`). All of these are
mapped to the FaultCard schema. New artifact types live in sibling
top-level folders that we register explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from ..schemas import FaultCard

# Top-level folder under cards/ -> Pydantic model.
# All current top-level folders are FaultCard subclasses; future artifact
# types (e.g. `runtime_observations/`, `injection_recipes/`) get their
# own entries.
FAULT_CARD_FOLDERS = {
    "resource_leak",
    "concurrency",
    "error_handling",
    "config",
    "aging",
}

REGISTRY: Mapping[str, type[BaseModel]] = {
    folder: FaultCard for folder in FAULT_CARD_FOLDERS
}


def resolve_schema(card_path: Path, cards_root: Path) -> type[BaseModel]:
    """Return the Pydantic model that should validate `card_path`.

    Raises ValueError if the top-level folder under `cards_root` is not
    in the registry.
    """
    rel = card_path.resolve().relative_to(cards_root.resolve())
    if not rel.parts:
        raise ValueError(f"card path {card_path} is the cards root itself")
    top = rel.parts[0]
    if top not in REGISTRY:
        raise ValueError(
            f"unknown schema folder {top!r} (registered: {sorted(REGISTRY)}). "
            "Add it to validators/registry.py."
        )
    return REGISTRY[top]
