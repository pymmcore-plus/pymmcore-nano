import enum
from pathlib import Path
import sys
import logging
import pytest
import pymmcore_nano as pmn

logger = logging.getLogger(__name__)


DEMO_CFG = Path(__file__).parent / "MMConfig_demo.cfg"


@pytest.fixture
def adapter_paths() -> list[str]:
    adapters = Path(__file__).parent / "adapters" / sys.platform
    if adapters.is_dir():
        return [str(adapters)]
    return []


def test_enums() -> None:
    assert pmn.DeviceType.CameraDevice == 2
    assert isinstance(pmn.DeviceType.CameraDevice, enum.IntEnum)
    assert pmn.DeviceDetectionStatus.Unimplemented == -2
    assert isinstance(pmn.DeviceDetectionStatus.Unimplemented, enum.IntEnum)


def test_core_without_adapters() -> None:
    mmc = pmn.CMMCore()
    assert mmc.getVersionInfo().startswith("MMCore version")
    assert mmc.getLoadedDevices() == ["Core"]


def test_core(adapter_paths: list[str]) -> None:
    if not adapter_paths:
        pytest.skip("No adapters found")

    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths(adapter_paths)
    mmc.loadSystemConfiguration(DEMO_CFG)

    assert "Camera" in mmc.getLoadedDevices()
    cfg = mmc.getConfigState("Channel", "DAPI")
    assert isinstance(cfg, pmn.Configuration)


def test_camera_snap(adapter_paths: list[str]) -> None:
    if not adapter_paths:
        pytest.skip("No adapters found")

    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths(adapter_paths)
    mmc.loadSystemConfiguration(DEMO_CFG)

    assert "Camera" in mmc.getLoadedDevices()
    mmc.snapImage()
    img = mmc.getImage()
    assert img is not None


@pytest.mark.skip(reason="mmc.getROI() is not able to return a valid ROI object")
def test_camera_roi_change(adapter_paths: list[str]) -> None:
    if not adapter_paths:
        pytest.skip("No adapters found")

    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths(adapter_paths)
    mmc.loadSystemConfiguration(DEMO_CFG)

    roi = mmc.getROI()
    assert roi is not None
