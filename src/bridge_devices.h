// Bridge device classes that forward MM::Device calls to Python objects.
// These enable Python-implemented devices to be registered as real devices
// in CMMCore's device registry via the MockDeviceAdapter infrastructure.

#pragma once

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "DeviceBase.h"
#include "ImageMetadata.h"
#include "MMDevice.h"
#include "MockDeviceAdapter.h"

#include "Error.h" // CMMError (mmcore)

#include <algorithm>
#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace nb = nanobind;

// ============================================================================
// Helpers — factor out GIL + cast boilerplate
// ============================================================================

// A Python exception raised by a device method, carried as a C++ exception
// with the formatted traceback (what()), its last line ("ExcType: message")
// and whether it was a NotImplementedError (which maps to
// DEVICE_UNSUPPORTED_COMMAND, the code a C++ base class returns for an optional
// method the adapter does not implement). The bridge classes turn it into a
// device error code where the MM interface has one (see
// PyBridgeDeviceBase::reportPyError); value-returning methods let it
// propagate, and nanobind re-raises it in Python.
struct PyError : std::runtime_error {
    std::string headline;
    bool unsupported;
    PyError(const std::string &what, std::string headline_, bool unsupported_)
        : std::runtime_error(what), headline(std::move(headline_)), unsupported(unsupported_) {}
};

// Last non-empty line of a formatted traceback ("ExcType: message").
inline std::string tracebackHeadline(const std::string &what) {
    auto end = what.find_last_not_of("\n ");
    if (end == std::string::npos)
        return what;
    auto start = what.rfind('\n', end);
    start = start == std::string::npos ? 0 : start + 1;
    return what.substr(start, end - start + 1);
}

// Convert a pending nb::python_error (GIL held) into a PyError and clear it.
[[noreturn]] inline void throwPyError(nb::python_error &e) {
    bool unsupported = e.matches(PyExc_NotImplementedError);
    std::string msg = e.what();
    e.restore();
    PyErr_Clear();
    throw PyError(msg, tracebackHeadline(msg), unsupported);
}

template <typename T> T py_get(const nb::object &py, const char *attr) {
    nb::gil_scoped_acquire gil;
    try {
        return nb::cast<T>(py.attr(attr)());
    } catch (nb::python_error &e) {
        throwPyError(e);
    }
}

template <typename... Args>
void py_set(const nb::object &py, const char *attr, Args &&...args) {
    nb::gil_scoped_acquire gil;
    try {
        py.attr(attr)(std::forward<Args>(args)...);
    } catch (nb::python_error &e) {
        throwPyError(e);
    }
}

template <typename... Args>
int py_call(const nb::object &py, const char *attr, Args &&...args) {
    nb::gil_scoped_acquire gil;
    try {
        py.attr(attr)(std::forward<Args>(args)...);
    } catch (nb::python_error &e) {
        throwPyError(e);
    }
    return DEVICE_OK;
}

// GIL-acquiring wrapper for inline Python calls that aren't simple
// get/set/call. Catches nb::python_error and rethrows as PyError.
template <typename F> auto py_invoke(F &&fn) -> decltype(fn()) {
    nb::gil_scoped_acquire gil;
    try {
        return fn();
    } catch (nb::python_error &e) {
        throwPyError(e);
    }
}

// ============================================================================
// PropertyHandle — returned by create_property(), allows dynamic updates
// to a single property's limits and allowed values. Valid for the device's
// entire lifetime (the dev_ pointer lives as long as CMMCore owns the device).
// ============================================================================

class PropertyHandle {
    MM::Device *dev_ = nullptr;
    std::string name_;
    std::shared_ptr<std::atomic<bool>> alive_;
    // Shared with the ActionLambda in PyCallbacks so runtime updates propagate.
    std::shared_ptr<std::atomic<long>> seqMaxLength_;

    struct Vtable {
        int (*setPropertyLimits)(MM::Device *, const char *, double, double);
        int (*setAllowedValues)(MM::Device *, const char *, std::vector<std::string> &);
    };
    Vtable vt_{};

    void checkAlive() const {
        if (!alive_ || !*alive_)
            throw std::runtime_error("Device has been unloaded");
    }

  public:
    PropertyHandle() = delete;

    template <typename TDevice>
    PropertyHandle(TDevice *dev, std::string name, std::shared_ptr<std::atomic<bool>> alive,
                   std::shared_ptr<std::atomic<long>> seqMaxLength = nullptr)
        : dev_(dev), name_(std::move(name)), alive_(std::move(alive)),
          seqMaxLength_(std::move(seqMaxLength)) {
        vt_.setPropertyLimits = [](MM::Device *d, const char *n, double lo, double hi) -> int {
            return static_cast<TDevice *>(d)->SetPropertyLimits(n, lo, hi);
        };
        vt_.setAllowedValues = [](MM::Device *d, const char *n,
                                  std::vector<std::string> &vals) -> int {
            return static_cast<TDevice *>(d)->SetAllowedValues(n, vals);
        };
    }

    void setLimits(double lo, double hi) {
        checkAlive();
        vt_.setPropertyLimits(dev_, name_.c_str(), lo, hi);
    }

    void setAllowedValues(std::vector<std::string> values) {
        checkAlive();
        vt_.setAllowedValues(dev_, name_.c_str(), values);
    }

    void setSequenceMaxLength(long maxLength) {
        checkAlive();
        if (seqMaxLength_)
            *seqMaxLength_ = maxLength;
    }
};

// ============================================================================
// DeviceCallbacks — passed to Python's initialize() so the device can send
// notifications to CMMCore (property changes, position updates, etc.).
// Valid for the device's entire lifetime. Shares the alive_ flag with the
// bridge device.
// ============================================================================

class DeviceCallbacks {
    MM::Device *dev_ = nullptr;
    MM::Core *cb_ = nullptr;
    std::shared_ptr<std::atomic<bool>> alive_;

    // Type-erased CStateDeviceBase methods — only populated for state devices.
    using SetPosLabelFn = int (*)(MM::Device *, long, const char *);
    using OnStateChangedFn = int (*)(MM::Device *, long);
    SetPosLabelFn setPositionLabel_ = nullptr;
    OnStateChangedFn onStateChanged_ = nullptr;

    void checkStateDevice(const char *method) const {
        if (!setPositionLabel_)
            throw std::runtime_error(std::string(method) +
                                     " is only available on State devices");
    }

    void checkAlive() const {
        if (!alive_ || !*alive_)
            throw std::runtime_error("Device has been unloaded");
    }

  public:
    DeviceCallbacks() = delete;

    DeviceCallbacks(MM::Device *dev, MM::Core *cb, std::shared_ptr<std::atomic<bool>> alive)
        : dev_(dev), cb_(cb), alive_(std::move(alive)) {}

    // Called by initializeWithPropertyFactory for state devices.
    void enableStateDevice(SetPosLabelFn setLabel, OnStateChangedFn onStateChanged) {
        setPositionLabel_ = setLabel;
        onStateChanged_ = onStateChanged;
    }

    // The label CMMCore assigned to this device (CDeviceBase::GetLabel). This
    // is the only way a device instantiated by the bridge (loadPyDeviceAdapter)
    // can learn its own label.
    std::string getLabel() const {
        checkAlive();
        char buf[MM::MaxStrLength];
        buf[0] = '\0';
        dev_->GetLabel(buf);
        return std::string(buf);
    }

    void onPropertyChanged(const std::string &name, const std::string &value) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->OnPropertyChanged(dev_, name.c_str(), value.c_str());
    }

    void onPropertiesChanged() {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->OnPropertiesChanged(dev_);
    }

    void onStagePositionChanged(double pos) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->OnStagePositionChanged(dev_, pos);
    }

    void onXYStagePositionChanged(double x, double y) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->OnXYStagePositionChanged(dev_, x, y);
    }

    void onExposureChanged(double newExposure) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->OnExposureChanged(dev_, newExposure);
    }

    void onShutterOpenChanged(bool open) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->OnShutterOpenChanged(dev_, open);
    }

    void logMessage(const std::string &msg, bool debugOnly = false) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->LogMessage(dev_, msg.c_str(), debugOnly);
    }

    void acqFinished(int statusCode = 0) {
        checkAlive();
        nb::gil_scoped_release release;
        cb_->AcqFinished(dev_, statusCode);
    }

    void setPositionLabel(long pos, const std::string &label) {
        checkAlive();
        checkStateDevice("set_position_label");
        setPositionLabel_(dev_, pos, label.c_str());
    }

    // Notify CMMCore that the device moved on its own (e.g. a manually
    // turned turret). Sends both State and Label, like the C++
    // CStateDeviceBase::OnStateChanged().
    void onStateChanged(long pos) {
        checkAlive();
        checkStateDevice("on_state_changed");
        nb::gil_scoped_release release;
        onStateChanged_(dev_, pos);
    }
};

// ============================================================================
// createPropertyFactory — builds the create_property callable that is passed
// to Python's initialize(create_property, notify).
//
// Each call to create_property registers an MM property on the C++ device
// with an ActionLambda for get/set, and returns a PropertyHandle for
// dynamic constraint updates.
// ============================================================================

