# Harness-specific setup

The skills in this plugin are **harness-agnostic** — they name capabilities and
resolve paths at runtime, so they work under any agent that can load a
`SKILL.md`, run a shell command, and (for the broker-backed skills) call an MCP
server.

Everything harness-specific lives here, not in a `SKILL.md`.
`scripts/validate.sh` check 7 enforces that.

## Where things live

| Thing | Resolution |
|---|---|
| Plugin resources (`scripts/`, `assets/`, `references/`) | `$FINANCIAL_SKILLS_ROOT`, else two levels up from the skill's own directory, else `$FINANCIAL_HOME/env.sh` |
| Personal data (policy, trade log, charts) | `${FINANCIAL_HOME:-~/.financial}` |

`scripts/charts.py` is self-locating — it finds `assets/palette.py` from its own
path, so a caller only needs to know where `charts.py` is.

`scripts/doctor.sh` resolves the root once and records it in
`$FINANCIAL_HOME/env.sh`, so skills can source one file instead of each
re-deriving it.

## Claude Code

**Install:**

```
/plugin marketplace add duncankmckinnon/financial-skills
/plugin install financial-skills@financial-skills
```

Resources install to `~/.claude/plugins/cache/financial-skills/financial-skills/<sha>/`.
The `<sha>` changes on every update, so never hardcode it — re-run
`scripts/doctor.sh` after an update and it will re-resolve.

**Connect the MCP server:** the plugin ships `.mcp.json`, so installing it
registers `robinhood-trading`. Authorize with:

```
/mcp
```

**Note on data location:** earlier versions of this plugin wrote to
`~/.claude/financial/`. That was wrong — it puts your financial data inside a
tool's config directory. The default is now `~/.financial`. If you have an
existing `~/.claude/financial/`, `doctor.sh` will detect it and offer to keep
using it via `FINANCIAL_HOME` rather than splitting your data across two places.

## Other MCP-capable agents

Any agent that supports HTTP MCP servers with OAuth can use the broker-backed
skills. Register the server yourself:

```json
{
  "robinhood-trading": {
    "type": "http",
    "url": "https://agent.robinhood.com/mcp/trading"
  }
}
```

Then complete the OAuth flow however your harness does it. The skills only
require that a server named `robinhood-trading` is reachable; they resolve
capabilities to tool names via `references/mcp-tools.md`.

Point the agent at `skills/` (or copy the directory into wherever it keeps
skills) and set `FINANCIAL_SKILLS_ROOT` to the plugin directory.

## Agents with no MCP support

`retirement-planning` and `financial-charts` work with **no broker connection at
all** — they operate on numbers you supply. `portfolio-review`, `rebalancing`,
and `trade-workflow` will report that they need the `robinhood-trading` server
and stop cleanly rather than guessing at your holdings.

## Requirements in every harness

- `uv` — the only manual install. Supplies Python and fetches the charting
  dependency on demand; no virtualenv to manage.
- `xy==0.0.6` — the charting library, pinned. `uv run --with 'xy==0.0.6'`
  fetches it on first use and caches it, so the first chart render needs network
  access. Do not float the version: the horizontal-bar axis semantics this
  plugin depends on are unstable pre-1.0 (see `references/chart-recipes.md`).
- `jq` — development only, for `scripts/validate.sh`

`scripts/doctor.sh` verifies all of the above, including an end-to-end smoke
chart that proves the whole chain works rather than just its parts.
