"""Erro de trajetória: quão longe o voo real ficou do plano.

Mesma métrica que o `mission-test` do projeto PX4 usa como invariante
(trajectory_rms <= max_rms_m).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from dronemetrics.geo import Waypoint, haversine_m


def trajectory_rms_m(planned: Sequence[Waypoint], actual: Sequence[Waypoint]) -> float:
    """RMS (raiz do erro quadrático médio) das distâncias ponto-a-ponto, em metros.

    `planned` e `actual` devem ter o mesmo comprimento (amostras pareadas no tempo).

    >>> trajectory_rms_m([(0.0, 0.0)], [(0.0, 0.0)])
    0.0
    """
    if len(planned) != len(actual):
        raise ValueError("planned e actual precisam ter o mesmo número de amostras")
    if not planned:
        return 0.0
    sq = [haversine_m(p, a) ** 2 for p, a in zip(planned, actual, strict=True)]
    return math.sqrt(sum(sq) / len(sq))
