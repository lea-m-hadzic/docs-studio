# Quickstart

An empty directory to a built site, in about two minutes.

## Generate

```bash
docs-studio init my-docs \
  --name "my-package" \
  --description "What it does, in one line" \
  --author "Your Lab" \
  --repo-url https://github.com/org/my-package \
  --language python \
  --preset ocean-violet \
  --yes
```

Without `--yes` it asks for each of those instead, with sensible defaults — the
directory name, a site URL guessed from the repository. [`init`](init.md) has the full
set of flags.

```text
docs-studio 0.1.0 created a site in ./my-docs
  palette ocean-violet (Ocean / Violet), python profile
  + .github/workflows/docs.yml
  + docs/api.md
  + docs/assets/favicon.svg
  + docs/assets/logo-dark.svg
  + docs/assets/logo.svg
  + docs/index.md
  + docs/install.md
  + docs/quickstart.md
  + docs/stylesheets/custom.css
  + docs/stylesheets/extra.css
  + docs/usage.md
  + zensical.toml
  no logo was supplied, so a monogram was generated from the project's initials (MP).
  Set branding.logo in docs-studio.toml to replace it.
```

No logo was given, so one was drawn from the project's initials and the palette, in
both schemes — see [Logo and favicon](branding.md).

## Validate

```bash
cd my-docs
docs-studio check
```

Every page is still a generated starter, which `check` reports as a note rather than a
failure:

```text
  ok   docs-studio.toml parses and validates
  ok   navigation and page set agree (5 pages in the nav)
  ok   13 internal links and anchors resolve
  ok   palette 'ocean-violet': 26 contrast pairs checked in both schemes, tightest accent_text/bg (4.53:1 of 4.5)
  ok   `zensical build --clean --strict` succeeded
  info: docs/index.md:1: still the generated starter page; replace the text and delete the marker comment at the top [starter-page]
  …
check passed: 0 error(s), 0 warning(s), 5 note(s)
```

## Preview

```bash
zensical serve
```

Then open `http://localhost:8000`. `docs-studio preview` does the same thing and tells
you how to install Zensical if it is missing.

## Write

The pages under `docs/` are starters. Each carries a marker comment on its first line,
`check` lists every page that still has one, and `--require-authored` turns that into a
failure so an unwritten page cannot ship:

```bash
docs-studio check --require-authored
```

Add or rename pages by editing the `[[nav]]` tables in `docs-studio.toml`; the next
[`update`](update.md) creates a starter for anything new.

## Make it yours

Change the palette in `docs-studio.toml`, then regenerate the styling:

```bash
docs-studio update --dry-run    # the plan and the diffs, writing nothing
docs-studio update              # asks before writing
```

Your pages, your artwork and `docs/stylesheets/custom.css` are not touched. See
[File ownership](ownership.md).

## Publish

`init` wrote `.github/workflows/docs.yml`, manual-only by default. One setting has to
be changed by hand first: in the repository's **Settings → Pages**, set **Source** to
**GitHub Actions**. Then run the Documentation workflow from the Actions tab.
[Deploying](deployment.md) covers the rest.
