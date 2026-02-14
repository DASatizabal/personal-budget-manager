"""Extended tests for RecurringCharge model (linked cards, special charges, etc.)"""

import pytest
from budget_app.models.recurring_charge import RecurringCharge
from budget_app.models.credit_card import CreditCard
from budget_app.models.transaction import Transaction
from budget_app.models.shared_expense import SharedExpense


class TestGetActualAmount:
    """Tests for get_actual_amount with linked card resolution"""

    def test_fixed_amount_returns_stored(self, temp_db):
        """FIXED amount type should return the stored amount"""
        charge = RecurringCharge(
            id=None, name='Netflix', amount=-15.99,
            day_of_month=15, payment_method='CH',
            amount_type='FIXED'
        )
        charge.save()
        assert charge.get_actual_amount() == -15.99

    def test_credit_card_balance_resolves_to_min_payment(self, temp_db):
        """CREDIT_CARD_BALANCE should return -card.min_payment"""
        card = CreditCard(
            id=None, pay_type_code='CH', name='Chase Freedom',
            credit_limit=10000.0, current_balance=3000.0,
            interest_rate=0.1899, due_day=15,
            min_payment_type='FIXED', min_payment_amount=75.0
        )
        card.save()

        charge = RecurringCharge(
            id=None, name='Chase Freedom Payment',
            amount=0, day_of_month=15, payment_method='C',
            amount_type='CREDIT_CARD_BALANCE',
            linked_card_id=card.id
        )
        charge.save()

        assert charge.get_actual_amount() == -75.0

    def test_calculated_resolves_to_min_payment(self, temp_db):
        """CALCULATED should also return -card.min_payment"""
        card = CreditCard(
            id=None, pay_type_code='WY', name='Wyndham',
            credit_limit=5000.0, current_balance=2000.0,
            interest_rate=0.22, due_day=20,
            min_payment_type='FIXED', min_payment_amount=50.0
        )
        card.save()

        charge = RecurringCharge(
            id=None, name='Wyndham Payment',
            amount=0, day_of_month=20, payment_method='C',
            amount_type='CALCULATED',
            linked_card_id=card.id
        )
        charge.save()

        assert charge.get_actual_amount() == -50.0

    def test_linked_card_missing_falls_back_to_amount(self, temp_db):
        """If linked card doesn't exist, should return stored amount"""
        # Create a card, link a charge, then delete the card
        card = CreditCard(
            id=None, pay_type_code='DEL', name='Deleted Card',
            credit_limit=5000.0, current_balance=1000.0,
            interest_rate=0.18, due_day=10
        )
        card.save()
        card_id = card.id

        charge = RecurringCharge(
            id=None, name='Ghost Card Payment',
            amount=-100.0, day_of_month=15, payment_method='C',
            amount_type='CALCULATED',
            linked_card_id=card_id
        )
        charge.save()

        # Delete the card (unlinks the charge's linked_card_id to NULL)
        card.delete()

        # Reload charge from DB to get updated linked_card_id=NULL
        charge = RecurringCharge.get_by_id(charge.id)
        # With linked_card_id=NULL, CALCULATED type falls through to stored amount
        assert charge.get_actual_amount() == -100.0


class TestRecurringChargeDelete:
    """Tests for delete operation (unlinking)"""

    def test_delete_unlinks_transactions(self, temp_db):
        """Deleting a charge should unlink (not delete) its transactions"""
        charge = RecurringCharge(
            id=None, name='Test Charge', amount=-50.0,
            day_of_month=10, payment_method='C'
        )
        charge.save()

        trans = Transaction(
            id=None, date='2025-06-10', description='Test Charge',
            amount=-50.0, payment_method='C',
            recurring_charge_id=charge.id
        )
        trans.save()

        charge.delete()

        # Transaction should still exist but with recurring_charge_id = NULL
        retrieved = Transaction.get_by_id(trans.id)
        assert retrieved is not None
        assert retrieved.recurring_charge_id is None

    def test_delete_unlinks_shared_expenses(self, temp_db):
        """Deleting a charge should unlink shared expenses"""
        charge = RecurringCharge(
            id=None, name='Mortgage', amount=-1900.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL'
        )
        charge.save()

        expense = SharedExpense(
            id=None, name='Mortgage', monthly_amount=1900.0,
            linked_recurring_id=charge.id
        )
        expense.save()

        charge.delete()

        # Shared expense should still exist but unlinked
        retrieved = SharedExpense.get_by_id(expense.id)
        assert retrieved is not None
        assert retrieved.linked_recurring_id is None


