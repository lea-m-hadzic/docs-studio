# Running a measurement

Where [Quickstart](quickstart.md) shows one path through, this page explains the
pieces: what a run is, what a schedule decides, and what happens when something stops
halfway.

## A run is a file

`Run.open` returns a writer bound to one log file. It is a context manager, and the
closing entry it writes is what marks the log complete:

```python
from tidepool import Run

with Run.open("harbour-2026.log", schedule="every(30, unit='s')") as run:
    run.record(depth=4.2, salinity=31.1)
```

Outside a `with` block, call `run.close()` yourself. A log with no closing entry is not
corrupt — it is *open*, and replay yields everything up to the last complete entry.

## Fields

Every keyword passed to `record` is a field. Fields are not declared in advance, but
they must be consistent: the first entry fixes the set, and a later entry with a
different set raises `FieldMismatch`.

```python
run.record(depth=4.2, salinity=31.1)
run.record(depth=4.3)                  # FieldMismatch: missing 'salinity'
```

Values may be `int`, `float`, `str`, `bool` or `None`. Anything else raises
`UnsupportedValue` at the call site rather than at replay, so a bad value is caught
where it was written.

## Schedules

A schedule decides which calls to `record` become samples. It is evaluated at write
time, recorded in the log, and replayed verbatim.

| Schedule | What it admits |
| --- | --- |
| `every(n, unit='s')` | the first call in each `n`-second window |
| `every(n)` | every `n`th call, counting from the first |
| `all()` | every call |
| `first(n)` | the first `n` calls, then nothing |

```python
with Run.open("coarse.log", schedule="every(10)") as run:
    for value in range(100):
        run.record(value=value)        # 10 samples recorded, 100 calls made
```

!!! info "The call count is kept even when the sample is not"
    A rejected call still advances the counters, and the totals are written into the
    closing entry. `Run.stats` reports both, so a run can say how much it discarded.

## Interruptions

If the process stops without closing the log, the log stays valid up to its last
complete entry. Reopening it appends; replay from either state works.

```bash
tidepool verify harbour-2026.log
```

!!! warning "An edited log is refused, not repaired"
    Each entry carries a checksum over itself and the one before it. If `verify`
    reports a mismatch, `Run.replay` raises `LogDamaged` at that entry. There is no
    repair mode: the design assumes a damaged log is a problem to investigate, not to
    paper over.

## Limitations

- One writer per log. Concurrent writers are not detected.
- Timestamps come from the system clock. A clock that steps backwards during a run will
  make a time-based schedule admit more samples than expected; `verify` reports the
  step but does not correct it.
- Logs are not compressed. A long run with many fields is large.