// GIL-safe destructor for Python objects captured in ActionLambda.
// CDeviceBase may destroy the ActionLambda without the GIL held.
struct PyCallbacks {
    nb::object getter;
    nb::object setter;
    // Sequence callbacks — none() if not sequenceable.
    nb::object seq_loader;  // (list[str]) -> None
    nb::object seq_starter; // () -> None
    nb::object seq_stopper; // () -> None
    // Shared with PropertyHandle so runtime updates propagate.
    std::shared_ptr<std::atomic<long>> seq_max_length;

    ~PyCallbacks() {
        try {
            nb::gil_scoped_acquire gil;
            getter.reset();
            setter.reset();
            seq_loader.reset();
            seq_starter.reset();
            seq_stopper.reset();
        } catch (...) {
        }
    }
};

// Converts a Python error into an MM device error code, recording the text on
// the device. See PyBridgeDeviceBase::reportPyError.
using PyErrorFn = std::function<int(const PyError &)>;

// Build an ActionLambda that forwards property actions to Python callables.
// Handles get/set and optionally sequencing (IsSequenceable, AfterLoadSequence,
// StartSequence, StopSequence).
// Returns the shared seq_max_length pointer (may be null if not sequenceable)
// so createPropertyFactory can pass it to PropertyHandle.
// Python errors are reported through onError as a device error code, like a
// C++ action handler returning an error, so CMMCore's own error handling
// (e.g. the per-property catch in getSystemState()) applies.
inline std::pair<std::unique_ptr<MM::ActionFunctor>, std::shared_ptr<std::atomic<long>>>
makePropertyAction(nb::object getter, nb::object setter, long seqMaxLength,
                   nb::object seqLoader, nb::object seqStarter, nb::object seqStopper,
                   PyErrorFn onError) {
    bool hasGetSet = !getter.is_none() || !setter.is_none();
    // maxLength == 0 means not sequenceable — callbacks are ignored even if
    // provided, since CMMCore won't invoke them on a non-sequenceable property.
    bool hasSeq = seqMaxLength > 0;
    if (!hasGetSet && !hasSeq)
        return {nullptr, nullptr};

    auto seqMaxPtr = std::make_shared<std::atomic<long>>(seqMaxLength);
    auto cbs = std::make_shared<PyCallbacks>(
        PyCallbacks{getter, setter, seqLoader, seqStarter, seqStopper, seqMaxPtr});
    auto functor = std::make_unique<MM::ActionLambda>(
        [cbs, onError](MM::PropertyBase *pProp, MM::ActionType eAct) -> int {
            nb::gil_scoped_acquire gil;
            try {
                if (eAct == MM::BeforeGet && !cbs->getter.is_none()) {
                    auto val = cbs->getter();
                    pProp->Set(nb::cast<std::string>(nb::str(val)).c_str());
                } else if (eAct == MM::AfterSet && !cbs->setter.is_none()) {
                    std::string val;
                    pProp->Get(val);
                    cbs->setter(nb::str(val.c_str()));
                } else if (eAct == MM::IsSequenceable) {
                    long maxLen = cbs->seq_max_length ? cbs->seq_max_length->load() : 0;
                    pProp->SetSequenceable(maxLen);
                } else if (eAct == MM::AfterLoadSequence && !cbs->seq_loader.is_none()) {
                    // Convert the C++ string sequence to a Python list
                    auto seq = pProp->GetSequence();
                    nb::list py_seq;
                    for (auto &s : seq)
                        py_seq.append(nb::str(s.c_str()));
                    cbs->seq_loader(py_seq);
                } else if (eAct == MM::StartSequence && !cbs->seq_starter.is_none()) {
                    cbs->seq_starter();
                } else if (eAct == MM::StopSequence && !cbs->seq_stopper.is_none()) {
                    cbs->seq_stopper();
                }
            } catch (nb::python_error &e) {
                try {
                    throwPyError(e);
                } catch (const PyError &err) {
                    return onError(err);
                }
            }
            return DEVICE_OK;
        });
    return {std::move(functor), seqMaxPtr};
}

// ============================================================================
// createPropertyFactory — builds the create_property callable that is passed
// to Python's initialize(create_property).
//
// Each call registers an MM property and returns a PropertyHandle for
// dynamic constraint updates. The factory is invalidated after initialize()
// returns — calling it later raises RuntimeError.
// ============================================================================

template <typename TDevice>
nb::object createPropertyFactory(TDevice *dev, std::shared_ptr<std::atomic<bool>> canCreate,
                                 std::shared_ptr<std::atomic<bool>> alive, PyErrorFn onError,
                                 const char *phase = "initialize_bridge()") {
    // Type-erased CreateProperty
    auto doCreate = [](MM::Device *d, const char *name, const char *val, MM::PropertyType t,
                       bool ro, MM::ActionFunctor *act, bool preInit) -> int {
        return static_cast<TDevice *>(d)->CreateProperty(name, val, t, ro, act, preInit);
    };

    return nb::cpp_function(
        [dev, doCreate, canCreate, alive, onError, phase](
            const std::string &name, const std::string &defaultValue, int mmType, bool readOnly,
            nb::object getter, nb::object setter, bool preInit, nb::object limits,
            nb::object allowedValues, long sequenceMaxLength, nb::object sequenceLoader,
            nb::object sequenceStarter, nb::object sequenceStopper) -> PropertyHandle {
            if (!*canCreate)
                throw std::runtime_error(std::string("create_property() can only be called "
                                                     "during ") +
                                         phase);
            if constexpr (std::is_base_of_v<CStateDeviceBase<TDevice>, TDevice>) {
                if (name == MM::g_Keyword_Label)
                    throw std::runtime_error(
                        "State devices may not create a 'Label' property: it is provided by "
                        "the bridge. Use notify.set_position_label() to define labels.");
            }

            auto [action, seqMaxPtr] =
                makePropertyAction(getter, setter, sequenceMaxLength, sequenceLoader,
                                   sequenceStarter, sequenceStopper, onError);

            int ret = doCreate(dev, name.c_str(), defaultValue.c_str(),
                               static_cast<MM::PropertyType>(mmType), readOnly, action.get(),
                               preInit);
            if (ret == DEVICE_DUPLICATE_PROPERTY)
                throw std::runtime_error("Cannot create property '" + name +
                                         "': the device already has a property with this "
                                         "name (possibly created by the C++ base class)");
            if (ret != DEVICE_OK)
                throw std::runtime_error("Cannot create property '" + name +
                                         "' (device error " + std::to_string(ret) + ")");
            action.release();

            PropertyHandle handle(dev, name, alive, seqMaxPtr);

            if (!limits.is_none()) {
                double lo = nb::cast<double>(limits[nb::int_(0)]);
                double hi = nb::cast<double>(limits[nb::int_(1)]);
                handle.setLimits(lo, hi);
            }
            if (!allowedValues.is_none()) {
                std::vector<std::string> vals;
                for (auto v : allowedValues)
                    vals.push_back(nb::cast<std::string>(nb::str(v)));
                handle.setAllowedValues(vals);
            }

            return handle;
        },
        nb::arg("name"), nb::arg("default_value"), nb::arg("mm_type"), nb::arg("read_only"),
        nb::kw_only(), nb::arg("getter") = nb::none(), nb::arg("setter") = nb::none(),
        nb::arg("pre_init") = false, nb::arg("limits") = nb::none(),
        nb::arg("allowed_values") = nb::none(), nb::arg("sequence_max_length") = 0,
        nb::arg("sequence_loader") = nb::none(), nb::arg("sequence_starter") = nb::none(),
        nb::arg("sequence_stopper") = nb::none());
}

// ============================================================================
// initializeWithPropertyFactory — calls Python's
//   initialize(create_property, notify)
// The create_property callable is invalidated after initialize() returns.
// The DeviceCallbacks object remains valid for the device's lifetime.
// ============================================================================

template <typename TDevice>
int initializeWithPropertyFactory(TDevice *dev, nb::object &py,
                                  std::shared_ptr<std::atomic<bool>> alive,
                                  MM::Core *coreCallback, PyErrorFn onError) {
    auto canCreate = std::make_shared<std::atomic<bool>>(true);
    nb::object factory = createPropertyFactory(dev, canCreate, alive, onError);

    // Create DeviceCallbacks — valid for the device's lifetime.
    // Heap-allocated, Python takes ownership.
    auto *notify = new DeviceCallbacks(dev, coreCallback, alive);

    // Enable the CStateDeviceBase callbacks for state devices.
    if constexpr (std::is_base_of_v<CStateDeviceBase<TDevice>, TDevice>) {
        notify->enableStateDevice(
            [](MM::Device *d, long pos, const char *label) -> int {
                return static_cast<TDevice *>(d)->SetPositionLabel(pos, label);
            },
            [](MM::Device *d, long pos) -> int {
                return static_cast<TDevice *>(d)->OnStateChanged(pos);
            });
    }

    nb::object py_notify = nb::cast(notify, nb::rv_policy::take_ownership);

    try {
        py.attr("initialize_bridge")(factory, py_notify);
    } catch (...) {
        *canCreate = false;
        throw;
    }
    *canCreate = false;
    return DEVICE_OK;
}

// ============================================================================
// Common helper for all bridge device classes.
// Provides shared state and behavior for Initialize/Shutdown/Busy/GetName.
// ============================================================================

