"""Tests focused on State Device functionality to increase MMCore.cpp coverage."""

import pymmcore_nano as pmn
import pytest


def test_state_device_basic_operations(demo_core: pmn.CMMCore) -> None:
    """Test basic state device operations."""
    state_devices = ["Dichroic", "Emission", "Excitation", "Objective", "Path", "LED"]

    for device in state_devices:
        # Test getting number of states
        num_states = demo_core.getNumberOfStates(device)
        assert num_states > 0

        # Test getting current state
        current_state = demo_core.getState(device)
        assert 0 <= current_state < num_states

        # Test setting state to a valid value
        demo_core.setState(device, 0)
        assert demo_core.getState(device) == 0

        # Test setting state to another valid value if available
        if num_states > 1:
            demo_core.setState(device, 1)
            assert demo_core.getState(device) == 1


def test_state_device_labels(demo_core: pmn.CMMCore) -> None:
    """Test state device label operations."""
    device = "LED"  # Use LED device for label testing

    # Get all state labels
    state_labels = demo_core.getStateLabels(device)
    assert isinstance(state_labels, list)
    assert len(state_labels) > 0

    # Test getting current state label
    current_label = demo_core.getStateLabel(device)
    assert current_label in state_labels

    # Test setting state by label
    if len(state_labels) > 1:
        demo_core.setStateLabel(device, state_labels[0])
        assert demo_core.getStateLabel(device) == state_labels[0]

        demo_core.setStateLabel(device, state_labels[1])
        assert demo_core.getStateLabel(device) == state_labels[1]


def test_state_device_label_mapping(demo_core: pmn.CMMCore) -> None:
    """Test state-to-label mapping functions."""
    device = "LED"

    state_labels = demo_core.getStateLabels(device)

    for _i, label in enumerate(state_labels):
        # Test getStateFromLabel
        state_from_label = demo_core.getStateFromLabel(device, label)

        # The state should correspond to the index for demo devices
        assert state_from_label >= 0

        # Test round-trip: set state, get label
        demo_core.setState(device, state_from_label)
        retrieved_label = demo_core.getStateLabel(device)
        assert retrieved_label == label


def test_state_device_custom_labels(demo_core: pmn.CMMCore) -> None:
    """Test defining custom state labels."""
    device = "LED"

    # Define a new state label for state 0
    test_label = "TestState0"
    demo_core.defineStateLabel(device, 0, test_label)

    # Set state to 0 and verify the label
    demo_core.setState(device, 0)
    current_label = demo_core.getStateLabel(device)
    assert current_label == test_label

    # Verify the label appears in the state labels list
    state_labels = demo_core.getStateLabels(device)
    assert test_label in state_labels


def test_state_device_error_conditions(demo_core: pmn.CMMCore) -> None:
    """Test error conditions for state devices."""
    device = "LED"
    num_states = demo_core.getNumberOfStates(device)

    # Test setting invalid state (too high)
    with pytest.raises(pmn.CMMError):
        demo_core.setState(device, num_states + 10)

    # Test setting invalid state (negative)
    with pytest.raises(pmn.CMMError):
        demo_core.setState(device, -1)

    # Test getting state from non-existent label
    with pytest.raises(pmn.CMMError):
        demo_core.getStateFromLabel(device, "NonExistentLabel")

    # Test setting state with non-existent label
    with pytest.raises(pmn.CMMError):
        demo_core.setStateLabel(device, "NonExistentLabel")
