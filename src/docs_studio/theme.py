"""Design tokens, palette presets and contrast validation.

The two reference sites (wm-physics-eval, ARIS.jl) each carried their own `--wm-*` /
`--aris-*` token block and then mapped it onto the Zensical theme's own `--md-*`
variables. The token *names* were the same in both; only the values differed. This
module is that shared vocabulary, named semantically and validated.

A :class:`Scheme` is one colour mode. A :class:`Palette` is the light/dark pair plus
the Material colour names Zensical uses for its own palette entries. Presets ship as
TOML next to this module; users can supply a full custom palette instead.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Iterator, Literal

# --------------------------------------------------------------------------- colour

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGBA = re.compile(
    r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*"
    r"(?:,\s*(0|1|0?\.\d+)\s*)?\)$"
)


class ColorError(ValueError):
    """A colour string that is not one of the supported forms."""


@dataclass(frozen=True, slots=True)
class Color:
    """An sRGB colour with straight alpha.

    Accepts `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa`, `rgb(...)` and `rgba(...)`.
    Renders back as `#rrggbb` when opaque and as `rgba(...)` otherwise, which is the
    form both reference stylesheets used for their translucent borders and tints.
    """

    r: int
    g: int
    b: int
    a: float = 1.0

    @classmethod
    def parse(cls, value: str | Color) -> Color:
        if isinstance(value, Color):
            return value
        text = value.strip()
        if _HEX.match(text):
            digits = text[1:]
            if len(digits) in (3, 4):
                digits = "".join(c * 2 for c in digits)
            r, g, b = (int(digits[i : i + 2], 16) for i in (0, 2, 4))
            a = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
            return cls(r, g, b, round(a, 4))
        m = _RGBA.match(text)
        if m:
            r, g, b = (int(m.group(i)) for i in (1, 2, 3))
            if max(r, g, b) > 255:
                raise ColorError(f"channel out of range in {value!r}")
            return cls(r, g, b, float(m.group(4)) if m.group(4) is not None else 1.0)
        raise ColorError(
            f"{value!r} is not a colour: use #rgb, #rrggbb, #rrggbbaa or rgba(r, g, b, a)"
        )

    def css(self) -> str:
        if self.a >= 1.0:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        alpha = f"{self.a:.4f}".rstrip("0").rstrip(".")
        return f"rgba({self.r}, {self.g}, {self.b}, {alpha})"

    def with_alpha(self, alpha: float) -> Color:
        return Color(self.r, self.g, self.b, round(alpha, 4))

    def over(self, backdrop: Color) -> Color:
        """Composite this colour over an opaque backdrop (source-over)."""
        if self.a >= 1.0:
            return self
        base = backdrop.flatten()
        mix = lambda s, d: round(s * self.a + d * (1 - self.a))  # noqa: E731
        return Color(mix(self.r, base.r), mix(self.g, base.g), mix(self.b, base.b))

    def flatten(self) -> Color:
        """The colour as if composited over white — the fallback backdrop."""
        return self if self.a >= 1.0 else self.over(Color(255, 255, 255))

    def luminance(self) -> float:
        """WCAG 2.1 relative luminance. Alpha is ignored; composite first."""

        def channel(v: int) -> float:
            s = v / 255
            return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

        return (
            0.2126 * channel(self.r)
            + 0.7152 * channel(self.g)
            + 0.0722 * channel(self.b)
        )

    def mix(self, other: Color, amount: float) -> Color:
        """Move `amount` of the way from this colour toward `other`.

        Mixing rather than multiplying each channel matters for the contrast guard: a
        dark saturated colour cannot be scaled bright enough to be readable on a dark
        background, but mixing it toward white always converges.
        """
        blend = lambda s, d: round(s + (d - s) * amount)  # noqa: E731
        return Color(
            blend(self.r, other.r), blend(self.g, other.g), blend(self.b, other.b), self.a
        )


def contrast_ratio(fg: Color, bg: Color) -> float:
    """WCAG 2.1 contrast ratio, compositing a translucent foreground over `bg`."""
    front, back = fg.over(bg).luminance(), bg.flatten().luminance()
    lighter, darker = max(front, back), min(front, back)
    return (lighter + 0.05) / (darker + 0.05)


def adjust_for_contrast(color: Color, bg: Color, target: float = 4.5) -> Color:
    """Darken or lighten `color` just enough to clear `target` against `bg`.

    This is the guard the ARIS site applied by hand: its coral `#F0787F` is only
    2.7:1 on white, so a darkened `#C73C44` carries any coral-coloured *text*. Here it
    is mechanical, so a user-supplied accent cannot silently ship unreadable text.
    """
    if contrast_ratio(color, bg) >= target:
        return color
    toward = (
        Color(0, 0, 0) if bg.flatten().luminance() > 0.5 else Color(255, 255, 255)
    )
    best = color
    for step in range(1, 101):
        candidate = color.mix(toward, step / 100)
        best = candidate
        if contrast_ratio(candidate, bg) >= target:
            return candidate
    return best


# --------------------------------------------------------------------------- tokens

SchemeName = Literal["light", "dark"]

#: Tokens a scheme must define. Everything else is derived.
REQUIRED_TOKENS: tuple[str, ...] = (
    "primary",
    "primary_hover",
    "on_primary",
    "secondary",
    "accent",
    "fg",
    "fg_body",
    "muted",
    "border",
    "bg",
    "surface",
    "surface_alt",
)

#: Tokens that are filled in when absent. `accent_text` is contrast-corrected from
#: `accent`; the tints and the translucent background follow the reference alphas.
DERIVED_TOKENS: tuple[str, ...] = (
    "primary_tint",
    "accent_text",
    "accent_tint",
    "bg_translucent",
    "link",
    "link_hover",
)

ALL_TOKENS: tuple[str, ...] = REQUIRED_TOKENS + DERIVED_TOKENS


@dataclass(frozen=True, slots=True)
class Scheme:
    """One colour mode's complete token set, with every derived token resolved."""

    name: SchemeName
    tokens: dict[str, Color]

    def __getitem__(self, token: str) -> Color:
        return self.tokens[token]

    @property
    def is_dark(self) -> bool:
        return self.name == "dark"

    @classmethod
    def build(cls, name: SchemeName, raw: dict[str, str | Color]) -> Scheme:
        missing = [t for t in REQUIRED_TOKENS if t not in raw]
        if missing:
            raise ColorError(
                f"{name} scheme is missing required token(s): {', '.join(missing)}"
            )
        unknown = [t for t in raw if t not in ALL_TOKENS]
        if unknown:
            raise ColorError(
                f"{name} scheme has unknown token(s): {', '.join(sorted(unknown))}"
            )
        tok = {k: Color.parse(v) for k, v in raw.items()}
        dark = name == "dark"
        tok.setdefault(
            "primary_tint",
            tok["primary"].with_alpha(0.14) if dark else tok["primary"].with_alpha(0.08),
        )
        tok.setdefault("accent_text", adjust_for_contrast(tok["accent"], tok["bg"]))
        tok.setdefault("accent_tint", tok["accent"].with_alpha(0.12 if dark else 0.10))
        tok.setdefault("bg_translucent", tok["bg"].with_alpha(0.7))
        tok.setdefault("link", tok["primary"])
        tok.setdefault("link_hover", tok["primary_hover"])
        return cls(name=name, tokens=tok)

    def css_values(self) -> dict[str, str]:
        """Token name (kebab-cased) to CSS value, in declaration order."""
        return {t.replace("_", "-"): self.tokens[t].css() for t in ALL_TOKENS}


