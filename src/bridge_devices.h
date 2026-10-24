// Bridge device classes that forward MM::Device calls to Python objects.
// These enable Python-implemented devices to be registered as real devices
// in CMMCore's device registry via the MockDeviceAdapter infrastructure.

#pragma once

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "DeviceBase.h"
#include "Error.h"
#include "ImageMetadata.h"
#include "MMDevice.h"
#include "MockDeviceAdapter.h"

#include <atomic>
#include <memory>
#include <string>
#include <vector>

namespace nb = nanobind;

// ============================================================================
// Helpers — factor out GIL + cast boilerplate
// ============================================================================

// Catch nb::python_error from Python calls and rethrow as CMMError with the
// Python traceback preserved. CMMError is what CMMCore's own device layer
// throws, so CMMCore passes it through (or tolerates it) with the message
// intact; any other exception type is reported as an "unknown system
// exception" or, in noexcept paths, aborts the process.

template <typename T> T py_get(const nb::object &py, const char *attr) {
    nb::gil_scoped_acquire gil;
    try {
        return nb::cast<T>(py.attr(attr)());
    } catch (nb::python_error &e) {
        std::string msg = e.what();
        e.restore();
        PyErr_Clear();
        throw CMMError(msg);
    }
}

template <typename... Args>
void py_set(const nb::object &py, const char *attr, Args &&...args) {
    nb::gil_scoped_acquire gil;
    try {
        py.attr(attr)(std::forward<Args>(args)...);
    } catch (nb::python_error &e) {
        std::string msg = e.what();
        e.restore();
        PyErr_Clear();
        throw CMMError(msg);
    }
}

template <typename... Args>
int py_call(const nb::object &py, const char *attr, Args &&...args) {
    nb::gil_scoped_acquire gil;
    try {
        py.attr(attr)(std::forward<Args>(args)...);
    } catch (nb::python_error &e) {
        std::string msg = e.what();
        e.restore();
        PyErr_Clear();
        throw CMMError(msg);
    }
    return DEVICE_OK;
}

