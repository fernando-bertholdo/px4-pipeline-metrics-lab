from __future__ import annotations

import pytest

from dronemetrics.mission import estimated_duration_s, waypoint_count


def test_waypoint_count(square_mission: list[tuple[float, float]]) -> None:
    assert waypoint_count(square_mission) == 5


def test_duration_includes_overhead(straight_mission: list[tuple[float, float]]) -> None:
    # sem overhead vs com overhead por waypoint
    bare = estimated_duration_s(straight_mission, 100.0, seconds_per_waypoint=0.0)
    with_overhead = estimated_duration_s(straight_mission, 100.0, seconds_per_waypoint=2.0)
    assert with_overhead == pytest.approx(bare + 2.0 * len(straight_mission))


def test_duration_rejects_zero_speed(straight_mission: list[tuple[float, float]]) -> None:
    with pytest.raises(ValueError):
        estimated_duration_s(straight_mission, 0.0)


def test_duration_scales_with_distance() -> None:
    short = estimated_duration_s([(0.0, 0.0), (0.0, 0.5)], 100.0, seconds_per_waypoint=0.0)
    long = estimated_duration_s([(0.0, 0.0), (0.0, 1.0)], 100.0, seconds_per_waypoint=0.0)
    assert long > short
