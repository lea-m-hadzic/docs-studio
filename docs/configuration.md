# `docs-studio.toml`

The one file you are expected to edit. Everything that distinguishes one generated site
from another lives here: project metadata, the palette, the branding, the navigation
and how it deploys. The styling does not — that is generated.

Validation is strict and unforgiving about silence: **an unknown key is an error**,
not a setting that quietly does nothing.

```text
docs-studio.toml has 1 problem(s):
  project.colour_scheme: Extra inputs are not permitted
```

!!! warning "No secrets belong here"
    The file is committed, and the Pages workflow needs no credentials — it
    authenticates with the workflow's own OIDC token. Nothing in the schema takes a
    token, a key or a password.

## A complete example

```toml
docs_studio_version = "0.1.0"

[project]
name = "my-package"
description = "What it does, in one line"
author = "Your Lab"
site_url = "https://org.github.io/my-package/"
repo_url = "https://github.com/org/my-package"
copyright = "MIT"
language = "python"

[theme]
preset = "ocean-violet"

[branding]
logo = "docs/assets/my-logo.svg"
logo_dark = "docs/assets/my-logo-dark.svg"
favicon = "docs/assets/favicon.ico"

[[resources]]
label = "GitHub Repository"
url = "https://github.com/org/my-package"
icon = "simple-github"

[[nav]]
title = "Home"
page = "index.md"

[[nav]]
title = "Getting started"
pages = ["quickstart.md", { title = "Installation", page = "install.md" }]

[deploy]
github_pages = true
trigger = "manual"
branch = "main"
python_version = "3.13"
zensical_version = "0.0.67"
```

## `[project]`

| Key | Type | Default | What it does |
| --- | --- | --- | --- |
| `name` | string | required | the site name, shown in the header |
| `description` | string | required | the site description |
| `author` | string | required | author or organisation |
| `site_url` | string | required | the published URL; a trailing slash is added |
| `slug` | string | from `name` | lowercase identifier; rarely set by hand |
| `repo_url` | string | — | the repository |
| `copyright` | string | — | the footer line |
| `language` | enum | `generic` | `python`, `julia` or `generic` |

`site_url` must be absolute. Under GitHub Pages it includes the repository path, and
that path is what makes assets resolve — see [Deploying](deployment.md#the-sub-path).
`check` derives the sub-path from it and refuses any link that would break under it.

`language` picks the wording of the starter pages and the fence languages `check`
expects. It does not change the design.

## `[theme]`

| Key | Type | Default | What it does |
| --- | --- | --- | --- |
| `preset` | string | `neutral` | a bundled palette |
| `palette_file` | string | — | a palette of your own, as a TOML file |
| `light` | table | — | token overrides for the light scheme |
| `dark` | table | — | token overrides for the dark scheme |
| `md_accent` | string | from the palette | the Material colour name Zensical uses |
| `extra_features` | list | `[]` | theme features appended to the toolkit's own |

Overrides layer on top of whichever palette was chosen:

```toml
[theme]
preset = "ocean-violet"

[theme.light]
primary = "#123456"

[theme.dark]
primary = "#8FA7FF"
```

[Palettes](palettes.md) lists every token and what each one carries.

## `[branding]`

| Key | Type | What it does |
| --- | --- | --- |
| `logo` | path | the header logo, copied in verbatim |
| `logo_dark` | path | the variant used under the dark scheme |
| `wordmark` | path | an image above the home-page headline |
| `favicon` | path | the favicon, copied in verbatim |
| `monogram_text` | string | one or two characters for the generated mark |

Paths are relative to `docs-studio.toml`. Accepted extensions are `.svg`, `.png`,
`.ico`, `.webp`, `.jpg` and `.jpeg`. `logo_dark` without `logo` is an error.
[Logo and favicon](branding.md) covers what happens to the files.

## `[[resources]]`

The compact outlined buttons in the home-page resource row. Repeatable.

| Key | Type | What it does |
| --- | --- | --- |
| `label` | string | the button text |
| `url` | string | absolute, or a `mailto:` link |
| `icon` | string | a theme icon shortcode |
| `image` | string | a path under `docs/`, for a mark the theme does not ship |

`icon` and `image` are mutually exclusive.

```toml
[[resources]]
label = "Dataset"
url = "https://example.org/dataset"
image = "assets/dataset-logo.svg"
```

## `[[nav]]`

Each table is either a single page or a titled section. Repeatable, and the order here
is the order in the sidebar.

```toml
[[nav]]
title = "Home"
page = "index.md"

[[nav]]
title = "Reference"
pages = [
  "api.md",
  { title = "Result schemas", page = "schemas.md" },
]
```

A `pages` entry may be a filename, whose label is derived from it
(`multiple-thresholds.md` becomes `Multiple thresholds`), or a table that sets the
label explicitly. An entry needs exactly one of `page` or `pages`.

Rules the validator enforces: every page ends in `.md` and lives under `docs/`, no page
appears twice, and `index.md` is in the nav.

## `[deploy]`

| Key | Type | Default | What it does |
| --- | --- | --- | --- |
| `github_pages` | bool | `true` | write `.github/workflows/docs.yml` |
| `trigger` | enum | `manual` | `manual` or `push` |
| `branch` | string | `main` | the branch `push` watches |
| `python_version` | string | `3.13` | the Python the workflow sets up |
| `zensical_version` | string | `0.0.67` | pinned exactly, so a build is reproducible |
| `extra_install` | list | `[]` | shell lines run before the checker |

`zensical_version` must be an exact version. A range is refused:

```text
  deploy.zensical_version: Value error, deploy.zensical_version must be an exact
  version, e.g. 0.0.67, so a published build is reproducible
```

`extra_install` is how the workflow gets `docs-studio` itself, which it does not assume
is installable from PyPI:

```toml
[deploy]
extra_install = ["pip install ."]
```

## Top level

| Key | Type | What it does |
| --- | --- | --- |
| `docs_studio_version` | string | the toolkit version that last generated this site |

It is informational. The manifest, not this key, is what `update` reads — see
[File ownership](ownership.md).
