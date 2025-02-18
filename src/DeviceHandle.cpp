#include "DeviceHandle.h"

// ------------------------------------------------------------------
// PropertyHandle
// ------------------------------------------------------------------

std::string PropertyHandle::getValue() {
    return core_->getProperty(device_label_.c_str(), property_name_.c_str());
}

void PropertyHandle::setValue(const char *propValue) {
    core_->setProperty(device_label_.c_str(), property_name_.c_str(), propValue);
}

void PropertyHandle::setValue(const bool propValue) {
    core_->setProperty(device_label_.c_str(), property_name_.c_str(), propValue);
}

void PropertyHandle::setValue(const long propValue) {
    core_->setProperty(device_label_.c_str(), property_name_.c_str(), propValue);
}

void PropertyHandle::setValue(const float propValue) {
    core_->setProperty(device_label_.c_str(), property_name_.c_str(), propValue);
}

void PropertyHandle::setValue(const double propValue) {
    core_->setProperty(device_label_.c_str(), property_name_.c_str(), propValue);
}

std::vector<std::string> PropertyHandle::getAllowedValues() {
    return core_->getAllowedPropertyValues(device_label_.c_str(), property_name_.c_str());
}

bool PropertyHandle::isReadOnly() {
    return core_->isPropertyReadOnly(device_label_.c_str(), property_name_.c_str());
}

bool PropertyHandle::isPreInit() {
    return core_->isPropertyPreInit(device_label_.c_str(), property_name_.c_str());
}

bool PropertyHandle::isSequenceable() {
    return core_->isPropertySequenceable(device_label_.c_str(), property_name_.c_str());
}

bool PropertyHandle::hasLimits() {
    return core_->hasPropertyLimits(device_label_.c_str(), property_name_.c_str());
}

double PropertyHandle::getLowerLimit() {
    return core_->getPropertyLowerLimit(device_label_.c_str(), property_name_.c_str());
}

double PropertyHandle::getUpperLimit() {
    return core_->getPropertyUpperLimit(device_label_.c_str(), property_name_.c_str());
}

MM::PropertyType PropertyHandle::getType() {
    return core_->getPropertyType(device_label_.c_str(), property_name_.c_str());
}

void PropertyHandle::startSequence() {
    core_->startPropertySequence(device_label_.c_str(), property_name_.c_str());
}

void PropertyHandle::stopSequence() {
    core_->stopPropertySequence(device_label_.c_str(), property_name_.c_str());
}

long PropertyHandle::getSequenceMaxLength() {
    return core_->getPropertySequenceMaxLength(device_label_.c_str(), property_name_.c_str());
}

void PropertyHandle::loadSequence(std::vector<std::string> eventSequence) {
    core_->loadPropertySequence(device_label_.c_str(), property_name_.c_str(), eventSequence);
}

// ------------------------------------------------------------------
// DeviceHandle
// ------------------------------------------------------------------

MM::DeviceType DeviceHandle::getType() { return core_->getDeviceType(label_.c_str()); }

std::string DeviceHandle::getLibrary() { return core_->getDeviceLibrary(label_.c_str()); }

std::string DeviceHandle::getName() { return core_->getDeviceName(label_.c_str()); }

std::string DeviceHandle::getDescription() {
    return core_->getDeviceDescription(label_.c_str());
}

std::vector<std::string> DeviceHandle::getPropertyNames() {
    return core_->getDevicePropertyNames(label_.c_str());
}

bool DeviceHandle::hasProperty(const char *propName) {
    return core_->hasProperty(label_.c_str(), propName);
}

PropertyHandle DeviceHandle::getPropertyObject(const std::string &propertyName) {
    return PropertyHandle(core_, label_, propertyName);
}

std::vector<PropertyHandle> DeviceHandle::getPropertyObjects() {
    std::vector<PropertyHandle> properties;
    for (const auto &propertyName : core_->getDevicePropertyNames(label_.c_str())) {
        properties.push_back(PropertyHandle(core_, label_, propertyName));
    }
    return properties;
}

bool DeviceHandle::isBusy() { return core_->deviceBusy(label_.c_str()); }

void DeviceHandle::await() { core_->waitForDevice(label_.c_str()); }

double DeviceHandle::getDelayMs() { return core_->getDeviceDelayMs(label_.c_str()); }

void DeviceHandle::setDelayMs(double delayMs) {
    core_->setDeviceDelayMs(label_.c_str(), delayMs);
}

bool DeviceHandle::usesDelay() { return core_->usesDeviceDelay(label_.c_str()); }

void DeviceHandle::unload() { core_->unloadDevice(label_.c_str()); }

