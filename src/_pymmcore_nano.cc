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

const std::string PYMMCORE_NANO_VERSION = "0";

///////////////// GIL_MACROS ///////////////////

// If you define HOLD_GIL in your build (e.g. -DHOLD_GIL),
// then the GIL will be held for the duration of all calls into C++ from
// Python.  By default, the GIL is released for most calls into C++ from Python.
#ifdef HOLD_GIL
#define NB_DEF_GIL(...) .def(__VA_ARGS__)
#else
#define NB_DEF_GIL(...) .def(__VA_ARGS__, nb::call_guard<nb::gil_scoped_release>())
#endif

///////////////// NUMPY ARRAY HELPERS ///////////////////

// Alias for read-only NumPy array
using np_array = nb::ndarray<nb::numpy, nb::ro>;
using StrVec = std::vector<std::string>;

/**
 * @brief Creates a read-only NumPy array for pBuf for a given width, height,
 * etc. These parameters are are gleaned either from image metadata or core
 * methods.
 *
 */
np_array build_grayscale_np_array(CMMCore &core, void *pBuf, unsigned width, unsigned height,
                                  unsigned byteDepth) {
  std::initializer_list<size_t> new_shape = {height, width};
  std::initializer_list<int64_t> strides = {width, 1};

  // Determine the dtype based on the element size
  nb::dlpack::dtype new_dtype;
  switch (byteDepth) {
    case 1: new_dtype = nb::dtype<uint8_t>(); break;
    case 2: new_dtype = nb::dtype<uint16_t>(); break;
    case 4: new_dtype = nb::dtype<uint32_t>(); break;
    default: throw std::invalid_argument("Unsupported element size");
  }

  // NOTE: I am definitely *not* sure that I've done this owner correctly.
  // we need to assign an owner to the array whose continued existence
  // keeps the underlying memory region alive:
  //
  // https://nanobind.readthedocs.io/en/latest/ndarray.html#returning-arrays-from-c-to-python
  // https://nanobind.readthedocs.io/en/latest/ndarray.html#data-ownership

  // This method comes directly from the docs above
  // but leads to a double free error
  // nb::capsule owner(data, [](void *p) noexcept { delete[] (float *)p; });

  // This method ties the lifetime of the buffer to the lifetime of the CMMCore
  // object but gives a bunch of "nanobind: leaked 6 instances!" warnings at
  // exit. those *could* be hidden with `nb::set_leak_warnings(false);` ... but
  // not sure if that's a good idea. nb::object owner = nb::cast(core,
  // nb::rv_policy::reference);

  // This would fully copy the data.  It's the safest, but also the slowest.
  // size_t total_size = std::accumulate(shape.begin(), shape.end(), (size_t)1,
  // std::multiplies<>()); auto buffer = std::make_unique<uint8_t[]>(total_size
  // * bytesPerPixel); std::memcpy(buffer.get(), pBuf, total_size *
  // bytesPerPixel);
  // // ... then later use buffer.release() as the data pointer in the array
  // constructor

  // This method gives neither leak warnings nor double free errors.
  // If the core object deletes the buffer prematurely, the numpy array will
  // point to invalid memory, potentially leading to crashes or undefined
  // behavior... so users should  call `img.copy()` if they want to ensure the
  // data is copied.
  nb::capsule owner(pBuf, [](void *p) noexcept {});

  // Create the ndarray
  return np_array(pBuf, new_shape, owner, strides, new_dtype);
}

// only reason we're making two functions here is that i had a hell of a time
// trying to create std::initializer_list dynamically based on numComponents
// (only on Linux) so we create two constructors
np_array build_rgb_np_array(CMMCore &core, void *pBuf, unsigned width, unsigned height,
                            unsigned byteDepth) {
  const unsigned out_byteDepth = byteDepth / 4;  // break up the 4 components

  std::initializer_list<size_t> new_shape = {height, width, 3};
  // Note the negative stride for the last dimension, data comes in as BGRA
  // we want to invert that to be ARGB
  std::initializer_list<int64_t> strides = {width * byteDepth, byteDepth, -1};
  // offset the buffer pointer (based on the byteDepth) to skip the alpha
  // channel so we end up with just RGB
  const uint8_t *offset_buf = static_cast<const uint8_t *>(pBuf) + out_byteDepth * 2;

  // Determine the dtype based on the element size
  nb::dlpack::dtype new_dtype;
  switch (out_byteDepth) {  // all RGB formats have 4 components in a single "pixel"
    case 1: new_dtype = nb::dtype<uint8_t>(); break;
    case 2: new_dtype = nb::dtype<uint16_t>(); break;
    case 4: new_dtype = nb::dtype<uint32_t>(); break;
    default: throw std::invalid_argument("Unsupported element size");
  }
  nb::capsule owner(pBuf, [](void *p) noexcept {});

  // Create the ndarray
  return np_array(offset_buf, new_shape, owner, strides, new_dtype);
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
    throw std::invalid_argument(
        "Image dimensions are wrong for this SLM. Expected (" + std::to_string(expectedHeight) +
        ", " + std::to_string(expectedWidth) + "), but received (" +
        std::to_string(pixels.shape(0)) + ", " + std::to_string(pixels.shape(1)) + ").");
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
                11);  // Total number of overridable virtual methods.

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
};

////////////////////////////////////////////////////////////////////////////
///////////////// main _pymmcore_nano module definition  ///////////////////
////////////////////////////////////////////////////////////////////////////

