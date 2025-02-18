#ifndef DEVICEHANDLE_H
#define DEVICEHANDLE_H

#include "MMCore.h"
#include <string>
#include <utility>
#include <vector>

// ------------------------------------------------------------------
// PropertyHandle
// ------------------------------------------------------------------

class PropertyHandle {
  protected:
    CMMCore *core_;
    std::string device_label_;
    std::string property_name_;

  public:
    PropertyHandle(CMMCore *core, const std::string &deviceLabel,
                   const std::string &propertyName)
        : core_(core), device_label_(deviceLabel), property_name_(propertyName) {};
    virtual ~PropertyHandle() {};

    const std::string &getDeviceLabel() const { return device_label_; }
    const std::string &getName() const { return property_name_; }

    std::string getValue() noexcept(false);
    void setValue(const char *propValue) noexcept(false);
    void setValue(const bool propValue) noexcept(false);
    void setValue(const long propValue) noexcept(false);
    void setValue(const float propValue) noexcept(false);
    void setValue(const double propValue) noexcept(false);
    std::vector<std::string> getAllowedValues() noexcept(false);
    bool isReadOnly() noexcept(false);
    bool isPreInit() noexcept(false);
    bool isSequenceable() noexcept(false);
    bool hasLimits() noexcept(false);
    double getLowerLimit() noexcept(false);
    double getUpperLimit() noexcept(false);
    MM::PropertyType getType() noexcept(false);
    void startSequence() noexcept(false);
    void stopSequence() noexcept(false);
    long getSequenceMaxLength() noexcept(false);
    void loadSequence(std::vector<std::string> eventSequence) noexcept(false);
};

// ------------------------------------------------------------------
// DeviceHandle
// ------------------------------------------------------------------
class DeviceHandle {
  protected:
    CMMCore *core_;
    std::string label_;

  public:
    DeviceHandle(CMMCore *core, const std::string &label) : core_(core), label_(label) {};
    virtual ~DeviceHandle() {};

    const std::string &getLabel() const { return label_; }

    MM::DeviceType getType() noexcept(false);
    std::string getLibrary() noexcept(false);
    std::string getName() noexcept(false);
    std::string getDescription() noexcept(false);
    std::vector<std::string> getPropertyNames() noexcept(false);
    PropertyHandle getPropertyObject(const std::string &propertyName) noexcept(false);
    std::vector<PropertyHandle> getPropertyObjects() noexcept(false);
    bool hasProperty(const char *propName) noexcept(false);
    bool isBusy() noexcept(false);
    void await() noexcept(false);
    double getDelayMs() noexcept(false);
    void setDelayMs(double delayMs) noexcept(false);
    bool usesDelay() noexcept(false);
    void unload() noexcept(false);
    void initialize() noexcept(false);
    DeviceInitializationState getInitializationState() noexcept(false);
    std::string getParentLabel() noexcept(false);
    void setParentLabel(const char *parentHubLabel) noexcept(false);
};

// ------------------------------------------------------------------
// StageDeviceHandle
// ------------------------------------------------------------------

class StageDeviceHandle : public DeviceHandle {
  public:
    StageDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};

    void setPosition(double pos);
    double getPosition();
    void setRelativePosition(double distance);
    void stop();
    void home();
    void setOrigin();
    bool isContinuousFocusDrive();
    void setAdapterOrigin(double newZUm) noexcept(false);
    void setFocusDirection(int sign);
    int getFocusDirection();
    bool isSequenceable();
    void startSequence();
    void stopSequence();
    long getSequenceMaxLength();
    void loadSequence(const std::vector<double> &positions);
};

// ------------------------------------------------------------------
// XYStageDeviceHandle
// ------------------------------------------------------------------

class XYStageDeviceHandle : public DeviceHandle {
  public:
    XYStageDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};

    void setPosition(double x, double y);
    std::pair<double, double> getPosition();
    void setRelativePosition(double dx, double dy);
    double getXPosition();
    double getYPosition();
    void stop();
    void home();
    void setOriginXY();
    void setOriginX();
    void setOriginY();
    void setAdapterOriginXY(double newXUm, double newYUm);
    bool isSequenceable();
    void startSequence();
    void stopSequence();
    long getSequenceMaxLength();
    void loadSequence(const std::vector<double> &xSequence,
                      const std::vector<double> &ySequence);
};

// ------------------------------------------------------------------
// CameraDeviceHandle
// ------------------------------------------------------------------

class CameraDeviceHandle : public DeviceHandle {
  public:
    CameraDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};

    double getExposure();
    void setExposure(double exposure);
    void startSequenceAcquisition(long numImages, double intervalMs,
                                  bool stopOnOverflow) noexcept(false);
    void prepareSequenceAcquisition() noexcept(false);
    void stopSequenceAcquisition() noexcept(false);
    bool isSequenceRunning() noexcept(false);
    bool isSequenceable() noexcept(false);
    void startSequence() noexcept(false);
    void stopSequence() noexcept(false);
    long getSequenceMaxLength() noexcept(false);
    void loadSequence(std::vector<double> exposureSequence_ms) noexcept(false);
};

