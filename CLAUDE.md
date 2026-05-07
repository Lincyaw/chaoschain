# chaoschain

Heterogeneous causal knowledge base for cascade fault chain mining.

## What this repo IS / IS NOT

**IS**: a Python library + CLI + Claude Code skill bundle that defines the
schema for fault cards, stores them as YAML files in `cards/`, and provides
search / validate / chain-discovery primitives that agents call.

**IS NOT**: an agent. No autonomous loop, no chaos injector, no LLM glue.
Agents (Claude Code or otherwise) consume this library to manage the
knowledge base.

Full reasoning: `docs/first-principles.md` (load-bearing — read once before
contributing).

<!-- auto-harness:begin -->
## Core principles

Three axioms govern all work. Fall back to these when a skill's instructions
don't cover a situation:

1. **Quality over quantity** — a few things done well beats many done poorly.
   Applies to fault cards, tests, observations, code, docs. If you can't say
   why each item exists, there are too many. Think three times before adding,
   once before removing.
2. **Surface problems early** — fail fast, validate before investing. The
   schema is enforced at write time; an unvalidated card does not exist.
   Never hide complexity to make something look simpler.
3. **Deliberate execution** — every decision traceable to a reason. Understand
   before acting; validate manually before automating; measure before
   optimizing; consider removing before adding.

Full text: `/home/ddq/.claude/plugins/cache/autoharness/autoharness/1.1.3/references/principles.md`.

## Project first principles (chaoschain-specific)

- **This repo is storage + schema + skill, not an agent.** When in doubt
  about scope, the agent logic lives elsewhere.
- **Fault cards are the unit of knowledge.** Each card captures one defect
  pattern with mechanism, activation, observable signals, downstream effects,
  evidence, and reproducibility status.
- **Predicate vocabulary is the ISA.** `<resource_class>.<object>.<operation>[.<modifier>]`.
  Cards link via shared predicates. Vocabulary changes are reviewed with
  schema-level care.
- **Connectivity > coverage.** Library health is measured by the bridgeable
  predicate ratio (`uv run chaoschain library stats`), not card count. A library of
  500 disconnected cards is worse than 50 cards that form chains.
- **Reproducibility is the only fact gate.** A card with
  `reproducibility.confirmed_in_chaos: false` is a hypothesis, not a fact.

## North-star targets

These are placeholders — set real baselines after the first 50 cards exist.

1. **Library connectivity** — `bridgeable_predicates / predicates_emitted`
   from `chaoschain library stats`. Target: ≥ 0.3 once card count ≥ 30.
   Measure: `uv run chaoschain library stats`
   Mechanism: script

2. **Schema validity** — every YAML under `cards/` parses cleanly.
   Currently: enforced.
   Measure: `uv run chaoschain card validate cards/`
   Mechanism: script (CI gate)

3. **Reproducibility ratio** — fraction of cards with
   `reproducibility.confirmed_in_chaos: true`. Target: ≥ 0.5 once chaos
   pipeline exists.
   Measure: not yet automated (TODO)
   Mechanism: script

Secondary tiebreaker: when forced to choose, prefer **fewer, higher-quality
cards / tests / lines of code** over more.

## Dev-loop stages

| Stage | Command | Notes |
|-------|---------|-------|
| Test | `uv run pytest` | Run after every code change |
| Lint | `uv run ruff check src/ tests/` | |
| Format | `uv run ruff format src/ tests/` | |
| Type check | `uv run mypy` | |
| Validate cards | `uv run chaoschain card validate cards/` | Run after any card change |
| Library stats | `uv run chaoschain library stats` | Track connectivity over time |
| Candidate chains | `uv run chaoschain library chains --max-hops 3` | Sanity check linking |
| Card history | `uv run chaoschain card history FC-NNNN` | Inspect change log per card |
| Card rollback | `uv run chaoschain --yes card rollback FC-NNNN <sha>` | Restore prior version |

## Versioning / snapshots

Cards are tracked in git. Every CLI write (`card add`, `card rm`,
`card rollback`) auto-commits unless `--no-commit` is passed. Destructive
ops require `--yes`. To inspect or revert a card:

```
chaoschain card history FC-0001                       # revisions for one card
chaoschain card show-at FC-0001 <commit>              # card content at a commit
chaoschain --yes card rollback FC-0001 <commit>       # restore + commit
```

The repo IS the version store — there is no separate snapshot mechanism.
The full CLI contract (commands, flags, exit codes, JSON shapes) lives in
`docs/cli-contract.md`.

## Project conventions

- **Package manager: `uv` only.** Do not use pip / poetry / pdm. All commands
  go through `uv run`.
- **Distributable via pip.** Public surface is `chaoschain` CLI + the
  `chaoschain.{schemas,store,validators}` Python API. Consumers (agents,
  pipelines) install with `pip install chaoschain`.
- **Cards live in `cards/<defect_class>/*.yaml`.** Top-level folder names are
  the schema dispatch keys (see `validators/registry.py`).
- **Predicates must come from the controlled vocabulary** in
  `src/chaoschain/schemas/predicates.py`. Inventing predicates inline is a
  vocabulary change and must be reviewed.
- **Evidence is mandatory.** A card with no `evidence[]` entries is rejected
  by the schema. `human_reviewed: true` is the gate for "this is real."
- **Schema changes require migration.** Bumping `schema_version` is paired
  with a migration test and a pass over existing cards.
- **Quality over quantity, applied strictly:**
  - Don't add fault cards in bulk. Add one. Validate it. Confirm it
    connects. Then consider another.
  - Don't expand the test suite for symmetry. Each test must verify a
    distinct requirement that would actually fail without it.
  - Don't add abstractions, helpers, or fields ahead of need. The current
    repo intentionally has no DI, no plugins, no async — add when forced.

## Card curation workflow

When asked to add, dedupe, or maintain cards, the **card-curator** skill at
`.claude/skills/card-curator/SKILL.md` is the authoritative process.
Highlights:

1. Search before creating. Most "new" cards are variants of existing ones.
2. Reject vague evidence. "There's a bug like this" is not a card.
3. New predicates require a vocabulary change, not inline invention.
4. Check `chaoschain library stats` before and after — note the delta.

## Active skills

- `.claude/skills/card-curator` — local skill for adding / deduping /
  maintaining cards in this repo (quality-gated, vocabulary-aware).
<!-- auto-harness:end -->