NB_MODULE(_pymmcore_nano, m) {
  // https://nanobind.readthedocs.io/en/latest/faq.html#why-am-i-getting-errors-about-leaked-functions-and-types
  nb::set_leak_warnings(false);

  m.doc() = "Python bindings for MMCore";

  /////////////////// Module Attributes ///////////////////

  m.attr("DEVICE_INTERFACE_VERSION") = DEVICE_INTERFACE_VERSION;
  m.attr("MODULE_INTERFACE_VERSION") = MODULE_INTERFACE_VERSION;
  std::string version = std::to_string(MMCore_versionMajor) + "." +
                        std::to_string(MMCore_versionMinor) + "." +
                        std::to_string(MMCore_versionPatch);
  m.attr("MMCore_version") = version;
  m.attr("MMCore_version_info") =
      std::tuple(MMCore_versionMajor, MMCore_versionMinor, MMCore_versionPatch);
  // the final combined version
  m.attr("PYMMCORE_NANO_VERSION") = PYMMCORE_NANO_VERSION;
  m.attr("__version__") =
      version + "." + std::to_string(DEVICE_INTERFACE_VERSION) + "." + PYMMCORE_NANO_VERSION;

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
  m.attr("DEVICE_INVALID_PROPERTY_LIMTS") = DEVICE_INVALID_PROPERTY_LIMTS;  // Fix Typo
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
  m.attr("g_Keyword_Metadata_CameraLabel") = MM::g_Keyword_Metadata_CameraLabel;
  m.attr("g_Keyword_Meatdata_Exposure") = MM::g_Keyword_Meatdata_Exposure;
  m.attr("g_Keyword_Metadata_Score") = MM::g_Keyword_Metadata_Score;
  m.attr("g_Keyword_Metadata_ImageNumber") = MM::g_Keyword_Metadata_ImageNumber;
  m.attr("g_Keyword_Metadata_ROI_X") = MM::g_Keyword_Metadata_ROI_X;
  m.attr("g_Keyword_Metadata_ROI_Y") = MM::g_Keyword_Metadata_ROI_Y;
  m.attr("g_Keyword_Metadata_TimeInCore") = MM::g_Keyword_Metadata_TimeInCore;
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
  m.attr("g_CFGCommand_ParentID") = MM::g_CFGCommand_ParentID;
  m.attr("g_CFGCommand_FocusDirection") = MM::g_CFGCommand_FocusDirection;
  m.attr("g_CFGGroup_System") = MM::g_CFGGroup_System;
  m.attr("g_CFGGroup_System_Startup") = MM::g_CFGGroup_System_Startup;
  m.attr("g_CFGGroup_System_Shutdown") = MM::g_CFGGroup_System_Shutdown;
  m.attr("g_CFGGroup_PixelSizeUm") = MM::g_CFGGroup_PixelSizeUm;

  /////////////////// Enums ///////////////////

  nb::enum_<MM::DeviceType>(m, "DeviceType", nb::is_arithmetic())
      .value("UnknownType", MM::DeviceType::UnknownType)
      .value("AnyType", MM::DeviceType::AnyType)
      .value("CameraDevice", MM::DeviceType::CameraDevice)
      .value("ShutterDevice", MM::DeviceType::ShutterDevice)
      .value("StateDevice", MM::DeviceType::StateDevice)
      .value("StageDevice", MM::DeviceType::StageDevice)
      .value("XYStageDevice", MM::DeviceType::XYStageDevice)
      .value("SerialDevice", MM::DeviceType::SerialDevice)
      .value("GenericDevice", MM::DeviceType::GenericDevice)
      .value("AutoFocusDevice", MM::DeviceType::AutoFocusDevice)
      .value("CoreDevice", MM::DeviceType::CoreDevice)
      .value("ImageProcessorDevice", MM::DeviceType::ImageProcessorDevice)
      .value("SignalIODevice", MM::DeviceType::SignalIODevice)
      .value("MagnifierDevice", MM::DeviceType::MagnifierDevice)
      .value("SLMDevice", MM::DeviceType::SLMDevice)
      .value("HubDevice", MM::DeviceType::HubDevice)
      .value("GalvoDevice", MM::DeviceType::GalvoDevice);

  nb::enum_<MM::PropertyType>(m, "PropertyType", nb::is_arithmetic())
      .value("Undef", MM::PropertyType::Undef)
      .value("String", MM::PropertyType::String)
      .value("Float", MM::PropertyType::Float)
      .value("Integer", MM::PropertyType::Integer);

  nb::enum_<MM::ActionType>(m, "ActionType", nb::is_arithmetic())
      .value("NoAction", MM::ActionType::NoAction)
      .value("BeforeGet", MM::ActionType::BeforeGet)
      .value("AfterSet", MM::ActionType::AfterSet)
      .value("IsSequenceable", MM::ActionType::IsSequenceable)
      .value("AfterLoadSequence", MM::ActionType::AfterLoadSequence)
      .value("StartSequence", MM::ActionType::StartSequence)
      .value("StopSequence", MM::ActionType::StopSequence);

  nb::enum_<MM::PortType>(m, "PortType", nb::is_arithmetic())
      .value("InvalidPort", MM::PortType::InvalidPort)
      .value("SerialPort", MM::PortType::SerialPort)
      .value("USBPort", MM::PortType::USBPort)
      .value("HIDPort", MM::PortType::HIDPort);

  nb::enum_<MM::FocusDirection>(m, "FocusDirection", nb::is_arithmetic())
      .value("FocusDirectionUnknown", MM::FocusDirection::FocusDirectionUnknown)
      .value("FocusDirectionTowardSample", MM::FocusDirection::FocusDirectionTowardSample)
      .value("FocusDirectionAwayFromSample", MM::FocusDirection::FocusDirectionAwayFromSample);

  nb::enum_<MM::DeviceNotification>(m, "DeviceNotification", nb::is_arithmetic())
      .value("Attention", MM::DeviceNotification::Attention)
      .value("Done", MM::DeviceNotification::Done)
      .value("StatusChanged", MM::DeviceNotification::StatusChanged);

  nb::enum_<MM::DeviceDetectionStatus>(m, "DeviceDetectionStatus", nb::is_arithmetic())
      .value("Unimplemented", MM::DeviceDetectionStatus::Unimplemented)
      .value("Misconfigured", MM::DeviceDetectionStatus::Misconfigured)
      .value("CanNotCommunicate", MM::DeviceDetectionStatus::CanNotCommunicate)
      .value("CanCommunicate", MM::DeviceDetectionStatus::CanCommunicate);

  nb::enum_<DeviceInitializationState>(m, "DeviceInitializationState", nb::is_arithmetic())
      .value("Uninitialized", DeviceInitializationState::Uninitialized)
      .value("InitializedSuccessfully", DeviceInitializationState::InitializedSuccessfully)
      .value("InitializationFailed", DeviceInitializationState::InitializationFailed);

// the SWIG wrapper doesn't create enums, it puts them all in the top level
// so for backwards compatibility we define them here as well
#ifdef MATCH_SWIG

  m.attr("UnknownType") = static_cast<int>(MM::DeviceType::UnknownType);
  m.attr("AnyType") = static_cast<int>(MM::DeviceType::AnyType);
  m.attr("CameraDevice") = static_cast<int>(MM::DeviceType::CameraDevice);
  m.attr("ShutterDevice") = static_cast<int>(MM::DeviceType::ShutterDevice);
  m.attr("StateDevice") = static_cast<int>(MM::DeviceType::StateDevice);
  m.attr("StageDevice") = static_cast<int>(MM::DeviceType::StageDevice);
  m.attr("XYStageDevice") = static_cast<int>(MM::DeviceType::XYStageDevice);
  m.attr("SerialDevice") = static_cast<int>(MM::DeviceType::SerialDevice);
  m.attr("GenericDevice") = static_cast<int>(MM::DeviceType::GenericDevice);
  m.attr("AutoFocusDevice") = static_cast<int>(MM::DeviceType::AutoFocusDevice);
  m.attr("CoreDevice") = static_cast<int>(MM::DeviceType::CoreDevice);
  m.attr("ImageProcessorDevice") = static_cast<int>(MM::DeviceType::ImageProcessorDevice);
  m.attr("SignalIODevice") = static_cast<int>(MM::DeviceType::SignalIODevice);
  m.attr("MagnifierDevice") = static_cast<int>(MM::DeviceType::MagnifierDevice);
  m.attr("SLMDevice") = static_cast<int>(MM::DeviceType::SLMDevice);
  m.attr("HubDevice") = static_cast<int>(MM::DeviceType::HubDevice);
  m.attr("GalvoDevice") = static_cast<int>(MM::DeviceType::GalvoDevice);

  m.attr("Undef") = static_cast<int>(MM::PropertyType::Undef);
  m.attr("String") = static_cast<int>(MM::PropertyType::String);
  m.attr("Float") = static_cast<int>(MM::PropertyType::Float);
  m.attr("Integer") = static_cast<int>(MM::PropertyType::Integer);

  m.attr("NoAction") = static_cast<int>(MM::ActionType::NoAction);
  m.attr("BeforeGet") = static_cast<int>(MM::ActionType::BeforeGet);
  m.attr("AfterSet") = static_cast<int>(MM::ActionType::AfterSet);
  m.attr("IsSequenceable") = static_cast<int>(MM::ActionType::IsSequenceable);
  m.attr("AfterLoadSequence") = static_cast<int>(MM::ActionType::AfterLoadSequence);
  m.attr("StartSequence") = static_cast<int>(MM::ActionType::StartSequence);
  m.attr("StopSequence") = static_cast<int>(MM::ActionType::StopSequence);

  m.attr("InvalidPort") = static_cast<int>(MM::PortType::InvalidPort);
  m.attr("SerialPort") = static_cast<int>(MM::PortType::SerialPort);
  m.attr("USBPort") = static_cast<int>(MM::PortType::USBPort);
  m.attr("HIDPort") = static_cast<int>(MM::PortType::HIDPort);

  m.attr("FocusDirectionUnknown") = static_cast<int>(MM::FocusDirection::FocusDirectionUnknown);
  m.attr("FocusDirectionTowardSample") =
      static_cast<int>(MM::FocusDirection::FocusDirectionTowardSample);
  m.attr("FocusDirectionAwayFromSample") =
      static_cast<int>(MM::FocusDirection::FocusDirectionAwayFromSample);

  m.attr("Attention") = static_cast<int>(MM::DeviceNotification::Attention);
  m.attr("Done") = static_cast<int>(MM::DeviceNotification::Done);
  m.attr("StatusChanged") = static_cast<int>(MM::DeviceNotification::StatusChanged);

  m.attr("Unimplemented") = static_cast<int>(MM::DeviceDetectionStatus::Unimplemented);
  m.attr("Misconfigured") = static_cast<int>(MM::DeviceDetectionStatus::Misconfigured);
  m.attr("CanNotCommunicate") = static_cast<int>(MM::DeviceDetectionStatus::CanNotCommunicate);
  m.attr("CanCommunicate") = static_cast<int>(MM::DeviceDetectionStatus::CanCommunicate);

  m.attr("Uninitialized") = static_cast<int>(DeviceInitializationState::Uninitialized);
  m.attr("InitializedSuccessfully") =
      static_cast<int>(DeviceInitializationState::InitializedSuccessfully);
  m.attr("InitializationFailed") =
      static_cast<int>(DeviceInitializationState::InitializationFailed);

#endif

  //////////////////// Supporting classes ////////////////////

  nb::class_<Configuration>(m, "Configuration")
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
      .def("getPropertyValue", &PropertySetting::getPropertyValue, "Returns the property value")
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
      .def("SetReadOnly", &MetadataTag::SetReadOnly, "readOnly"_a, "Sets the read-only status")
      // Virtual functions
      .def("ToSingleTag", &MetadataTag::ToSingleTag,
           "Converts to MetadataSingleTag if applicable")
      .def("ToArrayTag", &MetadataTag::ToArrayTag, "Converts to MetadataArrayTag if applicable")
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
      .def("Restore", nb::overload_cast<const char *>(&MetadataSingleTag::Restore), "stream"_a,
           "Restores from a serialized string");

  nb::class_<MetadataArrayTag, MetadataTag>(m, "MetadataArrayTag")
      .def(nb::init<>(), "Default constructor")
      .def(nb::init<const char *, const char *, bool>(), "name"_a, "device"_a, "readOnly"_a,
           "Parameterized constructor")
      .def("ToArrayTag", &MetadataArrayTag::ToArrayTag,
           "Returns this object as MetadataArrayTag")
      .def("AddValue", &MetadataArrayTag::AddValue, "val"_a, "Adds a value to the array")
      .def("SetValue", &MetadataArrayTag::SetValue, "val"_a, "idx"_a,
           "Sets a value at a specific index")
      .def("GetValue", &MetadataArrayTag::GetValue, "idx"_a, "Gets a value at a specific index")
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

  nb::class_<MMEventCallback, PyMMEventCallback>(m, "MMEventCallback")
      .def(nb::init<>())

      // Virtual methods
      // clang-format off
      NB_DEF_GIL("onPropertiesChanged", &MMEventCallback::onPropertiesChanged,
           "Called when properties are changed")
      NB_DEF_GIL("onPropertyChanged", &MMEventCallback::onPropertyChanged, "name"_a, "propName"_a,
           "propValue"_a, "Called when a specific property is changed")
      NB_DEF_GIL("onChannelGroupChanged", &MMEventCallback::onChannelGroupChanged,
           "newChannelGroupName"_a, "Called when the channel group changes")
      NB_DEF_GIL("onConfigGroupChanged", &MMEventCallback::onConfigGroupChanged, "groupName"_a,
           "newConfigName"_a, "Called when a configuration group changes")
      NB_DEF_GIL("onSystemConfigurationLoaded", &MMEventCallback::onSystemConfigurationLoaded,
           "Called when the system configuration is loaded")
      NB_DEF_GIL("onPixelSizeChanged", &MMEventCallback::onPixelSizeChanged, "newPixelSizeUm"_a,
           "Called when the pixel size changes")
      NB_DEF_GIL("onPixelSizeAffineChanged", &MMEventCallback::onPixelSizeAffineChanged, "v0"_a,
           "v1"_a, "v2"_a, "v3"_a, "v4"_a, "v5"_a,
           "Called when the pixel size affine transformation changes")
      NB_DEF_GIL("onSLMExposureChanged", &MMEventCallback::onSLMExposureChanged, "name"_a,
           "newExposure"_a, "Called when the SLM exposure changes")
      NB_DEF_GIL("onExposureChanged", &MMEventCallback::onExposureChanged, "name"_a, "newExposure"_a,
           "Called when the exposure changes")
      NB_DEF_GIL("onStagePositionChanged", &MMEventCallback::onStagePositionChanged, "name"_a,
           "pos"_a, "Called when the stage position changes")
      NB_DEF_GIL("onXYStagePositionChanged", &MMEventCallback::onXYStagePositionChanged, "name"_a,
           "xpos"_a, "ypos"_a, "Called when the XY stage position changes")
      ;
  // clang-format on

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

  nb::class_<CMMCore>(m, "CMMCore")
      .def(nb::init<>())

      NB_DEF_GIL(
          "loadSystemConfiguration",
          [](CMMCore& self,
             nb::object fileName) {  // accept any object that can be cast to a string (e.g. Path)
                self.loadSystemConfiguration(nb::str(fileName).c_str());
          },
          "fileName"_a)

      NB_DEF_GIL("saveSystemConfiguration", &CMMCore::saveSystemConfiguration, "fileName"_a)
      .def_static("enableFeature", &CMMCore::enableFeature, "name"_a, "enable"_a)
      .def_static("isFeatureEnabled", &CMMCore::isFeatureEnabled, "name"_a)
      NB_DEF_GIL("loadDevice", &CMMCore::loadDevice, "label"_a, "moduleName"_a, "deviceName"_a)
      NB_DEF_GIL("unloadDevice", &CMMCore::unloadDevice, "label"_a)
      NB_DEF_GIL("unloadAllDevices", &CMMCore::unloadAllDevices)
      NB_DEF_GIL("initializeAllDevices", &CMMCore::initializeAllDevices)
      NB_DEF_GIL("initializeDevice", &CMMCore::initializeDevice, "label"_a)
      NB_DEF_GIL("getDeviceInitializationState", &CMMCore::getDeviceInitializationState, "label"_a)
      NB_DEF_GIL("reset", &CMMCore::reset)
      NB_DEF_GIL("unloadLibrary", &CMMCore::unloadLibrary, "moduleName"_a)
      NB_DEF_GIL("updateCoreProperties", &CMMCore::updateCoreProperties)
      NB_DEF_GIL("getCoreErrorText", &CMMCore::getCoreErrorText, "code"_a)
      NB_DEF_GIL("getVersionInfo", &CMMCore::getVersionInfo)
      NB_DEF_GIL("getAPIVersionInfo", &CMMCore::getAPIVersionInfo)
      NB_DEF_GIL("getSystemState", &CMMCore::getSystemState)
      NB_DEF_GIL("setSystemState", &CMMCore::setSystemState, "conf"_a)
      NB_DEF_GIL("getConfigState", &CMMCore::getConfigState, "group"_a, "config"_a)
      NB_DEF_GIL("getConfigGroupState", nb::overload_cast<const char*>(&CMMCore::getConfigGroupState),
           "group"_a)
      NB_DEF_GIL("saveSystemState", &CMMCore::saveSystemState, "fileName"_a)
      NB_DEF_GIL("loadSystemState", &CMMCore::loadSystemState, "fileName"_a)
      NB_DEF_GIL("registerCallback", &CMMCore::registerCallback, "cb"_a)
      NB_DEF_GIL(
          "setPrimaryLogFile",
          [](CMMCore& self,
             nb::object filename,  // accept any object that can be cast to a string (e.g. Path)
             bool truncate) {
                                    self.setPrimaryLogFile(nb::str(filename).c_str(),
                                                           truncate);  // convert to string
          },
          "filename"_a, "truncate"_a = false)

      NB_DEF_GIL("getPrimaryLogFile", &CMMCore::getPrimaryLogFile)
      NB_DEF_GIL("logMessage", nb::overload_cast<const char*>(&CMMCore::logMessage), "msg"_a)
      NB_DEF_GIL("logMessage", nb::overload_cast<const char*, bool>(&CMMCore::logMessage), "msg"_a,
           "debugOnly"_a)

      NB_DEF_GIL("enableDebugLog", &CMMCore::enableDebugLog, "enable"_a)
      NB_DEF_GIL("debugLogEnabled", &CMMCore::debugLogEnabled)
      NB_DEF_GIL("enableStderrLog", &CMMCore::enableStderrLog, "enable"_a)
      NB_DEF_GIL("stderrLogEnabled", &CMMCore::stderrLogEnabled)
      NB_DEF_GIL(
          "startSecondaryLogFile",
          [](CMMCore& self,
             nb::object filename,  // accept any object that can be cast to a string (e.g. Path)
             bool enableDebug, bool truncate, bool synchronous) {
                                                        return self.startSecondaryLogFile(
                                                            nb::str(filename).c_str(),
                                                            enableDebug, truncate, synchronous);
          },
          "filename"_a, "enableDebug"_a, "truncate"_a = true, "synchronous"_a = false)
      NB_DEF_GIL("stopSecondaryLogFile", &CMMCore::stopSecondaryLogFile, "handle"_a)

      NB_DEF_GIL("getDeviceAdapterSearchPaths", &CMMCore::getDeviceAdapterSearchPaths)
      NB_DEF_GIL("setDeviceAdapterSearchPaths", &CMMCore::setDeviceAdapterSearchPaths, "paths"_a)
      NB_DEF_GIL("getDeviceAdapterNames", &CMMCore::getDeviceAdapterNames)
      NB_DEF_GIL("getAvailableDevices", &CMMCore::getAvailableDevices, "library"_a)
      NB_DEF_GIL("getAvailableDeviceDescriptions", &CMMCore::getAvailableDeviceDescriptions, "library"_a)
      NB_DEF_GIL("getAvailableDeviceTypes", &CMMCore::getAvailableDeviceTypes, "library"_a)
      NB_DEF_GIL("getLoadedDevices", &CMMCore::getLoadedDevices)
      NB_DEF_GIL("getLoadedDevicesOfType", &CMMCore::getLoadedDevicesOfType, "devType"_a)
      NB_DEF_GIL("getDeviceType", &CMMCore::getDeviceType, "label"_a)
      NB_DEF_GIL("getDeviceLibrary", &CMMCore::getDeviceLibrary, "label"_a)
      NB_DEF_GIL("getDeviceName", nb::overload_cast<const char*>(&CMMCore::getDeviceName), "label"_a)
      NB_DEF_GIL("getDeviceDescription", &CMMCore::getDeviceDescription, "label"_a)
      NB_DEF_GIL("getDevicePropertyNames", &CMMCore::getDevicePropertyNames, "label"_a)
      NB_DEF_GIL("hasProperty", &CMMCore::hasProperty, "label"_a, "propName"_a)
      NB_DEF_GIL("getProperty", &CMMCore::getProperty, "label"_a, "propName"_a)
      NB_DEF_GIL("setProperty",
           nb::overload_cast<const char*, const char*, const char*>(&CMMCore::setProperty),
           "label"_a, "propName"_a, "propValue"_a)
      NB_DEF_GIL("setProperty", nb::overload_cast<const char*, const char*, bool>(&CMMCore::setProperty),
           "label"_a, "propName"_a, "propValue"_a)
      NB_DEF_GIL("setProperty", nb::overload_cast<const char*, const char*, long>(&CMMCore::setProperty),
           "label"_a, "propName"_a, "propValue"_a)
      NB_DEF_GIL("setProperty",
           nb::overload_cast<const char*, const char*, float>(&CMMCore::setProperty), "label"_a,
           "propName"_a, "propValue"_a)
      NB_DEF_GIL("getAllowedPropertyValues", &CMMCore::getAllowedPropertyValues, "label"_a, "propName"_a)
      NB_DEF_GIL("isPropertyReadOnly", &CMMCore::isPropertyReadOnly, "label"_a, "propName"_a)
      NB_DEF_GIL("isPropertyPreInit", &CMMCore::isPropertyPreInit, "label"_a, "propName"_a)
      NB_DEF_GIL("isPropertySequenceable", &CMMCore::isPropertySequenceable, "label"_a, "propName"_a)
      NB_DEF_GIL("hasPropertyLimits", &CMMCore::hasPropertyLimits, "label"_a, "propName"_a)
      NB_DEF_GIL("getPropertyLowerLimit", &CMMCore::getPropertyLowerLimit, "label"_a, "propName"_a)
      NB_DEF_GIL("getPropertyUpperLimit", &CMMCore::getPropertyUpperLimit, "label"_a, "propName"_a)
      NB_DEF_GIL("getPropertyType", &CMMCore::getPropertyType, "label"_a, "propName"_a)
      NB_DEF_GIL("startPropertySequence", &CMMCore::startPropertySequence, "label"_a, "propName"_a)
      NB_DEF_GIL("stopPropertySequence", &CMMCore::stopPropertySequence, "label"_a, "propName"_a)
      NB_DEF_GIL("getPropertySequenceMaxLength", &CMMCore::getPropertySequenceMaxLength, "label"_a,
           "propName"_a)
      NB_DEF_GIL("loadPropertySequence", &CMMCore::loadPropertySequence, "label"_a, "propName"_a,
           "eventSequence"_a)
      NB_DEF_GIL("deviceBusy", &CMMCore::deviceBusy, "label"_a)
      NB_DEF_GIL("waitForDevice", nb::overload_cast<const char*>(&CMMCore::waitForDevice), "label"_a)
      NB_DEF_GIL("waitForConfig", &CMMCore::waitForConfig, "group"_a, "configName"_a)
      NB_DEF_GIL("systemBusy", &CMMCore::systemBusy)
      NB_DEF_GIL("waitForSystem", &CMMCore::waitForSystem)
      NB_DEF_GIL("deviceTypeBusy", &CMMCore::deviceTypeBusy, "devType"_a)
      NB_DEF_GIL("waitForDeviceType", &CMMCore::waitForDeviceType, "devType"_a)
      NB_DEF_GIL("getDeviceDelayMs", &CMMCore::getDeviceDelayMs, "label"_a)
      NB_DEF_GIL("setDeviceDelayMs", &CMMCore::setDeviceDelayMs, "label"_a, "delayMs"_a)
      NB_DEF_GIL("usesDeviceDelay", &CMMCore::usesDeviceDelay, "label"_a)
      NB_DEF_GIL("setTimeoutMs", &CMMCore::setTimeoutMs, "timeoutMs"_a)
      NB_DEF_GIL("getTimeoutMs", &CMMCore::getTimeoutMs)
      NB_DEF_GIL("sleep", &CMMCore::sleep, "intervalMs"_a)

      NB_DEF_GIL("getCameraDevice", &CMMCore::getCameraDevice)
      NB_DEF_GIL("getShutterDevice", &CMMCore::getShutterDevice)
      NB_DEF_GIL("getFocusDevice", &CMMCore::getFocusDevice)
      NB_DEF_GIL("getXYStageDevice", &CMMCore::getXYStageDevice)
      NB_DEF_GIL("getAutoFocusDevice", &CMMCore::getAutoFocusDevice)
      NB_DEF_GIL("getImageProcessorDevice", &CMMCore::getImageProcessorDevice)
      NB_DEF_GIL("getSLMDevice", &CMMCore::getSLMDevice)
      NB_DEF_GIL("getGalvoDevice", &CMMCore::getGalvoDevice)
      NB_DEF_GIL("getChannelGroup", &CMMCore::getChannelGroup)
      NB_DEF_GIL("setCameraDevice", &CMMCore::setCameraDevice, "cameraLabel"_a)
      NB_DEF_GIL("setShutterDevice", &CMMCore::setShutterDevice, "shutterLabel"_a)
      NB_DEF_GIL("setFocusDevice", &CMMCore::setFocusDevice, "focusLabel"_a)
      NB_DEF_GIL("setXYStageDevice", &CMMCore::setXYStageDevice, "xyStageLabel"_a)
      NB_DEF_GIL("setAutoFocusDevice", &CMMCore::setAutoFocusDevice, "focusLabel"_a)
      NB_DEF_GIL("setImageProcessorDevice", &CMMCore::setImageProcessorDevice, "procLabel"_a)
      NB_DEF_GIL("setSLMDevice", &CMMCore::setSLMDevice, "slmLabel"_a)
      NB_DEF_GIL("setGalvoDevice", &CMMCore::setGalvoDevice, "galvoLabel"_a)
      NB_DEF_GIL("setChannelGroup", &CMMCore::setChannelGroup, "channelGroup"_a)

      NB_DEF_GIL("getSystemStateCache", &CMMCore::getSystemStateCache)
      NB_DEF_GIL("updateSystemStateCache", &CMMCore::updateSystemStateCache)
      NB_DEF_GIL("getPropertyFromCache", &CMMCore::getPropertyFromCache, "deviceLabel"_a, "propName"_a)
      NB_DEF_GIL("getCurrentConfigFromCache", &CMMCore::getCurrentConfigFromCache, "groupName"_a)
      NB_DEF_GIL("getConfigGroupStateFromCache", &CMMCore::getConfigGroupStateFromCache, "group"_a)

      NB_DEF_GIL("defineConfig", nb::overload_cast<const char*, const char*>(&CMMCore::defineConfig),
           "groupName"_a, "configName"_a)
      NB_DEF_GIL("defineConfig",
           nb::overload_cast<const char*, const char*, const char*, const char*, const char*>(
               &CMMCore::defineConfig),
           "groupName"_a, "configName"_a, "deviceLabel"_a, "propName"_a, "value"_a)
      NB_DEF_GIL("defineConfigGroup", &CMMCore::defineConfigGroup, "groupName"_a)
      NB_DEF_GIL("deleteConfigGroup", &CMMCore::deleteConfigGroup, "groupName"_a)
      NB_DEF_GIL("renameConfigGroup", &CMMCore::renameConfigGroup, "oldGroupName"_a, "newGroupName"_a)
      NB_DEF_GIL("isGroupDefined", &CMMCore::isGroupDefined, "groupName"_a)
      NB_DEF_GIL("isConfigDefined", &CMMCore::isConfigDefined, "groupName"_a, "configName"_a)
      NB_DEF_GIL("setConfig", &CMMCore::setConfig, "groupName"_a, "configName"_a)

      NB_DEF_GIL("deleteConfig", nb::overload_cast<const char*, const char*>(&CMMCore::deleteConfig),
           "groupName"_a, "configName"_a)
      NB_DEF_GIL("deleteConfig",
           nb::overload_cast<const char*, const char*, const char*, const char*>(
               &CMMCore::deleteConfig),
           "groupName"_a, "configName"_a, "deviceLabel"_a, "propName"_a)

      NB_DEF_GIL("renameConfig", &CMMCore::renameConfig, "groupName"_a, "oldConfigName"_a,
           "newConfigName"_a)
      NB_DEF_GIL("getAvailableConfigGroups", &CMMCore::getAvailableConfigGroups)
      NB_DEF_GIL("getAvailableConfigs", &CMMCore::getAvailableConfigs, "configGroup"_a)
      NB_DEF_GIL("getCurrentConfig", &CMMCore::getCurrentConfig, "groupName"_a)
      NB_DEF_GIL("getConfigData", &CMMCore::getConfigData, "configGroup"_a, "configName"_a)

      NB_DEF_GIL("getCurrentPixelSizeConfig", nb::overload_cast<>(&CMMCore::getCurrentPixelSizeConfig))
      NB_DEF_GIL("getCurrentPixelSizeConfig",
           nb::overload_cast<bool>(&CMMCore::getCurrentPixelSizeConfig), "cached"_a)
      NB_DEF_GIL("getPixelSizeUm", nb::overload_cast<>(&CMMCore::getPixelSizeUm))
      NB_DEF_GIL("getPixelSizeUm", nb::overload_cast<bool>(&CMMCore::getPixelSizeUm), "cached"_a)
      NB_DEF_GIL("getPixelSizeUmByID", &CMMCore::getPixelSizeUmByID, "resolutionID"_a)
      NB_DEF_GIL("getPixelSizeAffine", nb::overload_cast<>(&CMMCore::getPixelSizeAffine))
      NB_DEF_GIL("getPixelSizeAffine", nb::overload_cast<bool>(&CMMCore::getPixelSizeAffine), "cached"_a)
      NB_DEF_GIL("getPixelSizeAffineByID", &CMMCore::getPixelSizeAffineByID, "resolutionID"_a)
      NB_DEF_GIL("getMagnificationFactor", &CMMCore::getMagnificationFactor)
      NB_DEF_GIL("setPixelSizeUm", &CMMCore::setPixelSizeUm, "resolutionID"_a, "pixSize"_a)
      NB_DEF_GIL("setPixelSizeAffine", &CMMCore::setPixelSizeAffine, "resolutionID"_a, "affine"_a)
      NB_DEF_GIL("definePixelSizeConfig",
           nb::overload_cast<const char*, const char*, const char*, const char*>(
               &CMMCore::definePixelSizeConfig),
           "resolutionID"_a, "deviceLabel"_a, "propName"_a, "value"_a)
      NB_DEF_GIL("definePixelSizeConfig",
           nb::overload_cast<const char*>(&CMMCore::definePixelSizeConfig), "resolutionID"_a)
      NB_DEF_GIL("getAvailablePixelSizeConfigs", &CMMCore::getAvailablePixelSizeConfigs)
      NB_DEF_GIL("isPixelSizeConfigDefined", &CMMCore::isPixelSizeConfigDefined, "resolutionID"_a)
      NB_DEF_GIL("setPixelSizeConfig", &CMMCore::setPixelSizeConfig, "resolutionID"_a)
      NB_DEF_GIL("renamePixelSizeConfig", &CMMCore::renamePixelSizeConfig, "oldConfigName"_a,
           "newConfigName"_a)
      NB_DEF_GIL("deletePixelSizeConfig", &CMMCore::deletePixelSizeConfig, "configName"_a)
      NB_DEF_GIL("getPixelSizeConfigData", &CMMCore::getPixelSizeConfigData, "configName"_a)

      // Image Acquisition Methods
      NB_DEF_GIL("setROI", nb::overload_cast<int, int, int, int>(&CMMCore::setROI), "x"_a, "y"_a,
           "xSize"_a, "ySize"_a)
      NB_DEF_GIL("setROI", nb::overload_cast<const char*, int, int, int, int>(&CMMCore::setROI),
           "label"_a, "x"_a, "y"_a, "xSize"_a, "ySize"_a)
      NB_DEF_GIL("getROI",
           [](CMMCore& self) {
                int x, y, xSize, ySize;
                self.getROI(x, y, xSize, ySize);             // Call C++ method
                return std::make_tuple(x, y, xSize, ySize);  // Return a tuple
           })
      NB_DEF_GIL(
          "getROI",
          [](CMMCore& self, const char* label) {
                    int x, y, xSize, ySize;
                    self.getROI(label, x, y, xSize, ySize);  // Call the C++ method
                    return std::make_tuple(x, y, xSize,
                                           ySize);  // Return as Python tuple
          },
          "label"_a)
      NB_DEF_GIL("clearROI", &CMMCore::clearROI)
      NB_DEF_GIL("isMultiROISupported", &CMMCore::isMultiROISupported)
      NB_DEF_GIL("isMultiROIEnabled", &CMMCore::isMultiROIEnabled)
      NB_DEF_GIL("setMultiROI", &CMMCore::setMultiROI, "xs"_a, "ys"_a, "widths"_a, "heights"_a)
      NB_DEF_GIL("getMultiROI",
           [](CMMCore& self) -> std::tuple<std::vector<unsigned>, std::vector<unsigned>, std::vector<unsigned>,
                                           std::vector<unsigned>> {
                                std::vector<unsigned> xs, ys, widths, heights;
                                self.getMultiROI(xs, ys, widths, heights);
                                return {xs, ys, widths, heights};
           })

      NB_DEF_GIL("setExposure", nb::overload_cast<double>(&CMMCore::setExposure), "exp"_a)
      NB_DEF_GIL("setExposure", nb::overload_cast<const char*, double>(&CMMCore::setExposure),
           "cameraLabel"_a, "dExp"_a)
      NB_DEF_GIL("getExposure", nb::overload_cast<>(&CMMCore::getExposure))
      NB_DEF_GIL("getExposure", nb::overload_cast<const char*>(&CMMCore::getExposure), "label"_a)
      NB_DEF_GIL("snapImage", &CMMCore::snapImage)
      NB_DEF_GIL("getImage",
           [](CMMCore& self) -> np_array {
                                            return create_image_array(self, self.getImage()); })
      NB_DEF_GIL("getImage",
           [](CMMCore& self, unsigned channel) -> np_array {
                                                return create_image_array(
                                                    self, self.getImage(channel));
           })
      NB_DEF_GIL("getImageWidth", &CMMCore::getImageWidth)
      NB_DEF_GIL("getImageHeight", &CMMCore::getImageHeight)
      NB_DEF_GIL("getBytesPerPixel", &CMMCore::getBytesPerPixel)
      NB_DEF_GIL("getImageBitDepth", &CMMCore::getImageBitDepth)
      NB_DEF_GIL("getNumberOfComponents", &CMMCore::getNumberOfComponents)
      NB_DEF_GIL("getNumberOfCameraChannels", &CMMCore::getNumberOfCameraChannels)
      NB_DEF_GIL("getCameraChannelName", &CMMCore::getCameraChannelName, "channelNr"_a)
      NB_DEF_GIL("getImageBufferSize", &CMMCore::getImageBufferSize)
      NB_DEF_GIL("setAutoShutter", &CMMCore::setAutoShutter, "state"_a)
      NB_DEF_GIL("getAutoShutter", &CMMCore::getAutoShutter)
      NB_DEF_GIL("setShutterOpen", nb::overload_cast<bool>(&CMMCore::setShutterOpen), "state"_a)
      NB_DEF_GIL("getShutterOpen", nb::overload_cast<>(&CMMCore::getShutterOpen))
      NB_DEF_GIL("setShutterOpen", nb::overload_cast<const char*, bool>(&CMMCore::setShutterOpen),
           "shutterLabel"_a, "state"_a)
      NB_DEF_GIL("getShutterOpen", nb::overload_cast<const char*>(&CMMCore::getShutterOpen),
           "shutterLabel"_a)
      NB_DEF_GIL("startSequenceAcquisition",
           nb::overload_cast<long, double, bool>(&CMMCore::startSequenceAcquisition),
           "numImages"_a, "intervalMs"_a, "stopOnOverflow"_a)
      NB_DEF_GIL("startSequenceAcquisition",
           nb::overload_cast<const char*, long, double, bool>(&CMMCore::startSequenceAcquisition),
           "cameraLabel"_a, "numImages"_a, "intervalMs"_a, "stopOnOverflow"_a)
      NB_DEF_GIL("prepareSequenceAcquisition", &CMMCore::prepareSequenceAcquisition, "cameraLabel"_a)
      NB_DEF_GIL("startContinuousSequenceAcquisition", &CMMCore::startContinuousSequenceAcquisition,
           "intervalMs"_a)
      NB_DEF_GIL("stopSequenceAcquisition", nb::overload_cast<>(&CMMCore::stopSequenceAcquisition))
      NB_DEF_GIL("stopSequenceAcquisition",
           nb::overload_cast<const char*>(&CMMCore::stopSequenceAcquisition), "cameraLabel"_a)
      NB_DEF_GIL("isSequenceRunning", nb::overload_cast<>(&CMMCore::isSequenceRunning))
      NB_DEF_GIL("isSequenceRunning", nb::overload_cast<const char*>(&CMMCore::isSequenceRunning),
           "cameraLabel"_a)
      NB_DEF_GIL("getLastImage",
           [](CMMCore& self) -> np_array {
                                                                                                                                        return create_image_array(
                                                                                                                                            self,
                                                                                                                                            self.getLastImage());
           })
      NB_DEF_GIL("popNextImage",
           [](CMMCore& self) -> np_array {
                                                                                                                                            return create_image_array(
                                                                                                                                                self,
                                                                                                                                                self.popNextImage());
           })
      // this is a new overload that returns both the image and the metadata
      // not present in the original C++ API
      NB_DEF_GIL(
          "getLastImageMD",
          [](CMMCore& self) -> std::tuple<np_array, Metadata> {
            Metadata md;
            auto img = self.getLastImageMD(md);
            return {create_metadata_array(self, img, md), md};
          },
          "Get the last image in the circular buffer, return as tuple of image and metadata")
      NB_DEF_GIL(
          "getLastImageMD",
          [](CMMCore& self, Metadata& md) -> np_array {
                auto img = self.getLastImageMD(md);
                return create_metadata_array(self, img, md);
          },
          "md"_a,
          "Get the last image in the circular buffer, store metadata in the provided object")
      NB_DEF_GIL(
          "getLastImageMD",
          [](CMMCore& self, unsigned channel,
             unsigned slice) -> std::tuple<np_array, Metadata> {
                    Metadata md;
                    auto img = self.getLastImageMD(channel, slice, md);
                    return {create_metadata_array(self, img, md), md};
          },
          "channel"_a, "slice"_a,
          "Get the last image in the circular buffer for a specific channel and slice, return"
          "as tuple of image and metadata")
      NB_DEF_GIL(
          "getLastImageMD",
          [](CMMCore& self, unsigned channel, unsigned slice, Metadata& md) -> np_array {
                        auto img = self.getLastImageMD(channel, slice, md);
                        return create_metadata_array(self, img, md);
          },
          "channel"_a, "slice"_a, "md"_a,
          "Get the last image in the circular buffer for a specific channel and slice, store "
          "metadata in the provided object")

      NB_DEF_GIL(
          "popNextImageMD",
          [](CMMCore& self) -> std::tuple<np_array, Metadata> {
                            Metadata md;
                            auto img = self.popNextImageMD(md);
                            return {create_metadata_array(self, img, md), md};
          },
          "Get the last image in the circular buffer, return as tuple of image and metadata")
      NB_DEF_GIL(
          "popNextImageMD",
          [](CMMCore& self, Metadata& md) -> np_array {
                                auto img = self.popNextImageMD(md);
                                return create_metadata_array(self, img, md);
          },
          "md"_a,
          "Get the last image in the circular buffer, store metadata in the provided object")
      NB_DEF_GIL(
          "popNextImageMD",
          [](CMMCore& self, unsigned channel,
             unsigned slice) -> std::tuple<np_array, Metadata> {
                                    Metadata md;
                                    auto img = self.popNextImageMD(channel, slice, md);
                                    return {create_metadata_array(self, img, md), md};
          },
          "channel"_a, "slice"_a,
          "Get the last image in the circular buffer for a specific channel and slice, return"
          "as tuple of image and metadata")
      NB_DEF_GIL(
          "popNextImageMD",
          [](CMMCore& self, unsigned channel, unsigned slice, Metadata& md) -> np_array {
                                        auto img = self.popNextImageMD(channel, slice, md);
                                        return create_metadata_array(self, img, md);
          },
          "channel"_a, "slice"_a, "md"_a,
          "Get the last image in the circular buffer for a specific channel and slice, store "
          "metadata in the provided object")

      NB_DEF_GIL(
          "getNBeforeLastImageMD",
          [](CMMCore& self, unsigned long n) -> std::tuple<np_array, Metadata> {
                                            Metadata md;
                                            auto img = self.getNBeforeLastImageMD(n, md);
                                            return {create_metadata_array(self, img, md), md};
          },
          "n"_a,
          "Get the nth image before the last image in the circular buffer and return it as a "
          "tuple "
          "of image and metadata")
      NB_DEF_GIL(
          "getNBeforeLastImageMD",
          [](CMMCore& self, unsigned long n, Metadata& md) -> np_array {
                                                auto img = self.getNBeforeLastImageMD(n, md);
                                                return create_metadata_array(self, img, md);
          },
          "n"_a, "md"_a,
          "Get the nth image before the last image in the circular buffer and store the metadata "
          "in the provided object")

      // Circular Buffer Methods
      NB_DEF_GIL("getRemainingImageCount", &CMMCore::getRemainingImageCount)
      NB_DEF_GIL("getBufferTotalCapacity", &CMMCore::getBufferTotalCapacity)
      NB_DEF_GIL("getBufferFreeCapacity", &CMMCore::getBufferFreeCapacity)
      NB_DEF_GIL("isBufferOverflowed", &CMMCore::isBufferOverflowed)
      NB_DEF_GIL("setCircularBufferMemoryFootprint", &CMMCore::setCircularBufferMemoryFootprint,
           "sizeMB"_a)
      NB_DEF_GIL("getCircularBufferMemoryFootprint", &CMMCore::getCircularBufferMemoryFootprint)
      NB_DEF_GIL("initializeCircularBuffer", &CMMCore::initializeCircularBuffer)
      NB_DEF_GIL("clearCircularBuffer", &CMMCore::clearCircularBuffer)

      // Exposure Sequence Methods
      NB_DEF_GIL("isExposureSequenceable", &CMMCore::isExposureSequenceable, "cameraLabel"_a)
      NB_DEF_GIL("startExposureSequence", &CMMCore::startExposureSequence, "cameraLabel"_a)
      NB_DEF_GIL("stopExposureSequence", &CMMCore::stopExposureSequence, "cameraLabel"_a)
      NB_DEF_GIL("getExposureSequenceMaxLength", &CMMCore::getExposureSequenceMaxLength, "cameraLabel"_a)
      NB_DEF_GIL("loadExposureSequence", &CMMCore::loadExposureSequence, "cameraLabel"_a,
           "exposureSequence_ms"_a)

      // Autofocus Methods
      NB_DEF_GIL("getLastFocusScore", &CMMCore::getLastFocusScore)
      NB_DEF_GIL("getCurrentFocusScore", &CMMCore::getCurrentFocusScore)
      NB_DEF_GIL("enableContinuousFocus", &CMMCore::enableContinuousFocus, "enable"_a)
      NB_DEF_GIL("isContinuousFocusEnabled", &CMMCore::isContinuousFocusEnabled)
      NB_DEF_GIL("isContinuousFocusLocked", &CMMCore::isContinuousFocusLocked)
      NB_DEF_GIL("isContinuousFocusDrive", &CMMCore::isContinuousFocusDrive, "stageLabel"_a)
      NB_DEF_GIL("fullFocus", &CMMCore::fullFocus)
      NB_DEF_GIL("incrementalFocus", &CMMCore::incrementalFocus)
      NB_DEF_GIL("setAutoFocusOffset", &CMMCore::setAutoFocusOffset, "offset"_a)
      NB_DEF_GIL("getAutoFocusOffset", &CMMCore::getAutoFocusOffset)

      // State Device Control Methods
      NB_DEF_GIL("setState", &CMMCore::setState, "stateDeviceLabel"_a, "state"_a)
      NB_DEF_GIL("getState", &CMMCore::getState, "stateDeviceLabel"_a)
      NB_DEF_GIL("getNumberOfStates", &CMMCore::getNumberOfStates, "stateDeviceLabel"_a)
      NB_DEF_GIL("setStateLabel", &CMMCore::setStateLabel, "stateDeviceLabel"_a, "stateLabel"_a)
      NB_DEF_GIL("getStateLabel", &CMMCore::getStateLabel, "stateDeviceLabel"_a)
      NB_DEF_GIL("defineStateLabel", &CMMCore::defineStateLabel, "stateDeviceLabel"_a, "state"_a,
           "stateLabel"_a)
      NB_DEF_GIL("getStateLabels", &CMMCore::getStateLabels, "stateDeviceLabel"_a)
      NB_DEF_GIL("getStateFromLabel", &CMMCore::getStateFromLabel, "stateDeviceLabel"_a, "stateLabel"_a)

      // Stage Control Methods
      NB_DEF_GIL("setPosition", nb::overload_cast<const char*, double>(&CMMCore::setPosition),
           "stageLabel"_a, "position"_a)
      NB_DEF_GIL("setPosition", nb::overload_cast<double>(&CMMCore::setPosition), "position"_a)
      NB_DEF_GIL("getPosition", nb::overload_cast<const char*>(&CMMCore::getPosition), "stageLabel"_a)
      NB_DEF_GIL("getPosition", nb::overload_cast<>(&CMMCore::getPosition))
      NB_DEF_GIL("setRelativePosition",
           nb::overload_cast<const char*, double>(&CMMCore::setRelativePosition), "stageLabel"_a,
           "d"_a)
      NB_DEF_GIL("setRelativePosition", nb::overload_cast<double>(&CMMCore::setRelativePosition), "d"_a)
      NB_DEF_GIL("setOrigin", nb::overload_cast<const char*>(&CMMCore::setOrigin), "stageLabel"_a)
      NB_DEF_GIL("setOrigin", nb::overload_cast<>(&CMMCore::setOrigin))
      NB_DEF_GIL("setAdapterOrigin", nb::overload_cast<const char*, double>(&CMMCore::setAdapterOrigin),
           "stageLabel"_a, "newZUm"_a)
      NB_DEF_GIL("setAdapterOrigin", nb::overload_cast<double>(&CMMCore::setAdapterOrigin), "newZUm"_a)

      // Focus Direction Methods
      NB_DEF_GIL("setFocusDirection", &CMMCore::setFocusDirection, "stageLabel"_a, "sign"_a)
      NB_DEF_GIL("getFocusDirection", &CMMCore::getFocusDirection, "stageLabel"_a)

      // Stage Sequence Methods
      NB_DEF_GIL("isStageSequenceable", &CMMCore::isStageSequenceable, "stageLabel"_a)
      NB_DEF_GIL("isStageLinearSequenceable", &CMMCore::isStageLinearSequenceable, "stageLabel"_a)
      NB_DEF_GIL("startStageSequence", &CMMCore::startStageSequence, "stageLabel"_a)
      NB_DEF_GIL("stopStageSequence", &CMMCore::stopStageSequence, "stageLabel"_a)
      NB_DEF_GIL("getStageSequenceMaxLength", &CMMCore::getStageSequenceMaxLength, "stageLabel"_a)
      NB_DEF_GIL("loadStageSequence", &CMMCore::loadStageSequence, "stageLabel"_a, "positionSequence"_a)
      NB_DEF_GIL("setStageLinearSequence", &CMMCore::setStageLinearSequence, "stageLabel"_a, "dZ_um"_a,
           "nSlices"_a)

      // XY Stage Control Methods
      NB_DEF_GIL("setXYPosition",
           nb::overload_cast<const char*, double, double>(&CMMCore::setXYPosition),
           "xyStageLabel"_a, "x"_a, "y"_a)
      NB_DEF_GIL("setXYPosition", nb::overload_cast<double, double>(&CMMCore::setXYPosition), "x"_a,
           "y"_a)
      NB_DEF_GIL("setRelativeXYPosition",
           nb::overload_cast<const char*, double, double>(&CMMCore::setRelativeXYPosition),
           "xyStageLabel"_a, "dx"_a, "dy"_a)
      NB_DEF_GIL("setRelativeXYPosition",
           nb::overload_cast<double, double>(&CMMCore::setRelativeXYPosition), "dx"_a, "dy"_a)

      NB_DEF_GIL("getXYPosition",
           [](CMMCore& self, const char* xyStageLabel) -> std::tuple<double, double> {
                    double x, y;
                    self.getXYPosition(xyStageLabel, x, y);
                    return {x, y};
           },
           "xyStageLabel"_a)
          NB_DEF_GIL("getXYPosition",
               [](CMMCore& self) -> std::tuple<double, double> {
                        double x, y;
                        self.getXYPosition(x, y);
                        return {x, y};
               })
      NB_DEF_GIL("getXPosition", nb::overload_cast<const char*>(&CMMCore::getXPosition),
           "xyStageLabel"_a)
      NB_DEF_GIL("getYPosition", nb::overload_cast<const char*>(&CMMCore::getYPosition),
           "xyStageLabel"_a)
      NB_DEF_GIL("getXPosition", nb::overload_cast<>(&CMMCore::getXPosition))
      NB_DEF_GIL("getYPosition", nb::overload_cast<>(&CMMCore::getYPosition))
      NB_DEF_GIL("stop", &CMMCore::stop, "xyOrZStageLabel"_a)
      NB_DEF_GIL("home", &CMMCore::home, "xyOrZStageLabel"_a)
      NB_DEF_GIL("setOriginXY", nb::overload_cast<const char*>(&CMMCore::setOriginXY), "xyStageLabel"_a)
      NB_DEF_GIL("setOriginXY", nb::overload_cast<>(&CMMCore::setOriginXY))
      NB_DEF_GIL("setOriginX", nb::overload_cast<const char*>(&CMMCore::setOriginX), "xyStageLabel"_a)
      NB_DEF_GIL("setOriginX", nb::overload_cast<>(&CMMCore::setOriginX))
      NB_DEF_GIL("setOriginY", nb::overload_cast<const char*>(&CMMCore::setOriginY), "xyStageLabel"_a)
      NB_DEF_GIL("setOriginY", nb::overload_cast<>(&CMMCore::setOriginY))
      NB_DEF_GIL("setAdapterOriginXY",
           nb::overload_cast<const char*, double, double>(&CMMCore::setAdapterOriginXY),
           "xyStageLabel"_a, "newXUm"_a, "newYUm"_a)
      NB_DEF_GIL("setAdapterOriginXY", nb::overload_cast<double, double>(&CMMCore::setAdapterOriginXY),
           "newXUm"_a, "newYUm"_a)

      // XY Stage Sequence Methods
      NB_DEF_GIL("isXYStageSequenceable", &CMMCore::isXYStageSequenceable, "xyStageLabel"_a)
      NB_DEF_GIL("startXYStageSequence", &CMMCore::startXYStageSequence, "xyStageLabel"_a)
      NB_DEF_GIL("stopXYStageSequence", &CMMCore::stopXYStageSequence, "xyStageLabel"_a)
      NB_DEF_GIL("getXYStageSequenceMaxLength", &CMMCore::getXYStageSequenceMaxLength, "xyStageLabel"_a)
      NB_DEF_GIL("loadXYStageSequence", &CMMCore::loadXYStageSequence, "xyStageLabel"_a, "xSequence"_a,
           "ySequence"_a)

      // Serial Port Control
      NB_DEF_GIL("setSerialProperties", &CMMCore::setSerialProperties, "portName"_a, "answerTimeout"_a,
           "baudRate"_a, "delayBetweenCharsMs"_a, "handshaking"_a, "parity"_a, "stopBits"_a)
      NB_DEF_GIL("setSerialPortCommand", &CMMCore::setSerialPortCommand, "portLabel"_a, "command"_a,
           "term"_a)
      NB_DEF_GIL("getSerialPortAnswer", &CMMCore::getSerialPortAnswer, "portLabel"_a, "term"_a)
      NB_DEF_GIL("writeToSerialPort", &CMMCore::writeToSerialPort, "portLabel"_a, "data"_a)
      NB_DEF_GIL("readFromSerialPort", &CMMCore::readFromSerialPort, "portLabel"_a)

      // SLM Control
      // setSLMImage accepts a second argument (pixels) of either unsigned char* or unsigned int*
      NB_DEF_GIL("setSLMImage", [](CMMCore& self, const char* slmLabel, const nb::ndarray<uint8_t> &pixels) -> void
          {
            long expectedWidth = self.getSLMWidth(slmLabel);
            long expectedHeight = self.getSLMHeight(slmLabel);
            long bytesPerPixel = self.getSLMBytesPerPixel(slmLabel);
            validate_slm_image(pixels, expectedWidth, expectedHeight, bytesPerPixel);

            // Cast the numpy array to a pointer to unsigned char
            self.setSLMImage(slmLabel, reinterpret_cast<unsigned char *>(pixels.data()));
          },
           "slmLabel"_a, "pixels"_a)
      NB_DEF_GIL("setSLMPixelsTo",
           nb::overload_cast<const char*, unsigned char>(&CMMCore::setSLMPixelsTo), "slmLabel"_a,
           "intensity"_a)
      NB_DEF_GIL("setSLMPixelsTo",
           nb::overload_cast<const char*, unsigned char, unsigned char, unsigned char>(
               &CMMCore::setSLMPixelsTo),
           "slmLabel"_a, "red"_a, "green"_a, "blue"_a)
      NB_DEF_GIL("displaySLMImage", &CMMCore::displaySLMImage, "slmLabel"_a)
      NB_DEF_GIL("setSLMExposure", &CMMCore::setSLMExposure, "slmLabel"_a, "exposure_ms"_a)
      NB_DEF_GIL("getSLMExposure", &CMMCore::getSLMExposure, "slmLabel"_a)
      NB_DEF_GIL("getSLMWidth", &CMMCore::getSLMWidth, "slmLabel"_a)
      NB_DEF_GIL("getSLMHeight", &CMMCore::getSLMHeight, "slmLabel"_a)
      NB_DEF_GIL("getSLMNumberOfComponents", &CMMCore::getSLMNumberOfComponents, "slmLabel"_a)
      NB_DEF_GIL("getSLMBytesPerPixel", &CMMCore::getSLMBytesPerPixel, "slmLabel"_a)
      // SLM Sequence
      NB_DEF_GIL("getSLMSequenceMaxLength", &CMMCore::getSLMSequenceMaxLength, "slmLabel"_a)
      NB_DEF_GIL("startSLMSequence", &CMMCore::startSLMSequence, "slmLabel"_a)
      NB_DEF_GIL("stopSLMSequence", &CMMCore::stopSLMSequence, "slmLabel"_a)
      NB_DEF_GIL("loadSLMSequence", [](CMMCore& self, const char* slmLabel, std::vector<nb::ndarray<uint8_t>> &imageSequence) -> void {
                    long expectedWidth = self.getSLMWidth(slmLabel);
                    long expectedHeight = self.getSLMHeight(slmLabel);
                    long bytesPerPixel = self.getSLMBytesPerPixel(slmLabel);
                    std::vector<unsigned char *> inputVector;
                    for (auto &image : imageSequence) {
                      validate_slm_image(image, expectedWidth, expectedHeight, bytesPerPixel);
                      inputVector.push_back(reinterpret_cast<unsigned char *>(image.data()));
                    }
                    self.loadSLMSequence(slmLabel, inputVector);
      },"slmLabel"_a, "pixels"_a)

      // Galvo Control
      NB_DEF_GIL("pointGalvoAndFire", &CMMCore::pointGalvoAndFire, "galvoLabel"_a, "x"_a, "y"_a,
           "pulseTime_us"_a)
      NB_DEF_GIL("setGalvoSpotInterval", &CMMCore::setGalvoSpotInterval, "galvoLabel"_a,
           "pulseTime_us"_a)
      NB_DEF_GIL("setGalvoPosition", &CMMCore::setGalvoPosition, "galvoLabel"_a, "x"_a, "y"_a)
      NB_DEF_GIL("getGalvoPosition",
           [](CMMCore& self, const char* galvoLabel) {
                double x, y;
                self.getGalvoPosition(galvoLabel, x, y);  // Call C++ method
                return std::make_tuple(x, y);             // Return a tuple
           })
      NB_DEF_GIL("setGalvoIlluminationState", &CMMCore::setGalvoIlluminationState, "galvoLabel"_a,
           "on"_a)
      NB_DEF_GIL("getGalvoXRange", &CMMCore::getGalvoXRange, "galvoLabel"_a)
      NB_DEF_GIL("getGalvoXMinimum", &CMMCore::getGalvoXMinimum, "galvoLabel"_a)
      NB_DEF_GIL("getGalvoYRange", &CMMCore::getGalvoYRange, "galvoLabel"_a)
      NB_DEF_GIL("getGalvoYMinimum", &CMMCore::getGalvoYMinimum, "galvoLabel"_a)
      NB_DEF_GIL("addGalvoPolygonVertex", &CMMCore::addGalvoPolygonVertex, "galvoLabel"_a,
           "polygonIndex"_a, "x"_a, "y"_a, R"doc(Add a vertex to a galvo polygon.)doc")
      NB_DEF_GIL("deleteGalvoPolygons", &CMMCore::deleteGalvoPolygons, "galvoLabel"_a)
      NB_DEF_GIL("loadGalvoPolygons", &CMMCore::loadGalvoPolygons, "galvoLabel"_a)
      NB_DEF_GIL("setGalvoPolygonRepetitions", &CMMCore::setGalvoPolygonRepetitions, "galvoLabel"_a,
           "repetitions"_a)
      NB_DEF_GIL("runGalvoPolygons", &CMMCore::runGalvoPolygons, "galvoLabel"_a)
      NB_DEF_GIL("runGalvoSequence", &CMMCore::runGalvoSequence, "galvoLabel"_a)
      NB_DEF_GIL("getGalvoChannel", &CMMCore::getGalvoChannel, "galvoLabel"_a)

      // Device Discovery
      NB_DEF_GIL("supportsDeviceDetection", &CMMCore::supportsDeviceDetection, "deviceLabel"_a)
      NB_DEF_GIL("detectDevice", &CMMCore::detectDevice, "deviceLabel"_a)

      // Hub and Peripheral Devices
      NB_DEF_GIL("getParentLabel", &CMMCore::getParentLabel, "peripheralLabel"_a)
      NB_DEF_GIL("setParentLabel", &CMMCore::setParentLabel, "deviceLabel"_a, "parentHubLabel"_a)
      NB_DEF_GIL("getInstalledDevices", &CMMCore::getInstalledDevices, "hubLabel"_a)
      NB_DEF_GIL("getInstalledDeviceDescription", &CMMCore::getInstalledDeviceDescription, "hubLabel"_a,
           "peripheralLabel"_a)
      NB_DEF_GIL("getLoadedPeripheralDevices", &CMMCore::getLoadedPeripheralDevices, "hubLabel"_a)

      ;
}
