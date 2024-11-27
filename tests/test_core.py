import enum
from pathlib import Path
import pymmcore_nano as pmn
import pytest
import os
import sys
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def demo_camera_dll():
    return os.path.join(os.path.dirname(__file__), "device", "mmgr_dal_DemoCamera.dll")


root = Path.home() / "Library/Application Support/pymmcore-plus/mm"
mm = next(root.glob("Micro-Manager-*"), None)
paths = [str(mm)] if mm else []


def test_enums():
    assert pmn.DeviceType.CameraDevice == 2
    assert isinstance(pmn.DeviceType.CameraDevice, enum.IntEnum)
    assert pmn.DeviceDetectionStatus.Unimplemented == -2
    assert isinstance(pmn.DeviceDetectionStatus.Unimplemented, enum.IntEnum)

    mmc = pmn.CMMCore()
    assert mmc.getVersionInfo().startswith("MMCore version")
    assert mmc.getLoadedDevices() == ["Core"]
    mmc.setDeviceAdapterSearchPaths(paths)

    if mm:
        mmc.loadSystemConfiguration(mm / "MMConfig_demo.cfg")
        assert "Camera" in mmc.getLoadedDevices()
        cfg = mmc.getConfigState("Channel", "DAPI")
        assert isinstance(cfg, pmn.Configuration)


@pytest.mark.skipif(sys.platform != "win32", reason="DLL works only on Windows")
def test_camera_device(demo_camera_dll: str) -> None:
    """Tests that the built core can load a camera device from a local DLL."""
    logger.info("Testing camera device loading; path: %s", demo_camera_dll)
    mmc = pmn.CMMCore()
    mmc.setDeviceAdapterSearchPaths([demo_camera_dll])
    mmc.loadDevice("Camera", "DemoCamera", "DCam")
    mmc.initializeAllDevices()
    assert "DCam" in mmc.getLoadedDevices()
    assert mmc.getDeviceName("Camera") == "DCam"
    assert mmc.getDeviceDescription("DCam") == "Demo Camera"
    assert mmc.getDeviceLibrary("DCam") == demo_camera_dll
