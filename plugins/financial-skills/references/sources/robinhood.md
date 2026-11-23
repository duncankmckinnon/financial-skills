# Robinhood

Role: trading

Tool names below were observed in the server's own tool listing on 2026-11-22.
They were read from the listing, not exercised by a call.

## Connection

Server `robinhood-trading` (http, `https://agent.robinhood.com/mcp/trading`),
declared in the plugin's `.mcp.json`. Authorization is an OAuth flow and is
harness-specific — see `references/harness-setup.md`.

## Boundaries

- **All accounts are READ-ONLY at the server except the dedicated Agentic
  account.** This is Robinhood's boundary, not ours, and it is the primary
  safety guarantee. Nothing in this plugin can widen it. The accounts
  capability flags the one writable account as `agentic_allowed`.
- **Order placement requires the preview → place pair.** Preview surfaces
  warnings; place executes.
- **`trade-workflow`'s explicit human confirmation is required before any
  place call**, whatever the server's own tool guidance says about when a
  confirmation step may be skipped. The plugin's rule is the stricter one and
  it wins.
- Every skill in this plugin works with equities only. The server also exposes
  options, crypto and advanced orders; no skill uses them.

## Freshness

Live. Quotes and positions reflect the market at the time of the call.

## Capabilities

| Capability | Tool name | Verified |
|---|---|---|
| accounts | `get_accounts` | live |
| balances | `get_portfolio` | live |
| positions | `get_equity_positions` | live |
| quotes | `get_equity_quotes` | live |
| tax lots | `get_equity_tax_lots` | live |
| order history | `get_equity_orders` | live |
| transactions | `get_banking_transactions`, `get_credit_transactions` | live |
| order preview | `review_equity_order` | live |
| order place | `place_equity_order` | live |

## Other read tools

Outside the capability list, and safe for any skill to use:

| Purpose | Tool name | Verified |
|---|---|---|
| Symbol search | `search` | live |
| Tradability check | `get_equity_tradability` | live |
| Watchlists | `get_watchlists` | live |
| Robinhood bank accounts and their balances | `get_bank_accounts` | live |

## Gaps

- Transactions cover Robinhood bank and credit-card activity only. Brokerage
  cash activity (deposits, dividends) has no tool listed here; report it as a
  gap rather than inferring it from order history.
- Options, crypto and advanced orders are out of scope for every skill.

## Usage rules for skills

- Only `trade-workflow` may call the order preview or order place
  capabilities. Every other skill is read-only and says so in its own text.
- Preview warnings are surfaced **verbatim** to the human, never summarized
  away.
- One human confirmation authorizes exactly one placed order.
