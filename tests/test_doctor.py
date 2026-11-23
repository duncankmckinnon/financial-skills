"""Tests for scripts/doctor.py.

The critical one is that --fix never clobbers an existing investment policy:
that file holds real targets, limits and a do-not-sell list.
"""
import subprocess, sys, pathlib, os, pytest

BASE = pathlib.Path(__file__).parent.parent / "plugins/financial-skills"
DOCTOR = BASE / "scripts" / "doctor.py"


def run(home, *args, root=None):
    env = dict(os.environ, FINANCIAL_HOME=str(home))
    if root is not None:
        env["FINANCIAL_SKILLS_ROOT"] = str(root)
    return subprocess.run([sys.executable, str(DOCTOR), *args],
                          capture_output=True, text=True, env=env)


def test_report_only_mode_creates_nothing(tmp_path):
    home = tmp_path / "report_only"
    run(home)
    assert not home.exists()


def test_fix_creates_home_policy_and_env_files(tmp_path):
    home = tmp_path / "fixed"
    run(home, "--fix")
    assert (home / "investment-policy.md").is_file()
    assert (home / "env.sh").is_file()
    assert "FINANCIAL_SKILLS_ROOT" in (home / "env.sh").read_text()


def test_fix_writes_a_powershell_env_file_too(tmp_path):
    """Windows users cannot source env.sh."""
    home = tmp_path / "ps"
    run(home, "--fix")
    ps = home / "env.ps1"
    assert ps.is_file()
    assert "$env:FINANCIAL_SKILLS_ROOT" in ps.read_text()


def test_fix_never_overwrites_an_existing_policy(tmp_path):
    home = tmp_path / "existing"
    home.mkdir()
    policy = home / "investment-policy.md"
    policy.write_text("MY REAL TARGETS - DO NOT CLOBBER\n")
    before = policy.read_text()
    run(home, "--fix")
    assert policy.read_text() == before


def test_a_fully_set_up_environment_exits_zero(tmp_path):
    home = tmp_path / "ready"
    run(home, "--fix")
    assert run(home).returncode == 0


def test_an_unresolvable_root_is_blocking(tmp_path):
    r = run(tmp_path / "x", root=tmp_path / "nonexistent")
    assert r.returncode == 1


def test_a_degraded_environment_exits_two(tmp_path):
    """Usable, but missing the policy that unlocks drift and rebalancing."""
    assert run(tmp_path / "degraded").returncode == 2


def test_output_is_plain_when_not_a_terminal(tmp_path):
    """Captured output must not carry ANSI escapes -- Windows consoles and
    CI logs both mangle them."""
    r = run(tmp_path / "plain", "--fix")
    assert "\033[" not in r.stdout


# --- sources -----------------------------------------------------------------

import shutil


@pytest.fixture
def plugin_copy(tmp_path):
    """A private copy of the plugin, for tests that alter shipped files."""
    dst = tmp_path / "plugin"
    shutil.copytree(BASE, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def test_sources_section_lists_both_shipped_sources(tmp_path):
    out = run(tmp_path / "h").stdout
    assert "robinhood (trading)" in out
    assert "monarch (read-only)" in out


def test_fix_creates_the_sources_declaration(tmp_path):
    home = tmp_path / "h"
    run(home, "--fix")
    assert (home / "sources.md").is_file()


def test_fix_never_overwrites_an_existing_declaration(tmp_path):
    home = tmp_path / "h"
    home.mkdir()
    f = home / "sources.md"
    f.write_text("MY ACCOUNTS\n")
    run(home, "--fix")
    assert f.read_text() == "MY ACCOUNTS\n"


def test_a_missing_declaration_is_not_a_warning(tmp_path):
    home = tmp_path / "h"
    run(home, "--fix")
    (home / "sources.md").unlink()
    r = run(home)
    assert r.returncode == 0
    assert "no sources.md -- skills adapt to whichever sources are connected" in r.stdout


def test_a_user_defined_source_is_listed(tmp_path):
    home = tmp_path / "h"
    (home / "sources").mkdir(parents=True)
    (home / "sources" / "mybank.md").write_text("# My bank\nRole: read-only\n")
    assert "mybank (read-only, user-defined)" in run(home).stdout


def test_a_source_file_without_a_role_warns_and_does_not_crash(tmp_path):
    home = tmp_path / "h"
    (home / "sources").mkdir(parents=True)
    (home / "sources" / "broken.md").write_text("# no role here\n")
    r = run(home)
    assert "broken has no valid Role line" in r.stdout
    assert "Traceback" not in r.stderr


def test_two_trading_sources_warn(tmp_path):
    home = tmp_path / "h"
    (home / "sources").mkdir(parents=True)
    (home / "sources" / "other.md").write_text("Role: trading\n")
    assert "more than one source declares the trading role" in run(home).stdout


def test_no_trading_source_is_a_note_not_a_warning(tmp_path, plugin_copy):
    (plugin_copy / "references/sources/robinhood.md").unlink()
    home = tmp_path / "h"
    run(home, "--fix", root=plugin_copy)
    r = run(home, root=plugin_copy)
    assert "no source declares the trading role" in r.stdout
    assert r.returncode == 0


def test_the_template_is_not_listed_as_a_source(tmp_path):
    # Match the listing form: tmp_path itself contains this test's name.
    assert "_template (" not in run(tmp_path / "h").stdout
    assert "_template has no" not in run(tmp_path / "h").stdout
