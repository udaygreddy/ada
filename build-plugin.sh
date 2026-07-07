#!/usr/bin/env bash
# Assemble the ADA distribution artifacts from the canonical skill bundle (ada/):
#   - adp-discovery.plugin      (Cowork plugin package)
#   - adp-discovery-skill.zip   (skill folder — claude.ai upload / Claude Code install)
#   - .apm/ mirror + `apm pack`  (apm packaging; .apm/ is generated, gitignored)
# ada/ is the single source you edit. The .apm/ mirror is regenerated here (NOT
# committed); `apm pack` then emits ecosystem plugin manifests from it. If an
# outputs dir is given/found, the .plugin and zip are copied there (the .plugin
# also shows as an installable Cowork card).
#
# Note: because .apm/ is not committed, `apm install udaygreddy/ada` from GitHub
# is not available — apm here is a local build-time packaging step.
#
# Usage: ./build-plugin.sh [/path/to/cowork/outputs/dir]
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
NAME="adp-discovery"
BUILD="$REPO/build/$NAME"
SKILL_DST="$BUILD/skills/$NAME"
# Canonical skill source (the folder you edit).
SKILL_SRC="$REPO/ada"
# apm reads primitives from .apm/ only — keep a committed mirror there.
APM_MIRROR="$REPO/.apm/skills/$NAME"

# --- resync the apm mirror from the canonical source ---
rm -rf "$APM_MIRROR"
mkdir -p "$(dirname "$APM_MIRROR")"
cp -R "$SKILL_SRC" "$APM_MIRROR"
find "$APM_MIRROR" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$APM_MIRROR" -name '.DS_Store' -delete 2>/dev/null || true
echo "synced apm mirror .apm/skills/$NAME (from ada/) — commit it if changed"

rm -rf "$BUILD"
mkdir -p "$SKILL_DST" "$BUILD/.claude-plugin"

# Skill body = the canonical bundle (scripts/taxonomy/connectors/procedure/SKILL).
cp -R "$SKILL_SRC/." "$SKILL_DST/"
# Drop cruft that shouldn't ship.
find "$SKILL_DST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$SKILL_DST" -name '.DS_Store' -delete 2>/dev/null || true

# Manifest + plugin README.
cp "$REPO/plugin/plugin.json" "$BUILD/.claude-plugin/plugin.json"
cp "$REPO/plugin/README.md" "$BUILD/README.md"

# --- manual structure validation (mirrors `claude plugin validate`) ---
fail=0
[ -f "$BUILD/.claude-plugin/plugin.json" ] || { echo "MISSING plugin.json"; fail=1; }
python3 -c "import json,sys; d=json.load(open('$BUILD/.claude-plugin/plugin.json'));
import re; n=d.get('name','');
sys.exit(0 if re.fullmatch(r'[a-z0-9-]+', n) else 1)" \
  || { echo "plugin.json name missing or not kebab-case"; fail=1; }
[ -f "$SKILL_DST/SKILL.md" ] || { echo "MISSING skills/$NAME/SKILL.md"; fail=1; }
for s in ledger enumerate pii_scan package requirements _ada; do
  [ -f "$SKILL_DST/scripts/$s.py" ] || { echo "MISSING scripts/$s.py"; fail=1; }
done
python3 -m py_compile "$SKILL_DST"/scripts/*.py || { echo "scripts do not compile"; fail=1; }
[ "$fail" -eq 0 ] || { echo "VALIDATION FAILED"; exit 1; }
echo "validation OK"

# --- package ---
PKG="/tmp/$NAME.plugin"
rm -f "$PKG"
( cd "$BUILD" && zip -rq "$PKG" . -x "*.DS_Store" )
echo "built $PKG"

# --- skill-folder zip (claude.ai upload / Claude Code install) ---
# Top-level folder is "$NAME/" with SKILL.md at its root.
SKILLZIP="/tmp/$NAME-skill.zip"
rm -f "$SKILLZIP"
SKILLSTAGE="$REPO/build/skill"
rm -rf "$SKILLSTAGE"
mkdir -p "$SKILLSTAGE/$NAME"
cp -R "$SKILL_DST/." "$SKILLSTAGE/$NAME/"
( cd "$SKILLSTAGE" && zip -rq "$SKILLZIP" "$NAME" -x "*.DS_Store" )
echo "built $SKILLZIP"

# --- apm packaging (optional; needs the apm CLI: pip install apm-cli) ---
# Reads apm.yml + the generated .apm/ mirror and emits ecosystem plugin
# manifests (Claude / Copilot). Outputs are gitignored build artifacts.
APM_BIN="$(command -v apm || echo "$(python3 -m site --user-base 2>/dev/null)/bin/apm")"
if [ -x "$APM_BIN" ]; then
  if "$APM_BIN" pack >/tmp/apm-pack.log 2>&1; then
    echo "apm pack: emitted plugin manifests (.claude-plugin/, .github/plugin/ — gitignored)"
  else
    echo "apm pack: skipped/failed (see /tmp/apm-pack.log)"
  fi
else
  echo "apm not found; skipping apm pack (install: pip install apm-cli)"
fi

# --- deliver to outputs dir if provided or discoverable ---
OUT="${1:-}"
if [ -z "$OUT" ]; then
  OUT="$(ls -dt "$HOME/Library/Application Support/Claude/local-agent-mode-sessions"/*/*/local_*/outputs 2>/dev/null | head -1 || true)"
fi
if [ -n "$OUT" ] && [ -d "$OUT" ]; then
  cp "$PKG" "$OUT/$NAME.plugin"
  cp "$SKILLZIP" "$OUT/$NAME-skill.zip"
  echo "delivered to $OUT/ ($NAME.plugin + $NAME-skill.zip)"
else
  echo "no outputs dir found; artifacts at $PKG and $SKILLZIP"
fi
