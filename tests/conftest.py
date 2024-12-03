from pathlib import Path
import sys
import pytest
import pymmcore_nano as pmn


@pytest.fixture
def adapter_paths() -> list[str]:
    adapters = Path(__file__).parent / "adapters" / sys.platform
    if not adapters.is_dir():
        pytest.skip(f"No adapters for {sys.platform}")
    return [str(adapters)]


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
