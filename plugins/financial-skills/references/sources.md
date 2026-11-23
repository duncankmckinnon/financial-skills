# Data sources

A **source** is anything connected to the agent that can report financial
data: a broker, an aggregator, a bank. Skills never name a source or a tool.
They name a **capability** from the list below, and this file says how to turn
that into a call against whatever is actually connected.

No skill requires a particular source. Each one does everything the connected
capabilities support and names what it had to leave out.

## Capabilities

Source files use these names exactly.

| Capability | Kind | What it returns |
|---|---|---|
| accounts | read | the accounts a source can see, with type and an identifier |
| balances | read | cash, buying power and total value per account |
| positions | read | holdings: symbol, quantity, market value, cost basis |
| quotes | read | a current price for a symbol |
| tax lots | read | per-lot acquisition date, quantity and cost |
| order history | read | past orders and fills |
| transactions | read | cash activity: deposits, withdrawals, purchases, payments |
| order preview | write | simulate an order, returning warnings and estimated cost |
| order place | write | execute an order |

## Where source files live

- `references/sources/<name>.md` — sources shipped with the plugin.
- `$FINANCIAL_HOME/sources/<name>.md` — sources the human adds. Same format.
  They live there, not in the plugin, because an installed plugin directory is
  replaced on update.

Each file gives the source's role (`trading` or `read-only`), how it is
reached, its boundaries, how fresh its data is, a capability → tool table, and
its known gaps. Read the file for every source you are about to use.

## Resolving a capability to a tool

- **Read capabilities.** Use the tool the source file names. Where the file
  has no verified name, the tool may be resolved from the server's own live
  tool list — reading that list is not guessing. Never invent a name.
- **Write capabilities** (`order preview`, `order place`). Callable only with
  a name the source file marks `live`, only on the source whose role is
  `trading`, and only from `trade-workflow`.
- A tool a source file lists as off limits is never called, whatever it might
  make convenient.

## Which accounts to read

The human declares their sources in `$FINANCIAL_HOME/sources.md`: which
sources are connected, and for each account, the one source that is
authoritative for it. `assets/sources.template.md` is the skeleton.

**With a declaration**, read each account from its declared source only.

**Without one**, adapt to what is connected:

- One source connected — read it.
- Several connected, one of them the trading source — read the trading source
  alone, and say the others were ignored until the human declares them.
- Several connected, none of them the trading source — report each source
  separately, give no combined total, and ask the human to declare.

## Combining sources

1. **One account, one source.** Never add the same account from two sources.
   An aggregator commonly reports accounts a broker also reports.
2. **Unassigned accounts stay out of totals.** An account a source returns
   that the declaration does not list is *unassigned*: report it, leave it out
   of every total, and ask. Never match it to another account by name, balance
   or last four digits.
3. **Every figure carries its source and as-of time.** A total built from
   mixed freshness says so, and states the share of value that is not live.
4. **Live beats synced.** A live quote from any connected source wins over a
   synced value for the same symbol. Where there is no live quote — a fund with
   no ticker, a manual account — use the synced value and mark it not live.
   Never estimate a price.
5. **A gap is named, never filled.** A capability no connected source provides
   for an account is reported as a gap, not estimated.
6. **An unreachable source is said out loud.** If a declared source cannot be
   read, name the accounts that could not be read and do not present what
   remains as the whole portfolio.
7. **Write capabilities come from the trading source only.**

## Adapting to the data available

| Analysis | Needs | Without it |
|---|---|---|
| allocation, concentration, exposure | positions or balances | account-level only, from balances; stop if neither |
| unrealized P/L | positions with cost basis | omitted, named as a gap |
| drift | positions + policy | omitted |
| live pricing | quotes | synced values, marked not live |
| lot-aware tax checks | tax lots | named as a gap, no assumption |
| wash-sale check | transactions or order history | named as not checked |
| proposing trades | positions + policy | not available |
| previewing / placing | order preview + order place | `rebalancing` still presents the trade list for the human to place themselves; `trade-workflow` stops after sizing |

End every run with what was read and what was not: the sources used, any
unassigned or unreadable accounts, and each analysis left out with the
capability it was missing.

## Adding a source

Copy `references/sources/_template.md` to `$FINANCIAL_HOME/sources/<name>.md`,
fill it in from the server's tool list, then add the source and its accounts
to `$FINANCIAL_HOME/sources.md`. Connecting the server itself is
harness-specific — see `references/harness-setup.md`.
