import os
import sys
from collections.abc import Callable, Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pymmcore_nano as pmn
import pytest


@pytest.fixture(scope="session")
def adapter_paths() -> Iterable[list[str]]:
    # find all built libraries in the builddir
    from mm_test_adapters import device_adapter_path

    yield [str(device_adapter_path())]


@pytest.fixture
def core(adapter_paths: list[str]) -> Iterator[pmn.CMMCore]:
    """Return a CMMCore instance with the demo configuration loaded."""
    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths(adapter_paths)
    yield mmc
    mmc.registerCallback(None)


@pytest.fixture
def stderr_to_file(
    tmp_path: Path,
) -> Callable[[], AbstractContextManager[Callable[[], str]]]:
    """Return a context manager that redirects fd 2 to a file, for reading stderr.

    Unlike `capfd.readouterr()`, reading doesn't truncate anything, which races
    with MMCore's logging thread writing to stderr (losing output, or leaving NULs).
    The redirect has to happen in the test body: pytest re-applies its own fd
    capture after fixture setup.
    """

    @contextmanager
    def _redirect() -> Iterator[Callable[[], str]]:
        path = tmp_path / "stderr.txt"
        sys.stderr.flush()
        saved = os.dup(2)
        with open(path, "wb") as f:
            os.dup2(f.fileno(), 2)
        try:
            yield lambda: path.read_bytes().decode(errors="replace")
        finally:
            sys.stderr.flush()
            os.dup2(saved, 2)
            os.close(saved)

    return _redirect


@pytest.fixture
def demo_config() -> Path:
    return Path(__file__).parent / "MMConfig_demo.cfg"


@pytest.fixture
def demo_core(core: pmn.CMMCore, demo_config: Path) -> pmn.CMMCore:
    """Return a CMMCore instance with the demo configuration loaded."""
    core.loadSystemConfiguration(str(demo_config))
    return core
