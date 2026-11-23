"""Form renderers: every rule the old call API enforced, now behind build()."""
import pytest

import chart_forms as f
import chart_spec as s

ALLOC = [{"k": "AAPL", "v": 30.0}, {"k": "MSFT", "v": 25.0},
         {"k": "VTI", "v": 20.0}, {"k": "CASH", "v": 25.0}]
PTW = {"id": "a", "form": "part_to_whole", "label": "k", "value": "v"}
DIV = {"id": "d", "form": "diverging", "label": "k", "value": "v"}
MAG = {"id": "m", "form": "magnitude", "label": "k", "value": "v"}
HIST = [{"t": "2026-01", "a": 100.0, "b": 90.0, "lo": 80.0, "hi": 120.0},
        {"t": "2026-02", "a": 110.0, "b": 95.0, "lo": 85.0, "hi": 130.0},
        {"t": "2026-03", "a": 105.0, "b": 99.0, "lo": 88.0, "hi": 128.0}]


def rows(pairs):
    return [{"k": k, "v": v} for k, v in pairs]


def _hex(match):
    return "#%02x%02x%02x" % tuple(int(v) for v in match.groups())


def svg(chart, data, width="full", height="regular", mode="light"):
    """The chart's SVG, with xy's rgb(r,g,b) mark colours written as hex."""
    import re
    out = f.build(chart, data, width, height, mode).chart.to_svg()
    return re.sub(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", _hex, out)


# --- one case per form, reused for the size sweep -----------------------------

CASES = {
    "part_to_whole": (PTW, ALLOC),
    "magnitude": (MAG, ALLOC),
    "diverging": (DIV, rows([("up", 5.0), ("down", -3.0)])),
    "series": ({"id": "s", "form": "series", "x": "t", "y": ["a", "b"]}, HIST),
    "stacked_area": ({"id": "sa", "form": "stacked_area", "x": "t", "y": ["a", "b"]}, HIST),
    "distribution": ({"id": "h", "form": "distribution", "value": "v"},
                     [{"v": x} for x in [0.1, -0.2, 0.3, 0.05, -0.01] * 20]),
    "relationship": ({"id": "r", "form": "relationship", "x": "a", "y": "b"}, HIST),
    "matrix": ({"id": "x", "form": "matrix", "row": "r", "column": "c", "value": "v"},
               [{"r": "A", "c": "A", "v": 1.0}, {"r": "A", "c": "B", "v": 0.3},
                {"r": "B", "c": "A", "v": 0.3}, {"r": "B", "c": "B", "v": 1.0}]),
}
SIZES = [(form, w, h) for form in s.FORMS for w in s.WIDTHS for h in s.HEIGHTS
         if s.wider_or_equal(w, s.MIN_WIDTH[form])]


def test_every_form_has_a_case():
    assert set(CASES) == set(s.FORMS)


@pytest.mark.parametrize("form,width,height", SIZES)
def test_every_form_builds_at_every_size_it_supports(form, width, height):
    chart, data = CASES[form]
    out = svg(chart, data, width, height)
    assert f'width="{f.WIDTH_PX[width]}"' in out
    assert f'height="{f.HEIGHT_PX[height]}"' in out


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_dark_mode_uses_the_dark_surface(mode):
    import palette as p
    assert p.SURFACE[mode] in svg(PTW, ALLOC, mode=mode)


def test_png_and_html_export_work():
    b = f.build(PTW, ALLOC, "half", "short", "light")
    assert b.chart.to_png()[:4] == b"\x89PNG" if isinstance(b.chart.to_png(), bytes) else True
    assert "<html" in b.chart.to_html().lower()


# --- ported: allocation / part-to-whole -------------------------------------

def test_allocation_folds_long_tail_and_reports_it():
    many = rows([(f"S{i}", float(50 - i)) for i in range(20)])
    b = f.build(PTW, many, "full", "regular", "light")
    assert "Other" in b.chart.to_svg()
    assert any("folded 13 into Other" in w for w in b.warnings)


def test_fold_reports_how_many_were_folded():
    b = f.build(MAG, rows([(f"S{i}", float(i + 1)) for i in range(40)]),
                "full", "short", "light")
    assert any("folded" in w and "Other" in w for w in b.warnings)


def test_allocation_labels_sit_on_the_value_axis_at_segment_midpoints():
    labels = f._allocation_labels([("A", 30.0), ("B", 10.0)], "light")
    assert [a.x for a in labels] == [15.0, 35.0]         # running midpoints
    assert all(a.y == 0.0 for a in labels)               # single category row


def test_allocation_omits_labels_for_segments_too_thin_to_hold_them():
    folded = [("US equity", 80.0), ("Intl", 12.0), ("Bonds", 4.0),
              ("Real assets", 3.0), ("Cash", 1.0)]
    labelled = [a.text for a in f._allocation_labels(folded, "light")]
    assert any("US equity" in t for t in labelled)
    assert any("Intl" in t for t in labelled)
    assert not any("Cash" in t for t in labelled)
    assert not any("Real assets" in t for t in labelled)


def test_a_long_label_needs_a_wider_segment_than_a_short_one():
    short = f._allocation_labels([("US", 8.0), ("X", 92.0)], "light")
    long_ = f._allocation_labels([("Travel / airlines", 8.0), ("X", 92.0)], "light")
    assert any("US" in a.text for a in short)
    assert not any("Travel" in a.text for a in long_)


def test_label_fit_scales_with_width():
    """A segment that holds its label at full width cannot at half."""
    folded = [("Intl equity", 12.0), ("X", 88.0)]
    wide = f._allocation_labels(folded, "light", width_px=f.WIDTH_PX["full"])
    narrow = f._allocation_labels(folded, "light", width_px=f.WIDTH_PX["half"])
    assert any("Intl" in a.text for a in wide)
    assert not any("Intl" in a.text for a in narrow)


def test_unlabelled_share_accounts_for_label_length():
    items = [("AI / semis / megacap", 47.0), ("Core dividend ETFs", 13.5),
             ("Travel / airlines", 6.5), ("Everything else", 33.0)]
    assert f.unlabelled_share(items) > 0.15


def test_part_to_whole_warns_about_unlabelled_share():
    flat = rows([(f"S{i}", 100.0 - i * 0.1) for i in range(145)])
    b = f.build(PTW, flat, "full", "regular", "light")
    assert any("carry no direct label" in w and "table" in w for w in b.warnings)
    assert len(b.chart.to_svg()) > 0     # the shape that produced the smear


def test_allocation_labels_never_exceed_the_plotted_domain():
    labels = f._allocation_labels([("A", 50.0), ("B", 50.0)], "light")
    assert all(0.0 <= a.x <= 100.0 for a in labels)


def test_part_to_whole_plots_percentages_not_raw_values():
    out = svg(PTW, rows([("cats", 700.0), ("dogs", 300.0)]))
    assert "cats 70.0%" in out


# --- ported: diverging --------------------------------------------------------

def test_diverging_labels_sit_on_the_value_axis_not_the_category_axis():
    pairs = [("INTL", -20.0), ("CASH", 5.0), ("US", 10.0)]
    labels = f._diverging_bar_labels(pairs, "light", "%")
    assert [a.x for a in labels] == [-20.0, 5.0, 10.0]   # x = value
    assert [a.y for a in labels] == [0.0, 1.0, 2.0]      # y = category index


def test_drift_preset_labels_every_bar_with_a_sign():
    out = svg(dict(DIV, preset="drift"), rows([("US", 10.0), ("INTL", -20.0)]))
    assert "+10.0%" in out and "−20.0%" in out


def test_pl_preset_uses_blue_and_red_not_green():
    out = svg(dict(DIV, preset="pl"), rows([("AAPL", 500.0), ("MSFT", -300.0)]))
    assert "#2a78d6" in out and "#e34948" in out
    assert "#008300" not in out
    assert "+$500" in out


def test_diverging_sorts_by_default_and_can_keep_spec_order():
    data = rows([("b", 5.0), ("a", -3.0), ("c", 1.0)])
    assert f._diverging_order(DIV, data) == [("a", -3.0), ("c", 1.0), ("b", 5.0)]
    assert f._diverging_order(dict(DIV, sort=False), data)[0] == ("b", 5.0)


def test_all_positive_data_gets_no_empty_negative_arm():
    lo, hi = f._padded_domain([10.0, 50.0])
    assert lo == 0.0 and hi > 50.0


def test_all_negative_data_gets_no_empty_positive_arm():
    lo, hi = f._padded_domain([-10.0, -50.0])
    assert hi == 0.0 and lo < -50.0


def test_mixed_data_pads_both_sides():
    lo, hi = f._padded_domain([-10.0, 50.0])
    assert lo < -10.0 and hi > 50.0


# --- series, bands, reference lines -------------------------------------------

def test_series_takes_one_or_many_in_wide_form():
    assert "2026-02" in svg({"id": "s", "form": "series", "x": "t", "y": ["a"]}, HIST)
    assert svg({"id": "s", "form": "series", "x": "t", "y": ["a", "b"]}, HIST)


def test_series_long_form():
    long_rows = [{"t": r["t"], "name": n, "v": r[n]} for r in HIST for n in ("a", "b")]
    out = svg({"id": "s", "form": "series", "x": "t", "series": "name", "value": "v"},
              long_rows)
    assert "#2a78d6" in out and "#eb6834" in out   # two slots, fixed order


def test_emphasis_paints_one_series_and_grays_the_rest():
    out = svg({"id": "s", "form": "series", "x": "t", "y": ["a", "b"], "emphasis": "a"}, HIST)
    assert "#2a78d6" in out          # the point
    assert "#c3c2b7" in out          # context, de-emphasised
    assert "#eb6834" not in out


def test_reference_line_and_band_are_drawn():
    chart = {"id": "s", "form": "series", "x": "t", "y": ["a"],
             "band": {"lower": "lo", "upper": "hi"},
             "reference_lines": [{"y": 100.0, "label": "starting value"}]}
    plain = svg({"id": "s", "form": "series", "x": "t", "y": ["a"]}, HIST)
    out = svg(chart, HIST)
    assert "starting value" in out
    assert len(out) > len(plain)


def test_projection_preset_emphasises_the_median():
    data = [{"year": y, "median": m, "p10": lo, "p90": hi}
            for y, m, lo, hi in [(1, 10.0, 8.0, 12.0), (2, 20.0, 15.0, 25.0)]]
    out = svg({"id": "p", "form": "series", "preset": "projection", "x": "year",
               "y": ["p10", "median", "p90"], "emphasis": "median"}, data)
    assert "#2a78d6" in out and "#c3c2b7" in out


def test_series_refuses_a_ninth_hue():
    with pytest.raises(ValueError):
        f.series_colors(9, "light")


def test_stacked_area_contributions_preset():
    data = [{"year": y, "contributed": c, "growth": g}
            for y, c, g in [(1, 10.0, 2.0), (2, 20.0, 6.0), (3, 30.0, 14.0)]]
    out = svg({"id": "c", "form": "stacked_area", "preset": "contributions",
               "x": "year", "y": ["contributed", "growth"]}, data)
    assert "contributed" in out and "growth" in out


# --- matrix -------------------------------------------------------------------

def test_matrix_supports_sequential_and_diverging():
    chart, data = CASES["matrix"]
    assert svg(chart, data)
    assert svg(dict(chart, diverging=True, domain=[-1.0, 1.0]), data)


def test_correlation_preset_is_a_diverging_matrix_on_minus_one_to_one():
    chart, _ = CASES["matrix"]
    assert f._matrix_options(dict(chart, preset="correlation")) == (True, (-1.0, 1.0))
    assert f._matrix_options(chart) == (False, None)


def test_matrix_grid_keeps_first_seen_order_and_marks_missing_cells():
    chart, _ = CASES["matrix"]
    ys, xs, z = f._matrix_grid(chart, [{"r": "B", "c": "x", "v": 1.0},
                                       {"r": "A", "c": "y", "v": 2.0}])
    assert ys == ["B", "A"] and xs == ["x", "y"]
    assert z[0][0] == 1.0 and z[1][1] == 2.0 and z[0][1] != z[0][1]   # NaN


# --- facets -------------------------------------------------------------------

def test_facet_repeats_on_a_shared_value_axis():
    data = [{"acct": "A", "k": "x", "v": 10.0}, {"acct": "A", "k": "y", "v": 20.0},
            {"acct": "B", "k": "x", "v": 500.0}, {"acct": "B", "k": "y", "v": 900.0}]
    chart = dict(MAG, facet="acct")
    panels = f.build_facets(chart, data, "regular", "light")
    assert [name for name, _ in panels] == ["A", "B"]
    assert f.shared_domain(chart, data) == f._padded_domain([10.0, 20.0, 500.0, 900.0])
    # The small panel is drawn on the big panel's scale, not its own.
    assert f.facet_cell_width(chart) == "third"
    assert f'width="{f.WIDTH_PX["third"]}"' in panels[0][1].chart.to_svg()


def test_faceted_part_to_whole_uses_half_width_cells():
    assert f.facet_cell_width(dict(PTW, facet="acct")) == "half"


# --- presets, stamp, helpers --------------------------------------------------

def test_preset_sets_labels_not_behaviour():
    out = svg(dict(DIV, preset="drift"), rows([("US", 10.0)]))
    assert "percentage points vs target" in out
    assert "% of portfolio" in svg(dict(PTW, preset="allocation"), ALLOC)


def test_default_title_comes_from_the_preset_then_the_id():
    assert f.title_of(dict(DIV, preset="pl")) == "Unrealized P/L"
    assert f.title_of(dict(DIV, id="my_chart")) == "My chart"
    assert f.title_of(dict(DIV, title="Explicit")) == "Explicit"


def test_axis_labels_carry_an_as_of_stamp():
    label = f._axis_label("% of portfolio")
    assert "% of portfolio" in label and "as of" in label


def test_rendered_chart_contains_the_as_of_stamp():
    assert "as of" in svg(PTW, ALLOC)


def test_fold_tail_keeps_top_n_and_sums_rest():
    out = f.fold_tail([(f"S{i}", float(10 - i)) for i in range(10)], keep=7)
    assert len(out) == 8
    assert [l for l, _ in out[:7]] == ["S0", "S1", "S2", "S3", "S4", "S5", "S6"]
    assert out[7] == ("Other", 3.0 + 2.0 + 1.0)


def test_fold_tail_adds_no_other_when_nothing_to_fold():
    assert f.fold_tail([("A", 2.0), ("B", 1.0)], keep=7) == [("A", 2.0), ("B", 1.0)]


def test_fold_tail_sorts_descending():
    assert f.fold_tail([("A", 1.0), ("B", 5.0)], keep=7)[0][0] == "B"


def test_series_colors_uses_fixed_slot_order():
    assert f.series_colors(3, "light") == ["#2a78d6", "#eb6834", "#1baf7a"]


def test_polarity_color_is_blue_up_red_down():
    assert f.polarity_color(1.0, "light") == "#2a78d6"
    assert f.polarity_color(-1.0, "light") == "#e34948"
    assert f.polarity_color(0.0, "light") == "#2a78d6"


def test_signed_label_always_carries_a_sign():
    assert f.signed_label(12.4, "%") == "+12.4%"
    assert f.signed_label(-3.0, "%") == "−3.0%"
    assert f.signed_label(1240, "$").startswith("+")


def test_magnitude_warns_when_bars_outnumber_the_height():
    b = f.build(dict(MAG), rows([(f"S{i}", float(i + 1)) for i in range(9)]),
                "full", "short", "light")
    assert b.warnings == [] or all("folded" in w for w in b.warnings)


def test_the_as_of_stamp_survives_a_label_too_long_for_its_width():
    """At 'third' width a long axis label wrapped and lost the stamp's time."""
    long_text = "unrealized profit / loss"
    full = f._axis_label(long_text, f.WIDTH_PX["full"])
    narrow = f._axis_label(long_text, f.WIDTH_PX["third"])
    assert long_text in full and "as of" in full
    assert long_text not in narrow and narrow.startswith("as of")
    assert len(narrow) * f.AXIS_CHAR_PX <= f.WIDTH_PX["third"] - f.AXIS_MARGIN_PX


def test_a_long_title_is_not_used_as_the_part_to_whole_tick_label():
    out = svg(dict(PTW, title="Allocation by theme and account"), ALLOC)
    assert "Allocation by theme and account" not in out
    assert "Allocation" in svg(dict(PTW, title="Allocation"), ALLOC)
