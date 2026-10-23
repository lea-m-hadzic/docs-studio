# `presets`

Lists the bundled palettes and how much contrast headroom each has.

```bash
docs-studio presets
```

```text
indigo-lavender
  Indigo / Lavender / Coral — Violet links on a near-white page, lavender in dark mode, coral as a restrained accent.
  light primary #6254b8, dark primary #a79ae4, accent #f0787f
  WCAG: all 26 pairs pass; tightest is light accent_text/bg at 4.86:1

neutral
  Neutral — Desaturated slate links on warm-grey neutrals, with a quiet sage accent.
  light primary #3d4f66, dark primary #9fb4cc, accent #4f7d6e
  WCAG: all 26 pairs pass; tightest is light accent_text/bg at 4.52:1

ocean-violet
  Ocean / Violet — One blue-violet accent on cool neutrals, with a muted amber for warnings.
  light primary #4b5fd7, dark primary #7e8fff, accent #d98a32
  WCAG: all 26 pairs pass; tightest is light accent_text/bg at 4.53:1
```

The command takes no options. It reads the palettes the way the generator does, so if
a bundled palette is missing from your install this is where you find out.

## Reading the output

- **light primary / dark primary** are the colours that carry links and interactive
  state in each scheme. They are the two that most decide how a site feels.
- **accent** is decorative — a tint behind a warning, a highlight in a mark. It is
  never used for text; `accent_text`, derived from it, is.
- **WCAG** is 26 pairs: thirteen foreground-on-background combinations, in both
  schemes. The tightest is quoted so you can see how much margin there is, not merely
  that it passed.

## Choosing one

| Preset | Character | Suits |
| --- | --- | --- |
| `indigo-lavender` | violet links, lavender in dark mode, coral accent | a project that wants a distinct identity |
| `ocean-violet` | one blue-violet accent on cool neutrals | a project that wants to look sober |
| `neutral` | desaturated slate, quiet sage accent | a project with no palette yet, or one that wants the layout without the colour |

None of the three is a default in any meaningful sense; `neutral` is simply what `init`
falls back to when you do not choose.

[Palettes](palettes.md) covers overriding individual tokens and supplying a palette of
your own, which is how this site's own colours are defined.
