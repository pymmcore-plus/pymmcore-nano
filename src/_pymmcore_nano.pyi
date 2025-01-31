from collections.abc import Sequence
import enum
from typing import Annotated, overload
from numpy.typing import ArrayLike

class ActionType(enum.IntEnum):
    NoAction = 0
    BeforeGet = 1
    AfterSet = 2
    IsSequenceable = 3
    AfterLoadSequence = 4
    StartSequence = 5
    StopSequence = 6

AfterLoadSequence: int = 4
AfterSet: int = 2
AnyType: int = 1
Attention: int = 0
AutoFocusDevice: int = 9
BeforeGet: int = 1

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
    def setPrimaryLogFile(self, filename: object, truncate: bool = False) -> None: ...
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
        filename: object,
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
    def getMultiROI(self) -> tuple[list[int], list[int], list[int], list[int]]: ...
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
    def getImage(self) -> Annotated[ArrayLike, dict(writable=False)]: ...
    @overload
    def getImage(self, arg: int, /) -> Annotated[ArrayLike, dict(writable=False)]: ...
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
    def getLastImage(self) -> Annotated[ArrayLike, dict(writable=False)]: ...
    def popNextImage(self) -> Annotated[ArrayLike, dict(writable=False)]: ...
    @overload
    def getLastImageMD(
        self,
    ) -> tuple[Annotated[ArrayLike, dict(writable=False)], Metadata]:
        """
        Get the last image in the circular buffer, return as tuple of image and metadata
        """
    @overload
    def getLastImageMD(
        self, md: Metadata
    ) -> Annotated[ArrayLike, dict(writable=False)]:
        """
        Get the last image in the circular buffer, store metadata in the provided object
        """
    @overload
    def getLastImageMD(
        self, channel: int, slice: int
    ) -> tuple[Annotated[ArrayLike, dict(writable=False)], Metadata]:
        """
        Get the last image in the circular buffer for a specific channel and slice, returnas tuple of image and metadata
        """
    @overload
    def getLastImageMD(
        self, channel: int, slice: int, md: Metadata
    ) -> Annotated[ArrayLike, dict(writable=False)]:
        """
        Get the last image in the circular buffer for a specific channel and slice, store metadata in the provided object
        """
    @overload
    def popNextImageMD(
        self,
    ) -> tuple[Annotated[ArrayLike, dict(writable=False)], Metadata]:
        """
        Get the last image in the circular buffer, return as tuple of image and metadata
        """
    @overload
    def popNextImageMD(
        self, md: Metadata
    ) -> Annotated[ArrayLike, dict(writable=False)]:
        """
        Get the last image in the circular buffer, store metadata in the provided object
        """
    @overload
    def popNextImageMD(
        self, channel: int, slice: int
    ) -> tuple[Annotated[ArrayLike, dict(writable=False)], Metadata]:
        """
        Get the last image in the circular buffer for a specific channel and slice, returnas tuple of image and metadata
        """
    @overload
    def popNextImageMD(
        self, channel: int, slice: int, md: Metadata
    ) -> Annotated[ArrayLike, dict(writable=False)]:
        """
        Get the last image in the circular buffer for a specific channel and slice, store metadata in the provided object
        """
    @overload
    def getNBeforeLastImageMD(
        self, n: int
    ) -> tuple[Annotated[ArrayLike, dict(writable=False)], Metadata]:
        """
        Get the nth image before the last image in the circular buffer and return it as a tuple of image and metadata
        """
    @overload
    def getNBeforeLastImageMD(
        self, n: int, md: Metadata
    ) -> Annotated[ArrayLike, dict(writable=False)]:
        """
        Get the nth image before the last image in the circular buffer and store the metadata in the provided object
        """
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
    def setSLMImage(
        self, slmLabel: str, pixels: Annotated[ArrayLike, dict(dtype="uint8")]
    ) -> None: ...
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
    def loadSLMSequence(
        self, slmLabel: str, pixels: Sequence[Annotated[ArrayLike, dict(dtype="uint8")]]
    ) -> None: ...
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

class CMMError(RuntimeError):
    pass

CameraDevice: int = 2
CanCommunicate: int = 1
CanNotCommunicate: int = 0

class Configuration:
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

