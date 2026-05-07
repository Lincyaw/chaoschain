# First principles

Distillation of the design conversation that bootstrapped this repo.
These principles outrank any specific schema field or code pattern. If a
decision contradicts the principles, the principle wins and the artifact
gets revised.

## What this repo IS

A **library + CLI + skill bundle** that:

1. Defines the **schema** for fault cards (and future artifact types).
2. Provides **storage and retrieval** primitives (`CardRepository`, CLI).
3. Ships a small set of **Claude Code skills** describing how an agent
   should mine, deduplicate, and maintain the card library.

## What this repo IS NOT

- **Not an agent.** No autonomous loop, no LLM glue, no chaos injector.
  Those live in agents that consume this library.
- **Not a graph database.** Cards are files. Connectivity is a query
  result, not stored state.
- **Not a planner.** Long-chain reasoning, planning, dataset generation —
  all downstream consumers, not in scope here.

If a feature pulls us toward agent / graph / planner territory, it
belongs in another repo that depends on this one.

## Why fault cards (the unit of knowledge)

A "fault card" captures one dormant defect or runtime fault pattern:
its mechanism, what activates it, what symptoms it produces, what it
emits downstream, and where the evidence came from. Cards link by
matching `downstream_effects` against another card's observable
signals (or activation conditions) — the predicate vocabulary is the
shared interface that lets independent cards compose.

## Quality over quantity (load-bearing axiom)

This is the rule that overrides everything else, including roadmap
ambition:

- **Cards**: a single well-sourced, reviewed, reproducible card is more
  valuable than ten LLM-extracted half-cards. Don't batch-import. Don't
  treat card count as progress. Each card must justify its existence.
- **Tests**: every test verifies a distinct requirement. Don't add a
  test "to be safe." If a test would silently pass under the bug it's
  meant to catch, delete it.
- **Code**: lines of code are cost. Reach for the smallest module that
  satisfies the contract. Don't generalize until a second use case
  forces it.
- **Schema fields**: every field must serve either (a) human review or
  (b) automatic chain assembly. Fields that do neither get cut.

When in doubt: **think three times before adding, once before removing**.

## Connectivity > coverage

A library of 500 disconnected cards is less useful than 50 cards that
form chains. Health is measured by the **bridgeable predicate ratio**
(`stats` command), not card count. If the ratio drops while card count
rises, schema or vocabulary needs work — not more cards.

## Predicate vocabulary is the ISA

The controlled `<resource_class>.<object>.<operation>` vocabulary is
the contract between cards. If two cards use different phrasings for
the same condition, they will never link. Every PR that touches
`predicates.py` is a vocabulary change and must be reviewed with the
same care as a schema change.

## Validation > trust

A card that hasn't been validated by the schema does not exist as far
as the library is concerned. A card that hasn't been confirmed in
chaos experiments is `reproducibility.confirmed_in_chaos: false` and
downstream consumers must treat it as a hypothesis, not a fact.

## Schema evolution discipline

Schema versions are explicit (`schema_version: 1`). Bumping the
version requires:

1. A migration test (old YAML still validates after migration).
2. A reason recorded in this doc or a dedicated migration note.
3. A pass over existing cards to either upgrade or quarantine them.

Never silently change field semantics; that breaks every consumer.

## What to defer

Deliberately not in v0.1:

- Probabilistic edge weights (sample size too small for stats).
- Embedding-based search (start with exact predicate match; upgrade
  only when retrieval quality demonstrably blocks an agent).
- Graph storage (cards-on-disk + on-the-fly chain assembly is enough
  until proven slow).
- Mitigation / fix recommendations (different knowledge product).
- Strict ontology (vocabulary grows from real cards, not theory).
