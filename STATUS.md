# Personal Budget Manager - Status

## Goal / Current Milestone
Replace Excel-based budget tracking with a Python desktop application. Currently: **Phase 8 Complete** - MVP working + all phases through infrastructure complete.

## What's Done
- [x] SQLite database schema (accounts, credit cards, loans, recurring charges, transactions, paycheck config, shared expenses)
- [x] Excel import from existing `Budget v2 Claude.xlsx`
- [x] PyQt6 desktop UI with dark mode
- [x] Dashboard with account summaries, credit cards, loans
- [x] Balance update functionality (bulk and individual editing)
- [x] Recurring charges management
- [x] Auto-generation of recurring transactions (12 months ahead)
- [x] Transaction ledger view with running balances
- [x] Paycheck configuration with deductions
- [x] Lisa payment splitting (2 vs 3 paycheck months)
- [x] Database backup/restore
- [x] GitHub repository set up
- [x] **Phase 1 UI Fixes:**
  - Date display format MM/DD/YYYY
  - $ sign as label (not inside input fields)
  - No-scroll spinboxes to prevent accidental value changes
  - Improved spacing/padding across UI
  - Transactions tab caching (no reload on tab switch)
- [x] **Phase 2 Core Features:**
  - CSV export with table selection and date filtering
  - Balance recalculation tool (compare stored vs calculated balances)
  - Input validation on all forms (Transaction, Credit Card, Recurring Charge)
- [x] **Phase 3 Transactions Enhancements:**
  - Resizable columns with persistent widths (QSettings)
  - Column visibility toggles (Owed/Avail columns per card)
  - Payment type filter dropdown (multi-select)
  - Summary bar showing Chase balance, total CC available, utilization
  - Both "Owed" and "Avail" columns for each credit card
- [x] **Phase 4 Generation Fixes:**
  - Exclude special day codes (991-999) from regular generation loop
  - Exclude charges linked to Lisa Payments via shared_expenses
  - Configurable payday (pay_day_of_week in paycheck config)
  - Database migration for new column
- [x] **Phase 5 Credit Card Management:**
  - Enhanced card deletion workflow with CardDeletionDialog
  - Prompt to reassign linked charges when deleting card
  - Option to transfer or delete associated transactions
- [x] **Phase 6 Dashboard Improvements:**
  - Column sorting enabled on credit cards and loans tables
  - 90-day minimum balance alerts (already implemented)
- [x] **Phase 7 Data Safety & Quality:**
  - Auto-backup system before destructive operations
  - Undo functionality (Edit > Undo, Ctrl+Z)
  - Restore from auto-backup dialog
  - Confirmation dialogs for bulk operations
  - Detailed Excel import error handling with warnings
- [x] **Phase 8 Project Infrastructure:**
  - Logging system (budget_app/utils/logging_config.py)
  - Unit tests (25 tests for models and calculations)
  - pyproject.toml for proper Python packaging

## Session 2026-01-08 Fixes
- Credit card payments now use minimum payment instead of full balance
- Transaction sorting: positive amounts (Payday) before negative (charges) on same day
- Payday generation uses effective_date as anchor for bi-weekly schedule
- Fixed duplicate transactions: delete ALL future non-posted transactions on regenerate
- Added "Delete All" button to Transactions toolbar
- Fixed Lisa-linked charges (Mortgage, Spaceship, etc.) being excluded from generation
- Fixed shared_expenses linking in database

## Session 2026-01-09 Fixes
- **Lisa Payment Amount**: Fixed payday counting to start from beginning of each month (not today). January 2026 with 3 paydays now correctly calculates $833.33/payday.
- **No Duplicate Charges**: Shared expenses (Mortgage, SCCU Loan, Spaceship, Windows) linked to Lisa Payments now skipped in transaction generation.
- **CC ↔ Recurring Charge Sync**: Credit cards now auto-sync linked recurring charges on save (updates day_of_month to match due_day, sets amount_type to CALCULATED).
- **Recurring Charges Display**: Now shows actual calculated amounts and due days from linked credit cards.
- **BJs Fix**: Payment date corrected from day 5 to day 2 (matches credit card due_day).
- **Auto-create Recurring Charge**: New credit cards now automatically create linked recurring charge for payment tracking.
- **Missing CC Payments Fixed**: Created recurring charges for MicroCenter, Wyndham, Zales (were missing payment transactions).

## Session 2026-01-09 (Part 2) - Posted Transactions Feature
- **Checkbox Column**: Added checkmark column to Transactions tab for marking transactions as posted
- **Balance Updates on Post**: When checking a transaction as posted:
  - Updates Chase account balance for bank transactions
  - Updates credit card balance for CC charges
  - For CC payments from Chase, also reduces the linked card's balance
- **Posted Date Tracking**: New `posted_date` field records when transaction was marked as posted
- **Posted Tab**: New tab showing all posted transactions with Due Date, Posted Date, Pay Type, Description, Amount
- **Clear Posted Button**: Removes posted transactions from Transactions view (moves to Posted tab)
- **Skip Posted on Generate**: Recurring transaction generation now skips already-posted transactions to prevent duplicates
- **"Dirty" Pattern**: Dashboard and Posted views use mark_dirty() pattern for efficient lazy refresh

## Session 2026-01-13 Updates
- Added detailed TODO items for Phase 9 future features:
  - 9.2 Credit Card Payoff Planner (full implementation plan in `.claude/plans/humming-napping-pony.md`)
  - 9.6 Refresh Recurring Charges tab when Credit Cards tab updated
  - 9.7 Paycheck/paystub parsing (PDF)
  - 9.8 Modernize GUI appearance
  - 9.9 Dashboard "Quick Update" for balances
  - 9.10 Auto-select monetary input fields on click

## What's Next (Phase 9 - Future/Advanced)
Phase 9 contains advanced features for future development:
1. Tax estimation feature
2. Credit Card Payoff Planner (avalanche, snowball, hybrid, cashflow methods)
3. Deferred interest purchase tracking
4. Credit card statement parsing (PDF/CSV)
5. Bank API integration (Plaid/Yodlee)
6. Refresh Recurring Charges on CC update
7. Paycheck/paystub parsing
8. Modernize GUI appearance
9. Dashboard Quick Update
10. Auto-select monetary input fields

## Current Blockers
None

## How to Run
```bash
cd C:\Users\David\CascadeProjects\windsurf-project
pip install -r requirements.txt
python main.py
```

First run: Use File > Import from Excel to load data from your Excel workbook.

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `budget_app/views/dashboard_view.py` | Main dashboard with balance editing |
| `budget_app/views/transactions_view.py` | Transaction ledger with recurring generation |
| `budget_app/views/posted_transactions_view.py` | Posted transactions history view |
| `budget_app/views/widgets.py` | Custom no-scroll spinbox widgets |
| `budget_app/utils/excel_import.py` | Excel data import |
| `budget_app/utils/calculations.py` | Running balance & projection calculations |
| `budget_app/models/database.py` | SQLite schema and connection |

## Open Questions / Assumptions
- Excel file contains personal financial data and is excluded from git
- Database file (`budget_data.db`) is excluded from git (recreated on first run)
- Special day codes: 991=Mortgage, 992=Spaceship, 993=SCCU, 994=Windows, 999=Payday
- Lisa payments calculated based on 2 vs 3 paycheck months (3rd paycheck = extra payment month)
