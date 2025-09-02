from collections.abc import Iterable, Iterator
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
def demo_config() -> Path:
    return Path(__file__).parent / "MMConfig_demo.cfg"


@pytest.fixture
def demo_core(core: pmn.CMMCore, demo_config: Path) -> pmn.CMMCore:
    """Return a CMMCore instance with the demo configuration loaded."""
    core.loadSystemConfiguration(str(demo_config))
    return core
