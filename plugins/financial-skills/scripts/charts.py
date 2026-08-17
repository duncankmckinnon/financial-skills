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


_SCRATCH = None


def _reset_scratch():
    """Test hook: forget the current run's scratch directory."""
    global _SCRATCH
    _SCRATCH = None


def chart_dir(date=None, keep=False):
    """Where to write charts.

    Ephemeral by default: charts are derived output, regenerable from live
    data in seconds, and they hold real position and P/L figures. Keeping
    every render forever accumulates sensitive data with no lifecycle.

    The scratch directory is stable within a run, so a batch of charts lands
    together and can be opened as a set.

    Pass keep=True to archive deliberately under the financial home.
    """
    import datetime
    if keep:
        day = date or datetime.date.today().isoformat()
        return financial_home() / "charts" / day
    global _SCRATCH
    if _SCRATCH is None:
        import tempfile
        _SCRATCH = pathlib.Path(tempfile.mkdtemp(prefix="financial-charts-"))
    return _SCRATCH


def show(path):
    """Open a rendered chart for the human. macOS, Linux and Windows.

    Reading a PNG renders it into the agent's context, not the human's -- they
    see nothing until something opens it. Prefer the .html, which carries
    tooltips, crosshair, pan and zoom.

    Returns True if a viewer was launched. False means no display is available:
    report the file path instead of implying the chart was delivered.
    """
    import webbrowser
    p = pathlib.Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(p)
    try:
        return bool(webbrowser.open(p.as_uri()))
    except Exception:
        return False


def as_of():
    """Timestamp a chart is rendered at."""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _axis_label(text):
    """Axis label carrying the as-of stamp.

    A financial chart with no date on its face is indistinguishable from a
    stale one the moment prices move -- and an ephemeral chart that someone
    saves off has no directory name to fall back on.
    """
    return f"{text}  ·  as of {as_of()}"


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

    Always includes zero -- a chart that crops its own baseline misstates the
    data. Padding is applied only on sides the data actually reaches: an
    all-positive series gets no empty negative arm, which otherwise halves the
    usable width and implies losses that are not there.
    """
    lo, hi = min(list(values) + [0.0]), max(list(values) + [0.0])
    span = (hi - lo) or 1.0
    return (lo - span * pad if lo < 0 else 0.0,
            hi + span * pad if hi > 0 else 0.0)


# A segment narrower than its own label text has nowhere to put it. Labelling
# it anyway produces overlapping text and a final label that runs off the plot
# -- observed on a real 145-position portfolio where the largest holding was
# 4.7%, then again on a theme chart where a 6.5% segment carried a 22-character
# label. Width alone is not the test: a long label needs a wide segment, so the
# threshold scales with the text.
MIN_LABEL_SHARE = 0.06
# Fraction of the value axis one character occupies at the default figure
# width. Deliberately generous -- an omitted label costs nothing (the legend
# carries it) while an overlapping one makes the chart unreadable.
CHAR_SHARE = 0.0062


def _label_fits(text, share, min_share=MIN_LABEL_SHARE):
    """Can a segment holding `share` of the axis display `text` inline?"""
    return share >= max(min_share, len(text) * CHAR_SHARE)


def _segment_label(label, value, total):
    return f"{label} {value / total * 100:.1f}%"


def _allocation_labels(folded, mode, total=None, min_share=MIN_LABEL_SHARE):
    """Direct label per segment wide enough to hold one, at its midpoint.

    Segments too narrow for their own text are left to the legend rather
    than labelled into a collision.
    """
    if total is None:
        total = sum(v for _, v in folded) or 1.0
    out, run = [], 0.0
    for label, value in folded:
        text = _segment_label(label, value, total)
        if _label_fits(text, value / total, min_share):
            out.append(xy.label(run + value / 2, 0.0, text,
                                color=p.INK[mode]["secondary"], anchor="middle"))
        run += value
    return out


def unlabelled_share(items, keep=7, min_share=MIN_LABEL_SHARE):
    """Fraction of the chart that will carry no direct label.

    Callers should present a table alongside when this is non-trivial: the
    relief rule wants identity carried by something other than hue, and for a
    flat portfolio the chart alone cannot do it.
    """
    folded = fold_tail(items, keep=keep)
    total = sum(v for _, v in folded) or 1.0
    return sum(
        v for l, v in folded
        if not _label_fits(_segment_label(l, v, total), v / total, min_share)
    ) / total


def _diverging_bar_labels(pairs, mode, unit):
    """Signed label per bar, at the bar's tip on the value axis."""
    return [xy.label(v, float(i), signed_label(v, unit),
                     color=p.INK[mode]["secondary"],
                     anchor="start" if v >= 0 else "end")
            for i, (_, v) in enumerate(pairs)]


