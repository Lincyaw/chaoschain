"""Card store — load, search, and write fault cards.

This package is the **only** thing that knows how cards are laid out on disk.
Agents (Claude Code or any other) consume cards exclusively through this API,
so changing the on-disk layout never breaks downstream consumers.

Design contract:
  - All read paths return Pydantic models, not raw dicts.
  - All write paths validate before persisting (no half-formed cards on disk).
  - Search is intentionally simple (predicate / field exact match + substring).
    Smarter retrieval (embedding, graph queries) is out of scope for v0.1.
"""

from . import versioning
from .repository import CardRepository

__all__ = ["CardRepository", "versioning"]
