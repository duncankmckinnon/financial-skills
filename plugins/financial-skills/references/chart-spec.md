# Chart spec reference

A chart spec is one JSON file describing a run of charts, the rows behind
them, and the page they sit on. `scripts/charts.py` validates it and renders
it. Unknown keys anywhere are an error, so a typo is reported, never ignored.

```
uv run --with 'xy==0.0.6' python "$ROOT/scripts/charts.py" validate spec.json
uv run --with 'xy==0.0.6' python "$ROOT/scripts/charts.py" render spec.json [--open] [--keep] [--out DIR]
```

| Exit | Meaning |
|---|---|
| 0 | valid, or rendered |
| 2 | invalid spec — stdout is `{"problems": [{"path", "message"}]}`, nothing is written |
| 1 | anything else — the reason is on stderr |

## Top level

| Key | Required | Meaning |
|---|---|---|
| `title` | no | Page title. Also names the page file. |
| `mode` | no | `light` (default) or `dark`. |
| `sources` | no | Where the rows came from. Printed in the page header. |
| `data` | yes | Named tables of rows. |
| `charts` | yes | The charts. |
| `page` | no | Sections and blocks. Omitted: every chart once, full width, in order. |

### `sources`

```json
"sources": [
  {"name": "robinhood", "as_of": "2026-11-22 14:05", "live": true},
  {"name": "monarch",   "as_of": "2026-11-22 06:00", "live": false}
]
```

`name` is required. A source with `"live": false` makes the header say that
some figures are synced, not live. Fill this in whenever rows came from a
connected source.

### `data`

Each table is `{"rows": [ {...}, ... ]}` inline, or `{"file": "rows.json"}`
naming a JSON array of objects, resolved relative to the spec file.

## Charts

Every chart has:

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Letters, digits, `-`, `_`. Names the chart's files; unique. |
| `form` | yes | One of the forms below. |
| `from` | yes | The table to draw from. |
| `steps` | no | Data steps, applied in order. |
| `preset` | no | Labels and units for a financial case. |
| `title` | no | Panel heading. Defaults to the preset's, then the id. |
| `note` | no | Commentary printed under the chart. |
| `facet` | no | A field; the chart repeats once per distinct value. |

### Forms

| Form | Fields | Options | The reader's job |
|---|---|---|---|
| `part_to_whole` | `label`, `value` | — | see shares of a whole |
| `magnitude` | `label`, `value` | `unit` | compare sizes across categories |
| `diverging` | `label`, `value` | `unit`, `sort` | see above / below a baseline |
| `series` | `x`, and `y` or `series` + `value` | `emphasis`, `reference_lines`, `band` | follow values over a common x |
| `stacked_area` | `x`, `y` | — | see parts of a total over time |
| `distribution` | `value` | — | see the shape of a sample |
| `relationship` | `x`, `y` | — | see how two measures relate |
| `matrix` | `row`, `column`, `value` | `diverging`, `domain` | read a grid of values |

Every field is the name of a column in the chart's rows after its steps.

- `unit` is `"$"`, `"%"` or any short suffix. It formats the direct labels.
- `sort` (diverging) defaults to `true`, most negative first. `false` keeps
  the row order.
- `series` takes **wide** form, `"y": ["a", "b"]`, one column per line, or
  **long** form, `"series": "name", "value": "v"`, one row per point.
- `emphasis` names one series to draw in the accent colour; the rest go gray.
  Required when there are more than 8 series.
- `reference_lines` is a list of `{"y": number, "label": "text"}`.
- `band` is `{"lower": field, "upper": field}`, a shaded range behind the
  lines.
- `matrix` cells not present in the rows are left empty. `diverging: true`
  only where the data has a meaningful zero or midpoint; `domain` is
  `[low, high]`.

What validation refuses, and why:

| Refused | Because |
|---|---|
| two rows with the same label in `part_to_whole`, `magnitude`, `diverging` | two marks the reader cannot tell apart — add a `group` step |
| a negative value, or a zero total, in `part_to_whole` | a share of a net total is meaningless |
| a negative value in `stacked_area` | a stack cannot show one |
| more than 8 series or layers without `emphasis` | the palette has 8 slots and is never cycled |
| a missing, null or non-finite value where a number is needed | the chart would silently drop or misplace it |
| no rows left after the steps | there is nothing to draw |

There is no field for a second y-axis, a pie, or custom colours.

### Presets

A preset sets a default title, axis label and unit. It is valid only on its
own form.

| Preset | Form | Sets |
|---|---|---|
| `allocation` | `part_to_whole` | axis "% of portfolio" |
| `drift` | `diverging` | unit `%`, axis "percentage points vs target" |
| `pl` | `diverging` | unit `$`, axis "unrealized profit / loss" |
| `value_over_time` | `series` | title "Portfolio value" |
| `correlation` | `matrix` | diverging, domain −1 to +1 |
| `projection` | `series` | x label "year" |
| `contributions` | `stacked_area` | x label "year" |

### Facets

`"facet": "account"` repeats the chart once per distinct value of that field,
all panels on one shared value axis, laid out together in one full-width
panel. Up to 12 values; past that, group first. Not available on `matrix`.
A faceted chart can only be placed at `full` width.

## Data steps

Each step is an object with exactly one key. They run in order on the chart's
table and never change the table itself, so two charts can shape the same
table differently.

