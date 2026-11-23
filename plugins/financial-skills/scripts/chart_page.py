"""The page a run of charts is delivered as.

One self-contained HTML file: every chart is embedded in it, nothing is
fetched, and no sibling file is needed. A batch of charts is one finding, not
N -- opening a tab per chart makes the human assemble the story from separate
windows.

Each chart sits in an iframe holding the standalone document `xy` produced, so
tooltips, crosshair, pan and zoom all still work. The page itself runs no
script: every download is a plain link carrying its file as a data URI.

Everything written at runtime -- titles, notes, labels, table cells -- is
escaped. It is prose and data from a spec, and must stay literal text.
"""
import base64
import csv
import html
import io
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "assets"))

import palette as p  # noqa: E402
from chart_forms import HEIGHT_PX, MINUS, WIDTH_PX, as_of  # noqa: E402

PAGE_WIDTH_PX = WIDTH_PX["full"]
GAP_PX = 20
MAX_TABLE_ROWS = 200  # shown on the page; the CSV download always has them all

_e = html.escape  # escapes quotes too, so it is safe inside an attribute


def slug(text, fallback="charts"):
    """A safe, readable filename stem for a title or facet value."""
    out = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return out or fallback


def to_csv(rows, columns=None):
    """Rows as CSV text. Columns default to every key, in first-seen order."""
    if columns is None:
        columns = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(["" if row.get(c) is None else row.get(c) for c in columns])
    return buf.getvalue()


def _data_uri(mime, payload):
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"


def _download(filename, mime, payload, text):
    return (f'<a class="dl" download="{_e(filename)}" '
            f'href="{_data_uri(mime, payload)}">{_e(text)}</a>')


