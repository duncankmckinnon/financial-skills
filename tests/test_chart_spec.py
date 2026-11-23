"""A wrong spec must fail before anything renders, with every problem listed."""
import copy
import json

import pytest

import chart_spec as s

ROWS = [
    {"symbol": "NVDA", "account": "A", "value": 600, "cost": 400},
    {"symbol": "NVDA", "account": "B", "value": 400, "cost": 500},
    {"symbol": "VTI", "account": "A", "value": 1000, "cost": 900},
]


def good():
    return {
        "title": "Portfolio review",
        "mode": "light",
        "sources": [{"name": "robinhood", "as_of": "2026-11-22T14:05", "live": True}],
        "data": {"positions": {"rows": copy.deepcopy(ROWS)}},
        "charts": [{
            "id": "allocation", "form": "part_to_whole", "preset": "allocation",
            "title": "Allocation", "note": "Half the book is one name.",
            "from": "positions",
            "steps": [{"group": {"by": "symbol", "sum": ["value"]}}],
            "label": "symbol", "value": "value",
        }],
    }


def series_chart(**extra):
    return dict({"id": "trend", "form": "series", "from": "history",
                 "x": "month", "y": ["value"]}, **extra)


def with_history(spec):
    spec["data"]["history"] = {"rows": [
        {"month": "2026-01", "value": 10.0, "low": 8.0, "high": 12.0},
        {"month": "2026-02", "value": 11.0, "low": 9.0, "high": 13.0},
    ]}
    return spec


def paths(spec, tmp_path):
    return [p.path for p in s.validate(spec, tmp_path)]


def messages(spec, tmp_path, path):
    return " ".join(p.message for p in s.validate(spec, tmp_path) if p.path == path)


def test_good_spec_has_no_problems(tmp_path):
    assert s.validate(good(), tmp_path) == []


def test_unknown_top_level_key(tmp_path):
    spec = good(); spec["colour"] = 1
    assert paths(spec, tmp_path) == ["colour"]


def test_unknown_chart_key(tmp_path):
    spec = good(); spec["charts"][0]["y2"] = "x"
    assert paths(spec, tmp_path) == ["charts[0].y2"]


def test_unknown_form(tmp_path):
    spec = good(); spec["charts"][0]["form"] = "pie"; del spec["charts"][0]["preset"]
    assert paths(spec, tmp_path) == ["charts[0].form"]
    assert "part_to_whole" in messages(spec, tmp_path, "charts[0].form")


def test_preset_on_wrong_form(tmp_path):
    spec = good(); spec["charts"][0]["preset"] = "pl"
    assert paths(spec, tmp_path) == ["charts[0].preset"]


def test_missing_required_field(tmp_path):
    spec = good(); del spec["charts"][0]["value"]
    assert paths(spec, tmp_path) == ["charts[0].value"]


def test_field_absent_after_steps(tmp_path):
    spec = good(); spec["charts"][0]["value"] = "cost"
    assert paths(spec, tmp_path) == ["charts[0].value"]


def test_unknown_table(tmp_path):
    spec = good(); spec["charts"][0]["from"] = "nope"
    assert paths(spec, tmp_path) == ["charts[0].from"]


def test_bad_step_is_located(tmp_path):
    spec = good(); spec["charts"][0]["steps"] = [{"sort": {"by": "zz"}}]
    assert paths(spec, tmp_path) == ["charts[0].steps[0]"]


def test_duplicate_chart_id(tmp_path):
    spec = good(); spec["charts"].append(copy.deepcopy(spec["charts"][0]))
    assert paths(spec, tmp_path) == ["charts[1].id"]


def test_chart_id_must_be_a_safe_filename(tmp_path):
    spec = good(); spec["charts"][0]["id"] = "../etc"
    assert paths(spec, tmp_path) == ["charts[0].id"]


def test_page_names_unknown_chart(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation"}, {"chart": "zz"}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[1].chart"]


