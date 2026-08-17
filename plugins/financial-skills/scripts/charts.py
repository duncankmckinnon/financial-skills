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
import html
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

# Charts written this run, keyed by resolved output directory:
#   {dir: [(stem, panel title, span), ...]} in render order.
# The dashboard needs titles and an order that filenames cannot supply, and
# only the renderers know them. Populated by _write().
_PANELS = {}


def _reset_scratch():
    """Test hook: forget the current run's scratch directory and its charts."""
    global _SCRATCH
    _SCRATCH = None
    _PANELS.clear()


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


def _write(chart, out_dir, stem, title=None, note=None):
    """Write <stem>.html and <stem>.png, and register the chart for the run.

    `title` is the heading the dashboard puts over this chart; `note` is the
    commentary it prints underneath -- what the shape means, which the chart
    itself cannot say.
    """
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = out_dir / f"{stem}.html"
    chart.to_html(str(doc))
    chart.to_png(str(out_dir / f"{stem}.png"))
    panels = _PANELS.setdefault(str(out_dir.resolve()), [])
    # Re-rendering a stem replaces its panel rather than duplicating it.
    panels[:] = [row for row in panels if row[0] != stem]
    panels.append((stem, title or _prettify(stem), note))
    return doc


def _prettify(stem):
    """Fallback panel heading when a caller passed no title."""
    return stem.replace("_", " ").capitalize()


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
                        axis_label="% of total", stem="part_to_whole",
                        note=None):
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
    ), out_dir, stem, title=title, note=note)


def allocation_chart(items, out_dir, mode="light", title="Allocation",
                     note=None):
    """Financial preset: portfolio allocation as part-to-whole."""
    return part_to_whole_chart(items, out_dir, mode=mode, title=title,
                               axis_label="% of portfolio", stem="allocation",
                               note=note)


def _diverging_bar(pairs, out_dir, mode, stem, unit, axis_label, title=None,
                   note=None):
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
    ), out_dir, stem, title=title, note=note)


def diverging_chart(pairs, out_dir, mode="light", unit="", axis_label="change",
                    stem="diverging", sort=True, title=None, note=None):
    """Polarity for any data: diverging bar on a visible zero line.

    Positives blue, negatives red, every bar signed and directly labelled --
    polarity never rides on hue alone.
    """
    ordered = sorted(pairs, key=lambda kv: kv[1]) if sort else list(pairs)
    return _diverging_bar(ordered, out_dir, mode, stem, unit, axis_label,
                          title, note)


def magnitude_chart(items, out_dir, mode="light", title="Magnitude", unit="",
                    stem="magnitude", keep=None, note=None):
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
    ), out_dir, stem, title=title, note=note)


def series_chart(x, series, out_dir, mode="light", title="Value",
                 x_label="", stem="series", emphasis=None, note=None):
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
    return _write(xy.line_chart(*marks, *chrome, _theme(mode)), out_dir, stem,
                  title=title, note=note)


def relationship_chart(x, y, out_dir, mode="light", x_label="x", y_label="y",
                       stem="relationship", note=None):
    """Relationship between two measures: scatter, single hue."""
    return _write(xy.scatter_chart(
        xy.scatter(x, y, color=p.CATEGORICAL[mode][0]),
        xy.y_axis(label=y_label),
        xy.x_axis(label=_axis_label(x_label)),
        _theme(mode),
    ), out_dir, stem, title=f"{y_label} vs {x_label}", note=note)


def matrix_chart(labels, matrix, out_dir, mode="light", title="Matrix",
                 diverging=False, domain=None, stem="matrix", note=None):
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
    ), out_dir, stem, title=title, note=note)


def drift_chart(current, target, out_dir, mode="light", title="Drift vs target",
                note=None):
    """Financial preset: allocation drift vs policy targets."""
    return diverging_chart(compute_drift(current, target), out_dir, mode=mode,
                           unit="%", axis_label="percentage points vs target",
                           stem="drift", sort=False, title=title, note=note)


