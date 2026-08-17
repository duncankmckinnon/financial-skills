import sys, pathlib, pytest
base = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
sys.path.insert(0, str(base / "scripts"))
import charts as c


# --- ephemeral output -------------------------------------------------------

def test_chart_dir_is_ephemeral_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCIAL_HOME", str(tmp_path))
    c._reset_scratch()
    d = c.chart_dir()
    assert tmp_path not in d.parents          # not archived under the data home
    assert "charts" not in str(d.parent.name) or d.parent != tmp_path / "charts"


def test_chart_dir_is_stable_within_a_run():
    c._reset_scratch()
    assert c.chart_dir() == c.chart_dir()     # a batch lands in one directory


def test_chart_dir_keep_archives_under_the_financial_home(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCIAL_HOME", str(tmp_path))
    d = c.chart_dir(keep=True)
    assert d.parent == tmp_path / "charts"
    assert len(d.name) == 10 and d.name.count("-") == 2   # YYYY-MM-DD


# --- as-of stamp ------------------------------------------------------------

def test_axis_labels_carry_an_as_of_stamp():
    label = c._axis_label("% of portfolio")
    assert "% of portfolio" in label
    assert "as of" in label


def test_rendered_chart_contains_the_as_of_stamp(tmp_path):
    out = c.allocation_chart([("A", 60.0), ("B", 40.0)], tmp_path)
    assert "as of" in out.read_text()


# --- generic renderers ------------------------------------------------------

def test_magnitude_chart_renders_arbitrary_categories(tmp_path):
    out = c.magnitude_chart([("alpha", 12.0), ("beta", 30.0), ("gamma", 4.0)],
                            tmp_path, title="Anything at all", unit="")
    assert out.exists() and out.with_suffix(".png").stat().st_size > 0


def test_series_chart_takes_one_or_many_series(tmp_path):
    one = c.series_chart([1, 2, 3], {"only": [4.0, 5.0, 6.0]}, tmp_path)
    assert one.exists()
    many = c.series_chart([1, 2, 3],
                          {"a": [1.0, 2.0, 3.0], "b": [3.0, 2.0, 1.0]}, tmp_path)
    assert many.exists()


def test_series_chart_refuses_to_generate_a_ninth_hue(tmp_path):
    nine = {f"s{i}": [1.0, 2.0] for i in range(9)}
    with pytest.raises(ValueError):
        c.series_chart([1, 2], nine, tmp_path)


def test_part_to_whole_chart_works_on_non_financial_data(tmp_path):
    out = c.part_to_whole_chart([("cats", 7.0), ("dogs", 3.0)], tmp_path,
                                title="Pets")
    assert out.exists()


def test_diverging_chart_is_generic(tmp_path):
    out = c.diverging_chart([("up", 5.0), ("down", -3.0)], tmp_path,
                            unit="", axis_label="change")
    assert out.exists()
    text = out.read_text()
    assert "#2a78d6" in text and "#e34948" in text   # blue up, red down


def test_all_positive_data_gets_no_empty_negative_arm():
    """An empty negative arm halves the width and implies losses that aren't there."""
    lo, hi = c._padded_domain([10.0, 50.0])
    assert lo == 0.0 and hi > 50.0


def test_all_negative_data_gets_no_empty_positive_arm():
    lo, hi = c._padded_domain([-10.0, -50.0])
    assert hi == 0.0 and lo < -50.0


def test_mixed_data_pads_both_sides():
    lo, hi = c._padded_domain([-10.0, 50.0])
    assert lo < -10.0 and hi > 50.0


def test_relationship_chart_renders(tmp_path):
    out = c.relationship_chart([1.0, 2.0, 3.0], [2.0, 4.0, 5.0], tmp_path,
                               x_label="x", y_label="y")
    assert out.exists()


def test_matrix_chart_supports_sequential_and_diverging(tmp_path):
    seq = c.matrix_chart(["a", "b"], [[1.0, 2.0], [2.0, 1.0]], tmp_path,
                         diverging=False)
    assert seq.exists()
    div = c.matrix_chart(["a", "b"], [[1.0, -1.0], [-1.0, 1.0]], tmp_path,
                         diverging=True, domain=(-1.0, 1.0))
    assert div.exists()


def test_financial_presets_still_work(tmp_path):
    assert c.allocation_chart([("A", 1.0)], tmp_path).exists()
    assert c.pl_chart([("A", 1.0), ("B", -1.0)], tmp_path).exists()
    assert c.drift_chart({"A": 10.0}, {"A": 5.0}, tmp_path).exists()
