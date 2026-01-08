"""CSV export functionality for budget data"""

import csv
from pathlib import Path
from typing import Dict, List
from ..models.database import Database


def export_accounts(filepath: Path) -> int:
    """Export accounts to CSV. Returns row count."""
    db = Database()
    cursor = db.execute("""
        SELECT name, account_type, current_balance, pay_type_code
        FROM accounts ORDER BY name
    """)
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Account Type', 'Current Balance', 'Pay Type Code'])
        for row in rows:
            writer.writerow([row['name'], row['account_type'], row['current_balance'], row['pay_type_code']])

    return len(rows)


def export_credit_cards(filepath: Path) -> int:
    """Export credit cards to CSV. Returns row count."""
    db = Database()
    cursor = db.execute("""
        SELECT pay_type_code, name, credit_limit, current_balance,
               interest_rate, due_day, min_payment_type, min_payment_amount
        FROM credit_cards ORDER BY name
    """)
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Pay Type Code', 'Name', 'Credit Limit', 'Current Balance',
                        'Interest Rate', 'Due Day', 'Min Payment Type', 'Min Payment Amount'])
        for row in rows:
            writer.writerow([row['pay_type_code'], row['name'], row['credit_limit'],
                           row['current_balance'], row['interest_rate'], row['due_day'],
                           row['min_payment_type'], row['min_payment_amount']])

    return len(rows)


def export_loans(filepath: Path) -> int:
    """Export loans to CSV. Returns row count."""
    db = Database()
    cursor = db.execute("""
        SELECT pay_type_code, name, original_amount, current_balance,
               interest_rate, payment_amount, start_date, end_date
        FROM loans ORDER BY name
    """)
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Pay Type Code', 'Name', 'Original Amount', 'Current Balance',
                        'Interest Rate', 'Payment Amount', 'Start Date', 'End Date'])
        for row in rows:
            writer.writerow([row['pay_type_code'], row['name'], row['original_amount'],
                           row['current_balance'], row['interest_rate'], row['payment_amount'],
                           row['start_date'], row['end_date']])

    return len(rows)


def export_recurring_charges(filepath: Path) -> int:
    """Export recurring charges to CSV. Returns row count."""
    db = Database()
    cursor = db.execute("""
        SELECT rc.name, rc.amount, rc.day_of_month, rc.payment_method,
               rc.frequency, rc.amount_type, cc.name as linked_card, rc.is_active
        FROM recurring_charges rc
        LEFT JOIN credit_cards cc ON rc.linked_card_id = cc.id
        ORDER BY rc.day_of_month, rc.name
    """)
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Amount', 'Day of Month', 'Payment Method',
                        'Frequency', 'Amount Type', 'Linked Card', 'Active'])
        for row in rows:
            writer.writerow([row['name'], row['amount'], row['day_of_month'],
                           row['payment_method'], row['frequency'], row['amount_type'],
                           row['linked_card'] or '', 'Yes' if row['is_active'] else 'No'])

    return len(rows)


def export_transactions(filepath: Path, start_date: str = None, end_date: str = None) -> int:
    """Export transactions to CSV. Returns row count.

    Args:
        filepath: Path to save CSV
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    db = Database()

    query = """
        SELECT t.date, t.description, t.amount, t.payment_method,
               t.is_posted, t.notes, rc.name as recurring_charge
        FROM transactions t
        LEFT JOIN recurring_charges rc ON t.recurring_charge_id = rc.id
    """
    params = []

    if start_date and end_date:
        query += " WHERE t.date >= ? AND t.date <= ?"
        params = [start_date, end_date]
    elif start_date:
        query += " WHERE t.date >= ?"
        params = [start_date]
    elif end_date:
        query += " WHERE t.date <= ?"
        params = [end_date]

    query += " ORDER BY t.date, t.description"

    cursor = db.execute(query, tuple(params))
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Description', 'Amount', 'Payment Method',
                        'Posted', 'Notes', 'Recurring Charge'])
        for row in rows:
            writer.writerow([row['date'], row['description'], row['amount'],
                           row['payment_method'], 'Yes' if row['is_posted'] else 'No',
                           row['notes'] or '', row['recurring_charge'] or ''])

    return len(rows)


def export_paycheck_config(filepath: Path) -> int:
    """Export paycheck configuration to CSV. Returns row count."""
    db = Database()
    cursor = db.execute("""
        SELECT pc.gross_amount, pc.pay_frequency, pc.effective_date, pc.is_current,
               pd.name as deduction_name, pd.amount_type as deduction_type, pd.amount as deduction_amount
        FROM paycheck_configs pc
        LEFT JOIN paycheck_deductions pd ON pc.id = pd.paycheck_config_id
        ORDER BY pc.effective_date DESC, pd.name
    """)
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Gross Amount', 'Pay Frequency', 'Effective Date', 'Current',
                        'Deduction Name', 'Deduction Type', 'Deduction Amount'])
        for row in rows:
            writer.writerow([row['gross_amount'], row['pay_frequency'], row['effective_date'],
                           'Yes' if row['is_current'] else 'No',
                           row['deduction_name'] or '', row['deduction_type'] or '',
                           row['deduction_amount'] if row['deduction_amount'] else ''])

    return len(rows)


def export_shared_expenses(filepath: Path) -> int:
    """Export shared expenses (Lisa payments) to CSV. Returns row count."""
    db = Database()
    cursor = db.execute("""
        SELECT se.name, se.monthly_amount, se.split_type, se.custom_split_ratio,
               rc.name as linked_recurring
        FROM shared_expenses se
        LEFT JOIN recurring_charges rc ON se.linked_recurring_id = rc.id
        ORDER BY se.name
    """)
    rows = cursor.fetchall()

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Monthly Amount', 'Split Type', 'Custom Split Ratio', 'Linked Recurring'])
        for row in rows:
            writer.writerow([row['name'], row['monthly_amount'], row['split_type'],
                           row['custom_split_ratio'] or '', row['linked_recurring'] or ''])

    return len(rows)


def export_all(folder: Path, tables: List[str] = None,
               transaction_start: str = None, transaction_end: str = None) -> Dict[str, int]:
    """Export multiple tables to CSV files.

    Args:
        folder: Directory to save CSV files
        tables: List of table names to export. If None, exports all.
        transaction_start: Optional start date for transactions
        transaction_end: Optional end date for transactions

    Returns:
        Dictionary mapping table names to row counts exported
    """
    all_tables = ['accounts', 'credit_cards', 'loans', 'recurring_charges',
                  'transactions', 'paycheck', 'shared_expenses']

    if tables is None:
        tables = all_tables

    results = {}

    exporters = {
        'accounts': lambda: export_accounts(folder / 'accounts.csv'),
        'credit_cards': lambda: export_credit_cards(folder / 'credit_cards.csv'),
        'loans': lambda: export_loans(folder / 'loans.csv'),
        'recurring_charges': lambda: export_recurring_charges(folder / 'recurring_charges.csv'),
        'transactions': lambda: export_transactions(folder / 'transactions.csv',
                                                     transaction_start, transaction_end),
        'paycheck': lambda: export_paycheck_config(folder / 'paycheck_config.csv'),
        'shared_expenses': lambda: export_shared_expenses(folder / 'shared_expenses.csv'),
    }

    for table in tables:
        if table in exporters:
            results[table] = exporters[table]()

    return results
