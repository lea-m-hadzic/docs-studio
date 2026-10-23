"""Licensing and attribution, as testable facts.

The stylesheet this toolkit generates is a derivative work of two other projects, one
MIT and one Apache-2.0. Both licenses permit the redistribution outright; both attach
conditions to it. These tests pin the conditions, in the three places they can be lost:
the repository, the built distributions, and the files generated into somebody else's
project.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

from docs_studio.config import load_config
from docs_studio.scaffold import render_site
from docs_studio.validation import ATTRIBUTION_MARKER, check_project

REPO = Path(__file__).resolve().parents[1]
STYLESHEET = "docs/stylesheets/extra.css"

#: The canonical Apache License 2.0, as served from apache.org/licenses/LICENSE-2.0.txt.
APACHE_2_0_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"

#: sisl/ARIS.jl's LICENSE, copied verbatim.
ARIS_MIT_SHA256 = "efbf2b85a196cfaa2ecae58b67036f13ea47d1e8b2897cb9a413fca2cdd0a31f"

ARIS_COPYRIGHT = "Copyright (c) 2025 hdelecki <hdelecki@stanford.edu> and contributors"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------- the repository


def test_the_license_is_the_unmodified_apache_2_0_text():
    assert digest(REPO / "LICENSE") == APACHE_2_0_SHA256


def test_the_upstream_mit_license_is_carried_verbatim():
    """MIT requires the permission notice, not merely the copyright line."""
    path = REPO / "LICENSES" / "MIT-ARIS.jl.txt"
    assert digest(path) == ARIS_MIT_SHA256
    text = path.read_text(encoding="utf-8")
    assert ARIS_COPYRIGHT in text
    assert "Permission is hereby granted, free of charge" in text
    flat = " ".join(text.split())
    assert "shall be included in all copies or substantial portions" in flat


def test_the_notice_identifies_both_sources_with_their_licenses():
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    assert "github.com/sisl/ARIS.jl" in notice
    assert "github.com/sisl/wm-physics-eval" in notice
    assert ARIS_COPYRIGHT in notice
    assert "Apache License, Version 2.0" in notice
    assert "LICENSES/MIT-ARIS.jl.txt" in notice


def test_the_notice_states_the_changes_apache_4b_requires():
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    assert "Statement of changes" in notice
    assert "section 4(b)" in notice
    assert "--ds-" in notice, "it should say what was actually changed"


def test_the_notice_names_a_copyright_holder_for_the_original_material():
    """The attribution line must be filled in, and must not be a leftover placeholder."""
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    first, second = notice.splitlines()[:2]
    assert first == "docs-studio"
    assert second == "Copyright (c) 2026 Lea M. Hadzic"
    for placeholder in ("NOT YET DETERMINED", "TODO", "<", "[name of copyright owner]"):
        assert placeholder not in second, placeholder


def test_the_copyright_line_covers_only_this_project_s_own_material():
    """Upstream copyright stays with upstream; the two must not be conflated."""
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    assert "does not extend to the material in sections 1" in notice
    # The upstream notice is still reproduced, separately and verbatim.
    assert ARIS_COPYRIGHT in notice
    assert notice.index("Copyright (c) 2026 Lea M. Hadzic") < notice.index(ARIS_COPYRIGHT)


def test_the_notice_separates_attribution_from_acknowledgment():
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    assert "Acknowledgments  (not copyright attribution)" in notice


def test_the_notice_does_not_claim_permission_that_was_never_given():
    notice = (REPO / "NOTICE").read_text(encoding="utf-8").lower()
    for claim in ("with permission", "permission was granted", "permission has been obtained",
                  "approved by", "cleared by"):
        assert claim not in notice, claim


def test_package_metadata_declares_apache_and_ships_the_license_files():
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["license"] == "Apache-2.0"
    assert set(project["license-files"]) == {"LICENSE", "NOTICE", "LICENSES/*"}
    assert any("Apache" in c for c in project["classifiers"])
    assert not any("MIT" in c for c in project["classifiers"])


# ----------------------------------------------------------- the distributions


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is needed to build")
def test_the_wheel_and_sdist_carry_every_license_file(tmp_path: Path):
    result = subprocess.run(
        ["uv", "build", "--out-dir", str(tmp_path)], cwd=REPO, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    wheel = next(tmp_path.glob("docs_studio-*.whl"))
    names = set(zipfile.ZipFile(wheel).namelist())
    for required in ("LICENSE", "NOTICE", "LICENSES/MIT-ARIS.jl.txt"):
        assert any(n.endswith(required) for n in names), f"{required} missing from the wheel"

    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in names if n.endswith("licenses/LICENSE"))
        assert hashlib.sha256(archive.read(name)).hexdigest() == APACHE_2_0_SHA256

    sdist = next(tmp_path.glob("docs_studio-*.tar.gz"))
    with tarfile.open(sdist) as tar:
        members = {m.name.split("/", 1)[1] for m in tar.getmembers() if "/" in m.name}
    assert {"LICENSE", "NOTICE", "LICENSES/MIT-ARIS.jl.txt"} <= members


# ------------------------------------------------------- what we generate for others


def test_a_generated_stylesheet_carries_the_whole_mit_notice(project_root: Path):
    """The CSS is the derived artifact; the notice has to be *in* it, not beside it."""
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    css = render.by_path()[STYLESHEET].text
    assert ATTRIBUTION_MARKER in css
    assert ARIS_COPYRIGHT in css
    assert "Permission is hereby granted, free of charge" in css
    flat = " ".join(css.replace("*", " ").split())
    assert "shall be included in all copies or substantial portions" in flat


def test_a_generated_stylesheet_carries_the_apache_notice_and_the_changes(
    project_root: Path,
):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    css = render.by_path()[STYLESHEET].text
    assert "Apache License, Version 2.0" in css
    assert "http://www.apache.org/licenses/LICENSE-2.0" in css
    assert 'WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND' in css
    assert "CHANGES (Apache-2.0 section 4(b))" in css
    assert "github.com/sisl/wm-physics-eval" in css
    assert "github.com/sisl/ARIS.jl" in css
    # And a pointer to the full record.
    assert "NOTICE" in css


def test_the_attribution_comes_first_in_the_file(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    css = render.by_path()[STYLESHEET].text
    assert css.lstrip().startswith("/*")
    assert css.index(ARIS_COPYRIGHT) < css.index("--ds-primary")


@pytest.mark.skipif(shutil.which("zensical") is None, reason="zensical is not installed")
def test_the_attribution_survives_into_the_built_site(generated: Path):
    """A notice that the build strips is a notice the published site does not carry."""
    assert subprocess.run(
        [shutil.which("zensical"), "build", "--clean", "--strict"],
        cwd=generated, capture_output=True,
    ).returncode == 0
    built = next((generated / "site").rglob("extra.css"))
    text = built.read_text(encoding="utf-8")
    assert ATTRIBUTION_MARKER in text
    assert ARIS_COPYRIGHT in text
    assert "Apache License, Version 2.0" in text


def test_check_warns_when_the_attribution_header_is_removed(generated: Path):
    css = generated / "docs" / "stylesheets" / "extra.css"
    text = css.read_text(encoding="utf-8")
    css.write_text(text[text.index("/* Generated by docs-studio"):], encoding="utf-8")
    report = check_project(generated, build=False)
    hit = next(d for d in report.diagnostics if d.code == "attribution-removed")
    assert hit.level == "warning"
    assert "derivative work" in hit.message


def test_check_suggests_a_root_notice_but_does_not_insist(generated: Path):
    report = check_project(generated, build=False)
    hit = next(d for d in report.diagnostics if d.code == "attribution-file")
    assert hit.level == "info"
    assert report.ok


def test_the_suggestion_goes_away_once_there_is_one(generated: Path):
    (generated / "NOTICE").write_text("Derived styling: see docs-studio.\n", encoding="utf-8")
    codes = {d.code for d in check_project(generated, build=False).diagnostics}
    assert "attribution-file" not in codes


def test_this_repository_and_every_example_keeps_its_attribution():
    for site in (REPO, REPO / "examples" / "tidepool",
                 REPO / "examples" / "Lattice.jl", REPO / "examples" / "greenline"):
        css = site / "docs" / "stylesheets" / "extra.css"
        assert css.is_file(), site
        text = css.read_text(encoding="utf-8")
        assert ATTRIBUTION_MARKER in text, site
        assert ARIS_COPYRIGHT in text, site
