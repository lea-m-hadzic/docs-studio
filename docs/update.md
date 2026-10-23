# `update`

Regenerates the managed styling and configuration when you change the palette or move
to a new version of the toolkit, without touching anything of yours.

```bash
docs-studio update [OPTIONS]
```

## Options

| Option | Effect |
| --- | --- |
| `--path` | the site's root directory |
| `--dry-run` | print the plan and the diffs, write nothing |
| `--diff` / `--no-diff` | show the diff for each change; on by default |
| `--yes`, `-y` | apply without asking |
| `--verbose`, `-v` | also list the files it left untouched |
| `--force` | overwrite conflicts too — **this discards those edits** |

## A run

```text
$ docs-studio update --dry-run
docs-studio 0.1.0
  0 to create, 1 to update, 1 managed unchanged, 10 yours, untouched, 1 conflict(s)

 CONFLICT  docs/stylesheets/extra.css — edited since docs-studio generated it
    --- a/docs/stylesheets/extra.css
    +++ b/docs/stylesheets/extra.css
    @@ -14,45 +14,45 @@
     :root,
     [data-md-color-scheme="default"] {
    -  --ds-primary: #6254b8;
    +  --ds-primary: #3d4f66;
    …
   update  zensical.toml

1 conflict(s) will be left exactly as they are. Resolve them by hand, or re-run with
--force to discard those edits.

--dry-run: nothing was written.
```

Nothing is written until the plan is approved, interactively or with `--yes`.

## The decision table

Taken per file, from the manifest and what is on disk:

| | on disk | what happens |
| --- | --- | --- |
| managed | absent | created |
| managed | unchanged since generated | replaced when the new render differs |
| managed | **edited** | **conflict** — skipped, reported, never overwritten |
| managed | not in the manifest | **conflict** — it did not write it, so it will not take it over |
| seeded | absent | created — this is how a page added to the nav appears |
| seeded | present | left alone, always |

[Safe updates](updating.md) walks through what each row means and how to resolve a
conflict.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | everything applied, or there was nothing to do |
| 1 | a conflict was skipped, or you declined the plan |
| 2 | no `docs-studio.toml`, or it does not validate |

A conflict exits 1 even under `--dry-run`, so a scripted update fails loudly rather
than reporting success while skipping work.

## The common cases

**A new palette.** Edit `theme.preset` or the token overrides, then:

```bash
docs-studio update --dry-run
docs-studio update
```

**A page added to the nav.** Add the `[[nav]]` entry, then `update` creates the starter
page for it. Pages that already exist are untouched.

**A new version of docs-studio.** The run says which transition it is:

```text
docs-studio 0.1.0 → 0.2.0
```

**A managed file you edited on purpose.** Move the rules into
`docs/stylesheets/custom.css`, restore the managed file, and the conflict is gone.
See [Safe updates](updating.md#resolving-a-conflict).
