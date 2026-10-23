# Installation

## Requirements

- **Python 3.11** or later. Continuous integration runs 3.11, 3.12 and 3.13.
- Nothing else. The three runtime dependencies — Typer, Pydantic and Jinja2 — are pure
  Python, and `pip` or `uv` will fetch them.

[Zensical](https://zensical.org) is **optional**. `init` and `check` work without it,
and `check` says so rather than pretending it validated more than it did:

```text
  skip zensical build --clean --strict (zensical is not on PATH; install it with `pip install "zensical==0.0.67"`)
```

You need it to build or preview a site.

## Install

`docs-studio` is not published to PyPI, so install it from a clone:

```bash
git clone https://github.com/lea-m-hadzic/docs-studio
cd docs-studio
uv sync
uv run docs-studio --help
```

To use it outside that checkout, build a wheel and install that:

```bash
uv build
uv tool install dist/docs_studio-0.1.0-py3-none-any.whl
```

!!! warning "Do not trust an install you have not exercised"
    A generator that is missing one of its bundled templates fails only when somebody
    reaches that template. Run `docs-studio presets` and generate one throwaway site
    after installing; both touch the packaged data files.

## Add Zensical

```bash
pip install "zensical==0.0.67"
```

Or, installing `docs-studio` with its optional extra:

```bash
uv pip install "docs-studio[build]"
```

The version is pinned deliberately. A documentation build that is reproducible is
worth more than one that silently follows a moving theme — see
[`deploy.zensical_version`](configuration.md#deploy).

## Development checkout

```bash
git clone https://github.com/lea-m-hadzic/docs-studio
cd docs-studio
uv sync
uv run pytest
```

The suite is 254 tests and runs in roughly fifteen seconds. The ten that shell
out to Zensical skip themselves when it is not installed, so a bare checkout still
passes.

```bash
uv run docs-studio --help
uv run docs-studio presets
uv run docs-studio check          # this repository's own site
```

[Contributing](contributing.md) covers the layout of the source and what a change is
expected to come with.

## Check the install

```bash
docs-studio --version
```

```text
docs-studio 0.1.0
```

If that prints but `docs-studio init` fails with `TemplateNotFound`, the install is
missing its packaged templates — rebuild the wheel rather than working around it.
