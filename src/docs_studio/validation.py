"""`docs-studio check` — everything that can be verified without publishing.

The checks are layered, because the reference repositories made the distinction the
hard way: structural facts about a documentation site are universal, while anything
that compares the docs against the code is specific to the language and then to the
project.

universal
    The config parses. The navigation and the page set are a bijection. Every internal
    link and heading anchor resolves. Referenced assets exist, including the dark-mode
    logo that is referenced from CSS rather than from the config. No link is absolute
    in a way that breaks under a GitHub Pages sub-path. No generated file still
    contains template syntax. The palette clears WCAG AA in both colour schemes.

language-specific
    Code fences carry a language the profile expects, and fences in a language with a
    parser available are parsed: Python with `ast`, TOML with `tomllib`, JSON with
    `json`. A fence that does not parse is an error; a language with no parser here is
    left alone rather than guessed at.

project-specific
    Not the toolkit's business. Whether a documented function really exists, whether a
    documented default matches the code, whether a snippet produces the output shown —
    those belong in the project's own test suite, which can import the project. The
    reference sites do exactly this, and `check` deliberately does not try to.

The last step, when Zensical is installed, is `zensical build --clean --strict`: the
only way to know the site really builds. Syntactic validation here, semantic
verification there, and the report says which ran.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal

from .config import CONFIG_FILENAME, ConfigError, StudioProject, load_config
from .scaffold import LANGUAGE_PROFILES, Manifest, sha256_file
from .theme import check_contrast

__all__ = ["CheckReport", "Diagnostic", "Level", "check_project"]

Level = Literal["error", "warning", "info"]

STARTER_MARKER = "<!-- docs-studio:starter -->"
#: The generated stylesheet is a derivative work of two other projects, and carries
#: their notices in its header. If that header is gone, publishing the site
#: redistributes the derived material without the attribution its licenses require.
ATTRIBUTION_MARKER = "ATTRIBUTION — this file is a derivative work"
#: Files that, at the project root, would hold the same notices for the repository
#: as a whole. Any one of them satisfies the suggestion.
ATTRIBUTION_FILES = ("NOTICE", "NOTICE.txt", "NOTICE.md", "THIRD_PARTY_NOTICES",
                     "THIRD_PARTY_NOTICES.txt", "THIRD_PARTY_NOTICES.md",
                     "ATTRIBUTION", "ATTRIBUTION.md")
TEMPLATE_LEFTOVER = re.compile(r"\{\{|\}\}|\{%")
#: GitHub Actions expressions are written `${{ ... }}` and are not leftovers.
ACTIONS_EXPRESSION = re.compile(r"\$\{\{.*?\}\}")
FENCE_LINE = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_+-]*)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
INLINE_CODE = re.compile(r"`[^`]*`")
CSS_URL = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""")
HTML_REF = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One finding, with the file and line a reader can go to."""

    level: Level
    code: str
    message: str
    path: str | None = None
    line: int | None = None

    def render(self) -> str:
        where = self.path or ""
        if where and self.line:
            where = f"{where}:{self.line}"
        prefix = f"{where}: " if where else ""
        return f"{self.level}: {prefix}{self.message} [{self.code}]"


@dataclass
class CheckReport:
    """The diagnostics, plus what actually ran."""

    diagnostics: list[Diagnostic] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def add(
        self,
        level: Level,
        code: str,
        message: str,
        path: str | None = None,
        line: int | None = None,
    ) -> None:
        self.diagnostics.append(Diagnostic(level, code, message, path, line))

    def count(self, level: Level) -> int:
        return sum(1 for d in self.diagnostics if d.level == level)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def sorted(self) -> list[Diagnostic]:
        order = {"error": 0, "warning": 1, "info": 2}
        return sorted(
            self.diagnostics,
            key=lambda d: (order[d.level], d.path or "", d.line or 0, d.code),
        )


# ----------------------------------------------------------------- markdown parsing


def strip_fences(text: str) -> str:
    """The page with fenced code blocks blanked out, line numbering preserved."""
    out: list[str] = []
    closing: str | None = None
    for line in text.splitlines():
        match = FENCE_LINE.match(line)
        if closing is None and match:
            closing = match.group(1)[0] * 3
            out.append("")
            continue
        if closing is not None:
            out.append("")
            if line.strip().startswith(closing):
                closing = None
            continue
        out.append(line)
    return "\n".join(out)


def iter_fences(text: str) -> Iterator[tuple[int, str, str]]:
    """`(line number of the opening fence, language, body)` for each fenced block."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = FENCE_LINE.match(lines[index])
        if not match:
            index += 1
            continue
        marker, language = match.group(1)[0] * 3, match.group(2)
        start, body = index + 1, []
        index += 1
        while index < len(lines) and not lines[index].strip().startswith(marker):
            body.append(lines[index])
            index += 1
        index += 1
        yield start, language, "\n".join(body)


