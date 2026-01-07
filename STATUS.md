# Personal Budget Manager - Status

## Goal / Current Milestone
Replace Excel-based budget tracking with a Python desktop application. Currently: **MVP Complete** - core functionality working, ready for daily use.

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

## What's Next
1. 90-day minimum balance alerts on dashboard
2. CSV export functionality
3. Transaction editing/deletion in ledger
4. Balance recalculation tool
5. Improved paycheck date handling

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
| `budget_app/utils/excel_import.py` | Excel data import |
| `budget_app/utils/calculations.py` | Running balance & projection calculations |
| `budget_app/models/database.py` | SQLite schema and connection |

## Open Questions / Assumptions
- Excel file contains personal financial data and is excluded from git
- Database file (`budget_data.db`) is excluded from git (recreated on first run)
- Special day codes: 991=Mortgage, 992=Spaceship, 993=SCCU, 994=Windows, 999=Payday
- Lisa payments calculated based on 2 vs 3 paycheck months (3rd paycheck = extra payment month)
