"""`update`: the version transition, the diffs, and above all the conflicts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docs_studio import __version__
from docs_studio.scaffold import Manifest, sha256_file
from docs_studio.update import apply_update, plan_update, unified_diff

CSS = Path("docs/stylesheets/extra.css")
MY_EDIT = "\n/* an edit I made by hand and would like to keep */\n"


def actions(plan) -> dict[str, str]:
    return {a.path: a.kind for a in plan.actions}


def switch_preset(root: Path, preset: str = "indigo-lavender") -> None:
    config = root / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', f'preset = "{preset}"'),
        encoding="utf-8",
    )


def test_nothing_to_do_on_an_untouched_site(generated: Path):
    plan = plan_update(generated)
    assert plan.is_noop
    assert not plan.conflicts
    assert all(a.kind in ("unchanged", "keep") for a in plan.actions)
    assert plan.from_version == __version__ and plan.to_version == __version__


def test_changing_the_palette_updates_only_the_managed_files(generated: Path):
    switch_preset(generated)
    plan = plan_update(generated)
    assert {a.path for a in plan.writes} == {"zensical.toml", str(CSS)}
    assert all(a.ownership == "managed" for a in plan.writes)
    assert all(a.kind == "keep" for a in plan.actions if a.ownership == "seeded")


def test_a_dry_run_writes_nothing(generated: Path):
    switch_preset(generated)
    before = (generated / CSS).read_bytes()
    plan = plan_update(generated)
    assert plan.writes
    # plan_update is pure; nothing is written until apply_update is called.
    assert (generated / CSS).read_bytes() == before


def test_applying_writes_the_new_palette(generated: Path):
    switch_preset(generated)
    plan = plan_update(generated)
    written, skipped = apply_update(plan)
    assert not skipped
    assert set(written) == {"zensical.toml", str(CSS)}
    css = (generated / CSS).read_text()
    assert "#6254b8" in css and "#4b5fd7" not in css


def test_applying_is_idempotent(generated: Path):
    switch_preset(generated)
    apply_update(plan_update(generated))
    assert plan_update(generated).is_noop


def test_an_edited_managed_file_is_a_conflict_and_survives_the_update(generated: Path):
    target = generated / CSS
    mine = target.read_text() + MY_EDIT
    target.write_text(mine, encoding="utf-8")
    switch_preset(generated)

    plan = plan_update(generated)
    conflict = next(a for a in plan.conflicts)
    assert conflict.path == str(CSS)
    assert "edited since docs-studio generated it" in conflict.reason
    assert conflict.diff, "a conflict shows what would have changed"

    written, skipped = apply_update(plan)
    assert skipped == [str(CSS)]
    assert target.read_text() == mine, "the edit was not destroyed"
    # The rest of the update still went through.
    assert "zensical.toml" in written


def test_a_conflict_stays_a_conflict_until_someone_resolves_it(generated: Path):
    target = generated / CSS
    target.write_text(target.read_text() + MY_EDIT, encoding="utf-8")
    switch_preset(generated)
    apply_update(plan_update(generated))
    again = plan_update(generated)
    assert [a.path for a in again.conflicts] == [str(CSS)]


def test_force_overwrites_a_conflict_and_says_what_it_did(generated: Path):
    target = generated / CSS
    target.write_text(target.read_text() + MY_EDIT, encoding="utf-8")
    switch_preset(generated)
    written, skipped = apply_update(plan_update(generated), force=True)
    assert not skipped
    assert str(CSS) in written
    assert MY_EDIT not in target.read_text()
    assert plan_update(generated).is_noop


def test_a_managed_file_the_toolkit_did_not_write_is_not_taken_over(generated: Path):
    manifest_path = generated / ".docs-studio" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    del data["files"][str(CSS)]
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    plan = plan_update(generated)
    conflict = next(a for a in plan.conflicts)
    assert conflict.path == str(CSS)
    assert "not recorded in the manifest" in conflict.reason


def test_a_deleted_managed_file_is_recreated(generated: Path):
    (generated / CSS).unlink()
    plan = plan_update(generated)
    assert actions(plan)[str(CSS)] == "create"
    apply_update(plan)
    assert (generated / CSS).is_file()


def test_content_pages_are_never_regenerated_even_when_emptied(generated: Path):
    page = generated / "docs" / "index.md"
    page.write_text("# Mine\n", encoding="utf-8")
    plan = plan_update(generated)
    assert actions(plan)["docs/index.md"] == "keep"
    apply_update(plan)
    assert page.read_text() == "# Mine\n"


def test_a_page_added_to_the_nav_gets_a_starter_page(generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace(
            'pages = ["api.md"]', 'pages = ["api.md", "schemas.md"]'
        ),
        encoding="utf-8",
    )
    plan = plan_update(generated)
    assert actions(plan)["docs/schemas.md"] == "create"
    apply_update(plan)
    created = generated / "docs" / "schemas.md"
    assert created.is_file()
    assert "# Schemas" in created.read_text()
    assert Manifest.load(generated).ownership("docs/schemas.md") == "seeded"


def test_a_logo_supplied_later_replaces_the_monogram_without_deleting_it(
    generated: Path,
):
    (generated / "mark.svg").write_text("<svg/>", encoding="utf-8")
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text() + '\n[branding]\nlogo = "mark.svg"\n', encoding="utf-8"
    )
    plan = plan_update(generated)
    assert actions(plan)["docs/assets/mark.svg"] == "create"
    apply_update(plan)
    assert (generated / "docs" / "assets" / "mark.svg").is_file()
    # The old monogram is left on disk rather than deleted; the config no longer
    # points at it.
    assert (generated / "docs" / "assets" / "logo.svg").is_file()
    assert "assets/mark.svg" in (generated / "zensical.toml").read_text()


def test_a_user_logo_is_never_overwritten_by_an_update(generated: Path):
    (generated / "mark.svg").write_text("<svg>original</svg>", encoding="utf-8")
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text() + '\n[branding]\nlogo = "mark.svg"\n', encoding="utf-8"
    )
    apply_update(plan_update(generated))
    copied = generated / "docs" / "assets" / "mark.svg"
    copied.write_text("<svg>hand tuned</svg>", encoding="utf-8")
    apply_update(plan_update(generated))
    assert copied.read_text() == "<svg>hand tuned</svg>"


def test_the_manifest_records_the_version_that_last_wrote(generated: Path):
    manifest_path = generated / ".docs-studio" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["docs_studio_version"] = "0.0.1"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    plan = plan_update(generated)
    assert plan.from_version == "0.0.1" and plan.to_version == __version__
    switch_preset(generated)
    apply_update(plan_update(generated))
    assert Manifest.load(generated).docs_studio_version == __version__


def test_a_site_with_no_manifest_treats_every_managed_file_as_a_conflict(
    generated: Path,
):
    (generated / ".docs-studio" / "manifest.json").unlink()
    plan = plan_update(generated)
    assert not plan.had_manifest
    assert {a.path for a in plan.conflicts} == {
        "zensical.toml", str(CSS), ".github/workflows/docs.yml"
    }


def test_the_manifest_hashes_match_what_is_on_disk_after_an_update(generated: Path):
    switch_preset(generated)
    apply_update(plan_update(generated))
    manifest = Manifest.load(generated)
    for path, entry in manifest.files.items():
        assert sha256_file(generated / path) == entry["sha256"], path


def test_a_skipped_conflict_keeps_its_old_hash_in_the_manifest(generated: Path):
    target = generated / CSS
    recorded = Manifest.load(generated).digest(str(CSS))
    target.write_text(target.read_text() + MY_EDIT, encoding="utf-8")
    switch_preset(generated)
    apply_update(plan_update(generated))
    assert Manifest.load(generated).digest(str(CSS)) == recorded


def test_the_summary_counts_every_category(generated: Path):
    switch_preset(generated)
    summary = plan_update(generated).summary()
    assert "0 to create" in summary and "2 to update" in summary
    assert "yours, untouched" in summary


def test_unified_diff_is_readable_for_text():
    diff = unified_diff("a.css", b"one\ntwo\n", b"one\nTWO\n")
    assert "-two" in diff and "+TWO" in diff
    assert "a/a.css" in diff and "b/a.css" in diff


def test_unified_diff_says_so_for_binary():
    diff = unified_diff("logo.png", b"\x89PNG\x00\x01", b"\x89PNG\x00\x02\x03")
    assert "binary file" in diff and "logo.png" in diff


def test_update_on_a_directory_with_no_config_raises(tmp_path: Path):
    from docs_studio.config import ConfigError

    with pytest.raises(ConfigError):
        plan_update(tmp_path)
