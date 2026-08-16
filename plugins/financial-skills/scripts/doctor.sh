#!/usr/bin/env bash
# financial-skills environment doctor.
#
# Harness-agnostic. Reports by default; creates nothing unless --fix is passed,
# and never overwrites an existing investment policy.
#
#   doctor.sh          check and report
#   doctor.sh --fix    additionally create missing directories, the policy file
#                      from the template, and env.sh
#
# Exit 0 = ready to use. Exit 1 = something blocks. Exit 2 = usable but
# degraded (broker-backed skills unavailable).

set -uo pipefail

FIX=0
[ "${1:-}" = "--fix" ] && FIX=1

ROOT="${FINANCIAL_SKILLS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
HOME_DIR="${FINANCIAL_HOME:-$HOME/.financial}"

blocked=0
degraded=0
pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }
warn() { printf '  \033[33mwarn\033[0m %s\n' "$1"; degraded=1; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; blocked=1; }
note() { printf '       %s\n' "$1"; }

echo "financial-skills doctor"
echo

echo "Plugin resources"
if [ -f "$ROOT/scripts/charts.py" ] && [ -f "$ROOT/assets/palette.py" ]; then
  pass "resolved root: $ROOT"
else
  bad "cannot find scripts/charts.py and assets/palette.py under $ROOT"
  note "set FINANCIAL_SKILLS_ROOT to the plugin directory"
fi

echo
echo "Runtime"
if command -v uv >/dev/null 2>&1; then
  pass "uv $(uv --version 2>/dev/null | awk '{print $2}')"
else
  bad "uv not found -- required to render charts"
  note "install: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

if command -v jq >/dev/null 2>&1; then
  pass "jq (development only)"
else
  warn "jq not found -- only needed to run scripts/validate.sh"
fi

echo
echo "Charting"
if [ "$blocked" -eq 0 ] && command -v uv >/dev/null 2>&1; then
  # End-to-end smoke render. Every part can check out while the chain is
  # still broken -- this is the only check that proves it works.
  smoke=$(mktemp -d)
  if uv run --quiet --with 'xy==0.0.6' python - "$ROOT" "$smoke" >/dev/null 2>/tmp/fs_doctor_err <<'PY'
import sys, pathlib
root, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, f"{root}/scripts")
import charts as c
p = c.allocation_chart([("A", 60.0), ("B", 40.0)], out)
assert p.exists() and p.with_suffix(".png").stat().st_size > 0
print("ok")
PY
  then
    pass "end-to-end smoke chart rendered (xy 0.0.6)"
  else
    bad "smoke chart failed to render"
    note "$(tail -3 /tmp/fs_doctor_err 2>/dev/null | tr '\n' ' ')"
  fi
  rm -rf "$smoke"
else
  warn "skipped smoke chart -- fix the failures above first"
fi

echo
echo "Personal data ($HOME_DIR)"
# Migration notice: earlier versions wrote into the Claude config directory.
LEGACY="$HOME/.claude/financial"
if [ -d "$LEGACY" ] && [ "$HOME_DIR" != "$LEGACY" ]; then
  warn "found data at $LEGACY"
  note "that location is deprecated -- it puts your data inside a tool's config dir"
  note "to keep using it: export FINANCIAL_HOME=$LEGACY"
  note "to move it: mv $LEGACY $HOME_DIR   (review first; nothing is moved for you)"
fi

if [ -d "$HOME_DIR" ]; then
  pass "$HOME_DIR exists"
elif [ "$FIX" -eq 1 ]; then
  mkdir -p "$HOME_DIR/charts" && pass "created $HOME_DIR"
else
  warn "$HOME_DIR missing -- re-run with --fix to create it"
fi

POLICY="$HOME_DIR/investment-policy.md"
if [ -f "$POLICY" ]; then
  # Never overwrite: this file holds real targets, limits and do-not-sell lists.
  pass "investment policy present (left untouched)"
elif [ "$FIX" -eq 1 ] && [ -f "$ROOT/assets/investment-policy.template.md" ]; then
  mkdir -p "$HOME_DIR"
  cp "$ROOT/assets/investment-policy.template.md" "$POLICY"
  pass "created $POLICY from template"
  note "edit it with your targets, tolerance bands and do-not-sell list"
else
  warn "no investment policy -- drift and rebalancing are unavailable without one"
  note "re-run with --fix to create one from the template"
fi

echo
echo "Broker connection"
if [ -f "$ROOT/.mcp.json" ] && grep -q robinhood-trading "$ROOT/.mcp.json" 2>/dev/null; then
  pass "robinhood-trading is declared in .mcp.json"
else
  warn "robinhood-trading not declared in $ROOT/.mcp.json"
fi
# Authorization state is OAuth-held and not readable from disk. Report the
# limit honestly rather than showing a green check for something unverified.
note "authorization state cannot be checked from here -- see references/harness-setup.md"
note "retirement-planning and financial-charts work without any broker connection"

echo
echo "Environment file"
ENVF="$HOME_DIR/env.sh"
if [ "$FIX" -eq 1 ] && [ -d "$HOME_DIR" ]; then
  cat > "$ENVF" <<EOF
# Written by financial-skills doctor.sh -- re-run after a plugin update.
export FINANCIAL_SKILLS_ROOT="$ROOT"
export FINANCIAL_HOME="$HOME_DIR"
EOF
  pass "wrote $ENVF"
elif [ -f "$ENVF" ]; then
  pass "$ENVF present"
  grep -q "FINANCIAL_SKILLS_ROOT=\"$ROOT\"" "$ENVF" || \
    warn "env.sh records a different root -- re-run with --fix after a plugin update"
else
  warn "no env.sh -- re-run with --fix to record the resolved paths"
fi

echo
if [ "$blocked" -ne 0 ]; then
  echo "BLOCKED -- fix the FAIL items above."
  exit 1
elif [ "$degraded" -ne 0 ]; then
  echo "USABLE, DEGRADED -- see warnings above."
  exit 2
fi
echo "READY"
exit 0
