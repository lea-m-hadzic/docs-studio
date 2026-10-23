# Logo and favicon

Two rules hold everywhere here:

1. **A file you supply is copied byte for byte.** Nothing is resized, re-encoded,
   cropped or recoloured, so transparency and colour profiles survive and a wide logo
   stays wide.
2. **Nothing in `docs/assets/` is ever overwritten by [`update`](update.md).** Artwork
   is recorded as yours. Not even `--force` reaches it.

No image is generated from a model.

## Supplying a logo

```toml
[branding]
logo = "brand/my-logo.svg"
logo_dark = "brand/my-logo-dark.svg"
favicon = "brand/favicon.ico"
```

Or at generation time:

```bash
docs-studio init my-docs --logo brand/my-logo.svg --favicon brand/favicon.ico --yes
```

Each file is copied to `docs/assets/` under its own basename, and `zensical.toml` is
pointed at it. A path outside the target directory is copied in first, so the site
stays self-contained.

Accepted: `.svg`, `.png`, `.ico`, `.webp`, `.jpg`, `.jpeg`.

### Aspect ratio

The theme renders the header logo as an image sized by height, with width left to the
browser. An SVG should carry a `viewBox` and **no** `width` or `height` attributes, and
no `preserveAspectRatio` override; the default keeps it whole. A raster logo should be
trimmed to its own bounding box with transparent padding, not centred on a canvas —
the theme cannot know which part of a tall PNG is the mark.

## The dark variant

A mark with a deep brand tone goes murky on a dark header. `logo_dark` is swapped in by
the stylesheet under the slate scheme:

```css
[data-md-color-scheme="slate"] .md-header__button.md-logo :is(img, svg) {
  content: url("../assets/my-logo-dark.svg");
}
```

That rule is generated only when `logo_dark` is set. Because it lives in CSS rather
than in the config, nothing else would notice it was broken — so `check` reads the
stylesheet and verifies the file it points at exists (`css-asset-missing`).

With a logo and no dark variant, `check` leaves a note rather than a warning: a mark
that reads on both backgrounds genuinely does not need one.

## The generated monogram

With no `logo`, a mark is drawn from the project's initials and the palette, in both
schemes, and the dark swap is wired up:

```text
  no logo was supplied, so a monogram was generated from the project's initials (MP).
  Set branding.logo in docs-studio.toml to replace it.
```

Initials come from the name: `wm-physics-eval` gives `WP`, `ARIS.jl` gives `AJ`,
`CamelCase` gives `CC`, a single lowercase word gives its first two letters. Override
them:

```toml
[branding]
monogram_text = "GL"
```

The mark is a square `viewBox` with a rounded tile in `primary`, a wedge in
`secondary`, the initials in `on_primary`, and a small dot in `accent`. It is
deterministic — the same inputs always give the same file.

!!! warning "It is a placeholder, and it uses a system font"
    The initials are an SVG `<text>` element, so they render in whatever sans-serif the
    viewer has. That is deliberate: a web font would mean a third-party request, which
    a generated site does not make. It is good enough to launch with and should be
    replaced before it matters.

To regenerate it after changing the palette or the initials, delete it and update —
`update` creates a seeded file that is absent:

```bash
rm docs/assets/logo.svg docs/assets/logo-dark.svg docs/assets/favicon.svg
docs-studio update
```

## The favicon

A supplied favicon is copied through, whatever the format. With none, an SVG favicon is
generated: the same tile and initials, with the wedge and the dot dropped, because
neither survives at 16 px.

!!! note "No `.ico` is generated"
    Generating one would need an imaging library, which is a heavy dependency for a
    single file. Modern browsers accept an SVG favicon. If you want `.ico` — for older
    browsers, or because a tool expects it — make one and point `branding.favicon` at
    it.

## The wordmark

```toml
[branding]
wordmark = "brand/my-wordmark.svg"
```

A wordmark is shown above the home-page headline, not in the header. Replacing the
header's text site name would need a theme template override, and the toolkit prefers
supported customization to a fragile internal one — the header keeps the site name in
regular weight instead.

## Your own CSS

`docs/stylesheets/custom.css` is generated once, listed in `extra_css` **after** the
design system, and never touched again. Put logo-adjacent tweaks there:

```css
.md-header__button.md-logo :is(img, svg) {
  height: 1.4rem;
}
```

The `--ds-*` tokens are available, so rules written with them follow both schemes on
their own. See [File ownership](ownership.md).
