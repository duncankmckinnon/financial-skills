import sys, subprocess, pathlib, pytest
base = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
# Deliberately do NOT add assets/ to the path: charts.py must locate palette.py
# itself, so a caller under any harness only needs to know where charts.py is.
sys.path.insert(0, str(base / "scripts"))
import charts as c


def test_charts_locates_palette_without_caller_configuring_the_path():
    """A caller that knows only scripts/ must still get a working module."""
    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(base / 'scripts')!r}); "
         "import charts; print(charts.p.POSITIVE['light'])"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "#2a78d6"


def test_financial_home_defaults_outside_any_harness_config_dir(monkeypatch):
    monkeypatch.delenv("FINANCIAL_HOME", raising=False)
    home = c.financial_home()
    assert home.name == ".financial"
    assert ".claude" not in str(home)


def test_financial_home_honours_the_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCIAL_HOME", str(tmp_path / "elsewhere"))
    assert c.financial_home() == tmp_path / "elsewhere"


def test_chart_dir_is_dated_under_the_financial_home(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCIAL_HOME", str(tmp_path))
    d = c.chart_dir()
    assert d.parent == tmp_path / "charts"
    assert len(d.name) == 10 and d.name.count("-") == 2  # YYYY-MM-DD


def test_fold_tail_keeps_top_n_and_sums_rest():
    items = [(f"S{i}", float(10 - i)) for i in range(10)]
    out = c.fold_tail(items, keep=7)
    assert len(out) == 8
    assert [l for l, _ in out[:7]] == ["S0", "S1", "S2", "S3", "S4", "S5", "S6"]
    assert out[7] == ("Other", 3.0 + 2.0 + 1.0)


def test_fold_tail_adds_no_other_when_nothing_to_fold():
    out = c.fold_tail([("A", 2.0), ("B", 1.0)], keep=7)
    assert out == [("A", 2.0), ("B", 1.0)]
    assert "Other" not in [l for l, _ in out]


def test_fold_tail_sorts_descending():
    out = c.fold_tail([("A", 1.0), ("B", 5.0)], keep=7)
    assert out[0][0] == "B"


def test_compute_drift_covers_union_and_sorts_most_negative_first():
    out = c.compute_drift({"US": 70.0, "CASH": 5.0}, {"US": 60.0, "INTL": 20.0})
    assert dict(out) == {"US": 10.0, "CASH": 5.0, "INTL": -20.0}
    assert out[0][0] == "INTL"


def test_series_colors_uses_fixed_slot_order():
    assert c.series_colors(3, "light") == ["#2a78d6", "#eb6834", "#1baf7a"]


def test_series_colors_refuses_to_generate_a_ninth_hue():
    with pytest.raises(ValueError):
        c.series_colors(9, "light")


def test_polarity_color_is_blue_up_red_down():
    assert c.polarity_color(1.0, "light") == "#2a78d6"
    assert c.polarity_color(-1.0, "light") == "#e34948"
    assert c.polarity_color(0.0, "light") == "#2a78d6"


def test_signed_label_always_carries_a_sign():
    assert c.signed_label(12.4, "%") == "+12.4%"
    assert c.signed_label(-3.0, "%") == "−3.0%"
    assert c.signed_label(1240, "$").startswith("+")
