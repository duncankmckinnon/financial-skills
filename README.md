# financial-skills

Agent skills for personal investing and financial planning, distributed as a
Claude Code plugin marketplace and usable by any agent that can load a
`SKILL.md`.

Data comes from whichever sources you connect. Source files ship for
Robinhood's
[agentic-trading MCP](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)
(holdings and order execution) and Monarch Money (accounts held anywhere else),
and you can describe others yourself. Order execution is Robinhood only. Charts
render through the [`xy`](https://github.com/reflex-dev/xy) library.

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

| Skill | What it does | Needs a source |
|---|---|---|
| **`financial-setup`** | Sets up and verifies the environment. Start here. | no |
| **`portfolio-review`** | Allocation, concentration, exposure, unrealized P/L, drift vs target. Read-only. | yes |
| **`trade-workflow`** | The only path to a placed order: thesis → sizing → preview → explicit confirm → place → log. | yes — the trading one |
| **`rebalancing`** | Drift table, minimal trade set, tax and wash-sale checks. | yes |
| **`retirement-planning`** | Projections, savings rate, account location, glidepath. | no |
| **`financial-charts`** | All chart rendering: a JSON spec in, one downloadable page out. | no |

## Safety

Order placement is deliberately hard to do by accident:

- Robinhood's own boundary makes every account **read-only at the source**
  except one dedicated Agentic account.
- Every other source is **read-only to every skill**, including tools of its
  own that could edit data, such as Monarch's.
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
name *capabilities* rather than hardcoded sources or tool names. Point any agent
that can load a `SKILL.md` at `plugins/financial-skills/skills/`.

See [`plugins/financial-skills/README.md`](plugins/financial-skills/README.md)
for setup and the safety model, and
[`references/harness-setup.md`](plugins/financial-skills/references/harness-setup.md)
for per-harness instructions.

## Development

```bash
uv run --with 'xy==0.0.6' --with pytest pytest tests/ -q   # palette, chart spec, steps, forms, page, CLI, doctor
./scripts/validate.sh                                      # manifests + frontmatter
./tests/test_skill_contracts.sh                            # skill content guarantees
```

The Python suite runs anywhere. The two shell scripts are development-only and
need bash — on Windows, WSL or Git Bash. Nothing a *user* runs requires bash:
`doctor.py` and the charting module are cross-platform.

`scripts/validate.sh` enforces these invariants mechanically, so none depends
on anyone remembering:

- **check 6** — no `SKILL.md` hardcodes a tool name. Names live only in the
  per-source files under
  [`references/sources/`](plugins/financial-skills/references/sources/), and the
  check reads its list from them, so adding a source extends it automatically.
- **check 7** — no `SKILL.md` contains a harness-specific path or command.
  Those live only in
  [`references/harness-setup.md`](plugins/financial-skills/references/harness-setup.md).
- **check 8** — every source file follows one format: a role, the same five
  sections, and a row for each capability defined in
  [`references/sources.md`](plugins/financial-skills/references/sources.md). At
  most one source may hold the trading role.
- **check 9** — nothing points at the single tool-reference file that the
  per-source files replaced.

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
- **an MCP-capable agent and at least one connected source** — only for
  `portfolio-review`, `rebalancing` and `trade-workflow`. Any source will do for
  the first two; placing an order needs Robinhood. `financial-setup`,
  `retirement-planning`, and `financial-charts` need no source at all
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
compared. The page is one self-contained file: every chart on it stays
interactive — tooltips, crosshair, pan and zoom — and it needs no other file
and no network, so it can be moved or attached as it is.

**Every chart is downloadable.** Each panel links its PNG, its SVG, and the
CSV of the rows behind it; each table links its CSV; the header links the spec
that produced the page.

Each panel can carry a written takeaway: a chart shows a shape, and the note
says what the shape means. Notes describe **what the chart shows, not what to
do about it** — recommendations belong to `rebalancing` and `trade-workflow`,
which carry sizing, wash-sale checks and an explicit confirmation gate that a
caption under a chart does not.

*The picture above predates the page layout described here: sections, sized
blocks, headline figures and tables are newer than it.*

### Charts are declared, not coded

The agent writes a JSON **spec** — the rows, the charts, the page — and runs
one command. No chart code is written per request:

```bash
uv run --with 'xy==0.0.6' python plugins/financial-skills/scripts/charts.py render spec.json --open
```

```json
{
  "title": "Portfolio review",
  "data": {"positions": {"rows": [
    {"symbol": "NVDA", "account": "Agentic", "value": 5200, "cost": 2100},
    {"symbol": "VTI",  "account": "Roth IRA", "value": 8400, "cost": 7000}
  ]}},
  "charts": [
    {"id": "allocation", "form": "part_to_whole", "preset": "allocation",
     "from": "positions", "label": "symbol", "value": "value"},
    {"id": "pl", "form": "diverging", "preset": "pl", "from": "positions",
     "steps": [{"diff": {"a": "value", "b": "cost", "as": "pl"}}],
     "label": "symbol", "value": "pl"}
  ]
}
```

- **Rows go in raw.** Grouping, shares, differences, sorting and top-N are
  declared as `steps`, so data from any connected source can be charted
  without shaping code.
- **Eight forms**, picked by the reader's job rather than the subject:
  `part_to_whole`, `magnitude`, `diverging`, `series`, `stacked_area`,
  `distribution`, `relationship`, `matrix`. Series take reference lines and a
  shaded band; any chart but a matrix can repeat per account or source as
  small multiples on a shared axis.
- **The page is laid out in the spec:** sections holding charts at three
  widths and three heights, headline figures, tables and text. No limit on
  how many.
- **A wrong spec fails before anything renders**, with every problem listed
  and located. Unknown keys are errors.
- **The rules cannot be switched off.** Gains blue and losses red, signed
  labels, one y-axis, folding past eight hues, no pies: the spec has no field
  for any of them.

Full format:
[`references/chart-spec.md`](plugins/financial-skills/references/chart-spec.md).
How to use it well, and why gains are blue rather than green:
[`skills/financial-charts/SKILL.md`](plugins/financial-skills/skills/financial-charts/SKILL.md).

## Not advice

Decision-support tooling for your own accounts. It states its assumptions and
shows its work; where the data does not support a conclusion, it says so instead
of estimating quietly.
