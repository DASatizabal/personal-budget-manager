# Architecture & Design Decisions

## 2026-01-06: Chose PyQt6 over Tkinter
PyQt6 provides modern styling, better table widgets, and native dark mode support needed for financial data display.

## 2026-01-06: SQLite over PostgreSQL
Local-only requirement means SQLite is simpler, portable, and sufficient. No server needed.

## 2026-01-06: Removed UNIQUE constraint on recurring_charges.name
Excel data has legitimate duplicates (e.g., "BJs" appears twice for different payment methods). Deduplication handled via composite key: name + day + payment_method.

## 2026-01-06: Special day codes 991-999 for non-monthly charges
Preserved Excel convention: 991=Mortgage, 992=Spaceship loan, 993=SCCU, 994=Windows, 999=Payday. Allows same data model for different frequencies.

## 2026-01-06: Auto-generate 12 months of future transactions
Matches Excel projection behavior. Regeneration clears old future transactions first to avoid duplicates.

## 2026-01-06: Exclude Excel and DB files from git
Contains personal financial data. Users import their own Excel on first run; DB regenerates from import.

## 2026-01-06: Custom NoScrollSpinBox widgets
Created `widgets.py` with `NoScrollDoubleSpinBox` and `NoScrollSpinBox` that ignore wheel events. Prevents accidental value changes when scrolling the page.

## 2026-01-06: Transactions tab caching with dirty flag
Added `_data_dirty` flag to TransactionsView to skip expensive reload when switching tabs. Only reloads when: first load, date filter changes, or data is modified (add/edit/delete/generate).

## 2026-01-06: $ sign as external label, not input prefix
In Update All Balances dialog, moved `$` from `spinbox.setPrefix("$")` to a QLabel placed left of the input. Cleaner UX and matches user expectation.

## 2026-01-08: Credit card payments use minimum payment, not full balance
Changed `RecurringCharge.get_actual_amount()` to return `card.min_payment` instead of `card.current_balance` for credit card payment transactions. More realistic for projections.

## 2026-01-08: Transaction sorting - positive before negative on same day
Changed ORDER BY from `date, id` to `date, amount DESC, id`. Ensures income (Payday) appears before expenses on the same day, giving accurate running balance progression.

## 2026-01-08: Payday uses effective_date as bi-weekly anchor
Changed payday generation to use `paycheck.effective_date` as the reference point for the bi-weekly schedule, not just "next Friday from today". Paydays are calculated as multiples of 14 days from the anchor.

## 2026-01-08: Delete ALL future non-posted transactions on regenerate
Changed `Transaction.delete_future_recurring()` to delete all transactions where `is_posted = 0`, not just those with `recurring_charge_id IS NOT NULL`. Fixes duplicate Payday/LDBPD transactions.

## 2026-01-09: Lisa payment counts paydays from month start
Changed `_generate_payday_transactions()` to count paydays starting from the 1st of the month, not from `start_date` (today). This ensures 3-payday months like January 2026 (1/2, 1/16, 1/30) correctly calculate $833.33 per payday instead of $1250.

## 2026-01-09: Credit cards auto-sync linked recurring charges
Added `_sync_linked_recurring_charges()` to `CreditCard.save()`. When a credit card is saved, any linked recurring charges automatically update their `day_of_month` to match the card's `due_day` and set `amount_type` to `CALCULATED`. Ensures recurring charge payments always match the credit card's due date.

## 2026-01-09: CALCULATED amount_type for credit card payments
Added `CALCULATED` as an alias for `CREDIT_CARD_BALANCE` in `RecurringCharge.get_actual_amount()`. Both types pull the `min_payment` from the linked credit card. CALCULATED is the default for CC-linked charges.
