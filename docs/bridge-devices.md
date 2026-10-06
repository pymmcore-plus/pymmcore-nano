# Python Bridge Devices

This document explains how pymmcore-nano enables Python-implemented devices
to be registered as real devices in CMMCore's device registry, so that all
CMMCore features (auto-shutter, config groups, device enumeration, property
system, etc.) work transparently.

## Overview

```
 Python device object          C++ bridge device           CMMCore
 (your code)                   (bridge_devices.h)          (upstream)
 ┌──────────────┐              ┌──────────────────┐        ┌───────────┐
 │ MyCamera     │◄── GIL ────▶│ PyBridgeCamera   │◄──────▶│           │
 │  .snap_image │  forwarding  │ : CCameraBase<>  │ normal │ device    │
 │  .get_exp..  │              │                  │ device │ Manager_  │
 │  .set_exp..  │              │ owns nb::object  │ calls  │           │
 └──────────────┘              └──────────────────┘        └───────────┘
```

Each Python device is wrapped in a C++ "bridge" class that inherits from the
real MM device base (`CCameraBase`, `CShutterBase`, etc.). The bridge
acquires the GIL and forwards every MM method call to the Python object.
CMMCore sees the bridge as a normal device — it lives in `deviceManager_`,
has properties in `PropertyCollection`, and participates in auto-shutter,
config groups, and state enumeration.

## How It Works (no upstream patches)

The bridge uses MMCore's existing `MockDeviceAdapter` infrastructure
(originally designed for unit testing). The flow:

1. Python creates a `DeviceAdapter` and registers device classes
2. `core.loadPyDeviceAdapter(name, adapter)` registers it with CMMCore
3. `core.loadDevice(label, adapterName, deviceName)` instantiates the Python
   class and wraps it in the appropriate bridge
4. `core.initializeDevice(label)` calls `Initialize()` on the bridge, which
   calls `py_device.initialize_bridge(create_property, notify)`: a factory for
   registering properties and a `DeviceCallbacks` object for notifying CMMCore

## Two Loading APIs

### `loadPyDeviceAdapter` — adapter with multiple device classes

```python
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

adapter = DeviceAdapter()
adapter.add_device_class(
    "MyCam", MyCameraClass, DeviceType.CameraDevice, "My custom camera"
)
adapter.add_device_class(
    "MyShutter", MyShutterClass, DeviceType.ShutterDevice, "My custom shutter"
)

core = CMMCore()
core.loadPyDeviceAdapter("MyHardware", adapter)

# Standard CMMCore device discovery and loading:
core.getAvailableDevices("MyHardware")  # ["MyCam", "MyShutter"]
core.loadDevice("Cam1", "MyHardware", "MyCam")
core.initializeDevice("Cam1")
```

#### Benefits

- All devices from one adapter share the same `LoadedDeviceAdapter` mutex,
  matching the behavior of real C++ adapters (important for devices that share
  a communication bus).
- Easier discovery on the application side
- Could be supported by python entry-points to allow third-party packages to
  provide device adapter libraries without requiring explicit registration code

### `loadPyDevice` — convenience for a single pre-instantiated device

```python
cam = MyCameraClass()
core.loadPyDevice("Cam1", cam, DeviceType.CameraDevice)
core.initializeDevice("Cam1")
```

This creates a single-device adapter internally (named `_PyBridge_<n>`). The
Python object is shared (not copied) — the bridge holds a reference to the same
instance. The adapter is unloaded again, releasing the Python object, once the
last device loaded from it is unloaded (`unloadDevice`, `unloadAllDevices`,
`reset`, `loadSystemConfiguration`). A hub loaded this way shares its adapter
with the peripherals loaded from it.

#### Benefits

- Simpler for users who just want to directly instantiate and load a single
  python device without needing to create an adapter library to wrap it.

## Device Protocols

The C++ bridge expects Python device objects to implement specific methods.
These are documented as `typing.Protocol` classes in
`pymmcore_nano.protocols`:

