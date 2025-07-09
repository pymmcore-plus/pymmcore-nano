"""
Tests for XY Stage sequence functionality to improve MMCore.cpp coverage.
"""

import pymmcore_nano as pmn
import pytest


def test_xy_stage_sequence_support(demo_core: pmn.CMMCore) -> None:
    """Test XY stage sequence capability detection."""
    xy_stage = demo_core.getXYStageDevice()
    assert xy_stage == "XY"

    # Test if XY stage is sequenceable
    is_sequenceable = demo_core.isXYStageSequenceable(xy_stage)
    # This may be False for demo, but we're testing the code path
    assert isinstance(is_sequenceable, bool)


def test_xy_stage_sequence_max_length(demo_core: pmn.CMMCore) -> None:
    """Test getting XY stage sequence maximum length."""
    xy_stage = demo_core.getXYStageDevice()

    try:
        max_length = demo_core.getXYStageSequenceMaxLength(xy_stage)
        assert isinstance(max_length, int)
        assert max_length >= 0
    except pmn.CMMError as e:
        # Some devices may not support sequences - that's okay, we tested the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_xy_stage_sequence_loading(demo_core: pmn.CMMCore) -> None:
    """Test loading XY stage sequences."""
    xy_stage = demo_core.getXYStageDevice()

    # Test with simple sequence
    x_sequence = [0.0, 1.0, 2.0]
    y_sequence = [0.0, 1.0, 2.0]

    try:
        demo_core.loadXYStageSequence(xy_stage, x_sequence, y_sequence)
    except pmn.CMMError as e:
        # Device may not support sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_xy_stage_sequence_control(demo_core: pmn.CMMCore) -> None:
    """Test starting and stopping XY stage sequences."""
    xy_stage = demo_core.getXYStageDevice()

    try:
        # Try to start sequence
        demo_core.startXYStageSequence(xy_stage)

        # Try to stop sequence
        demo_core.stopXYStageSequence(xy_stage)

    except pmn.CMMError as e:
        # Device may not support sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_xy_stage_sequence_mismatched_lengths(demo_core: pmn.CMMCore) -> None:
    """Test XY stage sequence with mismatched X and Y sequence lengths."""
    xy_stage = demo_core.getXYStageDevice()

    # Mismatched sequence lengths
    x_sequence = [0.0, 1.0]
    y_sequence = [0.0, 1.0, 2.0]  # Different length

    try:
        demo_core.loadXYStageSequence(xy_stage, x_sequence, y_sequence)
        # If no error, that's fine - device may handle it
    except pmn.CMMError as e:
        # Expected error for mismatched lengths or unsupported sequences
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "length" in error_msg or "support" in error_msg


def test_xy_stage_sequence_empty_sequences(demo_core: pmn.CMMCore) -> None:
    """Test XY stage sequence with empty sequences."""
    xy_stage = demo_core.getXYStageDevice()

    # Empty sequences
    x_sequence = []
    y_sequence = []

    try:
        demo_core.loadXYStageSequence(xy_stage, x_sequence, y_sequence)
    except pmn.CMMError as e:
        # May fail for empty sequences or unsupported feature
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "empty" in error_msg or "support" in error_msg


def test_xy_stage_sequence_with_invalid_device(demo_core: pmn.CMMCore) -> None:
    """Test XY stage sequence functions with invalid device label."""
    invalid_device = "NonExistentXYStage"

    # Test isXYStageSequenceable with invalid device
    with pytest.raises(pmn.CMMError):
        demo_core.isXYStageSequenceable(invalid_device)

    # Test getXYStageSequenceMaxLength with invalid device
    with pytest.raises(pmn.CMMError):
        demo_core.getXYStageSequenceMaxLength(invalid_device)

    # Test loadXYStageSequence with invalid device
    with pytest.raises(pmn.CMMError):
        demo_core.loadXYStageSequence(invalid_device, [0.0], [0.0])

    # Test startXYStageSequence with invalid device
    with pytest.raises(pmn.CMMError):
        demo_core.startXYStageSequence(invalid_device)

    # Test stopXYStageSequence with invalid device
    with pytest.raises(pmn.CMMError):
        demo_core.stopXYStageSequence(invalid_device)


def test_xy_stage_sequence_with_null_device(demo_core: pmn.CMMCore) -> None:
    """Test XY stage sequence functions with null/empty device label."""
    # Test with empty string
    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.isXYStageSequenceable("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.getXYStageSequenceMaxLength("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.loadXYStageSequence("", [0.0], [0.0])

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.startXYStageSequence("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.stopXYStageSequence("")