// ------------------------------------------------------------------
// ShutterDeviceHandle
// ------------------------------------------------------------------

class ShutterDeviceHandle : public DeviceHandle {
  public:
    ShutterDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};
    void setOpen(bool state) noexcept(false);
    bool isOpen() noexcept(false);
};

// ------------------------------------------------------------------
// StateDeviceHandle
// ------------------------------------------------------------------

class StateDeviceHandle : public DeviceHandle {
  public:
    StateDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};
    void setState(long state) noexcept(false);
    long getState() noexcept(false);
    long getNumberOfStates();
    void setStateLabel(const char *stateLabel) noexcept(false);
    std::string getStateLabel() noexcept(false);
    void defineStateLabel(long state, const char *stateLabel) noexcept(false);
    std::vector<std::string> getStateLabels() noexcept(false);
    long getStateFromLabel(const char *stateLabel) noexcept(false);
};

// ------------------------------------------------------------------
// SerialDeviceHandle
// ------------------------------------------------------------------
class SerialDeviceHandle : public DeviceHandle {
  public:
    SerialDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};
    void setProperties(const char *answerTimeout, const char *baudRate,
                       const char *delayBetweenCharsMs, const char *handshaking,
                       const char *parity, const char *stopBits) noexcept(false);
    void setCommand(const char *command, const char *term) noexcept(false);
    std::string getAnswer(const char *term) noexcept(false);
    void write(const std::vector<char> &data) noexcept(false);
    std::vector<char> read() noexcept(false);
};

// ------------------------------------------------------------------
// SLMDeviceHandle
// ------------------------------------------------------------------
class SLMDeviceHandle : public DeviceHandle {
  public:
    SLMDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};
    void setImage(unsigned char *pixels) noexcept(false);
    void setImage(imgRGB32 pixels) noexcept(false);
    void setPixelsTo(unsigned char intensity) noexcept(false);
    void setPixelsTo(unsigned char red, unsigned char green,
                     unsigned char blue) noexcept(false);
    void displayImage() noexcept(false);
    void setExposure(double exposure_ms) noexcept(false);
    double getExposure() noexcept(false);
    unsigned getWidth() noexcept(false);
    unsigned getHeight() noexcept(false);
    unsigned getNumberOfComponents() noexcept(false);
    unsigned getBytesPerPixel() noexcept(false);

    long getSequenceMaxLength() noexcept(false);
    void startSequence() noexcept(false);
    void stopSequence() noexcept(false);
    void loadSequence(std::vector<unsigned char *> imageSequence) noexcept(false);
};

// ------------------------------------------------------------------
// GalvoDeviceHandle
// ------------------------------------------------------------------

class GalvoDeviceHandle : public DeviceHandle {
  public:
    GalvoDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};
    void pointAndFire(double x, double y, double pulseTime_us) noexcept(false);
    void setSpotInterval(double pulseTime_us) noexcept(false);
    void setPosition(double x, double y) noexcept(false);
    void getPosition(double &x_stage,
                     double &y_stage) noexcept(false); // using x_stage to get swig to work
    void setIlluminationState(bool on) noexcept(false);
    double getXRange() noexcept(false);
    double getXMinimum() noexcept(false);
    double getYRange() noexcept(false);
    double getYMinimum() noexcept(false);
    void addPolygonVertex(int polygonIndex, double x, double y) noexcept(false);
    void deletePolygons() noexcept(false);
    void loadPolygons() noexcept(false);
    void setPolygonRepetitions(int repetitions) noexcept(false);
    void runPolygons() noexcept(false);
    void runSequence() noexcept(false);
    std::string getChannel() noexcept(false);
};

// ------------------------------------------------------------------
// HubDeviceHandle
// ------------------------------------------------------------------
class HubDeviceHandle : public DeviceHandle {
  public:
    HubDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {};
    std::vector<std::string> getInstalledDevices() noexcept(false);
    std::string getInstalledDeviceDescription(const char *peripheralLabel) noexcept(false);
    std::vector<std::string> getLoadedPeripheralDevices() noexcept(false);
};

// ------------------------------------------------------------------
// others...
// ------------------------------------------------------------------

class ImageProcessorDeviceHandle : public DeviceHandle {
  public:
    ImageProcessorDeviceHandle(CMMCore *core, const std::string &label)
        : DeviceHandle(core, label) {}
};

class MagnifierDeviceHandle : public DeviceHandle {
  public:
    MagnifierDeviceHandle(CMMCore *core, const std::string &label)
        : DeviceHandle(core, label) {}
};

class AutoFocusDeviceHandle : public DeviceHandle {
  public:
    AutoFocusDeviceHandle(CMMCore *core, const std::string &label)
        : DeviceHandle(core, label) {}
};

class SignalIODeviceHandle : public DeviceHandle {
  public:
    SignalIODeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {}
};

class GenericDeviceHandle : public DeviceHandle {
  public:
    GenericDeviceHandle(CMMCore *core, const std::string &label) : DeviceHandle(core, label) {}
};

#endif // DEVICEHANDLE_H
