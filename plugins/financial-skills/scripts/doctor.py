#!/usr/bin/env python3
"""financial-skills environment doctor.

Cross-platform: macOS, Linux and Windows. Reports by default; creates nothing
unless --fix is passed, and never overwrites an existing investment policy or
sources declaration.

    doctor.py          check and report
    doctor.py --fix    additionally create the data home, the policy file from
                       the template, the sources declaration, and the env files

Exit 0 = ready. Exit 1 = something blocks. Exit 2 = usable but degraded
(some skills unavailable).

Run it with uv so Python is guaranteed:

    uv run python <plugin>/scripts/doctor.py
"""
import argparse
import os
import pathlib
import re
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


_ROLE = re.compile(r"^Role:\s*(trading|read-only)\s*$")


def source_roles(dirs):
    """Map each source name (file stem) under `dirs` to its declared role.

    The role is None when a file has no valid `Role:` line in its first ten
    lines. `_template.md` is a skeleton, not a source, and is skipped.
    """
    roles = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if f.name.startswith("_"):
                continue
            role = None
            try:
                head = f.read_text(errors="replace").splitlines()[:10]
            except OSError:
                head = []
            for line in head:
                m = _ROLE.match(line)
                if m:
                    role = m.group(1)
                    break
            roles[f.stem] = role
    return roles


def check_sources(r, root, home, fix):
    print("\nSources")
    shipped = source_roles([root / "references" / "sources"])
    user = source_roles([home / "sources"])
    mcp = root / ".mcp.json"
    declared = mcp.read_text() if mcp.is_file() else ""

    trading = []
    for name, role, mine in [(n, v, False) for n, v in shipped.items()] + \
                            [(n, v, True) for n, v in user.items()]:
        if role is None:
            r.warn(f"{name} has no valid Role line")
            r.note("add 'Role: read-only' or 'Role: trading' near the top of its file")
            continue
        r.ok(f"{name} ({role}{', user-defined' if mine else ''})")
        if name in declared:
            r.note("declared by the plugin in .mcp.json")
        else:
            r.note("connect it through your agent -- see references/harness-setup.md")
        if role == "trading":
            trading.append(name)

    if not shipped and not user:
        r.warn("no source files found -- the data-backed skills have nothing to read")
    if len(trading) > 1:
        r.warn(f"more than one source declares the trading role: {', '.join(trading)}")
    elif not trading:
        r.note("no source declares the trading role -- order placement is unavailable, "
               "everything else works")

    declaration = home / "sources.md"
    template = root / "assets" / "sources.template.md"
    if declaration.is_file():
        # Never overwrite: this is the human's account-to-source mapping.
        r.ok("sources.md present (left untouched)")
    elif fix and template.is_file() and home.is_dir():
        shutil.copyfile(template, declaration)
        r.ok(f"created {declaration} from template")
        r.note("list your sources and assign each account to exactly one")
    else:
        r.note("no sources.md -- skills adapt to whichever sources are connected")

    # Authorization is an OAuth token, not readable from disk. Report the
    # limit honestly rather than showing a green check for something unverified.
    r.note("authorization state cannot be checked from here -- see references/harness-setup.md")
    r.note("retirement-planning and financial-charts work without any source connected")


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
    check_sources(r, root, home, args.fix)
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
