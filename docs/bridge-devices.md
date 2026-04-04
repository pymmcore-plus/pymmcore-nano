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
   calls `py_device.initialize(bridge)` with a `PropertyBridge` for
   registering properties

## Two Loading APIs

### `loadPyDeviceAdapter` — adapter with multiple device classes

```python
from pymmcore_nano import CMMCore, DeviceAdapter, DeviceType

adapter = DeviceAdapter()
adapter.add_device_class("MyCam", MyCameraClass, DeviceType.CameraDevice,
                         "My custom camera")
adapter.add_device_class("MyShutter", MyShutterClass, DeviceType.ShutterDevice,
                         "My custom shutter")

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

This creates a single-device adapter internally. The Python object is shared
(not copied) — the bridge holds a reference to the same instance.

#### Benefits

- Simpler for users who just want to directly instantiate and load a single
  python device without needing to create an adapter library to wrap it.

## Device Protocols

The C++ bridge expects Python device objects to implement specific methods.
These are documented as `typing.Protocol` classes in
`pymmcore_nano.protocols`:

- `PyDevice` — base: `initialize(bridge)`, `shutdown()`, `busy()`
- `PyCamera` — camera methods (snap, exposure, ROI, binning, etc.)
- `PyShutter` — `set_open()`, `get_open()`, `fire()`
- `PyStage` — single-axis positioning
- `PyXYStage` — dual-axis positioning (step-based)
- `PyState` — filter wheel / turret (`get_number_of_positions()`)
- `PyAutoFocus` — continuous/incremental focus, offset, scores
- `PyGeneric` — properties only (no device-specific methods)
- `PyHub` — peripheral discovery (`detect_installed_devices()`)
- `PySLM` — spatial light modulator (image display, exposure)

These protocols are `@runtime_checkable`. The bridge does not enforce them
at registration time — missing methods will raise `AttributeError` at call
time, just as a missing method on any Python object would.

## Property System

MM devices have a string-based property system (name/value pairs with
optional types, limits, and allowed values). The bridge integrates with
this through the `PropertyBridge` object.

### How it works

During `initialize(bridge)`, the Python device registers properties:

```python
def initialize(self, bridge):
    bridge.create_property(
        "Gain", "1.0", PropertyType.Float, read_only=False,
        getter=lambda: self._gain,
        setter=lambda v: setattr(self, '_gain', float(v)),
        limits=(0.0, 100.0)
    )
    # can also set limits separately:
    # bridge.set_property_limits("Gain", 0.0, 100.0)

    bridge.create_property(
        "Mode", "Normal", PropertyType.String, read_only=False,
        getter=lambda: self._mode,
        setter=lambda v: setattr(self, '_mode', v),
        allowed_values=["Normal", "Fast", "Slow"]
    )
    # can also set allowed values separately:
    # bridge.set_allowed_values("Mode", ["Normal", "Fast", "Slow"])
```

The `PropertyBridge`:

- Wraps `CDeviceBase::CreateProperty()` with an `MM::ActionLambda` that
  calls the Python getter/setter
- On `BeforeGet` (CMMCore reads the property): calls `getter()`, converts
  to string, stores in the MM property
- On `AfterSet` (CMMCore writes the property): reads the string value from
  the MM property, passes to `setter(value_str)`
- `set_property_limits()` and `set_allowed_values()` wrap the corresponding
  `CDeviceBase` methods

After `initialize()` returns, the `PropertyBridge` is invalidated. Calling
its methods after that raises `RuntimeError`. This is enforced via a shared
validity flag that survives even if Python stores a reference to the bridge.

### Property lifecycle

```
bridge.create_property("Gain", ...)
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

## Key Files

| File | Purpose |
|------|---------|
| `src/bridge_devices.h` | All C++ bridge device classes + PropertyBridge + PyBridgeAdapter |
| `src/_pymmcore_nano.cc` | nanobind bindings for `DeviceAdapter`, `PropertyBridge`, `loadPyDevice`, `loadPyDeviceAdapter` |
| `src/pymmcore_nano/protocols.py` | Python `Protocol` classes documenting the bridge contract |
| `tests/test_bridge_devices.py` | Tests for all device types, properties, and adapter loading |

