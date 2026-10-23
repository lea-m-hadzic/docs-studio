# Python API

One entry per public name. Everything not listed here is private and may change in any
release.

## `Run`

```text
Run.open(path, *, schedule="all()", mode="append") -> Run
Run.replay(path, *, strict=True) -> Iterator[dict]
Run.stats(path) -> RunStats
```

A writer bound to one log file, plus the two class methods that read one back.

`Run.open` creates the log when it does not exist. `mode="append"` continues an
existing log; `mode="new"` refuses to open one that already exists. The returned object
is a context manager; leaving the block writes the closing entry.

`Run.replay` yields one dictionary per admitted sample, in log order. With
`strict=True` a checksum mismatch raises `LogDamaged`; with `strict=False` replay stops
at the last intact entry and yields what came before it.

`Run.stats` reads only the header and the closing entry, so it is cheap on a long log.

### `Run.record`

```text
record(**fields) -> bool
```

Offers one observation to the schedule. Returns `True` when it was recorded and `False`
when the schedule declined it. Raises `FieldMismatch` if the field set differs from the
first entry's, and `UnsupportedValue` for a value that is not `int`, `float`, `str`,
`bool` or `None`.

### `Run.close`

```text
close() -> None
```

Writes the closing entry and releases the file. Idempotent; calling it twice is not an
error.

## `mean`

```text
mean(samples, *, field) -> Summary
```

The arithmetic mean of `field` over the samples where it is not `None`, summed in
sequence order. Raises `NoSamples` when no sample has the field.

## `spread`

```text
spread(samples, *, field) -> Spread
```

The minimum, maximum and interquartile interval of `field`. Raises `NoSamples` with
fewer than two usable samples.

## `coverage`

```text
coverage(samples, *, field) -> Coverage
```

How much of the field is actually there: the counts of present, `None` and absent.
Never raises.

## Exceptions

| Exception | Raised when |
| --- | --- |
| `FieldMismatch` | an entry's field set differs from the first entry's |
| `UnsupportedValue` | a value is not one of the four supported types |
| `LogDamaged` | a checksum does not match during a strict replay |
| `NoSamples` | an aggregate has too few usable samples |

!!! info "Keep this page in step with the code"
    A test can compare this page against `inspect.signature` and
    `dataclasses.fields`, so a renamed parameter fails CI instead of going stale here.
    That check belongs in the project's own suite, not in `docs-studio check` — it has
    to import the package.
