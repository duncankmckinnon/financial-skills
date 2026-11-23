"""Load and validate a chart spec.

A spec is a JSON object describing a run of charts and the page they sit on.
Validation reports every problem at once, each with its location in the spec,
and runs each chart's data steps so that fields and values are checked against
the rows that will actually be drawn. Nothing renders unless this passes.

Unknown keys are errors everywhere: a typo must not silently drop a field.

Pure standard library with no charting import, so it tests without `xy`.
"""
import collections
import json
import pathlib
import re

import chart_data
from chart_data import is_number

Problem = collections.namedtuple("Problem", "path message")

FORMS = ("part_to_whole", "magnitude", "diverging", "series", "stacked_area",
         "distribution", "relationship", "matrix")

# A preset sets labels and units for a financial case, and nothing else.
PRESETS = {
    "allocation": "part_to_whole",
    "drift": "diverging",
    "pl": "diverging",
    "value_over_time": "series",
    "correlation": "matrix",
    "projection": "series",
    "contributions": "stacked_area",
}

WIDTHS = ("full", "half", "third")      # widest first
HEIGHTS = ("short", "regular", "tall")
DEFAULT_WIDTH, DEFAULT_HEIGHT = "full", "regular"
MAX_FACETS = 12
MAX_SERIES = 8  # the categorical palette has eight slots and is never cycled

# Required field keys per form. `series` is checked separately: it takes a
# wide form (y: [fields]) or a long form (series + value).
FIELDS = {
    "part_to_whole": ("label", "value"),
    "magnitude": ("label", "value"),
    "diverging": ("label", "value"),
    "series": ("x",),
    "stacked_area": ("x", "y"),
    "distribution": ("value",),
    "relationship": ("x", "y"),
    "matrix": ("row", "column", "value"),
}
OPTIONS = {
    "part_to_whole": (),
    "magnitude": ("unit",),
    "diverging": ("unit", "sort"),
    "series": ("y", "series", "value", "emphasis", "reference_lines", "band"),
    "stacked_area": (),
    "distribution": (),
    "relationship": (),
    "matrix": ("diverging", "domain"),
}
# The narrowest block each form stays readable in. Narrower is a validation
# error rather than an unreadable chart. A faceted chart always needs `full`.
MIN_WIDTH = {form: "third" for form in FORMS}
MIN_WIDTH.update(part_to_whole="half", matrix="half")

# Forms whose marks are named by a label, so two rows with one label would
# draw two marks the reader cannot tell apart.
_UNIQUE_LABEL = ("part_to_whole", "magnitude", "diverging")