@dataclass(frozen=True, slots=True)
class Palette:
    """A light/dark token pair plus the Material colour names Zensical itself uses."""

    name: str
    title: str
    description: str
    md_primary: str
    md_primary_dark: str
    md_accent: str
    light: Scheme
    dark: Scheme

    def schemes(self) -> Iterator[Scheme]:
        yield self.light
        yield self.dark

    @classmethod
    def from_mapping(cls, name: str, data: dict) -> Palette:
        for key in ("light", "dark"):
            if not isinstance(data.get(key), dict):
                raise ColorError(f"palette {name!r} has no [{key}] table")
        return cls(
            name=name,
            title=str(data.get("title", name)),
            description=str(data.get("description", "")),
            md_primary=str(data.get("md_primary", "white")),
            md_primary_dark=str(data.get("md_primary_dark", "black")),
            md_accent=str(data.get("md_accent", "indigo")),
            light=Scheme.build("light", data["light"]),
            dark=Scheme.build("dark", data["dark"]),
        )


# -------------------------------------------------------------------------- presets


@lru_cache(maxsize=1)
def preset_names() -> tuple[str, ...]:
    root = resources.files("docs_studio") / "presets"
    return tuple(sorted(p.name[:-5] for p in root.iterdir() if p.name.endswith(".toml")))


