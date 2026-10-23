# Visual validation

Captured from the three example sites, built with `zensical build --clean --strict` and
served locally. Light and dark are the browser's `prefers-color-scheme`, not the
in-page toggle, so these are what a visitor sees before touching anything.

| File | Site | Scheme | Viewport |
| --- | --- | --- | --- |
| `lattice-certificate-light-desktop.jpg` | Lattice.jl | light | 1280×900 |
| `lattice-home-dark-desktop.jpg` | Lattice.jl | dark | 1280×900 |
| `tidepool-home-light-desktop.jpg` | tidepool | light | 1280×900 |
| `tidepool-monogram-header.png` | tidepool | light | header detail, 1:1 |
| `greenline-home-light-desktop.jpg` | Greenline | light | 1280×900 |
| `greenline-usage-light-mobile.jpg` | Greenline | light | 375×812 |
| `greenline-home-dark-mobile.jpg` | Greenline | dark | 375×812 |
| `docs-studio-home-light-desktop.jpg` | docs-studio's own site | light | 1280×900 |
| `docs-studio-palettes-dark-desktop.jpg` | docs-studio's own site | dark | 1280×900 |
| `docs-studio-updating-dark-mobile.jpg` | docs-studio's own site | dark | 375×812 |

The three `docs-studio-*` files are this toolkit's own documentation site, which uses
the Studio Teal palette supplied as a `palette_file` rather than a bundled preset.

`lattice-certificate-light-desktop.jpg` is the page that exercises the `.ds-math`
display-equation block; `tidepool-monogram-header.png` is the generated placeholder
mark at the size the header actually renders it.
