# Architecture

Seven modules, no plugin system, no registry, no runtime. `docs-studio` renders files
from a validated config and records what it wrote; everything else follows from that.

```text
src/docs_studio/
  cli.py          Typer commands: init, check, update, presets, preview
  config.py       the docs-studio.toml schema (Pydantic, extra="forbid")
  theme.py        colour arithmetic, design tokens, presets, WCAG contrast
  assets.py       logo handling and the generated monogram
  scaffold.py     rendering, language profiles, the ownership manifest
  validation.py   the layered checker
  update.py       the plan, the diffs, the conflicts
  templates/      10 Jinja templates
  presets/        3 palettes, as TOML
```

## The dependency direction

```text
cli ──> update ──> scaffold ──> assets ──> config ──> theme
         │            │           │          │
         └────────────┴───────────┴──────────┴──> theme
 validation ──> scaffold, config, theme
```

It is acyclic, and deliberately so. `theme.py` depends on nothing in the package;
`config.py` depends only on `theme`; `scaffold.py` is the only module that renders;
`update.py` is the only one that decides what to write. `cli.py` holds no logic beyond
argument handling and printing.

The one placement that is not obvious: `Manifest` lives in `scaffold.py`, not
`update.py`. It describes generated files, which is `scaffold`'s subject, and putting
it in `update` would make the two import each other.

## `theme.py` — colour, with no I/O

A `Color` is sRGB with straight alpha, parsed from five syntaxes and rendered back as
`#rrggbb` or `rgba(…)`. It composites, mixes and reports WCAG relative luminance.

A `Scheme` is one colour mode's complete token set, built from twelve required tokens
with six derived. A `Palette` is the light/dark pair.

`adjust_for_contrast` is the one piece of real arithmetic: it mixes a colour toward
black or white until it clears a target ratio against a background. Mixing rather than
scaling each channel matters — a dark saturated colour cannot be scaled bright enough
to be readable on a dark background, but mixing toward white always converges.

## `config.py` — the schema, and nothing else

Pydantic models with `extra="forbid"`, so a misspelled key is an error rather than a
setting that silently does nothing. Validation is where it belongs: a nav entry
validates its own pages, the root model validates that no page appears twice, and
`ProjectConfig.pages_base_path` derives the Pages sub-path from `site_url`.

Errors are collected and formatted together, so one run tells you everything that is
wrong with the file.

## `scaffold.py` — render, then record

`render_site` returns a `SiteRender`: every file the config produces, as bytes, with an
ownership, and **nothing written**. That purity is what makes `update` possible — the
plan can be computed and shown without touching the disk.

`write_site` writes it, skipping anything that already exists unless told otherwise,
and saves the manifest. A skipped file is recorded with the hash of what is actually on
disk, so it is the user's from then on.

Language profiles are a frozen dataclass of strings — the fence language, the starter
wording, the fence languages `check` expects. Adding one is about thirty lines and no
new concepts.

## `validation.py` — layered, and honest about it

Universal structural checks, then language-specific ones, then the real build. The
markdown primitives are small and separately tested: `strip_fences` blanks fenced code
while preserving line numbering, `iter_links` matches brackets rather than running one
large regular expression, `slugify` mirrors the `toc` extension's slugs.

[Validation](validation.md) covers what each layer proves and what it does not.

## `update.py` — a plan, then an apply

`plan_update` reads the manifest, renders what the config would produce now, and
returns an `Action` per file. `apply_update` writes that plan. Splitting them is what
makes `--dry-run` trustworthy: the dry run is the same computation, with the write step
not called.

The manifest rewrite is the subtle part. A skipped conflict keeps its **old** recorded
hash, so it stays a conflict until somebody resolves it. Recording the current bytes
instead would make the next update think the file was pristine and overwrite the edit.

## `cli.py` — Typer, and no logic

Every command is a thin wrapper: parse, call into a module, print, exit with a code
that means something. The printing is deliberately plain — `ok`, `skip`, `error:` with
a file and line — so output is readable in a terminal and greppable in a log.

## Templates

Jinja2 with `StrictUndefined`, loaded through `PackageLoader`, so a missing variable is
an error at render time rather than an empty string in somebody's stylesheet. The one
custom filter, `tq`, emits a TOML basic string; every interpolated value in a generated
TOML goes through it.

Starter pages cross-reference each other through a `link(label, page)` helper that
degrades to plain text when the page is not in this nav. Without it, a user whose nav
omits a page gets a broken link on a site nobody has touched yet.

## What is deliberately absent

- **No plugin architecture.** Three presets and three language profiles are data, not
  extension points. A fourth of either is a file, not an API.
- **No abstraction over Zensical.** The generated `zensical.toml` is written the way a
  person would write it, and the site builds without `docs-studio` installed.
- **No state beyond the manifest.** No database, no cache, no lock file of its own.
- **No network.** Nothing in the package makes a request, and neither does a generated
  site.

[Where the design came from](comparative-analysis.md) covers the extraction that
produced the design system; [Contributing](contributing.md) covers working on this.
