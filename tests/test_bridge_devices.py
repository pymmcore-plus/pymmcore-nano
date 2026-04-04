"""Tests for Python bridge devices via MockDeviceAdapter."""

from __future__ import annotations

import numpy as np
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType


class MinimalCamera:
    """Minimal Python camera that satisfies the bridge interface."""

    def __init__(self, width: int = 64, height: int = 32) -> None:
        self._width = width
        self._height = height
        self._exposure = 10.0
        self._buf: np.ndarray | None = None
        self._gain: float = 1.0
        self._mode: str = "Normal"

    def initialize(self, create_property=None) -> None:
        if create_property is None:
            return
        self._gain_prop = create_property(
            "Gain",
            "1.0",
            2,
            False,
            getter=lambda: self._gain,
            setter=lambda v: setattr(self, "_gain", float(v)),
            limits=(0.0, 100.0),
        )
        create_property(
            "Mode",
            "Normal",
            1,
            False,
            getter=lambda: self._mode,
            setter=lambda v: setattr(self, "_mode", str(v)),
            allowed_values=["Normal", "Fast", "Slow"],
        )

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def snap_image(self) -> None:
        # Fill with a recognizable pattern
        self._buf = np.arange(self._width * self._height, dtype=np.uint8).reshape(
            self._height, self._width
        )

    def get_image_buffer(self) -> np.ndarray:
        assert self._buf is not None
        return self._buf

    def get_image_width(self) -> int:
        return self._width

    def get_image_height(self) -> int:
        return self._height

    def get_bytes_per_pixel(self) -> int:
        return 1

    def get_bit_depth(self) -> int:
        return 8

    def get_image_buffer_size(self) -> int:
        return self._width * self._height

    def get_exposure(self) -> float:
        return self._exposure

    def set_exposure(self, ms: float) -> None:
        self._exposure = ms

    def get_binning(self) -> int:
        return 1

    def set_binning(self, b: int) -> None:
        pass

    def set_roi(self, x: int, y: int, w: int, h: int) -> None:
        pass

    def get_roi(self) -> tuple[int, int, int, int]:
        return (0, 0, self._width, self._height)

    def clear_roi(self) -> None:
        pass

    def start_sequence_acquisition(
        self, n: int, interval: float, stop_on_overflow: bool
    ) -> None:
        pass

    def stop_sequence_acquisition(self) -> None:
        pass


class MinimalShutter:
    """Minimal Python shutter for the bridge."""

    def __init__(self) -> None:
        self._open = False

    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def set_open(self, state: bool) -> None:
        self._open = state

    def get_open(self) -> bool:
        return self._open

    def fire(self, delta_t: float) -> None:
        pass


def test_load_py_camera() -> None:
    core = CMMCore()
    cam = MinimalCamera(width=64, height=32)
    core.loadPyDevice("MyCam", cam, DeviceType.CameraDevice)
    core.initializeDevice("MyCam")

    # The device should appear in loaded devices
    assert "MyCam" in core.getLoadedDevices()

    # Set as the current camera
    core.setCameraDevice("MyCam")
    assert core.getCameraDevice() == "MyCam"

    # Snap and retrieve image
    core.snapImage()
    img = core.getImage()

    assert img.shape == (32, 64)
    assert img.dtype == np.uint8

    # Verify the pixel pattern round-trips
    expected = np.arange(64 * 32, dtype=np.uint8).reshape(32, 64)
    np.testing.assert_array_equal(img, expected)


def test_load_py_shutter() -> None:
    core = CMMCore()
    shutter = MinimalShutter()
    core.loadPyDevice("MyShutter", shutter, DeviceType.ShutterDevice)
    core.initializeDevice("MyShutter")

    assert "MyShutter" in core.getLoadedDevices()

    core.setShutterDevice("MyShutter")
    assert core.getShutterDevice() == "MyShutter"

    core.setShutterOpen(True)
    assert shutter._open is True

    core.setShutterOpen(False)
    assert shutter._open is False


def test_camera_exposure() -> None:
    core = CMMCore()
    cam = MinimalCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")

    core.setExposure(42.0)
    assert cam._exposure == 42.0
    assert core.getExposure() == 42.0


def test_unload_py_device() -> None:
    core = CMMCore()
    cam = MinimalCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    assert "Cam" in core.getLoadedDevices()

    core.unloadDevice("Cam")
    assert "Cam" not in core.getLoadedDevices()


