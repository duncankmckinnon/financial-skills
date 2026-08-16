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

## Setup

**1. Authorize the MCP server** (one time, interactive):

```
/mcp
```

Authorize `robinhood-trading`. The plugin ships the server config in `.mcp.json`;
it carries a URL only — no credentials live in this repo.

**2. Create your investment policy** (optional but unlocks drift and rebalancing):

```bash
mkdir -p ~/.claude/financial
cp assets/investment-policy.template.md ~/.claude/financial/investment-policy.md
```

Then edit it with your targets, tolerance bands, risk limits, and do-not-sell
list. Skills degrade gracefully without it — they report what is computable and
name what needs a policy, rather than inventing targets.

**3. Charts** need `uv`, which fetches `xy` on demand. No venv to manage.

## Where your data lives

Nothing personal enters this repository:

| File | Purpose |
|---|---|
| `~/.claude/financial/investment-policy.md` | Your targets and limits |
| `~/.claude/financial/trade-log.md` | Append-only record of placed orders |
| `~/.claude/financial/charts/<date>/` | Rendered charts |

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
