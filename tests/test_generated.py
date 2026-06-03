"""Testes de carga parametrizados — quantidade controlada por TEST_SCALE.

Cada caso é um cálculo real de KPI (não um no-op), então aumentar a escala
aumenta o trabalho de teste de forma realista. Usado pelas variações
"2x testes" e "4x testes" do experimento.
"""

from __future__ import annotations

import pytest

from dronemetrics.battery import battery_consumption_wh
from dronemetrics.geo import haversine_m
from tests.experiment_config import BASE_GENERATED_CASES, TEST_SCALE

_N = BASE_GENERATED_CASES * max(1, TEST_SCALE)


@pytest.mark.parametrize("i", range(_N))
def test_generated_distance_is_monotonic(i: int) -> None:
    """Distância cresce com a longitude alvo (caso i)."""
    target = (i + 1) * 0.001
    near = haversine_m((0.0, 0.0), (0.0, target))
    far = haversine_m((0.0, 0.0), (0.0, target + 0.001))
    assert far > near >= 0.0


@pytest.mark.parametrize("i", range(_N))
def test_generated_battery_positive(i: int) -> None:
    """Consumo de bateria e positivo para distancia/potencia positivas (caso i)."""
    wh = battery_consumption_wh(distance_m=100.0 * (i + 1), avg_power_w=180.0, speed_mps=12.0)
    assert wh > 0.0
