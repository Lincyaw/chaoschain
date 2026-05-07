"""Schema dispatch / validation helpers.

The actual CLI lives at `chaoschain.cli`; this subpackage owns the
folder-to-schema registry only.
"""

from .registry import REGISTRY, resolve_schema

__all__ = ["REGISTRY", "resolve_schema"]
