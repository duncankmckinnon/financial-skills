#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
err() { echo "FAIL: $*" >&2; fail=1; }
ok()  { echo "  ok: $*"; }

echo "== 1. JSON parses =="
for f in .claude-plugin/marketplace.json plugins/*/.claude-plugin/plugin.json plugins/*/.mcp.json; do
  [ -e "$f" ] || { err "missing $f"; continue; }
  jq empty "$f" 2>/dev/null && ok "$f" || err "$f is not valid JSON"
done

echo "== 2. referenced plugin dirs exist =="
if [ -e .claude-plugin/marketplace.json ]; then
  while read -r src; do
    [ -d "$src" ] && ok "$src" || err "marketplace.json references missing dir $src"
  done < <(jq -r '.plugins[].source' .claude-plugin/marketplace.json)
fi

echo "== 3-5. skills =="
shopt -s nullglob
for d in plugins/*/skills/*/; do
  name=$(basename "$d")
  f="${d}SKILL.md"
  [ -f "$f" ] || { err "$name: no SKILL.md"; continue; }
  head -1 "$f" | grep -q '^---$' || err "$name: SKILL.md does not open with YAML frontmatter"
  fm_name=$(awk 'NR>1 && /^---$/{exit} /^name:/{print $2}' "$f")
  [ "$fm_name" = "$name" ] || err "$name: frontmatter name '$fm_name' != directory name"
  fm_desc=$(awk 'NR>1 && /^---$/{exit} /^description:/{sub(/^description: */,""); print}' "$f")
  [ -n "$fm_desc" ] || err "$name: empty description"
  echo "$fm_desc" | grep -qiE 'when|use this|invoke' || err "$name: description states no trigger condition"
  [ "$fail" -eq 0 ] && ok "$name"
done

echo "== 6. no hardcoded MCP tool names outside references/mcp-tools.md =="
for f in plugins/*/skills/*/SKILL.md; do
  [ -e "$f" ] || continue
  if grep -nE '\b(review_equity_order|place_equity_order|get_positions|get_account|get_quote)\b' "$f"; then
    err "$f hardcodes an MCP tool name; route through references/mcp-tools.md"
  fi
done

[ "$fail" -eq 0 ] && echo "ALL CHECKS PASS" || echo "VALIDATION FAILED" >&2
exit "$fail"
