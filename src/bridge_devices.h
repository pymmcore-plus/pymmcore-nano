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

#include <atomic>
#include <memory>
#include <string>
#include <vector>

namespace nb = nanobind;

// ============================================================================
// Helpers — factor out GIL + cast boilerplate
// ============================================================================

// Catch nb::python_error from Python calls and rethrow as std::runtime_error
// with the Python traceback preserved. CMMCore's DeviceInstance layer catches
// std::exception, logs via LOG_ERROR, and wraps in CMMError — so the Python
// error info surfaces through MM's existing error pipeline.

template <typename T> T py_get(const nb::object &py, const char *attr) {
    nb::gil_scoped_acquire gil;
    try {
        return nb::cast<T>(py.attr(attr)());
    } catch (nb::python_error &e) {
        std::string msg = e.what();
        e.restore();
        PyErr_Clear();
        throw std::runtime_error(msg);
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
        throw std::runtime_error(msg);
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
        throw std::runtime_error(msg);
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
        throw std::runtime_error(msg);
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
    PropertyHandle(TDevice *dev, std::string name, std::shared_ptr<std::atomic<bool>> alive)
        : dev_(dev), name_(std::move(name)), alive_(std::move(alive)) {
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

    void checkAlive() const {
        if (!alive_ || !*alive_)
            throw std::runtime_error("Device has been unloaded");
    }

  public:
    DeviceCallbacks() = delete;

    DeviceCallbacks(MM::Device *dev, MM::Core *cb, std::shared_ptr<std::atomic<bool>> alive)
        : dev_(dev), cb_(cb), alive_(std::move(alive)) {}

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
};

// ============================================================================
// createPropertyFactory — builds the create_property callable that is passed
// to Python's initialize(create_property, notify).
//
// Each call to create_property registers an MM property on the C++ device
// with an ActionLambda for get/set, and returns a PropertyHandle for
// dynamic constraint updates.
// ============================================================================

// GIL-safe destructor for getter/setter captured in ActionLambda.
// CDeviceBase may destroy the ActionLambda without the GIL held.
struct PyCallbacks {
    nb::object getter;
    nb::object setter;
    ~PyCallbacks() {
        try {
            nb::gil_scoped_acquire gil;
            getter.reset();
            setter.reset();
        } catch (...) {
        }
    }
};

// Build an ActionLambda that forwards BeforeGet/AfterSet to Python callables.
inline std::unique_ptr<MM::ActionFunctor> makePropertyAction(nb::object getter,
                                                             nb::object setter) {
    if (getter.is_none() && setter.is_none())
        return nullptr;

    auto cbs = std::make_shared<PyCallbacks>(PyCallbacks{getter, setter});
    return std::make_unique<MM::ActionLambda>(
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
                }
            } catch (nb::python_error &e) {
                std::string msg = e.what();
                e.restore();
                PyErr_Clear();
                throw std::runtime_error(msg);
            }
            return DEVICE_OK;
        });
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
        [dev, doCreate, canCreate,
         alive](const std::string &name, const std::string &defaultValue, int mmType,
                bool readOnly, nb::object getter, nb::object setter, bool preInit,
                nb::object limits, nb::object allowedValues) -> PropertyHandle {
            if (!*canCreate)
                throw std::runtime_error("create_property() can only be called during "
                                         "initialize()");

            auto action = makePropertyAction(getter, setter);

            int ret = doCreate(dev, name.c_str(), defaultValue.c_str(),
                               static_cast<MM::PropertyType>(mmType), readOnly, action.get(),
                               preInit);
            if (ret == DEVICE_OK)
                action.release();

            PropertyHandle handle(dev, name, alive);

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
        nb::arg("allowed_values") = nb::none());
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
    nb::object py_notify = nb::cast(notify, nb::rv_policy::take_ownership);

    try {
        py.attr("initialize")(factory, py_notify);
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
    std::shared_ptr<std::atomic<bool>> alive_ = std::make_shared<std::atomic<bool>>(true);

    PyBridgeDeviceBase(nb::object py_dev, std::string name)
        : py_(std::move(py_dev)), deviceName_(std::move(name)) {}

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

    int shutdownCommon() {
        *alive_ = false;
        return py_call(py_, "shutdown");
    }

    bool busyCommon() { return py_get<bool>(py_, "busy"); }

    void getNameCommon(char *name) const {
        CDeviceUtils::CopyLimitedString(name, deviceName_.c_str());
    }
};

