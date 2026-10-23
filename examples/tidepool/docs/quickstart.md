# Quickstart

One run, from an empty directory to a number, in about a minute.

## Install

[Installation](install.md) has the full set of requirements. For this page:

```bash
pip install tidepool
```

## Record a run

```python
from tidepool import Run

with Run.open("harbour-2026.log", schedule="every(30, unit='s')") as run:
    for depth, salinity in [(4.2, 31.1), (4.3, 31.0), (4.1, 31.2)]:
        run.record(depth=depth, salinity=salinity)
```

`Run.open` creates the log if it is not there and appends to it if it is. The schedule
is recorded in the log's header, so a replay does not need to be told what it was.

## Replay it

```python
from tidepool import Run, mean, spread

samples = list(Run.replay("harbour-2026.log"))
print(len(samples))

print(mean(samples, field="salinity").value)
print(spread(samples, field="salinity").interval)
```

The first line prints the number of samples the schedule admitted, which is not
necessarily the number of calls to `record` — see
[Sampling and aggregation](aggregation.md).

## Check the log

```bash
tidepool verify harbour-2026.log
```

A healthy log prints its entry count and `checksum ok`. Any other output means the log
was truncated or edited, and replay will refuse it.

## What to read next

- [Running a measurement](usage.md): the same ground in more detail.
- [Sampling and aggregation](aggregation.md): the replay rule.
- [Python API](api.md): the full surface, by signature.