template <typename TDevice> class PyBridgeDeviceBase {
  protected:
    nb::object py_;
    std::string deviceName_;
    std::string deviceDescription_;
    std::shared_ptr<std::atomic<bool>> alive_ = std::make_shared<std::atomic<bool>>(true);
    // The bridge device itself and accessors for its protected CDeviceBase
    // error/log methods (set by the PYBRIDGE_COMMON_OVERRIDES constructor,
    // where the conversion and the protected members are accessible).
    TDevice *self_ = nullptr;
    void (*setErrorText_)(TDevice *, int, const char *) = nullptr;
    void (*logMessage_)(TDevice *, const char *) = nullptr;

  public:
    // Error code under which Python exceptions are reported to CMMCore.
    static constexpr int DEVICE_PYTHON_ERROR = 10100;

    // Record an error on the device (SetErrorText) and return the error code,
    // mirroring a C++ adapter that returns an error from a device call. For a
    // Python error, `what` is the formatted traceback and `headline` its last
    // line ("ExcType: message"), which is placed first so that it survives
    // MM::MaxStrLength truncation when CMMCore retrieves the error text. The
    // full text is also sent to the core log.
    int reportError(const std::string &what, const std::string &headline,
                    bool unsupported = false) const {
        auto *dev = const_cast<TDevice *>(self_);
        if (dev && logMessage_)
            logMessage_(dev, what.c_str());
        if (unsupported) {
            // the code the C++ base classes return for an optional method the
            // adapter does not implement (e.g. CXYStageBase::SetXOrigin)
            std::string text = "Unsupported device command: " + headline;
            if (dev && setErrorText_)
                setErrorText_(dev, DEVICE_UNSUPPORTED_COMMAND, text.c_str());
            return DEVICE_UNSUPPORTED_COMMAND;
        }
        std::string text = headline == what ? what : headline + "\n" + what;
        if (dev && setErrorText_)
            setErrorText_(dev, DEVICE_PYTHON_ERROR, text.c_str());
        return DEVICE_PYTHON_ERROR;
    }

    int reportPyError(const PyError &e) const {
        return reportError(e.what(), e.headline, e.unsupported);
    }

    // A C++-side error (e.g. a bridge consistency check), reported like a
    // Python error.
    int reportPyError(const std::string &what) const { return reportError(what, what); }

    PyErrorFn pyErrorFn() const {
        return [this](const PyError &e) { return this->reportPyError(e); };
    }

  protected:
    // Device-aware versions of the free helpers. Inside the bridge classes,
    // unqualified calls resolve to these (class scope hides the namespace
    // scope). Int-returning calls convert Python errors into device error
    // codes; value-returning calls (py_get) have no error channel in the MM
    // interface and keep throwing.
    template <typename... Args>
    int py_call(const nb::object &py, const char *attr, Args &&...args) const {
        try {
            return ::py_call(py, attr, std::forward<Args>(args)...);
        } catch (const PyError &e) {
            return reportPyError(e);
        } catch (const std::runtime_error &e) {
            return reportPyError(e.what());
        }
    }

    template <typename F> auto py_invoke(F &&fn) const -> decltype(fn()) {
        using R = decltype(fn());
        if constexpr (std::is_same_v<R, int>) {
            try {
                return ::py_invoke(std::forward<F>(fn));
            } catch (const PyError &e) {
                return reportPyError(e);
            } catch (const std::runtime_error &e) {
                return reportPyError(e.what());
            }
        } else {
            return ::py_invoke(std::forward<F>(fn));
        }
    }

    PyBridgeDeviceBase(nb::object py_dev, std::string name, std::string description = "")
        : py_(std::move(py_dev)), deviceName_(std::move(name)),
          deviceDescription_(std::move(description)) {}

    ~PyBridgeDeviceBase() {
        try {
            nb::gil_scoped_acquire gil;
            py_.reset();
        } catch (...) {
        }
    }

    // Called from the bridge device constructor (i.e. when CMMCore creates
    // the device, before Initialize()). Like a C++ adapter constructor, this is
    // where pre-init properties are created: the optional Python method
    //   create_pre_init_properties(create_property)
    // is called with a factory that is invalidated when it returns.
    void createPreInitPropertiesCommon(TDevice *dev) {
        nb::gil_scoped_acquire gil;
        if (!nb::hasattr(py_, "create_pre_init_properties"))
            return;
        auto canCreate = std::make_shared<std::atomic<bool>>(true);
        nb::object factory = createPropertyFactory(dev, canCreate, alive_, pyErrorFn(),
                                                   "create_pre_init_properties()");
        try {
            py_.attr("create_pre_init_properties")(factory);
        } catch (nb::python_error &e) {
            *canCreate = false;
            throwPyError(e);
        }
        *canCreate = false;
    }

    int initializeCommon(TDevice *dev, MM::Core *coreCallback) {
        return py_invoke([&]() -> int {
            return initializeWithPropertyFactory(dev, py_, alive_, coreCallback, pyErrorFn());
        });
    }

    // Per-device-type hooks around the Python initialize_bridge() call.
    // Bridge classes hide these to add C++-side setup (see PyBridgeState).
    int beforePyInitialize() { return DEVICE_OK; }
    int afterPyInitialize() { return DEVICE_OK; }

    // The Python shutdown() runs while the device is still alive, so that it
    // can use its DeviceCallbacks (e.g. a camera reporting AcqFinished after
    // stopping its acquisition thread, as C++ cameras do). Only afterwards are
    // the callbacks invalidated.
    //
    // shutdown() is called at most once. A Python error in it is reported
    // like any device error (so unloadDevice() raises, and as for a C++
    // device whose Shutdown() fails, the device stays loaded), but a second
    // Shutdown() returns DEVICE_OK: DeviceManager::UnloadAllDevices() calls it
    // again from ~DeviceManager, where an error would terminate the process.
    bool shutdownCalled_ = false;

    int shutdownCommon() {
        if (shutdownCalled_)
            return DEVICE_OK;
        shutdownCalled_ = true;
        int ret = py_call(py_, "shutdown");
        *alive_ = false;
        return ret;
    }

    bool busyCommon() { return py_get<bool>(py_, "busy"); }

    void getNameCommon(char *name) const {
        CDeviceUtils::CopyLimitedString(name, deviceName_.c_str());
    }

    void getDescriptionCommon(char *desc) const {
        CDeviceUtils::CopyLimitedString(desc, deviceDescription_.c_str());
    }
};

#define PYBRIDGE_COMMON_OVERRIDES(ClassName)                                                   \
  public:                                                                                      \
    ClassName(nb::object py_dev, std::string name, std::string description = "")               \
        : PyBridgeDeviceBase<ClassName>(std::move(py_dev), std::move(name),                    \
                                        std::move(description)) {                              \
        this->self_ = this;                                                                    \
        this->setErrorText_ = [](ClassName *d, int code, const char *text) {                   \
            d->SetErrorText(code, text);                                                       \
        };                                                                                     \
        this->logMessage_ = [](ClassName *d, const char *text) {                               \
            d->LogMessage(text, false);                                                        \
        };                                                                                     \
        this->createPreInitPropertiesCommon(this);                                             \
    }                                                                                          \
    int Initialize() override {                                                                \
        try {                                                                                  \
            int ret = this->beforePyInitialize();                                              \
            if (ret != DEVICE_OK)                                                              \
                return ret;                                                                    \
            ret = this->initializeCommon(this, this->GetCoreCallback());                       \
            if (ret != DEVICE_OK)                                                              \
                return ret;                                                                    \
            return this->afterPyInitialize();                                                  \
        } catch (const PyError &e) {                                                           \
            return this->reportPyError(e);                                                     \
        } catch (const std::runtime_error &e) {                                                \
            return this->reportPyError(e.what());                                              \
        }                                                                                      \
    }                                                                                          \
    int Shutdown() override { return this->shutdownCommon(); }                                 \
    bool Busy() override { return this->busyCommon(); }                                        \
    void GetName(char *name) const override { this->getNameCommon(name); }                     \
    void GetDescription(char *desc) const override { this->getDescriptionCommon(desc); }

// ============================================================================
// PyBridgeCamera
// ============================================================================

