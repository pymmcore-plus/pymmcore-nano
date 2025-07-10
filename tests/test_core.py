from __future__ import annotations

import enum
import time
from typing import TYPE_CHECKING, Callable

import numpy as np
import pymmcore_nano as pmn
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _wait_until(predicate: Callable[[], bool], timeout: float = 1.0, interval=0.05):
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < timeout:
        if predicate():
            return True
        time.sleep(interval)
    raise TimeoutError("Timed out waiting for condition")


def test_version():
    device_version = pmn.DEVICE_INTERFACE_VERSION
    assert isinstance(device_version, int)
    mmcore_version = pmn.MMCore_version
    assert isinstance(mmcore_version, str)
    assert isinstance(pmn.MMCore_version_info, tuple)
    assert str(device_version) in pmn.__version__
    assert mmcore_version in pmn.__version__
    assert isinstance(pmn.__version__, str)


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

    with pytest.raises(pmn.CMMError, match="already in use"):
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
    core.waitForSystem()
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
#    Configuration getConfigState(const char* group, const char* config) noexcept(false)
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
    assert demo_core.getCameraDevice() == "Camera"
    # change image dimensions to make it non-square
    demo_core.setProperty("Camera", "OnCameraCCDXSize", 256)
    expected_shape = (demo_core.getImageHeight(), demo_core.getImageWidth())
    bit_depth = demo_core.getImageBitDepth()
    assert expected_shape == (512, 256)
    assert demo_core.getNumberOfCameraChannels() == 1
    assert demo_core.getCameraChannelName(0) == ""

    demo_core.snapImage()
    img = demo_core.getImage()
    assert isinstance(img, np.ndarray)
    assert not img.flags.writeable
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        img[0, 0] = 0
    img = img.copy()
    assert img.flags.writeable

    assert img.dtype == np.uint16
    assert img.shape == expected_shape
    assert img.dtype.itemsize == demo_core.getBytesPerPixel() == bit_depth // 8 == 2

    demo_core.setProperty("Camera", "PixelType", "8bit")
    demo_core.snapImage()
    img2 = demo_core.getImage()
    assert img2.dtype == np.uint8
    assert img2.dtype.itemsize == demo_core.getBytesPerPixel() == 1

    demo_core.setProperty("Camera", "PixelType", "32bitRGB")
    assert demo_core.getNumberOfComponents() == 4
    demo_core.snapImage()
    img3 = demo_core.getImage()
    assert img3.shape == (*expected_shape, 3)
    assert img3.dtype == np.uint8

    demo_core.setProperty("Camera", "PixelType", "64bitRGB")
    assert demo_core.getNumberOfComponents() == 4
    demo_core.snapImage()
    img4 = demo_core.getImage()
    assert img4.shape == (*expected_shape, 3)
    assert img4.dtype == np.uint16

    demo_core.setProperty("Camera", "Binning", "2")
    demo_core.snapImage()
    img5 = demo_core.getImage(0)  # also testing overloaded method with channel
    assert img5.shape == (256, 128, 3)  # new shape


def test_image_processor(demo_core: pmn.CMMCore) -> None:
    assert demo_core.getCameraDevice() == "Camera"
    demo_core.loadDevice("MedianFilter", "DemoCamera", "MedianFilter")
    demo_core.initializeDevice("MedianFilter")
    demo_core.setImageProcessorDevice("MedianFilter")
    assert demo_core.getImageProcessorDevice() == "MedianFilter"

    demo_core.snapImage()
    demo_core.getImage()


def test_get_image_metadata(demo_core: pmn.CMMCore) -> None:
    assert demo_core.getCameraDevice() == "Camera"
    # change image dimensions to make it non-square
    demo_core.setProperty("Camera", "OnCameraCCDXSize", 256)
    expected_shape = (demo_core.getImageHeight(), demo_core.getImageWidth())
    assert expected_shape == (512, 256)

    demo_core.startSequenceAcquisition(2, 0, False)
    _wait_until(lambda: not demo_core.isSequenceRunning())

    img, md = demo_core.getLastImageMD()
    assert isinstance(img, np.ndarray)
    assert isinstance(md, pmn.Metadata)
    assert img.shape == expected_shape
    assert img.dtype == np.uint16
    assert md.GetSingleTag("Camera").GetValue() == "Camera"
    assert md.GetSingleTag("PixelType").GetValue() == "GRAY16"

    demo_core.setProperty("Camera", "PixelType", "32bitRGB")
    demo_core.startSequenceAcquisition("Camera", 2, 0, False)
    _wait_until(lambda: not demo_core.isSequenceRunning())

    img2, md2 = demo_core.getLastImageMD(0, 0)
    assert img2.shape == (*expected_shape, 3)
    assert img2.dtype == np.uint8
    assert md2.GetSingleTag("PixelType").GetValue() == "RGB32"

    demo_core.setProperty("Camera", "PixelType", "8bit")
    demo_core.startSequenceAcquisition(2, 0, False)
    _wait_until(lambda: not demo_core.isSequenceRunning())
    demo_core.stopSequenceAcquisition()
    # use the overload where we create our own metadata object
    md3 = pmn.Metadata()
    img3 = demo_core.getLastImageMD(md3)
    assert img3.shape == expected_shape
    assert img3.dtype == np.uint8

    with pytest.raises(KeyError, match="Undefined metadata key"):
        md.GetSingleTag("NumberOfComponents")


