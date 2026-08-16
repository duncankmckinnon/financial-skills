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
