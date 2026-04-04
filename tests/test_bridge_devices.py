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
        interval_ms: float,
        insert_image: Callable[[np.ndarray, dict | None], bool],
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
                    if not insert_image(img, {"frame": count}):
                        break
                    count += 1
                    time.sleep(interval_ms / 1000.0)
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


class MinimalSignalIO(MinimalDevice):
    def __init__(self) -> None:
        self._gate_open = True
        self._volts = 0.0
        self._min_volts = 0.0
        self._max_volts = 5.0

    def set_gate_open(self, open: bool) -> None:
        self._gate_open = open

    def get_gate_open(self) -> bool:
        return self._gate_open

    def set_signal(self, volts: float) -> None:
        self._volts = volts

    def get_signal(self) -> float:
        return self._volts

    def get_limits(self) -> tuple[float, float]:
        return (self._min_volts, self._max_volts)

    def is_da_sequenceable(self) -> bool:
        return False


class MinimalMagnifier(MinimalDevice):
    def __init__(self, mag: float = 10.0) -> None:
        self._mag = mag

    def get_magnification(self) -> float:
        return self._mag


class MinimalSerial(MinimalDevice):
    def __init__(self) -> None:
        self._buf = b""

    def get_port_type(self) -> int:
        return 1  # SerialPort

    def set_command(self, command: str, term: str) -> None:
        self._buf = (command + term).encode()

    def get_answer(self, term: str) -> str:
        return self._buf.decode()

    def write(self, data: bytes) -> None:
        self._buf = data

    def read(self, max_bytes: int) -> bytes:
        result = self._buf[:max_bytes]
        self._buf = self._buf[max_bytes:]
        return result

    def purge(self) -> None:
        self._buf = b""