def test_image_sequence(demo_core: pmn.CMMCore) -> None:
    assert demo_core.getBufferTotalCapacity() == 0
    assert demo_core.getBufferFreeCapacity() == 0

    demo_core.setCircularBufferMemoryFootprint(100)
    assert demo_core.getBufferTotalCapacity() == 200
    assert demo_core.getBufferFreeCapacity() == 200
    assert demo_core.getImageBufferSize() > 400_000

    assert demo_core.getCameraDevice() == "Camera"
    demo_core.setExposure(10)
    assert demo_core.getExposure() == 10
    assert demo_core.getExposure("Camera") == 10
    expected_shape = (demo_core.getImageHeight(), demo_core.getImageWidth())

    demo_core.initializeCircularBuffer()
    demo_core.prepareSequenceAcquisition("Camera")

    demo_core.startContinuousSequenceAcquisition(0)
    _wait_until(lambda: demo_core.isSequenceRunning())
    time.sleep(0.1)
    demo_core.stopSequenceAcquisition("Camera")
    _wait_until(lambda: not demo_core.isSequenceRunning("Camera"))

    assert not demo_core.isBufferOverflowed()
    assert demo_core.getBufferFreeCapacity() < 200
    assert demo_core.getRemainingImageCount() > 1

    with pytest.raises(pmn.CMMError):
        img, md = demo_core.getNBeforeLastImageMD(9999)

    img, md = demo_core.getNBeforeLastImageMD(2)
    assert isinstance(img, np.ndarray)
    assert isinstance(md, pmn.Metadata)
    assert img.shape == expected_shape
    assert img.dtype == np.uint16

    img = demo_core.getLastImage()
    assert isinstance(img, np.ndarray)
    assert img.dtype == np.uint16
    assert img.shape == expected_shape

    img = demo_core.popNextImage()
    assert isinstance(img, np.ndarray)
    assert img.dtype == np.uint16
    assert img.shape == expected_shape

    img2, md = demo_core.popNextImageMD()
    assert isinstance(img2, np.ndarray)
    assert img2.dtype == np.uint16
    assert img2.shape == expected_shape

    while demo_core.getRemainingImageCount():
        img = demo_core.popNextImage()
        assert isinstance(img, np.ndarray)

    assert demo_core.getBufferFreeCapacity() == 200
    demo_core.clearCircularBuffer()


def test_image_sequence_errors(demo_core: pmn.CMMCore) -> None:
    md = pmn.Metadata()
    with pytest.raises(pmn.CMMError):
        demo_core.popNextImage()
    with pytest.raises(pmn.CMMError):
        demo_core.getLastImage()
    with pytest.raises(pmn.CMMError):
        demo_core.popNextImageMD()
    with pytest.raises(pmn.CMMError):
        demo_core.popNextImageMD(md)
    with pytest.raises(pmn.CMMError):
        demo_core.getNBeforeLastImageMD(0, md)


def test_img_seq_no_camera(demo_core: pmn.CMMCore) -> None:
    demo_core.setCameraDevice("")
    assert not demo_core.getCameraDevice()
    assert not demo_core.isSequenceRunning()

    with pytest.raises(pmn.CMMError, match="Camera not loaded"):
        demo_core.startContinuousSequenceAcquisition(0)


def test_camera_roi_change(demo_core: pmn.CMMCore) -> None:
    assert demo_core.getCameraDevice() == "Camera"
    assert demo_core.getROI() == (0, 0, 512, 512)
    demo_core.setROI(10, 10, 100, 100)
    assert demo_core.getROI("Camera") == (10, 10, 100, 100)
    demo_core.clearROI()
    assert demo_core.getROI() == (0, 0, 512, 512)
    assert not demo_core.isMultiROIEnabled()
    assert not demo_core.isMultiROISupported()


def test_feature():
    """Test the StrictInitializationChecks feature."""
    feature_name = "StrictInitializationChecks"
    assert not pmn.CMMCore.isFeatureEnabled(feature_name)
    pmn.CMMCore.enableFeature(feature_name, True)
    assert pmn.CMMCore.isFeatureEnabled(feature_name)
    pmn.CMMCore.enableFeature(feature_name, False)
    assert not pmn.CMMCore.isFeatureEnabled(feature_name)
