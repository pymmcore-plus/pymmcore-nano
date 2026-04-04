"""Tests for Python bridge devices via MockDeviceAdapter."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import numpy as np
import pymmcore_nano as pmn
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

if TYPE_CHECKING:
    from collections.abc import Callable

    from pymmcore_nano import DeviceCallbacks
    from pymmcore_nano.protocols import CreatePropertyFn


class MinimalDevice:
    """Shared base for all minimal test devices."""

    def initialize(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False


class MinimalCamera(MinimalDevice):
    """Minimal Python camera that satisfies the bridge interface."""

    def __init__(self, width: int = 64, height: int = 32) -> None:
        self._width = width
        self._height = height
        self._exposure = 10.0
        self._buf: np.ndarray | None = None
        self._gain: float = 1.0
        self._mode: str = "Normal"
        self._capturing = False
        self._notify = None

    def initialize(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        super().initialize(create_property, notify)
        self._notify = notify
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

    def snap_image(self) -> None:
        # Fill with a recognizable pattern
        self._buf = np.arange(self._width * self._height, dtype=np.uint8).reshape(
            self._height, self._width
        )

    def get_image_buffer(self, channel: int = 0) -> np.ndarray:
        assert self._buf is not None
        return self._buf

    def is_exposure_sequenceable(self) -> bool:
        return False

    def get_image_width(self) -> int:
        return self._width

    def get_image_height(self) -> int:
        return self._height

    def get_bytes_per_pixel(self) -> int:
        return 1

    def get_number_of_components(self) -> int:
        return 1

    def get_number_of_channels(self) -> int:
        return 1

    def get_channel_name(self, channel: int) -> str:
        return ""

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

    def is_capturing(self) -> bool:
        return self._capturing

    def start_sequence_acquisition(
        self,
        n: int,
        interval: float,
        stop_on_overflow: bool,
        insert_image: Callable[[np.ndarray, dict | None], None],
    ) -> None:
        self._stop_event = threading.Event()
        self._capturing = True

        def run():
            count = 0
            try:
                while not self._stop_event.is_set():
                    if n is not None and n < 2**62 and count >= n:
                        break
                    img = np.full(
                        (self._height, self._width), count % 256, dtype=np.uint8
                    )
                    insert_image(img, {"frame": count})
                    count += 1
            finally:
                self._capturing = False
                if self._notify is not None:
                    self._notify.acq_finished()

        self._acq_thread = threading.Thread(target=run, daemon=True)
        self._acq_thread.start()

    def stop_sequence_acquisition(self) -> None:
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        if hasattr(self, "_acq_thread"):
            self._acq_thread.join(timeout=5.0)


class MinimalShutter(MinimalDevice):
    """Minimal Python shutter for the bridge."""

    def __init__(self) -> None:
        self._open = False

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


def test_sequence_acquisition() -> None:
    core = CMMCore()
    cam = MinimalCamera(width=64, height=32)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")

    # Set up circular buffer
    core.setCircularBufferMemoryFootprint(16)  # 16 MB
    core.initializeCircularBuffer()

    # Start finite acquisition (5 frames)
    core.startSequenceAcquisition(5, 0.0, True)

    # Wait for frames to arrive
    deadline = time.time() + 5.0
    while core.getRemainingImageCount() < 5 and time.time() < deadline:
        time.sleep(0.01)

    core.stopSequenceAcquisition()

    assert core.getRemainingImageCount() >= 5

    # Pop a frame and verify shape + metadata
    img, md = core.popNextImageMD()
    assert img.shape == (32, 64)
    assert img.dtype == np.uint8

    # CMMCore auto-adds standard metadata
    assert md.HasTag("Width")
    assert md.GetSingleTag("Width").GetValue() == "64"
    assert md.HasTag("Height")
    assert md.GetSingleTag("Height").GetValue() == "32"
    assert md.HasTag("Camera")
    assert md.GetSingleTag("Camera").GetValue() == "Cam"

    # Our Python device's custom metadata should be present too
    assert md.HasTag("frame")
    assert md.GetSingleTag("frame").GetValue() == "0"


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


def test_reload_py_device_after_unload() -> None:
    """Reloading the same label after unload should work."""
    core = CMMCore()

    cam1 = MinimalCamera(width=64, height=32)
    core.loadPyDevice("Cam", cam1, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    assert core.getImage().shape == (32, 64)

    core.unloadDevice("Cam")

    # Reload with a new device using the same label
    cam2 = MinimalCamera(width=16, height=8)
    core.loadPyDevice("Cam", cam2, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    assert core.getImage().shape == (8, 16)


def test_adapter_cleanup_on_core_destroy() -> None:
    """CMMCore destruction should release bridge adapter references."""
    import gc
    import weakref

    cam = MinimalCamera()
    cam_ref = weakref.ref(cam)

    core = CMMCore()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")

    del cam
    # Adapter still holds a reference
    assert cam_ref() is not None

    # Destroying the core should clean up everything
    del core
    gc.collect()
    assert cam_ref() is None, "CMMCore destruction leaked bridge adapter"


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


class MinimalStage(MinimalDevice):
    def __init__(self) -> None:
        self._pos_um = 0.0
        self._pos_steps = 0

    def set_position_um(self, pos: float) -> None:
        self._pos_um = pos

    def get_position_um(self) -> float:
        return self._pos_um

    def set_relative_position_um(self, d: float) -> None:
        self._pos_um += d

    def set_position_steps(self, steps: int) -> None:
        self._pos_steps = steps

    def get_position_steps(self) -> int:
        return self._pos_steps

    def set_adapter_origin_um(self, d: float) -> None:
        pass

    def set_origin(self) -> None:
        self._pos_um = 0.0
        self._pos_steps = 0

    def get_limits(self) -> tuple[float, float]:
        return (-10000.0, 10000.0)

    def move(self, velocity: float) -> None:
        pass

    def stop(self) -> None:
        pass

    def home(self) -> None:
        self._pos_um = 0.0
        self._pos_steps = 0

    def get_focus_direction(self) -> int:
        return 0  # FocusDirectionUnknown

    def is_continuous_focus_drive(self) -> bool:
        return False

    def is_stage_sequenceable(self) -> bool:
        return False


class MinimalXYStage(MinimalDevice):
    def __init__(self) -> None:
        self._x_um = 0.0
        self._y_um = 0.0
        self._x_steps = 0
        self._y_steps = 0

    # position (um)
    def set_position_um(self, x: float, y: float) -> None:
        self._x_um = x
        self._y_um = y
        self._x_steps = int(x / 0.1)
        self._y_steps = int(y / 0.1)

    def get_position_um(self) -> tuple[float, float]:
        return (self._x_um, self._y_um)

    def set_relative_position_um(self, dx: float, dy: float) -> None:
        self.set_position_um(self._x_um + dx, self._y_um + dy)

    def set_adapter_origin_um(self, x: float, y: float) -> None:
        pass

    # position (steps)
    def set_position_steps(self, x: int, y: int) -> None:
        self._x_steps = x
        self._y_steps = y
        self._x_um = x * 0.1
        self._y_um = y * 0.1

    def get_position_steps(self) -> tuple[int, int]:
        return (self._x_steps, self._y_steps)

    def set_relative_position_steps(self, x: int, y: int) -> None:
        self.set_position_steps(self._x_steps + x, self._y_steps + y)

    # motion
    def home(self) -> None:
        self._x_steps = 0
        self._y_steps = 0
        self._x_um = 0.0
        self._y_um = 0.0

    def stop(self) -> None:
        pass

    def move(self, vx: float, vy: float) -> None:
        pass

    # origin
    def set_origin(self) -> None:
        pass

    def set_x_origin(self) -> None:
        pass

    def set_y_origin(self) -> None:
        pass

    # limits + step size
    def get_limits_um(self) -> tuple[float, float, float, float]:
        return (-10000.0, 10000.0, -10000.0, 10000.0)

    def get_step_limits(self) -> tuple[int, int, int, int]:
        return (-100000, 100000, -100000, 100000)

    def get_step_size_x_um(self) -> float:
        return 0.1

    def get_step_size_y_um(self) -> float:
        return 0.1

    # sequencing
    def is_xy_stage_sequenceable(self) -> bool:
        return False


class MinimalState(MinimalDevice):
    def __init__(self, n_positions: int = 4, labels: list[str] | None = None) -> None:
        self._n = n_positions
        self._labels = labels

    def initialize(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        super().initialize(create_property, notify)
        if self._labels is not None:
            for i, label in enumerate(self._labels):
                notify.set_position_label(i, label)

    def get_number_of_positions(self) -> int:
        return self._n


class MinimalAutoFocus(MinimalDevice):
    def __init__(self) -> None:
        self._continuous = False
        self._offset = 0.0

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


class MinimalGeneric(MinimalDevice):
    pass


class MinimalHub(MinimalDevice):
    """Hub that discovers a camera and shutter as peripherals."""

    def detect_installed_devices(self):
        return [
            ("HubCam", MinimalCamera(), DeviceType.CameraDevice),
            ("HubShutter", MinimalShutter(), DeviceType.ShutterDevice),
        ]


class MinimalSLM(MinimalDevice):
    def __init__(self, width: int = 128, height: int = 128) -> None:
        self._width = width
        self._height = height
        self._exposure = 0.0
        self._image: np.ndarray | None = None

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

    core.setXYPosition(10.0, 20.0)
    assert xy._x_um == 10.0
    assert xy._y_um == 20.0


def test_load_py_state() -> None:
    core = CMMCore()
    labels = ["DAPI", "FITC", "TRITC", "Cy5"]
    state = MinimalState(n_positions=4, labels=labels)
    core.loadPyDevice("Wheel", state, DeviceType.StateDevice)
    core.initializeDevice("Wheel")

    assert "Wheel" in core.getLoadedDevices()
    assert core.getNumberOfStates("Wheel") == 4

    # Labels set during initialize should be accessible
    assert core.getStateLabels("Wheel") == ["DAPI", "FITC", "TRITC", "Cy5"]


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
    """Hub discovers peripherals via detect_installed_devices."""
    core = CMMCore()
    hub = MinimalHub()
    core.loadPyDevice("Hub", hub, DeviceType.HubDevice)
    core.initializeDevice("Hub")

    assert core.getDeviceType("Hub") == DeviceType.HubDevice

    # Hub should discover its peripherals
    peripherals = core.getInstalledDevices("Hub")
    assert "HubCam" in peripherals
    assert "HubShutter" in peripherals


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


def test_device_notifications() -> None:
    """Test that Python devices can emit notifications via DeviceCallbacks."""

    received: dict[str, tuple] = {}

    class Listener(pmn.MMEventCallback):
        def onPropertyChanged(self, dev: str, name: str, value: str) -> None:
            received["onPropertyChanged"] = (dev, name, value)

        def onExposureChanged(self, dev: str, exposure: float) -> None:
            received["onExposureChanged"] = (dev, exposure)

    class NotifyingCamera(MinimalCamera):
        def set_exposure(self, ms: float) -> None:
            self._exposure = ms
            # Notify CMMCore that exposure changed
            if self._notify is not None:
                self._notify.on_exposure_changed(ms)

    core = CMMCore()
    cam = NotifyingCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)

    cb = Listener()
    core.registerCallback(cb)

    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")

    # Setting exposure through CMMCore triggers the bridge → Python setter
    # → Python calls notify.on_exposure_changed → CMMCore posts notification
    # → notification thread delivers to callback (async)
    core.setExposure(42.0)
    assert cam._exposure == 42.0

    # Wait for async notification delivery
    deadline = time.time() + 2.0
    while "onExposureChanged" not in received and time.time() < deadline:
        time.sleep(0.01)

    assert "onExposureChanged" in received
    assert received["onExposureChanged"] == ("Cam", 42.0)


def test_python_exception_surfaces_as_runtime_error() -> None:
    """Python exceptions in device methods should surface with traceback info."""

    class BrokenStage(MinimalStage):
        def get_position_um(self) -> float:
            raise ValueError("motor not homed")

    core = CMMCore()
    stage = BrokenStage()
    core.loadPyDevice("Z", stage, DeviceType.StageDevice)
    core.initializeDevice("Z")
    core.setFocusDevice("Z")

    try:
        core.getPosition()
        msg = ""
    except RuntimeError as e:
        msg = str(e)

    assert "motor not homed" in msg, f"Expected Python error message, got: {msg!r}"


def test_python_exception_in_property_getter() -> None:
    """Python exceptions in property getters should surface."""

    class BadCamera(MinimalCamera):
        def initialize(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            create_property(
                "Bad",
                "0",
                2,
                False,
                getter=lambda: 1 / 0,  # ZeroDivisionError
            )

    core = CMMCore()
    cam = BadCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")

    try:
        core.getProperty("Cam", "Bad")
        msg = ""
    except RuntimeError as e:
        msg = str(e)

    assert "ZeroDivisionError" in msg, f"Expected Python error info, got: {msg!r}"
