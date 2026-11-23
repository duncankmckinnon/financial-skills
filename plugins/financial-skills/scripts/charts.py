#!/usr/bin/env python3
"""Render a chart spec into one self-contained page.

    uv run --with 'xy==0.0.6' python charts.py validate spec.json
    uv run --with 'xy==0.0.6' python charts.py render spec.json [--open] [--keep] [--out DIR]

A spec is a JSON file describing a run of charts, the rows behind them, and
the page they sit on -- see references/chart-spec.md. Nothing renders unless
the spec validates, and every problem is reported at once.

`render` prints one JSON object: the page, each chart's files, any warnings,
and whether a viewer was opened. Exit 0 rendered or valid, 2 invalid spec,
1 anything else.

This file is the only path a caller needs. It finds its sibling modules and
assets/palette.py from its own location.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import chart_spec  # noqa: E402  (import follows the path fix above)


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


def run_dir(keep=False, out=None):
    """Where a run's files go.

    Ephemeral by default: charts are derived output, regenerable from live
    data in seconds, and they hold real position and P/L figures. Keeping
    every render forever accumulates sensitive data with no lifecycle.
    `keep` archives deliberately under the financial home.
    """
    if out:
        return pathlib.Path(out).expanduser()
    if keep:
        return financial_home() / "charts" / datetime.date.today().isoformat()
    return pathlib.Path(tempfile.mkdtemp(prefix="financial-charts-"))


def show(path):
    """Open a rendered page for the human. macOS, Linux and Windows.

    Reading a PNG renders it into the agent's context, not the human's -- they
    see nothing until something opens it.

    Returns True if a viewer was launched. False means no display is available:
    report the file path instead of implying the page was delivered.
    """
    import webbrowser
    p = pathlib.Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(p)
    try:
        return bool(webbrowser.open(p.as_uri()))
    except Exception:
        return False


def _problems(problems):
    print(json.dumps({"problems": [p._asdict() for p in problems]}, indent=2))
    return 2


def _load(path):
    """(spec, base_dir, problems). Problems is non-empty when it cannot run."""
    try:
        spec = chart_spec.load(path)
    except chart_spec.SpecError as exc:
        return None, None, [exc.problem]
    base = pathlib.Path(path).resolve().parent
    return spec, base, chart_spec.validate(spec, base)


def _export(built, stem, out):
    """Write a built chart's PNG and SVG; return what the page embeds."""
    png, svg = out / f"{stem}.png", out / f"{stem}.svg"
    built.chart.to_png(str(png))
    markup = built.chart.to_svg()
    svg.write_text(markup, encoding="utf-8")
    return {"html": built.chart.to_html(), "png": png.read_bytes(), "svg": markup,
            "png_path": str(png), "svg_path": str(svg)}


def render(spec, base, out, mode):
    """Render every block of the page. Returns (page path, charts, warnings)."""
    # Imported here so `validate` never needs the charting dependency.
    import chart_forms
    import chart_page

    out.mkdir(parents=True, exist_ok=True)
    charts = {c["id"]: c for c in spec["charts"]}
    rows = {cid: chart_spec.chart_rows(spec, c, base) for cid, c in charts.items()}
    warnings, summary, done = [], {}, {}

    for cid, chart in charts.items():
        csv_path = out / f"{cid}.csv"
        csv_path.write_text(chart_page.to_csv(rows[cid]), encoding="utf-8")
        summary[cid] = {"id": cid, "csv": str(csv_path)}

    def chart_block(block):
        cid = block["chart"]
        chart = charts[cid]
        width = block.get("width", chart_spec.DEFAULT_WIDTH)
        height = block.get("height", chart_spec.DEFAULT_HEIGHT)
        key = (cid, width, height)
        if key in done:
            return done[key]
        common = {"id": cid, "title": chart_forms.title_of(chart),
                  "note": chart.get("note"), "height": height,
                  "csv": chart_page.to_csv(rows[cid])}
        if chart.get("facet"):
            cells = []
            for name, built in chart_forms.build_facets(chart, rows[cid], height, mode):
                files = _export(built, f"{cid}-{chart_page.slug(name, 'panel')}", out)
                warnings.extend(w for w in built.warnings if w not in warnings)
                cells.append(dict(files, name=name))
            summary[cid].setdefault("panels", [
                {"name": c["name"], "png": c["png_path"], "svg": c["svg_path"]}
                for c in cells])
            made = dict(common, kind="facets", cells=cells,
                        width=chart_forms.facet_cell_width(chart))
        else:
            built = chart_forms.build(chart, rows[cid], width, height, mode)
            warnings.extend(w for w in built.warnings if w not in warnings)
            # The first placement owns the plain filename; a second size of
            # the same chart is named for its size.
            first = "png" not in summary[cid]
            files = _export(built, cid if first else f"{cid}-{width}-{height}", out)
            if first:
                summary[cid].update(png=files["png_path"], svg=files["svg_path"])
            made = {**common, **files, "kind": "chart", "width": width}
        done[key] = made
        return made

    sections = []
    for section in spec.get("page") or chart_spec.default_page(spec):
        blocks = []
        for block in section["blocks"]:
            if "chart" in block:
                blocks.append(chart_block(block))
            elif "stat" in block:
                blocks.append(dict(block["stat"], kind="stat"))
            elif "text" in block:
                blocks.append({"kind": "text", "text": block["text"]})
            else:
                table = block["table"]
                data = chart_spec.chart_rows(spec, table, base)
                columns = table.get("columns") or [
                    k for k in dict.fromkeys(k for r in data for k in r)]
                blocks.append({"kind": "table", "title": table.get("title"),
                               "columns": columns, "rows": data,
                               "csv": chart_page.to_csv(data, columns)})
        sections.append({"heading": section.get("section"),
                         "text": section.get("text"), "blocks": blocks})

    title = spec.get("title") or "Charts"
    page = chart_page.write_page(
        out / f"{chart_page.slug(title)}.html", title=title, mode=mode,
        sources=spec.get("sources", []), sections=sections,
        spec_text=json.dumps(spec, indent=2))
    return page, [summary[cid] for cid in charts], warnings


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="charts.py", description="Render a chart spec into one page.")
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render", help="validate a spec, then render it")
    r.add_argument("spec")
    r.add_argument("--out", help="directory to write into (default: temporary)")
    r.add_argument("--keep", action="store_true",
                   help="archive under $FINANCIAL_HOME/charts/<date>/")
    r.add_argument("--open", action="store_true", help="open the page when done")
    v = sub.add_parser("validate", help="check a spec without rendering")
    v.add_argument("spec")
    args = ap.parse_args(argv)

    spec, base, problems = _load(args.spec)
    if problems:
        return _problems(problems)
    if args.command == "validate":
        print(json.dumps({"problems": []}))
        return 0

    try:
        page, charts, warnings = render(
            spec, base, run_dir(args.keep, args.out), spec.get("mode", "light"))
    except Exception as exc:  # a render failure the validator did not foresee
        print(f"render failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    opened = show(page) if args.open else False
    print(json.dumps({"page": str(page), "charts": charts, "warnings": warnings,
                      "opened": opened}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