class PyBridgeCamera : public CCameraBase<PyBridgeCamera>,
                       private PyBridgeDeviceBase<PyBridgeCamera> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeCamera)

    ~PyBridgeCamera() {
        try {
            nb::gil_scoped_acquire gil;
            img_arr_.reset();
        } catch (...) {
        }
    }

    nb::object img_arr_; // holds ndarray from get_image_buffer() to prevent GC

    // -- MM::Camera: getters --
    unsigned GetImageWidth() const override { return py_get<unsigned>(py_, "get_image_width"); }
    unsigned GetImageHeight() const override {
        return py_get<unsigned>(py_, "get_image_height");
    }
    unsigned GetImageBytesPerPixel() const override {
        return py_get<unsigned>(py_, "get_bytes_per_pixel");
    }
    unsigned GetNumberOfComponents() const override {
        return py_get<unsigned>(py_, "get_number_of_components");
    }
    unsigned GetNumberOfChannels() const override {
        return py_get<unsigned>(py_, "get_number_of_channels");
    }
    int GetChannelName(unsigned channel, char *name) override {
        return py_invoke([&]() -> int {
            auto pyName = nb::cast<std::string>(py_.attr("get_channel_name")(channel));
            CDeviceUtils::CopyLimitedString(name, pyName.c_str());
            return DEVICE_OK;
        });
    }
    unsigned GetBitDepth() const override { return py_get<unsigned>(py_, "get_bit_depth"); }
    long GetImageBufferSize() const override {
        return py_get<long>(py_, "get_image_buffer_size");
    }
    double GetExposure() const override { return py_get<double>(py_, "get_exposure"); }
    int GetBinning() const override { return py_get<int>(py_, "get_binning"); }

    // -- MM::Camera: setters --
    void SetExposure(double ms) override { py_set(py_, "set_exposure", ms); }
    int SetBinning(int bin) override { return py_call(py_, "set_binning", bin); }

    // -- MM::Camera: snap + buffer --
    int SnapImage() override { return py_call(py_, "snap_image"); }

    // A C-contiguous, writable view of a Python array (image processors write
    // into camera buffers through MM::ImageProcessor::Process). A
    // non-contiguous or read-only array is copied in Python first; the
    // returned object is the array the view refers to and must be kept alive
    // for as long as the pointer is used.
    using ImageArray = nb::ndarray<nb::c_contig, nb::device::cpu>;
    static std::pair<nb::object, ImageArray> contiguousImageArray(nb::object arr) {
        ImageArray nd;
        if (!nb::try_cast<ImageArray>(arr, nd, /*convert=*/false) || !isWritable(arr)) {
            arr = nb::module_::import_("numpy").attr("array")(arr, nb::arg("order") = "C",
                                                              nb::arg("copy") = true);
            nd = nb::cast<ImageArray>(arr, /*convert=*/false);
        }
        return {std::move(arr), std::move(nd)};
    }

    // nanobind imports NumPy arrays through DLPack, which does not refuse a
    // read-only array; ask the buffer protocol for a writable view instead.
    static bool isWritable(const nb::object &arr) {
        Py_buffer view;
        if (PyObject_GetBuffer(arr.ptr(), &view, PyBUF_SIMPLE | PyBUF_WRITABLE) != 0) {
            PyErr_Clear();
            return false;
        }
        PyBuffer_Release(&view);
        return true;
    }

    // CMMCore copies width * height * bytes-per-pixel bytes from the pointers
    // the camera hands it, so an array of any other size is a bug in the
    // device: too small would be read past its end, too large hides a
    // mismatch between shape() / dtype and the reported frame format.
    static void checkImageBytes(size_t actual, size_t expected) {
        if (actual != expected)
            throw std::runtime_error("Image buffer has " + std::to_string(actual) +
                                     " bytes, but the camera reports frames of " +
                                     std::to_string(expected) +
                                     " bytes (width * height * bytes per pixel)");
    }

    // Store the Python array in img_arr_ (so the pointer we hand to CMMCore
    // stays valid until the next call) and return its data pointer.
    //
    // We must NOT rely on nanobind's implicit conversion (nb::cast<ndarray<c_contig>>
    // on a non-contiguous array): that conversion produces a temporary copy
    // owned only by the local ndarray handle, so the returned pointer would
    // dangle as soon as it goes out of scope while img_arr_ still references
    // the original array. Instead, make the copy in Python and keep *that*.
    const unsigned char *holdImageArray(nb::object arr) {
        auto [obj, nd] = contiguousImageArray(std::move(arr));
        size_t expected =
            static_cast<size_t>(GetImageWidth()) * GetImageHeight() * GetImageBytesPerPixel();
        checkImageBytes(nd.nbytes(), expected);
        img_arr_ = std::move(obj);
        return static_cast<const unsigned char *>(nd.data());
    }

    // MM::Camera::GetImageBuffer has no error code. A Python error (or an
    // array of the wrong size) is recorded on the device and logged, and
    // rethrown as a CMMError with the same text: CMMCore::getImage() passes
    // a CMMError through unchanged (anything else becomes "unknown system
    // exception"), so the Python message reaches the caller.
    template <typename F> const unsigned char *imageBuffer(F &&fn) {
        try {
            return py_invoke(std::forward<F>(fn));
        } catch (const PyError &e) {
            reportPyError(e);
            throw CMMError(e.headline + "\n" + e.what());
        } catch (const std::runtime_error &e) {
            reportPyError(e.what());
            throw CMMError(e.what());
        }
    }

    const unsigned char *GetImageBuffer() override {
        return imageBuffer([&]() -> const unsigned char * {
            return holdImageArray(py_.attr("get_image_buffer")());
        });
    }

    const unsigned char *GetImageBuffer(unsigned channelNr) override {
        return imageBuffer([&]() -> const unsigned char * {
            return holdImageArray(py_.attr("get_image_buffer")(channelNr));
        });
    }

    // -- MM::Camera: ROI --
    int SetROI(unsigned x, unsigned y, unsigned w, unsigned h) override {
        return py_call(py_, "set_roi", x, y, w, h);
    }
    int ClearROI() override { return py_call(py_, "clear_roi"); }

    int GetROI(unsigned &x, unsigned &y, unsigned &w, unsigned &h) override {
        return py_invoke([&]() -> int {
            auto roi = py_.attr("get_roi")();
            x = nb::cast<unsigned>(roi[nb::int_(0)]);
            y = nb::cast<unsigned>(roi[nb::int_(1)]);
            w = nb::cast<unsigned>(roi[nb::int_(2)]);
            h = nb::cast<unsigned>(roi[nb::int_(3)]);
            return DEVICE_OK;
        });
    }

    // -- MM::Camera: exposure sequencing --
    std::vector<double> exposureSeq_;

    int IsExposureSequenceable(bool &f) const override {
        return py_invoke([&]() -> int {
            f = py_get<bool>(py_, "is_exposure_sequenceable");
            return DEVICE_OK;
        });
    }
    int GetExposureSequenceMaxLength(long &nrEvents) const override {
        return py_invoke([&]() -> int {
            nrEvents = py_get<long>(py_, "get_exposure_sequence_max_length");
            return DEVICE_OK;
        });
    }
    int ClearExposureSequence() override {
        exposureSeq_.clear();
        return DEVICE_OK;
    }
    int AddToExposureSequence(double exposureTime_ms) override {
        exposureSeq_.push_back(exposureTime_ms);
        return DEVICE_OK;
    }
    int SendExposureSequence() const override {
        return py_invoke([&]() -> int {
            nb::list py_seq;
            for (double v : exposureSeq_)
                py_seq.append(v);
            py_.attr("load_exposure_sequence")(py_seq);
            return DEVICE_OK;
        });
    }
    int StartExposureSequence() override { return py_call(py_, "start_exposure_sequence"); }
    int StopExposureSequence() override { return py_call(py_, "stop_exposure_sequence"); }

    // -- MM::Camera: sequence acquisition --
    bool IsCapturing() override { return py_get<bool>(py_, "is_capturing"); }

    int StartSequenceAcquisition(long numImages, double interval_ms,
                                 bool stopOnOverflow) override {
        int ret = GetCoreCallback()->PrepareForAcq(this);
        if (ret != DEVICE_OK)
            return ret;

        // Cache image dimensions once for the whole sequence. These shouldn't
        // change during a running acquisition and querying them on every frame
        // crosses the Python bridge 4 times per frame.
        unsigned w = GetImageWidth();
        unsigned h = GetImageHeight();
        unsigned bpp = GetImageBytesPerPixel();
        unsigned nComp = GetNumberOfComponents();

        return py_invoke([&]() -> int {
            // Create an insert_image callable that pushes a frame into
            // CMMCore's circular buffer. Python calls this per frame.
            auto *self = this;
            auto alive = alive_;
            // insert_image returns False on buffer overflow so Python
            // can stop acquisition when stopOnOverflow is set.
            nb::object inserter = nb::cpp_function(
                [self, alive, w, h, bpp, nComp](nb::object arr, nb::object metadata) -> bool {
                    // The Python acquisition thread may outlive the bridge
                    // device (e.g. unloadDevice while a runaway thread is
                    // still producing frames); `self` is dangling then.
                    if (!*alive)
                        throw std::runtime_error("Device has been unloaded");
                    auto [obj, nd] = contiguousImageArray(std::move(arr));
                    checkImageBytes(nd.nbytes(), static_cast<size_t>(w) * h * bpp);

                    // Build serialized metadata in MMCore's format. CMMCore
                    // tags the frame with Width/Height/PixelType, but knows no
                    // PixelType for e.g. 3 bytes per pixel ("Unknown"); these
                    // two tags let popNextImage() shape the frame regardless.
                    Metadata md;
                    md.PutImageTag("BytesPerPixel", std::to_string(bpp));
                    md.PutImageTag("NumberOfComponents", std::to_string(nComp));
                    if (!metadata.is_none()) {
                        nb::dict d = nb::cast<nb::dict>(metadata);
                        for (auto [key, val] : d) {
                            auto k = nb::cast<std::string>(nb::str(key));
                            auto v = nb::cast<std::string>(nb::str(val));
                            md.PutImageTag(k.c_str(), v);
                        }
                    }
                    std::string mdStr = md.Serialize();

                    int ret;
                    {
                        nb::gil_scoped_release release;
                        ret = self->GetCoreCallback()->InsertImage(
                            self, static_cast<const unsigned char *>(nd.data()), w, h, bpp,
                            nComp, mdStr.c_str());
                    }
                    return ret == DEVICE_OK;
                },
                nb::arg("image"), nb::arg("metadata") = nb::none());

            // An unbounded acquisition (StartSequenceAcquisition(interval) and
            // CMMCore::startContinuousSequenceAcquisition use LONG_MAX, which
            // is only 2**31-1 on Windows) is passed to Python as None.
            nb::object py_num = numImages == LONG_MAX ? nb::none() : nb::cast(numImages);
            py_.attr("start_sequence_acquisition")(py_num, interval_ms, inserter);
            return DEVICE_OK;
        });
    }

    int StartSequenceAcquisition(double interval_ms) override {
        return StartSequenceAcquisition(LONG_MAX, interval_ms, false);
    }

    int StopSequenceAcquisition() override { return py_call(py_, "stop_sequence_acquisition"); }
};

