"""The run dashboard: every chart of a run on one page, in one tab.

`chart_dir()` has always promised charts "land together and can be opened as
a set". These tests cover the half that opens them as a set.
"""
import re
import shutil
import sys
import pathlib
import webbrowser

import pytest

base = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
sys.path.insert(0, str(base / "scripts"))
sys.path.insert(0, str(base / "assets"))
import charts as c  # noqa: E402
import palette as p  # noqa: E402

ALLOC = [("AAPL", 30.0), ("MSFT", 25.0), ("VTI", 20.0), ("CASH", 25.0)]
PL = [("AAPL", 500.0), ("MSFT", -300.0)]


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    """One run of three charts, rendered once and shared -- rendering is slow."""
    d = tmp_path_factory.mktemp("run")
    c.allocation_chart(ALLOC, d)
    c.pl_chart(PL, d, title="Unrealized P/L")
    c.correlation_chart(["A", "B"], [[1.0, 0.3], [0.3, 1.0]], d)
    return d


def panel_srcs(html):
    """iframe sources, in document order."""
    return re.findall(r'<iframe[^>]*\bsrc="([^"]+)"', html)


def test_dashboard_embeds_every_chart_rendered_in_the_run(run_dir):
    html = c.dashboard(run_dir).read_text()
    assert set(panel_srcs(html)) == {
        "allocation.html", "pl.html", "correlation.html"}


def test_dashboard_keeps_render_order_not_alphabetical(run_dir):
    """The agent renders in the order the story is told. Preserve it."""
    html = c.dashboard(run_dir).read_text()
    assert panel_srcs(html) == [
        "allocation.html", "pl.html", "correlation.html"]


def test_dashboard_titles_each_panel_with_the_callers_title(run_dir):
    """`pl_chart(title=...)` was accepted and silently dropped. Now it lands."""
    assert "Unrealized P/L" in c.dashboard(run_dir).read_text()


def test_dashboard_sizes_its_frames_so_they_cannot_collapse(run_dir):
    """An iframe defaults to ~150px and has no intrinsic height of its own."""
    html = c.dashboard(run_dir).read_text()
    assert re.search(r"iframe\s*\{[^}]*height:", html), \
        "stylesheet gives iframes no height"


def iframe_rule(html):
    m = re.search(r"iframe\s*\{([^}]*)\}", html)
    assert m, "no iframe rule in the stylesheet"
    return m.group(1)


def test_frames_match_the_charts_native_size(run_dir):
    """xy renders at a fixed design size and does NOT reflow to its container.

    Observed: a stretched frame leaves a white band (xy hardcodes a white
    body), and a narrowed one crops the x-axis label and adds scrollbars.
    """
    rule = iframe_rule(c.dashboard(run_dir).read_text())
    assert f"width: {c.PANEL_WIDTH}px" in rule
    assert "%" not in rule, "a percentage width crops or letterboxes the chart"


def test_columns_are_never_narrower_than_a_chart(run_dir):
    """Two-up only when the viewport genuinely fits two charts side by side."""
    html = c.dashboard(run_dir).read_text()
    assert f"minmax({c.PANEL_WIDTH}px" in html


def test_no_panel_is_wider_than_any_other(run_dir):
    """A chart does not grow to fill a wider panel -- xy renders at a fixed
    size -- so a spanning panel buys dead space, not a bigger chart."""
    html = c.dashboard(run_dir).read_text()
    assert len(set(re.findall(r'<figure class="([^"]*)"', html))) == 1


def test_dashboard_carries_an_as_of_stamp(run_dir):
    """Same rule as the charts: an undated financial page reads as current."""
    assert "as of" in c.dashboard(run_dir).read_text()


def test_dashboard_chrome_follows_dark_mode(run_dir):
    html = c.dashboard(run_dir, mode="dark").read_text()
    assert p.SURFACE["dark"] in html
    assert p.SURFACE["light"] not in html


def test_dashboard_finds_charts_it_did_not_render_itself(run_dir, tmp_path):
    """Charts written by an earlier process leave no registry entry behind."""
    for f in run_dir.glob("*.html"):
        if f.name != "dashboard.html":
            shutil.copy(f, tmp_path / f.name)
    html = c.dashboard(tmp_path).read_text()
    assert set(panel_srcs(html)) == {
        "allocation.html", "pl.html", "correlation.html"}


def test_dashboard_never_embeds_itself(run_dir):
    """Regenerating in place must not nest the previous dashboard."""
    c.dashboard(run_dir)
    html = c.dashboard(run_dir).read_text()   # second pass sees its own output
    assert "dashboard.html" not in panel_srcs(html)


def test_dashboard_refuses_to_render_an_empty_page(tmp_path):
    """Reporting a dashboard with nothing on it would be a lie."""
    with pytest.raises(ValueError):
        c.dashboard(tmp_path)


# Commentary. A chart shows a shape; the note says what the shape means. It
# rides in the panel, under the chart it belongs to.

def note_texts(html):
    return re.findall(r'<p class="note">(.*?)</p>', html, re.S)


def test_a_note_reaches_the_panel_of_the_chart_it_was_written_for(tmp_path):
    c.allocation_chart(ALLOC, tmp_path, note="Half the book in one theme.")
    c.pl_chart(PL, tmp_path)
    html = c.dashboard(tmp_path).read_text()
    assert note_texts(html) == ["Half the book in one theme."]


def test_a_note_survives_the_preset_wrappers(tmp_path):
    """pl_chart -> diverging_chart -> _diverging_bar -> _write is three hops."""
    c.pl_chart(PL, tmp_path, note="Gains concentrated in one position.")
    html = c.dashboard(tmp_path).read_text()
    assert "Gains concentrated in one position." in note_texts(html)


def test_a_chart_without_a_note_gets_no_empty_element(tmp_path):
    c.pl_chart(PL, tmp_path)
    assert note_texts(c.dashboard(tmp_path).read_text()) == []


def test_notes_are_escaped_so_free_text_cannot_corrupt_the_page(tmp_path):
    """Notes are prose written at runtime -- an & or a < must stay literal."""
    c.pl_chart(PL, tmp_path, note='AT&T <b>fell</b> 3%')
    html = c.dashboard(tmp_path).read_text()
    assert "AT&amp;T &lt;b&gt;fell&lt;/b&gt; 3%" in html
    assert "<b>fell</b>" not in html


def test_note_line_breaks_are_preserved(tmp_path):
    """Two short lines beat one long one under a chart, so \\n must survive."""
    c.pl_chart(PL, tmp_path, note="First line.\nSecond line.")
    html = c.dashboard(tmp_path).read_text()
    assert "First line.\nSecond line." in html
    assert re.search(r"\.note\s*\{[^}]*white-space:\s*pre-line", html), \
        "newlines in a note collapse without white-space: pre-line"


def test_re_rendering_a_chart_replaces_its_note(tmp_path):
    c.pl_chart(PL, tmp_path, note="stale reading")
    c.pl_chart(PL, tmp_path, note="revised reading")
    notes = note_texts(c.dashboard(tmp_path).read_text())
    assert notes == ["revised reading"]


def test_show_all_reports_false_when_no_viewer_is_available(run_dir, monkeypatch):
    """Same contract as show(): False means report the path, never imply delivery."""
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: False)
    assert c.show_all(run_dir) is False


def test_show_all_writes_the_dashboard_even_when_it_cannot_open_it(run_dir,
                                                                   monkeypatch):
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: False)
    c.show_all(run_dir)
    assert (run_dir / "dashboard.html").exists()
