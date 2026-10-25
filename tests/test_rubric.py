from __future__ import annotations

import pytest

from agentrubric.rubric import DEFAULT_RUBRIC, Dimension, Rubric


def test_default_rubric_has_ten_weighted_dimensions():
    assert len(DEFAULT_RUBRIC.dimensions) == 10
    assert DEFAULT_RUBRIC.total_weight > 0
    assert "correctness" in DEFAULT_RUBRIC.keys


def test_get_dimension():
    assert DEFAULT_RUBRIC.get("safety").name == "Safety"
    with pytest.raises(KeyError):
        DEFAULT_RUBRIC.get("nope")


def test_rejects_duplicate_keys():
    with pytest.raises(ValueError):
        Rubric((Dimension("a", "A", ""), Dimension("a", "A2", "")))


def test_rejects_negative_or_zero_total_weight():
    with pytest.raises(ValueError):
        Rubric((Dimension("a", "A", "", weight=-1),))
    with pytest.raises(ValueError):
        Rubric((Dimension("a", "A", "", weight=0),))