CoreDevice: int = 10
DEVICE_BUFFER_OVERFLOW: int = 22
DEVICE_CAMERA_BUSY_ACQUIRING: int = 30
DEVICE_CAN_NOT_SET_PROPERTY: int = 32
DEVICE_COMM_HUB_MISSING: int = 36
DEVICE_CORE_CHANNEL_PRESETS_FAILED: int = 33
DEVICE_CORE_CONFIG_FAILED: int = 29
DEVICE_CORE_EXPOSURE_FAILED: int = 28
DEVICE_CORE_FOCUS_STAGE_UNDEF: int = 27
DEVICE_DUPLICATE_LABEL: int = 20
DEVICE_DUPLICATE_LIBRARY: int = 37
DEVICE_DUPLICATE_PROPERTY: int = 4
DEVICE_ERR: int = 1
DEVICE_IMAGE_PARAMS_FAILED: int = 26
DEVICE_INCOMPATIBLE_IMAGE: int = 31
DEVICE_INTERFACE_VERSION: int = 71
DEVICE_INTERNAL_INCONSISTENCY: int = 8
DEVICE_INVALID_INPUT_PARAM: int = 21
DEVICE_INVALID_PROPERTY: int = 2
DEVICE_INVALID_PROPERTY_LIMITS: int = 24
DEVICE_INVALID_PROPERTY_LIMTS: int = 24
DEVICE_INVALID_PROPERTY_TYPE: int = 5
DEVICE_INVALID_PROPERTY_VALUE: int = 3
DEVICE_LOCALLY_DEFINED_ERROR: int = 34
DEVICE_NATIVE_MODULE_FAILED: int = 6
DEVICE_NONEXISTENT_CHANNEL: int = 23
DEVICE_NOT_CONNECTED: int = 35
DEVICE_NOT_SUPPORTED: int = 9
DEVICE_NOT_YET_IMPLEMENTED: int = 41
DEVICE_NO_CALLBACK_REGISTERED: int = 13
DEVICE_NO_PROPERTY_DATA: int = 19
DEVICE_OK: int = 0
DEVICE_OUT_OF_MEMORY: int = 40
DEVICE_PROPERTY_NOT_SEQUENCEABLE: int = 38
DEVICE_SELF_REFERENCE: int = 18
DEVICE_SEQUENCE_TOO_LARGE: int = 39
DEVICE_SERIAL_BUFFER_OVERRUN: int = 15
DEVICE_SERIAL_COMMAND_FAILED: int = 14
DEVICE_SERIAL_INVALID_RESPONSE: int = 16
DEVICE_SERIAL_TIMEOUT: int = 17
DEVICE_SNAP_IMAGE_FAILED: int = 25
DEVICE_UNKNOWN_LABEL: int = 10
DEVICE_UNKNOWN_POSITION: int = 12
DEVICE_UNSUPPORTED_COMMAND: int = 11
DEVICE_UNSUPPORTED_DATA_FORMAT: int = 7

class DeviceDetectionStatus(enum.IntEnum):
    Unimplemented = -2
    Misconfigured = -1
    CanNotCommunicate = 0
    CanCommunicate = 1

class DeviceInitializationState(enum.IntEnum):
    Uninitialized = 0
    InitializedSuccessfully = 1
    InitializationFailed = 2

class DeviceNotification(enum.IntEnum):
    Attention = 0
    Done = 1
    StatusChanged = 2

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

Done: int = 1
Float: int = 2

class FocusDirection(enum.IntEnum):
    FocusDirectionUnknown = 0
    FocusDirectionTowardSample = 1
    FocusDirectionAwayFromSample = 2

FocusDirectionAwayFromSample: int = 2
FocusDirectionTowardSample: int = 1
FocusDirectionUnknown: int = 0
GalvoDevice: int = 16
GenericDevice: int = 8
HIDPort: int = 3
HubDevice: int = 15
ImageProcessorDevice: int = 11
InitializationFailed: int = 2
InitializedSuccessfully: int = 1
Integer: int = 3
InvalidPort: int = 0
IsSequenceable: int = 3
MMCore_version: str = "11.3.0"
MMCore_version_info: tuple = (11, 3, 0)

class MMEventCallback:
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
    def onSLMExposureChanged(self, name: str, newExposure: float) -> None:
        """Called when the SLM exposure changes"""
    def onExposureChanged(self, name: str, newExposure: float) -> None:
        """Called when the exposure changes"""
    def onStagePositionChanged(self, name: str, pos: float) -> None:
        """Called when the stage position changes"""
    def onXYStagePositionChanged(self, name: str, xpos: float, ypos: float) -> None:
        """Called when the XY stage position changes"""

MM_CODE_ERR: int = 1
MM_CODE_OK: int = 0
MODULE_INTERFACE_VERSION: int = 10
MagnifierDevice: int = 13

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

class MetadataIndexError(IndexError):
    pass

class MetadataKeyError(KeyError):
    pass

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

Misconfigured: int = -1
NoAction: int = 0
PYMMCORE_NANO_VERSION: str = "0"

class PortType(enum.IntEnum):
    InvalidPort = 0
    SerialPort = 1
    USBPort = 2
    HIDPort = 3

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

class PropertyType(enum.IntEnum):
    Undef = 0
    String = 1
    Float = 2
    Integer = 3

