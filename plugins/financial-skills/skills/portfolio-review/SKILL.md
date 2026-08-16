---
name: portfolio-review
description: Use when reviewing current holdings — what is held, how concentrated it is, sector and asset-class exposure, unrealized profit and loss, and drift from target allocation. Read-only; invoke this before any rebalancing or trading decision.
---

# Portfolio Review

Understand what is currently held and how it is exposed. This is the safest
starting point and the one to reach for first.

## This skill is read-only by construction

It **must not place** an order, preview an order, or modify a watchlist. Order
placement belongs to `trade-workflow` alone. If a review surfaces something that
warrants a trade, say so and hand off — do not act.

## Data

Read capabilities needed: positions, balances and buying power, live quotes,
and order history. **Resolve these to actual tool names via
`references/mcp-tools.md`** — never hardcode a tool name here.

Note the server's boundary: all accounts are readable; only the dedicated
Agentic account is writable. Reviewing every account is expected and safe.

Read the policy file at `$FINANCIAL_HOME/investment-policy.md` if it exists.

## Analyses

1. **Allocation** — by position and by asset class, as % of total portfolio value.
2. **Concentration** — largest positions as % of portfolio, flagged against the
   policy's maximum single-position limit. Name the number and the limit, not
   just "concentrated".
3. **Exposure** — sector and asset-class breakdown. Call out where several
   holdings load on the same exposure, since that concentration is invisible in
   a position-by-position view.
4. **Unrealized P/L** — per position, with the sign always shown.
5. **Drift** — current allocation minus policy target, in percentage points.
   Mark which classes are outside their tolerance band; those are the only
   rebalancing candidates.

## When the policy file is missing

Report everything computable without it (allocation, concentration, exposure,
P/L), then name the analyses that need a policy — drift, tolerance breaches, and
position-limit checks. Offer to create one from
`assets/investment-policy.template.md`.

**Never invent targets.** A drift number against a guessed target is worse than
no drift number.

## When the data is incomplete

Where lot-level cost basis is unavailable from the MCP, say so plainly and scope
the P/L claim to what the data supports. Do not estimate silently, and do not let
a confident tone paper over a gap. The same applies to any holding the server
does not return.

## Charts

Hand off to `financial-charts` — do not write chart code here:

- `allocation_chart` — allocation by position, top 7 + "Other"
- `drift_chart` — drift vs target, if a policy exists
- `pl_chart` — unrealized P/L per position

## Output

Lead with the two or three things that actually matter — a breached position
limit, a large drift, a concentrated exposure — then the supporting detail.
State assumptions. This is decision support, not advice.

## If the broker connection is unavailable

This skill needs the `robinhood-trading` MCP server. If it is not reachable —
not configured, not authorized, or the harness has no MCP support — say so
plainly, point at `references/harness-setup.md`, and stop. Do not guess at
holdings, prices, or balances, and do not substitute figures the human
mentioned in passing for data you were unable to read.
