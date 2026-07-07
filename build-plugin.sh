#!/usr/bin/env bash
# Assemble the ADA distribution artifacts from the canonical skill bundle
# (.apm/skills/ada-discovery/):
#   - ada-discovery.plugin      (Cowork plugin package)
#   - ada-discovery-skill.zip   (skill folder — claude.ai upload / Claude Code install)
# If an outputs dir is given/found, both are copied there (the .plugin also shows
# up as an installable card in Cowork chat).
#
# Usage: ./build-plugin.sh [/path/to/cowork/outputs/dir]
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
NAME="ada-discovery"
BUILD="$REPO/build/$NAME"
SKILL_DST="$BUILD/skills/$NAME"
# Canonical skill source (apm-native location).
SKILL_SRC="$REPO/.apm/skills/$NAME"

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
