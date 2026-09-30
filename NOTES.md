# Notes

## Q1 2026 net income (2026-01-01 to 2026-03-31)

<!-- TODO: write the number the app shows -->

## Decisions and assumptions

<!-- TODO: write up. Reminders of the data decisions we made: -->

- Only `posted` entries count. `draft` (JE-019, 5,000 bonus accrual) and
  `void` (JE-009 duplicate sale, JE-025 returned check) are loaded but excluded.
- Start and end dates are both inclusive. Entries are filtered by date, not by
  file order (the file is not sorted, e.g. JE-007, JE-025).
- Accounts are placed in sections by `subtype`, not `type` or number. Interest
  Income (type revenue, subtype other_income) goes under Other income.
- Sign is per section: revenue sections show credit - debit, expense sections
  show debit - credit. So Sales Returns & Discounts (contra revenue) shows as a
  negative line inside Revenue, and "Revenue" total is net revenue.
- Inactive accounts still appear with their history (Marketing (legacy), 6300).
- Every income statement account is listed, even with zero activity in the range.
- Entries are reported as recorded, no re-accrual: JE-007 books all Jan-Mar rent
  (9,000.00) on 2026-01-01, so January shows the full 9,000.00.
- JE-004 annual billing (12,000.00) goes to Deferred Revenue, a balance sheet
  account, so it is not revenue. Only the monthly 1,000.00 recognitions are.
- The vendor credit (JE-020) nets against Software expense.
- Money is `Decimal` from strings end to end; the API returns two-decimal strings
  and the frontend does no math, only formatting (parentheses, commas).
- Ledger is validated at load and fails fast: amounts must be non-negative
  decimal strings, each line has exactly one non-zero side, every entry
  balances, accounts must exist, status must be posted/draft/void.
- API: `start` and `end` are required, strict `YYYY-MM-DD`, real dates, and
  `start <= end`; otherwise 400 with an error message.
- Not validated (open questions): amounts with more than two decimal places,
  duplicate account numbers or entry ids, and subtypes outside the known list
  (such an account would be silently left off the statement).

## How I checked the numbers

<!-- TODO -->

## Where AI helped, and where it was wrong

<!-- TODO -->

## What I would do next

<!-- TODO -->