SLMDevice: int = 14
SerialDevice: int = 7
SerialPort: int = 1
ShutterDevice: int = 3
SignalIODevice: int = 12
StageDevice: int = 5
StartSequence: int = 5
StateDevice: int = 4
StatusChanged: int = 2
StopSequence: int = 6
String: int = 1
USBPort: int = 2
Undef: int = 0
Unimplemented: int = -2
Uninitialized: int = 0
UnknownType: int = 0
XYStageDevice: int = 6
g_CFGCommand_ConfigGroup: str = "ConfigGroup"
g_CFGCommand_ConfigPixelSize: str = "ConfigPixelSize"
g_CFGCommand_Configuration: str = "Config"
g_CFGCommand_Delay: str = "Delay"
g_CFGCommand_Device: str = "Device"
g_CFGCommand_Equipment: str = "Equipment"
g_CFGCommand_FocusDirection: str = "FocusDirection"
g_CFGCommand_ImageSynchro: str = "ImageSynchro"
g_CFGCommand_Label: str = "Label"
g_CFGCommand_ParentID: str = "Parent"
g_CFGCommand_PixelSizeAffine: str = "PixelSizeAffine"
g_CFGCommand_PixelSize_um: str = "PixelSize_um"
g_CFGCommand_Property: str = "Property"
g_CFGGroup_PixelSizeUm: str = "PixelSize_um"
g_CFGGroup_System: str = "System"
g_CFGGroup_System_Shutdown: str = "Shutdown"
g_CFGGroup_System_Startup: str = "Startup"
g_FieldDelimiters: str = ","
g_Keyword_ActualExposure: str = "ActualExposure"
g_Keyword_ActualInterval_ms: str = "ActualInterval-ms"
g_Keyword_AnswerTimeout: str = "AnswerTimeout"
g_Keyword_BaudRate: str = "BaudRate"
g_Keyword_Binning: str = "Binning"
g_Keyword_CCDTemperature: str = "CCDTemperature"
g_Keyword_CCDTemperatureSetPoint: str = "CCDTemperatureSetPoint"
g_Keyword_CameraChannelIndex: str = "CameraChannelIndex"
g_Keyword_CameraChannelName: str = "CameraChannelName"
g_Keyword_CameraID: str = "CameraID"
g_Keyword_CameraName: str = "CameraName"
g_Keyword_Channel: str = "Channel"
g_Keyword_Closed_Position: str = "ClosedPosition"
g_Keyword_ColorMode: str = "ColorMode"
g_Keyword_CoreAutoFocus: str = "AutoFocus"
g_Keyword_CoreAutoShutter: str = "AutoShutter"
g_Keyword_CoreCamera: str = "Camera"
g_Keyword_CoreChannelGroup: str = "ChannelGroup"
g_Keyword_CoreDevice: str = "Core"
g_Keyword_CoreFocus: str = "Focus"
g_Keyword_CoreGalvo: str = "Galvo"
g_Keyword_CoreImageProcessor: str = "ImageProcessor"
g_Keyword_CoreInitialize: str = "Initialize"
g_Keyword_CoreSLM: str = "SLM"
g_Keyword_CoreShutter: str = "Shutter"
g_Keyword_CoreTimeoutMs: str = "TimeoutMs"
g_Keyword_CoreXYStage: str = "XYStage"
g_Keyword_DataBits: str = "DataBits"
g_Keyword_Delay: str = "Delay_ms"
g_Keyword_DelayBetweenCharsMs: str = "DelayBetweenCharsMs"
g_Keyword_Description: str = "Description"
g_Keyword_EMGain: str = "EMGain"
g_Keyword_Elapsed_Time_ms: str = "ElapsedTime-ms"
g_Keyword_Exposure: str = "Exposure"
g_Keyword_Gain: str = "Gain"
g_Keyword_Handshaking: str = "Handshaking"
g_Keyword_HubID: str = "HubID"
g_Keyword_Interval_ms: str = "Interval-ms"
g_Keyword_Label: str = "Label"
g_Keyword_Meatdata_Exposure: str = "Exposure-ms"
g_Keyword_Metadata_CameraLabel: str = "Camera"
g_Keyword_Metadata_ImageNumber: str = "ImageNumber"
g_Keyword_Metadata_ROI_X: str = "ROI-X-start"
g_Keyword_Metadata_ROI_Y: str = "ROI-Y-start"
g_Keyword_Metadata_Score: str = "Score"
g_Keyword_Metadata_TimeInCore: str = "TimeReceivedByCore"
g_Keyword_Name: str = "Name"
g_Keyword_Offset: str = "Offset"
g_Keyword_Parity: str = "Parity"
g_Keyword_PixelType: str = "PixelType"
g_Keyword_Port: str = "Port"
g_Keyword_Position: str = "Position"
g_Keyword_ReadoutMode: str = "ReadoutMode"
g_Keyword_ReadoutTime: str = "ReadoutTime"
g_Keyword_Speed: str = "Speed"
g_Keyword_State: str = "State"
g_Keyword_StopBits: str = "StopBits"
g_Keyword_Transpose_Correction: str = "TransposeCorrection"
g_Keyword_Transpose_MirrorX: str = "TransposeMirrorX"
g_Keyword_Transpose_MirrorY: str = "TransposeMirrorY"
g_Keyword_Transpose_SwapXY: str = "TransposeXY"
g_Keyword_Type: str = "Type"
g_Keyword_Version: str = "Version"
