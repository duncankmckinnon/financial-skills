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


# A segment narrower than its own label has nowhere to put the text: the
# labels collide into an unreadable smear and the last one runs off the plot.
# Real portfolios hit this constantly -- one dominant class beside a thin tail.

def test_allocation_omits_labels_for_segments_too_thin_to_hold_them():
    folded = [("US equity", 80.0), ("Intl", 12.0), ("Bonds", 4.0),
              ("Real assets", 3.0), ("Cash", 1.0)]
    labels = c._allocation_labels(folded, "light")
    labelled = [a.text for a in labels]
    assert any("US equity" in t for t in labelled)
    assert any("Intl" in t for t in labelled)
    assert not any("Cash" in t for t in labelled)        # 1% cannot hold a label
    assert not any("Real assets" in t for t in labelled)  # 3% cannot either


def test_a_long_label_needs_a_wider_segment_than_a_short_one():
    """A 6.5% segment held a 22-char label and collided with its neighbour."""
    short = c._allocation_labels([("US", 8.0), ("X", 92.0)], "light")
    long_ = c._allocation_labels([("Travel / airlines", 8.0), ("X", 92.0)], "light")
    assert any("US" in a.text for a in short)
    assert not any("Travel" in a.text for a in long_)


def test_unlabelled_share_accounts_for_label_length():
    items = [("AI / semis / megacap", 47.0), ("Core dividend ETFs", 13.5),
             ("Travel / airlines", 6.5), ("Everything else", 33.0)]
    assert c.unlabelled_share(items) > 0.15   # the two long-labelled ones


def test_allocation_labels_never_exceed_the_plotted_domain():
    folded = [("A", 50.0), ("B", 50.0)]
    labels = c._allocation_labels(folded, "light")
    total = 100.0
    assert all(0.0 <= a.x <= total for a in labels)


def test_allocation_chart_survives_a_flat_many_position_portfolio(tmp_path):
    """145 near-equal positions: the shape that produced the smear."""
    flat = [(f"S{i}", 100.0 - i * 0.1) for i in range(145)]
    out = c.allocation_chart(flat, tmp_path)
    assert out.exists() and out.with_suffix(".png").stat().st_size > 0


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
