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

Read capabilities used: accounts, positions, balances, quotes, and order
history. **Resolve each to a source and a tool via `references/sources.md`** —
never hardcode a source or a tool name here.

Which accounts to read is decided there too: every account in the human's
`$FINANCIAL_HOME/sources.md`, each from its one declared source, or — with no
declaration — whatever is connected, by the fallback rules in that file.
Reading every account is expected and safe; nothing here writes.

Three rules from `references/sources.md` that this skill must visibly follow:

- **One account, one source.** An aggregator often reports accounts a broker
  also reports. Never add them together.
- An account a source returns that the declaration does not list is
  **unassigned**: report it, leave it out of every total, ask the human.
- If a declared source cannot be reached, name the accounts you **could not
  read** and do not present the rest as the whole portfolio.

## Adapting to what is connected

Do everything the connected capabilities support, following the table in
`references/sources.md`, and say what was left out:

- no positions, only balances → account-level allocation only
- no cost basis → no unrealized P/L; name the gap
- no live quotes for a holding → use the source's synced value, marked **not
  live**
- no policy → no drift (see below)

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

Where lot-level cost basis is unavailable from every connected source, say so plainly and scope
the P/L claim to what the data supports. Do not estimate silently, and do not let
a confident tone paper over a gap. The same applies to any holding no source
returns.

## Charts

Hand off to `financial-charts` — do not write chart code here:

- `allocation_chart` — allocation by position, top 7 + "Other"
- `drift_chart` — drift vs target, if a policy exists
- `pl_chart` — unrealized P/L per position

## Output

Lead with the two or three things that actually matter — a breached position
limit, a large drift, a concentrated exposure — then the supporting detail.
State assumptions. This is decision support, not advice.

Close with one short block, every time:

- **sources read**, and the as-of time of each
- the share of total value that is not live
- unassigned accounts and accounts you could not read
- each analysis left out, with the capability it was missing

## If no source is available

This skill needs at least one connected source that provides positions or balances. If none
is reachable — not configured, not authorized, or the harness cannot connect to
one — say so plainly, point at `references/harness-setup.md`, and stop. Do not
guess at holdings, prices, or balances, and do not substitute figures the human
mentioned in passing for data you were unable to read.
