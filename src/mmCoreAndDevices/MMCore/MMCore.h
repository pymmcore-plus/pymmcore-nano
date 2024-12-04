///////////////////////////////////////////////////////////////////////////////
// FILE:          MMCore.h
// PROJECT:       Micro-Manager
// SUBSYSTEM:     MMCore
//-----------------------------------------------------------------------------
// DESCRIPTION:   The interface to the MM core services.
//
// COPYRIGHT:     University of California, San Francisco, 2006-2014
//                100X Imaging Inc, www.100ximaging.com, 2008
//
// LICENSE:       This library is free software; you can redistribute it and/or
//                modify it under the terms of the GNU Lesser General Public
//                License as published by the Free Software Foundation.
//
//                You should have received a copy of the GNU Lesser General Public
//                License along with the source distribution; if not, write to
//                the Free Software Foundation, Inc., 59 Temple Place, Suite 330,
//                Boston, MA  02111-1307  USA
//
//                This file is distributed in the hope that it will be useful,
//                but WITHOUT ANY WARRANTY; without even the implied warranty
//                of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
//
//                IN NO EVENT SHALL THE COPYRIGHT OWNER OR
//                CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
//                INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES.
//
// AUTHOR:        Nenad Amodaj, nenad@amodaj.com, 06/07/2005
//
// NOTES:         Public methods follow a slightly different naming convention than
//                the rest of the C++ code, i.e we have:
//                   getConfiguration();
//                instead of:
//                   GetConfiguration();
//                The alternative (lowercase function names) convention is used
//                because public method names appear as wrapped methods in other
//                languages, in particular Java.

#pragma once

/*
 * Important! Read this before changing this file.
 *
 * Please see the version number and explanatory comment in the implementation
 * file (MMCore.cpp).
 */

// We use exception specifications to instruct SWIG to generate the correct
// exception specifications for Java.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4290) // 'C++ exception specification ignored'
#endif

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
// 'dynamic exception specifications are deprecated in C++11 [-Wdeprecated]'
#pragma GCC diagnostic ignored "-Wdeprecated"
#endif

#include "../MMDevice/DeviceThreads.h"
#include "../MMDevice/MMDevice.h"
#include "../MMDevice/MMDeviceConstants.h"
#include "Configuration.h"
#include "Error.h"
#include "ErrorCodes.h"
#include "Logging/Logger.h"

#include <cstring>
#include <deque>
#include <map>
#include <memory>
#include <string>
#include <vector>


#if !defined(SWIGJAVA) && !defined(SWIGPYTHON)
#   ifdef _MSC_VER
#      define MMCORE_DEPRECATED(prototype) __declspec(deprecated) prototype
#   elif defined(__GNUC__)
#      define MMCORE_DEPRECATED(prototype) prototype __attribute__((deprecated))
#   else
#      define MMCORE_DEPRECATED(prototype) prototype
#   endif
#else
#   define MMCORE_DEPRECATED(prototype) prototype
#endif

extern const int MMCore_versionMajor;
extern const int MMCore_versionMinor;
extern const int MMCore_versionPatch;

class CPluginManager;
class CircularBuffer;
class ConfigGroupCollection;
class CoreCallback;
class CorePropertyCollection;
class MMEventCallback;
class Metadata;
class PixelSizeConfigGroup;

class AutoFocusInstance;
class CameraInstance;
class DeviceInstance;
class GalvoInstance;
class ImageProcessorInstance;
class SLMInstance;
class ShutterInstance;
class StageInstance;
class XYStageInstance;

class CMMCore;

namespace mm {
   class DeviceManager;
   class LogManager;
} // namespace mm

typedef unsigned int* imgRGB32;

enum DeviceInitializationState {
   Uninitialized,
   InitializedSuccessfully,
   InitializationFailed,
};


/// The Micro-Manager Core.
/**
 * Provides a device-independent interface for hardware control. Additionally,
 * provides some facilities (such as configuration groups) for application
 * programming.
 *
 * The signatures of most of the public member functions are designed to be
 * wrapped by SWIG with minimal manual configuration.
 */
