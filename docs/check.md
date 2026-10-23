# `check`

Validates the site. Everything it reports carries a file and, where it has one, a
line, and it exits non-zero when it found an error — so the same command works
unchanged in continuous integration.

```bash
docs-studio check [OPTIONS]
```

## Options

| Option | Effect |
| --- | --- |
| `--path` | the site's root directory; defaults to the current one |
| `--build` / `--no-build` | run `zensical build --clean --strict`; on by default |
| `--require-authored` | treat a page that is still a generated starter as an error |
| `--quiet`, `-q` | print only problems |

## What it reports

```text
  ok   docs-studio.toml parses and validates
  ok   navigation and page set agree (8 pages in the nav)
  ok   21 internal links and anchors resolve
  ok   referenced assets, stylesheets and logo variants exist
  ok   no absolute paths that would break under /my-package/
  ok   markdown shape: fences balanced, lists well formed
  ok   no unrendered template syntax in generated files
  ok   palette 'ocean-violet': 26 contrast pairs checked in both schemes, tightest accent_text/bg (4.53:1 of 4.5)
  ok   python profile: fence languages checked, 11 blocks parsed (Python, JSON, TOML)
  ok   all 8 pages have been written
  ok   manifest from docs-studio 0.1.0 covers 15 files
  ok   `zensical build --clean --strict` succeeded

check passed: 0 error(s), 0 warning(s), 0 note(s)
```

A failure names the place:

```text
  error: docs/usage.md:3: link to nowhere.md, which does not exist under docs/ [link-missing-page]
check failed: 1 error(s), 0 warning(s), 5 note(s)
```

!!! info "It says what it skipped"
    Without Zensical installed, the last step cannot run, and the report says so rather
    than quietly checking less. A report you can trust is one that admits its gaps.

## Diagnostic codes

### Errors — these fail the run

| Code | Meaning |
| --- | --- |
| `config` | `docs-studio.toml` is missing, is not valid TOML, or fails validation |
| `structure` | there is no `docs/` directory |
| `nav-empty`, `nav-duplicate` | the nav is empty, or lists a page twice |
| `nav-missing-page` | the nav lists a page that does not exist |
| `link-missing-page`, `link-missing-file` | an internal link does not resolve |
| `anchor-missing` | no heading matches a `#fragment`, on this page or another |
| `asset-missing`, `theme-asset-missing` | a referenced image or the logo is not there |
| `stylesheet-missing`, `css-asset-missing` | `extra_css` or the stylesheet points at a missing file |
| `absolute-path-link`, `absolute-path-asset` | a path that would 404 under a Pages sub-path |
| `fence-unbalanced` | a code fence is not closed |
| `fence-syntax` | a Python, JSON or TOML block does not parse |
| `template-leftover` | a generated file still contains template syntax |
| `contrast` | a text pair falls below WCAG AA in either scheme |
| `zensical-missing`, `zensical-invalid` | `zensical.toml` is absent or unreadable |
| `build-failed` | the strict build failed, with its last lines quoted |
| `starter-page` | only under `--require-authored` |

### Warnings — reported, but the run passes

| Code | Meaning |
| --- | --- |
| `page-not-in-nav` | a page exists that nothing links to |
| `list-needs-blank-line`, `list-indent` | markdown that will not render as a list |
| `fence-unlabelled` | a code block with no language gets no highlighting |
| `manifest-missing`, `manifest-stale` | the manifest is gone, or names a file that is |
| `managed-file-edited` | a managed file has been edited since it was generated |

`managed-file-edited` is the early warning for a conflict: it tells you before you run
[`update`](update.md) that one is waiting.

### Notes

| Code | Meaning |
| --- | --- |
| `starter-page` | a page still carries its generated marker |
| `fence-unexpected-language` | a fence language outside this profile's usual set |
| `logo-no-dark-variant` | there is a logo but no dark-header variant |

## In continuous integration

```bash
docs-studio check --require-authored
```

The generated Pages workflow runs `docs-studio check --no-build` and then the strict
build as its own step, so a failure says which half broke. See
[Deploying](deployment.md).

## What it does not do

`check` validates the site, not your project. It does not import your package, so it
cannot tell you that a documented function has been renamed. That check belongs in your
own test suite — [Validation](validation.md) explains the split and gives two patterns
worth copying.
