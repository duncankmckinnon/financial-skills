# xy chart recipes

Pinned version: **xy==0.0.6** (verified 2026-08-15)
Run everything as: `uv run --with 'xy==0.0.6' python <script>`

All nine catalog forms are **AVAILABLE** natively. The `xy.pyplot`
matplotlib-compatible fallback the plan allowed for is **not needed**.

## API shape

`xy` is declarative composition, not stateful pyplot. Marks and chrome
components are passed as children to a chart container:

```python
xy.bar_chart(xy.bar(...), xy.legend(), xy.x_axis(...), xy.theme(...))
```

Available marks: `line`, `area`, `bar`, `column`, `scatter`, `hist`/`histogram`,
`heatmap`, `box`, `violin`, `ecdf`, `funnel`, `step`, `stairs`, `ribbon`,
`error_band`, `sankey`, `contour`, `hexbin`.
Chrome: `theme`, `legend`, `x_axis`, `y_axis`, `label`, `hline`, `vline`,
`annotations`, `tooltip`, `colorbar`, `callout`.
Export: `chart.to_html(path)`, `chart.to_png(path)`, `chart.to_svg(path)`.
**There is no `to_pdf`** — the plan's mention of PDF was wrong; HTML + PNG only.

## THE TRAP: `orientation="horizontal"`

Verified empirically over four failed probes. Get this wrong and the chart
renders silently wrong rather than raising.

- The **mark** takes `x` = category position (numeric), `y` = value (bar length).
- The **axis components stay screen-oriented**: `y_axis` configures the
  vertical screen axis (which holds the categories), `x_axis` configures the
  horizontal screen axis (which holds the values).

So category tick labels go on `y_axis`, and the value axis label goes on
`x_axis` — the opposite of what the mark's own arguments suggest.

Two further constraints:
- **Category axes must be numeric.** Passing strings raises
  `ValueError: bar y must be real numeric`. Use `0.0, 1.0, 2.0 …` positions
  plus `tick_values` / `tick_labels`.
- **`colors=` is per-series, not per-bar.** A diverging bar needs *two marks*
  — one for negative values, one for positive — not one mark with a colors list.
  Passing a per-bar list raises `ValueError: colors must have length 1, got 3`.

## Allocation — horizontal stacked bar
Status: AVAILABLE. Stack manually with `base=` accumulating the running total.

```python
marks, base = [], 0.0
for label, value, color in zip(labels, values, colors):
    marks.append(xy.bar(x=[0.0], y=[value], base=base, color=color, name=label,
                        orientation="horizontal", width=0.5,
                        stroke=SURFACE, stroke_width=2))   # 2px surface gap
    base += value
xy.bar_chart(*marks, xy.legend(),
             xy.y_axis(tick_values=[0.0], tick_labels=["Allocation"]),
             xy.x_axis(label="% of portfolio"), THEME)
```

## Drift vs target / per-position P/L — diverging bar
Status: AVAILABLE. Split into a negative mark and a positive mark.

```python
xs = [float(i) for i in range(len(labels))]
neg = [(p, v) for p, v in zip(xs, vals) if v < 0]
pos = [(p, v) for p, v in zip(xs, vals) if v >= 0]
xy.bar_chart(
    xy.bar(x=[p for p, _ in neg], y=[v for _, v in neg],
           color=NEGATIVE, orientation="horizontal", width=0.5),
    xy.bar(x=[p for p, _ in pos], y=[v for _, v in pos],
           color=POSITIVE, orientation="horizontal", width=0.5),
    xy.vline(0, color=BASELINE, width=2),          # visible zero line
    xy.y_axis(tick_values=xs, tick_labels=labels), # categories: y_axis
    xy.x_axis(label="percentage points vs target"),
    THEME)
```

## Portfolio value over time / price history — line
Status: AVAILABLE. Single series, no legend.

```python
xy.line_chart(xy.line(dates, values, color=SERIES_1, width=2), THEME)
```

## Return distribution — histogram
Status: AVAILABLE.

```python
xy.histogram_chart(xy.hist(values, bins=30, color=SERIES_1), THEME)
```