def test_device_properties() -> None:
    core = CMMCore()
    cam = MinimalCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")

    # Properties should be visible through CMMCore
    names = core.getDevicePropertyNames("Cam")
    # CCameraBase adds Transpose_* properties automatically
    assert "Gain" in names
    assert "Mode" in names

    # Read property through CMMCore
    # FloatProperty stores 4 decimal places (MM convention)
    assert float(core.getProperty("Cam", "Gain")) == 1.0
    assert core.getProperty("Cam", "Mode") == "Normal"

    # Write property through CMMCore → Python device updated
    core.setProperty("Cam", "Gain", "42.5")
    assert cam._gain == 42.5
    assert float(core.getProperty("Cam", "Gain")) == 42.5

    core.setProperty("Cam", "Mode", "Fast")
    assert cam._mode == "Fast"
    assert core.getProperty("Cam", "Mode") == "Fast"

    # Limits should be enforced by CDeviceBase
    assert core.hasPropertyLimits("Cam", "Gain")
    assert core.getPropertyLowerLimit("Cam", "Gain") == 0.0
    assert core.getPropertyUpperLimit("Cam", "Gain") == 100.0

    # Allowed values
    allowed = core.getAllowedPropertyValues("Cam", "Mode")
    assert set(allowed) == {"Normal", "Fast", "Slow"}


def test_load_py_device_adapter() -> None:
    """Test building a DeviceAdapter in Python and registering it."""

    class MyCam(MinimalCamera):
        """A test camera."""

        _TYPE = DeviceType.CameraDevice

    class MyShutter(MinimalShutter):
        """A test shutter."""

        _TYPE = DeviceType.ShutterDevice

    # Build the adapter in Python — scanning logic is Python's job
    # ultimately, pymmcore-plus would likely have conveniences to accept a ModuleType
    # and protocols to define device name, type, and description...
    # but this is the low level API:
    adapter = DeviceAdapter()
    adapter.add_device_class(MyCam.__name__, MyCam, MyCam._TYPE, MyCam.__doc__)
    adapter.add_device_class(
        MyShutter.__name__, MyShutter, MyShutter._TYPE, MyShutter.__doc__
    )

    core = CMMCore()
    core.loadPyDeviceAdapter("MyHardware", adapter)

    # Device discovery should work
    available = core.getAvailableDevices("MyHardware")
    assert "MyCam" in available
    assert "MyShutter" in available

    # Descriptions should work
    descs = core.getAvailableDeviceDescriptions("MyHardware")
    assert "A test camera." in descs
    assert "A test shutter." in descs

    # Load devices through normal CMMCore flow
    core.loadDevice("Cam1", "MyHardware", "MyCam")
    core.loadDevice("Shutter1", "MyHardware", "MyShutter")
    core.initializeDevice("Cam1")
    core.initializeDevice("Shutter1")

    assert "Cam1" in core.getLoadedDevices()
    assert "Shutter1" in core.getLoadedDevices()

    # Devices should work normally
    core.setCameraDevice("Cam1")
    core.snapImage()
    img = core.getImage()
    assert img.shape == (32, 64)  # MinimalCamera defaults

    core.setShutterDevice("Shutter1")
    core.setShutterOpen(True)
    assert core.getShutterOpen() is True

    # Can load a second instance of the same device class
    core.loadDevice("Cam2", "MyHardware", "MyCam")
    core.initializeDevice("Cam2")
    assert "Cam2" in core.getLoadedDevices()


# ============================================================================
# Minimal device stubs for new device types
# ============================================================================


class MinimalStage:
    def __init__(self) -> None:
        self._pos_um = 0.0
        self._pos_steps = 0

    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def set_position_um(self, pos: float) -> None:
        self._pos_um = pos

    def get_position_um(self) -> float:
        return self._pos_um

    def set_position_steps(self, steps: int) -> None:
        self._pos_steps = steps

    def get_position_steps(self) -> int:
        return self._pos_steps

    def set_origin(self) -> None:
        self._pos_um = 0.0
        self._pos_steps = 0

    def get_limits(self) -> tuple[float, float]:
        return (-10000.0, 10000.0)


class MinimalXYStage:
    def __init__(self) -> None:
        self._x_steps = 0
        self._y_steps = 0

    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def set_position_steps(self, x: int, y: int) -> None:
        self._x_steps = x
        self._y_steps = y

    def get_position_steps(self) -> tuple[int, int]:
        return (self._x_steps, self._y_steps)

    def home(self) -> None:
        self._x_steps = 0
        self._y_steps = 0

    def stop(self) -> None:
        pass

    def set_origin(self) -> None:
        pass

    def get_limits_um(self) -> tuple[float, float, float, float]:
        return (-10000.0, 10000.0, -10000.0, 10000.0)

    def get_step_limits(self) -> tuple[int, int, int, int]:
        return (-100000, 100000, -100000, 100000)

    def get_step_size_x_um(self) -> float:
        return 0.1

    def get_step_size_y_um(self) -> float:
        return 0.1


