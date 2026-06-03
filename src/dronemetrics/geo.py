"""Geometria geográfica: distâncias e comprimento de rota.

Um waypoint é uma tupla (lat, lon) em graus decimais.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

EARTH_RADIUS_M = 6_371_000.0
Waypoint = tuple[float, float]


def haversine_m(a: Waypoint, b: Waypoint) -> float:
    """Distância em metros entre dois pontos (lat, lon) pela fórmula de Haversine.

    >>> round(haversine_m((0.0, 0.0), (0.0, 1.0)))
    111195
    """
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def total_path_length_m(waypoints: Sequence[Waypoint]) -> float:
    """Soma das distâncias entre waypoints consecutivos (perímetro aberto).

    Retorna 0.0 para rotas com menos de dois pontos.
    """
    if len(waypoints) < 2:
        return 0.0
    return sum(
        haversine_m(waypoints[i], waypoints[i + 1])
        for i in range(len(waypoints) - 1)
    )
