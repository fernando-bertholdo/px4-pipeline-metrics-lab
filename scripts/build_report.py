#!/usr/bin/env python3
"""Report-as-code: injeta dados reais + figuras no template do relatório.

Lê docs/relatorio.template.md e substitui os marcadores abaixo por conteúdo
gerado a partir de data/*.csv, garantindo que o relatório seja 100%
reproduzível a partir dos dados coletados:

  <!--RUNS_TABLE-->     tabela de execuções reais (run_id + link + variação)
  <!--SUMMARY_TABLE-->  estatísticas por variação (média/desvio/n)
  <!--GENERATED_AT-->   timestamp de geração

Uso: python3 scripts/build_report.py --repo OWNER/REPO
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def runs_table(rows: list[dict], repo: str) -> str:
    head = (
        "| # | run_id | variação | status | workflow (s) | testes | falhas | link |\n"
        "|---|--------|----------|--------|--------------|--------|--------|------|\n"
    )
    body = []
    for i, r in enumerate(rows, 1):
        rid = r["run_id"]
        link = f"https://github.com/{repo}/actions/runs/{rid}"
        body.append(
            f"| {i} | `{rid}` | {r.get('variation','')} | {r.get('status','')} "
            f"| {r.get('workflow_duration','')} | {r.get('test_count','')} "
            f"| {r.get('test_failures','')} | [run]({link}) |"
        )
    return head + "\n".join(body)


def summary_table(rows: list[dict]) -> str:
    head = (
        "| variação | n | tempo médio (s) | desvio (s) | testes |\n"
        "|----------|---|-----------------|------------|--------|\n"
    )
    body = []
    for r in rows:
        def fmt(x: str) -> str:
            try:
                return f"{float(x):.1f}"
            except (ValueError, TypeError):
                return "—"

        body.append(
            f"| {r.get('variation','')} | {r.get('n','')} | {fmt(r.get('wf_mean',''))} "
            f"| {fmt(r.get('wf_std',''))} | {r.get('tests','')} |"
        )
    return head + "\n".join(body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--template", default="docs/relatorio.template.md")
    ap.add_argument("--out", default="docs/relatorio.md")
    args = ap.parse_args()

    data = Path(args.data_dir)
    template = Path(args.template).read_text()

    runs = read_csv(data / "metrics_runs.csv")
    summary = read_csv(data / "summary_stats.csv")

    out = (
        template.replace("<!--RUNS_TABLE-->", runs_table(runs, args.repo))
        .replace("<!--SUMMARY_TABLE-->", summary_table(summary))
        .replace("<!--GENERATED_AT-->", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
        .replace("<!--REPO-->", args.repo)
    )
    Path(args.out).write_text(out)
    print(f"OK: {args.out} gerado a partir de {len(runs)} runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
