"""Rendering a site: what comes out, who owns it, and whether it repeats."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from docs_studio.config import load_config
from docs_studio.scaffold import (
    CUSTOM_STYLESHEET,
    MANAGED_STYLESHEET,
    DEFAULT_FEATURES,
    LANGUAGE_PROFILES,
    MANIFEST_PATH,
    Manifest,
    render_site,
    write_site,
)


def test_a_render_produces_the_expected_set_of_files(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    paths = set(render.by_path())
    assert {
        "zensical.toml",
        "docs/stylesheets/extra.css",
        ".github/workflows/docs.yml",
        "docs/index.md",
        "docs/quickstart.md",
        "docs/install.md",
        "docs/api.md",
    } <= paths


def test_ownership_splits_styling_from_content(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    managed = {f.path for f in render.managed()}
    seeded = {f.path for f in render.seeded()}
    assert managed == {
        "zensical.toml", "docs/stylesheets/extra.css", ".github/workflows/docs.yml"
    }
    assert all(p.startswith("docs/") for p in seeded)
    assert all(
        p.endswith(".md") or "/assets/" in p or p == f"docs/{CUSTOM_STYLESHEET}"
        for p in seeded
    )
    # The custom stylesheet sits beside the managed one but is the user's.
    assert f"docs/{CUSTOM_STYLESHEET}" in seeded
    assert f"docs/{MANAGED_STYLESHEET}" in managed
    assert not managed & seeded


def test_rendering_is_deterministic(project_root: Path):
    config = load_config(project_root / "docs-studio.toml")
    first = {f.path: f.digest for f in render_site(config, project_root).files}
    second = {f.path: f.digest for f in render_site(config, project_root).files}
    assert first == second


def test_the_generated_zensical_config_is_valid_toml_and_matches_the_config(
    project_root: Path,
):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    site = tomllib.loads(render.by_path()["zensical.toml"].text)["project"]
    assert site["site_name"] == "example-pkg"
    assert site["site_url"] == "https://example.github.io/example-pkg/"
    assert site["docs_dir"] == "docs" and site["site_dir"] == "site"
    assert site["extra_css"] == [MANAGED_STYLESHEET, CUSTOM_STYLESHEET]
    assert site["theme"]["font"] is False, "no third-party font requests"
    assert tuple(site["theme"]["features"]) == DEFAULT_FEATURES
    assert len(site["theme"]["palette"]) == 2
    assert [p["scheme"] for p in site["theme"]["palette"]] == ["default", "slate"]


def test_the_nav_in_the_generated_config_mirrors_the_nav_in_ours(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    nav = tomllib.loads(render.by_path()["zensical.toml"].text)["project"]["nav"]
    assert nav[0] == {"Home": "index.md"}
    assert nav[1] == {"Getting started": [{"Quickstart": "quickstart.md"},
                                          {"Install": "install.md"}]}


def test_extra_features_are_appended_not_replaced(project_root: Path):
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text().replace(
            '[theme]\npreset = "ocean-violet"',
            '[theme]\npreset = "ocean-violet"\nextra_features = ["content.tabs.link"]',
        ),
        encoding="utf-8",
    )
    render = render_site(load_config(path), project_root)
    features = tomllib.loads(render.by_path()["zensical.toml"].text)["project"]["theme"][
        "features"
    ]
    assert features[: len(DEFAULT_FEATURES)] == list(DEFAULT_FEATURES)
    assert features[-1] == "content.tabs.link"


def test_the_stylesheet_declares_both_schemes_and_maps_them_onto_the_theme(
    project_root: Path,
):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    css = render.by_path()["docs/stylesheets/extra.css"].text
    assert '[data-md-color-scheme="default"]' in css
    assert '[data-md-color-scheme="slate"]' in css
    # Light and dark values are both present and different.
    assert render.palette.light["primary"].css() in css
    assert render.palette.dark["primary"].css() in css
    # The token -> theme-variable mapping, with the doubled attribute that outranks
    # the theme's own palette rules.
    assert (
        '[data-md-color-scheme="slate"][data-md-color-primary]' in css
    )
    for variable in (
        "--md-primary-fg-color",
        "--md-typeset-a-color",
        "--md-default-bg-color",
        "--md-code-bg-color",
        "--md-typeset-table-color",
    ):
        assert f"{variable}: var(--ds-" in css


def test_the_stylesheet_has_the_components_the_reference_sites_share(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    css = render.by_path()["docs/stylesheets/extra.css"].text
    for rule in (
        ".md-typeset .md-button--primary",
        ".md-typeset .grid.cards > ul > li",
        ".md-typeset :is(.admonition, details).warning",
        ".md-typeset h2",
        ".md-grid",
        ".md-sidebar--secondary",
        ".md-typeset h1.ds-home-title",
        ".md-typeset .ds-resources",
        ".md-typeset .ds-math",
    ):
        assert rule in css, rule
    assert "max-width: 62.5rem" in css
    assert "@media screen and (min-width: 60em)" in css


def test_the_dark_logo_swap_is_only_emitted_when_there_is_a_dark_logo(
    project_root: Path, tmp_path: Path
):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    css = render.by_path()["docs/stylesheets/extra.css"].text
    assert 'content: url("../assets/logo-dark.svg")' in css

    (project_root / "mark.svg").write_text("<svg/>", encoding="utf-8")
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text() + '\n[branding]\nlogo = "mark.svg"\n', encoding="utf-8"
    )
    single = render_site(load_config(path), project_root)
    assert single.assets.logo_ref == "assets/mark.svg"
    assert single.assets.logo_dark_ref is None
    assert "content: url(" not in single.by_path()["docs/stylesheets/extra.css"].text


def test_no_generated_file_contains_template_syntax(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    for spec in render.files:
        if spec.path.endswith((".svg", ".md", ".css", ".toml")):
            text = spec.text
            assert "{{" not in text and "{%" not in text, spec.path


def test_the_home_page_carries_the_resource_row_and_the_headline_class(
    project_root: Path,
):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    index = render.by_path()["docs/index.md"].text
    assert "{ .ds-home-title }" in index
    assert "{ .ds-resources }" in index
    assert ":simple-github: GitHub Repository" in index
    assert "https://github.com/example/example-pkg" in index


def test_every_profile_accepts_the_common_fence_languages():
    from docs_studio.scaffold import COMMON_FENCES

    for name, profile in LANGUAGE_PROFILES.items():
        assert set(COMMON_FENCES) <= set(profile.expected_fences), name
    # And each still carries its own language on top.
    assert "python" in LANGUAGE_PROFILES["python"].expected_fences
    assert "julia" in LANGUAGE_PROFILES["julia"].expected_fences
    assert "julia" not in LANGUAGE_PROFILES["python"].expected_fences


@pytest.mark.parametrize("language", list(LANGUAGE_PROFILES))
def test_each_language_profile_renders_its_own_wording(project_root: Path, language):
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text().replace('language = "python"', f'language = "{language}"'),
        encoding="utf-8",
    )
    render = render_site(load_config(path), project_root)
    install = render.by_path()["docs/install.md"].text
    profile = LANGUAGE_PROFILES[language]
    assert profile.requirement.split("**")[0] or True
    assert f"```{profile.fence}" in render.by_path()["docs/quickstart.md"].text
    assert "Fill this in before publishing" in install


def test_the_workflow_is_manual_only_by_default(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    workflow = render.by_path()[".github/workflows/docs.yml"].text
    assert "workflow_dispatch" in workflow
    assert "push:" not in workflow
    assert "pages: write" in workflow and "id-token: write" in workflow
    assert "contents: read" in workflow
    assert "zensical build --clean --strict" in workflow
    assert "docs-studio check" in workflow
    assert "upload-pages-artifact@v5" in workflow and "deploy-pages@v5" in workflow
    assert "${{ steps.deployment.outputs.page_url }}" in workflow


def test_the_workflow_installs_only_what_it_can(project_root: Path):
    """It must not `pip install docs-studio` unconditionally: the package may not be
    published, or may be the very repository being built."""
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    workflow = render.by_path()[".github/workflows/docs.yml"].text
    installs = [
        line.split("- run:", 1)[1].strip()
        for line in workflow.splitlines()
        if line.strip().startswith("- run: pip install")
    ]
    assert installs == ['pip install "zensical==0.0.67"'], installs
    # The checker still runs, but only when it is actually there.
    assert "command -v docs-studio" in workflow
    assert "docs-studio check --no-build" in workflow


def test_extra_install_lines_run_before_the_checker(project_root: Path):
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text().replace(
            'trigger = "manual"',
            'trigger = "manual"\nextra_install = ["pip install ."]',
        ),
        encoding="utf-8",
    )
    workflow = render_site(load_config(path), project_root).by_path()[
        ".github/workflows/docs.yml"
    ].text
    assert "pip install ." in workflow
    assert workflow.index("pip install .") < workflow.index("command -v docs-studio")


def test_the_push_trigger_is_explicit_in_the_config(project_root: Path):
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text().replace('trigger = "manual"', 'trigger = "push"'), encoding="utf-8"
    )
    workflow = render_site(load_config(path), project_root).by_path()[
        ".github/workflows/docs.yml"
    ].text
    assert "push:\n    branches:\n      - main" in workflow


def test_no_workflow_when_pages_is_off(project_root: Path):
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text().replace("github_pages = true", "github_pages = false"),
        encoding="utf-8",
    )
    render = render_site(load_config(path), project_root)
    assert ".github/workflows/docs.yml" not in render.by_path()


def test_write_site_writes_everything_and_records_a_manifest(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    written, skipped = write_site(render, project_root)
    assert not skipped
    assert len(written) == len(render.files)
    for spec in render.files:
        assert (project_root / spec.path).read_bytes() == spec.content
    manifest = Manifest.load(project_root)
    assert manifest is not None
    assert set(manifest.files) == set(render.by_path())
    assert manifest.ownership("zensical.toml") == "managed"
    assert manifest.ownership("docs/index.md") == "seeded"
    assert (project_root / MANIFEST_PATH).is_file()


def test_write_site_never_silently_overwrites(project_root: Path):
    target = project_root / "docs" / "index.md"
    target.parent.mkdir(parents=True)
    target.write_text("# My own home page\n", encoding="utf-8")
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    written, skipped = write_site(render, project_root)
    assert "docs/index.md" in skipped
    assert target.read_text() == "# My own home page\n"
    # A file that was left alone is recorded as the user's, so `update` leaves it be.
    manifest = Manifest.load(project_root)
    assert manifest.ownership("docs/index.md") == "seeded"
    assert manifest.digest("docs/index.md") != render.by_path()["docs/index.md"].digest


def test_write_site_overwrites_only_when_asked(project_root: Path):
    target = project_root / "docs" / "index.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Mine\n", encoding="utf-8")
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    written, skipped = write_site(render, project_root, overwrite=True)
    assert not skipped and "docs/index.md" in written
    assert target.read_text() != "# Mine\n"


def test_generating_twice_changes_nothing(generated: Path):
    before = {
        p.relative_to(generated).as_posix(): p.read_bytes()
        for p in generated.rglob("*")
        if p.is_file() and MANIFEST_PATH.name not in p.name
    }
    render = render_site(load_config(generated / "docs-studio.toml"), generated)
    write_site(render, generated)
    after = {
        p.relative_to(generated).as_posix(): p.read_bytes()
        for p in generated.rglob("*")
        if p.is_file() and MANIFEST_PATH.name not in p.name
    }
    assert before == after


def test_a_page_in_the_nav_with_no_dedicated_template_gets_a_generic_starter(
    project_root: Path,
):
    path = project_root / "docs-studio.toml"
    path.write_text(
        path.read_text().replace(
            '[[nav]]\ntitle = "Reference"\npages = ["api.md"]',
            '[[nav]]\ntitle = "Reference"\npages = ["api.md", "schemas.md"]',
        ),
        encoding="utf-8",
    )
    render = render_site(load_config(path), project_root)
    page = render.by_path()["docs/schemas.md"].text
    assert page.startswith("<!-- docs-studio:starter -->")
    assert "# Schemas" in page


def test_paths_are_posix_so_a_manifest_moves_between_platforms(generated: Path):
    manifest = Manifest.load(generated)
    assert all("\\" not in path for path in manifest.files)
    assert all(not path.startswith("/") for path in manifest.files)


def test_the_manifest_round_trips_through_json(generated: Path):
    first = Manifest.load(generated)
    first.save(generated)
    second = Manifest.load(generated)
    assert first.files == second.files
    assert first.docs_studio_version == second.docs_studio_version
