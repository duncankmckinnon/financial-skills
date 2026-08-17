---
name: financial-setup
description: Use when setting up, verifying, or troubleshooting the financial-skills environment — connecting the Robinhood broker, checking that charting works, creating the investment policy file, or diagnosing why another financial skill cannot run.
---

# Financial Setup

Get the environment working, and prove it — don't just describe the steps.

Run the doctor first, read what it says, and only then walk the human through
what is actually missing. Reciting a full setup guide at someone whose
environment is already fine wastes their time.

## 1. Run the doctor

```bash
uv run python "$ROOT/scripts/doctor.py"
```

Resolve `$ROOT` in this order — never hardcode an install path, since it differs
per harness and changes on update:

1. `$FINANCIAL_SKILLS_ROOT`, if set
2. two levels up from this skill's own directory (`skills/financial-setup/` →
   plugin root), which your harness tells you when it loads this skill
3. `$FINANCIAL_HOME/env.sh`, if a previous run wrote one

Exit codes: **0** ready · **1** something blocks · **2** usable but degraded.

The doctor checks resources, `uv`, `jq`, an **end-to-end smoke chart**, the data
home, the policy file, the broker declaration, and `env.sh`. The smoke chart is
the one that matters most: every individual part can check out while the chain
is still broken.

## 2. Fix what it found

Re-run with `--fix` to create the data home, an investment policy from the
template, and `env.sh`:

```bash
uv run python "$ROOT/scripts/doctor.py" --fix
```

`--fix` is additive only. It will **never overwrite** an existing investment
policy — that file holds real targets, limits, and a do-not-sell list, and a
helpful-looking reset would destroy them silently. If the human wants to start
over, have them move the old file aside themselves.

For anything the doctor reports as blocking that `--fix` cannot handle —
a missing `uv`, an unresolvable root — the fix is printed with the failure.

## 3. Connect the broker

This step is harness-specific and the doctor deliberately does not guess at it.
**Read `references/harness-setup.md`** and follow the section for the agent you
are running under.

Be straight about the limit: **authorization state cannot be checked** from a
script — it lives in an OAuth token the doctor cannot see. The doctor confirms
the server is *declared*, nothing more. The real test is asking
`portfolio-review` to read positions and seeing whether it works.

Tell the human which skills work without a broker at all:
`retirement-planning` and `financial-charts` need no connection.

## 4. Fill in the investment policy

The template at `assets/investment-policy.template.md` is a skeleton, not
defaults. Walk through it: target allocation, tolerance bands, maximum single
position, cash floor, do-not-sell list, tax constraints.

Explain what each one unlocks, so the human knows why it's worth the effort:

- **targets + tolerance bands** → drift analysis and rebalancing
- **maximum single position + cash floor** → the sizing check in `trade-workflow`
- **do-not-sell list** → positions rebalancing will never propose selling
- **tax constraints** → wash-sale and holding-period checks

Without a policy, the other skills still run — they report what is computable
and name what is missing, rather than inventing targets.

## Where data lives

`${FINANCIAL_HOME:-~/.financial}` holds the policy, the trade log, and rendered
charts. It is deliberately **outside** any agent's config directory — this is
the human's financial data, not a tool's state.

If the doctor reports data at a legacy location, it prints the path and both
options — keep it by setting `FINANCIAL_HOME`, or move it. Present both and let
the human choose. Never move their data for them.

## Boundaries

This skill must not place orders. It sets up and verifies the environment; it
does not touch the broker beyond checking that the server is declared.