class CMMCore
{
   friend class CoreCallback;
   friend class CorePropertyCollection;

public:
   CMMCore();
   ~CMMCore();

   /// A static method that does nothing.
   /**
    * This method can be called as a sanity check when dynamically loading the
    * Core library (e.g. through a foreign function interface for a high-level
    * language).
    */
   static void noop() {}

   /** \name Core feature control. */
   ///@{
   static void enableFeature(const char* name, bool enable) noexcept(false);
   static bool isFeatureEnabled(const char* name) noexcept(false);
   ///@}

   /** \name Initialization and setup. */
   ///@{
   void loadDevice(const char* label, const char* moduleName,
         const char* deviceName) noexcept(false);
   void unloadDevice(const char* label) noexcept(false);
   void unloadAllDevices() noexcept(false);
   void initializeAllDevices() noexcept(false);
   void initializeDevice(const char* label) noexcept(false);
   DeviceInitializationState getDeviceInitializationState(const char* label) const noexcept(false);
   void reset() noexcept(false);

   void unloadLibrary(const char* moduleName) noexcept(false);

   void updateCoreProperties() noexcept(false);

   std::string getCoreErrorText(int code) const;

   std::string getVersionInfo() const;
   std::string getAPIVersionInfo() const;
   Configuration getSystemState();
   void setSystemState(const Configuration& conf);
   Configuration getConfigState(const char* group, const char* config) noexcept(false);
   Configuration getConfigGroupState(const char* group) noexcept(false);
   void saveSystemState(const char* fileName) noexcept(false);
   void loadSystemState(const char* fileName) noexcept(false);
   void saveSystemConfiguration(const char* fileName) noexcept(false);
   void loadSystemConfiguration(const char* fileName) noexcept(false);
   void registerCallback(MMEventCallback* cb);
   ///@}

   /** \name Logging and log management. */
   ///@{
   void setPrimaryLogFile(const char* filename, bool truncate = false) noexcept(false);
   std::string getPrimaryLogFile() const;

   void logMessage(const char* msg);
   void logMessage(const char* msg, bool debugOnly);
   void enableDebugLog(bool enable);
   bool debugLogEnabled();
   void enableStderrLog(bool enable);
   bool stderrLogEnabled();

   int startSecondaryLogFile(const char* filename, bool enableDebug,
         bool truncate = true, bool synchronous = false) noexcept(false);
   void stopSecondaryLogFile(int handle) noexcept(false);

   ///@}

   /** \name Device listing. */
   ///@{
   std::vector<std::string> getDeviceAdapterSearchPaths();
   void setDeviceAdapterSearchPaths(const std::vector<std::string>& paths);

   std::vector<std::string> getDeviceAdapterNames() noexcept(false);

   std::vector<std::string> getAvailableDevices(const char* library) noexcept(false);
   std::vector<std::string> getAvailableDeviceDescriptions(const char* library) noexcept(false);
   std::vector<long> getAvailableDeviceTypes(const char* library) noexcept(false);
   ///@}

   /** \name Generic device control.
    *
    * Functionality supported by all devices.
    */
   ///@{
   std::vector<std::string> getLoadedDevices() const;
   std::vector<std::string> getLoadedDevicesOfType(MM::DeviceType devType) const;
   MM::DeviceType getDeviceType(const char* label) noexcept(false);
   std::string getDeviceLibrary(const char* label) noexcept(false);
   std::string getDeviceName(const char* label) noexcept(false);
   std::string getDeviceDescription(const char* label) noexcept(false);

