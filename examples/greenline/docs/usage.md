# Planning a route

Where [Quickstart](quickstart.md) plans one route, this page covers the options and
what each one gives up.

## The default route

```bash
greenline route "Harbour Market" "Western Library"
```

The default balances distance against protection: it will take a short unprotected
stretch rather than a long detour, and it always names the stretch it took.

## The options

| Option | What it does | What it costs |
| --- | --- | --- |
| `--avoid-unprotected` | protected lanes only | usually longer; sometimes impossible |
| `--shortest` | shortest path, protection ignored | routes you down arterials |
| `--max-gap <metres>` | allow unprotected stretches up to this length | nothing, if the number is honest |
| `--no-hills` | avoid segments steeper than 6% | longer, and not always possible |
| `--depart <time>` | plan for a time of day | nothing; affects lane closures only |

```bash
greenline route "Harbour Market" "Western Library" --max-gap 200
```

`--max-gap` is the one most people end up using. A 200-metre unprotected stretch to
cross a junction is a different thing from two kilometres on a main road, and the
default cannot tell which you mean.

## Reading the output

```text
Harbour Market → Western Library
  4.1 km, 17 min, 3.4 km protected (83%)

  1. Quay Path, 1.2 km                       protected
  3. Fifth Avenue, 0.7 km                    UNPROTECTED — painted lane only
```

- The time estimate assumes 15 km/h on the flat and does not account for traffic
  lights. It is a lower bound in practice.
- The percentage is of distance, not of time.
- `UNPROTECTED` is always upper case, so it cannot be missed in a long route.

!!! info "Times are deliberately crude"
    A more precise estimate would need traffic-light timings and live traffic, neither
    of which the volunteers have. A crude estimate that is obviously crude is better
    than a precise-looking one that is wrong.

## When there is no route

```bash
greenline route "Harbour Market" "Eastbank Depot" --avoid-unprotected
```

```text
No protected route exists between these points.

The nearest thing is 6.8 km with one gap:
  Eastbank Bridge, 900 m                     UNPROTECTED — no separation
```

It reports the failure first and the fallback second, in that order, so that skimming
the output cannot produce the wrong impression.

## Limitations

- No live traffic, weather, or roadworks beyond reported blockages.
- One-way restrictions are included for lanes but not for the ordinary roads a route
  may briefly use.
- Nothing is personalised. Two people asking the same question get the same answer.