// ============================================================================
// PyBridgeShutter
// ============================================================================

class PyBridgeShutter : public CShutterBase<PyBridgeShutter>,
                        private PyBridgeDeviceBase<PyBridgeShutter> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeShutter)

    // -- MM::Shutter --
    int SetOpen(bool open) override { return py_call(py_, "set_open", open); }

    int GetOpen(bool &open) override {
        return py_invoke([&]() -> int {
            open = py_get<bool>(py_, "get_open");
            return DEVICE_OK;
        });
    }

    int Fire(double deltaT) override { return py_call(py_, "fire", deltaT); }
};

// ============================================================================
// PyBridgeStage
// ============================================================================

class PyBridgeStage : public CStageBase<PyBridgeStage>,
                      private PyBridgeDeviceBase<PyBridgeStage> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeStage)

    // -- MM::Stage: position --
    int SetPositionUm(double pos) override { return py_call(py_, "set_position_um", pos); }
    int GetPositionUm(double &pos) override {
        return py_invoke([&]() -> int {
            pos = py_get<double>(py_, "get_position_um");
            return DEVICE_OK;
        });
    }
    int SetRelativePositionUm(double d) override {
        return py_call(py_, "set_relative_position_um", d);
    }
    int SetPositionSteps(long steps) override {
        return py_call(py_, "set_position_steps", steps);
    }
    int GetPositionSteps(long &steps) override {
        return py_invoke([&]() -> int {
            steps = py_get<long>(py_, "get_position_steps");
            return DEVICE_OK;
        });
    }
    int SetAdapterOriginUm(double d) override {
        return py_call(py_, "set_adapter_origin_um", d);
    }
    int SetOrigin() override { return py_call(py_, "set_origin"); }
    int GetLimits(double &lo, double &hi) override {
        return py_invoke([&]() -> int {
            auto lim = py_.attr("get_limits")();
            lo = nb::cast<double>(lim[nb::int_(0)]);
            hi = nb::cast<double>(lim[nb::int_(1)]);
            return DEVICE_OK;
        });
    }

    // -- MM::Stage: motion --
    int Move(double velocity) override { return py_call(py_, "move", velocity); }
    int Stop() override { return py_call(py_, "stop"); }
    int Home() override { return py_call(py_, "home"); }

    // -- MM::Stage: focus --
    int GetFocusDirection(MM::FocusDirection &direction) override {
        return py_invoke([&]() -> int {
            direction =
                static_cast<MM::FocusDirection>(py_get<int>(py_, "get_focus_direction"));
            return DEVICE_OK;
        });
    }
    bool IsContinuousFocusDrive() const override {
        return py_get<bool>(py_, "is_continuous_focus_drive");
    }

    // -- MM::Stage: sequencing --
    std::vector<double> stageSeq_;

    int IsStageSequenceable(bool &f) const override {
        return py_invoke([&]() -> int {
            f = py_get<bool>(py_, "is_stage_sequenceable");
            return DEVICE_OK;
        });
    }
    int GetStageSequenceMaxLength(long &nrEvents) const override {
        return py_invoke([&]() -> int {
            nrEvents = py_get<long>(py_, "get_stage_sequence_max_length");
            return DEVICE_OK;
        });
    }
    int ClearStageSequence() override {
        stageSeq_.clear();
        return DEVICE_OK;
    }
    int AddToStageSequence(double position) override {
        stageSeq_.push_back(position);
        return DEVICE_OK;
    }
    int SendStageSequence() override {
        return py_invoke([&]() -> int {
            nb::list py_seq;
            for (double v : stageSeq_)
                py_seq.append(v);
            py_.attr("load_stage_sequence")(py_seq);
            return DEVICE_OK;
        });
    }
    int StartStageSequence() override { return py_call(py_, "start_stage_sequence"); }
    int StopStageSequence() override { return py_call(py_, "stop_stage_sequence"); }
};

// ============================================================================
// PyBridgeXYStage
// ============================================================================

class PyBridgeXYStage : public CXYStageBase<PyBridgeXYStage>,
                        private PyBridgeDeviceBase<PyBridgeXYStage> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeXYStage)

    // Like C++ adapters, a Python XY stage either works in microns (it defines
    // set_position_um), or is a stepper that only implements the steps methods.
    // For a stepper, CXYStageBase converts um <-> steps, applying the
    // TransposeMirrorX/Y properties and the adapter origin, exactly as for a C++
    // adapter that doesn't override SetPositionUm.
    bool usesSteps_ = false;
    bool hasSetOrigin_ = false;
    bool hasSetXOrigin_ = false;
    bool hasSetYOrigin_ = false;

    int beforePyInitialize() {
        nb::gil_scoped_acquire gil;
        usesSteps_ = !nb::hasattr(py_, "set_position_um");
        hasSetOrigin_ = nb::hasattr(py_, "set_origin");
        hasSetXOrigin_ = nb::hasattr(py_, "set_x_origin");
        hasSetYOrigin_ = nb::hasattr(py_, "set_y_origin");
        return DEVICE_OK;
    }

    // A stepper's moves are reported to CMMCore (as e.g. DemoCamera's XY stage
    // does); a micron-based Python device notifies for itself.
    int notifyPositionUm() {
        double x, y;
        int ret = CXYStageBase::GetPositionUm(x, y);
        if (ret != DEVICE_OK)
            return ret;
        return OnXYStagePositionChanged(x, y);
    }

    // -- MM::XYStage: position (um) --
    int SetPositionUm(double x, double y) override {
        if (!usesSteps_)
            return py_call(py_, "set_position_um", x, y);
        int ret = CXYStageBase::SetPositionUm(x, y);
        return ret == DEVICE_OK ? OnXYStagePositionChanged(x, y) : ret;
    }
    int GetPositionUm(double &x, double &y) override {
        if (usesSteps_)
            return CXYStageBase::GetPositionUm(x, y);
        return py_invoke([&]() -> int {
            auto pos = py_.attr("get_position_um")();
            x = nb::cast<double>(pos[nb::int_(0)]);
            y = nb::cast<double>(pos[nb::int_(1)]);
            return DEVICE_OK;
        });
    }
    int SetRelativePositionUm(double dx, double dy) override {
        if (!usesSteps_)
            return py_call(py_, "set_relative_position_um", dx, dy);
        int ret = CXYStageBase::SetRelativePositionUm(dx, dy);
        return ret == DEVICE_OK ? notifyPositionUm() : ret;
    }
    int SetAdapterOriginUm(double x, double y) override {
        if (usesSteps_)
            return CXYStageBase::SetAdapterOriginUm(x, y);
        return py_call(py_, "set_adapter_origin_um", x, y);
    }
    int UsesOnXYStagePositionChanged(bool &result) const override {
        result = usesSteps_;
        return DEVICE_OK;
    }

    // -- MM::XYStage: position (steps) --
    int SetPositionSteps(long x, long y) override {
        return py_call(py_, "set_position_steps", x, y);
    }
    int GetPositionSteps(long &x, long &y) override {
        return py_invoke([&]() -> int {
            auto pos = py_.attr("get_position_steps")();
            x = nb::cast<long>(pos[nb::int_(0)]);
            y = nb::cast<long>(pos[nb::int_(1)]);
            return DEVICE_OK;
        });
    }
    int SetRelativePositionSteps(long x, long y) override {
        return py_call(py_, "set_relative_position_steps", x, y);
    }

    // -- MM::XYStage: motion --
    int Home() override { return py_call(py_, "home"); }
    int Stop() override { return py_call(py_, "stop"); }
    int Move(double vx, double vy) override { return py_call(py_, "move", vx, vy); }

    // -- MM::XYStage: origin --
    // Without a device-specific set_origin, zero the adapter origin (software
    // origin), as many C++ adapters do.
    int SetOrigin() override {
        if (!hasSetOrigin_)
            return SetAdapterOriginUm(0.0, 0.0);
        return py_call(py_, "set_origin");
    }
    // Without device-specific methods, report DEVICE_UNSUPPORTED_COMMAND as
    // CXYStageBase does for a C++ adapter that doesn't override these.
    int SetXOrigin() override {
        return hasSetXOrigin_ ? py_call(py_, "set_x_origin") : CXYStageBase::SetXOrigin();
    }
    int SetYOrigin() override {
        return hasSetYOrigin_ ? py_call(py_, "set_y_origin") : CXYStageBase::SetYOrigin();
    }

    // -- MM::XYStage: limits + step size --
    int GetLimitsUm(double &xMin, double &xMax, double &yMin, double &yMax) override {
        return py_invoke([&]() -> int {
            auto lim = py_.attr("get_limits_um")();
            xMin = nb::cast<double>(lim[nb::int_(0)]);
            xMax = nb::cast<double>(lim[nb::int_(1)]);
            yMin = nb::cast<double>(lim[nb::int_(2)]);
            yMax = nb::cast<double>(lim[nb::int_(3)]);
            return DEVICE_OK;
        });
    }
    int GetStepLimits(long &xMin, long &xMax, long &yMin, long &yMax) override {
        return py_invoke([&]() -> int {
            auto lim = py_.attr("get_step_limits")();
            xMin = nb::cast<long>(lim[nb::int_(0)]);
            xMax = nb::cast<long>(lim[nb::int_(1)]);
            yMin = nb::cast<long>(lim[nb::int_(2)]);
            yMax = nb::cast<long>(lim[nb::int_(3)]);
            return DEVICE_OK;
        });
    }
    double GetStepSizeXUm() override { return py_get<double>(py_, "get_step_size_x_um"); }
    double GetStepSizeYUm() override { return py_get<double>(py_, "get_step_size_y_um"); }

    // -- MM::XYStage: sequencing --
    std::vector<std::pair<double, double>> xySeq_;

    int IsXYStageSequenceable(bool &f) const override {
        return py_invoke([&]() -> int {
            f = py_get<bool>(py_, "is_xy_stage_sequenceable");
            return DEVICE_OK;
        });
    }
    int GetXYStageSequenceMaxLength(long &nrEvents) const override {
        return py_invoke([&]() -> int {
            nrEvents = py_get<long>(py_, "get_xy_stage_sequence_max_length");
            return DEVICE_OK;
        });
    }
    int ClearXYStageSequence() override {
        xySeq_.clear();
        return DEVICE_OK;
    }
    int AddToXYStageSequence(double positionX, double positionY) override {
        xySeq_.emplace_back(positionX, positionY);
        return DEVICE_OK;
    }
    int SendXYStageSequence() override {
        return py_invoke([&]() -> int {
            nb::list py_seq;
            for (auto &[x, y] : xySeq_)
                py_seq.append(nb::make_tuple(x, y));
            py_.attr("load_xy_stage_sequence")(py_seq);
            return DEVICE_OK;
        });
    }
    int StartXYStageSequence() override { return py_call(py_, "start_xy_stage_sequence"); }
    int StopXYStageSequence() override { return py_call(py_, "stop_xy_stage_sequence"); }
};