void DeviceHandle::initialize() { core_->initializeDevice(label_.c_str()); }

DeviceInitializationState DeviceHandle::getInitializationState() {
    return core_->getDeviceInitializationState(label_.c_str());
}

void DeviceHandle::setParentLabel(const char *parentHubLabel) {
    core_->setParentLabel(label_.c_str(), parentHubLabel);
}

std::string DeviceHandle::getParentLabel() { return core_->getParentLabel(label_.c_str()); }

// ------------------------------------------------------------------
// StageDeviceHandle
// ------------------------------------------------------------------

void StageDeviceHandle::setPosition(double pos) { core_->setPosition(label_.c_str(), pos); }

double StageDeviceHandle::getPosition() { return core_->getPosition(label_.c_str()); }

void StageDeviceHandle::setRelativePosition(double distance) {
    core_->setRelativePosition(label_.c_str(), distance);
}

void StageDeviceHandle::stop() { core_->stop(label_.c_str()); }

void StageDeviceHandle::home() { core_->home(label_.c_str()); }

void StageDeviceHandle::setOrigin() { core_->setOrigin(label_.c_str()); }

bool StageDeviceHandle::isContinuousFocusDrive() {
    core_->isContinuousFocusDrive(label_.c_str());
}
void StageDeviceHandle::setAdapterOrigin(double newZUm) {
    core_->setAdapterOrigin(label_.c_str(), newZUm);
}

void StageDeviceHandle::setFocusDirection(int sign) {
    core_->setFocusDirection(label_.c_str(), sign);
}

int StageDeviceHandle::getFocusDirection() { return core_->getFocusDirection(label_.c_str()); }

bool StageDeviceHandle::isSequenceable() { return core_->isStageSequenceable(label_.c_str()); }

void StageDeviceHandle::startSequence() { core_->startStageSequence(label_.c_str()); }

void StageDeviceHandle::stopSequence() { core_->stopStageSequence(label_.c_str()); }

long StageDeviceHandle::getSequenceMaxLength() {
    return core_->getStageSequenceMaxLength(label_.c_str());
}

void StageDeviceHandle::loadSequence(const std::vector<double> &positions) {
    core_->loadStageSequence(label_.c_str(), positions);
}

// ------------------------------------------------------------------
// XYStageDeviceHandle
// ------------------------------------------------------------------

void XYStageDeviceHandle::setPosition(double x, double y) {
    core_->setXYPosition(label_.c_str(), x, y);
}

std::pair<double, double> XYStageDeviceHandle::getPosition() {
    double x, y;
    core_->getXYPosition(label_.c_str(), x, y);
    return {x, y};
}

void XYStageDeviceHandle::setRelativePosition(double dx, double dy) {
    core_->setRelativeXYPosition(label_.c_str(), dx, dy);
}

double XYStageDeviceHandle::getXPosition() { return core_->getXPosition(label_.c_str()); }

double XYStageDeviceHandle::getYPosition() { return core_->getYPosition(label_.c_str()); }

void XYStageDeviceHandle::stop() { core_->stop(label_.c_str()); }

void XYStageDeviceHandle::home() { core_->home(label_.c_str()); }

void XYStageDeviceHandle::setOriginXY() { core_->setOriginXY(label_.c_str()); }

void XYStageDeviceHandle::setOriginX() { core_->setOriginX(label_.c_str()); }

void XYStageDeviceHandle::setOriginY() { core_->setOriginY(label_.c_str()); }

void XYStageDeviceHandle::setAdapterOriginXY(double newXUm, double newYUm) {
    core_->setAdapterOriginXY(label_.c_str(), newXUm, newYUm);
}

bool XYStageDeviceHandle::isSequenceable() {
    return core_->isXYStageSequenceable(label_.c_str());
}

void XYStageDeviceHandle::startSequence() { core_->startXYStageSequence(label_.c_str()); }

void XYStageDeviceHandle::stopSequence() { core_->stopXYStageSequence(label_.c_str()); }

long XYStageDeviceHandle::getSequenceMaxLength() {
    return core_->getXYStageSequenceMaxLength(label_.c_str());
}

void XYStageDeviceHandle::loadSequence(const std::vector<double> &xSequence,
                                       const std::vector<double> &ySequence) {
    core_->loadXYStageSequence(label_.c_str(), xSequence, ySequence);
}

// ------------------------------------------------------------------
// CameraDeviceHandle
// ------------------------------------------------------------------

void CameraDeviceHandle::setExposure(double exposure) {
    core_->setExposure(label_.c_str(), exposure);
}

double CameraDeviceHandle::getExposure() { return core_->getExposure(label_.c_str()); }

