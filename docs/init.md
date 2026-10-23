# `init`

Creates a documentation site, in a new directory or in a repository you already have.

```bash
docs-studio init [DIRECTORY] [OPTIONS]
```

`DIRECTORY` defaults to the current directory, and is created if it does not exist.

## What it writes

| Path | Owner | What it is |
| --- | --- | --- |
| `docs-studio.toml` | you | every setting; the only file you are expected to edit |
| `zensical.toml` | managed | derived entirely from the above |
| `docs/stylesheets/extra.css` | managed | the generated design system |
| `docs/stylesheets/custom.css` | you | where your own CSS goes |
| `docs/*.md` | you | one starter page per nav entry |
| `docs/assets/` | you | the logo, its dark variant, the favicon |
| `.github/workflows/docs.yml` | managed | the Pages workflow, if enabled |
| `.docs-studio/manifest.json` | — | checksums and ownership; commit it |

[File ownership](ownership.md) explains what those owners mean in practice.

## It never silently overwrites

A file that already exists is skipped and reported:

```text
  = docs/index.md (already there, left alone)
```

`--force` overwrites instead. Either way, `init` in a repository that already has a
`docs/` directory is safe to run.

## Options

### Project

| Option | Effect |
| --- | --- |
| `--name` | the project name, shown in the header |
| `--description` | one line, used as the site description |
| `--author` | author or organisation |
| `--site-url` | the published URL, including any Pages sub-path |
| `--repo-url` | the repository; also used to guess `--site-url` |
| `--copyright` | the footer line |
| `--language` | `python`, `julia` or `generic` |

`--site-url` is guessed from `--repo-url` when you leave it out: a GitHub repository at
`https://github.com/sisl/ARIS.jl` gives `https://sisl.github.io/ARIS.jl/`. That
sub-path matters — see [Deploying](deployment.md#the-sub-path).

### Appearance

| Option | Effect |
| --- | --- |
| `--preset` | a bundled palette; see [`presets`](presets.md) |
| `--logo` | a logo file, copied in verbatim |
| `--logo-dark` | the variant for the dark header |
| `--wordmark` | an image shown above the home-page headline |
| `--favicon` | a favicon file, copied in verbatim |

A path outside the target directory is copied into `docs/assets/` so the site is
self-contained. With no `--logo`, a monogram is generated.
[Logo and favicon](branding.md) has the details.

### Home-page resources

```bash
--resource "GitHub Repository|https://github.com/org/repo|simple-github"
--resource "Paper|https://example.org/paper|material/file-document-outline"
```

`Label|URL|icon`, repeatable. The icon is a theme shortcode; omit it for a generic
link icon. With no `--resource` but a `--repo-url`, one GitHub button is added for you.

### Deployment

| Option | Effect |
| --- | --- |
| `--trigger` | `manual` (default) or `push` |
| `--pages` / `--no-pages` | write the workflow, or do not |

### How it runs

| Option | Effect |
| --- | --- |
| `--yes`, `-y` | never prompt; fall back to defaults, and fail if something required has none |
| `--config FILE` | copy an existing `docs-studio.toml` and use it, asking nothing |
| `--force` | overwrite files that already exist |

## Interactive

Without `--yes`, `init` asks for the project name, description, author, repository
URL, site URL, language profile and palette, in that order, each with a default you can
accept with Return.

```text
$ docs-studio init my-docs
Project name [my-docs]: interactive-pkg
One-line description [Documentation for interactive-pkg]: What it does, in one line
Author or organisation [interactive-pkg]: Example Lab
Repository URL (blank for none): https://github.com/example/interactive-pkg
Site URL [https://example.github.io/interactive-pkg/]:
Language profile (python | julia | generic) [generic]: python
Palette preset (indigo-lavender | neutral | ocean-violet) [neutral]: indigo-lavender
```

## Scripted

`--yes` makes it fully non-interactive, which is what you want in a template repository
or a bootstrap script. Everything it cannot default to has to be passed, and a missing
required value is an error rather than a prompt.

For a site you have generated before, keep the config and use it directly:

```bash
docs-studio init new-repo --config path/to/docs-studio.toml
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | the site was created |
| 2 | a bad flag, a missing file, or a required value missing under `--yes` |

A palette that fails contrast is reported as a warning and the site is still written,
so you can see it and fix it; `check` then reports it as an error.
