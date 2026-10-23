"""`docs-studio.toml` validation: what it accepts, and what it says when it refuses."""

from __future__ import annotations

from pathlib import Path

import pytest

from docs_studio.config import (
    CONFIG_FILENAME,
    ConfigError,
    NavEntry,
    ProjectConfig,
    StudioProject,
    load_config,
    titleize,
)

BASE = {
    "project": {
        "name": "example-pkg",
        "description": "An example package",
        "author": "Example Lab",
        "site_url": "https://example.github.io/example-pkg/",
    }
}


def test_a_minimal_config_validates_with_sensible_defaults():
    project = StudioProject.model_validate(BASE)
    assert project.project.slug == "example-pkg"
    assert project.project.language == "generic"
    assert project.theme.preset == "neutral"
    assert project.deploy.github_pages is True
    assert project.deploy.trigger == "manual"


def test_a_trailing_slash_is_added_to_the_site_url():
    assert ProjectConfig(**{**BASE["project"], "site_url": "https://a.github.io/b"}).site_url == (
        "https://a.github.io/b/"
    )


def test_a_relative_site_url_is_refused():
    with pytest.raises(Exception) as exc:
        ProjectConfig(**{**BASE["project"], "site_url": "example.github.io/b"})
    assert "site_url" in str(exc.value)


@pytest.mark.parametrize(
    "site_url, expected",
    [
        ("https://sisl.github.io/ARIS.jl/", "/ARIS.jl/"),
        ("https://sisl.github.io/wm-physics-eval/", "/wm-physics-eval/"),
        ("https://example.github.io/", "/"),
        ("https://docs.example.org/", "/"),
        ("https://example.github.io/a/b/", "/a/b/"),
    ],
)
def test_the_pages_sub_path_is_derived_from_the_site_url(site_url, expected):
    assert ProjectConfig(**{**BASE["project"], "site_url": site_url}).pages_base_path == expected


def test_a_slug_is_derived_from_the_name_when_absent():
    assert ProjectConfig(**{**BASE["project"], "name": "ARIS.jl"}).slug == "aris.jl"
    assert ProjectConfig(**{**BASE["project"], "name": "My Great Project"}).slug == (
        "my-great-project"
    )


