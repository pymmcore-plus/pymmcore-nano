"""Tests for Python bridge devices via MockDeviceAdapter."""

from __future__ import annotations

import numpy as np
from pymmcore_nano import CMMCore, DeviceType, PropertyBridge


class MinimalCamera:
    """Minimal Python camera that satisfies the bridge interface."""

    def __init__(self, width: int = 64, height: int = 32) -> None:
        self._width = width
        self._height = height
        self._exposure = 10.0
        self._buf: np.ndarray | None = None
        self._gain: float = 1.0
        self._mode: str = "Normal"

    def name(self) -> str:
        return "MinimalCamera"

    def initialize(self, bridge: PropertyBridge | None = None) -> None:
        if bridge is None:
            return
        bridge.create_property(
            "Gain",
            "1.0",
            2,
            False,
            getter=lambda: self._gain,
            setter=lambda v: setattr(self, "_gain", float(v)),
        )
        bridge.set_property_limits("Gain", 0.0, 100.0)
        bridge.create_property(
            "Mode",
            "Normal",
            1,
            False,
            getter=lambda: self._mode,
            setter=lambda v: setattr(self, "_mode", str(v)),
        )
        bridge.set_allowed_values("Mode", ["Normal", "Fast", "Slow"])

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

    def name(self) -> str:
        return "MinimalShutter"

    def initialize(self, bridge=None) -> None:
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
