# Personal Budget Manager - Status

## Goal
Replace Excel-based budget tracking with a Python desktop application. **All phases complete — v1.0 ready for use.**

## What's Done

### Core Application
- [x] SQLite database schema (accounts, credit cards, loans, recurring charges, transactions, paycheck config, shared expenses, Plaid links)
- [x] Excel import from existing `Budget v2 Claude.xlsx`
- [x] PyQt6 desktop UI with dark/light mode toggle (qdarkstyle)
- [x] 11-tab interface covering all financial workflows
- [x] 1,013 unit tests across 27 test files

### Phase 1: Quick UI Fixes
- [x] Date display format MM/DD/YYYY (storage stays ISO)
- [x] $ sign as label (not inside input fields)
- [x] No-scroll spinboxes to prevent accidental value changes
- [x] Improved spacing/padding across UI
- [x] Transactions tab caching (no reload on tab switch)

### Phase 2: Core Feature Gaps
- [x] CSV export with table selection and date filtering
- [x] Balance recalculation tool
- [x] Input validation on all forms

### Phase 3: Transactions Enhancements
- [x] Resizable columns with persistent widths (QSettings)
- [x] Column visibility toggles (Owed/Avail columns per card)
- [x] Multi-select payment type filter dropdown
- [x] Summary bar (Chase balance, total CC available, utilization)

### Phase 4: Recurring Charges & Generation Fixes
- [x] Exclude special day codes (991-999) from regular generation
- [x] Exclude charges linked to Lisa Payments
- [x] Configurable payday (pay_day_of_week)

### Phase 5: Credit Card Management
- [x] Enhanced card deletion with charge reassignment (CardDeletionDialog)
- [x] Option to transfer or delete associated transactions

### Phase 6: Dashboard Improvements
- [x] Column sorting on credit cards and loans tables
- [x] 90-day minimum balance alerts

### Phase 7: Data Safety & Quality
- [x] Auto-backup system before destructive operations
- [x] Undo functionality (Edit > Undo, Ctrl+Z)
- [x] Confirmation dialogs for bulk operations
- [x] Detailed Excel import error handling with warnings

### Phase 8: Project Infrastructure
- [x] Logging system (`logging_config.py`)
- [x] Unit tests (grew from 25 to 1,013)
- [x] pyproject.toml for proper Python packaging

### Phase 8.5: Posted Transactions
- [x] Checkbox column to mark transactions as posted
- [x] Balance updates on post (Chase and/or linked CC)
- [x] Posted tab showing transaction history
- [x] Skip posted transactions when regenerating

### Phase 9: Advanced Features
- [x] 9.1 MoneySpinBox/PercentSpinBox auto-select widgets
- [x] 9.2 Cross-tab refresh (CC changes notify Recurring Charges)
- [x] 9.3 Dashboard "Quick Update" dialog (Ctrl+U)
- [x] 9.4 Dark mode with qdarkstyle theme
- [x] 9.5 Credit Card Payoff Planner (5 strategies: Avalanche, Snowball, Hybrid, High Utilization, Cash on Hand)
- [x] 9.6 Paystub PDF parsing and import
- [x] 9.7 Credit card statement parsing (8 bank formats)
- [x] 9.9 Deferred interest purchase tracking
- [x] 9.10 Plaid API integration (one-click bank balance sync)

## Current Blockers
None

## How to Run
```bash
cd personal-budget-manager
pip install PyQt6 pandas openpyxl pdfplumber plaid-python qdarkstyle
python main.py
```
First run: Use File > Import from Excel to load data from your Excel workbook.

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| **Views** | |
| `budget_app/views/main_window.py` | Main window, tab manager, menu bar |
| `budget_app/views/dashboard_view.py` | Dashboard with account summaries and balance alerts |
| `budget_app/views/transactions_view.py` | Transaction ledger with running balances |
| `budget_app/views/posted_transactions_view.py` | Posted transactions history |
| `budget_app/views/credit_cards_view.py` | Credit card management |
| `budget_app/views/payoff_planner_view.py` | 5-strategy payoff comparison |
| `budget_app/views/deferred_interest_view.py` | 0% APR promotional tracking |
| `budget_app/views/recurring_charges_view.py` | Recurring expense management |
| `budget_app/views/paycheck_view.py` | Paycheck config + paystub import |
| `budget_app/views/shared_expenses_view.py` | Lisa Payments / shared expenses |
| `budget_app/views/pdf_import_view.py` | PDF statement import |
| `budget_app/views/bank_api_view.py` | Plaid bank sync |
| `budget_app/views/widgets.py` | MoneySpinBox, PercentSpinBox |
| **Models** | |
| `budget_app/models/database.py` | SQLite schema and connection |
| `budget_app/models/account.py` | Bank accounts |
| `budget_app/models/credit_card.py` | Credit cards |
| `budget_app/models/loan.py` | Loans |
| `budget_app/models/transaction.py` | Transactions (posted/pending) |
| `budget_app/models/recurring_charge.py` | Recurring charges |
| `budget_app/models/paycheck.py` | Paycheck config + deductions |
| `budget_app/models/shared_expense.py` | Shared expenses |
| `budget_app/models/deferred_interest.py` | Deferred interest purchases |
| `budget_app/models/plaid_link.py` | Plaid items + account mappings |
| **Utilities** | |
| `budget_app/utils/calculations.py` | Running balance & projection calculations |
| `budget_app/utils/payoff_calculator.py` | Credit card payoff strategies |
| `budget_app/utils/statement_parser.py` | PDF statement parsing (8 formats) |
| `budget_app/utils/excel_import.py` | Excel data import |
| `budget_app/utils/csv_export.py` | CSV export with date filtering |
| `budget_app/utils/backup.py` | Auto-backup and restore |
| `budget_app/utils/plaid_client.py` | Plaid API wrapper |
| `budget_app/utils/plaid_config.py` | Plaid credentials management |
| `budget_app/utils/plaid_link_server.py` | Local HTTP server for Plaid Link |
| `budget_app/utils/logging_config.py` | Logging configuration |

## Open Questions / Assumptions
- Excel file contains personal financial data and is excluded from git
- Database file (`budget_data.db`) is excluded from git (recreated on first run)
- Special day codes: 991=Mortgage, 992=Spaceship, 993=SCCU, 994=Windows, 999=Payday
- Lisa payments calculated based on 2 vs 3 paycheck months
- Plaid credentials stored in `plaid_config.json` (gitignored)
