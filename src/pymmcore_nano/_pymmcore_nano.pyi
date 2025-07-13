import enum
from collections.abc import Sequence
from typing import Annotated, overload

from numpy.typing import ArrayLike

DEVICE_INTERFACE_VERSION: int = 73
MODULE_INTERFACE_VERSION: int = 10
MMCore_version: str = "11.9.0"
MMCore_version_info: tuple = (11, 9, 0)
PYMMCORE_NANO_VERSION: str = "2"
MM_CODE_OK: int = 0
MM_CODE_ERR: int = 1
DEVICE_OK: int = 0
DEVICE_ERR: int = 1
DEVICE_INVALID_PROPERTY: int = 2
DEVICE_INVALID_PROPERTY_VALUE: int = 3
DEVICE_DUPLICATE_PROPERTY: int = 4
DEVICE_INVALID_PROPERTY_TYPE: int = 5
DEVICE_NATIVE_MODULE_FAILED: int = 6
DEVICE_UNSUPPORTED_DATA_FORMAT: int = 7
DEVICE_INTERNAL_INCONSISTENCY: int = 8
DEVICE_NOT_SUPPORTED: int = 9
DEVICE_UNKNOWN_LABEL: int = 10
DEVICE_UNSUPPORTED_COMMAND: int = 11
DEVICE_UNKNOWN_POSITION: int = 12
DEVICE_NO_CALLBACK_REGISTERED: int = 13
DEVICE_SERIAL_COMMAND_FAILED: int = 14
DEVICE_SERIAL_BUFFER_OVERRUN: int = 15
DEVICE_SERIAL_INVALID_RESPONSE: int = 16
DEVICE_SERIAL_TIMEOUT: int = 17
DEVICE_SELF_REFERENCE: int = 18
DEVICE_NO_PROPERTY_DATA: int = 19
DEVICE_DUPLICATE_LABEL: int = 20
DEVICE_INVALID_INPUT_PARAM: int = 21
DEVICE_BUFFER_OVERFLOW: int = 22
DEVICE_NONEXISTENT_CHANNEL: int = 23
DEVICE_INVALID_PROPERTY_LIMITS: int = 24
DEVICE_INVALID_PROPERTY_LIMTS: int = 24
DEVICE_SNAP_IMAGE_FAILED: int = 25
DEVICE_IMAGE_PARAMS_FAILED: int = 26
DEVICE_CORE_FOCUS_STAGE_UNDEF: int = 27
DEVICE_CORE_EXPOSURE_FAILED: int = 28
DEVICE_CORE_CONFIG_FAILED: int = 29
DEVICE_CAMERA_BUSY_ACQUIRING: int = 30
DEVICE_INCOMPATIBLE_IMAGE: int = 31
DEVICE_CAN_NOT_SET_PROPERTY: int = 32
DEVICE_CORE_CHANNEL_PRESETS_FAILED: int = 33
DEVICE_LOCALLY_DEFINED_ERROR: int = 34
DEVICE_NOT_CONNECTED: int = 35
DEVICE_COMM_HUB_MISSING: int = 36
DEVICE_DUPLICATE_LIBRARY: int = 37
DEVICE_PROPERTY_NOT_SEQUENCEABLE: int = 38
DEVICE_SEQUENCE_TOO_LARGE: int = 39
DEVICE_OUT_OF_MEMORY: int = 40
DEVICE_NOT_YET_IMPLEMENTED: int = 41
DEVICE_PUMP_IS_RUNNING: int = 42
g_Keyword_Name: str = "Name"
g_Keyword_Description: str = "Description"
g_Keyword_CameraName: str = "CameraName"
g_Keyword_CameraID: str = "CameraID"
g_Keyword_CameraChannelName: str = "CameraChannelName"
g_Keyword_CameraChannelIndex: str = "CameraChannelIndex"
g_Keyword_Binning: str = "Binning"
g_Keyword_Exposure: str = "Exposure"
g_Keyword_ActualExposure: str = "ActualExposure"
g_Keyword_ActualInterval_ms: str = "ActualInterval-ms"
g_Keyword_Interval_ms: str = "Interval-ms"
g_Keyword_Elapsed_Time_ms: str = "ElapsedTime-ms"
g_Keyword_PixelType: str = "PixelType"
g_Keyword_ReadoutTime: str = "ReadoutTime"
g_Keyword_ReadoutMode: str = "ReadoutMode"
g_Keyword_Gain: str = "Gain"
g_Keyword_EMGain: str = "EMGain"
g_Keyword_Offset: str = "Offset"
g_Keyword_CCDTemperature: str = "CCDTemperature"
g_Keyword_CCDTemperatureSetPoint: str = "CCDTemperatureSetPoint"
g_Keyword_State: str = "State"
g_Keyword_Label: str = "Label"
g_Keyword_Position: str = "Position"
g_Keyword_Type: str = "Type"
g_Keyword_Delay: str = "Delay_ms"
g_Keyword_BaudRate: str = "BaudRate"
g_Keyword_DataBits: str = "DataBits"
g_Keyword_StopBits: str = "StopBits"
g_Keyword_Parity: str = "Parity"
g_Keyword_Handshaking: str = "Handshaking"
g_Keyword_DelayBetweenCharsMs: str = "DelayBetweenCharsMs"
g_Keyword_Port: str = "Port"
g_Keyword_AnswerTimeout: str = "AnswerTimeout"
g_Keyword_Speed: str = "Speed"
g_Keyword_CoreDevice: str = "Core"
g_Keyword_CoreInitialize: str = "Initialize"
g_Keyword_CoreCamera: str = "Camera"
g_Keyword_CoreShutter: str = "Shutter"
g_Keyword_CoreXYStage: str = "XYStage"
g_Keyword_CoreFocus: str = "Focus"
g_Keyword_CoreAutoFocus: str = "AutoFocus"
g_Keyword_CoreAutoShutter: str = "AutoShutter"
g_Keyword_CoreChannelGroup: str = "ChannelGroup"
g_Keyword_CoreImageProcessor: str = "ImageProcessor"
g_Keyword_CoreSLM: str = "SLM"
g_Keyword_CoreGalvo: str = "Galvo"
g_Keyword_CorePressurePump: str = "PressurePump"
g_Keyword_CoreVolumetricPump: str = "VolumetricPump"
g_Keyword_CoreTimeoutMs: str = "TimeoutMs"
g_Keyword_Channel: str = "Channel"
g_Keyword_Version: str = "Version"
g_Keyword_ColorMode: str = "ColorMode"
g_Keyword_Transpose_SwapXY: str = "TransposeXY"
g_Keyword_Transpose_MirrorX: str = "TransposeMirrorX"
g_Keyword_Transpose_MirrorY: str = "TransposeMirrorY"
g_Keyword_Transpose_Correction: str = "TransposeCorrection"
g_Keyword_Closed_Position: str = "ClosedPosition"
g_Keyword_HubID: str = "HubID"
g_Keyword_PixelType_GRAY8: str = "GRAY8"
g_Keyword_PixelType_GRAY16: str = "GRAY16"
g_Keyword_PixelType_GRAY32: str = "GRAY32"
g_Keyword_PixelType_RGB32: str = "RGB32"
g_Keyword_PixelType_RGB64: str = "RGB64"
g_Keyword_PixelType_Unknown: str = "Unknown"
g_Keyword_Current_Volume: str = "Volume_uL"
g_Keyword_Min_Volume: str = "Min_Volume_uL"
g_Keyword_Max_Volume: str = "Max_Volume_uL"
g_Keyword_Flowrate: str = "Flowrate_uL_per_sec"
g_Keyword_Pressure_Imposed: str = "Pressure Imposed"
g_Keyword_Pressure_Measured: str = "Pressure Measured"
g_Keyword_Metadata_CameraLabel: str = "Camera"
g_Keyword_Metadata_Exposure: str = "Exposure-ms"
g_Keyword_Metadata_Height: str = "Height"
g_Keyword_Metadata_ImageNumber: str = "ImageNumber"
g_Keyword_Metadata_ROI_X: str = "ROI-X-start"
g_Keyword_Metadata_ROI_Y: str = "ROI-Y-start"
g_Keyword_Metadata_Score: str = "Score"
g_Keyword_Metadata_TimeInCore: str = "TimeReceivedByCore"
g_Keyword_Metadata_Width: str = "Width"
g_FieldDelimiters: str = ","
g_CFGCommand_Device: str = "Device"
g_CFGCommand_Label: str = "Label"
g_CFGCommand_Property: str = "Property"
g_CFGCommand_Configuration: str = "Config"
g_CFGCommand_ConfigGroup: str = "ConfigGroup"
g_CFGCommand_Equipment: str = "Equipment"
g_CFGCommand_Delay: str = "Delay"
g_CFGCommand_ImageSynchro: str = "ImageSynchro"
g_CFGCommand_ConfigPixelSize: str = "ConfigPixelSize"
g_CFGCommand_PixelSize_um: str = "PixelSize_um"
g_CFGCommand_PixelSizeAffine: str = "PixelSizeAffine"
g_CFGCommand_PixelSizedxdz: str = "PixelSizeAngle_dxdz"
g_CFGCommand_PixelSizedydz: str = "PixelSizeAngle_dydz"
g_CFGCommand_PixelSizeOptimalZUm: str = "PixelSizeOptimalZ_Um"
g_CFGCommand_ParentID: str = "Parent"
g_CFGCommand_FocusDirection: str = "FocusDirection"
g_CFGGroup_System: str = "System"
g_CFGGroup_System_Startup: str = "Startup"
g_CFGGroup_System_Shutdown: str = "Shutdown"
g_CFGGroup_PixelSizeUm: str = "PixelSize_um"

