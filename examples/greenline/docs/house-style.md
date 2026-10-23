# House style

Conventions for the map data and for these pages. They exist so that a map edited by
forty people reads as though one person did it.

## Lane names

- Use the name on the street sign, not the name on a planning document.
- Keep the street type: `Mill Street bike lane`, not `Mill bike lane`.
- Put a qualifier in brackets when one segment of a lane needs distinguishing:
  `Quay Path (east end)`.
- No abbreviations. `Avenue`, not `Ave`.

## Notes

The `notes` field is for what a rider needs to know before they get there. One or two
sentences, specific:

- Good: "Narrows to 180 cm at the Mill Street junction."
- Good: "Gives way to pedestrians across the whole plaza."
- Bad: "Can be busy."
- Bad: "Nice route!"

Nothing about enforcement, nothing about other road users' behaviour, and no opinions
about the council.

## Attribution

Data from another source needs its source recorded and its licence checked before it
goes in:

```json
{
  "source": "City open data portal, cycle infrastructure layer, 2026-09",
  "source_licence": "CC BY 4.0"
}
```

!!! warning "Unlicensed data stays out"
    If you cannot establish that a source permits reuse, it does not go in the map,
    however obviously correct it is. One contaminated layer would make the whole map
    unredistributable, and nobody wants to be the person who audits 1,284 segments.

## These pages

- Second person, present tense. "Report one", not "a blockage may be reported".
- Say what something costs, not only what it does. Every option on
  [Planning a route](usage.md) has a trade-off column for that reason.
- A limitation goes at the end of its own page, in its own section, not in a footnote.
- No screenshots of the terminal. Paste the text in a `text` block, so it can be
  searched and copied.
