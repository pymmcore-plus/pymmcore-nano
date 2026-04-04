// Bridge device classes that forward MM::Device calls to Python objects.
// These enable Python-implemented devices to be registered as real devices
// in CMMCore's device registry via the MockDeviceAdapter infrastructure.

#pragma once

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "DeviceBase.h"
#include "MMDevice.h"
#include "MockDeviceAdapter.h"

#include <atomic>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

namespace nb = nanobind;

// ============================================================================
// Helpers — factor out GIL + cast boilerplate
// ============================================================================

template <typename T> T py_get(const nb::object &py, const char *attr) {
    nb::gil_scoped_acquire gil;
    return nb::cast<T>(py.attr(attr)());
}

template <typename... Args>
void py_set(const nb::object &py, const char *attr, Args &&...args) {
    nb::gil_scoped_acquire gil;
    py.attr(attr)(std::forward<Args>(args)...);
}

template <typename... Args>
int py_call(const nb::object &py, const char *attr, Args &&...args) {
    nb::gil_scoped_acquire gil;
    py.attr(attr)(std::forward<Args>(args)...);
    return DEVICE_OK;
}

// ============================================================================
// PropertyHandle — returned by create_property(), allows dynamic updates
// to a single property's limits and allowed values. Valid for the device's
// entire lifetime (the dev_ pointer lives as long as CMMCore owns the device).
// ============================================================================

class PropertyHandle {
    MM::Device *dev_ = nullptr;
    std::string name_;

    struct Vtable {
        int (*setPropertyLimits)(MM::Device *, const char *, double, double);
        int (*setAllowedValues)(MM::Device *, const char *, std::vector<std::string> &);
    };
    Vtable vt_{};

  public:
    PropertyHandle() = delete;

    template <typename TDevice>
    PropertyHandle(TDevice *dev, std::string name) : dev_(dev), name_(std::move(name)) {
        vt_.setPropertyLimits = [](MM::Device *d, const char *n, double lo, double hi) -> int {
            return static_cast<TDevice *>(d)->SetPropertyLimits(n, lo, hi);
        };
        vt_.setAllowedValues = [](MM::Device *d, const char *n,
                                  std::vector<std::string> &vals) -> int {
            return static_cast<TDevice *>(d)->SetAllowedValues(n, vals);
        };
    }

    void setLimits(double lo, double hi) { vt_.setPropertyLimits(dev_, name_.c_str(), lo, hi); }

    void setAllowedValues(std::vector<std::string> values) {
        vt_.setAllowedValues(dev_, name_.c_str(), values);
    }
};

