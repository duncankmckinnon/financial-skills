# Financial Skills Marketplace — Design

**Date:** 2026-08-15
**Status:** Approved design, pending implementation plan

## 1. Purpose

Turn this repo into a Claude Code plugin marketplace publishing a single plugin,
`financial-skills`, that provides personal investing and financial-planning
workflows. Portfolio data and trade execution come from Robinhood's official
agentic-trading MCP server; charting comes from the `xy` Python library.

The skills carry judgment and workflow. The MCP carries data and execution. The
chart skill carries rendering. No skill duplicates another's job.

### Non-goals

- No trading strategy, backtesting engine, or signal generation.
- No support for brokers other than Robinhood.
- No tax filing, no advice framed as professional financial advice. Skills state
  assumptions and show their work; the human decides.
- No storage of credentials in the repo. Auth is Robinhood's OAuth flow, handled
  by the MCP client.

## 2. Repository layout

```
financial-skills/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── financial-skills/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── .mcp.json
│       ├── README.md
│       ├── assets/
│       │   ├── investment-policy.template.md
│       │   └── palette.py
│       ├── references/
│       │   ├── mcp-tools.md
│       │   └── chart-recipes.md
│       └── skills/
│           ├── portfolio-review/SKILL.md
│           ├── trade-workflow/SKILL.md
│           ├── rebalancing/SKILL.md
│           ├── retirement-planning/SKILL.md
│           └── financial-charts/SKILL.md
├── scripts/
│   └── validate.sh
├── docs/superpowers/specs/
├── README.md
└── LICENSE
```

The plugin lives under `plugins/` rather than at the repo root (`source: "./"`).
There is one plugin today; nesting means adding a second later is an edit to
`marketplace.json`, not a repo restructure.

