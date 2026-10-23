"""Shared fixtures. Nothing here touches the network or the user's real projects."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from docs_studio.cli import app
from docs_studio.config import load_config
from docs_studio.scaffold import render_site, write_site

MINIMAL_CONFIG = """
docs_studio_version = "0.1.0"

[project]
name = "example-pkg"
description = "An example package"
author = "Example Lab"
site_url = "https://example.github.io/example-pkg/"
repo_url = "https://github.com/example/example-pkg"
language = "python"

[theme]
preset = "ocean-violet"

[[resources]]
label = "GitHub Repository"
url = "https://github.com/example/example-pkg"
icon = "simple-github"

[[nav]]
title = "Home"
page = "index.md"

[[nav]]
title = "Getting started"
pages = ["quickstart.md", "install.md"]

[[nav]]
title = "Reference"
pages = ["api.md"]

[deploy]
github_pages = true
trigger = "manual"
"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli():
    """Invoke the CLI and return the result, with output captured."""
    runner = CliRunner()

    def invoke(*args: str, input: str | None = None):
        return runner.invoke(app, list(args), input=input)

    return invoke


@pytest.fixture
def config_text() -> str:
    return MINIMAL_CONFIG


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A directory holding a valid docs-studio.toml and nothing else."""
    (tmp_path / "docs-studio.toml").write_text(MINIMAL_CONFIG, encoding="utf-8")
    return tmp_path


@pytest.fixture
def generated(project_root: Path) -> Path:
    """A fully generated site, as `init` would leave it."""
    config = load_config(project_root / "docs-studio.toml")
    write_site(render_site(config, project_root), project_root)
    return project_root
