"""`docs-studio update` — regenerate the managed styling without losing anyone's work.

The contract, in one sentence: a file the toolkit generated and nobody has touched
since is replaced; a file somebody has touched is a **conflict**, reported and left
exactly as it is.

How each file is decided, using the manifest written at generation time:

====================  ==========================================================
on disk / manifest    action
====================  ==========================================================
managed, absent       created
managed, unchanged    replaced when the new render differs, else left alone
managed, edited       **conflict** — skipped, reported, never overwritten
managed, untracked    **conflict** — the toolkit did not write it, so it will not
                      take it over
seeded, absent        created (this is how a page added to the nav appears)
seeded, present       left alone, always — content and artwork are yours
====================  ==========================================================

`--dry-run` prints the same plan and writes nothing. Without it, nothing is written
until the plan is approved, either interactively or with `--yes`. `--force` applies
conflicts too, and is the only way to lose an edit; it says so.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from . import __version__
from .config import CONFIG_FILENAME, load_config
from .scaffold import (
    FileSpec,
    Manifest,
    SiteRender,
    render_site,
    sha256_bytes,
    sha256_file,
)

__all__ = [
    "Action",
    "ActionKind",
    "UpdatePlan",
    "apply_update",
    "plan_update",
    "unified_diff",
]

ActionKind = Literal["create", "replace", "unchanged", "conflict", "keep"]

#: Conflicts are the two kinds that are never written without `--force`.
CONFLICT_REASONS = {
    "edited": "edited since docs-studio generated it",
    "untracked": "not recorded in the manifest, so docs-studio did not write it",
}


@dataclass(frozen=True, slots=True)
class Action:
    """What `update` intends to do about one file."""

    path: str
    kind: ActionKind
    ownership: str
    reason: str = ""
    diff: str = ""

    @property
    def is_conflict(self) -> bool:
        return self.kind == "conflict"

    @property
    def writes(self) -> bool:
        return self.kind in ("create", "replace")

    def headline(self) -> str:
        label = {
            "create": "create",
            "replace": "update",
            "unchanged": "unchanged",
            "conflict": "CONFLICT",
            "keep": "keep",
        }[self.kind]
        suffix = f" — {self.reason}" if self.reason else ""
        return f"{label:>9}  {self.path}{suffix}"


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    """Every action, plus the version transition it belongs to."""

    root: Path
    render: SiteRender
    actions: tuple[Action, ...]
    from_version: str
    to_version: str
    had_manifest: bool

    @property
    def conflicts(self) -> list[Action]:
        return [a for a in self.actions if a.is_conflict]

    @property
    def writes(self) -> list[Action]:
        return [a for a in self.actions if a.writes]

    @property
    def unchanged(self) -> list[Action]:
        return [a for a in self.actions if a.kind == "unchanged"]

    @property
    def kept(self) -> list[Action]:
        return [a for a in self.actions if a.kind == "keep"]

    @property
    def is_noop(self) -> bool:
        return not self.writes and not self.conflicts

    def summary(self) -> str:
        creates = sum(1 for a in self.writes if a.kind == "create")
        replaces = sum(1 for a in self.writes if a.kind == "replace")
        parts = [
            f"{creates} to create",
            f"{replaces} to update",
            f"{len(self.unchanged)} managed unchanged",
            f"{len(self.kept)} yours, untouched",
        ]
        if self.conflicts:
            parts.append(f"{len(self.conflicts)} conflict(s)")
        return ", ".join(parts)


def unified_diff(path: str, before: bytes, after: bytes) -> str:
    """A readable diff, or a plain statement when the file is not text."""
    try:
        old = before.decode("utf-8").splitlines(keepends=True)
        new = after.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return f"binary file {path} differs ({len(before)} → {len(after)} bytes)\n"
    return "".join(
        difflib.unified_diff(old, new, fromfile=f"a/{path}", tofile=f"b/{path}", n=3)
    )


def plan_update(root: Path) -> UpdatePlan:
    """Work out what would change, reading the manifest and the files on disk."""
    config = load_config(root / CONFIG_FILENAME)
    render = render_site(config, root)
    manifest = Manifest.load(root)
    actions: list[Action] = []

    for spec in sorted(render.files, key=lambda f: f.path):
        actions.append(_decide(root, spec, manifest))

    return UpdatePlan(
        root=root,
        render=render,
        actions=tuple(actions),
        from_version=manifest.docs_studio_version if manifest else "unknown",
        to_version=__version__,
        had_manifest=manifest is not None,
    )


def _decide(root: Path, spec: FileSpec, manifest: Manifest | None) -> Action:
    target = root / spec.path
    recorded = manifest.digest(spec.path) if manifest else None

    if spec.ownership == "seeded":
        if target.exists():
            return Action(spec.path, "keep", spec.ownership, "yours; never regenerated")
        return Action(spec.path, "create", spec.ownership, "new page or asset")

    if not target.exists():
        return Action(spec.path, "create", spec.ownership)

    on_disk = target.read_bytes()
    if recorded is None:
        return Action(
            spec.path,
            "conflict",
            spec.ownership,
            CONFLICT_REASONS["untracked"],
            unified_diff(spec.path, on_disk, spec.content),
        )
    if sha256_bytes(on_disk) != recorded:
        return Action(
            spec.path,
            "conflict",
            spec.ownership,
            CONFLICT_REASONS["edited"],
            unified_diff(spec.path, on_disk, spec.content),
        )
    if on_disk == spec.content:
        return Action(spec.path, "unchanged", spec.ownership)
    return Action(
        spec.path,
        "replace",
        spec.ownership,
        "",
        unified_diff(spec.path, on_disk, spec.content),
    )


def apply_update(plan: UpdatePlan, *, force: bool = False) -> tuple[list[str], list[str]]:
    """Write the plan. Returns `(written, skipped_conflicts)`.

    Conflicts are skipped unless `force`, which overwrites the file on disk and
    therefore discards whatever was in it.
    """
    specs = plan.render.by_path()
    written: list[str] = []
    skipped: list[str] = []

    for action in plan.actions:
        if action.kind in ("unchanged", "keep"):
            continue
        if action.is_conflict and not force:
            skipped.append(action.path)
            continue
        target = plan.root / action.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(specs[action.path].content)
        written.append(action.path)

    _write_manifest(plan, written)
    return written, skipped


def _write_manifest(plan: UpdatePlan, written: list[str]) -> None:
    """Record what is on disk now.

    A skipped conflict keeps its *old* recorded digest, so it stays a conflict until
    somebody resolves it — losing that would silently make the next update overwrite
    the edit.
    """
    previous = Manifest.load(plan.root)
    manifest = Manifest(
        docs_studio_version=__version__,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        files={},
    )
    written_set = set(written)
    for spec in sorted(plan.render.files, key=lambda f: f.path):
        path, target = spec.path, plan.root / spec.path
        if path in written_set:
            manifest.files[path] = {"sha256": spec.digest, "ownership": spec.ownership}
        elif previous and path in previous.files and spec.ownership == "managed":
            manifest.files[path] = dict(previous.files[path])
        elif target.is_file():
            manifest.files[path] = {
                "sha256": sha256_file(target),
                "ownership": spec.ownership,
            }
    manifest.save(plan.root)
