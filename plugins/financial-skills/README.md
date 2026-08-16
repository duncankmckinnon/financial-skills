# financial-skills

Personal investing and financial-planning skills for Claude Code, backed by
Robinhood's agentic-trading MCP.

The skills carry the judgment and workflow; the MCP carries the data and
execution; `financial-charts` carries the rendering. No skill duplicates
another's job.

## Skills

| Skill | What it does | Needs the MCP |
|---|---|---|
| `portfolio-review` | Allocation, concentration, exposure, unrealized P/L, drift vs target. Read-only. | yes |
| `trade-workflow` | The only path to a placed order: thesis → sizing → preview → explicit confirm → place → log. | yes |
| `rebalancing` | Drift table, minimal trade set, tax and wash-sale checks; hands trades to `trade-workflow` one at a time. | yes |
| `retirement-planning` | Projections, savings rate vs goal, account location, glidepath. | no |
| `financial-charts` | All chart rendering, via the `xy` library. | no |
| `financial-setup` | Sets up and verifies the environment. Start here. | no |

## Setup

Ask your agent to **set up financial skills**, or run the doctor directly:

```bash
scripts/doctor.sh          # check and report
scripts/doctor.sh --fix    # create the data home, policy file and env.sh
```

It checks resources, `uv`, an end-to-end smoke chart, your data home, the policy
file, and the broker declaration. `--fix` is additive and **never overwrites an
existing investment policy**.

Connecting the broker is harness-specific — see
[`references/harness-setup.md`](references/harness-setup.md).

## Works with any agent

The skills are harness-agnostic: they resolve resource paths at runtime, keep
data outside any tool's config directory, and refer to broker capabilities
rather than hardcoded tool names. `scripts/validate.sh` check 7 fails the build
if a `SKILL.md` picks up a harness-specific path or command.

Point any agent that can load a `SKILL.md` at `skills/`, set
`FINANCIAL_SKILLS_ROOT` to this directory, and register an MCP server named
`robinhood-trading`. Agents without MCP support can still use
`retirement-planning` and `financial-charts`.

## Where your data lives

`${FINANCIAL_HOME:-~/.financial}` — deliberately outside any agent's config
directory, because this is your data, not a tool's state. Nothing personal
enters this repository.

| File | Purpose |
|---|---|
| `$FINANCIAL_HOME/investment-policy.md` | Your targets and limits |
| `$FINANCIAL_HOME/trade-log.md` | Append-only record of placed orders |
| `$FINANCIAL_HOME/charts/<date>/` | Rendered charts |
| `$FINANCIAL_HOME/env.sh` | Resolved paths, written by the doctor |

## Safety model

Layered, outermost first:

1. **Robinhood's server boundary.** Every account except the dedicated Agentic
   account is read-only *at the source*. Nothing this plugin does can widen that.
2. **Single write path.** `trade-workflow` is the only skill allowed to place an
   order; the other four state in their own text that they must not.
3. **Preview → explicit confirm → place**, non-skippable. One confirmation
   authorizes exactly one order. Silence is not confirmation, and changing any
   parameter voids it.
4. **Append-only trade log** — timestamp, thesis, preview warnings, result.
5. **Policy limits** checked before preview, with the number and the limit shown.

## Charts

Gains are **blue**, losses are **red** — not green/red. Measured with the palette
validator: blue↔red separates at protan ΔE 21.6, green↔red at 7.2, inside the
band where roughly 8% of men cannot tell the pair apart. Polarity additionally
carries an explicit sign and a direct label, so it never rides on hue alone.

## Not advice

These are decision-support tools for your own accounts. They state their
assumptions and show their work. They are not financial advice, and where the
data does not support a conclusion — missing lot-level cost basis, for example —
they say so rather than estimating quietly.