   std::vector<std::string> getDevicePropertyNames(const char* label) noexcept(false);
   bool hasProperty(const char* label, const char* propName) noexcept(false);
   std::string getProperty(const char* label, const char* propName) noexcept(false);
   void setProperty(const char* label, const char* propName, const char* propValue) noexcept(false);
   void setProperty(const char* label, const char* propName, const bool propValue) noexcept(false);
   void setProperty(const char* label, const char* propName, const long propValue) noexcept(false);
   void setProperty(const char* label, const char* propName, const float propValue) noexcept(false);
   void setProperty(const char* label, const char* propName, const double propValue) noexcept(false);

   std::vector<std::string> getAllowedPropertyValues(const char* label, const char* propName) noexcept(false);
   bool isPropertyReadOnly(const char* label, const char* propName) noexcept(false);
   bool isPropertyPreInit(const char* label, const char* propName) noexcept(false);
   bool isPropertySequenceable(const char* label, const char* propName) noexcept(false);
   bool hasPropertyLimits(const char* label, const char* propName) noexcept(false);
   double getPropertyLowerLimit(const char* label, const char* propName) noexcept(false);
   double getPropertyUpperLimit(const char* label, const char* propName) noexcept(false);
   MM::PropertyType getPropertyType(const char* label, const char* propName) noexcept(false);

   void startPropertySequence(const char* label, const char* propName) noexcept(false);
   void stopPropertySequence(const char* label, const char* propName) noexcept(false);
   long getPropertySequenceMaxLength(const char* label, const char* propName) noexcept(false);
   void loadPropertySequence(const char* label, const char* propName, std::vector<std::string> eventSequence) noexcept(false);

   bool deviceBusy(const char* label) noexcept(false);
   void waitForDevice(const char* label) noexcept(false);
   void waitForConfig(const char* group, const char* configName) noexcept(false);
   bool systemBusy() noexcept(false);
   void waitForSystem() noexcept(false);
   bool deviceTypeBusy(MM::DeviceType devType) noexcept(false);
   void waitForDeviceType(MM::DeviceType devType) noexcept(false);

   double getDeviceDelayMs(const char* label) noexcept(false);
   void setDeviceDelayMs(const char* label, double delayMs) noexcept(false);
   bool usesDeviceDelay(const char* label) noexcept(false);

   void setTimeoutMs(long timeoutMs) {if (timeoutMs > 0) timeoutMs_ = timeoutMs;}
   long getTimeoutMs() { return timeoutMs_;}

   void sleep(double intervalMs) const;
   ///@}

   /** \name Management of 'current' device for specific roles. */
   ///@{
   std::string getCameraDevice();
   std::string getShutterDevice();
   std::string getFocusDevice();
   std::string getXYStageDevice();
   std::string getAutoFocusDevice();
   std::string getImageProcessorDevice();
   std::string getSLMDevice();
   std::string getGalvoDevice();
   std::string getChannelGroup();
   void setCameraDevice(const char* cameraLabel) noexcept(false);
   void setShutterDevice(const char* shutterLabel) noexcept(false);
   void setFocusDevice(const char* focusLabel) noexcept(false);
   void setXYStageDevice(const char* xyStageLabel) noexcept(false);
   void setAutoFocusDevice(const char* focusLabel) noexcept(false);
   void setImageProcessorDevice(const char* procLabel) noexcept(false);
   void setSLMDevice(const char* slmLabel) noexcept(false);
   void setGalvoDevice(const char* galvoLabel) noexcept(false);
   void setChannelGroup(const char* channelGroup) noexcept(false);
   ///@}

   /** \name System state cache.
    *
    * The system state cache retains the last-set or last-read value of each
    * device property.
    */
   ///@{
   Configuration getSystemStateCache() const;
   void updateSystemStateCache();
   std::string getPropertyFromCache(const char* deviceLabel,
         const char* propName) const noexcept(false);
   std::string getCurrentConfigFromCache(const char* groupName) noexcept(false);
   Configuration getConfigGroupStateFromCache(const char* group) noexcept(false);
   ///@}

