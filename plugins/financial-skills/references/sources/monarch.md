# Monarch Money

Role: read-only

Tool names below were observed in the server's own tool listing on 2026-11-22.
They were read from the listing, not exercised by a call.

## Connection

Monarch Money's own MCP server, authorized with OAuth. The plugin does not
declare it in `.mcp.json`; the human connects it through their harness — see
`references/harness-setup.md`.

## Boundaries

- **Monarch is an aggregator.** It reports accounts held at other
  institutions, and that can include the very accounts the trading source
  reports. Never add an account from here to the same account read elsewhere —
  see "Combining sources" in `references/sources.md`.
- Every data call takes an `intent`. Use `investment_tracking` for holdings
  and balances, and the closest listed category otherwise. Never put personal
  details or circumstances in `intent_description`.
- No order capability of any kind.

## Freshness

Synced from each institution on Monarch's schedule, **not live**. Treat every
value as synced and mark it so. Holdings are current-only: the source cannot
show what was held on a past date.

## Capabilities

| Capability | Tool name | Verified |
|---|---|---|
| accounts | `GetAccounts` | live |
| balances | `GetAccounts` | live |
| positions | `GetInvestments` | live |
| quotes | none | no |
| tax lots | none | no |
| order history | none | no |
| transactions | `GetTransactions` | live |
| order preview | none | no |
| order place | none | no |

## Gaps

- No quotes. Position values are Monarch's synced values.
- No lot-level cost basis. Scope any profit/loss claim to what the positions
  capability returns, and say when cost basis is absent.
- No order history. A wash-sale check can use transactions, and must say that
  it did.
- Some holdings carry no ticker (employer-plan funds, manually tracked
  accounts) and cannot be matched to a live quote from another source.

## Tools no skill may call

Monarch also exposes tools that create, update, delete, move or allocate:
budgets, transactions and their splits, goals, rules, categories, merchants,
tags, account debt details and balance history. They are outside the
capability list. **No skill in this plugin may call any of them.** This source
is read-only to the plugin even though the server itself is not.