def iter_links(text: str) -> Iterator[tuple[int, str]]:
    """`(line number, target)` for each inline link or image outside code.

    Scanned with a small bracket matcher rather than one large regular expression, so
    a label containing brackets — `[![](logo.svg) Dataset](url)`, which both reference
    home pages use — resolves to the outer target and not to a fragment of it.
    """
    for number, line in enumerate(strip_fences(text).splitlines(), start=1):
        clean = INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)
        position = 0
        while True:
            opening = clean.find("](", position)
            if opening == -1:
                break
            cursor, depth = opening + 2, 1
            while cursor < len(clean) and depth:
                if clean[cursor] == "(":
                    depth += 1
                elif clean[cursor] == ")":
                    depth -= 1
                cursor += 1
            if depth:
                break
            target = clean[opening + 2 : cursor - 1].strip()
            position = cursor
            if not target:
                continue
            # A title after the target: [text](page.md "Title")
            yield number, target.split()[0]


def headings(text: str) -> Iterator[tuple[int, str]]:
    for number, line in enumerate(strip_fences(text).splitlines(), start=1):
        match = HEADING.match(line)
        if match:
            yield number, match.group(2)


def slugify(heading: str) -> str:
    """The anchor Python-Markdown's `toc` extension produces for a heading.

    Mirrors its default slugify after first removing the markup a heading can carry:
    an `attr_list` suffix, inline code, links and raw HTML.
    """
    text = re.sub(r"\{[^}]*\}\s*$", "", heading)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def anchors(text: str) -> set[str]:
    """Every anchor a page offers: its heading slugs, plus explicit `{ #id }`."""
    found = {slugify(h) for _, h in headings(text)}
    found |= set(re.findall(r"\{[^}]*#([A-Za-z0-9_-]+)[^}]*\}", strip_fences(text)))
    return found - {""}


# ------------------------------------------------------------------------- the check


def check_project(
    root: Path,
    *,
    build: bool = True,
    require_authored: bool = False,
) -> CheckReport:
    """Run every check that applies to the site at `root`."""
    report = CheckReport()
    config_path = root / CONFIG_FILENAME

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        report.add("error", "config", str(exc), CONFIG_FILENAME)
        return report
    report.steps.append(f"{CONFIG_FILENAME} parses and validates")

    docs = root / "docs"
    if not docs.is_dir():
        report.add("error", "structure", "there is no docs/ directory", "docs")
        return report

    pages = {p.name: p.read_text(encoding="utf-8") for p in sorted(docs.glob("*.md"))}
    _check_structure(report, config, docs, pages)
    _check_links(report, docs, pages)
    _check_assets(report, root, config, docs, pages)
    _check_pages_paths(report, config, pages)
    _check_markdown_shape(report, pages)
    _check_template_leftovers(report, root, pages)
    _check_attribution(report, root)
    _check_theme(report, root, config)
    _check_language(report, config, pages)
    _check_starters(report, pages, require_authored=require_authored)
    _check_manifest(report, root)
    if build:
        _check_build(report, root)
    else:
        report.skipped.append("zensical build (not requested)")
    return report


def _check_structure(
    report: CheckReport, config: StudioProject, docs: Path, pages: dict[str, str]
) -> None:
    nav_pages = config.pages
    if not nav_pages:
        report.add(
            "error",
            "nav-empty",
            "the nav is empty; list at least index.md",
            CONFIG_FILENAME,
        )
        return
    duplicates = {p for p in nav_pages if nav_pages.count(p) > 1}
    for page in sorted(duplicates):
        report.add(
            "error", "nav-duplicate", f"{page} appears more than once in the nav", CONFIG_FILENAME
        )
    for page in nav_pages:
        if page not in pages and not (docs / page).is_file():
            report.add(
                "error",
                "nav-missing-page",
                f"the nav lists {page}, which does not exist under docs/",
                CONFIG_FILENAME,
            )
    for page in pages:
        if page not in nav_pages:
            report.add(
                "warning",
                "page-not-in-nav",
                f"docs/{page} exists but is in no nav section, so nothing links to it",
                f"docs/{page}",
            )
    report.steps.append(
        f"navigation and page set agree ({len(nav_pages)} pages in the nav)"
    )