   /** \name Configuration groups. */
   ///@{
   void defineConfig(const char* groupName, const char* configName) noexcept(false);
   void defineConfig(const char* groupName, const char* configName,
         const char* deviceLabel, const char* propName,
         const char* value) noexcept(false);
   void defineConfigGroup(const char* groupName) noexcept(false);
   void deleteConfigGroup(const char* groupName) noexcept(false);
   void renameConfigGroup(const char* oldGroupName,
         const char* newGroupName) noexcept(false);
   bool isGroupDefined(const char* groupName);
   bool isConfigDefined(const char* groupName, const char* configName);
   void setConfig(const char* groupName, const char* configName) noexcept(false);
   void deleteConfig(const char* groupName, const char* configName) noexcept(false);
   void deleteConfig(const char* groupName, const char* configName,
         const char* deviceLabel, const char* propName) noexcept(false);
   void renameConfig(const char* groupName, const char* oldConfigName,
         const char* newConfigName) noexcept(false);
   std::vector<std::string> getAvailableConfigGroups() const;
   std::vector<std::string> getAvailableConfigs(const char* configGroup) const;
   std::string getCurrentConfig(const char* groupName) noexcept(false);
   Configuration getConfigData(const char* configGroup,
         const char* configName) noexcept(false);
   ///@}

   /** \name The pixel size configuration group. */
   ///@{
   std::string getCurrentPixelSizeConfig() noexcept(false);
   std::string getCurrentPixelSizeConfig(bool cached) noexcept(false);
   double getPixelSizeUm();
   double getPixelSizeUm(bool cached);
   double getPixelSizeUmByID(const char* resolutionID) noexcept(false);
   std::vector<double> getPixelSizeAffine() noexcept(false);
   std::vector<double> getPixelSizeAffine(bool cached) noexcept(false);
   std::vector<double> getPixelSizeAffineByID(const char* resolutionID) noexcept(false);
   double getMagnificationFactor() const;
   void setPixelSizeUm(const char* resolutionID, double pixSize)  noexcept(false);
   void setPixelSizeAffine(const char* resolutionID, std::vector<double> affine)  noexcept(false);
   void definePixelSizeConfig(const char* resolutionID,
         const char* deviceLabel, const char* propName,
         const char* value) noexcept(false);
   void definePixelSizeConfig(const char* resolutionID) noexcept(false);
   std::vector<std::string> getAvailablePixelSizeConfigs() const;
   bool isPixelSizeConfigDefined(const char* resolutionID) const noexcept(false);
   void setPixelSizeConfig(const char* resolutionID) noexcept(false);
   void renamePixelSizeConfig(const char* oldConfigName,
         const char* newConfigName) noexcept(false);
   void deletePixelSizeConfig(const char* configName) noexcept(false);
   Configuration getPixelSizeConfigData(const char* configName) noexcept(false);
   ///@}

   /** \name Image acquisition. */
   ///@{
   void setROI(int x, int y, int xSize, int ySize) noexcept(false);
   void setROI(const char* label, int x, int y, int xSize, int ySize) noexcept(false);
   void getROI(int& x, int& y, int& xSize, int& ySize) noexcept(false);
   void getROI(const char* label, int& x, int& y, int& xSize, int& ySize) noexcept(false);
   void clearROI() noexcept(false);

   bool isMultiROISupported() noexcept(false);
   bool isMultiROIEnabled() noexcept(false);
   void setMultiROI(std::vector<unsigned> xs, std::vector<unsigned> ys,
           std::vector<unsigned> widths,
           std::vector<unsigned> heights) noexcept(false);
   void getMultiROI(std::vector<unsigned>& xs, std::vector<unsigned>& ys,
           std::vector<unsigned>& widths,
           std::vector<unsigned>& heights) noexcept(false);

   void setExposure(double exp) noexcept(false);
   void setExposure(const char* cameraLabel, double dExp) noexcept(false);
   double getExposure() noexcept(false);
   double getExposure(const char* label) noexcept(false);

   void snapImage() noexcept(false);
   void* getImage() noexcept(false);
   void* getImage(unsigned numChannel) noexcept(false);

