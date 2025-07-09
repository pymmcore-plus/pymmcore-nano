#pragma once

#ifdef MMCORE_ENABLE_TESTING

#include "MockDeviceAdapter.h"
#include "../MMDevice/MMDevice.h"
#include <memory>
#include <string>
#include <vector>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <algorithm>

// Simple mock camera device for testing
class MockCamera : public MM::Camera {
private:
    std::string label_;
    std::string description_;
    std::string moduleName_;
    bool initialized_;
    bool busy_;
    double delayMs_;
    MM::Core* callback_;
    
    // Camera-specific
    unsigned width_;
    unsigned height_;
    unsigned bytesPerPixel_;
    double exposure_;
    bool acquiring_;
    std::vector<unsigned char> imageBuffer_;
    
public:
    MockCamera() 
        : initialized_(false), busy_(false), delayMs_(0.0), callback_(nullptr),
          width_(512), height_(512), bytesPerPixel_(1), exposure_(10.0), acquiring_(false) {
        SetDescription("Mock Camera for Testing");
        imageBuffer_.resize(width_ * height_ * bytesPerPixel_, 128);
    }
    
    virtual ~MockCamera() {}
    
    // Device interface
    virtual MM::DeviceType GetType() const { return MM::CameraDevice; }
    virtual int Initialize() { initialized_ = true; return DEVICE_OK; }
    virtual int Shutdown() { initialized_ = false; return DEVICE_OK; }
    virtual bool Busy() { return busy_; }
    virtual double GetDelayMs() const { return delayMs_; }
    virtual void SetDelayMs(double delay) { delayMs_ = delay; }
    virtual bool UsesDelay() { return true; }
    virtual void SetLabel(const char* label) { label_ = label; }
    virtual void GetLabel(char* name) const { strcpy(name, label_.c_str()); }
    virtual void SetModuleName(const char* moduleName) { moduleName_ = moduleName; }
    virtual void GetModuleName(char* moduleName) const { strcpy(moduleName, moduleName_.c_str()); }
    virtual void SetDescription(const char* description) { description_ = description; }
    virtual void GetDescription(char* description) const { strcpy(description, description_.c_str()); }
    virtual void GetName(char* name) const { strcpy(name, "MockCamera"); }
    virtual void SetCallback(MM::Core* callback) { callback_ = callback; }
    virtual bool SupportsDeviceDetection() { return false; }
    virtual MM::DeviceDetectionStatus DetectDevice() { return MM::Misconfigured; }
    virtual void SetParentID(const char*) {}
    virtual void GetParentID(char*) const {}
    
