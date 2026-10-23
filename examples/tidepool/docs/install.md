# Installation

## Requirements

- **Python 3.11** or later. Continuous integration runs 3.11, 3.12 and 3.13.
- No compiler and no system libraries. The only dependency is the standard library.

## Install

```bash
pip install tidepool
```

From a clone, for development:

```bash
git clone https://github.com/example/tidepool
cd tidepool
pip install -e ".[dev]"
```

!!! note "Logs outlive installations"
    A log written by one version is readable by every later version. The reverse is not
    promised: a log written by a newer release may use an entry type an older one does
    not know, and replay will say so rather than skip it.

## Check the install

```bash
tidepool --version
```

```python
from tidepool import Run

with Run.open("smoke.log") as run:
    run.record(value=1)
assert len(list(Run.replay("smoke.log"))) == 1
```

If that runs without output, the install is working. If `tidepool` is not found on the
command line but the import works, the console script is not on `PATH` — the usual
cause is a user-level install whose `bin` directory is not in the shell's `PATH`.
