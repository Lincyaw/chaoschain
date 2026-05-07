"""Schema definitions for chaoschain knowledge artifacts.

Each artifact type lives in its own module and exposes:
  - a top-level Pydantic model
  - a SCHEMA_VERSION constant

The validator registry (validators/registry.py) discovers schemas by
folder name under cards/, so adding a new schema = new module here +
new entry in the registry.
"""

from .fault_card import SCHEMA_VERSION as FAULT_CARD_SCHEMA_VERSION
from .fault_card import FaultCard

__all__ = ["FAULT_CARD_SCHEMA_VERSION", "FaultCard"]
