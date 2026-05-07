# chaoschain

Heterogeneous causal knowledge base for cascade fault chain mining.

`chaoschain` is a **library + CLI** that defines the schema, storage, and
retrieval primitives for a fault-card knowledge base — a structured corpus
of dormant defects, their activation conditions, and their downstream
runtime symptoms. Cards link via a controlled predicate vocabulary, which
makes it possible to assemble candidate cascade chains from previously
independent faults.

The repo is **not an agent**. Agents (Claude Code or otherwise) consume
this library to mine, deduplicate, and maintain the knowledge base.

## Install

```bash
pip install chaoschain
# or, in this repo:
uv sync
```

## CLI

```
chaoschain validate cards/                   # schema-check all cards
chaoschain list                              # list every card id
chaoschain get FC-0001                       # print one card as YAML
chaoschain add path/to/draft.yaml            # validate + write to canonical path
chaoschain rm FC-0001                        # delete a card
chaoschain search --emits app_resource.connection_pool.exhausted
chaoschain search --text "retry storm"
chaoschain chains --max-hops 3               # candidate cascade chains
chaoschain stats                             # connectivity / coverage health
chaoschain predicates                        # controlled vocabulary
```

All commands accept `--cards-root <path>` (default `./cards`).

## Library

```python
from chaoschain.store import CardRepository
from chaoschain.schemas import FaultCard

repo = CardRepository("cards/")
card = repo.get("FC-0001").card
hits = repo.search(emits_predicate="app_resource.connection_pool.exhausted")
chains = repo.find_chains(max_hops=3)
stats = repo.coverage_stats()
```

## Layout

```
cards/<defect_class>/*.yaml       # card storage (top folder = schema dispatch key)
src/chaoschain/
  schemas/                        # Pydantic models + predicate ISA
  store/                          # CardRepository: load, search, write
  validators/                     # folder-to-schema registry
  cli.py                          # `chaoschain` entry point
docs/
  first-principles.md             # design axioms (read first)
  schema-v0.1.md                  # FaultCard field reference
  predicate-vocabulary.md         # the StatePredicate ISA
.claude/skills/card-curator/      # Claude Code skill for adding/maintaining cards
```

## Design principle (load-bearing)

**Quality over quantity.** A library of 50 well-sourced, validated,
reproducible cards that link into chains is worth more than 500
disconnected ones. Library health is `bridgeable_predicates /
predicates_emitted` from `chaoschain stats`, not card count.

Full reasoning: `docs/first-principles.md`.
