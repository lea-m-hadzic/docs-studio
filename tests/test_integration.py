"""End-to-end: generate, validate, and really build with Zensical.

These are the only tests that shell out to `zensical`. They are skipped when it is not
installed, so the suite still runs without it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from docs_studio.cli import app
from typer.testing import CliRunner

ZENSICAL = shutil.which("zensical")
needs_zensical = pytest.mark.skipif(ZENSICAL is None, reason="zensical is not installed")

CASES = [
    ("python", "ocean-violet", "https://example.github.io/py-research/", "py-research"),
    ("julia", "indigo-lavender", "https://example.github.io/JlResearch.jl/", "JlResearch.jl"),
    ("generic", "neutral", "https://example.github.io/field-notes/", "field-notes"),
]


def generate(root: Path, name: str, language: str, preset: str, site_url: str) -> None:
    result = CliRunner().invoke(
        app,
        [
            "init", str(root),
            "--name", name,
            "--description", f"A {language} project used to exercise docs-studio",
            "--author", "Example Lab",
            "--site-url", site_url,
            "--repo-url", f"https://github.com/example/{name}",
            "--language", language,
            "--preset", preset,
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("language, preset, site_url, name", CASES)
def test_generate_and_check(tmp_path: Path, language, preset, site_url, name):
    root = tmp_path / name
    generate(root, name, language, preset, site_url)
    result = CliRunner().invoke(app, ["check", "--path", str(root), "--no-build"])
    assert result.exit_code == 0, result.output


@needs_zensical
@pytest.mark.parametrize("language, preset, site_url, name", CASES)
def test_a_generated_site_builds_strictly(tmp_path: Path, language, preset, site_url, name):
    root = tmp_path / name
    generate(root, name, language, preset, site_url)
    build = subprocess.run(
        [ZENSICAL, "build", "--clean", "--strict"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    site = root / "site"
    assert (site / "index.html").is_file()
    assert (site / "404.html").is_file()
    assert (site / "sitemap.xml").is_file()
    assert (site / "search.json").is_file() or list(site.glob("**/search*"))

    html = (site / "index.html").read_text(encoding="utf-8")
    # The project stylesheet is linked, and the palette reached the page.
    assert "stylesheets/extra.css" in html
    css = next(site.rglob("extra.css"))
    assert "--ds-primary" in css.read_text(encoding="utf-8")
    # The home page's own classes survived the markdown pipeline.
    assert "ds-home-title" in html and "ds-resources" in html


@needs_zensical
def test_the_built_site_makes_no_third_party_requests(tmp_path: Path):
    """`font = false`, no CDN, no maths renderer — the property worth not losing."""
    root = tmp_path / "offline"
    generate(root, "offline", "python", "neutral", "https://example.github.io/offline/")
    assert subprocess.run(
        [ZENSICAL, "build", "--clean", "--strict"], cwd=root, capture_output=True
    ).returncode == 0

    external: list[str] = []
    for page in (root / "site").rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for marker in (
            "fonts.googleapis.com",
            "fonts.gstatic.com",
            "cdn.jsdelivr.net",
            "cdnjs.cloudflare.com",
            "unpkg.com",
            "polyfill.io",
            "mathjax",
            "katex",
        ):
            if marker in text.lower():
                external.append(f"{page.name}: {marker}")
    assert not external, external


@needs_zensical
def test_the_built_site_resolves_assets_under_a_pages_sub_path(tmp_path: Path):
    root = tmp_path / "subpath"
    generate(root, "subpath", "python", "neutral", "https://example.github.io/subpath/")
    assert subprocess.run(
        [ZENSICAL, "build", "--clean", "--strict"], cwd=root, capture_output=True
    ).returncode == 0
    html = (root / "site" / "index.html").read_text(encoding="utf-8")
    # Relative asset references work whatever the site is mounted under; what must not
    # appear is a reference rooted at the domain.
    assert 'href="/assets' not in html and 'src="/assets' not in html
    for reference in ("stylesheets/extra.css", "assets/logo.svg"):
        assert reference in html


@needs_zensical
def test_an_edit_to_a_managed_stylesheet_survives_an_update_and_still_builds(
    tmp_path: Path,
):
    """The scenario the whole manifest exists for."""
    root = tmp_path / "edited"
    generate(root, "edited", "python", "ocean-violet", "https://example.github.io/edited/")
    css = root / "docs" / "stylesheets" / "extra.css"
    mine = css.read_text() + "\n.md-typeset .mine { color: red; }\n"
    css.write_text(mine, encoding="utf-8")

    config = root / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', 'preset = "indigo-lavender"'),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app, ["update", "--path", str(root), "--yes", "--no-diff"]
    )
    assert result.exit_code == 1, result.output  # a conflict was skipped
    assert "CONFLICT" in result.output
    assert css.read_text() == mine, "the hand edit was preserved"
    # zensical.toml did get its update, and the site still builds.
    assert subprocess.run(
        [ZENSICAL, "build", "--clean", "--strict"], cwd=root, capture_output=True
    ).returncode == 0


@needs_zensical
def test_check_runs_the_strict_build_itself(tmp_path: Path):
    root = tmp_path / "builds"
    generate(root, "builds", "python", "neutral", "https://example.github.io/builds/")
    result = CliRunner().invoke(app, ["check", "--path", str(root)])
    assert result.exit_code == 0, result.output
    assert "`zensical build --clean --strict` succeeded" in result.output


@needs_zensical
def test_check_fails_when_the_strict_build_fails(tmp_path: Path):
    root = tmp_path / "broken"
    generate(root, "broken", "python", "neutral", "https://example.github.io/broken/")
    # A link Zensical itself rejects under --strict, which `check` cannot see:
    # an anchor into a page's rendered output.
    (root / "docs" / "usage.md").write_text(
        "# Usage\n\n<!-- docs-studio:starter -->\n", encoding="utf-8"
    )
    (root / "zensical.toml").write_text(
        (root / "zensical.toml").read_text().replace(
            '"stylesheets/custom.css"]',
            '"stylesheets/custom.css", "stylesheets/missing.css"]',
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["check", "--path", str(root)])
    assert result.exit_code == 1
    assert "stylesheet-missing" in result.output
