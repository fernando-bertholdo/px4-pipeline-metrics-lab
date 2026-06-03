from __future__ import annotations

import pytest

from dronemetrics.trajectory import trajectory_rms_m


def test_identical_paths_have_zero_error() -> None:
    path = [(0.0, 0.0), (0.0, 0.001), (0.0, 0.002)]
    assert trajectory_rms_m(path, path) == pytest.approx(0.0)


def test_mismatched_lengths_raise() -> None:
    with pytest.raises(ValueError):
        trajectory_rms_m([(0.0, 0.0)], [(0.0, 0.0), (0.0, 0.1)])


def test_empty_is_zero() -> None:
    assert trajectory_rms_m([], []) == 0.0


def test_rms_is_positive_when_paths_differ() -> None:
    planned = [(0.0, 0.0), (0.0, 0.001)]
    actual = [(0.00001, 0.0), (0.0, 0.00101)]
    assert trajectory_rms_m(planned, actual) > 0.0
