# Investment Policy

Copy to `$FINANCIAL_HOME/investment-policy.md` (default `~/.financial/`) and
edit. `scripts/doctor.sh --fix` places it there for you.
**Never commit this file** — it describes real positions.

Skills read this file to know your targets and limits. Without it they will
report what is computable and tell you which analyses need a policy; they will
not invent targets.

## Target allocation

| Asset class or symbol | Target % | Tolerance band (± pp) |
|---|---|---|
| US equity | 60 | 5 |
| International equity | 20 | 5 |
| Bonds | 15 | 3 |
| Cash | 5 | 2 |

Targets should sum to 100. The tolerance band is what makes something a trade:
a class 1pp off a 5pp band is *in policy* and must not be rebalanced.

## Risk limits

- Maximum single position: 10% of portfolio
- Cash floor (never spend below): $0
- Maximum trade size without extra scrutiny: $0

## Do not sell

Absolute. Rebalancing works around these rather than proposing to sell them.

- `SYMBOL` — reason (long-term holding, low basis, vesting schedule, …)

## Tax constraints

- Prefer long-term lots: yes / no
- Wash-sale window to respect: 30 days
- Taxable accounts: (list)
- Tax-advantaged accounts: (list)

## Notes

Anything else a skill should weigh — upcoming liquidity needs, concentration
you have accepted deliberately, sectors you will not hold.