def load_preset(name: str) -> Palette:
    """Load a bundled preset by name."""
    if name not in preset_names():
        raise KeyError(
            f"unknown palette preset {name!r}; available: {', '.join(preset_names())}"
        )
    text = (resources.files("docs_studio") / "presets" / f"{name}.toml").read_text(
        encoding="utf-8"
    )
    return Palette.from_mapping(name, tomllib.loads(text))


def load_palette_file(path: Path) -> Palette:
    """Load a custom palette from a standalone TOML file."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Palette.from_mapping(data.get("name", path.stem), data)


# ---------------------------------------------------------------------- contrast


@dataclass(frozen=True, slots=True)
class ContrastCheck:
    """One foreground/background pair and the ratio it achieved."""

    scheme: SchemeName
    foreground: str
    background: str
    ratio: float
    required: float
    kind: str  # "text" or "ui"

    @property
    def ok(self) -> bool:
        return self.ratio >= self.required

    def describe(self) -> str:
        return (
            f"{self.scheme}: {self.foreground} on {self.background} is "
            f"{self.ratio:.2f}:1, needs {self.required:.1f}:1 ({self.kind})"
        )


#: (foreground token, backdrop token, minimum ratio, kind). Body text and link text
#: must clear WCAG AA 4.5:1; non-text UI boundaries clear 3:1. `accent` itself is
#: deliberately absent: it is a decorative fill only, which is why `accent_text`
#: exists, and the reference design uses it exactly that way.
CONTRAST_PAIRS: tuple[tuple[str, str, float, str], ...] = (
    ("fg", "bg", 4.5, "text"),
    ("fg", "surface", 4.5, "text"),
    ("fg_body", "bg", 4.5, "text"),
    ("fg_body", "surface", 4.5, "text"),
    ("fg", "surface_alt", 4.5, "text"),
    ("muted", "bg", 4.5, "text"),
    ("link", "bg", 4.5, "text"),
    ("link_hover", "bg", 4.5, "text"),
    ("on_primary", "primary", 4.5, "text"),
    ("accent_text", "bg", 4.5, "text"),
    ("fg_body", "primary_tint", 4.5, "text"),
    ("primary", "surface_alt", 3.0, "ui"),
    ("primary", "bg", 3.0, "ui"),
)


def check_contrast(palette: Palette) -> list[ContrastCheck]:
    """Every pair in both schemes. Tinted backdrops are composited over `bg` first."""
    results: list[ContrastCheck] = []
    for scheme in palette.schemes():
        page_bg = scheme["bg"].flatten()
        for fg_name, bg_name, required, kind in CONTRAST_PAIRS:
            backdrop = scheme[bg_name].over(page_bg)
            results.append(
                ContrastCheck(
                    scheme=scheme.name,
                    foreground=fg_name,
                    background=bg_name,
                    ratio=contrast_ratio(scheme[fg_name], backdrop),
                    required=required,
                    kind=kind,
                )
            )
    return results


def contrast_failures(palette: Palette) -> list[ContrastCheck]:
    return [c for c in check_contrast(palette) if not c.ok]
