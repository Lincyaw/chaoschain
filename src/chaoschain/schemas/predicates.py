"""Controlled vocabulary for StatePredicate — the ISA of the fault card library.

A predicate has the shape `<resource_class>.<object>.<operation>[.<modifier>]`.
The first three components are controlled enums; the modifier is free text but
should be reused across cards to keep clustering meaningful.

Two cards link via `downstream_effects -> system_requirements/activation`
matching on these predicates, so consistency here is load-bearing.
"""

from __future__ import annotations

from enum import StrEnum


class ResourceClass(StrEnum):
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    CONCURRENCY = "concurrency"
    APP_RESOURCE = "app_resource"
    TIME = "time"
    CONFIG = "config"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    TOPOLOGY = "topology"


class Operation(StrEnum):
    EXHAUSTED = "exhausted"
    SATURATED = "saturated"
    LEAKED = "leaked"
    ACCUMULATED = "accumulated"
    CONTENDED = "contended"
    BLOCKED = "blocked"
    DELAYED = "delayed"
    STALLED = "stalled"
    DEGRADED = "degraded"
    CORRUPTED = "corrupted"
    INCONSISTENT = "inconsistent"
    AMPLIFIED = "amplified"
    SILENCED = "silenced"
    MASKED = "masked"


class Timescale(StrEnum):
    SUB_SECOND = "sub_second"
    SECONDS = "seconds"
    MINUTES_TO_HOURS = "minutes_to_hours"
    HOURS_TO_DAYS = "hours_to_days"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectClass(StrEnum):
    RESOURCE_LEAK = "resource_leak"
    CONCURRENCY = "concurrency"
    ERROR_HANDLING = "error_handling"
    CONFIG_COUPLING = "config_coupling"
    AGING = "aging"
    DESIGN_ANTI_PATTERN = "design_anti_pattern"


class DetectionDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    SILENT = "silent"


class EvidenceType(StrEnum):
    BUG_REPORT = "bug_report"
    INCIDENT = "incident"
    POSTMORTEM = "postmortem"
    ACADEMIC = "academic"
    COMMIT = "commit"
    CVE = "cve"
    EXPERIMENT = "experiment"


def parse_predicate(s: str) -> tuple[ResourceClass, str, Operation, str | None]:
    """Parse `class.object.op[.modifier]`.

    `object` is intentionally free text — it names the concrete resource
    instance (e.g. `connection_pool`, `memory`, `db_client`). Constraining it
    too early would prevent the vocabulary from growing with real cards.
    """
    parts = s.split(".")
    if len(parts) < 3:
        raise ValueError(
            f"predicate {s!r} must have at least 3 dotted parts: <class>.<object>.<op>"
        )
    cls = ResourceClass(parts[0])
    obj = parts[1]
    if not obj:
        raise ValueError(f"predicate {s!r} has empty object segment")
    op = Operation(parts[2])
    modifier = ".".join(parts[3:]) if len(parts) > 3 else None
    return cls, obj, op, modifier


def is_valid_predicate(s: str) -> bool:
    try:
        parse_predicate(s)
    except (ValueError, KeyError):
        return False
    return True
