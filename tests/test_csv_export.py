"""Unit tests for CSV export functionality"""

import pytest
import csv
import tempfile
import os
from pathlib import Path
from budget_app.models.account import Account
from budget_app.models.credit_card import CreditCard
from budget_app.models.loan import Loan
from budget_app.models.recurring_charge import RecurringCharge
from budget_app.models.transaction import Transaction
from budget_app.models.shared_expense import SharedExpense
from budget_app.models.paycheck import PaycheckConfig, PaycheckDeduction
from budget_app.utils.csv_export import (
    export_accounts,
    export_credit_cards,
    export_loans,
    export_recurring_charges,
    export_transactions,
    export_paycheck_config,
    export_shared_expenses,
    export_all,
)


@pytest.fixture
def export_dir():
    """Create a temp directory for CSV exports"""
    d = tempfile.mkdtemp()
    yield Path(d)
    # Cleanup
    import shutil
    shutil.rmtree(d, ignore_errors=True)


def _read_csv(filepath):
    """Read CSV and return (headers, rows)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)
    return headers, rows


class TestExportAccounts:
    """Tests for export_accounts"""

    def test_exports_accounts(self, temp_db, export_dir):
        """Should export accounts with correct headers and data"""
        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()
        Account(id=None, name='Savings', account_type='SAVINGS',
                current_balance=10000.0, pay_type_code='S').save()

        filepath = export_dir / 'accounts.csv'
        count = export_accounts(filepath)

        assert count == 2
        headers, rows = _read_csv(filepath)
        assert headers == ['Name', 'Account Type', 'Current Balance', 'Pay Type Code']
        assert len(rows) == 2

    def test_empty_accounts(self, temp_db, export_dir):
        """Should handle empty table gracefully"""
        filepath = export_dir / 'accounts.csv'
        count = export_accounts(filepath)
        assert count == 0
        headers, rows = _read_csv(filepath)
        assert len(rows) == 0


class TestExportCreditCards:
    """Tests for export_credit_cards"""

    def test_exports_credit_cards(self, temp_db, export_dir):
        """Should export credit cards with correct data"""
        CreditCard(
            id=None, pay_type_code='CH', name='Chase Freedom',
            credit_limit=10000.0, current_balance=3000.0,
            interest_rate=0.1899, due_day=15,
            min_payment_type='CALCULATED'
        ).save()

        filepath = export_dir / 'credit_cards.csv'
        count = export_credit_cards(filepath)

        assert count == 1
        headers, rows = _read_csv(filepath)
        assert 'Name' in headers
        assert rows[0][1] == 'Chase Freedom'  # name column


class TestExportTransactions:
    """Tests for export_transactions with date filtering"""

    def test_exports_all_transactions(self, temp_db, export_dir):
        """Should export all transactions when no date filter"""
        Transaction(id=None, date='2025-01-15', description='Payday',
                   amount=2500.0, payment_method='C').save()
        Transaction(id=None, date='2025-02-15', description='Netflix',
                   amount=-15.99, payment_method='CH').save()

        filepath = export_dir / 'transactions.csv'
        count = export_transactions(filepath)
        assert count == 2

    def test_exports_with_start_date(self, temp_db, export_dir):
        """Should filter transactions by start_date"""
        Transaction(id=None, date='2025-01-01', description='Old',
                   amount=-50.0, payment_method='C').save()
        Transaction(id=None, date='2025-06-15', description='New',
                   amount=-75.0, payment_method='C').save()

        filepath = export_dir / 'transactions.csv'
        count = export_transactions(filepath, start_date='2025-06-01')
        assert count == 1
        _, rows = _read_csv(filepath)
        assert rows[0][1] == 'New'

    def test_exports_with_date_range(self, temp_db, export_dir):
        """Should filter transactions by start and end date"""
        Transaction(id=None, date='2025-01-01', description='Too Early',
                   amount=-50.0, payment_method='C').save()
        Transaction(id=None, date='2025-03-15', description='In Range',
                   amount=-75.0, payment_method='C').save()
        Transaction(id=None, date='2025-12-01', description='Too Late',
                   amount=-100.0, payment_method='C').save()

        filepath = export_dir / 'transactions.csv'
        count = export_transactions(filepath, start_date='2025-02-01', end_date='2025-06-30')
        assert count == 1

    def test_posted_field_yes_no(self, temp_db, export_dir):
        """Posted field should display as 'Yes' or 'No'"""
        Transaction(id=None, date='2025-01-15', description='Posted',
                   amount=-50.0, payment_method='C', is_posted=True).save()
        Transaction(id=None, date='2025-01-16', description='Unposted',
                   amount=-30.0, payment_method='C', is_posted=False).save()

        filepath = export_dir / 'transactions.csv'
        export_transactions(filepath)
        _, rows = _read_csv(filepath)

        posted_values = {row[1]: row[4] for row in rows}
        assert posted_values['Posted'] == 'Yes'
        assert posted_values['Unposted'] == 'No'


class TestExportLoans:
    """Tests for export_loans"""

    def test_exports_loans(self, temp_db, export_dir):
        """Should export loans with correct data"""
        Loan(id=None, pay_type_code='K1', name='401k Loan',
             original_amount=10000.0, current_balance=7500.0,
             interest_rate=0.045, payment_amount=200.0).save()

        filepath = export_dir / 'loans.csv'
        count = export_loans(filepath)
        assert count == 1
        headers, rows = _read_csv(filepath)
        assert 'Original Amount' in headers


class TestExportRecurringCharges:
    """Tests for export_recurring_charges"""

    def test_exports_with_linked_card_name(self, temp_db, export_dir):
        """Should resolve linked card name in export"""
        card = CreditCard(
            id=None, pay_type_code='CH', name='Chase Freedom',
            credit_limit=10000.0, current_balance=3000.0,
            interest_rate=0.1899, due_day=15
        )
        card.save()

        # The card.save() auto-creates a linked recurring charge
        filepath = export_dir / 'recurring_charges.csv'
        count = export_recurring_charges(filepath)
        assert count >= 1
        _, rows = _read_csv(filepath)
        # The auto-created charge should have the linked card name
        linked_cards = [row[6] for row in rows]  # linked_card column
        assert 'Chase Freedom' in linked_cards


class TestExportAll:
    """Tests for export_all batch export"""

    def test_exports_selected_tables(self, temp_db, export_dir):
        """Should export only the specified tables"""
        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        results = export_all(export_dir, tables=['accounts'])
        assert 'accounts' in results
        assert results['accounts'] == 1
        assert (export_dir / 'accounts.csv').exists()

    def test_exports_all_tables_by_default(self, temp_db, export_dir):
        """Should export all tables when tables=None"""
        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        results = export_all(export_dir)
        assert 'accounts' in results
        assert 'credit_cards' in results
        assert 'transactions' in results
        assert len(results) == 7

    def test_ignores_unknown_table(self, temp_db, export_dir):
        """Should ignore table names not in the exporter map"""
        results = export_all(export_dir, tables=['nonexistent'])
        assert 'nonexistent' not in results


class TestExportPaycheckConfig:
    """Tests for export_paycheck_config"""

    def test_exports_paycheck_with_deductions(self, temp_db, export_dir):
        """Should export paycheck config joined with deductions"""
        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-01', is_current=True
        )
        config.save()
        PaycheckDeduction(
            id=None, paycheck_config_id=config.id,
            name='Tax', amount_type='FIXED', amount=500.0
        ).save()

        filepath = export_dir / 'paycheck_config.csv'
        count = export_paycheck_config(filepath)
        assert count >= 1
        _, rows = _read_csv(filepath)
        assert any('Tax' in row[4] for row in rows)


class TestExportSharedExpenses:
    """Tests for export_shared_expenses"""

    def test_exports_shared_expenses(self, temp_db, export_dir):
        """Should export shared expenses with correct data"""
        SharedExpense(id=None, name='Mortgage', monthly_amount=1900.0,
                     split_type='HALF').save()

        filepath = export_dir / 'shared_expenses.csv'
        count = export_shared_expenses(filepath)
        assert count == 1
        headers, rows = _read_csv(filepath)
        assert rows[0][0] == 'Mortgage'
        assert rows[0][2] == 'HALF'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