| Step | Shape | Effect |
|---|---|---|
| `filter` | `{"field": f, "equals": v}` or `{"field": f, "in": [v, ...]}` | keep matching rows |
| `group` | `{"by": f or [f, ...], "sum": [..], "mean": [..], "count": [..]}` | one row per group, holding the `by` fields and the aggregated fields |
| `share` | `{"of": f, "as": g}` | `g` = percent of the column's total |
| `diff` | `{"a": f, "b": g, "as": h}` | `h` = `a − b` |
| `sort` | `{"by": f, "desc": false}` | order rows |
| `top` | `{"n": k, "by": f}` | keep the `k` largest, largest first |

There are no expressions. A figure the steps cannot produce is computed
before the rows go into the spec.

Folding a long tail into "Other" is done by the form, not by a step:
`part_to_whole` keeps the top 7, and `magnitude` folds to what its height can
hold. Both report what they folded in the run's warnings.

## The page

`page` is a list of sections. A section has an optional `section` heading, an
optional `text` paragraph, and a `blocks` list. Blocks flow left to right and
wrap. There is no limit on sections or blocks.

| Block | Shape |
|---|---|
| chart | `{"chart": id, "width": "full", "height": "regular"}` |
| stat | `{"stat": {"label", "value", "unit", "change", "change_unit"}}` |
| table | `{"table": {"from", "steps", "columns", "title"}}` |
| text | `{"text": "a paragraph"}` |

- `width` is `full` (1200px), `half` (590px) or `third` (386px). `height` is
  `short` (260px), `regular` (420px) or `tall` (640px). Defaults: `full`,
  `regular`. Two halves or three thirds make one row.
- **A chart is drawn at the size its block declares.** Sizes are fixed when
  the page is rendered; on a narrow window the blocks wrap, they do not
  shrink.
- `part_to_whole` and `matrix` need at least `half`. Narrower is a validation
  error.
- A chart may be placed more than once, at different sizes. Every declared
  chart must be placed at least once.
- A stat's `value` is a number. `change` is drawn with an explicit sign, blue
  when positive and red when negative.
- A table shows the first 200 rows; its CSV download has all of them.

The page has no filters, tabs or controls. Nothing is computed in the
browser.

## What `render` writes

One directory — temporary by default, `$FINANCIAL_HOME/charts/<date>/` with
`--keep`, or `--out DIR` — holding:

- `<title-slug>.html`, the page. One self-contained file: it needs no sibling
  file and no network. Each chart on it is interactive (tooltips, crosshair,
  pan, zoom) and has PNG, SVG and CSV download links; each table has a CSV
  link; the header has a link to download the spec.
- `<id>.png`, `<id>.svg`, `<id>.csv` per chart. The CSV is the chart's rows
  after its steps. A second placement at another size is
  `<id>-<width>-<height>.png`. A faceted chart writes `<id>-<value>.png` and
  `.svg` per panel.

and prints one JSON object:

```json
{
  "page": ".../portfolio-review.html",
  "charts": [{"id": "allocation", "png": "...", "svg": "...", "csv": "..."}],
  "warnings": ["Allocation: folded 5 into Other"],
  "opened": true
}
```

A faceted chart has `"panels": [{"name", "png", "svg"}]` in place of `png`
and `svg`. `opened` is `false` when `--open` was not passed or no viewer could
be launched.

## A worked spec

```json
{
  "title": "Portfolio review",
  "sources": [{"name": "robinhood", "as_of": "2026-11-22 14:05", "live": true}],
  "data": {
    "positions": {"rows": [
      {"symbol": "NVDA", "account": "Agentic", "value": 5200, "cost": 2100},
      {"symbol": "VTI",  "account": "Roth IRA", "value": 8400, "cost": 7000},
      {"symbol": "DAL",  "account": "Agentic", "value": 900,  "cost": 1500}
    ]},
    "history": {"file": "history.json"}
  },
  "charts": [
    {"id": "allocation", "form": "part_to_whole", "preset": "allocation",
     "from": "positions", "label": "symbol", "value": "value",
     "note": "VTI is over half the book."},
    {"id": "pl", "form": "diverging", "preset": "pl", "from": "positions",
     "steps": [{"diff": {"a": "value", "b": "cost", "as": "pl"}}],
     "label": "symbol", "value": "pl"},
    {"id": "value", "form": "series", "preset": "value_over_time",
     "from": "history", "x": "month", "y": ["value"],
     "reference_lines": [{"y": 12000, "label": "contributed"}]},
    {"id": "by_account", "form": "magnitude", "title": "Holdings by account",
     "from": "positions", "facet": "account",
     "label": "symbol", "value": "value", "unit": "$"}
  ],
  "page": [
    {"section": "Where the money is", "blocks": [
      {"stat": {"label": "Total value", "value": 14500, "unit": "$",
                "change": 5.6, "change_unit": "%"}},
      {"chart": "allocation", "height": "short"},
      {"chart": "pl", "width": "half"},
      {"chart": "value", "width": "half"}
    ]},
    {"section": "By account", "blocks": [
      {"chart": "by_account", "height": "short"},
      {"table": {"from": "positions", "title": "Positions",
                 "columns": ["symbol", "account", "value", "cost"]}}
    ]}
  ]
}
```
