"""The `docs-studio.toml` schema.

Everything that distinguishes one generated site from another lives in this one file:
project metadata, which palette, which logo, the navigation, and how it deploys. The
styling does not — that is generated and managed by the toolkit.

Validation is deliberately strict and unforgiving about silence: an unknown key is an
error rather than a setting that quietly does nothing.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .theme import ColorError, Palette, Scheme, load_palette_file, load_preset

__all__ = [
    "BrandingConfig",
    "ConfigError",
    "DeployConfig",
    "NavEntry",
    "NavPage",
    "ProjectConfig",
    "ResourceLink",
    "StudioProject",
    "ThemeConfig",
    "CONFIG_FILENAME",
    "load_config",
    "titleize",
]

CONFIG_FILENAME = "docs-studio.toml"

SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
LanguageProfile = Literal["python", "julia", "generic"]


class ConfigError(Exception):
    """A `docs-studio.toml` that cannot be used, with a readable explanation."""


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ------------------------------------------------------------------------- project


class ProjectConfig(Base):
    """Who the site is for and what it is called."""

    name: Annotated[str, Field(min_length=1, max_length=120)]
    slug: str | None = None
    description: Annotated[str, Field(min_length=1, max_length=400)]
    author: Annotated[str, Field(min_length=1)]
    site_url: str
    repo_url: str | None = None
    copyright: str | None = None
    language: LanguageProfile = "generic"

    @field_validator("site_url")
    @classmethod
    def _site_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("site_url must start with https:// (or http:// for a local host)")
        return value if value.endswith("/") else value + "/"

    @field_validator("repo_url")
    @classmethod
    def _repo_url(cls, value: str | None) -> str | None:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("repo_url must be an absolute URL")
        return value.rstrip("/") if value else value

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value and not SLUG.match(value):
            raise ValueError(
                "slug must be lowercase and start with a letter or digit, "
                "e.g. my-package"
            )
        return value

    @model_validator(mode="after")
    def _default_slug(self) -> ProjectConfig:
        if not self.slug:
            derived = re.sub(r"[^a-z0-9._-]+", "-", self.name.lower()).strip("-")
            object.__setattr__(self, "slug", derived or "docs")
        return self

    @property
    def pages_base_path(self) -> str:
        """The GitHub Pages sub-path, e.g. `/ARIS.jl/` — `/` for a user or apex site.

        Zensical resolves asset URLs from `site_url`, so this is what makes a site
        work under `https://<org>.github.io/<repo>/` without a rebuild.
        """
        rest = self.site_url.split("//", 1)[-1]
        path = "/" + rest.partition("/")[2]
        return path if path.endswith("/") else path + "/"


# --------------------------------------------------------------------------- theme


class PaletteOverride(Base):
    """Per-scheme token overrides, layered on top of the chosen preset."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)


class ThemeConfig(Base):
    """Which palette, and anything overridden on top of it."""

    preset: str = "neutral"
    palette_file: str | None = None
    light: dict[str, str] = Field(default_factory=dict)
    dark: dict[str, str] = Field(default_factory=dict)
    md_accent: str | None = None
    #: Extra Zensical theme features appended to the toolkit's own list.
    extra_features: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_source(self) -> ThemeConfig:
        if self.palette_file and (self.preset not in ("neutral", "custom")):
            raise ValueError(
                "set either theme.preset or theme.palette_file, not both "
                "(palette_file implies a custom palette)"
            )
        return self

    def resolve(self, base_dir: Path) -> Palette:
        """The final palette: preset or file, then per-scheme overrides."""
        try:
            if self.palette_file:
                path = (base_dir / self.palette_file).resolve()
                if not path.is_file():
                    raise ConfigError(f"theme.palette_file does not exist: {path}")
                palette = load_palette_file(path)
            else:
                palette = load_preset(self.preset)
        except KeyError as exc:
            raise ConfigError(str(exc).strip("\"'")) from exc
        except ColorError as exc:
            raise ConfigError(f"palette: {exc}") from exc
        if not (self.light or self.dark or self.md_accent):
            return palette
        try:
            light = (
                Scheme.build("light", {**_raw(palette.light), **self.light})
                if self.light
                else palette.light
            )
            dark = (
                Scheme.build("dark", {**_raw(palette.dark), **self.dark})
                if self.dark
                else palette.dark
            )
        except ColorError as exc:
            raise ConfigError(f"theme override: {exc}") from exc
        return Palette(
            name=palette.name,
            title=palette.title,
            description=palette.description,
            md_primary=palette.md_primary,
            md_primary_dark=palette.md_primary_dark,
            md_accent=self.md_accent or palette.md_accent,
            light=light,
            dark=dark,
        )


