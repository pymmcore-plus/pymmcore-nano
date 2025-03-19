import atexit
import os
from pathlib import Path
import sys
from typing import Iterable
import pytest
import pymmcore_nano as pmn
import shutil

BUILDDIR = Path(__file__).parent.parent / "builddir"
BUILT_ADAPTERS = BUILDDIR / "src" / "mmcoreAndDevices" / "DeviceAdapters"


@pytest.fixture(scope="session")
def adapter_paths() -> Iterable[list[str]]:
    lib_ext = {"linux": "so", "darwin": "dylib", "win32": "dll"}[sys.platform]
    adapter_path = Path(__file__).parent / "adapters" / sys.platform
    # find all built libraries in the builddir
    if BUILT_ADAPTERS.is_dir() and (
        libs := [x for x in BUILT_ADAPTERS.rglob(f"*.{lib_ext}")]
    ):
        adapter_path.mkdir(exist_ok=True, parents=True)
        # NOTE: on windows this WILL leave .dll files in the adapter_path
        # after the test is over, since they are locked by the python process.
        atexit.register(lambda: shutil.rmtree(adapter_path, ignore_errors=True))
        for lib in libs:
            # removing extension (using stem) is important,
            # it affects the name of the device library in micromanager.
            lib_name = lib.name if os.name == "nt" else lib.stem
            shutil.copy2(lib, adapter_path / lib_name)
    elif not adapter_path.is_dir():
        pytest.skip(f"No adapters for {sys.platform}")
    yield [str(adapter_path)]


@pytest.fixture
def core(adapter_paths: list[str]) -> pmn.CMMCore:
    """Return a CMMCore instance with the demo configuration loaded."""
    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths(adapter_paths)
    return mmc


@pytest.fixture
def demo_config() -> Path:
    return Path(__file__).parent / "MMConfig_demo.cfg"


@pytest.fixture
def demo_core(core: pmn.CMMCore, demo_config: Path) -> pmn.CMMCore:
    """Return a CMMCore instance with the demo configuration loaded."""
    core.loadSystemConfiguration(str(demo_config))
    return core