### 2.1 `.claude-plugin/marketplace.json`

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "financial-skills",
  "description": "Personal investing and financial-planning skills for Claude Code, backed by the Robinhood agentic-trading MCP.",
  "owner": { "name": "Duncan McKinnon" },
  "plugins": [
    {
      "name": "financial-skills",
      "source": "./plugins/financial-skills",
      "description": "Portfolio review, disciplined trade workflows, rebalancing, retirement planning, and financial charting.",
      "category": "productivity"
    }
  ]
}
```

### 2.2 `plugins/financial-skills/.claude-plugin/plugin.json`

```json
{
  "name": "financial-skills",
  "description": "Portfolio review, disciplined trade workflows, rebalancing, retirement planning, and financial charting.",
  "author": { "name": "Duncan McKinnon" }
}
```

### 2.3 `plugins/financial-skills/.mcp.json`

A bare server map at plugin root (no `mcpServers` wrapper — confirmed against
`claude-plugins-official/plugins/example-plugin/.mcp.json`):

```json
{
  "robinhood-trading": {
    "type": "http",
    "url": "https://agent.robinhood.com/mcp/trading"
  }
}
```

Installing the plugin therefore wires up the MCP server. Authorization is a
separate, interactive OAuth step the user performs once via `/mcp`.

## 3. Robinhood MCP binding

### 3.1 What the server provides

Confirmed from Robinhood's agentic-trading documentation:

- **Read-only** across all of the user's Robinhood accounts: positions, balances,
  portfolio value, order and transaction history, watchlists.
- **Write (orders) confined to a dedicated Robinhood Agentic account.** All other
  accounts are read-only at the server. This is Robinhood's boundary, not ours,
  and it is the primary safety guarantee.
- **Equities only** at launch; options and other asset classes are stated as
  coming later in the beta.
- An order **preview → place** pair (`review_equity_order` → `place_equity_order`)
  that surfaces warnings before execution.
- Research helpers: symbol search, live equity quotes, tradability checks,
  popular lists, watchlist management.

### 3.2 Tool-name pinning (open item, with a defined resolution)

The exact tool names and signatures cannot be enumerated without completing the
OAuth flow, which requires an interactive session. Rather than let five skills
each guess at names, **all MCP tool references live in one file**:
`references/mcp-tools.md`.

That file ships with the names confirmed from documentation
(`review_equity_order`, `place_equity_order`) marked **verified**, and every other
capability described **by function with its name marked unverified**.

Resolution procedure, performed once during implementation:

1. In an interactive session, authorize the server (`/mcp`).
2. Enumerate the exposed tools and their input schemas.
3. Rewrite `references/mcp-tools.md` with the real names, arguments, and return
   shapes; remove all `unverified` markers.

Skills MUST reference capabilities through this file and MUST NOT hardcode tool
names in their own prose. Correcting the tool list is then a one-file edit.

## 4. Skills

Five skills. Each is independently usable and states what it does, what it needs,
and what it must never do. They compose through **data on disk**, not by calling
each other's internals.

### 4.1 `portfolio-review` (read-only)

- **Purpose:** Understand what is currently held and how it is exposed.
- **Reads:** MCP positions, balances, quotes, order history; the investment policy
  file (§5) if present.
- **Produces:** Allocation breakdown, concentration analysis (largest positions as
  % of portfolio), sector/asset-class exposure, drift vs. policy targets,
  unrealized P/L per position, and charts via `financial-charts`.
- **Must never:** Call any order-placing tool. This skill is read-only by
  construction and says so in its own instructions.

### 4.2 `trade-workflow`

- **Purpose:** The only path to placing an order. Encodes the guardrails so no
  trade is one-shot.
- **Required sequence, non-skippable:**
  1. **Thesis** — state the reason for the trade in writing.
  2. **Sizing** — position size as % of portfolio, checked against the policy
     file's risk limits and the account's buying power.
  3. **Preview** — call the review/preview tool; surface every warning it returns
     verbatim, including any the model considers minor.
  4. **Confirm** — present symbol, side, quantity, order type, limit price,
     estimated cost, and preview warnings, then **stop and wait for explicit human
     confirmation**. Silence, ambiguity, or an unrelated reply is not
     confirmation.
  5. **Place** — call the place tool only after step 4 returns an explicit yes.
  6. **Log** — append the order and its outcome to the trade log (§5).
- **Must never:** Skip preview; place multiple orders from a single confirmation;
  infer confirmation; place an order in any account other than the Agentic
  account.

### 4.3 `rebalancing`

- **Purpose:** Close the gap between current allocation and policy targets with
  the fewest trades.
- **Reads:** Current allocation (same MCP reads as `portfolio-review`), the policy
  file's targets, drift tolerance bands, and do-not-sell list.
- **Produces:** A drift table, a proposed trade list (symbol, side, quantity,
  estimated value), the resulting projected allocation, and before/after charts.
- **Hands off:** The trade list goes to `trade-workflow`, one order at a time,
  each with its own confirmation. `rebalancing` does not place orders itself and
  does not batch-confirm.
- **Tax awareness:** Flags positions with short-term holding periods and
  potential wash-sale conflicts against recent order history, and prefers selling
  lots that avoid them where the data allows. Where lot-level data is
  unavailable from the MCP, it says so rather than assuming.

### 4.4 `retirement-planning` (no MCP dependency)

- **Purpose:** Long-horizon planning that works with or without a broker
  connection.
- **Reads:** User-supplied figures (age, target retirement age, current balances
  by account type, contribution rate, expected spending) and optionally current
  portfolio value from the MCP if connected.
- **Produces:** Contribution/withdrawal projections across scenarios, savings-rate
  vs. goal analysis, account-location commentary (401k / IRA / taxable / HSA),
  glidepath comparison, and projection charts.
- **Stated assumptions:** Every projection prints its assumptions (return rate,
  inflation, contribution growth, withdrawal rate) alongside the result. A
  projection without visible assumptions is not an acceptable output.

### 4.5 `financial-charts`

- **Purpose:** Owns all chart rendering. The other four skills call it; none of
  them contains chart code.
- Full specification in §6.

## 5. Shared state (outside the repo)

Personal financial data never lives in this repository. Two files, both under
`~/.claude/financial/`:

| File | Written by | Read by |
|---|---|---|
| `investment-policy.md` | User (from template, offered on first run) | `portfolio-review`, `rebalancing`, `trade-workflow` |
| `trade-log.md` | `trade-workflow` (append-only) | `rebalancing` (wash-sale checks), user |

`assets/investment-policy.template.md` ships in the plugin and defines the
schema: target allocation by asset class and/or symbol, drift tolerance bands,
maximum single-position size, do-not-sell list, tax constraints, and cash floor.

Skills degrade gracefully without the policy file: they report what they can and
tell the user which analyses require a policy, rather than inventing targets.

Chart output defaults to `~/.claude/financial/charts/<YYYY-MM-DD>/`.

## 6. Charting

### 6.1 Runtime

The `xy` library (`https://github.com/reflex-dev/xy`) — a Python charting library
with a Rust core, exporting HTML, PNG, SVG, and PDF.

