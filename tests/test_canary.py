"""Teste-canário — passa por padrão, falha quando FORCE_FAIL=True.

Usado pela variação "commit com teste falhando" para gerar um run com
status=failure de forma controlada e reversível.
"""

from __future__ import annotations

from tests.experiment_config import FORCE_FAIL


def test_canary_pipeline_health() -> None:
    assert FORCE_FAIL is False, "variação controlada: teste-canário forçado a falhar"
