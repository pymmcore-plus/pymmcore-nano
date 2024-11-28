from typing import Any
from collections.abc import Sequence
import enum
from typing import overload

class CMMCore:
    def __init__(self) -> None: ...
    def loadSystemConfiguration(self, fileName: object) -> None: ...
    def saveSystemConfiguration(self, fileName: str) -> None: ...
    @staticmethod
    def enableFeature(name: str, enable: bool) -> None: ...
    @staticmethod
    def isFeatureEnabled(name: str) -> bool: ...
    def loadDevice(self, label: str, moduleName: str, deviceName: str) -> None: ...
    def unloadDevice(self, label: str) -> None: ...
    def unloadAllDevices(self) -> None: ...
    def initializeAllDevices(self) -> None: ...
    def initializeDevice(self, label: str) -> None: ...
    def getDeviceInitializationState(self, label: str) -> DeviceInitializationState: ...
    def reset(self) -> None: ...
    def unloadLibrary(self, moduleName: str) -> None: ...
    def updateCoreProperties(self) -> None: ...
    def getCoreErrorText(self, code: int) -> str: ...
    def getVersionInfo(self) -> str: ...
    def getAPIVersionInfo(self) -> str: ...
    def getSystemState(self) -> Configuration: ...
    def setSystemState(self, conf: Configuration) -> None: ...
    def getConfigState(self, group: str, config: str) -> Configuration: ...
    def getConfigGroupState(self, group: str) -> Configuration: ...
    def saveSystemState(self, fileName: str) -> None: ...
    def loadSystemState(self, fileName: str) -> None: ...
    def registerCallback(self, cb: MMEventCallback) -> None: ...
    def setPrimaryLogFile(self, filename: str, truncate: bool = False) -> None: ...
    def getPrimaryLogFile(self) -> str: ...
    @overload
    def logMessage(self, msg: str) -> None: ...
    @overload
    def logMessage(self, msg: str, debugOnly: bool) -> None: ...
    def enableDebugLog(self, enable: bool) -> None: ...
    def debugLogEnabled(self) -> bool: ...
    def enableStderrLog(self, enable: bool) -> None: ...
    def stderrLogEnabled(self) -> bool: ...
    def startSecondaryLogFile(
        self,
        filename: str,
        enableDebug: bool,
        truncate: bool = True,
        synchronous: bool = False,
    ) -> int: ...
    def stopSecondaryLogFile(self, handle: int) -> None: ...
    def getDeviceAdapterSearchPaths(self) -> list[str]: ...
    def setDeviceAdapterSearchPaths(self, paths: Sequence[str]) -> None: ...
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
    def hasProperty(self, label: str, propName: str) -> bool: ...
    def getProperty(self, label: str, propName: str) -> str: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: str) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: bool) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: int) -> None: ...
    @overload
    def setProperty(self, label: str, propName: str, propValue: float) -> None: ...
    def getAllowedPropertyValues(self, label: str, propName: str) -> list[str]: ...
    def isPropertyReadOnly(self, label: str, propName: str) -> bool: ...
    def isPropertyPreInit(self, label: str, propName: str) -> bool: ...
    def isPropertySequenceable(self, label: str, propName: str) -> bool: ...
    def hasPropertyLimits(self, label: str, propName: str) -> bool: ...
    def getPropertyLowerLimit(self, label: str, propName: str) -> float: ...
    def getPropertyUpperLimit(self, label: str, propName: str) -> float: ...
    def getPropertyType(self, label: str, propName: str) -> PropertyType: ...
    def startPropertySequence(self, label: str, propName: str) -> None: ...
    def stopPropertySequence(self, label: str, propName: str) -> None: ...
    def getPropertySequenceMaxLength(self, label: str, propName: str) -> int: ...
    def loadPropertySequence(
        self, label: str, propName: str, eventSequence: Sequence[str]
    ) -> None: ...
    def deviceBusy(self, label: str) -> bool: ...
    def waitForDevice(self, label: str) -> None: ...
    def waitForConfig(self, group: str, configName: str) -> None: ...
    def systemBusy(self) -> bool: ...
    def waitForSystem(self) -> None: ...
    def deviceTypeBusy(self, devType: DeviceType) -> bool: ...
    def waitForDeviceType(self, devType: DeviceType) -> None: ...
    def getDeviceDelayMs(self, label: str) -> float: ...
    def setDeviceDelayMs(self, label: str, delayMs: float) -> None: ...
    def usesDeviceDelay(self, label: str) -> bool: ...
    def setTimeoutMs(self, timeoutMs: int) -> None: ...
    def getTimeoutMs(self) -> int: ...
    def sleep(self, intervalMs: float) -> None: ...
    def getCameraDevice(self) -> str: ...
    def getShutterDevice(self) -> str: ...
    def getFocusDevice(self) -> str: ...
    def getXYStageDevice(self) -> str: ...
    def getAutoFocusDevice(self) -> str: ...
    def getImageProcessorDevice(self) -> str: ...
    def getSLMDevice(self) -> str: ...
    def getGalvoDevice(self) -> str: ...
    def getChannelGroup(self) -> str: ...
    def setCameraDevice(self, cameraLabel: str) -> None: ...
    def setShutterDevice(self, shutterLabel: str) -> None: ...
    def setFocusDevice(self, focusLabel: str) -> None: ...
    def setXYStageDevice(self, xyStageLabel: str) -> None: ...
    def setAutoFocusDevice(self, focusLabel: str) -> None: ...
    def setImageProcessorDevice(self, procLabel: str) -> None: ...
    def setSLMDevice(self, slmLabel: str) -> None: ...
    def setGalvoDevice(self, galvoLabel: str) -> None: ...
    def setChannelGroup(self, channelGroup: str) -> None: ...
    def getSystemStateCache(self) -> Configuration: ...
    def updateSystemStateCache(self) -> None: ...
    def getPropertyFromCache(self, deviceLabel: str, propName: str) -> str: ...
    def getCurrentConfigFromCache(self, groupName: str) -> str: ...
    def getConfigGroupStateFromCache(self, group: str) -> Configuration: ...
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
    def defineConfigGroup(self, groupName: str) -> None: ...
    def deleteConfigGroup(self, groupName: str) -> None: ...
    def renameConfigGroup(self, oldGroupName: str, newGroupName: str) -> None: ...
    def isGroupDefined(self, groupName: str) -> bool: ...
    def isConfigDefined(self, groupName: str, configName: str) -> bool: ...
    def setConfig(self, groupName: str, configName: str) -> None: ...
    @overload
    def deleteConfig(self, groupName: str, configName: str) -> None: ...
    @overload
    def deleteConfig(
        self, groupName: str, configName: str, deviceLabel: str, propName: str
    ) -> None: ...
    def renameConfig(
        self, groupName: str, oldConfigName: str, newConfigName: str
    ) -> None: ...
    def getAvailableConfigGroups(self) -> list[str]: ...
    def getAvailableConfigs(self, configGroup: str) -> list[str]: ...
    def getCurrentConfig(self, groupName: str) -> str: ...
    def getConfigData(self, configGroup: str, configName: str) -> Configuration: ...
    @overload
    def getCurrentPixelSizeConfig(self) -> str: ...
    @overload
    def getCurrentPixelSizeConfig(self, cached: bool) -> str: ...
    @overload
    def getPixelSizeUm(self) -> float: ...
    @overload
    def getPixelSizeUm(self, cached: bool) -> float: ...
    def getPixelSizeUmByID(self, resolutionID: str) -> float: ...
    @overload
    def getPixelSizeAffine(self) -> list[float]: ...
    @overload
    def getPixelSizeAffine(self, cached: bool) -> list[float]: ...
    def getPixelSizeAffineByID(self, resolutionID: str) -> list[float]: ...
    def getMagnificationFactor(self) -> float: ...
    def setPixelSizeUm(self, resolutionID: str, pixSize: float) -> None: ...
    def setPixelSizeAffine(
        self, resolutionID: str, affine: Sequence[float]
    ) -> None: ...
    @overload
    def definePixelSizeConfig(
        self, resolutionID: str, deviceLabel: str, propName: str, value: str
    ) -> None: ...
    @overload
    def definePixelSizeConfig(self, resolutionID: str) -> None: ...
    def getAvailablePixelSizeConfigs(self) -> list[str]: ...
    def isPixelSizeConfigDefined(self, resolutionID: str) -> bool: ...
    def setPixelSizeConfig(self, resolutionID: str) -> None: ...
    def renamePixelSizeConfig(self, oldConfigName: str, newConfigName: str) -> None: ...
    def deletePixelSizeConfig(self, configName: str) -> None: ...
    def getPixelSizeConfigData(self, configName: str) -> Configuration: ...
    @overload
    def setROI(self, x: int, y: int, xSize: int, ySize: int) -> None: ...
    @overload
    def setROI(self, label: str, x: int, y: int, xSize: int, ySize: int) -> None: ...
    @overload
    def getROI(self) -> tuple[int, int, int, int]: ...
    @overload
    def getROI(self, label: str) -> tuple[int, int, int, int]: ...
    def clearROI(self) -> None: ...
    def isMultiROISupported(self) -> bool: ...
    def isMultiROIEnabled(self) -> bool: ...
    def setMultiROI(
        self,
        xs: Sequence[int],
        ys: Sequence[int],
        widths: Sequence[int],
        heights: Sequence[int],
    ) -> None: ...
    def getMultiROI(
        self,
        xs: Sequence[int],
        ys: Sequence[int],
        widths: Sequence[int],
        heights: Sequence[int],
    ) -> None: ...
    @overload
    def setExposure(self, exp: float) -> None: ...
    @overload
    def setExposure(self, cameraLabel: str, dExp: float) -> None: ...
    @overload
    def getExposure(self) -> float: ...
    @overload
    def getExposure(self, label: str) -> float: ...
    def snapImage(self) -> None: ...
    @overload
    def getImage(self) -> Any: ...
    @overload
    def getImage(self, numChannel: int) -> Any: ...
    def getImageWidth(self) -> int: ...
    def getImageHeight(self) -> int: ...
    def getBytesPerPixel(self) -> int: ...
    def getImageBitDepth(self) -> int: ...
    def getNumberOfComponents(self) -> int: ...
    def getNumberOfCameraChannels(self) -> int: ...
    def getCameraChannelName(self, channelNr: int) -> str: ...
    def getImageBufferSize(self) -> int: ...
    def setAutoShutter(self, state: bool) -> None: ...
    def getAutoShutter(self) -> bool: ...
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
    def prepareSequenceAcquisition(self, cameraLabel: str) -> None: ...
    def startContinuousSequenceAcquisition(self, intervalMs: float) -> None: ...
    @overload
    def stopSequenceAcquisition(self) -> None: ...
    @overload
    def stopSequenceAcquisition(self, cameraLabel: str) -> None: ...
    @overload
    def isSequenceRunning(self) -> bool: ...
    @overload
    def isSequenceRunning(self, cameraLabel: str) -> bool: ...
    def getLastImage(self) -> Any: ...
    def popNextImage(self) -> Any: ...
    def getLastImageMD(self, md: Metadata) -> Any: ...
    def getNBeforeLastImageMD(self, n: int, md: Metadata) -> Any: ...
    def getRemainingImageCount(self) -> int: ...
    def getBufferTotalCapacity(self) -> int: ...
    def getBufferFreeCapacity(self) -> int: ...
    def isBufferOverflowed(self) -> bool: ...
    def setCircularBufferMemoryFootprint(self, sizeMB: int) -> None: ...
    def getCircularBufferMemoryFootprint(self) -> int: ...
    def initializeCircularBuffer(self) -> None: ...
    def clearCircularBuffer(self) -> None: ...
    def isExposureSequenceable(self, cameraLabel: str) -> bool: ...
    def startExposureSequence(self, cameraLabel: str) -> None: ...
    def stopExposureSequence(self, cameraLabel: str) -> None: ...
    def getExposureSequenceMaxLength(self, cameraLabel: str) -> int: ...
    def loadExposureSequence(
        self, cameraLabel: str, exposureSequence_ms: Sequence[float]
    ) -> None: ...
    def getLastFocusScore(self) -> float: ...
    def getCurrentFocusScore(self) -> float: ...
    def enableContinuousFocus(self, enable: bool) -> None: ...
    def isContinuousFocusEnabled(self) -> bool: ...
    def isContinuousFocusLocked(self) -> bool: ...
    def isContinuousFocusDrive(self, stageLabel: str) -> bool: ...
    def fullFocus(self) -> None: ...
    def incrementalFocus(self) -> None: ...
    def setAutoFocusOffset(self, offset: float) -> None: ...
    def getAutoFocusOffset(self) -> float: ...
    def setState(self, stateDeviceLabel: str, state: int) -> None: ...
    def getState(self, stateDeviceLabel: str) -> int: ...
    def getNumberOfStates(self, stateDeviceLabel: str) -> int: ...
    def setStateLabel(self, stateDeviceLabel: str, stateLabel: str) -> None: ...
    def getStateLabel(self, stateDeviceLabel: str) -> str: ...
    def defineStateLabel(
        self, stateDeviceLabel: str, state: int, stateLabel: str
    ) -> None: ...
    def getStateLabels(self, stateDeviceLabel: str) -> list[str]: ...
    def getStateFromLabel(self, stateDeviceLabel: str, stateLabel: str) -> int: ...
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
    def setFocusDirection(self, stageLabel: str, sign: int) -> None: ...
    def getFocusDirection(self, stageLabel: str) -> int: ...
    def isStageSequenceable(self, stageLabel: str) -> bool: ...
    def isStageLinearSequenceable(self, stageLabel: str) -> bool: ...
    def startStageSequence(self, stageLabel: str) -> None: ...
    def stopStageSequence(self, stageLabel: str) -> None: ...
    def getStageSequenceMaxLength(self, stageLabel: str) -> int: ...
    def loadStageSequence(
        self, stageLabel: str, positionSequence: Sequence[float]
    ) -> None: ...
    def setStageLinearSequence(
        self, stageLabel: str, dZ_um: float, nSlices: int
    ) -> None: ...
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
    def getXYPosition(
        self, xyStageLabel: str, x_stage: float, y_stage: float
    ) -> None: ...
    @overload
    def getXYPosition(self, x_stage: float, y_stage: float) -> None: ...
    @overload
    def getXPosition(self, xyStageLabel: str) -> float: ...
    @overload
    def getXPosition(self) -> float: ...
    @overload
    def getYPosition(self, xyStageLabel: str) -> float: ...
    @overload
    def getYPosition(self) -> float: ...
    def stop(self, xyOrZStageLabel: str) -> None: ...
    def home(self, xyOrZStageLabel: str) -> None: ...
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
    def isXYStageSequenceable(self, xyStageLabel: str) -> bool: ...
    def startXYStageSequence(self, xyStageLabel: str) -> None: ...
    def stopXYStageSequence(self, xyStageLabel: str) -> None: ...
    def getXYStageSequenceMaxLength(self, xyStageLabel: str) -> int: ...
    def loadXYStageSequence(
        self, xyStageLabel: str, xSequence: Sequence[float], ySequence: Sequence[float]
    ) -> None: ...
    def setSerialProperties(
        self,
        portName: str,
        answerTimeout: str,
        baudRate: str,
        delayBetweenCharsMs: str,
        handshaking: str,
        parity: str,
        stopBits: str,
    ) -> None: ...
    def setSerialPortCommand(self, portLabel: str, command: str, term: str) -> None: ...
    def getSerialPortAnswer(self, portLabel: str, term: str) -> str: ...
    def writeToSerialPort(self, portLabel: str, data: Sequence[str]) -> None: ...
    def readFromSerialPort(self, portLabel: str) -> list[str]: ...
    def setSLMImage(self, slmLabel: str, pixels: int) -> None: ...
    @overload
    def setSLMPixelsTo(self, slmLabel: str, intensity: int) -> None: ...
    @overload
    def setSLMPixelsTo(
        self, slmLabel: str, red: int, green: int, blue: int
    ) -> None: ...
    def displaySLMImage(self, slmLabel: str) -> None: ...
    def setSLMExposure(self, slmLabel: str, exposure_ms: float) -> None: ...
    def getSLMExposure(self, slmLabel: str) -> float: ...
    def getSLMWidth(self, slmLabel: str) -> int: ...
    def getSLMHeight(self, slmLabel: str) -> int: ...
    def getSLMNumberOfComponents(self, slmLabel: str) -> int: ...
    def getSLMBytesPerPixel(self, slmLabel: str) -> int: ...
    def getSLMSequenceMaxLength(self, slmLabel: str) -> int: ...
    def startSLMSequence(self, slmLabel: str) -> None: ...
    def stopSLMSequence(self, slmLabel: str) -> None: ...
    def pointGalvoAndFire(
        self, galvoLabel: str, x: float, y: float, pulseTime_us: float
    ) -> None: ...
    def setGalvoSpotInterval(self, galvoLabel: str, pulseTime_us: float) -> None: ...
    def setGalvoPosition(self, galvoLabel: str, x: float, y: float) -> None: ...
    def getGalvoPosition(self, arg: str, /) -> tuple[float, float]: ...
    def setGalvoIlluminationState(self, galvoLabel: str, on: bool) -> None: ...
    def getGalvoXRange(self, galvoLabel: str) -> float: ...
    def getGalvoXMinimum(self, galvoLabel: str) -> float: ...
    def getGalvoYRange(self, galvoLabel: str) -> float: ...
    def getGalvoYMinimum(self, galvoLabel: str) -> float: ...
    def addGalvoPolygonVertex(
        self, galvoLabel: str, polygonIndex: int, x: float, y: float
    ) -> None:
        """Add a vertex to a galvo polygon."""
    def deleteGalvoPolygons(self, galvoLabel: str) -> None: ...
    def loadGalvoPolygons(self, galvoLabel: str) -> None: ...
    def setGalvoPolygonRepetitions(self, galvoLabel: str, repetitions: int) -> None: ...
    def runGalvoPolygons(self, galvoLabel: str) -> None: ...
    def runGalvoSequence(self, galvoLabel: str) -> None: ...
    def getGalvoChannel(self, galvoLabel: str) -> str: ...
    def supportsDeviceDetection(self, deviceLabel: str) -> bool: ...
    def detectDevice(self, deviceLabel: str) -> DeviceDetectionStatus: ...
    def getParentLabel(self, peripheralLabel: str) -> str: ...
    def setParentLabel(self, deviceLabel: str, parentHubLabel: str) -> None: ...
    def getInstalledDevices(self, hubLabel: str) -> list[str]: ...
    def getInstalledDeviceDescription(
        self, hubLabel: str, peripheralLabel: str
    ) -> str: ...
    def getLoadedPeripheralDevices(self, hubLabel: str) -> list[str]: ...

class Configuration:
    def __init__(self) -> None: ...

DEVICE_INTERFACE_VERSION: int = 71

class DeviceDetectionStatus(enum.IntEnum):
    Misconfigured = -1
    Unimplemented = -2
    CanNotCommunicate = 0
    CanCommunicate = 1

class DeviceInitializationState(enum.IntEnum):
    CoreIdle = 0
    CoreBusy = 1
    CoreError = 2

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

class FocusDirection(enum.IntEnum):
    FocusDirectionUnknown = 0
    FocusDirectionTowardSample = 1
    FocusDirectionAwayFromSample = 2

class MMEventCallback:
    def __init__(self) -> None: ...

class Metadata:
    def __init__(self) -> None: ...

class PortType(enum.IntEnum):
    InvalidPort = 0
    SerialPort = 1
    USBPort = 2
    HIDPort = 3

class PropertyType(enum.IntEnum):
    Undef = 0
    String = 1
    Float = 2
    Integer = 3