class MinimalState:
    def __init__(self, n_positions: int = 4) -> None:
        self._n = n_positions

    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def get_number_of_positions(self) -> int:
        return self._n


class MinimalAutoFocus:
    def __init__(self) -> None:
        self._continuous = False
        self._offset = 0.0

    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def set_continuous_focusing(self, state: bool) -> None:
        self._continuous = state

    def get_continuous_focusing(self) -> bool:
        return self._continuous

    def is_continuous_focus_locked(self) -> bool:
        return self._continuous

    def full_focus(self) -> None:
        pass

    def incremental_focus(self) -> None:
        pass

    def get_last_focus_score(self) -> float:
        return 1.0

    def get_current_focus_score(self) -> float:
        return 1.0

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, offset: float) -> None:
        self._offset = offset


class MinimalGeneric:
    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False


class MinimalHub:
    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def detect_installed_devices(self) -> None:
        pass


class MinimalSLM:
    def __init__(self, width: int = 128, height: int = 128) -> None:
        self._width = width
        self._height = height
        self._exposure = 0.0
        self._image: np.ndarray | None = None

    def initialize(self, create_property=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def set_image(self, pixels: np.ndarray) -> None:
        self._image = pixels

    def display_image(self) -> None:
        pass

    def set_pixels_to(self, intensity: int) -> None:
        pass

    def set_pixels_to_rgb(self, r: int, g: int, b: int) -> None:
        pass

    def set_exposure(self, interval_ms: float) -> None:
        self._exposure = interval_ms

    def get_exposure(self) -> float:
        return self._exposure

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_number_of_components(self) -> int:
        return 1

    def get_bytes_per_pixel(self) -> int:
        return 1


# ============================================================================
# Tests for new device types
# ============================================================================


def test_load_py_stage() -> None:
    core = CMMCore()
    stage = MinimalStage()
    core.loadPyDevice("Z", stage, DeviceType.StageDevice)
    core.initializeDevice("Z")
    core.setFocusDevice("Z")

    assert "Z" in core.getLoadedDevices()
    assert core.getFocusDevice() == "Z"

    core.setPosition(42.5)
    assert stage._pos_um == 42.5
    assert core.getPosition() == 42.5


def test_load_py_xy_stage() -> None:
    core = CMMCore()
    xy = MinimalXYStage()
    core.loadPyDevice("XY", xy, DeviceType.XYStageDevice)
    core.initializeDevice("XY")
    core.setXYStageDevice("XY")

    assert "XY" in core.getLoadedDevices()

    # XYStageBase converts Um to Steps via GetStepSize{X,Y}Um
    core.setXYPosition(10.0, 20.0)
    # 10.0 / 0.1 = 100 steps, 20.0 / 0.1 = 200 steps
    assert xy._x_steps == 100
    assert xy._y_steps == 200


def test_load_py_state() -> None:
    core = CMMCore()
    state = MinimalState(n_positions=6)
    core.loadPyDevice("Wheel", state, DeviceType.StateDevice)
    core.initializeDevice("Wheel")

    assert "Wheel" in core.getLoadedDevices()
    assert core.getNumberOfStates("Wheel") == 6


def test_load_py_autofocus() -> None:
    core = CMMCore()
    af = MinimalAutoFocus()
    core.loadPyDevice("AF", af, DeviceType.AutoFocusDevice)
    core.initializeDevice("AF")
    core.setAutoFocusDevice("AF")

    assert "AF" in core.getLoadedDevices()

    core.setAutoFocusOffset(5.0)
    assert af._offset == 5.0
    assert core.getAutoFocusOffset() == 5.0


def test_load_py_generic() -> None:
    core = CMMCore()
    dev = MinimalGeneric()
    core.loadPyDevice("Gen", dev, DeviceType.GenericDevice)
    core.initializeDevice("Gen")

    assert "Gen" in core.getLoadedDevices()
    assert core.getDeviceType("Gen") == DeviceType.GenericDevice


def test_load_py_hub() -> None:
    core = CMMCore()
    hub = MinimalHub()
    core.loadPyDevice("Hub", hub, DeviceType.HubDevice)
    core.initializeDevice("Hub")

    assert "Hub" in core.getLoadedDevices()
    assert core.getDeviceType("Hub") == DeviceType.HubDevice


def test_load_py_slm() -> None:
    core = CMMCore()
    slm = MinimalSLM(width=64, height=32)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    core.setSLMDevice("SLM")

    assert "SLM" in core.getLoadedDevices()
    assert core.getSLMWidth("SLM") == 64
    assert core.getSLMHeight("SLM") == 32

    core.setSLMExposure("SLM", 100.0)
    assert slm._exposure == 100.0
