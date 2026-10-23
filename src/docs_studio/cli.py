"""The `docs-studio` command line.

Four commands do the work: `init` creates a site, `check` validates it, `update`
regenerates the managed styling, and `presets` shows the palettes. `preview` is a thin
pass-through to Zensical's own dev server and is only offered when Zensical is
installed.

Every command exits non-zero when it found something wrong, so the same commands can
be used unchanged in continuous integration.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from . import __version__
from .assets import initials
from .config import CONFIG_FILENAME, ConfigError, load_config
from .scaffold import (
    LANGUAGE_PROFILES,
    Manifest,
    default_config_toml,
    render_site,
    write_site,
)
from .theme import check_contrast, load_preset, preset_names
from .update import apply_update, plan_update
from .validation import CheckReport, check_project

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Generate polished Zensical documentation sites from one config file.",
)

ERROR = typer.colors.RED
WARN = typer.colors.YELLOW
GOOD = typer.colors.GREEN
DIM = typer.colors.BRIGHT_BLACK


def _echo(text: str = "", color: str | None = None, bold: bool = False) -> None:
    typer.echo(typer.style(text, fg=color, bold=bold) if color or bold else text)


def _fail(message: str) -> None:
    _echo(f"error: {message}", ERROR)
    raise typer.Exit(code=2)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"docs-studio {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """docs-studio."""


# ------------------------------------------------------------------------------ init


def _parse_resource(raw: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) not in (2, 3) or not all(parts[:2]):
        _fail(
            f"--resource {raw!r}: expected 'Label|https://url' with an optional "
            "'|icon-name', e.g. 'GitHub|https://github.com/org/repo|simple-github'"
        )
    label, url = parts[0], parts[1]
    icon = parts[2] if len(parts) == 3 and parts[2] else "material/link"
    return label, url, icon


def _guess_site_url(repo_url: str | None, name: str) -> str:
    """The GitHub Pages URL for a repository, which is right far more often than not."""
    if repo_url:
        match = re.match(
            r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url
        )
        if match:
            owner, repo = match.groups()
            return f"https://{owner.lower()}.github.io/{repo}/"
    return f"https://example.github.io/{name}/"


@app.command()
def init(
    directory: Annotated[
        Path, typer.Argument(help="Where to create the site. Defaults to the current directory.")
    ] = Path("."),
    name: Annotated[Optional[str], typer.Option(help="Project name, as shown in the header.")] = None,
    description: Annotated[Optional[str], typer.Option(help="One-line site description.")] = None,
    author: Annotated[Optional[str], typer.Option(help="Author or organisation.")] = None,
    site_url: Annotated[Optional[str], typer.Option(help="Published URL, including any Pages sub-path.")] = None,
    repo_url: Annotated[Optional[str], typer.Option(help="Repository URL.")] = None,
    language: Annotated[Optional[str], typer.Option(help="python | julia | generic.")] = None,
    preset: Annotated[Optional[str], typer.Option(help="Palette preset. See `docs-studio presets`.")] = None,
    logo: Annotated[Optional[Path], typer.Option(help="Logo file to copy in. A monogram is generated if omitted.")] = None,
    logo_dark: Annotated[Optional[Path], typer.Option(help="Dark-header logo variant.")] = None,
    wordmark: Annotated[Optional[Path], typer.Option(help="Wordmark shown above the home headline.")] = None,
    favicon: Annotated[Optional[Path], typer.Option(help="Favicon file to copy in.")] = None,
    copyright_line: Annotated[Optional[str], typer.Option("--copyright", help="Footer copyright line.")] = None,
    resource: Annotated[
        Optional[list[str]],
        typer.Option(help="Home-page resource button: 'Label|https://url|icon'. Repeatable."),
    ] = None,
    trigger: Annotated[str, typer.Option(help="Pages workflow trigger: manual | push.")] = "manual",
    pages: Annotated[bool, typer.Option("--pages/--no-pages", help="Generate the GitHub Pages workflow.")] = True,
    config: Annotated[
        Optional[Path],
        typer.Option(help=f"Use an existing {CONFIG_FILENAME} instead of asking anything."),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Never prompt; fail if something required is missing.")] = False,
    force: Annotated[bool, typer.Option(help="Overwrite files that already exist. Off by default.")] = False,
) -> None:
    """Create a documentation site, in a new directory or an existing repository."""
    root = directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / CONFIG_FILENAME

    if config is not None:
        source = config.resolve()
        if not source.is_file():
            _fail(f"--config {source} does not exist")
        if source != config_path:
            if config_path.exists() and not force:
                _fail(
                    f"{CONFIG_FILENAME} already exists in {root}; pass --force to replace it"
                )
            shutil.copyfile(source, config_path)
    elif config_path.exists() and not force:
        _echo(
            f"{CONFIG_FILENAME} already exists; using it. Pass --force to rewrite it.",
            DIM,
        )
    else:
        _write_fresh_config(
            config_path,
            root=root,
            name=name,
            description=description,
            author=author,
            site_url=site_url,
            repo_url=repo_url,
            language=language,
            preset=preset,
            logo=logo,
            logo_dark=logo_dark,
            wordmark=wordmark,
            favicon=favicon,
            copyright_line=copyright_line,
            resources=[_parse_resource(r) for r in (resource or [])],
            trigger=trigger,
            pages=pages,
            interactive=not yes,
        )

    try:
        project = load_config(config_path)
        render = render_site(project, root)
    except ConfigError as exc:
        _fail(str(exc))
        return
    except FileNotFoundError as exc:
        _fail(str(exc))
        return

    failures = [c for c in check_contrast(render.palette) if not c.ok]
    for failure in failures:
        _echo(f"  contrast: {failure.describe()}", WARN)
    if failures:
        _echo(
            "  the palette does not clear WCAG AA; adjust it in "
            f"{CONFIG_FILENAME} and run `docs-studio update`.",
            WARN,
        )

    written, skipped = write_site(render, root, overwrite=force)
    _echo()
    _echo(f"docs-studio {__version__} created a site in {root}", bold=True)
    _echo(
        f"  palette {render.palette.name} ({render.palette.title}), "
        f"{project.project.language} profile"
    )
    for path in written:
        _echo(f"  + {path}", GOOD)
    for path in skipped:
        _echo(f"  = {path} (already there, left alone)", DIM)
    if not render.assets.copies:
        _echo(
            "  no logo was supplied, so a monogram was generated from the project's "
            f"initials ({initials(project.project.name)}). Set branding.logo in "
            f"{CONFIG_FILENAME} to replace it.",
            DIM,
        )
    _echo(
        "  the generated stylesheet is a derivative work and carries the notices its "
        "licenses require in its header; keep them with it when you publish "
        "(docs-studio check verifies this).",
        DIM,
    )
    _echo()
    _echo("Next:")
    _echo("  1. write the pages under docs/ (they are starters)")
    _echo("  2. docs-studio check")
    _echo('  3. pip install "zensical==0.0.67" && zensical serve')
    if project.deploy.github_pages:
        _echo(
            "  4. in the repository's Settings → Pages, set Source to "
            '"GitHub Actions", then run the Documentation workflow'
        )


def _write_fresh_config(
    config_path: Path,
    *,
    root: Path,
    name: str | None,
    description: str | None,
    author: str | None,
    site_url: str | None,
    repo_url: str | None,
    language: str | None,
    preset: str | None,
    logo: Path | None,
    logo_dark: Path | None,
    wordmark: Path | None,
    favicon: Path | None,
    copyright_line: str | None,
    resources: list[tuple[str, str, str]],
    trigger: str,
    pages: bool,
    interactive: bool,
) -> None:
    def ask(label: str, value: str | None, default: str | None = None) -> str:
        if value:
            return value
        if not interactive:
            if default is not None:
                return default
            _fail(f"--{label.lower().replace(' ', '-')} is required with --yes")
        return typer.prompt(label, default=default) if default else typer.prompt(label)

    project_name = ask("Project name", name, root.name)
    project_description = ask(
        "One-line description", description, f"Documentation for {project_name}"
    )
    project_author = ask("Author or organisation", author, project_name)
    repository = repo_url or (
        typer.prompt("Repository URL (blank for none)", default="") if interactive else ""
    )
    repository = repository.strip() or None
    url = ask("Site URL", site_url, _guess_site_url(repository, project_name))

    profile = language or (
        typer.prompt(
            f"Language profile ({' | '.join(LANGUAGE_PROFILES)})", default="generic"
        )
        if interactive
        else "generic"
    )
    if profile not in LANGUAGE_PROFILES:
        _fail(f"unknown language profile {profile!r}; one of {', '.join(LANGUAGE_PROFILES)}")

    palette = preset or (
        typer.prompt(f"Palette preset ({' | '.join(preset_names())})", default="neutral")
        if interactive
        else "neutral"
    )
    if palette not in preset_names():
        _fail(f"unknown preset {palette!r}; one of {', '.join(preset_names())}")

    if trigger not in ("manual", "push"):
        _fail("--trigger must be manual or push")

    if not resources and repository:
        resources = [("GitHub Repository", repository, "simple-github")]

    def relative(path: Path | None) -> str | None:
        if path is None:
            return None
        resolved = path.resolve()
        if not resolved.is_file():
            _fail(f"{path} does not exist")
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            # Outside the repository: copy it in first, so the site is self-contained.
            destination = root / "docs" / "assets" / resolved.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolved, destination)
            return destination.relative_to(root).as_posix()

    text = default_config_toml(
        name=project_name,
        description=project_description,
        author=project_author,
        site_url=url,
        repo_url=repository,
        language=profile,
        preset=palette,
        copyright_line=copyright_line,
        logo=relative(logo),
        favicon=relative(favicon),
        resources=resources,
        trigger=trigger,
        pages_github=pages,
    )
    extra: list[str] = []
    if logo_dark:
        extra.append(f'logo_dark = "{relative(logo_dark)}"')
    if wordmark:
        extra.append(f'wordmark = "{relative(wordmark)}"')
    if extra:
        text = text.replace(
            "\n# Compact outlined buttons",
            "\n" + "\n".join(extra) + "\n\n# Compact outlined buttons",
            1,
        )
    config_path.write_text(text, encoding="utf-8")


# ----------------------------------------------------------------------------- check


@app.command()
def check(
    path: Annotated[Path, typer.Option(help="The site's root directory.")] = Path("."),
    build: Annotated[
        bool,
        typer.Option("--build/--no-build", help="Also run `zensical build --clean --strict`."),
    ] = True,
    require_authored: Annotated[
        bool,
        typer.Option(help="Treat a page that is still a generated starter as an error."),
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Only print problems.")] = False,
) -> None:
    """Validate the site: config, structure, links, assets, theme, and the build."""
    root = path.resolve()
    report = check_project(root, build=build, require_authored=require_authored)
    _print_report(report, quiet=quiet)
    raise typer.Exit(code=1 if report.errors else 0)


def _print_report(report: CheckReport, *, quiet: bool) -> None:
    if not quiet:
        for step in report.steps:
            _echo(f"  ok   {step}", GOOD)
        for step in report.skipped:
            _echo(f"  skip {step}", DIM)
    for diagnostic in report.sorted():
        if quiet and diagnostic.level == "info":
            continue
        color = {"error": ERROR, "warning": WARN, "info": DIM}[diagnostic.level]
        _echo(f"  {diagnostic.render()}", color)
    _echo()
    counts = (
        f"{report.count('error')} error(s), {report.count('warning')} warning(s), "
        f"{report.count('info')} note(s)"
    )
    if report.errors:
        _echo(f"check failed: {counts}", ERROR, bold=True)
    else:
        _echo(f"check passed: {counts}", GOOD, bold=True)


# ---------------------------------------------------------------------------- update


@app.command()
def update(
    path: Annotated[Path, typer.Option(help="The site's root directory.")] = Path("."),
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the plan and write nothing.")] = False,
    show_diff: Annotated[bool, typer.Option("--diff/--no-diff", help="Print the diff for each change.")] = True,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Apply without asking.")] = False,
    force: Annotated[
        bool,
        typer.Option(help="Overwrite conflicts too. This discards those edits."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Also list the files left untouched."),
    ] = False,
) -> None:
    """Regenerate the managed styling and config, keeping your content and edits."""
    root = path.resolve()
    try:
        plan = plan_update(root)
    except ConfigError as exc:
        _fail(str(exc))
        return
    except FileNotFoundError as exc:
        _fail(str(exc))
        return

    if not plan.had_manifest:
        _echo(
            "warning: there is no .docs-studio/manifest.json here, so every managed "
            "file that already exists counts as a conflict. If this site was "
            "generated by docs-studio, restore the manifest from version control.",
            WARN,
        )
    if plan.from_version != plan.to_version:
        _echo(f"docs-studio {plan.from_version} → {plan.to_version}", bold=True)
    else:
        _echo(f"docs-studio {plan.to_version}", bold=True)
    _echo(f"  {plan.summary()}")
    _echo()

    for action in plan.actions:
        if action.kind == "unchanged" or (action.kind == "keep" and not verbose):
            continue
        color = ERROR if action.is_conflict else (GOOD if action.kind == "create" else None)
        _echo(action.headline(), color)
        if show_diff and action.diff and action.kind != "keep":
            for line in action.diff.splitlines():
                shade = (
                    GOOD if line.startswith("+") and not line.startswith("+++")
                    else ERROR if line.startswith("-") and not line.startswith("---")
                    else DIM
                )
                _echo(f"    {line}", shade)
    if plan.is_noop:
        _echo("nothing to do: everything managed is already current.", GOOD)
        raise typer.Exit(code=0)

    if plan.conflicts and not force:
        _echo()
        _echo(
            f"{len(plan.conflicts)} conflict(s) will be left exactly as they are. "
            "Resolve them by hand, or re-run with --force to discard those edits.",
            WARN,
        )

    if dry_run:
        _echo()
        _echo("--dry-run: nothing was written.", DIM)
        raise typer.Exit(code=1 if plan.conflicts else 0)

    if not yes:
        _echo()
        verb = "Apply, overwriting conflicts" if force else "Apply these changes"
        if not typer.confirm(verb, default=False):
            _echo("nothing was written.", DIM)
            raise typer.Exit(code=1)

    written, skipped = apply_update(plan, force=force)
    _echo()
    for item in written:
        _echo(f"  wrote   {item}", GOOD)
    for item in skipped:
        _echo(f"  skipped {item} (conflict)", WARN)
    manifest = Manifest.load(root)
    if manifest:
        _echo(f"  manifest: {len(manifest.files)} files, docs-studio {manifest.docs_studio_version}", DIM)
    raise typer.Exit(code=1 if skipped else 0)


# --------------------------------------------------------------------------- presets


@app.command()
def presets() -> None:
    """List the bundled palettes and how much contrast headroom each has."""
    for name in preset_names():
        palette = load_preset(name)
        results = check_contrast(palette)
        tightest = min(results, key=lambda r: r.ratio / r.required)
        failures = [r for r in results if not r.ok]
        _echo(f"{name}", bold=True)
        _echo(f"  {palette.title} — {palette.description}")
        _echo(
            f"  light primary {palette.light['primary'].css()}, "
            f"dark primary {palette.dark['primary'].css()}, "
            f"accent {palette.light['accent'].css()}"
        )
        status = (
            f"{len(failures)} pair(s) below target"
            if failures
            else f"all {len(results)} pairs pass"
        )
        _echo(
            f"  WCAG: {status}; tightest is {tightest.scheme} "
            f"{tightest.foreground}/{tightest.background} at {tightest.ratio:.2f}:1",
            ERROR if failures else GOOD,
        )
        _echo()


# --------------------------------------------------------------------------- preview


@app.command()
def preview(
    path: Annotated[Path, typer.Option(help="The site's root directory.")] = Path("."),
    addr: Annotated[str, typer.Option(help="Address for the dev server.")] = "localhost:8000",
    open_browser: Annotated[bool, typer.Option("--open", help="Open a browser window.")] = False,
) -> None:
    """Serve the site locally with Zensical's own dev server."""
    root = path.resolve()
    executable = shutil.which("zensical")
    if not executable:
        _fail(
            'zensical is not on PATH. Install it with `pip install "zensical==0.0.67"` '
            "(or `uv pip install docs-studio[build]`), then try again."
        )
        return
    if not (root / "zensical.toml").is_file():
        _fail(f"there is no zensical.toml in {root}; run `docs-studio init` first")
        return
    command = [executable, "serve", "--dev-addr", addr]
    if open_browser:
        command.append("--open")
    _echo(f"$ {' '.join(command)}", DIM)
    raise typer.Exit(code=subprocess.call(command, cwd=root))  # noqa: S603


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
