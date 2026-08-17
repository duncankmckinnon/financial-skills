---
name: financial-charts
description: Use when rendering any chart of financial data — allocation, drift, profit/loss, portfolio value over time, return distributions, correlation, retirement projections, or contributions vs growth. Invoke this rather than writing chart code inline.
---

# Financial Charts

This skill owns **all** chart rendering in the plugin. `portfolio-review`,
`rebalancing`, and `retirement-planning` call it rather than growing their own
chart code.

## Runtime

Always:

```bash
uv run --with 'xy==0.0.6' python <script>
```

**Never invoke bare `python3`** — on this machine it is a broken shim pointing at
a deleted venv. `uv` fetches `xy` on demand; there is no venv to manage.

## Entry point

Import the shipped module, `scripts/charts.py`. Do not write chart code inline —
the module encodes rules that are easy to get wrong and that fail *silently*
when wrong.

**Resolving the path**, in order — this skill works under any agent harness, so
never hardcode an install location:

1. `$FINANCIAL_SKILLS_ROOT`, if set
2. two levels up from this skill's own directory (`skills/financial-charts/` →
   plugin root), which your harness tells you when it loads this skill
3. `$FINANCIAL_HOME/env.sh`, written by `financial-setup`

`charts.py` is **self-locating** — it finds `assets/palette.py` from its own
path, so you only need the one path above.

```python
import sys
sys.path.insert(0, f"{ROOT}/scripts")   # ROOT resolved as above
import charts as c

c.allocation_chart(items, c.chart_dir(), mode="light")
```

Every renderer takes `out_dir` and `mode` (`"light"` or `"dark"`), writes
`<name>.html` and `<name>.png`, and returns the HTML path. `c.chart_dir()`
returns today's dated output directory under `$FINANCIAL_HOME`.

## Choosing the form — by the data's job, not by convention

| The reader must… | Function | Form |
|---|---|---|
| See allocation by position or class | `allocation_chart` | Horizontal stacked bar, top 7 + "Other" |
| See portfolio value over time | `value_over_time_chart` | Line, single series |
| See over/under vs target | `drift_chart` | Diverging bar on a zero line |
| See per-position profit and loss | `pl_chart` | Diverging bar, sorted |
| See the shape of returns | `distribution_chart` | Histogram |
| See how holdings move together | `correlation_chart` | Diverging heatmap |
| See a retirement projection | `projection_chart` | Line, median emphasized |
| See contributions vs growth | `contributions_chart` | Stacked area |
| See price history | `value_over_time_chart` | Line (close) |

Part-to-whole is a **stacked bar, never a pie** — position names are long and
real portfolios exceed the classes a pie can carry.

`xy` has **no candlestick/OHLC chart**. Do not attempt one. A close-price line is
the better read for holding-period decisions anyway.

## Color rules

- **Gains are blue, losses are red. Never green/red.** Measured: blue↔red
  separates at protan ΔE 21.6; green↔red at 7.2, inside the failure band where
  roughly 8% of men cannot tell the pair apart. This is deliberate — do not
  "fix" it to match finance convention.
- **Polarity never rides on hue alone.** Every gain/loss mark carries an explicit
  `+`/`−` sign and a direct value label, anchored to a visible zero line. The
  module does this for you; do not strip it.
- **One y-axis. Never a dual-axis chart.** Two measures of different scale become
  two charts, small multiples, or a common-base index.
- Categorical hues are assigned in **fixed slot order, never cycled**. Past 8
  classes the tail must **fold** into "Other" or facet into small multiples — a
  generated 9th hue is indistinguishable under CVD. `series_colors` raises
  rather than let this happen.
- **Relief rule:** categorical slots 3–5 (aqua, yellow, magenta) sit below 3:1
  contrast on the light surface, so charts using them ship visible direct labels
  or an accompanying table.

## Flat portfolios need a table, not just the chart

`allocation_chart` labels only segments wide enough to hold their text (≥6% of
the total); thinner ones are carried by the legend, because labelling them
produces overlapping text and a final label off the plot edge.

Call `c.unlabelled_share(items)` before reporting. When it is non-trivial,
**print the allocation as a table alongside the chart** — that is what satisfies
the relief rule, and for a flat book the chart alone cannot carry identity.

A portfolio of 100+ near-equal positions has no readable stacked bar at position
level at all. Group into asset classes or themes first, or report the table
alone. A chart that cannot be read is worse than no chart.
- Text wears ink tokens (primary/secondary/muted), never a series color.

## Output

Write to `$FINANCIAL_HOME/charts/<YYYY-MM-DD>/`. Both HTML (interactive —
`xy` gives tooltips, crosshairs, pan and zoom for free) and PNG.

## Mandatory final steps

### 1. Look at it yourself

**Render, then read the PNG and inspect it** before reporting done. The palette
is validated by script, but nothing validates layout. Every layout bug this
module has had — labels placed off-plot, tip labels clipped at the plot edge,
segment labels colliding, an axis labelled in percent while plotting dollars —
**passed its unit tests** and was caught only by looking. Check for:

- label collisions and labels running off the plot
- the zero line actually visible on diverging charts
- legend not covering marks
- axis label and plotted units actually agreeing
- dark-mode text legible against the dark surface

### 2. Then show it to the human

**Reading a PNG renders it into your context, not theirs.** The human sees
nothing unless you open it. Never describe a chart as though they can see it.

Open the interactive HTML — it carries tooltips, crosshair, pan and zoom:

```bash
open "$FINANCIAL_HOME/charts/<date>/<name>.html"     # macOS
xdg-open "$FINANCIAL_HOME/charts/<date>/<name>.html" # Linux
```

If the environment has no display, say so and give the file path instead of
pretending the chart was delivered.

Report the numbers in text as well. A chart the human has not opened yet, or
cannot open, must not be the only place a finding appears.

## Boundaries

This skill must not call any MCP tool and must not place, preview, or modify any
order. It renders data it is handed. Order placement belongs to `trade-workflow`
alone.

See `references/chart-recipes.md` for the verified `xy` call behind each form,
including the `orientation="horizontal"` axis-role trap that renders charts
silently wrong.