// ============================================================================
// PyBridgeState
// ============================================================================

class PyBridgeState : public CStateDeviceBase<PyBridgeState>,
                      private PyBridgeDeviceBase<PyBridgeState> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeState)

  public:
    // As in C++ state device adapters, CStateDeviceBase owns the position
    // labels and the "Label" property (via CStateBase::OnLabel); the Python
    // device provides the "State" property and seeds default labels with
    // notify.set_position_label(). Label is created before the Python
    // initialize so that seeded labels also become its allowed values.
    int beforePyInitialize() {
        return CreateStringProperty(MM::g_Keyword_Label, "", false,
                                    new CPropertyAction(this, &CStateBase::OnLabel));
    }

    int afterPyInitialize() {
        if (!HasProperty(MM::g_Keyword_State))
            throw std::runtime_error("Python State devices must create a 'State' property "
                                     "in initialize_bridge()");
        return DEVICE_OK;
    }

    // -- MM::State --
    // CStateDeviceBase provides defaults for SetPosition, GetPosition,
    // GetPositionLabel, SetPositionLabel, GetLabelPosition, SetGateOpen,
    // GetGateOpen — all driven by the "State" and "Label" properties.
    // The only pure virtual remaining is GetNumberOfPositions.
    unsigned long GetNumberOfPositions() const override {
        return py_invoke(
            [&]() { return nb::cast<unsigned long>(py_.attr("get_number_of_positions")()); });
    }
};

// ============================================================================
// PyBridgeAutoFocus
// ============================================================================

class PyBridgeAutoFocus : public CAutoFocusBase<PyBridgeAutoFocus>,
                          private PyBridgeDeviceBase<PyBridgeAutoFocus> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeAutoFocus)

    // -- MM::AutoFocus --
    int SetContinuousFocusing(bool state) override {
        return py_call(py_, "set_continuous_focusing", state);
    }
    int GetContinuousFocusing(bool &state) override {
        return py_invoke([&]() -> int {
            state = py_get<bool>(py_, "get_continuous_focusing");
            return DEVICE_OK;
        });
    }
    bool IsContinuousFocusLocked() override {
        return py_get<bool>(py_, "is_continuous_focus_locked");
    }
    int FullFocus() override { return py_call(py_, "full_focus"); }
    int IncrementalFocus() override { return py_call(py_, "incremental_focus"); }
    int GetLastFocusScore(double &score) override {
        return py_invoke([&]() -> int {
            score = py_get<double>(py_, "get_last_focus_score");
            return DEVICE_OK;
        });
    }
    int GetCurrentFocusScore(double &score) override {
        return py_invoke([&]() -> int {
            score = py_get<double>(py_, "get_current_focus_score");
            return DEVICE_OK;
        });
    }
    int GetOffset(double &offset) override {
        return py_invoke([&]() -> int {
            offset = py_get<double>(py_, "get_offset");
            return DEVICE_OK;
        });
    }
    int SetOffset(double offset) override { return py_call(py_, "set_offset", offset); }
};

// ============================================================================
// PyBridgeSignalIO
// ============================================================================

class PyBridgeSignalIO : public CSignalIOBase<PyBridgeSignalIO>,
                         private PyBridgeDeviceBase<PyBridgeSignalIO> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeSignalIO)

    // -- MM::SignalIO: core --
    int SetGateOpen(bool open) override { return py_call(py_, "set_gate_open", open); }
    int GetGateOpen(bool &open) override {
        return py_invoke([&]() -> int {
            open = py_get<bool>(py_, "get_gate_open");
            return DEVICE_OK;
        });
    }
    int SetSignal(double volts) override { return py_call(py_, "set_signal", volts); }
    int GetSignal(double &volts) override {
        return py_invoke([&]() -> int {
            volts = py_get<double>(py_, "get_signal");
            return DEVICE_OK;
        });
    }
    int GetLimits(double &minVolts, double &maxVolts) override {
        return py_invoke([&]() -> int {
            auto lim = py_.attr("get_limits")();
            minVolts = nb::cast<double>(lim[nb::int_(0)]);
            maxVolts = nb::cast<double>(lim[nb::int_(1)]);
            return DEVICE_OK;
        });
    }

    // -- MM::SignalIO: DA sequencing --
    std::vector<double> daSeq_;

    int IsDASequenceable(bool &f) const override {
        return py_invoke([&]() -> int {
            f = py_get<bool>(py_, "is_da_sequenceable");
            return DEVICE_OK;
        });
    }
    int GetDASequenceMaxLength(long &nrEvents) const override {
        return py_invoke([&]() -> int {
            nrEvents = py_get<long>(py_, "get_da_sequence_max_length");
            return DEVICE_OK;
        });
    }
    int ClearDASequence() override {
        daSeq_.clear();
        return DEVICE_OK;
    }
    int AddToDASequence(double voltage) override {
        daSeq_.push_back(voltage);
        return DEVICE_OK;
    }
    int SendDASequence() override {
        return py_invoke([&]() -> int {
            nb::list py_seq;
            for (double v : daSeq_)
                py_seq.append(v);
            py_.attr("load_da_sequence")(py_seq);
            return DEVICE_OK;
        });
    }
    int StartDASequence() override { return py_call(py_, "start_da_sequence"); }
    int StopDASequence() override { return py_call(py_, "stop_da_sequence"); }
};

// ============================================================================
// PyBridgeMagnifier
// ============================================================================

class PyBridgeMagnifier : public CMagnifierBase<PyBridgeMagnifier>,
                          private PyBridgeDeviceBase<PyBridgeMagnifier> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeMagnifier)

    double GetMagnification() override { return py_get<double>(py_, "get_magnification"); }
};

// ============================================================================
// PyBridgeSerial
// ============================================================================

class PyBridgeSerial : public CSerialBase<PyBridgeSerial>,
                       private PyBridgeDeviceBase<PyBridgeSerial> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeSerial)

    MM::PortType GetPortType() const override {
        return static_cast<MM::PortType>(py_get<int>(py_, "get_port_type"));
    }

    int SetCommand(const char *command, const char *term) override {
        return py_invoke([&]() -> int {
            py_.attr("set_command")(std::string(command),
                                    term ? std::string(term) : std::string());
            return DEVICE_OK;
        });
    }

    int GetAnswer(char *txt, unsigned maxChars, const char *term) override {
        return py_invoke([&]() -> int {
            auto answer = nb::cast<std::string>(
                py_.attr("get_answer")(term ? std::string(term) : std::string()));
            strncpy(txt, answer.c_str(), maxChars);
            if (maxChars > 0)
                txt[maxChars - 1] = '\0';
            return DEVICE_OK;
        });
    }

    int Write(const unsigned char *buf, unsigned long bufLen) override {
        return py_invoke([&]() -> int {
            // Pass as Python bytes object
            nb::object py_bytes = nb::steal(
                PyBytes_FromStringAndSize(reinterpret_cast<const char *>(buf), bufLen));
            py_.attr("write")(py_bytes);
            return DEVICE_OK;
        });
    }

    int Read(unsigned char *buf, unsigned long bufLen, unsigned long &charsRead) override {
        return py_invoke([&]() -> int {
            nb::object result = py_.attr("read")(bufLen);
            Py_buffer view;
            if (PyObject_GetBuffer(result.ptr(), &view, PyBUF_SIMPLE) != 0)
                throw nb::python_error();
            charsRead = std::min(static_cast<unsigned long>(view.len), bufLen);
            std::memcpy(buf, view.buf, charsRead);
            PyBuffer_Release(&view);
            return DEVICE_OK;
        });
    }

    int Purge() override { return py_call(py_, "purge"); }
};

