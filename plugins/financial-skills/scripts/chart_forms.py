"""Form renderers: one per chart form, built on `xy`.

Run via: uv run --with 'xy==0.0.6' python ...

`build()` turns a validated chart dict and its rows into an `xy` chart at the
pixel size its page block declares. It writes nothing; the caller exports.

Rendering rules this module enforces so a spec cannot get them wrong:
  - gains blue / losses red, never green/red
  - every polarity mark carries an explicit sign and a direct value label
  - diverging charts anchor to a visible zero line
  - one y-axis, never two
  - categorical hues in fixed slot order; long tails fold into "Other"
  - part-to-whole is a stacked bar, never a pie
  - every chart carries an as-of stamp

See references/chart-recipes.md for the verified xy 0.0.6 call behind each
form, including the orientation="horizontal" axis-role trap.
"""
import collections
import datetime
import pathlib
import sys

import xy

# Self-locating: find assets/palette.py relative to this file rather than
# making every caller configure sys.path.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "assets"))

import palette as p  # noqa: E402  (import follows the path fix above)
import chart_spec  # noqa: E402

MINUS = "−"  # U+2212, not a hyphen

# xy renders at any pixel size but does NOT reflow afterwards, so a chart is
# built at the size of the block it will sit in. Three widths tile a 1200px
# page with 20px gutters: 590*2+20 and 386*3+40.
WIDTH_PX = {"full": 1200, "half": 590, "third": 386}
HEIGHT_PX = {"short": 260, "regular": 420, "tall": 640}

Built = collections.namedtuple("Built", "chart warnings")

_PRESET = {
    "allocation": {"title": "Allocation", "axis": "% of portfolio"},
    "drift": {"title": "Drift vs target", "axis": "percentage points vs target",
              "unit": "%"},
    "pl": {"title": "Unrealized P/L", "axis": "unrealized profit / loss",
           "unit": "$"},
    "value_over_time": {"title": "Portfolio value"},
    "correlation": {"title": "Correlation", "diverging": True,
                    "domain": (-1.0, 1.0)},
    "projection": {"title": "Projection", "x_label": "year"},
    "contributions": {"title": "Contributions vs growth", "x_label": "year"},
}


def _preset(chart):
    return _PRESET.get(chart.get("preset"), {})


def title_of(chart):
    """The chart's heading: its own title, else its preset's, else its id."""
    if chart.get("title"):
        return chart["title"]
    if "title" in _preset(chart):
        return _preset(chart)["title"]
    return chart["id"].replace("_", " ").replace("-", " ").capitalize()


