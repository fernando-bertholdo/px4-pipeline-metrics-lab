"""Fixtures compartilhadas pela suíte."""

from __future__ import annotations

import pytest


@pytest.fixture
def square_mission() -> list[tuple[float, float]]:
    """Missão quadrada de ~50 m de lado perto da origem (lat, lon em graus)."""
    d = 0.00045  # ~50 m em latitude
    return [(0.0, 0.0), (d, 0.0), (d, d), (0.0, d), (0.0, 0.0)]


@pytest.fixture
def straight_mission() -> list[tuple[float, float]]:
    """Trecho reto de 1 grau de longitude (~111 km no equador)."""
    return [(0.0, 0.0), (0.0, 1.0)]
