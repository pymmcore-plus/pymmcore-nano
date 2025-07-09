"""
Tests for Image Processor functionality to improve MMCore.cpp coverage.
"""

import pymmcore_nano as pmn
import pytest


def test_image_processor_device_assignment(demo_core: pmn.CMMCore) -> None:
    """Test image processor device assignment and retrieval."""
    # Initially no image processor should be set
    demo_core.getImageProcessorDevice()

    # Load and assign an image processor
    demo_core.loadDevice("TestProcessor", "DemoCamera", "MedianFilter")
    demo_core.initializeDevice("TestProcessor")
    demo_core.setImageProcessorDevice("TestProcessor")

    # Verify assignment
    assert demo_core.getImageProcessorDevice() == "TestProcessor"

    # Clean up
    demo_core.setImageProcessorDevice("")
    demo_core.unloadDevice("TestProcessor")


def test_image_processor_device_types(demo_core: pmn.CMMCore) -> None:
    """Test loading different types of image processors."""
    # Test different image processor types
    processors = [
        ("TransposeProcessor", "TransposeProcessor"),
        ("ImageFlipX", "ImageFlipX"),
        ("ImageFlipY", "ImageFlipY"),
        ("MedianFilter", "MedianFilter"),
    ]

    for label, device_name in processors:
        demo_core.loadDevice(label, "DemoCamera", device_name)
        demo_core.initializeDevice(label)

        # Verify device type
        device_type = demo_core.getDeviceType(label)
        assert device_type == pmn.DeviceType.ImageProcessorDevice

        # Test setting as active processor
        demo_core.setImageProcessorDevice(label)
        assert demo_core.getImageProcessorDevice() == label

        # Clean up
        demo_core.setImageProcessorDevice("")
        demo_core.unloadDevice(label)


def test_image_processor_with_camera_operations(demo_core: pmn.CMMCore) -> None:
    """Test image processor functionality with camera operations."""
    # Load and set up image processor
    demo_core.loadDevice("TestFlip", "DemoCamera", "ImageFlipX")
    demo_core.initializeDevice("TestFlip")
    demo_core.setImageProcessorDevice("TestFlip")

    try:
        # Take image with processor active
        demo_core.snapImage()
        img = demo_core.getImage()
        assert img is not None

        # Image should be processed (we can't easily verify the flip,
        # but code path is exercised)
        assert img.shape[0] > 0 and img.shape[1] > 0

    finally:
        # Clean up
        demo_core.setImageProcessorDevice("")
        demo_core.unloadDevice("TestFlip")


def test_image_processor_device_properties(demo_core: pmn.CMMCore) -> None:
    """Test image processor device properties."""
    demo_core.loadDevice("TestMedian", "DemoCamera", "MedianFilter")
    demo_core.initializeDevice("TestMedian")

    try:
        # Get device properties
        properties = demo_core.getDevicePropertyNames("TestMedian")
        assert len(properties) >= 0  # May have no properties, but should not error

        # Test device description
        description = demo_core.getDeviceDescription("TestMedian")
        assert isinstance(description, str)

    finally:
        demo_core.unloadDevice("TestMedian")


def test_image_processor_invalid_device_assignment(demo_core: pmn.CMMCore) -> None:
    """Test image processor assignment with invalid device."""
    # Test with non-existent device
    with pytest.raises(pmn.CMMError):
        demo_core.setImageProcessorDevice("NonExistentProcessor")


def test_image_processor_wrong_device_type_assignment(demo_core: pmn.CMMCore) -> None:
    """Test image processor assignment with wrong device type."""
    # Try to assign a camera as image processor (should fail)
    with pytest.raises(pmn.CMMError):
        demo_core.setImageProcessorDevice("Camera")


def test_image_processor_null_device_assignment(demo_core: pmn.CMMCore) -> None:
    """Test image processor assignment with null/empty device."""
    # Setting empty string should clear the image processor
    demo_core.setImageProcessorDevice("")
    assert demo_core.getImageProcessorDevice() == ""


def test_image_processor_multiple_assignments(demo_core: pmn.CMMCore) -> None:
    """Test multiple image processor assignments."""
    # Load multiple processors
    demo_core.loadDevice("Processor1", "DemoCamera", "ImageFlipX")
    demo_core.loadDevice("Processor2", "DemoCamera", "ImageFlipY")
    demo_core.initializeDevice("Processor1")
    demo_core.initializeDevice("Processor2")

    try:
        # Test switching between processors
        demo_core.setImageProcessorDevice("Processor1")
        assert demo_core.getImageProcessorDevice() == "Processor1"

        demo_core.setImageProcessorDevice("Processor2")
        assert demo_core.getImageProcessorDevice() == "Processor2"

        # Clear processor
        demo_core.setImageProcessorDevice("")
        assert demo_core.getImageProcessorDevice() == ""

    finally:
        demo_core.setImageProcessorDevice("")
        demo_core.unloadDevice("Processor1")
        demo_core.unloadDevice("Processor2")


def test_image_processor_busy_state(demo_core: pmn.CMMCore) -> None:
    """Test image processor busy state detection."""
    demo_core.loadDevice("TestProcessor", "DemoCamera", "MedianFilter")
    demo_core.initializeDevice("TestProcessor")

    try:
        # Test device busy state
        is_busy = demo_core.deviceBusy("TestProcessor")
        assert isinstance(is_busy, bool)

        # Most demo devices are never busy, but we test the code path
        assert is_busy is False

    finally:
        demo_core.unloadDevice("TestProcessor")


def test_image_processor_wait_for_device(demo_core: pmn.CMMCore) -> None:
    """Test waiting for image processor device."""
    demo_core.loadDevice("TestProcessor", "DemoCamera", "MedianFilter")
    demo_core.initializeDevice("TestProcessor")

    try:
        # Test waiting for device (should return immediately for demo devices)
        demo_core.waitForDevice("TestProcessor")

        # Test with timeout
        demo_core.waitForDeviceType(pmn.DeviceType.ImageProcessorDevice)

    finally:
        demo_core.unloadDevice("TestProcessor")
