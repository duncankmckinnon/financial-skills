---
name: trade-workflow
description: Use when placing, previewing, or sizing any equity order. This is the only path to an executed trade — invoke it whenever a trade is contemplated, including trades proposed by rebalancing.
---

# Trade Workflow

**This is the only skill permitted to place an order.** Every other skill in the
plugin is read-only and says so. If you are not in this skill, you are not
placing a trade.

Orders may only be placed in the Robinhood **Agentic account**. Every other
account is read-only at the server — that is Robinhood's boundary, and it is
what keeps a mistake here from reaching the rest of the portfolio.

Resolve every capability below to an actual tool name via
`references/mcp-tools.md`. Never hardcode a tool name in this file.

## The sequence — six steps, in order, none skippable

### 1. Thesis

Write down why, before anything else. What is the trade, and what has to be true
for it to be a good idea? A trade with no stated reason does not proceed.

### 2. Sizing

Compute position size as a % of the portfolio and check it against:

- the policy's **maximum single position** limit
- the policy's **cash floor**
- the account's **buying power**

**Report the check, don't just perform it.** Show the number and the limit it was
measured against. If the policy file is missing, say so and ask for the limit
rather than assuming one.

### 3. Preview

Call the preview capability. **Surface every warning it returns verbatim** —
including ones that look minor, boilerplate, or already understood. Never
summarize warnings away, never filter them, never decide on the human's behalf
that a warning is unimportant. The preview exists precisely because the model is
not the right judge of that.

### 4. Confirm

Present, together in one place:

- symbol, side, quantity
- order type and limit price
- estimated cost
- **every** preview warning

Then **stop and wait.**

- **One confirmation authorizes exactly one order.** Never carry a confirmation
  across to a second trade.
- **Silence is not confirmation.** Neither is an ambiguous reply, a question, a
  change of subject, or enthusiasm about the thesis.
- A confirmation for a *different* order is not transferable.
- If **any** order parameter changes after confirmation — quantity, price, order
  type, symbol — the confirmation is void. Re-preview and re-confirm.
- Never batch-confirm a list of trades.

### 5. Place

Only after an explicit yes to step 4. One order.

### 6. Log

Append to `$FINANCIAL_HOME/trade-log.md`:

- timestamp
- symbol, side, quantity, order type, limit price
- the thesis from step 1
- the preview warnings from step 3
- resulting order id and status

The log is append-only. `rebalancing` reads it for wash-sale checks, and it is
the record of what was actually done and why.

## If something goes wrong

If the place call fails or returns an unexpected status, **report it exactly** —
including partial fills — and log it. Do not retry silently. A trade whose state
is unclear is a thing the human needs to know about immediately.

## If the broker connection is unavailable

This skill needs the `robinhood-trading` MCP server. If it is not reachable —
not configured, not authorized, or the harness has no MCP support — say so
plainly, point at `references/harness-setup.md`, and stop. Do not guess at
holdings, prices, or balances, and do not substitute figures the human
mentioned in passing for data you were unable to read.
