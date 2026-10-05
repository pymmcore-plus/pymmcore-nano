"""Regression tests for the Python bridge devices (review of PR #86).

Each test documents a behavior that was found to be incorrect, unsafe, or
inconsistent with the C++ MMCore/MMDevice semantics during review, and failed
before the accompanying fixes. The notes above each test give the C++ reference
that establishes the expected behavior.
"""

from __future__ import annotations

import gc
import weakref
from typing import TYPE_CHECKING

import numpy as np
import pymmcore_nano as pmn
import pytest
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

from test_bridge_devices import (
    MinimalCamera,
    MinimalHub,
    MinimalSLM,
    MinimalXYStepper,
)

if TYPE_CHECKING:
    from pymmcore_nano import DeviceCallbacks
    from pymmcore_nano.protocols import CreatePropertyFn


# ---------------------------------------------------------------------------
# 1. PyBridgeCamera::GetImageBuffer returns a pointer into a temporary when the
#    Python array is not C-contiguous.
#
#    Before the fix, nb::cast<nb::ndarray<nb::c_contig,...>> converted a non-contiguous
#    array by calling `.astype(dtype, 'C')` (nanobind nb_ndarray.cpp,
#    ndarray_import).  With no cleanup list (nb::cast), the converted array is
#    owned only by the temporary `nd`; `img_arr_` still references the ORIGINAL
#    non-contiguous array.  When `nd` goes out of scope the converted copy is
#    freed and the returned data pointer dangles.  CMMCore then memcpy's
#    GetImageBufferSize() bytes from freed memory.
# ---------------------------------------------------------------------------


class FortranCamera(MinimalCamera):
    """Camera whose get_image_buffer() returns a Fortran-ordered array."""

    def snap_image(self) -> None:
        img = np.arange(self._width * self._height, dtype=np.uint8).reshape(
            self._height, self._width
        )
        self._buf = np.asfortranarray(img)
        assert not self._buf.flags.c_contiguous

    def get_image_buffer_size(self) -> int:
        # Allocate/free a same-sized block here (called by CMMCore *after*
        # GetImageBuffer returned) so that a freed temporary is very likely to
        # be reused and overwritten, making the use-after-free observable.
        junk = np.full(self._width * self._height, 0xEE, dtype=np.uint8)
        del junk
        return self._width * self._height


@pytest.mark.parametrize("shape", [(64, 32), (200, 200), (400, 300)])
def test_noncontiguous_image_buffer_is_copied_safely(shape: tuple[int, int]) -> None:
    h, w = shape
    core = CMMCore()
    cam = FortranCamera(width=w, height=h)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")

    expected = np.arange(w * h, dtype=np.uint8).reshape(h, w)
    for _ in range(5):
        core.snapImage()
        img = core.getImage()
        np.testing.assert_array_equal(img, expected)


# ---------------------------------------------------------------------------
# 2. SLM byte-size validation multiplied BytesPerPixel by NumberOfComponents.
#
#    In MMDevice, SLM::GetBytesPerPixel() is the *total* bytes per pixel.  The
#    canonical RGB SLM adapter, GenericSLM, returns GetBytesPerPixel() == 4 and
#    GetNumberOfComponents() == 3 (mmCoreAndDevices
#    DeviceAdapters/GenericSLM/GenericSLM.cpp:294-303).  A correctly sized
#    32-bit RGB image is therefore (h, w, 4) uint8 == w*h*4 bytes, which is what
#    the pre-PR validate_slm_image accepted.  The PR now expects w*h*4*3 bytes
#    and rejects every valid image for such a device.
# ---------------------------------------------------------------------------


class GenericSLMLike(MinimalSLM):
    """Mirrors GenericSLM's reported pixel format: 4 bytes/pixel, 3 components."""

    def get_number_of_components(self) -> int:
        return 3

    def get_bytes_per_pixel(self) -> int:
        return 4


def test_slm_bytes_per_pixel_is_total_not_per_component() -> None:
    core = CMMCore()
    slm = GenericSLMLike(width=8, height=4)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    assert core.getSLMBytesPerPixel("SLM") == 4
    assert core.getSLMNumberOfComponents("SLM") == 3

    # w*h*bytesPerPixel bytes — the image size MMCore/GenericSLM actually use.
    img = np.zeros((4, 8, 4), dtype=np.uint8)
    core.setSLMImage("SLM", img)
    assert slm._image is not None and slm._image.shape == (4, 8, 4)


