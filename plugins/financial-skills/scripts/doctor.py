#!/usr/bin/env python3
"""financial-skills environment doctor.

Cross-platform: macOS, Linux and Windows. Reports by default; creates nothing
unless --fix is passed, and never overwrites an existing investment policy.

    doctor.py          check and report
    doctor.py --fix    additionally create the data home, the policy file from
                       the template, and the env files

Exit 0 = ready. Exit 1 = something blocks. Exit 2 = usable but degraded
(broker-backed skills unavailable).

Run it with uv so Python is guaranteed:

    uv run python <plugin>/scripts/doctor.py
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

XY_PIN = "xy==0.0.6"

# Colour only when attached to a terminal. Captured output and older Windows
# consoles both mangle escape sequences.
_TTY = sys.stdout.isatty()


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _TTY else text


class Report:
    def __init__(self):
        self.blocked = False
        self.degraded = False

    def ok(self, msg):
        print(f"  {_c('32', 'ok')}   {msg}")

    def warn(self, msg):
        print(f"  {_c('33', 'warn')} {msg}")
        self.degraded = True

    def bad(self, msg):
        print(f"  {_c('31', 'FAIL')} {msg}")
        self.blocked = True

    @staticmethod
    def note(msg):
        print(f"       {msg}")


def resolve_root():
    env = os.environ.get("FINANCIAL_SKILLS_ROOT")
    if env:
        return pathlib.Path(env).expanduser()
    return pathlib.Path(__file__).resolve().parent.parent


def financial_home():
    env = os.environ.get("FINANCIAL_HOME")
    if env:
        return pathlib.Path(env).expanduser()
    return pathlib.Path.home() / ".financial"


SMOKE = """
import sys, pathlib
root, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, str(pathlib.Path(root) / "scripts"))
import charts as c
p = c.allocation_chart([("A", 60.0), ("B", 40.0)], out)
assert p.exists() and p.with_suffix(".png").stat().st_size > 0
"""


def check_resources(r, root):
    print("Plugin resources")
    if (root / "scripts" / "charts.py").is_file() and \
       (root / "assets" / "palette.py").is_file():
        r.ok(f"resolved root: {root}")
        return True
    r.bad(f"cannot find scripts/charts.py and assets/palette.py under {root}")
    r.note("set FINANCIAL_SKILLS_ROOT to the plugin directory")
    return False


def check_runtime(r):
    print("\nRuntime")
    uv = shutil.which("uv")
    if uv:
        r.ok(f"uv ({uv})")
    else:
        r.bad("uv not found -- required to render charts")
        r.note("install: https://docs.astral.sh/uv/getting-started/installation/")
    if shutil.which("jq"):
        r.ok("jq (development only)")
    else:
        r.warn("jq not found -- only needed to run scripts/validate.sh")
    return uv


def check_charting(r, root, uv, resources_ok):
    print("\nCharting")
    if not (uv and resources_ok):
        r.warn("skipped smoke chart -- fix the failures above first")
        return
    # Every part can check out while the chain is still broken. This is the
    # only check that proves it works end to end.
    smoke = tempfile.mkdtemp(prefix="financial-doctor-")
    try:
        proc = subprocess.run(
            [uv, "run", "--quiet", "--with", XY_PIN, "python", "-c", SMOKE,
             str(root), smoke],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            r.ok(f"end-to-end smoke chart rendered ({XY_PIN})")
        else:
            r.bad("smoke chart failed to render")
            for line in (proc.stderr or "").strip().splitlines()[-3:]:
                r.note(line)
    finally:
        shutil.rmtree(smoke, ignore_errors=True)


def check_data(r, root, home, fix):
    print(f"\nPersonal data ({home})")
    legacy = pathlib.Path.home() / ".claude" / "financial"
    if legacy.is_dir() and legacy != home:
        r.warn(f"found data at {legacy}")
        r.note("that location is deprecated -- it puts your data inside a tool's config dir")
        r.note(f"to keep using it: set FINANCIAL_HOME={legacy}")
        r.note("to move it, move the directory yourself; nothing is moved for you")

    if home.is_dir():
        r.ok(f"{home} exists")
    elif fix:
        (home / "charts").mkdir(parents=True, exist_ok=True)
        r.ok(f"created {home}")
    else:
        r.warn(f"{home} missing -- re-run with --fix to create it")

    policy = home / "investment-policy.md"
    template = root / "assets" / "investment-policy.template.md"
    if policy.is_file():
        # Never overwrite: real targets, limits and do-not-sell list live here.
        r.ok("investment policy present (left untouched)")
    elif fix and template.is_file():
        home.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, policy)
        r.ok(f"created {policy} from template")
        r.note("edit it with your targets, tolerance bands and do-not-sell list")
    else:
        r.warn("no investment policy -- drift and rebalancing are unavailable without one")
        r.note("re-run with --fix to create one from the template")


def check_broker(r, root):
    print("\nBroker connection")
    mcp = root / ".mcp.json"
    if mcp.is_file() and "robinhood-trading" in mcp.read_text():
        r.ok("robinhood-trading is declared in .mcp.json")
    else:
        r.warn(f"robinhood-trading not declared in {mcp}")
    # Authorization is an OAuth token, not readable from disk. Report the
    # limit honestly rather than showing a green check for something unverified.
    r.note("authorization state cannot be checked from here -- see references/harness-setup.md")
    r.note("retirement-planning and financial-charts work without any broker connection")


def check_env_files(r, root, home, fix):
    print("\nEnvironment files")
    sh, ps1 = home / "env.sh", home / "env.ps1"
    if fix and home.is_dir():
        sh.write_text(
            "# Written by financial-skills doctor.py -- re-run after a plugin update.\n"
            f'export FINANCIAL_SKILLS_ROOT="{root}"\n'
            f'export FINANCIAL_HOME="{home}"\n'
        )
        ps1.write_text(
            "# Written by financial-skills doctor.py -- re-run after a plugin update.\n"
            f'$env:FINANCIAL_SKILLS_ROOT = "{root}"\n'
            f'$env:FINANCIAL_HOME = "{home}"\n'
        )
        r.ok(f"wrote {sh.name} and {ps1.name}")
    elif sh.is_file() or ps1.is_file():
        r.ok("env files present")
        if sh.is_file() and str(root) not in sh.read_text():
            r.warn("env.sh records a different root -- re-run with --fix after a plugin update")
    else:
        r.warn("no env files -- re-run with --fix to record the resolved paths")


def main(argv=None):
    ap = argparse.ArgumentParser(description="financial-skills environment doctor")
    ap.add_argument("--fix", action="store_true",
                    help="create missing directories, policy and env files")
    args = ap.parse_args(argv)

    root, home = resolve_root(), financial_home()
    r = Report()

    print("financial-skills doctor\n")
    resources_ok = check_resources(r, root)
    uv = check_runtime(r)
    check_charting(r, root, uv, resources_ok)
    check_data(r, root, home, args.fix)
    check_broker(r, root)
    check_env_files(r, root, home, args.fix)

    print()
    if r.blocked:
        print("BLOCKED -- fix the FAIL items above.")
        return 1
    if r.degraded:
        print("USABLE, DEGRADED -- see warnings above.")
        return 2
    print("READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