// ============================================================================
// createPropertyFactory — builds the create_property callable that is passed
// to Python's initialize(create_property).
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
            if (eAct == MM::BeforeGet && !cbs->getter.is_none()) {
                auto val = cbs->getter();
                pProp->Set(nb::cast<std::string>(nb::str(val)).c_str());
            } else if (eAct == MM::AfterSet && !cbs->setter.is_none()) {
                std::string val;
                pProp->Get(val);
                cbs->setter(nb::str(val.c_str()));
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
nb::object createPropertyFactory(TDevice *dev, std::shared_ptr<std::atomic<bool>> canCreate) {
    // Type-erased CreateProperty
    auto doCreate = [](MM::Device *d, const char *name, const char *val, MM::PropertyType t,
                       bool ro, MM::ActionFunctor *act, bool preInit) -> int {
        return static_cast<TDevice *>(d)->CreateProperty(name, val, t, ro, act, preInit);
    };

    return nb::cpp_function(
        [dev, doCreate, canCreate](const std::string &name, const std::string &defaultValue,
                                   int mmType, bool readOnly, nb::object getter,
                                   nb::object setter, bool preInit, nb::object limits,
                                   nb::object allowedValues) -> PropertyHandle {
            if (!*canCreate)
                throw std::runtime_error("create_property() can only be called during "
                                         "initialize()");

            auto action = makePropertyAction(getter, setter);

            int ret = doCreate(dev, name.c_str(), defaultValue.c_str(),
                               static_cast<MM::PropertyType>(mmType), readOnly, action.get(),
                               preInit);
            if (ret == DEVICE_OK)
                action.release();

            PropertyHandle handle(dev, name);

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
// initializeWithPropertyFactory — calls Python's initialize(create_property).
// The create_property callable is invalidated after initialize() returns.
// ============================================================================

template <typename TDevice> int initializeWithPropertyFactory(TDevice *dev, nb::object &py) {
    auto canCreate = std::make_shared<std::atomic<bool>>(true);
    nb::object factory = createPropertyFactory(dev, canCreate);
    try {
        py.attr("initialize")(factory);
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

    PyBridgeDeviceBase(nb::object py_dev, std::string name)
        : py_(std::move(py_dev)), deviceName_(std::move(name)) {}

    ~PyBridgeDeviceBase() {
        try {
            nb::gil_scoped_acquire gil;
            py_.reset();
        } catch (...) {
        }
    }

    int initializeCommon(TDevice *dev) {
        nb::gil_scoped_acquire gil;
        return initializeWithPropertyFactory(dev, py_);
    }

    int shutdownCommon() { return py_call(py_, "shutdown"); }

    bool busyCommon() { return py_get<bool>(py_, "busy"); }

    void getNameCommon(char *name) const {
        CDeviceUtils::CopyLimitedString(name, deviceName_.c_str());
    }
};

#define PYBRIDGE_COMMON_OVERRIDES(ClassName)                                                   \
  public:                                                                                      \
    ClassName(nb::object py_dev, std::string name)                                             \
        : PyBridgeDeviceBase<ClassName>(std::move(py_dev), std::move(name)) {}                 \
    int Initialize() override { return this->initializeCommon(this); }                         \
    int Shutdown() override { return this->shutdownCommon(); }                                 \
    bool Busy() override { return this->busyCommon(); }                                        \
    void GetName(char *name) const override { this->getNameCommon(name); }

// ============================================================================
// PyBridgeCamera
// ============================================================================

class PyBridgeCamera : public CCameraBase<PyBridgeCamera>,
                       private PyBridgeDeviceBase<PyBridgeCamera> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeCamera)

    std::vector<unsigned char> buf_;
    std::atomic<bool> capturing_{false};

    // -- MM::Camera: getters --
    unsigned GetImageWidth() const override { return py_get<unsigned>(py_, "get_image_width"); }
    unsigned GetImageHeight() const override {
        return py_get<unsigned>(py_, "get_image_height");
    }
    unsigned GetImageBytesPerPixel() const override {
        return py_get<unsigned>(py_, "get_bytes_per_pixel");
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
    int SnapImage() override {
        nb::gil_scoped_acquire gil;
        py_.attr("snap_image")();
        nb::object arr = py_.attr("get_image_buffer")();
        auto nd = nb::cast<nb::ndarray<nb::c_contig, nb::ro, nb::device::cpu>>(arr);
        size_t nbytes = nd.nbytes();
        buf_.resize(nbytes);
        std::memcpy(buf_.data(), nd.data(), nbytes);
        return DEVICE_OK;
    }

    const unsigned char *GetImageBuffer() override { return buf_.data(); }

    // -- MM::Camera: ROI --
    int SetROI(unsigned x, unsigned y, unsigned w, unsigned h) override {
        return py_call(py_, "set_roi", x, y, w, h);
    }
    int ClearROI() override { return py_call(py_, "clear_roi"); }

    int GetROI(unsigned &x, unsigned &y, unsigned &w, unsigned &h) override {
        nb::gil_scoped_acquire gil;
        auto roi = py_.attr("get_roi")();
        x = nb::cast<unsigned>(roi[nb::int_(0)]);
        y = nb::cast<unsigned>(roi[nb::int_(1)]);
        w = nb::cast<unsigned>(roi[nb::int_(2)]);
        h = nb::cast<unsigned>(roi[nb::int_(3)]);
        return DEVICE_OK;
    }

    // -- MM::Camera: sequence acquisition --
    int IsExposureSequenceable(bool &f) const override {
        f = false;
        return DEVICE_OK;
    }

    bool IsCapturing() override { return capturing_; }

    int StartSequenceAcquisition(long numImages, double interval_ms,
                                 bool stopOnOverflow) override {
        nb::gil_scoped_acquire gil;
        py_.attr("start_sequence_acquisition")(numImages, interval_ms, stopOnOverflow);
        capturing_ = true;
        return DEVICE_OK;
    }

    int StartSequenceAcquisition(double interval_ms) override {
        return StartSequenceAcquisition(LONG_MAX, interval_ms, false);
    }

    int StopSequenceAcquisition() override {
        nb::gil_scoped_acquire gil;
        py_.attr("stop_sequence_acquisition")();
        capturing_ = false;
        return DEVICE_OK;
    }
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

    // -- MM::Stage (pure virtuals only — base provides defaults for rest) --
    int SetPositionUm(double pos) override { return py_call(py_, "set_position_um", pos); }
    int GetPositionUm(double &pos) override {
        pos = py_get<double>(py_, "get_position_um");
        return DEVICE_OK;
    }
    int SetPositionSteps(long steps) override {
        return py_call(py_, "set_position_steps", steps);
    }
    int GetPositionSteps(long &steps) override {
        steps = py_get<long>(py_, "get_position_steps");
        return DEVICE_OK;
    }
    int SetOrigin() override { return py_call(py_, "set_origin"); }
    int GetLimits(double &lo, double &hi) override {
        nb::gil_scoped_acquire gil;
        auto lim = py_.attr("get_limits")();
        lo = nb::cast<double>(lim[nb::int_(0)]);
        hi = nb::cast<double>(lim[nb::int_(1)]);
        return DEVICE_OK;
    }
    int IsStageSequenceable(bool &f) const override {
        f = false;
        return DEVICE_OK;
    }
    bool IsContinuousFocusDrive() const override { return false; }
};

// ============================================================================
// PyBridgeXYStage
// ============================================================================

class PyBridgeXYStage : public CXYStageBase<PyBridgeXYStage>,
                        private PyBridgeDeviceBase<PyBridgeXYStage> {
    PYBRIDGE_COMMON_OVERRIDES(PyBridgeXYStage)

    // -- MM::XYStage (pure virtuals — base provides Um/relative/origin defaults) --
    int SetPositionSteps(long x, long y) override {
        return py_call(py_, "set_position_steps", x, y);
    }
    int GetPositionSteps(long &x, long &y) override {
        nb::gil_scoped_acquire gil;
        auto pos = py_.attr("get_position_steps")();
        x = nb::cast<long>(pos[nb::int_(0)]);
        y = nb::cast<long>(pos[nb::int_(1)]);
        return DEVICE_OK;
    }
    int Home() override { return py_call(py_, "home"); }
    int Stop() override { return py_call(py_, "stop"); }
    int SetOrigin() override { return py_call(py_, "set_origin"); }
    int GetLimitsUm(double &xMin, double &xMax, double &yMin, double &yMax) override {
        nb::gil_scoped_acquire gil;
        auto lim = py_.attr("get_limits_um")();
        xMin = nb::cast<double>(lim[nb::int_(0)]);
        xMax = nb::cast<double>(lim[nb::int_(1)]);
        yMin = nb::cast<double>(lim[nb::int_(2)]);
        yMax = nb::cast<double>(lim[nb::int_(3)]);
        return DEVICE_OK;
    }
    int GetStepLimits(long &xMin, long &xMax, long &yMin, long &yMax) override {
        nb::gil_scoped_acquire gil;
        auto lim = py_.attr("get_step_limits")();
        xMin = nb::cast<long>(lim[nb::int_(0)]);
        xMax = nb::cast<long>(lim[nb::int_(1)]);
        yMin = nb::cast<long>(lim[nb::int_(2)]);
        yMax = nb::cast<long>(lim[nb::int_(3)]);
        return DEVICE_OK;
    }
    double GetStepSizeXUm() override { return py_get<double>(py_, "get_step_size_x_um"); }
    double GetStepSizeYUm() override { return py_get<double>(py_, "get_step_size_y_um"); }
    int IsXYStageSequenceable(bool &f) const override {
        f = false;
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
        nb::gil_scoped_acquire gil;
        return nb::cast<unsigned long>(py_.attr("get_number_of_positions")());
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
        nb::gil_scoped_acquire gil;
        size_t nbytes = static_cast<size_t>(GetWidth()) * GetHeight() * GetBytesPerPixel();
        auto arr = nb::ndarray<uint8_t, nb::c_contig>(pixels, {nbytes});
        py_.attr("set_image")(arr);
        return DEVICE_OK;
    }
    int SetImage(unsigned int *pixels) override {
        nb::gil_scoped_acquire gil;
        size_t n = static_cast<size_t>(GetWidth()) * GetHeight();
        auto arr = nb::ndarray<uint32_t, nb::c_contig>(pixels, {n});
        py_.attr("set_image")(arr);
        return DEVICE_OK;
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