Charts run via **`uv run --with xy python <script>`**. This requires no virtualenv
management and avoids the user's `python3`, which is a broken shim pointing at a
deleted `~/.arize-tracing` venv. `uv` is confirmed present at
`/opt/homebrew/bin/uv`.

Default outputs: **HTML** (xy supports tooltips, crosshairs, pan/zoom, so the
interactive layer comes free) plus **PNG** for pasting elsewhere.

### 6.2 API-surface verification (implementation step)

Two documentation sources disagree on which chart types have shipped (notably
`pie_chart`). The confirmed top-level API is `xy.line_chart`, `xy.scatter_chart`,
the mark constructors `xy.line` / `xy.scatter`, `xy.theme(...)`, a
matplotlib-compatible `xy.pyplot` interface, and `chart.to_html/to_png/to_svg/to_pdf`.

Bar charts, histograms, and heatmaps — which most of the catalog below needs —
are **not confirmed** in the top-level API. Implementation MUST begin by
introspecting the installed package:

```
uv run --with xy python -c "import xy; print(sorted(n for n in dir(xy) if not n.startswith('_')))"
```

and, if the top-level API lacks bar/hist/heatmap, use the `xy.pyplot`
matplotlib-compatible interface (`ax.bar`, `ax.barh`, `ax.hist`, `ax.imshow`) for
those forms. `references/chart-recipes.md` records the working call for each
catalog entry against the version actually installed, and pins that version.

No chart form in the catalog depends on a capability `xy` does not have. In
particular, **`xy` has no candlestick/OHLC chart** (roadmap, not shipped), so
price history is a close-price line — which is also the better form for
holding-period decisions.

### 6.3 Catalog — form chosen by the data's job

| Job | Form | Color job |
|---|---|---|
| Allocation by position / sector | Horizontal stacked bar, top 7 + "Other" | Categorical |
| Portfolio value over time | Line, single series (no legend; title names it) | Single hue |
| Drift vs. target allocation | Diverging bar centered on 0 | Diverging |
| Per-position P/L | Diverging bar, sorted by magnitude | Diverging |
| Return distribution | Histogram | Single hue |
| Holdings correlation | Heatmap | Diverging (−1…+1 is polarity) |
| Retirement projection | Line with **emphasis** — median in accent, percentile bands gray | 1 hue + gray |
| Contributions vs. growth | Stacked area | Categorical (2 slots) |
| Price history | Line (close price) | Single hue |

Part-to-whole uses a **stacked bar, not a pie**: position names are long, and
real portfolios exceed the ~7 classes a pie can carry. Beyond 7 classes the tail
folds into "Other" — never into additional generated hues.

### 6.4 Palette

Pinned into `assets/palette.py` as plain hex constants with light and dark
variants, consumed by `xy.theme(...)` and the mark constructors. Values are taken
from the validated reference palette and were re-validated for this design with
`scripts/validate_palette.js`:

| Set | Mode | Result |
|---|---|---|
| Categorical, 8 slots | light | ALL PASS — worst adjacent CVD ΔE 9.1, normal-vision 19.6 |
| Categorical, 8 slots | dark | ALL PASS — worst adjacent CVD ΔE 8.4, normal-vision 19.3 |
| Diverging poles blue↔red | light | ALL PASS — CVD ΔE 21.6, normal-vision 32.3, contrast ≥3:1 |
| Diverging poles blue↔red | dark | ALL PASS — CVD ΔE 19.2, normal-vision 29.0, contrast ≥3:1 |

Three light-mode categorical slots (aqua, yellow, magenta) fall below 3:1 contrast
against the light surface. The **relief rule** applies: charts using those slots
ship visible direct labels or an accompanying table. This is not optional.

### 6.5 The gain/loss color decision

**Gains and losses are encoded blue (positive) ↔ red (negative), not green/red.**

Measured, not asserted:

