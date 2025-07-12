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
        """
        Loads a device from the plugin library. label assigned name for the device during the core session moduleName the name of the device adapter module (short name, not full file name) deviceName the name of the device. The name must correspond to one of the names recognized by the specific plugin library.
        """
    def unloadDevice(self, label: str) -> None:
        """Unloads the device from the core and adjusts all configuration data."""
    def unloadAllDevices(self) -> None: ...
    def initializeAllDevices(self) -> None:
        """
        Calls Initialize() method for each loaded device. Parallel implemnetation should be faster
        """
    def initializeDevice(self, label: str) -> None:
        """Initializes specific device. label the device label"""
    def getDeviceInitializationState(self, label: str) -> DeviceInitializationState:
        """
        Queries the initialization state of the given device. label the device label
        """
    def reset(self) -> None:
        """Unloads all devices from the core, clears all configuration data."""
    def unloadLibrary(self, moduleName: str) -> None:
        """Forcefully unload a library. Experimental. Don't use."""
    def updateCoreProperties(self) -> None:
        """
        Updates CoreProperties (currently all Core properties are devices types) with the loaded hardware. After this call, each of the Core-Device properties will be populated with the currently loaded devices of that type
        """
    def getCoreErrorText(self, code: int) -> str: ...
    def getVersionInfo(self) -> str: ...
    def getAPIVersionInfo(self) -> str: ...
    def getSystemState(self) -> Configuration:
        """
        Returns the entire system state, i.e. the collection of all property values from all devices.
         For legacy reasons, this function does not throw an exception if there is an error. If there is an error, properties may be missing from the return value.
         Configuration  object containing a collection of device-property-value triplets
        """
    def setSystemState(self, conf: Configuration) -> None:
        """
        Sets all properties contained in the Configuration object. The procedure will attempt to set each property it encounters, but won't stop if any of the properties fail or if the requested device is not present. It will just quietly continue. conf the configuration object representing the desired system state
        """
    def getConfigState(self, group: str, config: str) -> Configuration:
        """
        Returns a partial state of the system, only for devices included in the specified configuration.
        """
    def getConfigGroupState(self, group: str) -> Configuration:
        """
        Returns the partial state of the system, only for the devices included in the specified group. It will create a union of all devices referenced in a group.
        """
    def saveSystemState(self, fileName: str) -> None:
        """
        Saves the current system state to a text file of the MM specific format. The file records only read-write properties. The file format is directly readable by the complementary loadSystemState() command.
        """
    def loadSystemState(self, fileName: str) -> None:
        """
        Loads the system configuration from the text file conforming to the MM specific format. The configuration contains a list of commands to build the desired system state from read-write properties. Format specification: the same as in loadSystemConfiguration() command
        """
    def registerCallback(self, cb: MMEventCallback | None) -> None:
        """
        Register a callback (listener class). MMCore will send notifications on internal events using this interface. Pass nullptr to unregister. The caller is responsible for ensuring that the object pointed to by cb remains valid until it is unregistered. This function is not thread safe.
        """
    def setPrimaryLogFile(self, filename: object, truncate: bool = False) -> None: ...
    def getPrimaryLogFile(self) -> str: ...
    @overload
    def logMessage(self, msg: str) -> None:
        """Record text message in the log file."""
    @overload
    def logMessage(self, msg: str, debugOnly: bool) -> None: ...
    def enableDebugLog(self, enable: bool) -> None:
        """
        Enable or disable logging of debug messages. enable if set to true, debug messages will be recorded in the log file
        """
    def debugLogEnabled(self) -> bool:
        """Indicates if logging of debug messages is enabled"""
    def enableStderrLog(self, enable: bool) -> None:
        """
        Enables or disables log message display on the standard console. enable if set to true, log file messages will be echoed on the stderr.
        """
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
        """
        Stop capturing logging output into an additional file. handle The secondary log handle returned by startSecondaryLogFile().
        """
    def getDeviceAdapterSearchPaths(self) -> list[str]: ...
    def setDeviceAdapterSearchPaths(self, paths: Sequence[str]) -> None:
        """
        Set the device adapter search paths. Upon subsequent attempts to load device adapters, these paths (and only these paths) will be searched. Calling this function has no effect on device adapters that have already been loaded. If you want to simply add to the list of paths, you must first retrieve the current paths by calling getDeviceAdapterSearchPaths(). paths the device adapter search paths
        """
    def getDeviceAdapterNames(self) -> list[str]: ...
    def getAvailableDevices(self, library: str) -> list[str]: ...
    def getAvailableDeviceDescriptions(self, library: str) -> list[str]: ...
    def getAvailableDeviceTypes(self, library: str) -> list[int]: ...
    def getLoadedDevices(self) -> list[str]: ...
    def getLoadedDevicesOfType(self, devType: DeviceType) -> list[str]: ...
    def getDeviceType(self, label: str) -> DeviceType: ...
    def getDeviceLibrary(self, label: str) -> str: ...
    def getDeviceName(self, label: str) -> str: ...
    def getDeviceDescription(self, label: str) -> str: ...
    def getDevicePropertyNames(self, label: str) -> list[str]: ...
    def hasProperty(self, label: str, propName: str) -> bool:
        """
        Checks if device has a property with a specified name. The exception will be thrown in case device label is not defined.
        """
    def getProperty(self, label: str, propName: str) -> str: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: str) -> None:
        """
        Changes the value of the device property. label the device label propName the property name propValue the new property value
        """
    @overload
    def setProperty(self, label: str, propName: str, propValue: bool) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: int) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: float) -> None: ...
    def getAllowedPropertyValues(self, label: str, propName: str) -> list[str]: ...
    def isPropertyReadOnly(self, label: str, propName: str) -> bool:
        """
        Tells us whether the property can be modified. true for a read-only property label the device label propName the property name
        """
    def isPropertyPreInit(self, label: str, propName: str) -> bool:
        """
        Tells us whether the property must be defined prior to initialization. true for pre-init property label the device label propName the property name
        """
    def isPropertySequenceable(self, label: str, propName: str) -> bool: ...
    def hasPropertyLimits(self, label: str, propName: str) -> bool:
        """
        Queries device if the specific property has limits. label the device name propName the property label
        """
    def getPropertyLowerLimit(self, label: str, propName: str) -> float:
        """
        Returns the property lower limit value, if the property has limits - 0 otherwise.
        """
    def getPropertyUpperLimit(self, label: str, propName: str) -> float:
        """
        Returns the property upper limit value, if the property has limits - 0 otherwise.
        """
    def getPropertyType(self, label: str, propName: str) -> PropertyType: ...
    def startPropertySequence(self, label: str, propName: str) -> None:
        """
        Starts an ongoing sequence of triggered events in a property of a device This should only be called for device-properties that are sequenceable label the device name propName the property label
        """
    def stopPropertySequence(self, label: str, propName: str) -> None:
        """
        Stops an ongoing sequence of triggered events in a property of a device This should only be called for device-properties that are sequenceable label the device label propName the property name
        """
    def getPropertySequenceMaxLength(self, label: str, propName: str) -> int:
        """
        Queries device property for the maximum number of events that can be put in a sequence label the device name propName the property label
        """
    def loadPropertySequence(
        self, label: str, propName: str, eventSequence: Sequence[str]
    ) -> None:
        """
        Transfer a sequence of events/states/whatever to the device This should only be called for device-properties that are sequenceable label the device name propName the property label eventSequence the sequence of events/states that the device will execute in response to external triggers
        """
    def deviceBusy(self, label: str) -> bool:
        """
        Checks the busy status of the specific device. label the device label true if the device is busy
        """
    def waitForDevice(self, label: str) -> None:
        """
        Waits (blocks the calling thread) until the specified device becomes device the device label
        """
    def waitForConfig(self, group: str, configName: str) -> None:
        """
        Blocks until all devices included in the configuration become ready. group the configuration group config the configuration preset
        """
    def systemBusy(self) -> bool:
        """
        Checks the busy status of the entire system. The system will report busy if any of the devices is busy. status (true on busy)
        """
    def waitForSystem(self) -> None:
        """Blocks until all devices in the system become ready (not-busy)."""
    def deviceTypeBusy(self, devType: DeviceType) -> bool:
        """
        Checks the busy status for all devices of the specific type. The system will report busy if any of the devices of the specified type are busy. true on busy devType a constant specifying the device type
        """
    def waitForDeviceType(self, devType: DeviceType) -> None:
        """
        Blocks until all devices of the specific type become ready (not-busy). devType a constant specifying the device type
        """
    def getDeviceDelayMs(self, label: str) -> float:
        """
        Reports action delay in milliseconds for the specific device. The delay is used in the synchronization process to ensure that the action is performed, without polling. Value of "0" means that action is either blocking or that polling of device status is required. Some devices ignore this setting. the delay time in milliseconds label the device label
        """
    def setDeviceDelayMs(self, label: str, delayMs: float) -> None:
        """
        Overrides the built-in value for the action delay. Some devices ignore this setting. label the device label delayMs the desired delay in milliseconds
        """
    def usesDeviceDelay(self, label: str) -> bool:
        """
        Signals if the device will use the delay setting or not. label the device label true if the device uses a delay
        """
    def setTimeoutMs(self, timeoutMs: int) -> None: ...
    def getTimeoutMs(self) -> int: ...
    def sleep(self, intervalMs: float) -> None:
        """
        Waits (blocks the calling thread) for specified time in milliseconds. intervalMs the time to sleep in milliseconds
        """
    def getCameraDevice(self) -> str: ...
    def getShutterDevice(self) -> str: ...
    def getFocusDevice(self) -> str: ...
    def getXYStageDevice(self) -> str: ...
    def getAutoFocusDevice(self) -> str: ...
    def getImageProcessorDevice(self) -> str: ...
    def getSLMDevice(self) -> str: ...
    def getGalvoDevice(self) -> str: ...
    def getChannelGroup(self) -> str: ...
    def setCameraDevice(self, cameraLabel: str) -> None:
        """Sets the current camera device. camera the camera device label"""
    def setShutterDevice(self, shutterLabel: str) -> None:
        """Sets the current shutter device. shutter the shutter device label"""
    def setFocusDevice(self, focusLabel: str) -> None:
        """Sets the current focus device. focus the focus stage device label"""
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
        Returns the entire system state, i.e. the collection of all property values from all devices. This method will return cached values instead of querying each device Configuration object containing a collection of device-property-value triplets
        """
    def updateSystemStateCache(self) -> None:
        """Updates the state of the entire hardware."""
    def getPropertyFromCache(self, deviceLabel: str, propName: str) -> str: ...
    def getCurrentConfigFromCache(self, groupName: str) -> str: ...
    def getConfigGroupStateFromCache(self, group: str) -> Configuration:
        """
        Returns the partial state of the system cache, only for the devices included in the specified group. It will create a union of all devices referenced in a group.
        """
    @overload
    def defineConfig(self, groupName: str, configName: str) -> None:
        """
        Defines a configuration. If the configuration group/name was not previously defined a new configuration will be automatically created; otherwise nothing happens. groupName the configuration group name configName the configuration preset name
        """
    @overload
    def defineConfig(
        self,
        groupName: str,
        configName: str,
        deviceLabel: str,
        propName: str,
        value: str,
    ) -> None:
        """
        Defines a single configuration entry (setting). If the configuration group/name was not previously defined a new configuration will be automatically created. If the name was previously defined the new setting will be added to its list of property settings. The new setting will override previously defined ones if it refers to the same property name. groupName the group name configName the configuration name deviceLabel the device label propName the property name value the property value
        """
    def defineConfigGroup(self, groupName: str) -> None:
        """Creates an empty configuration group."""
    def deleteConfigGroup(self, groupName: str) -> None:
        """Deletes an entire configuration group."""
    def renameConfigGroup(self, oldGroupName: str, newGroupName: str) -> None:
        """Renames a configuration group."""
    def isGroupDefined(self, groupName: str) -> bool:
        """
        Checks if the group already exists. true if the group is already defined
        """
    def isConfigDefined(self, groupName: str, configName: str) -> bool:
        """
        Checks if the configuration already exists within a group. true if the configuration is already defined
        """
    def setConfig(self, groupName: str, configName: str) -> None:
        """
        Applies a configuration to a group. The command will fail if the configuration was not previously defined. groupName the configuration group name configName the configuration preset name
        """
    @overload
    def deleteConfig(self, groupName: str, configName: str) -> None:
        """
        Deletes a configuration from a group. The command will fail if the configuration was not previously defined.
        """
    @overload
    def deleteConfig(
        self, groupName: str, configName: str, deviceLabel: str, propName: str
    ) -> None:
        """
        Deletes a property from a configuration in the specified group. The command will fail if the configuration was not previously defined.
        """
    def renameConfig(
        self, groupName: str, oldConfigName: str, newConfigName: str
    ) -> None:
        """
        Renames a configuration within a specified group. The command will fail if the configuration was not previously defined.
        """
    def getAvailableConfigGroups(self) -> list[str]: ...
    def getAvailableConfigs(self, configGroup: str) -> list[str]: ...
    def getCurrentConfig(self, groupName: str) -> str: ...
    def getConfigData(self, configGroup: str, configName: str) -> Configuration:
        """
        Returns the configuration object for a given group and name. The configuration object
        """
    @overload
    def getCurrentPixelSizeConfig(self) -> str: ...
    @overload
    def getCurrentPixelSizeConfig(self, cached: bool) -> str: ...
    @overload
    def getPixelSizeUm(self) -> float:
        """
        Returns the current pixel size in microns. This method is based on sensing the current pixel size configuration and adjusting for the binning.
        """
    @overload
    def getPixelSizeUm(self, cached: bool) -> float:
        """
        Returns the current pixel size in microns. This method is based on sensing the current pixel size configuration and adjusting for the binning. For legacy reasons, an exception is not thrown if there is an error. Instead, 0.0 is returned if any property values cannot be read, or if no pixel size preset matches the property values.
        """
    def getPixelSizeUmByID(self, resolutionID: str) -> float:
        """Returns the pixel size in um for the requested pixel size group"""
    @overload
    def getPixelSizeAffine(self) -> list[float]: ...
    @overload
    def getPixelSizeAffine(self, cached: bool) -> list[float]: ...
    def getPixelSizeAffineByID(self, resolutionID: str) -> list[float]: ...
    @overload
    def getPixelSizedxdz(self) -> float:
        """
        Returns the angle between the camera's x axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in x caused by a translation in z, i.e. dx / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 angle (dx/dz) of the Z-stage axis with the camera axis (dimensionless)
        """
    @overload
    def getPixelSizedxdz(self, cached: bool) -> float:
        """
        Returns the angle between the camera's x axis and the axis (direction) of the z drive for the given pixel size configuration. This angle is dimensionless (i.e. the ratio of the translation in x caused by a translation in z, i.e. dx / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 resolutionID The pixel size configuration group name Angle (dx/dz) of the Z-stage axis with the camera axis (dimensionless)
        """
    @overload
    def getPixelSizedxdz(self, resolutionID: str) -> float:
        """
        Returns the angle between the camera's x axis and the axis (direction) of the z drive for the given pixel size configuration. This angle is dimensionless (i.e. the ratio of the translation in x caused by a translation in z, i.e. dx / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 resolutionID The pixel size configuration group name Angle (dx/dz) of the Z-stage axis with the camera axis (dimensionless)
        """
    @overload
    def getPixelSizedydz(self) -> float:
        """
        Returns the angle between the camera's y axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in y caused by a translation in z, i.e. dy / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 angle (dy/dz) of the Z-stage axis with the camera axis (dimensionless)
        """
    @overload
    def getPixelSizedydz(self, cached: bool) -> float:
        """
        Returns the angle between the camera's y axis and the axis (direction) of the z drive for the given pixel size configuration. This angle is dimensionless (i.e. the ratio of the translation in y caused by a translation in z, i.e. dy / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 @resolutionID Name of Pixel Size configuration for this dy /dz angle angle (dy/dz) of the Z-stage axis with the camera axis (dimensionless)
        """
    @overload
    def getPixelSizedydz(self, resolutionID: str) -> float:
        """
        Returns the angle between the camera's y axis and the axis (direction) of the z drive for the given pixel size configuration. This angle is dimensionless (i.e. the ratio of the translation in y caused by a translation in z, i.e. dy / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 @resolutionID Name of Pixel Size configuration for this dy /dz angle angle (dy/dz) of the Z-stage axis with the camera axis (dimensionless)
        """
    @overload
    def getPixelSizeOptimalZUm(self) -> float:
        """
        Returns the optimal z step size in um There is no magic to this number, but lets the system configuration communicate to the end user what the optimal Z step size is for this pixel size configuration
        """
    @overload
    def getPixelSizeOptimalZUm(self, cached: bool) -> float:
        """
        Returns the optimal z step size in um, optionally using cached pixel configuration There is no magic to this number, but lets the system configuration communicate to the end user what the optimal Z step size is for this pixel size configuration
        """
    @overload
    def getPixelSizeOptimalZUm(self, resolutionID: str) -> float:
        """
        Returns the optimal z step size in um, optionally using cached pixel configuration There is no magic to this number, but lets the system configuration communicate to the end user what the optimal Z step size is for this pixel size configuration
        """
    def setPixelSizedxdz(self, resolutionID: str, dXdZ: float) -> None:
        """
        Sets the angle between the camera's x axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in x caused by a translation in z, i.e. dx / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 resolutionID The pixel size configuration group name dxdz Angle of the Z-stage axis with the camera axis (dimensionless)
        """
    def setPixelSizedydz(self, resolutionID: str, dYdZ: float) -> None:
        """
        Sets the angle between the camera's y axis and the axis (direction) of the z drive. This angle is dimensionless (i.e. the ratio of the translation in y caused by a translation in z, i.e. dy / dz). This angle can be different for different z drives (if there are multiple Z drives in the system, please add the Core-Focus device to the pixel size configuration). See: https://github.com/micro-manager/micro-manager/issues/1984 resolutionID The pixel size configuration group name dydz Angle of the Z-stage axis with the camera axis (dimensionless)
        """
    def setPixelSizeOptimalZUm(self, resolutionID: str, optimalZ: float) -> None:
        """
        Sets the opimal Z stepSize (in microns). There is no magic here, this number is provided by the person configuring the microscope, to be used by the person using the microscope. resolutionID The pixel size configuration group name optimalZ Optimal z step in microns
        """
    def getMagnificationFactor(self) -> float:
        """
        Returns the product of all Magnifiers in the system or 1.0 when none is found This is used internally by GetPixelSizeUm products of all magnifier devices in the system or 1.0 when none is found
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
    ) -> None:
        """
        Defines a single pixel size entry (setting). The system will treat pixel size configurations very similar to configuration presets, i.e. it will try to detect if any of the pixel size presets matches the current state of the system. If the pixel size was previously defined the new setting will be added to its list of property settings. The new setting will override previously defined ones if it refers to the same property name. resolutionID identifier for one unique property setting deviceLabel device label propName property name value property value
        """
    @overload
    def definePixelSizeConfig(self, resolutionID: str) -> None:
        """Defines an empty pixel size entry."""
    def getAvailablePixelSizeConfigs(self) -> list[str]: ...
    def isPixelSizeConfigDefined(self, resolutionID: str) -> bool:
        """
        Checks if the Pixel Size Resolution already exists true if the configuration is already defined
        """
    def setPixelSizeConfig(self, resolutionID: str) -> None:
        """
        Applies a Pixel Size Configuration. The command will fail if the configuration was not previously defined. resolutionID the pixel size configuration group name
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
        """
        Returns the configuration object for a give pixel size preset. The configuration object
        """
    @overload
    def setROI(self, x: int, y: int, xSize: int, ySize: int) -> None:
        """
        Set the hardwar region of interest for the current camera. A successful call to this method will clear any images in the sequence buffer, even if the ROI does not change. If multiple ROIs are set prior to this call, they will be replaced by the new single ROI. The coordinates are in units of binned pixels. That is, conceptually, binning is applied before the ROI. x coordinate of the top left corner y coordinate of the top left corner xSize number of horizontal pixels ySize number of horizontal pixels
        """
    @overload
    def setROI(self, label: str, x: int, y: int, xSize: int, ySize: int) -> None:
        """
        Set the hardware region of interest for a specified camera. A successful call to this method will clear any images in the sequence buffer, even if the ROI does not change. Warning: the clearing of the sequence buffer will interfere with any sequence acquisitions currently being performed on other cameras. If multiple ROIs are set prior to this call, they will be replaced by the new single ROI. The coordinates are in units of binned pixels. That is, conceptually, binning is applied before the ROI. label camera label x coordinate of the top left corner y coordinate of the top left corner xSize number of horizontal pixels ySize number of horizontal pixels
        """
    @overload
    def getROI(self) -> tuple[int, int, int, int]: ...
    @overload
    def getROI(self, label: str) -> tuple[int, int, int, int]: ...
    def clearROI(self) -> None:
        """
        Set the region of interest of the current camera to the full frame. A successful call to this method will clear any images in the sequence buffer, even if the ROI does not change.
        """
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
        Set multiple ROIs for the current camera device. Will fail if the camera does not support multiple ROIs, any widths or heights are non-positive, or if the vectors do not all have the same length. xs X indices for the upper-left corners of each ROI. ys Y indices for the upper-left corners of each ROI. widths Width in pixels for each ROI. heights Height in pixels for each ROI.
        """
    def getMultiROI(self) -> tuple[list[int], list[int], list[int], list[int]]: ...
    @overload
    def setExposure(self, exp: float) -> None:
        """
        Sets the exposure setting of the current camera in milliseconds. dExp the exposure in milliseconds
        """
    @overload
    def setExposure(self, cameraLabel: str, dExp: float) -> None:
        """
        Sets the exposure setting of the specified camera in milliseconds. label the camera device label dExp the exposure in milliseconds
        """
    @overload
    def getExposure(self) -> float:
        """
        Returns the current exposure setting of the camera in milliseconds. the exposure time in milliseconds
        """
    @overload
    def getExposure(self, label: str) -> float:
        """
        Returns the current exposure setting of the specified camera in milliseconds. label the camera device label the exposure time in milliseconds
        """
    def snapImage(self) -> None:
        """
        Acquires a single image with current settings. Snap is not allowed while the acquisition thread is run
        """
    @overload
    def getImage(self) -> Annotated[ArrayLike, {"writable": False}]: ...
    @overload
    def getImage(self, arg: int, /) -> Annotated[ArrayLike, {"writable": False}]:
        """
        Horizontal dimension of the image buffer in pixels. the width in pixels (an integer)
        """
    def getImageWidth(self) -> int:
        """
        Horizontal dimension of the image buffer in pixels. the width in pixels (an integer)
        """
    def getImageHeight(self) -> int:
        """
        Vertical dimension of the image buffer in pixels. the height in pixels (an integer)
        """
    def getBytesPerPixel(self) -> int:
        """
        How many bytes for each pixel. This value does not necessarily reflect the capabilities of the particular camera A/D converter.  the number of bytes
        """
    def getImageBitDepth(self) -> int:
        """
        How many bits of dynamic range are to be expected from the camera. This value should be used only as a guideline - it does not guarantee that image buffer will contain only values from the returned dynamic range.
         the number of bits
        """
    def getNumberOfComponents(self) -> int:
        """
        Returns the number of components the default camera is returning. For example color camera will return 4 components (RGBA) on each snap.
        """
    def getNumberOfCameraChannels(self) -> int:
        """
        Returns the number of simultaneous channels the default camera is returning.
        """
    def getCameraChannelName(self, channelNr: int) -> str: ...
    def getImageBufferSize(self) -> int:
        """
        Returns the size of the internal image buffer.
         buffer size
        """
    def setAutoShutter(self, state: bool) -> None:
        """
        If this option is enabled Shutter automatically opens and closes when the image is acquired. state true for enabled
        """
    def getAutoShutter(self) -> bool:
        """Returns the current setting of the auto-shutter option."""
    @overload
    def setShutterOpen(self, state: bool) -> None:
        """
        Opens or closes the currently selected (default) shutter. state the desired state of the shutter (true for open)
        """
    @overload
    def setShutterOpen(self, shutterLabel: str, state: bool) -> None:
        """
        Opens or closes the specified shutter. state the desired state of the shutter (true for open)
        """
    @overload
    def getShutterOpen(self) -> bool:
        """Returns the state of the currently selected (default) shutter."""
    @overload
    def getShutterOpen(self, shutterLabel: str) -> bool:
        """
        Returns the state of the specified shutter. shutterLabel the name of the shutter
        """
    @overload
    def startSequenceAcquisition(
        self, numImages: int, intervalMs: float, stopOnOverflow: bool
    ) -> None:
        """
        Starts streaming camera sequence acquisition. This command does not block the calling thread for the duration of the acquisition. numImages Number of images requested from the camera intervalMs The interval between images, currently only supported by Andor cameras stopOnOverflow whether or not the camera stops acquiring when the circular buffer is full
        """
    @overload
    def startSequenceAcquisition(
        self, cameraLabel: str, numImages: int, intervalMs: float, stopOnOverflow: bool
    ) -> None:
        """
        Starts streaming camera sequence acquisition for a specified camera. This command does not block the calling thread for the duration of the acquisition. The difference between this method and the one with the same name but operating on the "default" camera is that it does not automatically initialize the circular buffer.
        """
    def prepareSequenceAcquisition(self, cameraLabel: str) -> None: ...
    def startContinuousSequenceAcquisition(self, intervalMs: float) -> None:
        """
        Starts the continuous camera sequence acquisition. This command does not block the calling thread for the duration of the acquisition.
        """
    @overload
    def stopSequenceAcquisition(self) -> None:
        """Stops streaming camera sequence acquisition."""
    @overload
    def stopSequenceAcquisition(self, cameraLabel: str) -> None:
        """
        Stops streaming camera sequence acquisition for a specified camera. label The camera name
        """
    @overload
    def isSequenceRunning(self) -> bool:
        """
        Check if the current camera is acquiring the sequence Returns false when the sequence is done
        """
    @overload
    def isSequenceRunning(self, cameraLabel: str) -> bool:
        """
        Check if the specified camera is acquiring the sequence Returns false when the sequence is done
        """
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
        """
        Removes all images from the circular buffer. It is rarely necessary to call this directly since starting a sequence acquisition or changing the ROI will always clear the buffer.
        """
    def isExposureSequenceable(self, cameraLabel: str) -> bool:
        """
        Queries camera if exposure can be used in a sequence cameraLabel the camera device label true if exposure can be sequenced
        """
    def startExposureSequence(self, cameraLabel: str) -> None:
        """
        Starts an ongoing sequence of triggered exposures in a camera This should only be called for cameras where exposure time is sequenceable cameraLabel the camera device label
        """
    def stopExposureSequence(self, cameraLabel: str) -> None:
        """
        Stops an ongoing sequence of triggered exposures in a camera This should only be called for cameras where exposure time is sequenceable cameraLabel the camera device label
        """
    def getExposureSequenceMaxLength(self, cameraLabel: str) -> int:
        """
        Gets the maximum length of a camera's exposure sequence. This should only be called for cameras where exposure time is sequenceable cameraLabel the camera device label
        """
    def loadExposureSequence(
        self, cameraLabel: str, exposureSequence_ms: Sequence[float]
    ) -> None:
        """
        Transfer a sequence of exposure times to the camera. This should only be called for cameras where exposure time is sequenceable cameraLabel the camera device label exposureTime_ms sequence of exposure times the camera will use during a sequence acquisition
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
        Sets the state (position) on the specific device. The command will fail if the device does not support states. deviceLabel the device label state the new state
        """
    def getState(self, stateDeviceLabel: str) -> int:
        """
        Returns the current state (position) on the specific device. The command will fail if the device does not support states. the current state deviceLabel the device label
        """
    def getNumberOfStates(self, stateDeviceLabel: str) -> int:
        """
        Returns the total number of available positions (states). For legacy reasons, an exception is not thrown on error. Instead, -1 is returned if deviceLabel is not a valid state device.
        """
    def setStateLabel(self, stateDeviceLabel: str, stateLabel: str) -> None:
        """
        Sets device state using the previously assigned label (string). deviceLabel the device label stateLabel the state label
        """
    def getStateLabel(self, stateDeviceLabel: str) -> str: ...
    def defineStateLabel(
        self, stateDeviceLabel: str, state: int, stateLabel: str
    ) -> None:
        """
        Defines a label for the specific state/ deviceLabel the device label state the state to be labeled label the label for the specified state
        """
    def getStateLabels(self, stateDeviceLabel: str) -> list[str]: ...
    def getStateFromLabel(self, stateDeviceLabel: str, stateLabel: str) -> int:
        """
        Obtain the state for a given label. the state (an integer) deviceLabel the device label stateLabel the label for which the state is being queried
        """
    @overload
    def setPosition(self, stageLabel: str, position: float) -> None:
        """
        Sets the position of the stage in microns. label the stage device label position the desired stage position, in microns
        """
    @overload
    def setPosition(self, position: float) -> None:
        """
        Sets the position of the stage in microns. Uses the current Z positioner (focus) device. position the desired stage position, in microns
        """
    @overload
    def getPosition(self, stageLabel: str) -> float:
        """
        Returns the current position of the stage in microns. the position in microns label the single-axis drive device label
        """
    @overload
    def getPosition(self) -> float:
        """
        Returns the current position of the stage in microns. Uses the current Z positioner (focus) device. the position in microns
        """
    @overload
    def setRelativePosition(self, stageLabel: str, d: float) -> None:
        """
        Sets the relative position of the stage in microns. label the single-axis drive device label d the amount to move the stage, in microns (positive or negative)
        """
    @overload
    def setRelativePosition(self, d: float) -> None:
        """
        Sets the relative position of the stage in microns. Uses the current Z positioner (focus) device. d the amount to move the stage, in microns (positive or negative)
        """
    @overload
    def setOrigin(self, stageLabel: str) -> None:
        """
        Zero the given focus/Z stage's coordinates at the current position. The current position becomes the new origin (Z = 0). Not to be confused with setAdapterOrigin(). label the stage device label
        """
    @overload
    def setOrigin(self) -> None:
        """
        Zero the current focus/Z stage's coordinates at the current position. The current position becomes the new origin (Z = 0). Not to be confused with setAdapterOrigin().
        """
    @overload
    def setAdapterOrigin(self, stageLabel: str, newZUm: float) -> None:
        """
        Enable software translation of coordinates for the given focus/Z stage. The current position of the stage becomes Z = newZUm. Only some stages support this functionality; it is recommended that setOrigin() be used instead where available. label the stage device label newZUm the new coordinate to assign to the current Z position
        """
    @overload
    def setAdapterOrigin(self, newZUm: float) -> None:
        """
        Enable software translation of coordinates for the current focus/Z stage. The current position of the stage becomes Z = newZUm. Only some stages support this functionality; it is recommended that setOrigin() be used instead where available. newZUm the new coordinate to assign to the current Z position
        """
    def setFocusDirection(self, stageLabel: str, sign: int) -> None:
        """
        Set the focus direction of a stage. The sign should be +1 (or any positive value), zero, or -1 (or any negative value), and is interpreted in the same way as the return value of getFocusDirection(). Once this method is called, getFocusDirection() for the stage will always return the set value. For legacy reasons, an exception is not thrown if there is an error. Instead, nothing is done if stageLabel is not a valid focus stage.
        """
    def getFocusDirection(self, stageLabel: str) -> int:
        """
        Get the focus direction of a stage. Returns +1 if increasing position brings objective closer to sample, -1 if increasing position moves objective away from sample, or 0 if unknown. (Make sure to check for zero!) The returned value is determined by the most recent call to setFocusDirection() for the stage, or defaults to what the stage device adapter declares (often 0, for unknown). An exception is thrown if the direction has not been set and the device encounters an error when determining the default direction.
        """
    def isStageSequenceable(self, stageLabel: str) -> bool:
        """
        Queries stage if it can be used in a sequence label the stage device label true if the stage can be sequenced
        """
    def isStageLinearSequenceable(self, stageLabel: str) -> bool:
        """
        Queries if the stage can be used in a linear sequence A linear sequence is defined by a stepsize and number of slices label the stage device label true if the stage supports linear sequences
        """
    def startStageSequence(self, stageLabel: str) -> None:
        """
        Starts an ongoing sequence of triggered events in a stage This should only be called for stages label the stage device label
        """
    def stopStageSequence(self, stageLabel: str) -> None:
        """
        Stops an ongoing sequence of triggered events in a stage This should only be called for stages that are sequenceable label the stage device label
        """
    def getStageSequenceMaxLength(self, stageLabel: str) -> int:
        """
        Gets the maximum length of a stage's position sequence. This should only be called for stages that are sequenceable label the stage device label the maximum length (integer)
        """
    def loadStageSequence(
        self, stageLabel: str, positionSequence: Sequence[float]
    ) -> None:
        """
        Transfer a sequence of events/states/whatever to the device This should only be called for device-properties that are sequenceable label the device label positionSequence a sequence of positions that the stage will execute in response to external triggers
        """
    def setStageLinearSequence(
        self, stageLabel: str, dZ_um: float, nSlices: int
    ) -> None:
        """
        Loads a linear sequence (defined by stepsize and nr. of steps) into the device. Why was it not called loadStageLinearSequence??? label Name of the stage device dZ_um Step size between slices in microns nSlices Number of slices fo ethis sequence Presumably the sequence will repeat after this number of TTLs was received
        """
    @overload
    def setXYPosition(self, xyStageLabel: str, x: float, y: float) -> None:
        """
        Sets the position of the XY stage in microns. label the XY stage device label x the X axis position in microns y the Y axis position in microns
        """
    @overload
    def setXYPosition(self, x: float, y: float) -> None:
        """
        Sets the position of the XY stage in microns. Uses the current XY stage device. x the X axis position in microns y the Y axis position in microns
        """
    @overload
    def setRelativeXYPosition(self, xyStageLabel: str, dx: float, dy: float) -> None:
        """
        Sets the relative position of the XY stage in microns. label the xy stage device label dx the distance to move in X (positive or negative) dy the distance to move in Y (positive or negative)
        """
    @overload
    def setRelativeXYPosition(self, dx: float, dy: float) -> None:
        """
        Sets the relative position of the XY stage in microns. Uses the current XY stage device. dx the distance to move in X (positive or negative) dy the distance to move in Y (positive or negative)
        """
    @overload
    def getXYPosition(self, xyStageLabel: str) -> tuple[float, float]: ...
    @overload
    def getXYPosition(self) -> tuple[float, float]: ...
    @overload
    def getXPosition(self, xyStageLabel: str) -> float:
        """
        Obtains the current position of the X axis of the XY stage in microns. the x position label the stage device label
        """
    @overload
    def getXPosition(self) -> float:
        """
        Obtains the current position of the X axis of the XY stage in microns. Uses the current XY stage device. the x position label the stage device label
        """
    @overload
    def getYPosition(self, xyStageLabel: str) -> float:
        """
        Obtains the current position of the Y axis of the XY stage in microns. the y position label the stage device label
        """
    @overload
    def getYPosition(self) -> float:
        """
        Obtains the current position of the Y axis of the XY stage in microns. Uses the current XY stage device. the y position label the stage device label
        """
    def stop(self, xyOrZStageLabel: str) -> None:
        """
        Stop the XY or focus/Z stage motors Not all stages support this operation; check before use. label the stage device label (either XY or focus/Z stage)
        """
    def home(self, xyOrZStageLabel: str) -> None:
        """
        Perform a hardware homing operation for an XY or focus/Z stage. Not all stages support this operation. The user should be warned before calling this method, as it can cause large stage movements, potentially resulting in collision (e.g. with an expensive objective lens). label the stage device label (either XY or focus/Z stage)
        """
    @overload
    def setOriginXY(self, xyStageLabel: str) -> None:
        """
        Zero the given XY stage's coordinates at the current position. The current position becomes the new origin. Not to be confused with setAdapterOriginXY(). label the stage device label
        """
    @overload
    def setOriginXY(self) -> None:
        """
        Zero the current XY stage's coordinates at the current position. The current position becomes the new origin. Not to be confused with setAdapterOriginXY().
        """
    @overload
    def setOriginX(self, xyStageLabel: str) -> None:
        """
        Zero the given XY stage's X coordinate at the current position. The current position becomes the new X = 0. label the xy stage device label
        """
    @overload
    def setOriginX(self) -> None:
        """
        Zero the given XY stage's X coordinate at the current position. The current position becomes the new X = 0.
        """
    @overload
    def setOriginY(self, xyStageLabel: str) -> None:
        """
        Zero the given XY stage's Y coordinate at the current position. The current position becomes the new Y = 0. label the xy stage device label
        """
    @overload
    def setOriginY(self) -> None:
        """
        Zero the given XY stage's Y coordinate at the current position. The current position becomes the new Y = 0.
        """
    @overload
    def setAdapterOriginXY(
        self, xyStageLabel: str, newXUm: float, newYUm: float
    ) -> None:
        """
        Enable software translation of coordinates for the given XY stage. The current position of the stage becomes (newXUm, newYUm). It is recommended that setOriginXY() be used instead where available. label the XY stage device label newXUm the new coordinate to assign to the current X position newYUm the new coordinate to assign to the current Y position
        """
    @overload
    def setAdapterOriginXY(self, newXUm: float, newYUm: float) -> None:
        """
        Enable software translation of coordinates for the current XY stage. The current position of the stage becomes (newXUm, newYUm). It is recommended that setOriginXY() be used instead where available. newXUm the new coordinate to assign to the current X position newYUm the new coordinate to assign to the current Y position
        """
    def isXYStageSequenceable(self, xyStageLabel: str) -> bool:
        """
        Queries XY stage if it can be used in a sequence label the XY stage device label
        """
    def startXYStageSequence(self, xyStageLabel: str) -> None:
        """
        Starts an ongoing sequence of triggered events in an XY stage This should only be called for stages label the XY stage device label
        """
    def stopXYStageSequence(self, xyStageLabel: str) -> None:
        """
        Stops an ongoing sequence of triggered events in an XY stage This should only be called for stages that are sequenceable label the XY stage device label
        """
    def getXYStageSequenceMaxLength(self, xyStageLabel: str) -> int:
        """
        Gets the maximum length of an XY stage's position sequence. This should only be called for XY stages that are sequenceable label the XY stage device label the maximum allowed sequence length
        """
    def loadXYStageSequence(
        self, xyStageLabel: str, xSequence: Sequence[float], ySequence: Sequence[float]
    ) -> None:
        """
        Transfer a sequence of stage positions to the xy stage. xSequence and ySequence must have the same length. This should only be called for XY stages that are sequenceable label the XY stage device label xSequence the sequence of x positions that the stage will execute in response to external triggers ySequence the sequence of y positions that the stage will execute in response to external triggers
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
    def getSerialPortAnswer(self, portLabel: str, term: str) -> str: ...
    def writeToSerialPort(self, portLabel: str, data: Sequence[str]) -> None:
        """
        Sends an array of characters to the serial port and returns immediately.
        """
    def readFromSerialPort(self, portLabel: str) -> list[str]: ...
    def setSLMImage(
        self, slmLabel: str, pixels: Annotated[ArrayLike, {"dtype": "uint8"}]
    ) -> None: ...
    @overload
    def setSLMPixelsTo(self, slmLabel: str, intensity: int) -> None:
        """Set all SLM pixels to a single 8-bit intensity."""
    @overload
    def setSLMPixelsTo(self, slmLabel: str, red: int, green: int, blue: int) -> None:
        """Set all SLM pixels to an RGB color."""
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
        """Returns the width (in "pixels") of the SLM deviceLabel name of the SLM"""
    def getSLMHeight(self, slmLabel: str) -> int:
        """
        Returns the height (in "pixels") of the SLM deviceLabel name of the SLM
        """
    def getSLMNumberOfComponents(self, slmLabel: str) -> int:
        """
        Returns the number of components (usually these depict colors) of the SLM For instance, an RGB projector will return 3, but a grey scale SLM returns 1 deviceLabel name of the SLM
        """
    def getSLMBytesPerPixel(self, slmLabel: str) -> int:
        """Returns the number of bytes per SLM pixel deviceLabel name of the SLM"""
    def getSLMSequenceMaxLength(self, slmLabel: str) -> int:
        """
        For SLMs that support sequences, returns the maximum length of the sequence that can be uploaded to the device deviceLabel name of the SLM
        """
    def startSLMSequence(self, slmLabel: str) -> None:
        """
        Starts the sequence previously uploaded to the SLM deviceLabel name of the SLM
        """
    def stopSLMSequence(self, slmLabel: str) -> None:
        """
        Stops the SLM sequence if previously started deviceLabel name of the SLM
        """
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
    def getGalvoChannel(self, galvoLabel: str) -> str: ...
    def pressurePumpStop(self, pumpLabel: str) -> None:
        """Stops the pressure pump"""
    def pressurePumpCalibrate(self, pumpLabel: str) -> None:
        """Calibrates the pump"""
    def pressurePumpRequiresCalibration(self, pumpLabel: str) -> bool:
        """Returns boolean whether the pump is operational before calibration"""
    def setPumpPressureKPa(self, pumpLabel: str, pressure: float) -> None:
        """Sets the pressure of the pump in kPa"""
    def getPumpPressureKPa(self, pumpLabel: str) -> float:
        """Gets the pressure of the pump in kPa"""
    def volumetricPumpStop(self, pumpLabel: str) -> None:
        """Stops the volumetric pump"""
    def volumetricPumpHome(self, pumpLabel: str) -> None:
        """Homes the pump"""
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
        Return whether or not the device supports automatic device detection (i.e. whether or not detectDevice() may be safely called). For legacy reasons, an exception is not thrown if there is an error. Instead, false is returned if label is not a valid device.
        """
    def detectDevice(self, deviceLabel: str) -> DeviceDetectionStatus: ...
    def getParentLabel(self, peripheralLabel: str) -> str: ...
    def setParentLabel(self, deviceLabel: str, parentHubLabel: str) -> None:
        """Sets parent device label"""
    def getInstalledDevices(self, hubLabel: str) -> list[str]: ...
    def getInstalledDeviceDescription(
        self, hubLabel: str, peripheralLabel: str
    ) -> str: ...
    def getLoadedPeripheralDevices(self, hubLabel: str) -> list[str]: ...