def _check_links(report: CheckReport, docs: Path, pages: dict[str, str]) -> None:
    page_anchors = {name: anchors(text) for name, text in pages.items()}
    internal = 0
    for name, text in pages.items():
        for line, target in iter_links(text):
            if target.startswith(("http://", "https://", "mailto:", "data:", "#!")):
                continue
            internal += 1
            path, _, anchor = target.partition("#")
            if not path:
                if anchor and anchor not in page_anchors[name]:
                    report.add(
                        "error",
                        "anchor-missing",
                        f"no heading on this page matches #{anchor}",
                        f"docs/{name}",
                        line,
                    )
                continue
            if path.endswith(".md"):
                if path not in pages:
                    report.add(
                        "error",
                        "link-missing-page",
                        f"link to {path}, which does not exist under docs/",
                        f"docs/{name}",
                        line,
                    )
                elif anchor and anchor not in page_anchors[path]:
                    report.add(
                        "error",
                        "anchor-missing",
                        f"no heading in {path} matches #{anchor}",
                        f"docs/{name}",
                        line,
                    )
            elif not (docs / path).exists():
                report.add(
                    "error",
                    "link-missing-file",
                    f"link to {path}, which does not exist under docs/",
                    f"docs/{name}",
                    line,
                )
    report.steps.append(f"{internal} internal links and anchors resolve")


def _check_assets(
    report: CheckReport,
    root: Path,
    config: StudioProject,
    docs: Path,
    pages: dict[str, str],
) -> None:
    for name, text in pages.items():
        for reference in HTML_REF.findall(text):
            if reference.startswith(("http://", "https://", "data:", "#")):
                continue
            if not (docs / reference).exists():
                report.add(
                    "error",
                    "asset-missing",
                    f"references {reference}, which does not exist under docs/",
                    f"docs/{name}",
                )

    zensical = root / "zensical.toml"
    if not zensical.is_file():
        report.add(
            "error",
            "zensical-missing",
            "there is no zensical.toml; run `docs-studio update` to regenerate it",
            "zensical.toml",
        )
        return
    try:
        site = tomllib.loads(zensical.read_text(encoding="utf-8"))["project"]
    except (tomllib.TOMLDecodeError, KeyError) as exc:
        report.add("error", "zensical-invalid", f"zensical.toml: {exc}", "zensical.toml")
        return

    theme = site.get("theme", {})
    for key in ("logo", "favicon"):
        reference = theme.get(key)
        if reference and not (docs / reference).is_file():
            report.add(
                "error",
                "theme-asset-missing",
                f"theme.{key} points at docs/{reference}, which does not exist",
                "zensical.toml",
            )
    for sheet in site.get("extra_css", []):
        if not (docs / sheet).is_file():
            report.add(
                "error",
                "stylesheet-missing",
                f"extra_css lists {sheet}, which does not exist under docs/",
                "zensical.toml",
            )

    # The dark-mode logo is referenced from the stylesheet, not from the config, so a
    # missing variant would otherwise only show up as a broken image in dark mode.
    stylesheet = docs / "stylesheets" / "extra.css"
    if stylesheet.is_file():
        css = stylesheet.read_text(encoding="utf-8")
        for reference in CSS_URL.findall(css):
            if reference.startswith(("http://", "https://", "data:")):
                continue
            resolved = (stylesheet.parent / reference).resolve()
            if not resolved.is_file():
                report.add(
                    "error",
                    "css-asset-missing",
                    f"the stylesheet references {reference}, which does not exist",
                    "docs/stylesheets/extra.css",
                )
    if config.branding.logo and not config.branding.logo_dark:
        report.add(
            "info",
            "logo-no-dark-variant",
            "there is no branding.logo_dark; the same logo is used on the dark header, "
            "which suits a mark that reads on both backgrounds and not one that does not",
        )
    report.steps.append("referenced assets, stylesheets and logo variants exist")


