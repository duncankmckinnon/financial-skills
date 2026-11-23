"""Declarative data steps: the shaping an agent used to do by hand."""
import pytest

import chart_data as d

ROWS = [
    {"symbol": "NVDA", "account": "A", "value": 600, "cost": 400},
    {"symbol": "NVDA", "account": "B", "value": 400, "cost": 500},
    {"symbol": "VTI", "account": "A", "value": 1000, "cost": 900},
]


def test_no_steps_returns_a_copy():
    out = d.apply_steps(ROWS, [])
    assert out == ROWS and out is not ROWS and out[0] is not ROWS[0]


def test_filter_equals_and_in():
    assert len(d.apply_steps(ROWS, [{"filter": {"field": "account", "equals": "A"}}])) == 2
    assert len(d.apply_steps(ROWS, [{"filter": {"field": "symbol", "in": ["VTI"]}}])) == 1


def test_group_sums_and_keeps_first_seen_order():
    out = d.apply_steps(ROWS, [{"group": {"by": "symbol", "sum": ["value", "cost"]}}])
    assert out == [{"symbol": "NVDA", "value": 1000, "cost": 900},
                   {"symbol": "VTI", "value": 1000, "cost": 900}]


def test_group_by_two_fields_mean_and_count():
    out = d.apply_steps(ROWS, [{"group": {"by": ["symbol", "account"], "count": ["value"]}}])
    assert len(out) == 3 and out[0]["value"] == 1
    out = d.apply_steps(ROWS, [{"group": {"by": "symbol", "mean": ["value"]}}])
    assert out[0]["value"] == 500


def test_share_is_percent_of_column_total():
    out = d.apply_steps(ROWS, [{"group": {"by": "symbol", "sum": ["value"]}},
                               {"share": {"of": "value", "as": "pct"}}])
    assert [r["pct"] for r in out] == [50.0, 50.0]


def test_diff_sort_top():
    out = d.apply_steps(ROWS, [{"diff": {"a": "value", "b": "cost", "as": "pl"}},
                               {"sort": {"by": "pl", "desc": True}},
                               {"top": {"n": 2, "by": "pl"}}])
    assert [r["pl"] for r in out] == [200, 100]


def test_top_keeps_the_largest_whatever_the_incoming_order():
    out = d.apply_steps(ROWS, [{"top": {"n": 1, "by": "value"}}])
    assert out[0]["symbol"] == "VTI"


def test_input_is_not_mutated():
    before = [dict(r) for r in ROWS]
    d.apply_steps(ROWS, [{"diff": {"a": "value", "b": "cost", "as": "pl"}}])
    assert ROWS == before


@pytest.mark.parametrize("steps,index", [
    ([{"nope": {}}], 0),
    ([{"filter": {"field": "account", "equals": "A"}}, {"sort": {"by": "missing"}}], 1),
    ([{"share": {"of": "symbol", "as": "pct"}}], 0),           # non-numeric
    ([{"filter": {"field": "account"}}], 0),                   # neither equals nor in
    ([{"filter": {"field": "a", "equals": 1}, "sort": {"by": "a"}}], 0),  # two keys
    ([{"group": {"by": "symbol"}}], 0),                        # no aggregate
    ([{"group": {"by": "symbol", "sum": ["value"], "extra": 1}}], 0),     # unknown key
    ([{"top": {"n": 0, "by": "value"}}], 0),
    (["sort"], 0),                                             # not an object
    ([{"diff": {"a": "value", "b": "symbol", "as": "x"}}], 0),  # non-numeric operand
])
def test_bad_steps_raise_with_the_step_index(steps, index):
    with pytest.raises(d.StepError) as e:
        d.apply_steps(ROWS, steps)
    assert e.value.index == index


def test_share_of_a_zero_total_raises():
    with pytest.raises(d.StepError):
        d.apply_steps([{"v": 0}], [{"share": {"of": "v", "as": "p"}}])


def test_booleans_are_not_numbers():
    with pytest.raises(d.StepError):
        d.apply_steps([{"v": True}], [{"share": {"of": "v", "as": "p"}}])
