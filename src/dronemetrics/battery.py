"""Estimativas simples de energia de bateria para uma missão."""

from __future__ import annotations


def battery_consumption_wh(distance_m: float, avg_power_w: float, speed_mps: float) -> float:
    """Energia consumida (Wh) para percorrer `distance_m` a `speed_mps` com `avg_power_w`.

    Modelo: energia = potência média x tempo de voo; tempo = distância / velocidade.

    >>> round(battery_consumption_wh(1000.0, 180.0, 10.0), 1)
    5.0
    """
    if speed_mps <= 0:
        raise ValueError("speed_mps deve ser positivo")
    if distance_m < 0 or avg_power_w < 0:
        raise ValueError("distância e potência não podem ser negativas")
    flight_time_h = (distance_m / speed_mps) / 3600.0
    return avg_power_w * flight_time_h


def remaining_capacity_pct(capacity_wh: float, consumed_wh: float) -> float:
    """Percentual de bateria restante, limitado ao intervalo [0, 100]."""
    if capacity_wh <= 0:
        raise ValueError("capacity_wh deve ser positivo")
    pct = 100.0 * (capacity_wh - consumed_wh) / capacity_wh
    return max(0.0, min(100.0, pct))