void CameraDeviceHandle::startSequenceAcquisition(long numImages, double intervalMs,
                                                  bool stopOnOverflow) {
    core_->startSequenceAcquisition(label_.c_str(), numImages, intervalMs, stopOnOverflow);
}

void CameraDeviceHandle::prepareSequenceAcquisition() {
    core_->prepareSequenceAcquisition(label_.c_str());
}

void CameraDeviceHandle::stopSequenceAcquisition() {
    core_->stopSequenceAcquisition(label_.c_str());
}

bool CameraDeviceHandle::isSequenceRunning() { core_->isSequenceRunning(label_.c_str()); }

bool CameraDeviceHandle::isSequenceable() { core_->isExposureSequenceable(label_.c_str()); }

void CameraDeviceHandle::startSequence() { core_->startExposureSequence(label_.c_str()); }

void CameraDeviceHandle::stopSequence() { core_->stopExposureSequence(label_.c_str()); }

long CameraDeviceHandle::getSequenceMaxLength() {
    core_->getExposureSequenceMaxLength(label_.c_str());
}

void CameraDeviceHandle::loadSequence(std::vector<double> exposureSequence_ms) {
    core_->loadExposureSequence(label_.c_str(), exposureSequence_ms);
}

// ------------------------------------------------------------------
// ShutterDeviceHandle
// ------------------------------------------------------------------

void ShutterDeviceHandle::setOpen(bool state) { core_->setShutterOpen(label_.c_str(), state); }

bool ShutterDeviceHandle::isOpen() { return core_->getShutterOpen(label_.c_str()); }

// ------------------------------------------------------------------
// StateDeviceHandle
// ------------------------------------------------------------------

void StateDeviceHandle::setState(long state) { core_->setState(label_.c_str(), state); }

long StateDeviceHandle::getState() { return core_->getState(label_.c_str()); }

long StateDeviceHandle::getNumberOfStates() { return core_->getNumberOfStates(label_.c_str()); }

void StateDeviceHandle::setStateLabel(const char *stateLabel) {
    core_->setStateLabel(label_.c_str(), stateLabel);
}

std::string StateDeviceHandle::getStateLabel() { return core_->getStateLabel(label_.c_str()); }

void StateDeviceHandle::defineStateLabel(long state, const char *stateLabel) {
    core_->defineStateLabel(label_.c_str(), state, stateLabel);
}

std::vector<std::string> StateDeviceHandle::getStateLabels() {
    return core_->getStateLabels(label_.c_str());
}

long StateDeviceHandle::getStateFromLabel(const char *stateLabel) {
    return core_->getStateFromLabel(label_.c_str(), stateLabel);
}

// ------------------------------------------------------------------
// SerialDeviceHandle
// ------------------------------------------------------------------

void SerialDeviceHandle::setProperties(const char *answerTimeout, const char *baudRate,
                                       const char *delayBetweenCharsMs, const char *handshaking,
                                       const char *parity, const char *stopBits) {
    core_->setSerialProperties(label_.c_str(), answerTimeout, baudRate, delayBetweenCharsMs,
                               handshaking, parity, stopBits);
}

void SerialDeviceHandle::setCommand(const char *command, const char *term) {
    core_->setSerialPortCommand(label_.c_str(), command, term);
}

std::string SerialDeviceHandle::getAnswer(const char *term) {
    return core_->getSerialPortAnswer(label_.c_str(), term);
}

void SerialDeviceHandle::write(const std::vector<char> &data) {
    core_->writeToSerialPort(label_.c_str(), data);
}

std::vector<char> SerialDeviceHandle::read() {
    return core_->readFromSerialPort(label_.c_str());
}

// ------------------------------------------------------------------
// SLMDeviceHandle
// ------------------------------------------------------------------

void SLMDeviceHandle::setImage(unsigned char *pixels) noexcept(false) {
    core_->setSLMImage(label_.c_str(), pixels);
}

void SLMDeviceHandle::setImage(imgRGB32 pixels) noexcept(false) {
    core_->setSLMImage(label_.c_str(), pixels);
}

void SLMDeviceHandle::setPixelsTo(unsigned char intensity) noexcept(false) {
    core_->setSLMPixelsTo(label_.c_str(), intensity);
}

void SLMDeviceHandle::setPixelsTo(unsigned char red, unsigned char green,
                                  unsigned char blue) noexcept(false) {
    core_->setSLMPixelsTo(label_.c_str(), red, green, blue);
}

void SLMDeviceHandle::displayImage() noexcept(false) { core_->displaySLMImage(label_.c_str()); }

