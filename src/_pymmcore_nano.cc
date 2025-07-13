#include <nanobind/make_iterator.h>
#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>
#include <nanobind/trampoline.h>

#include "MMCore.h"
#include "MMEventCallback.h"
#include "ModuleInterface.h"

namespace nb = nanobind;

using namespace nb::literals;

const std::string PYMMCORE_NANO_VERSION = "2";

///////////////// GIL_MACROS ///////////////////

// If you define HOLD_GIL in your build (e.g. -DHOLD_GIL),
// then the GIL will be held for the duration of all calls into C++ from
// Python.  By default, the GIL is released for most calls into C++ from Python.
#ifdef HOLD_GIL
#define RGIL
#define GIL_HELD 1
#else
#define RGIL , nb::call_guard<nb::gil_scoped_release>()
#define GIL_HELD 0
#endif

///////////////// NUMPY ARRAY HELPERS ///////////////////

// Alias for read-only NumPy array
using np_array = nb::ndarray<nb::numpy, nb::ro>;
using StrVec = std::vector<std::string>;

// Helper function to allocate a new buffer, copy the data,
// and return an np_array that views the data starting at (raw_ptr + offset)
np_array make_np_array_from_copy(const void *src, size_t nbytes,
                                 std::initializer_list<size_t> shape,
                                 std::initializer_list<int64_t> strides,
                                 nb::dlpack::dtype dtype, size_t offset = 0) {
    uint8_t *raw_ptr;
    auto buffer = std::make_unique<uint8_t[]>(nbytes);
    std::memcpy(buffer.get(), src, nbytes);
    raw_ptr = buffer.release();

    // acquire the GIL before creating Python objects.
    nb::gil_scoped_acquire gil;
    nb::capsule owner(raw_ptr,
                      [](void *ptr) noexcept { delete[] static_cast<uint8_t *>(ptr); });
    return np_array(raw_ptr + offset, shape, owner, strides, dtype);
}

/**
 * @brief Creates a read-only NumPy array for pBuf for a given width, height,
 * etc. These parameters are are gleaned either from image metadata or core
 * methods.
 *
 */
np_array build_grayscale_np_array(CMMCore &core, void *pBuf, unsigned width, unsigned height,
                                  unsigned byteDepth) {
    std::initializer_list<size_t> shape = {height, width};
    std::initializer_list<int64_t> strides = {width, 1};

    // Determine the dtype based on the element size.
    nb::dlpack::dtype dtype;
    switch (byteDepth) {
    case 1: dtype = nb::dtype<uint8_t>(); break;
    case 2: dtype = nb::dtype<uint16_t>(); break;
    case 4: dtype = nb::dtype<uint32_t>(); break;
    default: throw std::invalid_argument("Unsupported element size");
    }

    // pBuf is assumed to be a contiguous grayscale image with (height*width) pixels.
    size_t nbytes = static_cast<size_t>(height) * width * byteDepth;
    return make_np_array_from_copy(pBuf, nbytes, shape, strides, dtype);
}

// only reason we're making two functions here is that i had a hell of a time
// trying to create std::initializer_list dynamically based on numComponents
// (only on Linux) so we create two constructors
np_array build_rgb_np_array(CMMCore &core, void *pBuf, unsigned width, unsigned height,
                            unsigned byteDepth) {
    // The source is in BGRA order with 4 components per pixel.
    // We will create a view that skips the alpha channel and inverts the order.
    const unsigned out_byteDepth = byteDepth / 4;

    std::initializer_list<size_t> shape = {height, width, 3};
    // Note the negative stride for the last dimension, data comes in as BGRA
    // we want to invert that to be ARGB
    std::initializer_list<int64_t> strides = {width * byteDepth, byteDepth, -1};

    // Determine the dtype based on per-channel size.
    nb::dlpack::dtype dtype;
    switch (out_byteDepth) { // all RGB formats have 4 components in a single "pixel"
    case 1: dtype = nb::dtype<uint8_t>(); break;
    case 2: dtype = nb::dtype<uint16_t>(); break;
    case 4: dtype = nb::dtype<uint32_t>(); break;
    default: throw std::invalid_argument("Unsupported element size");
    }

    // The original pBuf contains BGRA pixels; each pixel takes byteDepth bytes.
    // Therefore, copy height*width*byteDepth bytes.
    size_t nbytes = static_cast<size_t>(height) * width * byteDepth;
    // Compute an offset into each pixel so that the view starts at the R channel.
    // For BGRA, offset = out_byteDepth * 2 yields [R, G, B] when using a -1 stride.
    size_t offset = out_byteDepth * 2;
    return make_np_array_from_copy(pBuf, nbytes, shape, strides, dtype, offset);
}

/** @brief Create a read-only NumPy array using core methods
 *  getImageWidth/getImageHeight/getBytesPerPixel/getNumberOfComponents
 */
np_array create_image_array(CMMCore &core, void *pBuf) {
    // Retrieve image properties
    unsigned width = core.getImageWidth();
    unsigned height = core.getImageHeight();
    unsigned bytesPerPixel = core.getBytesPerPixel();
    unsigned numComponents = core.getNumberOfComponents();
    if (numComponents == 4) {
        return build_rgb_np_array(core, pBuf, width, height, bytesPerPixel);
    } else {
        return build_grayscale_np_array(core, pBuf, width, height, bytesPerPixel);
    }
}

/**
 * @brief Creates a read-only NumPy array for pBuf by using
 * width/height/pixelType from a metadata object if possible, otherwise falls
 * back to core methods.
 *
 */
np_array create_metadata_array(CMMCore &core, void *pBuf, const Metadata md) {
    std::string width_str, height_str, pixel_type;
    unsigned width = 0, height = 0;
    unsigned bytesPerPixel, numComponents = 1;
    try {
        // These keys are unfortunately hard-coded in the source code
        // see https://github.com/micro-manager/mmCoreAndDevices/pull/531
        // Retrieve and log the values of the tags
        width_str = md.GetSingleTag("Width").GetValue();
        height_str = md.GetSingleTag("Height").GetValue();
        pixel_type = md.GetSingleTag("PixelType").GetValue();
        width = std::stoi(width_str);
        height = std::stoi(height_str);

        if (pixel_type == "GRAY8") {
            bytesPerPixel = 1;
        } else if (pixel_type == "GRAY16") {
            bytesPerPixel = 2;
        } else if (pixel_type == "GRAY32") {
            bytesPerPixel = 4;
        } else if (pixel_type == "RGB32") {
            numComponents = 4;
            bytesPerPixel = 4;
        } else if (pixel_type == "RGB64") {
            numComponents = 4;
            bytesPerPixel = 8;
        } else {
            throw std::runtime_error("Unsupported pixelType.");
        }
    } catch (...) {
        // The metadata doesn't have what we need to shape the array...
        // Fallback to core.getImageWidth etc...
        return create_image_array(core, pBuf);
    }
    if (numComponents == 4) {
        return build_rgb_np_array(core, pBuf, width, height, bytesPerPixel);
    } else {
        return build_grayscale_np_array(core, pBuf, width, height, bytesPerPixel);
    }
}

void validate_slm_image(const nb::ndarray<uint8_t> &pixels, long expectedWidth,
                        long expectedHeight, long bytesPerPixel) {
    // Check dtype
    if (pixels.dtype() != nb::dtype<uint8_t>()) {
        throw std::invalid_argument("Pixel array type is wrong. Expected uint8.");
    }

    // Check dimensions
    if (pixels.ndim() != 2 && pixels.ndim() != 3) {
        throw std::invalid_argument(
            "Pixels must be a 2D numpy array [h,w] of uint8, or a 3D numpy array "
            "[h,w,c] of uint8 with 3 color channels [R,G,B].");
    }

    // Check shape
    if (pixels.shape(0) != expectedHeight || pixels.shape(1) != expectedWidth) {
        throw std::invalid_argument("Image dimensions are wrong for this SLM. Expected (" +
                                    std::to_string(expectedHeight) + ", " +
                                    std::to_string(expectedWidth) + "), but received (" +
                                    std::to_string(pixels.shape(0)) + ", " +
                                    std::to_string(pixels.shape(1)) + ").");
    }

    // Check total bytes
    long expectedBytes = expectedWidth * expectedHeight * bytesPerPixel;
    if (pixels.nbytes() != expectedBytes) {
        throw std::invalid_argument("Image size is wrong for this SLM. Expected " +
                                    std::to_string(expectedBytes) + " bytes, but received " +
                                    std::to_string(pixels.nbytes()) +
                                    " bytes. Does this SLM support RGB?");
    }

    // Ensure C-contiguous layout
    // TODO
}

///////////////// Trampoline class for MMEventCallback ///////////////////

// Allow Python to override virtual functions in MMEventCallback
// https://nanobind.readthedocs.io/en/latest/classes.html#overriding-virtual-functions-in-python

class PyMMEventCallback : public MMEventCallback {
  public:
    NB_TRAMPOLINE(MMEventCallback,
                  14); // Total number of overridable virtual methods.

    void onPropertiesChanged() override { NB_OVERRIDE(onPropertiesChanged); }

    void onPropertyChanged(const char *name, const char *propName,
                           const char *propValue) override {
        NB_OVERRIDE(onPropertyChanged, name, propName, propValue);
    }

    void onChannelGroupChanged(const char *newChannelGroupName) override {
        NB_OVERRIDE(onChannelGroupChanged, newChannelGroupName);
    }

    void onConfigGroupChanged(const char *groupName, const char *newConfigName) override {
        NB_OVERRIDE(onConfigGroupChanged, groupName, newConfigName);
    }

    void onSystemConfigurationLoaded() override { NB_OVERRIDE(onSystemConfigurationLoaded); }

    void onPixelSizeChanged(double newPixelSizeUm) override {
        NB_OVERRIDE(onPixelSizeChanged, newPixelSizeUm);
    }

    void onPixelSizeAffineChanged(double v0, double v1, double v2, double v3, double v4,
                                  double v5) override {
        NB_OVERRIDE(onPixelSizeAffineChanged, v0, v1, v2, v3, v4, v5);
    }

    void onStagePositionChanged(const char *name, double pos) override {
        NB_OVERRIDE(onStagePositionChanged, name, pos);
    }

    void onXYStagePositionChanged(const char *name, double xpos, double ypos) override {
        NB_OVERRIDE(onXYStagePositionChanged, name, xpos, ypos);
    }

    void onExposureChanged(const char *name, double newExposure) override {
        NB_OVERRIDE(onExposureChanged, name, newExposure);
    }

    void onSLMExposureChanged(const char *name, double newExposure) override {
        NB_OVERRIDE(onSLMExposureChanged, name, newExposure);
    }

    void onImageSnapped(const char *cameraLabel) override {
        NB_OVERRIDE(onImageSnapped, cameraLabel);
    }

    void onSequenceAcquisitionStarted(const char *cameraLabel) override {
        NB_OVERRIDE(onSequenceAcquisitionStarted, cameraLabel);
    }

    void onSequenceAcquisitionStopped(const char *cameraLabel) override {
        NB_OVERRIDE(onSequenceAcquisitionStopped, cameraLabel);
    }
};

////////////////////////////////////////////////////////////////////////////
///////////////// main _pymmcore_nano module definition  ///////////////////
////////////////////////////////////////////////////////////////////////////

