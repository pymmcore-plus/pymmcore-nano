"""Tests for Python bridge devices via MockDeviceAdapter."""

from __future__ import annotations

import numpy as np
from pymmcore_nano import CMMCore, DeviceType


class MinimalCamera:
    """Minimal Python camera that satisfies the bridge interface."""

    def __init__(self, width: int = 64, height: int = 32) -> None:
        self._width = width
        self._height = height
        self._exposure = 10.0
        self._buf: np.ndarray | None = None

    def name(self) -> str:
        return "MinimalCamera"

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def busy(self) -> bool:
        return False

    def snap_image(self) -> None:
        # Fill with a recognizable pattern
        self._buf = np.arange(
            self._width * self._height, dtype=np.uint8
        ).reshape(self._height, self._width)

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

    def initialize(self) -> None:
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
