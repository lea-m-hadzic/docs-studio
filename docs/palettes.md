# Palettes

A palette is a set of semantic colour tokens, declared once per scheme and then mapped
onto the theme's own `--md-*` variables. That mapping is why one palette change
restyles the whole site rather than a handful of rules.

```bash
docs-studio presets
```

See [`presets`](presets.md) for the three bundled ones.

## The tokens

Twelve per scheme are required. Six more are derived if you leave them out.

### Required

| Token | Carries |
| --- | --- |
| `primary` | links, active navigation, filled buttons |
| `primary_hover` | the hover and focus state of all of those |
| `on_primary` | text on a filled primary surface |
| `secondary` | the deep brand tone: the display-equation rule, the generated monogram |
| `accent` | decorative only — a tint behind a warning, a highlight in a mark |
| `fg` | headings and strong text |
| `fg_body` | body text |
| `muted` | secondary text, "On this page", the note callout's bar |
| `border` | hairlines on cards, tables and secondary buttons |
| `bg` | the page |
| `surface` | cards and tables |
| `surface_alt` | code blocks and the note callout |

### Derived

| Token | Default |
| --- | --- |
| `primary_tint` | `primary` at 8% (light) or 14% (dark) |
| `accent_text` | `accent`, corrected until it clears 4.5:1 on `bg` |
| `accent_tint` | `accent` at 10% (light) or 12% (dark) |
| `bg_translucent` | `bg` at 70% |
| `link` | `primary` |
| `link_hover` | `primary_hover` |

Each is a `--ds-*` custom property in the generated stylesheet, available to your own
CSS — see [Logo and favicon](branding.md) and the comments in
`docs/stylesheets/custom.css`.

## `accent` and `accent_text`

Worth understanding, because it is the one place the toolkit changes a colour you gave
it.

A brand accent is often too light to read as text. ARIS.jl's coral `#F0787F` is 2.7:1
on white — fine as a tint behind a callout, unreadable as a word. That site solved it
by hand, picking a darkened `#C73C44` wherever coral text was unavoidable.

`docs-studio` does it mechanically. `accent` stays decorative and is never used for
text. `accent_text` is mixed toward black or white until it clears 4.5:1 against that
scheme's background:

```text
light: accent_text on bg is 4.86:1, needs 4.5:1 (text)
```

Set `accent_text` yourself to override the correction. Nothing checks `accent` itself
for contrast, deliberately — that is what makes it free to be a brand colour.

## Overriding tokens

Layer changes on top of a preset:

```toml
[theme]
preset = "ocean-violet"

[theme.light]
primary = "#0F6E6B"
primary_hover = "#0A5350"

[theme.dark]
primary = "#5FC9C0"
primary_hover = "#8ADBD4"
```

Untouched tokens keep the preset's values. An unknown token name is an error, not a
typo that silently does nothing.

Colours may be written as `#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb(…)` or `rgba(…)`.
Translucent values are composited over the page background before contrast is measured,
so a 10% border is not mistaken for failing text.

## A palette of your own

For a full identity, a file is cleaner than a pile of overrides. This site uses one:

```toml
[theme]
preset = "neutral"
palette_file = "docs-studio-palette.toml"
```

The file is the same shape as a bundled preset:

```toml
name = "studio-teal"
title = "Studio Teal"
description = "Deep teal on warm neutrals, with amber as a restrained accent."
md_primary = "white"
md_primary_dark = "black"
md_accent = "teal"

[light]
primary = "#0F6E6B"
primary_hover = "#0A5350"
primary_tint = "#EAF4F3"
on_primary = "#FFFFFF"
secondary = "#123B3A"
accent = "#D97A2B"
fg = "#16211F"
fg_body = "#2A3634"
muted = "#596765"
border = "#E0E6E4"
bg = "#FBFBFA"
surface = "#FFFFFF"
surface_alt = "#F2F5F4"

[dark]
primary = "#5FC9C0"
primary_hover = "#8ADBD4"
primary_tint = "rgba(95, 201, 192, 0.14)"
on_primary = "#0E1716"
secondary = "#3E8F89"
accent = "#E8A75C"
fg = "#F1F6F5"
fg_body = "#DDE7E5"
muted = "#9BABA8"
border = "rgba(255, 255, 255, 0.1)"
bg = "#0E1716"
surface = "#15201F"
surface_alt = "#1C2827"
```

`md_primary`, `md_primary_dark` and `md_accent` are the Material colour names Zensical
puts in its own palette entries. They matter less than the tokens — the tokens win, by
the mapping — but the accent name sets the colour of a few pieces of theme chrome.

## Contrast is checked, not assumed

Thirteen foreground-on-background pairs, in both schemes, every time anything is
generated or checked:

```text
  ok   palette 'studio-teal': 26 contrast pairs checked in both schemes, tightest accent_text/bg (4.58:1 of 4.5)
```

Text pairs must clear 4.5:1 and are errors below it. Non-text pairs — the primary
against a code background, for instance — must clear 3:1 and are warnings.

`init` reports a failing palette and still writes the site, so you can look at it.
[`check`](check.md) reports it as an error, so it cannot be published.

!!! note "WCAG 2.1, and only that"
    The model is relative luminance. It does not account for font weight or size, so a
    pair that passes at 4.5:1 can still read poorly at a small weight. It is a floor,
    not a judgement.
