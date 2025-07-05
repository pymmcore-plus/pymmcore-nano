# pymmcore-nano

[![License](https://img.shields.io/pypi/l/pymmcore-nano.svg?color=green)](https://github.com/pymmcore-plus/pymmcore-nano/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pymmcore-nano.svg?color=green)](https://pypi.org/project/pymmcore-nano)
[![Python Version](https://img.shields.io/pypi/pyversions/pymmcore-nano.svg?color=green)](https://python.org)
[![CI](https://github.com/pymmcore-plus/pymmcore-nano/actions/workflows/ci.yml/badge.svg)](https://github.com/pymmcore-plus/pymmcore-nano/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pymmcore-plus/pymmcore-nano/branch/main/graph/badge.svg)](https://codecov.io/gh/pymmcore-plus/pymmcore-nano)

Experimental python bindings for [CMMCore](https://github.com/micro-manager/mmCoreAndDevices)
(the device abstraction layer for micro-manager) using [nanobind](https://nanobind.readthedocs.io/en/latest/).

This package can be used as a (mostly) drop-in replacement for [`pymmcore`](https://pypi.org/project/pymmcore/).
There are a few slight differences in behavior.  You are encouraged to try it where you might use 
pymmcore; and [let us know](https://github.com/pymmcore-plus/pymmcore-nano/issues) if you run into any issues!

## Installation

```sh
pip install pymmcore-nano
```

Versioning is the same as for pymmcore.  

```
MMCoreMajor.MMCoreMinor.MMCorePatch.DeviceInterface.pymmcore-nano-build
```

For example, the version `11.3.0.71.2` refers to:

- MMCore version 11.3.0
- Device interface 71
- pymmcore-nano build number of 2 (this is a zero indexed version that resets each time
the MMCore or Device Interface versions increment)


## For Developers

### Clone repo

```sh
git clone https://github.com/pymmcore-plus/pymmcore-nano.git
git submodule update --init
```

### Setup dev environment (editable install)

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

This repo contains a few device adapters that are useful for testing,
in src/mmCoreAndDevices/DeviceAdapters.  These adapters are built as a part of the
installation.  

On windows, in order to build the SequenceTester device (optional) you will also
need boost installed (e.g. `choco install boost-msvc-14.3`, or similar version
according to your version of visual studio)

### Test

Regardless of whether the environment is active, you can run:

```sh
just test
```

or, if the environment is active and you have already run `just install`

```sh
pytest
```

### Releasing

To release a new version:

- update the `PYMMCORE_NANO_VERSION` value in [`_pymmcore_nano.cc`](./src/_pymmcore_nano.cc)
- run `just version`
- commit changes to main
- run `just release`

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
run:

```python
python scripts/update_sources.py
```

After updating, you can test the build and python code as usual.

```sh
just build
pytest
```
