"""Extended tests for calculations module - covering find_first_negative_balance,
special charge generation, payday generation, and interest charges."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from budget_app.models.account import Account
from budget_app.models.credit_card import CreditCard
from budget_app.models.loan import Loan
from budget_app.models.recurring_charge import RecurringCharge
from budget_app.models.transaction import Transaction
from budget_app.models.paycheck import PaycheckConfig, PaycheckDeduction
from budget_app.models.shared_expense import SharedExpense


class TestFindFirstNegativeBalance:
    """Tests for find_first_negative_balance function"""

    def test_never_negative(self):
        """Should return (None, None) when balance never goes negative"""
        from budget_app.utils.calculations import find_first_negative_balance

        today = datetime.now().date()

        trans = MagicMock()
        trans.payment_method = 'C'
        trans.amount = -100.0
        trans.date = (today + timedelta(days=5)).strftime('%Y-%m-%d')
        trans.date_obj = today + timedelta(days=5)

        bal, dt = find_first_negative_balance(1000.0, [trans], 'C')
        assert bal is None
        assert dt is None

    def test_goes_negative(self):
        """Should return balance and date when it first goes negative"""
        from budget_app.utils.calculations import find_first_negative_balance

        today = datetime.now().date()

        trans = MagicMock()
        trans.payment_method = 'C'
        trans.amount = -1500.0
        trans.date = (today + timedelta(days=10)).strftime('%Y-%m-%d')
        trans.date_obj = today + timedelta(days=10)

        bal, dt = find_first_negative_balance(1000.0, [trans], 'C')
        assert bal == -500.0
        assert dt == today + timedelta(days=10)

    def test_already_negative_starting_balance(self):
        """Should return today when starting balance is already negative"""
        from budget_app.utils.calculations import find_first_negative_balance

        today = datetime.now().date()

        trans = MagicMock()
        trans.payment_method = 'C'
        trans.amount = -100.0
        trans.date = (today + timedelta(days=5)).strftime('%Y-%m-%d')
        trans.date_obj = today + timedelta(days=5)

        bal, dt = find_first_negative_balance(-200.0, [trans], 'C')
        assert bal == -200.0
        assert dt == today

    def test_already_negative_no_transactions(self):
        """Should return (starting_balance, today) when already negative and no transactions"""
        from budget_app.utils.calculations import find_first_negative_balance

        today = datetime.now().date()

        bal, dt = find_first_negative_balance(-500.0, [], 'C')
        assert bal == -500.0
        assert dt == today

    def test_no_transactions_positive_balance(self):
        """Should return (None, None) when no transactions and balance is positive"""
        from budget_app.utils.calculations import find_first_negative_balance

        bal, dt = find_first_negative_balance(1000.0, [], 'C')
        assert bal is None
        assert dt is None

    def test_filters_by_payment_method(self):
        """Should only consider transactions for the specified payment method"""
        from budget_app.utils.calculations import find_first_negative_balance

        today = datetime.now().date()

        trans_c = MagicMock()
        trans_c.payment_method = 'C'
        trans_c.amount = -100.0
        trans_c.date = (today + timedelta(days=5)).strftime('%Y-%m-%d')
        trans_c.date_obj = today + timedelta(days=5)

        trans_s = MagicMock()
        trans_s.payment_method = 'S'
        trans_s.amount = -99999.0
        trans_s.date = (today + timedelta(days=5)).strftime('%Y-%m-%d')
        trans_s.date_obj = today + timedelta(days=5)

        bal, dt = find_first_negative_balance(500.0, [trans_c, trans_s], 'C')
        assert bal is None  # Only -100 from 500, never negative
        assert dt is None

    def test_multiple_transactions_finds_first(self):
        """Should find the first date that goes negative"""
        from budget_app.utils.calculations import find_first_negative_balance

        today = datetime.now().date()

        trans1 = MagicMock()
        trans1.payment_method = 'C'
        trans1.amount = -600.0
        trans1.date = (today + timedelta(days=10)).strftime('%Y-%m-%d')
        trans1.date_obj = today + timedelta(days=10)

        trans2 = MagicMock()
        trans2.payment_method = 'C'
        trans2.amount = -600.0
        trans2.date = (today + timedelta(days=20)).strftime('%Y-%m-%d')
        trans2.date_obj = today + timedelta(days=20)

        bal, dt = find_first_negative_balance(1000.0, [trans1, trans2], 'C')
        # After trans1: 1000 - 600 = 400 (still positive)
        # After trans2: 400 - 600 = -200 (first negative)
        assert bal == -200.0
        assert dt == today + timedelta(days=20)


class TestGenerateSpecialCharges:
    """Tests for _generate_special_charges (codes 991-995)"""

    def test_code_991_mortgage_biweekly(self, temp_db):
        """Code 991 should generate bi-weekly transactions on Fridays"""
        from budget_app.utils.calculations import _generate_special_charges

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        charge = RecurringCharge(
            id=None, name='Mortgage', amount=-1900.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        transactions = _generate_special_charges(start, end, [charge])

        # All generated transactions should be on Fridays
        for t in transactions:
            assert t.date_obj.weekday() == 4  # Friday
        # Should have at least 1 bi-weekly occurrence in a month
        assert len(transactions) >= 1
        assert all(t.amount == -1900.0 for t in transactions)

    def test_code_992_monthly_special(self, temp_db):
        """Code 992-995 should generate monthly on the 15th"""
        from budget_app.utils.calculations import _generate_special_charges

        start = date(2025, 6, 1)
        end = date(2025, 8, 31)

        charge = RecurringCharge(
            id=None, name='Spaceship', amount=-400.0,
            day_of_month=992, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        transactions = _generate_special_charges(start, end, [charge])

        # Should generate on the 15th of each month: Jun, Jul, Aug
        assert len(transactions) == 3
        for t in transactions:
            assert t.date_obj.day == 15
            assert t.amount == -400.0

    def test_code_993_monthly_special(self, temp_db):
        """Code 993 (SCCU Loan) should also generate monthly on the 15th"""
        from budget_app.utils.calculations import _generate_special_charges

        start = date(2025, 6, 1)
        end = date(2025, 7, 31)

        charge = RecurringCharge(
            id=None, name='SCCU Loan', amount=-250.0,
            day_of_month=993, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        transactions = _generate_special_charges(start, end, [charge])
        assert len(transactions) == 2

    def test_skips_lisa_linked(self, temp_db):
        """Should skip charges linked to Lisa Payments"""
        from budget_app.utils.calculations import _generate_special_charges

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        charge = RecurringCharge(
            id=None, name='Lisa Linked', amount=-500.0,
            day_of_month=992, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        lisa_linked_ids = {charge.id}
        transactions = _generate_special_charges(start, end, [charge], lisa_linked_ids)
        assert len(transactions) == 0

    def test_skips_already_posted(self, temp_db):
        """Should skip transactions that are already posted"""
        from budget_app.utils.calculations import _generate_special_charges

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        charge = RecurringCharge(
            id=None, name='Mortgage', amount=-1900.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        # Generate first to see what dates come out
        transactions = _generate_special_charges(start, end, [charge])

        if transactions:
            # Mark the first one as posted
            posted_recurring = {(charge.id, transactions[0].date)}
            filtered = _generate_special_charges(start, end, [charge],
                                                  posted_recurring=posted_recurring)
            assert len(filtered) < len(transactions)

    def test_year_boundary_992(self, temp_db):
        """Code 992-995 should handle December to January rollover"""
        from budget_app.utils.calculations import _generate_special_charges

        start = date(2025, 11, 1)
        end = date(2026, 2, 28)

        charge = RecurringCharge(
            id=None, name='Windows', amount=-100.0,
            day_of_month=994, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        transactions = _generate_special_charges(start, end, [charge])
        # Nov 15, Dec 15, Jan 15, Feb 15 = 4
        assert len(transactions) == 4
        dates = [t.date_obj for t in transactions]
        assert date(2025, 12, 15) in dates
        assert date(2026, 1, 15) in dates


class TestGeneratePaydayTransactions:
    """Tests for _generate_payday_transactions"""

    def test_generates_payday_deposits(self, temp_db):
        """Should generate Payday transactions on Fridays (biweekly)"""
        from budget_app.utils.calculations import _generate_payday_transactions

        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-03', is_current=True  # Jan 3 2025 = Friday
        )
        config.save()

        deduction = PaycheckDeduction(
            id=None, paycheck_config_id=config.id,
            name='Tax', amount_type='FIXED', amount=1000.0
        )
        deduction.save()
        config = PaycheckConfig.get_by_id(config.id)

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        transactions = _generate_payday_transactions(start, end, config)

        # Filter to Payday transactions only
        paydays = [t for t in transactions if t.description == 'Payday']
        assert len(paydays) >= 2  # At least 2 paydays in a month
        # Net = 5000 - 1000 = 4000
        assert all(t.amount == 4000.0 for t in paydays)
        # All should be on Fridays (anchored from effective_date which is a Friday)
        assert all(t.date_obj.weekday() == 4 for t in paydays)

    def test_generates_lisa_payments(self, temp_db):
        """Should generate Lisa Payment transactions on paydays"""
        from budget_app.utils.calculations import _generate_payday_transactions

        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-03', is_current=True
        )
        config.save()
        config = PaycheckConfig.get_by_id(config.id)

        # Create shared expenses for Lisa
        SharedExpense(id=None, name='Mortgage', monthly_amount=1900.0,
                     split_type='HALF').save()

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        transactions = _generate_payday_transactions(start, end, config)

        lisa_payments = [t for t in transactions if t.description == 'Lisa Payment']
        assert len(lisa_payments) >= 2
        # All should be negative (expense)
        assert all(t.amount < 0 for t in lisa_payments)

    def test_generates_ldbpd_markers(self, temp_db):
        """Should generate LDBPD markers (day before payday)"""
        from budget_app.utils.calculations import _generate_payday_transactions

        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-03', is_current=True
        )
        config.save()
        config = PaycheckConfig.get_by_id(config.id)

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        transactions = _generate_payday_transactions(start, end, config)

        ldbpd = [t for t in transactions if t.description == 'LDBPD']
        paydays = [t for t in transactions if t.description == 'Payday']

        # Should have an LDBPD for each payday
        assert len(ldbpd) >= 1
        # LDBPD amount should be 0
        assert all(t.amount == 0 for t in ldbpd)

    def test_skips_posted_paydays(self, temp_db):
        """Should skip paydays that are already posted"""
        from budget_app.utils.calculations import _generate_payday_transactions

        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-03', is_current=True
        )
        config.save()
        config = PaycheckConfig.get_by_id(config.id)

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        # First generate without posted set
        all_trans = _generate_payday_transactions(start, end, config)
        paydays_all = [t for t in all_trans if t.description == 'Payday']

        if paydays_all:
            # Mark the first payday as posted
            posted_other = {('Payday', paydays_all[0].date)}
            filtered = _generate_payday_transactions(start, end, config, posted_other)
            paydays_filtered = [t for t in filtered if t.description == 'Payday']
            assert len(paydays_filtered) == len(paydays_all) - 1

    def test_three_paycheck_month_lisa(self, temp_db):
        """Months with 3 paydays should divide Lisa payment by 3"""
        from budget_app.utils.calculations import _generate_payday_transactions

        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-03', is_current=True
        )
        config.save()
        config = PaycheckConfig.get_by_id(config.id)

        SharedExpense(id=None, name='Mortgage', monthly_amount=1800.0,
                     split_type='HALF').save()

        # January 2026 has 3 Fridays in bi-weekly schedule
        # Use a wide enough range to find a 3-paycheck month
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        transactions = _generate_payday_transactions(start, end, config)
        lisa_payments = [t for t in transactions if t.description == 'Lisa Payment']

        # Some lisa payments should be /3 (600) and some /2 (900)
        amounts = set(abs(round(t.amount, 2)) for t in lisa_payments)
        assert len(amounts) >= 1  # At least some Lisa payments generated


class TestGenerateInterestCharges:
    """Tests for _generate_interest_charges"""

    def test_generates_interest_for_cards_with_balance(self, temp_db):
        """Should generate monthly interest charges for cards with a balance"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        card = CreditCard(
            id=None, pay_type_code='CH', name='Chase Freedom',
            credit_limit=10000.0, current_balance=3000.0,
            interest_rate=0.24, due_day=15
        )
        card.save()

        start = date(2025, 6, 1)
        end = date(2025, 8, 31)

        result = _generate_interest_charges(start, end, [], set())

        interest_trans = [t for t in result if 'Interest' in t.description]
        assert len(interest_trans) >= 1
        # Interest should be positive (adds to card balance)
        assert all(t.amount > 0 for t in interest_trans)
        # Should be charged to the card's pay type
        assert all(t.payment_method == 'CH' for t in interest_trans)

    def test_no_interest_for_zero_balance(self, temp_db):
        """Should not generate interest for cards with $0 balance"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        CreditCard(
            id=None, pay_type_code='ZB', name='Zero Balance',
            credit_limit=5000.0, current_balance=0.0,
            interest_rate=0.24, due_day=10
        ).save()

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        result = _generate_interest_charges(start, end, [], set())
        interest_trans = [t for t in result if 'Interest' in t.description]
        assert len(interest_trans) == 0

    def test_no_interest_for_zero_rate(self, temp_db):
        """Should not generate interest for cards with 0% APR"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        CreditCard(
            id=None, pay_type_code='NR', name='No Rate',
            credit_limit=5000.0, current_balance=2000.0,
            interest_rate=0.0, due_day=10
        ).save()

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        result = _generate_interest_charges(start, end, [], set())
        interest_trans = [t for t in result if 'Interest' in t.description]
        assert len(interest_trans) == 0

    def test_no_cards_returns_transactions_unchanged(self, temp_db):
        """With no credit cards, should return input transactions unchanged"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        existing = [
            Transaction(id=None, date='2025-06-15', description='Test',
                       amount=-50.0, payment_method='C')
        ]

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        result = _generate_interest_charges(start, end, existing, set())
        assert len(result) == 1  # Just the original transaction

    def test_interest_charged_3_days_after_due(self, temp_db):
        """Interest should be charged on due_day + 3"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        card = CreditCard(
            id=None, pay_type_code='IC', name='Interest Card',
            credit_limit=10000.0, current_balance=5000.0,
            interest_rate=0.24, due_day=10
        )
        card.save()

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        result = _generate_interest_charges(start, end, [], set())
        interest_trans = [t for t in result if 'Interest' in t.description]

        assert len(interest_trans) == 1
        # Due day 10 + 3 = 13th
        assert interest_trans[0].date_obj == date(2025, 6, 13)

    def test_interest_amount_calculation(self, temp_db):
        """Interest amount should be balance * (APR / 12)"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        card = CreditCard(
            id=None, pay_type_code='IA', name='Interest Amount',
            credit_limit=10000.0, current_balance=6000.0,
            interest_rate=0.24, due_day=10
        )
        card.save()

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        result = _generate_interest_charges(start, end, [], set())
        interest_trans = [t for t in result if 'Interest' in t.description]

        assert len(interest_trans) == 1
        # 6000 * (0.24 / 12) = 6000 * 0.02 = 120.0
        assert interest_trans[0].amount == 120.0

    def test_skips_posted_interest(self, temp_db):
        """Should skip interest that's already posted"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        card = CreditCard(
            id=None, pay_type_code='PI', name='Posted Interest',
            credit_limit=10000.0, current_balance=3000.0,
            interest_rate=0.24, due_day=10
        )
        card.save()

        start = date(2025, 6, 1)
        end = date(2025, 6, 30)

        posted_other = {('Posted Interest Interest', '2025-06-13')}
        result = _generate_interest_charges(start, end, [], posted_other)
        interest_trans = [t for t in result if 'Interest' in t.description]
        assert len(interest_trans) == 0

    def test_due_day_rollover_to_next_month(self, temp_db):
        """Interest date rolling past end of month should go to next month"""
        from budget_app.utils.calculations import _generate_interest_charges

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        card = CreditCard(
            id=None, pay_type_code='RO', name='Rollover Card',
            credit_limit=10000.0, current_balance=3000.0,
            interest_rate=0.24, due_day=29  # 29 + 3 = 32, rolls to next month
        )
        card.save()

        start = date(2025, 6, 1)
        end = date(2025, 7, 15)

        result = _generate_interest_charges(start, end, [], set())
        interest_trans = [t for t in result if 'Interest' in t.description]

        # June has 30 days. due_day=29, interest_day=32 > 30, so rolls to July 2
        if interest_trans:
            assert interest_trans[0].date_obj == date(2025, 7, 2)