    // Camera interface
    virtual int SnapImage() { 
        busy_ = true;
        // Simulate exposure time
        return DEVICE_OK; 
    }
    virtual const unsigned char* GetImageBuffer() { 
        busy_ = false;
        return imageBuffer_.data(); 
    }
    virtual const unsigned char* GetImageBuffer(unsigned channelNr) {
        // For multi-channel support - just return same buffer for all channels
        (void)channelNr;
        return GetImageBuffer();
    }
    virtual const unsigned int* GetImageBufferAsRGB32() {
        // Simple implementation - just cast to uint32
        return reinterpret_cast<const unsigned int*>(imageBuffer_.data());
    }
    virtual unsigned GetNumberOfComponents() const { return 1; }
    virtual int GetComponentName(unsigned component, char* name) {
        if (component == 0) {
            strcpy(name, "Gray");
            return DEVICE_OK;
        }
        return DEVICE_INVALID_PROPERTY;
    }
    virtual unsigned GetNumberOfChannels() const { return 1; }
    virtual int GetChannelName(unsigned channel, char* name) {
        if (channel == 0) {
            strcpy(name, "Channel0");
            return DEVICE_OK;
        }
        return DEVICE_INVALID_PROPERTY;
    }
    virtual unsigned GetImageWidth() const { return width_; }
    virtual unsigned GetImageHeight() const { return height_; }
    virtual unsigned GetImageBytesPerPixel() const { return bytesPerPixel_; }
    virtual unsigned GetBitDepth() const { return 8; }
    virtual long GetImageBufferSize() const { return width_ * height_ * bytesPerPixel_; }
    virtual double GetPixelSizeUm() const { return 1.0; }
    virtual double GetExposure() const { return exposure_; }
    virtual void SetExposure(double exp) { exposure_ = exp; }
    virtual int SetROI(unsigned x, unsigned y, unsigned xSize, unsigned ySize) { 
        (void)x; (void)y;  // Ignore position for simplicity
        width_ = xSize; height_ = ySize; 
        imageBuffer_.resize(width_ * height_ * bytesPerPixel_, 128);
        return DEVICE_OK; 
    }
    virtual int GetROI(unsigned& x, unsigned& y, unsigned& xSize, unsigned& ySize) { 
        x = 0; y = 0; xSize = width_; ySize = height_; return DEVICE_OK; 
    }
    virtual int ClearROI() { 
        width_ = 512; height_ = 512; 
        imageBuffer_.resize(width_ * height_ * bytesPerPixel_, 128);
        return DEVICE_OK; 
    }
    virtual bool SupportsMultiROI() { return false; }
    virtual bool IsMultiROISet() { return false; }
    virtual int GetMultiROICount(unsigned& count) { count = 0; return DEVICE_OK; }
    virtual int SetMultiROI(const unsigned*, const unsigned*, const unsigned*, const unsigned*, unsigned) { 
        return DEVICE_NOT_SUPPORTED; 
    }
    virtual int GetMultiROI(unsigned*, unsigned*, unsigned*, unsigned*, unsigned*) { 
        return DEVICE_NOT_SUPPORTED; 
    }
    virtual int PrepareSequenceAcqusition() { return DEVICE_OK; }
    virtual int StartSequenceAcquisition(long numImages, double intervalMs, bool stopOnOverflow) { 
        (void)numImages; (void)intervalMs; (void)stopOnOverflow;
        acquiring_ = true; return DEVICE_OK; 
    }
    virtual int StartSequenceAcquisition(double intervalMs) { 
        (void)intervalMs;
        acquiring_ = true; return DEVICE_OK; 
    }
    virtual int StopSequenceAcquisition() { acquiring_ = false; return DEVICE_OK; }
    virtual bool IsCapturing() { return acquiring_; }
    virtual void GetTags(char* serializedMetadata) { 
        if (serializedMetadata) strcpy(serializedMetadata, "{}"); 
    }
    virtual void AddTag(const char*, const char*, const char*) {}
    virtual void RemoveTag(const char*) {}
    virtual int GetBinning() const { return 1; }
    virtual int SetBinning(int) { return DEVICE_OK; }
    virtual int IsExposureSequenceable(bool& isSequenceable) const { isSequenceable = false; return DEVICE_OK; }
    virtual int GetExposureSequenceMaxLength(long& nrEvents) const { nrEvents = 0; return DEVICE_OK; }
    virtual int StartExposureSequence() { return DEVICE_OK; }
    virtual int StopExposureSequence() { return DEVICE_OK; }
    virtual int ClearExposureSequence() { return DEVICE_OK; }
    virtual int AddToExposureSequence(double) { return DEVICE_OK; }
    virtual int SendExposureSequence() const { return DEVICE_OK; }
    