   unsigned getImageWidth();
   unsigned getImageHeight();
   unsigned getBytesPerPixel();
   unsigned getImageBitDepth();
   unsigned getNumberOfComponents();
   unsigned getNumberOfCameraChannels();
   std::string getCameraChannelName(unsigned int channelNr);
   long getImageBufferSize();

   void setAutoShutter(bool state);
   bool getAutoShutter();
   void setShutterOpen(bool state) noexcept(false);
   bool getShutterOpen() noexcept(false);
   void setShutterOpen(const char* shutterLabel, bool state) noexcept(false);
   bool getShutterOpen(const char* shutterLabel) noexcept(false);

   void startSequenceAcquisition(long numImages, double intervalMs,
         bool stopOnOverflow) noexcept(false);
   void startSequenceAcquisition(const char* cameraLabel, long numImages,
         double intervalMs, bool stopOnOverflow) noexcept(false);
   void prepareSequenceAcquisition(const char* cameraLabel) noexcept(false);
   void startContinuousSequenceAcquisition(double intervalMs) noexcept(false);
   void stopSequenceAcquisition() noexcept(false);
   void stopSequenceAcquisition(const char* cameraLabel) noexcept(false);
   bool isSequenceRunning() throw ();
   bool isSequenceRunning(const char* cameraLabel) noexcept(false);

   void* getLastImage() noexcept(false);
   void* popNextImage() noexcept(false);
   void* getLastImageMD(unsigned channel, unsigned slice, Metadata& md)
      const noexcept(false);
   void* popNextImageMD(unsigned channel, unsigned slice, Metadata& md)
      noexcept(false);
   void* getLastImageMD(Metadata& md) const noexcept(false);
   void* getNBeforeLastImageMD(unsigned long n, Metadata& md)
      const noexcept(false);
   void* popNextImageMD(Metadata& md) noexcept(false);

   long getRemainingImageCount();
   long getBufferTotalCapacity();
   long getBufferFreeCapacity();
   bool isBufferOverflowed() const;
   void setCircularBufferMemoryFootprint(unsigned sizeMB) noexcept(false);
   unsigned getCircularBufferMemoryFootprint();
   void initializeCircularBuffer() noexcept(false);
   void clearCircularBuffer() noexcept(false);

   bool isExposureSequenceable(const char* cameraLabel) noexcept(false);
   void startExposureSequence(const char* cameraLabel) noexcept(false);
   void stopExposureSequence(const char* cameraLabel) noexcept(false);
   long getExposureSequenceMaxLength(const char* cameraLabel) noexcept(false);
   void loadExposureSequence(const char* cameraLabel,
         std::vector<double> exposureSequence_ms) noexcept(false);
   ///@}

   /** \name Autofocus control. */
   ///@{
   double getLastFocusScore();
   double getCurrentFocusScore();
   void enableContinuousFocus(bool enable) noexcept(false);
   bool isContinuousFocusEnabled() noexcept(false);
   bool isContinuousFocusLocked() noexcept(false);
   bool isContinuousFocusDrive(const char* stageLabel) noexcept(false);
   void fullFocus() noexcept(false);
   void incrementalFocus() noexcept(false);
   void setAutoFocusOffset(double offset) noexcept(false);
   double getAutoFocusOffset() noexcept(false);
   ///@}

   /** \name State device control. */
   ///@{
   void setState(const char* stateDeviceLabel, long state) noexcept(false);
   long getState(const char* stateDeviceLabel) noexcept(false);
   long getNumberOfStates(const char* stateDeviceLabel);
   void setStateLabel(const char* stateDeviceLabel,
         const char* stateLabel) noexcept(false);
   std::string getStateLabel(const char* stateDeviceLabel) noexcept(false);
   void defineStateLabel(const char* stateDeviceLabel,
         long state, const char* stateLabel) noexcept(false);
   std::vector<std::string> getStateLabels(const char* stateDeviceLabel)
      noexcept(false);
   long getStateFromLabel(const char* stateDeviceLabel,
         const char* stateLabel) noexcept(false);
   ///@}