class DeviceType(enum.IntEnum):
    UnknownType = 0
    AnyType = 1
    CameraDevice = 2
    ShutterDevice = 3
    StateDevice = 4
    StageDevice = 5
    XYStageDevice = 6
    SerialDevice = 7
    GenericDevice = 8
    AutoFocusDevice = 9
    CoreDevice = 10
    ImageProcessorDevice = 11
    SignalIODevice = 12
    MagnifierDevice = 13
    SLMDevice = 14
    HubDevice = 15
    GalvoDevice = 16
    PressurePumpDevice = 17
    VolumetricPumpDevice = 18

UnknownType: int = 0
AnyType: int = 1
CameraDevice: int = 2
ShutterDevice: int = 3
StateDevice: int = 4
StageDevice: int = 5
XYStageDevice: int = 6
SerialDevice: int = 7
GenericDevice: int = 8
AutoFocusDevice: int = 9
CoreDevice: int = 10
ImageProcessorDevice: int = 11
SignalIODevice: int = 12
MagnifierDevice: int = 13
SLMDevice: int = 14
HubDevice: int = 15
GalvoDevice: int = 16
PressurePumpDevice: int = 17
VolumetricPumpDevice: int = 18

class PropertyType(enum.IntEnum):
    Undef = 0
    String = 1
    Float = 2
    Integer = 3

Undef: int = 0
String: int = 1
Float: int = 2
Integer: int = 3

class ActionType(enum.IntEnum):
    NoAction = 0
    BeforeGet = 1
    AfterSet = 2
    IsSequenceable = 3
    AfterLoadSequence = 4
    StartSequence = 5
    StopSequence = 6

NoAction: int = 0
BeforeGet: int = 1
AfterSet: int = 2
IsSequenceable: int = 3
AfterLoadSequence: int = 4
StartSequence: int = 5
StopSequence: int = 6

class PortType(enum.IntEnum):
    InvalidPort = 0
    SerialPort = 1
    USBPort = 2
    HIDPort = 3

InvalidPort: int = 0
SerialPort: int = 1
USBPort: int = 2
HIDPort: int = 3

class FocusDirection(enum.IntEnum):
    FocusDirectionUnknown = 0
    FocusDirectionTowardSample = 1
    FocusDirectionAwayFromSample = 2

FocusDirectionUnknown: int = 0
FocusDirectionTowardSample: int = 1
FocusDirectionAwayFromSample: int = 2

class DeviceNotification(enum.IntEnum):
    Attention = 0
    Done = 1
    StatusChanged = 2

Attention: int = 0
Done: int = 1
StatusChanged: int = 2

class DeviceDetectionStatus(enum.IntEnum):
    Unimplemented = -2
    Misconfigured = -1
    CanNotCommunicate = 0
    CanCommunicate = 1

Unimplemented: int = -2
Misconfigured: int = -1
CanNotCommunicate: int = 0
CanCommunicate: int = 1

class DeviceInitializationState(enum.IntEnum):
    Uninitialized = 0
    InitializedSuccessfully = 1
    InitializationFailed = 2

Uninitialized: int = 0
InitializedSuccessfully: int = 1
InitializationFailed: int = 2

class Configuration:
    """
    Encapsulation of  configuration information.

    A configuration is a collection of device property settings.
    """
    def __init__(self) -> None: ...
    def addSetting(self, setting: PropertySetting) -> None: ...
    def deleteSetting(self, device: str, property: str) -> None: ...
    def isPropertyIncluded(self, device: str, property: str) -> bool: ...
    def isConfigurationIncluded(self, cfg: Configuration) -> bool: ...
    def isSettingIncluded(self, setting: PropertySetting) -> bool: ...
    @overload
    def getSetting(self, index: int) -> PropertySetting: ...
    @overload
    def getSetting(self, device: str, property: str) -> PropertySetting: ...
    def size(self) -> int: ...
    def getVerbose(self) -> str: ...

class PropertySetting:
    @overload
    def __init__(
        self, deviceLabel: str, prop: str, value: str, readOnly: bool = False
    ) -> None:
        """Constructor specifying the entire contents"""
    @overload
    def __init__(self) -> None:
        """Default constructor"""
    def getDeviceLabel(self) -> str:
        """Returns the device label"""
    def getPropertyName(self) -> str:
        """Returns the property name"""
    def getReadOnly(self) -> bool:
        """Returns the read-only status"""
    def getPropertyValue(self) -> str:
        """Returns the property value"""
    def getKey(self) -> str:
        """Returns the unique key"""
    def getVerbose(self) -> str:
        """Returns a verbose description"""
    def isEqualTo(self, other: PropertySetting) -> bool:
        """Checks if this property setting is equal to another"""
    @staticmethod
    def generateKey(device: str, prop: str) -> str:
        """Generates a unique key based on device and property"""

class Metadata:
    @overload
    def __init__(self) -> None:
        """Empty constructor"""
    @overload
    def __init__(self, arg: Metadata) -> None:
        """Copy constructor"""
    def Clear(self) -> None:
        """Clears all tags"""
    def GetKeys(self) -> list[str]:
        """Returns all tag keys"""
    def HasTag(self, key: str) -> bool:
        """Checks if a tag exists for the given key"""
    def GetSingleTag(self, key: str) -> MetadataSingleTag:
        """Gets a single tag by key"""
    def GetArrayTag(self, key: str) -> MetadataArrayTag:
        """Gets an array tag by key"""
    def SetTag(self, tag: MetadataTag) -> None:
        """Sets a tag"""
    def RemoveTag(self, key: str) -> None:
        """Removes a tag by key"""
    def Merge(self, newTags: Metadata) -> None:
        """Merges new tags into the metadata"""
    def Serialize(self) -> str:
        """Serializes the metadata"""
    def Restore(self, stream: str) -> bool:
        """Restores metadata from a serialized string"""
    def Dump(self) -> str:
        """Dumps metadata in human-readable format"""
    def PutTag(self, key: str, deviceLabel: str, value: str) -> None:
        """Adds a MetadataSingleTag"""
    def PutImageTag(self, key: str, value: str) -> None:
        """Adds an image tag"""
    def __getitem__(self, arg: str, /) -> str: ...
    def __setitem__(self, arg0: str, arg1: str, /) -> None: ...
    def __delitem__(self, arg: str, /) -> None: ...