class TestRecurringChargeQueries:
    """Tests for query methods"""

    def test_get_all_active_only(self, temp_db):
        """get_all(active_only=True) should exclude inactive charges"""
        RecurringCharge(
            id=None, name='Active', amount=-50.0,
            day_of_month=5, payment_method='C', is_active=True
        ).save()
        RecurringCharge(
            id=None, name='Inactive', amount=-30.0,
            day_of_month=10, payment_method='C', is_active=False
        ).save()

        active = RecurringCharge.get_all(active_only=True)
        all_charges = RecurringCharge.get_all(active_only=False)

        assert len(active) == 1
        assert active[0].name == 'Active'
        assert len(all_charges) == 2

    def test_get_special_charges(self, temp_db):
        """get_special_charges should return only charges with day >= 991"""
        RecurringCharge(
            id=None, name='Netflix', amount=-15.99,
            day_of_month=15, payment_method='CH'
        ).save()
        RecurringCharge(
            id=None, name='Mortgage', amount=-1900.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL'
        ).save()
        RecurringCharge(
            id=None, name='Payday', amount=2500.0,
            day_of_month=999, payment_method='C',
            frequency='SPECIAL'
        ).save()

        specials = RecurringCharge.get_special_charges()
        assert len(specials) == 2
        names = {c.name for c in specials}
        assert 'Mortgage' in names
        assert 'Payday' in names
        assert 'Netflix' not in names

    def test_get_by_day(self, temp_db):
        """get_by_day should return active charges on that day"""
        RecurringCharge(
            id=None, name='Netflix', amount=-15.99,
            day_of_month=15, payment_method='CH'
        ).save()
        RecurringCharge(
            id=None, name='Gym', amount=-30.0,
            day_of_month=15, payment_method='C'
        ).save()
        RecurringCharge(
            id=None, name='Other', amount=-20.0,
            day_of_month=1, payment_method='C'
        ).save()

        day_15 = RecurringCharge.get_by_day(15)
        assert len(day_15) == 2


class TestCreditCardAutoSync:
    """Tests for CC save auto-syncing linked recurring charges"""

    def test_new_card_creates_recurring_charge(self, temp_db):
        """Saving a new card should auto-create a linked recurring charge"""
        card = CreditCard(
            id=None, pay_type_code='NEW', name='New Card',
            credit_limit=5000.0, current_balance=0.0,
            interest_rate=0.18, due_day=20
        )
        card.save()

        # Should have created a linked recurring charge
        from budget_app.models.database import Database
        db = Database()
        row = db.execute(
            "SELECT * FROM recurring_charges WHERE linked_card_id = ?",
            (card.id,)
        ).fetchone()
        assert row is not None
        assert dict(row)['day_of_month'] == 20
        assert dict(row)['amount_type'] == 'CALCULATED'

    def test_updating_card_syncs_due_day(self, temp_db):
        """Updating a card's due_day should sync to linked recurring charge"""
        card = CreditCard(
            id=None, pay_type_code='SYN', name='Sync Card',
            credit_limit=5000.0, current_balance=0.0,
            interest_rate=0.18, due_day=15
        )
        card.save()

        # Change due day and save
        card.due_day = 25
        card.save()

        # Linked charge should now have day_of_month=25
        from budget_app.models.database import Database
        db = Database()
        row = db.execute(
            "SELECT day_of_month FROM recurring_charges WHERE linked_card_id = ?",
            (card.id,)
        ).fetchone()
        assert row is not None
        assert dict(row)['day_of_month'] == 25


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
