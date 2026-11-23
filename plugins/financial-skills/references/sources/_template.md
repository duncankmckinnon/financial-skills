# <Source name>

Role: read-only

<!-- Role is `read-only` or `trading`. Only one source may be `trading`, and a
     user-added source should stay `read-only`. Say when and how the tool
     names below were verified. -->

## Connection

<!-- Server name and how the human connects it. -->

## Boundaries

<!-- What is readable, what (if anything) is writable, which asset classes,
     whether it reports accounts that another source also reports. -->

## Freshness

<!-- Live, or synced on a schedule. State the schedule if known. -->

## Capabilities

<!-- One row per capability, names exactly as in references/sources.md.
     Tool name is backticked, or `none` written bare. Verified is live, docs
     or no. -->

| Capability | Tool name | Verified |
|---|---|---|
| accounts | none | no |
| balances | none | no |
| positions | none | no |
| quotes | none | no |
| tax lots | none | no |
| order history | none | no |
| transactions | none | no |
| order preview | none | no |
| order place | none | no |

## Gaps

<!-- Each thing a skill must report rather than estimate. -->