def as_of():
    """Timestamp a chart is rendered at."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# In the interactive page xy wraps an axis label that is wider than the plot,
# and the wrapped line falls outside the frame -- which silently cut the time
# off the as-of stamp at 'third' width. Seen in a browser render, not in the
# PNG export, which does not wrap. ~9.5px a character against the plot width.
AXIS_CHAR_PX = 9.5
AXIS_MARGIN_PX = 90


def _axis_label(text, width_px=None):
    """Axis label carrying the as-of stamp.

    A financial chart with no date on its face is indistinguishable from a
    stale one the moment prices move -- and a chart someone saves off has no
    page header to fall back on. When the label would not fit the width it is
    drawn at, the descriptive text is dropped and the stamp kept: the panel
    heading still names the chart, and nothing else carries the date.
    """
    stamp = f"as of {as_of()}"
    full = f"{text}  ·  {stamp}" if text else stamp
    if width_px is not None and len(full) * AXIS_CHAR_PX > width_px - AXIS_MARGIN_PX:
        return stamp
    return full


# ---------------------------------------------------------------------------
# Shaping helpers
# ---------------------------------------------------------------------------

def fold_tail(items, keep=7):
    """Top `keep` by value descending; everything else summed into 'Other'.

    Never generates additional hues for a long tail -- the tail folds.
    """
    ordered = sorted(items, key=lambda kv: kv[1], reverse=True)
    if len(ordered) <= keep:
        return ordered
    head, tail = ordered[:keep], ordered[keep:]
    return head + [("Other", sum(v for _, v in tail))]


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


def _value_label(value, unit=""):
    return f"${value:,.0f}" if unit == "$" else f"{value:,.1f}{unit}"


def _pairs(chart, rows):
    return [(str(r[chart["label"]]), float(r[chart["value"]])) for r in rows]


def _theme(mode):
    return xy.theme(
        background=p.SURFACE[mode], plot_background=p.SURFACE[mode],
        grid_color=p.INK[mode]["grid"], axis_color=p.INK[mode]["baseline"],
        text_color=p.INK[mode]["primary"],
    )


def _size(width, height):
    return {"width": WIDTH_PX[width], "height": HEIGHT_PX[height]}


# Annotations are SCREEN-oriented (x = value axis, y = category axis) even
# though bar marks with orientation="horizontal" are transposed. Getting this
# backwards places labels off-plot: they still appear in the output source but
# vanish from the render. These builders are extracted so the coordinates can
# be asserted directly -- grepping the output cannot catch the bug.

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
# threshold scales with the text -- and with the width the chart is drawn at.
MIN_LABEL_SHARE = 0.06
# Label text is a fixed pixel size whatever the chart's width, so the share of
# the axis one character takes grows as the chart narrows. Measured off
# renders at 386, 590 and 1200px: ~7.5px a character, with ~80px of the width
# going to the category tick label and padding rather than the plot.
# Deliberately generous -- an omitted label costs nothing (the legend carries
# it) while an overlapping one makes the chart unreadable.
CHAR_PX = 7.5
PLOT_MARGIN_PX = 80
REF_WIDTH_PX = 900


def _label_fits(text, share, min_share=MIN_LABEL_SHARE, width_px=REF_WIDTH_PX):
    """Can a segment holding `share` of the axis display `text` inline?"""
    plot_px = max(1, width_px - PLOT_MARGIN_PX)
    return share >= max(min_share, len(text) * CHAR_PX / plot_px)


def _segment_label(label, value, total):
    return f"{label} {value / total * 100:.1f}%"


def _allocation_labels(folded, mode, total=None, min_share=MIN_LABEL_SHARE,
                       width_px=REF_WIDTH_PX):
    """Direct label per segment wide enough to hold one, at its midpoint.

    Segments too narrow for their own text are left to the legend rather
    than labelled into a collision.
    """
    if total is None:
        total = sum(v for _, v in folded) or 1.0
    out, run = [], 0.0
    for label, value in folded:
        text = _segment_label(label, value, total)
        if _label_fits(text, value / total, min_share, width_px):
            out.append(xy.label(run + value / 2, 0.0, text,
                                color=p.INK[mode]["secondary"], anchor="middle"))
        run += value
    return out


def unlabelled_share(items, keep=7, min_share=MIN_LABEL_SHARE,
                     width_px=REF_WIDTH_PX):
    """Fraction of a part-to-whole chart that will carry no direct label.

    When this is non-trivial a table belongs alongside: the relief rule wants
    identity carried by something other than hue, and for a flat portfolio the
    chart alone cannot do it.
    """
    folded = fold_tail(items, keep=keep)
    total = sum(v for _, v in folded) or 1.0
    return sum(
        v for l, v in folded
        if not _label_fits(_segment_label(l, v, total), v / total, min_share,
                           width_px)
    ) / total


def _diverging_bar_labels(pairs, mode, unit):
    """Signed label per bar, at the bar's tip on the value axis."""
    # dx follows the sign: xy's default nudges every label rightwards, which
    # pushes a negative bar's label back over the bar it belongs to.
    return [xy.label(v, float(i), signed_label(v, unit),
                     color=p.INK[mode]["secondary"],
                     anchor="start" if v >= 0 else "end",
                     dx=6.0 if v >= 0 else -6.0)
            for i, (_, v) in enumerate(pairs)]


