"""Audit tests for the Python bridge devices (PR #86).

Each test here documents a behavior that was found to be incorrect, unsafe, or
inconsistent with the C++ MMCore/MMDevice semantics during review.  They are
written to FAIL on the PR head as reviewed (marked xfail(strict=True) so that
fixing one flips the test); see the notes above each test for the C++ reference
that establishes the expected behavior.

`test_noncontiguous_image_buffer_is_copied_safely` is the one exception: the
accompanying change to PyBridgeCamera::GetImageBuffer fixes it, so it is a
regular regression test.
"""

from __future__ import annotations

import gc
import weakref
from typing import TYPE_CHECKING

import numpy as np
import pytest
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

from test_bridge_devices import (
    MinimalCamera,
    MinimalHub,
    MinimalSLM,
)

if TYPE_CHECKING:
    from pymmcore_nano import DeviceCallbacks
    from pymmcore_nano.protocols import CreatePropertyFn


# ---------------------------------------------------------------------------
# 1. PyBridgeCamera::GetImageBuffer returns a pointer into a temporary when the
#    Python array is not C-contiguous.
#
#    nb::cast<nb::ndarray<nb::c_contig,...>>(img_arr_) converts a non-contiguous
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
# 2. SLM byte-size validation multiplies BytesPerPixel by NumberOfComponents.
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


@pytest.mark.xfail(
    strict=True,
    reason="SLM check uses BytesPerPixel*NumberOfComponents; MM BytesPerPixel is "
    "already the total (GenericSLM: 4 bpp, 3 components)",
)
def test_slm_bytes_per_pixel_is_total_not_per_component() -> None:
    core = CMMCore()
    slm = GenericSLMLike(width=8, height=4)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    assert core.getSLMBytesPerPixel("SLM") == 4
    assert core.getSLMNumberOfComponents("SLM") == 3

    # w*h*bytesPerPixel bytes — the image size MMCore/GenericSLM actually use.
    img = np.zeros((4, 8, 4), dtype=np.uint8)
    core.setSLMImage("SLM", img)  # raises "Image size is wrong ... Expected 384"


# ---------------------------------------------------------------------------
# 3. unloadDevice() does not release the Python device object.
#
#    loadPyDevice registers a one-off PyBridgeAdapter (named _PyBridge_N) that
#    keeps an nb::object to the pre-instantiated device in its devices_ vector.
#    CMMCore::unloadDevice only destroys the DeviceInstance; the mock adapter
#    stays in CPluginManager::moduleMap_ until unloadLibrary()/~CMMCore.  So
#    every load/unload cycle leaks one adapter and one Python device object for
#    the lifetime of the core.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="loadPyDevice's one-off mock adapter keeps the Python device alive "
    "until unloadLibrary()/~CMMCore",
)
def test_unload_releases_python_device() -> None:
    core = CMMCore()
    cam = MinimalCamera()
    ref = weakref.ref(cam)
    core.loadPyDevice("Cam", cam, DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    core.unloadDevice("Cam")
    del cam
    gc.collect()
    assert ref() is None, "unloaded Python device is still referenced by CMMCore"


# ---------------------------------------------------------------------------
# 4. Python exceptions escape as std::runtime_error rather than device errors.
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


@pytest.mark.xfail(
    strict=True,
    reason="Python errors escape as std::runtime_error, bypassing MMCore's "
    "catch(CMMError&) sites",
)
def test_getSystemState_tolerates_failing_python_getter() -> None:
    core = CMMCore()
    core.loadPyDevice("Cam", FlakyGetterCamera(), DeviceType.CameraDevice)
    core.initializeDevice("Cam")
    # C++ semantics: the failing property is recorded as "" and the other
    # properties are still returned.
    state = core.getSystemState()
    assert state.getSetting("Cam", "Gain").getPropertyValue() == "1.0000"
    assert state.getSetting("Cam", "Flaky").getPropertyValue() == ""


# ---------------------------------------------------------------------------
# 5. Hub peripherals discovered via detect_installed_devices() cannot be loaded.
#
#    In MM, DetectInstalledDevices() produces *prototype* instances; the user
#    then calls loadDevice(label, library, name) and the adapter's
#    CreateDevice(name) creates the real device.  PyBridgeAdapter::CreateDevice
#    only knows the entries added with addDevice/addDeviceClass, so a hub
#    loaded with loadPyDevice can report peripherals that can never be loaded,
#    and the instances returned by detect_installed_devices() are never the
#    ones that end up in the core.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="PyBridgeAdapter::CreateDevice does not know devices reported by "
    "detect_installed_devices()",
)
def test_hub_peripherals_are_loadable() -> None:
    core = CMMCore()
    core.loadPyDevice("Hub", MinimalHub(), DeviceType.HubDevice)
    core.initializeDevice("Hub")
    lib = core.getDeviceLibrary("Hub")
    assert "HubCam" in core.getInstalledDevices("Hub")
    core.loadDevice("HubCam", lib, "HubCam")  # Failed to load device "HubCam"
    core.setParentLabel("HubCam", "Hub")
    core.initializeDevice("HubCam")


# ---------------------------------------------------------------------------
# 6. A Python exception raised while instantiating a device class is discarded.
#
#    PyBridgeAdapter::CreateDevice catches nb::python_error, clears it and
#    returns nullptr; CMMCore then reports a generic "Failed to load device"
#    and the real cause is lost.
# ---------------------------------------------------------------------------


class ExplodingCamera(MinimalCamera):
    def __init__(self) -> None:
        raise RuntimeError("camera firmware not found")


@pytest.mark.xfail(
    strict=True, reason="PyBridgeAdapter::CreateDevice swallows the Python exception"
)
def test_constructor_error_is_reported() -> None:
    adapter = DeviceAdapter()
    adapter.add_device_class("Boom", ExplodingCamera, DeviceType.CameraDevice, "")
    core = CMMCore()
    core.loadPyDeviceAdapter("Adapter", adapter)
    with pytest.raises(RuntimeError, match="firmware not found"):
        core.loadDevice("Cam", "Adapter", "Boom")


# ---------------------------------------------------------------------------
# 7. loadPyDeviceAdapter() empties the Python DeviceAdapter even when loading
#    fails (e.g. duplicate adapter name), leaving an unusable object behind.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="loadPyDeviceAdapter moves the entries out of the Python DeviceAdapter "
    "unconditionally",
)
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