_TOP = {"title", "mode", "sources", "data", "charts", "page"}
_CHART_COMMON = {"id", "form", "preset", "title", "note", "from", "steps", "facet"}
_SOURCE = {"name", "as_of", "live"}
_SECTION = {"section", "text", "blocks"}
_BLOCK_KINDS = ("chart", "stat", "table", "text")
_STAT = {"label", "value", "unit", "change", "change_unit"}
_TABLE_BLOCK = {"from", "steps", "columns", "title"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class SpecError(ValueError):
    """A spec that could not be read at all. Carries one Problem."""

    def __init__(self, problem):
        super().__init__(problem.message)
        self.problem = problem


def load(path):
    """Read a spec file. Raises SpecError if it is unreadable or not JSON."""
    path = pathlib.Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SpecError(Problem("", f"cannot read {path}: {exc.strerror or exc}"))
    except ValueError as exc:
        raise SpecError(Problem("", f"{path} is not valid JSON: {exc}"))


def wider_or_equal(width, minimum):
    return WIDTHS.index(width) <= WIDTHS.index(minimum)


def min_width(chart):
    """The narrowest block this chart may be placed in."""
    if chart.get("facet"):
        return "full"
    return MIN_WIDTH.get(chart.get("form"), "third")


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _read_table(name, table, base_dir, add):
    """Rows of one named table, or None after reporting why not."""
    path = f"data.{name}"
    if not isinstance(table, dict):
        add(path, "a table is an object with 'rows' or 'file'")
        return None
    unknown = sorted(set(table) - {"rows", "file"})
    if unknown:
        add(path, f"unknown key(s): {', '.join(unknown)}")
        return None
    if ("rows" in table) == ("file" in table):
        add(path, "needs exactly one of 'rows' or 'file'")
        return None
    if "file" in table:
        if not isinstance(table["file"], str):
            add(f"{path}.file", "must be a path, relative to the spec")
            return None
        target = pathlib.Path(base_dir) / table["file"]
        try:
            rows = json.loads(target.read_text(encoding="utf-8"))
        except OSError as exc:
            add(f"{path}.file", f"cannot read {target}: {exc.strerror or exc}")
            return None
        except ValueError as exc:
            add(f"{path}.file", f"{target} is not valid JSON: {exc}")
            return None
        where = f"{path}.file"
    else:
        rows, where = table["rows"], f"{path}.rows"
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        add(where, "must be a list of objects, one per row")
        return None
    return rows


def _tables(spec, base_dir, add):
    data = spec.get("data", {})
    if not isinstance(data, dict):
        add("data", "must be an object of named tables")
        return {}
    out = {}
    for name, table in data.items():
        out[name] = _read_table(name, table, base_dir, add)
    return out


def tables(spec, base_dir):
    """The spec's named tables with files read. Assumes a validated spec."""
    return _tables(spec, base_dir, lambda *_: None)


def chart_rows(spec, chart, base_dir):
    """A chart's (or table block's) rows after its steps. Validated spec only."""
    rows = tables(spec, base_dir)[chart["from"]]
    return chart_data.apply_steps(rows, chart.get("steps", []))


# ---------------------------------------------------------------------------
# Row checks
# ---------------------------------------------------------------------------

def _has_field(rows, field, path, add):
    """Report and return False unless every row carries `field`, non-null."""
    if not isinstance(field, str):
        add(path, "must be a field name")
        return False
    if not any(field in r for r in rows):
        available = sorted({k for r in rows for k in r})
        add(path, f"no field '{field}' in the rows after the steps; "
                  f"available: {', '.join(available) or 'none'}")
        return False
    bad = [i for i, r in enumerate(rows) if r.get(field) is None]
    if bad:
        add(path, f"row {bad[0]}: '{field}' is missing or null"
                  + (f" (and {len(bad) - 1} more rows)" if len(bad) > 1 else ""))
        return False
    return True


def _numeric(rows, field, path, add):
    """As _has_field, and every value must be a finite number."""
    if not isinstance(field, str):
        add(path, "must be a field name")
        return False
    if not any(field in r for r in rows):
        return _has_field(rows, field, path, add)
    bad = [i for i, r in enumerate(rows) if not is_number(r.get(field))]
    if bad:
        add(path, f"row {bad[0]}: '{field}' is missing or not a finite number"
                  + (f" (and {len(bad) - 1} more rows)" if len(bad) > 1 else ""))
        return False
    return True


def _facets(chart, rows):
    """Rows split by the facet field, or one unnamed group."""
    field = chart.get("facet")
    if not field:
        return {None: rows}
    out = {}
    for row in rows:
        out.setdefault(row.get(field), []).append(row)
    return out


def _check_rows(chart, rows, path, add):
    form = chart["form"]
    groups = _facets(chart, rows)

    def unique(fields, at, what):
        for name, members in groups.items():
            seen = set()
            for row in members:
                key = tuple(str(row[f]) for f in fields)
                if key in seen:
                    where = f" in facet '{name}'" if name is not None else ""
                    add(at, f"{what} '{' / '.join(key)}' appears more than once"
                            f"{where}; add a group step so each appears once")
                    return
                seen.add(key)

    if form in _UNIQUE_LABEL:
        ok_label = _has_field(rows, chart["label"], f"{path}.label", add)
        ok_value = _numeric(rows, chart["value"], f"{path}.value", add)
        if ok_label:
            unique([chart["label"]], f"{path}.label", "label")
        if ok_value and form == "part_to_whole":
            for name, members in groups.items():
                values = [r[chart["value"]] for r in members]
                where = f" in facet '{name}'" if name is not None else ""
                if min(values) < 0:
                    add(f"{path}.value", f"part_to_whole cannot show a negative "
                                         f"value{where}; a share of a net total is meaningless")
                    break
                if sum(values) <= 0:
                    add(f"{path}.value", f"values total zero{where}, so there is no whole to divide")
                    break

    elif form == "series":
        _check_series(chart, rows, groups, path, add, unique)

    elif form == "stacked_area":
        ok = _has_field(rows, chart["x"], f"{path}.x", add)
        ys = chart["y"]
        if not isinstance(ys, list) or not ys or not all(isinstance(y, str) for y in ys):
            add(f"{path}.y", "must be a list of field names")
            return
        if len(ys) > MAX_SERIES:
            add(f"{path}.y", f"{len(ys)} layers exceeds the {MAX_SERIES}-slot palette; group first")
        for y in ys:
            if _numeric(rows, y, f"{path}.y", add) and min(r[y] for r in rows) < 0:
                add(f"{path}.y", f"'{y}' has a negative value; a stacked area cannot show one")
        if ok:
            unique([chart["x"]], f"{path}.x", "x value")

    elif form == "distribution":
        _numeric(rows, chart["value"], f"{path}.value", add)

    elif form == "relationship":
        _numeric(rows, chart["x"], f"{path}.x", add)
        _numeric(rows, chart["y"], f"{path}.y", add)

    elif form == "matrix":
        ok_r = _has_field(rows, chart["row"], f"{path}.row", add)
        ok_c = _has_field(rows, chart["column"], f"{path}.column", add)
        _numeric(rows, chart["value"], f"{path}.value", add)
        if ok_r and ok_c:
            unique([chart["row"], chart["column"]], f"{path}.value", "cell")


def series_names(chart, rows):
    """The series a `series` chart will draw, in order."""
    if "y" in chart:
        return list(chart["y"])
    seen = []
    for row in rows:
        name = str(row[chart["series"]])
        if name not in seen:
            seen.append(name)
    return seen


def _check_series(chart, rows, groups, path, add, unique):
    wide = "y" in chart
    long_keys = [k for k in ("series", "value") if k in chart]
    if wide and long_keys:
        add(f"{path}.y", "give either 'y' (a list of fields) or 'series' with "
                         "'value', not both")
        return
    if not wide and len(long_keys) < 2:
        missing = "y" if not long_keys else ("value" if "value" not in chart else "series")
        add(f"{path}.{missing}", "a series chart needs 'y' (a list of fields), "
                                 "or 'series' with 'value'")
        return
    ok = _has_field(rows, chart["x"], f"{path}.x", add)
    if wide:
        ys = chart["y"]
        if not isinstance(ys, list) or not ys or not all(isinstance(y, str) for y in ys):
            add(f"{path}.y", "must be a list of field names")
            return
        ok = all([_numeric(rows, y, f"{path}.y", add) for y in ys]) and ok
        if ok:
            unique([chart["x"]], f"{path}.x", "x value")
        count_at = f"{path}.y"
    else:
        ok = _has_field(rows, chart["series"], f"{path}.series", add) and ok
        ok = _numeric(rows, chart["value"], f"{path}.value", add) and ok
        if ok:
            unique([chart["series"], chart["x"]], f"{path}.x", "series / x pair")
        count_at = f"{path}.series"
    if not ok:
        return
    names = series_names(chart, rows)
    emphasis = chart.get("emphasis")
    if emphasis is not None and emphasis not in names:
        add(f"{path}.emphasis", f"'{emphasis}' is not one of the series: {', '.join(names)}")
    elif emphasis is None and len(names) > MAX_SERIES:
        add(count_at, f"{len(names)} series exceeds the {MAX_SERIES}-slot palette; "
                      "group them, or set 'emphasis' to draw one in colour and "
                      "the rest gray")

    band = chart.get("band")
    if band is not None:
        if not isinstance(band, dict) or set(band) != {"lower", "upper"}:
            add(f"{path}.band", "must be an object with 'lower' and 'upper' field names")
        else:
            for side in ("lower", "upper"):
                _numeric(rows, band[side], f"{path}.band.{side}", add)
    lines = chart.get("reference_lines")
    if lines is not None:
        if not isinstance(lines, list):
            add(f"{path}.reference_lines", "must be a list")
            return
        for i, line in enumerate(lines):
            at = f"{path}.reference_lines[{i}]"
            if not isinstance(line, dict) or set(line) - {"y", "label"}:
                add(at, "must be an object with 'y' and an optional 'label'")
            elif not is_number(line.get("y")):
                add(f"{at}.y", "must be a number")
            elif "label" in line and not isinstance(line["label"], str):
                add(f"{at}.label", "must be text")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _steps(owner, rows, path, add):
    """Rows after the owner's steps, or None after reporting why not."""
    steps = owner.get("steps", [])
    if not isinstance(steps, list):
        add(f"{path}.steps", "must be a list of steps")
        return None
    try:
        return chart_data.apply_steps(rows, steps)
    except chart_data.StepError as exc:
        add(f"{path}.steps[{exc.index}]", exc.message)
        return None


def _check_chart(i, chart, tables_, seen_ids, add):
    path = f"charts[{i}]"
    if not isinstance(chart, dict):
        add(path, "a chart is an object")
        return
    cid = chart.get("id")
    if not isinstance(cid, str) or not _ID.match(cid):
        add(f"{path}.id", "needs an 'id' of letters, digits, '-' and '_' "
                          "(it names the chart's files)")
    elif cid in seen_ids:
        add(f"{path}.id", f"'{cid}' is already used by another chart")
    else:
        seen_ids.add(cid)

    form = chart.get("form")
    if form not in FORMS:
        add(f"{path}.form", f"unknown form {form!r}; expected one of: {', '.join(FORMS)}")
        return
    allowed = _CHART_COMMON | set(FIELDS[form]) | set(OPTIONS[form])
    for key in sorted(set(chart) - allowed):
        add(f"{path}.{key}", f"'{key}' is not a key of a {form} chart")

    preset = chart.get("preset")
    if preset is not None:
        if preset not in PRESETS:
            add(f"{path}.preset", f"unknown preset {preset!r}; expected one of: "
                                  f"{', '.join(PRESETS)}")
        elif PRESETS[preset] != form:
            add(f"{path}.preset", f"preset '{preset}' belongs on a "
                                  f"{PRESETS[preset]} chart, not {form}")
    for key in ("title", "note", "unit", "emphasis"):
        if key in chart and key in allowed and not isinstance(chart[key], str):
            add(f"{path}.{key}", "must be text")
    for key in ("sort", "diverging"):
        if key in chart and key in allowed and not isinstance(chart[key], bool):
            add(f"{path}.{key}", "must be true or false")
    if "domain" in chart and form == "matrix":
        dom = chart["domain"]
        if not (isinstance(dom, list) and len(dom) == 2
                and all(is_number(v) for v in dom) and dom[0] < dom[1]):
            add(f"{path}.domain", "must be [low, high] with low below high")

    missing = [f for f in FIELDS[form] if f not in chart]
    for field in missing:
        add(f"{path}.{field}", f"a {form} chart needs '{field}'")

    source = chart.get("from")
    if source not in tables_:
        add(f"{path}.from", f"needs 'from' naming a table in 'data'; "
                            f"available: {', '.join(tables_) or 'none'}")
        return
    if tables_[source] is None:
        return  # the table itself was reported; nothing more to learn here
    if not tables_[source]:
        add(f"{path}.from", f"table '{source}' has no rows")
        return
    rows = _steps(chart, tables_[source], path, add)
    if rows is None or missing:
        return
    if not rows:
        add(f"{path}.steps", "no rows are left after the steps, so there is nothing to draw")
        return

    facet = chart.get("facet")
    if facet is not None:
        if form == "matrix":
            add(f"{path}.facet", "a matrix chart cannot be faceted")
            return
        if not _has_field(rows, facet, f"{path}.facet", add):
            return
        distinct = len({r[facet] for r in rows})
        if distinct > MAX_FACETS:
            add(f"{path}.facet", f"'{facet}' has {distinct} distinct values; small "
                                 f"multiples stop being readable past {MAX_FACETS} "
                                 "-- group first")
            return
    _check_rows(chart, rows, path, add)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _check_block(path, block, charts_by_id, tables_, placed, add):
    if not isinstance(block, dict):
        add(path, "a block is an object")
        return
    kinds = [k for k in _BLOCK_KINDS if k in block]
    if isinstance(block.get("chart"), str) and block["chart"] in charts_by_id:
        # Counted as placed even if the block is malformed, so one mistake is
        # not reported twice.
        placed.add(block["chart"])
    if len(kinds) != 1:
        add(path, f"a block has exactly one of: {', '.join(_BLOCK_KINDS)}")
        return
    kind = kinds[0]
    extra = set(block) - {kind} - ({"width", "height"} if kind == "chart" else set())
    for key in sorted(extra):
        if key in ("width", "height"):
            add(f"{path}.{key}", f"only a chart block takes '{key}'")
        else:
            add(f"{path}.{key}", f"'{key}' is not a key of a {kind} block")

    if kind == "chart":
        cid = block["chart"]
        if cid not in charts_by_id:
            add(f"{path}.chart", f"no chart with id {cid!r}")
            return
        placed.add(cid)
        width = block.get("width", DEFAULT_WIDTH)
        height = block.get("height", DEFAULT_HEIGHT)
        if width not in WIDTHS:
            add(f"{path}.width", f"must be one of: {', '.join(WIDTHS)}")
        else:
            need = min_width(charts_by_id[cid])
            if not wider_or_equal(width, need):
                why = ("a faceted chart" if charts_by_id[cid].get("facet")
                       else f"a {charts_by_id[cid].get('form')} chart")
                add(f"{path}.width", f"{why} cannot be read at '{width}'; "
                                     f"the narrowest it supports is '{need}'")
        if height not in HEIGHTS:
            add(f"{path}.height", f"must be one of: {', '.join(HEIGHTS)}")

    elif kind == "text":
        if not isinstance(block["text"], str):
            add(f"{path}.text", "must be text")

    elif kind == "stat":
        stat = block["stat"]
        if not isinstance(stat, dict):
            add(f"{path}.stat", "must be an object")
            return
        for key in sorted(set(stat) - _STAT):
            add(f"{path}.stat.{key}", f"'{key}' is not a key of a stat")
        if not isinstance(stat.get("label"), str) or not stat.get("label"):
            add(f"{path}.stat.label", "a stat needs a text 'label'")
        if not is_number(stat.get("value")):
            add(f"{path}.stat.value", "a stat needs a numeric 'value'")
        if "change" in stat and not is_number(stat["change"]):
            add(f"{path}.stat.change", "must be a number")
        for key in ("unit", "change_unit"):
            if key in stat and not isinstance(stat[key], str):
                add(f"{path}.stat.{key}", "must be text")

    elif kind == "table":
        table = block["table"]
        if not isinstance(table, dict):
            add(f"{path}.table", "must be an object")
            return
        for key in sorted(set(table) - _TABLE_BLOCK):
            add(f"{path}.table.{key}", f"'{key}' is not a key of a table block")
        if "title" in table and not isinstance(table["title"], str):
            add(f"{path}.table.title", "must be text")
        source = table.get("from")
        if source not in tables_:
            add(f"{path}.table.from", f"needs 'from' naming a table in 'data'; "
                                      f"available: {', '.join(tables_) or 'none'}")
            return
        if tables_[source] is None:
            return
        rows = _steps(table, tables_[source], f"{path}.table", add)
        if rows is None:
            return
        columns = table.get("columns")
        if columns is not None:
            if (not isinstance(columns, list) or not columns
                    or not all(isinstance(c, str) for c in columns)):
                add(f"{path}.table.columns", "must be a list of field names")
            else:
                known = {k for r in rows for k in r}
                absent = [c for c in columns if c not in known]
                if absent:
                    add(f"{path}.table.columns",
                        f"no such field(s) after the steps: {', '.join(absent)}")


def _check_page(spec, charts_by_id, tables_, add):
    page = spec["page"]
    if not isinstance(page, list) or not page:
        add("page", "must be a non-empty list of sections")
        return
    placed = set()
    for i, section in enumerate(page):
        path = f"page[{i}]"
        if not isinstance(section, dict):
            add(path, "a section is an object")
            continue
        for key in sorted(set(section) - _SECTION):
            add(f"{path}.{key}", f"'{key}' is not a key of a section")
        for key in ("section", "text"):
            if key in section and not isinstance(section[key], str):
                add(f"{path}.{key}", "must be text")
        blocks = section.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            add(f"{path}.blocks", "a section needs a non-empty list of blocks")
            continue
        for j, block in enumerate(blocks):
            _check_block(f"{path}.blocks[{j}]", block, charts_by_id, tables_, placed, add)
    for i, chart in enumerate(spec.get("charts", [])):
        if isinstance(chart, dict) and chart.get("id") in charts_by_id \
                and charts_by_id[chart["id"]] is chart and chart["id"] not in placed:
            add(f"charts[{i}].id", f"chart '{chart['id']}' is declared but placed in "
                                   "no block of 'page'")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def validate(spec, base_dir):
    """Every problem with `spec`, as a list of Problem. Empty means valid."""
    problems = []

    def add(path, message):
        problems.append(Problem(path, message))

    if not isinstance(spec, dict):
        add("", "a spec is a JSON object")
        return problems
    for key in sorted(set(spec) - _TOP):
        add(key, f"'{key}' is not a key of a spec; expected: {', '.join(sorted(_TOP))}")
    if "title" in spec and not isinstance(spec["title"], str):
        add("title", "must be text")
    if spec.get("mode", "light") not in ("light", "dark"):
        add("mode", "must be 'light' or 'dark'")

    sources = spec.get("sources", [])
    if not isinstance(sources, list):
        add("sources", "must be a list")
    else:
        for i, source in enumerate(sources):
            path = f"sources[{i}]"
            if not isinstance(source, dict):
                add(path, "a source is an object")
                continue
            for key in sorted(set(source) - _SOURCE):
                add(f"{path}.{key}", f"'{key}' is not a key of a source")
            if not isinstance(source.get("name"), str) or not source.get("name"):
                add(f"{path}.name", "a source needs a text 'name'")
            if "as_of" in source and not isinstance(source["as_of"], str):
                add(f"{path}.as_of", "must be text")
            if "live" in source and not isinstance(source["live"], bool):
                add(f"{path}.live", "must be true or false")

    tables_ = _tables(spec, base_dir, add)

    charts = spec.get("charts")
    if not isinstance(charts, list) or not charts:
        add("charts", "a spec needs a non-empty list of charts")
        charts = []
    seen = set()
    charts_by_id = {}
    for i, chart in enumerate(charts):
        before = set(seen)
        _check_chart(i, chart, tables_, seen, add)
        new = seen - before
        if new:
            charts_by_id[new.pop()] = chart

    if "page" in spec:
        _check_page(spec, charts_by_id, tables_, add)
    return problems


def default_page(spec):
    """The page used when a spec declares none: every chart, full width."""
    return [{"blocks": [{"chart": c["id"]} for c in spec["charts"]]}]