def _check_attribution(report: CheckReport, root: Path) -> None:
    """The derived stylesheet must keep the notices its licenses require."""
    stylesheet = root / "docs" / "stylesheets" / "extra.css"
    if not stylesheet.is_file():
        return
    if ATTRIBUTION_MARKER not in stylesheet.read_text(encoding="utf-8"):
        report.add(
            "warning",
            "attribution-removed",
            "the attribution header is gone from the generated stylesheet. It is a "
            "derivative work of two other projects, and publishing this site "
            "redistributes it; restore the header with `docs-studio update --force`, "
            "or carry the same notices elsewhere in what you publish",
            "docs/stylesheets/extra.css",
            1,
        )
        return
    if not any((root / name).is_file() for name in ATTRIBUTION_FILES):
        report.add(
            "info",
            "attribution-file",
            "the stylesheet carries its notices, which is what the licenses require. "
            "A NOTICE file at the repository root, pointing at docs-studio and its "
            "two upstreams, makes them easier to find",
        )
    report.steps.append("the generated stylesheet keeps its attribution header")


def _check_pages_paths(
    report: CheckReport, config: StudioProject, pages: dict[str, str]
) -> None:
    base = config.project.pages_base_path
    for name, text in pages.items():
        for line, target in iter_links(text):
            if target.startswith("/") and not target.startswith("//"):
                report.add(
                    "error",
                    "absolute-path-link",
                    f"{target} is an absolute path, which resolves to the domain root "
                    f"and not to {base}; use a relative link",
                    f"docs/{name}",
                    line,
                )
        for reference in HTML_REF.findall(text):
            if reference.startswith("/") and not reference.startswith("//"):
                report.add(
                    "error",
                    "absolute-path-asset",
                    f"{reference} is an absolute path and will 404 under {base}",
                    f"docs/{name}",
                )
    if base == "/":
        report.steps.append("site_url is a root site; no sub-path to get wrong")
    else:
        report.steps.append(f"no absolute paths that would break under {base}")


def _check_markdown_shape(report: CheckReport, pages: dict[str, str]) -> None:
    for name, text in pages.items():
        opens = sum(1 for line in text.splitlines() if FENCE_LINE.match(line))
        if opens % 2:
            report.add(
                "error",
                "fence-unbalanced",
                "a fenced code block is not closed",
                f"docs/{name}",
            )
        lines = text.splitlines()
        inside = False
        for index, line in enumerate(lines):
            if FENCE_LINE.match(line):
                inside = not inside
                continue
            if inside:
                continue
            previous = lines[index - 1] if index else ""
            if re.match(r"(- |\* |\d+\. )", line) and previous.strip() and not re.match(
                r"(\s*)(- |\* |\d+\. )|\s|\||#|!!!|<", previous
            ):
                report.add(
                    "warning",
                    "list-needs-blank-line",
                    "a list that does not start after a blank line renders as prose",
                    f"docs/{name}",
                    index + 1,
                )
            if re.match(r" {1,3}(- |\* |\d+\. )", line):
                report.add(
                    "warning",
                    "list-indent",
                    "a nested list indented by fewer than 4 spaces is not nested",
                    f"docs/{name}",
                    index + 1,
                )
    report.steps.append("markdown shape: fences balanced, lists well formed")


def _check_template_leftovers(
    report: CheckReport, root: Path, pages: dict[str, str]
) -> None:
    candidates: dict[str, str] = {f"docs/{n}": t for n, t in pages.items()}
    for extra in ("zensical.toml", "docs/stylesheets/extra.css", ".github/workflows/docs.yml"):
        path = root / extra
        if path.is_file():
            candidates[extra] = path.read_text(encoding="utf-8")
    for name, text in candidates.items():
        for number, line in enumerate(text.splitlines(), start=1):
            if TEMPLATE_LEFTOVER.search(ACTIONS_EXPRESSION.sub("", line)):
                report.add(
                    "error",
                    "template-leftover",
                    "this line still contains template syntax, so something did not render",
                    name,
                    number,
                )
    report.steps.append("no unrendered template syntax in generated files")