   /** \name Focus (Z) stage control. */
   ///@{
   void setPosition(const char* stageLabel, double position) noexcept(false);
   void setPosition(double position) noexcept(false);
   double getPosition(const char* stageLabel) noexcept(false);
   double getPosition() noexcept(false);
   void setRelativePosition(const char* stageLabel, double d) noexcept(false);
   void setRelativePosition(double d) noexcept(false);
   void setOrigin(const char* stageLabel) noexcept(false);
   void setOrigin() noexcept(false);
   void setAdapterOrigin(const char* stageLabel, double newZUm) noexcept(false);
   void setAdapterOrigin(double newZUm) noexcept(false);

   void setFocusDirection(const char* stageLabel, int sign);
   int getFocusDirection(const char* stageLabel) noexcept(false);

   bool isStageSequenceable(const char* stageLabel) noexcept(false);
   bool isStageLinearSequenceable(const char* stageLabel) noexcept(false);
   void startStageSequence(const char* stageLabel) noexcept(false);
   void stopStageSequence(const char* stageLabel) noexcept(false);
   long getStageSequenceMaxLength(const char* stageLabel) noexcept(false);
   void loadStageSequence(const char* stageLabel,
         std::vector<double> positionSequence) noexcept(false);
   void setStageLinearSequence(const char* stageLabel, double dZ_um, int nSlices) noexcept(false);
   ///@}

   /** \name XY stage control. */
   ///@{
   void setXYPosition(const char* xyStageLabel,
         double x, double y) noexcept(false);
   void setXYPosition(double x, double y) noexcept(false);
   void setRelativeXYPosition(const char* xyStageLabel,
         double dx, double dy) noexcept(false);
   void setRelativeXYPosition(double dx, double dy) noexcept(false);
   void getXYPosition(const char* xyStageLabel,
         double &x_stage, double &y_stage) noexcept(false);
   void getXYPosition(double &x_stage, double &y_stage) noexcept(false);
   double getXPosition(const char* xyStageLabel) noexcept(false);
   double getYPosition(const char* xyStageLabel) noexcept(false);
   double getXPosition() noexcept(false);
   double getYPosition() noexcept(false);
   void stop(const char* xyOrZStageLabel) noexcept(false);
   void home(const char* xyOrZStageLabel) noexcept(false);
   void setOriginXY(const char* xyStageLabel) noexcept(false);
   void setOriginXY() noexcept(false);
   void setOriginX(const char* xyStageLabel) noexcept(false);
   void setOriginX() noexcept(false);
   void setOriginY(const char* xyStageLabel) noexcept(false);
   void setOriginY() noexcept(false);
   void setAdapterOriginXY(const char* xyStageLabel,
         double newXUm, double newYUm) noexcept(false);
   void setAdapterOriginXY(double newXUm, double newYUm) noexcept(false);

   bool isXYStageSequenceable(const char* xyStageLabel) noexcept(false);
   void startXYStageSequence(const char* xyStageLabel) noexcept(false);
   void stopXYStageSequence(const char* xyStageLabel) noexcept(false);
   long getXYStageSequenceMaxLength(const char* xyStageLabel) noexcept(false);
   void loadXYStageSequence(const char* xyStageLabel,
         std::vector<double> xSequence,
         std::vector<double> ySequence) noexcept(false);
   ///@}

   /** \name Serial port control. */
   ///@{
   void setSerialProperties(const char* portName,
      const char* answerTimeout,
      const char* baudRate,
      const char* delayBetweenCharsMs,
      const char* handshaking,
      const char* parity,
      const char* stopBits) noexcept(false);

   void setSerialPortCommand(const char* portLabel, const char* command,
         const char* term) noexcept(false);
   std::string getSerialPortAnswer(const char* portLabel,
         const char* term) noexcept(false);
   void writeToSerialPort(const char* portLabel,
         const std::vector<char> &data) noexcept(false);
   std::vector<char> readFromSerialPort(const char* portLabel)
      noexcept(false);
   ///@}