def pl_chart(items, out_dir, mode="light", title="Unrealized P/L", note=None):
    """Financial preset: unrealized profit and loss per position."""
    return diverging_chart(items, out_dir, mode=mode, unit="$",
                           axis_label="unrealized profit / loss", stem="pl",
                           title=title, note=note)


def value_over_time_chart(dates, values, out_dir, mode="light",
                          title="Portfolio value", note=None):
    """Financial preset: a single value series over time."""
    return series_chart(dates, {title: values}, out_dir, mode=mode,
                        title=title, stem="value_over_time", note=note)


def distribution_chart(values, out_dir, mode="light",
                       title="Distribution", bins=30, stem="distribution",
                       note=None):
    """Distribution of any numeric sample: histogram, single hue."""
    return _write(xy.histogram_chart(
        xy.hist(values, bins=bins, color=p.CATEGORICAL[mode][0]),
        xy.x_axis(label=_axis_label(title)),
        _theme(mode),
    ), out_dir, stem, title=title, note=note)


def correlation_chart(labels, matrix, out_dir, mode="light",
                      title="Correlation", note=None):
    """Financial preset: -1..+1 correlation as a diverging matrix."""
    return matrix_chart(labels, matrix, out_dir, mode=mode, title=title,
                        diverging=True, domain=(-1.0, 1.0), stem="correlation",
                        note=note)


def projection_chart(years, median, bands, out_dir, mode="light",
                     title="Projection", note=None):
    """Emphasis: median in the accent hue, percentile bands de-emphasised."""
    band_marks = [xy.line(years, series, color=p.DE_EMPHASIS[mode], width=2,
                          name=name) for name, series in bands.items()]
    return _write(xy.line_chart(
        *band_marks,  # drawn first so the median paints on top
        xy.line(years, median, color=p.CATEGORICAL[mode][0], width=2,
                name="median"),
        xy.legend(), xy.y_axis(label=title), xy.x_axis(label="year"),
        _theme(mode),
    ), out_dir, "projection", title=title, note=note)


def contributions_chart(years, contributed, growth, out_dir, mode="light",
                        title="Contributions vs growth", note=None):
    """Part-to-whole over time: stacked area, 2 categorical slots."""
    colors = series_colors(2, mode)
    top = [c_ + g for c_, g in zip(contributed, growth)]
    return _write(xy.area_chart(
        xy.area(years, top, base=contributed, color=colors[1], name="growth"),
        xy.area(years, contributed, color=colors[0], name="contributed"),
        xy.legend(), xy.y_axis(label=title), xy.x_axis(label="year"),
        _theme(mode),
    ), out_dir, "contributions", title=title, note=note)


# ---------------------------------------------------------------------------
# The run dashboard. A batch of charts is one finding, not N -- opening a tab
# per chart makes the human assemble the story from separate windows.
# ---------------------------------------------------------------------------

# xy renders every chart at a fixed design size and does NOT reflow to its
# container. Both directions were checked in a browser, not assumed:
#   - a frame WIDER than this leaves a white band beside the chart, because xy
#     hardcodes body{background:#fff} whatever the theme
#   - a frame NARROWER crops the x-axis label and its as-of stamp, and adds
#     scrollbars inside every panel
# So panels are sized to the chart rather than the chart to the panel, and the
# grid refuses to make a column too narrow to hold one.
PANEL_WIDTH = 900
PANEL_HEIGHT = 420

DASHBOARD_STEM = "dashboard"
DASHBOARD = f"{DASHBOARD_STEM}.html"


def _panels(out_dir):
    """Charts to show, in render order.

    Falls back to scanning the directory: charts written by an earlier
    process leave no registry entry, and a dashboard that silently omits
    them is worse than no dashboard.
    """
    out_dir = pathlib.Path(out_dir)
    registered = _PANELS.get(str(out_dir.resolve()), [])
    # Excluding the dashboard itself: regenerating in place must not nest
    # the previous run's page inside the new one.
    present = {f.stem for f in out_dir.glob("*.html")} - {DASHBOARD_STEM}
    rows = [row for row in registered if row[0] in present]
    known = {row[0] for row in rows}
    rows += [(stem, _prettify(stem), None) for stem in sorted(present - known)]
    return rows