NB_MODULE(_pymmcore_nano, m) {
    // https://nanobind.readthedocs.io/en/latest/faq.html#why-am-i-getting-errors-about-leaked-functions-and-types
    nb::set_leak_warnings(false);

    m.doc() = "Python bindings for MMCore";

    /////////////////// Module Attributes ///////////////////

    m.attr("DEVICE_INTERFACE_VERSION") = CMMCore::getMMDeviceDeviceInterfaceVersion();
    m.attr("MODULE_INTERFACE_VERSION") = CMMCore::getMMDeviceModuleInterfaceVersion();
    std::string version = std::to_string(CMMCore::getMMCoreVersionMajor()) + "." +
                          std::to_string(CMMCore::getMMCoreVersionMinor()) + "." +
                          std::to_string(CMMCore::getMMCoreVersionPatch());
    m.attr("MMCore_version") = version;
    m.attr("MMCore_version_info") =
        std::tuple(CMMCore::getMMCoreVersionMajor(), CMMCore::getMMCoreVersionMinor(),
                   CMMCore::getMMCoreVersionPatch());
    // the final combined version
    m.attr("PYMMCORE_NANO_VERSION") = PYMMCORE_NANO_VERSION;
    m.attr("__version__") = version + "." +
                            std::to_string(CMMCore::getMMDeviceDeviceInterfaceVersion()) + "." +
                            PYMMCORE_NANO_VERSION;

#ifdef MATCH_SWIG
    m.attr("_MATCH_SWIG") = 1;
#else
    m.attr("_MATCH_SWIG") = 0;
#endif
    m.attr("MM_CODE_OK") = MM_CODE_OK;
    m.attr("MM_CODE_ERR") = MM_CODE_ERR;
    m.attr("DEVICE_OK") = DEVICE_OK;
    m.attr("DEVICE_ERR") = DEVICE_ERR;
    m.attr("DEVICE_INVALID_PROPERTY") = DEVICE_INVALID_PROPERTY;
    m.attr("DEVICE_INVALID_PROPERTY_VALUE") = DEVICE_INVALID_PROPERTY_VALUE;
    m.attr("DEVICE_DUPLICATE_PROPERTY") = DEVICE_DUPLICATE_PROPERTY;
    m.attr("DEVICE_INVALID_PROPERTY_TYPE") = DEVICE_INVALID_PROPERTY_TYPE;
    m.attr("DEVICE_NATIVE_MODULE_FAILED") = DEVICE_NATIVE_MODULE_FAILED;
    m.attr("DEVICE_UNSUPPORTED_DATA_FORMAT") = DEVICE_UNSUPPORTED_DATA_FORMAT;
    m.attr("DEVICE_INTERNAL_INCONSISTENCY") = DEVICE_INTERNAL_INCONSISTENCY;
    m.attr("DEVICE_NOT_SUPPORTED") = DEVICE_NOT_SUPPORTED;
    m.attr("DEVICE_UNKNOWN_LABEL") = DEVICE_UNKNOWN_LABEL;
    m.attr("DEVICE_UNSUPPORTED_COMMAND") = DEVICE_UNSUPPORTED_COMMAND;
    m.attr("DEVICE_UNKNOWN_POSITION") = DEVICE_UNKNOWN_POSITION;
    m.attr("DEVICE_NO_CALLBACK_REGISTERED") = DEVICE_NO_CALLBACK_REGISTERED;
    m.attr("DEVICE_SERIAL_COMMAND_FAILED") = DEVICE_SERIAL_COMMAND_FAILED;
    m.attr("DEVICE_SERIAL_BUFFER_OVERRUN") = DEVICE_SERIAL_BUFFER_OVERRUN;
    m.attr("DEVICE_SERIAL_INVALID_RESPONSE") = DEVICE_SERIAL_INVALID_RESPONSE;
    m.attr("DEVICE_SERIAL_TIMEOUT") = DEVICE_SERIAL_TIMEOUT;
    m.attr("DEVICE_SELF_REFERENCE") = DEVICE_SELF_REFERENCE;
    m.attr("DEVICE_NO_PROPERTY_DATA") = DEVICE_NO_PROPERTY_DATA;
    m.attr("DEVICE_DUPLICATE_LABEL") = DEVICE_DUPLICATE_LABEL;
    m.attr("DEVICE_INVALID_INPUT_PARAM") = DEVICE_INVALID_INPUT_PARAM;
    m.attr("DEVICE_BUFFER_OVERFLOW") = DEVICE_BUFFER_OVERFLOW;
    m.attr("DEVICE_NONEXISTENT_CHANNEL") = DEVICE_NONEXISTENT_CHANNEL;
    m.attr("DEVICE_INVALID_PROPERTY_LIMITS") = DEVICE_INVALID_PROPERTY_LIMTS;
    m.attr("DEVICE_INVALID_PROPERTY_LIMTS") = DEVICE_INVALID_PROPERTY_LIMTS; // Fix Typo
    m.attr("DEVICE_SNAP_IMAGE_FAILED") = DEVICE_SNAP_IMAGE_FAILED;
    m.attr("DEVICE_IMAGE_PARAMS_FAILED") = DEVICE_IMAGE_PARAMS_FAILED;
    m.attr("DEVICE_CORE_FOCUS_STAGE_UNDEF") = DEVICE_CORE_FOCUS_STAGE_UNDEF;
    m.attr("DEVICE_CORE_EXPOSURE_FAILED") = DEVICE_CORE_EXPOSURE_FAILED;
    m.attr("DEVICE_CORE_CONFIG_FAILED") = DEVICE_CORE_CONFIG_FAILED;
    m.attr("DEVICE_CAMERA_BUSY_ACQUIRING") = DEVICE_CAMERA_BUSY_ACQUIRING;
    m.attr("DEVICE_INCOMPATIBLE_IMAGE") = DEVICE_INCOMPATIBLE_IMAGE;
    m.attr("DEVICE_CAN_NOT_SET_PROPERTY") = DEVICE_CAN_NOT_SET_PROPERTY;
    m.attr("DEVICE_CORE_CHANNEL_PRESETS_FAILED") = DEVICE_CORE_CHANNEL_PRESETS_FAILED;
    m.attr("DEVICE_LOCALLY_DEFINED_ERROR") = DEVICE_LOCALLY_DEFINED_ERROR;
    m.attr("DEVICE_NOT_CONNECTED") = DEVICE_NOT_CONNECTED;
    m.attr("DEVICE_COMM_HUB_MISSING") = DEVICE_COMM_HUB_MISSING;
    m.attr("DEVICE_DUPLICATE_LIBRARY") = DEVICE_DUPLICATE_LIBRARY;
    m.attr("DEVICE_PROPERTY_NOT_SEQUENCEABLE") = DEVICE_PROPERTY_NOT_SEQUENCEABLE;
    m.attr("DEVICE_SEQUENCE_TOO_LARGE") = DEVICE_SEQUENCE_TOO_LARGE;
    m.attr("DEVICE_OUT_OF_MEMORY") = DEVICE_OUT_OF_MEMORY;
    m.attr("DEVICE_NOT_YET_IMPLEMENTED") = DEVICE_NOT_YET_IMPLEMENTED;
    m.attr("DEVICE_PUMP_IS_RUNNING") = DEVICE_PUMP_IS_RUNNING;

    m.attr("g_Keyword_Name") = MM::g_Keyword_Name;
    m.attr("g_Keyword_Description") = MM::g_Keyword_Description;
    m.attr("g_Keyword_CameraName") = MM::g_Keyword_CameraName;
    m.attr("g_Keyword_CameraID") = MM::g_Keyword_CameraID;
    m.attr("g_Keyword_CameraChannelName") = MM::g_Keyword_CameraChannelName;
    m.attr("g_Keyword_CameraChannelIndex") = MM::g_Keyword_CameraChannelIndex;
    m.attr("g_Keyword_Binning") = MM::g_Keyword_Binning;
    m.attr("g_Keyword_Exposure") = MM::g_Keyword_Exposure;
    m.attr("g_Keyword_ActualExposure") = MM::g_Keyword_ActualExposure;
    m.attr("g_Keyword_ActualInterval_ms") = MM::g_Keyword_ActualInterval_ms;
    m.attr("g_Keyword_Interval_ms") = MM::g_Keyword_Interval_ms;
    m.attr("g_Keyword_Elapsed_Time_ms") = MM::g_Keyword_Elapsed_Time_ms;
    m.attr("g_Keyword_PixelType") = MM::g_Keyword_PixelType;
    m.attr("g_Keyword_ReadoutTime") = MM::g_Keyword_ReadoutTime;
    m.attr("g_Keyword_ReadoutMode") = MM::g_Keyword_ReadoutMode;
    m.attr("g_Keyword_Gain") = MM::g_Keyword_Gain;
    m.attr("g_Keyword_EMGain") = MM::g_Keyword_EMGain;
    m.attr("g_Keyword_Offset") = MM::g_Keyword_Offset;
    m.attr("g_Keyword_CCDTemperature") = MM::g_Keyword_CCDTemperature;
    m.attr("g_Keyword_CCDTemperatureSetPoint") = MM::g_Keyword_CCDTemperatureSetPoint;
    m.attr("g_Keyword_State") = MM::g_Keyword_State;
    m.attr("g_Keyword_Label") = MM::g_Keyword_Label;
    m.attr("g_Keyword_Position") = MM::g_Keyword_Position;
    m.attr("g_Keyword_Type") = MM::g_Keyword_Type;
    m.attr("g_Keyword_Delay") = MM::g_Keyword_Delay;
    m.attr("g_Keyword_BaudRate") = MM::g_Keyword_BaudRate;
    m.attr("g_Keyword_DataBits") = MM::g_Keyword_DataBits;
    m.attr("g_Keyword_StopBits") = MM::g_Keyword_StopBits;
    m.attr("g_Keyword_Parity") = MM::g_Keyword_Parity;
    m.attr("g_Keyword_Handshaking") = MM::g_Keyword_Handshaking;
    m.attr("g_Keyword_DelayBetweenCharsMs") = MM::g_Keyword_DelayBetweenCharsMs;
    m.attr("g_Keyword_Port") = MM::g_Keyword_Port;
    m.attr("g_Keyword_AnswerTimeout") = MM::g_Keyword_AnswerTimeout;
    m.attr("g_Keyword_Speed") = MM::g_Keyword_Speed;
    m.attr("g_Keyword_CoreDevice") = MM::g_Keyword_CoreDevice;
    m.attr("g_Keyword_CoreInitialize") = MM::g_Keyword_CoreInitialize;
    m.attr("g_Keyword_CoreCamera") = MM::g_Keyword_CoreCamera;
    m.attr("g_Keyword_CoreShutter") = MM::g_Keyword_CoreShutter;
    m.attr("g_Keyword_CoreXYStage") = MM::g_Keyword_CoreXYStage;
    m.attr("g_Keyword_CoreFocus") = MM::g_Keyword_CoreFocus;
    m.attr("g_Keyword_CoreAutoFocus") = MM::g_Keyword_CoreAutoFocus;
    m.attr("g_Keyword_CoreAutoShutter") = MM::g_Keyword_CoreAutoShutter;
    m.attr("g_Keyword_CoreChannelGroup") = MM::g_Keyword_CoreChannelGroup;
    m.attr("g_Keyword_CoreImageProcessor") = MM::g_Keyword_CoreImageProcessor;
    m.attr("g_Keyword_CoreSLM") = MM::g_Keyword_CoreSLM;
    m.attr("g_Keyword_CoreGalvo") = MM::g_Keyword_CoreGalvo;
    m.attr("g_Keyword_CorePressurePump") = MM::g_Keyword_CorePressurePump;
    m.attr("g_Keyword_CoreVolumetricPump") = MM::g_Keyword_CoreVolumetricPump;
    m.attr("g_Keyword_CoreTimeoutMs") = MM::g_Keyword_CoreTimeoutMs;
    m.attr("g_Keyword_Channel") = MM::g_Keyword_Channel;
    m.attr("g_Keyword_Version") = MM::g_Keyword_Version;
    m.attr("g_Keyword_ColorMode") = MM::g_Keyword_ColorMode;
    m.attr("g_Keyword_Transpose_SwapXY") = MM::g_Keyword_Transpose_SwapXY;
    m.attr("g_Keyword_Transpose_MirrorX") = MM::g_Keyword_Transpose_MirrorX;
    m.attr("g_Keyword_Transpose_MirrorY") = MM::g_Keyword_Transpose_MirrorY;
    m.attr("g_Keyword_Transpose_Correction") = MM::g_Keyword_Transpose_Correction;
    m.attr("g_Keyword_Closed_Position") = MM::g_Keyword_Closed_Position;
    m.attr("g_Keyword_HubID") = MM::g_Keyword_HubID;
    m.attr("g_Keyword_PixelType_GRAY8") = MM::g_Keyword_PixelType_GRAY8;
    m.attr("g_Keyword_PixelType_GRAY16") = MM::g_Keyword_PixelType_GRAY16;
    m.attr("g_Keyword_PixelType_GRAY32") = MM::g_Keyword_PixelType_GRAY32;
    m.attr("g_Keyword_PixelType_RGB32") = MM::g_Keyword_PixelType_RGB32;
    m.attr("g_Keyword_PixelType_RGB64") = MM::g_Keyword_PixelType_RGB64;
    m.attr("g_Keyword_PixelType_Unknown") = MM::g_Keyword_PixelType_Unknown;
    m.attr("g_Keyword_Current_Volume") = MM::g_Keyword_Current_Volume;
    m.attr("g_Keyword_Min_Volume") = MM::g_Keyword_Min_Volume;
    m.attr("g_Keyword_Max_Volume") = MM::g_Keyword_Max_Volume;
    m.attr("g_Keyword_Flowrate") = MM::g_Keyword_Flowrate;
    m.attr("g_Keyword_Pressure_Imposed") = MM::g_Keyword_Pressure_Imposed;
    m.attr("g_Keyword_Pressure_Measured") = MM::g_Keyword_Pressure_Measured;
    m.attr("g_Keyword_Metadata_CameraLabel") = MM::g_Keyword_Metadata_CameraLabel;
    m.attr("g_Keyword_Metadata_Exposure") = MM::g_Keyword_Metadata_Exposure;
    m.attr("g_Keyword_Metadata_Height") = MM::g_Keyword_Metadata_Height;
    m.attr("g_Keyword_Metadata_ImageNumber") = MM::g_Keyword_Metadata_ImageNumber;
    m.attr("g_Keyword_Metadata_ROI_X") = MM::g_Keyword_Metadata_ROI_X;
    m.attr("g_Keyword_Metadata_ROI_Y") = MM::g_Keyword_Metadata_ROI_Y;
    m.attr("g_Keyword_Metadata_Score") = MM::g_Keyword_Metadata_Score;
    m.attr("g_Keyword_Metadata_TimeInCore") = MM::g_Keyword_Metadata_TimeInCore;
    m.attr("g_Keyword_Metadata_Width") = MM::g_Keyword_Metadata_Width;
    m.attr("g_FieldDelimiters") = MM::g_FieldDelimiters;
    m.attr("g_CFGCommand_Device") = MM::g_CFGCommand_Device;
    m.attr("g_CFGCommand_Label") = MM::g_CFGCommand_Label;
    m.attr("g_CFGCommand_Property") = MM::g_CFGCommand_Property;
    m.attr("g_CFGCommand_Configuration") = MM::g_CFGCommand_Configuration;
    m.attr("g_CFGCommand_ConfigGroup") = MM::g_CFGCommand_ConfigGroup;
    m.attr("g_CFGCommand_Equipment") = MM::g_CFGCommand_Equipment;
    m.attr("g_CFGCommand_Delay") = MM::g_CFGCommand_Delay;
    m.attr("g_CFGCommand_ImageSynchro") = MM::g_CFGCommand_ImageSynchro;
    m.attr("g_CFGCommand_ConfigPixelSize") = MM::g_CFGCommand_ConfigPixelSize;
    m.attr("g_CFGCommand_PixelSize_um") = MM::g_CFGCommand_PixelSize_um;
    m.attr("g_CFGCommand_PixelSizeAffine") = MM::g_CFGCommand_PixelSizeAffine;
    m.attr("g_CFGCommand_PixelSizedxdz") = MM::g_CFGCommand_PixelSizedxdz;
    m.attr("g_CFGCommand_PixelSizedydz") = MM::g_CFGCommand_PixelSizedydz;
    m.attr("g_CFGCommand_PixelSizeOptimalZUm") = MM::g_CFGCommand_PixelSizeOptimalZUm;
    m.attr("g_CFGCommand_ParentID") = MM::g_CFGCommand_ParentID;
    m.attr("g_CFGCommand_FocusDirection") = MM::g_CFGCommand_FocusDirection;
    m.attr("g_CFGGroup_System") = MM::g_CFGGroup_System;
    m.attr("g_CFGGroup_System_Startup") = MM::g_CFGGroup_System_Startup;
    m.attr("g_CFGGroup_System_Shutdown") = MM::g_CFGGroup_System_Shutdown;
    m.attr("g_CFGGroup_PixelSizeUm") = MM::g_CFGGroup_PixelSizeUm;

/////////////////// Enums ///////////////////

// Helper macro for SWIG compatibility attributes
#ifdef MATCH_SWIG
#define SWIG_COMPAT_ATTR(name, value) m.attr(name) = static_cast<int>(value);
#else
#define SWIG_COMPAT_ATTR(name, value)
#endif

// Macro that binds an enum value and optionally creates module attribute for SWIG compatibility
#define BIND_ENUM_VALUE(enum_obj, name, enum_value)                                            \
    enum_obj.value(name, enum_value);                                                          \
    SWIG_COMPAT_ATTR(name, enum_value)

    // DeviceType enum
    auto device_type_enum = nb::enum_<MM::DeviceType>(m, "DeviceType", nb::is_arithmetic());
    BIND_ENUM_VALUE(device_type_enum, "UnknownType", MM::DeviceType::UnknownType)
    BIND_ENUM_VALUE(device_type_enum, "AnyType", MM::DeviceType::AnyType)
    BIND_ENUM_VALUE(device_type_enum, "CameraDevice", MM::DeviceType::CameraDevice)
    BIND_ENUM_VALUE(device_type_enum, "ShutterDevice", MM::DeviceType::ShutterDevice)
    BIND_ENUM_VALUE(device_type_enum, "StateDevice", MM::DeviceType::StateDevice)
    BIND_ENUM_VALUE(device_type_enum, "StageDevice", MM::DeviceType::StageDevice)
    BIND_ENUM_VALUE(device_type_enum, "XYStageDevice", MM::DeviceType::XYStageDevice)
    BIND_ENUM_VALUE(device_type_enum, "SerialDevice", MM::DeviceType::SerialDevice)
    BIND_ENUM_VALUE(device_type_enum, "GenericDevice", MM::DeviceType::GenericDevice)
    BIND_ENUM_VALUE(device_type_enum, "AutoFocusDevice", MM::DeviceType::AutoFocusDevice)
    BIND_ENUM_VALUE(device_type_enum, "CoreDevice", MM::DeviceType::CoreDevice)
    BIND_ENUM_VALUE(device_type_enum, "ImageProcessorDevice",
                    MM::DeviceType::ImageProcessorDevice)
    BIND_ENUM_VALUE(device_type_enum, "SignalIODevice", MM::DeviceType::SignalIODevice)
    BIND_ENUM_VALUE(device_type_enum, "MagnifierDevice", MM::DeviceType::MagnifierDevice)
    BIND_ENUM_VALUE(device_type_enum, "SLMDevice", MM::DeviceType::SLMDevice)
    BIND_ENUM_VALUE(device_type_enum, "HubDevice", MM::DeviceType::HubDevice)
    BIND_ENUM_VALUE(device_type_enum, "GalvoDevice", MM::DeviceType::GalvoDevice)
    BIND_ENUM_VALUE(device_type_enum, "PressurePumpDevice", MM::DeviceType::PressurePumpDevice)
    BIND_ENUM_VALUE(device_type_enum, "VolumetricPumpDevice",
                    MM::DeviceType::VolumetricPumpDevice)

    // PropertyType enum
    auto property_type_enum =
        nb::enum_<MM::PropertyType>(m, "PropertyType", nb::is_arithmetic());
    BIND_ENUM_VALUE(property_type_enum, "Undef", MM::PropertyType::Undef)
    BIND_ENUM_VALUE(property_type_enum, "String", MM::PropertyType::String)
    BIND_ENUM_VALUE(property_type_enum, "Float", MM::PropertyType::Float)
    BIND_ENUM_VALUE(property_type_enum, "Integer", MM::PropertyType::Integer)

    // ActionType enum
    auto action_type_enum = nb::enum_<MM::ActionType>(m, "ActionType", nb::is_arithmetic());
    BIND_ENUM_VALUE(action_type_enum, "NoAction", MM::ActionType::NoAction)
    BIND_ENUM_VALUE(action_type_enum, "BeforeGet", MM::ActionType::BeforeGet)
    BIND_ENUM_VALUE(action_type_enum, "AfterSet", MM::ActionType::AfterSet)
    BIND_ENUM_VALUE(action_type_enum, "IsSequenceable", MM::ActionType::IsSequenceable)
    BIND_ENUM_VALUE(action_type_enum, "AfterLoadSequence", MM::ActionType::AfterLoadSequence)
    BIND_ENUM_VALUE(action_type_enum, "StartSequence", MM::ActionType::StartSequence)
    BIND_ENUM_VALUE(action_type_enum, "StopSequence", MM::ActionType::StopSequence)

    // PortType enum
    auto port_type_enum = nb::enum_<MM::PortType>(m, "PortType", nb::is_arithmetic());
    BIND_ENUM_VALUE(port_type_enum, "InvalidPort", MM::PortType::InvalidPort)
    BIND_ENUM_VALUE(port_type_enum, "SerialPort", MM::PortType::SerialPort)
    BIND_ENUM_VALUE(port_type_enum, "USBPort", MM::PortType::USBPort)
    BIND_ENUM_VALUE(port_type_enum, "HIDPort", MM::PortType::HIDPort)

    // FocusDirection enum
    auto focus_direction_enum =
        nb::enum_<MM::FocusDirection>(m, "FocusDirection", nb::is_arithmetic());
    BIND_ENUM_VALUE(focus_direction_enum, "FocusDirectionUnknown",
                    MM::FocusDirection::FocusDirectionUnknown)
    BIND_ENUM_VALUE(focus_direction_enum, "FocusDirectionTowardSample",
                    MM::FocusDirection::FocusDirectionTowardSample)
    BIND_ENUM_VALUE(focus_direction_enum, "FocusDirectionAwayFromSample",
                    MM::FocusDirection::FocusDirectionAwayFromSample)

    // DeviceNotification enum
    auto device_notification_enum =
        nb::enum_<MM::DeviceNotification>(m, "DeviceNotification", nb::is_arithmetic());
    BIND_ENUM_VALUE(device_notification_enum, "Attention", MM::DeviceNotification::Attention)
    BIND_ENUM_VALUE(device_notification_enum, "Done", MM::DeviceNotification::Done)
    BIND_ENUM_VALUE(device_notification_enum, "StatusChanged",
                    MM::DeviceNotification::StatusChanged)

    // DeviceDetectionStatus enum
    auto device_detection_status_enum =
        nb::enum_<MM::DeviceDetectionStatus>(m, "DeviceDetectionStatus", nb::is_arithmetic());
    BIND_ENUM_VALUE(device_detection_status_enum, "Unimplemented",
                    MM::DeviceDetectionStatus::Unimplemented)
    BIND_ENUM_VALUE(device_detection_status_enum, "Misconfigured",
                    MM::DeviceDetectionStatus::Misconfigured)
    BIND_ENUM_VALUE(device_detection_status_enum, "CanNotCommunicate",
                    MM::DeviceDetectionStatus::CanNotCommunicate)
    BIND_ENUM_VALUE(device_detection_status_enum, "CanCommunicate",
                    MM::DeviceDetectionStatus::CanCommunicate)

    // DeviceInitializationState enum
    auto device_initialization_state_enum = nb::enum_<DeviceInitializationState>(
        m, "DeviceInitializationState", nb::is_arithmetic());
    BIND_ENUM_VALUE(device_initialization_state_enum, "Uninitialized",
                    DeviceInitializationState::Uninitialized)
    BIND_ENUM_VALUE(device_initialization_state_enum, "InitializedSuccessfully",
                    DeviceInitializationState::InitializedSuccessfully)
    BIND_ENUM_VALUE(device_initialization_state_enum, "InitializationFailed",
                    DeviceInitializationState::InitializationFailed)

// Clean up the macros
#undef BIND_ENUM_VALUE
#undef SWIG_COMPAT_ATTR

    //////////////////// Supporting classes ////////////////////

    nb::class_<Configuration>(m, "Configuration", R"doc(
Encapsulation of  configuration information.


A configuration is a collection of device property settings.
)doc")
        .def(nb::init<>())
        .def("addSetting", &Configuration::addSetting, "setting"_a)
        .def("deleteSetting", &Configuration::deleteSetting, "device"_a, "property"_a)
        .def("isPropertyIncluded", &Configuration::isPropertyIncluded, "device"_a, "property"_a)
        .def("isConfigurationIncluded", &Configuration::isConfigurationIncluded, "cfg"_a)
        .def("isSettingIncluded", &Configuration::isSettingIncluded, "setting"_a)
        .def("getSetting", nb::overload_cast<size_t>(&Configuration::getSetting, nb::const_),
             "index"_a)
        .def("getSetting",
             nb::overload_cast<const char *, const char *>(&Configuration::getSetting),
             "device"_a, "property"_a)
        .def("size", &Configuration::size)
        .def("getVerbose", &Configuration::getVerbose);

    nb::class_<PropertySetting>(m, "PropertySetting")
        .def(nb::init<const char *, const char *, const char *, bool>(), "deviceLabel"_a,
             "prop"_a, "value"_a, "readOnly"_a = false,
             "Constructor specifying the entire contents")
        .def(nb::init<>(), "Default constructor")
        .def("getDeviceLabel", &PropertySetting::getDeviceLabel, "Returns the device label")
        .def("getPropertyName", &PropertySetting::getPropertyName, "Returns the property name")
        .def("getReadOnly", &PropertySetting::getReadOnly, "Returns the read-only status")
        .def("getPropertyValue", &PropertySetting::getPropertyValue,
             "Returns the property value")
        .def("getKey", &PropertySetting::getKey, "Returns the unique key")
        .def("getVerbose", &PropertySetting::getVerbose, "Returns a verbose description")
        .def("isEqualTo", &PropertySetting::isEqualTo, "other"_a,
             "Checks if this property setting is equal to another")
        .def_static("generateKey", &PropertySetting::generateKey, "device"_a, "prop"_a,
                    "Generates a unique key based on device and property");

    nb::class_<Metadata>(m, "Metadata")
        .def(nb::init<>(), "Empty constructor")
        .def(nb::init<const Metadata &>(), "Copy constructor")
        // Member functions
        .def("Clear", &Metadata::Clear, "Clears all tags")
        .def("GetKeys", &Metadata::GetKeys, "Returns all tag keys")
        .def("HasTag", &Metadata::HasTag, "key"_a, "Checks if a tag exists for the given key")
        .def("GetSingleTag", &Metadata::GetSingleTag, "key"_a, "Gets a single tag by key")
        .def("GetArrayTag", &Metadata::GetArrayTag, "key"_a, "Gets an array tag by key")
        .def("SetTag", &Metadata::SetTag, "tag"_a, "Sets a tag")
        .def("RemoveTag", &Metadata::RemoveTag, "key"_a, "Removes a tag by key")
        .def("Merge", &Metadata::Merge, "newTags"_a, "Merges new tags into the metadata")
        .def("Serialize", &Metadata::Serialize, "Serializes the metadata")
        .def("Restore", &Metadata::Restore, "stream"_a,
             "Restores metadata from a serialized string")
        .def("Dump", &Metadata::Dump, "Dumps metadata in human-readable format")
        // Template methods (bound using lambdas due to C++ template limitations
        // in bindings)
        .def(
            "PutTag",
            [](Metadata &self, const std::string &key, const std::string &deviceLabel,
               const std::string &value) { self.PutTag(key, deviceLabel, value); },
            "key"_a, "deviceLabel"_a, "value"_a, "Adds a MetadataSingleTag")

        .def(
            "PutImageTag",
            [](Metadata &self, const std::string &key, const std::string &value) {
                self.PutImageTag(key, value);
            },
            "key"_a, "value"_a, "Adds an image tag")
        // MutableMapping Methods:
        .def("__getitem__",
             [](Metadata &self, const std::string &key) {
                 MetadataSingleTag tag = self.GetSingleTag(key.c_str());
                 return tag.GetValue();
             })
        .def("__setitem__",
             [](Metadata &self, const std::string &key, const std::string &value) {
                 MetadataSingleTag tag(key.c_str(), "__", false);
                 tag.SetValue(value.c_str());
                 self.SetTag(tag);
             })
        .def("__delitem__", &Metadata::RemoveTag);
    //  .def("__iter__",
    //       [m](Metadata &self) {
    //         StrVec keys = self.GetKeys();
    //         return nb::make_iterator(m, "keys_iterator", keys);
    //       },  nb::keep_alive<0, 1>())

    nb::class_<MetadataTag>(m, "MetadataTag")
        // MetadataTag is Abstract ... no constructors
        // Member functions
        .def("GetDevice", &MetadataTag::GetDevice, "Returns the device label")
        .def("GetName", &MetadataTag::GetName, "Returns the name of the tag")
        .def("GetQualifiedName", &MetadataTag::GetQualifiedName, "Returns the qualified name")
        .def("IsReadOnly", &MetadataTag::IsReadOnly, "Checks if the tag is read-only")
        .def("SetDevice", &MetadataTag::SetDevice, "device"_a, "Sets the device label")
        .def("SetName", &MetadataTag::SetName, "name"_a, "Sets the name of the tag")
        .def("SetReadOnly", &MetadataTag::SetReadOnly, "readOnly"_a,
             "Sets the read-only status")
        // Virtual functions
        .def("ToSingleTag", &MetadataTag::ToSingleTag,
             "Converts to MetadataSingleTag if applicable")
        .def("ToArrayTag", &MetadataTag::ToArrayTag,
             "Converts to MetadataArrayTag if applicable")
        .def("Clone", &MetadataTag::Clone, "Creates a clone of the MetadataTag")
        .def("Serialize", &MetadataTag::Serialize, "Serializes the MetadataTag to a string")
        .def("Restore", nb::overload_cast<const char *>(&MetadataTag::Restore), "stream"_a,
             "Restores from a serialized string");
    // Ommitting the std::istringstream& overload: Python doesn't have a
    // stringstream equivalent
    //  .def("Restore",
    //  nb::overload_cast<std::istringstream&>(&MetadataTag::Restore),
    //  "istream"_a,
    //       "Restores from an input stream")
    // Static methods
    //  .def_static("ReadLine", &MetadataTag::ReadLine, "istream"_a,
    //    "Reads a line from an input stream");

    nb::class_<MetadataSingleTag, MetadataTag>(m, "MetadataSingleTag")
        .def(nb::init<>(), "Default constructor")
        .def(nb::init<const char *, const char *, bool>(), "name"_a, "device"_a, "readOnly"_a,
             "Parameterized constructor")
        // Member functions
        .def("GetValue", &MetadataSingleTag::GetValue, "Returns the value")
        .def("SetValue", &MetadataSingleTag::SetValue, "val"_a, "Sets the value")
        .def("ToSingleTag", &MetadataSingleTag::ToSingleTag,
             "Returns this object as MetadataSingleTag")
        .def("Clone", &MetadataSingleTag::Clone, "Clones this tag")
        .def("Serialize", &MetadataSingleTag::Serialize, "Serializes this tag to a string")
        // Omitting the std::istringstream& overload: Python doesn't have a
        // stringstream equivalent
        //  .def("Restore",
        //  nb::overload_cast<std::istringstream&>(&MetadataSingleTag::Restore),
        //  "istream"_a, "Restores from an input stream")
        .def("Restore", nb::overload_cast<const char *>(&MetadataSingleTag::Restore),
             "stream"_a, "Restores from a serialized string");

    nb::class_<MetadataArrayTag, MetadataTag>(m, "MetadataArrayTag")
        .def(nb::init<>(), "Default constructor")
        .def(nb::init<const char *, const char *, bool>(), "name"_a, "device"_a, "readOnly"_a,
             "Parameterized constructor")
        .def("ToArrayTag", &MetadataArrayTag::ToArrayTag,
             "Returns this object as MetadataArrayTag")
        .def("AddValue", &MetadataArrayTag::AddValue, "val"_a, "Adds a value to the array")
        .def("SetValue", &MetadataArrayTag::SetValue, "val"_a, "idx"_a,
             "Sets a value at a specific index")
        .def("GetValue", &MetadataArrayTag::GetValue, "idx"_a,
             "Gets a value at a specific index")
        .def("GetSize", &MetadataArrayTag::GetSize, "Returns the size of the array")
        .def("Clone", &MetadataArrayTag::Clone, "Clones this tag")
        .def("Serialize", &MetadataArrayTag::Serialize, "Serializes this tag to a string")
        // Omitting the std::istringstream& overload: Python doesn't have a
        // stringstream equivalent
        //  .def("Restore",
        //  nb::overload_cast<std::istringstream&>(&MetadataArrayTag::Restore),
        //       "istream"_a, "Restores from an input stream")
        .def("Restore", nb::overload_cast<const char *>(&MetadataArrayTag::Restore), "stream"_a,
             "Restores from a serialized string");

    nb::class_<MMEventCallback, PyMMEventCallback>(m, "MMEventCallback", R"doc(
Interface for receiving events from MMCore.


Use by passing an instance to [`CMMCore.registerCallback`][pymmcore_nano.CMMCore.registerCallback].
)doc")
        .def(nb::init<>())

        // Virtual methods
        .def("onPropertiesChanged", &MMEventCallback::onPropertiesChanged,
             "Called when properties are changed")
        .def("onPropertyChanged", &MMEventCallback::onPropertyChanged, "name"_a, "propName"_a,
             "propValue"_a, "Called when a specific property is changed")
        .def("onChannelGroupChanged", &MMEventCallback::onChannelGroupChanged,
             "newChannelGroupName"_a, "Called when the channel group changes")
        .def("onConfigGroupChanged", &MMEventCallback::onConfigGroupChanged, "groupName"_a,
             "newConfigName"_a, "Called when a configuration group changes")
        .def("onSystemConfigurationLoaded", &MMEventCallback::onSystemConfigurationLoaded,
             "Called when the system configuration is loaded")
        .def("onPixelSizeChanged", &MMEventCallback::onPixelSizeChanged, "newPixelSizeUm"_a,
             "Called when the pixel size changes")
        .def("onPixelSizeAffineChanged", &MMEventCallback::onPixelSizeAffineChanged, "v0"_a,
             "v1"_a, "v2"_a, "v3"_a, "v4"_a, "v5"_a,
             "Called when the pixel size affine transformation changes")
        // These bindings are ugly lambda workarounds because the original methods
        // take char* instead of const char*
        // https://github.com/micro-manager/mmCoreAndDevices/pull/530
        .def(
            "onSLMExposureChanged",
            [](MMEventCallback &self, const std::string &name, double newExposure) {
                self.onSLMExposureChanged(const_cast<char *>(name.c_str()), newExposure);
            },
            "name"_a, "newExposure"_a)
        .def(
            "onExposureChanged",
            [&](MMEventCallback &self, const std::string &name, double newExposure) {
                self.onExposureChanged(const_cast<char *>(name.c_str()), newExposure);
            },
            "name"_a, "newExposure"_a)
        .def(
            "onStagePositionChanged",
            [&](MMEventCallback &self, const std::string &name, double pos) {
                self.onStagePositionChanged(const_cast<char *>(name.c_str()), pos);
            },
            "name"_a, "pos"_a)
        .def(
            "onXYStagePositionChanged",
            [&](MMEventCallback &self, const std::string &name, double xpos, double ypos) {
                self.onXYStagePositionChanged(const_cast<char *>(name.c_str()), xpos, ypos);
            },
            "name"_a, "xpos"_a, "ypos"_a)
        .def(
            "onImageSnapped",
            [&](MMEventCallback &self, const std::string &cameraLabel) {
                self.onImageSnapped(const_cast<char *>(cameraLabel.c_str()));
            },
            "cameraLabel"_a, "Called when an image is snapped")
        .def(
            "onSequenceAcquisitionStarted",
            [&](MMEventCallback &self, const std::string &cameraLabel) {
                self.onSequenceAcquisitionStarted(const_cast<char *>(cameraLabel.c_str()));
            },
            "cameraLabel"_a, "Called when sequence acquisition starts")
        .def(
            "onSequenceAcquisitionStopped",
            [&](MMEventCallback &self, const std::string &cameraLabel) {
                self.onSequenceAcquisitionStopped(const_cast<char *>(cameraLabel.c_str()));
            },
            "cameraLabel"_a, "Called when sequence acquisition stops");

    //////////////////// Exceptions ////////////////////

    // Register the exception with RuntimeError as the base
    // NOTE:
    // at the moment, we're not exposing all of the methods on the CMMErrors class
    // because this is far simpler... but we could expose more if needed
    // this will expose pymmcore_nano.CMMErrors as a subclass of RuntimeError
    // and a basic message will be propagated, for example:
    // CMMError('Failed to load device "SomeDevice" from adapter module
    // "SomeModule"')
    nb::exception<CMMError>(m, "CMMError", PyExc_RuntimeError);
    nb::exception<MetadataKeyError>(m, "MetadataKeyError", PyExc_KeyError);
    nb::exception<MetadataIndexError>(m, "MetadataIndexError", PyExc_IndexError);

    //////////////////// MMCore ////////////////////

    nb::class_<CMMCore>(m, "CMMCore", R"doc(
The main MMCore object.


Manages multiple device adapters. Provides a device-independent interface for hardware control.
Additionally, provides some facilities (such as configuration groups) for application
programming.
)doc")
        .def(nb::init<>())
        .def(
            "loadSystemConfiguration",
            // accept any object that can be cast to a string (e.g. Path)
            [](CMMCore &self, nb::object fileName) {
                self.loadSystemConfiguration(nb::str(fileName).c_str());
            },
            "fileName"_a, "Loads a system configuration from a file.")
        .def("saveSystemConfiguration", &CMMCore::saveSystemConfiguration, "fileName"_a, "Saves the current system configuration to a text file of the MM specific format. The configuration file records only the information essential to the hardware setup: devices, labels, pre-initialization properties, and configurations. The file format is the same as for the system state." RGIL)
        .def_static("enableFeature", &CMMCore::enableFeature, "name"_a, "enable"_a RGIL)
        .def_static("isFeatureEnabled", &CMMCore::isFeatureEnabled, "name"_a RGIL)
        .def_static("getMMCoreVersionMajor", &CMMCore::getMMCoreVersionMajor RGIL)
        .def_static("getMMCoreVersionMinor", &CMMCore::getMMCoreVersionMinor RGIL)
        .def_static("getMMCoreVersionPatch", &CMMCore::getMMCoreVersionPatch RGIL)
        .def_static("getMMDeviceModuleInterfaceVersion", &CMMCore::getMMDeviceModuleInterfaceVersion RGIL)
        .def_static("getMMDeviceDeviceInterfaceVersion", &CMMCore::getMMDeviceDeviceInterfaceVersion RGIL)
        .def("loadDevice", &CMMCore::loadDevice, "label"_a, "moduleName"_a, "deviceName"_a, "Loads a device from the plugin library." RGIL)
        .def("unloadDevice", &CMMCore::unloadDevice, "label"_a, "Unloads the device from the core and adjusts all configuration data." RGIL)
        .def("unloadAllDevices", &CMMCore::unloadAllDevices)
        .def("initializeAllDevices", &CMMCore::initializeAllDevices, "Calls Initialize() method for each loaded device. Parallel implemnetation should be faster" RGIL)
        .def("initializeDevice", &CMMCore::initializeDevice, "label"_a RGIL)
        .def("getDeviceInitializationState", &CMMCore::getDeviceInitializationState, "label"_a, "Queries the initialization state of the given device." RGIL)
        .def("reset", &CMMCore::reset, "Unloads all devices from the core, clears all configuration data." RGIL)
        .def("unloadLibrary", &CMMCore::unloadLibrary, "moduleName"_a, "Forcefully unload a library. Experimental. Don't use." RGIL)
        .def("updateCoreProperties", &CMMCore::updateCoreProperties, "Updates CoreProperties (currently all Core properties are devices types) with the loaded hardware. After this call, each of the Core-Device properties will be populated with the currently loaded devices of that type" RGIL)
        .def("getCoreErrorText", &CMMCore::getCoreErrorText, "code"_a, "Returns a pre-defined error test with the given error code" RGIL)
        .def("getVersionInfo", &CMMCore::getVersionInfo RGIL)
        .def("getAPIVersionInfo", &CMMCore::getAPIVersionInfo, "Returns the module and device interface versions." RGIL)
        .def("getSystemState", &CMMCore::getSystemState, "Returns the entire system state, i.e. the collection of all property values from all devices." RGIL)
        .def("setSystemState", &CMMCore::setSystemState, "conf"_a, "Sets all properties contained in the Configuration object. The procedure will attempt to set each property it encounters, but won't stop if any of the properties fail or if the requested device is not present. It will just quietly continue." RGIL)
        .def("getConfigState", &CMMCore::getConfigState, "group"_a, "config"_a, "Returns a partial state of the system, only for devices included in the specified configuration." RGIL)
        .def("getConfigGroupState",
             nb::overload_cast<const char *>(&CMMCore::getConfigGroupState),
             "group"_a RGIL)
        .def("saveSystemState", &CMMCore::saveSystemState, "fileName"_a, "Saves the current system state to a text file of the MM specific format. The file records only read-write properties. The file format is directly readable by the complementary loadSystemState() command." RGIL)
        .def("loadSystemState", &CMMCore::loadSystemState, "fileName"_a, "Loads the system configuration from the text file conforming to the MM specific format. The configuration contains a list of commands to build the desired system state from read-write properties." RGIL)
        .def("registerCallback", &CMMCore::registerCallback, R"doc(Register a callback (listener class).


MMCore will send notifications on internal events using this interface
          )doc", nb::arg("cb").none() RGIL)
        .def(
            "setPrimaryLogFile",
            // accept any object that can be cast to a string (e.g. Path)
            [](CMMCore &self, nb::object filename, bool truncate) {
                // convert to string
                self.setPrimaryLogFile(nb::str(filename).c_str(), truncate);
            },
            "filename"_a,
            "truncate"_a = false )

        .def("getPrimaryLogFile", &CMMCore::getPrimaryLogFile, "Return the name of the primary Core log file." RGIL)
        .def("logMessage", nb::overload_cast<const char *>(&CMMCore::logMessage), "msg"_a RGIL)
        .def("logMessage",
             nb::overload_cast<const char *, bool>(&CMMCore::logMessage),
             "msg"_a,
             "debugOnly"_a RGIL)

        .def("enableDebugLog", &CMMCore::enableDebugLog, "enable"_a, "Enable or disable logging of debug messages." RGIL)
        .def("debugLogEnabled", &CMMCore::debugLogEnabled, "Indicates if logging of debug messages is enabled" RGIL)
        .def("enableStderrLog", &CMMCore::enableStderrLog, "enable"_a, "Enables or disables log message display on the standard console." RGIL)
        .def("stderrLogEnabled", &CMMCore::stderrLogEnabled, "Indicates whether logging output goes to stdErr" RGIL)
        .def(
            "startSecondaryLogFile",
            // accept any object that can be cast to a string (e.g. Path)
            [](CMMCore &self,
               nb::object filename,
               bool enableDebug,
               bool truncate,
               bool synchronous) {
                return self.startSecondaryLogFile(nb::str(filename).c_str(), enableDebug,
                                                  truncate, synchronous);
            },
            "filename"_a,
            "enableDebug"_a,
            "truncate"_a = true,
            "synchronous"_a = false )
        .def("stopSecondaryLogFile", &CMMCore::stopSecondaryLogFile, "handle"_a, "Stop capturing logging output into an additional file." RGIL)

        .def("getDeviceAdapterSearchPaths", &CMMCore::getDeviceAdapterSearchPaths, "Return the current device adapter search paths." RGIL)
        .def("setDeviceAdapterSearchPaths", &CMMCore::setDeviceAdapterSearchPaths, "paths"_a, "Set the device adapter search paths." RGIL)
        .def("getDeviceAdapterNames", &CMMCore::getDeviceAdapterNames, "Return the names of discoverable device adapters." RGIL)
        .def("getAvailableDevices", &CMMCore::getAvailableDevices, "library"_a, "Get available devices from the specified device library." RGIL)
        .def("getAvailableDeviceDescriptions",
             &CMMCore::getAvailableDeviceDescriptions,
             "library"_a, "Get descriptions for available devices from the specified library." RGIL)
        .def("getAvailableDeviceTypes", &CMMCore::getAvailableDeviceTypes, "library"_a, "Get type information for available devices from the specified library." RGIL)
        .def("getLoadedDevices", &CMMCore::getLoadedDevices, "Returns an array of labels for currently loaded devices." RGIL)
        .def("getLoadedDevicesOfType", &CMMCore::getLoadedDevicesOfType, "devType"_a, "Returns an array of labels for currently loaded devices of specific type." RGIL)
        .def("getDeviceType", &CMMCore::getDeviceType, "label"_a RGIL)
        .def("getDeviceLibrary", &CMMCore::getDeviceLibrary, "label"_a, "Returns device library (aka module, device adapter) name." RGIL)
        .def("getDeviceName",
             nb::overload_cast<const char *>(&CMMCore::getDeviceName),
             "label"_a RGIL)
        .def("getDeviceDescription", &CMMCore::getDeviceDescription, "label"_a, "Returns description text for a given device label. \"Description\" is determined by the library and is immutable." RGIL)
        .def("getDevicePropertyNames", &CMMCore::getDevicePropertyNames, "label"_a, "Returns all property names supported by the device." RGIL)
        .def("hasProperty", &CMMCore::hasProperty, "label"_a, "propName"_a, "Checks if device has a property with a specified name. The exception will be thrown in case device label is not defined." RGIL)
        .def("getProperty", &CMMCore::getProperty, "label"_a, "propName"_a, "Returns the property value for the specified device." RGIL)
        .def("setProperty",
             nb::overload_cast<const char *, const char *, const char *>(&CMMCore::setProperty),
             "label"_a,
             "propName"_a,
             "propValue"_a RGIL)
        .def("setProperty",
             nb::overload_cast<const char *, const char *, bool>(&CMMCore::setProperty),
             "label"_a,
             "propName"_a,
             "propValue"_a RGIL)
        .def("setProperty",
             nb::overload_cast<const char *, const char *, long>(&CMMCore::setProperty),
             "label"_a,
             "propName"_a,
             "propValue"_a RGIL)
        .def("setProperty",
             nb::overload_cast<const char *, const char *, float>(&CMMCore::setProperty),
             "label"_a,
             "propName"_a,
             "propValue"_a RGIL)
        .def("getAllowedPropertyValues",
             &CMMCore::getAllowedPropertyValues,
             "label"_a,
             "propName"_a, "Returns all valid values for the specified property. If the array is empty it means that there are no restrictions for values. However, even if all values are allowed it is not guaranteed that all of them will be actually accepted by the device at run time." RGIL)
        .def("isPropertyReadOnly", &CMMCore::isPropertyReadOnly, "label"_a, "propName"_a, "Tells us whether the property can be modified." RGIL)
        .def("isPropertyPreInit", &CMMCore::isPropertyPreInit, "label"_a, "propName"_a, "Tells us whether the property must be defined prior to initialization." RGIL)
        .def(
            "isPropertySequenceable", &CMMCore::isPropertySequenceable, "label"_a, "propName"_a, "Queries device if the specified property can be used in a sequence" RGIL)
        .def("hasPropertyLimits", &CMMCore::hasPropertyLimits, "label"_a, "propName"_a, "Queries device if the specific property has limits." RGIL)
        .def("getPropertyLowerLimit", &CMMCore::getPropertyLowerLimit, "label"_a, "propName"_a, "Returns the property lower limit value, if the property has limits - 0 otherwise." RGIL)
        .def("getPropertyUpperLimit", &CMMCore::getPropertyUpperLimit, "label"_a, "propName"_a, "Returns the property upper limit value, if the property has limits - 0 otherwise." RGIL)
        .def("getPropertyType", &CMMCore::getPropertyType, "label"_a, "propName"_a, "Returns the intrinsic property type." RGIL)
        .def("startPropertySequence", &CMMCore::startPropertySequence, "label"_a, "propName"_a, "Starts an ongoing sequence of triggered events in a property of a device This should only be called for device-properties that are sequenceable" RGIL)
        .def("stopPropertySequence", &CMMCore::stopPropertySequence, "label"_a, "propName"_a, "Stops an ongoing sequence of triggered events in a property of a device This should only be called for device-properties that are sequenceable" RGIL)
        .def("getPropertySequenceMaxLength",
             &CMMCore::getPropertySequenceMaxLength,
             "label"_a,
             "propName"_a, "Queries device property for the maximum number of events that can be put in a sequence" RGIL)
        .def("loadPropertySequence",
             &CMMCore::loadPropertySequence,
             "label"_a,
             "propName"_a,
             "eventSequence"_a, "Transfer a sequence of events/states/whatever to the device This should only be called for device-properties that are sequenceable" RGIL)
        .def("deviceBusy", &CMMCore::deviceBusy, "label"_a, "Checks the busy status of the specific device." RGIL)
        .def("waitForDevice",
             nb::overload_cast<const char *>(&CMMCore::waitForDevice),
             "label"_a RGIL)
        .def("waitForConfig", &CMMCore::waitForConfig, "group"_a, "configName"_a, "Blocks until all devices included in the configuration become ready." RGIL)
        .def("systemBusy", &CMMCore::systemBusy, "Checks the busy status of the entire system. The system will report busy if any of the devices is busy." RGIL)
        .def("waitForSystem", &CMMCore::waitForSystem, "Blocks until all devices in the system become ready (not-busy)." RGIL)
        .def("deviceTypeBusy", &CMMCore::deviceTypeBusy, "devType"_a, "Checks the busy status for all devices of the specific type. The system will report busy if any of the devices of the specified type are busy." RGIL)
        .def("waitForDeviceType", &CMMCore::waitForDeviceType, "devType"_a, "Blocks until all devices of the specific type become ready (not-busy)." RGIL)
        .def("getDeviceDelayMs", &CMMCore::getDeviceDelayMs, "label"_a, "Reports action delay in milliseconds for the specific device. The delay is used in the synchronization process to ensure that the action is performed, without polling. Value of \"0\" means that action is either blocking or that polling of device status is required. Some devices ignore this setting." RGIL)
        .def("setDeviceDelayMs", &CMMCore::setDeviceDelayMs, "label"_a, "delayMs"_a, "Overrides the built-in value for the action delay. Some devices ignore this setting." RGIL)
        .def("usesDeviceDelay", &CMMCore::usesDeviceDelay, "label"_a, "Signals if the device will use the delay setting or not." RGIL)
        .def("setTimeoutMs", &CMMCore::setTimeoutMs, "timeoutMs"_a RGIL)
        .def("getTimeoutMs", &CMMCore::getTimeoutMs RGIL)
        .def("sleep", &CMMCore::sleep, "intervalMs"_a, "Waits (blocks the calling thread) for specified time in milliseconds." RGIL)

        .def("getCameraDevice", &CMMCore::getCameraDevice, "Returns the label of the currently selected camera device." RGIL)
        .def("getShutterDevice", &CMMCore::getShutterDevice, "Returns the label of the currently selected shutter device." RGIL)
        .def("getFocusDevice", &CMMCore::getFocusDevice, "Returns the label of the currently selected focus device." RGIL)
        .def("getXYStageDevice", &CMMCore::getXYStageDevice, "Returns the label of the currently selected XYStage device." RGIL)
        .def("getAutoFocusDevice", &CMMCore::getAutoFocusDevice, "Returns the label of the currently selected auto-focus device." RGIL)
        .def("getImageProcessorDevice", &CMMCore::getImageProcessorDevice, "Returns the label of the currently selected image processor device." RGIL)
        .def("getSLMDevice", &CMMCore::getSLMDevice, "Returns the label of the currently selected SLM device." RGIL)
        .def("getGalvoDevice", &CMMCore::getGalvoDevice, "Returns the label of the currently selected Galvo device." RGIL)
        .def("getChannelGroup", &CMMCore::getChannelGroup, "Returns the group determining the channel selection." RGIL)
        .def("setCameraDevice", &CMMCore::setCameraDevice, "cameraLabel"_a, "Sets the current camera device." RGIL)
        .def("setShutterDevice", &CMMCore::setShutterDevice, "shutterLabel"_a, "Sets the current shutter device." RGIL)
        .def("setFocusDevice", &CMMCore::setFocusDevice, "focusLabel"_a, "Sets the current focus device." RGIL)
        .def("setXYStageDevice", &CMMCore::setXYStageDevice, "xyStageLabel"_a, "Sets the current XY device." RGIL)
        .def("setAutoFocusDevice", &CMMCore::setAutoFocusDevice, "focusLabel"_a, "Sets the current auto-focus device." RGIL)
        .def("setImageProcessorDevice", &CMMCore::setImageProcessorDevice, "procLabel"_a, "Sets the current image processor device." RGIL)
        .def("setSLMDevice", &CMMCore::setSLMDevice, "slmLabel"_a, "Sets the current slm device." RGIL)
        .def("setGalvoDevice", &CMMCore::setGalvoDevice, "galvoLabel"_a, "Sets the current galvo device." RGIL)
        .def("setChannelGroup", &CMMCore::setChannelGroup, "channelGroup"_a, "Specifies the group determining the channel selection." RGIL)

        .def("getSystemStateCache", &CMMCore::getSystemStateCache, "Returns the entire system state, i.e. the collection of all property values from all devices. This method will return cached values instead of querying each device" RGIL)
        .def("updateSystemStateCache", &CMMCore::updateSystemStateCache, "Updates the state of the entire hardware." RGIL)
        .def("getPropertyFromCache",
             &CMMCore::getPropertyFromCache,
             "deviceLabel"_a,
             "propName"_a, "Returns the cached property value for the specified device." RGIL)
        .def("getCurrentConfigFromCache", &CMMCore::getCurrentConfigFromCache, "groupName"_a, "Returns the configuration for a given group based on the data in the cache. An empty string is a valid return value, since the system state will not always correspond to any of the defined configurations. Also, in general it is possible that the system state fits multiple configurations. This method will return only the first matching configuration, if any." RGIL)
        .def("getConfigGroupStateFromCache", &CMMCore::getConfigGroupStateFromCache, "group"_a, "Returns the partial state of the system cache, only for the devices included in the specified group. It will create a union of all devices referenced in a group." RGIL)

        .def("defineConfig",
             nb::overload_cast<const char *, const char *>(&CMMCore::defineConfig ),
             "groupName"_a,
             "configName"_a RGIL)
        .def("defineConfig",
             nb::overload_cast<const char *,
                               const char *,
                               const char *,
                               const char *,
                               const char *>(&CMMCore::defineConfig),
             "groupName"_a,
             "configName"_a,
             "deviceLabel"_a,
             "propName"_a,
             "value"_a RGIL)
        .def("defineConfigGroup", &CMMCore::defineConfigGroup, "groupName"_a, "Creates an empty configuration group." RGIL)
        .def("deleteConfigGroup", &CMMCore::deleteConfigGroup, "groupName"_a, "Deletes an entire configuration group." RGIL)
        .def("renameConfigGroup",
             &CMMCore::renameConfigGroup,
             "oldGroupName"_a,
             "newGroupName"_a, "Renames a configuration group." RGIL)
        .def("isGroupDefined", &CMMCore::isGroupDefined, "groupName"_a, "Checks if the group already exists." RGIL)
        .def("isConfigDefined", &CMMCore::isConfigDefined, "groupName"_a, "configName"_a, "Checks if the configuration already exists within a group." RGIL)
        .def("setConfig", &CMMCore::setConfig, "groupName"_a, "configName"_a, "Applies a configuration to a group. The command will fail if the configuration was not previously defined." RGIL)

        .def("deleteConfig",
             nb::overload_cast<const char *, const char *>(&CMMCore::deleteConfig),
             "groupName"_a,
             "configName"_a RGIL)
        .def("deleteConfig",
             nb::overload_cast<const char *, const char *, const char *, const char *>(
                 &CMMCore::deleteConfig),
             "groupName"_a,
             "configName"_a,
             "deviceLabel"_a,
             "propName"_a RGIL)

        .def("renameConfig",
             &CMMCore::renameConfig,
             "groupName"_a,
             "oldConfigName"_a,
             "newConfigName"_a, "Renames a configuration within a specified group. The command will fail if the configuration was not previously defined." RGIL)
        .def("getAvailableConfigGroups", &CMMCore::getAvailableConfigGroups, "Returns the names of all defined configuration groups" RGIL)
        .def("getAvailableConfigs", &CMMCore::getAvailableConfigs, "configGroup"_a, "Returns all defined configuration names in a given group" RGIL)
        .def("getCurrentConfig", &CMMCore::getCurrentConfig, "groupName"_a, "Returns the current configuration for a given group. An empty string is a valid return value, since the system state will not always correspond to any of the defined configurations. Also, in general it is possible that the system state fits multiple configurations. This method will return only the first matching configuration, if any." RGIL)
        .def("getConfigData", &CMMCore::getConfigData, "configGroup"_a, "configName"_a, "Returns the configuration object for a given group and name." RGIL)

        .def("getCurrentPixelSizeConfig",
             nb::overload_cast<>(&CMMCore::getCurrentPixelSizeConfig) RGIL)
        .def("getCurrentPixelSizeConfig",
             nb::overload_cast<bool>(&CMMCore::getCurrentPixelSizeConfig),
             "cached"_a RGIL)
        .def("getPixelSizeUm", nb::overload_cast<>(&CMMCore::getPixelSizeUm) RGIL)
        .def("getPixelSizeUm", nb::overload_cast<bool>(&CMMCore::getPixelSizeUm), "cached"_a RGIL)
        .def("getPixelSizeUmByID", &CMMCore::getPixelSizeUmByID, "resolutionID"_a, "Returns the pixel size in um for the requested pixel size group" RGIL)
        .def("getPixelSizeAffine", nb::overload_cast<>(&CMMCore::getPixelSizeAffine) RGIL)
        .def("getPixelSizeAffine",
             nb::overload_cast<bool>(&CMMCore::getPixelSizeAffine),
             "cached"_a RGIL)
        .def("getPixelSizeAffineByID", &CMMCore::getPixelSizeAffineByID, "resolutionID"_a, "Returns the Affine Transform to related camera pixels with stage movement for the requested pixel size group The raw affine transform without correction for binning and magnification will be returned." RGIL)

        .def("getPixelSizedxdz", nb::overload_cast<>(&CMMCore::getPixelSizedxdz) RGIL)
        .def("getPixelSizedxdz", nb::overload_cast<bool>(&CMMCore::getPixelSizedxdz), "cached"_a RGIL)
        .def("getPixelSizedxdz", nb::overload_cast<const char*>(&CMMCore::getPixelSizedxdz), "resolutionID"_a RGIL)
        .def("getPixelSizedydz", nb::overload_cast<>(&CMMCore::getPixelSizedydz) RGIL)
        .def("getPixelSizedydz", nb::overload_cast<bool>(&CMMCore::getPixelSizedydz), "cached"_a RGIL)
        .def("getPixelSizedydz", nb::overload_cast<const char*>(&CMMCore::getPixelSizedydz), "resolutionID"_a RGIL)
        .def("getPixelSizeOptimalZUm", nb::overload_cast<>(&CMMCore::getPixelSizeOptimalZUm) RGIL)
        .def("getPixelSizeOptimalZUm", nb::overload_cast<bool>(&CMMCore::getPixelSizeOptimalZUm), "cached"_a RGIL)
        .def("getPixelSizeOptimalZUm", nb::overload_cast<const char*>(&CMMCore::getPixelSizeOptimalZUm), "resolutionID"_a RGIL)
        .def("setPixelSizedxdz", &CMMCore::setPixelSizedxdz, "resolutionID"_a, "dXdZ"_a, "Sets the angle between the camera's x axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in x caused by a translation in z, i.e. dx / dz). \n This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). \n See: https://github.com/micro-manager/micro-manager/issues/1984" RGIL)
        .def("setPixelSizedydz", &CMMCore::setPixelSizedydz, "resolutionID"_a, "dYdZ"_a, "Sets the angle between the camera's y axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in y caused by a translation in z, i.e. dy / dz). \n This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). \n See: https://github.com/micro-manager/micro-manager/issues/1984" RGIL)
        .def("setPixelSizeOptimalZUm", &CMMCore::setPixelSizeOptimalZUm, "resolutionID"_a, "optimalZ"_a, "Sets the opimal Z stepSize (in microns). There is no magic here, this number is provided by the person configuring the microscope, to be used by the person using the microscope." RGIL)

        .def("getMagnificationFactor", &CMMCore::getMagnificationFactor, "Returns the product of all Magnifiers in the system or 1.0 when none is found This is used internally by GetPixelSizeUm" RGIL)
        .def("setPixelSizeUm", &CMMCore::setPixelSizeUm, "resolutionID"_a, "pixSize"_a, "Sets pixel size in microns for the specified resolution sensing configuration preset." RGIL)
        .def("setPixelSizeAffine", &CMMCore::setPixelSizeAffine, "resolutionID"_a, "affine"_a, "Sets the raw affine transform for the specific pixel size configuration The affine transform consists of the first two rows of a 3x3 matrix, the third row is alsways assumed to be 0.0 0.0 1.0. The transform should be valid for binning 1 and no magnification device (as given by the getMagnification() function). Order: row[0]col[0] row[0]c[1] row[0]c[2] row[1]c[0] row[1]c[1] row[1]c[2] The given vector has to have 6 doubles, or bad stuff will happen" RGIL)

        .def("definePixelSizeConfig",
             nb::overload_cast<const char *, const char *, const char *, const char *>(
                 &CMMCore::definePixelSizeConfig),
             "resolutionID"_a,
             "deviceLabel"_a,
             "propName"_a,
             "value"_a RGIL)
        .def("definePixelSizeConfig",
             nb::overload_cast<const char *>(&CMMCore::definePixelSizeConfig),
             "resolutionID"_a RGIL)
        .def("getAvailablePixelSizeConfigs", &CMMCore::getAvailablePixelSizeConfigs, "Returns all defined resolution preset names" RGIL)
        .def("isPixelSizeConfigDefined", &CMMCore::isPixelSizeConfigDefined, "resolutionID"_a, "Checks if the Pixel Size Resolution already exists" RGIL)
        .def("setPixelSizeConfig", &CMMCore::setPixelSizeConfig, "resolutionID"_a, "Applies a Pixel Size Configuration. The command will fail if the configuration was not previously defined." RGIL)
        .def("renamePixelSizeConfig",
             &CMMCore::renamePixelSizeConfig,
             "oldConfigName"_a,
             "newConfigName"_a, "Renames a pixel size configuration. The command will fail if the configuration was not previously defined." RGIL)
        .def("deletePixelSizeConfig", &CMMCore::deletePixelSizeConfig, "configName"_a, "Deletes a pixel size configuration. The command will fail if the configuration was not previously defined." RGIL)
        .def("getPixelSizeConfigData", &CMMCore::getPixelSizeConfigData, "configName"_a, "Returns the configuration object for a give pixel size preset." RGIL)

        // Image Acquisition Methods
        .def("setROI",
             nb::overload_cast<int, int, int, int>(&CMMCore::setROI),
             "x"_a,
             "y"_a,
             "xSize"_a,
             "ySize"_a RGIL)
        .def("setROI",
             nb::overload_cast<const char *, int, int, int, int>(&CMMCore::setROI),
             "label"_a,
             "x"_a,
             "y"_a,
             "xSize"_a,
             "ySize"_a RGIL)
        .def("getROI",
             [](CMMCore &self) {
                int x, y, xSize, ySize;
                self.getROI(x, y, xSize, ySize);            // Call C++ method
                return std::make_tuple(x, y, xSize, ySize); // Return a tuple
             } RGIL)
        .def(
            "getROI",
            [](CMMCore &self, const char *label) {
                int x, y, xSize, ySize;
                self.getROI(label, x, y, xSize, ySize);     // Call the C++ method
                return std::make_tuple(x, y, xSize, ySize); // Return as Python tuple
            },
            "label"_a RGIL)
        .def("clearROI", &CMMCore::clearROI, "Set the region of interest of the current camera to the full frame." RGIL)
        .def("isMultiROISupported", &CMMCore::isMultiROISupported, "Queries the camera to determine if it supports multiple ROIs." RGIL)
        .def("isMultiROIEnabled", &CMMCore::isMultiROIEnabled, "Queries the camera to determine if multiple ROIs are currently set." RGIL)
        .def("setMultiROI", &CMMCore::setMultiROI, "xs"_a, "ys"_a, "widths"_a, "heights"_a, "Set multiple ROIs for the current camera device. Will fail if the camera does not support multiple ROIs, any widths or heights are non-positive, or if the vectors do not all have the same length." RGIL)
        .def("getMultiROI",
             [](CMMCore &self) -> std::tuple<std::vector<unsigned>,
                                             std::vector<unsigned>,
                                             std::vector<unsigned>,
                                             std::vector<unsigned>> {
                std::vector<unsigned> xs, ys, widths, heights;
                self.getMultiROI(xs, ys, widths, heights);
                return {xs, ys, widths, heights};
             } RGIL)

        .def("setExposure", nb::overload_cast<double>(&CMMCore::setExposure), "exp"_a RGIL)
        .def("setExposure",
             nb::overload_cast<const char *, double>(&CMMCore::setExposure),
             "cameraLabel"_a,
             "dExp"_a RGIL)
        .def("getExposure", nb::overload_cast<>(&CMMCore::getExposure) RGIL)
        .def("getExposure", nb::overload_cast<const char *>(&CMMCore::getExposure), "label"_a RGIL)
        .def("snapImage", &CMMCore::snapImage, "Acquires a single image with current settings. Snap is not allowed while the acquisition thread is run" RGIL)
        .def(
            "getImage",
            [](CMMCore &self) -> np_array {
                return create_image_array(self, self.getImage()); } RGIL)
        .def("getImage",
             [](CMMCore &self, unsigned channel) -> np_array {
                return create_image_array(self, self.getImage(channel));
             } RGIL)
        .def("getImageWidth", &CMMCore::getImageWidth, "Horizontal dimension of the image buffer in pixels." RGIL)
        .def("getImageHeight", &CMMCore::getImageHeight, "Vertical dimension of the image buffer in pixels." RGIL)
        .def("getBytesPerPixel", &CMMCore::getBytesPerPixel, "How many bytes for each pixel. This value does not necessarily reflect the capabilities of the particular camera A/D converter." RGIL)
        .def("getImageBitDepth", &CMMCore::getImageBitDepth, "How many bits of dynamic range are to be expected from the camera. This value should be used only as a guideline - it does not guarantee that image buffer will contain only values from the returned dynamic range." RGIL)
        .def("getNumberOfComponents", &CMMCore::getNumberOfComponents, "Returns the number of components the default camera is returning. For example color camera will return 4 components (RGBA) on each snap." RGIL)
        .def("getNumberOfCameraChannels", &CMMCore::getNumberOfCameraChannels, "Returns the number of simultaneous channels the default camera is returning." RGIL)
        .def("getCameraChannelName", &CMMCore::getCameraChannelName, "channelNr"_a, "Returns the name of the requested channel as known by the default camera" RGIL)
        .def("getImageBufferSize", &CMMCore::getImageBufferSize, "Returns the size of the internal image buffer." RGIL)
        .def("setAutoShutter", &CMMCore::setAutoShutter, "state"_a, "If this option is enabled Shutter automatically opens and closes when the image is acquired." RGIL)
        .def("getAutoShutter", &CMMCore::getAutoShutter, "Returns the current setting of the auto-shutter option." RGIL)
        .def("setShutterOpen", nb::overload_cast<bool>(&CMMCore::setShutterOpen), "state"_a RGIL)
        .def("getShutterOpen", nb::overload_cast<>(&CMMCore::getShutterOpen) RGIL)
        .def("setShutterOpen",
             nb::overload_cast<const char *, bool>(&CMMCore::setShutterOpen),
             "shutterLabel"_a,
             "state"_a RGIL)
        .def("getShutterOpen",
             nb::overload_cast<const char *>(&CMMCore::getShutterOpen),
             "shutterLabel"_a RGIL)
        .def("startSequenceAcquisition",
             nb::overload_cast<long, double, bool>(&CMMCore::startSequenceAcquisition),
             "numImages"_a,
             "intervalMs"_a,
             "stopOnOverflow"_a RGIL)
        .def("startSequenceAcquisition",
             nb::overload_cast<const char *, long, double, bool>(
                 &CMMCore::startSequenceAcquisition),
             "cameraLabel"_a,
             "numImages"_a,
             "intervalMs"_a,
             "stopOnOverflow"_a RGIL)
        .def(
            "prepareSequenceAcquisition", &CMMCore::prepareSequenceAcquisition, "cameraLabel"_a, "Prepare the camera for the sequence acquisition to save the time in the StartSequenceAcqusition() call which is supposed to come next." RGIL)
        .def("startContinuousSequenceAcquisition",
             &CMMCore::startContinuousSequenceAcquisition,
             "intervalMs"_a, "Starts the continuous camera sequence acquisition. This command does not block the calling thread for the duration of the acquisition." RGIL)
        .def("stopSequenceAcquisition", nb::overload_cast<>(&CMMCore::stopSequenceAcquisition) RGIL)
        .def("stopSequenceAcquisition",
             nb::overload_cast<const char *>(&CMMCore::stopSequenceAcquisition),
             "cameraLabel"_a RGIL)
        .def("isSequenceRunning", nb::overload_cast<>(&CMMCore::isSequenceRunning) RGIL)
        .def("isSequenceRunning",
             nb::overload_cast<const char *>(&CMMCore::isSequenceRunning),
             "cameraLabel"_a RGIL)
        .def("getLastImage",
             [](CMMCore &self) -> np_array {
                return create_image_array(self, self.getLastImage());
             } RGIL)
        .def("popNextImage",
             [](CMMCore &self) -> np_array {
                return create_image_array(self, self.popNextImage());
             } RGIL)
        // this is a new overload that returns both the image and the metadata
        // not present in the original C++ API
        .def(
            "getLastImageMD",
            [](CMMCore &self) -> std::tuple<np_array, Metadata> {
                Metadata md;
                auto img = self.getLastImageMD(md);
                return {create_metadata_array(self, img, md), md};
            },
            "Get the last image in the circular buffer, return as tuple of image and metadata" RGIL)
        .def(
            "getLastImageMD",
            [](CMMCore &self, Metadata &md) -> np_array {
                auto img = self.getLastImageMD(md);
                return create_metadata_array(self, img, md);
            },
            "md"_a,
            "Get the last image in the circular buffer, store metadata in the provided object" RGIL)
        .def(
            "getLastImageMD",
            [](CMMCore &self,
               unsigned channel,
               unsigned slice) -> std::tuple<np_array, Metadata> {
                Metadata md;
                auto img = self.getLastImageMD(channel, slice, md);
                return {create_metadata_array(self, img, md), md};
            },
            "channel"_a,
            "slice"_a,
            "Get the last image in the circular buffer for a specific channel and slice, return"
            "as tuple of image and metadata" RGIL)
        .def(
            "getLastImageMD",
            [](CMMCore &self, unsigned channel, unsigned slice, Metadata &md) -> np_array {
                auto img = self.getLastImageMD(channel, slice, md);
                return create_metadata_array(self, img, md);
            },
            "channel"_a,
            "slice"_a,
            "md"_a,
            "Get the last image in the circular buffer for a specific channel and slice, store "
            "metadata in the provided object" RGIL)

        .def(
            "popNextImageMD",
            [](CMMCore &self) -> std::tuple<np_array, Metadata> {
                Metadata md;
                auto img = self.popNextImageMD(md);
                return {create_metadata_array(self, img, md), md};
            },
            "Get the last image in the circular buffer, return as tuple of image and metadata" RGIL)
        .def(
            "popNextImageMD",
            [](CMMCore &self, Metadata &md) -> np_array {
                auto img = self.popNextImageMD(md);
                return create_metadata_array(self, img, md);
            },
            "md"_a,
            "Get the last image in the circular buffer, store metadata in the provided object" RGIL)
        .def(
            "popNextImageMD",
            [](CMMCore &self,
               unsigned channel,
               unsigned slice) -> std::tuple<np_array, Metadata> {
                Metadata md;
                auto img = self.popNextImageMD(channel, slice, md);
                return {create_metadata_array(self, img, md), md};
            },
            "channel"_a,
            "slice"_a,
            "Get the last image in the circular buffer for a specific channel and slice, return"
            "as tuple of image and metadata" RGIL)
        .def(
            "popNextImageMD",
            [](CMMCore &self, unsigned channel, unsigned slice, Metadata &md) -> np_array {
                auto img = self.popNextImageMD(channel, slice, md);
                return create_metadata_array(self, img, md);
            },
            "channel"_a,
            "slice"_a,
            "md"_a,
            "Get the last image in the circular buffer for a specific channel and slice, store "
            "metadata in the provided object" RGIL)

        .def(
            "getNBeforeLastImageMD",
            [](CMMCore &self, unsigned long n) -> std::tuple<np_array, Metadata> {
                Metadata md;
                auto img = self.getNBeforeLastImageMD(n, md);
                return {create_metadata_array(self, img, md), md};
            },
            "n"_a,
            "Get the nth image before the last image in the circular buffer and return it as a "
            "tuple "
            "of image and metadata" RGIL)
        .def(
            "getNBeforeLastImageMD",
            [](CMMCore &self, unsigned long n, Metadata &md) -> np_array {
                auto img = self.getNBeforeLastImageMD(n, md);
                return create_metadata_array(self, img, md);
            },
            "n"_a,
            "md"_a,
            "Get the nth image before the last image in the circular buffer and store the "
            "metadata "
            "in the provided object" RGIL)

        // Circular Buffer Methods
        .def("getRemainingImageCount", &CMMCore::getRemainingImageCount, "Returns number ofimages available in the Circular Buffer" RGIL)
        .def("getBufferTotalCapacity", &CMMCore::getBufferTotalCapacity, "Returns the total number of images that can be stored in the buffer" RGIL)
        .def("getBufferFreeCapacity", &CMMCore::getBufferFreeCapacity, "Returns the number of images that can be added to the buffer without overflowing" RGIL)
        .def("isBufferOverflowed", &CMMCore::isBufferOverflowed, "Indicates whether the circular buffer is overflowed" RGIL)
        .def("setCircularBufferMemoryFootprint",
             &CMMCore::setCircularBufferMemoryFootprint,
             "sizeMB"_a, "Reserve memory for the circular buffer." RGIL)
        .def("getCircularBufferMemoryFootprint", &CMMCore::getCircularBufferMemoryFootprint, "Returns the size of the Circular Buffer in MB" RGIL)
        .def("initializeCircularBuffer", &CMMCore::initializeCircularBuffer, "Initialize circular buffer based on the current camera settings." RGIL)
        .def("clearCircularBuffer", &CMMCore::clearCircularBuffer, "Removes all images from the circular buffer." RGIL)

        // Exposure Sequence Methods
        .def("isExposureSequenceable", &CMMCore::isExposureSequenceable, "cameraLabel"_a, "Queries camera if exposure can be used in a sequence" RGIL)
        .def("startExposureSequence", &CMMCore::startExposureSequence, "cameraLabel"_a, "Starts an ongoing sequence of triggered exposures in a camera This should only be called for cameras where exposure time is sequenceable" RGIL)
        .def("stopExposureSequence", &CMMCore::stopExposureSequence, "cameraLabel"_a, "Stops an ongoing sequence of triggered exposures in a camera This should only be called for cameras where exposure time is sequenceable" RGIL)
        .def("getExposureSequenceMaxLength",
             &CMMCore::getExposureSequenceMaxLength,
             "cameraLabel"_a, "Gets the maximum length of a camera's exposure sequence. This should only be called for cameras where exposure time is sequenceable" RGIL)
        .def("loadExposureSequence",
             &CMMCore::loadExposureSequence,
             "cameraLabel"_a,
             "exposureSequence_ms"_a, "Transfer a sequence of exposure times to the camera. This should only be called for cameras where exposure time is sequenceable" RGIL)

        // Autofocus Methods
        .def("getLastFocusScore", &CMMCore::getLastFocusScore, "Returns the latest focus score from the focusing device. Use this value to estimate or record how reliable the focus is. The range of values is device dependent." RGIL)
        .def("getCurrentFocusScore", &CMMCore::getCurrentFocusScore, "Returns the focus score from the default focusing device measured at the current Z position. Use this value to create profiles or just to verify that the image is in focus. The absolute range of returned scores depends on the actual focusing device." RGIL)
        .def("enableContinuousFocus", &CMMCore::enableContinuousFocus, "enable"_a, "Enables or disables the operation of the continuous focusing hardware device." RGIL)
        .def("isContinuousFocusEnabled", &CMMCore::isContinuousFocusEnabled, "Checks if the continuous focusing hardware device is ON or OFF." RGIL)
        .def("isContinuousFocusLocked", &CMMCore::isContinuousFocusLocked, "Returns the lock-in status of the continuous focusing device." RGIL)
        .def("isContinuousFocusDrive", &CMMCore::isContinuousFocusDrive, "stageLabel"_a, "Check if a stage has continuous focusing capability (positions can be set while continuous focus runs)." RGIL)
        .def("fullFocus", &CMMCore::fullFocus, "Performs focus acquisition and lock for the one-shot focusing device." RGIL)
        .def("incrementalFocus", &CMMCore::incrementalFocus, "Performs incremental focus for the one-shot focusing device." RGIL)
        .def("setAutoFocusOffset", &CMMCore::setAutoFocusOffset, "offset"_a, "Applies offset the one-shot focusing device." RGIL)
        .def("getAutoFocusOffset", &CMMCore::getAutoFocusOffset, "Measures offset for the one-shot focusing device." RGIL)

        // State Device Control Methods
        .def("setState", &CMMCore::setState, "stateDeviceLabel"_a, "state"_a, "Sets the state (position) on the specific device. The command will fail if the device does not support states." RGIL)
        .def("getState", &CMMCore::getState, "stateDeviceLabel"_a, "Returns the current state (position) on the specific device. The command will fail if the device does not support states." RGIL)
        .def("getNumberOfStates", &CMMCore::getNumberOfStates, "stateDeviceLabel"_a, "Returns the total number of available positions (states)." RGIL)
        .def("setStateLabel", &CMMCore::setStateLabel, "stateDeviceLabel"_a, "stateLabel"_a, "Sets device state using the previously assigned label (string)." RGIL)
        .def("getStateLabel", &CMMCore::getStateLabel, "stateDeviceLabel"_a, "Returns the current state as the label (string)." RGIL)
        .def("defineStateLabel",
             &CMMCore::defineStateLabel,
             "stateDeviceLabel"_a,
             "state"_a,
             "stateLabel"_a, "Defines a label for the specific state/" RGIL)
        .def("getStateLabels", &CMMCore::getStateLabels, "stateDeviceLabel"_a, "Return labels for all states" RGIL)
        .def("getStateFromLabel",
             &CMMCore::getStateFromLabel,
             "stateDeviceLabel"_a,
             "stateLabel"_a, "Obtain the state for a given label." RGIL)

        // Stage Control Methods
        .def("setPosition",
             nb::overload_cast<const char *, double>(&CMMCore::setPosition),
             "stageLabel"_a,
             "position"_a RGIL)
        .def("setPosition", nb::overload_cast<double>(&CMMCore::setPosition), "position"_a RGIL)
        .def("getPosition",
             nb::overload_cast<const char *>(&CMMCore::getPosition),
             "stageLabel"_a RGIL)
        .def("getPosition", nb::overload_cast<>(&CMMCore::getPosition) RGIL)
        .def("setRelativePosition",
             nb::overload_cast<const char *, double>(&CMMCore::setRelativePosition),
             "stageLabel"_a,
             "d"_a RGIL)
        .def("setRelativePosition",
             nb::overload_cast<double>(&CMMCore::setRelativePosition),
             "d"_a RGIL)
        .def("setOrigin", nb::overload_cast<const char *>(&CMMCore::setOrigin), "stageLabel"_a RGIL)
        .def("setOrigin", nb::overload_cast<>(&CMMCore::setOrigin) RGIL)
        .def("setAdapterOrigin",
             nb::overload_cast<const char *, double>(&CMMCore::setAdapterOrigin),
             "stageLabel"_a,
             "newZUm"_a RGIL)
        .def("setAdapterOrigin",
             nb::overload_cast<double>(&CMMCore::setAdapterOrigin),
             "newZUm"_a RGIL)

        // Focus Direction Methods
        .def("setFocusDirection", &CMMCore::setFocusDirection, "stageLabel"_a, "sign"_a, "Set the focus direction of a stage.\n\nThe sign should be +1 (or any positive value), zero, or -1 (or any negative value), and is interpreted in the same way as the return value of getFocusDirection()." RGIL)
        .def("getFocusDirection", &CMMCore::getFocusDirection, "stageLabel"_a, "Get the focus direction of a stage.\n\nReturns +1 if increasing position brings objective closer to sample, -1 if increasing position moves objective away from sample, or 0 if unknown. (Make sure to check for zero!)" RGIL)

        // Stage Sequence Methods
        .def("isStageSequenceable", &CMMCore::isStageSequenceable, "stageLabel"_a, "Queries stage if it can be used in a sequence" RGIL)
        .def("isStageLinearSequenceable", &CMMCore::isStageLinearSequenceable, "stageLabel"_a, "Queries if the stage can be used in a linear sequence A linear sequence is defined by a stepsize and number of slices" RGIL)
        .def("startStageSequence", &CMMCore::startStageSequence, "stageLabel"_a, "Starts an ongoing sequence of triggered events in a stage This should only be called for stages" RGIL)
        .def("stopStageSequence", &CMMCore::stopStageSequence, "stageLabel"_a, "Stops an ongoing sequence of triggered events in a stage This should only be called for stages that are sequenceable" RGIL)
        .def("getStageSequenceMaxLength", &CMMCore::getStageSequenceMaxLength, "stageLabel"_a, "Gets the maximum length of a stage's position sequence. This should only be called for stages that are sequenceable" RGIL)
        .def("loadStageSequence",
             &CMMCore::loadStageSequence,
             "stageLabel"_a,
             "positionSequence"_a, "Transfer a sequence of events/states/whatever to the device This should only be called for device-properties that are sequenceable" RGIL)
        .def("setStageLinearSequence",
             &CMMCore::setStageLinearSequence,
             "stageLabel"_a,
             "dZ_um"_a,
             "nSlices"_a, "Loads a linear sequence (defined by stepsize and nr. of steps) into the device. Why was it not called loadStageLinearSequence???" RGIL)

        // XY Stage Control Methods
        .def("setXYPosition",
             nb::overload_cast<const char *, double, double>(&CMMCore::setXYPosition),
             "xyStageLabel"_a,
             "x"_a,
             "y"_a RGIL)
        .def("setXYPosition",
             nb::overload_cast<double, double>(&CMMCore::setXYPosition),
             "x"_a,
             "y"_a RGIL)
        .def("setRelativeXYPosition",
             nb::overload_cast<const char *, double, double>(&CMMCore::setRelativeXYPosition),
             "xyStageLabel"_a,
             "dx"_a,
             "dy"_a RGIL)
        .def("setRelativeXYPosition",
             nb::overload_cast<double, double>(&CMMCore::setRelativeXYPosition),
             "dx"_a,
             "dy"_a RGIL)

        .def(
            "getXYPosition",
            [](CMMCore &self, const char *xyStageLabel) -> std::tuple<double, double> {
                double x, y;
                self.getXYPosition(xyStageLabel, x, y);
                return {x, y};
            },
            "xyStageLabel"_a RGIL)
        .def("getXYPosition",
             [](CMMCore &self) -> std::tuple<double, double> {
                double x, y;
                self.getXYPosition(x, y);
                return {x, y};
             } RGIL)
        .def("getXPosition",
             nb::overload_cast<const char *>(&CMMCore::getXPosition),
             "xyStageLabel"_a RGIL)
        .def("getYPosition",
             nb::overload_cast<const char *>(&CMMCore::getYPosition),
             "xyStageLabel"_a RGIL)
        .def("getXPosition", nb::overload_cast<>(&CMMCore::getXPosition) RGIL)
        .def("getYPosition", nb::overload_cast<>(&CMMCore::getYPosition) RGIL)
        .def("stop", &CMMCore::stop, "xyOrZStageLabel"_a, "Stop the XY or focus/Z stage motors" RGIL)
        .def("home", &CMMCore::home, "xyOrZStageLabel"_a, "Perform a hardware homing operation for an XY or focus/Z stage." RGIL)
        .def("setOriginXY",
             nb::overload_cast<const char *>(&CMMCore::setOriginXY),
             "xyStageLabel"_a RGIL)
        .def("setOriginXY", nb::overload_cast<>(&CMMCore::setOriginXY) RGIL)
        .def("setOriginX",
             nb::overload_cast<const char *>(&CMMCore::setOriginX),
             "xyStageLabel"_a RGIL)
        .def("setOriginX", nb::overload_cast<>(&CMMCore::setOriginX) RGIL)
        .def("setOriginY",
             nb::overload_cast<const char *>(&CMMCore::setOriginY),
             "xyStageLabel"_a RGIL)
        .def("setOriginY", nb::overload_cast<>(&CMMCore::setOriginY) RGIL)
        .def("setAdapterOriginXY",
             nb::overload_cast<const char *, double, double>(&CMMCore::setAdapterOriginXY),
             "xyStageLabel"_a,
             "newXUm"_a,
             "newYUm"_a RGIL)
        .def("setAdapterOriginXY",
             nb::overload_cast<double, double>(&CMMCore::setAdapterOriginXY),
             "newXUm"_a,
             "newYUm"_a RGIL)

        // XY Stage Sequence Methods
        .def("isXYStageSequenceable", &CMMCore::isXYStageSequenceable, "xyStageLabel"_a, "Queries XY stage if it can be used in a sequence" RGIL)
        .def("startXYStageSequence", &CMMCore::startXYStageSequence, "xyStageLabel"_a, "Starts an ongoing sequence of triggered events in an XY stage This should only be called for stages" RGIL)
        .def("stopXYStageSequence", &CMMCore::stopXYStageSequence, "xyStageLabel"_a, "Stops an ongoing sequence of triggered events in an XY stage This should only be called for stages that are sequenceable" RGIL)
        .def("getXYStageSequenceMaxLength",
             &CMMCore::getXYStageSequenceMaxLength,
             "xyStageLabel"_a, "Gets the maximum length of an XY stage's position sequence. This should only be called for XY stages that are sequenceable" RGIL)
        .def("loadXYStageSequence",
             &CMMCore::loadXYStageSequence,
             "xyStageLabel"_a,
             "xSequence"_a,
             "ySequence"_a, "Transfer a sequence of stage positions to the xy stage. xSequence and ySequence must have the same length. This should only be called for XY stages that are sequenceable" RGIL)

        // Serial Port Control
        .def("setSerialProperties",
             &CMMCore::setSerialProperties,
             "portName"_a,
             "answerTimeout"_a,
             "baudRate"_a,
             "delayBetweenCharsMs"_a,
             "handshaking"_a,
             "parity"_a,
             "stopBits"_a, "Sets all com port properties in a single call" RGIL)
        .def("setSerialPortCommand",
             &CMMCore::setSerialPortCommand,
             "portLabel"_a,
             "command"_a,
             "term"_a, "Send string to the serial device and return an answer. This command blocks until it receives an answer from the device terminated by the specified sequence." RGIL)
        .def("getSerialPortAnswer", &CMMCore::getSerialPortAnswer, "portLabel"_a, "term"_a, "Continuously read from the serial port until the terminating sequence is encountered." RGIL)
        .def("writeToSerialPort", &CMMCore::writeToSerialPort, "portLabel"_a, "data"_a, "Sends an array of characters to the serial port and returns immediately." RGIL)
        .def("readFromSerialPort", &CMMCore::readFromSerialPort, "portLabel"_a, "Reads the contents of the Rx buffer." RGIL)

        // SLM Control
        // setSLMImage accepts a second argument (pixels) of either unsigned char* or unsigned
        // int*
        .def(
            "setSLMImage",
            [](CMMCore &self,
               const char *slmLabel,
               const nb::ndarray<uint8_t> &pixels) -> void {
                long expectedWidth = self.getSLMWidth(slmLabel);
                long expectedHeight = self.getSLMHeight(slmLabel);
                long bytesPerPixel = self.getSLMBytesPerPixel(slmLabel);
                validate_slm_image(pixels, expectedWidth, expectedHeight, bytesPerPixel);

                // Cast the numpy array to a pointer to unsigned char
                self.setSLMImage(slmLabel, reinterpret_cast<unsigned char *>(pixels.data()));
            },
            "slmLabel"_a,
            "pixels"_a RGIL)
        .def("setSLMPixelsTo",
             nb::overload_cast<const char *, unsigned char>(&CMMCore::setSLMPixelsTo),
             "slmLabel"_a,
             "intensity"_a RGIL)
        .def("setSLMPixelsTo",
             nb::overload_cast<const char *, unsigned char, unsigned char, unsigned char>(
                 &CMMCore::setSLMPixelsTo),
             "slmLabel"_a,
             "red"_a,
             "green"_a,
             "blue"_a RGIL)
        .def("displaySLMImage", &CMMCore::displaySLMImage, "slmLabel"_a, "Display the waiting image on the SLM." RGIL)
        .def("setSLMExposure", &CMMCore::setSLMExposure, "slmLabel"_a, "exposure_ms"_a, "For SLM devices with build-in light source (such as projectors) this will set the exposure time, but not (yet) start the illumination" RGIL)
        .def("getSLMExposure", &CMMCore::getSLMExposure, "slmLabel"_a, "Returns the exposure time that will be used by the SLM for illumination" RGIL)
        .def("getSLMWidth", &CMMCore::getSLMWidth, "slmLabel"_a, "Returns the width (in \"pixels\") of the SLM" RGIL)
        .def("getSLMHeight", &CMMCore::getSLMHeight, "slmLabel"_a, "Returns the height (in \"pixels\") of the SLM" RGIL)
        .def("getSLMNumberOfComponents", &CMMCore::getSLMNumberOfComponents, "slmLabel"_a, "Returns the number of components (usually these depict colors) of the SLM For instance, an RGB projector will return 3, but a grey scale SLM returns 1" RGIL)
        .def("getSLMBytesPerPixel", &CMMCore::getSLMBytesPerPixel, "slmLabel"_a, "Returns the number of bytes per SLM pixel" RGIL)
        // SLM Sequence
        .def("getSLMSequenceMaxLength", &CMMCore::getSLMSequenceMaxLength, "slmLabel"_a, "For SLMs that support sequences, returns the maximum length of the sequence that can be uploaded to the device" RGIL)
        .def("startSLMSequence", &CMMCore::startSLMSequence, "slmLabel"_a, "Starts the sequence previously uploaded to the SLM" RGIL)
        .def("stopSLMSequence", &CMMCore::stopSLMSequence, "slmLabel"_a, "Stops the SLM sequence if previously started" RGIL)
        .def(
            "loadSLMSequence",
            [](CMMCore &self,
               const char *slmLabel,
               std::vector<nb::ndarray<uint8_t>> &imageSequence) -> void {
                long expectedWidth = self.getSLMWidth(slmLabel);
                long expectedHeight = self.getSLMHeight(slmLabel);
                long bytesPerPixel = self.getSLMBytesPerPixel(slmLabel);
                std::vector<unsigned char *> inputVector;
                for (auto &image : imageSequence) {
                    validate_slm_image(image, expectedWidth, expectedHeight, bytesPerPixel);
                    inputVector.push_back(reinterpret_cast<unsigned char *>(image.data()));
                }
                self.loadSLMSequence(slmLabel, inputVector);
            },
            "slmLabel"_a,
            "pixels"_a RGIL)

        // Galvo Control
        .def("pointGalvoAndFire",
             &CMMCore::pointGalvoAndFire,
             "galvoLabel"_a,
             "x"_a,
             "y"_a,
             "pulseTime_us"_a, "Set the Galvo to an x,y position and fire the laser for a predetermined duration." RGIL)
        .def("setGalvoSpotInterval",
             &CMMCore::setGalvoSpotInterval,
             "galvoLabel"_a,
             "pulseTime_us"_a RGIL)
        .def("setGalvoPosition", &CMMCore::setGalvoPosition, "galvoLabel"_a, "x"_a, "y"_a, "Set the Galvo to an x,y position" RGIL)
        .def("getGalvoPosition",
             [](CMMCore &self, const char *galvoLabel) -> std::tuple<double, double> {
                double x, y;
                self.getGalvoPosition(galvoLabel, x, y); // Call C++ method
                return std::make_tuple(x, y);            // Return a tuple
             } RGIL)
        .def("setGalvoIlluminationState",
             &CMMCore::setGalvoIlluminationState,
             "galvoLabel"_a,
             "on"_a, "Set the galvo's illumination state to on or off" RGIL)
        .def("getGalvoXRange", &CMMCore::getGalvoXRange, "galvoLabel"_a, "Get the Galvo x range" RGIL)
        .def("getGalvoXMinimum", &CMMCore::getGalvoXMinimum, "galvoLabel"_a, "Get the Galvo x minimum" RGIL)
        .def("getGalvoYRange", &CMMCore::getGalvoYRange, "galvoLabel"_a, "Get the Galvo y range" RGIL)
        .def("getGalvoYMinimum", &CMMCore::getGalvoYMinimum, "galvoLabel"_a, "Get the Galvo y minimum" RGIL)
        .def("addGalvoPolygonVertex",
             &CMMCore::addGalvoPolygonVertex,
             "galvoLabel"_a,
             "polygonIndex"_a,
             "x"_a,
             "y"_a,
             R"doc(Add a vertex to a galvo polygon.)doc" RGIL)
        .def("deleteGalvoPolygons", &CMMCore::deleteGalvoPolygons, "galvoLabel"_a, "Remove all added polygons" RGIL)
        .def("loadGalvoPolygons", &CMMCore::loadGalvoPolygons, "galvoLabel"_a, "Load a set of galvo polygons to the device" RGIL)
        .def("setGalvoPolygonRepetitions",
             &CMMCore::setGalvoPolygonRepetitions,
             "galvoLabel"_a,
             "repetitions"_a, "Set the number of times to loop galvo polygons" RGIL)
        .def("runGalvoPolygons", &CMMCore::runGalvoPolygons, "galvoLabel"_a, "Run a loop of galvo polygons" RGIL)
        .def("runGalvoSequence", &CMMCore::runGalvoSequence, "galvoLabel"_a, "Run a sequence of galvo positions" RGIL)
        .def("getGalvoChannel", &CMMCore::getGalvoChannel, "galvoLabel"_a, "Get the name of the active galvo channel (for a multi-laser galvo device)." RGIL)
        
        // PressurePump Control
        .def("pressurePumpStop", &CMMCore::pressurePumpStop, "pumpLabel"_a, "Stops the pressure pump" RGIL)
        .def("pressurePumpCalibrate", &CMMCore::pressurePumpCalibrate, "pumpLabel"_a RGIL)
        .def("pressurePumpRequiresCalibration", &CMMCore::pressurePumpRequiresCalibration, "pumpLabel"_a, "Returns boolean whether the pump is operational before calibration" RGIL)
        .def("setPumpPressureKPa", &CMMCore::setPumpPressureKPa, "pumpLabel"_a, "pressure"_a, "Sets the pressure of the pump in kPa" RGIL)
        .def("getPumpPressureKPa", &CMMCore::getPumpPressureKPa, "pumpLabel"_a, "Gets the pressure of the pump in kPa" RGIL)
        
        // VolumetricPump control
        .def("volumetricPumpStop", &CMMCore::volumetricPumpStop, "pumpLabel"_a, "Stops the volumetric pump" RGIL)
        .def("volumetricPumpHome", &CMMCore::volumetricPumpHome, "pumpLabel"_a RGIL)
        .def("volumetricPumpRequiresHoming", &CMMCore::volumetricPumpRequiresHoming, "pumpLabel"_a RGIL)
        .def("invertPumpDirection", &CMMCore::invertPumpDirection, "pumpLabel"_a, "invert"_a, "Sets whether the pump direction needs to be inverted" RGIL)
        .def("isPumpDirectionInverted", &CMMCore::isPumpDirectionInverted, "pumpLabel"_a, "Gets whether the pump direction needs to be inverted" RGIL)
        .def("setPumpVolume", &CMMCore::setPumpVolume, "pumpLabel"_a, "volume"_a, "Sets the volume of fluid in the pump in uL. Note it does not withdraw upto this amount. It is merely to inform MM of the volume in a prefilled pump." RGIL)
        .def("getPumpVolume", &CMMCore::getPumpVolume, "pumpLabel"_a, "Get the fluid volume in the pump in uL" RGIL)
        .def("setPumpMaxVolume", &CMMCore::setPumpMaxVolume, "pumpLabel"_a, "volume"_a, "Sets the max volume of the pump in uL" RGIL)
        .def("getPumpMaxVolume", &CMMCore::getPumpMaxVolume, "pumpLabel"_a, "Gets the max volume of the pump in uL" RGIL)
        .def("setPumpFlowrate", &CMMCore::setPumpFlowrate, "pumpLabel"_a, "volume"_a, "Sets the flowrate of the pump in uL per second" RGIL)
        .def("getPumpFlowrate", &CMMCore::getPumpFlowrate, "pumpLabel"_a, "Gets the flowrate of the pump in uL per second" RGIL)
        .def("pumpStart", &CMMCore::pumpStart, "pumpLabel"_a, "Start dispensing at the set flowrate until syringe is empty, or manually stopped (whichever occurs first)." RGIL)
        .def("pumpDispenseDurationSeconds", &CMMCore::pumpDispenseDurationSeconds, "pumpLabel"_a, "seconds"_a, "Dispenses for the provided duration (in seconds) at the set flowrate" RGIL)
        .def("pumpDispenseVolumeUl", &CMMCore::pumpDispenseVolumeUl, "pumpLabel"_a, "microLiter"_a, "Dispenses the provided volume (in uL) at the set flowrate" RGIL)

        // Device Discovery
        .def("supportsDeviceDetection", &CMMCore::supportsDeviceDetection, "deviceLabel"_a, "Return whether or not the device supports automatic device detection (i.e. whether or not detectDevice() may be safely called)." RGIL)
        .def("detectDevice", &CMMCore::detectDevice, "deviceLabel"_a, "Tries to communicate to a device through a given serial port Used to automate discovery of correct serial port Also configures the serial port correctly" RGIL)

        // Hub and Peripheral Devices
        .def("getParentLabel", &CMMCore::getParentLabel, "peripheralLabel"_a RGIL)
        .def("setParentLabel", &CMMCore::setParentLabel, "deviceLabel"_a, "parentHubLabel"_a, "Sets parent device label" RGIL)
        .def("getInstalledDevices", &CMMCore::getInstalledDevices, "hubLabel"_a, "Performs auto-detection and loading of child devices that are attached to a Hub device. For example, if a motorized microscope is represented by a Hub device, it is capable of discovering what specific child devices are currently attached. In that case this call might report that Z-stage, filter changer and objective turret are currently installed and return three device names in the string list." RGIL)
        .def("getInstalledDeviceDescription",
             &CMMCore::getInstalledDeviceDescription,
             "hubLabel"_a,
             "peripheralLabel"_a RGIL)
        .def("getLoadedPeripheralDevices", &CMMCore::getLoadedPeripheralDevices, "hubLabel"_a RGIL)

        ;
}
