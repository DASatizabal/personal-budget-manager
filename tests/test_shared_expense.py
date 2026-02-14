"""Unit tests for SharedExpense model"""

import pytest
from budget_app.models.shared_expense import SharedExpense
from budget_app.models.recurring_charge import RecurringCharge


class TestSharedExpenseSplitAmount:
    """Tests for get_split_amount calculation"""

    def test_half_split_two_paychecks(self, temp_db):
        """HALF split with 2 paychecks = monthly / 2"""
        expense = SharedExpense(
            id=None, name='Mortgage', monthly_amount=1900.0, split_type='HALF'
        )
        assert expense.get_split_amount(2) == 950.0

    def test_third_split(self, temp_db):
        """THIRD split = monthly / 3"""
        expense = SharedExpense(
            id=None, name='Utilities', monthly_amount=300.0, split_type='THIRD'
        )
        assert expense.get_split_amount(2) == 100.0  # THIRD always divides by 3

    def test_three_paychecks_forces_third(self, temp_db):
        """With 3 paychecks, HALF split should divide by 3"""
        expense = SharedExpense(
            id=None, name='Mortgage', monthly_amount=1800.0, split_type='HALF'
        )
        # paycheck_count=3 triggers the THIRD branch
        assert expense.get_split_amount(3) == 600.0

    def test_custom_split_ratio(self, temp_db):
        """CUSTOM split = monthly * ratio / paycheck_count"""
        expense = SharedExpense(
            id=None, name='Rent', monthly_amount=2000.0,
            split_type='CUSTOM', custom_split_ratio=0.6
        )
        # 2000 * 0.6 / 2 = 600
        assert expense.get_split_amount(2) == 600.0

    def test_custom_split_three_paychecks(self, temp_db):
        """CUSTOM split with 3 paychecks"""
        expense = SharedExpense(
            id=None, name='Rent', monthly_amount=2000.0,
            split_type='CUSTOM', custom_split_ratio=0.6
        )
        # 2000 * 0.6 / 3 = 400
        assert expense.get_split_amount(3) == pytest.approx(400.0)

    def test_default_split_is_half(self, temp_db):
        """Default split_type should behave as HALF"""
        expense = SharedExpense(
            id=None, name='Default', monthly_amount=1000.0
        )
        assert expense.get_split_amount(2) == 500.0


class TestSharedExpenseCRUD:
    """Tests for SharedExpense CRUD operations"""

    def test_save_and_retrieve(self, temp_db):
        """SharedExpense should be saveable and retrievable"""
        expense = SharedExpense(
            id=None, name='Mortgage', monthly_amount=1900.0, split_type='HALF'
        )
        expense.save()

        retrieved = SharedExpense.get_by_id(expense.id)
        assert retrieved is not None
        assert retrieved.name == 'Mortgage'
        assert retrieved.monthly_amount == 1900.0

    def test_delete(self, temp_db):
        """Deleted expense should not be retrievable"""
        expense = SharedExpense(
            id=None, name='Deletable', monthly_amount=100.0
        )
        expense.save()
        eid = expense.id

        expense.delete()
        assert SharedExpense.get_by_id(eid) is None

    def test_get_all(self, temp_db):
        """get_all should return all expenses ordered by name"""
        SharedExpense(id=None, name='Zales', monthly_amount=50.0).save()
        SharedExpense(id=None, name='Aetna', monthly_amount=200.0).save()

        expenses = SharedExpense.get_all()
        assert len(expenses) == 2
        assert expenses[0].name == 'Aetna'  # alphabetical
        assert expenses[1].name == 'Zales'

    def test_get_total_monthly(self, temp_db):
        """get_total_monthly should sum all monthly amounts"""
        SharedExpense(id=None, name='Mortgage', monthly_amount=1900.0).save()
        SharedExpense(id=None, name='Spaceship', monthly_amount=400.0).save()

        assert SharedExpense.get_total_monthly() == 2300.0

    def test_get_total_monthly_empty(self, temp_db):
        """get_total_monthly should return 0 with no expenses"""
        assert SharedExpense.get_total_monthly() == 0.0

    def test_calculate_lisa_payment_two_paychecks(self, temp_db):
        """calculate_lisa_payment should sum split amounts for all expenses"""
        SharedExpense(id=None, name='Mortgage', monthly_amount=1900.0, split_type='HALF').save()
        SharedExpense(id=None, name='Spaceship', monthly_amount=400.0, split_type='HALF').save()

        # (1900/2) + (400/2) = 950 + 200 = 1150
        assert SharedExpense.calculate_lisa_payment(2) == 1150.0

    def test_calculate_lisa_payment_three_paychecks(self, temp_db):
        """calculate_lisa_payment with 3 paychecks uses /3"""
        SharedExpense(id=None, name='Mortgage', monthly_amount=1800.0, split_type='HALF').save()
        SharedExpense(id=None, name='Spaceship', monthly_amount=300.0, split_type='HALF').save()

        # (1800/3) + (300/3) = 600 + 100 = 700
        assert SharedExpense.calculate_lisa_payment(3) == pytest.approx(700.0)

    def test_get_linked_recurring_ids(self, temp_db):
        """get_linked_recurring_ids should return set of linked charge IDs"""
        charge = RecurringCharge(
            id=None, name='Mortgage', amount=-1900.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        SharedExpense(
            id=None, name='Mortgage', monthly_amount=1900.0,
            linked_recurring_id=charge.id
        ).save()
        SharedExpense(
            id=None, name='Unlinked', monthly_amount=100.0
        ).save()

        ids = SharedExpense.get_linked_recurring_ids()
        assert charge.id in ids
        assert len(ids) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
