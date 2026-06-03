#!/usr/bin/env bash
# Baixa o JSON bruto das execuções do workflow via `gh api` (sem deps Python no Mac).
# Gera data/raw/{runs.json, timing_<id>.json, jobs_<id>.json, junit/<id>.xml}.
# Uso: scripts/fetch_raw.sh OWNER/REPO [RAW_DIR]
set -euo pipefail

REPO="${1:?uso: fetch_raw.sh OWNER/REPO [RAW_DIR]}"
RAW="${2:-data/raw}"
mkdir -p "$RAW/junit"

echo "Baixando lista de runs de $REPO ..."
gh api --paginate "/repos/$REPO/actions/runs?per_page=100" --jq '.workflow_runs[]' > "$RAW/runs.jsonl"

python3 - "$RAW" <<'PY'
import sys, json
raw = sys.argv[1]
objs = [json.loads(l) for l in open(f"{raw}/runs.jsonl") if l.strip()]
objs = [o for o in objs if str(o.get("path", "")).endswith("ci.yml")]
json.dump(objs, open(f"{raw}/runs.json", "w"), indent=2)
open(f"{raw}/ids.txt", "w").write("\n".join(str(o["id"]) for o in objs))
print(f"{len(objs)} runs do ci.yml")
PY

while read -r id; do
  [ -z "$id" ] && continue
  echo "  run $id: timing + jobs + artifact"
  gh api "/repos/$REPO/actions/runs/$id/timing" > "$RAW/timing_$id.json" 2>/dev/null || echo '{}' > "$RAW/timing_$id.json"
  gh api "/repos/$REPO/actions/runs/$id/jobs" > "$RAW/jobs_$id.json"
  artid=$(gh api "/repos/$REPO/actions/runs/$id/artifacts" \
            --jq '.artifacts[] | select(.name=="test-reports") | .id' 2>/dev/null | head -1 || true)
  if [ -n "${artid:-}" ]; then
    if gh api "/repos/$REPO/actions/artifacts/$artid/zip" > "$RAW/art_$id.zip" 2>/dev/null && [ -s "$RAW/art_$id.zip" ]; then
      python3 - "$RAW" "$id" <<'PY'
import sys, zipfile, os
raw, rid = sys.argv[1], sys.argv[2]
try:
    z = zipfile.ZipFile(f"{raw}/art_{rid}.zip")
    for n in z.namelist():
        if n.endswith("junit.xml"):
            open(f"{raw}/junit/{rid}.xml", "wb").write(z.read(n))
            break
except Exception as e:
    print(f"  (artifact zip ilegível: {e})")
finally:
    if os.path.exists(f"{raw}/art_{rid}.zip"):
        os.remove(f"{raw}/art_{rid}.zip")
PY
    fi
  fi
done < "$RAW/ids.txt"

rm -f "$RAW/runs.jsonl" "$RAW/ids.txt"
echo "Pronto. Raw em $RAW/"
