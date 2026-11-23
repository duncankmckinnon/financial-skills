# My data sources

This file tells the financial skills which connected sources to read and which
source is authoritative for each account. It exists so that an account two
sources both report is never counted twice.

Rules the skills follow:

- Every account maps to **exactly one** source.
- An account a source returns that is not listed here is left out of every
  total and reported as unassigned, until you add it.
- Remove this file and the skills fall back to adapting to whatever is
  connected.

## Sources

One name per line, matching a file in the plugin's `references/sources/` or in
`sources/` next to this file.

- robinhood

## Accounts

Name each account the way its source names it. Add a row per account.

| Account | Source |
|---|---|
