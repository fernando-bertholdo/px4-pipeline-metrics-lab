"""dronemetrics — KPIs de missão para drones (PX4/SITL).

Biblioteca didática usada como cobaia de um experimento de performance de
pipeline CI/CD (Inteli, Módulo 10, Aula 11 — Performance no SITL e CI).

Funções puras e determinísticas: fáceis de testar, rápidas e baratas em CI,
o que as torna ideais para medir o comportamento do pipeline sob variações
controladas.
"""

from dronemetrics.battery import battery_consumption_wh, remaining_capacity_pct
from dronemetrics.geo import haversine_m, total_path_length_m
from dronemetrics.mission import estimated_duration_s, waypoint_count
from dronemetrics.trajectory import trajectory_rms_m

__all__ = [
    "haversine_m",
    "total_path_length_m",
    "trajectory_rms_m",
    "battery_consumption_wh",
    "remaining_capacity_pct",
    "estimated_duration_s",
    "waypoint_count",
]

__version__ = "0.1.0"
