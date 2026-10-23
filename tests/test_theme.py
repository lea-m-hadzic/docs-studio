"""Colour parsing, contrast arithmetic, and the bundled presets."""

from __future__ import annotations

import pytest

from docs_studio.theme import (
    CONTRAST_PAIRS,
    Color,
    ColorError,
    Palette,
    Scheme,
    adjust_for_contrast,
    check_contrast,
    contrast_failures,
    contrast_ratio,
    load_preset,
    preset_names,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("#fff", (255, 255, 255, 1.0)),
        ("#000000", (0, 0, 0, 1.0)),
        ("#6254B8", (98, 84, 184, 1.0)),
        ("#ffffff1a", (255, 255, 255, 0.1020)),
        ("rgba(255, 255, 255, 0.1)", (255, 255, 255, 0.1)),
        ("rgb(1, 2, 3)", (1, 2, 3, 1.0)),
        ("  #abc  ", (170, 187, 204, 1.0)),
    ],
)
def test_parses_every_supported_form(text, expected):
    color = Color.parse(text)
    assert (color.r, color.g, color.b, pytest.approx(color.a, abs=1e-3)) == expected


@pytest.mark.parametrize("text", ["", "#12345", "blue", "rgba(300, 0, 0, 1)", "#gggggg"])
def test_rejects_what_it_cannot_parse(text):
    with pytest.raises(ColorError):
        Color.parse(text)


def test_round_trips_through_css():
    assert Color.parse("#6254B8").css() == "#6254b8"
    assert Color.parse("rgba(255, 255, 255, 0.1)").css() == "rgba(255, 255, 255, 0.1)"


def test_known_contrast_ratios():
    # The two anchors of the WCAG scale.
    assert contrast_ratio(Color.parse("#000"), Color.parse("#fff")) == pytest.approx(21.0, abs=0.01)
    assert contrast_ratio(Color.parse("#fff"), Color.parse("#fff")) == pytest.approx(1.0, abs=0.01)


def test_translucent_foreground_is_composited_before_measuring():
    faint = Color.parse("rgba(0, 0, 0, 0.1)")
    assert contrast_ratio(faint, Color.parse("#fff")) < 1.5


def test_adjust_for_contrast_fixes_the_coral_case():
    """ARIS's coral is 2.7:1 on white; the guard darkens it until it is readable."""
    coral, white = Color.parse("#F0787F"), Color.parse("#ffffff")
    assert contrast_ratio(coral, white) < 4.5
    fixed = adjust_for_contrast(coral, white)
    assert contrast_ratio(fixed, white) >= 4.5
    assert fixed.luminance() < coral.luminance()


def test_adjust_for_contrast_lightens_on_a_dark_background():
    dark = Color.parse("#14121f")
    fixed = adjust_for_contrast(Color.parse("#3a3560"), dark)
    assert contrast_ratio(fixed, dark) >= 4.5
    assert fixed.luminance() > Color.parse("#3a3560").luminance()


def test_adjust_for_contrast_leaves_a_passing_colour_alone():
    white = Color.parse("#ffffff")
    assert adjust_for_contrast(Color.parse("#222222"), white) == Color.parse("#222222")


def test_every_preset_loads_and_passes_contrast_in_both_schemes():
    assert set(preset_names()) == {"indigo-lavender", "neutral", "ocean-violet"}
    for name in preset_names():
        palette = load_preset(name)
        failures = contrast_failures(palette)
        assert not failures, f"{name}: " + "; ".join(f.describe() for f in failures)
        assert len(check_contrast(palette)) == 2 * len(CONTRAST_PAIRS)


def test_unknown_preset_names_itself_and_the_alternatives():
    with pytest.raises(KeyError) as exc:
        load_preset("burgundy")
    assert "burgundy" in str(exc.value) and "neutral" in str(exc.value)


def test_derived_tokens_are_filled_in():
    scheme = Scheme.build(
        "light",
        {
            "primary": "#4B5FD7",
            "primary_hover": "#3949AB",
            "on_primary": "#ffffff",
            "secondary": "#2A3A8F",
            "accent": "#F0787F",
            "fg": "#20242a",
            "fg_body": "#2f3440",
            "muted": "#5d6676",
            "border": "#e3e6ea",
            "bg": "#ffffff",
            "surface": "#ffffff",
            "surface_alt": "#f3f5f7",
        },
    )
    assert scheme["link"] == scheme["primary"]
    assert scheme["link_hover"] == scheme["primary_hover"]
    assert scheme["bg_translucent"].a == pytest.approx(0.7)
    assert contrast_ratio(scheme["accent_text"], scheme["bg"]) >= 4.5


def test_a_missing_required_token_is_named():
    with pytest.raises(ColorError) as exc:
        Scheme.build("light", {"primary": "#000"})
    assert "missing required token" in str(exc.value)
    assert "surface_alt" in str(exc.value)


def test_an_unknown_token_is_rejected_rather_than_ignored():
    base = {t: "#808080" for t in (
        "primary", "primary_hover", "on_primary", "secondary", "accent",
        "fg", "fg_body", "muted", "border", "bg", "surface", "surface_alt",
    )}
    with pytest.raises(ColorError) as exc:
        Scheme.build("light", {**base, "primry": "#000"})
    assert "primry" in str(exc.value)


def test_a_custom_palette_that_fails_contrast_is_reported_not_silently_accepted():
    unreadable = {t: "#f2f2f2" for t in (
        "primary", "primary_hover", "on_primary", "secondary", "accent",
        "fg", "fg_body", "muted", "border", "bg", "surface", "surface_alt",
    )}
    palette = Palette.from_mapping("bad", {"light": unreadable, "dark": unreadable})
    failures = contrast_failures(palette)
    assert failures
    assert {f.scheme for f in failures} == {"light", "dark"}
