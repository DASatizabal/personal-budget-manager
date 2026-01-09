# Claude Code Handoff Prompt

> **START OF SESSION**: Read this file, STATUS.md, TODO.md, and DECISIONS.md before proceeding.

## What We're Building
Personal Budget Manager - a Python/PyQt6 desktop app replacing an Excel-based financial tracking system. Tracks bank accounts, 11 credit cards, 2 401k loans, recurring charges, and projects future cash flow.

## Current State
**Phase 8 Complete** - All core phases complete including infrastructure. GitHub repo created.

Working features:
- Excel import from `Budget v2 Claude.xlsx`
- Dashboard with accounts, credit cards, loans
- Balance editing (bulk and individual)
- Recurring charges tab
- Transaction ledger with running balances
- Auto-generation of 12 months of recurring transactions
- Paycheck config with deductions
- Lisa payment splitting
- Dark mode UI
- **Phase 1 fixes:** MM/DD/YYYY dates, $ label placement, no-scroll spinboxes, improved spacing, tab caching
- **Phase 2 features:** CSV export, balance recalculation tool, input validation
- **Phase 3 features:** Resizable columns, column visibility toggles, payment type filter, summary bar, Owed+Avail columns
- **Phase 4 features:** Smart charge exclusion (special codes, Lisa-linked), configurable payday
- **Phase 5 features:** Enhanced card deletion with charge reassignment and transaction handling
- **Phase 6 features:** Dashboard table sorting, 90-day balance alerts
- **Phase 7 features:** Auto-backup/undo system, confirmation dialogs, detailed import error handling
- **Phase 8 features:** Logging system, 25 unit tests, pyproject.toml packaging
- **Session 2026-01-08 fixes:** CC min payment, transaction sorting (positive first), payday anchor date, delete all non-posted, Delete All button
- **Session 2026-01-09 fixes:** Lisa payment 3-payday month calculation, duplicate shared expense prevention, CC↔recurring charge auto-sync

## Key Constraints
- **Local only** - no cloud/server, SQLite database
- **Excel file excluded from git** - contains personal financial data
- **Special day codes**: 991-999 for non-monthly charges (991=Mortgage, 999=Payday)
- **Payment method codes**: C=Chase, S=Savings, credit card codes match Excel

## What to Work on Next
See TODO.md for full backlog. All core phases (1-8) are complete. **Phase 9: Advanced Features** contains future/nice-to-have items:
1. Tax estimation feature
2. Optimal payment distribution algorithm
3. Deferred interest purchase tracking
4. Credit card statement parsing (PDF/CSV upload)
5. Bank API integration (Plaid/Yodlee)

## Don't Touch
- Excel import logic in `excel_import.py` - working correctly after multiple fixes
- Database schema in `database.py` - stable, data already imported
- The `.gitignore` exclusions for *.xlsx and *.db files

## File Structure
```
windsurf-project/
├── main.py                 # Entry point
├── requirements.txt        # PyQt6, pandas, openpyxl
├── pyproject.toml          # Python packaging configuration
├── budget_app/
│   ├── models/            # SQLite models (database.py, credit_card.py, etc.)
│   ├── views/             # PyQt6 UI (dashboard_view.py, transactions_view.py, etc.)
│   │   └── widgets.py     # Custom NoScrollSpinBox widgets
│   ├── utils/             # excel_import.py, calculations.py, csv_export.py
│   │   ├── backup.py      # Auto-backup and restore utilities
│   │   └── logging_config.py  # Logging configuration
│   └── controllers/       # (minimal, logic mostly in views)
├── tests/                  # Unit tests (pytest)
│   ├── test_calculations.py
│   └── test_models.py
├── STATUS.md              # Current project status
├── TODO.md                # Prioritized backlog (9 phases)
├── DECISIONS.md           # Architecture decisions log
└── .claude/HANDOFF.md     # This file
```

## How to Run
```bash
pip install -r requirements.txt
python main.py
```
First run: File > Import from Excel to load data.

## Session End Protocol
When user says "I'm done for now":
1. Update STATUS.md with current progress
2. Update TODO.md with completed items
3. Update DECISIONS.md with any new architectural decisions
4. Update this HANDOFF.md file
5. Commit all changes
6. Push to GitHub
