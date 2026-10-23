import pymmcore_nano as pmn
import pytest


def test_swig_container_names(demo_core: pmn.CMMCore) -> None:
    # e.g. pycro-manager builds stage sequences with pymmcore.DoubleVector()
    with pytest.warns(DeprecationWarning, match="DoubleVector"):
        z_sequence = pmn.DoubleVector()
    z_sequence.append(1.0)
    z_sequence.append(2.0)
    z_stage = demo_core.getFocusDevice()
    demo_core.setProperty(z_stage, "UseSequences", "Yes")
    demo_core.loadStageSequence(z_stage, z_sequence)

    with pytest.warns(DeprecationWarning, match="StrVector"):
        from pymmcore_nano import StrVector
    assert StrVector is list

    with pytest.raises(AttributeError):
        pmn.NotAVector  # noqa: B018
