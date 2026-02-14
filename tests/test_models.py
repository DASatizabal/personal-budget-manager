"""Unit tests for budget_app models"""

import pytest


class TestCreditCardModel:
    """Tests for CreditCard model"""

    def test_available_credit_calculation(self, temp_db):
        """Available credit should be limit minus balance"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None,
            pay_type_code='TEST',
            name='Test Card',
            credit_limit=10000.0,
            current_balance=3000.0,
            interest_rate=0.1899,
            due_day=15
        )
        card.save()

        assert card.available_credit == 7000.0

    def test_utilization_calculation(self, temp_db):
        """Utilization should be balance divided by limit"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None,
            pay_type_code='TEST',
            name='Test Card',
            credit_limit=10000.0,
            current_balance=2500.0,
            interest_rate=0.1899,
            due_day=15
        )
        card.save()

        assert card.utilization == 0.25

    def test_utilization_with_zero_limit(self, temp_db):
        """Utilization should be 0 when limit is 0"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None,
            pay_type_code='TEST',
            name='Test Card',
            credit_limit=0,
            current_balance=0,
            interest_rate=0,
            due_day=1
        )
        card.save()

        assert card.utilization == 0

    def test_min_payment_fixed(self, temp_db):
        """Min payment should return fixed amount when set"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None,
            pay_type_code='TEST',
            name='Test Card',
            credit_limit=10000.0,
            current_balance=5000.0,
            interest_rate=0.1899,
            due_day=15,
            min_payment_type='FIXED',
            min_payment_amount=100.0
        )
        card.save()

        assert card.min_payment == 100.0

    def test_min_payment_full_balance(self, temp_db):
        """Min payment should be full balance when type is FULL_BALANCE"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None,
            pay_type_code='TEST',
            name='Test Card',
            credit_limit=10000.0,
            current_balance=500.0,
            interest_rate=0.1899,
            due_day=15,
            min_payment_type='FULL_BALANCE'
        )
        card.save()

        assert card.min_payment == 500.0

    def test_save_and_retrieve(self, temp_db):
        """Card should be saveable and retrievable"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None,
            pay_type_code='SAVE',
            name='Save Test Card',
            credit_limit=5000.0,
            current_balance=1000.0,
            interest_rate=0.15,
            due_day=20
        )
        card.save()

        # Retrieve
        retrieved = CreditCard.get_by_id(card.id)
        assert retrieved is not None
        assert retrieved.name == 'Save Test Card'
        assert retrieved.credit_limit == 5000.0

    def test_get_all_returns_all_cards(self, temp_db):
        """get_all should return all saved cards"""
        from budget_app.models.credit_card import CreditCard

        card1 = CreditCard(
            id=None, pay_type_code='C1', name='Card 1',
            credit_limit=1000, current_balance=100, interest_rate=0.1, due_day=1
        )
        card1.save()

        card2 = CreditCard(
            id=None, pay_type_code='C2', name='Card 2',
            credit_limit=2000, current_balance=200, interest_rate=0.2, due_day=2
        )
        card2.save()

        all_cards = CreditCard.get_all()
        assert len(all_cards) == 2

    def test_monthly_interest(self, temp_db):
        """monthly_interest = (balance * rate) / 12"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None, pay_type_code='MI', name='Interest Card',
            credit_limit=10000.0, current_balance=6000.0,
            interest_rate=0.24, due_day=10
        )
        card.save()
        # (6000 * 0.24) / 12 = 120.0
        assert card.monthly_interest == 120.0

    def test_min_payment_calculated(self, temp_db):
        """CALCULATED min payment = max(1% balance + monthly interest, min($25, balance))"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None, pay_type_code='MC', name='Calc Card',
            credit_limit=10000.0, current_balance=5000.0,
            interest_rate=0.24, due_day=15,
            min_payment_type='CALCULATED'
        )
        card.save()
        # monthly_interest = (5000 * 0.24) / 12 = 100
        # base = 5000 * 0.01 + 100 = 150
        # max(150, min(25, 5000)) = max(150, 25) = 150
        assert card.min_payment == 150.0

    def test_min_payment_calculated_small_balance(self, temp_db):
        """CALCULATED min payment with small balance should use $25 floor"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None, pay_type_code='SM', name='Small Card',
            credit_limit=5000.0, current_balance=1000.0,
            interest_rate=0.12, due_day=10,
            min_payment_type='CALCULATED'
        )
        card.save()
        # monthly_interest = (1000 * 0.12) / 12 = 10
        # base = 1000 * 0.01 + 10 = 20
        # max(20, min(25, 1000)) = max(20, 25) = 25
        assert card.min_payment == 25.0

    def test_get_by_id_returns_none(self, temp_db):
        """get_by_id should return None for nonexistent ID"""
        from budget_app.models.credit_card import CreditCard

        assert CreditCard.get_by_id(99999) is None

    def test_get_by_code(self, temp_db):
        """get_by_code should return the card matching pay_type_code"""
        from budget_app.models.credit_card import CreditCard

        card = CreditCard(
            id=None, pay_type_code='GBC', name='Get By Code Card',
            credit_limit=3000.0, current_balance=500.0,
            interest_rate=0.15, due_day=5
        )
        card.save()

        retrieved = CreditCard.get_by_code('GBC')
        assert retrieved is not None
        assert retrieved.name == 'Get By Code Card'

    def test_get_by_code_returns_none(self, temp_db):
        """get_by_code should return None for nonexistent code"""
        from budget_app.models.credit_card import CreditCard

        assert CreditCard.get_by_code('NOPE') is None

    def test_get_total_balance(self, temp_db):
        """get_total_balance should sum all card balances"""
        from budget_app.models.credit_card import CreditCard

        CreditCard(
            id=None, pay_type_code='T1', name='Card 1',
            credit_limit=5000, current_balance=1000, interest_rate=0.1, due_day=1
        ).save()
        CreditCard(
            id=None, pay_type_code='T2', name='Card 2',
            credit_limit=5000, current_balance=2500, interest_rate=0.2, due_day=2
        ).save()

        assert CreditCard.get_total_balance() == 3500.0

    def test_get_total_credit_limit(self, temp_db):
        """get_total_credit_limit should sum all card limits"""
        from budget_app.models.credit_card import CreditCard

        CreditCard(
            id=None, pay_type_code='L1', name='Card 1',
            credit_limit=5000, current_balance=0, interest_rate=0.1, due_day=1
        ).save()
        CreditCard(
            id=None, pay_type_code='L2', name='Card 2',
            credit_limit=8000, current_balance=0, interest_rate=0.2, due_day=2
        ).save()

        assert CreditCard.get_total_credit_limit() == 13000.0

    def test_get_total_utilization(self, temp_db):
        """get_total_utilization = total_balance / total_limit"""
        from budget_app.models.credit_card import CreditCard

        CreditCard(
            id=None, pay_type_code='U1', name='Card 1',
            credit_limit=10000, current_balance=2000, interest_rate=0.1, due_day=1
        ).save()
        CreditCard(
            id=None, pay_type_code='U2', name='Card 2',
            credit_limit=10000, current_balance=3000, interest_rate=0.2, due_day=2
        ).save()

        # (2000 + 3000) / (10000 + 10000) = 5000 / 20000 = 0.25
        assert CreditCard.get_total_utilization() == 0.25

    def test_get_total_utilization_no_cards(self, temp_db):
        """get_total_utilization should be 0 with no cards"""
        from budget_app.models.credit_card import CreditCard

        assert CreditCard.get_total_utilization() == 0.0

    def test_create_card_without_due_day_no_recurring_charge(self, temp_db):
        """New card without due_day should not create a recurring charge"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.database import Database

        card = CreditCard(
            id=None, pay_type_code='ND', name='No Due Day',
            credit_limit=5000, current_balance=0,
            interest_rate=0.18, due_day=None
        )
        card.save()

        db = Database()
        row = db.execute(
            "SELECT COUNT(*) FROM recurring_charges WHERE linked_card_id = ?",
            (card.id,)
        ).fetchone()
        assert row[0] == 0

    def test_delete_card_unlinks_recurring_charges(self, temp_db):
        """Deleting a card should set linked_card_id to NULL on recurring charges"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.database import Database

        card = CreditCard(
            id=None, pay_type_code='DL', name='Delete Me',
            credit_limit=5000, current_balance=1000,
            interest_rate=0.18, due_day=15
        )
        card.save()
        card_id = card.id

        # Verify recurring charge was created
        db = Database()
        row = db.execute(
            "SELECT id FROM recurring_charges WHERE linked_card_id = ?",
            (card_id,)
        ).fetchone()
        assert row is not None
        charge_id = row[0]

        # Delete the card
        card.delete()

        # Recurring charge should still exist but unlinked
        row = db.execute(
            "SELECT linked_card_id FROM recurring_charges WHERE id = ?",
            (charge_id,)
        ).fetchone()
        assert row is not None
        assert row[0] is None


class TestAccountModel:
    """Tests for Account model"""

    def test_save_and_retrieve(self, temp_db):
        """Account should be saveable and retrievable"""
        from budget_app.models.account import Account

        account = Account(
            id=None,
            name='Test Checking',
            account_type='CHECKING',
            current_balance=5000.0,
            pay_type_code='TC'
        )
        account.save()

        retrieved = Account.get_by_id(account.id)
        assert retrieved is not None
        assert retrieved.name == 'Test Checking'
        assert retrieved.current_balance == 5000.0

    def test_get_checking_account(self, temp_db):
        """get_checking_account should return checking account"""
        from budget_app.models.account import Account

        checking = Account(
            id=None,
            name='Chase',
            account_type='CHECKING',
            current_balance=1500.0,
            pay_type_code='C'
        )
        checking.save()

        savings = Account(
            id=None,
            name='Savings',
            account_type='SAVINGS',
            current_balance=5000.0,
            pay_type_code='S'
        )
        savings.save()

        result = Account.get_checking_account()
        assert result is not None
        assert result.account_type == 'CHECKING'


class TestTransactionModel:
    """Tests for Transaction model"""

    def test_date_obj_property(self, temp_db):
        """date_obj should return a date object"""
        from budget_app.models.transaction import Transaction

        trans = Transaction(
            id=None,
            date='2025-06-15',
            description='Test Transaction',
            amount=-100.0,
            payment_method='C'
        )
        trans.save()

        from datetime import date
        assert trans.date_obj == date(2025, 6, 15)

    def test_save_and_retrieve(self, temp_db):
        """Transaction should be saveable and retrievable"""
        from budget_app.models.transaction import Transaction

        trans = Transaction(
            id=None,
            date='2025-06-15',
            description='Test Transaction',
            amount=-150.0,
            payment_method='C'
        )
        trans.save()

        retrieved = Transaction.get_by_id(trans.id)
        assert retrieved is not None
        assert retrieved.description == 'Test Transaction'
        assert retrieved.amount == -150.0


class TestRecurringChargeModel:
    """Tests for RecurringCharge model"""

    def test_get_actual_amount_fixed(self, temp_db):
        """Fixed amount type should return the stored amount"""
        from budget_app.models.recurring_charge import RecurringCharge

        charge = RecurringCharge(
            id=None,
            name='Netflix',
            amount=15.99,
            day_of_month=15,
            payment_method='CH',
            amount_type='FIXED'
        )
        charge.save()

        # get_actual_amount returns the charge amount as stored
        assert charge.get_actual_amount() == 15.99

    def test_save_and_retrieve(self, temp_db):
        """Recurring charge should be saveable and retrievable"""
        from budget_app.models.recurring_charge import RecurringCharge

        charge = RecurringCharge(
            id=None,
            name='Test Charge',
            amount=50.0,
            day_of_month=1,
            payment_method='C'
        )
        charge.save()

        retrieved = RecurringCharge.get_by_id(charge.id)
        assert retrieved is not None
        assert retrieved.name == 'Test Charge'
        assert retrieved.amount == 50.0


class TestPaycheckConfigModel:
    """Tests for PaycheckConfig model"""

    def test_net_pay_calculation(self, temp_db):
        """Net pay should be gross minus deductions"""
        from budget_app.models.paycheck import PaycheckConfig, PaycheckDeduction

        config = PaycheckConfig(
            id=None,
            gross_amount=5000.0,
            pay_frequency='BIWEEKLY',
            effective_date='2025-01-01',
            is_current=True
        )
        config.save()

        # Add deductions
        deduction1 = PaycheckDeduction(
            id=None,
            paycheck_config_id=config.id,
            name='Tax',
            amount_type='FIXED',
            amount=500.0
        )
        deduction1.save()

        deduction2 = PaycheckDeduction(
            id=None,
            paycheck_config_id=config.id,
            name='Insurance',
            amount_type='FIXED',
            amount=200.0
        )
        deduction2.save()

        # Refresh config to get deductions
        config = PaycheckConfig.get_by_id(config.id)

        # Net = 5000 - 500 - 200 = 4300
        assert config.net_pay == 4300.0

    def test_percentage_deductions(self, temp_db):
        """Percentage deductions should calculate correctly"""
        from budget_app.models.paycheck import PaycheckConfig, PaycheckDeduction

        config = PaycheckConfig(
            id=None,
            gross_amount=4000.0,
            pay_frequency='BIWEEKLY',
            effective_date='2025-01-01',
            is_current=True
        )
        config.save()

        # 10% deduction
        deduction = PaycheckDeduction(
            id=None,
            paycheck_config_id=config.id,
            name='401k',
            amount_type='PERCENTAGE',
            amount=0.10  # 10%
        )
        deduction.save()

        config = PaycheckConfig.get_by_id(config.id)

        # Net = 4000 - (4000 * 0.10) = 4000 - 400 = 3600
        assert config.net_pay == 3600.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