   /** \name SLM control.
    *
    * Control of spatial light modulators such as liquid crystal on silicon
    * (LCoS), digital micromirror devices (DMD), or multimedia projectors.
    */
   ///@{
   void setSLMImage(const char* slmLabel,
         unsigned char * pixels) noexcept(false);
   void setSLMImage(const char* slmLabel, imgRGB32 pixels) noexcept(false);
   void setSLMPixelsTo(const char* slmLabel,
         unsigned char intensity) noexcept(false);
   void setSLMPixelsTo(const char* slmLabel,
         unsigned char red, unsigned char green,
         unsigned char blue) noexcept(false);
   void displaySLMImage(const char* slmLabel) noexcept(false);
   void setSLMExposure(const char* slmLabel, double exposure_ms)
      noexcept(false);
   double getSLMExposure(const char* slmLabel) noexcept(false);
   unsigned getSLMWidth(const char* slmLabel) noexcept(false);
   unsigned getSLMHeight(const char* slmLabel) noexcept(false);
   unsigned getSLMNumberOfComponents(const char* slmLabel) noexcept(false);
   unsigned getSLMBytesPerPixel(const char* slmLabel) noexcept(false);

   long getSLMSequenceMaxLength(const char* slmLabel) noexcept(false);
   void startSLMSequence(const char* slmLabel) noexcept(false);
   void stopSLMSequence(const char* slmLabel) noexcept(false);
   void loadSLMSequence(const char* slmLabel,
         std::vector<unsigned char*> imageSequence) noexcept(false);
   ///@}

   /** \name Galvo control.
    *
    * Control of beam-steering devices.
    */
   ///@{
   void pointGalvoAndFire(const char* galvoLabel, double x, double y,
         double pulseTime_us) noexcept(false);
   void setGalvoSpotInterval(const char* galvoLabel,
         double pulseTime_us) noexcept(false);
   void setGalvoPosition(const char* galvoLabel, double x, double y)
      noexcept(false);
   void getGalvoPosition(const char* galvoLabel,
         double &x_stage, double &y_stage) noexcept(false); // using x_stage to get swig to work
   void setGalvoIlluminationState(const char* galvoLabel, bool on)
      noexcept(false);
   double getGalvoXRange(const char* galvoLabel) noexcept(false);
   double getGalvoXMinimum(const char* galvoLabel) noexcept(false);
   double getGalvoYRange(const char* galvoLabel) noexcept(false);
   double getGalvoYMinimum(const char* galvoLabel) noexcept(false);
   void addGalvoPolygonVertex(const char* galvoLabel, int polygonIndex,
         double x, double y) noexcept(false);
   void deleteGalvoPolygons(const char* galvoLabel) noexcept(false);
   void loadGalvoPolygons(const char* galvoLabel) noexcept(false);
   void setGalvoPolygonRepetitions(const char* galvoLabel, int repetitions)
      noexcept(false);
   void runGalvoPolygons(const char* galvoLabel) noexcept(false);
   void runGalvoSequence(const char* galvoLabel) noexcept(false);
   std::string getGalvoChannel(const char* galvoLabel) noexcept(false);
   ///@}

   /** \name Device discovery. */
   ///@{
   bool supportsDeviceDetection(const char* deviceLabel);
   MM::DeviceDetectionStatus detectDevice(const char* deviceLabel);
   ///@}

   /** \name Hub and peripheral devices. */
   ///@{
   std::string getParentLabel(const char* peripheralLabel) noexcept(false);
   void setParentLabel(const char* deviceLabel,
         const char* parentHubLabel) noexcept(false);

