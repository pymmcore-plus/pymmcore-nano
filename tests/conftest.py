from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Iterable
import pytest
import pymmcore_nano as pmn

BUILDDIR = Path(__file__).parent.parent / "builddir"
BUILT_ADAPTERS = BUILDDIR / "src" / "mmcoreAndDevices" / "DeviceAdapters"


@pytest.fixture(scope="session")
def adapter_paths() -> Iterable[list[str]]:
    lib_ext = {"linux": "so", "darwin": "dylib", "win32": "dll"}[sys.platform]
    # find all built libraries in the builddir
    if BUILT_ADAPTERS.is_dir() and (
        libs := [x for x in BUILT_ADAPTERS.rglob(f"*.{lib_ext}")]
    ):
        # copy them to a new temporary directory
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            for lib in libs:
                lib.rename(tmp_path / lib.stem)
            yield [str(tmpdir)]
    else:
        adapters = Path(__file__).parent / "adapters" / sys.platform
        if not adapters.is_dir():
            pytest.skip(f"No adapters for {sys.platform}")
        yield [str(adapters)]


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
