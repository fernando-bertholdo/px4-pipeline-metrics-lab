REPO ?= fernando-bertholdo/px4-pipeline-metrics-lab

.PHONY: test lint collect collect-raw graphs report reproduce experiment

test:
	pytest

lint:
	ruff check .

## Coleta via API (precisa de GITHUB_TOKEN; ex.: export GITHUB_TOKEN=$$(gh auth token))
collect:
	python3 scripts/collect_metrics.py --repo $(REPO) --source api

## Coleta a partir do JSON bruto já baixado (sem rede/token)
collect-raw:
	python3 scripts/collect_metrics.py --repo $(REPO) --source raw

graphs:
	python3 scripts/make_graphs.py

report:
	python3 scripts/build_report.py --repo $(REPO)

## Refaz dataset + gráficos + relatório a partir de data/raw/
reproduce: collect-raw graphs report
	@echo "Reprodução concluída: data/, figures/, docs/relatorio.md"

## Roda o experimento inteiro (cria os ~17 commits/runs reais)
experiment:
	bash scripts/run_experiment.sh
