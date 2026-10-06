"""Regression tests for the Python bridge devices (review of PR #86).

Each test documents a behavior that was found to be incorrect, unsafe, or
inconsistent with the C++ MMCore/MMDevice semantics during review, and failed
before the accompanying fixes. The notes above each test give the C++ reference
that establishes the expected behavior.
"""

from __future__ import annotations

import gc
import os
import subprocess
import sys
import textwrap
import weakref
from typing import TYPE_CHECKING

import numpy as np
import pymmcore_nano as pmn
import pytest
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

from test_bridge_devices import (
    MinimalCamera,
    MinimalGeneric,
    MinimalHub,
    MinimalSLM,
    MinimalStage,
    MinimalState,
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


def test_hub_peripheral_factories_are_called_on_load() -> None:
    """A hub may report a zero-argument factory instead of a class."""
    made: list[MinimalCamera] = []

    def make_cam() -> MinimalCamera:
        made.append(MinimalCamera())
        return made[-1]

    class FactoryHub(MinimalHub):
        def detect_installed_devices(self):
            return [("HubCam", make_cam, DeviceType.CameraDevice)]

    core = CMMCore()
    core.loadPyDevice("Hub", FactoryHub(), DeviceType.HubDevice)
    lib = core.getDeviceLibrary("Hub")
    core.loadDevice("Cam1", lib, "HubCam")
    core.initializeDevice("Cam1")
    assert type(made[-1]) is MinimalCamera
    core.setCameraDevice("Cam1")
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


# ===========================================================================
# Review round 2 (unicore-fixes2)
# ===========================================================================


# ---------------------------------------------------------------------------
# 8. Shutdown ordering and error handling.
#
#    shutdownCommon() cleared alive_ *before* calling the Python shutdown(), so
#    any DeviceCallbacks call made while shutting down (e.g. a camera reporting
#    AcqFinished after stopping its acquisition thread, as C++ cameras do) raised
#    "Device has been unloaded".  The resulting error code from Shutdown() makes
#    DeviceManager::UnloadDevice throw before erasing the device, so the device
#    stays loaded; and when the core is destroyed, ~DeviceManager calls
#    UnloadAllDevices() again, whose throw inside a destructor terminates the
#    process.  A Python error in shutdown() is therefore logged and never
#    returned as an error code.
# ---------------------------------------------------------------------------


class NotifyingShutdownCamera(MinimalCamera):
    def shutdown(self) -> None:
        # like CameraDevice.shutdown -> stop_sequence_acquisition -> acq_finished
        self._notify.acq_finished()
        self._notify.log_message("bye")


def test_notify_is_usable_during_shutdown() -> None:
    core = CMMCore()
    cam = NotifyingShutdownCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.unloadDevice("Cam")
    assert "Cam" not in core.getLoadedDevices()
    with pytest.raises(RuntimeError, match="unloaded"):
        cam._notify.log_message("too late")


class FailingShutdownCamera(MinimalCamera):
    calls = 0

    def shutdown(self) -> None:
        self.calls += 1
        raise RuntimeError("hardware already gone")


@pytest.mark.parametrize("how", ["unloadDevice", "unloadAllDevices", "reset"])
def test_python_error_in_shutdown_is_reported_once(how: str) -> None:
    """As for a C++ device whose Shutdown() fails: the unload raises and the
    device stays loaded. shutdown() is not called again: the next unload
    succeeds, and destroying the core must not call std::terminate (its
    ~DeviceManager calls Shutdown() a second time from a destructor)."""
    core = CMMCore()
    cam = FailingShutdownCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    unload = getattr(core, how)
    with pytest.raises(pmn.CMMError, match="hardware already gone"):
        unload("Cam") if how == "unloadDevice" else unload()
    assert "Cam" in core.getLoadedDevices()
    assert cam.calls == 1
    unload("Cam") if how == "unloadDevice" else unload()
    assert "Cam" not in core.getLoadedDevices()
    assert cam.calls == 1


def test_python_error_in_shutdown_does_not_abort_core_destruction() -> None:
    core = CMMCore()
    core.loadPyDevice("Cam", FailingShutdownCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    del core
    gc.collect()


# ---------------------------------------------------------------------------
# 9. Image buffers handed to CMMCore were never checked against the frame size
#    the camera reports, so an undersized array was read past its end
#    (GetImageBufferSize() bytes in getImage(); w*h*bpp bytes in InsertImage).
# ---------------------------------------------------------------------------


class UndersizedSnapCamera(MinimalCamera):
    def snap_image(self) -> None:
        self._buf = np.zeros((2, 2), dtype=np.uint8)


def test_undersized_snap_buffer_raises() -> None:
    core = CMMCore()
    core.loadPyDevice(
        "Cam", UndersizedSnapCamera(width=256, height=256), DeviceType.CameraDevice
    )
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    # MM::Camera::GetImageBuffer has no error channel; the bridge raises a
    # CMMError, which CMMCore::getImage passes through with its text.
    with pytest.raises(pmn.CMMError, match="4 bytes, but the camera reports"):
        core.getImage()


class OversizedSnapCamera(MinimalCamera):
    def snap_image(self) -> None:
        # right shape, wrong dtype: twice the bytes the camera reports
        self._buf = np.zeros((self._height, self._width), dtype=np.uint16)


def test_image_buffer_of_wrong_size_is_rejected() -> None:
    """The byte count must match exactly: a larger array hides a shape/dtype
    mismatch (here uint16 data for a camera reporting 1 byte per pixel)."""
    core = CMMCore()
    core.loadPyDevice("Cam", OversizedSnapCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    with pytest.raises(pmn.CMMError, match="bytes"):
        core.getImage()


class RaisingBufferCamera(MinimalCamera):
    def get_image_buffer(self, channel: int = 0) -> np.ndarray:
        raise RuntimeError("frame grabber timed out")


def test_get_image_buffer_error_text_reaches_python() -> None:
    core = CMMCore()
    core.loadPyDevice("Cam", RaisingBufferCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    with pytest.raises(pmn.CMMError, match="frame grabber timed out"):
        core.getImage()


class ReadOnlyCamera(MinimalCamera):
    """Hands out read-only arrays (e.g. views of a frozen or memory-mapped buffer)."""

    def snap_image(self) -> None:
        super().snap_image()
        assert self._buf is not None
        self._buf.setflags(write=False)

    def start_sequence_acquisition(self, n, interval, insert_image) -> None:
        for i in range(n):
            frame = np.full((self._height, self._width), i, dtype=np.uint8)
            frame.setflags(write=False)
            insert_image(frame, None)

    def stop_sequence_acquisition(self) -> None:
        pass

    def is_capturing(self) -> bool:
        return False


def test_read_only_arrays_are_copied_not_shared() -> None:
    """CMMCore hands camera buffers to image processors as writable memory, so
    a read-only array must not be handed to it directly (the bridge copies it;
    a writable array is shared, as before)."""
    import sys

    core = CMMCore()
    cam = ReadOnlyCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.snapImage()
    before = sys.getrefcount(cam._buf)
    img = core.getImage()
    np.testing.assert_array_equal(img, cam._buf)
    # (measured outside the assert: pytest's assertion rewriting keeps a
    # temporary reference to cam._buf while evaluating the expression)
    after = sys.getrefcount(cam._buf)
    assert after == before, "bridge kept the read-only array"
    assert not cam._buf.flags.writeable

    core.startSequenceAcquisition(2, 0, True)
    assert core.getRemainingImageCount() == 2
    np.testing.assert_array_equal(core.popNextImage(), 0)
    np.testing.assert_array_equal(core.popNextImage(), 1)

    # a writable array is still shared (no copy)
    plain = MinimalCamera()
    core.loadPyDevice("Plain", plain, DeviceType.CameraDevice)
    core.initializeDevice("Plain")
    core.setCameraDevice("Plain")
    core.snapImage()
    before = sys.getrefcount(plain._buf)
    core.getImage()
    after = sys.getrefcount(plain._buf)
    assert after == before + 1


class UndersizedSeqCamera(MinimalCamera):
    errors: list[Exception]

    def start_sequence_acquisition(self, n, interval, insert_image) -> None:
        self.errors = []
        try:
            insert_image(np.zeros((2, 2), dtype=np.uint8), None)
        except Exception as e:
            self.errors.append(e)

    def stop_sequence_acquisition(self) -> None:
        pass

    def is_capturing(self) -> bool:
        return False


def test_undersized_inserted_frame_raises() -> None:
    core = CMMCore()
    cam = UndersizedSeqCamera(width=256, height=256)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.startSequenceAcquisition(1, 0, True)
    assert len(cam.errors) == 1 and "bytes" in str(cam.errors[0])
    assert core.getRemainingImageCount() == 0


class ColorSeqCamera(MinimalCamera):
    """(h, w, 3) uint8 frames: 3 bytes per pixel, a format CMMCore tags as
    PixelType=Unknown in the circular buffer."""

    def __init__(self) -> None:
        super().__init__(width=8, height=4)

    def get_bytes_per_pixel(self) -> int:
        return 3

    def get_number_of_components(self) -> int:
        return 3

    def get_image_buffer_size(self) -> int:
        return self._width * self._height * 3

    def start_sequence_acquisition(self, n, interval, insert_image) -> None:
        for _ in range(n):
            frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            frame[..., 1] = 7
            insert_image(frame, None)

    def stop_sequence_acquisition(self) -> None:
        pass

    def is_capturing(self) -> bool:
        return False


def test_pop_next_image_uses_the_frame_format_not_the_camera() -> None:
    """Sequence frames carry their own pixel format, so popNextImage() shapes
    them correctly even when the camera's format changed since (and without
    asking the camera at all)."""
    core = CMMCore()
    cam = ColorSeqCamera()
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.startSequenceAcquisition(2, 0, True)
    assert core.getRemainingImageCount() == 2
    md = pmn.Metadata()
    img = core.popNextImageMD(md)
    assert img.shape == (4, 8, 3) and img.dtype == np.uint8
    np.testing.assert_array_equal(img[..., 1], 7)
    assert md.GetSingleTag("BytesPerPixel").GetValue() == "3"
    # the camera now reports a different format; the queued frame keeps its own
    cam._width, cam._height = 100, 100
    cam.get_image_width = lambda: 100  # type: ignore[method-assign]
    assert core.popNextImage().shape == (4, 8, 3)


# ---------------------------------------------------------------------------
# 10. Hub peripherals and the one-off adapter.
#
#    (a) The names reported by detect_installed_devices() were only registered
#        with the adapter by getInstalledDevices(); C++ adapters register their
#        device names statically, and loadSystemConfiguration() loads
#        peripherals by name without ever calling discovery.
#    (b) unloadDevice() unloaded the one-off adapter behind the device even when
#        other devices (the hub, or its peripherals) were still loaded from it:
#        CMMCore::unloadLibrary unloads every device of the module first.
# ---------------------------------------------------------------------------


def test_hub_peripheral_loadable_without_discovery() -> None:
    core = CMMCore()
    core.loadPyDevice("Hub", MinimalHub(), DeviceType.HubDevice)
    lib = core.getDeviceLibrary("Hub")
    # as in a config file: hub and peripheral loaded before initialization
    core.loadDevice("HubCam", lib, "HubCam")
    core.setParentLabel("HubCam", "Hub")
    core.initializeAllDevices()
    assert core.getParentLabel("HubCam") == "Hub"
    core.setCameraDevice("HubCam")
    core.snapImage()
    assert core.getImage().shape == (32, 64)


def _load_hub_and_peripheral(core: CMMCore) -> str:
    core.loadPyDevice("Hub", MinimalHub(), DeviceType.HubDevice)
    core.initializeDevice("Hub")
    lib = core.getDeviceLibrary("Hub")
    assert "HubCam" in core.getInstalledDevices("Hub")
    core.loadDevice("HubCam", lib, "HubCam")
    core.setParentLabel("HubCam", "Hub")
    core.initializeDevice("HubCam")
    return lib


def test_unloading_peripheral_keeps_hub() -> None:
    core = CMMCore()
    lib = _load_hub_and_peripheral(core)
    core.unloadDevice("HubCam")
    assert "Hub" in core.getLoadedDevices()
    assert core.getDeviceLibrary("Hub") == lib
    # the hub still works, and the peripheral can be loaded again
    core.loadDevice("HubCam", lib, "HubCam")
    core.initializeDevice("HubCam")


def test_unloading_hub_keeps_peripheral_like_cpp() -> None:
    core = CMMCore()
    _load_hub_and_peripheral(core)
    core.unloadDevice("Hub")
    assert "HubCam" in core.getLoadedDevices()
    core.setCameraDevice("HubCam")
    core.snapImage()
    # the adapter is released with the last device that used it
    core.unloadDevice("HubCam")
    assert "Hub" not in core.getLoadedDevices()
    core.loadPyDevice("Hub", MinimalHub(), DeviceType.HubDevice)


def test_load_system_configuration_releases_python_devices(tmp_path) -> None:
    """CMMCore::loadSystemConfiguration unloads devices itself (not through the
    Python wrapper), so the one-off adapters have to be released afterwards."""
    core = CMMCore()
    cam = MinimalCamera()
    ref = weakref.ref(cam)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    cfg = tmp_path / "empty.cfg"
    cfg.write_text("Property,Core,Initialize,0\nProperty,Core,Initialize,1\n")
    core.loadSystemConfiguration(str(cfg))
    del cam
    gc.collect()
    assert ref() is None, "Python device still referenced after loadSystemConfiguration"


# ---------------------------------------------------------------------------
# 11. Pre-init properties.
#
#    C++ adapters create pre-init properties in their constructor, so they can
#    be set (e.g. from a config file) before Initialize().  The bridge created
#    every property inside Initialize(): a pre_init property did not exist
#    before initializeDevice() and could not be set after it.
#    The bridge now calls an optional create_pre_init_properties(create_property)
#    on the Python device when the bridge device is created.
# ---------------------------------------------------------------------------


class PortCamera(MinimalCamera):
    port = "COM1"
    port_at_init: str | None = None

    def create_pre_init_properties(self, create_property: CreatePropertyFn) -> None:
        create_property(
            "Port",
            "COM1",
            1,
            False,
            pre_init=True,
            getter=lambda: self.port,
            setter=lambda v: setattr(self, "port", v),
            allowed_values=["COM1", "COM2"],
        )

    def initialize_bridge(self, create_property, notify) -> None:
        super().initialize_bridge(create_property, notify)
        self.port_at_init = self.port


@pytest.mark.parametrize("via", ["loadPyDevice", "adapter"])
def test_pre_init_property_exists_before_initialize(via: str) -> None:
    core = CMMCore()
    if via == "loadPyDevice":
        cam = PortCamera()
        core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    else:
        adapter = DeviceAdapter()
        adapter.add_device_class("Cam", PortCamera, DeviceType.CameraDevice, "")
        core.loadPyDeviceAdapter("PortAdapter", adapter)
        core.loadDevice("Cam", "PortAdapter", "Cam")
    assert "Port" in core.getDevicePropertyNames("Cam")
    assert core.isPropertyPreInit("Cam", "Port")
    assert list(core.getAllowedPropertyValues("Cam", "Port")) == ["COM1", "COM2"]
    core.setProperty("Cam", "Port", "COM2")
    core.initializeDevice("Cam")
    assert core.getProperty("Cam", "Port") == "COM2"
    # regular properties are still created by initialize_bridge
    assert "Gain" in core.getDevicePropertyNames("Cam")
    # with strict checks (as pymmcore-plus enables), it is a real pre-init property
    CMMCore.enableFeature("StrictInitializationChecks", True)
    try:
        with pytest.raises(pmn.CMMError, match="pre-init"):
            core.setProperty("Cam", "Port", "COM1")
    finally:
        CMMCore.enableFeature("StrictInitializationChecks", False)


def test_pre_init_factory_is_invalidated() -> None:
    saved: list = []

    class LeakyCamera(MinimalCamera):
        def create_pre_init_properties(self, create_property) -> None:
            saved.append(create_property)

    core = CMMCore()
    core.loadPyDevice("Cam", LeakyCamera(), DeviceType.CameraDevice)
    with pytest.raises(RuntimeError, match="create_pre_init_properties"):
        saved[0]("Late", "0", 1, False)


# ---------------------------------------------------------------------------
# 12. NotImplementedError maps to DEVICE_UNSUPPORTED_COMMAND, the code a C++
#     base class returns for an unimplemented optional method (e.g.
#     CXYStageBase::SetXOrigin), rather than a generic Python error.
# ---------------------------------------------------------------------------


def test_not_implemented_error_is_unsupported_command() -> None:
    class Stepper(MinimalXYStepper):
        def set_x_origin(self) -> None:
            raise NotImplementedError("no X origin")

    core = CMMCore()
    core.loadPyDevice("XY", Stepper(), DeviceType.XYStageDevice)
    core.initializeDevice("XY")
    with pytest.raises(pmn.CMMError, match=r"Unsupported device command.*no X origin"):
        core.setOriginX("XY")


# ---------------------------------------------------------------------------
# 13. Continuous acquisition passed LONG_MAX as num_images.  LONG_MAX is
#     2**31-1 on Windows, so Python code could not tell "unbounded" from a large
#     count portably.  The bridge now passes None for an unbounded acquisition.
# ---------------------------------------------------------------------------


def test_continuous_acquisition_passes_none() -> None:
    seen: list = []

    class Cam(MinimalCamera):
        def start_sequence_acquisition(self, n, interval, insert_image) -> None:
            seen.append(n)

        def stop_sequence_acquisition(self) -> None:
            pass

        def is_capturing(self) -> bool:
            return False

    core = CMMCore()
    core.loadPyDevice("Cam", Cam(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.setCameraDevice("Cam")
    core.startContinuousSequenceAcquisition(0)
    core.startSequenceAcquisition(5, 0, True)
    assert seen == [None, 5]


# ---------------------------------------------------------------------------
# 14. A Python exception in is_capturing() terminated the process.
#
#     PyBridgeCamera::IsCapturing() let the PyError escape, and
#     CMMCore::isSequenceRunning() is declared MMCORE_NOEXCEPT (MMCore.h) and
#     only catches CMMError, so std::terminate was called.  Acquisition loops
#     poll isSequenceRunning() continuously.  The same applies to Busy() (the
#     core's wait loops, reset()) and GetNumberOfPositions()
#     (CMMCore::getNumberOfStates() promises not to throw).  These now record
#     the error on the device and return false / 0.
# ---------------------------------------------------------------------------


def _run_in_subprocess(code: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.abspath(__file__))}
    return subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_error_in_is_capturing_does_not_abort_the_process() -> None:
    res = _run_in_subprocess(
        """
        from pymmcore_nano import CMMCore, DeviceType
        from test_bridge_devices import MinimalCamera

        class Cam(MinimalCamera):
            def is_capturing(self):
                raise RuntimeError("camera link lost")

        core = CMMCore()
        core.loadPyDevice("C", Cam(), DeviceType.CameraDevice)
        core.initializeDevice("C")
        core.setCameraDevice("C")
        assert core.isSequenceRunning() is False
        print("SURVIVED")
        """
    )
    assert "SURVIVED" in res.stdout, (res.stdout, res.stderr[-1500:])


def test_error_in_busy_is_reported_not_raised() -> None:
    class Dev(MinimalGeneric):
        def busy(self) -> bool:
            raise RuntimeError("controller unreachable")

    core = CMMCore()
    core.loadPyDevice("D", Dev(), DeviceType.GenericDevice)
    core.initializeDevice("D")
    assert core.deviceBusy("D") is False
    core.waitForDevice("D")  # must not raise or hang
    core.reset()  # waitForSystem() runs inside reset()


def test_error_in_get_number_of_positions_is_reported_not_raised() -> None:
    class Wheel(MinimalState):
        def get_number_of_positions(self) -> int:
            raise RuntimeError("no wheel")

    core = CMMCore()
    core.loadPyDevice("W", Wheel(), DeviceType.StateDevice)
    core.initializeDevice("W")
    assert core.getNumberOfStates("W") == 0


# ---------------------------------------------------------------------------
# 15. Errors from value-returning methods reached Python as a bare
#     RuntimeError (nanobind's default translation of std::runtime_error).
#     They are now CMMError, with the exception line first and the traceback
#     below, like the device errors CMMCore raises itself.
# ---------------------------------------------------------------------------


def test_error_in_value_returning_method_is_a_cmm_error() -> None:
    class Cam(MinimalCamera):
        def get_exposure(self) -> float:
            raise ValueError("exposure register unreadable")

    core = CMMCore()
    core.loadPyDevice("C", Cam(), DeviceType.CameraDevice)
    core.initializeDevice("C")
    core.setCameraDevice("C")
    with pytest.raises(pmn.CMMError) as ei:
        core.getExposure()
    lines = str(ei.value).splitlines()
    assert lines[0] == "ValueError: exposure register unreadable"
    assert "Traceback" in str(ei.value)


# ---------------------------------------------------------------------------
# 16. Hub peripheral prototypes leaked the Python device objects.
#
#     PyBridgeHub::DetectInstalledDevices() wraps every reported peripheral in
#     a prototype bridge device (HubBase::AddInstalledDevice) holding an
#     nb::object reference to the Python instance.  MMDevice's HubBase
#     destructor is `virtual ~HubBase() {}`, so the prototypes -- and the
#     Python objects they referenced -- outlived the hub, the adapter and the
#     core.  ~PyBridgeHub() now calls ClearInstalledDevices().
# ---------------------------------------------------------------------------


def test_hub_prototypes_are_released_when_the_hub_is_unloaded() -> None:
    made: list[weakref.ref] = []

    def factory() -> MinimalStage:
        d = MinimalStage()
        made.append(weakref.ref(d))
        return d

    class Hub(MinimalHub):
        def detect_installed_devices(self):
            return [("S1", factory, DeviceType.StageDevice)]

    core = CMMCore()
    core.loadPyDevice("H", Hub(), DeviceType.HubDevice)
    core.initializeDevice("H")
    assert core.getInstalledDevices("H") == ["S1"]
    gc.collect()
    assert [r() is not None for r in made] == [True]  # the prototype's instance

    core.unloadDevice("H")
    gc.collect()
    assert all(r() is None for r in made), "prototype instances outlive the hub"


# ---------------------------------------------------------------------------
# 17. PropertyHandle / DeviceCallbacks stayed "alive" after a bridge device
#     was destroyed without Shutdown().
#
#     alive_ was only cleared in shutdownCommon().  A hub prototype replaced by
#     PyBridgeAdapter::CreateDevice's DetectInstalledDevices() fallback (which
#     calls ClearInstalledDevices()) left the handles created in its
#     create_pre_init_properties() pointing at freed memory while checkAlive()
#     still passed.  The destructor now clears alive_.
# ---------------------------------------------------------------------------


def test_handle_of_a_destroyed_prototype_raises() -> None:
    handles: list[pmn.PropertyHandle] = []

    class Stage(MinimalStage):
        def create_pre_init_properties(self, create_property: CreatePropertyFn) -> None:
            handles.append(
                create_property(
                    "Port", "COM1", 1, False, pre_init=True, allowed_values=["COM1"]
                )
            )

    class Hub(MinimalHub):
        def detect_installed_devices(self):
            return [("S1", Stage, DeviceType.StageDevice)]

    core = CMMCore()
    core.loadPyDevice("H", Hub(), DeviceType.HubDevice)
    core.initializeDevice("H")
    core.getInstalledDevices("H")  # prototype #1 -> handles[0]
    assert len(handles) == 1
    with pytest.raises(pmn.CMMError):
        # unknown name: the adapter re-detects, deleting prototype #1
        core.loadDevice("X", core.getDeviceLibrary("H"), "NoSuchDevice")
    assert len(handles) == 2
    with pytest.raises(RuntimeError, match="Device has been unloaded"):
        handles[0].set_allowed_values(["COM3"])
    handles[1].set_allowed_values(["COM3"])  # the live prototype still works


# ---------------------------------------------------------------------------
# 18. PropertyHandle.set_limits() / set_allowed_values() ignored the device
#     error code.
#
#     CDeviceBase::SetPropertyLimits returns DEVICE_INVALID_PROPERTY_LIMTS for
#     a String property; the handle discarded it, so the Python device believed
#     the constraint was in place while CMMCore enforced none.
# ---------------------------------------------------------------------------


def test_set_limits_on_a_string_property_raises() -> None:
    class Dev(MinimalGeneric):
        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            super().initialize_bridge(create_property, notify)
            self.h = create_property(
                "Mode", "a", 1, False, getter=lambda: "a", setter=lambda v: None
            )

    core = CMMCore()
    dev = Dev()
    core.loadPyDevice("D", dev, DeviceType.GenericDevice)
    core.initializeDevice("D")
    with pytest.raises(RuntimeError, match="Cannot set limits"):
        dev.h.set_limits(0.0, 5.0)
    assert not core.hasPropertyLimits("D", "Mode")
    # the same check applies to create_property(limits=...)
    core.loadPyDevice("D2", _StringWithLimits(), DeviceType.GenericDevice)
    with pytest.raises(pmn.CMMError, match="Cannot set limits"):
        core.initializeDevice("D2")


class _StringWithLimits(MinimalGeneric):
    def initialize_bridge(
        self, create_property: CreatePropertyFn, notify: DeviceCallbacks
    ) -> None:
        super().initialize_bridge(create_property, notify)
        create_property("Mode", "a", 1, False, getter=lambda: "a", limits=(0, 1))


# ---------------------------------------------------------------------------
# 19. loadPyDeviceAdapter() with a name that is already loaded leaked the
#     adapter copy: registerAndStoreBridgeAdapter released the unique_ptr
#     before CPluginManager::LoadMockAdapter checked the name and threw.
# ---------------------------------------------------------------------------


def test_duplicate_adapter_name_raises_without_leaking() -> None:
    class First(MinimalGeneric):
        pass

    class Second(MinimalGeneric):
        pass

    core = CMMCore()
    a1 = DeviceAdapter()
    a1.add_device_class("Dev", First, DeviceType.GenericDevice, "")
    core.loadPyDeviceAdapter("Dup", a1)
    a2 = DeviceAdapter()
    a2.add_device_class("Dev", Second, DeviceType.GenericDevice, "")
    with pytest.raises(pmn.CMMError, match="already loaded"):
        core.loadPyDeviceAdapter("Dup", a2)
    ref = weakref.ref(Second)
    del a2, Second
    gc.collect()
    assert ref() is None, "the rejected adapter copy kept the class alive"
    core.loadDevice("D", "Dup", "Dev")  # the first registration is intact
    core.initializeDevice("D")


# ---------------------------------------------------------------------------
# 20. PropertyHandle.set_sequence_max_length() was silently ignored for a
#     property created without getter, setter or sequence_max_length (no
#     ActionLambda is attached, so CMMCore never asks it IsSequenceable).
# ---------------------------------------------------------------------------


def test_set_sequence_max_length_without_handler_raises() -> None:
    class Dev(MinimalGeneric):
        def initialize_bridge(
            self, create_property: CreatePropertyFn, notify: DeviceCallbacks
        ) -> None:
            super().initialize_bridge(create_property, notify)
            self.h = create_property("Static", "1", 3, False)

    core = CMMCore()
    dev = Dev()
    core.loadPyDevice("D", dev, DeviceType.GenericDevice)
    core.initializeDevice("D")
    with pytest.raises(RuntimeError, match="no action handler"):
        dev.h.set_sequence_max_length(10)
    assert not core.isPropertySequenceable("D", "Static")
