"""Logo handling and the generated monogram."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from docs_studio.assets import (
    FAVICON_NAME,
    LOGO_DARK_NAME,
    LOGO_NAME,
    favicon_svg,
    initials,
    monogram_svg,
    plan_assets,
)
from docs_studio.config import StudioProject
from docs_studio.theme import load_preset

BASE = {
    "project": {
        "name": "example-pkg",
        "description": "An example package",
        "author": "Example Lab",
        "site_url": "https://example.github.io/example-pkg/",
    }
}
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("wm-physics-eval", "WP"),
        ("ARIS.jl", "AJ"),
        ("scikit-learn", "SL"),
        ("numpy", "NU"),
        ("CamelCase", "CC"),
        ("x", "X"),
        ("", "DS"),
        ("---", "DS"),
    ],
)
def test_initials(name, expected):
    assert initials(name) == expected


def test_the_monogram_is_a_square_svg_that_cannot_distort_or_crop():
    svg = monogram_svg("AJ", load_preset("indigo-lavender").light)
    assert svg.startswith("<svg")
    assert 'viewBox="0 0 96 96"' in svg
    # No intrinsic width/height and no preserveAspectRatio override: the theme scales
    # it by height and the default xMidYMid meet keeps it whole.
    assert "preserveAspectRatio" not in svg
    assert not re.search(r"<svg[^>]*\swidth=", svg)
    assert "AJ" in svg and 'role="img"' in svg


def test_the_monogram_uses_the_palette_it_is_given():
    palette = load_preset("indigo-lavender")
    light = monogram_svg("AJ", palette.light)
    dark = monogram_svg("AJ", palette.dark)
    assert palette.light["primary"].css() in light
    assert palette.dark["primary"].css() in dark
    assert light != dark


def test_the_monogram_is_deterministic():
    scheme = load_preset("neutral").light
    assert monogram_svg("AB", scheme) == monogram_svg("AB", scheme)


def test_the_favicon_drops_what_does_not_survive_at_16px():
    scheme = load_preset("neutral").light
    assert "clip-path" not in favicon_svg("AB", scheme)
    assert "circle" not in favicon_svg("AB", scheme)


def test_with_no_logo_a_monogram_is_planned_for_both_schemes(tmp_path: Path):
    config = StudioProject.model_validate(BASE)
    plan = plan_assets(config, tmp_path, load_preset("neutral"))
    assert plan.logo_ref == f"assets/{LOGO_NAME}"
    assert plan.logo_dark_ref == f"assets/{LOGO_DARK_NAME}"
    assert plan.favicon_ref == f"assets/{FAVICON_NAME}"
    assert not plan.copies
    assert set(plan.generated) == {
        f"assets/{LOGO_NAME}", f"assets/{LOGO_DARK_NAME}", f"assets/{FAVICON_NAME}"
    }


def test_monogram_text_overrides_the_initials(tmp_path: Path):
    config = StudioProject.model_validate({**BASE, "branding": {"monogram_text": "ZZ"}})
    plan = plan_assets(config, tmp_path, load_preset("neutral"))
    assert ">ZZ<" in plan.generated[f"assets/{LOGO_NAME}"]


def test_a_supplied_logo_is_copied_byte_for_byte(tmp_path: Path):
    source = tmp_path / "art" / "mark.png"
    source.parent.mkdir()
    payload = PNG_HEADER + b"transparent pixels and an ICC profile"
    source.write_bytes(payload)
    config = StudioProject.model_validate({**BASE, "branding": {"logo": "art/mark.png"}})
    plan = plan_assets(config, tmp_path, load_preset("neutral"))
    assert plan.logo_ref == "assets/mark.png"
    assert plan.copies["assets/mark.png"].read_bytes() == payload
    # No monogram is generated when the project has its own mark.
    assert f"assets/{LOGO_NAME}" not in plan.generated


def test_a_supplied_favicon_suppresses_the_generated_one(tmp_path: Path):
    (tmp_path / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    config = StudioProject.model_validate({**BASE, "branding": {"favicon": "favicon.ico"}})
    plan = plan_assets(config, tmp_path, load_preset("neutral"))
    assert plan.favicon_ref == "assets/favicon.ico"
    assert f"assets/{FAVICON_NAME}" not in plan.generated


def test_all_four_branding_slots_are_carried_through(tmp_path: Path):
    for name in ("logo.svg", "logo-dark.svg", "wordmark.svg", "favicon.ico"):
        (tmp_path / name).write_bytes(b"<svg/>")
    config = StudioProject.model_validate(
        {
            **BASE,
            "branding": {
                "logo": "logo.svg",
                "logo_dark": "logo-dark.svg",
                "wordmark": "wordmark.svg",
                "favicon": "favicon.ico",
            },
        }
    )
    plan = plan_assets(config, tmp_path, load_preset("neutral"))
    assert plan.wordmark_ref == "assets/wordmark.svg"
    assert plan.logo_dark_ref == "assets/logo-dark.svg"
    assert len(plan.copies) == 4
    assert not plan.generated


def test_a_branding_path_that_does_not_exist_names_the_setting(tmp_path: Path):
    config = StudioProject.model_validate({**BASE, "branding": {"logo": "missing.svg"}})
    with pytest.raises(FileNotFoundError) as exc:
        plan_assets(config, tmp_path, load_preset("neutral"))
    assert "branding.logo" in str(exc.value)
