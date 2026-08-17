#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
S=plugins/financial-skills/skills
has()  { grep -qiF -- "$2" "$1" || { echo "FAIL: $1 missing: $2" >&2; fail=1; }; }
lacks(){ grep -qiF -- "$2" "$1" && { echo "FAIL: $1 must not contain: $2" >&2; fail=1; }; return 0; }

f=$S/financial-charts/SKILL.md
[ -f "$f" ] || { echo "FAIL: no $f" >&2; exit 1; }
has "$f" "uv run --with"
has "$f" "scripts/charts.py"
has "$f" "blue"
# The skill must forbid green/red, not merely avoid the phrase -- an earlier
# "lacks green/red" guard failed the correct text that bans it.
has "$f" "Never green/red"
lacks "$f" "gains are green"
has "$f" "never a dual-axis"
has "$f" "fold"
has "$f" "not theirs"
has "$f" "magnitude_chart"
has "$f" "ephemeral"
has "$f" "as-of stamp"
has "$f" "open "

f=$S/portfolio-review/SKILL.md
[ -f "$f" ] || { echo "FAIL: no $f" >&2; fail=1; }
if [ -f "$f" ]; then
  has "$f" "read-only"
  has "$f" "must not place"
  has "$f" "references/mcp-tools.md"
  has "$f" "investment-policy.md"
  has "$f" "financial-charts"
fi

f=$S/trade-workflow/SKILL.md
[ -f "$f" ] || { echo "FAIL: no $f" >&2; fail=1; }
if [ -f "$f" ]; then
  for phrase in "thesis" "sizing" "preview" "explicit" "confirm" "log" \
                "one confirmation authorizes exactly one order" \
                "silence is not confirmation" \
                "trade-log.md" "Agentic account"; do
    has "$f" "$phrase"
  done
fi

f=$S/rebalancing/SKILL.md
[ -f "$f" ] || { echo "FAIL: no $f" >&2; fail=1; }
if [ -f "$f" ]; then
  has "$f" "trade-workflow"
  has "$f" "must not place"
  has "$f" "one at a time"
  has "$f" "wash"
  has "$f" "do-not-sell"
  has "$f" "tolerance band"
fi

f=$S/retirement-planning/SKILL.md
[ -f "$f" ] || { echo "FAIL: no $f" >&2; fail=1; }
if [ -f "$f" ]; then
  has "$f" "assumptions"
  has "$f" "without a broker"
  has "$f" "must not place"
  has "$f" "projection_chart"
  has "$f" "not financial advice"
fi

f=$S/financial-setup/SKILL.md
[ -f "$f" ] || { echo "FAIL: no $f" >&2; fail=1; }
if [ -f "$f" ]; then
  has "$f" "scripts/doctor.sh"
  has "$f" "references/harness-setup.md"
  has "$f" "--fix"
  has "$f" "FINANCIAL_HOME"
  has "$f" "never overwrite"
  has "$f" "authorization state cannot be checked"
fi

[ "$fail" -eq 0 ] && echo "SKILL CONTRACTS PASS" || echo "SKILL CONTRACTS FAILED" >&2
exit "$fail"
