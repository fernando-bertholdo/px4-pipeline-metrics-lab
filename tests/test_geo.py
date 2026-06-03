from __future__ import annotations

import math

import pytest

from dronemetrics.geo import haversine_m, total_path_length_m


def test_zero_distance() -> None:
    assert haversine_m((0.0, 0.0), (0.0, 0.0)) == pytest.approx(0.0)


def test_one_degree_longitude_at_equator() -> None:
    # ~111.19 km por grau de longitude no equador
    assert haversine_m((0.0, 0.0), (0.0, 1.0)) == pytest.approx(111_195, rel=1e-3)


def test_symmetry() -> None:
    a, b = (12.3, -45.6), (7.8, 90.1)
    assert haversine_m(a, b) == pytest.approx(haversine_m(b, a))


def test_path_length_single_point_is_zero() -> None:
    assert total_path_length_m([(1.0, 2.0)]) == 0.0


def test_path_length_sums_segments(square_mission: list[tuple[float, float]]) -> None:
    total = total_path_length_m(square_mission)
    assert total == pytest.approx(4 * haversine_m((0.0, 0.0), (0.00045, 0.0)), rel=1e-6)
    assert math.isfinite(total)
