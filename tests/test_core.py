import enum
from pathlib import Path
import sys

import pytest
import pymmcore_nano as pmn


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
