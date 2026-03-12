"""Tests targeting uncovered functions in MMCore.cpp."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pymmcore_nano as pmn
import pytest

if TYPE_CHECKING:
    from pathlib import Path


# ── Property operations ─────────────────────────────────────────────────────


def test_property_type_and_limits(demo_core: pmn.CMMCore) -> None:
    dev = "Camera"
    prop = "Exposure"
    assert demo_core.getPropertyType(dev, prop) == pmn.PropertyType.Float

    has_limits = demo_core.hasPropertyLimits(dev, prop)
    assert isinstance(has_limits, bool)
    if has_limits:
        lo = demo_core.getPropertyLowerLimit(dev, prop)
        hi = demo_core.getPropertyUpperLimit(dev, prop)
        assert lo <= hi


def test_allowed_property_values(demo_core: pmn.CMMCore) -> None:
    dev = "Camera"
    allowed = demo_core.getAllowedPropertyValues(dev, "Binning")
    assert isinstance(allowed, tuple)
    assert len(allowed) > 0


def test_property_sequenceable(demo_core: pmn.CMMCore) -> None:
    dev = "Camera"
    prop = "Exposure"
    is_seq = demo_core.isPropertySequenceable(dev, prop)
    assert isinstance(is_seq, bool)
    if is_seq:
        max_len = demo_core.getPropertySequenceMaxLength(dev, prop)
        assert max_len >= 0


def test_set_property_numeric_overloads(demo_core: pmn.CMMCore) -> None:
    demo_core.setProperty("Camera", "Exposure", 25.0)
    assert demo_core.getProperty("Camera", "Exposure") == "25.0000"
    demo_core.setProperty("Camera", "Exposure", 10.0)
    assert demo_core.getProperty("Camera", "Exposure") == "10.0000"
    # bool overload maps True -> "1"
    demo_core.setProperty("Camera", "TransposeCorrection", True)
    assert demo_core.getProperty("Camera", "TransposeCorrection") == "1"
    demo_core.setProperty("Camera", "TransposeCorrection", False)
    assert demo_core.getProperty("Camera", "TransposeCorrection") == "0"


# ── Exposure and binning ────────────────────────────────────────────────────


def test_exposure_overloads(demo_core: pmn.CMMCore) -> None:
    demo_core.setExposure(20.0)
    assert demo_core.getExposure() == 20.0
    assert demo_core.getExposure("Camera") == 20.0

    demo_core.setExposure("Camera", 30.0)
    assert demo_core.getExposure("Camera") == 30.0


def test_binning_overloads(demo_core: pmn.CMMCore) -> None:
    demo_core.setBinning(1)
    assert demo_core.getBinning() == 1
    assert demo_core.getBinning("Camera") == 1

    demo_core.setBinning("Camera", 2)
    assert demo_core.getBinning("Camera") == 2
    demo_core.setBinning(1)

    vals = demo_core.getAllowedBinningValues()
    assert isinstance(vals, tuple)
    vals2 = demo_core.getAllowedBinningValues("Camera")
    assert vals == vals2


# ── Exposure sequencing ─────────────────────────────────────────────────────


def test_exposure_sequenceable(demo_core: pmn.CMMCore) -> None:
    # Enable exposure sequencing on the demo camera
    demo_core.setProperty("Camera", "UseExposureSequences", "Yes")

    assert demo_core.isExposureSequenceable("Camera")
    max_len = demo_core.getExposureSequenceMaxLength("Camera")
    assert max_len > 0

    demo_core.loadExposureSequence("Camera", [10.0, 20.0, 30.0])
    demo_core.startExposureSequence("Camera")
    demo_core.stopExposureSequence("Camera")

    demo_core.setProperty("Camera", "UseExposureSequences", "No")


# ── Stage origin operations ─────────────────────────────────────────────────


def test_z_stage_origin_operations(demo_core: pmn.CMMCore) -> None:
    demo_core.setPosition("Z", 50.0)
    demo_core.waitForDevice("Z")
    demo_core.setOrigin("Z")
    demo_core.setOrigin()


def test_xy_stage_origin_operations(demo_core: pmn.CMMCore) -> None:
    demo_core.setOriginXY("XY")
    demo_core.setOriginXY()
    with pytest.raises(pmn.CMMError):
        demo_core.setOriginX("XY")
    with pytest.raises(pmn.CMMError):
        demo_core.setOriginY("XY")
    with pytest.raises(pmn.CMMError):
        demo_core.setOriginX()
    with pytest.raises(pmn.CMMError):
        demo_core.setOriginY()
    demo_core.setAdapterOriginXY(100.0, 200.0)
    demo_core.setAdapterOriginXY("XY", 100.0, 200.0)


def test_stage_home(demo_core: pmn.CMMCore) -> None:
    with pytest.raises(pmn.CMMError):
        demo_core.home("Z")


# ── Stage sequencing ────────────────────────────────────────────────────────


def test_stage_sequencing(demo_core: pmn.CMMCore) -> None:
    demo_core.setProperty("Z", "UseSequences", "Yes")

    assert demo_core.isStageSequenceable("Z")
    max_len = demo_core.getStageSequenceMaxLength("Z")
    assert max_len > 0

    demo_core.loadStageSequence("Z", [1.0, 2.0, 3.0])
    demo_core.startStageSequence("Z")
    demo_core.stopStageSequence("Z")

    is_linear = demo_core.isStageLinearSequenceable("Z")
    assert isinstance(is_linear, bool)

    uses_cb = demo_core.isStageUsingCallbacks("Z")
    assert isinstance(uses_cb, bool)

    demo_core.setProperty("Z", "UseSequences", "No")


# ── XY position tuple overload ──────────────────────────────────────────────


def test_xy_position_tuple(demo_core: pmn.CMMCore) -> None:
    target = (10.0, 20.0)
    demo_core.setXYPosition("XY", *target)
    demo_core.waitForDevice("XY")
    assert demo_core.getXYPosition("XY") == pytest.approx(target, abs=1e-2)
    assert demo_core.getXYPosition() == pytest.approx(target, abs=1e-2)


# ── Config group management ─────────────────────────────────────────────────


def test_rename_config_group(demo_core: pmn.CMMCore) -> None:
    demo_core.defineConfigGroup("TempGroup")
    assert "TempGroup" in demo_core.getAvailableConfigGroups()
    demo_core.renameConfigGroup("TempGroup", "RenamedGroup")
    groups = demo_core.getAvailableConfigGroups()
    assert "TempGroup" not in groups
    assert "RenamedGroup" in groups
    demo_core.deleteConfigGroup("RenamedGroup")


def test_config_crud(demo_core: pmn.CMMCore) -> None:
    group = "TestCRUD"
    demo_core.defineConfigGroup(group)
    demo_core.defineConfig(group, "preset1")
    demo_core.defineConfig(group, "preset2", "Camera", "Binning", "1")

    configs = demo_core.getAvailableConfigs(group)
    assert "preset1" in configs
    assert "preset2" in configs

    demo_core.renameConfig(group, "preset1", "renamedPreset")
    configs = demo_core.getAvailableConfigs(group)
    assert "renamedPreset" in configs
    assert "preset1" not in configs

    demo_core.deleteConfig(group, "preset2", "Camera", "Binning")
    demo_core.deleteConfig(group, "renamedPreset")
    demo_core.deleteConfigGroup(group)


def test_config_state(demo_core: pmn.CMMCore) -> None:
    state = demo_core.getConfigState("Channel", "DAPI")
    assert isinstance(state, pmn.Configuration)

    group_state = demo_core.getConfigGroupState("Channel")
    assert isinstance(group_state, pmn.Configuration)

    cached = demo_core.getConfigGroupStateFromCache("Channel")
    assert isinstance(cached, pmn.Configuration)


# ── Pixel size config ───────────────────────────────────────────────────────


def test_pixel_size_config_lifecycle(demo_core: pmn.CMMCore) -> None:
    name = "TestPixelSize"
    demo_core.definePixelSizeConfig(name)
    assert demo_core.isPixelSizeConfigDefined(name)

    demo_core.setPixelSizeUm(name, 0.5)

    affine = [0.5, 0.0, 0.0, 0.0, 0.5, 0.0]
    demo_core.setPixelSizeAffine(name, affine)

    demo_core.renamePixelSizeConfig(name, "RenamedPx")
    assert demo_core.isPixelSizeConfigDefined("RenamedPx")
    assert not demo_core.isPixelSizeConfigDefined(name)

    demo_core.deletePixelSizeConfig("RenamedPx")
    assert not demo_core.isPixelSizeConfigDefined("RenamedPx")


def test_pixel_size_config_with_property(demo_core: pmn.CMMCore) -> None:
    name = "TestPxProp"
    demo_core.definePixelSizeConfig(name, "Camera", "Binning", "1")
    assert demo_core.isPixelSizeConfigDefined(name)
    demo_core.setPixelSizeUm(name, 0.325)

    data = demo_core.getPixelSizeConfigData(name)
    assert isinstance(data, pmn.Configuration)

    demo_core.deletePixelSizeConfig(name)


def test_current_pixel_size(demo_core: pmn.CMMCore) -> None:
    cfg = demo_core.getCurrentPixelSizeConfig()
    assert isinstance(cfg, str)
    cached = demo_core.getCurrentPixelSizeConfig(True)
    assert isinstance(cached, str)

    um = demo_core.getPixelSizeUm()
    assert isinstance(um, float)

    affine = demo_core.getPixelSizeAffine()
    assert isinstance(affine, tuple)
    assert len(affine) == 6

    cached_affine = demo_core.getPixelSizeAffine(True)
    assert isinstance(cached_affine, tuple)


def test_pixel_size_by_id(demo_core: pmn.CMMCore) -> None:
    configs = demo_core.getAvailablePixelSizeConfigs()
    if configs:
        name = configs[0]
        um = demo_core.getPixelSizeUmByID(name)
        assert isinstance(um, float)
        affine = demo_core.getPixelSizeAffineByID(name)
        assert isinstance(affine, tuple)
        assert len(affine) == 6


def test_pixel_size_dxdz_dydz(demo_core: pmn.CMMCore) -> None:
    name = "TestDxDz"
    demo_core.definePixelSizeConfig(name, "Camera", "Binning", "1")
    demo_core.setPixelSizeUm(name, 0.5)
    demo_core.setPixelSizedxdz(name, 0.1)
    demo_core.setPixelSizedydz(name, 0.2)
    demo_core.setPixelSizeOptimalZUm(name, 5.0)

    dxdz = demo_core.getPixelSizedxdz(name)
    assert dxdz == pytest.approx(0.1)
    dydz = demo_core.getPixelSizedydz(name)
    assert dydz == pytest.approx(0.2)
    oz = demo_core.getPixelSizeOptimalZUm(name)
    assert oz == pytest.approx(5.0)

    demo_core.setPixelSizeConfig(name)
    demo_core.getPixelSizedxdz()
    demo_core.getPixelSizedxdz(True)
    demo_core.getPixelSizedydz()
    demo_core.getPixelSizedydz(True)
    demo_core.getPixelSizeOptimalZUm()
    demo_core.getPixelSizeOptimalZUm(True)

    demo_core.deletePixelSizeConfig(name)


# ── Device info ─────────────────────────────────────────────────────────────


def test_device_info(demo_core: pmn.CMMCore) -> None:
    assert demo_core.getDeviceName("Camera") == "DCam"
    assert demo_core.getDeviceDescription("Camera") == "Demo camera"
    assert demo_core.getDeviceLibrary("Camera") == "DemoCamera"
    assert demo_core.getDeviceType("Camera") == pmn.DeviceType.CameraDevice

    state = demo_core.getDeviceInitializationState("Camera")
    assert state == pmn.DeviceInitializationState.InitializedSuccessfully

    parent = demo_core.getParentLabel("Camera")
    assert isinstance(parent, str)


def test_set_parent_label(demo_core: pmn.CMMCore) -> None:
    parent = demo_core.getParentLabel("Camera")
    demo_core.setParentLabel("Camera", parent)
    assert demo_core.getParentLabel("Camera") == parent


def test_device_property_names(demo_core: pmn.CMMCore) -> None:
    names = demo_core.getDevicePropertyNames("Camera")
    assert isinstance(names, tuple)
    assert len(names) > 0


def test_installed_devices(demo_core: pmn.CMMCore) -> None:
    devs = demo_core.getInstalledDevices("DHub")
    assert isinstance(devs, tuple)
    assert len(devs) > 0

    if devs:
        desc = demo_core.getInstalledDeviceDescription("DHub", devs[0])
        assert isinstance(desc, str)


def test_loaded_peripheral_devices(demo_core: pmn.CMMCore) -> None:
    peripherals = demo_core.getLoadedPeripheralDevices("DHub")
    assert isinstance(peripherals, tuple)
    assert len(peripherals) > 0


# ── Save / Load system state ───────────────────────────────────────────────


def test_save_load_system_state(demo_core: pmn.CMMCore, tmp_path: Path) -> None:
    state_file = tmp_path / "state.cfg"
    demo_core.saveSystemState(str(state_file))
    assert state_file.exists()
    assert state_file.stat().st_size > 0


def test_save_load_system_configuration(demo_core: pmn.CMMCore, tmp_path: Path) -> None:
    cfg_file = str(tmp_path / "config.cfg")
    demo_core.saveSystemConfiguration(cfg_file)
    demo_core.loadSystemConfiguration(cfg_file)


# ── Device busy / wait ──────────────────────────────────────────────────────


def test_device_busy_and_wait(demo_core: pmn.CMMCore) -> None:
    assert isinstance(demo_core.deviceBusy("Camera"), bool)
    demo_core.waitForDevice("Camera")

    assert isinstance(demo_core.systemBusy(), bool)
    demo_core.waitForSystem()


# ── Circular buffer ─────────────────────────────────────────────────────────


def test_circular_buffer_memory(demo_core: pmn.CMMCore) -> None:
    demo_core.setCircularBufferMemoryFootprint(50)
    footprint = demo_core.getCircularBufferMemoryFootprint()
    assert footprint == 50
    demo_core.clearCircularBuffer()


# ── ROI overloads ───────────────────────────────────────────────────────────


def test_roi_device_overloads(demo_core: pmn.CMMCore) -> None:
    demo_core.setROI("Camera", 10, 10, 100, 100)
    roi = demo_core.getROI("Camera")
    assert roi == (10, 10, 100, 100)

    demo_core.setROI(20, 20, 200, 200)
    roi = demo_core.getROI()
    assert roi == (20, 20, 200, 200)

    demo_core.clearROI()


# ── Snap / getImage overloads ───────────────────────────────────────────────


def test_snap_and_get_image(demo_core: pmn.CMMCore) -> None:
    demo_core.snapImage()
    img = demo_core.getImage()
    assert img is not None
    img2 = demo_core.getImage(0)  # channel overload
    assert img2 is not None


# ── MultiROI ────────────────────────────────────────────────────────────────


def test_multi_roi_supported(demo_core: pmn.CMMCore) -> None:
    assert isinstance(demo_core.isMultiROISupported(), bool)
    assert isinstance(demo_core.isMultiROIEnabled(), bool)


# ── Device adapter names ────────────────────────────────────────────────────


def test_get_device_adapter_names(core: pmn.CMMCore) -> None:
    names = core.getDeviceAdapterNames()
    assert isinstance(names, tuple)
    assert "DemoCamera" in names


# ── Default device setters ──────────────────────────────────────────────────


def test_default_device_setters(demo_core: pmn.CMMCore) -> None:
    demo_core.setCameraDevice("Camera")
    assert demo_core.getCameraDevice() == "Camera"

    demo_core.setFocusDevice("Z")
    assert demo_core.getFocusDevice() == "Z"

    demo_core.setXYStageDevice("XY")
    assert demo_core.getXYStageDevice() == "XY"

    demo_core.setShutterDevice("White Light Shutter")
    assert demo_core.getShutterDevice() == "White Light Shutter"

    demo_core.setAutoFocusDevice("Autofocus")
    assert demo_core.getAutoFocusDevice() == "Autofocus"

    demo_core.setChannelGroup("Channel")
    assert demo_core.getChannelGroup() == "Channel"


def test_set_galvo_device(demo_core: pmn.CMMCore) -> None:
    demo_core.setGalvoDevice("")
    assert demo_core.getGalvoDevice() == ""


def test_set_slm_device(demo_core: pmn.CMMCore) -> None:
    demo_core.setSLMDevice("")
    assert demo_core.getSLMDevice() == ""


def test_set_image_processor_device(demo_core: pmn.CMMCore) -> None:
    demo_core.setImageProcessorDevice("")
    assert demo_core.getImageProcessorDevice() == ""


# ── waitForConfig ───────────────────────────────────────────────────────────


def test_wait_for_config(demo_core: pmn.CMMCore) -> None:
    demo_core.setConfig("Channel", "DAPI")
    demo_core.waitForConfig("Channel", "DAPI")


# ── detect device ───────────────────────────────────────────────────────────


def test_supports_device_detection(core: pmn.CMMCore) -> None:
    core.loadDevice("Cam", "DemoCamera", "DCam")
    core.initializeDevice("Cam")
    result = core.supportsDeviceDetection("Cam")
    assert isinstance(result, bool)


# ── unloadLibrary ───────────────────────────────────────────────────────────


def test_unload_library(core: pmn.CMMCore) -> None:
    core.loadDevice("Cam", "DemoCamera", "DCam")
    core.initializeDevice("Cam")
    core.unloadDevice("Cam")
    core.unloadLibrary("DemoCamera")


# ── setProperty on int-like prop ────────────────────────────────────────────


def test_set_property_int(demo_core: pmn.CMMCore) -> None:
    demo_core.setProperty("Camera", "OnCameraCCDXSize", "512")
    val = demo_core.getProperty("Camera", "OnCameraCCDXSize")
    assert val == "512"


# ── Galvo device ────────────────────────────────────────────────────────────


@pytest.fixture
def galvo_core(core: pmn.CMMCore) -> pmn.CMMCore:
    core.loadDevice("Galvo", "DemoCamera", "DGalvo")
    core.initializeDevice("Galvo")
    core.setGalvoDevice("Galvo")
    return core


def test_galvo_basic(galvo_core: pmn.CMMCore) -> None:
    assert galvo_core.getGalvoDevice() == "Galvo"
    galvo_core.setGalvoPosition("Galvo", 1.0, 2.0)
    x, y = galvo_core.getGalvoPosition("Galvo")
    assert isinstance(x, float)
    assert isinstance(y, float)

    galvo_core.setGalvoIlluminationState("Galvo", True)
    galvo_core.setGalvoIlluminationState("Galvo", False)

    galvo_core.setGalvoSpotInterval("Galvo", 10.0)
    galvo_core.pointGalvoAndFire("Galvo", 5.0, 5.0, 100.0)

    channel = galvo_core.getGalvoChannel("Galvo")
    assert isinstance(channel, str)


def test_galvo_ranges(galvo_core: pmn.CMMCore) -> None:
    xrange = galvo_core.getGalvoXRange("Galvo")
    assert isinstance(xrange, float)
    yrange = galvo_core.getGalvoYRange("Galvo")
    assert isinstance(yrange, float)
    xmin = galvo_core.getGalvoXMinimum("Galvo")
    assert isinstance(xmin, float)
    ymin = galvo_core.getGalvoYMinimum("Galvo")
    assert isinstance(ymin, float)


def test_galvo_polygons(galvo_core: pmn.CMMCore) -> None:
    galvo_core.addGalvoPolygonVertex("Galvo", 0, 0.0, 0.0)
    galvo_core.addGalvoPolygonVertex("Galvo", 0, 10.0, 0.0)
    galvo_core.addGalvoPolygonVertex("Galvo", 0, 10.0, 10.0)
    galvo_core.setGalvoPolygonRepetitions("Galvo", 5)
    galvo_core.loadGalvoPolygons("Galvo")
    galvo_core.runGalvoPolygons("Galvo")
    galvo_core.deleteGalvoPolygons("Galvo")

    galvo_core.runGalvoSequence("Galvo")


# ── Pump devices ────────────────────────────────────────────────────────────


@pytest.fixture
def pressure_pump_core(core: pmn.CMMCore) -> pmn.CMMCore:
    core.loadDevice("PPump", "DemoCamera", "DPressurePump")
    core.initializeDevice("PPump")
    return core


def test_pressure_pump(pressure_pump_core: pmn.CMMCore) -> None:
    c = pressure_pump_core
    req = c.pressurePumpRequiresCalibration("PPump")
    assert isinstance(req, bool)
    # demo pump doesn't support calibrate
    with pytest.raises(pmn.CMMError):
        c.pressurePumpCalibrate("PPump")

    c.setPumpPressureKPa("PPump", 50.0)
    p = c.getPumpPressureKPa("PPump")
    assert isinstance(p, float)

    c.pressurePumpStop("PPump")


def test_volumetric_pump(core: pmn.CMMCore) -> None:
    dev = "VPump"
    core.loadDevice(dev, "DemoCamera", "DVolumetricPump")
    core.initializeDevice(dev)
    req = core.volumetricPumpRequiresHoming(dev)
    assert isinstance(req, bool)
    assert not core.isPumpDirectionInverted(dev)

    core.setPumpVolume(dev, 10.0)
    assert core.getPumpVolume(dev) == 10.0
    core.setPumpMaxVolume(dev, 100.0)
    assert core.getPumpMaxVolume(dev) == 100.0
    core.setPumpFlowrate(dev, 5.0)
    assert core.getPumpFlowrate(dev) == 5.0

    core.pumpStart(dev)
    core.pumpDispenseDurationSeconds(dev, 1.0)
    core.pumpDispenseVolumeUl(dev, 5.0)
    core.volumetricPumpStop(dev)


# ── Serial port (no demo device, test error path) ──────────────────────────


def test_serial_port_errors(demo_core: pmn.CMMCore) -> None:
    with pytest.raises(pmn.CMMError):
        demo_core.setSerialPortCommand("NoSuchPort", "test", "\r")
    with pytest.raises(pmn.CMMError):
        demo_core.getSerialPortAnswer("NoSuchPort", "\r")
    with pytest.raises(pmn.CMMError):
        demo_core.writeToSerialPort("NoSuchPort", [])
    with pytest.raises(pmn.CMMError):
        demo_core.readFromSerialPort("NoSuchPort")


# ── Property sequence on Core device (hits IsCoreDeviceLabel branches) ─────


def test_property_sequence_on_core_device(demo_core: pmn.CMMCore) -> None:
    assert not demo_core.isPropertySequenceable("Core", "Initialize")
    assert demo_core.getPropertySequenceMaxLength("Core", "Initialize") == 0
    demo_core.startPropertySequence("Core", "Initialize")
    demo_core.stopPropertySequence("Core", "Initialize")
    demo_core.loadPropertySequence("Core", "Initialize", [])


# ── updateCoreProperties ────────────────────────────────────────────────────


def test_update_core_properties(demo_core: pmn.CMMCore) -> None:
    demo_core.updateCoreProperties()


# ── detectDevice ────────────────────────────────────────────────────────────


def test_detect_device(core: pmn.CMMCore) -> None:
    core.loadDevice("Cam", "DemoCamera", "DCam")
    core.initializeDevice("Cam")
    result = core.detectDevice("Cam")
    assert isinstance(result, pmn.DeviceDetectionStatus)


# ── getConfigState (already covered, but ensure specific overloads) ────────


def test_get_config_state_overloads(demo_core: pmn.CMMCore) -> None:
    groups = demo_core.getAvailableConfigGroups()
    for group in groups:
        configs = demo_core.getAvailableConfigs(group)
        if configs:
            state = demo_core.getConfigState(group, configs[0])
            assert isinstance(state, pmn.Configuration)
            break


# ── MultiROI error paths ───────────────────────────────────────────────────


def test_multi_roi_set_get(demo_core: pmn.CMMCore) -> None:
    demo_core.setProperty("Camera", "AllowMultiROI", "1")
    assert demo_core.isMultiROISupported()

    demo_core.setMultiROI([0], [0], [100], [100])
    assert demo_core.isMultiROIEnabled()
    assert demo_core.getMultiROI() == ((0,), (0,), (100,), (100,))

    demo_core.setProperty("Camera", "AllowMultiROI", "0")
