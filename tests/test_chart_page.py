"""The page: one self-contained file, every block type, downloads that work."""
import base64
import html
import html.parser
import re

import pytest

import chart_forms as f
import chart_page as pg
import palette as p

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="590" height="260"></svg>'
CHART_HTML = ('<!doctype html><html><head><script>var a = "</script>";</script>'
              '</head><body>chart body</body></html>')
HOSTILE = '<script>alert(1)</script>&"\''


def chart(cid="allocation", **kw):
    return dict({"kind": "chart", "id": cid, "title": "Allocation",
                 "note": "Half the book is one name.\nThe rest is spread thin.",
                 "html": CHART_HTML, "png": PNG, "svg": SVG,
                 "csv": "symbol,value\nNVDA,1000\n",
                 "width": "half", "height": "short"}, **kw)


def page(tmp_path, blocks=None, **kw):
    args = dict(title="Portfolio review", mode="light", sources=[],
                sections=[{"heading": "Where the money is", "text": "Both sources.",
                           "blocks": blocks or [chart()]}],
                spec_text='{"title": "Portfolio review"}')
    args.update(kw)
    out = pg.write_page(tmp_path / "page.html", **args)
    return out.read_text(encoding="utf-8")


def downloads(text):
    """{filename: decoded bytes} for every download link on the page."""
    out = {}
    for name, href in re.findall(r'download="([^"]+)" href="([^"]+)"', text):
        assert href.startswith("data:"), href[:40]
        out[name] = base64.b64decode(href.split("base64,", 1)[1])
    return out


def test_page_is_one_file_with_no_external_references(tmp_path):
    text = page(tmp_path)
    for attr, value in re.findall(r'\b(src|href)="([^"]*)"', text):
        assert value.startswith(("data:", "#")), (attr, value[:60])
    assert "http://" not in text.replace("http://www.w3.org", "")
    assert "https://" not in text
    assert list(tmp_path.iterdir()) == [tmp_path / "page.html"]


def test_the_page_itself_runs_no_script(tmp_path):
    """Downloads are plain links; only the embedded charts carry script."""
    assert "<script" not in page(tmp_path)


def test_every_chart_block_has_three_downloads(tmp_path):
    got = downloads(page(tmp_path))
    assert {"allocation.png", "allocation.svg", "allocation.csv"} <= set(got)


def test_downloads_decode_to_the_original_bytes(tmp_path):
    got = downloads(page(tmp_path))
    assert got["allocation.png"] == PNG
    assert got["allocation.svg"].decode() == SVG
    assert got["allocation.csv"].decode() == "symbol,value\nNVDA,1000\n"


def test_spec_download_is_present(tmp_path):
    assert downloads(page(tmp_path))["spec.json"].decode() == '{"title": "Portfolio review"}'


def test_embedded_chart_survives_a_closing_script_tag_in_its_html(tmp_path):
    text = page(tmp_path)
    srcdoc = re.search(r'srcdoc="([^"]*)"', text).group(1)
    assert html.unescape(srcdoc) == CHART_HTML      # round-trips exactly
    assert "</script>" not in srcdoc                # and cannot end anything early


def test_blocks_carry_their_declared_size(tmp_path):
    text = page(tmp_path)
    w, h = f.WIDTH_PX["half"], f.HEIGHT_PX["short"]
    assert f'width="{w}" height="{h}"' in text          # the frame matches the chart
    assert f"width:{w}px" in text                       # and so does its panel


def test_table_block_has_a_csv_download_and_its_cells(tmp_path):
    table = {"kind": "table", "title": "Positions", "columns": ["symbol", "value"],
             "rows": [{"symbol": "NVDA", "value": 1234567.5}, {"symbol": "VTI", "value": 10}],
             "csv": "symbol,value\nNVDA,1234567.5\nVTI,10\n"}
    text = page(tmp_path, [chart(), table])
    assert "<th>symbol</th>" in text and "<td>NVDA</td>" in text
    assert "1,234,567.5" in text
    assert downloads(text)["positions.csv"].decode().startswith("symbol,value")


def test_stat_change_is_signed_and_uses_polarity_colour(tmp_path):
    up = {"kind": "stat", "label": "Total value", "value": 184250, "unit": "$",
          "change": 2.1, "change_unit": "%"}
    down = dict(up, label="Cash", change=-2.1)
    text = page(tmp_path, [chart(), up, down])
    assert "$184,250" in text
    assert re.search(rf'color:{p.POSITIVE["light"]}[^>]*>\+2\.1%', text)
    assert re.search(rf'color:{p.NEGATIVE["light"]}[^>]*>−2\.1%', text)   # U+2212


def test_stat_without_a_change_shows_none(tmp_path):
    text = page(tmp_path, [chart(), {"kind": "stat", "label": "Accounts", "value": 4}])
    assert ">4<" in text and "class=\"change\"" not in text


def test_text_block_and_section_text_appear(tmp_path):
    text = page(tmp_path, [chart(), {"kind": "text", "text": "A paragraph."}])
    assert "A paragraph." in text and "Both sources." in text
    assert "<h2>Where the money is</h2>" in text


