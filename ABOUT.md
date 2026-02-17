# Personal Budget Manager

A desktop application for comprehensive personal finance tracking, built to replace Excel-based budget management.

## What It Does

### Financial Tracking (11 tabs)
- **Dashboard** — Account summaries, credit card utilization, loan balances, 90-day minimum balance alerts
- **Transactions** — Full ledger with running balances, filtering, sorting, and 12-month projections
- **Posted** — Confirmed transaction history (separate from projected)
- **Credit Cards** — Track balances, limits, due dates, interest rates, utilization per card
- **Payoff Planner** — Compare 5 payoff strategies (Avalanche, Snowball, Hybrid, High Utilization, Cash on Hand)
- **Deferred Interest** — Track 0% APR promotional purchases with risk-level alerts
- **Recurring Charges** — Auto-generate transactions across multiple frequencies
- **Paycheck** — Configure pay schedule, gross/net, deductions; import from paystub PDFs
- **Lisa Payments** — Shared expense splitting (2 vs 3 paycheck months)
- **PDF Import** — Parse credit card statements and paystubs from 8+ bank formats
- **Bank API** — One-click balance sync via Plaid (link accounts, auto-map, compare balances)

### Key Features
- Excel import from existing spreadsheets
- CSV export with date range filtering
- PDF statement parsing (credit cards, checking, paystubs)
- Plaid API integration for automatic bank sync
- Auto-backup system with undo support (Ctrl+Z)
- Dark/light mode toggle
- Custom MoneySpinBox/PercentSpinBox widgets (auto-select, no scroll, no arrows)
- 1,013 unit tests across 27 test files

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **GUI Framework** | PyQt6 |
| **Database** | SQLite3 (local, portable) |
| **Theme** | qdarkstyle |
| **Data Processing** | pandas, openpyxl |
| **PDF Parsing** | pdfplumber |
| **Bank Integration** | plaid-python |
| **Testing** | pytest, pytest-qt, pytest-cov |

## Running the App

```bash
pip install PyQt6 pandas openpyxl pdfplumber plaid-python qdarkstyle
python main.py
```

First run: File > Import from Excel to load data from your workbook.

## Project Structure

```
personal-budget-manager/
├── main.py                          # Entry point
├── pyproject.toml                   # Python packaging config
├── budget_app/
│   ├── models/                      # Data models (11 files)
│   │   ├── database.py              #   SQLite schema + connection
│   │   ├── account.py               #   Bank accounts
│   │   ├── credit_card.py           #   Credit cards
│   │   ├── loan.py                  #   Loans
│   │   ├── transaction.py           #   Transactions (posted/pending)
│   │   ├── recurring_charge.py      #   Recurring charges
│   │   ├── paycheck.py              #   Paycheck config + deductions
│   │   ├── shared_expense.py        #   Shared expenses
│   │   ├── deferred_interest.py     #   Deferred interest purchases
│   │   └── plaid_link.py            #   Plaid items + account mappings
│   ├── views/                       # PyQt6 UI components (14 files)
│   │   ├── main_window.py           #   Main window + tab manager + menus
│   │   ├── dashboard_view.py        #   Dashboard tab
│   │   ├── transactions_view.py     #   Transactions tab
│   │   ├── posted_transactions_view.py  #   Posted tab
│   │   ├── credit_cards_view.py     #   Credit Cards tab
│   │   ├── payoff_planner_view.py   #   Payoff Planner tab
│   │   ├── deferred_interest_view.py #  Deferred Interest tab
│   │   ├── recurring_charges_view.py #  Recurring Charges tab
│   │   ├── paycheck_view.py         #   Paycheck tab
│   │   ├── shared_expenses_view.py  #   Lisa Payments tab
│   │   ├── pdf_import_view.py       #   PDF Import tab
│   │   ├── bank_api_view.py         #   Bank API tab
│   │   └── widgets.py               #   MoneySpinBox, PercentSpinBox
│   └── utils/                       # Business logic (11 files)
│       ├── calculations.py          #   Running balance projections
│       ├── payoff_calculator.py     #   5-strategy payoff engine
│       ├── statement_parser.py      #   PDF statement parsing (8 formats)
│       ├── excel_import.py          #   Excel data import
│       ├── csv_export.py            #   CSV export
│       ├── backup.py                #   Auto-backup and restore
│       ├── plaid_client.py          #   Plaid API wrapper
│       ├── plaid_config.py          #   Plaid credentials management
│       ├── plaid_link_server.py     #   Local HTTP server for Plaid Link
│       └── logging_config.py        #   Logging configuration
└── tests/                           # 1,013 tests across 27 files
    ├── conftest.py                  #   Shared fixtures
    ├── test_models.py
    ├── test_calculations.py
    ├── test_payoff_calculator.py
    ├── test_statement_parser.py
    ├── test_plaid_integration.py
    ├── test_paycheck_view.py
    └── ...                          #   (20 more test files)
```