# ---------------------------------------------------------------------------
# 3. unloadDevice() did not release the Python device object.
#
#    loadPyDevice registers a one-off PyBridgeAdapter (named _PyBridge_N) that
#    keeps an nb::object to the pre-instantiated device in its devices_ vector.
#    CMMCore::unloadDevice only destroys the DeviceInstance; the mock adapter
#    stays in CPluginManager::moduleMap_ until unloadLibrary()/~CMMCore.  So
#    every load/unload cycle leaks one adapter and one Python device object for
#    the lifetime of the core.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("how", ["unloadDevice", "unloadAllDevices", "reset"])
def test_unload_releases_python_device(how: str) -> None:
    core = CMMCore()
    cam = MinimalCamera()
    ref = weakref.ref(cam)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    if how == "unloadDevice":
        core.unloadDevice("Cam")
    elif how == "unloadAllDevices":
        core.unloadAllDevices()
    else:
        core.reset()
    del cam
    gc.collect()
    assert ref() is None, "unloaded Python device is still referenced by CMMCore"
    # the label can be reused
    core.loadPyDevice("Cam", MinimalCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")


# ---------------------------------------------------------------------------
# 4. Python exceptions escaped as std::runtime_error rather than device errors.
#
#    MMCore only knows CMMError.  For a C++ device whose property action
#    returns an error code, CMMCore::getSystemState() swallows the resulting
#    CMMError and records "" for that property (MMCore.cpp, getSystemState,
#    `catch (const CMMError&)`).  The bridge instead throws std::runtime_error
#    out of the ActionLambda, which bypasses every `catch (CMMError&)` in
#    MMCore: one failing Python getter makes getSystemState() (and so
#    getSystemStateCache refreshes / property browsers) fail wholesale.
# ---------------------------------------------------------------------------


class FlakyGetterCamera(MinimalCamera):
    def initialize_bridge(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        super().initialize_bridge(create_property, notify)
        create_property("Flaky", "0", 2, False, getter=lambda: 1 / 0)


def test_getSystemState_tolerates_failing_python_getter() -> None:
    core = CMMCore()
    core.loadPyDevice("Cam", FlakyGetterCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    # C++ semantics: the failing property is recorded as "" and the other
    # properties are still returned.
    state = core.getSystemState()
    assert state.getSetting("Cam", "Gain").getPropertyValue() == "1.0000"
    assert state.getSetting("Cam", "Flaky").getPropertyValue() == ""


def test_python_error_text_is_a_device_error_with_headline_first() -> None:
    """Python errors are reported like C++ device errors (CMMError), with the
    exception line first so it survives MM::MaxStrLength truncation, followed
    by the traceback."""
    core = CMMCore()
    core.loadPyDevice("Cam", FlakyGetterCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    with pytest.raises(pmn.CMMError) as ei:
        core.getProperty("Cam", "Flaky")
    msg = str(ei.value)
    assert msg.index("ZeroDivisionError: division by zero") < msg.index("Traceback")


def test_device_callbacks_expose_label() -> None:
    """A device instantiated by the bridge can learn its label from notify."""
    seen: dict[str, str] = {}

    class LabelCamera(MinimalCamera):
        def initialize_bridge(self, create_property, notify) -> None:
            seen["label"] = notify.label
            seen["get_label"] = notify.get_label()

    adapter = DeviceAdapter()
    adapter.add_device_class("Cam", LabelCamera, DeviceType.CameraDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Adapter", adapter)
    core.loadDevice("MyCam", "Adapter", "Cam")
    core.initializeDevice("MyCam")
    assert seen == {"label": "MyCam", "get_label": "MyCam"}


def test_xy_stepper_without_origin_methods_reports_unsupported() -> None:
    """Like CXYStageBase, a missing set_x_origin/set_y_origin means
    DEVICE_UNSUPPORTED_COMMAND, not an AttributeError."""

    class StepperWithoutOrigins(MinimalXYStepper):
        # hasattr() is False when the attribute lookup raises AttributeError
        @property
        def set_x_origin(self):  # type: ignore[override]
            raise AttributeError("set_x_origin")

        @property
        def set_y_origin(self):  # type: ignore[override]
            raise AttributeError("set_y_origin")

    stepper = StepperWithoutOrigins()
    assert not hasattr(stepper, "set_x_origin")

    core = CMMCore()
    core.loadPyDevice("XY", stepper, DeviceType.XYStageDevice)
    core.initializeDevice("XY")
    core.setXYStageDevice("XY")
    for fn in (core.setOriginX, core.setOriginY):
        with pytest.raises(pmn.CMMError) as ei:
            fn("XY")
        assert "AttributeError" not in str(ei.value)


# ---------------------------------------------------------------------------
# 5. Hub peripherals discovered via detect_installed_devices() could not be loaded.
#
#    In MM, DetectInstalledDevices() produces *prototype* instances; the user
#    then calls loadDevice(label, library, name) and the adapter's
#    CreateDevice(name) creates the real device.  PyBridgeAdapter::CreateDevice
#    only knows the entries added with addDevice/addDeviceClass, so a hub
#    loaded with loadPyDevice can report peripherals that can never be loaded,
#    and the instances returned by detect_installed_devices() are never the
#    ones that end up in the core.
# ---------------------------------------------------------------------------


def test_hub_peripherals_are_loadable() -> None:
    core = CMMCore()
    hub = MinimalHub()
    core.loadPyDevice("Hub", hub, DeviceType.HubDevice)
    core.initializeDevice("Hub")
    lib = core.getDeviceLibrary("Hub")
    assert "HubCam" in core.getInstalledDevices("Hub")
    core.loadDevice("HubCam", lib, "HubCam")
    core.setParentLabel("HubCam", "Hub")
    core.initializeDevice("HubCam")
    assert core.getParentLabel("HubCam") == "Hub"
    assert "HubCam" in core.getLoadedPeripheralDevices("Hub")
    # The instance reported by detect_installed_devices() is the one loaded.
    core.setCameraDevice("HubCam")
    core.snapImage()
    assert core.getImage().shape == (32, 64)


def test_hub_peripheral_classes_are_instantiated_on_load() -> None:
    """A hub may report device *classes*; each load creates a new instance."""

    class ClassHub(MinimalHub):
        def detect_installed_devices(self):
            return [("HubCam", MinimalCamera, DeviceType.CameraDevice)]

    core = CMMCore()
    core.loadPyDevice("Hub", ClassHub(), DeviceType.HubDevice)
    core.initializeDevice("Hub")
    lib = core.getDeviceLibrary("Hub")
    assert list(core.getInstalledDevices("Hub")) == ["HubCam"]
    core.loadDevice("Cam1", lib, "HubCam")
    core.loadDevice("Cam2", lib, "HubCam")
    core.initializeDevice("Cam1")
    core.initializeDevice("Cam2")
    assert core.getDeviceType("Cam1") == DeviceType.CameraDevice
    assert core.getDeviceType("Cam2") == DeviceType.CameraDevice


# ---------------------------------------------------------------------------
# 6. A Python exception raised while instantiating a device class was discarded.
#
#    PyBridgeAdapter::CreateDevice catches nb::python_error, clears it and
#    returns nullptr; CMMCore then reports a generic "Failed to load device"
#    and the real cause is lost.
# ---------------------------------------------------------------------------


class ExplodingCamera(MinimalCamera):
    def __init__(self) -> None:
        raise RuntimeError("camera firmware not found")


def test_constructor_error_is_reported() -> None:
    adapter = DeviceAdapter()
    adapter.add_device_class("Boom", ExplodingCamera, DeviceType.CameraDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Adapter", adapter)
    with pytest.raises(RuntimeError, match="firmware not found"):
        core.loadDevice("Cam", "Adapter", "Boom")


# ---------------------------------------------------------------------------
# 7. loadPyDeviceAdapter() emptied the Python DeviceAdapter, even when loading
#    failed (e.g. duplicate adapter name), leaving an unusable object behind.
# ---------------------------------------------------------------------------


def test_failed_loadPyDeviceAdapter_does_not_consume_adapter() -> None:
    adapter = DeviceAdapter()
    adapter.add_device_class("Cam", MinimalCamera, DeviceType.CameraDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Dup", adapter)
    core2 = CMMCore()
    # Same adapter object, second core: the entries were moved out by the first
    # call, so this adapter now registers zero devices.
    core2.loadPyDeviceAdapter("Dup", adapter)
    assert list(core2.getAvailableDevices("Dup")) == ["Cam"]
