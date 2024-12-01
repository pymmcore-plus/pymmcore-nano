import enum
from pathlib import Path
import sys
import time
from typing import Callable
import pytest
import pymmcore_nano as pmn


def _wait_until(predicate: Callable[[], bool], timeout: float = 1.0, interval=0.05):
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < timeout:
        if predicate():
            return True
        time.sleep(interval)
    raise TimeoutError("Timed out waiting for condition")


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
def demo_core(core: pmn.CMMCore) -> pmn.CMMCore:
    """Return a CMMCore instance with the demo configuration loaded."""
    cfg = Path(__file__).parent / "MMConfig_demo.cfg"
    core.loadSystemConfiguration(cfg)
    return core


def test_enums() -> None:
    assert pmn.DeviceType.CameraDevice == 2
    assert isinstance(pmn.DeviceType.CameraDevice, enum.IntEnum)
    assert pmn.DeviceDetectionStatus.Unimplemented == -2
    assert isinstance(pmn.DeviceDetectionStatus.Unimplemented, enum.IntEnum)


def test_bare_core() -> None:
    """Test basic CMMCore functionality without providing any adapters."""
    mmc = pmn.CMMCore()
    api_version_info = mmc.getAPIVersionInfo()
    assert api_version_info.startswith("Device API version")
    assert str(pmn.DEVICE_INTERFACE_VERSION) in api_version_info
    assert mmc.getVersionInfo().startswith("MMCore version")
    assert mmc.getLoadedDevices() == ["Core"]
    timeout = mmc.getTimeoutMs()
    assert timeout > 0
    mmc.setTimeoutMs(1000)
    assert mmc.getTimeoutMs() == 1000

    with pytest.raises(pmn.CMMError):
        mmc.loadDevice("Camera", "DemoCamera", "DCam")


def test_device_listings(core: pmn.CMMCore) -> None:
    """Test device listing functions."""
    assert core.getDeviceAdapterSearchPaths() != []
    names = core.getDeviceAdapterNames()
    assert "DemoCamera" in names
    devices = core.getAvailableDevices("DemoCamera")
    assert "DCam" in devices
    cam = devices.index("DCam")
    descriptions = core.getAvailableDeviceDescriptions("DemoCamera")
    assert descriptions[cam] == "Demo camera"
    types = core.getAvailableDeviceTypes("DemoCamera")
    assert types[cam] == pmn.DeviceType.CameraDevice


def test_device_loading(core: pmn.CMMCore) -> None:
    """Test device loading functions."""
    LABEL, LIBRARY, DEVICE_NAME = "Camera", "DemoCamera", "DCam"
    core.loadDevice(LABEL, LIBRARY, DEVICE_NAME)
    assert LABEL in core.getLoadedDevices()
    assert core.getDeviceName(LABEL) == DEVICE_NAME
    assert core.getDeviceDescription(LABEL) == "Demo camera"
    assert core.getDeviceType(LABEL) == pmn.DeviceType.CameraDevice
    assert core.getDeviceLibrary(LABEL) == LIBRARY

    with pytest.raises(pmn.CMMError, match="Failed to load device"):
        core.loadDevice(LABEL, LIBRARY, DEVICE_NAME)

    init_state = core.getDeviceInitializationState(LABEL)
    assert init_state == pmn.DeviceInitializationState.Uninitialized
    assert not pmn.DeviceInitializationState.Uninitialized  # test __bool__
    core.initializeDevice(LABEL)
    init_state = core.getDeviceInitializationState(LABEL)
    assert init_state == pmn.DeviceInitializationState.InitializedSuccessfully
    with pytest.raises(pmn.CMMError, match="Device already initialized"):
        core.initializeDevice(LABEL)

    core.unloadDevice(LABEL)
    assert LABEL not in core.getLoadedDevices()
    with pytest.raises(pmn.CMMError, match=f'No device with label "{LABEL}"'):
        core.unloadDevice(LABEL)

    core.loadDevice(LABEL, LIBRARY, DEVICE_NAME)
    core.initializeAllDevices()
    init_state = core.getDeviceInitializationState(LABEL)
    assert init_state == pmn.DeviceInitializationState.InitializedSuccessfully
    core.unloadAllDevices()
    assert LABEL not in core.getLoadedDevices()

    # build it again to call reset()
    core.loadDevice(LABEL, LIBRARY, DEVICE_NAME)
    assert LABEL in core.getLoadedDevices()
    core.initializeDevice(LABEL)
    assert core.getDeviceInitializationState(LABEL)
    core.reset()
    assert LABEL not in core.getLoadedDevices()
    assert core.getLoadedDevices() == ["Core"]
    with pytest.raises(pmn.CMMError, match=f'No device with label "{LABEL}"'):
        assert core.getDeviceInitializationState(LABEL)


