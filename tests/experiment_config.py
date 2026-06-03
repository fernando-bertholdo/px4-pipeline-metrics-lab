"""Knobs do experimento de performance de pipeline.

O driver `scripts/run_experiment.sh` edita ESTE arquivo (e o ci.yml) para
produzir cada variação controlada — um fator por commit. Manter os knobs
centralizados aqui torna cada diff mínimo e auditável.

  TEST_SCALE  -> multiplica a quantidade de testes gerados (carga de teste).
  ENABLE_SLOW -> liga um teste artificialmente lento (cauda de duração).
  FORCE_FAIL  -> faz um teste-canário falhar (run com status=failure).

Os valores também podem ser sobrescritos por variáveis de ambiente de mesmo
nome, o que permite variações sem alterar o arquivo, se necessário.
"""

from __future__ import annotations

import os


def _as_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _as_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- baseline (cada variação altera no máximo um destes) ---
TEST_SCALE: int = _as_int("DRONEMETRICS_TEST_SCALE", 1)
ENABLE_SLOW: bool = _as_bool("DRONEMETRICS_ENABLE_SLOW", False)
FORCE_FAIL: bool = _as_bool("DRONEMETRICS_FORCE_FAIL", False)

# Quantidade-base de casos no teste parametrizado de carga (x TEST_SCALE).
BASE_GENERATED_CASES: int = 40
SLOW_TEST_SECONDS: float = 30.0
