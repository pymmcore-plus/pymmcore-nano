#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "MMCore.h"
#include "MMEventCallback.h"

namespace nb = nanobind;

using namespace nb::literals;

NB_MODULE(_pymmcore_nano, m) {
  m.doc() = "Python bindings for MMCore";

  // define module level attributes
  m.attr("DEVICE_INTERFACE_VERSION") = DEVICE_INTERFACE_VERSION;

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

  nb::enum_<MM::DeviceDetectionStatus>(m, "DeviceDetectionStatus", nb::is_arithmetic())
      .value("Misconfigured", MM::DeviceDetectionStatus::Misconfigured)
      .value("Unimplemented", MM::DeviceDetectionStatus::Unimplemented)
      .value("CanNotCommunicate", MM::DeviceDetectionStatus::CanNotCommunicate)
      .value("CanCommunicate", MM::DeviceDetectionStatus::CanCommunicate);

  nb::enum_<MM::PropertyType>(m, "PropertyType", nb::is_arithmetic())
      .value("Undef", MM::PropertyType::Undef)
      .value("String", MM::PropertyType::String)
      .value("Float", MM::PropertyType::Float)
      .value("Integer", MM::PropertyType::Integer);

  nb::enum_<MM::FocusDirection>(m, "FocusDirection", nb::is_arithmetic())
      .value("FocusDirectionUnknown", MM::FocusDirection::FocusDirectionUnknown)
      .value("FocusDirectionTowardSample", MM::FocusDirection::FocusDirectionTowardSample)
      .value("FocusDirectionAwayFromSample", MM::FocusDirection::FocusDirectionAwayFromSample);

  nb::enum_<MM::PortType>(m, "PortType", nb::is_arithmetic())
      .value("InvalidPort", MM::PortType::InvalidPort)
      .value("SerialPort", MM::PortType::SerialPort)
      .value("USBPort", MM::PortType::USBPort)
      .value("HIDPort", MM::PortType::HIDPort);

  nb::enum_<DeviceInitializationState>(m, "DeviceInitializationState", nb::is_arithmetic())
      .value("CoreIdle", DeviceInitializationState::Uninitialized)
      .value("CoreBusy", DeviceInitializationState::InitializedSuccessfully)
      .value("CoreError", DeviceInitializationState::InitializationFailed);

  //////////////////// Supporting classes ////////////////////

  nb::class_<Configuration>(m, "Configuration")
      .def(nb::init<>())  // Assuming it has a default constructor
      // Add any methods or properties for Configuration here
      ;

  nb::class_<Metadata>(m, "Metadata")
      .def(nb::init<>())  // Assuming it has a default constructor
                          // Add any methods or properties for Configuration here
      ;

  nb::class_<MMEventCallback>(m, "MMEventCallback")
      .def(nb::init<>())  // Assuming it has a default constructor
      // Add any methods or properties for MMEventCallback here
      ;
  //////////////////// MMCore ////////////////////

  nb::class_<CMMCore>(m, "CMMCore")
      .def(nb::init<>())

      // accept any object that can be cast to a string, so as to support Path objects
      .def(
          "loadSystemConfiguration",
          [](CMMCore& self, nb::object fileName) {
            self.loadSystemConfiguration(nb::str(fileName).c_str());  // convert to string
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
      .def("setPrimaryLogFile", &CMMCore::setPrimaryLogFile, "filename"_a, "truncate"_a = false)
      .def("getPrimaryLogFile", &CMMCore::getPrimaryLogFile)
      .def("logMessage", nb::overload_cast<const char*>(&CMMCore::logMessage), "msg"_a)
      .def("logMessage", nb::overload_cast<const char*, bool>(&CMMCore::logMessage), "msg"_a,
           "debugOnly"_a)

      .def("enableDebugLog", &CMMCore::enableDebugLog, "enable"_a)
      .def("debugLogEnabled", &CMMCore::debugLogEnabled)
      .def("enableStderrLog", &CMMCore::enableStderrLog, "enable"_a)
      .def("stderrLogEnabled", &CMMCore::stderrLogEnabled)
      .def("startSecondaryLogFile", &CMMCore::startSecondaryLogFile, "filename"_a, "enableDebug"_a,
           "truncate"_a = true, "synchronous"_a = false)
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