| Pair | Protan CVD ΔE | Verdict |
|---|---|---|
| blue `#2a78d6` ↔ red `#e34948` | **21.6** | PASS, ~3× the ≥8 target |
| green `#008300` ↔ red `#e34948` | **7.2** | WARN band — legal only with secondary encoding |

Conventional green/red sits in the failure band the validator exists to catch;
roughly 8% of men cannot separate that pair reliably. Blue/red clears every gate
with margin in both light and dark modes.

Polarity additionally **never rides on hue alone**: every gain/loss mark carries
an explicit sign (`+`/`−`) and a direct value label, and diverging bars are
anchored to a visible zero line.

### 6.6 Chart rules (binding on every chart the plugin emits)

- **One y-axis. Never a dual-axis chart.** Two measures of different scale become
  two charts, small multiples, or a common-base index.
- Sequential = one hue, light→dark. Diverging = two hues + neutral gray midpoint.
  Never a rainbow; never a hue at the diverging midpoint.
- Color follows the entity, never its rank — filtering the position list must not
  repaint the survivors.
- Categorical hues assigned in fixed slot order, never cycled. A 9th series folds
  into "Other" or facets into small multiples.
- ≥2 series ⇒ a legend is always present; ≤4 series are also direct-labeled.
  A single series gets no legend box.
- Thin marks, 2px lines, ≥8px markers, 2px surface gap between stacked segments
  and adjacent bars, recessive grid and axes.
- Text wears text tokens (primary/secondary/muted ink), never the series color.
- Money is formatted with `tabular-nums` in any column that aligns vertically.
- Every chart is rendered and **looked at** before being called done — the
  validator checks color, not label collisions, geometry, or overflow.

## 7. Safety model

Layered, outermost first:

1. **Robinhood's server boundary.** Every account except the dedicated Agentic
   account is read-only at the source. Nothing this plugin does can change that.
2. **Single write path.** `trade-workflow` is the only skill permitted to call an
   order-placing tool. `portfolio-review`, `rebalancing`, `retirement-planning`,
   and `financial-charts` each state in their own instructions that they must not.
3. **Non-skippable preview → explicit confirm → place.** One confirmation
   authorizes exactly one order.
4. **Append-only trade log.** Every placed order is recorded with timestamp,
   thesis, preview warnings, and result.
5. **Policy limits.** Position sizing is checked against the policy file's maximum
   single-position size and cash floor before preview.
6. **No credentials in the repo.** The `.mcp.json` carries a URL only; OAuth is
   handled by the MCP client.

Skills present analysis with stated assumptions. They do not present themselves as
licensed financial advice, and they do not hide uncertainty behind confident
phrasing — where data is missing (lot-level cost basis, for example), they say so.

## 8. Validation

`scripts/validate.sh` — bash + `jq` (confirmed at `/opt/homebrew/bin/jq`).
Deliberately not Python, given the broken `python3` shim. Checks:

1. `.claude-plugin/marketplace.json` and every `plugin.json` / `.mcp.json` parse
   as valid JSON.
2. Every `plugins/*/` referenced by `marketplace.json` exists on disk.
3. Every `skills/*/SKILL.md` exists and opens with YAML frontmatter.
4. Each skill's frontmatter `name:` matches its directory name.
5. Each skill's frontmatter `description:` is non-empty and mentions a trigger
   condition.
6. No skill file contains a hardcoded MCP tool name outside
   `references/mcp-tools.md` (grep guard, enforcing §3.2).

Exit non-zero on any failure. Intended to run before every commit.

## 9. Dependencies

| Dependency | Required by | Notes |
|---|---|---|
| Robinhood agentic MCP | portfolio-review, trade-workflow, rebalancing | OAuth, one-time interactive authorization |
| `uv` | financial-charts | Present at `/opt/homebrew/bin/uv` |
| `xy` (pinned version) | financial-charts | Fetched on demand by `uv run --with xy` |
| `jq` | scripts/validate.sh | Present at `/opt/homebrew/bin/jq` |

`retirement-planning` has no external dependency and works standalone.

## 10. Open items

One, with a defined resolution path (§3.2): the exact Robinhood MCP tool names and
input schemas, pending a one-time interactive OAuth enumeration. All other
decisions in this document are settled.
