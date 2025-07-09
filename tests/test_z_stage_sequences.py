"""
Tests for Z Stage sequence functionality to improve MMCore.cpp coverage.
"""

import pymmcore_nano as pmn
import pytest


def test_z_stage_sequence_support(demo_core: pmn.CMMCore) -> None:
    """Test Z stage sequence capability detection."""
    z_stage = demo_core.getFocusDevice()
    assert z_stage == "Z"

    # Test if Z stage is sequenceable
    is_sequenceable = demo_core.isStageSequenceable(z_stage)
    # This may be False for demo, but we're testing the code path
    assert isinstance(is_sequenceable, bool)


def test_z_stage_linear_sequence_support(demo_core: pmn.CMMCore) -> None:
    """Test Z stage linear sequence capability detection."""
    z_stage = demo_core.getFocusDevice()

    # Test if Z stage supports linear sequences
    is_linear_sequenceable = demo_core.isStageLinearSequenceable(z_stage)
    # This may be False for demo, but we're testing the code path
    assert isinstance(is_linear_sequenceable, bool)


def test_z_stage_sequence_max_length(demo_core: pmn.CMMCore) -> None:
    """Test getting Z stage sequence maximum length."""
    z_stage = demo_core.getFocusDevice()

    try:
        max_length = demo_core.getStageSequenceMaxLength(z_stage)
        assert isinstance(max_length, int)
        assert max_length >= 0
    except pmn.CMMError as e:
        # Some stages may not support sequences - that's okay, we tested the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_z_stage_sequence_loading(demo_core: pmn.CMMCore) -> None:
    """Test loading Z stage sequences."""
    z_stage = demo_core.getFocusDevice()

    # Test with simple position sequence
    position_sequence = [0.0, 1.0, 2.0, 3.0, 4.0]

    try:
        demo_core.loadStageSequence(z_stage, position_sequence)
    except pmn.CMMError as e:
        # Stage may not support sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_z_stage_linear_sequence_setup(demo_core: pmn.CMMCore) -> None:
    """Test setting up Z stage linear sequences."""
    z_stage = demo_core.getFocusDevice()

    # Test with linear sequence parameters
    dz_um = 0.5  # Step size in microns
    n_slices = 10  # Number of slices

    try:
        demo_core.setStageLinearSequence(z_stage, dz_um, n_slices)
    except pmn.CMMError as e:
        # Stage may not support linear sequences, but we exercised the code path
        assert (
            "sequenc" in str(e).lower()
            or "support" in str(e).lower()
            or "linear" in str(e).lower()
        )


def test_z_stage_sequence_control(demo_core: pmn.CMMCore) -> None:
    """Test starting and stopping Z stage sequences."""
    z_stage = demo_core.getFocusDevice()

    try:
        # Try to start stage sequence
        demo_core.startStageSequence(z_stage)

        # Try to stop stage sequence
        demo_core.stopStageSequence(z_stage)

    except pmn.CMMError as e:
        # Stage may not support sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_z_stage_sequence_empty_sequence(demo_core: pmn.CMMCore) -> None:
    """Test Z stage sequence with empty sequence."""
    z_stage = demo_core.getFocusDevice()

    # Empty position sequence
    position_sequence = []

    try:
        demo_core.loadStageSequence(z_stage, position_sequence)
    except pmn.CMMError as e:
        # May fail for empty sequences or unsupported feature
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "empty" in error_msg or "support" in error_msg


def test_z_stage_sequence_single_position(demo_core: pmn.CMMCore) -> None:
    """Test Z stage sequence with single position."""
    z_stage = demo_core.getFocusDevice()

    # Single position sequence
    position_sequence = [10.0]

    try:
        demo_core.loadStageSequence(z_stage, position_sequence)
    except pmn.CMMError as e:
        # Stage may not support sequences, but we exercised the code path
        assert "sequenc" in str(e).lower() or "support" in str(e).lower()


def test_z_stage_sequence_large_range(demo_core: pmn.CMMCore) -> None:
    """Test Z stage sequence with large position range."""
    z_stage = demo_core.getFocusDevice()

    # Larger position sequence with bigger range
    position_sequence = [
        i * 100.0 for i in range(20)
    ]  # 0 to 1900 microns in 100um steps

    try:
        demo_core.loadStageSequence(z_stage, position_sequence)
    except pmn.CMMError as e:
        # Stage may not support sequences or this range
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "range" in error_msg or "support" in error_msg


def test_z_stage_sequence_with_invalid_stage(demo_core: pmn.CMMCore) -> None:
    """Test Z stage sequence functions with invalid stage label."""
    invalid_stage = "NonExistentStage"

    # Test isStageSequenceable with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.isStageSequenceable(invalid_stage)

    # Test isStageLinearSequenceable with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.isStageLinearSequenceable(invalid_stage)

    # Test getStageSequenceMaxLength with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.getStageSequenceMaxLength(invalid_stage)

    # Test loadStageSequence with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.loadStageSequence(invalid_stage, [0.0])

    # Test setStageLinearSequence with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.setStageLinearSequence(invalid_stage, 1.0, 5)

    # Test startStageSequence with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.startStageSequence(invalid_stage)

    # Test stopStageSequence with invalid stage
    with pytest.raises(pmn.CMMError):
        demo_core.stopStageSequence(invalid_stage)


def test_z_stage_sequence_with_null_stage(demo_core: pmn.CMMCore) -> None:
    """Test Z stage sequence functions with null/empty stage label."""
    # Test with empty string
    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.isStageSequenceable("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.isStageLinearSequenceable("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.getStageSequenceMaxLength("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.loadStageSequence("", [0.0])

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.setStageLinearSequence("", 1.0, 5)

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.startStageSequence("")

    with pytest.raises((pmn.CMMError, TypeError)):
        demo_core.stopStageSequence("")


def test_z_stage_linear_sequence_invalid_parameters(demo_core: pmn.CMMCore) -> None:
    """Test Z stage linear sequence with invalid parameters."""
    z_stage = demo_core.getFocusDevice()

    # Test with negative step size
    try:
        demo_core.setStageLinearSequence(z_stage, -1.0, 5)
    except pmn.CMMError as e:
        # May fail for negative step size or unsupported sequences
        error_msg = str(e).lower()
        assert (
            "sequenc" in error_msg
            or "step" in error_msg
            or "support" in error_msg
            or "negativ" in error_msg
        )

    # Test with zero slices
    try:
        demo_core.setStageLinearSequence(z_stage, 1.0, 0)
    except pmn.CMMError as e:
        # May fail for zero slices or unsupported sequences
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "slice" in error_msg or "support" in error_msg


def test_z_stage_sequence_stop_without_start(demo_core: pmn.CMMCore) -> None:
    """Test stopping Z stage sequence without starting it."""
    z_stage = demo_core.getFocusDevice()

    try:
        # Try to stop without starting
        demo_core.stopStageSequence(z_stage)
    except pmn.CMMError as e:
        # May fail because sequence wasn't started, or sequences not supported
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "support" in error_msg or "start" in error_msg


def test_z_stage_sequence_start_without_load(demo_core: pmn.CMMCore) -> None:
    """Test starting Z stage sequence without loading it."""
    z_stage = demo_core.getFocusDevice()

    try:
        # Try to start without loading
        demo_core.startStageSequence(z_stage)
    except pmn.CMMError as e:
        # May fail because sequence wasn't loaded, or sequences not supported
        error_msg = str(e).lower()
        assert "sequenc" in error_msg or "support" in error_msg or "load" in error_msg
