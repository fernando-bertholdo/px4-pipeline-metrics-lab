from __future__ import annotations

import pytest

from dronemetrics.battery import battery_consumption_wh, remaining_capacity_pct


def test_consumption_basic() -> None:
    # 1000 m a 10 m/s = 100 s = 1/36 h; x 180 W = 5 Wh
    assert battery_consumption_wh(1000.0, 180.0, 10.0) == pytest.approx(5.0, rel=1e-6)


def test_consumption_rejects_zero_speed() -> None:
    with pytest.raises(ValueError):
        battery_consumption_wh(1000.0, 180.0, 0.0)


def test_remaining_capacity_clamped() -> None:
    assert remaining_capacity_pct(100.0, 150.0) == 0.0
    assert remaining_capacity_pct(100.0, -10.0) == 100.0


def test_remaining_capacity_half() -> None:
    assert remaining_capacity_pct(100.0, 50.0) == pytest.approx(50.0)
