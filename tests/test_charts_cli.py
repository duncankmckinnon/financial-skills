"""charts.py as a command: a spec in, one page and its files out."""
import copy
import datetime
import json
import os
import pathlib
import subprocess
import sys

BASE = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
CHARTS = BASE / "scripts" / "charts.py"

SPEC = {
    "title": "Portfolio review",
    "sources": [{"name": "monarch", "as_of": "2026-11-22T06:00", "live": False}],
    "data": {"positions": {"rows": [
        {"symbol": "NVDA", "account": "A", "value": 600, "cost": 400},
        {"symbol": "NVDA", "account": "B", "value": 400, "cost": 500},
        {"symbol": "VTI", "account": "A", "value": 1000, "cost": 900},
    ]}},
    "charts": [
        {"id": "allocation", "form": "part_to_whole", "preset": "allocation",
         "from": "positions", "note": "Half the book is one name.",
         "steps": [{"group": {"by": "symbol", "sum": ["value"]}}],
         "label": "symbol", "value": "value"},
        {"id": "pl", "form": "diverging", "preset": "pl", "from": "positions",
         "steps": [{"group": {"by": "symbol", "sum": ["value", "cost"]}},
                   {"diff": {"a": "value", "b": "cost", "as": "pl"}}],
         "label": "symbol", "value": "pl"},
    ],
}


def run(tmp_path, spec, *args, env=None, name="spec.json"):
    path = tmp_path / name
    if spec is not None:
        path.write_text(json.dumps(spec) if not isinstance(spec, str) else spec)
    proc = subprocess.run([sys.executable, str(CHARTS), *args, str(path)],
                          capture_output=True, text=True,
                          env=dict(os.environ, **(env or {})))
    return proc


def render(tmp_path, spec, *args, env=None):
    out = tmp_path / "out"
    proc = run(tmp_path, spec, "render", "--out", str(out), *args, env=env)
    return proc, out


def test_render_writes_page_and_per_chart_files(tmp_path):
    proc, out = render(tmp_path, SPEC)
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert pathlib.Path(summary["page"]) == out / "portfolio-review.html"
    assert pathlib.Path(summary["page"]).stat().st_size > 0
    assert [c["id"] for c in summary["charts"]] == ["allocation", "pl"]
    for c in summary["charts"]:
        for kind in ("png", "svg", "csv"):
            assert pathlib.Path(c[kind]).stat().st_size > 0
            assert pathlib.Path(c[kind]).parent == out
    assert (out / "pl.csv").read_text().splitlines()[0] == "symbol,value,cost,pl"


def test_render_summary_is_one_json_object(tmp_path):
    proc, _ = render(tmp_path, SPEC)
    assert set(json.loads(proc.stdout)) == {"page", "charts", "warnings", "opened"}
    assert json.loads(proc.stdout)["opened"] is False


def test_the_page_is_self_contained_and_carries_the_spec(tmp_path):
    proc, out = render(tmp_path, SPEC)
    text = pathlib.Path(json.loads(proc.stdout)["page"]).read_text()
    assert text.count("<iframe") == 2
    assert 'download="allocation.png"' in text and 'download="spec.json"' in text
    assert "not live" in text and "Half the book is one name." in text


def test_invalid_spec_exits_two_and_writes_nothing(tmp_path):
    bad = copy.deepcopy(SPEC)
    bad["charts"][0]["form"] = "pie"
    bad["colour"] = 1
    proc, out = render(tmp_path, bad)
    assert proc.returncode == 2
    problems = json.loads(proc.stdout)["problems"]
    assert {p["path"] for p in problems} == {"colour", "charts[0].form"}
    assert not out.exists()


def test_validate_exits_zero_on_a_good_spec_and_renders_nothing(tmp_path):
    proc = run(tmp_path, SPEC, "validate")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == {"problems": []}
    assert [f.name for f in tmp_path.iterdir()] == ["spec.json"]


def test_validate_exits_two_on_a_bad_spec(tmp_path):
    bad = copy.deepcopy(SPEC); bad["mode"] = "sepia"
    assert run(tmp_path, bad, "validate").returncode == 2


def test_unreadable_spec_file_exits_two(tmp_path):
    proc = run(tmp_path, None, "render", name="absent.json")
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["problems"]
    proc = run(tmp_path, "{not json", "render")
    assert proc.returncode == 2


def test_keep_writes_under_financial_home(tmp_path):
    proc = run(tmp_path, SPEC, "render", "--keep", env={"FINANCIAL_HOME": str(tmp_path / "home")})
    assert proc.returncode == 0, proc.stderr
    page = pathlib.Path(json.loads(proc.stdout)["page"])
    assert page.parent == tmp_path / "home" / "charts" / datetime.date.today().isoformat()


def test_default_run_directory_is_temporary_not_the_financial_home(tmp_path):
    proc = run(tmp_path, SPEC, "render", env={"FINANCIAL_HOME": str(tmp_path / "home")})
    page = pathlib.Path(json.loads(proc.stdout)["page"])
    assert tmp_path not in page.parents and not (tmp_path / "home").exists()


def test_default_page_places_every_chart_full_width(tmp_path):
    proc, out = render(tmp_path, SPEC)
    text = pathlib.Path(json.loads(proc.stdout)["page"]).read_text()
    assert text.count('width="1200" height="420"') == 2