    // Property interface - simplified implementations
    virtual unsigned GetNumberOfProperties() const { return 3; }
    virtual int GetProperty(const char* name, char* value) const {
        if (strcmp(name, "Exposure") == 0) {
            snprintf(value, MM::MaxStrLength, "%.2f", exposure_);
            return DEVICE_OK;
        } else if (strcmp(name, "Width") == 0) {
            snprintf(value, MM::MaxStrLength, "%u", width_);
            return DEVICE_OK;
        } else if (strcmp(name, "Height") == 0) {
            snprintf(value, MM::MaxStrLength, "%u", height_);
            return DEVICE_OK;
        }
        return DEVICE_INVALID_PROPERTY;
    }
    virtual int SetProperty(const char* name, const char* value) {
        if (strcmp(name, "Exposure") == 0) {
            exposure_ = atof(value);
            return DEVICE_OK;
        } else if (strcmp(name, "Width") == 0) {
            width_ = atoi(value);
            imageBuffer_.resize(width_ * height_ * bytesPerPixel_, 128);
            return DEVICE_OK;
        } else if (strcmp(name, "Height") == 0) {
            height_ = atoi(value);
            imageBuffer_.resize(width_ * height_ * bytesPerPixel_, 128);
            return DEVICE_OK;
        }
        return DEVICE_INVALID_PROPERTY;
    }
    virtual bool HasProperty(const char* name) const {
        return strcmp(name, "Exposure") == 0 || strcmp(name, "Width") == 0 || strcmp(name, "Height") == 0;
    }
    virtual bool GetPropertyName(unsigned idx, char* name) const {
        switch(idx) {
            case 0: strcpy(name, "Exposure"); return true;
            case 1: strcpy(name, "Width"); return true;
            case 2: strcpy(name, "Height"); return true;
            default: return false;
        }
    }
    virtual int GetPropertyReadOnly(const char*, bool& readOnly) const { readOnly = false; return DEVICE_OK; }
    virtual int GetPropertyInitStatus(const char*, bool& preInit) const { preInit = false; return DEVICE_OK; }
    virtual int HasPropertyLimits(const char*, bool& hasLimits) const { hasLimits = false; return DEVICE_OK; }
    virtual int GetPropertyLowerLimit(const char*, double&) const { return DEVICE_OK; }
    virtual int GetPropertyUpperLimit(const char*, double&) const { return DEVICE_OK; }
    virtual int GetPropertyType(const char*, MM::PropertyType& pt) const { pt = MM::Float; return DEVICE_OK; }
    virtual unsigned GetNumberOfPropertyValues(const char*) const { return 0; }
    virtual bool GetPropertyValueAt(const char*, unsigned, char*) const { return false; }
    virtual int IsPropertySequenceable(const char*, bool& isSequenceable) const { isSequenceable = false; return DEVICE_OK; }
    virtual int GetPropertySequenceMaxLength(const char*, long& nrEvents) const { nrEvents = 0; return DEVICE_OK; }
    virtual int StartPropertySequence(const char*) { return DEVICE_OK; }
    virtual int StopPropertySequence(const char*) { return DEVICE_OK; }
    virtual int ClearPropertySequence(const char*) { return DEVICE_OK; }
    virtual int AddToPropertySequence(const char*, const char*) { return DEVICE_OK; }
    virtual int SendPropertySequence(const char*) { return DEVICE_OK; }
    virtual bool GetErrorText(int, char*) const { return false; }
    
    // Deprecated methods
    virtual HDEVMODULE GetModuleHandle() const { return nullptr; }
    virtual void SetModuleHandle(HDEVMODULE) {}
};

// Simple mock stage device for testing
class MockStage : public MM::Stage {
private:
    std::string label_;
    std::string description_;
    std::string moduleName_;
    bool initialized_;
    bool busy_;
    double delayMs_;
    MM::Core* callback_;
    double position_;
    
public:
    MockStage() 
        : initialized_(false), busy_(false), delayMs_(0.0), callback_(nullptr), position_(0.0) {
        SetDescription("Mock Stage for Testing");
    }
    
    virtual ~MockStage() {}
    
