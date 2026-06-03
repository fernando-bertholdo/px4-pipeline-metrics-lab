#!/usr/bin/env python3
"""Gera os gráficos do experimento a partir de data/metrics_runs.csv.

Produz PNGs em figures/ (formato escolhido para colar no relatório):
  fig1_total_per_run.png      tempo total do pipeline por execução      [obrigatório 1]
  fig2_time_per_job.png       tempo por job (lint x test), empilhado     [obrigatório 2]
  fig3_success_failure.png    taxa de sucesso x falha                    [obrigatório 3]
  fig4_tests_vs_duration.png  nº de testes x duração do pipeline         [obrigatório 4]
  fig5_cache_effect.png       efeito do cache (média ± desvio)           [diferencial]
  fig6_parallel_effect.png    efeito do paralelismo (média ± desvio)     [diferencial]
  fig7_pareto_steps.png       Pareto de gargalos por etapa               [diferencial]

Também grava data/summary_stats.csv (média/desvio/n por variação).

Uso: python3 scripts/make_graphs.py [--data-dir data] [--fig-dir figures]
Requisitos: pandas, matplotlib  (pip install -r requirements-analysis.txt)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

OK_COLOR = "#2e7d32"
FAIL_COLOR = "#c62828"
BAR1 = "#1565c0"
BAR2 = "#90caf9"
ACCENT = "#ef6c00"
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True, "grid.alpha": 0.3})


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df.get(col), errors="coerce")


def load(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "metrics_runs.csv")
    for c in [
        "workflow_duration", "lead_time_s", "test_count", "test_failures",
        "avg_test_time_s", "lint_duration_s", "test_duration_s", "install_deps_s",
    ]:
        if c in df.columns:
            df[c] = _num(df, c)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["run_label"] = [f"R{i+1}\n{v}" for i, v in enumerate(df["variation"].fillna(""))]
    return df


def fig1_total_per_run(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = [OK_COLOR if str(s) == "success" else FAIL_COLOR for s in df["status"]]
    ax.bar(range(len(df)), df["workflow_duration"], color=colors)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["run_label"], rotation=90, fontsize=7)
    ax.set_ylabel("Duração do workflow (s)")
    ax.set_title("Tempo total do pipeline por execução (verde=sucesso, vermelho=falha)")
    for i, v in enumerate(df["workflow_duration"]):
        if pd.notna(v):
            ax.text(i, v + 0.5, f"{v:.0f}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig2_time_per_job(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    lint = df["lint_duration_s"].fillna(0)
    test = df["test_duration_s"].fillna(0)
    x = range(len(df))
    ax.bar(x, lint, label="lint", color=BAR2)
    ax.bar(x, test, bottom=lint, label="test", color=BAR1)
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["run_label"], rotation=90, fontsize=7)
    ax.set_ylabel("Duração do job (s)")
    ax.set_title("Tempo por job (lint x test) empilhado por execução")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig3_success_failure(df: pd.DataFrame, out: Path) -> None:
    counts = df["status"].value_counts()
    fig, ax = plt.subplots(figsize=(6, 5))
    labels = list(counts.index)
    colors = [OK_COLOR if str(label_) == "success" else FAIL_COLOR for label_ in labels]
    ax.bar(labels, counts.values, color=colors)
    for i, v in enumerate(counts.values):
        ax.text(i, v + 0.05, str(v), ha="center", va="bottom")
    ax.set_ylabel("Nº de execuções")
    total = int(counts.sum())
    ok = int(counts.get("success", 0))
    ax.set_title(f"Sucesso x falha — {ok}/{total} verdes ({100*ok/total:.0f}%)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig4_tests_vs_duration(df: pd.DataFrame, out: Path) -> None:
    sub = df.dropna(subset=["test_count", "workflow_duration"])
    fig, ax = plt.subplots(figsize=(8, 6))
    ok = sub[sub["status"] == "success"]
    bad = sub[sub["status"] != "success"]
    ax.scatter(ok["test_count"], ok["workflow_duration"], color=BAR1, s=60, label="sucesso")
    ax.scatter(bad["test_count"], bad["workflow_duration"], color=FAIL_COLOR, s=60, label="falha")
    if len(sub) >= 2 and sub["test_count"].nunique() >= 2:
        import numpy as np

        m, b = np.polyfit(sub["test_count"], sub["workflow_duration"], 1)
        xs = np.linspace(sub["test_count"].min(), sub["test_count"].max(), 50)
        ax.plot(xs, m * xs + b, "--", color=ACCENT, label=f"tendência: {m:.3f}s/teste")
    ax.set_xlabel("Quantidade de testes executados")
    ax.set_ylabel("Duração do workflow (s)")
    ax.set_title("Relação entre quantidade de testes e duração do pipeline")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def _group_stats(df: pd.DataFrame, labels: list[str], col: str) -> pd.DataFrame:
    sub = df[df["variation"].isin(labels)]
    g = sub.groupby("variation")[col].agg(["mean", "std", "count"]).reindex(labels).dropna(how="all")
    g["std"] = g["std"].fillna(0.0)
    return g


def fig5_cache_effect(df: pd.DataFrame, out: Path) -> None:
    g = _group_stats(df, ["no_cache", "baseline"], "install_deps_s")
    if g.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 5))
    names = {"baseline": "cache ON", "no_cache": "cache OFF"}
    xs = [names.get(i, i) for i in g.index]
    ax.bar(xs, g["mean"], yerr=g["std"], capsize=6, color=[OK_COLOR, FAIL_COLOR][: len(g)])
    for i, (m, n) in enumerate(zip(g["mean"], g["count"], strict=False)):
        ax.text(i, m, f"{m:.1f}s (n={int(n)})", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("Duração do passo 'Install dev deps' (s)")
    ax.set_title("Efeito do cache de pip (média ± desvio)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig6_parallel_effect(df: pd.DataFrame, out: Path) -> None:
    labels = ["baseline", "pytest_parallel", "jobs_parallel"]
    g = _group_stats(df, labels, "workflow_duration")
    if g.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    pretty = {
        "baseline": "baseline\n(seq)",
        "pytest_parallel": "pytest -n auto\n(intra-job)",
        "jobs_parallel": "jobs paralelos\n(sem needs)",
    }
    xs = [pretty.get(i, i) for i in g.index]
    ax.bar(xs, g["mean"], yerr=g["std"], capsize=6, color=BAR1)
    for i, (m, n) in enumerate(zip(g["mean"], g["count"], strict=False)):
        ax.text(i, m, f"{m:.0f}s (n={int(n)})", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("Duração do workflow (s)")
    ax.set_title("Efeito do paralelismo no tempo total (média ± desvio)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig7_pareto_steps(data_dir: Path, out: Path) -> None:
    """Pareto dos gargalos: duração média por etapa (steps) no run baseline."""
    runs = json.loads((data_dir / "metrics.json").read_text())
    base = [r for r in runs if (r.get("status") == "success")]
    if not base:
        base = runs
    durations: dict[str, list[float]] = {}
    for r in base:
        for job in r.get("jobs", []):
            for s in job.get("steps", []):
                d = s.get("duration_s")
                if d:
                    durations.setdefault(f"{job['name']}/{s['name']}", []).append(d)
    if not durations:
        return
    means = {k: sum(v) / len(v) for k, v in durations.items()}
    items = sorted(means.items(), key=lambda kv: kv[1], reverse=True)[:8]
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(range(len(names))[::-1], vals, color=ACCENT)
    ax.set_yticks(range(len(names))[::-1])
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Duração média da etapa (s)")
    ax.set_title("Pareto de gargalos — onde o pipeline gasta tempo (profile, não palpite)")
    for i, v in enumerate(vals[::-1]):
        ax.text(v, i, f" {v:.1f}s", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def write_summary(df: pd.DataFrame, out: Path) -> None:
    g = df.groupby("variation").agg(
        n=("workflow_duration", "count"),
        wf_mean=("workflow_duration", "mean"),
        wf_std=("workflow_duration", "std"),
        test_mean=("test_duration_s", "mean"),
        install_mean=("install_deps_s", "mean"),
        tests=("test_count", "max"),
    )
    g.to_csv(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--fig-dir", default="figures")
    args = ap.parse_args()
    data_dir, fig_dir = Path(args.data_dir), Path(args.fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = load(data_dir)
    fig1_total_per_run(df, fig_dir / "fig1_total_per_run.png")
    fig2_time_per_job(df, fig_dir / "fig2_time_per_job.png")
    fig3_success_failure(df, fig_dir / "fig3_success_failure.png")
    fig4_tests_vs_duration(df, fig_dir / "fig4_tests_vs_duration.png")
    fig5_cache_effect(df, fig_dir / "fig5_cache_effect.png")
    fig6_parallel_effect(df, fig_dir / "fig6_parallel_effect.png")
    fig7_pareto_steps(data_dir, fig_dir / "fig7_pareto_steps.png")
    write_summary(df, data_dir / "summary_stats.csv")
    print(f"OK: gráficos em {fig_dir}/ e summary_stats.csv em {data_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
