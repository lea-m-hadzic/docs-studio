# Comparative analysis and extraction strategy

Where the design system came from, and how it was generalized. The two reference sites
were read as source material only; neither repository was modified.

- [wm-physics-eval](https://sisl.github.io/wm-physics-eval/)
- [ARIS.jl](https://sisl.github.io/ARIS.jl/)

## 1. Comparative audit

### zensical.toml — near-identical

Identical in both, modulo project strings: `edit_uri = ""`, `docs_dir`/`site_dir`, `extra_css`,
`theme.language = "en"`, `theme.font = false`, the same 10 `features`, two `palette` entries
(`default`/white + `slate`/black, `lucide/sun` + `lucide/moon` toggles), and the same
`markdown_extensions` block (admonition, attr_list, md_in_html, tables, toc.permalink,
pymdownx.details/emoji/highlight/inlinehilite/snippets/superfences).

Differences: `site_name`/`description`/`author`/`site_url`/`copyright`, the `nav` tree, `logo`
(`assets/aris-mark.svg` vs `assets/wm-physics-eval-mark.png`), and `palette.accent`
("deep purple" vs "indigo").

Neither uses `repo_url`/`repo_name` — repository links live in homepage resource buttons instead.
Both pin `zensical==0.0.67` in CI (verified 2026-10-22: 0.0.67 is still the newest release;
`zensical build` flags `-f/--config-file`, `-c/--clean`, `-s/--strict`; `serve` has
`-a/--dev-addr`, `-o/--open`, and `--strict` is documented as "currently unsupported").

### docs/stylesheets/extra.css — the design system

ARIS 7.7 KB, wm-physics-eval 6.9 KB. Section-for-section the same file with a different token
prefix (`--aris-*` vs `--wm-*`). Shared, in order:

1. Token block under `:root, [data-md-color-scheme="default"]`, then a dark override under
   `[data-md-color-scheme="slate"]` — same token names in both: `primary`, `primary-dark`
   (hover), `primary-light` (tint), `on-primary`, `ink`, `text`, `muted`, `border`, `bg`,
   `bg-translucent`, `surface`, `surface-alt`.
2. The token→theme mapping, selector
   `[data-md-color-scheme="default"][data-md-color-primary], [data-md-color-scheme="slate"][data-md-color-primary]`
   — the doubled attribute is deliberate, to outrank the theme's own palette rules. Maps onto
   `--md-primary-fg-color`, `--md-primary-fg-color--dark`, `--md-primary-bg-color`,
   `--md-accent-fg-color`, `--md-accent-fg-color--transparent`, `--md-typeset-a-color`,
   `--md-default-fg-color`, `--md-default-fg-color--light`, `--md-typeset-color`,
   `--md-default-bg-color`, `--md-default-bg-color--light`, `--md-code-bg-color`,
   `--md-code-fg-color`, `--md-typeset-table-color`.
3. `a:hover/:focus` → primary-dark.
4. `.md-button` secondary = surface + `inset 0 0 0 0.05rem border`; `--primary` = primary bg,
   on-primary text; both hover states.
5. `.grid.cards > ul > li` and `table:not([class])` on `surface` + project border.
6. Admonitions: info/abstract tinted primary-light with primary title bar; note on surface-alt
   with muted bar; warning on an accent tint with a contrast-safe accent title bar.
7. `table td code { white-space: nowrap }`.
8. `h2 { margin-top: 1.8em; padding-top: .45em; border-top: 1px solid var(--md-default-fg-color--lightest) }`.
9. `.md-grid { max-width: 62.5rem }` + narrowed `.md-sidebar--secondary` above 60em
   (10rem ARIS / 8.5rem wm).
10. `.md-header__topic:first-child { font-weight: 400 }`.
11. Homepage `h1.<prefix>-home-title { font-size: 2.125em; font-weight: 400 }`.
12. `.<prefix>-resources` — flex-wrap row of compact outlined `.md-button`s, `font-size: .7rem`,
    transparent background, primary-light hover, `:focus-visible` outline, `.twemoji` sized to
    1.1em.

Project-specific only: ARIS has the coral accent pair (`--aris-accent` #F0787F decorative +
`--aris-accent-text` #C73C44 for text, because coral is 2.7:1 on white), the slate dark-logo swap
via `content: url("../assets/aris-mark-dark.svg")`, and `.aris-math` (Unicode display equations,
no MathJax). wm-physics-eval has `--wm-warning` amber instead of coral, `.wm-flow` (a one-off
diagram row) and `.wm-hf-logo` (sizing for a third-party raster logo).

### Homepages

Same skeleton: `# Welcome to <name>! { .<prefix>-home-title }` → resource button row → bold
one-line summary → 2-3 prose paragraphs → "Developed by ..." → `[Quickstart]{.md-button
.md-button--primary}` + `[Installation]{.md-button}` → a language code block (+ a bash block in
wm) → an `!!! info` convention callout → an h2 with a 2-card `grid cards` → "where to go
next" link list → a scope/limitations section.

### Deployment workflow

`.github/workflows/docs.yml` is byte-identical apart from the install line and checker path:
`on: workflow_dispatch` only, `permissions: contents read / pages write / id-token write`,
`concurrency: group pages, cancel-in-progress false`, `environment: github-pages`, then
configure-pages@v6 → checkout@v7 → setup-python@v6 (3.13) → `pip install "zensical==0.0.67"` →
run the checker → `zensical build --clean --strict` → upload-pages-artifact@v5 (`path: site`) →
deploy-pages@v5.

### Docs checkers — different in kind

ARIS `.github/scripts/check_docs.py` (179 lines, plain stdlib, no Julia): nav↔page bijection,
internal links + anchors, referenced assets, `theme.logo`/`favicon`/`extra_css` targets, assets
referenced from CSS `url("../...")`, documented API names vs statically parsed `export` blocks,
banned placeholder/publication/registry strings, an install-page content assertion, and an
allow-list of external hosts.

wm-physics-eval `tests/test_docs.py` (390 lines) imports the package: it *executes* every Python
snippet against scripted judges and synthetic videos, runs every CLI example, diffs the CLI page
against the real argparse parser, checks documented signatures/defaults against
`inspect.signature`, checks documented dataclass fields against `dataclasses.fields`, plus
markdown-shape lint and regex scans for stale names, private paths, credentials and result claims.

The split that matters: **syntactic/structural checks are universal** (nav, links, anchors,
assets, markdown shape, placeholders), **snippet execution and API-surface agreement are
language- and project-specific**.

## 2. Classification

| Layer | Content | Toolkit treatment |
|---|---|---|
| Reusable design system | the 12 CSS sections above, token names, the doubled-attribute mapping selector, grid/sidebar proportions, button and admonition recipes | generated from a Jinja template, **managed** |
| Theme config | features list, two-entry palette, markdown_extensions, `font = false`, `edit_uri = ""` | generated into `zensical.toml`, **managed** |
| Project metadata | name, description, author, site_url, copyright, logo paths, nav, resource links | `docs-studio.toml`, user-owned |
| Documentation content | every `docs/*.md` body | **seeded once**, never rewritten |
| Infrastructure | `docs.yml`, the docs checker | workflow generated managed; the checker becomes the `docs-studio check` command |

## 3. Extraction strategy

- **Semantic tokens, stable `--ds-*` prefix.** The two prefixes become one. Identity comes from
  `docs-studio.toml`; nobody edits CSS to rebrand. A `secondary` token is added (the deep brand
  tone — ARIS indigo) because the triad exists in the brand but had no CSS role; it is used by the
  generated monogram and the display-equation rule and is documented as available.
- **Both project-specific accents generalize to one pair**: `accent` (decorative) +
  `accent_text` (contrast-safe). ARIS's coral and wm's amber are the same slot.
- **Contrast is validated, not assumed** — WCAG 2.1 ratios for every text-on-background pair in
  both schemes. ARIS's `#F0787F` → `#C73C44` derivation is exactly the guard that belongs in the
  toolkit, so `accent_text` is auto-darkened/lightened when the supplied accent fails.
- **No third-party requests, preserved.** `font = false`; no MathJax/KaTeX; display equations stay
  Unicode in a styled block; no CDN. Generated sites make zero external requests.
- **Checker split by layer**: universal structural checks always run; a language profile
  (`python` / `julia` / `generic`) adds its own; project-specific assertions stay in the user's
  repo, out of the toolkit.
- **Ownership manifest** (`.docs-studio/manifest.json`, sha256 per file, `managed` vs `seeded`)
  is what makes `update` safe: a managed file whose hash moved is a conflict, reported and
  skipped, never overwritten.

## 4. Caveat carried forward

The Zensical search dialog could not be driven by this environment's automated browser on the
reference sites either (identical theme bundle). Search index and worker deploy and initialize;
the UI chrome is not clickable here. Reported as a limitation, not claimed working.
