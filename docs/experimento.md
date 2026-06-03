# Desenho do experimento

> Experimento controlado: medir como **um fator por vez** afeta o tempo e a
> estabilidade do pipeline CI/CD. Cada variação é **um commit** em `main`, que
> dispara **um run** do workflow `ci.yml`. As métricas vêm da API do GitHub
> Actions (não da interface).

## Hipóteses

| ID | Fator alterado | Hipótese (H) |
|----|----------------|--------------|
| H1 | cache de pip ON×OFF | Sem cache, o passo *Install dev deps* fica mais lento; o tempo total sobe. |
| H2 | 1ª execução (cache frio) | O run que **popula** o cache não economiza nada — só execuções seguintes ganham. **(surpresa candidata)** |
| H3 | quantidade de testes (1×→8×) | A duração cresce com o nº de testes, de forma sublinear (há overhead fixo). |
| H4 | teste lento (+30 s) | A cauda de duração passa a dominar o job de teste. |
| H5 | teste falhando | `status=failure`; o run pode ficar **mais curto** (fail-fast). |
| H6 | `pytest -n auto` (xdist) | "Paralelizar acelera." **Provável surpresa:** em suíte pequena, o overhead de workers deixa **mais lento**. |
| H7 | xdist com carga maior (4×) | Com mais testes, o paralelismo intra-job passa a compensar. |
| H8 | jobs paralelos (sem `needs`) | Rodar `lint` e `test` concorrentes reduz o *wall-time* total. |

## Matriz de execuções (≥12; 17 runs com repetições para variância)

| # | Variação (label) | Knobs vs baseline | Repetições |
|---|------------------|-------------------|------------|
| 1–3 | `baseline` | — (cache on, jobs seq, 1× testes) | 3× |
| 4–5 | `no_cache` | `CACHE=off` | 2× |
| 6 | `tests_2x` | `TEST_SCALE=2` | 1× |
| 7 | `tests_4x` | `TEST_SCALE=4` | 1× |
| 8 | `tests_8x` | `TEST_SCALE=8` | 1× |
| 9 | `slow_test` | `ENABLE_SLOW=on` | 1× |
| 10 | `failing` | `FORCE_FAIL=on` | 1× |
| 11–12 | `pytest_parallel` | `PYTEST_PARALLEL=on` (`-n auto`) | 2× |
| 13 | `pytest_parallel_4x` | `-n auto` + `TEST_SCALE=4` | 1× |
| 14–15 | `jobs_parallel` | remove `needs: lint` | 2× |
| 16 | `jobs_parallel_2x` | sem `needs` + `TEST_SCALE=2` | 1× |
| 17 | `baseline_final` | — (checagem de drift) | 1× |

As repetições (baseline 3×, no_cache 2×, pytest_parallel 2×, jobs_parallel 2×)
permitem calcular **média ± desvio** e separar o sinal do ruído do runner
compartilhado do GitHub.

## Como as variações viram commits

- Knobs de *step* (`CACHE`, `PYTEST_PARALLEL`, `TEST_SCALE`, `ENABLE_SLOW`,
  `FORCE_FAIL`) ficam em **`experiment.env`**, lido pelo workflow para o
  `$GITHUB_ENV`. Mudar a variação = editar uma linha.
- Paralelismo de **jobs** é estrutural: a linha `needs: lint  # MARKER:NEEDS`
  é alternada pelo driver (`scripts/run_experiment.sh`).
- Cada commit registra `commit_sha → label → hipótese → knobs` em
  `data/variation_log.csv`, que o coletor junta às métricas.

## Métricas coletadas

Obrigatórias: tempo total do workflow, tempo por job, tempo por etapa, status
(sucesso/falha), nº de testes, nº de falhas, tempo médio de teste, commit, data/hora,
mensagem do commit. Opcionais: tempo do *install* (proxy do cache economizado),
*lead time* (commit→fim), tentativas (`run_attempt`).