def test_an_unknown_key_is_an_error_rather_than_a_silent_no_op(tmp_path: Path):
    path = tmp_path / CONFIG_FILENAME
    path.write_text(
        """
[project]
name = "x"
description = "y"
author = "z"
site_url = "https://a.github.io/b/"
colour_scheme = "dark"
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "colour_scheme" in str(exc.value)


def test_an_unknown_language_profile_is_refused():
    with pytest.raises(Exception):
        StudioProject.model_validate(
            {"project": {**BASE["project"], "language": "fortran"}}
        )


def test_a_nav_entry_needs_exactly_one_of_page_or_pages():
    with pytest.raises(Exception):
        NavEntry(title="Home")
    with pytest.raises(Exception):
        NavEntry(title="Home", page="index.md", pages=["a.md"])


def test_a_nav_page_must_be_a_markdown_file_inside_docs():
    with pytest.raises(Exception):
        NavEntry(title="Home", page="index.html")
    with pytest.raises(Exception):
        NavEntry(title="Home", page="../secrets.md")
    with pytest.raises(Exception):
        NavEntry(title="Home", page="/etc/passwd.md")


def test_a_duplicated_nav_page_is_refused_and_both_sections_are_named():
    with pytest.raises(Exception) as exc:
        StudioProject.model_validate(
            {
                **BASE,
                "nav": [
                    {"title": "Home", "page": "index.md"},
                    {"title": "Guide", "pages": ["usage.md"]},
                    {"title": "Extra", "pages": ["usage.md"]},
                ],
            }
        )
    assert "usage.md" in str(exc.value)
    assert "Guide" in str(exc.value) and "Extra" in str(exc.value)


def test_a_nav_without_the_home_page_is_refused():
    with pytest.raises(Exception) as exc:
        StudioProject.model_validate(
            {**BASE, "nav": [{"title": "Guide", "pages": ["usage.md"]}]}
        )
    assert "index.md" in str(exc.value)


def test_nav_labels_come_from_the_entry_or_from_the_filename():
    entry = NavEntry(
        title="Guide",
        pages=["multiple-thresholds.md", {"title": "Installing it", "page": "install.md"}],
    )
    assert entry.labelled_pages == [
        ("Multiple thresholds", "multiple-thresholds.md"),
        ("Installing it", "install.md"),
    ]


@pytest.mark.parametrize(
    "page, label",
    [
        ("index.md", "Index"),
        ("multiple-thresholds.md", "Multiple thresholds"),
        ("expected_spec.md", "Expected spec"),
        ("api.md", "Api"),
    ],
)
def test_titleize(page, label):
    assert titleize(page) == label


def test_a_resource_takes_an_icon_or_an_image_but_not_both():
    from docs_studio.config import ResourceLink

    ResourceLink(label="GitHub", url="https://github.com/a/b", icon="simple-github")
    ResourceLink(label="Data", url="https://example.org", image="assets/logo.svg")
    with pytest.raises(Exception):
        ResourceLink(
            label="Both", url="https://example.org", icon="simple-github", image="assets/l.svg"
        )


def test_a_relative_resource_url_is_refused():
    from docs_studio.config import ResourceLink

    with pytest.raises(Exception):
        ResourceLink(label="Docs", url="quickstart.md")


def test_a_dark_logo_without_a_light_one_is_refused():
    from docs_studio.config import BrandingConfig

    BrandingConfig(logo="docs/assets/a.svg", logo_dark="docs/assets/b.svg")
    with pytest.raises(Exception):
        BrandingConfig(logo_dark="docs/assets/b.svg")


def test_an_unsupported_image_format_is_refused():
    from docs_studio.config import BrandingConfig

    with pytest.raises(Exception) as exc:
        BrandingConfig(logo="docs/assets/logo.pdf")
    assert ".svg" in str(exc.value)


def test_the_zensical_version_must_be_pinned_exactly():
    from docs_studio.config import DeployConfig

    DeployConfig(zensical_version="0.0.67")
    for loose in (">=0.0.67", "0.0", "latest"):
        with pytest.raises(Exception):
            DeployConfig(zensical_version=loose)


def test_theme_overrides_are_layered_on_the_preset(tmp_path: Path):
    project = StudioProject.model_validate(
        {
            **BASE,
            "theme": {"preset": "ocean-violet", "light": {"primary": "#123456"}},
        }
    )
    palette = project.palette(tmp_path)
    assert palette.light["primary"].css() == "#123456"
    # Untouched tokens still come from the preset.
    assert palette.light["surface_alt"].css() == "#f3f5f7"
    assert palette.dark["primary"].css() == "#7e8fff"


def test_a_custom_palette_file_is_loaded(tmp_path: Path):
    tokens = "\n".join(
        f'{t} = "#808080"'
        for t in (
            "primary", "primary_hover", "on_primary", "secondary", "accent",
            "fg", "fg_body", "muted", "border", "bg", "surface", "surface_alt",
        )
    )
    (tmp_path / "pal.toml").write_text(
        f'title = "Mine"\n\n[light]\n{tokens}\n\n[dark]\n{tokens}\n', encoding="utf-8"
    )
    project = StudioProject.model_validate(
        {**BASE, "theme": {"palette_file": "pal.toml"}}
    )
    assert project.palette(tmp_path).title == "Mine"


def test_a_missing_palette_file_is_reported_with_its_path(tmp_path: Path):
    project = StudioProject.model_validate(
        {**BASE, "theme": {"palette_file": "nope.toml"}}
    )
    with pytest.raises(ConfigError) as exc:
        project.palette(tmp_path)
    assert "nope.toml" in str(exc.value)


def test_a_missing_config_file_says_where_it_looked(tmp_path: Path):
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path / CONFIG_FILENAME)
    assert str(tmp_path) in str(exc.value)


def test_invalid_toml_is_reported_as_such(tmp_path: Path):
    path = tmp_path / CONFIG_FILENAME
    path.write_text("[project\nname = 1", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "not valid TOML" in str(exc.value)


def test_every_validation_error_is_listed_not_just_the_first(tmp_path: Path):
    path = tmp_path / CONFIG_FILENAME
    path.write_text('[project]\nname = "x"\n', encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(path)
    message = str(exc.value)
    assert "description" in message and "author" in message and "site_url" in message
