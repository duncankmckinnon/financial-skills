---
name: rebalancing
description: Use when bringing a portfolio back to its target allocation — computing drift, deciding which trades close it, and handling tax and wash-sale considerations. Invoke when allocation has drifted or new cash needs directing.
---

# Rebalancing

Close the gap between current allocation and policy targets with the fewest
trades that do the job.

## Inputs

- Current allocation — the same read capabilities `portfolio-review` uses,
  resolved via `references/mcp-tools.md`.
- `$FINANCIAL_HOME/investment-policy.md` — targets, **tolerance bands**,
  do-not-sell list, cash floor, maximum single position, tax constraints.
- `$FINANCIAL_HOME/trade-log.md` — recent activity, for wash-sale checks.

Without a policy file this skill cannot run. Offer to create one from
`assets/investment-policy.template.md` rather than assuming targets.

## Method

### 1. Drift table

Current minus target, in percentage points, per class. **Only classes outside
their tolerance band are candidates.** A class 1pp off a 5pp band is *in policy*
— rebalancing it is churn, and churn costs spread and tax. Say explicitly which
classes are in band and therefore left alone.

### 2. Minimal trade set

Prefer, in order:

1. **Direct new cash** at underweight classes, where the cash floor allows. This
   closes drift with no sale and no tax event.
2. **Sell overweight** only where cash alone cannot close the band.

Fewer, larger trades beat many small ones. Every trade has a cost.

### 3. Tax awareness

- Flag any lot with a **short-term holding period** — selling it converts a
  long-term rate into a short-term one.
- Check the trade log and order history for **wash-sale** conflicts inside the
  policy's window (30 days by default) in both directions.
- Prefer lots that avoid both problems.
- **Where lot-level data is unavailable from the MCP, say so.** Do not assume
  FIFO, do not estimate a holding period, and do not present a tax conclusion the
  data cannot support.

### 4. The do-not-sell list is absolute

Never propose selling a listed position, for any drift, under any tolerance
breach. Rebalance around it using the remaining positions — and **say that you
did**, so the constraint's cost is visible rather than hidden.

## Handoff

Present the full picture first: the drift table, the proposed trade list
(symbol, side, quantity, estimated value), and the projected post-trade
allocation.

Then pass trades to **`trade-workflow`, one at a time.** Each gets its own
preview and its own confirmation.

**This skill must not place orders and must not batch-confirm.** A ten-position
rebalance means ten confirmations. That friction is deliberate — it is the last
checkpoint before ten real orders hit a real account.

## Charts

Via `financial-charts`:

- `drift_chart` — drift vs target, before
- `allocation_chart` — current and projected post-trade allocation

## If the broker connection is unavailable

This skill needs the `robinhood-trading` MCP server. If it is not reachable —
not configured, not authorized, or the harness has no MCP support — say so
plainly, point at `references/harness-setup.md`, and stop. Do not guess at
holdings, prices, or balances, and do not substitute figures the human
mentioned in passing for data you were unable to read.
