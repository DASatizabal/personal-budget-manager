# Personal Budget Manager

A desktop application for comprehensive personal finance tracking, designed to replace Excel-based budget management.

## What It Does

This application helps users manage their finances by tracking:

- **Bank Accounts** - Multiple accounts (checking, savings, cash) with running balances
- **Credit Cards** - Track balances, limits, due dates, interest rates, and utilization
- **Loans** - Loan tracking with amortization and interest calculations
- **Recurring Charges** - Automated transaction generation (12 months ahead) with various frequencies
- **Paycheck Configuration** - Bi-weekly/monthly payday scheduling with deduction tracking
- **Shared Expenses** - Split expense tracking for shared payments

### Key Features

- Dashboard with account summaries and 90-day minimum balance alerts
- Full transaction ledger with filtering, sorting, and running balance calculations
- Posted vs. projected transaction workflow
- Excel import from existing spreadsheets
- CSV export with date range filtering
- Auto-backup system with undo support
- Dark mode support

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **GUI Framework** | PyQt6 |
| **Database** | SQLite3 (local, portable) |
| **Data Processing** | pandas, openpyxl |
| **Testing** | pytest, pytest-cov |

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Project Structure

```
budget_app/
├── models/      # Data models (accounts, cards, transactions, etc.)
├── views/       # PyQt6 UI components (7 tabs)
├── utils/       # Excel import, CSV export, calculations, backup
└── controllers/ # Business logic (placeholder)
tests/           # Unit tests
```
