# financial-skills

A Claude Code plugin marketplace for personal investing and financial planning.

## Install

```
/plugin marketplace add duncanmckinnon/financial-skills
/plugin install financial-skills@financial-skills
```

## What it publishes

One plugin, **`financial-skills`**, with six skills:

- **`financial-setup`** — sets up and verifies the environment. Start here.

- **`portfolio-review`** — allocation, concentration, exposure, unrealized P/L,
  drift vs target. Read-only.
- **`trade-workflow`** — the only path to a placed order: thesis → sizing →
  preview → explicit confirm → place → log.
- **`rebalancing`** — drift table, minimal trade set, tax and wash-sale checks.
- **`retirement-planning`** — projections, savings rate, account location,
  glidepath. No broker connection required.
- **`financial-charts`** — all chart rendering, via the `xy` library.

Portfolio data and order execution come from Robinhood's agentic-trading MCP
(`https://agent.robinhood.com/mcp/trading`), which the plugin wires up on install
and which you authorize once.

## Works with any agent

The marketplace is the distribution channel, not a dependency. The skills
themselves are harness-agnostic — they resolve paths at runtime, store data in
`${FINANCIAL_HOME:-~/.financial}` rather than any tool's config directory, and
name broker *capabilities* rather than hardcoded tool names. Point any agent
that can load a `SKILL.md` at `plugins/financial-skills/skills/`.

See [`plugins/financial-skills/README.md`](plugins/financial-skills/README.md)
for setup and the safety model, and
[`references/harness-setup.md`](plugins/financial-skills/references/harness-setup.md)
for per-harness instructions.

## Development

```bash
./scripts/validate.sh                              # manifests + skill frontmatter
./tests/test_skill_contracts.sh                    # skill content guarantees
./tests/test_doctor.sh                             # setup doctor behaviour
uv run --with 'xy==0.0.6' --with pytest pytest tests/ -q   # palette + charts
```

`scripts/validate.sh` enforces two invariants mechanically, so neither depends
on anyone remembering:

- **check 6** — no `SKILL.md` hardcodes an MCP tool name. Those live only in
  [`references/mcp-tools.md`](plugins/financial-skills/references/mcp-tools.md),
  so correcting one is a single-file edit.
- **check 7** — no `SKILL.md` contains a harness-specific path or command.
  Those live only in
  [`references/harness-setup.md`](plugins/financial-skills/references/harness-setup.md).

Charts run through `uv run --with 'xy==0.0.6'`; there is no venv to manage.

## Requirements

`uv`, `jq`, and a Claude Code install. `retirement-planning` works standalone;
the other MCP-backed skills need the Robinhood authorization.
