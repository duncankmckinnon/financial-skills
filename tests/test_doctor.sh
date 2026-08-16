#!/usr/bin/env bash
# Tests for scripts/doctor.sh. The critical one is that --fix never clobbers
# an existing investment policy -- that file holds real targets and limits.
set -uo pipefail
cd "$(dirname "$0")/.."
DOCTOR=plugins/financial-skills/scripts/doctor.sh
fail=0
t() { printf '  %s\n' "$1"; }
bad() { echo "FAIL: $*" >&2; fail=1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

t "report-only mode creates nothing"
H="$TMP/report_only"
FINANCIAL_HOME="$H" "$DOCTOR" >/dev/null 2>&1
[ -d "$H" ] && bad "report-only mode created $H"

t "--fix creates the home, policy and env.sh"
H="$TMP/fixed"
FINANCIAL_HOME="$H" "$DOCTOR" --fix >/dev/null 2>&1
[ -f "$H/investment-policy.md" ] || bad "--fix did not create the policy file"
[ -f "$H/env.sh" ] || bad "--fix did not write env.sh"
grep -q "FINANCIAL_SKILLS_ROOT" "$H/env.sh" 2>/dev/null || bad "env.sh records no root"

t "--fix NEVER overwrites an existing policy"
H="$TMP/existing"
mkdir -p "$H"
printf 'MY REAL TARGETS — DO NOT CLOBBER\n' > "$H/investment-policy.md"
before=$(cat "$H/investment-policy.md")
FINANCIAL_HOME="$H" "$DOCTOR" --fix >/dev/null 2>&1
after=$(cat "$H/investment-policy.md")
[ "$before" = "$after" ] || bad "--fix overwrote an existing investment policy"

t "exit code reports readiness"
H="$TMP/ready"
FINANCIAL_HOME="$H" "$DOCTOR" --fix >/dev/null 2>&1
FINANCIAL_HOME="$H" "$DOCTOR" >/dev/null 2>&1
[ "$?" -eq 0 ] || bad "a fully set up environment did not exit 0"

t "a bad root is reported as blocking"
FINANCIAL_SKILLS_ROOT=/nonexistent FINANCIAL_HOME="$TMP/x" "$DOCTOR" >/dev/null 2>&1
[ "$?" -eq 1 ] || bad "an unresolvable root did not exit 1"

[ "$fail" -eq 0 ] && echo "DOCTOR TESTS PASS" || echo "DOCTOR TESTS FAILED" >&2
exit "$fail"
