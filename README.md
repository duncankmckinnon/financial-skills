# financial-skills

Agent skills for personal investing and financial planning, distributed as a
Claude Code plugin marketplace and usable by any agent that can load a
`SKILL.md`.

Portfolio data and order execution come from Robinhood's
[agentic-trading MCP](https://robinhood.com/us/en/support/articles/agentic-trading-overview/);
charts render through the [`xy`](https://github.com/reflex-dev/xy) library.

## Install

```
/plugin marketplace add duncankmckinnon/financial-skills
/plugin install financial-skills@financial-skills
```

Then ask your agent to **set up financial skills** — the `financial-setup` skill
runs a doctor that verifies everything end to end, including an actual test
chart render, and tells you exactly what is missing.

For other agents, see
[per-harness setup](plugins/financial-skills/references/harness-setup.md).

## What it publishes

One plugin, **`financial-skills`**, with six skills:

| Skill | What it does | Needs a broker |
|---|---|---|
| **`financial-setup`** | Sets up and verifies the environment. Start here. | no |
| **`portfolio-review`** | Allocation, concentration, exposure, unrealized P/L, drift vs target. Read-only. | yes |
| **`trade-workflow`** | The only path to a placed order: thesis → sizing → preview → explicit confirm → place → log. | yes |
| **`rebalancing`** | Drift table, minimal trade set, tax and wash-sale checks. | yes |
| **`retirement-planning`** | Projections, savings rate, account location, glidepath. | no |
| **`financial-charts`** | All chart rendering, via the `xy` library. | no |

## Safety

Order placement is deliberately hard to do by accident:

- Robinhood's own boundary makes every account **read-only at the source**
  except one dedicated Agentic account.
- **One skill** (`trade-workflow`) may place an order; the other five state in
  their own text that they must not.
- **Preview → explicit confirm → place** is non-skippable. One confirmation
  authorizes exactly one order, silence is never confirmation, and changing any
  parameter voids it.
- Every placed order is appended to a trade log with its thesis and the preview
  warnings verbatim.

Your data — policy, trade log, charts — lives in
`${FINANCIAL_HOME:-~/.financial}`, never in this repo and never inside an
agent's config directory.

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
uv run --with 'xy==0.0.6' --with pytest pytest tests/ -q   # palette, charts, doctor
./scripts/validate.sh                                      # manifests + frontmatter
./tests/test_skill_contracts.sh                            # skill content guarantees
```

The Python suite runs anywhere. The two shell scripts are development-only and
need bash — on Windows, WSL or Git Bash. Nothing a *user* runs requires bash:
`doctor.py` and the charting module are cross-platform.

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

- **`uv`** — the only thing you install by hand. It supplies Python and fetches
  the charting dependency on demand, so there is no virtualenv to manage.
- **[`xy`](https://github.com/reflex-dev/xy) `==0.0.6`** — the charting library,
  pinned. Fetched automatically by `uv run --with 'xy==0.0.6'` on first render
  and cached after, so the **first chart render needs network access**. The
  version is pinned because `xy` is pre-1.0 and its horizontal-bar axis
  semantics are relied on directly — see
  [`references/chart-recipes.md`](plugins/financial-skills/references/chart-recipes.md).
- **an MCP-capable agent** — only for the three broker-backed skills;
  `financial-setup`, `retirement-planning`, and `financial-charts` need no
  broker connection at all
- **`jq`** — development only, for `scripts/validate.sh`

Run `plugins/financial-skills/scripts/doctor.py` to check all of it at once.

## Charts

![A portfolio review on one page: allocation by theme, drift vs target,
unrealized P/L, portfolio value over time, a correlation heatmap and income by
source, each panel carrying a short written takeaway underneath.](docs/dashboard.png)

*One `portfolio-review` run, rendered by `financial-charts` and opened as a
single page. Synthetic data — no real holdings.*

**A run of charts opens as one page, not one tab each.** A review is a single
finding, not six of them, and charts you have to open one at a time cannot be
compared. Every chart stays interactive on that page — tooltips, crosshair, pan
and zoom — and links out to itself for a closer look.

Each panel can carry a written takeaway: a chart shows a shape, and the note
says what the shape means. Notes describe **what the chart shows, not what to
do about it** — recommendations belong to `rebalancing` and `trade-workflow`,
which carry sizing, wash-sale checks and an explicit confirmation gate that a
caption under a chart does not.

### Putting your own charts on it

The dashboard is not limited to the portfolio presets, and neither is the
charting module. Ask for anything chartable and it lands on the same page,
because every renderer writes into the same run directory:

> "Chart my trailing 12-month income by source and add it to the review."

Pick the renderer by **the reader's job**, not by the subject — each one
applies the palette, folding, labelling and axis rules for you:

| The reader must… | Renderer |
|---|---|
| Compare magnitude across categories | `magnitude_chart` |
| Follow one or more series over a common x | `series_chart` |
| See part-to-whole | `part_to_whole_chart` |
| See above/below a baseline | `diverging_chart` |
| See the shape of a sample | `distribution_chart` |
| See a grid of values | `matrix_chart` |
| See how two measures relate | `relationship_chart` |

Full API and the rules each renderer enforces — including the palette, the
folding rule and why gains are blue rather than green:
[`skills/financial-charts/SKILL.md`](plugins/financial-skills/skills/financial-charts/SKILL.md).

## Not advice

Decision-support tooling for your own accounts. It states its assumptions and
shows its work; where the data does not support a conclusion, it says so instead
of estimating quietly.