class MinimalGalvo(MinimalDevice):
    def __init__(self) -> None:
        self._x = 0.0
        self._y = 0.0
        self._illumination = False
        self._spot_interval = 0.0
        self._polygons: dict[int, list[tuple[float, float]]] = {}
        self._repetitions = 1
        self._sequence_running = False

    def point_and_fire(self, x: float, y: float, time_us: float) -> None:
        self._x = x
        self._y = y

    def set_spot_interval(self, pulse_interval_us: float) -> None:
        self._spot_interval = pulse_interval_us

    def set_position(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    def get_position(self) -> tuple[float, float]:
        return (self._x, self._y)

    def set_illumination_state(self, on: bool) -> None:
        self._illumination = on

    def get_x_range(self) -> float:
        return 100.0

    def get_x_minimum(self) -> float:
        return 0.0

    def get_y_range(self) -> float:
        return 100.0

    def get_y_minimum(self) -> float:
        return 0.0

    def add_polygon_vertex(self, polygon_index: int, x: float, y: float) -> None:
        self._polygons.setdefault(polygon_index, []).append((x, y))

    def delete_polygons(self) -> None:
        self._polygons.clear()

    def load_polygons(self) -> None:
        pass

    def set_polygon_repetitions(self, repetitions: int) -> None:
        self._repetitions = repetitions

    def run_polygons(self) -> None:
        pass

    def run_sequence(self) -> None:
        self._sequence_running = True

    def stop_sequence(self) -> None:
        self._sequence_running = False

    def get_channel(self) -> str:
        return ""


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

    def is_slm_sequenceable(self) -> bool:
        return False


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


def test_load_py_signal_io() -> None:
    core = CMMCore()
    da = MinimalSignalIO()
    core.loadPyDevice("DA", da, DeviceType.SignalIODevice)
    core.initializeDevice("DA")

    assert "DA" in core.getLoadedDevices()
    assert core.getDeviceType("DA") == DeviceType.SignalIODevice


def test_load_py_magnifier() -> None:
    core = CMMCore()
    mag = MinimalMagnifier(mag=40.0)
    core.loadPyDevice("Mag", mag, DeviceType.MagnifierDevice)
    core.initializeDevice("Mag")

    assert "Mag" in core.getLoadedDevices()
    assert core.getDeviceType("Mag") == DeviceType.MagnifierDevice
    assert core.getMagnificationFactor() == 40.0


def test_load_py_serial() -> None:
    core = CMMCore()
    ser = MinimalSerial()
    core.loadPyDevice("COM1", ser, DeviceType.SerialDevice)
    core.initializeDevice("COM1")

    assert "COM1" in core.getLoadedDevices()
    assert core.getDeviceType("COM1") == DeviceType.SerialDevice

    # Command/answer round-trip
    core.setSerialPortCommand("COM1", "HELLO", "\n")
    assert core.getSerialPortAnswer("COM1", "\n") == "HELLO\n"


def test_load_py_galvo() -> None:
    core = CMMCore()
    galvo = MinimalGalvo()
    core.loadPyDevice("Galvo", galvo, DeviceType.GalvoDevice)
    core.initializeDevice("Galvo")
    core.setGalvoDevice("Galvo")

    assert "Galvo" in core.getLoadedDevices()
    assert core.getDeviceType("Galvo") == DeviceType.GalvoDevice

    # Position
    core.setGalvoPosition("Galvo", 10.0, 20.0)
    assert galvo._x == 10.0
    assert galvo._y == 20.0
    pos = core.getGalvoPosition("Galvo")
    assert pos == (10.0, 20.0)

    # Range
    assert core.getGalvoXRange("Galvo") == 100.0
    assert core.getGalvoYRange("Galvo") == 100.0

    # Illumination
    core.setGalvoIlluminationState("Galvo", True)
    assert galvo._illumination is True

    # Polygons
    core.addGalvoPolygonVertex("Galvo", 0, 1.0, 2.0)
    core.addGalvoPolygonVertex("Galvo", 0, 3.0, 4.0)
    assert galvo._polygons[0] == [(1.0, 2.0), (3.0, 4.0)]

    core.deleteGalvoPolygons("Galvo")
    assert galvo._polygons == {}

    # Sequence
    core.runGalvoSequence("Galvo")
    assert galvo._sequence_running is True
    # Note: stopGalvoSequence is not in the CMMCore public API —
    # StopSequence is called internally. Test the Python method directly.


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

    # Set and verify image data round-trips through the bridge
    img = np.arange(64 * 32, dtype=np.uint8).reshape(32, 64)
    core.setSLMImage("SLM", img)
    assert slm._image is not None
    assert slm._image.shape == (32, 64)
    np.testing.assert_array_equal(slm._image, img)


def test_slm_rgb_image() -> None:
    """RGB SLM receives properly shaped (h, w, 3) array."""

    class RGBSlm(MinimalSLM):
        def get_number_of_components(self) -> int:
            return 3

    core = CMMCore()
    slm = RGBSlm(width=8, height=4)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")

    img = np.ones((4, 8, 3), dtype=np.uint8) * 42
    core.setSLMImage("SLM", img)
    assert slm._image is not None
    assert slm._image.shape == (4, 8, 3)
    np.testing.assert_array_equal(slm._image, img)


def test_property_sequencing() -> None:
    """Property sequencing lifecycle: query, load, start, stop."""

    class SeqDevice(MinimalDevice):
        def __init__(self) -> None:
            self._voltage = 0.0
            self._loaded_seq: list[str] = []
            self._seq_started = False
            self._seq_stopped = False
            self._voltage_handle = None

        def initialize(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            super().initialize(create_property, notify)
            # Non-sequenceable property
            create_property(
                "Mode",
                "Off",
                1,
                False,
                getter=lambda: "Off",
            )
            # Sequenceable property
            self._voltage_handle = create_property(
                "Voltage",
                "0.0",
                2,
                False,
                getter=lambda: self._voltage,
                setter=lambda v: setattr(self, "_voltage", float(v)),
                sequence_max_length=10,
                sequence_loader=lambda seq: setattr(self, "_loaded_seq", seq),
                sequence_starter=lambda: setattr(self, "_seq_started", True),
                sequence_stopper=lambda: setattr(self, "_seq_stopped", True),
            )

    core = CMMCore()
    dev = SeqDevice()
    core.loadPyDevice("Dev", dev, DeviceType.GenericDevice)
    core.initializeDevice("Dev")

    # Non-sequenceable property
    assert not core.isPropertySequenceable("Dev", "Mode")

    # Sequenceable property
    assert core.isPropertySequenceable("Dev", "Voltage")
    assert core.getPropertySequenceMaxLength("Dev", "Voltage") == 10

    # Load a sequence
    core.loadPropertySequence("Dev", "Voltage", ["1.0", "2.0", "3.0"])
    assert dev._loaded_seq == ["1.0", "2.0", "3.0"]

    # Start / stop
    core.startPropertySequence("Dev", "Voltage")
    assert dev._seq_started

    core.stopPropertySequence("Dev", "Voltage")
    assert dev._seq_stopped

    # Dynamic max length update via PropertyHandle
    assert core.getPropertySequenceMaxLength("Dev", "Voltage") == 10
    dev._voltage_handle.set_sequence_max_length(20)
    assert core.getPropertySequenceMaxLength("Dev", "Voltage") == 20


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


# ============================================================================
# Device-level sequencing tests
# ============================================================================


class SequenceableCamera(MinimalCamera):
    """Camera that supports exposure sequencing."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loaded_exposure_seq: list[float] = []
        self._exp_seq_started = False
        self._exp_seq_stopped = False

    def is_exposure_sequenceable(self) -> bool:
        return True

    def get_exposure_sequence_max_length(self) -> int:
        return 5

    def load_exposure_sequence(self, sequence: list[float]) -> None:
        self._loaded_exposure_seq = list(sequence)

    def start_exposure_sequence(self) -> None:
        self._exp_seq_started = True

    def stop_exposure_sequence(self) -> None:
        self._exp_seq_stopped = True


class SequenceableStage(MinimalStage):
    """Stage that supports sequencing."""

    def __init__(self) -> None:
        super().__init__()
        self._loaded_seq: list[float] = []
        self._seq_started = False
        self._seq_stopped = False

    def is_stage_sequenceable(self) -> bool:
        return True

    def get_stage_sequence_max_length(self) -> int:
        return 10

    def load_stage_sequence(self, positions: list[float]) -> None:
        self._loaded_seq = list(positions)

    def start_stage_sequence(self) -> None:
        self._seq_started = True

    def stop_stage_sequence(self) -> None:
        self._seq_stopped = True


class SequenceableXYStage(MinimalXYStage):
    """XY stage that supports sequencing."""

    def __init__(self) -> None:
        super().__init__()
        self._loaded_seq: list[tuple[float, float]] = []
        self._seq_started = False
        self._seq_stopped = False

    def is_xy_stage_sequenceable(self) -> bool:
        return True

    def get_xy_stage_sequence_max_length(self) -> int:
        return 8

    def load_xy_stage_sequence(self, positions: list[tuple[float, float]]) -> None:
        self._loaded_seq = [tuple(p) for p in positions]

    def start_xy_stage_sequence(self) -> None:
        self._seq_started = True

    def stop_xy_stage_sequence(self) -> None:
        self._seq_stopped = True


class SequenceableSLM(MinimalSLM):
    """SLM that supports sequencing."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loaded_seq: list[np.ndarray] = []
        self._seq_started = False
        self._seq_stopped = False

    def is_slm_sequenceable(self) -> bool:
        return True

    def get_slm_sequence_max_length(self) -> int:
        return 4

    def load_slm_sequence(self, images: list[np.ndarray]) -> None:
        self._loaded_seq = [np.array(img) for img in images]

    def start_slm_sequence(self) -> None:
        self._seq_started = True

    def stop_slm_sequence(self) -> None:
        self._seq_stopped = True


def test_exposure_sequencing() -> None:
    """Exposure sequence lifecycle: query, load, start, stop."""
    core = CMMCore()
    cam = SequenceableCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")

    assert core.isExposureSequenceable("Cam")
    assert core.getExposureSequenceMaxLength("Cam") == 5

    core.loadExposureSequence("Cam", [10.0, 20.0, 30.0])
    assert cam._loaded_exposure_seq == [10.0, 20.0, 30.0]

    core.startExposureSequence("Cam")
    assert cam._exp_seq_started

    core.stopExposureSequence("Cam")
    assert cam._exp_seq_stopped


def test_stage_sequencing() -> None:
    """Stage sequence lifecycle: query, load, start, stop."""
    core = CMMCore()
    stage = SequenceableStage()
    core.loadPyDevice("Z", stage, DeviceType.StageDevice)
    core.initializeDevice("Z")
    core.setFocusDevice("Z")

    assert core.isStageSequenceable("Z")
    assert core.getStageSequenceMaxLength("Z") == 10

    core.loadStageSequence("Z", [0.0, 1.0, 2.0, 3.0])
    assert stage._loaded_seq == [0.0, 1.0, 2.0, 3.0]

    core.startStageSequence("Z")
    assert stage._seq_started

    core.stopStageSequence("Z")
    assert stage._seq_stopped


def test_xy_stage_sequencing() -> None:
    """XY stage sequence lifecycle: query, load, start, stop."""
    core = CMMCore()
    xy = SequenceableXYStage()
    core.loadPyDevice("XY", xy, DeviceType.XYStageDevice)
    core.initializeDevice("XY")
    core.setXYStageDevice("XY")

    assert core.isXYStageSequenceable("XY")
    assert core.getXYStageSequenceMaxLength("XY") == 8

    core.loadXYStageSequence("XY", [1.0, 3.0, 5.0], [2.0, 4.0, 6.0])
    assert xy._loaded_seq == [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]

    core.startXYStageSequence("XY")
    assert xy._seq_started

    core.stopXYStageSequence("XY")
    assert xy._seq_stopped


def test_slm_sequencing() -> None:
    """SLM sequence lifecycle: query, load, start, stop."""
    core = CMMCore()
    slm = SequenceableSLM(width=8, height=4)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    core.setSLMDevice("SLM")

    assert core.getSLMSequenceMaxLength("SLM") == 4

    img1 = np.ones((4, 8), dtype=np.uint8) * 10
    img2 = np.ones((4, 8), dtype=np.uint8) * 20
    core.loadSLMSequence("SLM", [img1, img2])
    assert len(slm._loaded_seq) == 2
    np.testing.assert_array_equal(slm._loaded_seq[0], img1)
    np.testing.assert_array_equal(slm._loaded_seq[1], img2)

    core.startSLMSequence("SLM")
    assert slm._seq_started

    core.stopSLMSequence("SLM")
    assert slm._seq_stopped