    // Device interface
    virtual MM::DeviceType GetType() const { return MM::StageDevice; }
    virtual int Initialize() { initialized_ = true; return DEVICE_OK; }
    virtual int Shutdown() { initialized_ = false; return DEVICE_OK; }
    virtual bool Busy() { return busy_; }
    virtual double GetDelayMs() const { return delayMs_; }
    virtual void SetDelayMs(double delay) { delayMs_ = delay; }
    virtual bool UsesDelay() { return true; }
    virtual void SetLabel(const char* label) { label_ = label; }
    virtual void GetLabel(char* name) const { strcpy(name, label_.c_str()); }
    virtual void SetModuleName(const char* moduleName) { moduleName_ = moduleName; }
    virtual void GetModuleName(char* moduleName) const { strcpy(moduleName, moduleName_.c_str()); }
    virtual void SetDescription(const char* description) { description_ = description; }
    virtual void GetDescription(char* description) const { strcpy(description, description_.c_str()); }
    virtual void GetName(char* name) const { strcpy(name, "MockStage"); }
    virtual void SetCallback(MM::Core* callback) { callback_ = callback; }
    virtual bool SupportsDeviceDetection() { return false; }
    virtual MM::DeviceDetectionStatus DetectDevice() { return MM::Misconfigured; }
    virtual void SetParentID(const char*) {}
    virtual void GetParentID(char*) const {}
    
    // Stage interface
    virtual int SetPositionUm(double pos) { position_ = pos; return DEVICE_OK; }
    virtual int GetPositionUm(double& pos) { pos = position_; return DEVICE_OK; }
    virtual int SetRelativePositionUm(double d) { position_ += d; return DEVICE_OK; }
    virtual int SetOrigin() { position_ = 0.0; return DEVICE_OK; }
    virtual int GetLimits(double& min, double& max) { min = -1000.0; max = 1000.0; return DEVICE_OK; }
    virtual int Move(double velocity) { (void)velocity; return DEVICE_OK; }
    virtual int Stop() { return DEVICE_OK; }
    virtual int Home() { position_ = 0.0; return DEVICE_OK; }
    virtual int SetAdapterOriginUm(double d) { (void)d; return DEVICE_OK; }
    virtual int SetPositionSteps(long steps) { position_ = steps * 0.1; return DEVICE_OK; }  // 0.1 um per step
    virtual int GetPositionSteps(long& steps) { steps = (long)(position_ / 0.1); return DEVICE_OK; }
    virtual int GetFocusDirection(MM::FocusDirection& direction) { 
        direction = MM::FocusDirectionUnknown; 
        return DEVICE_OK; 
    }
    virtual bool IsContinuousFocusDrive() const { return false; }
    virtual int IsStageSequenceable(bool& isSequenceable) const { isSequenceable = false; return DEVICE_OK; }
    virtual int IsStageLinearSequenceable(bool& isSequenceable) const { isSequenceable = false; return DEVICE_OK; }
    virtual int GetStageSequenceMaxLength(long& nrEvents) const { nrEvents = 0; return DEVICE_OK; }
    virtual int StartStageSequence() { return DEVICE_NOT_SUPPORTED; }
    virtual int StopStageSequence() { return DEVICE_NOT_SUPPORTED; }
    virtual int ClearStageSequence() { return DEVICE_NOT_SUPPORTED; }
    virtual int AddToStageSequence(double) { return DEVICE_NOT_SUPPORTED; }
    virtual int SendStageSequence() { return DEVICE_NOT_SUPPORTED; }
    virtual int SetStageLinearSequence(double, long) { return DEVICE_NOT_SUPPORTED; }
    
