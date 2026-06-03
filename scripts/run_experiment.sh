#!/usr/bin/env bash
# Driver do experimento: aplica ~17 variações controladas (um fator por commit),
# faz push de cada uma e espera o run do GitHub Actions concluir antes da próxima.
#
# Pré-requisitos: estar na raiz do repo, com `gh` autenticado e remote `origin`
# já configurado (ver README / bootstrap). Cada variação parte do BASELINE e
# muda exatamente um fator, para um diff mínimo e auditável.
#
# Uso: bash scripts/run_experiment.sh
set -uo pipefail

LOG="data/raw/run_experiment.log"
mkdir -p data/raw
echo "commit_sha,label,hypothesis,knobs" > data/variation_log.csv

# Identidade de commit (e-mail noreply do GitHub -> atribui à conta sem expor e-mail)
EMAIL="$(gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"' 2>/dev/null || echo 'noreply@users.noreply.github.com')"
git config user.name  "Fernando Bertholdo"
git config user.email "$EMAIL"

# --- estado dos knobs (resetado ao baseline antes de cada variação) ---
CACHE=on; PARALLEL=off; SCALE=1; SLOW=off; FAIL=off; JOBS=seq
reset_baseline() { CACHE=on; PARALLEL=off; SCALE=1; SLOW=off; FAIL=off; JOBS=seq; }

write_env() {
  cat > experiment.env <<EOF
CACHE=$CACHE
PYTEST_PARALLEL=$PARALLEL
TEST_SCALE=$SCALE
ENABLE_SLOW=$SLOW
FORCE_FAIL=$FAIL
EOF
}

set_needs() {  # $1 = seq|parallel
  python3 - "$1" <<'PY'
import sys, re
mode = sys.argv[1]
p = ".github/workflows/ci.yml"
s = open(p).read()
target = "    needs: lint  # MARKER:NEEDS" if mode == "seq" \
         else "    # MARKER:NEEDS (parallel: sem needs)"
s = re.sub(r"^.*# MARKER:NEEDS.*$", target, s, count=1, flags=re.M)
open(p, "w").write(s)
PY
}

wait_for_run() {  # $1 = sha
  local sha="$1" rid="" tries=0
  while :; do
    rid=$(gh run list --workflow=ci.yml --limit 25 --json databaseId,headSha \
            --jq ".[] | select(.headSha==\"$sha\") | .databaseId" 2>/dev/null | head -1)
    [ -n "$rid" ] && break
    tries=$((tries + 1)); [ "$tries" -gt 40 ] && { echo "    [warn] run não apareceu p/ ${sha:0:7}"; return 1; }
    sleep 4
  done
  echo "    run $rid (sha ${sha:0:7}) — aguardando conclusão..."
  gh run watch "$rid" --exit-status >/dev/null 2>&1 || true
  local concl; concl=$(gh run view "$rid" --json conclusion --jq .conclusion 2>/dev/null)
  echo "    -> run $rid: ${concl:-desconhecido}"
}

variation() {  # $1 label  $2 hypothesis  $3 commit-subject
  write_env; set_needs "$JOBS"
  git add experiment.env .github/workflows/ci.yml
  git commit -q --allow-empty -m "$3"
  local sha; sha=$(git rev-parse HEAD)
  printf '%s,%s,"%s","%s"\n' "$sha" "$1" "$2" \
    "CACHE=$CACHE;PYTEST_PARALLEL=$PARALLEL;SCALE=$SCALE;SLOW=$SLOW;FAIL=$FAIL;JOBS=$JOBS" \
    >> data/variation_log.csv
  git push -q origin main
  echo "[$(date +%H:%M:%S)] $1 — ${3}"
  wait_for_run "$sha"
}

echo "===== início do experimento: $(date) ====="

# 1-3: baseline (o 1o popula o cache de pip; repetições dão variância)
reset_baseline;                 variation baseline           "tempo de referência; 1o run popula o cache (cache frio)"      "ci: baseline #1 (cache on, jobs sequenciais, 1x)"
reset_baseline;                 variation baseline           "repetição p/ variância (cache quente)"                        "ci: baseline #2 [repeat]"
reset_baseline;                 variation baseline           "repetição p/ variância (cache quente)"                        "ci: baseline #3 [repeat]"
# 4-5: sem cache
reset_baseline; CACHE=off;      variation no_cache           "sem cache aumenta o install de deps"                          "ci: no_cache #1 (CACHE=off)"
reset_baseline; CACHE=off;      variation no_cache           "repetição p/ variância do efeito de cache"                    "ci: no_cache #2 (CACHE=off) [repeat]"
# 6-8: escala de testes
reset_baseline; SCALE=2;        variation tests_2x           "2x testes: duração sobe de forma sublinear"                   "ci: tests_2x (TEST_SCALE=2)"
reset_baseline; SCALE=4;        variation tests_4x           "4x testes"                                                    "ci: tests_4x (TEST_SCALE=4)"
reset_baseline; SCALE=8;        variation tests_8x           "8x testes: reforça a regressão testes x duração"              "ci: tests_8x (TEST_SCALE=8)"
# 9: teste lento
reset_baseline; SLOW=on;        variation slow_test          "1 teste de 30s domina a cauda de duração"                     "ci: slow_test (ENABLE_SLOW=on)"
# 10: falha controlada
reset_baseline; FAIL=on;        variation failing            "status=failure; fail-fast pode encurtar o run"                "ci: failing (FORCE_FAIL=on)"
# 11-13: paralelismo intra-job (xdist) — SURPRESA esperada
reset_baseline; PARALLEL=on;    variation pytest_parallel    "SURPRESA: xdist deixa a suíte pequena MAIS lenta (overhead)"   "ci: pytest_parallel #1 (-n auto)"
reset_baseline; PARALLEL=on;    variation pytest_parallel    "repetição p/ variância"                                       "ci: pytest_parallel #2 (-n auto) [repeat]"
reset_baseline; PARALLEL=on; SCALE=4; variation pytest_parallel_4x "com carga maior (4x) o paralelismo passa a compensar?"  "ci: pytest_parallel_4x (-n auto, 4x)"
# 14-16: paralelismo de jobs (sem needs)
reset_baseline; JOBS=parallel;  variation jobs_parallel      "jobs concorrentes reduzem o wall-time total"                  "ci: jobs_parallel #1 (sem needs)"
reset_baseline; JOBS=parallel;  variation jobs_parallel      "repetição p/ variância"                                       "ci: jobs_parallel #2 (sem needs) [repeat]"
reset_baseline; JOBS=parallel; SCALE=2; variation jobs_parallel_2x "jobs paralelos + 2x testes"                            "ci: jobs_parallel_2x (sem needs, 2x)"
# 17: baseline final (checagem de drift)
reset_baseline;                 variation baseline_final     "checagem de drift no fim do experimento"                      "ci: baseline_final (cache on, seq)"

# volta o repo ao estado baseline e versiona os metadados sem disparar run novo
reset_baseline; write_env; set_needs seq
git add experiment.env .github/workflows/ci.yml data/variation_log.csv
git commit -q -m "chore: volta ao baseline + variation_log [skip ci]" || true
git push -q origin main || true

echo "===== fim do experimento: $(date) ====="
echo "DONE" > data/raw/experiment_done.flag