def part_to_whole_chart(items, out_dir, mode="light", title="Share",
                        axis_label="% of total", stem="part_to_whole"):
    """Part-to-whole for any categorical data: horizontal stacked bar.

    Top 7 by value plus a folded "Other". Never a pie -- long names and more
    than ~7 classes are the normal case, and a pie handles neither.
    """
    folded = fold_tail(items, keep=7)
    colors = series_colors(len(folded), mode)
    total = sum(v for _, v in folded) or 1.0
    # Plot percentages, not raw values: the axis is labelled "% of portfolio",
    # and an axis whose label and units disagree misstates the chart.
    pct = [(label, value / total * 100.0) for label, value in folded]
    marks, base = [], 0.0
    for (label, value), color in zip(pct, colors):
        marks.append(xy.bar(
            x=[0.0], y=[value], base=base, color=color, name=label,
            orientation="horizontal", width=0.5,
            stroke=p.SURFACE[mode], stroke_width=2,  # 2px surface gap
        ))
        base += value
    return _write(xy.bar_chart(
        *marks, *_allocation_labels(pct, mode, 100.0),
        # Legend below the plot: inside the frame it covers the thin
        # right-hand segments, which are exactly the ones it has to explain.
        # xy has no out-of-frame legend placement, so make room instead: the
        # category axis is padded upward and the legend sits in the empty band
        # above the bar. Inside the frame it would cover the thin right-hand
        # segments, which are exactly the ones it has to explain.
        xy.legend(loc="upper center", ncols=4),
        xy.y_axis(tick_values=[0.0], tick_labels=[title], domain=(-0.4, 1.5)),
        xy.x_axis(label=_axis_label(axis_label), domain=(0.0, 100.0)),
        _theme(mode),
    ), out_dir, stem)


def allocation_chart(items, out_dir, mode="light", title="Allocation"):
    """Financial preset: portfolio allocation as part-to-whole."""
    return part_to_whole_chart(items, out_dir, mode=mode, title=title,
                               axis_label="% of portfolio", stem="allocation")


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
        xy.x_axis(label=_axis_label(axis_label),
                  domain=_padded_domain([v for _, v in pairs])),
        _theme(mode),
    ), out_dir, stem)


def diverging_chart(pairs, out_dir, mode="light", unit="", axis_label="change",
                    stem="diverging", sort=True):
    """Polarity for any data: diverging bar on a visible zero line.

    Positives blue, negatives red, every bar signed and directly labelled --
    polarity never rides on hue alone.
    """
    ordered = sorted(pairs, key=lambda kv: kv[1]) if sort else list(pairs)
    return _diverging_bar(ordered, out_dir, mode, stem, unit, axis_label)


def magnitude_chart(items, out_dir, mode="light", title="Magnitude", unit="",
                    stem="magnitude", keep=None):
    """Compare magnitude across arbitrary categories: horizontal bars.

    One hue -- the categories are the subject, not their identity, so this is
    a sequential job rather than a categorical one.
    """
    ordered = sorted(items, key=lambda kv: kv[1])
    if keep:
        ordered = sorted(fold_tail(ordered, keep=keep), key=lambda kv: kv[1])
    xs = [float(i) for i in range(len(ordered))]
    values = [v for _, v in ordered]
    return _write(xy.bar_chart(
        xy.bar(x=xs, y=values, color=p.CATEGORICAL[mode][0],
               orientation="horizontal", width=0.6),
        *[xy.label(v, x, f"{v:,.1f}{unit}" if unit != "$" else f"${v:,.0f}",
                   color=p.INK[mode]["secondary"])
          for x, v in zip(xs, values)],
        xy.y_axis(tick_values=xs, tick_labels=[l for l, _ in ordered]),
        xy.x_axis(label=_axis_label(title), domain=_padded_domain(values)),
        _theme(mode),
    ), out_dir, stem)


