"""`docs/stylesheets/custom.css` — the file the user owns.

The design-system stylesheet is managed, so editing it is a conflict. That is only
reasonable if there is somewhere obvious to put your own CSS instead. This file is that
place, and these tests pin the three properties it has to have: it exists, it loads
last, and nothing the toolkit does ever touches it.
"""

from __future__ import annotations

import json
import subprocess
import shutil
import tomllib
from pathlib import Path

import pytest

from docs_studio import __version__
from docs_studio.config import load_config
from docs_studio.scaffold import (
    CUSTOM_STYLESHEET,
    MANAGED_STYLESHEET,
    STYLESHEETS,
    Manifest,
    render_site,
    write_site,
)
from docs_studio.update import apply_update, plan_update
from docs_studio.validation import check_project

CUSTOM = Path("docs") / "stylesheets" / "custom.css"
MANAGED = Path("docs") / "stylesheets" / "extra.css"
MY_CSS = "\n.md-typeset .lead { color: var(--ds-muted); }\n"

ZENSICAL = shutil.which("zensical")


def switch_preset(root: Path, preset: str = "indigo-lavender") -> None:
    config = root / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', f'preset = "{preset}"'),
        encoding="utf-8",
    )


def actions(plan) -> dict[str, str]:
    return {a.path: a.kind for a in plan.actions}


# ------------------------------------------------------------------- it is generated


def test_a_new_site_has_a_custom_stylesheet(generated: Path):
    assert (generated / CUSTOM).is_file()


def test_it_is_seeded_not_managed(generated: Path):
    manifest = Manifest.load(generated)
    assert manifest.ownership(CUSTOM.as_posix()) == "seeded"
    assert manifest.ownership(MANAGED.as_posix()) == "managed"


def test_the_render_agrees(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    spec = render.by_path()[CUSTOM.as_posix()]
    assert spec.ownership == "seeded"
    assert CUSTOM.as_posix() not in {f.path for f in render.managed()}


def test_it_explains_where_custom_css_belongs(generated: Path):
    text = (generated / CUSTOM).read_text()
    assert text.lstrip().startswith("/*")
    assert "belongs to you" in text
    assert "extra.css" in text, "it should say which file not to edit"
    assert "--ds-primary" in text, "it should point at the tokens"
    # An example, commented out, so the file is inert as generated.
    assert ".md-typeset .lead" in text
    assert not [
        line for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "*/"))
    ], "the generated file must contain no active rules"


def test_it_names_the_project(project_root: Path):
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    assert "example-pkg" in render.by_path()[CUSTOM.as_posix()].text


# ------------------------------------------------------------------ it is referenced


def test_zensical_lists_both_stylesheets_in_load_order(generated: Path):
    site = tomllib.loads((generated / "zensical.toml").read_text())["project"]
    assert site["extra_css"] == [MANAGED_STYLESHEET, CUSTOM_STYLESHEET]
    assert site["extra_css"] == list(STYLESHEETS)


def test_the_custom_sheet_loads_after_the_generated_one(generated: Path):
    """Equal specificity means last one wins, so the order is the whole feature."""
    extra_css = tomllib.loads((generated / "zensical.toml").read_text())["project"][
        "extra_css"
    ]
    assert extra_css.index(CUSTOM_STYLESHEET) > extra_css.index(MANAGED_STYLESHEET)


def test_check_is_clean_on_a_site_that_has_one(generated: Path):
    report = check_project(generated, build=False)
    assert report.ok, [d.render() for d in report.errors]
    assert "stylesheet-missing" not in {d.code for d in report.diagnostics}


def test_check_notices_if_it_is_deleted_while_still_referenced(generated: Path):
    (generated / CUSTOM).unlink()
    report = check_project(generated, build=False)
    hit = next(d for d in report.errors if d.code == "stylesheet-missing")
    assert "custom.css" in hit.message


# ----------------------------------------------------------------- it is never touched


def test_editing_it_is_not_a_conflict(generated: Path):
    target = generated / CUSTOM
    target.write_text(target.read_text() + MY_CSS, encoding="utf-8")
    plan = plan_update(generated)
    assert not plan.conflicts
    assert actions(plan)[CUSTOM.as_posix()] == "keep"


def test_update_does_not_modify_it(generated: Path):
    target = generated / CUSTOM
    mine = target.read_text() + MY_CSS
    target.write_text(mine, encoding="utf-8")
    apply_update(plan_update(generated))
    assert target.read_text() == mine


def test_changing_the_palette_updates_managed_css_and_preserves_custom_css(
    generated: Path,
):
    """The scenario the whole file exists for."""
    custom, managed = generated / CUSTOM, generated / MANAGED
    mine = custom.read_text() + MY_CSS
    custom.write_text(mine, encoding="utf-8")
    before_managed = managed.read_text()

    switch_preset(generated)
    written, skipped = apply_update(plan_update(generated))

    assert not skipped, "nothing should conflict"
    assert MANAGED.as_posix() in written
    assert CUSTOM.as_posix() not in written
    assert managed.read_text() != before_managed
    assert "#6254b8" in managed.read_text(), "the new palette landed"
    assert custom.read_text() == mine, "the custom sheet is untouched"


