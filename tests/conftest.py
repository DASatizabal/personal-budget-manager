"""Shared test fixtures for budget_app tests"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    from budget_app.models import database
    original_path = database.DB_PATH
    database.DB_PATH = Path(path)

    # Reset the singleton
    database.Database._instance = None
    database.Database._connection = None

    # Initialize the database
    database.init_db()

    yield path

    # Cleanup
    database.Database._instance = None
    database.Database._connection = None
    database.DB_PATH = original_path

    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def sample_account(temp_db):
    """Create a sample checking account"""
    from budget_app.models.account import Account
    account = Account(
        id=None, name='Chase', account_type='CHECKING',
        current_balance=5000.0, pay_type_code='C'
    )
    account.save()
    return account


@pytest.fixture
def sample_card(temp_db):
    """Create a sample credit card"""
    from budget_app.models.credit_card import CreditCard
    card = CreditCard(
        id=None, pay_type_code='CH', name='Chase Freedom',
        credit_limit=10000.0, current_balance=3000.0,
        interest_rate=0.1899, due_day=15
    )
    card.save()
    return card


@pytest.fixture
def sample_loan(temp_db):
    """Create a sample loan"""
    from budget_app.models.loan import Loan
    loan = Loan(
        id=None, pay_type_code='K1', name='401k Loan 1',
        original_amount=10000.0, current_balance=7500.0,
        interest_rate=0.045, payment_amount=200.0,
        start_date='2024-01-01', end_date='2027-01-01'
    )
    loan.save()
    return loan


@pytest.fixture
def sample_recurring_charge(temp_db):
    """Create a sample recurring charge"""
    from budget_app.models.recurring_charge import RecurringCharge
    charge = RecurringCharge(
        id=None, name='Netflix', amount=-15.99,
        day_of_month=15, payment_method='CH',
        frequency='MONTHLY', amount_type='FIXED'
    )
    charge.save()
    return charge


@pytest.fixture
def multiple_cards(temp_db):
    """Create multiple cards with varying utilizations for color threshold testing"""
    from budget_app.models.credit_card import CreditCard
    cards = []
    for code, name, limit, balance, rate, due in [
        ('CH', 'Chase Freedom', 10000, 3000, 0.1899, 15),
        ('AM', 'Amex Blue', 5000, 4500, 0.2199, 20),
        ('DC', 'Discover', 8000, 3200, 0.1599, 10),
        ('CI', 'Citi', 15000, 0, 0.1299, 25),
    ]:
        card = CreditCard(
            id=None, pay_type_code=code, name=name,
            credit_limit=limit, current_balance=balance,
            interest_rate=rate, due_day=due
        )
        card.save()
        cards.append(card)
    return cards


@pytest.fixture
def sample_paycheck_config(temp_db):
    """Create a paycheck config with deductions"""
    from budget_app.models.paycheck import PaycheckConfig, PaycheckDeduction
    config = PaycheckConfig(
        id=None, gross_amount=3500.0,
        pay_frequency='BIWEEKLY',
        effective_date='2026-01-09',
        is_current=True, pay_day_of_week=4
    )
    config.save()

    d1 = PaycheckDeduction(
        id=None, paycheck_config_id=config.id,
        name='Federal Tax', amount_type='PERCENTAGE', amount=0.22
    )
    d1.save()
    d2 = PaycheckDeduction(
        id=None, paycheck_config_id=config.id,
        name='Health Insurance', amount_type='FIXED', amount=250.0
    )
    d2.save()

    # Refresh to get deductions loaded
    config = PaycheckConfig.get_by_id(config.id)
    return config


@pytest.fixture
def sample_shared_expenses(temp_db):
    """Create shared expenses for testing"""
    from budget_app.models.shared_expense import SharedExpense
    expenses = []
    for name, amount, split_type in [
        ('Rent', 2000.0, 'HALF'),
        ('Utilities', 300.0, 'THIRD'),
    ]:
        e = SharedExpense(id=None, name=name, monthly_amount=amount, split_type=split_type)
        e.save()
        expenses.append(e)
    return expenses


@pytest.fixture
def sample_deferred_purchase(temp_db):
    """Create a deferred interest purchase linked to a card"""
    from budget_app.models.credit_card import CreditCard
    from budget_app.models.deferred_interest import DeferredPurchase
    card = CreditCard(
        id=None, pay_type_code='DP', name='Deferred Card',
        credit_limit=10000.0, current_balance=3000.0,
        interest_rate=0.2999, due_day=15
    )
    card.save()
    purchase = DeferredPurchase(
        id=None, credit_card_id=card.id,
        description='Best Buy TV', purchase_amount=1500.0,
        remaining_balance=1200.0, promo_apr=0.0,
        standard_apr=0.2999, promo_end_date='2027-06-15',
        min_monthly_payment=50.0
    )
    purchase.save()
    return purchase


@pytest.fixture
def sample_transactions(temp_db):
    """Create a mix of transactions for testing"""
    from budget_app.models.transaction import Transaction
    transactions = []
    data = [
        ('2026-02-01', 'Paycheck', 2500.0, 'C', False),
        ('2026-02-05', 'Groceries', -150.0, 'C', False),
        ('2026-02-10', 'Netflix', -15.99, 'CH', False),
        ('2026-01-15', 'Old Payment', -200.0, 'C', True),
    ]
    for date, desc, amount, method, posted in data:
        t = Transaction(
            id=None, date=date, description=desc,
            amount=amount, payment_method=method,
            is_posted=posted,
            posted_date='2026-01-20' if posted else None
        )
        t.save()
        transactions.append(t)
    return transactions


@pytest.fixture
def mock_qmessagebox(monkeypatch):
    """Mock QMessageBox to avoid blocking dialogs. Returns tracker."""
    from unittest.mock import MagicMock
    from PyQt6.QtWidgets import QMessageBox

    tracker = MagicMock()
    tracker.last_return = QMessageBox.StandardButton.Yes

    def mock_warning(parent, title, text, buttons=None, **kwargs):
        tracker.warning_called = True
        tracker.warning_title = title
        tracker.warning_text = text
        return tracker.last_return

    def mock_question(parent, title, text, buttons=None, **kwargs):
        tracker.question_called = True
        tracker.question_title = title
        tracker.question_text = text
        return tracker.last_return

    def mock_information(parent, title, text, **kwargs):
        tracker.info_called = True
        tracker.info_title = title
        tracker.info_text = text

    def mock_critical(parent, title, text, buttons=None, **kwargs):
        tracker.critical_called = True
        tracker.critical_title = title
        tracker.critical_text = text
        return tracker.last_return

    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(mock_warning))
    monkeypatch.setattr(QMessageBox, 'question', staticmethod(mock_question))
    monkeypatch.setattr(QMessageBox, 'information', staticmethod(mock_information))
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(mock_critical))

    return tracker