// ============================================================================
// PyBridgeGalvo
// ============================================================================

class PyBridgeGalvo : public CGalvoBase<PyBridgeGalvo>,
                      private PyBridgeDeviceBase<PyBridgeGalvo> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeGalvo)

    // -- MM::Galvo: position + illumination --
    int PointAndFire(double x, double y, double time_us) override {
        return py_call(py_, "point_and_fire", x, y, time_us);
    }
    int SetSpotInterval(double pulseInterval_us) override {
        return py_call(py_, "set_spot_interval", pulseInterval_us);
    }
    int SetPosition(double x, double y) override { return py_call(py_, "set_position", x, y); }
    int GetPosition(double &x, double &y) override {
        return py_invoke([&]() -> int {
            auto pos = py_.attr("get_position")();
            x = nb::cast<double>(pos[nb::int_(0)]);
            y = nb::cast<double>(pos[nb::int_(1)]);
            return DEVICE_OK;
        });
    }
    int SetIlluminationState(bool on) override {
        return py_call(py_, "set_illumination_state", on);
    }

    // -- MM::Galvo: range --
    double GetXRange() override { return py_get<double>(py_, "get_x_range"); }
    double GetXMinimum() override { return py_get<double>(py_, "get_x_minimum"); }
    double GetYRange() override { return py_get<double>(py_, "get_y_range"); }
    double GetYMinimum() override { return py_get<double>(py_, "get_y_minimum"); }

    // -- MM::Galvo: polygons --
    int AddPolygonVertex(int polygonIndex, double x, double y) override {
        return py_call(py_, "add_polygon_vertex", polygonIndex, x, y);
    }
    int DeletePolygons() override { return py_call(py_, "delete_polygons"); }
    int LoadPolygons() override { return py_call(py_, "load_polygons"); }
    int SetPolygonRepetitions(int repetitions) override {
        return py_call(py_, "set_polygon_repetitions", repetitions);
    }
    int RunPolygons() override { return py_call(py_, "run_polygons"); }

    // -- MM::Galvo: sequence --
    int RunSequence() override { return py_call(py_, "run_sequence"); }
    int StopSequence() override { return py_call(py_, "stop_sequence"); }

    // -- MM::Galvo: channel --
    int GetChannel(char *channelName) override {
        return py_invoke([&]() -> int {
            auto name = nb::cast<std::string>(py_.attr("get_channel")());
            CDeviceUtils::CopyLimitedString(channelName, name.c_str());
            return DEVICE_OK;
        });
    }
};

// ============================================================================
// PyBridgeGeneric
// ============================================================================

class PyBridgeGeneric : public CGenericBase<PyBridgeGeneric>,
                        private PyBridgeDeviceBase<PyBridgeGeneric> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeGeneric)
};

// Forward declarations — PyBridgeHub::DetectInstalledDevices needs these.
inline MM::Device *createBridgeDevice(nb::object py_dev, MM::DeviceType type,
                                      const std::string &name,
                                      const std::string &description = "");
class PyBridgeAdapter;

// A hub may report a peripheral as a device instance, a device class, or a
// zero-argument factory returning a device; the latter two are called on each
// load. Device objects are recognised by the bridge's initialize_bridge()
// method, so a callable without it is a factory.
inline bool isDeviceFactory(const nb::object &obj) {
    return PyType_Check(obj.ptr()) ||
           (PyCallable_Check(obj.ptr()) && !nb::hasattr(obj, "initialize_bridge"));
}

// ============================================================================
// PyBridgeHub
// ============================================================================

class PyBridgeHub : public HubBase<PyBridgeHub>, private PyBridgeDeviceBase<PyBridgeHub> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeHub)

    // The adapter that created this hub (set by PyBridgeAdapter::CreateDevice),
    // so that discovered peripherals can be made loadable through it.
    PyBridgeAdapter *adapter_ = nullptr;

  public:
    void setAdapter(PyBridgeAdapter *adapter) { adapter_ = adapter; }

    // Discover peripherals by calling Python's detect_installed_devices(),
    // which returns a list of (name, py_device_or_class, device_type) tuples.
    // Each is wrapped in a prototype bridge device registered with HubBase
    // (for getInstalledDevices()), and registered with the adapter so that
    // loadDevice(label, adapter, name) can create it, as for C++ hubs.
    int DetectInstalledDevices() override;
};

// ============================================================================
// PyBridgeSLM
// ============================================================================

class PyBridgeSLM : public CSLMBase<PyBridgeSLM>, private PyBridgeDeviceBase<PyBridgeSLM> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeSLM)

    // -- MM::SLM --
    // As in MMDevice (see GenericSLM: GetBytesPerPixel() == 4 with 3
    // components), GetBytesPerPixel() is the total number of bytes per pixel.
    // An 8-bit image with bytesPerPixel > 1 is presented as (h, w, bytesPerPixel).
    int SetImage(unsigned char *pixels) override {
        ensureSLMDimsCached();
        size_t h = cachedH_, w = cachedW_;
        size_t pixDepth = cachedBpp_;
        return py_invoke([&]() -> int {
            nb::ndarray<nb::numpy, uint8_t, nb::c_contig> arr;
            if (pixDepth == 1)
                arr = nb::ndarray<nb::numpy, uint8_t, nb::c_contig>(pixels, {h, w});
            else
                arr = nb::ndarray<nb::numpy, uint8_t, nb::c_contig>(pixels, {h, w, pixDepth});
            py_.attr("set_image")(arr);
            return DEVICE_OK;
        });
    }
    int SetImage(unsigned int *pixels) override {
        ensureSLMDimsCached();
        size_t h = cachedH_, w = cachedW_;
        return py_invoke([&]() -> int {
            auto arr = nb::ndarray<nb::numpy, uint32_t, nb::c_contig>(pixels, {h, w});
            py_.attr("set_image")(arr);
            return DEVICE_OK;
        });
    }
    int DisplayImage() override { return py_call(py_, "display_image"); }
    int SetPixelsTo(unsigned char intensity) override {
        return py_call(py_, "set_pixels_to", intensity);
    }
    int SetPixelsTo(unsigned char r, unsigned char g, unsigned char b) override {
        return py_call(py_, "set_pixels_to_rgb", r, g, b);
    }
    int SetExposure(double interval_ms) override {
        return py_call(py_, "set_exposure", interval_ms);
    }
    double GetExposure() override { return py_get<double>(py_, "get_exposure"); }
    unsigned GetWidth() override { return py_get<unsigned>(py_, "get_width"); }
    unsigned GetHeight() override { return py_get<unsigned>(py_, "get_height"); }
    unsigned GetNumberOfComponents() override {
        return py_get<unsigned>(py_, "get_number_of_components");
    }
    unsigned GetBytesPerPixel() override {
        return py_get<unsigned>(py_, "get_bytes_per_pixel");
    }
    // Cached SLM dimensions — populated once to avoid repeated Python
    // bridge crossings in SetImage / AddToSLMSequence / SendSLMSequence.
    unsigned cachedW_ = 0, cachedH_ = 0, cachedNComp_ = 0, cachedBpp_ = 0;
    bool slmDimsCached_ = false;

    void ensureSLMDimsCached() {
        if (!slmDimsCached_) {
            cachedW_ = GetWidth();
            cachedH_ = GetHeight();
            cachedNComp_ = GetNumberOfComponents();
            cachedBpp_ = GetBytesPerPixel();
            slmDimsCached_ = true;
        }
    }

    // -- MM::SLM: sequencing --
    std::vector<std::vector<unsigned char>> slmSeq8_;
    std::vector<std::vector<unsigned int>> slmSeq32_;
    bool usingSeq32_ = false;

    int IsSLMSequenceable(bool &f) const override {
        return py_invoke([&]() -> int {
            f = py_get<bool>(py_, "is_slm_sequenceable");
            return DEVICE_OK;
        });
    }
    int GetSLMSequenceMaxLength(long &nrEvents) const override {
        return py_invoke([&]() -> int {
            nrEvents = py_get<long>(py_, "get_slm_sequence_max_length");
            return DEVICE_OK;
        });
    }
    int ClearSLMSequence() override {
        slmSeq8_.clear();
        slmSeq32_.clear();
        usingSeq32_ = false;
        return DEVICE_OK;
    }
    int AddToSLMSequence(const unsigned char *const image) override {
        ensureSLMDimsCached();
        size_t nbytes = (size_t)cachedH_ * cachedW_ * cachedBpp_;
        slmSeq8_.emplace_back(image, image + nbytes);
        usingSeq32_ = false;
        return DEVICE_OK;
    }
    int AddToSLMSequence(const unsigned int *const image) override {
        ensureSLMDimsCached();
        size_t npixels = (size_t)cachedH_ * cachedW_;
        slmSeq32_.emplace_back(image, image + npixels);
        usingSeq32_ = true;
        return DEVICE_OK;
    }
    int SendSLMSequence() override {
        ensureSLMDimsCached();
        size_t h = cachedH_, w = cachedW_;
        size_t pixDepth = cachedBpp_;
        return py_invoke([&]() -> int {
            nb::list py_seq;
            if (usingSeq32_) {
                for (auto &buf : slmSeq32_) {
                    auto arr =
                        nb::ndarray<nb::numpy, uint32_t, nb::c_contig>(buf.data(), {h, w});
                    py_seq.append(arr);
                }
            } else {
                for (auto &buf : slmSeq8_) {
                    nb::ndarray<nb::numpy, uint8_t, nb::c_contig> arr;
                    if (pixDepth == 1)
                        arr = nb::ndarray<nb::numpy, uint8_t, nb::c_contig>(buf.data(), {h, w});
                    else
                        arr = nb::ndarray<nb::numpy, uint8_t, nb::c_contig>(buf.data(),
                                                                            {h, w, pixDepth});
                    py_seq.append(arr);
                }
            }
            py_.attr("load_slm_sequence")(py_seq);
            return DEVICE_OK;
        });
    }
    int StartSLMSequence() override { return py_call(py_, "start_slm_sequence"); }
    int StopSLMSequence() override { return py_call(py_, "stop_slm_sequence"); }
};

