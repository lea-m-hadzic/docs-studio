# Validation: what `check` does, and what has to be yours

`docs-studio check` validates the *site*. It cannot validate the *project*, because it
does not import it — and that boundary is worth being explicit about, since the useful
half of documentation testing lives on the other side of it.

## Three layers

### Universal — always runs

Structural facts that are true of any documentation site:

| Check | Diagnostic code |
| --- | --- |
| `docs-studio.toml` parses and validates | `config` |
| the nav and the page set are a bijection | `nav-missing-page`, `page-not-in-nav` |
| no page appears twice in the nav | `nav-duplicate` (and refused by the config) |
| every internal link resolves | `link-missing-page`, `link-missing-file` |
| every heading anchor resolves, same page and across pages | `anchor-missing` |
| referenced assets exist | `asset-missing`, `theme-asset-missing` |
| the stylesheet and the assets it references exist | `stylesheet-missing`, `css-asset-missing` |
| no absolute path that would 404 under a Pages sub-path | `absolute-path-link`, `absolute-path-asset` |
| fenced code is balanced; lists are well formed | `fence-unbalanced`, `list-needs-blank-line`, `list-indent` |
| no unrendered template syntax | `template-leftover` |
| the palette clears WCAG AA in both schemes | `contrast` |
| managed files match the manifest | `managed-file-edited`, `manifest-missing`, `manifest-stale` |
| no page is still the generated starter | `starter-page` |

Anchors are matched against the slugs Python-Markdown's `toc` extension produces, after
stripping the markup a heading can carry — an `attr_list` suffix, inline code, a link,
raw HTML — so `## \`is_estimate\`` and `# Welcome! { .ds-home-title }` resolve the way
they do in the built site.

### Language-specific — picked by `project.language`

Fences are checked against the languages the profile expects, and parsed where a real
parser is available: Python with `ast`, TOML with `tomllib`, JSON with `json`. A fence
in a language with no parser here — Julia, say — is left alone rather than guessed at
with a regular expression. Getting a false error out of a brittle pattern is worse than
getting no error.

### Project-specific — yours

Everything that needs to import the project:

- Does a documented function exist, and is it exported?
- Does a documented default match the source?
- Does a snippet on the page actually run, and produce the output shown?
- Does the CLI page list exactly the options the parser has?

`docs-studio check` does none of this and should not try. Put it in the project's own
test suite, where the project is importable and CI already runs it.

## Two patterns worth copying

Both reference sites solved this, in different ways, and the difference is instructive.

### Static: parse the source, compare the names

`ARIS.jl` documents a Julia package, so its checker — 180 lines of plain standard
library, no Julia needed — parses the module's `export` blocks statically and fails
when an API page documents a name the package does not export:

```python
# In the project's own tests, not in docs-studio.
import re
from pathlib import Path

def exported_names(module: Path) -> set[str]:
    text = re.sub(r"#[^\n]*", "", module.read_text())
    names: set[str] = set()
    for block in re.finditer(r"\bexport\b(.*?)(?=\n\s*\n|\ninclude|\nend\b)", text, re.S):
        names |= {t for t in re.split(r"[,\s]+", block.group(1)) if t.isidentifier()}
    return names

def test_api_page_documents_only_exported_names():
    exported = exported_names(Path("src/MyPackage.jl"))
    page = Path("docs/api.md").read_text()
    for heading in re.findall(r"^#{2,3}\s+`(\w+)`\s*$", page, re.M):
        assert heading in exported, f"docs/api.md documents {heading}, which is not exported"
```

Cheap, no runtime for the documented language, and it catches the failure that actually
happens: a name renamed in the source and left behind on the page.

### Dynamic: run the snippets

`wm-physics-eval` documents a Python package, so its checker imports it and *executes*
every snippet against scripted stand-ins, then compares documented signatures against
`inspect.signature` and documented dataclass fields against `dataclasses.fields`:

```python
# In the project's own tests.
import ast, inspect, io, re, contextlib
from pathlib import Path

import my_package

FENCE = re.compile(r"^```python[^\n]*\n(.*?)^```", re.S | re.M)

def test_every_python_snippet_runs():
    for page in sorted(Path("docs").glob("*.md")):
        namespace: dict = {}
        with contextlib.redirect_stdout(io.StringIO()):
            for source in FENCE.findall(page.read_text()):
                exec(compile(source, str(page), "exec"), namespace)

def test_documented_parameters_exist():
    page = Path("docs/api.md").read_text()
    for name, params in re.findall(r"^(\w+)(\(.*?\))$", page, re.M):
        target = getattr(my_package, name, None)
        if target is None:
            continue
        documented = [a.arg for a in ast.parse(f"def f{params}: pass").body[0].args.args]
        real = list(inspect.signature(target).parameters)
        assert set(documented) <= set(real), f"{name}: {set(documented) - set(real)}"
```

More work to set up — the snippets need fixtures, fakes and a sandbox directory — and
far stronger: a page that has drifted from the code fails CI rather than quietly
misleading a reader.

## Syntactic validation and semantic verification

`check`'s first eleven steps are syntactic: they establish that the site is
*well formed*. The last one is not. `zensical build --clean --strict` is the only step
that establishes the site actually builds, with the real markdown pipeline, the real
theme and the real link resolver — and it is the step that catches what a checker
written against a model of the renderer never will.

So `check` runs it by default, and reports when it could not:

```text
  skip zensical build --clean --strict (zensical is not on PATH; install it with `pip install "zensical==0.0.67"`)
```

A report that says what it skipped is worth more than one that quietly checked less.
