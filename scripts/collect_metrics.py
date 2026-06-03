#!/usr/bin/env python3
"""Coletor de métricas do pipeline CI/CD (GitHub Actions).

Consulta a API REST do GitHub (ou lê o cache bruto em data/raw/) e produz uma
base de dados estruturada com as métricas de cada execução do workflow.

Sem dependências de terceiros (apenas stdlib), então roda em qualquer lugar:
no seu Mac, no runner do CI ou no sandbox de análise.

Saídas (em --out-dir, default data/):
  * metrics.csv          -> uma linha por (run, job), no schema exigido:
        run_id,commit_sha,commit_message,status,workflow_duration,
        job_name,job_duration,test_count,test_failures,timestamp
  * metrics_runs.csv     -> uma linha por run (métricas agregadas + opcionais
        + label/hipótese da variação, se data/variation_log.csv existir)
  * metrics.json         -> estrutura completa (runs, jobs, steps)

Modos:
  --source api  (default)  consulta a API; precisa de GITHUB_TOKEN no ambiente.
                           Também grava o JSON bruto em --raw-dir (vira cache).
  --source raw             lê de --raw-dir (gerado por scripts/fetch_raw.sh ou
                           por uma execução anterior em modo api). Não precisa
                           de token nem de rede.

Exemplos:
  GITHUB_TOKEN=$(gh auth token) \\
    python3 scripts/collect_metrics.py --repo fernando-bertholdo/px4-pipeline-metrics-lab
  python3 scripts/collect_metrics.py --repo OWNER/REPO --source raw
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

API = "https://api.github.com"
WORKFLOW_FILE = "ci.yml"


# --------------------------------------------------------------------------- #
# Utilidades de tempo
# --------------------------------------------------------------------------- #
def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def seconds_between(start: str | None, end: str | None) -> float | None:
    s, e = parse_iso(start), parse_iso(end)
    if s is None or e is None:
        return None
    return round((e - s).total_seconds(), 3)


def first_line(text: str | None) -> str:
    if not text:
        return ""
    return text.splitlines()[0] if text.splitlines() else ""


# --------------------------------------------------------------------------- #
# Cliente HTTP mínimo da API do GitHub (stdlib)
# --------------------------------------------------------------------------- #
class GitHub:
    def __init__(self, token: str) -> None:
        self.token = token

    def _request(self, url: str) -> tuple[bytes, dict[str, str]]:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "dronemetrics-collector")
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return resp.read(), dict(resp.headers)

    def get_json(self, path: str) -> dict:
        data, _ = self._request(path if path.startswith("http") else API + path)
        return json.loads(data)

    def get_paginated(self, path: str, key: str) -> list[dict]:
        items: list[dict] = []
        url = API + path + ("&" if "?" in path else "?") + "per_page=100"
        while url:
            data, headers = self._request(url)
            payload = json.loads(data)
            items.extend(payload.get(key, []))
            url = _next_link(headers.get("Link", ""))
        return items

    def get_bytes(self, url: str) -> bytes:
        data, _ = self._request(url)
        return data


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        segs = part.split(";")
        if len(segs) < 2:
            continue
        url = segs[0].strip().strip("<>")
        if 'rel="next"' in segs[1]:
            return url
    return None


# --------------------------------------------------------------------------- #
# JUnit
# --------------------------------------------------------------------------- #
def parse_junit(xml_bytes: bytes) -> dict:
    """Retorna {tests, failures, errors, skipped, time} somando todos testsuites."""
    out = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    suites = root.iter("testsuite")
    for s in suites:
        out["tests"] += int(s.get("tests", 0))
        out["failures"] += int(s.get("failures", 0))
        out["errors"] += int(s.get("errors", 0))
        out["skipped"] += int(s.get("skipped", 0))
        out["time"] += float(s.get("time", 0.0) or 0.0)
    return out


def junit_from_artifacts(gh: GitHub, run_id: int, raw_dir: Path) -> dict | None:
    """Baixa o artifact 'test-reports' do run, extrai junit.xml e parseia."""
    arts = gh.get_json(f"/repos/{REPO}/actions/runs/{run_id}/artifacts")
    for art in arts.get("artifacts", []):
        if art.get("name") == "test-reports":
            blob = gh.get_bytes(art["archive_download_url"])
            try:
                zf = zipfile.ZipFile(BytesIO(blob))
            except zipfile.BadZipFile:
                return None
            for name in zf.namelist():
                if name.endswith("junit.xml"):
                    xml_bytes = zf.read(name)
                    (raw_dir / "junit").mkdir(parents=True, exist_ok=True)
                    (raw_dir / "junit" / f"{run_id}.xml").write_bytes(xml_bytes)
                    return parse_junit(xml_bytes)
    return None


# --------------------------------------------------------------------------- #
# Coleta
# --------------------------------------------------------------------------- #
def collect_from_api(gh: GitHub, raw_dir: Path) -> list[dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    runs = gh.get_paginated(f"/repos/{REPO}/actions/runs", "workflow_runs")
    runs = [r for r in runs if str(r.get("path", "")).endswith(WORKFLOW_FILE)]
    (raw_dir / "runs.json").write_text(json.dumps(runs, indent=2))
    records = []
    for r in runs:
        rid = r["id"]
        timing = gh.get_json(f"/repos/{REPO}/actions/runs/{rid}/timing")
        jobs = gh.get_json(f"/repos/{REPO}/actions/runs/{rid}/jobs")
        (raw_dir / f"timing_{rid}.json").write_text(json.dumps(timing, indent=2))
        (raw_dir / f"jobs_{rid}.json").write_text(json.dumps(jobs, indent=2))
        junit = junit_from_artifacts(gh, rid, raw_dir)
        records.append(_build_record(r, timing, jobs, junit))
    return records


def collect_from_raw(raw_dir: Path) -> list[dict]:
    runs = json.loads((raw_dir / "runs.json").read_text())
    records = []
    for r in runs:
        rid = r["id"]
        timing = _load_json(raw_dir / f"timing_{rid}.json")
        jobs = _load_json(raw_dir / f"jobs_{rid}.json")
        junit_path = raw_dir / "junit" / f"{rid}.xml"
        junit = parse_junit(junit_path.read_bytes()) if junit_path.exists() else None
        records.append(_build_record(r, timing, jobs, junit))
    return records


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _build_record(run: dict, timing: dict, jobs: dict, junit: dict | None) -> dict:
    rid = run["id"]
    run_started = run.get("run_started_at") or run.get("created_at")
    updated = run.get("updated_at")
    commit = run.get("head_commit") or {}
    commit_ts = commit.get("timestamp")

    wf_ms = timing.get("run_duration_ms")
    workflow_duration = (
        round(wf_ms / 1000.0, 3) if wf_ms else seconds_between(run_started, updated)
    )

    job_list = []
    for j in jobs.get("jobs", []):
        steps = [
            {
                "name": s.get("name"),
                "conclusion": s.get("conclusion"),
                "duration_s": seconds_between(s.get("started_at"), s.get("completed_at")),
            }
            for s in j.get("steps", [])
        ]
        job_list.append(
            {
                "name": j.get("name"),
                "conclusion": j.get("conclusion"),
                "duration_s": seconds_between(j.get("started_at"), j.get("completed_at")),
                "steps": steps,
            }
        )

    tests = junit or {}
    executed = max(0, tests.get("tests", 0) - tests.get("skipped", 0))
    failures = tests.get("failures", 0) + tests.get("errors", 0)
    total_time = tests.get("time", 0.0)
    avg_test = round(total_time / executed, 4) if executed else None

    lead_time = seconds_between(commit_ts, updated)

    return {
        "run_id": rid,
        "commit_sha": run.get("head_sha", ""),
        "commit_message": first_line(commit.get("message") or run.get("display_title")),
        "status": run.get("conclusion") or run.get("status") or "",
        "run_attempt": run.get("run_attempt", 1),
        "event": run.get("event", ""),
        "workflow_duration": workflow_duration,
        "timestamp": run_started,
        "lead_time_s": lead_time,
        "test_count": executed,
        "test_failures": failures,
        "test_total_time_s": round(total_time, 3),
        "avg_test_time_s": avg_test,
        "jobs": job_list,
    }


# --------------------------------------------------------------------------- #
# Junção com o log de variações
# --------------------------------------------------------------------------- #
def load_variation_log(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            out[row["commit_sha"]] = row
    return out


# --------------------------------------------------------------------------- #
# Escrita das saídas
# --------------------------------------------------------------------------- #
REQUIRED_COLUMNS = [
    "run_id", "commit_sha", "commit_message", "status", "workflow_duration",
    "job_name", "job_duration", "test_count", "test_failures", "timestamp",
]


def write_metrics_csv(records: list[dict], out: Path) -> None:
    """Schema exigido pelo enunciado: uma linha por (run, job)."""
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        w.writeheader()
        for r in records:
            for job in r["jobs"] or [{"name": "", "duration_s": None}]:
                w.writerow(
                    {
                        "run_id": r["run_id"],
                        "commit_sha": r["commit_sha"][:12],
                        "commit_message": r["commit_message"],
                        "status": r["status"],
                        "workflow_duration": r["workflow_duration"],
                        "job_name": job["name"],
                        "job_duration": job["duration_s"],
                        "test_count": r["test_count"],
                        "test_failures": r["test_failures"],
                        "timestamp": r["timestamp"],
                    }
                )


def write_runs_csv(records: list[dict], variations: dict[str, dict], out: Path) -> None:
    cols = [
        "run_id", "commit_sha", "variation", "hypothesis", "status",
        "workflow_duration", "lead_time_s", "test_count", "test_failures",
        "avg_test_time_s", "run_attempt", "lint_duration_s", "test_duration_s",
        "install_deps_s", "timestamp",
    ]
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            var = variations.get(r["commit_sha"], {})
            jobs_by_name = {j["name"]: j for j in r["jobs"]}
            test_job = jobs_by_name.get("test", {})
            install_s = None
            for s in test_job.get("steps", []):
                if s["name"] and "Install" in s["name"]:
                    install_s = s["duration_s"]
            w.writerow(
                {
                    "run_id": r["run_id"],
                    "commit_sha": r["commit_sha"][:12],
                    "variation": var.get("label", ""),
                    "hypothesis": var.get("hypothesis", ""),
                    "status": r["status"],
                    "workflow_duration": r["workflow_duration"],
                    "lead_time_s": r["lead_time_s"],
                    "test_count": r["test_count"],
                    "test_failures": r["test_failures"],
                    "avg_test_time_s": r["avg_test_time_s"],
                    "run_attempt": r["run_attempt"],
                    "lint_duration_s": jobs_by_name.get("lint", {}).get("duration_s"),
                    "test_duration_s": test_job.get("duration_s"),
                    "install_deps_s": install_s,
                    "timestamp": r["timestamp"],
                }
            )


def main() -> int:
    global REPO
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--source", choices=["api", "raw"], default="api")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--variation-log", default="data/variation_log.csv")
    ap.add_argument(
        "--only-logged",
        action="store_true",
        help="mantém apenas runs cujo commit_sha está no variation_log (descarta runs órfãos/aquecimento)",
    )
    args = ap.parse_args()

    REPO = args.repo
    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.source == "api":
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            print("ERRO: defina GITHUB_TOKEN (ex.: export GITHUB_TOKEN=$(gh auth token))", file=sys.stderr)
            return 2
        try:
            records = collect_from_api(GitHub(token), raw_dir)
        except urllib.error.HTTPError as e:
            print(f"ERRO HTTP {e.code} ao consultar a API: {e.reason}", file=sys.stderr)
            return 1
    else:
        records = collect_from_raw(raw_dir)

    records.sort(key=lambda r: r["timestamp"] or "")
    variations = load_variation_log(Path(args.variation_log))

    if args.only_logged and variations:
        logged = set(variations.keys())
        before = len(records)
        records = [r for r in records if r["commit_sha"] in logged]
        print(f"--only-logged: {len(records)}/{before} runs mantidos (canônicos do variation_log)")

    write_metrics_csv(records, out_dir / "metrics.csv")
    write_runs_csv(records, variations, out_dir / "metrics_runs.csv")
    (out_dir / "metrics.json").write_text(json.dumps(records, indent=2, default=str))

    n_jobs = sum(len(r["jobs"]) for r in records)
    print(f"OK: {len(records)} runs, {n_jobs} jobs -> {out_dir}/metrics.csv, metrics_runs.csv, metrics.json")
    return 0


REPO = ""

if __name__ == "__main__":
    raise SystemExit(main())