## Supported Device Types

| Type | Bridge Class | Base Class | Python Protocol |
|------|-------------|------------|-----------------|
| Camera | `PyBridgeCamera` | `CCameraBase<>` | `PyCamera` |
| Shutter | `PyBridgeShutter` | `CShutterBase<>` | `PyShutter` |
| Stage | `PyBridgeStage` | `CStageBase<>` | `PyStage` |
| XYStage | `PyBridgeXYStage` | `CXYStageBase<>` | `PyXYStage` |
| State | `PyBridgeState` | `CStateDeviceBase<>` | `PyState` |
| AutoFocus | `PyBridgeAutoFocus` | `CAutoFocusBase<>` | `PyAutoFocus` |
| Generic | `PyBridgeGeneric` | `CGenericBase<>` | `PyGeneric` |
| Hub | `PyBridgeHub` | `HubBase<>` | `PyHub` |
| SLM | `PyBridgeSLM` | `CSLMBase<>` | `PySLM` |

## Adding a New Device Type

1. In `bridge_devices.h`:
   - Create a new class inheriting from the appropriate `C*Base<>`
   - Implement pure virtuals that don't have base defaults
   - Use `py_get`, `py_set`, `py_call` helpers for method forwarding
   - Use `initializeWithBridge(this, py_)` in `Initialize()`
   - Store `deviceName_` for `GetName()`
2. Add the type to `createBridgeDevice()` switch
3. In `protocols.py`: add a `Py*` protocol class
4. In `tests/test_bridge_devices.py`: add a minimal stub and test
5. Rebuild and run tests

## GIL and Threading

- Every bridge method that calls into Python acquires the GIL via
  `nb::gil_scoped_acquire`
- `GetImageBuffer()` returns a C++-owned buffer pointer without the GIL
- GIL acquisition is re-entrant (safe for nested calls)
- `std::atomic<bool> capturing_` is used for `IsCapturing()` to avoid
  GIL acquisition on a hot path

## Lifecycle and Cleanup

- Bridge devices hold `nb::object` references to Python devices
- Destructors acquire the GIL before releasing references (`py_.reset()`)
- All destructors are wrapped in `try/catch(...)` to prevent
  `std::terminate` if GIL acquisition fails during shutdown
- `PyBridgeAdapter` destructors similarly acquire GIL before clearing
  the device vector
- Adapter capsules are stored in a module-level `_bridge_adapters` dict
  (not a static C++ map) to ensure cleanup happens during Python GC,
  not during static destruction after interpreter shutdown
- `PropertyBridge` getter/setter callables are wrapped in a
  `shared_ptr<PyCallbacks>` whose destructor acquires the GIL — this
  handles the case where `~CDeviceBase` destroys `ActionLambda` captures
  without the GIL

## Known Limitations

- **Sequence acquisition**: The bridge's `StartSequenceAcquisition` calls
  into Python, but there is no mechanism for Python to push frames into
  CMMCore's circular buffer via `InsertImage`. This requires further design.
- **`IsCapturing` flag**: Managed by the C++ bridge, not forwarded to Python.
  If the Python device's sequence finishes independently, the flag may be
  stale.
- **RGB cameras**: `GetNumberOfComponents()` defaults to 1 (from
  `CCameraBase`). Not currently forwarded to Python.
- **Adapter cleanup on CMMCore destruction**: The `MockDeviceAdapter` API
  provides no unload notification. Adapter capsules may outlive the CMMCore
  that references them (benign — they hold Python objects, not C++ pointers).
- **SLM `set_image` array shapes**: The 8-bit overload passes a flat
  `uint8` array of total bytes; the 32-bit overload passes a `uint32`
  array of pixel count. Python implementations must handle both.
