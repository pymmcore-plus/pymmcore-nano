# pymmcore-nano

[![License](https://img.shields.io/pypi/l/pymmcore-nano.svg?color=green)](https://github.com/pymmcore-plus/pymmcore-nano/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pymmcore-nano.svg?color=green)](https://pypi.org/project/pymmcore-nano)
[![Python Version](https://img.shields.io/pypi/pyversions/pymmcore-nano.svg?color=green)](https://python.org)
[![CI](https://github.com/pymmcore-plus/pymmcore-nano/actions/workflows/ci.yml/badge.svg)](https://github.com/pymmcore-plus/pymmcore-nano/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pymmcore-plus/pymmcore-nano/branch/main/graph/badge.svg)](https://codecov.io/gh/pymmcore-plus/pymmcore-nano)

Experimental python bindings for CMMCore using nanobind.

## Clone repo

```sh
git clone https://github.com/pymmcore-plus/pymmcore-nano.git
git submodule update --init
```

## Setup dev environment (editable install)

Make sure you have uv installed: <https://docs.astral.sh/uv/getting-started/installation/>

This project uses `just` as a task runner.
If you have `just` installed (e.g. `brew install just`), you can fully setup the project with:

```sh
just install
```

If you prefer not to install `just` globally, you can install it with the rest of the
project dependencies using uv.  Then activate the environment and call `just install`

```sh
uv sync --no-install-project
. .venv/bin/activate  # Windows: .venv\Scripts\activate
just install
```

### Test

Regardless of whether the environment is active, you can run:

```sh
just test
# or
just test-cov
```

or, if the environment is active:

```sh
pytest
```

### Building Device Adapters

This repo contains a few device adapters that are useful for testing,
in src/mmCoreAndDevices/DeviceAdapters.  To build these, you can run:

```sh
just build-devices
```

Or, to build a specific device within the DeviceAdapters subdirectory, you can run:

```sh
just build-adapter DemoCamera
```

### Updating `mmCoreAndDevices` source code

Rather than using git submodules, this repository checks in the
[`mmCoreAndDevices`](https://github.com/micro-manager/mmCoreAndDevices) source
code. This makes measuring C++ code coverage easier, as the `mmCoreAndDevices`
code is included in the same repository (see codecov results
[here](https://app.codecov.io/gh/pymmcore-plus/pymmcore-nano/tree/main/src%2FmmCoreAndDevices)),
and it also makes it easier to make changes to the `mmCoreAndDevices` code
directly from this repository (e.g., to fix bugs or add features that are
pending in the upstream repo).

To bring in new changes from the upstream `mmCoreAndDevices` repository, you can
run two scripts:

```python
python scripts/update_sources.py
python scripts/patch_sources.py
```

The first script (`update_sources.py`) will update the `src/mmCoreAndDevices`
directory with the latest changes from the `mmCoreAndDevices` repository,
*overwriting* any changes in the local repo.

The second script (`patch_sources.py`) replays all of the changes that we
want to make to the sources in order to build the project. This includes changes
to the `CMakeLists.txt` files.  This essentially means that all changes to the
source MUST be `patch_sources.py`, which serves as a nice record of changes that
should be upstreamed.

After running these scripts, you can test the build and python code as usual.

```sh
just build
pytest
```
