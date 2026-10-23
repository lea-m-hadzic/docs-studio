# Deploying to GitHub Pages

With `deploy.github_pages = true`, `init` writes `.github/workflows/docs.yml`. It is
modelled on a workflow that is in production, and it is managed — change it through
`docs-studio.toml`, not by editing it.

## One-time setup, by hand

In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**.

Until that is done the deploy step fails with *"Pages site not found"*. It is the one
step nothing can do for you.

!!! warning "docs-studio does not touch your repository"
    It does not create repositories, change settings, push, or deploy. It writes a
    workflow file; everything after that is yours to run.

## The workflow

```yaml
name: Documentation
on:
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
```

Minimal permissions, and no secrets: it authenticates with the workflow's own OIDC
token. Then, in order:

1. `actions/configure-pages@v6`
2. `actions/checkout@v7`
3. `actions/setup-python@v6`, at `deploy.python_version`
4. `pip install "zensical==0.0.67"`, at `deploy.zensical_version`
5. any `deploy.extra_install` lines
6. `docs-studio check --no-build`, if `docs-studio` is on `PATH`
7. `zensical build --clean --strict`
8. `actions/upload-pages-artifact@v5`, uploading `site`
9. `actions/deploy-pages@v5`

The build is strict, so a broken link fails the run instead of going live.

### Getting the checker into the job

Step 6 runs the checker only when it is installed, because the workflow cannot assume
`docs-studio` is on PyPI — it may not be published, and in this repository's case it
*is* the project being built. Install it with `extra_install`:

```toml
[deploy]
extra_install = ["pip install ."]
```

For a project that does not depend on it, point at wherever you install it from. With
no `extra_install`, the job says so and carries on:

```text
docs-studio is not installed in this job, so the checker did not run.
Add it under deploy.extra_install in docs-studio.toml to run it here.
```

The strict build still runs either way, so the deployment is still gated.

## Manual or on push

```toml
[deploy]
trigger = "manual"
```

`manual` emits `workflow_dispatch` only: nothing publishes until someone runs it from
the Actions tab. That is the default, and it is the right one for a site whose contents
are still settling.

```toml
[deploy]
trigger = "push"
branch = "main"
```

`push` adds the push trigger for `branch`, keeping `workflow_dispatch` as well.

Change the setting and run [`update`](update.md); the workflow is managed, so it is
regenerated.

## The sub-path

A project site lives under the repository name:

```text
https://org.github.io/my-package/
```

Everything on the page has to resolve relative to that, not to the domain root. Two
things make it work:

- `project.site_url` includes the path, and Zensical resolves asset URLs from it.
- `check` derives the sub-path and **fails** any link or asset that starts with `/`:

```text
  error: docs/usage.md:3: /index.html is an absolute path, which resolves to the
  domain root and not to /my-package/; use a relative link [absolute-path-link]
```

Use relative links between pages (`install.md`, `../assets/logo.svg`) and this cannot
go wrong. A user or organisation site, served at the domain root, has
`pages_base_path` of `/` and the check has nothing to catch.

## Publishing elsewhere

The generated site is an ordinary Zensical project. Any static host works:

```bash
zensical build --clean --strict
# then upload site/
```

`docs-studio` generates no configuration for Netlify, Vercel, Read the Docs or GitLab
Pages. `site_url` still has to match wherever it lands, or assets will not resolve.

## `site/` is build output

Add it to `.gitignore`, along with Zensical's `.cache/`:

```text
site/
.cache/
```

The workflow builds from source on every run; a committed `site/` is only ever stale.