def series_chart(x, series, out_dir, mode="light", title="Value",
                 x_label="", stem="series", emphasis=None):
    """One or more series over a common x.

    A single series gets no legend -- the axis label names it. Two or more get
    a legend in fixed slot order. Pass `emphasis` to paint one series in the
    accent hue and the rest in the de-emphasis gray, which is usually the
    honest form when one line is the point and the others are context.
    """
    names = list(series)
    marks = []
    if emphasis:
        for n in names:
            if n == emphasis:
                continue
            marks.append(xy.line(x, series[n], color=p.DE_EMPHASIS[mode],
                                 width=2, name=n))
        marks.append(xy.line(x, series[emphasis],
                             color=p.CATEGORICAL[mode][0], width=2,
                             name=emphasis))
    else:
        colors = series_colors(len(names), mode)
        for n, color in zip(names, colors):
            marks.append(xy.line(x, series[n], color=color, width=2, name=n))
    chrome = [xy.y_axis(label=title), xy.x_axis(label=_axis_label(x_label))]
    if len(names) > 1:
        chrome.insert(0, xy.legend())
    return _write(xy.line_chart(*marks, *chrome, _theme(mode)), out_dir, stem)


def relationship_chart(x, y, out_dir, mode="light", x_label="x", y_label="y",
                       stem="relationship"):
    """Relationship between two measures: scatter, single hue."""
    return _write(xy.scatter_chart(
        xy.scatter(x, y, color=p.CATEGORICAL[mode][0]),
        xy.y_axis(label=y_label),
        xy.x_axis(label=_axis_label(x_label)),
        _theme(mode),
    ), out_dir, stem)


def matrix_chart(labels, matrix, out_dir, mode="light", title="Matrix",
                 diverging=False, domain=None, stem="matrix"):
    """Grid of values as a heatmap.

    diverging=True for data with a meaningful zero or midpoint (correlation,
    change vs baseline); the ramp then runs red - neutral - blue. Otherwise a
    single-hue sequential ramp, which is the safer default for magnitude.
    """
    ramp = p.diverging_ramp(mode, 5) if diverging else p.SEQUENTIAL_BLUE
    kw = {"domain": domain} if domain else {}
    return _write(xy.heatmap_chart(
        xy.heatmap(matrix, x=labels, y=labels, colormap=ramp, **kw),
        xy.x_axis(label=_axis_label(title)),
        _theme(mode),
    ), out_dir, stem)


def drift_chart(current, target, out_dir, mode="light", title="Drift vs target"):
    """Financial preset: allocation drift vs policy targets."""
    return diverging_chart(compute_drift(current, target), out_dir, mode=mode,
                           unit="%", axis_label="percentage points vs target",
                           stem="drift", sort=False)


def pl_chart(items, out_dir, mode="light", title="Unrealized P/L"):
    """Financial preset: unrealized profit and loss per position."""
    return diverging_chart(items, out_dir, mode=mode, unit="$",
                           axis_label="unrealized profit / loss", stem="pl")


def value_over_time_chart(dates, values, out_dir, mode="light",
                          title="Portfolio value"):
    """Financial preset: a single value series over time."""
    return series_chart(dates, {title: values}, out_dir, mode=mode,
                        title=title, stem="value_over_time")


def distribution_chart(values, out_dir, mode="light",
                       title="Distribution", bins=30, stem="distribution"):
    """Distribution of any numeric sample: histogram, single hue."""
    return _write(xy.histogram_chart(
        xy.hist(values, bins=bins, color=p.CATEGORICAL[mode][0]),
        xy.x_axis(label=_axis_label(title)),
        _theme(mode),
    ), out_dir, stem)


def correlation_chart(labels, matrix, out_dir, mode="light",
                      title="Correlation"):
    """Financial preset: -1..+1 correlation as a diverging matrix."""
    return matrix_chart(labels, matrix, out_dir, mode=mode, title=title,
                        diverging=True, domain=(-1.0, 1.0), stem="correlation")


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