// GIL-acquiring wrapper for inline Python calls that aren't simple
// get/set/call. Catches nb::python_error and rethrows as std::runtime_error.
template <typename F> auto py_invoke(F &&fn) -> decltype(fn()) {
    nb::gil_scoped_acquire gil;
    try {
        return fn();
    } catch (nb::python_error &e) {
        std::string msg = e.what();
        e.restore();
        PyErr_Clear();
        throw CMMError(msg);
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

// Build an ActionLambda that forwards property actions to Python callables.
// Handles get/set and optionally sequencing (IsSequenceable, AfterLoadSequence,
// StartSequence, StopSequence).
// Returns the shared seq_max_length pointer (may be null if not sequenceable)
// so createPropertyFactory can pass it to PropertyHandle.
inline std::pair<std::unique_ptr<MM::ActionFunctor>, std::shared_ptr<std::atomic<long>>>
makePropertyAction(nb::object getter, nb::object setter, long seqMaxLength,
                   nb::object seqLoader, nb::object seqStarter, nb::object seqStopper) {
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
        [cbs](MM::PropertyBase *pProp, MM::ActionType eAct) -> int {
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
                std::string msg = e.what();
                e.restore();
                PyErr_Clear();
                throw CMMError(msg);
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
                                 std::shared_ptr<std::atomic<bool>> alive) {
    // Type-erased CreateProperty
    auto doCreate = [](MM::Device *d, const char *name, const char *val, MM::PropertyType t,
                       bool ro, MM::ActionFunctor *act, bool preInit) -> int {
        return static_cast<TDevice *>(d)->CreateProperty(name, val, t, ro, act, preInit);
    };

    return nb::cpp_function(
        [dev, doCreate, canCreate, alive](
            const std::string &name, const std::string &defaultValue, int mmType, bool readOnly,
            nb::object getter, nb::object setter, bool preInit, nb::object limits,
            nb::object allowedValues, long sequenceMaxLength, nb::object sequenceLoader,
            nb::object sequenceStarter, nb::object sequenceStopper) -> PropertyHandle {
            if (!*canCreate)
                throw std::runtime_error("create_property() can only be called during "
                                         "initialize()");
            if constexpr (std::is_base_of_v<CStateDeviceBase<TDevice>, TDevice>) {
                if (name == MM::g_Keyword_Label)
                    throw std::runtime_error(
                        "State devices may not create a 'Label' property: it is provided by "
                        "the bridge. Use notify.set_position_label() to define labels.");
            }

            auto [action, seqMaxPtr] =
                makePropertyAction(getter, setter, sequenceMaxLength, sequenceLoader,
                                   sequenceStarter, sequenceStopper);

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
                                  MM::Core *coreCallback) {
    auto canCreate = std::make_shared<std::atomic<bool>>(true);
    nb::object factory = createPropertyFactory(dev, canCreate, alive);

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

    int initializeCommon(TDevice *dev, MM::Core *coreCallback) {
        nb::gil_scoped_acquire gil;
        return initializeWithPropertyFactory(dev, py_, alive_, coreCallback);
    }

    // Per-device-type hooks around the Python initialize_bridge() call.
    // Bridge classes hide these to add C++-side setup (see PyBridgeState).
    int beforePyInitialize() { return DEVICE_OK; }
    int afterPyInitialize() { return DEVICE_OK; }

    int shutdownCommon() {
        *alive_ = false;
        return py_call(py_, "shutdown");
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
                                        std::move(description)) {}                             \
    int Initialize() override {                                                                \
        int ret = this->beforePyInitialize();                                                  \
        if (ret != DEVICE_OK)                                                                  \
            return ret;                                                                        \
        ret = this->initializeCommon(this, this->GetCoreCallback());                           \
        if (ret != DEVICE_OK)                                                                  \
            return ret;                                                                        \
        return this->afterPyInitialize();                                                      \
    }                                                                                          \
    /* CMMCore aborts the process if Shutdown() fails while unloading in a destructor, */      \
    /* so log the Python error instead of reporting it. */                                     \
    int Shutdown() override {                                                                  \
        try {                                                                                  \
            return this->shutdownCommon();                                                     \
        } catch (const std::exception &e) {                                                    \
            this->LogMessage(std::string("shutdown() failed: ") + e.what());                   \
            return DEVICE_OK;                                                                  \
        }                                                                                      \
    }                                                                                          \
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

    // Keep the array CMMCore will read from alive until the next call. A
    // non-contiguous array is copied here (ascontiguousarray returns the array
    // itself when no copy is needed), so the pointer never refers to a temporary.
    const unsigned char *holdImageArray(nb::object arr) {
        img_arr_ = nb::module_::import_("numpy").attr("ascontiguousarray")(arr);
        auto nd = nb::cast<nb::ndarray<nb::c_contig, nb::ro, nb::device::cpu>>(img_arr_);
        // CMMCore reads exactly w*h*bpp bytes from the returned pointer.
        size_t expected = (size_t)GetImageWidth() * GetImageHeight() * GetImageBytesPerPixel();
        if (nd.nbytes() != expected)
            throw CMMError("get_image_buffer() returned " + std::to_string(nd.nbytes()) +
                           " bytes; expected " + std::to_string(expected) +
                           " (width * height * bytes_per_pixel)");
        return static_cast<const unsigned char *>(nd.data());
    }

    const unsigned char *GetImageBuffer() override {
        return py_invoke([&] { return holdImageArray(py_.attr("get_image_buffer")()); });
    }

    const unsigned char *GetImageBuffer(unsigned channelNr) override {
        return py_invoke(
            [&] { return holdImageArray(py_.attr("get_image_buffer")(channelNr)); });
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
        f = py_get<bool>(py_, "is_exposure_sequenceable");
        return DEVICE_OK;
    }
    int GetExposureSequenceMaxLength(long &nrEvents) const override {
        nrEvents = py_get<long>(py_, "get_exposure_sequence_max_length");
        return DEVICE_OK;
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

        // PrepareForAcq opened the auto-shutter; close it again if Python fails.
        try {
            // Cache image dimensions once for the whole sequence. These shouldn't
            // change during a running acquisition and querying them on every frame
            // crosses the Python bridge 4 times per frame.
            unsigned w = GetImageWidth();
            unsigned h = GetImageHeight();
            unsigned bpp = GetImageBytesPerPixel();
            unsigned nComp = GetNumberOfComponents();
            return startPySequence(numImages, interval_ms, w, h, bpp, nComp);
        } catch (...) {
            GetCoreCallback()->AcqFinished(this, DEVICE_ERR);
            throw;
        }
    }

    int startPySequence(long numImages, double interval_ms, unsigned w, unsigned h,
                        unsigned bpp, unsigned nComp) {
        return py_invoke([&]() -> int {
            // Create an insert_image callable that pushes a frame into
            // CMMCore's circular buffer. Python calls this per frame.
            auto *self = this;
            // insert_image returns False on buffer overflow so Python
            // can stop acquisition when stopOnOverflow is set.
            nb::object inserter = nb::cpp_function(
                [self, alive = alive_, w, h, bpp, nComp](nb::object arr,
                                                         nb::object metadata) -> bool {
                    // The acquisition thread may outlive the device.
                    if (!*alive)
                        throw std::runtime_error("Device has been unloaded");
                    auto nd = nb::cast<nb::ndarray<nb::c_contig, nb::ro, nb::device::cpu>>(arr);

                    // Build serialized metadata in MMCore's format
                    Metadata md;
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

            py_.attr("start_sequence_acquisition")(numImages, interval_ms, inserter);
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
        open = py_get<bool>(py_, "get_open");
        return DEVICE_OK;
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
        pos = py_get<double>(py_, "get_position_um");
        return DEVICE_OK;
    }
    int SetRelativePositionUm(double d) override {
        return py_call(py_, "set_relative_position_um", d);
    }
    int SetPositionSteps(long steps) override {
        return py_call(py_, "set_position_steps", steps);
    }
    int GetPositionSteps(long &steps) override {
        steps = py_get<long>(py_, "get_position_steps");
        return DEVICE_OK;
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
        direction = static_cast<MM::FocusDirection>(py_get<int>(py_, "get_focus_direction"));
        return DEVICE_OK;
    }
    bool IsContinuousFocusDrive() const override {
        return py_get<bool>(py_, "is_continuous_focus_drive");
    }

    // -- MM::Stage: sequencing --
    std::vector<double> stageSeq_;

    int IsStageSequenceable(bool &f) const override {
        f = py_get<bool>(py_, "is_stage_sequenceable");
        return DEVICE_OK;
    }
    int GetStageSequenceMaxLength(long &nrEvents) const override {
        nrEvents = py_get<long>(py_, "get_stage_sequence_max_length");
        return DEVICE_OK;
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

    int beforePyInitialize() {
        nb::gil_scoped_acquire gil;
        usesSteps_ = !nb::hasattr(py_, "set_position_um");
        hasSetOrigin_ = nb::hasattr(py_, "set_origin");
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
    int SetXOrigin() override { return py_call(py_, "set_x_origin"); }
    int SetYOrigin() override { return py_call(py_, "set_y_origin"); }

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
        f = py_get<bool>(py_, "is_xy_stage_sequenceable");
        return DEVICE_OK;
    }
    int GetXYStageSequenceMaxLength(long &nrEvents) const override {
        nrEvents = py_get<long>(py_, "get_xy_stage_sequence_max_length");
        return DEVICE_OK;
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
        state = py_get<bool>(py_, "get_continuous_focusing");
        return DEVICE_OK;
    }
    bool IsContinuousFocusLocked() override {
        return py_get<bool>(py_, "is_continuous_focus_locked");
    }
    int FullFocus() override { return py_call(py_, "full_focus"); }
    int IncrementalFocus() override { return py_call(py_, "incremental_focus"); }
    int GetLastFocusScore(double &score) override {
        score = py_get<double>(py_, "get_last_focus_score");
        return DEVICE_OK;
    }
    int GetCurrentFocusScore(double &score) override {
        score = py_get<double>(py_, "get_current_focus_score");
        return DEVICE_OK;
    }
    int GetOffset(double &offset) override {
        offset = py_get<double>(py_, "get_offset");
        return DEVICE_OK;
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
        open = py_get<bool>(py_, "get_gate_open");
        return DEVICE_OK;
    }
    int SetSignal(double volts) override { return py_call(py_, "set_signal", volts); }
    int GetSignal(double &volts) override {
        volts = py_get<double>(py_, "get_signal");
        return DEVICE_OK;
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
        f = py_get<bool>(py_, "is_da_sequenceable");
        return DEVICE_OK;
    }
    int GetDASequenceMaxLength(long &nrEvents) const override {
        nrEvents = py_get<long>(py_, "get_da_sequence_max_length");
        return DEVICE_OK;
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

// ============================================================================
// PyBridgeHub
// ============================================================================

// Stand-in for a peripheral reported by a Python hub. CMMCore only reads its
// name and description (getInstalledDevices); as with C++ hubs, a peripheral
// is loaded as a fresh device from the adapter, never from discovery.
class InstalledPeripheral : public CGenericBase<InstalledPeripheral> {
    std::string name_;
    std::string description_;

  public:
    InstalledPeripheral(std::string name, std::string description)
        : name_(std::move(name)), description_(std::move(description)) {}
    int Initialize() override { return DEVICE_OK; }
    int Shutdown() override { return DEVICE_OK; }
    bool Busy() override { return false; }
    void GetName(char *name) const override {
        CDeviceUtils::CopyLimitedString(name, name_.c_str());
    }
    void GetDescription(char *desc) const override {
        CDeviceUtils::CopyLimitedString(desc, description_.c_str());
    }
};

class PyBridgeHub : public HubBase<PyBridgeHub>, private PyBridgeDeviceBase<PyBridgeHub> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeHub)

    // Discover peripherals by calling Python's detect_installed_devices(),
    // which returns a list of (name, description) tuples.
    int DetectInstalledDevices() override {
        ClearInstalledDevices();
        return py_invoke([&]() -> int {
            nb::object peripherals = py_.attr("detect_installed_devices")();
            for (auto item : peripherals) {
                auto tup = nb::cast<nb::tuple>(item);
                AddInstalledDevice(new InstalledPeripheral(nb::cast<std::string>(tup[0]),
                                                           nb::cast<std::string>(tup[1])));
            }
            return DEVICE_OK;
        });
    }
};

// ============================================================================
// PyBridgeSLM
// ============================================================================

class PyBridgeSLM : public CSLMBase<PyBridgeSLM>, private PyBridgeDeviceBase<PyBridgeSLM> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeSLM)

    // -- MM::SLM --
    int SetImage(unsigned char *pixels) override {
        ensureSLMDimsCached();
        size_t h = cachedH_, w = cachedW_;
        size_t pixDepth = cachedBpp_; // total bytes per pixel, across all components
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
        f = py_get<bool>(py_, "is_slm_sequenceable");
        return DEVICE_OK;
    }
    int GetSLMSequenceMaxLength(long &nrEvents) const override {
        nrEvents = py_get<long>(py_, "get_slm_sequence_max_length");
        return DEVICE_OK;
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
        nb::object py_obj; // either an instance or a class
        MM::DeviceType type;
        bool is_class; // true = call py_obj() to instantiate
    };

    std::vector<DeviceEntry> devices_;
    bool loaded_ = false;

  public:
    PyBridgeAdapter() = default;

    // Move constructor: leaves the source marked as loaded so it
    // rejects further modifications.
    PyBridgeAdapter(PyBridgeAdapter &&other) noexcept
        : devices_(std::move(other.devices_)), loaded_(other.loaded_) {
        other.loaded_ = true;
    }
    PyBridgeAdapter &operator=(PyBridgeAdapter &&) = delete;
    PyBridgeAdapter(const PyBridgeAdapter &) = delete;
    PyBridgeAdapter &operator=(const PyBridgeAdapter &) = delete;

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

    MM::Device *CreateDevice(const char *name) override {
        nb::gil_scoped_acquire gil;
        for (auto it = devices_.begin(); it != devices_.end(); ++it) {
            if (it->name == name) {
                MM::Device *dev;
                try {
                    nb::object py_dev = it->is_class ? it->py_obj() : it->py_obj;
                    dev = createBridgeDevice(py_dev, it->type, it->name, it->description);
                } catch (nb::python_error &e) {
                    std::string msg = e.what();
                    e.restore();
                    PyErr_Clear();
                    throw CMMError("Failed to create device \"" + std::string(name) +
                                   "\": " + msg);
                } catch (...) {
                    return nullptr;
                }
                // An instance backs exactly one device; don't keep it alive here.
                if (!it->is_class)
                    devices_.erase(it);
                return dev;
            }
        }
        // Like a C++ adapter, this one can only create devices it knows. A
        // hub's peripherals are loadable by name only if their classes are
        // registered on the same DeviceAdapter.
        throw CMMError("No device named \"" + std::string(name) +
                       "\" in this Python device adapter. To load a hub's peripherals "
                       "by name, register their classes with "
                       "DeviceAdapter.add_device_class().");
    }

    void DeleteDevice(MM::Device *device) override { delete device; }
};
