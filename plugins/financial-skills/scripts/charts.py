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
import palette as p

MINUS = "−"  # U+2212, not a hyphen


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