def test_chart_placed_in_no_block(tmp_path):
    spec = good(); spec["page"] = [{"blocks": [{"text": "hello"}]}]
    assert paths(spec, tmp_path) == ["charts[0].id"]


def test_unsupported_size(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation", "width": "third"}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[0].width"]
    assert "half" in messages(spec, tmp_path, "page[0].blocks[0].width")


def test_unknown_size_name(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation", "height": "huge"}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[0].height"]


def test_size_on_a_non_chart_block(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation"}, {"text": "x", "width": "half"}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[1].width"]


def test_block_needs_exactly_one_kind(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation", "text": "x"}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[0]"]


def test_too_many_facets(tmp_path):
    spec = good()
    spec["data"]["positions"]["rows"] = [
        {"symbol": "S", "account": f"A{i}", "value": 1} for i in range(13)]
    spec["charts"][0].update(steps=[], facet="account")
    assert paths(spec, tmp_path) == ["charts[0].facet"]
    assert "12" in messages(spec, tmp_path, "charts[0].facet")


def test_facet_on_matrix(tmp_path):
    spec = good()
    spec["charts"] = [{"id": "m", "form": "matrix", "from": "positions",
                       "row": "symbol", "column": "account", "value": "value",
                       "facet": "account"}]
    assert paths(spec, tmp_path) == ["charts[0].facet"]


def test_duplicate_labels_are_judged_within_a_facet(tmp_path):
    spec = good(); spec["charts"][0].update(steps=[], facet="account")
    assert s.validate(spec, tmp_path) == []


def test_empty_after_steps(tmp_path):
    spec = good()
    spec["charts"][0]["steps"] = [{"filter": {"field": "symbol", "equals": "ZZZ"}}]
    assert paths(spec, tmp_path) == ["charts[0].steps"]
    assert "no rows" in messages(spec, tmp_path, "charts[0].steps")


def test_null_or_missing_value(tmp_path):
    spec = good(); spec["charts"][0]["steps"] = []
    spec["data"]["positions"]["rows"] = [{"symbol": "A", "value": 1}, {"symbol": "B"},
                                         {"symbol": "C", "value": None}]
    assert paths(spec, tmp_path) == ["charts[0].value"]
    assert "row 1" in messages(spec, tmp_path, "charts[0].value")


def test_non_finite_value(tmp_path):
    spec = good(); spec["charts"][0]["steps"] = []
    spec["data"]["positions"]["rows"] = [{"symbol": "A", "value": float("nan")}]
    assert paths(spec, tmp_path) == ["charts[0].value"]


def test_negative_part_to_whole(tmp_path):
    spec = good(); spec["charts"][0]["steps"] = []
    spec["data"]["positions"]["rows"] = [{"symbol": "A", "value": 5}, {"symbol": "B", "value": -1}]
    assert paths(spec, tmp_path) == ["charts[0].value"]


def test_zero_total_part_to_whole(tmp_path):
    spec = good(); spec["charts"][0]["steps"] = []
    spec["data"]["positions"]["rows"] = [{"symbol": "A", "value": 0}, {"symbol": "B", "value": 0}]
    assert paths(spec, tmp_path) == ["charts[0].value"]


def test_duplicate_labels(tmp_path):
    spec = good(); spec["charts"][0]["steps"] = []
    assert paths(spec, tmp_path) == ["charts[0].label"]
    assert "group" in messages(spec, tmp_path, "charts[0].label")


def test_data_file_is_read_relative_to_spec(tmp_path):
    spec = with_history(good())
    (tmp_path / "history.json").write_text(json.dumps(spec["data"]["history"]["rows"]))
    spec["data"]["history"] = {"file": "history.json"}
    spec["charts"].append(series_chart())
    assert s.validate(spec, tmp_path) == []


def test_missing_data_file(tmp_path):
    spec = good(); spec["data"]["history"] = {"file": "history.json"}
    assert paths(spec, tmp_path) == ["data.history.file"]


