"""Failing tests for review findings against unicore-fixes3 (2a872e9).

Each test reproduces one defect. They are expected to FAIL on 2a872e9 and to
pass once the corresponding issue is fixed.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import numpy as np
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

from test_bridge_devices import MinimalCamera, MinimalSLM


class _Dev:
    def initialize_bridge(self, create_property, notify) -> None:
        pass

    def busy(self) -> bool:
        return False

    def shutdown(self) -> None:
        pass


# ---------------------------------------------------------------------------
# R1. Destroying a core whose Python devices' shutdown() raise aborts the
#     process.  ~CMMCore -> reset() -> unloadAllDevices() stops at the first
#     failing Shutdown() (DeviceManager::UnloadAllDevices does not continue);
#     ~DeviceManager then calls Shutdown() on the remaining devices for the
#     first time, from a destructor, and the second failure is thrown out of
#     it -> std::terminate.  shutdownCalled_ only covers a *repeated* call.
# ---------------------------------------------------------------------------


def test_core_destruction_with_failing_shutdowns_does_not_abort() -> None:
    script = textwrap.dedent(
        """
        import gc
        from pymmcore_nano import CMMCore, DeviceType

        class Gen:
            def initialize_bridge(self, cp, notify): pass
            def busy(self): return False
            def shutdown(self): raise RuntimeError("shutdown failed")

        core = CMMCore()
        core.loadPyDevice("A", Gen(), DeviceType.GenericDevice)
        core.loadPyDevice("B", Gen(), DeviceType.GenericDevice)
        core.initializeAllDevices()
        del core
        gc.collect()
        print("survived")
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "survived" in proc.stdout


# ---------------------------------------------------------------------------
# R2. A peripheral *instance* reported by a hub is wrapped in a new prototype
#     bridge device each time the hub's peripherals are detected, and every
#     bridge constructor calls create_pre_init_properties() on the instance.
#     A device that keeps its PropertyHandles (as pymmcore-plus does) ends up
#     holding the prototype's handles: later updates go to the prototype.
# ---------------------------------------------------------------------------


class _PeriphWithPreInit(_Dev):
    def __init__(self) -> None:
        self.port = "A"
        self.handle = None

    def create_pre_init_properties(self, create_property) -> None:
        self.handle = create_property(
            "Port",
            "A",
            1,
            False,
            pre_init=True,
            getter=lambda: self.port,
            setter=lambda v: setattr(self, "port", v),
            allowed_values=["A", "B"],
        )


class _InstanceHub(_Dev):
    def __init__(self) -> None:
        self.periph = _PeriphWithPreInit()

    def detect_installed_devices(self):
        return [("P", self.periph, DeviceType.GenericDevice)]


def test_hub_prototype_does_not_steal_pre_init_handles() -> None:
    core = CMMCore()
    hub = _InstanceHub()
    core.loadPyDevice("H", hub, DeviceType.HubDevice)
    lib = core.getDeviceLibrary("H")
    # configuration-file order: the peripheral is loaded by name first
    core.loadDevice("X", lib, "P")
    core.initializeDevice("H")
    core.initializeDevice("X")
    core.getInstalledDevices("H")  # e.g. a hardware wizard / GUI

    hub.periph.handle.set_allowed_values(["A", "B", "C"])
    assert "C" in core.getAllowedPropertyValues("X", "Port")


# ---------------------------------------------------------------------------
# R3. Loading a hub peripheral by name before the hub is initialized (what a
#     configuration file does) runs detect_installed_devices() on the
#     uninitialized hub; if that raises, the Python error is recorded on the
#     *hub* and loadDevice() only reports "failed to instantiate device".
# ---------------------------------------------------------------------------


class _NeedsInitHub(_Dev):
    def __init__(self) -> None:
        self.connected = False

    def initialize_bridge(self, create_property, notify) -> None:
        self.connected = True

    def detect_installed_devices(self):
        if not self.connected:
            raise RuntimeError("hub not connected")
        return [("P1", _Dev, DeviceType.GenericDevice)]


def test_peripheral_load_reports_hub_detection_error() -> None:
    ad = DeviceAdapter()
    ad.add_device_class("Hub", _NeedsInitHub, DeviceType.HubDevice, "hub")
    core = CMMCore()
    core.loadPyDeviceAdapter("PyAd", ad)
    core.loadDevice("H", "PyAd", "Hub")
    try:
        core.loadDevice("P", "PyAd", "P1")
    except RuntimeError as e:
        assert "hub not connected" in str(e)
    else:  # pragma: no cover - if detection before init is ever supported
        pass


# ---------------------------------------------------------------------------
# R4. setSLMImage() accepts a non-C-contiguous array (nb::ndarray<uint8_t>
#     has no c_contig constraint, and the size check only compares nbytes)
#     and passes pixels.data() to a device that reads it as C-contiguous:
#     the device silently receives a scrambled image.
# ---------------------------------------------------------------------------


def test_set_slm_image_non_contiguous() -> None:
    core = CMMCore()
    slm = MinimalSLM(width=4, height=3)
    core.loadPyDevice("SLM", slm, DeviceType.SLMDevice)
    core.initializeDevice("SLM")
    view = np.arange(12, dtype=np.uint8).reshape(4, 3).T  # (3, 4), F-order
    assert not view.flags.c_contiguous
    try:
        core.setSLMImage("SLM", view)
    except (TypeError, ValueError):
        return  # rejecting it is fine too
    np.testing.assert_array_equal(slm._image, view)


# ---------------------------------------------------------------------------
# R5. PyBridgeCamera::StartSequenceAcquisition calls PrepareForAcq() (which
#     opens the auto-shutter) before start_sequence_acquisition(); when the
#     latter raises, nothing closes the shutter again.
# ---------------------------------------------------------------------------


class _Shutter(_Dev):
    def __init__(self) -> None:
        self.open = False

    def set_open(self, o: bool) -> None:
        self.open = o

    def get_open(self) -> bool:
        return self.open

    def fire(self, dt: float) -> None:
        pass


class _BadStartCamera(MinimalCamera):
    def start_sequence_acquisition(self, n, interval, insert) -> None:
        raise RuntimeError("SDK: trigger mode not supported")


def test_failed_sequence_start_closes_auto_shutter() -> None:
    core = CMMCore()
    shutter = _Shutter()
    core.loadPyDevice("S", shutter, DeviceType.ShutterDevice)
    core.loadPyDevice("C", _BadStartCamera(), DeviceType.CameraDevice)
    core.initializeAllDevices()
    core.setShutterDevice("S")
    core.setCameraDevice("C")
    core.setAutoShutter(True)
    try:
        core.startSequenceAcquisition(5, 0, True)
    except RuntimeError:
        pass
    assert not shutter.open
