# Reporting a blockage

A lane that is closed, flooded, or full of scaffolding is a blockage. Reporting one
takes a single command and changes everyone's routing at the next data refresh.

## Report one

```bash
greenline report "Mill Street bike lane" --reason scaffolding
```

```text
Reported: Mill Street bike lane — scaffolding
  expires 2026-11-21 (30 days)
  routing around it from the next refresh
```

The lane name has to match the map. `greenline lanes near "Mill Street"` lists
candidates if it does not.

## The reasons

| Reason | Expires after | Use it for |
| --- | --- | --- |
| `scaffolding` | 30 days | building work in the lane |
| `flooded` | 7 days | standing water |
| `roadworks` | 60 days | dug up |
| `obstructed` | 14 days | a parked car, a skip, a fallen tree |
| `removed` | never | the lane is gone for good |

Every reason except `removed` expires on its own. That is the point: a blockage nobody
re-reports goes away, so the map drifts back toward reality rather than accumulating
stale closures.

!!! warning "`removed` is for a lane that no longer exists"
    It does not expire, and clearing it needs a volunteer with write access. If the
    lane is merely unusable for now, one of the other reasons is the right one.

## Check what is blocked

```bash
greenline blockages
```

```text
7 active blockages

  Mill Street bike lane        scaffolding   expires in 28 days
  Quay Path (east end)         flooded       expires in 3 days
  Fifth Avenue connector       obstructed    expires in 11 days
  …
```

## Re-report and clear

A blockage that is still there when it expires should be reported again — the same
command does it. To clear one early:

```bash
greenline report "Quay Path (east end)" --clear
```

You can only clear a blockage you reported, unless you have write access to the map.
That rule exists because the person who saw the flood is usually the person who can see
it has gone.

## What happens to your report

Reports go to the volunteer map as a signed entry with a timestamp and the reason. No
account, no email address, and no location is collected — the signing key is local and
the only thing it establishes is that the same person can clear their own report. See
[Questions](faq.md#what-does-greenline-know-about-me).