class MetadataTag:
    def GetDevice(self) -> str:
        """Returns the device label"""
    def GetName(self) -> str:
        """Returns the name of the tag"""
    def GetQualifiedName(self) -> str:
        """Returns the qualified name"""
    def IsReadOnly(self) -> bool:
        """Checks if the tag is read-only"""
    def SetDevice(self, device: str) -> None:
        """Sets the device label"""
    def SetName(self, name: str) -> None:
        """Sets the name of the tag"""
    def SetReadOnly(self, readOnly: bool) -> None:
        """Sets the read-only status"""
    def ToSingleTag(self) -> MetadataSingleTag:
        """Converts to MetadataSingleTag if applicable"""
    def ToArrayTag(self) -> MetadataArrayTag:
        """Converts to MetadataArrayTag if applicable"""
    def Clone(self) -> MetadataTag:
        """Creates a clone of the MetadataTag"""
    def Serialize(self) -> str:
        """Serializes the MetadataTag to a string"""
    def Restore(self, stream: str) -> bool:
        """Restores from a serialized string"""

class MetadataSingleTag(MetadataTag):
    @overload
    def __init__(self) -> None:
        """Default constructor"""
    @overload
    def __init__(self, name: str, device: str, readOnly: bool) -> None:
        """Parameterized constructor"""
    def GetValue(self) -> str:
        """Returns the value"""
    def SetValue(self, val: str) -> None:
        """Sets the value"""
    def ToSingleTag(self) -> MetadataSingleTag:
        """Returns this object as MetadataSingleTag"""
    def Clone(self) -> MetadataTag:
        """Clones this tag"""
    def Serialize(self) -> str:
        """Serializes this tag to a string"""
    def Restore(self, stream: str) -> bool:
        """Restores from a serialized string"""

class MetadataArrayTag(MetadataTag):
    @overload
    def __init__(self) -> None:
        """Default constructor"""
    @overload
    def __init__(self, name: str, device: str, readOnly: bool) -> None:
        """Parameterized constructor"""
    def ToArrayTag(self) -> MetadataArrayTag:
        """Returns this object as MetadataArrayTag"""
    def AddValue(self, val: str) -> None:
        """Adds a value to the array"""
    def SetValue(self, val: str, idx: int) -> None:
        """Sets a value at a specific index"""
    def GetValue(self, idx: int) -> str:
        """Gets a value at a specific index"""
    def GetSize(self) -> int:
        """Returns the size of the array"""
    def Clone(self) -> MetadataTag:
        """Clones this tag"""
    def Serialize(self) -> str:
        """Serializes this tag to a string"""
    def Restore(self, stream: str) -> bool:
        """Restores from a serialized string"""

class MMEventCallback:
    """
    Interface for receiving events from MMCore.

    Use by passing an instance to [`CMMCore.registerCallback`][pymmcore_nano.CMMCore.registerCallback].
    """
    def __init__(self) -> None: ...
    def onPropertiesChanged(self) -> None:
        """Called when properties are changed"""
    def onPropertyChanged(self, name: str, propName: str, propValue: str) -> None:
        """Called when a specific property is changed"""
    def onChannelGroupChanged(self, newChannelGroupName: str) -> None:
        """Called when the channel group changes"""
    def onConfigGroupChanged(self, groupName: str, newConfigName: str) -> None:
        """Called when a configuration group changes"""
    def onSystemConfigurationLoaded(self) -> None:
        """Called when the system configuration is loaded"""
    def onPixelSizeChanged(self, newPixelSizeUm: float) -> None:
        """Called when the pixel size changes"""
    def onPixelSizeAffineChanged(
        self, v0: float, v1: float, v2: float, v3: float, v4: float, v5: float
    ) -> None:
        """Called when the pixel size affine transformation changes"""
    def onSLMExposureChanged(self, name: str, newExposure: float) -> None: ...
    def onExposureChanged(self, name: str, newExposure: float) -> None: ...
    def onStagePositionChanged(self, name: str, pos: float) -> None: ...
    def onXYStagePositionChanged(self, name: str, xpos: float, ypos: float) -> None: ...
    def onImageSnapped(self, cameraLabel: str) -> None:
        """Called when an image is snapped"""
    def onSequenceAcquisitionStarted(self, cameraLabel: str) -> None:
        """Called when sequence acquisition starts"""
    def onSequenceAcquisitionStopped(self, cameraLabel: str) -> None:
        """Called when sequence acquisition stops"""

class CMMError(RuntimeError):
    pass

class MetadataKeyError(KeyError):
    pass

class MetadataIndexError(IndexError):
    pass

