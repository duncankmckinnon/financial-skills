---
name: retirement-planning
description: Use when projecting retirement readiness — savings rate versus goal, contribution and withdrawal projections, account-type location across 401k/IRA/taxable/HSA, and glidepath comparisons. Works without a broker connection.
---

# Retirement Planning

Long-horizon planning. This skill **works without a broker** connection and has
no MCP dependency — it is useful with nothing but numbers the human supplies.

## Inputs

From the human: current age, target retirement age, balances by account type,
annual contribution, expected retirement spending, and any known one-off events
(inheritance, home purchase, tuition).

Current portfolio value may come from the MCP if it happens to be connected, but
is **never required**. Ask for what is missing rather than stalling.

This skill **must not place** orders. It has no reason to touch an order
capability at all.

## Every projection prints its assumptions

Alongside every result, state:

- nominal return
- inflation
- contribution growth
- withdrawal rate
- time horizon

**A projection without visible assumptions is not an acceptable output.** The
number is entirely a function of these, and a reader who cannot see them cannot
judge the number.

Then say **which assumptions the result is most sensitive to** — usually return
and withdrawal rate — and what the answer looks like if each is wrong by a
plausible margin. A single point estimate presented with confidence is the main
way this kind of analysis misleads.

## Analyses

1. **Projection** — balance over time to and through retirement, across
   scenarios (conservative / central / optimistic, or percentile bands).
2. **Savings rate vs goal** — what is being saved, what the goal implies, and the
   gap in both dollars and percentage points.
3. **Account location** — which accounts to fill in which order (employer match
   first, then HSA, then tax-advantaged, then taxable), and why the ordering
   changes with bracket and horizon.
4. **Glidepath** — how the equity/bond mix should shift with time, and what
   holding a static allocation instead would cost or risk.

## Charts

Via `financial-charts`:

- `projection_chart` — median emphasized in the accent hue, percentile bands
  de-emphasized. The median is the point; the bands are context.
- `contributions_chart` — contributions vs growth as a stacked area, which shows
  the crossover where returns start outrunning deposits.

## Framing

This is decision support with stated assumptions. It is **not financial advice**,
it does not account for the human's full circumstances, and it should say so once,
plainly, without hedging every sentence.

Where a number depends on tax law, note that the analysis reflects current rules
as the human has described them.
