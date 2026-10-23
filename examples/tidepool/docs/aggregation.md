# Sampling and aggregation

## Why replay

An aggregate is defined over the sequence `Run.replay` yields, not over the file's
bytes and not over the calls that produced it. That indirection is the whole point:
the sequence is a function of the log alone, so it is the same on every machine, under
every Python version, and at every point in the future.

```python
from tidepool import Run

first = list(Run.replay("harbour-2026.log"))
second = list(Run.replay("harbour-2026.log"))
assert first == second
```

## The three aggregates

Each takes the replayed sequence and a field name, and returns a result type described
on [Result schemas](schemas.md).

| Aggregate | Returns | Defined when |
| --- | --- | --- |
| `mean(samples, field=...)` | `Summary` | at least one sample has the field |
| `spread(samples, field=...)` | `Spread` | at least two samples have the field |
| `coverage(samples, field=...)` | `Coverage` | always |

```python
from tidepool import Run, coverage, mean, spread

samples = list(Run.replay("harbour-2026.log"))
mean(samples, field="salinity").value
spread(samples, field="salinity").interval
coverage(samples, field="salinity").missing
```

A sample whose field is `None` counts toward `coverage` and is excluded from `mean` and
`spread`. That split is deliberate: a missing reading is information about the run, not
a zero.

## Reduction order

Summation is in replay order, with no pairwise or parallel reduction. This is slower
than it needs to be on a long log and is the reason two runs agree to the last bit:

```python
# What `mean` does, in effect.
total, n = 0.0, 0
for sample in samples:
    if sample.get("salinity") is not None:
        total += sample["salinity"]
        n += 1
value = total / n
```

!!! note "The cost is real"
    On a log of a few million entries this is noticeably slower than a vectorised sum.
    If you need speed more than bit-identical agreement, aggregate outside `tidepool`
    with whatever reduction you like — the replayed sequence is plain dictionaries.

## Combining runs

There is no cross-log aggregate. Two logs are two runs, and the only honest way to
combine them is to say how:

```python
from tidepool import Run, mean

a = list(Run.replay("harbour-morning.log"))
b = list(Run.replay("harbour-evening.log"))
pooled = mean(a + b, field="salinity")
```

That concatenation is yours, not `tidepool`'s. Whether it means anything depends on
whether the two runs measured the same thing, which the logs cannot tell you.
