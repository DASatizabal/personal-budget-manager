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