   std::vector<std::string> getInstalledDevices(const char* hubLabel) noexcept(false);
   std::string getInstalledDeviceDescription(const char* hubLabel,
         const char* peripheralLabel) noexcept(false);
   std::vector<std::string> getLoadedPeripheralDevices(const char* hubLabel) noexcept(false);
   ///@}

private:
   // make object non-copyable
   CMMCore(const CMMCore&);
   CMMCore& operator=(const CMMCore&);

private:
   // LogManager should be the first data member, so that it is available for
   // as long as possible during construction and (especially) destruction.
   std::shared_ptr<mm::LogManager> logManager_;
   mm::logging::Logger appLogger_;
   mm::logging::Logger coreLogger_;

   bool everSnapped_;

   std::weak_ptr<CameraInstance> currentCameraDevice_;
   std::weak_ptr<ShutterInstance> currentShutterDevice_;
   std::weak_ptr<StageInstance> currentFocusDevice_;
   std::weak_ptr<XYStageInstance> currentXYStageDevice_;
   std::weak_ptr<AutoFocusInstance> currentAutofocusDevice_;
   std::weak_ptr<SLMInstance> currentSLMDevice_;
   std::weak_ptr<GalvoInstance> currentGalvoDevice_;
   std::weak_ptr<ImageProcessorInstance> currentImageProcessor_;

   std::string channelGroup_;
   long pollingIntervalMs_;
   long timeoutMs_;
   bool autoShutter_;
   std::vector<double> *nullAffine_;
   MM::Core* callback_;                 // core services for devices
   ConfigGroupCollection* configGroups_;
   CorePropertyCollection* properties_;
   MMEventCallback* externalCallback_;  // notification hook to the higher layer (e.g. GUI)
   PixelSizeConfigGroup* pixelSizeGroup_;
   CircularBuffer* cbuf_;

   std::shared_ptr<CPluginManager> pluginManager_;
   std::shared_ptr<mm::DeviceManager> deviceManager_;
   std::map<int, std::string> errorText_;

   // Must be unlocked when calling MMEventCallback or calling device methods
   // or acquiring a module lock
   mutable MMThreadLock stateCacheLock_;
   mutable Configuration stateCache_; // Synchronized by stateCacheLock_

   MMThreadLock* pPostedErrorsLock_;
   mutable std::deque<std::pair< int, std::string> > postedErrors_;

private:
   void InitializeErrorMessages();
   void CreateCoreProperties();

   // Parameter/value validation
   static void CheckDeviceLabel(const char* label) noexcept(false);
   static void CheckPropertyName(const char* propName) noexcept(false);
   static void CheckPropertyValue(const char* propValue) noexcept(false);
   static void CheckStateLabel(const char* stateLabel) noexcept(false);
   static void CheckConfigGroupName(const char* groupName) noexcept(false);
   static void CheckConfigPresetName(const char* presetName) noexcept(false);
   bool IsCoreDeviceLabel(const char* label) const noexcept(false);

   void applyConfiguration(const Configuration& config) noexcept(false);
   int applyProperties(std::vector<PropertySetting>& props, std::string& lastError);
   void waitForDevice(std::shared_ptr<DeviceInstance> pDev) noexcept(false);
   Configuration getConfigGroupState(const char* group, bool fromCache) noexcept(false);
   std::string getDeviceErrorText(int deviceCode, std::shared_ptr<DeviceInstance> pDevice);
   std::string getDeviceName(std::shared_ptr<DeviceInstance> pDev);
   void logError(const char* device, const char* msg);
   void updateAllowedChannelGroups();
   void assignDefaultRole(std::shared_ptr<DeviceInstance> pDev);
   void updateCoreProperty(const char* propName, MM::DeviceType devType) noexcept(false);
   void loadSystemConfigurationImpl(const char* fileName) noexcept(false);
   void initializeAllDevicesSerial() noexcept(false);
   void initializeAllDevicesParallel() noexcept(false);
   int initializeVectorOfDevices(std::vector<std::pair<std::shared_ptr<DeviceInstance>, std::string> > pDevices);
};

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif

#ifdef _MSC_VER
#pragma warning(pop)
#endif
