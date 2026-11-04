# Swedish Bank Statement Counterpart (No Suspense)

Interim (suspense) accounts are forbidden in this accounting policy. Odoo
books every imported bank statement line against the journal's suspense
account until it is reconciled, which parks the amount on an interim account
and hides errors.

This module resolves the counterpart account at import time, so the line is
booked directly against a real account.

## Configuration

Open the bank journal and go to the **Advanced Settings** tab:

| Field | Meaning |
|---|---|
| **Never Use Suspense Account** | Enables the policy for this journal. |
| **Counterpart for Incoming Amounts** | Account for positive line amounts, typically `1510 Kundfordringar`. |
| **Counterpart for Outgoing Amounts** | Account for negative line amounts, typically `2440 Leverantörsskulder`. |

## Resolution order

1. **The partner's own account** — `property_account_receivable_id` for
   incoming amounts, `property_account_payable_id` for outgoing. This is the
   most precise answer and is used whenever the line has a partner (either
   set directly or resolved from the counterparty bank account number).
2. **The journal's configured counterpart** — the receivable/payable account
   set above.

If neither yields an account, the import **fails loudly** instead of silently
posting to suspense. A silent suspense posting is worse than a loud error,
because nobody notices it until reconciliation.

## Behaviour

| Amount | Partner set | Result |
|---|---|---|
| +469.59 | yes | `1930 D / 1510 K` (partner's receivable) |
| −469.59 | yes | `1930 K / 2440 D` (partner's payable) |
| +469.59 | no | `1930 D / 1510 K` (journal default) |
| −469.59 | no | `1930 K / 2440 D` (journal default) |
| any | no, and no journal default | **UserError** |

## Notes

- The policy is **per journal**. Journals without the flag keep standard
  Odoo behaviour, so the module can be installed without changing anything
  until you opt in.
- A counterpart already set by another module is never overwritten.
- Cash journals (`type = cash`) work the same way.
