#!/usr/bin/env bash
# run_gate_tests.sh — the code-enforced regressions from TEST-CASES.md (G1-G4).
#
# These are the checks that must hold no matter how the model judges: a failed
# validation can't be approved silently, an approved file can't be swapped, and
# a doctored ledger can't be packaged. Unlike the document cases, these ARE
# script-assertable — so they run here.
#
# Usage: tests/run_gate_tests.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ADA="$REPO/ada"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0; fail=0
ok(){ echo "  PASS  $1"; pass=$((pass+1)); }
no(){ echo "  FAIL  $1"; fail=$((fail+1)); }
py(){ python3 "$ADA/scripts/$@"; }

SRC="$REPO/tests/cases/R1/PayrollJournal_04012026-06302026.pdf"
[ -f "$SRC" ] || python3 "$REPO/tests/make_fixtures.py" >/dev/null

cd "$WORK"
mkdir -p .ada drop
cp "$SRC" drop/PayrollJournal_04012026-06302026.pdf

py ledger.py init --ledger ./.ada/l.jsonl --run-id GATE --client Acme \
  --operator op --host test >/dev/null
py ledger.py authorize --ledger ./.ada/l.jsonl --connector paychex-export \
  --scope ./drop >/dev/null
py enumerate.py ./drop --connector paychex-export --out ./.ada/c.jsonl 2>/dev/null
py pii_scan.py --candidates ./.ada/c.jsonl --update 2>/dev/null

echo "gate regressions"

# G1 — a failed validation cannot be approved without an explicit override.
if py ledger.py approve --ledger ./.ada/l.jsonl --path ./drop/PayrollJournal_04012026-06302026.pdf \
     --checklist-id 3c.payroll_register --validation fail \
     --validation-note "wrong quarter" >/dev/null 2>&1; then
  no "G1 approve refused on validation=fail without --override"
else
  ok "G1 approve refused on validation=fail without --override"
fi

# G2 — with --override it is approved AND the override is recorded.
py ledger.py approve --ledger ./.ada/l.jsonl --path ./drop/PayrollJournal_04012026-06302026.pdf \
  --checklist-id 3c.payroll_register --validation fail \
  --validation-note "client confirms intentional" --override >/dev/null 2>&1
if grep -q '"override": true' ./.ada/l.jsonl; then
  ok "G2 override approves and is recorded in the ledger"
else
  no "G2 override approves and is recorded in the ledger"
fi

# G3 — a file changed after approval no longer matches its content hash.
echo "TAMPERED" >> drop/PayrollJournal_04012026-06302026.pdf
py enumerate.py ./drop --connector paychex-export --out ./.ada/c.jsonl 2>/dev/null
py package.py --ledger ./.ada/l.jsonl --candidates ./.ada/c.jsonl \
  --taxonomy "$ADA/taxonomy.yaml" --out ./pkg >/dev/null 2>&1
if [ "$(find ./pkg/files -type f 2>/dev/null | wc -l | tr -d ' ')" = "0" ]; then
  ok "G3 file modified after approval is not staged"
else
  no "G3 file modified after approval is not staged"
fi

# G4 — a hand-edited ledger breaks the chain and blocks packaging.
python3 - <<'PY'
p = "./.ada/l.jsonl"
s = open(p).read().replace('"client confirms intentional"', '"nothing to see"')
open(p, "w").write(s)
PY
if py ledger.py verify --ledger ./.ada/l.jsonl >/dev/null 2>&1; then
  no "G4 tampered ledger detected by verify"
else
  ok "G4 tampered ledger detected by verify"
fi
if py package.py --ledger ./.ada/l.jsonl --candidates ./.ada/c.jsonl \
     --taxonomy "$ADA/taxonomy.yaml" --out ./pkg2 >/dev/null 2>&1; then
  no "G4 package aborts on tampered ledger"
else
  ok "G4 package aborts on tampered ledger"
fi

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
