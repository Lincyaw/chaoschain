"""FaultCard v0.1 — the unit of the chaoschain knowledge base.

Design principles (see docs/first-principles.md):
  - Cards link via `downstream_effects` <-> `system_requirements`/activation.
  - Predicates use the controlled StatePredicate vocabulary.
  - Activation conditions stay free text (high diversity); effects/requirements
    are the structured "ports" that participate in automatic chain assembly.
  - Reproducibility is a runtime-filled field, not a manual claim.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .predicates import (
    Confidence,
    DefectClass,
    DetectionDifficulty,
    EvidenceType,
    Timescale,
    is_valid_predicate,
)

SCHEMA_VERSION = 1


class CodeSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    pattern: str


class Defect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_: DefectClass = Field(alias="class")
    subclass: str | None = None
    mechanism: str
    code_signature: list[CodeSignature] = Field(default_factory=list)


class Activation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: list[str] = Field(default_factory=list)
    amplifying: list[str] = Field(default_factory=list)
    timescale: Timescale


class MetricSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predicate: str
    direction: str | None = None
    shape: str | None = None

    @field_validator("predicate")
    @classmethod
    def _check_predicate(cls, v: str) -> str:
        if not is_valid_predicate(v):
            raise ValueError(f"invalid predicate: {v!r}")
        return v


class LogSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    frequency: str | None = None


class TraceSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str


class Observable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[MetricSignal] = Field(default_factory=list)
    logs: list[LogSignal] = Field(default_factory=list)
    traces: list[TraceSignal] = Field(default_factory=list)
    detection_difficulty: DetectionDifficulty


class DownstreamEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predicate: str
    confidence: Confidence
    delay: Timescale

    @field_validator("predicate")
    @classmethod
    def _check_predicate(cls, v: str) -> str:
        if not is_valid_predicate(v):
            raise ValueError(f"invalid predicate: {v!r}")
        return v


class SystemRequirement(BaseModel):
    """Structural condition the target system must satisfy for the card to
    instantiate. Kept as free-form key/value to allow vocabulary growth — but
    keys SHOULD cluster across cards (`has_component`, `language`, ...)."""

    model_config = ConfigDict(extra="allow")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    type: EvidenceType
    extracted_by: str | None = None
    human_reviewed: bool = False


class Reproducibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed_in_chaos: bool = False
    last_attempt: str | None = None
    recipe_ref: str | None = None


class FaultCard(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^FC-\d{4,}$")
    name: str
    schema_version: int = Field(default=SCHEMA_VERSION)
    last_reviewed: str | None = None

    defect: Defect
    activation: Activation
    observable: Observable
    downstream_effects: list[DownstreamEffect]
    system_requirements: list[SystemRequirement] = Field(default_factory=list)
    evidence: list[Evidence] = Field(min_length=1)
    reproducibility: Reproducibility = Field(default_factory=Reproducibility)

    @field_validator("schema_version")
    @classmethod
    def _check_version(cls, v: int) -> int:
        if v != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {v} not supported (current: {SCHEMA_VERSION}). "
                "Add a migration before bumping."
            )
        return v
