import enum
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
def demo_core(adapter_paths: list[str]) -> pmn.CMMCore:
    """Return a CMMCore instance with the demo configuration loaded."""
    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths(adapter_paths)
    cfg = Path(__file__).parent / "MMConfig_demo.cfg"
    mmc.loadSystemConfiguration(cfg)
    return mmc


def test_enums() -> None:
    assert pmn.DeviceType.CameraDevice == 2
    assert isinstance(pmn.DeviceType.CameraDevice, enum.IntEnum)
    assert pmn.DeviceDetectionStatus.Unimplemented == -2
    assert isinstance(pmn.DeviceDetectionStatus.Unimplemented, enum.IntEnum)


def test_core_without_adapters() -> None:
    mmc = pmn.CMMCore()
    assert mmc.getVersionInfo().startswith("MMCore version")
    assert mmc.getLoadedDevices() == ["Core"]


def test_core(demo_core: pmn.CMMCore) -> None:
    assert "Camera" in demo_core.getLoadedDevices()
    cfg = demo_core.getConfigState("Channel", "DAPI")
    assert isinstance(cfg, pmn.Configuration)


def test_camera_snap(demo_core: pmn.CMMCore) -> None:
    assert "Camera" in demo_core.getLoadedDevices()
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img is not None


def test_camera_roi_change(demo_core: pmn.CMMCore) -> None:
    assert demo_core.getROI() == (0, 0, 512, 512)
    demo_core.setROI(10, 10, 100, 100)
    assert demo_core.getROI() == (10, 10, 100, 100)
