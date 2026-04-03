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
// PropertyBridge — passed to Python's initialize(bridge) as a capability
// token for registering MM properties on the C++ device.
//
// Exposed to Python as a nanobind class (registered in NB_MODULE).
// Wraps a raw CDeviceBase pointer that is only valid during Initialize().
// ============================================================================

class PropertyBridge {
    // Type-erased pointer to the CDeviceBase. Valid only during Initialize().
    MM::Device *dev_ = nullptr;

    // Helper: access CDeviceBase methods via the raw MM::Device pointer.
    // CDeviceBase is a template, but the property methods we need are
    // inherited from its non-template base. We cast through the known
    // CDeviceBase interface using the MM::Device virtual methods directly,
    // but CreateProperty etc. are not virtual on MM::Device — they're on
    // CDeviceBase. So we use a function pointer table set during construction.
    struct Vtable {
        int (*createProperty)(MM::Device *, const char *, const char *, MM::PropertyType, bool,
                              MM::ActionFunctor *, bool);
        int (*setPropertyLimits)(MM::Device *, const char *, double, double);
        int (*setAllowedValues)(MM::Device *, const char *, std::vector<std::string> &);
    };
    Vtable vt_{};

  public:
    PropertyBridge() = default;

    template <typename TDevice> explicit PropertyBridge(TDevice *dev) : dev_(dev) {
        vt_.createProperty = [](MM::Device *d, const char *name, const char *val,
                                MM::PropertyType t, bool ro, MM::ActionFunctor *act,
                                bool preInit) -> int {
            return static_cast<TDevice *>(d)->CreateProperty(name, val, t, ro, act, preInit);
        };
        vt_.setPropertyLimits = [](MM::Device *d, const char *name, double lo,
                                   double hi) -> int {
            return static_cast<TDevice *>(d)->SetPropertyLimits(name, lo, hi);
        };
        vt_.setAllowedValues = [](MM::Device *d, const char *name,
                                  std::vector<std::string> &vals) -> int {
            return static_cast<TDevice *>(d)->SetAllowedValues(name, vals);
        };
    }

    // Invalidate after Initialize() returns.
    void invalidate() { dev_ = nullptr; }

    // -- Python-facing API --

    void createProperty(const std::string &name, const std::string &defaultValue, int mmType,
                        bool readOnly, nb::object getter, nb::object setter, bool preInit) {
        if (!dev_)
            throw std::runtime_error("PropertyBridge is only valid during initialize()");

        MM::ActionFunctor *action = nullptr;
        if (!getter.is_none() || !setter.is_none()) {
            // Wrap getter/setter in a shared_ptr so the ActionLambda
            // destructor (called by ~CDeviceBase, potentially without
            // GIL) safely releases via the ref-guard destructor.
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
            auto cbs = std::make_shared<PyCallbacks>(PyCallbacks{getter, setter});

            action = new MM::ActionLambda(
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

        vt_.createProperty(dev_, name.c_str(), defaultValue.c_str(),
                           static_cast<MM::PropertyType>(mmType), readOnly, action, preInit);
    }

    void setPropertyLimits(const std::string &name, double lo, double hi) {
        if (!dev_)
            throw std::runtime_error("PropertyBridge is only valid during initialize()");
        vt_.setPropertyLimits(dev_, name.c_str(), lo, hi);
    }

    void setAllowedValues(const std::string &name, std::vector<std::string> values) {
        if (!dev_)
            throw std::runtime_error("PropertyBridge is only valid during initialize()");
        vt_.setAllowedValues(dev_, name.c_str(), values);
    }
};

// ============================================================================
// PyBridgeCamera
// ============================================================================

class PyBridgeCamera : public CCameraBase<PyBridgeCamera> {
    nb::object py_;
    std::vector<unsigned char> buf_;
    std::atomic<bool> capturing_{false};

  public:
    explicit PyBridgeCamera(nb::object py_dev) : py_(std::move(py_dev)) {}

    ~PyBridgeCamera() {
        try {
            nb::gil_scoped_acquire gil;
            py_.reset();
        } catch (...) {
        }
    }

    // -- MM::Device --
    int Initialize() override {
        nb::gil_scoped_acquire gil;
        PropertyBridge bridge(this);
        py_.attr("initialize")(nb::cast(bridge, nb::rv_policy::reference));
        bridge.invalidate();
        return DEVICE_OK;
    }

    int Shutdown() override { return py_call(py_, "shutdown"); }
    bool Busy() override { return py_get<bool>(py_, "busy"); }

    void GetName(char *name) const override {
        nb::gil_scoped_acquire gil;
        auto s = nb::cast<std::string>(py_.attr("name")());
        CDeviceUtils::CopyLimitedString(name, s.c_str());
    }

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

class PyBridgeShutter : public CShutterBase<PyBridgeShutter> {
    nb::object py_;

  public:
    explicit PyBridgeShutter(nb::object py_dev) : py_(std::move(py_dev)) {}

    ~PyBridgeShutter() {
        try {
            nb::gil_scoped_acquire gil;
            py_.reset();
        } catch (...) {
        }
    }

    // -- MM::Device --
    int Initialize() override {
        nb::gil_scoped_acquire gil;
        PropertyBridge bridge(this);
        py_.attr("initialize")(nb::cast(bridge, nb::rv_policy::reference));
        bridge.invalidate();
        return DEVICE_OK;
    }

    int Shutdown() override { return py_call(py_, "shutdown"); }
    bool Busy() override { return py_get<bool>(py_, "busy"); }

    void GetName(char *name) const override {
        nb::gil_scoped_acquire gil;
        auto s = nb::cast<std::string>(py_.attr("name")());
        CDeviceUtils::CopyLimitedString(name, s.c_str());
    }

    // -- MM::Shutter --
    int SetOpen(bool open) override { return py_call(py_, "set_open", open); }

    int GetOpen(bool &open) override {
        open = py_get<bool>(py_, "get_open");
        return DEVICE_OK;
    }

    int Fire(double deltaT) override { return py_call(py_, "fire", deltaT); }
};

// ============================================================================
// PyBridgeAdapter — implements MockDeviceAdapter for Python bridge devices
// ============================================================================

class PyBridgeAdapter : public MockDeviceAdapter {
    struct DeviceInfo {
        std::string name;
        nb::object py_dev;
        MM::DeviceType type;
    };

    std::vector<DeviceInfo> devices_;

  public:
    ~PyBridgeAdapter() {
        try {
            nb::gil_scoped_acquire gil;
            devices_.clear();
        } catch (...) {
        }
    }

    void addDevice(const std::string &name, nb::object py_dev, MM::DeviceType type) {
        devices_.push_back({name, std::move(py_dev), type});
    }

    void InitializeModuleData(RegisterDeviceFunc registerDevice) override {
        for (auto &d : devices_) {
            registerDevice(d.name.c_str(), d.type, "Python bridge device");
        }
    }

    MM::Device *CreateDevice(const char *name) override {
        nb::gil_scoped_acquire gil;
        for (auto &d : devices_) {
            if (d.name == name) {
                switch (d.type) {
                case MM::CameraDevice: return new PyBridgeCamera(d.py_dev);
                case MM::ShutterDevice: return new PyBridgeShutter(d.py_dev);
                // TODO: Stage, XYStage, State, SLM, Hub
                default: return nullptr;
                }
            }
        }
        return nullptr;
    }

    void DeleteDevice(MM::Device *device) override { delete device; }
};