def _bar_capacity(height):
    """How many horizontal bars stay readable at this height."""
    return max(4, (HEIGHT_PX[height] - 80) // 22)


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

def _part_to_whole(chart, rows, width, height, mode, domain, warnings):
    """Horizontal stacked bar. Top 7 by value plus a folded "Other".

    Never a pie -- long names and more than ~7 classes are the normal case,
    and a pie handles neither.
    """
    items = _pairs(chart, rows)
    folded = fold_tail(items, keep=7)
    if len(items) > 7:
        warnings.append(f"{title_of(chart)}: folded {len(items) - 7} into Other")
    width_px = WIDTH_PX[width]
    share = unlabelled_share(items, width_px=width_px)
    other = dict(folded).get("Other", 0.0) / (sum(v for _, v in folded) or 1.0)
    if len(items) > 7 and other > 0.5:
        # A flat book: "Other" is labelled, but it hides nearly everything.
        warnings.append(
            f"{title_of(chart)}: 'Other' is {other * 100:.0f}% of the bar, so most "
            "items carry no direct label -- group into classes first, or show "
            "the figures in a table alongside")
    elif share > 0.25:
        warnings.append(
            f"{title_of(chart)}: {share * 100:.0f}% of the bar will carry no direct "
            "label at this size -- show the figures in a table alongside")
    colors = series_colors(len(folded), mode)
    total = sum(v for _, v in folded) or 1.0
    # Plot percentages, not raw values: the axis is labelled in percent, and
    # an axis whose label and units disagree misstates the chart.
    pct = [(label, value / total * 100.0) for label, value in folded]
    marks, base = [], 0.0
    for (label, value), color in zip(pct, colors):
        marks.append(xy.bar(
            x=[0.0], y=[value], base=base, color=color, name=label,
            orientation="horizontal", width=0.5,
            stroke=p.SURFACE[mode], stroke_width=2,  # 2px surface gap
        ))
        base += value
    title = title_of(chart)
    return xy.bar_chart(
        *marks, *_allocation_labels(pct, mode, 100.0, width_px=width_px),
        # xy has no out-of-frame legend placement, so make room instead: the
        # category axis is padded upward and the legend sits in the empty band
        # above the bar. Inside the frame it would cover the thin right-hand
        # segments, which are exactly the ones it has to explain.
        xy.legend(loc="upper center", ncols=4 if width == "full" else 3),
        # A long title as the lone category tick is clipped at the left edge;
        # the panel heading already carries it.
        xy.y_axis(tick_values=[0.0], tick_labels=[title if len(title) <= 12 else ""],
                  domain=(-0.4, 1.5)),
        xy.x_axis(label=_axis_label(_preset(chart).get("axis", "% of total"),
                                    WIDTH_PX[width]),
                  domain=(0.0, 100.0)),
        _theme(mode), **_size(width, height),
    )


def _diverging_order(chart, rows):
    pairs = _pairs(chart, rows)
    return sorted(pairs, key=lambda kv: kv[1]) if chart.get("sort", True) else pairs


def _diverging(chart, rows, width, height, mode, domain, warnings):
    """Polarity on a visible zero line. Positives blue, negatives red, every
    bar signed and directly labelled -- polarity never rides on hue alone."""
    pairs = _diverging_order(chart, rows)
    if len(pairs) > _bar_capacity(height):
        warnings.append(
            f"{title_of(chart)}: {len(pairs)} bars are cramped at height "
            f"'{height}' -- use a taller block or a top step")
    unit = chart.get("unit", _preset(chart).get("unit", ""))
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
    return xy.bar_chart(
        *marks, *_diverging_bar_labels(pairs, mode, unit),
        xy.vline(0, color=p.INK[mode]["baseline"], width=2),  # visible zero
        xy.y_axis(tick_values=xs, tick_labels=[l for l, _ in pairs]),
        xy.x_axis(label=_axis_label(_preset(chart).get("axis", title_of(chart)),
                                    WIDTH_PX[width]),
                  domain=domain or _padded_domain([v for _, v in pairs])),
        _theme(mode), **_size(width, height),
    )


def _magnitude(chart, rows, width, height, mode, domain, warnings):
    """Magnitude across categories: horizontal bars, one hue -- the categories
    are the subject, not their identity."""
    items = _pairs(chart, rows)
    capacity = _bar_capacity(height)
    if len(items) > capacity:
        warnings.append(f"{title_of(chart)}: folded {len(items) - (capacity - 1)} "
                        f"into Other to fit height '{height}'")
        items = fold_tail(items, keep=capacity - 1)
    ordered = sorted(items, key=lambda kv: kv[1])
    unit = chart.get("unit", "")
    xs = [float(i) for i in range(len(ordered))]
    values = [v for _, v in ordered]
    return xy.bar_chart(
        xy.bar(x=xs, y=values, color=p.CATEGORICAL[mode][0],
               orientation="horizontal", width=0.6),
        *[xy.label(v, x, _value_label(v, unit), color=p.INK[mode]["secondary"])
          for x, v in zip(xs, values)],
        xy.y_axis(tick_values=xs, tick_labels=[l for l, _ in ordered]),
        xy.x_axis(label=_axis_label(title_of(chart), WIDTH_PX[width]),
                  domain=domain or _padded_domain(values)),
        _theme(mode), **_size(width, height),
    )


def _series_data(chart, rows):
    """{name: (x values, y values)} in drawing order."""
    if "y" in chart:
        xs = [r[chart["x"]] for r in rows]
        return {name: (xs, [float(r[name]) for r in rows]) for name in chart["y"]}
    out = {}
    for row in rows:
        xs, ys = out.setdefault(str(row[chart["series"]]), ([], []))
        xs.append(row[chart["x"]])
        ys.append(float(row[chart["value"]]))
    return out


def _series(chart, rows, width, height, mode, domain, warnings):
    """One or more series over a common x.

    A single series gets no legend -- the axis label names it. `emphasis`
    paints one series in the accent hue and the rest in the de-emphasis gray,
    the honest form when one line is the point and the others are context.
    """
    data = _series_data(chart, rows)
    names = list(data)
    emphasis = chart.get("emphasis")
    marks = []
    band = chart.get("band")
    if band:  # drawn first, so every line paints over it
        marks.append(xy.error_band(
            [r[chart["x"]] for r in rows],
            [float(r[band["lower"]]) for r in rows],
            [float(r[band["upper"]]) for r in rows],
            color=p.DE_EMPHASIS[mode], opacity=0.35))
    if emphasis:
        for n in names:
            if n != emphasis:
                marks.append(xy.line(*data[n], color=p.DE_EMPHASIS[mode],
                                     width=2, name=n))
        marks.append(xy.line(*data[emphasis], color=p.CATEGORICAL[mode][0],
                             width=2, name=emphasis))
    else:
        for n, color in zip(names, series_colors(len(names), mode)):
            marks.append(xy.line(*data[n], color=color, width=2, name=n))
    for line in chart.get("reference_lines", []):
        marks.append(xy.hline(line["y"], text=line.get("label"),
                              color=p.INK[mode]["muted"], width=1.5))
    y_kw = {"domain": domain} if domain else {}
    chrome = [xy.y_axis(label=title_of(chart), **y_kw),
              xy.x_axis(label=_axis_label(_preset(chart).get("x_label", ""),
                                          WIDTH_PX[width]))]
    if len(names) > 1:
        chrome.insert(0, xy.legend())
    return xy.line_chart(*marks, *chrome, _theme(mode), **_size(width, height))


def _stacked_area(chart, rows, width, height, mode, domain, warnings):
    """Part-to-whole over time: layers stacked in the order the spec lists."""
    xs = [r[chart["x"]] for r in rows]
    names = chart["y"]
    colors = series_colors(len(names), mode)
    base = [0.0] * len(rows)
    layers = []
    for name, color in zip(names, colors):
        top = [b + float(r[name]) for b, r in zip(base, rows)]
        layers.append(xy.area(xs, top, base=list(base), color=color, name=name))
        base = top
    return xy.area_chart(
        *reversed(layers),  # upper layers first so lower ones are not covered
        xy.legend(), xy.y_axis(label=title_of(chart)),
        xy.x_axis(label=_axis_label(_preset(chart).get("x_label", ""),
                                    WIDTH_PX[width])),
        _theme(mode), **_size(width, height),
    )


def _distribution(chart, rows, width, height, mode, domain, warnings):
    """Shape of a numeric sample: histogram, single hue."""
    return xy.histogram_chart(
        xy.hist([float(r[chart["value"]]) for r in rows], bins=30,
                color=p.CATEGORICAL[mode][0]),
        xy.x_axis(label=_axis_label(title_of(chart), WIDTH_PX[width])),
        _theme(mode), **_size(width, height),
    )


def _relationship(chart, rows, width, height, mode, domain, warnings):
    """How two measures relate: scatter, single hue."""
    return xy.scatter_chart(
        xy.scatter([float(r[chart["x"]]) for r in rows],
                   [float(r[chart["y"]]) for r in rows],
                   color=p.CATEGORICAL[mode][0]),
        xy.y_axis(label=chart["y"]),
        xy.x_axis(label=_axis_label(chart["x"], WIDTH_PX[width])),
        _theme(mode), **_size(width, height),
    )


def _matrix_grid(chart, rows):
    """(row labels, column labels, z) in first-seen order; missing cells NaN."""
    ys, xs = [], []
    for r in rows:
        if str(r[chart["row"]]) not in ys:
            ys.append(str(r[chart["row"]]))
        if str(r[chart["column"]]) not in xs:
            xs.append(str(r[chart["column"]]))
    z = [[float("nan")] * len(xs) for _ in ys]
    for r in rows:
        z[ys.index(str(r[chart["row"]]))][xs.index(str(r[chart["column"]]))] = \
            float(r[chart["value"]])
    return ys, xs, z


def _matrix_options(chart):
    """(diverging, domain) from the chart, falling back to its preset."""
    diverging = chart.get("diverging", _preset(chart).get("diverging", False))
    domain = chart.get("domain", _preset(chart).get("domain"))
    return diverging, tuple(domain) if domain else None


def _matrix(chart, rows, width, height, mode, domain, warnings):
    """Grid of values as a heatmap.

    A diverging ramp only where the data has a meaningful zero or midpoint;
    otherwise a single-hue sequential ramp, the safer default for magnitude.
    """
    ys, xs, z = _matrix_grid(chart, rows)
    diverging, dom = _matrix_options(chart)
    ramp = p.diverging_ramp(mode, 5) if diverging else p.SEQUENTIAL_BLUE
    kw = {"domain": dom} if dom else {}
    return xy.heatmap_chart(
        xy.heatmap(z, x=xs, y=ys, colormap=ramp, **kw),
        xy.x_axis(label=_axis_label(title_of(chart), WIDTH_PX[width])),
        _theme(mode), **_size(width, height),
    )


_FORMS = {
    "part_to_whole": _part_to_whole, "magnitude": _magnitude,
    "diverging": _diverging, "series": _series, "stacked_area": _stacked_area,
    "distribution": _distribution, "relationship": _relationship,
    "matrix": _matrix,
}


def build(chart, rows, width, height, mode, domain=None):
    """Build one chart at the size of the block it will sit in.

    `domain` overrides the value axis; small multiples pass the shared one.
    Returns Built(chart, warnings) and writes nothing.
    """
    warnings = []
    made = _FORMS[chart["form"]](chart, rows, width, height, mode, domain, warnings)
    return Built(made, warnings)


# ---------------------------------------------------------------------------
# Small multiples
# ---------------------------------------------------------------------------

def facet_cell_width(chart):
    """The width each small multiple is drawn at."""
    return chart_spec.MIN_WIDTH[chart["form"]]


def shared_domain(chart, rows):
    """One value-axis domain for every panel of a faceted chart, or None.

    Without it each panel scales to its own data and a small account looks
    as large as a big one -- the comparison the multiples exist to make.
    """
    form = chart["form"]
    if form in ("magnitude", "diverging"):
        return _padded_domain([float(r[chart["value"]]) for r in rows])
    if form == "series":
        values = [y for _, ys in _series_data(chart, rows).values() for y in ys]
        band = chart.get("band")
        if band:
            values += [float(r[band[k]]) for r in rows for k in ("lower", "upper")]
        values += [line["y"] for line in chart.get("reference_lines", [])]
        lo, hi = min(values), max(values)
        pad = (hi - lo or 1.0) * 0.06
        return (lo - pad, hi + pad)
    return None


def build_facets(chart, rows, height, mode):
    """[(facet value, Built)] in first-seen order, on a shared value axis."""
    groups = {}
    for row in rows:
        groups.setdefault(str(row[chart["facet"]]), []).append(row)
    domain = shared_domain(chart, rows)
    width = facet_cell_width(chart)
    out = []
    for name, members in groups.items():
        cell = dict(chart, title=name)
        out.append((name, build(cell, members, width, height, mode, domain)))
    return out
