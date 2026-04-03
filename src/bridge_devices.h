// Bridge device classes that forward MM::Device calls to Python objects.
// These enable Python-implemented devices to be registered as real devices
// in CMMCore's device registry via the MockDeviceAdapter infrastructure.

#pragma once

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

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
//
// Real device adapters don't catch exceptions from their own methods —
// CMMCore catches at the public API boundary. We follow the same pattern:
// if the Python device raises, we let it propagate.
// ============================================================================

// Call a Python getter, return the cast result.
template <typename T>
T py_get(const nb::object& py, const char* attr) {
    nb::gil_scoped_acquire gil;
    return nb::cast<T>(py.attr(attr)());
}

// Call a Python method with args, no return value.
template <typename... Args>
void py_set(const nb::object& py, const char* attr, Args&&... args) {
    nb::gil_scoped_acquire gil;
    py.attr(attr)(std::forward<Args>(args)...);
}

// Call a Python method with args, return DEVICE_OK.
template <typename... Args>
int py_call(const nb::object& py, const char* attr, Args&&... args) {
    nb::gil_scoped_acquire gil;
    py.attr(attr)(std::forward<Args>(args)...);
    return DEVICE_OK;
}

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
    int Initialize() override { return py_call(py_, "initialize"); }
    int Shutdown() override { return py_call(py_, "shutdown"); }
    bool Busy() override { return py_get<bool>(py_, "busy"); }

    void GetName(char* name) const override {
        nb::gil_scoped_acquire gil;
        auto s = nb::cast<std::string>(py_.attr("name")());
        CDeviceUtils::CopyLimitedString(name, s.c_str());
    }

    // -- MM::Camera: getters --
    unsigned GetImageWidth() const override {
        return py_get<unsigned>(py_, "get_image_width");
    }
    unsigned GetImageHeight() const override {
        return py_get<unsigned>(py_, "get_image_height");
    }
    unsigned GetImageBytesPerPixel() const override {
        return py_get<unsigned>(py_, "get_bytes_per_pixel");
    }
    unsigned GetBitDepth() const override {
        return py_get<unsigned>(py_, "get_bit_depth");
    }
    long GetImageBufferSize() const override {
        return py_get<long>(py_, "get_image_buffer_size");
    }
    double GetExposure() const override {
        return py_get<double>(py_, "get_exposure");
    }
    int GetBinning() const override {
        return py_get<int>(py_, "get_binning");
    }

    // -- MM::Camera: setters --
    void SetExposure(double ms) override { py_set(py_, "set_exposure", ms); }
    int SetBinning(int bin) override {
        return py_call(py_, "set_binning", bin);
    }

    // -- MM::Camera: snap + buffer --
    int SnapImage() override {
        nb::gil_scoped_acquire gil;
        py_.attr("snap_image")();
        nb::object arr = py_.attr("get_image_buffer")();
        auto nd = nb::cast<nb::ndarray<nb::c_contig>>(arr);
        size_t nbytes = nd.nbytes();
        buf_.resize(nbytes);
        std::memcpy(buf_.data(), nd.data(), nbytes);
        return DEVICE_OK;
    }

    const unsigned char* GetImageBuffer() override { return buf_.data(); }

    // -- MM::Camera: ROI --
    int SetROI(unsigned x, unsigned y, unsigned w, unsigned h) override {
        return py_call(py_, "set_roi", x, y, w, h);
    }
    int ClearROI() override { return py_call(py_, "clear_roi"); }

    int GetROI(unsigned& x, unsigned& y, unsigned& w, unsigned& h) override {
        nb::gil_scoped_acquire gil;
        auto roi = py_.attr("get_roi")();
        x = nb::cast<unsigned>(roi[nb::int_(0)]);
        y = nb::cast<unsigned>(roi[nb::int_(1)]);
        w = nb::cast<unsigned>(roi[nb::int_(2)]);
        h = nb::cast<unsigned>(roi[nb::int_(3)]);
        return DEVICE_OK;
    }

    // -- MM::Camera: sequence acquisition --
    int IsExposureSequenceable(bool& f) const override {
        f = false;
        return DEVICE_OK;
    }

    bool IsCapturing() override { return capturing_; }

    int StartSequenceAcquisition(long numImages, double interval_ms,
                                 bool stopOnOverflow) override {
        nb::gil_scoped_acquire gil;
        py_.attr("start_sequence_acquisition")(numImages, interval_ms,
                                               stopOnOverflow);
        capturing_ = true;  // set after success
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
    int Initialize() override { return py_call(py_, "initialize"); }
    int Shutdown() override { return py_call(py_, "shutdown"); }
    bool Busy() override { return py_get<bool>(py_, "busy"); }

    void GetName(char* name) const override {
        nb::gil_scoped_acquire gil;
        auto s = nb::cast<std::string>(py_.attr("name")());
        CDeviceUtils::CopyLimitedString(name, s.c_str());
    }

    // -- MM::Shutter --
    int SetOpen(bool open) override {
        return py_call(py_, "set_open", open);
    }

    int GetOpen(bool& open) override {
        open = py_get<bool>(py_, "get_open");
        return DEVICE_OK;
    }

    int Fire(double deltaT) override {
        return py_call(py_, "fire", deltaT);
    }
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

    void addDevice(const std::string& name, nb::object py_dev,
                   MM::DeviceType type) {
        devices_.push_back({name, std::move(py_dev), type});
    }

    void InitializeModuleData(RegisterDeviceFunc registerDevice) override {
        for (auto& d : devices_) {
            registerDevice(d.name.c_str(), d.type, "Python bridge device");
        }
    }

    MM::Device* CreateDevice(const char* name) override {
        nb::gil_scoped_acquire gil;
        for (auto& d : devices_) {
            if (d.name == name) {
                switch (d.type) {
                case MM::CameraDevice:
                    return new PyBridgeCamera(d.py_dev);
                case MM::ShutterDevice:
                    return new PyBridgeShutter(d.py_dev);
                // TODO: Stage, XYStage, State, SLM, Hub
                default:
                    return nullptr;
                }
            }
        }
        return nullptr;
    }

    void DeleteDevice(MM::Device* device) override {
        delete device;
    }
};
