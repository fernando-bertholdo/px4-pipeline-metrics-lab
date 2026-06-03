"""Teste artificialmente lento — desligado por padrão.

Ligado pela variação "teste lento" (ENABLE_SLOW=True), que introduz uma cauda
de duração no job de testes para observar seu efeito no tempo do pipeline.
"""

from __future__ import annotations

import time

import pytest

from tests.experiment_config import ENABLE_SLOW, SLOW_TEST_SECONDS


@pytest.mark.skipif(not ENABLE_SLOW, reason="teste lento desligado (ENABLE_SLOW=False)")
def test_slow_path_simulation() -> None:
    """Simula um teste de integração lento (ex.: cold-start de SITL)."""
    time.sleep(SLOW_TEST_SECONDS)
    assert SLOW_TEST_SECONDS > 0
