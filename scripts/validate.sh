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

echo "== 6. no SKILL.md hardcodes a tool name from references/sources/ =="
# Names are read from the source files themselves, so adding a source extends
# this check with no edit here. A name is any backticked token in a table row.
tools=$(for f in plugins/*/references/sources/*.md; do
  case "$f" in */_template.md) continue ;; esac
  [ -e "$f" ] && grep '^|' "$f" | grep -oE '`[A-Za-z_][A-Za-z0-9_]*`' | tr -d '`'
done | sort -u)
if [ -z "$tools" ]; then
  err "no tool names found under references/sources/ -- check 6 has nothing to enforce"
else
  for f in plugins/*/skills/*/SKILL.md; do
    [ -e "$f" ] || continue
    hit=0
    for t in $tools; do
      if grep -nw -- "$t" "$f"; then hit=1; fi
    done
    [ "$hit" -eq 1 ] && err "$f hardcodes a tool name; route through references/sources.md"
  done
  [ "$fail" -eq 0 ] && ok "$(echo "$tools" | wc -l | tr -d ' ') tool names checked against every SKILL.md"
fi

echo "== 7. plugin content is harness-agnostic =="
# Everything the user reads must work under any agent, not just Claude Code.
# Scope is every doc the plugin ships -- skills, references AND assets -- not
# just SKILL.md: a stale legacy path in the policy template shipped once
# because this check only looked at skills.
# references/harness-setup.md is the one file allowed to name a harness.
# The /mcp pattern excludes a following '/' or '-' so the URL
# .../mcp/trading and the filename references/mcp-tools.md are not flagged.
for f in $(find plugins/*/skills plugins/*/references plugins/*/assets -name '*.md' 2>/dev/null | sort); do
  case "$f" in */references/harness-setup.md) continue ;; esac
  if grep -nE '~/\.claude/|CLAUDE_PLUGIN_ROOT|(^|[^a-zA-Z])/mcp([^a-zA-Z/-]|$)|claude plugin ' "$f"; then
    err "$f names a harness-specific path or command; move it to references/harness-setup.md"
  else
    ok "${f#plugins/*/} is harness-agnostic"
  fi
done

echo "== 8. source files follow the shared format =="
CAPS="accounts|balances|positions|quotes|tax lots|order history|transactions|order preview|order place"
for p in plugins/*/; do
  idx="${p}references/sources.md"
  if [ ! -f "$idx" ]; then err "missing $idx"; continue; fi
  echo "$CAPS" | tr '|' '\n' | while read -r c; do
    grep -qiF -- "$c" "$idx" || echo "$c"
  done | grep -q . && err "$idx does not define every capability"
  for phrase in "one account, one source" "unassigned" "not live" "Without it"; do
    grep -qiF -- "$phrase" "$idx" || err "$idx missing: $phrase"
  done
  trading=0
  for f in "${p}"references/sources/*.md; do
    [ -e "$f" ] || continue
    case "$f" in */_template.md) continue ;; esac
    before=$fail
    role=$(head -10 "$f" | sed -nE 's/^Role:[[:space:]]*(trading|read-only)[[:space:]]*$/\1/p' | head -1)
    [ -n "$role" ] || err "$f: no 'Role: trading' or 'Role: read-only' line in its first 10 lines"
    [ "$role" = "trading" ] && trading=$((trading + 1))
    for h in Connection Boundaries Freshness Capabilities Gaps; do
      grep -q "^## $h\$" "$f" || err "$f: missing section '## $h'"
    done
    # Rows of the Capabilities table only: from its heading to the next H2.
    rows=$(awk '/^## Capabilities$/{on=1; next} /^## /{on=0} on && /^\|/' "$f" \
           | grep -vE '^\|[[:space:]]*(Capability|-+)' )
    firsts=$(echo "$rows" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
    while read -r c; do
      echo "$firsts" | grep -qxF -- "$c" || err "$f: Capabilities table has no row for '$c'"
    done < <(echo "$CAPS" | tr '|' '\n')
    while read -r c; do
      [ -z "$c" ] && continue
      echo "$c" | grep -qxE "$CAPS" || err "$f: '$c' is not a capability defined in references/sources.md"
    done <<< "$firsts"
    if [ "$role" = "read-only" ]; then
      for c in "order preview" "order place"; do
        echo "$rows" | awk -F'|' -v c="$c" '{gsub(/^[ \t]+|[ \t]+$/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $3); if ($2==c && $3!="none") bad=1} END{exit !bad}' \
          && err "$f: a read-only source must have 'none' for $c"
      done
    fi
    [ "$fail" -eq "$before" ] && ok "${f#plugins/*/}"
  done
  [ "$trading" -le 1 ] || err "${p}references/sources/: more than one shipped source declares Role: trading"
done

[ "$fail" -eq 0 ] && echo "ALL CHECKS PASS" || echo "VALIDATION FAILED" >&2
exit "$fail"
