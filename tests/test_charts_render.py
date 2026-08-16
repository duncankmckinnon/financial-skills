import sys, pathlib, pytest
base = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
sys.path.insert(0, str(base / "scripts"))
sys.path.insert(0, str(base / "assets"))
import charts as c

ALLOC = [("AAPL", 30.0), ("MSFT", 25.0), ("VTI", 20.0), ("CASH", 25.0)]


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_allocation_chart_writes_html_and_png(tmp_path, mode):
    out = c.allocation_chart(ALLOC, tmp_path, mode=mode)
    assert out.exists() and out.stat().st_size > 0
    assert out.with_suffix(".png").exists()


def test_allocation_chart_folds_long_tail_to_eight_marks(tmp_path):
    many = [(f"S{i}", float(50 - i)) for i in range(20)]
    out = c.allocation_chart(many, tmp_path)
    assert "Other" in out.read_text()


def test_drift_chart_labels_every_bar_with_a_sign(tmp_path):
    out = c.drift_chart({"US": 70.0}, {"US": 60.0}, tmp_path)
    assert "+10.0%" in out.read_text()


# Regression guards. Annotations in a horizontal-orientation chart are
# SCREEN-oriented (x = value, y = category) while the bar marks are
# transposed. Getting this backwards puts labels off-plot, where they vanish
# from the render while still appearing in the HTML -- so asserting on the
# HTML text alone cannot catch it. Assert the coordinates instead.

def test_diverging_labels_sit_on_the_value_axis_not_the_category_axis():
    pairs = [("INTL", -20.0), ("CASH", 5.0), ("US", 10.0)]
    labels = c._diverging_bar_labels(pairs, "light", "%")
    assert [a.x for a in labels] == [-20.0, 5.0, 10.0]   # x = value
    assert [a.y for a in labels] == [0.0, 1.0, 2.0]      # y = category index


def test_allocation_labels_sit_on_the_value_axis_at_segment_midpoints():
    labels = c._allocation_labels([("A", 30.0), ("B", 10.0)], "light")
    assert [a.x for a in labels] == [15.0, 35.0]         # running midpoints
    assert all(a.y == 0.0 for a in labels)               # single category row


def test_pl_chart_uses_blue_and_red_not_green(tmp_path):
    out = c.pl_chart([("AAPL", 500.0), ("MSFT", -300.0)], tmp_path)
    text = out.read_text()
    assert "#2a78d6" in text and "#e34948" in text
    assert "#008300" not in text


def test_value_over_time_is_single_series(tmp_path):
    out = c.value_over_time_chart(["2026-01", "2026-02"], [100.0, 110.0], tmp_path)
    assert out.exists()


def test_distribution_chart_renders(tmp_path):
    out = c.distribution_chart([0.1, -0.2, 0.3, 0.05, -0.01] * 20, tmp_path)
    assert out.exists()


def test_correlation_chart_renders(tmp_path):
    out = c.correlation_chart(["A", "B"], [[1.0, 0.3], [0.3, 1.0]], tmp_path)
    assert out.exists()


def test_projection_chart_emphasises_median(tmp_path):
    out = c.projection_chart([1, 2, 3], [10.0, 20.0, 30.0],
                             {"p10": [8.0, 15.0, 22.0], "p90": [12.0, 25.0, 40.0]},
                             tmp_path)
    text = out.read_text()
    assert "#2a78d6" in text          # median in the accent hue
    assert "#c3c2b7" in text          # bands de-emphasised


def test_contributions_chart_renders(tmp_path):
    out = c.contributions_chart([1, 2, 3], [10.0, 20.0, 30.0],
                                [2.0, 6.0, 14.0], tmp_path)
    assert out.exists()


def test_renderers_reject_more_than_eight_series(tmp_path):
    with pytest.raises(ValueError):
        c.series_colors(9, "light")
