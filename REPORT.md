# docs-studio v0.1.0 — build report

*Updated after the customization-stylesheet change; see [§1.1](#11-the-user-owned-stylesheet) and [§8](#8-release-readiness).*

What was built, how it was verified, what it does not do, and what should happen next.
The comparative analysis that this was derived from is in
[docs/comparative-analysis.md](docs/comparative-analysis.md); the validation design is
in [docs/validation.md](docs/validation.md).

---

## 1. What was built

A standalone, installable Python package and CLI that generates Zensical documentation
sites carrying the design language of
[wm-physics-eval](https://sisl.github.io/wm-physics-eval/) and
[ARIS.jl](https://sisl.github.io/ARIS.jl/). Both reference repositories were read only;
neither was modified.

```
src/docs_studio/
  cli.py          Typer commands: init, check, update, presets, preview
  config.py       the docs-studio.toml schema (Pydantic, extra="forbid")
  theme.py        colour arithmetic, design tokens, presets, WCAG contrast
  assets.py       logo handling and the generated monogram
  scaffold.py     rendering, language profiles, the ownership manifest
  validation.py   the layered checker
  update.py       the plan, the diffs, the conflicts
  templates/      10 Jinja templates (config, 2 stylesheets, workflow, 6 page starters)
  presets/        indigo-lavender, ocean-violet, neutral
tests/            11 modules, 251 tests
docs/             comparative analysis, validation design
examples/         three generated sites, plus screenshots
```

3,020 lines of source, 2,560 of tests. Runtime dependencies: `typer`, `pydantic`,
`jinja2`. Zensical is optional (`docs-studio[build]`), so `init` and `check` work
without it and `check` says when it skipped the build.

### The design system, generalized

The two reference stylesheets turned out to be the same file with a different token
prefix: twelve sections, in the same order, with the same token names. That is the
whole extraction. One stable `--ds-*` prefix replaces `--wm-*` and `--aris-*`; the
token block is generated from the palette; the token→`--md-*` mapping (with the doubled
`[data-md-color-scheme=…][data-md-color-primary]` selector that outranks the theme's own
palette rules) is carried over verbatim in structure.

Preserved from the references, deliberately:

- `font = false`, no CDN, no MathJax or KaTeX. **A generated site makes zero
  third-party requests**, and there is a test that asserts it on built HTML.
- Display equations as Unicode in a styled block (`.ds-math`), which is what made the
  zero-request property possible on ARIS.
- `edit_uri = ""`, repository links as home-page resource buttons rather than
  `repo_url` theme chrome.
- `.md-grid` at 62.5rem with a narrowed secondary sidebar, the h2 hairline, the
  regular-weight header wordmark and home headline, the compact outlined resource row,
  the dark-mode logo swap via CSS `content: url(...)`.
- The Pages workflow, structurally identical: minimal permissions, the checker, a
  strict build, `upload-pages-artifact@v5`, `deploy-pages@v5`, manual-only by default.

### 1.1 The user-owned stylesheet

Every site also gets `docs/stylesheets/custom.css`, seeded once and never touched
again, listed in `extra_css` **after** the generated sheet:

```toml
extra_css = ["stylesheets/extra.css", "stylesheets/custom.css"]
```

This closes the one real gap in the ownership model. The design-system stylesheet is
managed, so editing it is a conflict — which is only fair if there is an obvious place
to put your own CSS instead. Now there is, and because it is `seeded`:

- editing it is not a conflict, and `update` never reads or rewrites it;
- a palette change rewrites `extra.css` and leaves `custom.css` alone;
- `--force`, which exists to overwrite conflicts, does not reach it;
- a site generated before this existed acquires it on the next `update`, with no
  conflict, and `zensical.toml` picks up the second entry;
- a `custom.css` that was already there is kept, not replaced.

As generated it is pure comment — 0 CSS rules, confirmed in the browser on all three
example sites — so adding it cannot change how anything looks. It names the tokens and
shows one worked example, so the first thing a reader sees is which variables to reach
for.

### The two design decisions worth stating

**`accent_text` is derived, not trusted.** ARIS's coral `#F0787F` is 2.7:1 on white, so
the site used a darkened `#C73C44` wherever coral text was unavoidable. In the toolkit
that correction is mechanical: `accent` stays decorative and `accent_text` is mixed
toward black or white until it clears 4.5:1 against that scheme's background. A
user-supplied accent cannot ship unreadable text by accident.

**`secondary` was added.** The reference palettes had a deep brand tone (ARIS indigo
`#25235E`) that appeared in the logo and nowhere in the CSS. Rather than drop it, it is
a first-class token used by the generated monogram and the display-equation border, and
documented as available. It is the one token the references did not have; everything
else is theirs.

---

## 2. CLI demonstration

### `init`

```text
$ docs-studio init demo-pkg --name demo-pkg --description "A demonstration package" \
      --author "Example Lab" --repo-url https://github.com/example/demo-pkg \
      --language python --preset indigo-lavender --yes

docs-studio 0.1.0 created a site in ./demo-pkg
  palette indigo-lavender (Indigo / Lavender / Coral), python profile
  + .github/workflows/docs.yml
  + docs/api.md
  + docs/assets/favicon.svg
  + docs/assets/logo-dark.svg
  + docs/assets/logo.svg
  + docs/index.md
  + docs/install.md
  + docs/quickstart.md
  + docs/stylesheets/extra.css
  + docs/usage.md
  + zensical.toml
  no logo was supplied, so a monogram was generated from the project's initials (DP).
  Set branding.logo in docs-studio.toml to replace it.

Next:
  1. write the pages under docs/ (they are starters)
  2. docs-studio check
  3. pip install "zensical==0.0.67" && zensical serve
  4. in the repository's Settings → Pages, set Source to "GitHub Actions", then run the
     Documentation workflow
```

### `check`

```text
$ docs-studio check
  ok   docs-studio.toml parses and validates
  ok   navigation and page set agree (5 pages in the nav)
  ok   13 internal links and anchors resolve
  ok   referenced assets, stylesheets and logo variants exist
  ok   no absolute paths that would break under /demo-pkg/
  ok   markdown shape: fences balanced, lists well formed
  ok   no unrendered template syntax in generated files
  ok   palette 'indigo-lavender': 26 contrast pairs checked in both schemes,
       tightest accent_text/bg (4.86:1 of 4.5)
  ok   python profile: fence languages checked, 4 blocks parsed (Python, JSON, TOML)
  ok   5 of 5 pages are still starters
  ok   manifest from docs-studio 0.1.0 covers 11 files
  ok   `zensical build --clean --strict` succeeded
  info: docs/index.md:1: still the generated starter page; replace the text and delete
        the marker comment at the top [starter-page]
  …

check passed: 0 error(s), 0 warning(s), 5 note(s)
```

A failure names the file and line:

```text
  error: docs/usage.md:3: link to nowhere.md, which does not exist under docs/ [link-missing-page]
check failed: 1 error(s), 0 warning(s), 5 note(s)
```

### `update --dry-run`

The maintainer switched the palette to `neutral` **and** had hand-edited the stylesheet:

```text
$ docs-studio update --dry-run
docs-studio 0.1.0
  0 to create, 1 to update, 1 managed unchanged, 8 yours, untouched, 1 conflict(s)

 CONFLICT  docs/stylesheets/extra.css — edited since docs-studio generated it
    --- a/docs/stylesheets/extra.css
    +++ b/docs/stylesheets/extra.css
    @@ -14,45 +14,45 @@
     :root,
     [data-md-color-scheme="default"] {
    -  --ds-primary: #6254b8;
    -  --ds-primary-hover: #4f42a0;
    +  --ds-primary: #3d4f66;
    +  --ds-primary-hover: #2c3a4d;
       --ds-on-primary: #ffffff;
    …
   update  zensical.toml
    …

1 conflict(s) will be left exactly as they are. Resolve them by hand, or re-run with
--force to discard those edits.

--dry-run: nothing was written.
```

Applying it writes `zensical.toml`, skips the stylesheet, and exits 1 — and the
hand-written rule is still there afterwards. There is an integration test for exactly
this, including that the site still builds after.

---

## 3. The three example sites

In [`examples/`](examples), each generated by `init`, then written. All three are
fictional projects; nothing on them is a real API, result or publication.

| site | profile | palette | branding | pages | `check` | strict build |
| --- | --- | --- | --- | --- | --- | --- |
| [`tidepool`](examples/tidepool) | `python` | ocean-violet | generated monogram | 8 | 0 errors, 0 warnings | passed |
| [`Lattice.jl`](examples/Lattice.jl) | `julia` | indigo-lavender | supplied SVG + dark variant + favicon | 8 | 0 errors, 0 warnings | passed |
| [`greenline`](examples/greenline) | `generic` | neutral | monogram, `monogram_text = "GL"` | 8 | 0 errors, 0 warnings | passed |

`greenline` is a bike-lane route planner maintained by volunteers — deliberately
nothing like the two research sites the design came from. It has no API page, no
citation page, a `Contributing` section and an FAQ, and it uses `trigger = "push"`
rather than manual deployment. It needed no code change to produce; it is the evidence
the toolkit is not wired to its two sources.

`Lattice.jl` exercises the paths the other two do not: a supplied logo with a dark
variant (so the CSS swap is live), a supplied favicon, and `.ds-math` display equations
on two pages.

Each site also demonstrates a real workflow step: `tidepool` and `Lattice.jl` had pages
added to the nav after `init` and picked up starter pages from `update`; `greenline`
had its monogram regenerated with custom initials by deleting the asset and running
`update`.

### Visual validation

Built with `zensical build --clean --strict`, served locally, inspected in a browser.
Screenshots in [`examples/screenshots/`](examples/screenshots).

| check | result |
| --- | --- |
| light, desktop 1280×900 | correct on all three; palette, hairlines, sidebar proportions as in the references |
| dark, desktop | correct; `slate` scheme active from `prefers-color-scheme`, `--ds-primary` resolves to the dark value, page background `rgb(20, 18, 31)` on Lattice.jl |
| dark-mode logo swap | verified by computed style: `content: url(".../lattice-mark-dark.svg")`, logo box 24×24, no distortion |
| mobile 375×812, light and dark | correct; hamburger nav, breadcrumb, wrapped resource row |
| horizontal overflow at 375px | none — `documentElement.scrollWidth == clientWidth == 375`; wide tables and code blocks scroll inside their own containers |
| `.ds-math` display block | renders with the `secondary` left border, `surface_alt` fill, muted `.ds-where` caption |
| third-party requests | none: no `fonts.googleapis.com`, `fonts.gstatic.com`, jsDelivr, cdnjs, unpkg, polyfill.io, MathJax or KaTeX in any built page (asserted by test) |
| assets under a Pages sub-path | no `href="/assets…"` or `src="/assets…"`; all references relative |

---

## 4. Testing report

```text
$ uv run pytest
251 passed in 12.97s
```

| module | tests | covers |
| --- | --- | --- |
| `test_theme.py` | 24 | colour parsing and rejection, WCAG ratios, alpha compositing, the contrast adjuster, all three presets in both schemes, custom palettes that fail |
| `test_config.py` | 31 | every validation rule, Pages sub-path derivation, nav duplicates and labels, resources, branding, error message quality |
| `test_assets.py` | 18 | initials, monogram determinism and geometry, byte-for-byte logo copying, all four branding slots, missing-file errors |
| `test_scaffold.py` | 24 | the rendered file set, ownership split, determinism, generated `zensical.toml` parsed back as TOML, every CSS component, the workflow, idempotence, no-overwrite, POSIX paths |
| `test_validation.py` | 47 | the markdown parsing primitives and every diagnostic code |
| `test_update.py` | 22 | the full action matrix, conflicts, `--force`, manifest hashes, version transitions |
| `test_cli.py` | 49 | help and `--version`, interactive and non-interactive `init`, collisions, bad flags, all exit codes, `preview` pass-through |
| `test_packaging.py` | 5 | templates loadable through the package loader, and **the built wheel** installed into a clean venv generating a working site |
| `test_custom_stylesheet.py` | 20 | the user-owned stylesheet: that it exists, is seeded, is listed last, survives palette changes, `--force` and version transitions, and is acquired safely by an older site |
| `test_integration.py` | 11 | the three profile/palette combinations generated, checked and **built strictly**; zero third-party requests; sub-path assets; the edit-survives-update scenario |

Tests that run `zensical` skip themselves when it is not installed, so the suite passes
without it: the 10 Zensical-gated tests skip and the other 241 pass.

### Failures found during development, and what they were

1. **`adjust_for_contrast` could not lighten a dark saturated colour.** It scaled each
   channel, which saturates; `#3a3560` on `#14121f` stalled at 4.02:1 against a 4.5
   target. Changed to mix toward black or white, which always converges. Found by
   `test_adjust_for_contrast_lightens_on_a_dark_background`.
2. **The generated workflow failed the toolkit's own checker.** GitHub Actions
   expressions are written `${{ … }}`, which the `template-leftover` check read as
   unrendered Jinja. Those spans are now removed before the check runs, and there is a
   test that the workflow's real expression is not flagged.
3. **The API starter page contained invalid Python.** The signature block was labelled
   `python` but held `example_name(argument, *, option=None) -> Result`, which `ast`
   rightly rejects. Relabelled `text`, which is what wm-physics-eval does for
   signatures.
4. **Starter pages linked to pages that might not be in the nav.** `index.md` linked to
   `usage.md` unconditionally; a user whose nav omits it got a broken link on a site
   nobody had touched. Templates now go through a `link(label, page)` helper that
   degrades to plain text when the page is not in this nav.
5. **`docs_studio_version` landed inside `[deploy]`.** It was emitted after the last
   table in the generated TOML, so it parsed as a key of that table and failed
   validation. Moved above `[project]`.

All five were caught by the suite or by running the tool, and all five are now covered
by a test.

---

## 5. Repository readiness

### Provenance and licensing

| item | provenance | note |
| --- | --- | --- |
| `src/`, `tests/`, templates | written for this toolkit | Apache-2.0 |
| the CSS structure | **derived** from the two reference stylesheets: 21 of 36 rules identical after normalizing the prefix | see [NOTICE](NOTICE); the two sources are MIT and Apache-2.0, and neither permission is obtained |
| the Pages workflow | modelled on ARIS.jl's, which is itself the standard GitHub Pages recipe from `actions/*` documentation | step names and action versions are the published ones |
| palette values | `indigo-lavender` and `ocean-violet` reproduce 19 of 22 values each from the reference stylesheets; `neutral` and `studio-teal` are original | taken as part of the derived stylesheets, so covered by [NOTICE](NOTICE) |
| `simple-*` / `lucide/*` / `material/*` icon shortcodes | resolved by Zensical's bundled theme at build time | referenced, not vendored |
| `examples/brand/lattice-*.svg` | drawn for the example site | Apache-2.0, with the rest |
| generated monogram | drawn by `assets.py` from the palette and initials | deterministic; no model involved |
| example site prose | written for this report | fictional projects, labelled as such on every home page |

**Superseded — and since resolved.** The project is now Apache-2.0 with full
attribution; see [NOTICE](NOTICE) and [RELEASE.md](RELEASE.md) §1. The original
assessment below was wrong. An evidence-based review before release
found that the stylesheet is a *derivative work*, not an independent reimplementation
(21 of 36 rules identical after normalizing the custom-property prefix), that the two
sources carry **different** licenses (MIT and Apache-2.0), and that no permission has
been obtained from either copyright holder. See [NOTICE](NOTICE) and
[RELEASE.md](RELEASE.md) §1.

Zensical itself is pinned at `0.0.67` and not vendored. Verified on 2026-10-22 that
0.0.67 is the current release, that its CLI takes `build -f/-c/-s` and
`serve -f/-a/-o/-s`, and that the config keys used here (`font`, `palette` as an array
of tables, `extra_css`, `nav` as nested tables, `validation.invalid_links`) are what its
config loader actually reads.

### No secrets, nothing published

`docs-studio.toml` holds no credentials and the Pages workflow needs none — it
authenticates with the workflow's own OIDC token. Nothing was published to PyPI, no
GitHub repository was created, nothing was pushed, nothing was deployed. The two
reference repositories were not modified.

### Ready to use

```bash
cd ~/Desktop/docs-studio
uv sync
uv run pytest
uv run docs-studio --help
uv run docs-studio presets
```

---

## 6. Known limitations

1. **The Zensical search dialog could not be driven here.** `/search.json` deploys
   (23 KB on the Greenline site) and the theme bundle loads, but the dialog renders its
   input lazily and does not open under this environment's automated browser. The same
   limitation was observed on the reference sites, which ship the identical theme
   bundle. **Search is not claimed to work; it is untested.**
2. **The generated monogram uses an SVG `<text>` element**, so it renders with whatever
   system font the viewer has. That is fine for a placeholder and deliberate — no web
   font means no third-party request — but a real logo should replace it before launch.
3. **No `.ico` favicon is generated.** The generated favicon is SVG, which modern
   browsers accept. A supplied `.ico` is copied through; generating one would need
   Pillow, which is a heavy dependency for one file.
4. **A wordmark goes above the home headline, not in the header.** Replacing the
   header's text site name needs a template override, which is exactly the fragile
   internal customization this avoids.
5. **`update` never deletes.** A page removed from the nav, or a monogram superseded by
   a real logo, stays on disk. `check` reports an orphaned page as a warning; removing
   it is the maintainer's decision.
6. **`check` cannot see your code.** By design — see
   [docs/validation.md](docs/validation.md). A documented function that does not exist
   will not be caught here.
7. **Julia, and any language without a parser in the standard library, gets fence
   checking but not fence parsing.** A syntactically broken Julia snippet passes.
8. **One docs directory, one site.** No multi-version (`mike`), no i18n, no blog
   plugin, no `mkdocstrings`. Zensical supports some of these; the toolkit does not
   generate them.
9. **`--force` on `update` is irreversible** for a file not in version control. It says
   so, and it is the only way to lose an edit.
10. **The contrast model is WCAG 2.1 relative luminance.** It does not model APCA, font
    weight or size, so a pair that passes at 4.5:1 can still read poorly at small
    weights.

---

## 7. Prioritized next steps for v0.1

**Should land before anyone else uses it**

1. **A `docs-studio.toml` reference page**, generated from the Pydantic models so it
   cannot drift. The README documents the common fields; the full schema is currently
   only readable in `config.py`.
2. **`update --interactive`**, resolving conflicts one file at a time (keep / take /
   show diff / write `.new` beside it). Today a conflict is all-or-nothing per run, and
   `--force` is a blunt instrument.
3. **CI for this repository**: the suite on 3.11/3.12/3.13, plus a job that builds the
   three example sites strictly. The toolkit has no workflow of its own, which is a
   poor advertisement.

**Soon after**

4. **`docs-studio check --format json`**, so the diagnostics can be annotated onto a
   pull request rather than read in a log.
5. **A `--palette-from-logo` hint**: sample the dominant colours of a supplied logo and
   propose a palette, contrast-corrected. The arithmetic is already there.
6. **More language profiles** — Rust, TypeScript — each a `LanguageProfile` and a set
   of expected fences. Adding one is about thirty lines.
7. **Deletion handling in `update`**: offer to remove managed files that the config no
   longer produces, behind a confirmation.

**Worth considering, not obviously right**

8. **Vendoring a minimal `.ico` writer** to generate a favicon without Pillow.
9. **Multi-version docs** via `mike`, if anyone asks. It is a large surface and nobody
   has.

*(The previous list's item 9 — a seeded `custom.css` so additions have a home that is
never a conflict — is now implemented; see [§1.1](#11-the-user-owned-stylesheet).)*

---

## 8. Release readiness

A packaging audit run against a **fresh wheel installed into a clean virtual
environment outside the source tree**, with nothing from the checkout on `sys.path`.

### Build

```text
$ uv build
Building wheel from source distribution...
Successfully built docs_studio-0.1.0.tar.gz
Successfully built docs_studio-0.1.0-py3-none-any.whl
```

| | size | contents |
| --- | --- | --- |
| wheel | 49 KB | `docs_studio/` only — 27 entries, including all 10 templates and all 3 presets |
| sdist | 61 KB | `src/`, `tests/`, `README.md`, `LICENSE`, `pyproject.toml` |

The wheel is built *from the sdist*, so the sdist is self-contained by construction.

**One thing was fixed here:** the sdist was picking up `examples/README.md` and
`examples/screenshots/README.md` — two stray files from directories it does not
otherwise ship. `[tool.hatch.build.targets.sdist]` now carries an explicit
`exclude = ["examples", "docs"]`, so the distribution holds the package and its suite
and nothing else. The example sites stay in the repository, where they belong.

### Fresh install

```text
$ uv venv -p 3.13 venv
$ uv pip install dist/docs_studio-0.1.0-py3-none-any.whl
$ ./venv/bin/docs-studio --version
docs-studio 0.1.0
```

| check | result |
| --- | --- |
| console script | `docs-studio = docs_studio.cli:app`, resolves and runs |
| `--version` | `docs-studio 0.1.0`, matching `docs_studio.__version__` |
| `--help`, and `--help` on all five commands | all respond |
| metadata | name, version, `Requires-Python: >=3.11`, `License-Expression: MIT`, summary all present |
| `Requires-Dist` | `jinja2>=3.1`, `pydantic>=2.7`, `typer>=0.12`, `zensical==0.0.67; extra == "build"` |
| resolved tree | 15 packages; no stray build or test dependency |
| `docs-studio[build]` extra | pulls `zensical==0.0.67`; `zensical --version` confirms |
| templates and presets | all 14 data files load through `importlib.resources` from the installed wheel |

### README commands, verbatim, from the wheel

Each command in the README was run against the fresh install:

- `docs-studio presets` — all three palettes, with their contrast verdicts.
- `docs-studio init my-docs --name … --preset ocean-violet --yes` — full site, with
  `custom.css` generated and listed in `extra_css`.
- `docs-studio check` **with Zensical absent** — passes, and says what it skipped:
  `skip zensical build --clean --strict (zensical is not on PATH; …)`. Exit 0.
- `docs-studio check` **with Zensical installed** — `ok  zensical build --clean
  --strict succeeded`. Exit 0.
- `docs-studio preview` with Zensical absent — exits 2 with the install instruction,
  rather than a traceback.
- `docs-studio update` on a fresh site — `nothing to do`.

**One README correction:** the install section said
`uv tool install docs-studio`, which would fail, because the package is not on PyPI.
It now gives the clone and the build-a-wheel routes, and notes the PyPI command as
something for after publication. Nothing in the README now describes a command that
does not work today.

### Verdict

**Ready for a v0.1 repository release.** 251 tests pass; the three example sites check
clean and build strictly; the wheel works from a cold install with no checkout present;
and every documented command does what it says. The open items in §6 and §7 are
follow-ups, not blockers — the largest of them, a safe home for custom CSS, is what
this round closed.

Not ready for a *PyPI* release, and not because of the code: the distribution name
`docs-studio` has not been checked for availability, and a published package implies a
support commitment that is the maintainer's to make. Nothing has been published, no
repository created, nothing committed or pushed.
