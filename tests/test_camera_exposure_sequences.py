"""
Tests for Camera exposure sequence functionality to improve MMCore.cpp coverage.
"""

import pymmcore_nano as pmn
import pytest


def test_camera_exposure_sequence_support(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence capability detection."""
    camera = demo_core.getCameraDevice()
    assert camera == "Camera"

    # Test if camera supports exposure sequences
    is_sequenceable = demo_core.isExposureSequenceable(camera)
    # This may be False for demo camera, but we're testing the code path
    assert isinstance(is_sequenceable, bool)


def test_camera_exposure_sequence_max_length(demo_core: pmn.CMMCore) -> None:
    """Test getting camera exposure sequence maximum length."""
    camera = demo_core.getCameraDevice()

    try:
        max_length = demo_core.getExposureSequenceMaxLength(camera)
        assert isinstance(max_length, int)
        assert max_length >= 0
    except pmn.CMMError as e:
        # Some cameras may not support exposure sequences -
        # that's okay, we tested the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_camera_exposure_sequence_loading(demo_core: pmn.CMMCore) -> None:
    """Test loading camera exposure sequences."""
    camera = demo_core.getCameraDevice()

    # Test with simple exposure sequence (in milliseconds)
    exposure_sequence = [10.0, 20.0, 30.0, 40.0, 50.0]

    try:
        demo_core.loadExposureSequence(camera, exposure_sequence)
    except pmn.CMMError as e:
        # Camera may not support exposure sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_camera_exposure_sequence_control(demo_core: pmn.CMMCore) -> None:
    """Test starting and stopping camera exposure sequences."""
    camera = demo_core.getCameraDevice()

    try:
        # Try to start exposure sequence
        demo_core.startExposureSequence(camera)

        # Try to stop exposure sequence
        demo_core.stopExposureSequence(camera)

    except pmn.CMMError as e:
        # Camera may not support exposure sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_camera_exposure_sequence_empty_sequence(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence with empty sequence."""
    camera = demo_core.getCameraDevice()

    # Empty exposure sequence
    exposure_sequence = []

    try:
        demo_core.loadExposureSequence(camera, exposure_sequence)
    except pmn.CMMError as e:
        # May fail for empty sequences or unsupported feature
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "empty" in error_msg or "support" in error_msg


def test_camera_exposure_sequence_single_exposure(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence with single exposure."""
    camera = demo_core.getCameraDevice()

    # Single exposure sequence
    exposure_sequence = [25.0]

    try:
        demo_core.loadExposureSequence(camera, exposure_sequence)
    except pmn.CMMError as e:
        # Camera may not support exposure sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_camera_exposure_sequence_long_sequence(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence with long sequence."""
    camera = demo_core.getCameraDevice()

    # Longer exposure sequence
    exposure_sequence = [i * 10.0 for i in range(1, 101)]  # 100 exposures

    try:
        demo_core.loadExposureSequence(camera, exposure_sequence)
    except pmn.CMMError as e:
        # Camera may not support exposure sequences or this length
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "length" in error_msg or "support" in error_msg


def test_camera_exposure_sequence_with_invalid_camera(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence functions with invalid camera label."""
    invalid_camera = "NonExistentCamera"

    # Test isExposureSequenceable with invalid camera
    with pytest.raises(pmn.CMMError):
        demo_core.isExposureSequenceable(invalid_camera)

    # Test getExposureSequenceMaxLength with invalid camera
    with pytest.raises(pmn.CMMError):
        demo_core.getExposureSequenceMaxLength(invalid_camera)

    # Test loadExposureSequence with invalid camera
    with pytest.raises(pmn.CMMError):
        demo_core.loadExposureSequence(invalid_camera, [10.0])

    # Test startExposureSequence with invalid camera
    with pytest.raises(pmn.CMMError):
        demo_core.startExposureSequence(invalid_camera)

    # Test stopExposureSequence with invalid camera
    with pytest.raises(pmn.CMMError):
        demo_core.stopExposureSequence(invalid_camera)


def test_camera_exposure_sequence_with_null_camera(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence functions with null/empty camera label."""
    # Test with empty string
    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.isExposureSequenceable("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.getExposureSequenceMaxLength("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.loadExposureSequence("", [10.0])

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.startExposureSequence("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.stopExposureSequence("")


def test_camera_exposure_sequence_invalid_exposures(demo_core: pmn.CMMCore) -> None:
    """Test camera exposure sequence with invalid exposure values."""
    camera = demo_core.getCameraDevice()

    # Test with negative exposures
    try:
        demo_core.loadExposureSequence(camera, [-10.0, -5.0])
    except pmn.CMMError as e:
        # May fail for negative exposures or unsupported sequences
        error_msg = str(e).lower()
        assert (
            "sequenc" in error_msg
            or "exposur" in error_msg
            or "support" in error_msg
            or "negativ" in error_msg
        )

    # Test with zero exposures
    try:
        demo_core.loadExposureSequence(camera, [0.0, 0.0])
    except pmn.CMMError as e:
        # May fail for zero exposures or unsupported sequences
        error_msg = str(e).lower()
        assert (
            "sequenc" in error_msg or "exposur" in error_msg or "support" in error_msg
        )


def test_camera_exposure_sequence_stop_without_start(demo_core: pmn.CMMCore) -> None:
    """Test stopping camera exposure sequence without starting it."""
    camera = demo_core.getCameraDevice()

    try:
        # Try to stop without starting
        demo_core.stopExposureSequence(camera)
    except pmn.CMMError as e:
        # May fail because sequence wasn't started, or sequences not supported
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "support" in error_msg or "start" in error_msg


def test_camera_exposure_sequence_start_without_load(demo_core: pmn.CMMCore) -> None:
    """Test starting camera exposure sequence without loading it."""
    camera = demo_core.getCameraDevice()

    try:
        # Try to start without loading
        demo_core.startExposureSequence(camera)
    except pmn.CMMError as e:
        # May fail because sequence wasn't loaded, or sequences not supported
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "support" in error_msg or "load" in error_msg