def _cell(stem, title, note):
    """One panel: heading, the chart itself, and what it means.

    Notes are prose written at runtime, so they are escaped -- an ampersand
    or a stray angle bracket in a note must stay literal text.
    """
    caption = html.escape(title)
    body = (f'    <figure class="panel">\n'
            f'      <figcaption>{caption}'
            f'<a href="{stem}.html" target="_blank">open</a></figcaption>\n'
            f'      <iframe src="{stem}.html" title="{caption}" '
            f'loading="lazy"></iframe>\n')
    if note:
        body += f'      <p class="note">{html.escape(note)}</p>\n'
    return body + "    </figure>"


def dashboard(out_dir=None, title="Charts", mode="light"):
    """Write one page laying every chart of the run out in a grid.

    Each chart is embedded as an iframe of the standalone HTML it already
    wrote, so tooltips, crosshair, pan and zoom all still work, and each panel
    links out to the chart on its own for a closer look.

    Returns the path of the written page. Raises if there is nothing to show.
    """
    out_dir = pathlib.Path(out_dir if out_dir is not None else chart_dir())
    rows = _panels(out_dir)
    if not rows:
        raise ValueError(
            f"no charts in {out_dir} to build a dashboard from -- render some "
            "first, passing the same out_dir")
    surface, ink = p.SURFACE[mode], p.INK[mode]
    cells = "\n".join(_cell(stem, t, note) for stem, t, note in rows)
    doc = out_dir / DASHBOARD
    doc.write_text(f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: {mode}; }}
  body {{ margin: 0; padding: 24px; background: {surface}; color: {ink["primary"]};
         font-family: system-ui, sans-serif; }}
  header {{ margin: 0 0 20px; }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0; }}
  .stamp {{ font-size: 13px; color: {ink["muted"]}; margin-top: 4px; }}
  .grid {{ display: grid; gap: 20px; justify-content: center;
           grid-template-columns: repeat(auto-fit, minmax({PANEL_WIDTH}px, 1fr)); }}
  .panel {{ margin: 0; border: 1px solid {ink["grid"]}; border-radius: 8px;
            overflow: hidden; background: {surface}; }}
  figcaption {{ display: flex; justify-content: space-between; align-items: baseline;
                gap: 12px; padding: 10px 14px; font-size: 14px; font-weight: 600;
                border-bottom: 1px solid {ink["grid"]}; color: {ink["primary"]}; }}
  figcaption a {{ font-size: 12px; font-weight: 400; color: {ink["muted"]}; }}
  /* Centred at the chart's own size: stretching it bands the panel white,
     shrinking it crops the axis. See PANEL_WIDTH. */
  iframe {{ display: block; margin: 0 auto; border: 0;
            width: {PANEL_WIDTH}px; height: {PANEL_HEIGHT}px; }}
  /* pre-line: a note is written as one or two short lines, and collapsing
     them into a paragraph loses the author's breaks. */
  .note {{ margin: 0 auto; padding: 12px 16px 14px; max-width: {PANEL_WIDTH}px;
           border-top: 1px solid {ink["grid"]}; white-space: pre-line;
           font-size: 13px; line-height: 1.5; color: {ink["secondary"]}; }}
</style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="stamp">as of {as_of()} &middot; {len(rows)} charts</div>
  </header>
  <div class="grid">
{cells}
  </div>
</body>
</html>
""")
    return doc


def show_all(out_dir=None, title="Charts", mode="light"):
    """Build the run dashboard and open it -- one tab for the whole batch.

    Same contract as show(): False means no viewer could be launched, so
    report the path rather than implying the charts were delivered.
    """
    return show(dashboard(out_dir, title=title, mode=mode))