def _check_theme(report: CheckReport, root: Path, config: StudioProject) -> None:
    try:
        palette = config.palette(root)
    except ConfigError as exc:
        report.add("error", "palette", str(exc), CONFIG_FILENAME)
        return
    results = check_contrast(palette)
    for result in results:
        if not result.ok:
            report.add(
                "error" if result.kind == "text" else "warning",
                "contrast",
                result.describe(),
                CONFIG_FILENAME,
            )
    worst = min(results, key=lambda r: r.ratio / r.required)
    report.steps.append(
        f"palette {palette.name!r}: {len(results)} contrast pairs checked in both "
        f"schemes, tightest {worst.foreground}/{worst.background} "
        f"({worst.ratio:.2f}:1 of {worst.required:.1f})"
    )


def _check_language(
    report: CheckReport, config: StudioProject, pages: dict[str, str]
) -> None:
    profile = LANGUAGE_PROFILES[config.project.language]
    parsed = 0
    for name, text in pages.items():
        for line, language, body in iter_fences(text):
            if not language:
                report.add(
                    "warning",
                    "fence-unlabelled",
                    "a code fence with no language gets no highlighting",
                    f"docs/{name}",
                    line,
                )
                continue
            if language not in profile.expected_fences:
                report.add(
                    "info",
                    "fence-unexpected-language",
                    f"fence language {language!r} is outside the "
                    f"{config.project.language} profile's usual set "
                    f"({', '.join(profile.expected_fences)})",
                    f"docs/{name}",
                    line,
                )
            problem = _parse_fence(language, body)
            if problem:
                report.add(
                    "error", "fence-syntax", f"this {language} block {problem}",
                    f"docs/{name}", line,
                )
            elif language in ("python", "json", "toml"):
                parsed += 1
    report.steps.append(
        f"{config.project.language} profile: fence languages checked, {parsed} blocks "
        "parsed (Python, JSON, TOML)"
    )


def _parse_fence(language: str, body: str) -> str | None:
    """A real parser where one is available; silence where none is."""
    if not body.strip():
        return None
    try:
        if language == "python":
            ast.parse(body)
        elif language == "json":
            json.loads(body)
        elif language == "toml":
            tomllib.loads(body)
    except SyntaxError as exc:
        return f"does not parse: line {exc.lineno}: {exc.msg}"
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        return f"does not parse: {exc}"
    return None


def _check_starters(
    report: CheckReport, pages: dict[str, str], *, require_authored: bool
) -> None:
    starters = [name for name, text in pages.items() if STARTER_MARKER in text]
    for name in starters:
        report.add(
            "error" if require_authored else "info",
            "starter-page",
            "still the generated starter page; replace the text and delete the marker "
            "comment at the top",
            f"docs/{name}",
            1,
        )
    if starters:
        report.steps.append(f"{len(starters)} of {len(pages)} pages are still starters")
    else:
        report.steps.append(f"all {len(pages)} pages have been written")


def _check_manifest(report: CheckReport, root: Path) -> None:
    manifest = Manifest.load(root)
    if manifest is None:
        report.add(
            "warning",
            "manifest-missing",
            "there is no .docs-studio/manifest.json, so `docs-studio update` cannot "
            "tell a generated file from an edited one; run `docs-studio init` here or "
            "restore the file from version control",
        )
        return
    missing = [p for p in manifest.files if not (root / p).exists()]
    for path in missing:
        report.add(
            "warning", "manifest-stale", "recorded in the manifest but no longer on disk", path
        )
    edited = [
        path
        for path, entry in manifest.files.items()
        if entry.get("ownership") == "managed"
        and (root / path).is_file()
        and sha256_file(root / path) != entry.get("sha256")
    ]
    for path in edited:
        report.add(
            "warning",
            "managed-file-edited",
            "a managed file has been edited since it was generated; `docs-studio "
            "update` will report it as a conflict rather than overwrite it",
            path,
        )
    report.steps.append(
        f"manifest from docs-studio {manifest.docs_studio_version} covers "
        f"{len(manifest.files)} files"
    )


def _check_build(report: CheckReport, root: Path) -> None:
    executable = shutil.which("zensical")
    if not executable:
        report.skipped.append(
            "zensical build --clean --strict (zensical is not on PATH; "
            'install it with `pip install "zensical==0.0.67"`)'
        )
        return
    result = subprocess.run(  # noqa: S603 - a fixed command, user's own project
        [executable, "build", "--clean", "--strict"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-12:]
        report.add(
            "error",
            "build-failed",
            "`zensical build --clean --strict` failed:\n    "
            + "\n    ".join(tail),
        )
    else:
        report.steps.append("`zensical build --clean --strict` succeeded")