def _number(value, unit=""):
    """A figure for display: thousands separators, no needless decimals."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    body = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}".rstrip("0").rstrip(".")
    if unit == "$":
        return f"{MINUS}${body.lstrip('-')}" if value < 0 else f"${body}"
    return body.replace("-", MINUS) + unit


def _signed(value, unit=""):
    """Explicit sign, so polarity never rides on colour alone."""
    sign = "+" if value >= 0 else MINUS
    return sign + _number(abs(value), "") + unit if unit != "$" \
        else f"{sign}${_number(abs(value))}"


def _frame(doc, title, width, height):
    # srcdoc holds the chart's whole document, escaped as an attribute value:
    # a "</script>" inside it is then just text and cannot end anything early.
    return (f'<iframe title="{_e(title)}" loading="lazy" '
            f'width="{WIDTH_PX[width]}" height="{HEIGHT_PX[height]}" '
            f'srcdoc="{_e(doc)}"></iframe>')


def _note(note):
    return f'<p class="note">{_e(note)}</p>' if note else ""


def _chart_block(block):
    cid = block["id"]
    links = (_download(f"{cid}.png", "image/png", block["png"], "PNG")
             + _download(f"{cid}.svg", "image/svg+xml", block["svg"], "SVG")
             + _download(f"{cid}.csv", "text/csv;charset=utf-8", block["csv"], "CSV"))
    return (f'<figure class="panel" style="width:{WIDTH_PX[block["width"]]}px">'
            f'<figcaption><span>{_e(block["title"])}</span>'
            f'<span class="dls">{links}</span></figcaption>'
            f'{_frame(block["html"], block["title"], block["width"], block["height"])}'
            f'{_note(block.get("note"))}</figure>')


def _facets_block(block):
    cid = block["id"]
    cells = ""
    for cell in block["cells"]:
        stem = f"{cid}-{slug(cell['name'], 'panel')}"
        links = (_download(f"{stem}.png", "image/png", cell["png"], "PNG")
                 + _download(f"{stem}.svg", "image/svg+xml", cell["svg"], "SVG"))
        cells += (f'<div class="cell" style="width:{WIDTH_PX[block["width"]]}px">'
                  f'<div class="cellcap"><span>{_e(cell["name"])}</span>'
                  f'<span class="dls">{links}</span></div>'
                  f'{_frame(cell["html"], cell["name"], block["width"], block["height"])}'
                  f'</div>')
    csv_link = _download(f"{cid}.csv", "text/csv;charset=utf-8", block["csv"], "CSV")
    return (f'<figure class="panel" style="width:{PAGE_WIDTH_PX}px">'
            f'<figcaption><span>{_e(block["title"])}</span>'
            f'<span class="dls">{csv_link}</span></figcaption>'
            f'<div class="cells">{cells}</div>{_note(block.get("note"))}</figure>')


def _stat_block(block, mode):
    unit = block.get("unit") or ""
    body = (f'<div class="statlabel">{_e(block["label"])}</div>'
            f'<div class="statvalue">{_e(_number(block["value"], unit))}</div>')
    if block.get("change") is not None:
        change = block["change"]
        colour = p.POSITIVE[mode] if change >= 0 else p.NEGATIVE[mode]
        body += (f'<div class="change" style="color:{colour}">'
                 f'{_e(_signed(change, block.get("change_unit") or ""))}</div>')
    return f'<div class="stat">{body}</div>'


def _table_block(block):
    columns = block["columns"]
    rows = block["rows"]
    head = "".join(f"<th>{_e(str(c))}</th>" for c in columns)
    body = ""
    for row in rows[:MAX_TABLE_ROWS]:
        cells = ""
        for c in columns:
            v = row.get(c)
            numeric = isinstance(v, (int, float)) and not isinstance(v, bool)
            text = "" if v is None else (_number(v) if numeric else str(v))
            cells += f'<td class="num">{_e(text)}</td>' if numeric else f"<td>{_e(text)}</td>"
        body += f"<tr>{cells}</tr>"
    more = ""
    if len(rows) > MAX_TABLE_ROWS:
        more = (f'<p class="note">{len(rows) - MAX_TABLE_ROWS} more rows are in '
                "the CSV download.</p>")
    title = block.get("title") or "Table"
    link = _download(f"{slug(title, 'table')}.csv", "text/csv;charset=utf-8",
                     block["csv"], "CSV")
    return (f'<figure class="panel tablepanel"><figcaption><span>{_e(title)}</span>'
            f'<span class="dls">{link}</span></figcaption>'
            f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>{more}</figure>')


def _block(block, mode):
    kind = block["kind"]
    if kind == "chart":
        return _chart_block(block)
    if kind == "facets":
        return _facets_block(block)
    if kind == "stat":
        return _stat_block(block, mode)
    if kind == "table":
        return _table_block(block)
    if kind == "text":
        return f'<p class="prose">{_e(block["text"])}</p>'
    raise ValueError(f"unknown block kind {kind!r}")


def _sources_line(sources):
    if not sources:
        return ""
    parts = []
    for s in sources:
        detail = []
        if s.get("as_of"):
            detail.append(f"as of {s['as_of']}")
        if s.get("live") is False:
            detail.append("not live")
        parts.append(_e(s["name"]) + (f" ({_e(', '.join(detail))})" if detail else ""))
    line = f'<div class="stamp">Sources: {" &middot; ".join(parts)}</div>'
    if any(s.get("live") is False for s in sources):
        line += ('<div class="stamp warn">Some figures are synced, not live. '
                 "Check each source's as-of time before acting on them.</div>")
    return line


def write_page(path, *, title, mode, sources, sections, spec_text):
    """Write the page and return its path. Raises if there is nothing to show."""
    if not sections or not any(s.get("blocks") for s in sections):
        raise ValueError("a page needs at least one section with a block")
    surface, ink = p.SURFACE[mode], p.INK[mode]
    charts = sum(1 for s in sections for b in s["blocks"]
                 if b["kind"] in ("chart", "facets"))
    body = ""
    for section in sections:
        body += "<section>"
        if section.get("heading"):
            body += f"<h2>{_e(section['heading'])}</h2>"
        if section.get("text"):
            body += f'<p class="prose">{_e(section["text"])}</p>'
        body += '<div class="blocks">'
        body += "".join(_block(b, mode) for b in section["blocks"])
        body += "</div></section>\n"
    spec_link = _download("spec.json", "application/json", spec_text, "Download spec")
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<style>
  :root {{ color-scheme: {mode}; }}
  body {{ margin: 0; padding: 24px; background: {surface}; color: {ink["primary"]};
         font-family: system-ui, sans-serif; }}
  main {{ max-width: {PAGE_WIDTH_PX}px; margin: 0 auto; }}
  header {{ margin: 0 0 24px; display: flex; justify-content: space-between;
            align-items: flex-start; gap: 16px; }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0; }}
  h2 {{ font-size: 16px; font-weight: 600; margin: 28px 0 8px; }}
  .stamp {{ font-size: 13px; color: {ink["muted"]}; margin-top: 4px; }}
  .warn {{ color: {ink["secondary"]}; }}
  .prose {{ margin: 0 0 12px; max-width: 75ch; width: 100%; font-size: 14px;
            line-height: 1.5; color: {ink["secondary"]}; white-space: pre-line; }}
  /* Fixed-width blocks that wrap: xy does not reflow a chart to its container,
     so a column is never squeezed narrower than the chart drawn for it. */
  .blocks {{ display: flex; flex-wrap: wrap; gap: {GAP_PX}px; align-items: flex-start; }}
  /* The frame is a shadow, not a border: a border adds 2px to every panel,
     and two 590px charts plus the gutter then no longer fit a 1200px row. */
  .panel {{ margin: 0; box-shadow: 0 0 0 1px {ink["grid"]}; border-radius: 8px;
            overflow: hidden; background: {surface}; }}
  .tablepanel {{ width: 100%; box-sizing: border-box; }}
  figcaption, .cellcap {{ display: flex; justify-content: space-between;
      align-items: baseline; gap: 12px; padding: 10px 14px; font-size: 14px;
      font-weight: 600; border-bottom: 1px solid {ink["grid"]}; }}
  .cellcap {{ font-weight: 500; font-size: 13px; }}
  .dls {{ display: flex; gap: 10px; white-space: nowrap; }}
  a.dl {{ font-size: 12px; font-weight: 400; color: {ink["muted"]}; }}
  iframe {{ display: block; border: 0; }}
  .cells {{ display: flex; flex-wrap: wrap; gap: {GAP_PX}px; padding: 0; }}
  /* pre-line: a note is written as one or two short lines, and collapsing
     them into a paragraph loses the author's breaks. */
  .note {{ margin: 0; padding: 12px 16px 14px; border-top: 1px solid {ink["grid"]};
           white-space: pre-line; font-size: 13px; line-height: 1.5;
           color: {ink["secondary"]}; }}
  .stat {{ min-width: 170px; padding: 14px 16px; box-shadow: 0 0 0 1px {ink["grid"]};
           border-radius: 8px; }}
  .statlabel {{ font-size: 13px; color: {ink["muted"]}; }}
  .statvalue {{ font-size: 26px; font-weight: 600; margin-top: 4px; }}
  .change {{ font-size: 14px; font-weight: 600; margin-top: 2px; }}
  .scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: left; padding: 7px 14px; border-bottom: 1px solid {ink["grid"]}; }}
  th {{ color: {ink["muted"]}; font-weight: 500; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>{_e(title)}</h1>
      <div class="stamp">as of {as_of()} &middot; {charts} chart{"" if charts == 1 else "s"}</div>
      {_sources_line(sources)}
    </div>
    <div class="dls">{spec_link}</div>
  </header>
{body}</main>
</body>
</html>
""", encoding="utf-8")
    return path