def test_data_file_must_be_a_list_of_objects(tmp_path):
    (tmp_path / "h.json").write_text('{"not": "a list"}')
    spec = good(); spec["data"]["history"] = {"file": "h.json"}
    assert paths(spec, tmp_path) == ["data.history.file"]


def test_table_needs_exactly_one_of_rows_or_file(tmp_path):
    spec = good(); spec["data"]["positions"]["file"] = "x.json"
    assert "data.positions" in paths(spec, tmp_path)


def test_all_problems_reported_at_once(tmp_path):
    spec = good()
    spec["colour"] = 1
    spec["mode"] = "sepia"
    spec["charts"][0]["y2"] = "x"
    assert len(s.validate(spec, tmp_path)) == 3


def test_reference_line_needs_a_number(tmp_path):
    spec = with_history(good())
    spec["charts"].append(series_chart(reference_lines=[{"y": "x", "label": "avg"}]))
    assert paths(spec, tmp_path) == ["charts[1].reference_lines[0].y"]


def test_band_fields_must_exist(tmp_path):
    spec = with_history(good())
    spec["charts"].append(series_chart(band={"lower": "low", "upper": "nope"}))
    assert paths(spec, tmp_path) == ["charts[1].band.upper"]


def test_series_takes_wide_or_long_form_not_both(tmp_path):
    spec = with_history(good())
    spec["charts"].append(series_chart(series="month", value="value"))
    assert paths(spec, tmp_path) == ["charts[1].y"]


def test_more_than_eight_series_needs_emphasis(tmp_path):
    spec = good()
    spec["data"]["long"] = {"rows": [
        {"t": t, "name": f"s{i}", "v": float(i)} for t in (1, 2) for i in range(9)]}
    chart = {"id": "many", "form": "series", "from": "long",
             "x": "t", "series": "name", "value": "v"}
    spec["charts"].append(chart)
    assert paths(spec, tmp_path) == ["charts[1].series"]
    chart["emphasis"] = "s3"
    assert s.validate(spec, tmp_path) == []


def test_emphasis_must_name_a_series(tmp_path):
    spec = with_history(good())
    spec["charts"].append(series_chart(emphasis="nope"))
    assert paths(spec, tmp_path) == ["charts[1].emphasis"]


def test_stat_block_needs_label_and_numeric_value(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation"},
                                {"stat": {"label": "x", "value": "abc"}}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[1].stat.value"]


def test_table_block_columns_must_exist(tmp_path):
    spec = good()
    spec["page"] = [{"blocks": [{"chart": "allocation"},
                                {"table": {"from": "positions", "columns": ["symbol", "zz"]}}]}]
    assert paths(spec, tmp_path) == ["page[0].blocks[1].table.columns"]


def test_source_needs_a_name_and_live_is_boolean(tmp_path):
    spec = good(); spec["sources"] = [{"live": "yes"}]
    assert sorted(paths(spec, tmp_path)) == ["sources[0].live", "sources[0].name"]


def test_a_spec_that_is_not_an_object(tmp_path):
    assert [p.path for p in s.validate([1, 2], tmp_path)] == [""]


def test_charts_are_required(tmp_path):
    spec = good(); spec["charts"] = []
    assert paths(spec, tmp_path) == ["charts"]


def test_load_reports_bad_json(tmp_path):
    f = tmp_path / "spec.json"; f.write_text("{not json")
    with pytest.raises(s.SpecError):
        s.load(f)
    with pytest.raises(s.SpecError):
        s.load(tmp_path / "absent.json")


def test_chart_rows_returns_rows_after_steps(tmp_path):
    spec = good()
    rows = s.chart_rows(spec, spec["charts"][0], tmp_path)
    assert rows == [{"symbol": "NVDA", "value": 1000}, {"symbol": "VTI", "value": 1000}]


def test_presets_all_point_at_real_forms():
    assert set(s.PRESETS.values()) <= set(s.FORMS)
    assert s.MAX_FACETS == 12