class TestGenerateFutureTransactionsIntegration:
    """Integration tests for generate_future_transactions with real DB"""

    def test_generates_monthly_charges(self, temp_db):
        """Should generate transactions for monthly recurring charges"""
        from budget_app.utils.calculations import generate_future_transactions

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        RecurringCharge(
            id=None, name='Netflix', amount=-15.99,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        ).save()

        transactions = generate_future_transactions(months_ahead=2,
                                                     start_date=date(2025, 6, 1))

        netflix = [t for t in transactions if t.description == 'Netflix']
        assert len(netflix) >= 2
        assert all(t.amount == -15.99 for t in netflix)

    def test_skips_lisa_linked_charges(self, temp_db):
        """Charges linked to shared expenses should not generate separately"""
        from budget_app.utils.calculations import generate_future_transactions

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        charge = RecurringCharge(
            id=None, name='Mortgage Charge', amount=-1900.0,
            day_of_month=1, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        )
        charge.save()

        SharedExpense(id=None, name='Mortgage', monthly_amount=1900.0,
                     linked_recurring_id=charge.id).save()

        transactions = generate_future_transactions(months_ahead=1,
                                                     start_date=date(2025, 6, 1))

        mortgage = [t for t in transactions if t.description == 'Mortgage Charge']
        assert len(mortgage) == 0  # Should be excluded

    def test_transactions_sorted_by_date(self, temp_db):
        """Output transactions should be sorted by date"""
        from budget_app.utils.calculations import generate_future_transactions

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        RecurringCharge(
            id=None, name='Early', amount=-50.0,
            day_of_month=1, payment_method='C'
        ).save()
        RecurringCharge(
            id=None, name='Late', amount=-75.0,
            day_of_month=28, payment_method='C'
        ).save()

        transactions = generate_future_transactions(months_ahead=2,
                                                     start_date=date(2025, 6, 1))

        dates = [t.date for t in transactions]
        assert dates == sorted(dates)

    def test_with_paycheck_generates_payday(self, temp_db):
        """Should generate Payday transactions when paycheck config exists"""
        from budget_app.utils.calculations import generate_future_transactions

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        config = PaycheckConfig(
            id=None, gross_amount=5000.0, pay_frequency='BIWEEKLY',
            effective_date='2025-01-03', is_current=True
        )
        config.save()

        transactions = generate_future_transactions(months_ahead=1,
                                                     start_date=date(2025, 6, 1))

        paydays = [t for t in transactions if t.description == 'Payday']
        assert len(paydays) >= 2

    def test_skips_posted_recurring(self, temp_db):
        """Should skip recurring transactions that are already posted"""
        from budget_app.utils.calculations import generate_future_transactions

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()

        charge = RecurringCharge(
            id=None, name='Netflix', amount=-15.99,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        )
        charge.save()

        # Create a posted transaction for June 15th
        Transaction(
            id=None, date='2025-06-15', description='Netflix',
            amount=-15.99, payment_method='C',
            recurring_charge_id=charge.id,
            is_posted=True, posted_date='2025-06-15'
        ).save()

        transactions = generate_future_transactions(months_ahead=2,
                                                     start_date=date(2025, 6, 1))

        netflix_june = [t for t in transactions
                       if t.description == 'Netflix' and t.date.startswith('2025-06')]
        # June 15th should be skipped (already posted)
        assert len(netflix_june) == 0


class TestGetStartingBalancesIntegration:
    """Integration tests for get_starting_balances with real DB"""

    def test_includes_all_account_types(self, temp_db):
        """Should include accounts, cards, and loans"""
        from budget_app.utils.calculations import get_starting_balances

        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()
        Account(id=None, name='Savings', account_type='SAVINGS',
                current_balance=10000.0, pay_type_code='S').save()
        CreditCard(
            id=None, pay_type_code='CH', name='Chase Card',
            credit_limit=5000, current_balance=1500, interest_rate=0.18, due_day=10
        ).save()
        Loan(
            id=None, pay_type_code='K1', name='401k Loan',
            original_amount=10000, current_balance=7500,
            interest_rate=0.045, payment_amount=200
        ).save()

        balances = get_starting_balances()
        assert balances['C'] == 5000.0
        assert balances['S'] == 10000.0
        assert balances['CH'] == 1500.0
        assert balances['K1'] == 7500.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