## Holdings correlation — heatmap
Status: AVAILABLE. `colormap` accepts an explicit list of hex stops, so the
diverging ramp from `palette.diverging_ramp()` drops straight in.

```python
xy.heatmap_chart(
    xy.heatmap(z, x=labels, y=labels,
               colormap=diverging_ramp(mode, 5), domain=(-1.0, 1.0)),
    THEME)
```

Note: `heatmap` accepts **string** x/y (unlike `bar`).

## Retirement projection — line with emphasis
Status: AVAILABLE. Draw the bands first so the median paints on top.

```python
xy.line_chart(
    *[xy.line(years, s, color=DE_EMPHASIS, width=2, name=n)
      for n, s in bands.items()],
    xy.line(years, median, color=SERIES_1, width=2, name="median"),
    xy.legend(), THEME)
```

## Contributions vs growth — stacked area
Status: AVAILABLE. Stack by passing the lower series as `base`, and pass the
*cumulative* upper series as `y`.

```python
xy.area_chart(
    xy.area(years, cumulative_top, base=contributed, color=SERIES_2, name="growth"),
    xy.area(years, contributed, color=SERIES_1, name="contributed"),
    xy.legend(), THEME)
```

## Theme
Status: AVAILABLE, signature matches the plan exactly.

```python
xy.theme(background=SURFACE, plot_background=SURFACE, grid_color=GRID,
         axis_color=BASELINE, text_color=PRIMARY_INK)
```

## Calls added with the declarative spec

Verified against `xy` 0.0.6 on 2026-11-22, by render and by looking.

| Need | Call | Notes |
|---|---|---|
| Render at a block's size | `xy.bar_chart(..., width=590, height=260)` — any chart constructor | `width` / `height` are pixels. The chart does **not** reflow afterwards, so size is fixed at build time. PNG export is 2× those pixels; SVG is 1×. |
| SVG export | `chart.to_svg()` | Returns the markup. Mark colours come out as `rgb(r,g,b)`, text and chrome as hex — normalise before asserting on a colour. |
| HTML export | `chart.to_html()` | Self-contained (~440 KB), with its own restrictive content-security policy. Returns the document; writes it too when given a path. |
| Reference line | `xy.hline(y, text="label", color=…, width=1.5)` | The label sits on the line at the right edge. |
| Shaded range behind a series | `xy.error_band(x, lower, upper, color=…, opacity=0.35)` | Draw it before the lines so they paint over it. |
| Negative-bar label | `xy.label(v, i, text, anchor="end", dx=-6.0)` | `dx` defaults to `+6` for every label. Left at the default, a negative bar's label is pushed back over its own bar. |
| Missing heatmap cell | `float("nan")` in `z` | Renders as an empty cell. |
| String x values | `xy.line(["2026-01", "2026-02"], [...])` | Treated as ordered categories; tick labels thin themselves. |

**Label fit is in pixels, not share.** Label text is ~7.5px a character at
every chart width, and ~80px of the width goes to the category tick label and
padding. A segment label that fits at 1200px collides at 590px, so
`_label_fits` takes the render width.

**Small multiples are separate charts.** `xy.facet_chart` repeats one mark
composition per value, which does not fit categorical bars whose labels differ
between panels. `build_facets` instead builds one chart per value and passes
every panel the same value-axis `domain`.

**The interactive chart needs WebGL2.** `to_html()` draws with WebGL2; in a
viewer without it the frame shows only "xy: WebGL2 unavailable in this
browser." The PNG and SVG exports do not need it, which is why every panel
links both. Checking a page headlessly needs software GL switched on
(`--enable-unsafe-swiftshader --use-angle=swiftshader`), or every frame is
blank and the page looks broken when it is not.

**Axis labels wrap in the page but not in the PNG.** The interactive render
wraps an axis label wider than the plot, and the second line falls outside the
frame. The PNG export never wraps, so this is invisible unless the page itself
is looked at. `_axis_label` therefore drops the descriptive text and keeps the
as-of stamp when the two will not fit the render width.
