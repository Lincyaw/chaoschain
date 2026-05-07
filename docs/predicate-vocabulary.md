# Predicate vocabulary (StatePredicate ISA)

Predicates are the shared interface between cards. Get this wrong and
cards stop linking; therefore the vocabulary changes carefully.

## Shape

```
<resource_class>.<object>.<operation>[.<modifier>]
```

- `resource_class` — controlled enum (see below). Adding a new class
  is a vocabulary bump.
- `object` — free text naming the concrete resource instance
  (`connection_pool`, `memory`, `db_client`, ...). Reuse existing
  object names when possible.
- `operation` — controlled enum (see below).
- `modifier` — free text qualifier, optional. Use it for shape /
  intensity / time scale (`slow`, `bursty`, `right_skewed`).

## Controlled `resource_class`

| Class | Examples (object) |
|---|---|
| `compute` | cpu, memory, gc, thread_pool |
| `storage` | disk_space, file_handle, iops |
| `network` | bandwidth, socket, connection |
| `concurrency` | lock, semaphore, queue |
| `app_resource` | connection_pool, cache, buffer |
| `time` | timeout, deadline, clock |
| `config` | flag, limit, threshold |
| `latency` | p50, p99, tail |
| `error_rate` | 5xx, timeout, exception |
| `topology` | replica, shard, leader |

## Controlled `operation`

| Op | Meaning |
|---|---|
| `exhausted` / `saturated` | resource hit its hard cap (instantaneous) |
| `leaked` / `accumulated` | resource creeps over time |
| `contended` / `blocked` | concurrency wait |
| `delayed` / `stalled` | timing degradation |
| `degraded` | metric got worse without specific shape |
| `corrupted` / `inconsistent` | state went bad |
| `amplified` | non-linear blow-up (retry storm, fan-out) |
| `silenced` / `masked` | symptom suppressed (often by another defect) |

## Adding to the vocabulary

1. Try first to express the new condition with existing terms — most
   "new" conditions are old conditions with a different modifier.
2. If a real card cannot be expressed, propose the addition with:
   - the card that motivated it
   - the predicate string you want to add
   - which existing predicate it would *not* be the same as
3. Update `predicates.py` and this doc in the same change.

## Anti-patterns

- ❌ Free text in `resource_class` or `operation` — they are enums.
- ❌ Synonyms (`drained` vs `exhausted`) — pick one and stick with it.
- ❌ Mechanism-flavored predicates (`memory.leaked.because_finalizer`).
  The mechanism belongs in `defect.mechanism`, not the predicate.
