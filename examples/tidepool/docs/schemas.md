# Result schemas

Each aggregate returns a frozen dataclass. The fields below are the whole of each type;
there are no private attributes to discover.

## `Summary`

Returned by [`mean`](api.md#mean).

| Field | Type | Meaning |
| --- | --- | --- |
| `field` | `str` | the field this summarises |
| `value` | `float` | the arithmetic mean, in sequence order |
| `n` | `int` | samples that contributed |
| `skipped` | `int` | samples whose field was `None` |

## `Spread`

Returned by [`spread`](api.md#spread).

| Field | Type | Meaning |
| --- | --- | --- |
| `field` | `str` | the field this describes |
| `minimum` | `float` | smallest value seen |
| `maximum` | `float` | largest value seen |
| `interval` | `tuple[float, float]` | the interquartile interval, inclusive |
| `n` | `int` | samples that contributed |

## `Coverage`

Returned by [`coverage`](api.md#coverage).

| Field | Type | Meaning |
| --- | --- | --- |
| `field` | `str` | the field this counts |
| `present` | `int` | samples with a value |
| `null` | `int` | samples whose value was `None` |
| `absent` | `int` | samples that did not carry the field at all |

!!! note "`absent` is normally zero"
    A log's field set is fixed by its first entry, so `absent` can only be non-zero
    when samples from two different logs are aggregated together.

## `RunStats`

Returned by [`Run.stats`](api.md#run).

| Field | Type | Meaning |
| --- | --- | --- |
| `path` | `str` | the log this describes |
| `schedule` | `str` | the schedule recorded in the header |
| `offered` | `int` | calls to `record` |
| `recorded` | `int` | calls the schedule admitted |
| `closed` | `bool` | whether the log has a closing entry |