#define PYBRIDGE_COMMON_OVERRIDES(ClassName)                                                   \
  public:                                                                                      \
    ClassName(nb::object py_dev, std::string name)                                             \
        : PyBridgeDeviceBase<ClassName>(std::move(py_dev), std::move(name)) {}                 \
    int Initialize() override {                                                                \
        return this->initializeCommon(this, this->GetCoreCallback());                          \
    }                                                                                          \
    int Shutdown() override { return this->shutdownCommon(); }                                 \
    bool Busy() override { return this->busyCommon(); }                                        \
    void GetName(char *name) const override { this->getNameCommon(name); }

// ============================================================================
// PyBridgeCamera
// ============================================================================

class PyBridgeCamera : public CCameraBase<PyBridgeCamera>,
                       private PyBridgeDeviceBase<PyBridgeCamera> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeCamera)

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

    const unsigned char *GetImageBuffer() override {
        return py_invoke([&]() -> const unsigned char * {
            // Zero-copy: store the Python array to prevent GC and return its
            // data pointer directly. The c_contig constraint will trigger an
            // implicit copy only if the array is non-contiguous (e.g. a slice).
            img_arr_ = py_.attr("get_image_buffer")();
            auto nd = nb::cast<nb::ndarray<nb::c_contig, nb::ro, nb::device::cpu>>(img_arr_);
            return static_cast<const unsigned char *>(nd.data());
        });
    }

    const unsigned char *GetImageBuffer(unsigned channelNr) override {
        return py_invoke([&]() -> const unsigned char * {
            img_arr_ = py_.attr("get_image_buffer")(channelNr);
            auto nd = nb::cast<nb::ndarray<nb::c_contig, nb::ro, nb::device::cpu>>(img_arr_);
            return static_cast<const unsigned char *>(nd.data());
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

    // -- MM::Camera: sequence acquisition --
    int IsExposureSequenceable(bool &f) const override {
        f = py_get<bool>(py_, "is_exposure_sequenceable");
        return DEVICE_OK;
    }

    bool IsCapturing() override { return py_get<bool>(py_, "is_capturing"); }

    int StartSequenceAcquisition(long numImages, double interval_ms,
                                 bool stopOnOverflow) override {
        int ret = GetCoreCallback()->PrepareForAcq(this);
        if (ret != DEVICE_OK)
            return ret;

        return py_invoke([&]() -> int {
            // Create an insert_image callable that pushes a frame into
            // CMMCore's circular buffer. Python calls this per frame.
            auto *self = this;
            nb::object inserter = nb::cpp_function(
                [self](nb::object arr, nb::object metadata) {
                    auto nd = nb::cast<nb::ndarray<nb::c_contig, nb::ro, nb::device::cpu>>(arr);
                    unsigned w = self->GetImageWidth();
                    unsigned h = self->GetImageHeight();
                    unsigned bpp = self->GetImageBytesPerPixel();
                    unsigned nComp = self->GetNumberOfComponents();

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

                    {
                        nb::gil_scoped_release release;
                        self->GetCoreCallback()->InsertImage(
                            self, static_cast<const unsigned char *>(nd.data()), w, h, bpp,
                            nComp, mdStr.c_str());
                    }
                },
                nb::arg("image"), nb::arg("metadata") = nb::none());

            py_.attr("start_sequence_acquisition")(numImages, interval_ms, stopOnOverflow,
                                                   inserter);
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
    int IsStageSequenceable(bool &f) const override {
        f = py_get<bool>(py_, "is_stage_sequenceable");
        return DEVICE_OK;
    }
};

// ============================================================================
// PyBridgeXYStage
// ============================================================================

class PyBridgeXYStage : public CXYStageBase<PyBridgeXYStage>,
                        private PyBridgeDeviceBase<PyBridgeXYStage> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeXYStage)

    // -- MM::XYStage: position (um) --
    int SetPositionUm(double x, double y) override {
        return py_call(py_, "set_position_um", x, y);
    }
    int GetPositionUm(double &x, double &y) override {
        return py_invoke([&]() -> int {
            auto pos = py_.attr("get_position_um")();
            x = nb::cast<double>(pos[nb::int_(0)]);
            y = nb::cast<double>(pos[nb::int_(1)]);
            return DEVICE_OK;
        });
    }
    int SetRelativePositionUm(double dx, double dy) override {
        return py_call(py_, "set_relative_position_um", dx, dy);
    }
    int SetAdapterOriginUm(double x, double y) override {
        return py_call(py_, "set_adapter_origin_um", x, y);
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
    int SetOrigin() override { return py_call(py_, "set_origin"); }
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
    int IsXYStageSequenceable(bool &f) const override {
        f = py_get<bool>(py_, "is_xy_stage_sequenceable");
        return DEVICE_OK;
    }
};

// ============================================================================
// PyBridgeState
// ============================================================================

class PyBridgeState : public CStateDeviceBase<PyBridgeState>,
                      private PyBridgeDeviceBase<PyBridgeState> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeState)

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
// PyBridgeGeneric
// ============================================================================

class PyBridgeGeneric : public CGenericBase<PyBridgeGeneric>,
                        private PyBridgeDeviceBase<PyBridgeGeneric> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeGeneric)
};

// ============================================================================
// PyBridgeHub
// ============================================================================

class PyBridgeHub : public HubBase<PyBridgeHub>, private PyBridgeDeviceBase<PyBridgeHub> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeHub)

    // HubBase provides defaults for DetectInstalledDevices,
    // GetNumberOfInstalledDevices, GetInstalledDevice, ClearInstalledDevices.
    // Override DetectInstalledDevices if the Python device supports it.
    int DetectInstalledDevices() override { return py_call(py_, "detect_installed_devices"); }
};

