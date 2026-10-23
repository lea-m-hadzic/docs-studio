# Contributing

## Setting up

```bash
git clone https://github.com/lea-m-hadzic/docs-studio
cd docs-studio
uv sync
uv run pytest
```

254 tests, roughly fifteen seconds. The ten that shell out to Zensical skip
themselves when it is not installed, so a bare checkout still passes — but install it
before sending anything, because those ten are the ones that prove a generated site
actually builds.

## The layout

[Architecture](architecture.md) covers the modules and why they depend on each other
the way they do. In short: `theme` knows nothing about files, `config` is only a
schema, `scaffold` is the only module that renders, `update` is the only one that
decides what to write, and `cli` holds no logic.

## What a change comes with

**A test that fails without it.** Every bug fixed so far has one, and the test names
the failure rather than the fix: `test_adjust_for_contrast_lightens_on_a_dark_background`,
not `test_colour_fix_2`.

**The whole suite passing**, including the Zensical builds.

**The example sites still clean**, if you touched a template:

```bash
for site in examples/tidepool examples/Lattice.jl examples/greenline; do
  uv run docs-studio check --path "$site"
done
```

A template change usually means a managed file in each example needs regenerating:

```bash
uv run docs-studio update --path examples/tidepool --dry-run
```

**This site rebuilt**, if you changed what the documentation describes:

```bash
uv run docs-studio check
```

## Adding a palette preset

A TOML file in `src/docs_studio/presets/`, with twelve tokens per scheme. It is picked
up automatically — there is no registry to edit. [Palettes](palettes.md) lists the
tokens.

It has to clear contrast in both schemes:

```bash
uv run docs-studio presets
```

A preset that fails is a bug, not a style choice.

## Adding a language profile

A `LanguageProfile` in `scaffold.py`: the fence language, the starter wording, and the
fence languages `check` should expect. About thirty lines.

The wording is the part to get right. It must not claim the project is published
anywhere or has any particular API — where a real command is needed, the starter says
so and gives both cases. Generating a confident-looking `pip install` for a package
that is not on PyPI is worse than generating nothing.

## Changing a template

Templates are Jinja2 with `StrictUndefined`, so a variable you forget to pass is an
error at render time. Two rules:

- **A starter page may only link to a page in the nav.** Use the `link(label, page)`
  helper, which degrades to plain text. A hardcoded link breaks every site whose nav
  does not include that page.
- **A code fence must be valid in the language it claims.** `check` parses `python`,
  `json` and `toml` fences, including in generated pages. A signature that is not
  runnable Python goes in a `text` fence.

## Style

Match what is there. Comments explain *why*, not what — the ones worth reading in this
codebase are the ones recording a decision: why the mapping selector is doubled, why a
skipped conflict keeps its old hash, why `secondary` exists.

Type hints throughout. Dataclasses for anything with more than two fields. No `Any`
where a real type will do.

## What not to add

The scope is deliberately small, and the pressure is always toward more:

- **No plugin architecture.** Presets and profiles are data.
- **No abstraction over Zensical.** The generated config is what a person would write.
- **No network calls**, in the package or in a generated site. The no-third-party-request
  property is tested, and it is worth keeping.
- **No image generation beyond the monogram**, which is deterministic SVG drawn from
  the palette.

## Reporting something

A good report has the `docs-studio.toml` that produced it, the command, the output, and
the versions:

```bash
docs-studio --version
zensical --version
python --version
```

For a rendering problem, say which scheme and which viewport — light and dark are
different stylesheets' worth of values, and the layout changes at 60em.

## Licensing

Apache-2.0. A contribution is taken as offered under the same terms.

The generated styling derives from two other projects, one MIT and one Apache-2.0.
`NOTICE` in the repository root is the record: what was derived, from where, under
which license, and what was changed. If you bring in code or artwork from elsewhere,
add it there — an unattributed addition is far more trouble to unpick later than to
document now, and this project is its own worked example.

Two things to keep working when you touch the stylesheet template:

- **the attribution header stays at the top of the generated file.** It is what makes
  a published site carry the notices its licenses require. `docs-studio check` warns
  if it is gone, and `tests/test_licensing.py` fails.
- **the upstream copyright notice is reproduced verbatim**, not paraphrased into a
  field. MIT requires the notice itself.
