# Questions

## Why does it route me onto an arterial road sometimes?

Because the default route trades a short unprotected stretch against a long detour, and
it thought the detour was worse. It always names the stretch. If you disagree with the
trade, `--avoid-unprotected` or `--max-gap` will make a different one — see
[Planning a route](usage.md#the-options).

## Why is the time estimate so pessimistic?

It assumes 15 km/h and ignores traffic lights, so on a route with many junctions it is
a lower bound that reads as slow. A better estimate would need light timings nobody
here has. See the note on [Planning a route](usage.md#reading-the-output).

## What does Greenline know about me?

Nothing that leaves your machine, except a blockage report if you file one, and that
carries a timestamp, a reason, and a local signing key — no account, no email address,
no location history. Routing is entirely offline once the map is downloaded.

## Can I use it in another city?

Not as it stands. The lane map is this city's, and routes outside its bounding box are
rejected. The code has no city-specific logic in it, so another group could run their
own instance with their own map, but that is a project rather than a configuration
change.

## Is there a phone app?

No, and there is unlikely to be one. None of the volunteers wants to maintain a mobile
app, and saying so is more honest than leaving the question open for three years.

## A lane has been blocked for months. Why does it keep coming back?

Because most blockage reasons expire, so a blockage nobody re-reports disappears from
the map. If a lane is permanently gone, it should be reported as `removed`, which does
not expire. See [Reporting a blockage](blockages.md#the-reasons).

## I surveyed a lane and the pull request got questions back. Is that normal?

Yes — roughly one survey in five. The usual question is about the width measurement,
because "narrowest point" catches people out. See
[Adding a lane](adding-a-lane.md#survey-a-segment).

## Who decides what counts as protected?

The volunteers did, by vote, and the result is the table on
[Adding a lane](adding-a-lane.md#what-counts-as-protected). Wand posts count; paint
does not. Reopening that argument needs a new vote, not a new pull request.