- `PyDevice` — base: `initialize_bridge(create_property, notify)`,
  `shutdown()`, `busy()`, and the optional
  `create_pre_init_properties(create_property)`
- `PyCamera` — camera methods (snap, exposure, ROI, binning, sequence
  acquisition, etc.)
- `PyShutter` — `set_open()`, `get_open()`, `fire()`
- `PyStage` — single-axis positioning
- `PyXYStage` — dual-axis positioning in microns
- `PyXYStepperStage` — dual-axis positioning in steps only (`CXYStageBase`
  converts microns, mirroring, and the adapter origin)
- `PyState` — filter wheel / turret (`get_number_of_positions()`, plus a
  "State" property; see [State devices](#state-devices))
- `PyAutoFocus` — continuous/incremental focus, offset, scores
- `PyGeneric` — properties only (no device-specific methods)
- `PyHub` — peripheral discovery (`detect_installed_devices()`); the reported
  names are loadable from the hub's adapter with `core.loadDevice()`, also
  before `getInstalledDevices()` was called (as a config file does)
- `PySLM` — spatial light modulator (image display, exposure)
- `PySignalIO`, `PyMagnifier`, `PySerial`, `PyGalvo` — the remaining MM
  device types

These protocols are `@runtime_checkable`. The bridge does not enforce them
at registration time — missing methods will raise `AttributeError` at call
time, just as a missing method on any Python object would.

### Errors

An exception raised by a Python device method is reported to CMMCore the way
a C++ adapter reports an error code: the device records the exception line
and traceback as its error text (code 10100), the traceback goes to the core
log, and CMMCore raises `CMMError`. A `NotImplementedError` is reported as
`DEVICE_UNSUPPORTED_COMMAND`, the code the C++ base classes return for
optional methods an adapter does not override. Exceptions in `shutdown()` are
logged only: a Shutdown error would leave the device loaded and terminate the
process when the core is destroyed (`~DeviceManager` calls Shutdown again).

## Property System

MM devices have a string-based property system (name/value pairs with
optional types, limits, and allowed values). The bridge integrates with
this through the `create_property` callable passed to `initialize_bridge()`,
which returns a `PropertyHandle` for later updates.

### How it works

During `initialize_bridge(create_property, notify)`, the Python device
registers properties:

```python
def initialize_bridge(self, create_property, notify):
    self._gain_prop = create_property(
        "Gain",
        "1.0",
        PropertyType.Float,
        read_only=False,
        getter=lambda: self._gain,
        setter=lambda v: setattr(self, "_gain", float(v)),
        limits=(0.0, 100.0),
    )
    # limits and allowed values can be changed later through the handle:
    # self._gain_prop.set_limits(0.0, 200.0)

    create_property(
        "Mode",
        "Normal",
        PropertyType.String,
        read_only=False,
        getter=lambda: self._mode,
        setter=lambda v: setattr(self, "_mode", v),
        allowed_values=["Normal", "Fast", "Slow"],
    )
```

`create_property`:

- Wraps `CDeviceBase::CreateProperty()` with an `MM::ActionLambda` that
  calls the Python getter/setter (and the sequence callbacks, when
  `sequence_max_length > 0`)
- On `BeforeGet` (CMMCore reads the property): calls `getter()`, converts
  to string, stores in the MM property
- On `AfterSet` (CMMCore writes the property): reads the string value from
  the MM property, passes to `setter(value_str)`
- Python errors in the callbacks become device errors, so e.g.
  `getSystemState()` tolerates a failing getter as it does for C++ devices

After `initialize_bridge()` returns, the factory is invalidated. Calling it
later raises `RuntimeError`. `PropertyHandle.set_limits()`,
`set_allowed_values()` and `set_sequence_max_length()` stay valid for the
device's lifetime.

### Pre-init properties

C++ adapters create pre-init properties in their constructor, so that they
exist before `Initialize()` and can be set from a configuration file. A
Python device does the same by defining

```python
def create_pre_init_properties(self, create_property):
    create_property(
        "Port",
        "COM1",
        PropertyType.String,
        False,
        pre_init=True,
        getter=...,
        setter=...,
        allowed_values=["COM1", "COM2"],
    )
```

which the bridge calls when CMMCore creates the device (before
`initialize_bridge()`). The factory passed here is invalidated when the method
returns.

### Property lifecycle

```
create_property("Gain", ...)
  → CDeviceBase::CreateProperty("Gain", "1.0", Float, false, ActionLambda)
    → MM::PropertyCollection stores MM::FloatProperty with the lambda

core.getProperty("dev", "Gain")
  → CDeviceBase::GetProperty → PropertyCollection::Get
    → MM::FloatProperty::Update → ActionLambda(BeforeGet)
      → GIL acquire → getter() → pProp->Set(str(value))
    → returns string value to CMMCore

core.setProperty("dev", "Gain", "42.5")
  → CDeviceBase::SetProperty → PropertyCollection::Set
    → validates limits (0.0-100.0) → MM::FloatProperty::Set("42.5")
    → MM::FloatProperty::Apply → ActionLambda(AfterSet)
      → GIL acquire → pProp->Get(val) → setter("42.5000")
```

CDeviceBase handles validation (limits, allowed values, read-only checks)
before the lambda is ever called.

### State devices

As in C++ state device adapters, the position labels live in
`CStateDeviceBase` — there is one label map, and the "Label" property is
derived from it:

- The Python device creates an integer "State" property (like an adapter's
  `OnState` handler) and may seed default labels with
  `notify.set_position_label(pos, label)` during `initialize_bridge()` (like
  `SetPositionLabel()` in an adapter's `Initialize()`).
- The bridge creates "Label" with `CStateBase::OnLabel` before calling
  `initialize_bridge()`, so seeded labels become its allowed values. A Python
  device may not create its own "Label" property.
- `CMMCore.defineStateLabel()`, `setStateLabel()`, `getStateLabel()` and the
  "Label" property all read and write that one map.
- `notify.on_state_changed(pos)` maps to `CStateDeviceBase::OnStateChanged()`,
  for when the device moves on its own (it notifies both State and Label).

## Key Files

| File | Purpose |
|------|---------|
| `src/bridge_devices.h` | All C++ bridge device classes + `PropertyHandle`, `DeviceCallbacks`, `PyBridgeAdapter` |
| `src/_pymmcore_nano.cc` | nanobind bindings for `DeviceAdapter`, `PropertyHandle`, `DeviceCallbacks`, `loadPyDevice`, `loadPyDeviceAdapter`, and the one-off adapter bookkeeping in `unloadDevice` & co. |
| `src/pymmcore_nano/protocols.py` | Python `Protocol` classes documenting the bridge contract |
| `tests/test_bridge_devices.py` | Tests for all device types, properties, and adapter loading |
| `tests/test_bridge_audit.py` | Regression tests from the reviews against MMCore/MMDevice semantics |

## Supported Device Types

| Type | Bridge Class | Base Class | Python Protocol |
|------|-------------|------------|-----------------|
| Camera | `PyBridgeCamera` | `CCameraBase<>` | `PyCamera` |
| Shutter | `PyBridgeShutter` | `CShutterBase<>` | `PyShutter` |
| Stage | `PyBridgeStage` | `CStageBase<>` | `PyStage` |
| XYStage | `PyBridgeXYStage` | `CXYStageBase<>` | `PyXYStage`, `PyXYStepperStage` |
| State | `PyBridgeState` | `CStateDeviceBase<>` | `PyState` |
| AutoFocus | `PyBridgeAutoFocus` | `CAutoFocusBase<>` | `PyAutoFocus` |
| Generic | `PyBridgeGeneric` | `CGenericBase<>` | `PyGeneric` |
| Hub | `PyBridgeHub` | `HubBase<>` | `PyHub` |
| SLM | `PyBridgeSLM` | `CSLMBase<>` | `PySLM` |
| SignalIO | `PyBridgeSignalIO` | `CSignalIOBase<>` | `PySignalIO` |
| Magnifier | `PyBridgeMagnifier` | `CMagnifierBase<>` | `PyMagnifier` |
| Serial | `PyBridgeSerial` | `CSerialBase<>` | `PySerial` |
| Galvo | `PyBridgeGalvo` | `CGalvoBase<>` | `PyGalvo` |

## Adding a New Device Type

1. In `bridge_devices.h`:
   - Create a new class inheriting from the appropriate `C*Base<>`
   - Implement pure virtuals that don't have base defaults
   - Use `py_get`, `py_set`, `py_call`, `py_invoke` helpers for method
     forwarding (int-returning calls turn Python errors into device errors)
   - Add `PYBRIDGE_COMMON_OVERRIDES(ClassName)`, which provides the
     constructor, `Initialize`, `Shutdown`, `Busy`, `GetName`, `GetDescription`
2. Add the type to `createBridgeDevice()` switch
3. In `protocols.py`: add a `Py*` protocol class
4. In `tests/test_bridge_devices.py`: add a minimal stub and test
5. Rebuild and run tests

## GIL and Threading

- Every bridge method that calls into Python acquires the GIL via
  `nb::gil_scoped_acquire`; CMMCore holds the device's module lock around
  those calls, so the lock order is always module lock, then GIL
- `DeviceCallbacks` methods (called from Python, GIL held) release the GIL
  before calling into CMMCore, which is what makes it safe to call them from a
  camera's acquisition thread while another thread is inside the core
- `GetImageBuffer()` returns a pointer into the Python array, which the bridge
  keeps alive until the next call (a non-contiguous array is copied first);
  the array must hold at least `width * height * bytes_per_pixel` bytes
- `insert_image` copies the frame into CMMCore's circular buffer with the
  GIL released, after checking its size the same way
- GIL acquisition is re-entrant (safe for nested calls)

## Lifecycle and Cleanup

- Bridge devices hold `nb::object` references to Python devices
- Destructors acquire the GIL before releasing references (`py_.reset()`)
- All destructors are wrapped in `try/catch(...)` to prevent
  `std::terminate` if GIL acquisition fails during shutdown
- `PyBridgeAdapter` destructors similarly acquire GIL before clearing
  the device vector
- CMMCore owns the adapters (through `LoadedDeviceAdapterImplMock`), and
  `loadPyDeviceAdapter` hands it a copy of the Python `DeviceAdapter`, so the
  Python object can be registered with several cores
- The one-off adapters created by `loadPyDevice` are unloaded when the last
  device loaded from them is unloaded (see the `unloadDevice`,
  `unloadAllDevices`, `reset` and `loadSystemConfiguration` bindings)
- `shutdown()` runs with the device still alive (so `notify` works, e.g. to
  report `acq_finished()`); afterwards `notify` and the `PropertyHandle`s
  raise `RuntimeError("Device has been unloaded")`
- Property getter/setter callables are wrapped in a
  `shared_ptr<PyCallbacks>` whose destructor acquires the GIL — this
  handles the case where `~CDeviceBase` destroys `ActionLambda` captures
  without the GIL

## Known Limitations

- **Image processors**: CMMCore passes camera buffers to an image processor
  as writable memory, so a read-only (e.g. broadcast) array returned by
  `get_image_buffer()` or passed to `insert_image()` would be written to.
- **Sequence frames of 3-component cameras** are tagged `PixelType=Unknown`
  by CMMCore (it only knows 1, 2, 4 and 8 bytes per pixel), so `popNextImage`
  falls back to asking the camera for its current dimensions.
- **`PropertyHandle` / `set_position_label` after initialization** modify the
  device's property tables without CMMCore's module lock; call them from a
  device method (which CMMCore calls with the lock held) rather than from an
  unrelated thread.