void SLMDeviceHandle::setExposure(double exposure_ms) noexcept(false) {
    core_->setSLMExposure(label_.c_str(), exposure_ms);
}

double SLMDeviceHandle::getExposure() noexcept(false) {
    return core_->getSLMExposure(label_.c_str());
}

unsigned SLMDeviceHandle::getWidth() noexcept(false) {
    return core_->getSLMWidth(label_.c_str());
}

unsigned SLMDeviceHandle::getHeight() noexcept(false) {
    return core_->getSLMHeight(label_.c_str());
}

unsigned SLMDeviceHandle::getNumberOfComponents() noexcept(false) {
    return core_->getSLMNumberOfComponents(label_.c_str());
}

unsigned SLMDeviceHandle::getBytesPerPixel() noexcept(false) {
    return core_->getSLMBytesPerPixel(label_.c_str());
}

long SLMDeviceHandle::getSequenceMaxLength() noexcept(false) {
    return core_->getSLMSequenceMaxLength(label_.c_str());
}

void SLMDeviceHandle::startSequence() noexcept(false) {
    core_->startSLMSequence(label_.c_str());
}

void SLMDeviceHandle::stopSequence() noexcept(false) { core_->stopSLMSequence(label_.c_str()); }

void SLMDeviceHandle::loadSequence(std::vector<unsigned char *> imageSequence) noexcept(false) {
    core_->loadSLMSequence(label_.c_str(), imageSequence);
}

// ------------------------------------------------------------------
// GalvoDeviceHandle
// ------------------------------------------------------------------

void GalvoDeviceHandle::pointAndFire(double x, double y, double pulseTime_us) noexcept(false) {
    core_->pointGalvoAndFire(label_.c_str(), x, y, pulseTime_us);
}

void GalvoDeviceHandle::setSpotInterval(double pulseTime_us) noexcept(false) {
    core_->setGalvoSpotInterval(label_.c_str(), pulseTime_us);
}

void GalvoDeviceHandle::setPosition(double x, double y) noexcept(false) {
    core_->setGalvoPosition(label_.c_str(), x, y);
}

void GalvoDeviceHandle::getPosition(double &x_stage, double &y_stage) noexcept(false) {
    core_->getGalvoPosition(label_.c_str(), x_stage, y_stage);
}

void GalvoDeviceHandle::setIlluminationState(bool on) noexcept(false) {
    core_->setGalvoIlluminationState(label_.c_str(), on);
}

double GalvoDeviceHandle::getXRange() noexcept(false) {
    return core_->getGalvoXRange(label_.c_str());
}

double GalvoDeviceHandle::getXMinimum() noexcept(false) {
    return core_->getGalvoXMinimum(label_.c_str());
}

double GalvoDeviceHandle::getYRange() noexcept(false) {
    return core_->getGalvoYRange(label_.c_str());
}

double GalvoDeviceHandle::getYMinimum() noexcept(false) {
    return core_->getGalvoYMinimum(label_.c_str());
}

void GalvoDeviceHandle::addPolygonVertex(int polygonIndex, double x, double y) noexcept(false) {
    core_->addGalvoPolygonVertex(label_.c_str(), polygonIndex, x, y);
}

void GalvoDeviceHandle::deletePolygons() noexcept(false) {
    core_->deleteGalvoPolygons(label_.c_str());
}

void GalvoDeviceHandle::loadPolygons() noexcept(false) {
    core_->loadGalvoPolygons(label_.c_str());
}

void GalvoDeviceHandle::setPolygonRepetitions(int repetitions) noexcept(false) {
    core_->setGalvoPolygonRepetitions(label_.c_str(), repetitions);
}

void GalvoDeviceHandle::runPolygons() noexcept(false) {
    core_->runGalvoPolygons(label_.c_str());
}

void GalvoDeviceHandle::runSequence() noexcept(false) {
    core_->runGalvoSequence(label_.c_str());
}

std::string GalvoDeviceHandle::getChannel() noexcept(false) {
    return core_->getGalvoChannel(label_.c_str());
}

// ------------------------------------------------------------------
// HubDeviceHandle
// ------------------------------------------------------------------

std::vector<std::string> HubDeviceHandle::getInstalledDevices() noexcept(false) {
    return core_->getInstalledDevices(label_.c_str());
}

std::string
HubDeviceHandle::getInstalledDeviceDescription(const char *peripheralLabel) noexcept(false) {
    return core_->getInstalledDeviceDescription(label_.c_str(), peripheralLabel);
}

std::vector<std::string> HubDeviceHandle::getLoadedPeripheralDevices() noexcept(false) {
    return core_->getLoadedPeripheralDevices(label_.c_str());
}