def _raw(scheme: Scheme) -> dict[str, str]:
    """A scheme back as plain CSS strings, so overrides can be layered on it."""
    return {name: color.css() for name, color in scheme.tokens.items()}


# ------------------------------------------------------------------------ branding


class BrandingConfig(Base):
    """Logo, optional dark variant and wordmark, favicon.

    Paths are relative to the repository root. Supplied files are copied into
    `docs/assets/` verbatim — never resized, re-encoded or cropped — and are never
    overwritten by `docs-studio update`.
    """

    logo: str | None = None
    logo_dark: str | None = None
    wordmark: str | None = None
    favicon: str | None = None
    #: One or two characters for the generated placeholder mark. Defaults to the
    #: project's initials. Ignored when `logo` is set.
    monogram_text: str | None = None

    @field_validator("logo", "logo_dark", "wordmark", "favicon")
    @classmethod
    def _suffix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        allowed = {".svg", ".png", ".ico", ".webp", ".jpg", ".jpeg"}
        if Path(value).suffix.lower() not in allowed:
            raise ValueError(
                f"{value!r}: expected one of {', '.join(sorted(allowed))}"
            )
        return value

    @field_validator("monogram_text")
    @classmethod
    def _monogram(cls, value: str | None) -> str | None:
        if value is not None and not 1 <= len(value.strip()) <= 2:
            raise ValueError("monogram_text must be one or two characters")
        return value

    @model_validator(mode="after")
    def _dark_needs_light(self) -> BrandingConfig:
        if self.logo_dark and not self.logo:
            raise ValueError("branding.logo_dark needs branding.logo as well")
        return self


# ----------------------------------------------------------------------- resources


class ResourceLink(Base):
    """One compact outlined button in the homepage resource row."""

    label: Annotated[str, Field(min_length=1, max_length=60)]
    url: str
    #: A theme icon shortcode, e.g. `simple-github` or `material/file-document-outline`.
    icon: str | None = None
    #: A local image under `docs/`, e.g. `assets/huggingface-logo.svg`, for a brand
    #: logo the theme does not ship.
    image: str | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://", "mailto:")):
            raise ValueError("resource url must be absolute, or a mailto: link")
        return value

    @model_validator(mode="after")
    def _icon_xor_image(self) -> ResourceLink:
        if self.icon and self.image:
            raise ValueError("a resource takes either icon or image, not both")
        return self


# ----------------------------------------------------------------------------- nav


def titleize(page: str) -> str:
    """A nav label for a page that did not give one: `multiple-thresholds.md` →
    `Multiple thresholds`."""
    stem = Path(page).stem.replace("_", "-")
    words = [w for w in stem.split("-") if w]
    if not words:
        return page
    return " ".join([words[0].capitalize(), *words[1:]])


class NavPage(Base):
    """A page in a section, with an explicit nav label."""

    title: Annotated[str, Field(min_length=1)]
    page: str


