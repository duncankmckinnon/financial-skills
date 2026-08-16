# financial-skills

A Claude Code plugin marketplace for personal investing and financial planning.

## Install

```
/plugin marketplace add duncanmckinnon/financial-skills
/plugin install financial-skills@financial-skills
```

## What it publishes

One plugin, **`financial-skills`**, with five skills:

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
and which you authorize once with `/mcp`.

See [`plugins/financial-skills/README.md`](plugins/financial-skills/README.md)
for setup, the safety model, and where your data lives (outside this repo).

## Development

```bash
./scripts/validate.sh                              # manifests + skill frontmatter
./tests/test_skill_contracts.sh                    # skill content guarantees
uv run --with 'xy==0.0.6' --with pytest pytest tests/ -q   # palette + charts
```

`scripts/validate.sh` also enforces that no `SKILL.md` hardcodes an MCP tool
name — those live only in
[`references/mcp-tools.md`](plugins/financial-skills/references/mcp-tools.md),
so correcting one is a single-file edit.

Charts run through `uv run --with 'xy==0.0.6'`; there is no venv to manage.

## Requirements

`uv`, `jq`, and a Claude Code install. `retirement-planning` works standalone;
the other MCP-backed skills need the Robinhood authorization.
