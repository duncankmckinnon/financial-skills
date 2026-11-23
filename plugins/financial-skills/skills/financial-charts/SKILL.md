---
name: financial-charts
description: Use when rendering any chart of financial data — allocation, drift, profit/loss, portfolio value over time, spending, return distributions, correlation, retirement projections, or contributions vs growth — or when building a dashboard page of charts, figures and tables. Invoke this rather than writing chart code inline.
---

# Financial Charts

This skill owns **all** chart rendering in the plugin. `portfolio-review`,
`rebalancing`, and `retirement-planning` hand off to it rather than growing
their own chart code.

Charts are **declared, not coded**. You write a JSON spec — the rows, the
charts, the page — and run one fixed command. The agent writes no Python.

## Runtime

Always:

```bash
uv run --with 'xy==0.0.6' python "$ROOT/scripts/charts.py" validate spec.json
uv run --with 'xy==0.0.6' python "$ROOT/scripts/charts.py" render spec.json --open
```

**Never invoke bare `python3`** — on some machines it is a broken shim. `uv`
fetches `xy` on demand; there is no venv to manage.

**Resolving `$ROOT`**, in order — this skill works under any agent harness, so
never hardcode an install location:

1. `$FINANCIAL_SKILLS_ROOT`, if set
2. two levels up from this skill's own directory (`skills/financial-charts/` →
   plugin root), which your harness tells you when it loads this skill
3. `$FINANCIAL_HOME/env.sh`, written by `financial-setup`

`charts.py` is self-locating — it finds its sibling modules and the palette
from its own path, so that one path is all you need.

## The workflow

1. **Write the spec** to a scratch file. The full format — every key, form,
   step and block — is in `references/chart-spec.md`. Read it before writing
   your first spec of a session.
2. **Validate.** A wrong spec is refused before anything renders, with every
   problem listed and located (`charts[2].steps[0]`). Fix them all, re-run.
3. **Render** with `--open`. One command produces the whole run.
4. **Read the summary** it prints: the page path, each chart's PNG, and any
   `warnings`. Report the warnings — they are findings about the charts, such
   as "folded 5 into Other" or a bar that will carry no label.

A short spec, to show the shape:

```json
{
  "title": "Portfolio review",
  "sources": [{"name": "robinhood", "as_of": "2026-11-22 14:05", "live": true}],
  "data": {"positions": {"rows": [
    {"symbol": "NVDA", "value": 5200, "cost": 2100},
    {"symbol": "VTI",  "value": 8400, "cost": 7000}
  ]}},
  "charts": [
    {"id": "allocation", "form": "part_to_whole", "preset": "allocation",
     "from": "positions", "label": "symbol", "value": "value",
     "note": "VTI is over half the book."},
    {"id": "pl", "form": "diverging", "preset": "pl", "from": "positions",
     "steps": [{"diff": {"a": "value", "b": "cost", "as": "pl"}}],
     "label": "symbol", "value": "pl"}
  ]
}
```

### Hand it rows, not pre-shaped numbers

Put the rows in as the source returned them and declare the shaping in
`steps`: `filter`, `group`, `share`, `diff`, `sort`, `top`. Two charts can
shape one table differently, and each chart's shaped rows are downloadable as
CSV, so the human can check the figures behind any chart.

Steps are a closed list with no expressions. A figure they cannot produce —
a correlation, a projection — you compute first and put in the rows.

### Say where the rows came from

When rows came from connected sources, fill in the spec's `"sources"`: each
source's name, its as-of time, and whether it is live. The page header prints
them and says plainly when any figure is synced rather than live. This is how
the rule in `references/sources.md` — every figure carries its source and
as-of time — reaches the page. Hand-supplied numbers need no `sources`.

## Choosing a form

Pick by the reader's job, whatever the subject — the module is **not limited
to portfolio data**:

| The reader's job | Form |
|---|---|
| Compare size across categories | `magnitude` |
| Follow one or more series over a common x | `series` |
| See part-to-whole | `part_to_whole` |
| See above/below a baseline | `diverging` |
| See parts of a total over time | `stacked_area` |
| See the shape of a sample | `distribution` |
| See a grid of values | `matrix` |
| See how two measures relate | `relationship` |

Presets set the labels and units for the financial cases: `allocation`,
`drift`, `pl`, `value_over_time`, `correlation`, `projection`,
`contributions`.

- `series` with `"emphasis": "name"` paints one series in the accent hue and
  the rest gray. When one line is the point and the others are context, that
  is the honest form — reach for it before a rainbow of equal-weight series.
- `series` takes `reference_lines` and a shaded `band` — a target, a starting
  value, a low–high range.
- `"facet": "account"` repeats a chart per account, or per source, on one
  shared axis. Use it instead of cramming every account into one chart.
- `matrix` with `"diverging": true` only when the data has a meaningful zero
  or midpoint. Otherwise the sequential ramp; a diverging ramp on data with no
  midpoint invents a story about the middle of the range.

Part-to-whole is a **stacked bar, never a pie** — position names are long and
real portfolios exceed the classes a pie can carry. `xy` has **no
candlestick/OHLC chart**; a close-price `series` is the better read for
holding-period decisions anyway.

## Building the page

Without `"page"`, every chart appears once, full width. Declare `page` to tell
the story in order: sections with headings, and in each section any mix of

- **chart** blocks at `full`, `half` or `third` width and `short`, `regular`
  or `tall` height — the chart is drawn at exactly that size
- **stat** blocks — a headline number, with an optional signed change
- **table** blocks — the rows themselves, with a CSV download
- **text** blocks — a paragraph of commentary

