"""Tests for Python bridge devices via MockDeviceAdapter."""

from __future__ import annotations

import contextlib
import functools
import gc
import os
import subprocess
import sys
import threading
import time
import weakref
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pymmcore_nano as pmn
import pytest
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pymmcore_nano import DeviceCallbacks
    from pymmcore_nano.protocols import CreatePropertyFn


class MinimalDevice:
    """Shared base for all minimal test devices."""

    def initialize_bridge(
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

    def initialize_bridge(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        super().initialize_bridge(create_property, notify)
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

    # Loaded device descriptions should come from the bridge's GetDescription
    assert core.getDeviceDescription("Cam1") == "A test camera."
    assert core.getDeviceDescription("Shutter1") == "A test shutter."

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
        self._pos = 0
        self._notify: DeviceCallbacks | None = None

    def initialize_bridge(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        super().initialize_bridge(create_property, notify)
        self._notify = notify
        create_property(
            "State",
            "0",
            3,  # MM::Integer
            False,
            getter=lambda: self._pos,
            setter=lambda v: setattr(self, "_pos", int(v)),
            allowed_values=list(range(self._n)),
        )
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

    def detect_installed_devices(self) -> list[tuple[str, str]]:
        return [
            ("HubCam", "Minimal Python camera"),
            ("HubShutter", "Minimal Python shutter"),
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

    # Position (um)
    core.setPosition(42.5)
    assert stage._pos_um == 42.5
    assert core.getPosition() == 42.5

    core.setRelativePosition(10.0)
    assert stage._pos_um == 52.5

    # Origin
    core.setOrigin("Z")
    assert stage._pos_um == 0.0

    # Home
    core.home("Z")

    # Focus direction + continuous focus drive
    assert core.getFocusDirection("Z") == 0
    assert core.isContinuousFocusDrive("Z") is False

    # Sequenceable query
    assert not core.isStageSequenceable("Z")


def test_load_py_xy_stage() -> None:
    core = CMMCore()
    xy = MinimalXYStage()
    core.loadPyDevice("XY", xy, DeviceType.XYStageDevice)
    core.initializeDevice("XY")
    core.setXYStageDevice("XY")

    assert "XY" in core.getLoadedDevices()

    # Position (um)
    core.setXYPosition(10.0, 20.0)
    assert xy._x_um == 10.0
    assert xy._y_um == 20.0
    x, y = core.getXYPosition()
    assert x == 10.0
    assert y == 20.0

    # Relative position
    core.setRelativeXYPosition(5.0, -5.0)
    assert xy._x_um == 15.0
    assert xy._y_um == 15.0

    # Home
    core.home("XY")
    assert xy._x_um == 0.0
    assert xy._y_um == 0.0

    # Stop (no-op but exercises the bridge)
    core.stop("XY")

    # Sequenceable query
    assert not core.isXYStageSequenceable("XY")


class MinimalXYStepper(MinimalDevice):
    """XY stage that only works in steps (no *_um methods, no set_origin)."""

    def __init__(self) -> None:
        self.steps = (0, 0)

    def set_position_steps(self, x: int, y: int) -> None:
        self.steps = (x, y)

    def get_position_steps(self) -> tuple[int, int]:
        return self.steps

    def set_relative_position_steps(self, dx: int, dy: int) -> None:
        self.steps = (self.steps[0] + dx, self.steps[1] + dy)

    def get_step_size_x_um(self) -> float:
        return 0.1

    def get_step_size_y_um(self) -> float:
        return 0.1

    def home(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def move(self, vx: float, vy: float) -> None:
        pass

    def set_x_origin(self) -> None:
        pass

    def set_y_origin(self) -> None:
        pass

    def get_limits_um(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, 0.0, 0.0)

    def get_step_limits(self) -> tuple[int, int, int, int]:
        return (0, 0, 0, 0)

    def is_xy_stage_sequenceable(self) -> bool:
        return False


def _load_stepper(core: CMMCore) -> MinimalXYStepper:
    stage = MinimalXYStepper()
    core.loadPyDevice("XY", stage, DeviceType.XYStageDevice)
    core.initializeDevice("XY")
    core.setXYStageDevice("XY")
    return stage


def test_py_xy_stepper_uses_cxystagebase_conversion() -> None:
    """Without *_um methods, CXYStageBase converts um <-> steps (nearest step)."""
    core = CMMCore()
    stage = _load_stepper(core)

    core.setXYPosition(100.5, -200.5)
    assert stage.steps == (1005, -2005)
    assert core.getXYPosition() == pytest.approx((100.5, -200.5))

    core.setXYPosition(0.19, -0.19)
    assert stage.steps == (2, -2)

    core.setRelativeXYPosition(1.0, 1.0)
    assert stage.steps == (12, 8)


def test_py_xy_stepper_mirroring() -> None:
    """CXYStageBase's TransposeMirrorX/Y apply, however they are set."""
    core = CMMCore()
    stage = _load_stepper(core)
    assert core.hasProperty("XY", "TransposeMirrorX")

    core.defineConfig("Orientation", "Mirrored", "XY", "TransposeMirrorX", "1")
    core.setConfig("Orientation", "Mirrored")
    core.setXYPosition(10.0, 20.0)
    assert stage.steps == (-100, 200)
    assert core.getXYPosition() == pytest.approx((10.0, 20.0))


def test_py_xy_stepper_origin() -> None:
    """setOriginXY zeroes the adapter origin; the hardware position is unchanged."""
    core = CMMCore()
    stage = _load_stepper(core)

    core.setXYPosition(10.0, 20.0)
    core.setOriginXY()
    assert stage.steps == (100, 200)
    assert core.getXYPosition() == pytest.approx((0.0, 0.0))

    core.setAdapterOriginXY(5.0, 6.0)
    assert core.getXYPosition() == pytest.approx((5.0, 6.0))
    assert stage.steps == (100, 200)


def test_py_xy_stepper_notifies_moves() -> None:
    received: list[tuple[str, float, float]] = []

    class Listener(pmn.MMEventCallback):
        def onXYStagePositionChanged(self, dev: str, x: float, y: float) -> None:
            received.append((dev, x, y))

    core = CMMCore()
    _load_stepper(core)
    cb = Listener()
    core.registerCallback(cb)

    core.setXYPosition(1.0, 2.0)
    core.setRelativeXYPosition(0.5, 0.5)

    deadline = time.time() + 2.0
    while len(received) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert received[0] == ("XY", pytest.approx(1.0), pytest.approx(2.0))
    assert received[1] == ("XY", pytest.approx(1.5), pytest.approx(2.5))


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


def _load_wheel(core: CMMCore) -> MinimalState:
    state = MinimalState(n_positions=4, labels=["DAPI", "FITC", "TRITC", "Cy5"])
    core.loadPyDevice("Wheel", state, DeviceType.StateDevice)
    core.initializeDevice("Wheel")
    return state


def test_py_state_label_property_follows_state() -> None:
    """The bridge provides Label from the same label map as getStateLabel."""
    core = CMMCore()
    state = _load_wheel(core)

    assert core.hasProperty("Wheel", "Label")
    assert sorted(core.getAllowedPropertyValues("Wheel", "Label")) == sorted(
        ["DAPI", "FITC", "TRITC", "Cy5"]
    )

    core.setState("Wheel", 2)
    assert state._pos == 2
    assert core.getProperty("Wheel", "Label") == "TRITC"
    assert core.getPropertyFromCache("Wheel", "Label") == "TRITC"

    core.setStateLabel("Wheel", "FITC")
    assert state._pos == 1
    assert core.getProperty("Wheel", "State") == "1"
    assert core.getPropertyFromCache("Wheel", "State") == "1"

    core.setProperty("Wheel", "Label", "Cy5")
    assert state._pos == 3
    assert core.getState("Wheel") == 3


def test_py_state_define_state_label() -> None:
    """defineStateLabel is visible through every label/Label accessor."""
    core = CMMCore()
    _load_wheel(core)

    core.defineStateLabel("Wheel", 1, "GFP")
    assert core.getStateLabels("Wheel") == ["DAPI", "GFP", "TRITC", "Cy5"]
    assert "GFP" in core.getAllowedPropertyValues("Wheel", "Label")
    assert "FITC" not in core.getAllowedPropertyValues("Wheel", "Label")

    core.setState("Wheel", 1)
    assert core.getStateLabel("Wheel") == "GFP"
    assert core.getProperty("Wheel", "Label") == "GFP"
    assert core.getPropertyFromCache("Wheel", "Label") == "GFP"

    core.setState("Wheel", 0)
    core.setProperty("Wheel", "Label", "GFP")
    assert core.getState("Wheel") == 1


def test_py_state_cannot_create_label_property() -> None:
    class StateWithLabel(MinimalState):
        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            super().initialize_bridge(create_property, notify)
            create_property("Label", "", 1, False)  # MM::String

    core = CMMCore()
    core.loadPyDevice("Wheel", StateWithLabel(), DeviceType.StateDevice)
    with pytest.raises(RuntimeError, match="may not create a 'Label' property"):
        core.initializeDevice("Wheel")


def test_py_state_requires_state_property() -> None:
    class StateWithoutState(MinimalDevice):
        def get_number_of_positions(self) -> int:
            return 2

    core = CMMCore()
    core.loadPyDevice("Wheel", StateWithoutState(), DeviceType.StateDevice)
    with pytest.raises(RuntimeError, match="must create a 'State' property"):
        core.initializeDevice("Wheel")


def test_py_state_on_state_changed() -> None:
    """A device-initiated move notifies CMMCore of both State and Label."""
    received: list[tuple[str, str, str]] = []

    class Listener(pmn.MMEventCallback):
        def onPropertyChanged(self, dev: str, name: str, value: str) -> None:
            received.append((dev, name, value))

    core = CMMCore()
    state = _load_wheel(core)
    cb = Listener()
    core.registerCallback(cb)

    # e.g. the user turned the wheel by hand
    state._pos = 2
    assert state._notify is not None
    state._notify.on_state_changed(2)

    deadline = time.time() + 2.0
    while len(received) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert ("Wheel", "State", "2") in received
    assert ("Wheel", "Label", "TRITC") in received
    assert core.getPropertyFromCache("Wheel", "Label") == "TRITC"


def test_on_state_changed_requires_state_device() -> None:
    core = CMMCore()
    cam = MinimalCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    assert cam._notify is not None
    with pytest.raises(RuntimeError, match="only available on State devices"):
        cam._notify.on_state_changed(0)


def test_load_py_autofocus() -> None:
    core = CMMCore()
    af = MinimalAutoFocus()
    core.loadPyDevice("AF", af, DeviceType.AutoFocusDevice)
    core.initializeDevice("AF")
    core.setAutoFocusDevice("AF")

    assert "AF" in core.getLoadedDevices()

    # Offset
    core.setAutoFocusOffset(5.0)
    assert af._offset == 5.0
    assert core.getAutoFocusOffset() == 5.0

    # Continuous focusing
    core.enableContinuousFocus(True)
    assert af._continuous is True
    assert core.isContinuousFocusEnabled() is True
    assert core.isContinuousFocusLocked() is True

    core.enableContinuousFocus(False)
    assert af._continuous is False

    # Focus operations
    core.fullFocus()
    core.incrementalFocus()

    # Scores
    assert core.getLastFocusScore() == 1.0
    assert core.getCurrentFocusScore() == 1.0


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

    # Point and fire
    core.pointGalvoAndFire("Galvo", 5.0, 5.0, 100.0)
    assert galvo._x == 5.0
    assert galvo._y == 5.0

    # Spot interval
    core.setGalvoSpotInterval("Galvo", 50.0)
    assert galvo._spot_interval == 50.0

    # Range minimums
    assert core.getGalvoXMinimum("Galvo") == 0.0
    assert core.getGalvoYMinimum("Galvo") == 0.0

    # Polygon load/repetitions/run
    core.addGalvoPolygonVertex("Galvo", 0, 0.0, 0.0)
    core.addGalvoPolygonVertex("Galvo", 0, 10.0, 10.0)
    core.setGalvoPolygonRepetitions("Galvo", 3)
    assert galvo._repetitions == 3
    core.loadGalvoPolygons("Galvo")
    core.runGalvoPolygons("Galvo")

    # Channel
    assert core.getGalvoChannel("Galvo") == ""

    # Sequence
    core.runGalvoSequence("Galvo")
    assert galvo._sequence_running is True


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

    # Peripheral descriptions come from detect_installed_devices
    cam_desc = core.getInstalledDeviceDescription("Hub", "HubCam")
    shutter_desc = core.getInstalledDeviceDescription("Hub", "HubShutter")
    assert "Minimal Python camera" in cam_desc
    assert "Minimal Python shutter" in shutter_desc


def test_load_py_slm() -> None:
    core = CMMCore()
    slm = MinimalSLM(width=64, height=32)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    core.setSLMDevice("SLM")

    assert "SLM" in core.getLoadedDevices()
    assert core.getSLMWidth("SLM") == 64
    assert core.getSLMHeight("SLM") == 32
    assert core.getSLMNumberOfComponents("SLM") == 1
    assert core.getSLMBytesPerPixel("SLM") == 1

    core.setSLMExposure("SLM", 100.0)
    assert slm._exposure == 100.0
    assert core.getSLMExposure("SLM") == 100.0

    # Set and verify image data round-trips through the bridge
    img = np.arange(64 * 32, dtype=np.uint8).reshape(32, 64)
    core.setSLMImage("SLM", img)
    assert slm._image is not None
    assert slm._image.shape == (32, 64)
    np.testing.assert_array_equal(slm._image, img)

    # DisplayImage
    core.displaySLMImage("SLM")

    # SetPixelsTo (uniform intensity)
    core.setSLMPixelsTo("SLM", 128)

    # SetPixelsTo (RGB)
    core.setSLMPixelsTo("SLM", 10, 20, 30)

    # Not sequenceable
    assert not slm.is_slm_sequenceable()


def test_slm_rgb_image() -> None:
    """RGB SLM receives properly shaped (h, w, 3) array."""

    class RGBSlm(MinimalSLM):
        def get_number_of_components(self) -> int:
            return 3

        def get_bytes_per_pixel(self) -> int:
            return 3  # total across components

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

        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            super().initialize_bridge(create_property, notify)
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
        def initialize_bridge(
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


def test_create_property_duplicate_name_raises() -> None:
    class DupProps(MinimalGeneric):
        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            create_property("Mode", "a", 1, False)  # MM::String
            create_property("Mode", "b", 1, False)

    core = CMMCore()
    core.loadPyDevice("Dev", DupProps(), DeviceType.GenericDevice)
    with pytest.raises(RuntimeError, match="Mode"):
        core.initializeDevice("Dev")


def test_create_property_colliding_with_base_class_property_raises() -> None:
    """CXYStageBase already creates TransposeMirrorX in C++."""

    class XYWithMirror(MinimalXYStage):
        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            super().initialize_bridge(create_property, notify)
            create_property("TransposeMirrorX", "0", 3, False)  # MM::Integer

    core = CMMCore()
    core.loadPyDevice("XY", XYWithMirror(), DeviceType.XYStageDevice)
    with pytest.raises(RuntimeError, match="TransposeMirrorX"):
        core.initializeDevice("XY")


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


def in_subprocess(
    fn: Callable[..., None] | None = None, *, env: dict[str, str] | None = None
) -> Any:
    """Run the test in a fresh interpreter so aborts/segfaults fail it, not pytest."""

    def decorator(fn: Callable[..., None]) -> Callable[..., None]:
        @functools.wraps(fn)
        def wrapper(**kwargs: Any) -> None:
            call = f"m.{fn.__name__}.__wrapped__(**{kwargs!r})"
            code = f"import {fn.__module__} as m; {call}"
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=Path(__file__).parent,  # so `import test_bridge_devices` resolves
                env={**os.environ, **(env or {})},
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert proc.returncode == 0, (
                f"exit {proc.returncode}\n{proc.stderr[-2000:]}"
            )

        return wrapper

    return decorator(fn) if fn is not None else decorator


LAYOUTS = {
    "transposed": lambda h, w: np.arange(h * w, dtype=np.uint8).reshape(w, h).T,
    "strided": lambda h, w: np.arange(h * w * 2, dtype=np.uint8).reshape(h, w * 2)[
        :, ::2
    ],
    "fortran": lambda h, w: np.asfortranarray(
        np.arange(h * w, dtype=np.uint8).reshape(h, w)
    ),
}


# Regression test for a use-after-free. When get_image_buffer() returned a
# non-contiguous array, the bridge handed CMMCore a pointer into a temporary
# contiguous copy that had already been freed. What getImage() then reads
# depends on whether the allocator has reused that memory, so the test runs
# with freed memory overwritten (macOS: MallocScribble, glibc: MALLOC_PERTURB_)
# and a dangling read returns wrong pixels on every run. Windows has no such
# switch, so detection there is best-effort. The image must stay well above
# 1 KiB: NumPy caches smaller freed blocks itself, out of the allocator's reach.
SCRIBBLE_FREED_MEMORY = {"MallocScribble": "1", "MALLOC_PERTURB_": "165"}


@pytest.mark.parametrize("layout", LAYOUTS)
@in_subprocess(env=SCRIBBLE_FREED_MEMORY)
def test_get_image_returns_exactly_the_camera_array(layout: str) -> None:
    """Any array layout the camera returns must come back unchanged, not scrambled
    or read from freed memory."""

    class Cam(MinimalCamera):
        def snap_image(self) -> None:
            self._buf = LAYOUTS[layout](self._height, self._width)

        def get_image_buffer_size(self) -> int:
            # CMMCore calls this after GetImageBuffer(); reusing a block of the
            # same size makes a dangling image pointer observable.
            junk = np.full(self._width * self._height, 0xEE, dtype=np.uint8)
            del junk
            return self._width * self._height

    core = CMMCore()
    cam = Cam(width=300, height=200)  # 60 kB: keep well above 1 KiB (see above)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    for _ in range(5):
        core.snapImage()
        np.testing.assert_array_equal(core.getImage(), cam._buf)


@pytest.mark.parametrize("shape", [(2, 2), (6, 9), (5, 8)])
def test_image_of_wrong_size_raises(shape: tuple[int, int]) -> None:
    """CMMCore reads exactly w*h*bpp bytes; any other size reads garbage."""

    class Cam(MinimalCamera):
        def snap_image(self) -> None:
            self._buf = np.zeros(shape, dtype=np.uint8)

    core = CMMCore()
    # note: these are NOT the same shape as the shape param.
    core.loadPyDevice("Cam", Cam(width=8, height=6), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    with pytest.raises(RuntimeError):
        core.getImage()


@pytest.mark.parametrize("layout", LAYOUTS)
def test_slm_receives_exactly_the_given_image(layout: str) -> None:
    """Non-contiguous input must be copied or rejected, never reinterpreted."""
    core = CMMCore()
    slm = MinimalSLM(width=4, height=3)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    img = LAYOUTS[layout](3, 4)
    try:
        core.setSLMImage("SLM", img)
    except (TypeError, ValueError):
        return  # rejecting it is acceptable
    np.testing.assert_array_equal(slm._image, img)


def test_slm_bytes_per_pixel_is_the_total() -> None:
    """SLM bpp is total bytes per pixel (GenericSLM: bpp=4, 3 components), not per
    component."""

    class RGBSLM(MinimalSLM):
        def get_number_of_components(self) -> int:
            return 3

        def get_bytes_per_pixel(self) -> int:
            return 4

    core = CMMCore()
    slm = RGBSLM(width=8, height=4)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    core.setSLMImage("SLM", np.zeros((4, 8, 4), dtype=np.uint8))
    assert slm._image is not None


def test_python_error_message_reaches_the_caller() -> None:
    """The device's own error message is what the user needs to diagnose a failure."""

    class Cam(MinimalCamera):
        def snap_image(self) -> None:
            raise RuntimeError("sensor overheated")

    core = CMMCore()
    core.loadPyDevice("Cam", Cam(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    with pytest.raises(RuntimeError, match="sensor overheated"):
        core.snapImage()


def test_failing_property_getter_does_not_break_system_state() -> None:
    """CMMCore::getSystemState tolerates per-property errors; same here."""

    class Dev(MinimalDevice):
        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            create_property("Bad", "0", 1, False, getter=self._boom)
            create_property("Good", "ok", 1, False, getter=lambda: "ok")

        def _boom(self) -> str:
            raise RuntimeError("cannot read")

    core = CMMCore()
    core.loadPyDevice("D", Dev(), DeviceType.GenericDevice)
    core.initializeDevice("D")
    state = core.getSystemState()  # C++ devices: per-property errors are tolerated
    assert state.isPropertyIncluded("D", "Good")


def test_device_constructor_error_is_reported() -> None:
    """The Python exception is the only clue why a device couldn't be created."""

    class Broken(MinimalDevice):
        def __init__(self) -> None:
            raise ValueError("serial port COM7 not found")

    ad = DeviceAdapter()
    ad.add_device_class("Broken", Broken, DeviceType.GenericDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Ad", ad)
    with pytest.raises(RuntimeError, match="COM7"):
        core.loadDevice("D", "Ad", "Broken")


@pytest.mark.parametrize("how", ["unloadDevice", "unloadAllDevices", "reset"])
def test_unloading_releases_the_python_device(how: str) -> None:
    """Once unloaded, the core must not keep the device (and its hardware) alive."""
    core = CMMCore()
    dev = MinimalGeneric()
    ref = weakref.ref(dev)
    core.loadPyDevice("D", dev, DeviceType.GenericDevice)
    core.initializeDevice("D")
    del dev
    if how == "unloadDevice":
        core.unloadDevice("D")
    else:
        getattr(core, how)()
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize("n_failing", [1, 2, 3])
@in_subprocess
def test_failing_shutdowns_never_abort_the_process(n_failing: int) -> None:
    """A Python exception in an unload/destructor path must not `terminate()`."""

    class Dev(MinimalDevice):
        def shutdown(self) -> None:
            raise RuntimeError("shutdown failed")

    core = CMMCore()
    for i in range(n_failing):
        core.loadPyDevice(f"D{i}", Dev(), DeviceType.GenericDevice)
    core.initializeAllDevices()
    with contextlib.suppress(Exception):
        core.unloadAllDevices()
    del core
    gc.collect()


@in_subprocess
def test_error_in_is_capturing_does_not_abort_the_process() -> None:
    """A raising device method must become an error, never a process abort."""

    class Cam(MinimalCamera):
        def is_capturing(self) -> bool:
            raise RuntimeError("SDK gone")

    core = CMMCore()
    core.loadPyDevice("Cam", Cam(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    with contextlib.suppress(Exception):
        core.isSequenceRunning()


@in_subprocess
def test_insert_image_after_camera_unload_raises() -> None:
    """A camera thread may outlive its device; using `insert_image` then must raise,
    not touch freed memory."""

    class Cam(MinimalCamera):
        def start_sequence_acquisition(self, n, interval_ms, insert_image) -> None:
            self.insert = insert_image

        def stop_sequence_acquisition(self) -> None:
            pass

        def is_capturing(self) -> bool:
            return False

    core = CMMCore()
    cam = Cam(width=4, height=2)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.startSequenceAcquisition(10, 0, True)
    core.unloadDevice("Cam")
    with pytest.raises(Exception):  # noqa: B017 - any clean error is acceptable
        cam.insert(np.zeros((2, 4), np.uint8), None)


def test_failed_sequence_start_closes_the_auto_shutter() -> None:
    """The bridge opens the auto-shutter (PrepareForAcq) before calling Python, so a
    failed start must close it again."""

    class Cam(MinimalCamera):
        def start_sequence_acquisition(self, n, interval_ms, insert_image) -> None:
            raise RuntimeError("SDK: trigger mode not supported")

    core = CMMCore()
    shutter = MinimalShutter()
    core.loadPyDevice("S", shutter, DeviceType.ShutterDevice)
    core.loadPyDevice("C", Cam(), DeviceType.CameraDevice)
    core.initializeAllDevices()
    core.setShutterDevice("S")
    core.setCameraDevice("C")
    core.setAutoShutter(True)
    with pytest.raises(RuntimeError):
        core.startSequenceAcquisition(5, 0, True)
    assert not shutter.get_open()


def test_instance_hub_peripherals_cannot_be_loaded_by_name() -> None:
    """A `loadPyDevice` hub has no factory, so its listed peripherals can't be
    loaded from its adapter (discovery never supplies the loaded device)."""
    core = CMMCore()
    core.loadPyDevice("Hub", MinimalHub(), DeviceType.HubDevice)
    core.initializeDevice("Hub")
    assert "HubCam" in core.getInstalledDevices("Hub")
    with pytest.raises(RuntimeError, match="add_device_class"):
        core.loadDevice("Cam", core.getDeviceLibrary("Hub"), "HubCam")


def test_adapter_hub_peripherals_load_after_discovery() -> None:
    """Like C++ hubs: a listed peripheral loads by name as a fresh device."""
    ad = DeviceAdapter()
    ad.add_device_class("Hub", MinimalHub, DeviceType.HubDevice, "")
    ad.add_device_class("HubCam", MinimalCamera, DeviceType.CameraDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Ad", ad)
    core.loadDevice("Hub", "Ad", "Hub")
    core.initializeDevice("Hub")
    assert "HubCam" in core.getInstalledDevices("Hub")
    core.loadDevice("Cam", "Ad", "HubCam")
    core.setParentLabel("Cam", "Hub")
    core.initializeDevice("Cam")
    assert core.getDeviceType("Cam") == DeviceType.CameraDevice


def test_adapter_hub_peripherals_load_before_discovery() -> None:
    """Config files load peripherals by name before the hub is initialized."""
    ad = DeviceAdapter()
    ad.add_device_class("Hub", MinimalHub, DeviceType.HubDevice, "")
    ad.add_device_class("HubCam", MinimalCamera, DeviceType.CameraDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Ad", ad)
    # same order as a config file: Device lines, Parent lines, then initialize
    core.loadDevice("Hub", "Ad", "Hub")
    core.loadDevice("Cam", "Ad", "HubCam")
    core.setParentLabel("Cam", "Hub")
    core.initializeAllDevices()
    assert core.getParentLabel("Cam") == "Hub"
    assert core.getDeviceType("Cam") == DeviceType.CameraDevice
