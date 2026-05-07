# FaultCard schema v0.1

Authoritative reference for the FaultCard schema. The Pydantic model in
`src/chaoschain/schemas/fault_card.py` is the source of truth — this
document explains intent. If they disagree, the model wins and the doc
gets updated.

## Top-level fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `id` | `FC-NNNN` string | yes | Stable identity. Never reused. |
| `name` | str | yes | Human-readable label. |
| `schema_version` | int | yes | Version pin (currently `1`). |
| `last_reviewed` | ISO date | no | When a human last sanity-checked this card. |
| `defect` | object | yes | Static side: what's wrong in code. |
| `activation` | object | yes | Conditions that wake the defect up. |
| `observable` | object | yes | Runtime signals visible while active. |
| `downstream_effects` | list | yes | The "output port" — what this card emits to other cards. |
| `system_requirements` | list | no | Structural conditions for instantiation in a target system. |
| `evidence` | list | yes (≥1) | Where this card came from. |
| `reproducibility` | object | no | Filled when the card is confirmed via chaos experiment. |

## defect

Captures the static defect.

- `class` — one of `resource_leak`, `concurrency`, `error_handling`,
  `config_coupling`, `aging`, `design_anti_pattern`.
- `subclass` — free text refinement (e.g., `connection_handle`).
- `mechanism` — natural-language explanation; both humans and LLMs
  read this.
- `code_signature` — optional list of `(language, pattern)` examples,
  used to bootstrap static scanners.

## activation

When the dormant defect becomes live.

- `required` — free-text predicates that ALL must hold. Free text by
  design: activation conditions vary too much to enumerate at v0.1.
- `amplifying` — accelerators / aggravators (free text).
- `timescale` — how fast the activation completes once conditions hold.
  Enum: `sub_second` / `seconds` / `minutes_to_hours` / `hours_to_days`.

## observable

Runtime signals while the card is active. Each list item is independent
— a card may produce *any* of its listed signals depending on the
deployment.

- `metrics[].predicate` — controlled `<class>.<object>.<op>[.modifier]`
  predicate.
- `logs[].pattern` / `traces[].pattern` — free text, matched as
  substrings or regexes by downstream tools.
- `detection_difficulty` — `easy` (loud), `medium`, or `silent` (slips
  past existing alerts). Silent is the high-value signal for chain
  construction.

## downstream_effects

**This is the link surface.** Every entry is a controlled predicate
plus confidence and delay. Card B can chain after card A iff A's
`downstream_effects[*].predicate` appears in B's `observable.metrics[*].predicate`
or matches one of B's `activation.required` predicates.

## system_requirements

Structural conditions for the card to apply to a given system. Schema
deliberately permissive (`extra="allow"`) — the vocabulary will
ossify as we see real cards. Common keys so far: `has_component`,
`exception_handling_present`, `language`.

## evidence

At least one entry required. `human_reviewed: true` is the gate for
"this card is real," not just "the schema accepted it."

## reproducibility

Set by the chaos pipeline, not by hand. `confirmed_in_chaos: true` is
the only thing that turns a card from hypothesis into fact.

## What changes a v0.2 bump

Any of the following requires bumping `schema_version`:

- Removing or renaming a field.
- Changing a field's type or enum values.
- Tightening a constraint that existing cards may violate.

Adding optional fields with defaults does not require a bump.
