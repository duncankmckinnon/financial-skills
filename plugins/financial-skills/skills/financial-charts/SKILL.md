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

Pass the **same `out_dir` for every chart of a run** — that is what lets
`c.show_all()` collect them into one page at the end.

## Commentary

Every renderer takes `note=` — one to three sentences printed under that chart
on the dashboard. A chart shows a shape; the note says what the shape means,
which the chart itself cannot do.

```python
c.allocation_chart(items, d, note=(
    "47% sits in AI / semis — nearly half the book in one correlated theme.\n"
    "The next seven positions together are smaller than that single slice."))
```

Newlines survive, so prefer two short lines to one long one.

**Say what the chart shows, not what to do about it.** "47% in one correlated
theme" reads the chart. "Trim NVDA" is a recommendation, and recommendations
belong to `rebalancing` and `trade-workflow`, which carry position sizing, wash
-sale checks and an explicit confirmation gate. A caption under a chart has
none of those, and the human may act on it without ever seeing the reasoning.

Three more rules:

- **Only what the chart supports.** A note asserting something the reader
  cannot see in the chart above it is unsourced — put it in the text report
  where it can carry its numbers.
- **The note is not the report.** It supplements the numbers you report in
  text; it does not replace them. The human may never open the dashboard.
- **No note is better than a filler note.** "Allocation across positions"
  restates the title. Leave `note=` unset and the panel prints nothing.

For a flat portfolio where `c.unlabelled_share(items)` is high, the note is a
good place to point at the table that carries the identities the chart cannot.

## Charting anything

The module is **not limited to portfolio data**. Pick the generic renderer by
the data's job — it applies the palette, folding, labelling and axis rules for
you, whatever the subject:

| The reader's job | Function |
|---|---|
| Compare magnitude across categories | `magnitude_chart(items, …)` |
| Follow one or more series over a common x | `series_chart(x, {name: values}, …)` |
| See part-to-whole | `part_to_whole_chart(items, …)` |
| See above/below a baseline | `diverging_chart(pairs, …)` |
| See the shape of a sample | `distribution_chart(values, …)` |
| See a grid of values | `matrix_chart(labels, matrix, diverging=…)` |
| See how two measures relate | `relationship_chart(x, y, …)` |

`series_chart(..., emphasis="name")` paints one series in the accent hue and the
rest gray. When one line is the point and the others are context, that is the
honest form — reach for it before a rainbow of equal-weight series.

`matrix_chart(diverging=True)` only when the data has a meaningful zero or
midpoint. Otherwise the sequential ramp; a diverging ramp on data with no
midpoint invents a story about the middle of the range.

## Financial presets

Thin wrappers over the generic renderers, with the right labels and units:

| The reader must… | Function | Form |
|---|---|---|
| See allocation by position or class | `allocation_chart` | Horizontal stacked bar, top 7 + "Other" |
| See portfolio value over time | `value_over_time_chart` | Line, single series |
| See over/under vs target | `drift_chart` | Diverging bar on a zero line |
| See per-position profit and loss | `pl_chart` | Diverging bar, sorted |
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

## Output — ephemeral by default

`c.chart_dir()` returns a **temporary directory**, stable for the run so a
batch of charts lands together. Charts are derived output: regenerable from
live data in seconds, and they hold real position and P/L figures. Keeping
every render forever accumulates sensitive data with no lifecycle.

Use `c.chart_dir(keep=True)` — archiving under `$FINANCIAL_HOME/charts/<date>/`
— only when the human asks for a chart they want to keep. Tell them where it
went when you do.

Both HTML (interactive — `xy` gives tooltips, crosshairs, pan and zoom for
free) and PNG are written, plus a `dashboard.html` collecting the run's charts
once you call `c.dashboard()` or `c.show_all()`.

Every chart carries an **as-of stamp** on its axis label. Do not strip it: an
ephemeral chart that someone saves off has no directory name to fall back on,
and an undated financial chart is indistinguishable from a stale one the moment
prices move.

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

**Render the whole batch, then open it once with `c.show_all()`.** A review is
one finding, not N — opening a tab per chart makes the human assemble the story
from separate windows, and a chart they closed to reach the next one is a chart
they cannot compare against.

```python
d = c.chart_dir()                       # stable for the run
c.allocation_chart(items, d, note="47% sits in AI / semis — half the book.")
c.pl_chart(pl, d, note="Gains concentrated in NVDA; losses small and spread.")
c.drift_chart(current, target, d)       # no note is fine
if not c.show_all(d, title="Portfolio review"):
    print(f"no display available - dashboard written to {d}/dashboard.html")
```

`show_all()` builds `dashboard.html` in the run directory — every chart of the
run in one grid, each still fully interactive and each linking out to itself
for a closer look — and opens that single tab. Headings come from each
renderer's `title=`, so pass a real one; panels appear in render order, so
render in the order the story is told.

For a genuinely single chart, `c.show(path)` still opens that chart alone.
Both return False when no viewer could be launched. Report the file path then,
rather than implying the chart was delivered.

Panels are sized to the chart's own 900×420 render — `xy` does not reflow to
its container, so a stretched frame bands the panel white and a narrowed one
crops the axis label. Two charts sit side by side only on a viewport wide
enough to hold both at full size; otherwise they stack. Do not "fix" this by
making the frames fluid.

Report the numbers in text as well. A chart the human has not opened yet, or
cannot open, must not be the only place a finding appears.

## Boundaries

This skill must not call any MCP tool and must not place, preview, or modify any
order. It renders data it is handed. Order placement belongs to `trade-workflow`
alone.

See `references/chart-recipes.md` for the verified `xy` call behind each form,
including the `orientation="horizontal"` axis-role trap that renders charts
silently wrong.
