"""Chart data-shaping helpers and renderers for the financial-skills plugin.

Run via: uv run --with 'xy==0.0.6' python ...

Rendering rules this module enforces so callers cannot get them wrong:
  - gains blue / losses red, never green/red
  - every polarity mark carries an explicit sign and a direct value label
  - diverging charts anchor to a visible zero line
  - one y-axis, never two
  - categorical hues in fixed slot order; long tails fold into "Other"

See references/chart-recipes.md for the verified xy 0.0.6 call for each form,
including the orientation="horizontal" axis-role trap.
"""
import os
import pathlib
import sys

import xy

# Self-locating: find assets/palette.py relative to this file rather than
# making every caller configure sys.path. Keeps the module usable from any
# agent harness, which only needs to know where this script lives.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "assets"))

import palette as p  # noqa: E402  (import follows the path fix above)

MINUS = "−"  # U+2212, not a hyphen


def financial_home():
    """Where personal financial data lives.

    Defaults to ~/.financial, deliberately not inside any agent harness's
    config directory -- this is the user's data, not the tool's. Override
    with FINANCIAL_HOME.
    """
    env = os.environ.get("FINANCIAL_HOME")
    if env:
        return pathlib.Path(env).expanduser()
    return pathlib.Path.home() / ".financial"


def chart_dir(date=None):
    """Dated chart output directory under the financial home."""
    import datetime
    day = date or datetime.date.today().isoformat()
    return financial_home() / "charts" / day


def fold_tail(items, keep=7):
    """Top `keep` by value descending; everything else summed into 'Other'.

    Never generates additional hues for a long tail -- the tail folds.
    """
    ordered = sorted(items, key=lambda kv: kv[1], reverse=True)
    if len(ordered) <= keep:
        return ordered
    head, tail = ordered[:keep], ordered[keep:]
    return head + [("Other", sum(v for _, v in tail))]


def compute_drift(current, target):
    """(label, current - target) in percentage points, most-negative first."""
    labels = set(current) | set(target)
    out = [(l, current.get(l, 0.0) - target.get(l, 0.0)) for l in labels]
    return sorted(out, key=lambda kv: kv[1])


def series_colors(n, mode):
    """First `n` categorical slots, fixed order, never cycled."""
    slots = p.CATEGORICAL[mode]
    if n > len(slots):
        raise ValueError(
            f"{n} series exceeds the {len(slots)}-slot categorical palette. "
            "Fold the tail into 'Other' or facet into small multiples -- "
            "never generate another hue."
        )
    return slots[:n]


def polarity_color(value, mode):
    """Blue for >= 0, red for < 0. Never green/red."""
    return p.POSITIVE[mode] if value >= 0 else p.NEGATIVE[mode]


def signed_label(value, unit=""):
    """Explicit sign so polarity never rides on hue alone."""
    sign = "+" if value >= 0 else MINUS
    mag = abs(value)
    if unit == "$":
        return f"{sign}${mag:,.0f}"
    if unit == "%":
        return f"{sign}{mag:.1f}%"
    return f"{sign}{mag:,.2f}{unit}"


# ---------------------------------------------------------------------------
# Renderers. Every one returns the path of the written HTML file and also
# writes a sibling PNG. See references/chart-recipes.md before editing --
# orientation="horizontal" has a non-obvious axis-role mapping.
# ---------------------------------------------------------------------------


def _theme(mode):
    return xy.theme(
        background=p.SURFACE[mode], plot_background=p.SURFACE[mode],
        grid_color=p.INK[mode]["grid"], axis_color=p.INK[mode]["baseline"],
        text_color=p.INK[mode]["primary"],
    )


def _write(chart, out_dir, stem):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html = out_dir / f"{stem}.html"
    chart.to_html(str(html))
    chart.to_png(str(out_dir / f"{stem}.png"))
    return html


# Annotations are SCREEN-oriented (x = value axis, y = category axis) even
# though bar marks with orientation="horizontal" are transposed. Getting this
# backwards places labels off-plot: they still appear in the HTML source but
# vanish from the render. These builders are extracted so the coordinates can
# be asserted directly -- grepping the HTML cannot catch the bug.

def _padded_domain(values, pad=0.28):
    """Value-axis domain with headroom so tip labels are not clipped.

    Always includes zero -- a diverging chart that crops its own baseline
    misstates the data.
    """
    lo, hi = min(list(values) + [0.0]), max(list(values) + [0.0])
    span = (hi - lo) or 1.0
    return (lo - span * pad, hi + span * pad)


def _allocation_labels(folded, mode, total=None):
    """Direct label per segment, at the segment midpoint on the value axis."""
    if total is None:
        total = sum(v for _, v in folded) or 1.0
    out, run = [], 0.0
    for label, value in folded:
        out.append(xy.label(run + value / 2, 0.0,
                            f"{label} {value / total * 100:.1f}%",
                            color=p.INK[mode]["secondary"]))
        run += value
    return out


def _diverging_bar_labels(pairs, mode, unit):
    """Signed label per bar, at the bar's tip on the value axis."""
    return [xy.label(v, float(i), signed_label(v, unit),
                     color=p.INK[mode]["secondary"],
                     anchor="start" if v >= 0 else "end")
            for i, (_, v) in enumerate(pairs)]


