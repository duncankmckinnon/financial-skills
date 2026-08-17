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
