"""Declarative data steps for chart specs.

A chart names a table and a list of steps; this module applies them. It is the
shaping an agent used to write by hand in a throwaway script -- grouping,
shares, differences, ordering -- reduced to a fixed vocabulary so a spec can
take raw rows straight from a data source.

Deliberately small and closed: six steps, no expressions, no eval. Pure
standard library with no charting import, so it tests without `xy`.
"""
import math

STEPS = ("filter", "group", "share", "diff", "sort", "top")

_KEYS = {
    "filter": {"field", "equals", "in"},
    "group": {"by", "sum", "mean", "count"},
    "share": {"of", "as"},
    "diff": {"a", "b", "as"},
    "sort": {"by", "desc"},
    "top": {"n", "by"},
}
_AGGREGATES = ("sum", "mean", "count")


class StepError(ValueError):
    """A step that cannot be applied. `index` is its position in the list."""

    def __init__(self, index, message):
        super().__init__(f"step {index}: {message}")
        self.index = index
        self.message = message


def is_number(value):
    """A finite int or float. A bool is not a number here."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _need(args, key, kind):
    if key not in args:
        raise ValueError(f"needs '{key}'")
    if not isinstance(args[key], kind):
        raise ValueError(f"'{key}' has the wrong type")
    return args[key]


def _column(rows, field, numeric=False):
    out = []
    for i, row in enumerate(rows):
        if field not in row:
            raise ValueError(f"row {i} has no field '{field}'")
        if numeric and not is_number(row[field]):
            raise ValueError(f"row {i}: '{field}' is not a finite number")
        out.append(row[field])
    return out


def _filter(rows, args):
    field = _need(args, "field", str)
    if ("equals" in args) == ("in" in args):
        raise ValueError("needs exactly one of 'equals' or 'in'")
    _column(rows, field)
    if "in" in args:
        wanted = _need(args, "in", list)
        return [r for r in rows if r[field] in wanted]
    return [r for r in rows if r[field] == args["equals"]]


def _group(rows, args):
    by = args.get("by")
    by = [by] if isinstance(by, str) else by
    if not isinstance(by, list) or not by or not all(isinstance(b, str) for b in by):
        raise ValueError("'by' must be a field name or a list of them")
    chosen = [a for a in _AGGREGATES if a in args]
    if not chosen:
        raise ValueError("needs at least one of 'sum', 'mean' or 'count'")
    plan = []
    for agg in chosen:
        for field in _need(args, agg, list):
            if not isinstance(field, str):
                raise ValueError(f"'{agg}' must list field names")
            plan.append((agg, field))
    for field in by:
        _column(rows, field)
    for agg, field in plan:
        _column(rows, field, numeric=agg != "count")

    groups = {}  # insertion-ordered: groups appear in first-seen order
    for row in rows:
        groups.setdefault(tuple(row[b] for b in by), []).append(row)
    out = []
    for key, members in groups.items():
        new = dict(zip(by, key))
        for agg, field in plan:
            if agg == "count":
                new[field] = len(members)
            else:
                total = sum(m[field] for m in members)
                new[field] = total if agg == "sum" else total / len(members)
        out.append(new)
    return out


def _share(rows, args):
    of, name = _need(args, "of", str), _need(args, "as", str)
    total = sum(_column(rows, of, numeric=True))
    if total == 0:
        raise ValueError(f"'{of}' totals zero, so a share of it is undefined")
    return [dict(r, **{name: r[of] / total * 100.0}) for r in rows]


def _diff(rows, args):
    a, b, name = _need(args, "a", str), _need(args, "b", str), _need(args, "as", str)
    _column(rows, a, numeric=True)
    _column(rows, b, numeric=True)
    return [dict(r, **{name: r[a] - r[b]}) for r in rows]


def _sort(rows, args):
    by = _need(args, "by", str)
    desc = args.get("desc", False)
    if not isinstance(desc, bool):
        raise ValueError("'desc' must be true or false")
    values = _column(rows, by)
    try:
        return sorted(rows, key=lambda r: r[by], reverse=desc)
    except TypeError:
        kinds = sorted({type(v).__name__ for v in values})
        raise ValueError(f"'{by}' mixes types that cannot be ordered: {kinds}")


def _top(rows, args):
    n, by = _need(args, "n", int), _need(args, "by", str)
    if isinstance(n, bool) or n < 1:
        raise ValueError("'n' must be a whole number of at least 1")
    _column(rows, by, numeric=True)
    return sorted(rows, key=lambda r: r[by], reverse=True)[:n]


_APPLY = {"filter": _filter, "group": _group, "share": _share,
          "diff": _diff, "sort": _sort, "top": _top}


def apply_steps(rows, steps):
    """Apply `steps` in order and return new rows. Never mutates its input."""
    out = [dict(r) for r in rows]
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or len(step) != 1:
            raise StepError(index, "a step is an object with exactly one key, "
                                   f"one of: {', '.join(STEPS)}")
        (name, args), = step.items()
        if name not in _APPLY:
            raise StepError(index, f"unknown step '{name}'; "
                                   f"expected one of: {', '.join(STEPS)}")
        if not isinstance(args, dict):
            raise StepError(index, f"'{name}' takes an object")
        unknown = sorted(set(args) - _KEYS[name])
        if unknown:
            raise StepError(index, f"'{name}' does not take: {', '.join(unknown)}")
        try:
            out = _APPLY[name](out, args)
        except ValueError as exc:
            raise StepError(index, f"{name}: {exc}") from None
    return out
