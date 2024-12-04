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

### test

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
