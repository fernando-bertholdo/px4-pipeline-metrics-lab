"""Métricas de alto nível de uma missão (contagem e duração)."""

from __future__ import annotations

from collections.abc import Sequence

from dronemetrics.geo import Waypoint, total_path_length_m


def waypoint_count(waypoints: Sequence[Waypoint]) -> int:
    """Número de waypoints da missão."""
    return len(waypoints)


def estimated_duration_s(
    waypoints: Sequence[Waypoint],
    cruise_speed_mps: float,
    seconds_per_waypoint: float = 2.0,
) -> float:
    """Duração estimada da missão (s): tempo de cruzeiro + folga por waypoint.

    A folga `seconds_per_waypoint` modela a desaceleração/aceleração em cada
    waypoint (o drone não passa reto em velocidade máxima).

    >>> estimated_duration_s([(0.0, 0.0), (0.0, 1.0)], 100.0, 0.0) > 1000
    True
    """
    if cruise_speed_mps <= 0:
        raise ValueError("cruise_speed_mps deve ser positivo")
    length = total_path_length_m(waypoints)
    cruise = length / cruise_speed_mps
    overhead = seconds_per_waypoint * max(0, len(waypoints))
    return cruise + overhead