    // Property interface - simplified
    virtual unsigned GetNumberOfProperties() const { return 1; }
    virtual int GetProperty(const char* name, char* value) const {
        if (strcmp(name, "Position") == 0) {
            snprintf(value, MM::MaxStrLength, "%.2f", position_);
            return DEVICE_OK;
        }
        return DEVICE_INVALID_PROPERTY;
    }
    virtual int SetProperty(const char* name, const char* value) {
        if (strcmp(name, "Position") == 0) {
            position_ = atof(value);
            return DEVICE_OK;
        }
        return DEVICE_INVALID_PROPERTY;
    }
    virtual bool HasProperty(const char* name) const {
        return strcmp(name, "Position") == 0;
    }
    virtual bool GetPropertyName(unsigned idx, char* name) const {
        if (idx == 0) { strcpy(name, "Position"); return true; }
        return false;
    }
    virtual int GetPropertyReadOnly(const char*, bool& readOnly) const { readOnly = false; return DEVICE_OK; }
    virtual int GetPropertyInitStatus(const char*, bool& preInit) const { preInit = false; return DEVICE_OK; }
    virtual int HasPropertyLimits(const char*, bool& hasLimits) const { hasLimits = false; return DEVICE_OK; }
    virtual int GetPropertyLowerLimit(const char*, double&) const { return DEVICE_OK; }
    virtual int GetPropertyUpperLimit(const char*, double&) const { return DEVICE_OK; }
    virtual int GetPropertyType(const char*, MM::PropertyType& pt) const { pt = MM::Float; return DEVICE_OK; }
    virtual unsigned GetNumberOfPropertyValues(const char*) const { return 0; }
    virtual bool GetPropertyValueAt(const char*, unsigned, char*) const { return false; }
    virtual int IsPropertySequenceable(const char*, bool& isSequenceable) const { isSequenceable = false; return DEVICE_OK; }
    virtual int GetPropertySequenceMaxLength(const char*, long& nrEvents) const { nrEvents = 0; return DEVICE_OK; }
    virtual int StartPropertySequence(const char*) { return DEVICE_OK; }
    virtual int StopPropertySequence(const char*) { return DEVICE_OK; }
    virtual int ClearPropertySequence(const char*) { return DEVICE_OK; }
    virtual int AddToPropertySequence(const char*, const char*) { return DEVICE_OK; }
    virtual int SendPropertySequence(const char*) { return DEVICE_OK; }
    virtual bool GetErrorText(int, char*) const { return false; }
    
    // Deprecated methods
    virtual HDEVMODULE GetModuleHandle() const { return nullptr; }
    virtual void SetModuleHandle(HDEVMODULE) {}
};

// Python-accessible mock device adapter
class PythonMockDeviceAdapter : public MockDeviceAdapter {
private:
    std::vector<std::unique_ptr<MM::Device>> devices_;
    
public:
    // Ensure proper destructor for virtual inheritance
    virtual ~PythonMockDeviceAdapter() = default;
    
    // Prevent copying to avoid unique_ptr issues
    PythonMockDeviceAdapter(const PythonMockDeviceAdapter&) = delete;
    PythonMockDeviceAdapter& operator=(const PythonMockDeviceAdapter&) = delete;
    
    // Allow moving
    PythonMockDeviceAdapter(PythonMockDeviceAdapter&&) = default;
    PythonMockDeviceAdapter& operator=(PythonMockDeviceAdapter&&) = default;
    
    // Default constructor
    PythonMockDeviceAdapter() = default;
    
    void InitializeModuleData(RegisterDeviceFunc registerDevice) override {
        registerDevice("MockCamera", MM::CameraDevice, "Mock camera for testing");
        registerDevice("MockStage", MM::StageDevice, "Mock stage for testing");
    }
    
    MM::Device* CreateDevice(const char* name) override {
        if (strcmp(name, "MockCamera") == 0) {
            auto device = std::make_unique<MockCamera>();
            MM::Device* ptr = device.get();
            devices_.push_back(std::move(device));
            return ptr;
        } else if (strcmp(name, "MockStage") == 0) {
            auto device = std::make_unique<MockStage>();
            MM::Device* ptr = device.get();
            devices_.push_back(std::move(device));
            return ptr;
        }
        return nullptr;
    }
    
    void DeleteDevice(MM::Device* device) override {
        devices_.erase(
            std::remove_if(devices_.begin(), devices_.end(),
                [device](const std::unique_ptr<MM::Device>& ptr) {
                    return ptr.get() == device;
                }),
            devices_.end()
        );
    }
};

#endif // MMCORE_ENABLE_TESTING