class CMMCore:
    """
    The main MMCore object.

    Manages multiple device adapters. Provides a device-independent interface for hardware control.
    Additionally, provides some facilities (such as configuration groups) for application
    programming.
    """
    def __init__(self) -> None: ...
    def loadSystemConfiguration(self, fileName: object) -> None:
        """Loads a system configuration from a file."""
    def saveSystemConfiguration(self, fileName: str) -> None:
        """
        Saves the current system configuration to a text file of the MM specific format. The configuration file records only the information essential to the hardware setup: devices, labels, pre-initialization properties, and configurations. The file format is the same as for the system state.
        """
    @staticmethod
    def enableFeature(name: str, enable: bool) -> None: ...
    @staticmethod
    def isFeatureEnabled(name: str) -> bool: ...
    @staticmethod
    def getMMCoreVersionMajor() -> int: ...
    @staticmethod
    def getMMCoreVersionMinor() -> int: ...
    @staticmethod
    def getMMCoreVersionPatch() -> int: ...
    @staticmethod
    def getMMDeviceModuleInterfaceVersion() -> int: ...
    @staticmethod
    def getMMDeviceDeviceInterfaceVersion() -> int: ...
    def loadDevice(self, label: str, moduleName: str, deviceName: str) -> None:
        """Loads a device from the plugin library."""
    def unloadDevice(self, label: str) -> None:
        """Unloads the device from the core and adjusts all configuration data."""
    def unloadAllDevices(self) -> None: ...
    def initializeAllDevices(self) -> None:
        """
        Calls Initialize() method for each loaded device. Parallel implemnetation should be faster
        """
    def initializeDevice(self, label: str) -> None: ...
    def getDeviceInitializationState(self, label: str) -> DeviceInitializationState:
        """Queries the initialization state of the given device."""
    def reset(self) -> None:
        """Unloads all devices from the core, clears all configuration data."""
    def unloadLibrary(self, moduleName: str) -> None:
        """Forcefully unload a library. Experimental. Don't use."""
    def updateCoreProperties(self) -> None:
        """
        Updates CoreProperties (currently all Core properties are devices types) with the loaded hardware. After this call, each of the Core-Device properties will be populated with the currently loaded devices of that type
        """
    def getCoreErrorText(self, code: int) -> str:
        """Returns a pre-defined error test with the given error code"""
    def getVersionInfo(self) -> str: ...
    def getAPIVersionInfo(self) -> str:
        """Returns the module and device interface versions."""
    def getSystemState(self) -> Configuration:
        """
        Returns the entire system state, i.e. the collection of all property values from all devices.
        """
    def setSystemState(self, conf: Configuration) -> None:
        """
        Sets all properties contained in the Configuration object. The procedure will attempt to set each property it encounters, but won't stop if any of the properties fail or if the requested device is not present. It will just quietly continue.
        """
    def getConfigState(self, group: str, config: str) -> Configuration:
        """
        Returns a partial state of the system, only for devices included in the specified configuration.
        """
    def getConfigGroupState(self, group: str) -> Configuration: ...
    def saveSystemState(self, fileName: str) -> None:
        """
        Saves the current system state to a text file of the MM specific format. The file records only read-write properties. The file format is directly readable by the complementary loadSystemState() command.
        """
    def loadSystemState(self, fileName: str) -> None:
        """
        Loads the system configuration from the text file conforming to the MM specific format. The configuration contains a list of commands to build the desired system state from read-write properties.
        """
    def registerCallback(self, cb: MMEventCallback | None) -> None:
        """
        Register a callback (listener class).

        MMCore will send notifications on internal events using this interface
        """
    def setPrimaryLogFile(self, filename: object, truncate: bool = False) -> None: ...
    def getPrimaryLogFile(self) -> str:
        """Return the name of the primary Core log file."""
    @overload
    def logMessage(self, msg: str) -> None: ...
    @overload
    def logMessage(self, msg: str, debugOnly: bool) -> None: ...
    def enableDebugLog(self, enable: bool) -> None:
        """Enable or disable logging of debug messages."""
    def debugLogEnabled(self) -> bool:
        """Indicates if logging of debug messages is enabled"""
    def enableStderrLog(self, enable: bool) -> None:
        """Enables or disables log message display on the standard console."""
    def stderrLogEnabled(self) -> bool:
        """Indicates whether logging output goes to stdErr"""
    def startSecondaryLogFile(
        self,
        filename: object,
        enableDebug: bool,
        truncate: bool = True,
        synchronous: bool = False,
    ) -> int: ...
    def stopSecondaryLogFile(self, handle: int) -> None:
        """Stop capturing logging output into an additional file."""
    def getDeviceAdapterSearchPaths(self) -> list[str]:
        """Return the current device adapter search paths."""
    def setDeviceAdapterSearchPaths(self, paths: Sequence[str]) -> None:
        """Set the device adapter search paths."""
    def getDeviceAdapterNames(self) -> list[str]:
        """Return the names of discoverable device adapters."""
    def getAvailableDevices(self, library: str) -> list[str]:
        """Get available devices from the specified device library."""
    def getAvailableDeviceDescriptions(self, library: str) -> list[str]:
        """Get descriptions for available devices from the specified library."""
    def getAvailableDeviceTypes(self, library: str) -> list[int]:
        """Get type information for available devices from the specified library."""
    def getLoadedDevices(self) -> list[str]:
        """Returns an array of labels for currently loaded devices."""
    def getLoadedDevicesOfType(self, devType: DeviceType) -> list[str]:
        """
        Returns an array of labels for currently loaded devices of specific type.
        """
    def getDeviceType(self, label: str) -> DeviceType: ...
    def getDeviceLibrary(self, label: str) -> str:
        """Returns device library (aka module, device adapter) name."""
    def getDeviceName(self, label: str) -> str: ...
    def getDeviceDescription(self, label: str) -> str:
        """
        Returns description text for a given device label. "Description" is determined by the library and is immutable.
        """
    def getDevicePropertyNames(self, label: str) -> list[str]:
        """Returns all property names supported by the device."""
    def hasProperty(self, label: str, propName: str) -> bool:
        """
        Checks if device has a property with a specified name. The exception will be thrown in case device label is not defined.
        """
    def getProperty(self, label: str, propName: str) -> str:
        """Returns the property value for the specified device."""
    @overload
    def setProperty(self, label: str, propName: str, propValue: str) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: bool) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: int) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: float) -> None: ...
    def getAllowedPropertyValues(self, label: str, propName: str) -> list[str]:
        """
        Returns all valid values for the specified property. If the array is empty it means that there are no restrictions for values. However, even if all values are allowed it is not guaranteed that all of them will be actually accepted by the device at run time.
        """
    def isPropertyReadOnly(self, label: str, propName: str) -> bool:
        """Tells us whether the property can be modified."""
    def isPropertyPreInit(self, label: str, propName: str) -> bool:
        """Tells us whether the property must be defined prior to initialization."""
    def isPropertySequenceable(self, label: str, propName: str) -> bool:
        """Queries device if the specified property can be used in a sequence"""
    def hasPropertyLimits(self, label: str, propName: str) -> bool:
        """Queries device if the specific property has limits."""
    def getPropertyLowerLimit(self, label: str, propName: str) -> float:
        """
        Returns the property lower limit value, if the property has limits - 0 otherwise.
        """
    def getPropertyUpperLimit(self, label: str, propName: str) -> float:
        """
        Returns the property upper limit value, if the property has limits - 0 otherwise.
        """
    def getPropertyType(self, label: str, propName: str) -> PropertyType:
        """Returns the intrinsic property type."""
    def startPropertySequence(self, label: str, propName: str) -> None:
        """
        Starts an ongoing sequence of triggered events in a property of a device This should only be called for device-properties that are sequenceable
        """
    def stopPropertySequence(self, label: str, propName: str) -> None:
        """
        Stops an ongoing sequence of triggered events in a property of a device This should only be called for device-properties that are sequenceable
        """
    def getPropertySequenceMaxLength(self, label: str, propName: str) -> int:
        """
        Queries device property for the maximum number of events that can be put in a sequence
        """
    def loadPropertySequence(
        self, label: str, propName: str, eventSequence: Sequence[str]
    ) -> None:
        """
        Transfer a sequence of events/states/whatever to the device This should only be called for device-properties that are sequenceable
        """
    def deviceBusy(self, label: str) -> bool:
        """Checks the busy status of the specific device."""
    def waitForDevice(self, label: str) -> None: ...
    def waitForConfig(self, group: str, configName: str) -> None:
        """Blocks until all devices included in the configuration become ready."""
    def systemBusy(self) -> bool:
        """
        Checks the busy status of the entire system. The system will report busy if any of the devices is busy.
        """
    def waitForSystem(self) -> None:
        """Blocks until all devices in the system become ready (not-busy)."""
    def deviceTypeBusy(self, devType: DeviceType) -> bool:
        """
        Checks the busy status for all devices of the specific type. The system will report busy if any of the devices of the specified type are busy.
        """
    def waitForDeviceType(self, devType: DeviceType) -> None:
        """Blocks until all devices of the specific type become ready (not-busy)."""
    def getDeviceDelayMs(self, label: str) -> float:
        """
        Reports action delay in milliseconds for the specific device. The delay is used in the synchronization process to ensure that the action is performed, without polling. Value of "0" means that action is either blocking or that polling of device status is required. Some devices ignore this setting.
        """
    def setDeviceDelayMs(self, label: str, delayMs: float) -> None:
        """
        Overrides the built-in value for the action delay. Some devices ignore this setting.
        """
    def usesDeviceDelay(self, label: str) -> bool:
        """Signals if the device will use the delay setting or not."""
    def setTimeoutMs(self, timeoutMs: int) -> None: ...
    def getTimeoutMs(self) -> int: ...
    def sleep(self, intervalMs: float) -> None:
        """Waits (blocks the calling thread) for specified time in milliseconds."""
    def getCameraDevice(self) -> str:
        """Returns the label of the currently selected camera device."""
    def getShutterDevice(self) -> str:
        """Returns the label of the currently selected shutter device."""
    def getFocusDevice(self) -> str:
        """Returns the label of the currently selected focus device."""
    def getXYStageDevice(self) -> str:
        """Returns the label of the currently selected XYStage device."""
    def getAutoFocusDevice(self) -> str:
        """Returns the label of the currently selected auto-focus device."""
    def getImageProcessorDevice(self) -> str:
        """Returns the label of the currently selected image processor device."""
    def getSLMDevice(self) -> str:
        """Returns the label of the currently selected SLM device."""
    def getGalvoDevice(self) -> str:
        """Returns the label of the currently selected Galvo device."""
    def getChannelGroup(self) -> str:
        """Returns the group determining the channel selection."""
    def setCameraDevice(self, cameraLabel: str) -> None:
        """Sets the current camera device."""
    def setShutterDevice(self, shutterLabel: str) -> None:
        """Sets the current shutter device."""
    def setFocusDevice(self, focusLabel: str) -> None:
        """Sets the current focus device."""
    def setXYStageDevice(self, xyStageLabel: str) -> None:
        """Sets the current XY device."""
    def setAutoFocusDevice(self, focusLabel: str) -> None:
        """Sets the current auto-focus device."""
    def setImageProcessorDevice(self, procLabel: str) -> None:
        """Sets the current image processor device."""
    def setSLMDevice(self, slmLabel: str) -> None:
        """Sets the current slm device."""
    def setGalvoDevice(self, galvoLabel: str) -> None:
        """Sets the current galvo device."""
    def setChannelGroup(self, channelGroup: str) -> None:
        """Specifies the group determining the channel selection."""
    def getSystemStateCache(self) -> Configuration:
        """
        Returns the entire system state, i.e. the collection of all property values from all devices. This method will return cached values instead of querying each device
        """
    def updateSystemStateCache(self) -> None:
        """Updates the state of the entire hardware."""
    def getPropertyFromCache(self, deviceLabel: str, propName: str) -> str:
        """Returns the cached property value for the specified device."""
    def getCurrentConfigFromCache(self, groupName: str) -> str:
        """
        Returns the configuration for a given group based on the data in the cache. An empty string is a valid return value, since the system state will not always correspond to any of the defined configurations. Also, in general it is possible that the system state fits multiple configurations. This method will return only the first matching configuration, if any.
        """
    def getConfigGroupStateFromCache(self, group: str) -> Configuration:
        """
        Returns the partial state of the system cache, only for the devices included in the specified group. It will create a union of all devices referenced in a group.
        """
    @overload
    def defineConfig(self, groupName: str, configName: str) -> None: ...
    @overload
    def defineConfig(
        self,
        groupName: str,
        configName: str,
        deviceLabel: str,
        propName: str,
        value: str,
    ) -> None: ...
    def defineConfigGroup(self, groupName: str) -> None:
        """Creates an empty configuration group."""
    def deleteConfigGroup(self, groupName: str) -> None:
        """Deletes an entire configuration group."""
    def renameConfigGroup(self, oldGroupName: str, newGroupName: str) -> None:
        """Renames a configuration group."""
    def isGroupDefined(self, groupName: str) -> bool:
        """Checks if the group already exists."""
    def isConfigDefined(self, groupName: str, configName: str) -> bool:
        """Checks if the configuration already exists within a group."""
    def setConfig(self, groupName: str, configName: str) -> None:
        """
        Applies a configuration to a group. The command will fail if the configuration was not previously defined.
        """
    @overload
    def deleteConfig(self, groupName: str, configName: str) -> None: ...
    @overload
    def deleteConfig(
        self, groupName: str, configName: str, deviceLabel: str, propName: str
    ) -> None: ...
    def renameConfig(
        self, groupName: str, oldConfigName: str, newConfigName: str
    ) -> None:
        """
        Renames a configuration within a specified group. The command will fail if the configuration was not previously defined.
        """
    def getAvailableConfigGroups(self) -> list[str]:
        """Returns the names of all defined configuration groups"""
    def getAvailableConfigs(self, configGroup: str) -> list[str]:
        """Returns all defined configuration names in a given group"""
    def getCurrentConfig(self, groupName: str) -> str:
        """
        Returns the current configuration for a given group. An empty string is a valid return value, since the system state will not always correspond to any of the defined configurations. Also, in general it is possible that the system state fits multiple configurations. This method will return only the first matching configuration, if any.
        """
    def getConfigData(self, configGroup: str, configName: str) -> Configuration:
        """Returns the configuration object for a given group and name."""
    @overload
    def getCurrentPixelSizeConfig(self) -> str: ...
    @overload
    def getCurrentPixelSizeConfig(self, cached: bool) -> str: ...
    @overload
    def getPixelSizeUm(self) -> float: ...
    @overload
    def getPixelSizeUm(self, cached: bool) -> float: ...
    def getPixelSizeUmByID(self, resolutionID: str) -> float:
        """Returns the pixel size in um for the requested pixel size group"""
    @overload
    def getPixelSizeAffine(self) -> list[float]: ...
    @overload
    def getPixelSizeAffine(self, cached: bool) -> list[float]: ...
    def getPixelSizeAffineByID(self, resolutionID: str) -> list[float]:
        """
        Returns the Affine Transform to related camera pixels with stage movement for the requested pixel size group The raw affine transform without correction for binning and magnification will be returned.
        """
    @overload
    def getPixelSizedxdz(self) -> float: ...
    @overload
    def getPixelSizedxdz(self, cached: bool) -> float: ...
    @overload
    def getPixelSizedxdz(self, resolutionID: str) -> float: ...
    @overload
    def getPixelSizedydz(self) -> float: ...
    @overload
    def getPixelSizedydz(self, cached: bool) -> float: ...
    @overload
    def getPixelSizedydz(self, resolutionID: str) -> float: ...
    @overload
    def getPixelSizeOptimalZUm(self) -> float: ...
    @overload
    def getPixelSizeOptimalZUm(self, cached: bool) -> float: ...
    @overload
    def getPixelSizeOptimalZUm(self, resolutionID: str) -> float: ...
    def setPixelSizedxdz(self, resolutionID: str, dXdZ: float) -> None:
        """
        Sets the angle between the camera's x axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in x caused by a translation in z, i.e. dx / dz).
         This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration).
         See: https://github.com/micro-manager/micro-manager/issues/1984
        """
    def setPixelSizedydz(self, resolutionID: str, dYdZ: float) -> None:
        """
        Sets the angle between the camera's y axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in y caused by a translation in z, i.e. dy / dz).
         This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration).
         See: https://github.com/micro-manager/micro-manager/issues/1984
        """
    def setPixelSizeOptimalZUm(self, resolutionID: str, optimalZ: float) -> None:
        """
        Sets the opimal Z stepSize (in microns). There is no magic here, this number is provided by the person configuring the microscope, to be used by the person using the microscope.
        """
    def getMagnificationFactor(self) -> float:
        """
        Returns the product of all Magnifiers in the system or 1.0 when none is found This is used internally by GetPixelSizeUm
        """
    def setPixelSizeUm(self, resolutionID: str, pixSize: float) -> None:
        """
        Sets pixel size in microns for the specified resolution sensing configuration preset.
        """
    def setPixelSizeAffine(self, resolutionID: str, affine: Sequence[float]) -> None:
        """
        Sets the raw affine transform for the specific pixel size configuration The affine transform consists of the first two rows of a 3x3 matrix, the third row is alsways assumed to be 0.0 0.0 1.0. The transform should be valid for binning 1 and no magnification device (as given by the getMagnification() function). Order: row[0]col[0] row[0]c[1] row[0]c[2] row[1]c[0] row[1]c[1] row[1]c[2] The given vector has to have 6 doubles, or bad stuff will happen
        """
    @overload
    def definePixelSizeConfig(
        self, resolutionID: str, deviceLabel: str, propName: str, value: str
    ) -> None: ...
    @overload
    def definePixelSizeConfig(self, resolutionID: str) -> None: ...
    def getAvailablePixelSizeConfigs(self) -> list[str]:
        """Returns all defined resolution preset names"""
    def isPixelSizeConfigDefined(self, resolutionID: str) -> bool:
        """Checks if the Pixel Size Resolution already exists"""
    def setPixelSizeConfig(self, resolutionID: str) -> None:
        """
        Applies a Pixel Size Configuration. The command will fail if the configuration was not previously defined.
        """
    def renamePixelSizeConfig(self, oldConfigName: str, newConfigName: str) -> None:
        """
        Renames a pixel size configuration. The command will fail if the configuration was not previously defined.
        """
    def deletePixelSizeConfig(self, configName: str) -> None:
        """
        Deletes a pixel size configuration. The command will fail if the configuration was not previously defined.
        """
    def getPixelSizeConfigData(self, configName: str) -> Configuration:
        """Returns the configuration object for a give pixel size preset."""
    @overload
    def setROI(self, x: int, y: int, xSize: int, ySize: int) -> None: ...
    @overload
    def setROI(self, label: str, x: int, y: int, xSize: int, ySize: int) -> None: ...
    @overload
    def getROI(self) -> tuple[int, int, int, int]: ...
    @overload
    def getROI(self, label: str) -> tuple[int, int, int, int]: ...
    def clearROI(self) -> None:
        """Set the region of interest of the current camera to the full frame."""
    def isMultiROISupported(self) -> bool:
        """Queries the camera to determine if it supports multiple ROIs."""
    def isMultiROIEnabled(self) -> bool:
        """Queries the camera to determine if multiple ROIs are currently set."""
    def setMultiROI(
        self,
        xs: Sequence[int],
        ys: Sequence[int],
        widths: Sequence[int],
        heights: Sequence[int],
    ) -> None:
        """
        Set multiple ROIs for the current camera device. Will fail if the camera does not support multiple ROIs, any widths or heights are non-positive, or if the vectors do not all have the same length.
        """
    def getMultiROI(self) -> tuple[list[int], list[int], list[int], list[int]]: ...
    @overload
    def setExposure(self, exp: float) -> None: ...
    @overload
    def setExposure(self, cameraLabel: str, dExp: float) -> None: ...
    @overload
    def getExposure(self) -> float: ...
    @overload
    def getExposure(self, label: str) -> float: ...
    def snapImage(self) -> None:
        """
        Acquires a single image with current settings. Snap is not allowed while the acquisition thread is run
        """
    @overload
    def getImage(self) -> Annotated[ArrayLike, {"writable": False}]: ...
    @overload
    def getImage(self, arg: int, /) -> Annotated[ArrayLike, {"writable": False}]: ...
    def getImageWidth(self) -> int:
        """Horizontal dimension of the image buffer in pixels."""
    def getImageHeight(self) -> int:
        """Vertical dimension of the image buffer in pixels."""
    def getBytesPerPixel(self) -> int:
        """
        How many bytes for each pixel. This value does not necessarily reflect the capabilities of the particular camera A/D converter.
        """
    def getImageBitDepth(self) -> int:
        """
        How many bits of dynamic range are to be expected from the camera. This value should be used only as a guideline - it does not guarantee that image buffer will contain only values from the returned dynamic range.
        """
    def getNumberOfComponents(self) -> int:
        """
        Returns the number of components the default camera is returning. For example color camera will return 4 components (RGBA) on each snap.
        """
    def getNumberOfCameraChannels(self) -> int:
        """
        Returns the number of simultaneous channels the default camera is returning.
        """
    def getCameraChannelName(self, channelNr: int) -> str:
        """
        Returns the name of the requested channel as known by the default camera
        """
    def getImageBufferSize(self) -> int:
        """Returns the size of the internal image buffer."""
    def setAutoShutter(self, state: bool) -> None:
        """
        If this option is enabled Shutter automatically opens and closes when the image is acquired.
        """
    def getAutoShutter(self) -> bool:
        """Returns the current setting of the auto-shutter option."""
    @overload
    def setShutterOpen(self, state: bool) -> None: ...
    @overload
    def setShutterOpen(self, shutterLabel: str, state: bool) -> None: ...
    @overload
    def getShutterOpen(self) -> bool: ...
    @overload
    def getShutterOpen(self, shutterLabel: str) -> bool: ...
    @overload
    def startSequenceAcquisition(
        self, numImages: int, intervalMs: float, stopOnOverflow: bool
    ) -> None: ...
    @overload
    def startSequenceAcquisition(
        self, cameraLabel: str, numImages: int, intervalMs: float, stopOnOverflow: bool
    ) -> None: ...
    def prepareSequenceAcquisition(self, cameraLabel: str) -> None:
        """
        Prepare the camera for the sequence acquisition to save the time in the StartSequenceAcqusition() call which is supposed to come next.
        """
    def startContinuousSequenceAcquisition(self, intervalMs: float) -> None:
        """
        Starts the continuous camera sequence acquisition. This command does not block the calling thread for the duration of the acquisition.
        """
    @overload
    def stopSequenceAcquisition(self) -> None: ...
    @overload
    def stopSequenceAcquisition(self, cameraLabel: str) -> None: ...
    @overload
    def isSequenceRunning(self) -> bool: ...
    @overload
    def isSequenceRunning(self, cameraLabel: str) -> bool: ...
    def getLastImage(self) -> Annotated[ArrayLike, {"writable": False}]: ...
    def popNextImage(self) -> Annotated[ArrayLike, {"writable": False}]: ...
    @overload
    def getLastImageMD(
        self,
    ) -> tuple[Annotated[ArrayLike, {"writable": False}], Metadata]:
        """
        Get the last image in the circular buffer, return as tuple of image and metadata
        """
    @overload
    def getLastImageMD(
        self, md: Metadata
    ) -> Annotated[ArrayLike, {"writable": False}]:
        """
        Get the last image in the circular buffer, store metadata in the provided object
        """
    @overload
    def getLastImageMD(
        self, channel: int, slice: int
    ) -> tuple[Annotated[ArrayLike, {"writable": False}], Metadata]:
        """
        Get the last image in the circular buffer for a specific channel and slice, returnas tuple of image and metadata
        """
    @overload
    def getLastImageMD(
        self, channel: int, slice: int, md: Metadata
    ) -> Annotated[ArrayLike, {"writable": False}]:
        """
        Get the last image in the circular buffer for a specific channel and slice, store metadata in the provided object
        """
    @overload
    def popNextImageMD(
        self,
    ) -> tuple[Annotated[ArrayLike, {"writable": False}], Metadata]:
        """
        Get the last image in the circular buffer, return as tuple of image and metadata
        """
    @overload
    def popNextImageMD(
        self, md: Metadata
    ) -> Annotated[ArrayLike, {"writable": False}]:
        """
        Get the last image in the circular buffer, store metadata in the provided object
        """
    @overload
    def popNextImageMD(
        self, channel: int, slice: int
    ) -> tuple[Annotated[ArrayLike, {"writable": False}], Metadata]:
        """
        Get the last image in the circular buffer for a specific channel and slice, returnas tuple of image and metadata
        """
    @overload
    def popNextImageMD(
        self, channel: int, slice: int, md: Metadata
    ) -> Annotated[ArrayLike, {"writable": False}]:
        """
        Get the last image in the circular buffer for a specific channel and slice, store metadata in the provided object
        """
    @overload
    def getNBeforeLastImageMD(
        self, n: int
    ) -> tuple[Annotated[ArrayLike, {"writable": False}], Metadata]:
        """
        Get the nth image before the last image in the circular buffer and return it as a tuple of image and metadata
        """
    @overload
    def getNBeforeLastImageMD(
        self, n: int, md: Metadata
    ) -> Annotated[ArrayLike, {"writable": False}]:
        """
        Get the nth image before the last image in the circular buffer and store the metadata in the provided object
        """
    def getRemainingImageCount(self) -> int:
        """Returns number ofimages available in the Circular Buffer"""
    def getBufferTotalCapacity(self) -> int:
        """Returns the total number of images that can be stored in the buffer"""
    def getBufferFreeCapacity(self) -> int:
        """
        Returns the number of images that can be added to the buffer without overflowing
        """
    def isBufferOverflowed(self) -> bool:
        """Indicates whether the circular buffer is overflowed"""
    def setCircularBufferMemoryFootprint(self, sizeMB: int) -> None:
        """Reserve memory for the circular buffer."""
    def getCircularBufferMemoryFootprint(self) -> int:
        """Returns the size of the Circular Buffer in MB"""
    def initializeCircularBuffer(self) -> None:
        """Initialize circular buffer based on the current camera settings."""
    def clearCircularBuffer(self) -> None:
        """Removes all images from the circular buffer."""
    def isExposureSequenceable(self, cameraLabel: str) -> bool:
        """Queries camera if exposure can be used in a sequence"""
    def startExposureSequence(self, cameraLabel: str) -> None:
        """
        Starts an ongoing sequence of triggered exposures in a camera This should only be called for cameras where exposure time is sequenceable
        """
    def stopExposureSequence(self, cameraLabel: str) -> None:
        """
        Stops an ongoing sequence of triggered exposures in a camera This should only be called for cameras where exposure time is sequenceable
        """
    def getExposureSequenceMaxLength(self, cameraLabel: str) -> int:
        """
        Gets the maximum length of a camera's exposure sequence. This should only be called for cameras where exposure time is sequenceable
        """
    def loadExposureSequence(
        self, cameraLabel: str, exposureSequence_ms: Sequence[float]
    ) -> None:
        """
        Transfer a sequence of exposure times to the camera. This should only be called for cameras where exposure time is sequenceable
        """
    def getLastFocusScore(self) -> float:
        """
        Returns the latest focus score from the focusing device. Use this value to estimate or record how reliable the focus is. The range of values is device dependent.
        """
    def getCurrentFocusScore(self) -> float:
        """
        Returns the focus score from the default focusing device measured at the current Z position. Use this value to create profiles or just to verify that the image is in focus. The absolute range of returned scores depends on the actual focusing device.
        """
    def enableContinuousFocus(self, enable: bool) -> None:
        """
        Enables or disables the operation of the continuous focusing hardware device.
        """
    def isContinuousFocusEnabled(self) -> bool:
        """Checks if the continuous focusing hardware device is ON or OFF."""
    def isContinuousFocusLocked(self) -> bool:
        """Returns the lock-in status of the continuous focusing device."""
    def isContinuousFocusDrive(self, stageLabel: str) -> bool:
        """
        Check if a stage has continuous focusing capability (positions can be set while continuous focus runs).
        """
    def fullFocus(self) -> None:
        """Performs focus acquisition and lock for the one-shot focusing device."""
    def incrementalFocus(self) -> None:
        """Performs incremental focus for the one-shot focusing device."""
    def setAutoFocusOffset(self, offset: float) -> None:
        """Applies offset the one-shot focusing device."""
    def getAutoFocusOffset(self) -> float:
        """Measures offset for the one-shot focusing device."""
    def setState(self, stateDeviceLabel: str, state: int) -> None:
        """
        Sets the state (position) on the specific device. The command will fail if the device does not support states.
        """
    def getState(self, stateDeviceLabel: str) -> int:
        """
        Returns the current state (position) on the specific device. The command will fail if the device does not support states.
        """
    def getNumberOfStates(self, stateDeviceLabel: str) -> int:
        """Returns the total number of available positions (states)."""
    def setStateLabel(self, stateDeviceLabel: str, stateLabel: str) -> None:
        """Sets device state using the previously assigned label (string)."""
    def getStateLabel(self, stateDeviceLabel: str) -> str:
        """Returns the current state as the label (string)."""
    def defineStateLabel(
        self, stateDeviceLabel: str, state: int, stateLabel: str
    ) -> None:
        """Defines a label for the specific state/"""
    def getStateLabels(self, stateDeviceLabel: str) -> list[str]:
        """Return labels for all states"""
    def getStateFromLabel(self, stateDeviceLabel: str, stateLabel: str) -> int:
        """Obtain the state for a given label."""
    @overload
    def setPosition(self, stageLabel: str, position: float) -> None: ...
    @overload
    def setPosition(self, position: float) -> None: ...
    @overload
    def getPosition(self, stageLabel: str) -> float: ...
    @overload
    def getPosition(self) -> float: ...
    @overload
    def setRelativePosition(self, stageLabel: str, d: float) -> None: ...
    @overload
    def setRelativePosition(self, d: float) -> None: ...
    @overload
    def setOrigin(self, stageLabel: str) -> None: ...
    @overload
    def setOrigin(self) -> None: ...
    @overload
    def setAdapterOrigin(self, stageLabel: str, newZUm: float) -> None: ...
    @overload
    def setAdapterOrigin(self, newZUm: float) -> None: ...
    def setFocusDirection(self, stageLabel: str, sign: int) -> None:
        """
        Set the focus direction of a stage.
        The sign should be +1 (or any positive value), zero, or -1 (or any negative value), and is interpreted in the same way as the return value of getFocusDirection().
        """
    def getFocusDirection(self, stageLabel: str) -> int:
        """
        Get the focus direction of a stage.
        Returns +1 if increasing position brings objective closer to sample, -1 if increasing position moves objective away from sample, or 0 if unknown. (Make sure to check for zero!)
        """
    def isStageSequenceable(self, stageLabel: str) -> bool:
        """Queries stage if it can be used in a sequence"""
    def isStageLinearSequenceable(self, stageLabel: str) -> bool:
        """
        Queries if the stage can be used in a linear sequence A linear sequence is defined by a stepsize and number of slices
        """
    def startStageSequence(self, stageLabel: str) -> None:
        """
        Starts an ongoing sequence of triggered events in a stage This should only be called for stages
        """
    def stopStageSequence(self, stageLabel: str) -> None:
        """
        Stops an ongoing sequence of triggered events in a stage This should only be called for stages that are sequenceable
        """
    def getStageSequenceMaxLength(self, stageLabel: str) -> int:
        """
        Gets the maximum length of a stage's position sequence. This should only be called for stages that are sequenceable
        """
    def loadStageSequence(
        self, stageLabel: str, positionSequence: Sequence[float]
    ) -> None:
        """
        Transfer a sequence of events/states/whatever to the device This should only be called for device-properties that are sequenceable
        """
    def setStageLinearSequence(
        self, stageLabel: str, dZ_um: float, nSlices: int
    ) -> None:
        """
        Loads a linear sequence (defined by stepsize and nr. of steps) into the device. Why was it not called loadStageLinearSequence???
        """
    @overload
    def setXYPosition(self, xyStageLabel: str, x: float, y: float) -> None: ...
    @overload
    def setXYPosition(self, x: float, y: float) -> None: ...
    @overload
    def setRelativeXYPosition(
        self, xyStageLabel: str, dx: float, dy: float
    ) -> None: ...
    @overload
    def setRelativeXYPosition(self, dx: float, dy: float) -> None: ...
    @overload
    def getXYPosition(self, xyStageLabel: str) -> tuple[float, float]: ...
    @overload
    def getXYPosition(self) -> tuple[float, float]: ...
    @overload
    def getXPosition(self, xyStageLabel: str) -> float: ...
    @overload
    def getXPosition(self) -> float: ...
    @overload
    def getYPosition(self, xyStageLabel: str) -> float: ...
    @overload
    def getYPosition(self) -> float: ...
    def stop(self, xyOrZStageLabel: str) -> None:
        """Stop the XY or focus/Z stage motors"""
    def home(self, xyOrZStageLabel: str) -> None:
        """Perform a hardware homing operation for an XY or focus/Z stage."""
    @overload
    def setOriginXY(self, xyStageLabel: str) -> None: ...
    @overload
    def setOriginXY(self) -> None: ...
    @overload
    def setOriginX(self, xyStageLabel: str) -> None: ...
    @overload
    def setOriginX(self) -> None: ...
    @overload
    def setOriginY(self, xyStageLabel: str) -> None: ...
    @overload
    def setOriginY(self) -> None: ...
    @overload
    def setAdapterOriginXY(
        self, xyStageLabel: str, newXUm: float, newYUm: float
    ) -> None: ...
    @overload
    def setAdapterOriginXY(self, newXUm: float, newYUm: float) -> None: ...
    def isXYStageSequenceable(self, xyStageLabel: str) -> bool:
        """Queries XY stage if it can be used in a sequence"""
    def startXYStageSequence(self, xyStageLabel: str) -> None:
        """
        Starts an ongoing sequence of triggered events in an XY stage This should only be called for stages
        """
    def stopXYStageSequence(self, xyStageLabel: str) -> None:
        """
        Stops an ongoing sequence of triggered events in an XY stage This should only be called for stages that are sequenceable
        """
    def getXYStageSequenceMaxLength(self, xyStageLabel: str) -> int:
        """
        Gets the maximum length of an XY stage's position sequence. This should only be called for XY stages that are sequenceable
        """
    def loadXYStageSequence(
        self, xyStageLabel: str, xSequence: Sequence[float], ySequence: Sequence[float]
    ) -> None:
        """
        Transfer a sequence of stage positions to the xy stage. xSequence and ySequence must have the same length. This should only be called for XY stages that are sequenceable
        """
    def setSerialProperties(
        self,
        portName: str,
        answerTimeout: str,
        baudRate: str,
        delayBetweenCharsMs: str,
        handshaking: str,
        parity: str,
        stopBits: str,
    ) -> None:
        """Sets all com port properties in a single call"""
    def setSerialPortCommand(self, portLabel: str, command: str, term: str) -> None:
        """
        Send string to the serial device and return an answer. This command blocks until it receives an answer from the device terminated by the specified sequence.
        """
    def getSerialPortAnswer(self, portLabel: str, term: str) -> str:
        """
        Continuously read from the serial port until the terminating sequence is encountered.
        """
    def writeToSerialPort(self, portLabel: str, data: Sequence[str]) -> None:
        """
        Sends an array of characters to the serial port and returns immediately.
        """
    def readFromSerialPort(self, portLabel: str) -> list[str]:
        """Reads the contents of the Rx buffer."""
    def setSLMImage(
        self, slmLabel: str, pixels: Annotated[ArrayLike, {"dtype": "uint8"}]
    ) -> None: ...
    @overload
    def setSLMPixelsTo(self, slmLabel: str, intensity: int) -> None: ...
    @overload
    def setSLMPixelsTo(
        self, slmLabel: str, red: int, green: int, blue: int
    ) -> None: ...
    def displaySLMImage(self, slmLabel: str) -> None:
        """Display the waiting image on the SLM."""
    def setSLMExposure(self, slmLabel: str, exposure_ms: float) -> None:
        """
        For SLM devices with build-in light source (such as projectors) this will set the exposure time, but not (yet) start the illumination
        """
    def getSLMExposure(self, slmLabel: str) -> float:
        """
        Returns the exposure time that will be used by the SLM for illumination
        """
    def getSLMWidth(self, slmLabel: str) -> int:
        """Returns the width (in "pixels") of the SLM"""
    def getSLMHeight(self, slmLabel: str) -> int:
        """Returns the height (in "pixels") of the SLM"""
    def getSLMNumberOfComponents(self, slmLabel: str) -> int:
        """
        Returns the number of components (usually these depict colors) of the SLM For instance, an RGB projector will return 3, but a grey scale SLM returns 1
        """
    def getSLMBytesPerPixel(self, slmLabel: str) -> int:
        """Returns the number of bytes per SLM pixel"""
    def getSLMSequenceMaxLength(self, slmLabel: str) -> int:
        """
        For SLMs that support sequences, returns the maximum length of the sequence that can be uploaded to the device
        """
    def startSLMSequence(self, slmLabel: str) -> None:
        """Starts the sequence previously uploaded to the SLM"""
    def stopSLMSequence(self, slmLabel: str) -> None:
        """Stops the SLM sequence if previously started"""
    def loadSLMSequence(
        self, slmLabel: str, pixels: Sequence[Annotated[ArrayLike, {"dtype": "uint8"}]]
    ) -> None: ...
    def pointGalvoAndFire(
        self, galvoLabel: str, x: float, y: float, pulseTime_us: float
    ) -> None:
        """
        Set the Galvo to an x,y position and fire the laser for a predetermined duration.
        """
    def setGalvoSpotInterval(self, galvoLabel: str, pulseTime_us: float) -> None: ...
    def setGalvoPosition(self, galvoLabel: str, x: float, y: float) -> None:
        """Set the Galvo to an x,y position"""
    def getGalvoPosition(self, arg: str, /) -> tuple[float, float]: ...
    def setGalvoIlluminationState(self, galvoLabel: str, on: bool) -> None:
        """Set the galvo's illumination state to on or off"""
    def getGalvoXRange(self, galvoLabel: str) -> float:
        """Get the Galvo x range"""
    def getGalvoXMinimum(self, galvoLabel: str) -> float:
        """Get the Galvo x minimum"""
    def getGalvoYRange(self, galvoLabel: str) -> float:
        """Get the Galvo y range"""
    def getGalvoYMinimum(self, galvoLabel: str) -> float:
        """Get the Galvo y minimum"""
    def addGalvoPolygonVertex(
        self, galvoLabel: str, polygonIndex: int, x: float, y: float
    ) -> None:
        """Add a vertex to a galvo polygon."""
    def deleteGalvoPolygons(self, galvoLabel: str) -> None:
        """Remove all added polygons"""
    def loadGalvoPolygons(self, galvoLabel: str) -> None:
        """Load a set of galvo polygons to the device"""
    def setGalvoPolygonRepetitions(self, galvoLabel: str, repetitions: int) -> None:
        """Set the number of times to loop galvo polygons"""
    def runGalvoPolygons(self, galvoLabel: str) -> None:
        """Run a loop of galvo polygons"""
    def runGalvoSequence(self, galvoLabel: str) -> None:
        """Run a sequence of galvo positions"""
    def getGalvoChannel(self, galvoLabel: str) -> str:
        """
        Get the name of the active galvo channel (for a multi-laser galvo device).
        """
    def pressurePumpStop(self, pumpLabel: str) -> None:
        """Stops the pressure pump"""
    def pressurePumpCalibrate(self, pumpLabel: str) -> None: ...
    def pressurePumpRequiresCalibration(self, pumpLabel: str) -> bool:
        """Returns boolean whether the pump is operational before calibration"""
    def setPumpPressureKPa(self, pumpLabel: str, pressure: float) -> None:
        """Sets the pressure of the pump in kPa"""
    def getPumpPressureKPa(self, pumpLabel: str) -> float:
        """Gets the pressure of the pump in kPa"""
    def volumetricPumpStop(self, pumpLabel: str) -> None:
        """Stops the volumetric pump"""
    def volumetricPumpHome(self, pumpLabel: str) -> None: ...
    def volumetricPumpRequiresHoming(self, pumpLabel: str) -> bool: ...
    def invertPumpDirection(self, pumpLabel: str, invert: bool) -> None:
        """Sets whether the pump direction needs to be inverted"""
    def isPumpDirectionInverted(self, pumpLabel: str) -> bool:
        """Gets whether the pump direction needs to be inverted"""
    def setPumpVolume(self, pumpLabel: str, volume: float) -> None:
        """
        Sets the volume of fluid in the pump in uL. Note it does not withdraw upto this amount. It is merely to inform MM of the volume in a prefilled pump.
        """
    def getPumpVolume(self, pumpLabel: str) -> float:
        """Get the fluid volume in the pump in uL"""
    def setPumpMaxVolume(self, pumpLabel: str, volume: float) -> None:
        """Sets the max volume of the pump in uL"""
    def getPumpMaxVolume(self, pumpLabel: str) -> float:
        """Gets the max volume of the pump in uL"""
    def setPumpFlowrate(self, pumpLabel: str, volume: float) -> None:
        """Sets the flowrate of the pump in uL per second"""
    def getPumpFlowrate(self, pumpLabel: str) -> float:
        """Gets the flowrate of the pump in uL per second"""
    def pumpStart(self, pumpLabel: str) -> None:
        """
        Start dispensing at the set flowrate until syringe is empty, or manually stopped (whichever occurs first).
        """
    def pumpDispenseDurationSeconds(self, pumpLabel: str, seconds: float) -> None:
        """Dispenses for the provided duration (in seconds) at the set flowrate"""
    def pumpDispenseVolumeUl(self, pumpLabel: str, microLiter: float) -> None:
        """Dispenses the provided volume (in uL) at the set flowrate"""
    def supportsDeviceDetection(self, deviceLabel: str) -> bool:
        """
        Return whether or not the device supports automatic device detection (i.e. whether or not detectDevice() may be safely called).
        """
    def detectDevice(self, deviceLabel: str) -> DeviceDetectionStatus:
        """
        Tries to communicate to a device through a given serial port Used to automate discovery of correct serial port Also configures the serial port correctly
        """
    def getParentLabel(self, peripheralLabel: str) -> str: ...
    def setParentLabel(self, deviceLabel: str, parentHubLabel: str) -> None:
        """Sets parent device label"""
    def getInstalledDevices(self, hubLabel: str) -> list[str]:
        """
        Performs auto-detection and loading of child devices that are attached to a Hub device. For example, if a motorized microscope is represented by a Hub device, it is capable of discovering what specific child devices are currently attached. In that case this call might report that Z-stage, filter changer and objective turret are currently installed and return three device names in the string list.
        """
    def getInstalledDeviceDescription(
        self, hubLabel: str, peripheralLabel: str
    ) -> str: ...
    def getLoadedPeripheralDevices(self, hubLabel: str) -> list[str]: ...