Two halves or three thirds make a row. Lead with the stats and the one chart
that carries the finding; put supporting charts at half width beneath; end
with the table that backs them. There is no limit on charts or sections.

Sizes are fixed when the page renders — blocks wrap on a narrow window, they
do not shrink. `part_to_whole` and `matrix` need at least `half`.

## Commentary

Every chart takes a `"note"` — one to three sentences printed under it. A
chart shows a shape; the note says what the shape means, which the chart
itself cannot do. Newlines survive, so prefer two short lines to one long one.

**Say what the chart shows, not what to do about it.** "47% in one correlated
theme" reads the chart. "Trim NVDA" is a recommendation, and recommendations
belong to `rebalancing` and `trade-workflow`, which carry position sizing,
wash-sale checks and an explicit confirmation gate. A caption under a chart
has none of those, and the human may act on it without ever seeing the
reasoning.

Three more rules:

- **Only what the chart supports.** A note asserting something the reader
  cannot see in the chart above it is unsourced — put it in the text report
  where it can carry its numbers.
- **The note is not the report.** It supplements the numbers you report in
  text; it does not replace them. The human may never open the page.
- **No note is better than a filler note.** "Allocation across positions"
  restates the title. Leave `"note"` out and the panel prints nothing.

## Color rules

Enforced in code. The spec has no field that turns any of them off.

- **Gains are blue, losses are red. Never green/red.** Measured: blue↔red
  separates at protan ΔE 21.6; green↔red at 7.2, inside the failure band where
  roughly 8% of men cannot tell the pair apart. This is deliberate — do not
  work around it to match finance convention.
- **Polarity never rides on hue alone.** Every gain/loss mark carries an
  explicit `+`/`−` sign and a direct value label, anchored to a visible zero
  line.
- **One y-axis. There is never a dual-axis chart.** Two measures of different
  scale become two charts, small multiples, or a common-base index.
- Categorical hues are assigned in **fixed slot order, never cycled**. Past 8
  classes the tail must **fold** into "Other" or facet into small multiples —
  a generated 9th hue is indistinguishable under CVD. Validation refuses a
  ninth series.
- **Relief rule:** categorical slots 3–5 (aqua, yellow, magenta) sit below 3:1
  contrast on the light surface, so charts using them ship visible direct
  labels or an accompanying table.

## Flat portfolios need a table, not just the chart

A `part_to_whole` chart labels only the segments wide enough to hold their
text; thinner ones are carried by the legend. When most of the bar is
unlabelled, or "Other" swallows most of it, the render **warns**. Act on it:
add a **table block** beside the chart — that is what satisfies the relief
rule, and for a flat book the chart alone cannot carry identity.

A portfolio of 100+ near-equal positions has no readable stacked bar at
position level at all. Group into asset classes or themes first, with a
`group` step, or show the table alone. A chart that cannot be read is worse
than no chart.

## Output — ephemeral by default

A run is written to a **temporary directory**. Charts are derived output:
regenerable from live data in seconds, and they hold real position and P/L
figures. Keeping every render forever accumulates sensitive data with no
lifecycle.

Pass `--keep` — archiving under `$FINANCIAL_HOME/charts/<date>/` — only when
the human asks for charts they want to keep. Tell them where it went.

The run is **one page**: a single self-contained HTML file with every chart on
it, interactive (tooltips, crosshair, pan, zoom), needing no other file and no
network — so it can be moved, attached or archived by itself. Every chart has
**download** links for PNG, SVG and the CSV of its rows; every table has its
CSV; the header has the spec that produced the page.

Every chart carries an **as-of stamp** on its axis. It cannot be removed: a
chart that someone saves off has no page header to fall back on, and an
undated financial chart is indistinguishable from a stale one the moment
prices move.

## Mandatory final steps

### 1. Look at it yourself

**Read the PNGs the summary lists and inspect them** before reporting done.
The palette is validated by script, but nothing validates layout. Every layout
bug this module has had — labels placed off-plot, tip labels clipped at the
plot edge, segment labels colliding, an axis labelled in percent while
plotting dollars, a row of panels wrapping because each was two pixels too
wide — **passed its unit tests** and was caught only by looking. Check for:

- label collisions and labels running off the plot
- the zero line actually visible on diverging charts
- legend not covering marks
- axis label and plotted units actually agreeing
- dark-mode text legible against the dark surface
- a chart too cramped for the size its block gave it — give it a bigger block

### 2. Then show it to the human

**Reading a PNG renders it into your context, not theirs.** The human sees
nothing unless the page is opened. Never describe a chart as though they can
see it.

`render --open` opens the page — one tab for the whole run. A review is one
finding, not N: opening a tab per chart makes the human assemble the story
from separate windows. The summary's `"opened"` is `false` when no viewer
could be launched. Report the page path then, rather than implying the charts
were delivered.

If a chart panel is blank apart from a line about WebGL, the viewer cannot
draw the interactive chart. Nothing is wrong with the page: the PNG and SVG
links on that panel still work, and so do the PNG files in the summary.

Report the numbers in text as well. A chart the human has not opened yet, or
cannot open, must not be the only place a finding appears.

## Boundaries

This skill must not call any data-source tool and must not place, preview, or
modify any order. It renders rows it is handed. Order placement belongs to
`trade-workflow` alone.

See `references/chart-spec.md` for the spec format, and
`references/chart-recipes.md` for the verified `xy` call behind each form —
needed only when changing the renderers, not when writing a spec.