def test_header_lists_sources_and_flags_not_live(tmp_path):
    text = page(tmp_path, sources=[
        {"name": "robinhood", "as_of": "2026-11-22T14:05", "live": True},
        {"name": "monarch", "as_of": "2026-11-22T06:00", "live": False}])
    assert "robinhood" in text and "monarch" in text
    assert "2026-11-22T06:00" in text
    assert "not live" in text


def test_header_says_nothing_about_liveness_without_sources(tmp_path):
    assert "not live" not in page(tmp_path)


def test_hostile_text_is_escaped_everywhere(tmp_path):
    blocks = [chart(title=HOSTILE, note=HOSTILE),
              {"kind": "stat", "label": HOSTILE, "value": 1, "unit": HOSTILE},
              {"kind": "table", "title": HOSTILE, "columns": [HOSTILE],
               "rows": [{HOSTILE: HOSTILE}], "csv": "x\n"},
              {"kind": "text", "text": HOSTILE}]
    text = page(tmp_path, blocks, title=HOSTILE,
                sources=[{"name": HOSTILE, "as_of": HOSTILE, "live": False}],
                sections=[{"heading": HOSTILE, "text": HOSTILE, "blocks": blocks}])
    assert "<script" not in text
    assert "alert(1)" in text                 # still there, as literal text

    class Strict(html.parser.HTMLParser):
        tags = []
        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
    parser = Strict()
    parser.feed(text)
    assert "script" not in parser.tags


def test_a_hostile_chart_id_cannot_break_out_of_the_download_attribute(tmp_path):
    text = page(tmp_path, [chart(cid='x" onclick="alert(1)')])
    assert 'onclick="alert(1)"' not in text


def test_a_note_keeps_its_line_breaks_and_a_chart_without_one_gets_no_element(tmp_path):
    text = page(tmp_path, [chart(), chart(cid="b", note=None)])
    assert "Half the book is one name.\nThe rest is spread thin." in text
    assert text.count('class="note"') == 1
    assert "white-space: pre-line" in text


def test_blocks_keep_the_order_given(tmp_path):
    text = page(tmp_path, [chart(cid="zeta", title="Zeta"), chart(cid="alpha", title="Alpha")])
    assert text.index("Zeta") < text.index("Alpha")


def test_page_carries_an_as_of_stamp_and_the_chart_count(tmp_path):
    text = page(tmp_path, [chart(), chart(cid="b")])
    assert "as of" in text and "2 charts" in text


def test_page_chrome_follows_dark_mode(tmp_path):
    text = page(tmp_path, mode="dark")
    assert p.SURFACE["dark"] in text and "color-scheme: dark" in text


def test_faceted_chart_shows_each_panel_with_its_own_downloads(tmp_path):
    facets = {"kind": "facets", "id": "by_account", "title": "By account", "note": None,
              "csv": "a,b\n", "width": "third", "height": "short",
              "cells": [{"name": "Agentic", "html": CHART_HTML, "png": PNG, "svg": SVG},
                        {"name": "Roth IRA", "html": CHART_HTML, "png": PNG, "svg": SVG}]}
    text = page(tmp_path, [facets])
    got = downloads(text)
    assert {"by_account-agentic.png", "by_account-roth-ira.svg", "by_account.csv"} <= set(got)
    assert "Agentic" in text and "Roth IRA" in text
    assert text.count("<iframe") == 2


def test_no_sections_raises(tmp_path):
    with pytest.raises(ValueError):
        pg.write_page(tmp_path / "p.html", title="t", mode="light", sources=[],
                      sections=[], spec_text="{}")


def test_to_csv_quotes_commas_and_newlines():
    out = pg.to_csv([{"a": "x, y", "b": "line\nbreak"}, {"a": 1, "c": 2}])
    assert out.splitlines()[0] == "a,b,c"
    assert '"x, y"' in out and '"line\nbreak"' in out


def test_to_csv_takes_a_column_list():
    assert pg.to_csv([{"a": 1, "b": 2}], ["b"]) == "b\r\n2\r\n" or \
        pg.to_csv([{"a": 1, "b": 2}], ["b"]) == "b\n2\n"


def test_slug_makes_a_safe_filename():
    assert pg.slug("Portfolio review — Q4 / 2026") == "portfolio-review-q4-2026"
    assert pg.slug("") == "charts" and pg.slug("../../etc") == "etc"


def test_panels_add_no_width_beyond_their_chart(tmp_path):
    """Two half-width charts and the gutter must fit one full-width row.

    A 1px border on each panel made the row 1204px and wrapped the second
    chart underneath -- caught by looking at a render, not by a test.
    """
    text = page(tmp_path)
    rule = re.search(r"\.panel \{([^}]*)\}", text).group(1)
    assert "border:" not in rule and "padding" not in rule
    assert 2 * f.WIDTH_PX["half"] + pg.GAP_PX <= pg.PAGE_WIDTH_PX
    assert 3 * f.WIDTH_PX["third"] + 2 * pg.GAP_PX <= pg.PAGE_WIDTH_PX
