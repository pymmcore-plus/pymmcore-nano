#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>

#include "MMCore.h"
#include "MMEventCallback.h"

namespace nb = nanobind;

using namespace nb::literals;

NB_MODULE(_pymmcore_nano, m) {
  m.doc() = "Python bindings for MMCore";

  /////////////////// Module Attributes ///////////////////

  m.attr("DEVICE_INTERFACE_VERSION") = DEVICE_INTERFACE_VERSION;

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
      // aliases
      //  .value("Unknown", MM::DeviceType::UnknownType)
      //  .value("Any", MM::DeviceType::AnyType)
      //  .value("Camera", MM::DeviceType::CameraDevice)
      //  .value("Shutter", MM::DeviceType::ShutterDevice)
      //  .value("State", MM::DeviceType::StateDevice)
      //  .value("Stage", MM::DeviceType::StageDevice)
      //  .value("XYStage", MM::DeviceType::XYStageDevice)
      //  .value("Serial", MM::DeviceType::SerialDevice)
      //  .value("Generic", MM::DeviceType::GenericDevice)
      //  .value("AutoFocus", MM::DeviceType::AutoFocusDevice)
      //  .value("Core", MM::DeviceType::CoreDevice)
      //  .value("ImageProcessor", MM::DeviceType::ImageProcessorDevice)
      //  .value("SignalIO", MM::DeviceType::SignalIODevice)
      //  .value("Magnifier", MM::DeviceType::MagnifierDevice)
      //  .value("SLM", MM::DeviceType::SLMDevice)
      //  .value("Hub", MM::DeviceType::HubDevice)
      //  .value("Galvo", MM::DeviceType::GalvoDevice)
      // actual values
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
      //  .value("Invalid", MM::PortType::InvalidPort)
      //  .value("Serial", MM::PortType::SerialPort)
      //  .value("USB", MM::PortType::USBPort)
      //  .value("HID", MM::PortType::HIDPort)
      .value("InvalidPort", MM::PortType::InvalidPort)
      .value("SerialPort", MM::PortType::SerialPort)
      .value("USBPort", MM::PortType::USBPort)
      .value("HIDPort", MM::PortType::HIDPort);

  nb::enum_<MM::FocusDirection>(m, "FocusDirection", nb::is_arithmetic())
      //  .value("Unknown", MM::FocusDirection::FocusDirectionUnknown)
      //  .value("TowardSample", MM::FocusDirection::FocusDirectionTowardSample)
      //  .value("AwayFromSample", MM::FocusDirection::FocusDirectionAwayFromSample)
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

  //////////////////// Supporting classes ////////////////////

  nb::class_<Configuration>(m, "Configuration")
      .def(nb::init<>())
      .def("addSetting", &Configuration::addSetting, "setting"_a)
      .def("deleteSetting", &Configuration::deleteSetting, "device"_a, "property"_a)
      .def("isPropertyIncluded", &Configuration::isPropertyIncluded, "device"_a, "property"_a)
      .def("isConfigurationIncluded", &Configuration::isConfigurationIncluded, "cfg"_a)
      .def("getSetting", nb::overload_cast<size_t>(&Configuration::getSetting, nb::const_),
           "index"_a)
      .def("getSetting", nb::overload_cast<const char*, const char*>(&Configuration::getSetting),
           "device"_a, "property"_a)
      .def("size", &Configuration::size)
      .def("getVerbose", &Configuration::getVerbose);

  nb::class_<PropertySetting>(m, "PropertySetting")
      .def(nb::init<const char*, const char*, const char*, bool>(), "deviceLabel"_a, "prop"_a,
           "value"_a, "readOnly"_a = false, "Constructor specifying the entire contents")
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
      .def(nb::init<const Metadata&>(), "Copy constructor")
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
      .def("Restore", &Metadata::Restore, "stream"_a, "Restores metadata from a serialized string")
      .def("Dump", &Metadata::Dump, "Dumps metadata in human-readable format")
      // Template methods (bound using lambdas due to C++ template limitations in bindings)
      .def(
          "PutTag",
          [](Metadata& self, const std::string& key, const std::string& deviceLabel,
             const std::string& value) { self.PutTag(key, deviceLabel, value); },
          "key"_a, "deviceLabel"_a, "value"_a, "Adds a MetadataSingleTag")

      .def(
          "PutImageTag",
          [](Metadata& self, const std::string& key, const std::string& value) {
            self.PutImageTag(key, value);
          },
          "key"_a, "value"_a, "Adds an image tag");

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
      .def("ToSingleTag", &MetadataTag::ToSingleTag, "Converts to MetadataSingleTag if applicable")
      .def("ToArrayTag", &MetadataTag::ToArrayTag, "Converts to MetadataArrayTag if applicable")
      .def("Clone", &MetadataTag::Clone, "Creates a clone of the MetadataTag")
      .def("Serialize", &MetadataTag::Serialize, "Serializes the MetadataTag to a string")
      .def("Restore", nb::overload_cast<const char*>(&MetadataTag::Restore), "stream"_a,
           "Restores from a serialized string");
  // Ommitting the std::istringstream& overload: Python doesn't have a stringstream equivalent
  //  .def("Restore", nb::overload_cast<std::istringstream&>(&MetadataTag::Restore),
  //  "istream"_a,
  //       "Restores from an input stream")
  // Static methods
  //  .def_static("ReadLine", &MetadataTag::ReadLine, "istream"_a,
  //    "Reads a line from an input stream");

  nb::class_<MetadataSingleTag, MetadataTag>(m, "MetadataSingleTag")
      .def(nb::init<>(), "Default constructor")
      .def(nb::init<const char*, const char*, bool>(), "name"_a, "device"_a, "readOnly"_a,
           "Parameterized constructor")
      // Member functions
      .def("GetValue", &MetadataSingleTag::GetValue, "Returns the value")
      .def("SetValue", &MetadataSingleTag::SetValue, "val"_a, "Sets the value")
      .def("ToSingleTag", &MetadataSingleTag::ToSingleTag,
           "Returns this object as MetadataSingleTag")
      .def("Clone", &MetadataSingleTag::Clone, "Clones this tag")
      .def("Serialize", &MetadataSingleTag::Serialize, "Serializes this tag to a string")
      // Omitting the std::istringstream& overload: Python doesn't have a stringstream equivalent
      //  .def("Restore", nb::overload_cast<std::istringstream&>(&MetadataSingleTag::Restore),
      //  "istream"_a, "Restores from an input stream")
      .def("Restore", nb::overload_cast<const char*>(&MetadataSingleTag::Restore), "stream"_a,
           "Restores from a serialized string");

  nb::class_<MetadataArrayTag, MetadataTag>(m, "MetadataArrayTag")
      .def(nb::init<>(), "Default constructor")
      .def(nb::init<const char*, const char*, bool>(), "name"_a, "device"_a, "readOnly"_a,
           "Parameterized constructor")
      .def("ToArrayTag", &MetadataArrayTag::ToArrayTag, "Returns this object as MetadataArrayTag")
      .def("AddValue", &MetadataArrayTag::AddValue, "val"_a, "Adds a value to the array")
      .def("SetValue", &MetadataArrayTag::SetValue, "val"_a, "idx"_a,
           "Sets a value at a specific index")
      .def("GetValue", &MetadataArrayTag::GetValue, "idx"_a, "Gets a value at a specific index")
      .def("GetSize", &MetadataArrayTag::GetSize, "Returns the size of the array")
      .def("Clone", &MetadataArrayTag::Clone, "Clones this tag")
      .def("Serialize", &MetadataArrayTag::Serialize, "Serializes this tag to a string")
      // Omitting the std::istringstream& overload: Python doesn't have a stringstream equivalent
      //  .def("Restore", nb::overload_cast<std::istringstream&>(&MetadataArrayTag::Restore),
      //       "istream"_a, "Restores from an input stream")
      .def("Restore", nb::overload_cast<const char*>(&MetadataArrayTag::Restore), "stream"_a,
           "Restores from a serialized string");

  nb::class_<MMEventCallback>(m, "MMEventCallback")
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
      .def("onPixelSizeAffineChanged", &MMEventCallback::onPixelSizeAffineChanged, "v0"_a, "v1"_a,
           "v2"_a, "v3"_a, "v4"_a, "v5"_a,
           "Called when the pixel size affine transformation changes")
      // These bindings are ugly lambda workarounds because the original methods take char* instead
      // of const char*
      // https://github.com/micro-manager/mmCoreAndDevices/pull/530
      .def(
          "onSLMExposureChanged",
          [](MMEventCallback& self, const std::string& name, double newExposure) {
            self.onSLMExposureChanged(const_cast<char*>(name.c_str()), newExposure);
          },
          "name"_a, "newExposure"_a)
      .def(
          "onExposureChanged",
          [&](MMEventCallback& self, const std::string& name, double newExposure) {
            self.onExposureChanged(const_cast<char*>(name.c_str()), newExposure);
          },
          "name"_a, "newExposure"_a)
      .def(
          "onStagePositionChanged",
          [&](MMEventCallback& self, const std::string& name, double pos) {
            self.onStagePositionChanged(const_cast<char*>(name.c_str()), pos);
          },
          "name"_a, "pos"_a)
      .def(
          "onXYStagePositionChanged",
          [&](MMEventCallback& self, const std::string& name, double xpos, double ypos) {
            self.onXYStagePositionChanged(const_cast<char*>(name.c_str()), xpos, ypos);
          },
          "name"_a, "xpos"_a, "ypos"_a);

  //////////////////// Exceptions ////////////////////

  // Register the exception with RuntimeError as the base
  // NOTE:
  // at the moment, we're not exposing all of the methods on the CMMErrors class
  // because this is far simpler... but we could expose more if needed
  // this will expose pymmcore_nano.CMMErrors as a subclass of RuntimeError
  // and a basic message will be propagated, for example:
  // CMMError('Failed to load device "SomeDevice" from adapter module "SomeModule"')
  nb::exception<CMMError>(m, "CMMError", PyExc_RuntimeError);

  //////////////////// MMCore ////////////////////

  nb::class_<CMMCore>(m, "CMMCore")
      .def(nb::init<>())

      .def(
          "loadSystemConfiguration",
          [](CMMCore& self,
             nb::object fileName) {  // accept any object that can be cast to a string (e.g. Path)
            self.loadSystemConfiguration(nb::str(fileName).c_str());
          },
          "fileName"_a)

      .def("saveSystemConfiguration", &CMMCore::saveSystemConfiguration, "fileName"_a)
      .def_static("enableFeature", &CMMCore::enableFeature, "name"_a, "enable"_a)
      .def_static("isFeatureEnabled", &CMMCore::isFeatureEnabled, "name"_a)
      .def("loadDevice", &CMMCore::loadDevice, "label"_a, "moduleName"_a, "deviceName"_a)
      .def("unloadDevice", &CMMCore::unloadDevice, "label"_a)
      .def("unloadAllDevices", &CMMCore::unloadAllDevices)
      .def("initializeAllDevices", &CMMCore::initializeAllDevices)
      .def("initializeDevice", &CMMCore::initializeDevice, "label"_a)
      .def("getDeviceInitializationState", &CMMCore::getDeviceInitializationState, "label"_a)
      .def("reset", &CMMCore::reset)
      .def("unloadLibrary", &CMMCore::unloadLibrary, "moduleName"_a)
      .def("updateCoreProperties", &CMMCore::updateCoreProperties)
      .def("getCoreErrorText", &CMMCore::getCoreErrorText, "code"_a)
      .def("getVersionInfo", &CMMCore::getVersionInfo)
      .def("getAPIVersionInfo", &CMMCore::getAPIVersionInfo)
      .def("getSystemState", &CMMCore::getSystemState)
      .def("setSystemState", &CMMCore::setSystemState, "conf"_a)
      .def("getConfigState", &CMMCore::getConfigState, "group"_a, "config"_a)
      .def("getConfigGroupState", nb::overload_cast<const char*>(&CMMCore::getConfigGroupState),
           "group"_a)
      .def("saveSystemState", &CMMCore::saveSystemState, "fileName"_a)
      .def("loadSystemState", &CMMCore::loadSystemState, "fileName"_a)
      .def("registerCallback", &CMMCore::registerCallback, "cb"_a)
      .def(
          "setPrimaryLogFile",
          [](CMMCore& self,
             nb::object filename,  // accept any object that can be cast to a string (e.g. Path)
             bool truncate) {
            self.setPrimaryLogFile(nb::str(filename).c_str(), truncate);  // convert to string
          },
          "filename"_a, "truncate"_a = false)

      .def("getPrimaryLogFile", &CMMCore::getPrimaryLogFile)
      .def("logMessage", nb::overload_cast<const char*>(&CMMCore::logMessage), "msg"_a)
      .def("logMessage", nb::overload_cast<const char*, bool>(&CMMCore::logMessage), "msg"_a,
           "debugOnly"_a)

      .def("enableDebugLog", &CMMCore::enableDebugLog, "enable"_a)
      .def("debugLogEnabled", &CMMCore::debugLogEnabled)
      .def("enableStderrLog", &CMMCore::enableStderrLog, "enable"_a)
      .def("stderrLogEnabled", &CMMCore::stderrLogEnabled)
      .def(
          "startSecondaryLogFile",
          [](CMMCore& self,
             nb::object filename,  // accept any object that can be cast to a string (e.g. Path)
             bool enableDebug, bool truncate, bool synchronous) {
            return self.startSecondaryLogFile(nb::str(filename).c_str(), enableDebug, truncate,
                                              synchronous);
          },
          "filename"_a, "enableDebug"_a, "truncate"_a = true, "synchronous"_a = false)
      .def("stopSecondaryLogFile", &CMMCore::stopSecondaryLogFile, "handle"_a)

      .def("getDeviceAdapterSearchPaths", &CMMCore::getDeviceAdapterSearchPaths)
      .def("setDeviceAdapterSearchPaths", &CMMCore::setDeviceAdapterSearchPaths, "paths"_a)
      .def("getDeviceAdapterNames", &CMMCore::getDeviceAdapterNames)
      .def("getAvailableDevices", &CMMCore::getAvailableDevices, "library"_a)
      .def("getAvailableDeviceDescriptions", &CMMCore::getAvailableDeviceDescriptions, "library"_a)
      .def("getAvailableDeviceTypes", &CMMCore::getAvailableDeviceTypes, "library"_a)
      .def("getLoadedDevices", &CMMCore::getLoadedDevices)
      .def("getLoadedDevicesOfType", &CMMCore::getLoadedDevicesOfType, "devType"_a)
      .def("getDeviceType", &CMMCore::getDeviceType, "label"_a)
      .def("getDeviceLibrary", &CMMCore::getDeviceLibrary, "label"_a)
      .def("getDeviceName", nb::overload_cast<const char*>(&CMMCore::getDeviceName), "label"_a)
      .def("getDeviceDescription", &CMMCore::getDeviceDescription, "label"_a)
      .def("getDevicePropertyNames", &CMMCore::getDevicePropertyNames, "label"_a)
      .def("hasProperty", &CMMCore::hasProperty, "label"_a, "propName"_a)
      .def("getProperty", &CMMCore::getProperty, "label"_a, "propName"_a)
      .def("setProperty",
           nb::overload_cast<const char*, const char*, const char*>(&CMMCore::setProperty),
           "label"_a, "propName"_a, "propValue"_a)
      .def("setProperty", nb::overload_cast<const char*, const char*, bool>(&CMMCore::setProperty),
           "label"_a, "propName"_a, "propValue"_a)
      .def("setProperty", nb::overload_cast<const char*, const char*, long>(&CMMCore::setProperty),
           "label"_a, "propName"_a, "propValue"_a)
      .def("setProperty",
           nb::overload_cast<const char*, const char*, float>(&CMMCore::setProperty), "label"_a,
           "propName"_a, "propValue"_a)
      .def("getAllowedPropertyValues", &CMMCore::getAllowedPropertyValues, "label"_a, "propName"_a)
      .def("isPropertyReadOnly", &CMMCore::isPropertyReadOnly, "label"_a, "propName"_a)
      .def("isPropertyPreInit", &CMMCore::isPropertyPreInit, "label"_a, "propName"_a)
      .def("isPropertySequenceable", &CMMCore::isPropertySequenceable, "label"_a, "propName"_a)
      .def("hasPropertyLimits", &CMMCore::hasPropertyLimits, "label"_a, "propName"_a)
      .def("getPropertyLowerLimit", &CMMCore::getPropertyLowerLimit, "label"_a, "propName"_a)
      .def("getPropertyUpperLimit", &CMMCore::getPropertyUpperLimit, "label"_a, "propName"_a)
      .def("getPropertyType", &CMMCore::getPropertyType, "label"_a, "propName"_a)
      .def("startPropertySequence", &CMMCore::startPropertySequence, "label"_a, "propName"_a)
      .def("stopPropertySequence", &CMMCore::stopPropertySequence, "label"_a, "propName"_a)
      .def("getPropertySequenceMaxLength", &CMMCore::getPropertySequenceMaxLength, "label"_a,
           "propName"_a)
      .def("loadPropertySequence", &CMMCore::loadPropertySequence, "label"_a, "propName"_a,
           "eventSequence"_a)
      .def("deviceBusy", &CMMCore::deviceBusy, "label"_a)
      .def("waitForDevice", nb::overload_cast<const char*>(&CMMCore::waitForDevice), "label"_a)
      .def("waitForConfig", &CMMCore::waitForConfig, "group"_a, "configName"_a)
      .def("systemBusy", &CMMCore::systemBusy)
      .def("waitForSystem", &CMMCore::waitForSystem)
      .def("deviceTypeBusy", &CMMCore::deviceTypeBusy, "devType"_a)
      .def("waitForDeviceType", &CMMCore::waitForDeviceType, "devType"_a)
      .def("getDeviceDelayMs", &CMMCore::getDeviceDelayMs, "label"_a)
      .def("setDeviceDelayMs", &CMMCore::setDeviceDelayMs, "label"_a, "delayMs"_a)
      .def("usesDeviceDelay", &CMMCore::usesDeviceDelay, "label"_a)
      .def("setTimeoutMs", &CMMCore::setTimeoutMs, "timeoutMs"_a)
      .def("getTimeoutMs", &CMMCore::getTimeoutMs)
      .def("sleep", &CMMCore::sleep, "intervalMs"_a)

      .def("getCameraDevice", &CMMCore::getCameraDevice)
      .def("getShutterDevice", &CMMCore::getShutterDevice)
      .def("getFocusDevice", &CMMCore::getFocusDevice)
      .def("getXYStageDevice", &CMMCore::getXYStageDevice)
      .def("getAutoFocusDevice", &CMMCore::getAutoFocusDevice)
      .def("getImageProcessorDevice", &CMMCore::getImageProcessorDevice)
      .def("getSLMDevice", &CMMCore::getSLMDevice)
      .def("getGalvoDevice", &CMMCore::getGalvoDevice)
      .def("getChannelGroup", &CMMCore::getChannelGroup)
      .def("setCameraDevice", &CMMCore::setCameraDevice, "cameraLabel"_a)
      .def("setShutterDevice", &CMMCore::setShutterDevice, "shutterLabel"_a)
      .def("setFocusDevice", &CMMCore::setFocusDevice, "focusLabel"_a)
      .def("setXYStageDevice", &CMMCore::setXYStageDevice, "xyStageLabel"_a)
      .def("setAutoFocusDevice", &CMMCore::setAutoFocusDevice, "focusLabel"_a)
      .def("setImageProcessorDevice", &CMMCore::setImageProcessorDevice, "procLabel"_a)
      .def("setSLMDevice", &CMMCore::setSLMDevice, "slmLabel"_a)
      .def("setGalvoDevice", &CMMCore::setGalvoDevice, "galvoLabel"_a)
      .def("setChannelGroup", &CMMCore::setChannelGroup, "channelGroup"_a)

      .def("getSystemStateCache", &CMMCore::getSystemStateCache)
      .def("updateSystemStateCache", &CMMCore::updateSystemStateCache)
      .def("getPropertyFromCache", &CMMCore::getPropertyFromCache, "deviceLabel"_a, "propName"_a)
      .def("getCurrentConfigFromCache", &CMMCore::getCurrentConfigFromCache, "groupName"_a)
      .def("getConfigGroupStateFromCache", &CMMCore::getConfigGroupStateFromCache, "group"_a)

      .def("defineConfig", nb::overload_cast<const char*, const char*>(&CMMCore::defineConfig),
           "groupName"_a, "configName"_a)
      .def("defineConfig",
           nb::overload_cast<const char*, const char*, const char*, const char*, const char*>(
               &CMMCore::defineConfig),
           "groupName"_a, "configName"_a, "deviceLabel"_a, "propName"_a, "value"_a)
      .def("defineConfigGroup", &CMMCore::defineConfigGroup, "groupName"_a)
      .def("deleteConfigGroup", &CMMCore::deleteConfigGroup, "groupName"_a)
      .def("renameConfigGroup", &CMMCore::renameConfigGroup, "oldGroupName"_a, "newGroupName"_a)
      .def("isGroupDefined", &CMMCore::isGroupDefined, "groupName"_a)
      .def("isConfigDefined", &CMMCore::isConfigDefined, "groupName"_a, "configName"_a)
      .def("setConfig", &CMMCore::setConfig, "groupName"_a, "configName"_a)

      .def("deleteConfig", nb::overload_cast<const char*, const char*>(&CMMCore::deleteConfig),
           "groupName"_a, "configName"_a)
      .def("deleteConfig",
           nb::overload_cast<const char*, const char*, const char*, const char*>(
               &CMMCore::deleteConfig),
           "groupName"_a, "configName"_a, "deviceLabel"_a, "propName"_a)

      .def("renameConfig", &CMMCore::renameConfig, "groupName"_a, "oldConfigName"_a,
           "newConfigName"_a)
      .def("getAvailableConfigGroups", &CMMCore::getAvailableConfigGroups)
      .def("getAvailableConfigs", &CMMCore::getAvailableConfigs, "configGroup"_a)
      .def("getCurrentConfig", &CMMCore::getCurrentConfig, "groupName"_a)
      .def("getConfigData", &CMMCore::getConfigData, "configGroup"_a, "configName"_a)

      .def("getCurrentPixelSizeConfig", nb::overload_cast<>(&CMMCore::getCurrentPixelSizeConfig))
      .def("getCurrentPixelSizeConfig",
           nb::overload_cast<bool>(&CMMCore::getCurrentPixelSizeConfig), "cached"_a)
      .def("getPixelSizeUm", nb::overload_cast<>(&CMMCore::getPixelSizeUm))
      .def("getPixelSizeUm", nb::overload_cast<bool>(&CMMCore::getPixelSizeUm), "cached"_a)
      .def("getPixelSizeUmByID", &CMMCore::getPixelSizeUmByID, "resolutionID"_a)
      .def("getPixelSizeAffine", nb::overload_cast<>(&CMMCore::getPixelSizeAffine))
      .def("getPixelSizeAffine", nb::overload_cast<bool>(&CMMCore::getPixelSizeAffine), "cached"_a)
      .def("getPixelSizeAffineByID", &CMMCore::getPixelSizeAffineByID, "resolutionID"_a)
      .def("getMagnificationFactor", &CMMCore::getMagnificationFactor)
      .def("setPixelSizeUm", &CMMCore::setPixelSizeUm, "resolutionID"_a, "pixSize"_a)
      .def("setPixelSizeAffine", &CMMCore::setPixelSizeAffine, "resolutionID"_a, "affine"_a)
      .def("definePixelSizeConfig",
           nb::overload_cast<const char*, const char*, const char*, const char*>(
               &CMMCore::definePixelSizeConfig),
           "resolutionID"_a, "deviceLabel"_a, "propName"_a, "value"_a)
      .def("definePixelSizeConfig",
           nb::overload_cast<const char*>(&CMMCore::definePixelSizeConfig), "resolutionID"_a)
      .def("getAvailablePixelSizeConfigs", &CMMCore::getAvailablePixelSizeConfigs)
      .def("isPixelSizeConfigDefined", &CMMCore::isPixelSizeConfigDefined, "resolutionID"_a)
      .def("setPixelSizeConfig", &CMMCore::setPixelSizeConfig, "resolutionID"_a)
      .def("renamePixelSizeConfig", &CMMCore::renamePixelSizeConfig, "oldConfigName"_a,
           "newConfigName"_a)
      .def("deletePixelSizeConfig", &CMMCore::deletePixelSizeConfig, "configName"_a)
      .def("getPixelSizeConfigData", &CMMCore::getPixelSizeConfigData, "configName"_a)

      .def("setROI", nb::overload_cast<int, int, int, int>(&CMMCore::setROI), "x"_a, "y"_a,
           "xSize"_a, "ySize"_a)
      .def("setROI", nb::overload_cast<const char*, int, int, int, int>(&CMMCore::setROI),
           "label"_a, "x"_a, "y"_a, "xSize"_a, "ySize"_a)
      .def("getROI",
           [](CMMCore& self) {
             int x, y, xSize, ySize;
             self.getROI(x, y, xSize, ySize);             // Call C++ method
             return std::make_tuple(x, y, xSize, ySize);  // Return a tuple
           })
      .def(
          "getROI",
          [](CMMCore& self, const char* label) {
            int x, y, xSize, ySize;
            self.getROI(label, x, y, xSize, ySize);      // Call the C++ method
            return std::make_tuple(x, y, xSize, ySize);  // Return as Python tuple
          },
          "label"_a)
      .def("clearROI", &CMMCore::clearROI)
      .def("isMultiROISupported", &CMMCore::isMultiROISupported)
      .def("isMultiROIEnabled", &CMMCore::isMultiROIEnabled)
      .def("setMultiROI", &CMMCore::setMultiROI, "xs"_a, "ys"_a, "widths"_a, "heights"_a)
      .def("getMultiROI", &CMMCore::getMultiROI, "xs"_a, "ys"_a, "widths"_a, "heights"_a)
      .def("setExposure", nb::overload_cast<double>(&CMMCore::setExposure), "exp"_a)
      .def("setExposure", nb::overload_cast<const char*, double>(&CMMCore::setExposure),
           "cameraLabel"_a, "dExp"_a)
      .def("getExposure", nb::overload_cast<>(&CMMCore::getExposure))
      .def("getExposure", nb::overload_cast<const char*>(&CMMCore::getExposure), "label"_a)
      .def("snapImage", &CMMCore::snapImage)
      .def("getImage", nb::overload_cast<>(&CMMCore::getImage))
      .def("getImage", nb::overload_cast<unsigned>(&CMMCore::getImage), "numChannel"_a)
      .def("getImageWidth", &CMMCore::getImageWidth)
      .def("getImageHeight", &CMMCore::getImageHeight)
      .def("getBytesPerPixel", &CMMCore::getBytesPerPixel)
      .def("getImageBitDepth", &CMMCore::getImageBitDepth)
      .def("getNumberOfComponents", &CMMCore::getNumberOfComponents)
      .def("getNumberOfCameraChannels", &CMMCore::getNumberOfCameraChannels)
      .def("getCameraChannelName", &CMMCore::getCameraChannelName, "channelNr"_a)
      .def("getImageBufferSize", &CMMCore::getImageBufferSize)
      .def("setAutoShutter", &CMMCore::setAutoShutter, "state"_a)
      .def("getAutoShutter", &CMMCore::getAutoShutter)
      .def("setShutterOpen", nb::overload_cast<bool>(&CMMCore::setShutterOpen), "state"_a)
      .def("getShutterOpen", nb::overload_cast<>(&CMMCore::getShutterOpen))
      .def("setShutterOpen", nb::overload_cast<const char*, bool>(&CMMCore::setShutterOpen),
           "shutterLabel"_a, "state"_a)
      .def("getShutterOpen", nb::overload_cast<const char*>(&CMMCore::getShutterOpen),
           "shutterLabel"_a)
      .def("startSequenceAcquisition",
           nb::overload_cast<long, double, bool>(&CMMCore::startSequenceAcquisition),
           "numImages"_a, "intervalMs"_a, "stopOnOverflow"_a)
      .def("startSequenceAcquisition",
           nb::overload_cast<const char*, long, double, bool>(&CMMCore::startSequenceAcquisition),
           "cameraLabel"_a, "numImages"_a, "intervalMs"_a, "stopOnOverflow"_a)
      .def("prepareSequenceAcquisition", &CMMCore::prepareSequenceAcquisition, "cameraLabel"_a)
      .def("startContinuousSequenceAcquisition", &CMMCore::startContinuousSequenceAcquisition,
           "intervalMs"_a)
      .def("stopSequenceAcquisition", nb::overload_cast<>(&CMMCore::stopSequenceAcquisition))
      .def("stopSequenceAcquisition",
           nb::overload_cast<const char*>(&CMMCore::stopSequenceAcquisition), "cameraLabel"_a)
      .def("isSequenceRunning", nb::overload_cast<>(&CMMCore::isSequenceRunning))
      .def("isSequenceRunning", nb::overload_cast<const char*>(&CMMCore::isSequenceRunning),
           "cameraLabel"_a)

      // Image Buffer Methods
      .def("getLastImage", &CMMCore::getLastImage)
      .def("popNextImage", &CMMCore::popNextImage)
      //  .def("getLastImageMD", &CMMCore::getLastImageMD, "channel"_a, "slice"_a, "md"_a)
      //  .def("popNextImageMD", &CMMCore::popNextImageMD, "channel"_a, "slice"_a, "md"_a)
      //  .def("popNextImageMD", &CMMCore::popNextImageMD, "md"_a)
      .def("getLastImageMD", nb::overload_cast<Metadata&>(&CMMCore::getLastImageMD, nb::const_),
           "md"_a)
      .def("getNBeforeLastImageMD", &CMMCore::getNBeforeLastImageMD, "n"_a, "md"_a)

      // Circular Buffer Methods
      .def("getRemainingImageCount", &CMMCore::getRemainingImageCount)
      .def("getBufferTotalCapacity", &CMMCore::getBufferTotalCapacity)
      .def("getBufferFreeCapacity", &CMMCore::getBufferFreeCapacity)
      .def("isBufferOverflowed", &CMMCore::isBufferOverflowed)
      .def("setCircularBufferMemoryFootprint", &CMMCore::setCircularBufferMemoryFootprint,
           "sizeMB"_a)
      .def("getCircularBufferMemoryFootprint", &CMMCore::getCircularBufferMemoryFootprint)
      .def("initializeCircularBuffer", &CMMCore::initializeCircularBuffer)
      .def("clearCircularBuffer", &CMMCore::clearCircularBuffer)

      // Exposure Sequence Methods
      .def("isExposureSequenceable", &CMMCore::isExposureSequenceable, "cameraLabel"_a)
      .def("startExposureSequence", &CMMCore::startExposureSequence, "cameraLabel"_a)
      .def("stopExposureSequence", &CMMCore::stopExposureSequence, "cameraLabel"_a)
      .def("getExposureSequenceMaxLength", &CMMCore::getExposureSequenceMaxLength, "cameraLabel"_a)
      .def("loadExposureSequence", &CMMCore::loadExposureSequence, "cameraLabel"_a,
           "exposureSequence_ms"_a)

      // Autofocus Methods
      .def("getLastFocusScore", &CMMCore::getLastFocusScore)
      .def("getCurrentFocusScore", &CMMCore::getCurrentFocusScore)
      .def("enableContinuousFocus", &CMMCore::enableContinuousFocus, "enable"_a)
      .def("isContinuousFocusEnabled", &CMMCore::isContinuousFocusEnabled)
      .def("isContinuousFocusLocked", &CMMCore::isContinuousFocusLocked)
      .def("isContinuousFocusDrive", &CMMCore::isContinuousFocusDrive, "stageLabel"_a)
      .def("fullFocus", &CMMCore::fullFocus)
      .def("incrementalFocus", &CMMCore::incrementalFocus)
      .def("setAutoFocusOffset", &CMMCore::setAutoFocusOffset, "offset"_a)
      .def("getAutoFocusOffset", &CMMCore::getAutoFocusOffset)

      // State Device Control Methods
      .def("setState", &CMMCore::setState, "stateDeviceLabel"_a, "state"_a)
      .def("getState", &CMMCore::getState, "stateDeviceLabel"_a)
      .def("getNumberOfStates", &CMMCore::getNumberOfStates, "stateDeviceLabel"_a)
      .def("setStateLabel", &CMMCore::setStateLabel, "stateDeviceLabel"_a, "stateLabel"_a)
      .def("getStateLabel", &CMMCore::getStateLabel, "stateDeviceLabel"_a)
      .def("defineStateLabel", &CMMCore::defineStateLabel, "stateDeviceLabel"_a, "state"_a,
           "stateLabel"_a)
      .def("getStateLabels", &CMMCore::getStateLabels, "stateDeviceLabel"_a)
      .def("getStateFromLabel", &CMMCore::getStateFromLabel, "stateDeviceLabel"_a, "stateLabel"_a)

      // Stage Control Methods
      .def("setPosition", nb::overload_cast<const char*, double>(&CMMCore::setPosition),
           "stageLabel"_a, "position"_a)
      .def("setPosition", nb::overload_cast<double>(&CMMCore::setPosition), "position"_a)
      .def("getPosition", nb::overload_cast<const char*>(&CMMCore::getPosition), "stageLabel"_a)
      .def("getPosition", nb::overload_cast<>(&CMMCore::getPosition))
      .def("setRelativePosition",
           nb::overload_cast<const char*, double>(&CMMCore::setRelativePosition), "stageLabel"_a,
           "d"_a)
      .def("setRelativePosition", nb::overload_cast<double>(&CMMCore::setRelativePosition), "d"_a)
      .def("setOrigin", nb::overload_cast<const char*>(&CMMCore::setOrigin), "stageLabel"_a)
      .def("setOrigin", nb::overload_cast<>(&CMMCore::setOrigin))
      .def("setAdapterOrigin", nb::overload_cast<const char*, double>(&CMMCore::setAdapterOrigin),
           "stageLabel"_a, "newZUm"_a)
      .def("setAdapterOrigin", nb::overload_cast<double>(&CMMCore::setAdapterOrigin), "newZUm"_a)

      // Focus Direction Methods
      .def("setFocusDirection", &CMMCore::setFocusDirection, "stageLabel"_a, "sign"_a)
      .def("getFocusDirection", &CMMCore::getFocusDirection, "stageLabel"_a)

      // Stage Sequence Methods
      .def("isStageSequenceable", &CMMCore::isStageSequenceable, "stageLabel"_a)
      .def("isStageLinearSequenceable", &CMMCore::isStageLinearSequenceable, "stageLabel"_a)
      .def("startStageSequence", &CMMCore::startStageSequence, "stageLabel"_a)
      .def("stopStageSequence", &CMMCore::stopStageSequence, "stageLabel"_a)
      .def("getStageSequenceMaxLength", &CMMCore::getStageSequenceMaxLength, "stageLabel"_a)
      .def("loadStageSequence", &CMMCore::loadStageSequence, "stageLabel"_a, "positionSequence"_a)
      .def("setStageLinearSequence", &CMMCore::setStageLinearSequence, "stageLabel"_a, "dZ_um"_a,
           "nSlices"_a)

      // XY Stage Control Methods
      .def("setXYPosition",
           nb::overload_cast<const char*, double, double>(&CMMCore::setXYPosition),
           "xyStageLabel"_a, "x"_a, "y"_a)
      .def("setXYPosition", nb::overload_cast<double, double>(&CMMCore::setXYPosition), "x"_a,
           "y"_a)
      .def("setRelativeXYPosition",
           nb::overload_cast<const char*, double, double>(&CMMCore::setRelativeXYPosition),
           "xyStageLabel"_a, "dx"_a, "dy"_a)
      .def("setRelativeXYPosition",
           nb::overload_cast<double, double>(&CMMCore::setRelativeXYPosition), "dx"_a, "dy"_a)
      .def("getXYPosition",
           nb::overload_cast<const char*, double&, double&>(&CMMCore::getXYPosition),
           "xyStageLabel"_a, "x_stage"_a, "y_stage"_a)
      .def("getXYPosition", nb::overload_cast<double&, double&>(&CMMCore::getXYPosition),
           "x_stage"_a, "y_stage"_a)
      .def("getXPosition", nb::overload_cast<const char*>(&CMMCore::getXPosition),
           "xyStageLabel"_a)
      .def("getYPosition", nb::overload_cast<const char*>(&CMMCore::getYPosition),
           "xyStageLabel"_a)
      .def("getXPosition", nb::overload_cast<>(&CMMCore::getXPosition))
      .def("getYPosition", nb::overload_cast<>(&CMMCore::getYPosition))
      .def("stop", &CMMCore::stop, "xyOrZStageLabel"_a)
      .def("home", &CMMCore::home, "xyOrZStageLabel"_a)
      .def("setOriginXY", nb::overload_cast<const char*>(&CMMCore::setOriginXY), "xyStageLabel"_a)
      .def("setOriginXY", nb::overload_cast<>(&CMMCore::setOriginXY))
      .def("setOriginX", nb::overload_cast<const char*>(&CMMCore::setOriginX), "xyStageLabel"_a)
      .def("setOriginX", nb::overload_cast<>(&CMMCore::setOriginX))
      .def("setOriginY", nb::overload_cast<const char*>(&CMMCore::setOriginY), "xyStageLabel"_a)
      .def("setOriginY", nb::overload_cast<>(&CMMCore::setOriginY))
      .def("setAdapterOriginXY",
           nb::overload_cast<const char*, double, double>(&CMMCore::setAdapterOriginXY),
           "xyStageLabel"_a, "newXUm"_a, "newYUm"_a)
      .def("setAdapterOriginXY", nb::overload_cast<double, double>(&CMMCore::setAdapterOriginXY),
           "newXUm"_a, "newYUm"_a)

      // XY Stage Sequence Methods
      .def("isXYStageSequenceable", &CMMCore::isXYStageSequenceable, "xyStageLabel"_a)
      .def("startXYStageSequence", &CMMCore::startXYStageSequence, "xyStageLabel"_a)
      .def("stopXYStageSequence", &CMMCore::stopXYStageSequence, "xyStageLabel"_a)
      .def("getXYStageSequenceMaxLength", &CMMCore::getXYStageSequenceMaxLength, "xyStageLabel"_a)
      .def("loadXYStageSequence", &CMMCore::loadXYStageSequence, "xyStageLabel"_a, "xSequence"_a,
           "ySequence"_a)

      // Serial Port Control
      .def("setSerialProperties", &CMMCore::setSerialProperties, "portName"_a, "answerTimeout"_a,
           "baudRate"_a, "delayBetweenCharsMs"_a, "handshaking"_a, "parity"_a, "stopBits"_a)
      .def("setSerialPortCommand", &CMMCore::setSerialPortCommand, "portLabel"_a, "command"_a,
           "term"_a)
      .def("getSerialPortAnswer", &CMMCore::getSerialPortAnswer, "portLabel"_a, "term"_a)
      .def("writeToSerialPort", &CMMCore::writeToSerialPort, "portLabel"_a, "data"_a)
      .def("readFromSerialPort", &CMMCore::readFromSerialPort, "portLabel"_a)

      // SLM Control
      .def("setSLMImage", nb::overload_cast<const char*, unsigned char*>(&CMMCore::setSLMImage),
           "slmLabel"_a, "pixels"_a)
      //  .def("setSLMImage", nb::overload_cast<const char*, imgRGB32>(&CMMCore::setSLMImage),
      //       "slmLabel"_a, "pixels"_a)
      .def("setSLMPixelsTo",
           nb::overload_cast<const char*, unsigned char>(&CMMCore::setSLMPixelsTo), "slmLabel"_a,
           "intensity"_a)
      .def("setSLMPixelsTo",
           nb::overload_cast<const char*, unsigned char, unsigned char, unsigned char>(
               &CMMCore::setSLMPixelsTo),
           "slmLabel"_a, "red"_a, "green"_a, "blue"_a)
      .def("displaySLMImage", &CMMCore::displaySLMImage, "slmLabel"_a)
      .def("setSLMExposure", &CMMCore::setSLMExposure, "slmLabel"_a, "exposure_ms"_a)
      .def("getSLMExposure", &CMMCore::getSLMExposure, "slmLabel"_a)
      .def("getSLMWidth", &CMMCore::getSLMWidth, "slmLabel"_a)
      .def("getSLMHeight", &CMMCore::getSLMHeight, "slmLabel"_a)
      .def("getSLMNumberOfComponents", &CMMCore::getSLMNumberOfComponents, "slmLabel"_a)
      .def("getSLMBytesPerPixel", &CMMCore::getSLMBytesPerPixel, "slmLabel"_a)
      // SLM Sequence
      .def("getSLMSequenceMaxLength", &CMMCore::getSLMSequenceMaxLength, "slmLabel"_a)
      .def("startSLMSequence", &CMMCore::startSLMSequence, "slmLabel"_a)
      .def("stopSLMSequence", &CMMCore::stopSLMSequence, "slmLabel"_a)
      //  .def("loadSLMSequence", &CMMCore::loadSLMSequence, "slmLabel"_a, "imageSequence"_a)

      // Galvo Control
      .def("pointGalvoAndFire", &CMMCore::pointGalvoAndFire, "galvoLabel"_a, "x"_a, "y"_a,
           "pulseTime_us"_a)
      .def("setGalvoSpotInterval", &CMMCore::setGalvoSpotInterval, "galvoLabel"_a,
           "pulseTime_us"_a)
      .def("setGalvoPosition", &CMMCore::setGalvoPosition, "galvoLabel"_a, "x"_a, "y"_a)
      .def("getGalvoPosition",
           [](CMMCore& self, const char* galvoLabel) {
             double x, y;
             self.getGalvoPosition(galvoLabel, x, y);  // Call C++ method
             return std::make_tuple(x, y);             // Return a tuple
           })
      .def("setGalvoIlluminationState", &CMMCore::setGalvoIlluminationState, "galvoLabel"_a,
           "on"_a)
      .def("getGalvoXRange", &CMMCore::getGalvoXRange, "galvoLabel"_a)
      .def("getGalvoXMinimum", &CMMCore::getGalvoXMinimum, "galvoLabel"_a)
      .def("getGalvoYRange", &CMMCore::getGalvoYRange, "galvoLabel"_a)
      .def("getGalvoYMinimum", &CMMCore::getGalvoYMinimum, "galvoLabel"_a)
      .def("addGalvoPolygonVertex", &CMMCore::addGalvoPolygonVertex, "galvoLabel"_a,
           "polygonIndex"_a, "x"_a, "y"_a, R"doc(Add a vertex to a galvo polygon.)doc")
      .def("deleteGalvoPolygons", &CMMCore::deleteGalvoPolygons, "galvoLabel"_a)
      .def("loadGalvoPolygons", &CMMCore::loadGalvoPolygons, "galvoLabel"_a)
      .def("setGalvoPolygonRepetitions", &CMMCore::setGalvoPolygonRepetitions, "galvoLabel"_a,
           "repetitions"_a)
      .def("runGalvoPolygons", &CMMCore::runGalvoPolygons, "galvoLabel"_a)
      .def("runGalvoSequence", &CMMCore::runGalvoSequence, "galvoLabel"_a)
      .def("getGalvoChannel", &CMMCore::getGalvoChannel, "galvoLabel"_a)

      // Device Discovery
      .def("supportsDeviceDetection", &CMMCore::supportsDeviceDetection, "deviceLabel"_a)
      .def("detectDevice", &CMMCore::detectDevice, "deviceLabel"_a)

      // Hub and Peripheral Devices
      .def("getParentLabel", &CMMCore::getParentLabel, "peripheralLabel"_a)
      .def("setParentLabel", &CMMCore::setParentLabel, "deviceLabel"_a, "parentHubLabel"_a)
      .def("getInstalledDevices", &CMMCore::getInstalledDevices, "hubLabel"_a)
      .def("getInstalledDeviceDescription", &CMMCore::getInstalledDeviceDescription, "hubLabel"_a,
           "peripheralLabel"_a)
      .def("getLoadedPeripheralDevices", &CMMCore::getLoadedPeripheralDevices, "hubLabel"_a)

      ;
}