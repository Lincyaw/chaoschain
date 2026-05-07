# chaoschain CLI contract

This document is the canonical contract for the `chaoschain` CLI. The
implementation in `src/chaoschain/cli/` MUST match this document; the
test suite asserts the most load-bearing pieces.

## Command tree

```
chaoschain
├── card list
├── card get <id>            (--at <commit>)
├── card add <file|dir>      (--force, --no-commit, --strict)
├── card rm <id>             (--no-commit; needs --yes)
├── card validate <path>
├── card history <id>        (--limit)
├── card show-at <id> <commit>
├── card rollback <id> <commit>   (--no-commit; needs --yes)
├── library stats
├── library chains           (--max-hops)
├── library search           (--emits, --observes, --text)
├── vocab list
├── vocab show <predicate>
├── version
└── dump-schema
```

Depth is capped at three levels (binary + group + verb).

## Global flags

These attach to the root command and apply to every subcommand:

| Flag             | Meaning                                                              |
|------------------|----------------------------------------------------------------------|
| `--cards-root P` | Card tree root. CLI > env `CHAOSCHAIN_CARDS_ROOT` > `./cards`.       |
| `--format X`     | `text` (default) or `json`. Stable JSON shapes documented below.     |
| `--quiet`        | Suppress informational stderr. Errors still print.                   |
| `--yes`          | Confirm destructive ops (`card rm`, `card rollback`).                |
| `--dry-run`      | Predict the action, perform no writes, exit 0.                       |
| `--read-only`    | Hard-disable write paths; any write attempt exits 4.                 |

Place them before the subcommand, e.g. `chaoschain --format json card list`.

## Output channels

* **stdout** — data only. In JSON mode, exactly one JSON value with one
  trailing newline.
* **stderr** — informational and error messages. Suppressed by `--quiet`
  in text mode (errors always print). In JSON mode, structured errors
  go to stderr as `{"error": {...}}`.
* **exit code** — see table below.

`<cmd> 2>/dev/null` should give clean data; `<cmd> >/dev/null` should
give clean info/errors.

## Exit codes

| Code | When                                                                |
|------|---------------------------------------------------------------------|
| 0    | Success.                                                            |
| 2    | Argument / syntax error (Typer's default).                          |
| 3    | Not found (unknown card id, missing file path).                     |
| 4    | Permission / `--read-only` violation.                               |
| 5    | Conflict (`card add` to existing id without `--force`).             |
| 6    | Refused for safety (destructive op without `--yes`).                |
| 7    | Environment error (cards root missing, git unavailable).            |
| 10   | Validation error (schema rejection).                                |
| 11   | Git operation failed (other than unavailable).                      |

In a batch (`card add <dir>`) the worst exit code wins, with priority
`10 > 5 > 11`.

Defined as named constants in `chaoschain.exit_codes`.

## JSON output schemas

```jsonc
// card list
{"cards": [{"id":"FC-0001","name":"...","class":"resource_leak","path":"cards/..."}]}

// card get <id>          (and card show-at when --format json)
{"id":"FC-0001","card":{...},"path":"..."}              // card get / get --at
{"id":"FC-0001","card":{...},"path":"...","at":"abc"}   // card get --at <commit>

// card history <id>
{"id":"FC-0001","revisions":[{"commit":"...","short":"abcdef0123","author":"...","date":"ISO8601","subject":"..."}]}

// card add (single-file success)
{"action":"add"|"update","id":"FC-0001","path":"cards/...","committed":true|false,"commit":null}

// card add --dry-run (single-file)
{"action":"add"|"update","id":"FC-0001","would_write":"cards/...","conflicts":[]|["FC-0001"]}

// card add (directory / batch)
{"results":[{"path":"...","ok":true,...},{...}]}

// card rm
{"action":"remove","id":"FC-0001","committed":true|false}

// card rm --dry-run
{"action":"remove","id":"FC-0001","would_delete":"cards/..."}

// card rollback
{"action":"rollback","id":"FC-0001","to":"<sha>","committed":true|false}

// card validate
{"files":[{"path":"...","ok":true,"errors":[]}],"total":N,"errors":N}

// library stats
{"cards":N,"predicates_emitted":N,"predicates_observed":N,"bridgeable_predicates":N,"connectivity_ratio":F}

// library chains
{"chains":[["FC-0001","FC-0002"]]}

// library search
{"matches":[{"id":"...","class":"...","name":"..."}]}

// vocab list
{"resource_classes":["compute",...],"operations":["exhausted",...]}

// vocab show <predicate>
{"predicate":"app_resource.connection_pool.exhausted","valid":true,"resource_class":"app_resource","object":"connection_pool","operation":"exhausted","modifier":null}
{"predicate":"foo.bar.baz","valid":false,"error":"..."}

// version
{"name":"chaoschain","version":"0.1.0","schema_versions":{"fault_card":1}}

// dump-schema
{"commands":[{"name":"card add","help":"...","args":[...],"options":[...]}, ...]}
// each option: {"name":"--format","type":"enum","choices":["text","json"],"default":"text","required":false,"help":"..."}

// errors (stderr, in --format json mode)
{"error":{"type":"...","message":"...","exit_code":N}}
```

## Environment variables

* `CHAOSCHAIN_CARDS_ROOT` — fallback for `--cards-root` (CLI flag wins).

## Stability

Breaking changes to this contract bump the package version's minor
component (pre-1.0) and are called out in the changelog.
