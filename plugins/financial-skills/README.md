# financial-skills

Personal investing and financial-planning skills for Claude Code, reading from
whichever data sources you connect. Source files ship for Robinhood's
agentic-trading MCP (holdings and order execution) and Monarch Money (accounts
held anywhere else); you can describe others yourself.

The skills carry the judgment and workflow; the sources carry the data, and the
trading source the execution; `financial-charts` carries the rendering. No skill duplicates
another's job.

## Skills

| Skill | What it does | Needs a source |
|---|---|---|
| `portfolio-review` | Allocation, concentration, exposure, unrealized P/L, drift vs target. Read-only. | yes |
| `trade-workflow` | The only path to a placed order: thesis → sizing → preview → explicit confirm → place → log. | yes — the trading one |
| `rebalancing` | Drift table, minimal trade set, tax and wash-sale checks; hands trades to `trade-workflow` one at a time. | yes |
| `retirement-planning` | Projections, savings rate vs goal, account location, glidepath. | no |
| `financial-charts` | All chart rendering: a JSON spec in, one downloadable page out. Via the `xy` library. | no |
| `financial-setup` | Sets up and verifies the environment. Start here. | no |

## Setup

Ask your agent to **set up financial skills**, or run the doctor directly:

```bash
uv run python scripts/doctor.py        # check and report
uv run python scripts/doctor.py --fix  # create the data home, policy, sources and env files
```

It checks resources, `uv`, an end-to-end smoke chart, your data home, the policy
file, and the source files. `--fix` is additive and **never overwrites an
existing investment policy or sources declaration**.

Connecting a source is harness-specific — see
[`references/harness-setup.md`](references/harness-setup.md).

## Data sources

Skills name a *capability* — positions, balances, quotes, transactions, order
preview — never a source. [`references/sources.md`](references/sources.md)
defines the list and the rules; each file under
[`references/sources/`](references/sources/) maps it to one source's tools.

| Source | Role | Provides |
|---|---|---|
| Robinhood | trading | accounts, balances, positions, live quotes, tax lots, order history, bank and card transactions, order preview and place |
| Monarch Money | read-only | accounts, balances and holdings across institutions, transactions — synced, not live |

Every skill **adapts to what is connected**. With Monarch alone you still get
allocation, concentration and drift, on synced values and marked as such; you
do not get lot-level tax checks or order placement, and the skill says so.

Tell the skills which source owns which account in
`$FINANCIAL_HOME/sources.md`. That is what keeps an account two sources both
report from being counted twice. An account you have not listed is reported as
unassigned and left out of totals — never matched up by guesswork.

To add a source of your own, copy
[`references/sources/_template.md`](references/sources/_template.md) into
`$FINANCIAL_HOME/sources/`.

## Dependencies

| Dependency | Needed by | Notes |
|---|---|---|
| `uv` | `financial-charts`, the doctor | The only manual install; supplies Python too |
| [`xy`](https://github.com/reflex-dev/xy) `==0.0.6` | `financial-charts` | Fetched by `uv` on first render, then cached — so the first render needs network. Pinned: pre-1.0, and the horizontal-bar axis semantics are relied on directly ([recipes](references/chart-recipes.md)) |
| `robinhood-trading` MCP | `trade-workflow`; optional for `portfolio-review` and `rebalancing` | The trading source. OAuth, authorized once per harness |
| Monarch Money MCP | optional for `portfolio-review` and `rebalancing` | Read-only source you connect yourself |
| `jq` | `scripts/validate.sh` | Development only |

`financial-setup`, `retirement-planning`, and `financial-charts` need no source
at all. `portfolio-review` and `rebalancing` need at least one, of any kind. `retirement-planning` needs nothing beyond the numbers you supply.

## Works with any agent

The skills are harness-agnostic: they resolve resource paths at runtime, keep
data outside any tool's config directory, and refer to capabilities rather
than hardcoded sources or tool names. `scripts/validate.sh` check 7 fails the build
if a `SKILL.md` picks up a harness-specific path or command.

Point any agent that can load a `SKILL.md` at `skills/`, set
`FINANCIAL_SKILLS_ROOT` to this directory, and connect at least one source. Agents without MCP support can still use
`retirement-planning` and `financial-charts`.

## Where your data lives

`${FINANCIAL_HOME:-~/.financial}` — deliberately outside any agent's config
directory, because this is your data, not a tool's state. Nothing personal
enters this repository.

| File | Purpose |
|---|---|
| `$FINANCIAL_HOME/investment-policy.md` | Your targets and limits |
| `$FINANCIAL_HOME/sources.md` | Which source owns which account |
| `$FINANCIAL_HOME/sources/` | Source files you add yourself |
| `$FINANCIAL_HOME/trade-log.md` | Append-only record of placed orders |
| `$FINANCIAL_HOME/charts/<date>/` | Rendered charts |
| `$FINANCIAL_HOME/env.sh` | Resolved paths, written by the doctor |

## Safety model

Layered, outermost first:

1. **Robinhood's server boundary.** Every account except the dedicated Agentic
   account is read-only *at the source*. Nothing this plugin does can widen that.
   Every other source is read-only to the plugin by rule: Monarch's own editing
   tools are listed as off limits to every skill.
2. **Single write path.** `trade-workflow` is the only skill allowed to place an
   order; the other five state in their own text that they must not.
3. **Preview → explicit confirm → place**, non-skippable. One confirmation
   authorizes exactly one order. Silence is not confirmation, and changing any
   parameter voids it.
4. **Append-only trade log** — timestamp, thesis, preview warnings, result.
5. **Policy limits** checked before preview, with the number and the limit shown.

## Charts

Charts are declared, not coded. The agent writes a JSON spec — rows, charts,
page layout — and runs `scripts/charts.py render spec.json`. The result is one
self-contained page: interactive charts at declared sizes, headline figures,
tables and text, with PNG, SVG and CSV downloads on every chart. A spec that
does not validate renders nothing and lists every problem. Format:
[`references/chart-spec.md`](references/chart-spec.md).

Gains are **blue**, losses are **red** — not green/red. Measured with the palette
validator: blue↔red separates at protan ΔE 21.6, green↔red at 7.2, inside the
band where roughly 8% of men cannot tell the pair apart. Polarity additionally
carries an explicit sign and a direct label, so it never rides on hue alone.

## Not advice

These are decision-support tools for your own accounts. They state their
assumptions and show their work. They are not financial advice, and where the
data does not support a conclusion — missing lot-level cost basis, for example —
they say so rather than estimating quietly.