#    void reset() noexcept(false);

#    void unloadLibrary(const char* moduleName) noexcept(false);

#    void updateCoreProperties() noexcept(false);

#    std::string getCoreErrorText(int code) const;

#    std::string getVersionInfo() const;
#    std::string getAPIVersionInfo() const;
#    Configuration getSystemState();
#    void setSystemState(const Configuration& conf);
#    Configuration getConfigState(const char* group, const char* config) noexcept(false);
#    Configuration getConfigGroupState(const char* group) noexcept(false);
#    void saveSystemState(const char* fileName) noexcept(false);
#    void loadSystemState(const char* fileName) noexcept(false);
#    void saveSystemConfiguration(const char* fileName) noexcept(false);
#    void loadSystemConfiguration(const char* fileName) noexcept(false);
#    void registerCallback(MMEventCallback* cb);


# have to use capfd to capture stderr, capsys won't work
def test_core_logging(capfd: pytest.CaptureFixture, tmp_path: Path) -> None:
    mmc = pmn.CMMCore()
    # no file logging at start
    assert not mmc.getPrimaryLogFile()
    # stderr logging disabled at start
    msg = "test logging"
    mmc.logMessage(msg)
    with pytest.raises(TimeoutError):
        _wait_until(lambda: msg in capfd.readouterr().err, timeout=0.1)

    # test file logging
    logfile = tmp_path / "test.log"
    mmc.setPrimaryLogFile(logfile)
    assert mmc.getPrimaryLogFile() == str(logfile)
    msg = "test file logging"
    mmc.logMessage(msg)
    _wait_until(lambda: msg in logfile.read_text())
    mmc.setPrimaryLogFile("")
    assert not mmc.getPrimaryLogFile()
    logfile.write_text("")
    mmc.logMessage(msg)
    with pytest.raises(TimeoutError):
        _wait_until(lambda: msg in logfile.read_text(), timeout=0.1)

    # secondary log file
    logfile2 = tmp_path / "test2.log"
    handle = mmc.startSecondaryLogFile(logfile2, enableDebug=True)
    assert isinstance(handle, int)
    assert not logfile2.read_text()
    msg = "test secondary file logging"
    mmc.logMessage(msg)
    _wait_until(lambda: msg in logfile2.read_text())
    mmc.stopSecondaryLogFile(handle)

    # test stderr logging
    mmc.enableStderrLog(True)
    assert mmc.stderrLogEnabled()
    msg = "test stderr logging"
    mmc.logMessage(msg)
    _wait_until(lambda: f"[IFO,App] {msg}" in capfd.readouterr().err)

    # test debug logging
    assert not mmc.debugLogEnabled()
    mmc.enableDebugLog(True)
    assert mmc.debugLogEnabled()
    msg = "test debug logging"
    mmc.logMessage(msg, True)  # log only in debug mode
    _wait_until(lambda: f"[dbg,App] {msg}" in capfd.readouterr().err)

    mmc.enableStderrLog(False)
    assert not mmc.stderrLogEnabled()


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