class NavEntry(Base):
    """A single page, or a titled section of pages."""

    title: Annotated[str, Field(min_length=1)]
    page: str | None = None
    pages: list[str | NavPage] = Field(default_factory=list)

    @model_validator(mode="after")
    def _page_xor_pages(self) -> NavEntry:
        if bool(self.page) == bool(self.pages):
            raise ValueError(
                f"nav entry {self.title!r} needs exactly one of page or pages"
            )
        for name in self.all_pages:
            if not name.endswith(".md"):
                raise ValueError(f"nav entry {self.title!r}: {name!r} is not a .md page")
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError(f"nav entry {self.title!r}: {name!r} must be inside docs/")
        return self

    @property
    def all_pages(self) -> list[str]:
        if self.page:
            return [self.page]
        return [p if isinstance(p, str) else p.page for p in self.pages]

    @property
    def labelled_pages(self) -> list[tuple[str, str]]:
        """`(label, page)` for every page in this entry, in nav order."""
        if self.page:
            return [(self.title, self.page)]
        return [
            (titleize(p), p) if isinstance(p, str) else (p.title, p.page)
            for p in self.pages
        ]

    @property
    def is_section(self) -> bool:
        return not self.page


# -------------------------------------------------------------------------- deploy


class DeployConfig(Base):
    """The optional GitHub Pages workflow."""

    github_pages: bool = True
    #: `manual` emits `workflow_dispatch` only — nothing publishes until someone asks.
    #: `push` adds `push: branches: [<branch>]`.
    trigger: Literal["manual", "push"] = "manual"
    branch: str = "main"
    python_version: str = "3.13"
    zensical_version: str = "0.0.67"
    #: Extra shell lines run before the checker, e.g. installing the documented package.
    extra_install: list[str] = Field(default_factory=list)

    @field_validator("zensical_version")
    @classmethod
    def _pinned(cls, value: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", value):
            raise ValueError(
                "deploy.zensical_version must be an exact version, e.g. 0.0.67, "
                "so a published build is reproducible"
            )
        return value


# ----------------------------------------------------------------------------- root


class StudioProject(Base):
    """The whole of `docs-studio.toml`."""

    project: ProjectConfig
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    branding: BrandingConfig = Field(default_factory=BrandingConfig)
    resources: list[ResourceLink] = Field(default_factory=list)
    nav: list[NavEntry] = Field(default_factory=list)
    deploy: DeployConfig = Field(default_factory=DeployConfig)
    #: The toolkit version that last generated this site. `update` reads it to
    #: describe the transition; it is written by `init` and by `update`.
    docs_studio_version: str | None = None

    @model_validator(mode="after")
    def _nav_is_consistent(self) -> StudioProject:
        seen: dict[str, str] = {}
        for entry in self.nav:
            for page in entry.all_pages:
                if page in seen:
                    raise ValueError(
                        f"{page} appears twice in the nav ({seen[page]!r} and "
                        f"{entry.title!r}); every page belongs in exactly one place"
                    )
                seen[page] = entry.title
        if self.nav and "index.md" not in seen:
            raise ValueError("the nav must include index.md, the site's home page")
        return self

    @property
    def pages(self) -> list[str]:
        return [page for entry in self.nav for page in entry.all_pages]

    def palette(self, base_dir: Path) -> Palette:
        return self.theme.resolve(base_dir)


def load_config(path: Path) -> StudioProject:
    """Read and validate `docs-studio.toml`, raising :class:`ConfigError`."""
    if not path.is_file():
        raise ConfigError(f"no {path.name} here: looked for {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path.name} is not valid TOML: {exc}") from exc
    try:
        return StudioProject.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_format_errors(path, exc)) from exc


def _format_errors(path: Path, exc: ValidationError) -> str:
    lines = [f"{path.name} has {exc.error_count()} problem(s):"]
    for error in exc.errors():
        where = ".".join(str(p) for p in error["loc"]) or "(root)"
        lines.append(f"  {where}: {error['msg']}")
    return "\n".join(lines)
