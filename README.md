# px4-pipeline-metrics-lab

Experimento prático de **performance de pipeline CI/CD** no GitHub Actions —
Inteli, Módulo 10, Aula 11 ("Performance no SITL e CI"). O projeto-cobaia é a
mini-lib **`dronemetrics`** (KPIs de missão de drone: distância, RMS de
trajetória, bateria, duração), escolhida por ser determinística, rápida e
barata em CI — o que dá um sinal limpo para medir o **pipeline**, não o app.

> **Tese da Aula 11 que este experimento testa empiricamente:** *"pipeline
> correto não é pipeline rápido; você não melhora o que não mede"*. Aqui a
> gente mede, com dados reais, o efeito de cache e paralelismo — e checa se o
> que o professor previu acontece no nosso runner.

## O que tem aqui

```
src/dronemetrics/        a biblioteca sob teste (funções puras de KPI)
tests/                   pytest; knobs do experimento em tests/experiment_config.py
.github/workflows/ci.yml pipeline: install -> lint (ruff) -> test (pytest+junit+cov) -> artefato
experiment.env           knobs lidos pelo workflow (cache, paralelismo, escala, slow, fail)
scripts/
  run_experiment.sh      aplica as ~17 variações (1 fator/commit) e espera cada run
  fetch_raw.sh           baixa o JSON bruto dos runs via `gh api`
  collect_metrics.py     API GitHub (ou raw) -> data/metrics.csv (+runs +json)  [stdlib]
  make_graphs.py         data -> figures/*.png  (matplotlib)
  build_report.py        injeta dados+figuras no relatório (report-as-code)
data/                    metrics.csv, metrics_runs.csv, metrics.json, variation_log.csv
figures/                 gráficos PNG
docs/experimento.md      desenho do experimento (hipóteses + matriz)
docs/relatorio.md        relatório técnico final (gerado)
```

## Métricas coletadas (via API, não copiadas da interface)

`run_id, commit_sha, commit_message, status, workflow_duration, job_name,
job_duration, test_count, test_failures, timestamp` (schema obrigatório, uma
linha por job em `data/metrics.csv`) + opcionais em `data/metrics_runs.csv`:
*lead time* (commit→fim), tempo do *install* (proxy do cache), tempo médio de
teste, tentativas, duração por job e por etapa.

## Reproduzir o experimento

Pré-requisitos: `gh` autenticado (`gh auth login`), Python 3.10+.

```bash
# 1. criar o repo e subir o baseline (uma vez)
gh repo create px4-pipeline-metrics-lab --public --source=. --remote=origin --push

# 2. rodar as ~17 variações (cada uma dispara 1 run e espera concluir)
bash scripts/run_experiment.sh

# 3. coletar as métricas reais (API) e gerar dataset
export GITHUB_TOKEN=$(gh auth token)
python3 scripts/collect_metrics.py --repo <owner>/px4-pipeline-metrics-lab

# 4. gráficos + relatório
pip install -r requirements-analysis.txt
python3 scripts/make_graphs.py
python3 scripts/build_report.py --repo <owner>/px4-pipeline-metrics-lab
```

Atalhos no `Makefile`: `make collect`, `make graphs`, `make report`,
`make reproduce` (refaz dataset+gráficos+relatório a partir de `data/raw/`).

## Rodar os testes localmente

```bash
pip install -r requirements-dev.txt
pytest                       # baseline (~98 testes)
DRONEMETRICS_TEST_SCALE=4 pytest   # simula a variação "4x testes"
ruff check .
```

## Mapa para o enunciado

| Exigência | Onde |
|-----------|------|
| Pipeline (deps, lint, testes, artefato, métricas) | `.github/workflows/ci.yml` |
| ≥12 execuções com variações controladas | `scripts/run_experiment.sh` (17 runs) |
| Script Python que consulta a API e gera CSV/JSON | `scripts/collect_metrics.py` |
| ≥4 gráficos | `figures/` (7 gráficos) |
| Relatório com as 8 perguntas + evidências reais | `docs/relatorio.md` |
| Reprodutibilidade | este README + `Makefile` + `scripts/` |
