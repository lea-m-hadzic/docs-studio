# Quickstart

Install it, plan one route, and see what it says about the gaps.

## Install

[Installation](install.md) has the full set of requirements. The short version:

```bash
pipx install greenline
greenline data refresh
```

The second command downloads the current lane map. Without it, every route fails with
`no lane data`.

## Plan a route

```bash
greenline route "Harbour Market" "Western Library"
```

Place names are matched against the lane map's own landmarks. If a name is ambiguous
you get the candidates rather than a guess:

```text
"library" matches 3 landmarks:
  Western Library
  Harbour Branch Library
  Old Library (closed)
```

## Ask for protected lanes only

```bash
greenline route "Harbour Market" "Western Library" --avoid-unprotected
```

```text
Harbour Market → Western Library
  5.3 km, 22 min, 5.3 km protected (100%)

  1.2 km longer than the default route, and 5 minutes slower.
```

When no protected route exists, it says so and shows the best route it found anyway,
with the gaps marked. It does not invent a path.

## Use coordinates instead

```bash
greenline route 51.5072,-0.1276 51.5194,-0.1270
```

Coordinates are latitude and longitude in that order, which is the opposite of what
some mapping tools use. A pair that lands outside the city's bounding box is rejected
rather than routed to the nearest edge.

## What to read next

- [Planning a route](usage.md): every option, and what it trades.
- [Reporting a blockage](blockages.md): when the map is wrong.