def test_a_chart_used_twice_renders_at_both_sizes(tmp_path):
    spec = copy.deepcopy(SPEC)
    spec["page"] = [{"section": "Overview", "blocks": [
        {"stat": {"label": "Total", "value": 2000, "unit": "$", "change": -1.5, "change_unit": "%"}},
        {"chart": "allocation", "width": "full", "height": "short"},
        {"chart": "allocation", "width": "half"},
        {"chart": "pl", "width": "half"},
        {"table": {"from": "positions", "columns": ["symbol", "value"], "title": "Positions"}},
        {"text": "Closing remark."}]}]
    proc, out = render(tmp_path, spec)
    assert proc.returncode == 0, proc.stderr
    text = pathlib.Path(json.loads(proc.stdout)["page"]).read_text()
    assert 'width="1200" height="260"' in text and 'width="590" height="420"' in text
    assert (out / "allocation.png").exists() and (out / "allocation-half-regular.png").exists()
    assert 'download="positions.csv"' in text and "Closing remark." in text and "$2,000" in text


def test_warnings_reach_the_summary(tmp_path):
    spec = copy.deepcopy(SPEC)
    spec["data"]["positions"]["rows"] = [{"symbol": f"S{i}", "value": 20 - i} for i in range(12)]
    spec["charts"] = [dict(spec["charts"][0], steps=[])]
    proc, _ = render(tmp_path, spec)
    assert any("folded 5 into Other" in w for w in json.loads(proc.stdout)["warnings"])


def test_faceted_chart_writes_a_file_per_panel(tmp_path):
    spec = copy.deepcopy(SPEC)
    spec["charts"] = [{"id": "by_account", "form": "magnitude", "from": "positions",
                       "facet": "account", "label": "symbol", "value": "value", "unit": "$"}]
    proc, out = render(tmp_path, spec)
    assert proc.returncode == 0, proc.stderr
    chart = json.loads(proc.stdout)["charts"][0]
    assert [pnl["name"] for pnl in chart["panels"]] == ["A", "B"]
    assert (out / "by_account-a.png").exists() and (out / "by_account-b.svg").exists()
    assert (out / "by_account.csv").exists()


def test_dark_mode_reaches_page_and_charts(tmp_path):
    proc, out = render(tmp_path, dict(SPEC, mode="dark"))
    assert "color-scheme: dark" in pathlib.Path(json.loads(proc.stdout)["page"]).read_text()


def test_data_file_is_resolved_next_to_the_spec(tmp_path):
    spec = copy.deepcopy(SPEC)
    (tmp_path / "rows.json").write_text(json.dumps(spec["data"]["positions"]["rows"]))
    spec["data"]["positions"] = {"file": "rows.json"}
    proc, _ = render(tmp_path, spec)
    assert proc.returncode == 0, proc.stderr


def test_open_reports_whether_a_viewer_launched(tmp_path):
    proc, _ = render(tmp_path, SPEC, "--open", env={"BROWSER": "true"})
    assert proc.returncode == 0, proc.stderr
    assert isinstance(json.loads(proc.stdout)["opened"], bool)


def test_no_arguments_prints_usage_and_fails():
    proc = subprocess.run([sys.executable, str(CHARTS)], capture_output=True, text=True)
    assert proc.returncode != 0 and "render" in (proc.stderr + proc.stdout)


# --- the module still locates itself, and the call API is gone ---------------

def test_scripts_locate_the_palette_without_caller_configuring_the_path():
    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(BASE / 'scripts')!r}); "
         "import chart_forms; print(chart_forms.p.POSITIVE['light'])"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "#2a78d6"


def test_the_old_call_api_is_gone():
    import charts
    for name in ("allocation_chart", "pl_chart", "drift_chart", "series_chart",
                 "dashboard", "show_all", "chart_dir"):
        assert not hasattr(charts, name), name


def test_financial_home_defaults_outside_any_harness_config_dir(monkeypatch):
    import charts
    monkeypatch.delenv("FINANCIAL_HOME", raising=False)
    home = charts.financial_home()
    assert home.name == ".financial" and ".claude" not in str(home)


def test_financial_home_honours_the_env_var(monkeypatch, tmp_path):
    import charts
    monkeypatch.setenv("FINANCIAL_HOME", str(tmp_path / "elsewhere"))
    assert charts.financial_home() == tmp_path / "elsewhere"


def test_show_refuses_a_missing_file(tmp_path):
    import charts, pytest
    with pytest.raises(FileNotFoundError):
        charts.show(tmp_path / "nope.html")


def test_the_worked_spec_in_the_reference_renders(tmp_path):
    """The documented example must be a spec that actually works."""
    import re
    doc = (BASE / "references" / "chart-spec.md").read_text()
    worked = doc.split("## A worked spec", 1)[1]
    spec = json.loads(re.search(r"```json\n(.*?)\n```", worked, re.S).group(1))
    (tmp_path / "history.json").write_text(json.dumps(
        [{"month": "2026-09", "value": 13000}, {"month": "2026-10", "value": 14500}]))
    proc, out = render(tmp_path, spec)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["warnings"] == []


def test_the_short_spec_in_the_skill_validates(tmp_path):
    import re
    doc = (BASE / "skills" / "financial-charts" / "SKILL.md").read_text()
    spec = json.loads(re.search(r"```json\n(.*?)\n```", doc, re.S).group(1))
    assert run(tmp_path, spec, "validate").returncode == 0
