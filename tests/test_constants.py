from enum import IntEnum

import pytest

import pymmcore_nano as pmn


@pytest.mark.skipif(
    not pmn._pymmcore_nano._MATCH_SWIG, reason="SWIG compatibility not enabled"
)
def test_enums() -> None:
    for obj in vars(pmn).values():
        if isinstance(obj, type) and issubclass(obj, IntEnum):
            for member in obj:
                assert getattr(pmn, member.name) == member.value