def allocation_chart(items, out_dir, mode="light", title="Allocation"):
    """Part-to-whole: horizontal stacked bar, top 7 + Other. Never a pie."""
    folded = fold_tail(items, keep=7)
    colors = series_colors(len(folded), mode)
    total = sum(v for _, v in folded) or 1.0
    marks, base = [], 0.0
    for (label, value), color in zip(folded, colors):
        marks.append(xy.bar(
            x=[0.0], y=[value], base=base, color=color, name=label,
            orientation="horizontal", width=0.5,
            stroke=p.SURFACE[mode], stroke_width=2,  # 2px surface gap
        ))
        base += value
    return _write(xy.bar_chart(
        *marks, *_allocation_labels(folded, mode, total), xy.legend(),
        xy.y_axis(tick_values=[0.0], tick_labels=[title]),
        xy.x_axis(label="% of portfolio"),
        _theme(mode),
    ), out_dir, "allocation")


def _diverging_bar(pairs, out_dir, mode, stem, unit, axis_label):
    """Shared body for drift and P/L: two marks, zero line, signed labels."""
    xs = [float(i) for i in range(len(pairs))]
    neg = [(x, v) for x, (_, v) in zip(xs, pairs) if v < 0]
    pos = [(x, v) for x, (_, v) in zip(xs, pairs) if v >= 0]
    marks = []
    if neg:
        marks.append(xy.bar(x=[x for x, _ in neg], y=[v for _, v in neg],
                            color=p.NEGATIVE[mode], orientation="horizontal",
                            width=0.5))
    if pos:
        marks.append(xy.bar(x=[x for x, _ in pos], y=[v for _, v in pos],
                            color=p.POSITIVE[mode], orientation="horizontal",
                            width=0.5))
    return _write(xy.bar_chart(
        *marks, *_diverging_bar_labels(pairs, mode, unit),
        xy.vline(0, color=p.INK[mode]["baseline"], width=2),  # visible zero
        xy.y_axis(tick_values=xs, tick_labels=[l for l, _ in pairs]),
        xy.x_axis(label=axis_label,
                  domain=_padded_domain([v for _, v in pairs])),
        _theme(mode),
    ), out_dir, stem)


def drift_chart(current, target, out_dir, mode="light", title="Drift vs target"):
    """Polarity: diverging bar centred on a visible zero line."""
    return _diverging_bar(compute_drift(current, target), out_dir, mode,
                          "drift", "%", "percentage points vs target")


def pl_chart(items, out_dir, mode="light", title="Unrealized P/L"):
    """Polarity: diverging bar, sorted by magnitude."""
    ordered = sorted(items, key=lambda kv: kv[1])
    return _diverging_bar(ordered, out_dir, mode, "pl", "$",
                          "unrealized profit / loss")


def value_over_time_chart(dates, values, out_dir, mode="light",
                          title="Portfolio value"):
    """Trend, single series: no legend -- the title names it."""
    return _write(xy.line_chart(
        xy.line(dates, values, color=p.CATEGORICAL[mode][0], width=2),
        xy.y_axis(label=title),
        _theme(mode),
    ), out_dir, "value_over_time")


def distribution_chart(returns, out_dir, mode="light",
                       title="Return distribution"):
    """Distribution: histogram, single hue."""
    return _write(xy.histogram_chart(
        xy.hist(returns, bins=30, color=p.CATEGORICAL[mode][0]),
        xy.x_axis(label=title),
        _theme(mode),
    ), out_dir, "distribution")


def correlation_chart(labels, matrix, out_dir, mode="light",
                      title="Correlation"):
    """-1..+1 is polarity, so the ramp diverges around a neutral midpoint."""
    return _write(xy.heatmap_chart(
        xy.heatmap(matrix, x=labels, y=labels,
                   colormap=p.diverging_ramp(mode, 5), domain=(-1.0, 1.0)),
        xy.x_axis(label=title),
        _theme(mode),
    ), out_dir, "correlation")


def projection_chart(years, median, bands, out_dir, mode="light",
                     title="Projection"):
    """Emphasis: median in the accent hue, percentile bands de-emphasised."""
    band_marks = [xy.line(years, series, color=p.DE_EMPHASIS[mode], width=2,
                          name=name) for name, series in bands.items()]
    return _write(xy.line_chart(
        *band_marks,  # drawn first so the median paints on top
        xy.line(years, median, color=p.CATEGORICAL[mode][0], width=2,
                name="median"),
        xy.legend(), xy.y_axis(label=title), xy.x_axis(label="year"),
        _theme(mode),
    ), out_dir, "projection")


def contributions_chart(years, contributed, growth, out_dir, mode="light",
                        title="Contributions vs growth"):
    """Part-to-whole over time: stacked area, 2 categorical slots."""
    colors = series_colors(2, mode)
    top = [c_ + g for c_, g in zip(contributed, growth)]
    return _write(xy.area_chart(
        xy.area(years, top, base=contributed, color=colors[1], name="growth"),
        xy.area(years, contributed, color=colors[0], name="contributed"),
        xy.legend(), xy.y_axis(label=title), xy.x_axis(label="year"),
        _theme(mode),
    ), out_dir, "contributions")