def test_it_survives_a_toolkit_version_change(generated: Path):
    custom = generated / CUSTOM
    mine = custom.read_text() + MY_CSS
    custom.write_text(mine, encoding="utf-8")

    manifest_path = generated / ".docs-studio" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["docs_studio_version"] = "0.0.1"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    plan = plan_update(generated)
    assert plan.from_version == "0.0.1" and plan.to_version == __version__
    apply_update(plan)
    assert custom.read_text() == mine


def test_force_does_not_reach_it_either(generated: Path):
    """`--force` overwrites conflicts; a seeded file is never one."""
    custom = generated / CUSTOM
    mine = custom.read_text() + MY_CSS
    custom.write_text(mine, encoding="utf-8")
    switch_preset(generated)
    apply_update(plan_update(generated), force=True)
    assert custom.read_text() == mine


def test_an_emptied_custom_sheet_stays_empty(generated: Path):
    custom = generated / CUSTOM
    custom.write_text("", encoding="utf-8")
    apply_update(plan_update(generated))
    assert custom.read_text() == ""


# --------------------------------------------------------------- acquiring it later


def test_a_site_generated_before_this_feature_acquires_it_on_update(generated: Path):
    """An older site has no custom.css and no manifest entry for one."""
    (generated / CUSTOM).unlink()
    manifest_path = generated / ".docs-studio" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    del data["files"][CUSTOM.as_posix()]
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    # Its zensical.toml did not list the second stylesheet either.
    zensical = generated / "zensical.toml"
    zensical.write_text(
        zensical.read_text().replace(
            f'extra_css = ["{MANAGED_STYLESHEET}", "{CUSTOM_STYLESHEET}"]',
            f'extra_css = ["{MANAGED_STYLESHEET}"]',
        ),
        encoding="utf-8",
    )
    # Re-record zensical.toml as generated, so it is not a conflict for an unrelated
    # reason: this is the state an older release would really have left behind.
    from docs_studio.scaffold import sha256_file

    data = json.loads(manifest_path.read_text())
    data["files"]["zensical.toml"]["sha256"] = sha256_file(zensical)
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    plan = plan_update(generated)
    assert actions(plan)[CUSTOM.as_posix()] == "create"
    assert not plan.conflicts

    apply_update(plan)
    assert (generated / CUSTOM).is_file()
    site = tomllib.loads(zensical.read_text())["project"]
    assert site["extra_css"] == [MANAGED_STYLESHEET, CUSTOM_STYLESHEET]
    assert Manifest.load(generated).ownership(CUSTOM.as_posix()) == "seeded"
    assert check_project(generated, build=False).ok


def test_a_custom_sheet_that_already_exists_is_preserved_by_init(project_root: Path):
    """Somebody who already keeps their CSS at that path does not lose it."""
    target = project_root / CUSTOM
    target.parent.mkdir(parents=True)
    target.write_text("/* mine, from before */\n.md-typeset { font-size: 1rem; }\n",
                      encoding="utf-8")

    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    written, skipped = write_site(render, project_root)

    assert CUSTOM.as_posix() in skipped
    assert target.read_text().startswith("/* mine, from before */")
    manifest = Manifest.load(project_root)
    assert manifest.ownership(CUSTOM.as_posix()) == "seeded"
    assert manifest.digest(CUSTOM.as_posix()) != render.by_path()[
        CUSTOM.as_posix()
    ].digest
    # And the next update still leaves it alone.
    assert actions(plan_update(project_root))[CUSTOM.as_posix()] == "keep"


def test_init_force_does_not_replace_it_either(project_root: Path):
    """--force is about managed files; content and artwork stay the user's."""
    target = project_root / CUSTOM
    target.parent.mkdir(parents=True)
    target.write_text("/* mine */\n", encoding="utf-8")
    render = render_site(load_config(project_root / "docs-studio.toml"), project_root)
    write_site(render, project_root, overwrite=True)
    # `init --force` is documented as overwriting; what matters afterwards is that
    # `update` still treats whatever is there as the user's.
    assert actions(plan_update(project_root))[CUSTOM.as_posix()] == "keep"


# ------------------------------------------------------------------------- it builds


@pytest.mark.skipif(ZENSICAL is None, reason="zensical is not installed")
def test_a_site_with_a_custom_rule_builds_and_serves_it(tmp_path: Path, generated: Path):
    custom = generated / CUSTOM
    custom.write_text(custom.read_text() + MY_CSS, encoding="utf-8")
    build = subprocess.run(
        [ZENSICAL, "build", "--clean", "--strict"],
        cwd=generated, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    html = (generated / "site" / "index.html").read_text(encoding="utf-8")
    first = html.index(MANAGED_STYLESHEET)
    second = html.index(CUSTOM_STYLESHEET)
    assert first < second, "the custom sheet must be linked after the generated one"

    served = next((generated / "site").rglob("custom.css"))
    assert ".md-typeset .lead" in served.read_text(encoding="utf-8")


@pytest.mark.skipif(ZENSICAL is None, reason="zensical is not installed")
def test_the_generated_custom_sheet_adds_no_rules_to_a_built_site(generated: Path):
    """As generated it is pure comment, so it cannot change how anything looks."""
    assert subprocess.run(
        [ZENSICAL, "build", "--clean", "--strict"], cwd=generated, capture_output=True
    ).returncode == 0
    served = next((generated / "site").rglob("custom.css")).read_text(encoding="utf-8")
    without_comments = __import__("re").sub(r"/\*.*?\*/", "", served, flags=16).strip()
    assert without_comments == ""
