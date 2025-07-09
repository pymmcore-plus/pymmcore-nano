"""
Test utilities for pymmcore-nano - Mock devices and testing infrastructure.

This module provides mock device implementations for comprehensive testing
of MMCore functionality. It's designed for internal testing only and should
not be used in production code.
"""

from abc import ABC, abstractmethod

import pymmcore_nano as pmn

# We'll define Python base classes that can be subclassed to create mock devices
# These will need to be implemented in C++ and exposed via a separate test module


class MockDevice(ABC):
    """Base class for mock devices used in testing."""

    @abstractmethod
    def initialize(self) -> int:
        """Initialize the device. Return DEVICE_OK (0) on success."""
        pass

    @abstractmethod
    def shutdown(self) -> int:
        """Shutdown the device. Return DEVICE_OK (0) on success."""
        pass

    @abstractmethod
    def is_busy(self) -> bool:
        """Return True if device is busy."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the device name."""
        pass


class MockSerialDevice(MockDevice):
    """Mock serial device for testing serial port functionality."""

    def __init__(self, name: str = "MockSerial", simulate_errors: bool = False):
        self.name = name
        self.simulate_errors = simulate_errors
        self.initialized = False

    def initialize(self) -> int:
        if self.simulate_errors:
            return 1  # DEVICE_ERR
        self.initialized = True
        return 0  # DEVICE_OK

    def shutdown(self) -> int:
        self.initialized = False
        return 0

    def is_busy(self) -> bool:
        return False

    def get_name(self) -> str:
        return self.name


class MockCamera(MockDevice):
    """Mock camera device that supports exposure sequences."""

    def __init__(self, name: str = "MockCamera", supports_sequences: bool = True):
        self.name = name
        self.supports_sequences = supports_sequences
        self.initialized = False
        self.exposure_sequence: list[float] = []
        self.sequence_running = False

    def initialize(self) -> int:
        self.initialized = True
        return 0

    def shutdown(self) -> int:
        self.initialized = False
        return 0

    def is_busy(self) -> bool:
        return self.sequence_running

    def get_name(self) -> str:
        return self.name

    def is_exposure_sequenceable(self) -> bool:
        return self.supports_sequences

    def load_exposure_sequence(self, exposures: list[float]) -> int:
        if not self.supports_sequences:
            return 1  # DEVICE_ERR
        self.exposure_sequence = exposures.copy()
        return 0

    def start_exposure_sequence(self) -> int:
        if not self.supports_sequences or not self.exposure_sequence:
            return 1  # DEVICE_ERR
        self.sequence_running = True
        return 0

    def stop_exposure_sequence(self) -> int:
        self.sequence_running = False
        return 0


class MockStage(MockDevice):
    """Mock stage device that supports sequences."""

    def __init__(self, name: str = "MockStage", supports_sequences: bool = True):
        self.name = name
        self.supports_sequences = supports_sequences
        self.initialized = False
        self.position = 0.0
        self.position_sequence: list[float] = []
        self.sequence_running = False

    def initialize(self) -> int:
        self.initialized = True
        return 0

    def shutdown(self) -> int:
        self.initialized = False
        return 0

    def is_busy(self) -> bool:
        return self.sequence_running

    def get_name(self) -> str:
        return self.name

    def is_stage_sequenceable(self) -> bool:
        return self.supports_sequences

    def load_stage_sequence(self, positions: list[float]) -> int:
        if not self.supports_sequences:
            return 1  # DEVICE_ERR
        self.position_sequence = positions.copy()
        return 0

    def start_stage_sequence(self) -> int:
        if not self.supports_sequences or not self.position_sequence:
            return 1  # DEVICE_ERR
        self.sequence_running = True
        return 0

    def stop_stage_sequence(self) -> int:
        self.sequence_running = False
        return 0