// ============================================================================
// PyBridgeSLM
// ============================================================================

class PyBridgeSLM : public CSLMBase<PyBridgeSLM>, private PyBridgeDeviceBase<PyBridgeSLM> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeSLM)

    // -- MM::SLM --
    int SetImage(unsigned char *pixels) override {
        return py_invoke([&]() -> int {
            size_t nbytes = static_cast<size_t>(GetWidth()) * GetHeight() * GetBytesPerPixel();
            auto arr = nb::ndarray<uint8_t, nb::c_contig>(pixels, {nbytes});
            py_.attr("set_image")(arr);
            return DEVICE_OK;
        });
    }
    int SetImage(unsigned int *pixels) override {
        return py_invoke([&]() -> int {
            size_t n = static_cast<size_t>(GetWidth()) * GetHeight();
            auto arr = nb::ndarray<uint32_t, nb::c_contig>(pixels, {n});
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
    int IsSLMSequenceable(bool &f) const override {
        f = false;
        return DEVICE_OK;
    }
};

#undef PYBRIDGE_COMMON_OVERRIDES

// ============================================================================
// Helper: create the right bridge device for a given MM::DeviceType
// ============================================================================

inline MM::Device *createBridgeDevice(nb::object py_dev, MM::DeviceType type,
                                      const std::string &name) {
    switch (type) {
    case MM::CameraDevice: return new PyBridgeCamera(py_dev, name);
    case MM::ShutterDevice: return new PyBridgeShutter(py_dev, name);
    case MM::StageDevice: return new PyBridgeStage(py_dev, name);
    case MM::XYStageDevice: return new PyBridgeXYStage(py_dev, name);
    case MM::StateDevice: return new PyBridgeState(py_dev, name);
    case MM::SLMDevice: return new PyBridgeSLM(py_dev, name);
    case MM::AutoFocusDevice: return new PyBridgeAutoFocus(py_dev, name);
    case MM::GenericDevice: return new PyBridgeGeneric(py_dev, name);
    case MM::HubDevice: return new PyBridgeHub(py_dev, name);
    default: return nullptr;
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
        for (auto &d : devices_) {
            if (d.name == name) {
                try {
                    nb::object py_dev = d.is_class ? d.py_obj() : d.py_obj;
                    return createBridgeDevice(py_dev, d.type, d.name);
                } catch (nb::python_error &e) {
                    e.restore();
                    PyErr_Clear();
                    return nullptr;
                } catch (...) {
                    return nullptr;
                }
            }
        }
        return nullptr;
    }

    void DeleteDevice(MM::Device *device) override { delete device; }
};
