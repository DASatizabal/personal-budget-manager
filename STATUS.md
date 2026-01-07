# Personal Budget Manager - Status

## Goal / Current Milestone
Replace Excel-based budget tracking with a Python desktop application. Currently: **Phase 1 Complete** - MVP working + UI polish applied.

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

## What's Next (Phase 2)
1. CSV export functionality
2. Balance recalculation tool
3. Input validation across forms

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
| `budget_app/views/widgets.py` | Custom no-scroll spinbox widgets |
| `budget_app/utils/excel_import.py` | Excel data import |
| `budget_app/utils/calculations.py` | Running balance & projection calculations |
| `budget_app/models/database.py` | SQLite schema and connection |

## Open Questions / Assumptions
- Excel file contains personal financial data and is excluded from git
- Database file (`budget_data.db`) is excluded from git (recreated on first run)
- Special day codes: 991=Mortgage, 992=Spaceship, 993=SCCU, 994=Windows, 999=Payday
- Lisa payments calculated based on 2 vs 3 paycheck months (3rd paycheck = extra payment month)
