# Installation

## Requirements

- **Python 3.11** or later, which is what the command-line tool is written in.
- About 40 MB of disk for the lane map.
- A network connection for `greenline data refresh`. Routing itself is offline.

## Install

```bash
pipx install greenline
```

`pipx` keeps it in its own environment, which is what you want for a command-line tool.
With plain `pip`:

```bash
pip install --user greenline
```

## Get the lane data

```bash
greenline data refresh
```

This downloads the current map into `~/.local/share/greenline/`. It is a few seconds on
a normal connection. Run it again whenever you want the latest blockage reports; a map
older than 30 days prints a warning on every route.

```bash
greenline data status
```

```text
lane map:   2026-10-19 (3 days old)
lanes:      1,284 segments, 412 km
blockages:  7 active, 2 expiring this week
```

## Check the install

```bash
greenline route "Harbour Market" "Quay Path"
```

Any route that prints segments is a working install. If you get `no lane data`, the
refresh has not run; if you get `command not found` but `pip show greenline` works, the
`pipx` or user `bin` directory is not on your `PATH`.

!!! note "Uninstalling leaves the data behind"
    `pipx uninstall greenline` removes the tool but not `~/.local/share/greenline/`.
    Delete that directory too if you want it gone.
