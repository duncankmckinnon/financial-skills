# Robinhood MCP tool reference

Server: `robinhood-trading` (http, `https://agent.robinhood.com/mcp/trading`)
Enumerated: **NOT YET — see "Pending verification" below.**

**This is the only file in the plugin that names MCP tools.** Skills describe
capabilities in prose and point here. Correcting a name is a one-file edit, and
`scripts/validate.sh` check 6 fails the build if a `SKILL.md` hardcodes one.

## Boundaries (from Robinhood's agentic-trading documentation)

- **All accounts are READ-ONLY at the server except the dedicated Agentic
  account.** This is Robinhood's boundary, not ours, and it is the primary
  safety guarantee. Nothing in this plugin can widen it.
- **Equities only** at launch. Options and other asset classes are stated as
  coming later in the beta.
- **Order placement requires the preview → place pair.** Preview surfaces
  warnings; place executes.
- Read access covers positions, balances, portfolio value, order and
  transaction history, and watchlists across all accounts.

## Pending verification

The exact tool names and input schemas require completing the server's OAuth
flow, which needs an interactive session. Until that is done:

1. Authorize `robinhood-trading` interactively — the flow is harness-specific,
   see `references/harness-setup.md`.
2. Enumerate the exposed tools and their input schemas.
3. Replace the table below with the real names, arguments, and return shapes,
   set every `Verified` cell to `yes`, and fill in the `Enumerated:` date above.

**Do not guess a name to unblock a skill.** A wrong tool name fails loudly at
call time, which is the correct outcome; an invented one that happens to exist
is far worse.

## Capabilities

`Verified: docs` means the name appears in Robinhood's published documentation
but has not been confirmed against the live server. `Verified: no` means the
capability is documented to exist but its tool name is unknown.

`Verified: live` means the name was observed against the authorized server.
`docs` means it appears in Robinhood's published documentation but has not been
confirmed live. `no` means the capability is documented to exist but its tool
name is still unknown.

| Capability | Tool name | Verified |
|---|---|---|
| List accounts | `get_accounts` | live |
| Portfolio value and balances | `get_portfolio` | live |
| Equity positions across accounts | `get_equity_positions` | live |
| Live equity quotes | `get_equity_quotes` | live |
| Preview an equity order, returning warnings and estimated cost | `review_equity_order` | docs |
| Place an equity order (Agentic account only) | `place_equity_order` | docs |
| Order history | unknown | no |
| Transaction history | unknown | no |
| Symbol search | unknown | no |
| Tradability check | unknown | no |
| Popular / trending lists | unknown | no |
| Watchlist read / write | unknown | no |

**This list is partial.** The four `live` names were observed during a real
portfolio review on 2026-08-15; the server exposes more than these. The `docs`
rows are the two order tools, and they are the ones it matters most to confirm
before `trade-workflow` is used against a funded Agentic account — a wrong name
fails loudly, which is correct, but it should be confirmed rather than assumed.

To finish: authorize the server, enumerate the full tool list with input
schemas, replace the `no` rows, and promote the `docs` rows to `live`.

## Usage rules for skills

- Only `trade-workflow` may call the preview or place capabilities. Every other
  skill is read-only and says so in its own text.
- Preview warnings are surfaced **verbatim** to the human, never summarized away.
- One human confirmation authorizes exactly one placed order.
- Where a read capability returns less than a skill needs — lot-level cost basis
  is the known example — the skill reports the gap rather than estimating.
