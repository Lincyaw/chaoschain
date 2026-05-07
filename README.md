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

The CLI is organized as `chaoschain <noun> <verb>`:

```
chaoschain card validate cards/              # schema-check all cards
chaoschain card list                         # list every card
chaoschain card get FC-0001                  # print one card as YAML
chaoschain card add path/to/draft.yaml       # validate + write + commit
chaoschain --yes card rm FC-0001             # destructive: requires --yes
chaoschain card history FC-0001              # git revisions for one card
chaoschain card show-at FC-0001 <commit>     # card content at a commit
chaoschain --yes card rollback FC-0001 <commit>

chaoschain library stats                     # connectivity / coverage
chaoschain library chains --max-hops 3       # candidate cascade chains
chaoschain library search --emits app_resource.connection_pool.exhausted
chaoschain library search --text "retry storm"

chaoschain vocab list                        # controlled vocabulary
chaoschain vocab show app_resource.connection_pool.exhausted

chaoschain version
chaoschain dump-schema                       # full command tree as JSON
```

Global flags: `--cards-root` (also reads `$CHAOSCHAIN_CARDS_ROOT`),
`--format {text,json}`, `--quiet`, `--yes`, `--dry-run`, `--read-only`.
Full contract — exit codes, JSON shapes, env vars — is in
[`docs/cli-contract.md`](docs/cli-contract.md).

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
  cli/                            # `chaoschain` entry point (noun-verb tree)
  exit_codes.py                   # canonical exit code table
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
predicates_emitted` from `chaoschain library stats`, not card count.

Full reasoning: `docs/first-principles.md`.