class MockXYStage(MockDevice):
    """Mock XY stage device that supports sequences."""

    def __init__(self, name: str = "MockXYStage", supports_sequences: bool = True):
        self.name = name
        self.supports_sequences = supports_sequences
        self.initialized = False
        self.x_position = 0.0
        self.y_position = 0.0
        self.x_sequence: list[float] = []
        self.y_sequence: list[float] = []
        self.sequence_running = False

    def initialize(self) -> int:
        self.initialized = True
        return 0

    def shutdown(self) -> int:
        self.initialized = False
        return 0

    def is_busy(self) -> bool:
        return self.sequence_running

    def get_name(self) -> str:
        return self.name

    def is_xy_stage_sequenceable(self) -> bool:
        return self.supports_sequences

    def load_xy_stage_sequence(
        self, x_positions: list[float], y_positions: list[float]
    ) -> int:
        if not self.supports_sequences:
            return 1  # DEVICE_ERR
        if len(x_positions) != len(y_positions):
            return 2  # DEVICE_INVALID_INPUT_PARAM
        self.x_sequence = x_positions.copy()
        self.y_sequence = y_positions.copy()
        return 0

    def start_xy_stage_sequence(self) -> int:
        if not self.supports_sequences or not self.x_sequence:
            return 1  # DEVICE_ERR
        self.sequence_running = True
        return 0

    def stop_xy_stage_sequence(self) -> int:
        self.sequence_running = False
        return 0


class MockErrorDevice(MockDevice):
    """Mock device that always returns errors - for testing error handling."""

    def __init__(self, name: str = "MockErrorDevice", error_code: int = 1):
        self.name = name
        self.error_code = error_code

    def initialize(self) -> int:
        return self.error_code

    def shutdown(self) -> int:
        return self.error_code

    def is_busy(self) -> bool:
        return False

    def get_name(self) -> str:
        return self.name


# Test utilities
def create_mock_core_with_serial_device() -> tuple[pmn.CMMCore, MockSerialDevice]:
    """Create a CMMCore instance with a mock serial device for testing."""
    # This would need to be implemented in C++ to actually work
    # For now, this is just a placeholder showing the intended API
    raise NotImplementedError("Mock device support not yet fully implemented")


def create_mock_core_with_sequenceable_camera() -> tuple[pmn.CMMCore, MockCamera]:
    """Create a CMMCore instance with a mock camera that supports sequences."""
    raise NotImplementedError("Mock device support not yet fully implemented")


def create_mock_core_with_sequenceable_stage() -> tuple[pmn.CMMCore, MockStage]:
    """Create a CMMCore instance with a mock stage that supports sequences."""
    raise NotImplementedError("Mock device support not yet fully implemented")


# For now, we'll implement a simpler approach that doesn't require the C++ bindings
class TestingUtils:
    """Utility functions for testing that don't require mock devices."""

    @staticmethod
    def get_uncovered_functions() -> list[str]:
        """Return a list of MMCore functions that need more test coverage."""
        return [
            "setSerialProperties",
            "setSerialPortCommand",
            "getSerialPortAnswer",
            "writeToSerialPort",
            "readFromSerialPort",
            "setSLMImage",
            "setSLMPixelsTo",
            "displaySLMImage",
            "setGalvoPosition",
            "getGalvoPosition",
            "setGalvoIlluminationState",
            "getGalvoIlluminationState",
            "addGalvoPolygonVertex",
            "deleteGalvoPolygonVertices",
            "loadGalvoPolygons",
            "setGalvoSpotInterval",
            "runGalvoSequence",
            "runGalvoPolygons",
            "stopGalvoSequence",
        ]

    @staticmethod
    def get_error_conditions_to_test() -> list[str]:
        """Return a list of error conditions that should be tested."""
        return [
            "Invalid device labels",
            "Null parameter values",
            "Empty sequences",
            "Mismatched sequence lengths",
            "Unsupported operations",
            "Device communication errors",
            "Property value out of range",
            "Device busy during operation",
            "Memory allocation failures",
            "Configuration file errors",
        ]
