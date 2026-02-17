# Personal Budget Manager

A Python desktop application for comprehensive personal finance tracking. Replaces Excel-based budget management with a full-featured PyQt6 GUI, SQLite database, PDF statement parsing, and Plaid bank sync.

## Features

### 11-Tab Interface
| Tab | What it does |
|-----|-------------|
| **Dashboard** | Account summaries, credit card utilization, loan balances, 90-day minimum balance alerts |
| **Transactions** | Full ledger with running balances, payment type filtering, and 12-month projections |
| **Posted** | Confirmed transaction history (separated from projected) |
| **Credit Cards** | Manage balances, limits, due dates, interest rates, and utilization |
| **Payoff Planner** | Compare 5 payoff strategies: Avalanche, Snowball, Hybrid, High Utilization, Cash on Hand |
| **Deferred Interest** | Track 0% APR promotional purchases with expiration alerts and risk levels |
| **Recurring Charges** | Auto-generate transactions across multiple frequencies (weekly, monthly, special codes) |
| **Paycheck** | Configure pay schedule, gross/net, deductions; import from paystub PDFs |
| **Lisa Payments** | Shared expense splitting based on 2 vs 3 paycheck months |
| **PDF Import** | Parse credit card statements and paystubs from 8+ bank formats |
| **Bank API** | One-click balance sync via Plaid — link accounts, auto-map, compare balances |

### Additional Capabilities
- **Excel import** from existing spreadsheets
- **CSV export** with table selection and date range filtering
- **Auto-backup** system with undo support (Ctrl+Z)
- **Dark/light mode** toggle (qdarkstyle theme)
- **Custom widgets** — MoneySpinBox and PercentSpinBox with auto-select, no scroll, no arrows

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| GUI | PyQt6 |
| Database | SQLite3 |
| Theme | qdarkstyle |
| PDF Parsing | pdfplumber |
| Bank Sync | plaid-python |
| Data Processing | pandas, openpyxl |
| Testing | pytest, pytest-qt (1,013 tests) |

## Getting Started

### Install Dependencies
```bash
pip install PyQt6 pandas openpyxl pdfplumber plaid-python qdarkstyle
```

### Run the App
```bash
python main.py
```

On first run, use **File > Import from Excel** to load data from your existing budget workbook.

### Run Tests
```bash
python -m pytest tests/ -v                # All 1,013 tests
python -m pytest tests/ --cov=budget_app  # With coverage report
```

## Project Structure

```
personal-budget-manager/
├── main.py                          # Application entry point
├── pyproject.toml                   # Python packaging configuration
├── budget_app/
│   ├── models/                      # SQLite data models (11 files)
│   │   ├── database.py              #   Schema, connection, migrations
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
│   │   ├── main_window.py           #   Main window, tab manager, menus
│   │   ├── dashboard_view.py        #   Dashboard tab
│   │   ├── transactions_view.py     #   Transactions tab
│   │   ├── posted_transactions_view.py
│   │   ├── credit_cards_view.py
│   │   ├── payoff_planner_view.py
│   │   ├── deferred_interest_view.py
│   │   ├── recurring_charges_view.py
│   │   ├── paycheck_view.py
│   │   ├── shared_expenses_view.py
│   │   ├── pdf_import_view.py
│   │   ├── bank_api_view.py
│   │   └── widgets.py              #   MoneySpinBox, PercentSpinBox
│   └── utils/                       # Business logic utilities (11 files)
│       ├── calculations.py          #   Balance projections
│       ├── payoff_calculator.py     #   5-strategy payoff engine
│       ├── statement_parser.py      #   PDF parsing (8 bank formats)
│       ├── excel_import.py          #   Excel data import
│       ├── csv_export.py            #   CSV export
│       ├── backup.py               #   Auto-backup and restore
│       ├── plaid_client.py          #   Plaid API wrapper
│       ├── plaid_config.py          #   Plaid credentials management
│       ├── plaid_link_server.py     #   Local HTTP server for Plaid Link
│       └── logging_config.py        #   Logging configuration
└── tests/                           # 1,013 tests across 27 files
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+U | Quick Update all balances |
| Ctrl+Z | Undo (restore from auto-backup) |
| F5 | Refresh current view |

## Configuration

### Plaid Bank Sync (optional)
1. Get API credentials from [Plaid Dashboard](https://dashboard.plaid.com)
2. Open the **Bank API** tab and enter credentials in the Settings panel
3. Click **Link New Account** to connect a bank via browser
4. Use **Sync All Balances** to fetch latest balances

Credentials are stored in `plaid_config.json` (gitignored).

### Data Files
- `budget_data.db` — SQLite database (created on first import, gitignored)
- `plaid_config.json` — Plaid API credentials (gitignored)
- Excel/PDF files used for import are not stored by the app