#undef PYBRIDGE_COMMON_OVERRIDES

// ============================================================================
// Helper: create the right bridge device for a given MM::DeviceType
// ============================================================================

inline MM::Device *createBridgeDevice(nb::object py_dev, MM::DeviceType type,
                                      const std::string &name, const std::string &description) {
    switch (type) {
    case MM::CameraDevice: return new PyBridgeCamera(py_dev, name, description);
    case MM::ShutterDevice: return new PyBridgeShutter(py_dev, name, description);
    case MM::StageDevice: return new PyBridgeStage(py_dev, name, description);
    case MM::XYStageDevice: return new PyBridgeXYStage(py_dev, name, description);
    case MM::StateDevice: return new PyBridgeState(py_dev, name, description);
    case MM::SLMDevice: return new PyBridgeSLM(py_dev, name, description);
    case MM::AutoFocusDevice: return new PyBridgeAutoFocus(py_dev, name, description);
    case MM::SignalIODevice: return new PyBridgeSignalIO(py_dev, name, description);
    case MM::GalvoDevice: return new PyBridgeGalvo(py_dev, name, description);
    case MM::MagnifierDevice: return new PyBridgeMagnifier(py_dev, name, description);
    case MM::SerialDevice: return new PyBridgeSerial(py_dev, name, description);
    case MM::GenericDevice: return new PyBridgeGeneric(py_dev, name, description);
    case MM::HubDevice: return new PyBridgeHub(py_dev, name, description);
    default:
        throw std::runtime_error("No Python bridge for device type " + std::to_string(type));
    }
}

// ============================================================================
// PyBridgeAdapter — implements MockDeviceAdapter for Python bridge devices.
//
// Supports two modes:
//   1. Pre-instantiated: addDevice(name, py_instance, type)
//      CreateDevice returns a bridge wrapping the existing instance.
//   2. Class-based: addDeviceClass(name, py_class, type, description)
//      CreateDevice instantiates the Python class on demand.
//
// Both modes can be mixed in the same adapter, and all devices from
// one adapter share the same LoadedDeviceAdapter mutex.
// ============================================================================

class PyBridgeAdapter : public MockDeviceAdapter {
    struct DeviceEntry {
        std::string name;
        std::string description;
        nb::object py_obj; // an instance, or a class / factory
        MM::DeviceType type;
        bool is_factory; // true = call py_obj() to instantiate
    };

    std::vector<DeviceEntry> devices_;
    bool loaded_ = false;
    // Hubs created by this adapter (and not yet deleted): their peripherals
    // are registered on demand, see CreateDevice.
    std::vector<PyBridgeHub *> hubs_;

  public:
    PyBridgeAdapter() = default;

    PyBridgeAdapter(PyBridgeAdapter &&) = delete;
    PyBridgeAdapter &operator=(PyBridgeAdapter &&) = delete;
    PyBridgeAdapter(const PyBridgeAdapter &) = delete;
    PyBridgeAdapter &operator=(const PyBridgeAdapter &) = delete;

    // Copy of the registered entries, for handing to CMMCore (which takes
    // ownership of the copy). The Python-side DeviceAdapter stays intact, so
    // it can be registered with several cores, and a failed registration
    // loses nothing.
    std::unique_ptr<PyBridgeAdapter> clone() const {
        nb::gil_scoped_acquire gil;
        auto copy = std::make_unique<PyBridgeAdapter>();
        copy->devices_ = devices_;
        return copy;
    }

    ~PyBridgeAdapter() {
        try {
            nb::gil_scoped_acquire gil;
            devices_.clear();
        } catch (...) {
        }
    }

    // Register a pre-instantiated Python device (for loadPyDevice).
    void addDevice(const std::string &name, nb::object py_dev, MM::DeviceType type) {
        if (loaded_)
            throw std::runtime_error("Cannot add devices after adapter has been loaded");
        devices_.push_back({name, "Python bridge device", std::move(py_dev), type, false});
    }

    // Register a Python device class (for loadPyDeviceAdapter).
    // CreateDevice will call py_cls() to instantiate.
    void addDeviceClass(const std::string &name, nb::object py_cls, MM::DeviceType type,
                        const std::string &description) {
        if (loaded_)
            throw std::runtime_error("Cannot add devices after adapter has been loaded");
        devices_.push_back({name, description, std::move(py_cls), type, true});
    }

    // Mark as loaded — called by registerAndStoreBridgeAdapter after
    // the adapter has been registered with CMMCore.
    void markLoaded() { loaded_ = true; }

    void InitializeModuleData(RegisterDeviceFunc registerDevice) override {
        for (auto &d : devices_) {
            registerDevice(d.name.c_str(), d.type, d.description.c_str());
        }
    }

    // Register a peripheral reported by a hub's detect_installed_devices(),
    // so that CreateDevice(name) can create it. `py_obj` is a device instance
    // (used as-is when loaded) or a device class / factory (called without
    // arguments when loaded).
    void registerDiscovered(const std::string &name, nb::object py_obj, MM::DeviceType type,
                            const std::string &description) {
        bool is_factory = isDeviceFactory(py_obj);
        for (auto &d : devices_) {
            if (d.name == name) {
                d = {name, description, std::move(py_obj), type, is_factory};
                return;
            }
        }
        devices_.push_back({name, description, std::move(py_obj), type, is_factory});
    }

    DeviceEntry *findEntry(const char *name) {
        for (auto &d : devices_)
            if (d.name == name)
                return &d;
        return nullptr;
    }

    MM::Device *CreateDevice(const char *name) override {
        nb::gil_scoped_acquire gil;
        DeviceEntry *entry = findEntry(name);
        if (!entry) {
            // A C++ adapter registers all of its device names up front, so a
            // hub's peripherals can be loaded by name without first calling
            // getInstalledDevices() (which is what loadSystemConfiguration
            // does). Ask the hubs of this adapter to detect their peripherals.
            for (auto *hub : hubs_) {
                hub->DetectInstalledDevices();
                if ((entry = findEntry(name)))
                    break;
            }
        }
        if (!entry)
            return nullptr;
        auto &d = *entry;
        MM::Device *dev = nullptr;
        try {
            nb::object py_dev = d.is_factory ? d.py_obj() : d.py_obj;
            dev = createBridgeDevice(py_dev, d.type, d.name, d.description);
        } catch (nb::python_error &e) {
            // Surface the Python error instead of a bare "failed to
            // instantiate device" from CMMCore.
            std::string msg = e.what();
            e.restore();
            PyErr_Clear();
            throw CMMError("Failed to instantiate Python device \"" + d.name + "\": " + msg);
        } catch (const std::exception &e) {
            throw CMMError("Failed to instantiate Python device \"" + d.name +
                           "\": " + e.what());
        }
        if (auto *hub = dynamic_cast<PyBridgeHub *>(dev)) {
            hub->setAdapter(this);
            hubs_.push_back(hub);
        }
        return dev;
    }

    void DeleteDevice(MM::Device *device) override {
        hubs_.erase(std::remove(hubs_.begin(), hubs_.end(), device), hubs_.end());
        delete device;
    }
};

inline int PyBridgeHub::DetectInstalledDevices() {
    ClearInstalledDevices();
    return py_invoke([&]() -> int {
        nb::object peripherals = py_.attr("detect_installed_devices")();
        for (auto item : peripherals) {
            auto tup = nb::cast<nb::tuple>(item);
            auto name = nb::cast<std::string>(tup[0]);
            nb::object py_obj = tup[1];
            auto type = nb::cast<MM::DeviceType>(tup[2]);
            // The prototype needs an instance; a class / factory is called for it.
            nb::object py_dev = isDeviceFactory(py_obj) ? py_obj() : py_obj;
            // Extract description from the Python object's class docstring.
            std::string desc;
            nb::object py_type =
                nb::borrow(reinterpret_cast<PyObject *>(Py_TYPE(py_dev.ptr())));
            nb::object doc = py_type.attr("__doc__");
            if (!doc.is_none())
                desc = nb::cast<std::string>(nb::str(doc));
            MM::Device *pDev = createBridgeDevice(py_dev, type, name, desc);
            if (pDev)
                AddInstalledDevice(pDev);
            if (adapter_)
                adapter_->registerDiscovered(name, py_obj, type, desc);
        }
        return DEVICE_OK;
    });
}
