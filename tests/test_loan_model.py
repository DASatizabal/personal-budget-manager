"""Unit tests for Loan model"""

import pytest
from budget_app.models.loan import Loan


class TestLoanProperties:
    """Tests for Loan computed properties"""

    def test_monthly_interest(self, temp_db):
        """monthly_interest = (balance * rate) / 12"""
        loan = Loan(
            id=None, pay_type_code='K1', name='401k Loan',
            original_amount=10000.0, current_balance=6000.0,
            interest_rate=0.06, payment_amount=200.0
        )
        loan.save()
        # (6000 * 0.06) / 12 = 30.0
        assert loan.monthly_interest == 30.0

    def test_monthly_interest_zero_balance(self, temp_db):
        """monthly_interest should be 0 when balance is 0"""
        loan = Loan(
            id=None, pay_type_code='K1', name='Paid Off Loan',
            original_amount=10000.0, current_balance=0.0,
            interest_rate=0.06, payment_amount=200.0
        )
        loan.save()
        assert loan.monthly_interest == 0.0

    def test_remaining_payments(self, temp_db):
        """remaining_payments = int(balance / payment) + 1"""
        loan = Loan(
            id=None, pay_type_code='K1', name='401k Loan',
            original_amount=10000.0, current_balance=1000.0,
            interest_rate=0.045, payment_amount=200.0
        )
        loan.save()
        # int(1000 / 200) + 1 = 6
        assert loan.remaining_payments == 6

    def test_remaining_payments_zero_payment(self, temp_db):
        """remaining_payments should be 0 when payment is 0"""
        loan = Loan(
            id=None, pay_type_code='K1', name='Stalled Loan',
            original_amount=10000.0, current_balance=5000.0,
            interest_rate=0.045, payment_amount=0.0
        )
        loan.save()
        assert loan.remaining_payments == 0


class TestLoanCRUD:
    """Tests for Loan CRUD operations"""

    def test_save_and_retrieve(self, temp_db):
        """Loan should be saveable and retrievable by ID"""
        loan = Loan(
            id=None, pay_type_code='K1', name='401k Loan 1',
            original_amount=10000.0, current_balance=7500.0,
            interest_rate=0.045, payment_amount=200.0,
            start_date='2024-01-01', end_date='2027-01-01'
        )
        loan.save()

        retrieved = Loan.get_by_id(loan.id)
        assert retrieved is not None
        assert retrieved.name == '401k Loan 1'
        assert retrieved.current_balance == 7500.0
        assert retrieved.interest_rate == 0.045
        assert retrieved.start_date == '2024-01-01'

    def test_get_by_code(self, temp_db):
        """get_by_code should return loan matching pay_type_code"""
        loan = Loan(
            id=None, pay_type_code='K2', name='401k Loan 2',
            original_amount=5000.0, current_balance=3000.0,
            interest_rate=0.05, payment_amount=150.0
        )
        loan.save()

        retrieved = Loan.get_by_code('K2')
        assert retrieved is not None
        assert retrieved.name == '401k Loan 2'

    def test_get_by_code_not_found(self, temp_db):
        """get_by_code should return None for nonexistent code"""
        assert Loan.get_by_code('NOPE') is None

    def test_delete(self, temp_db):
        """Deleted loan should not be retrievable"""
        loan = Loan(
            id=None, pay_type_code='K1', name='Deletable Loan',
            original_amount=5000.0, current_balance=2000.0,
            interest_rate=0.04, payment_amount=100.0
        )
        loan.save()
        loan_id = loan.id

        loan.delete()
        assert Loan.get_by_id(loan_id) is None

    def test_get_total_balance(self, temp_db):
        """get_total_balance should sum all loan balances"""
        Loan(
            id=None, pay_type_code='K1', name='Loan 1',
            original_amount=10000.0, current_balance=5000.0,
            interest_rate=0.04, payment_amount=100.0
        ).save()
        Loan(
            id=None, pay_type_code='K2', name='Loan 2',
            original_amount=8000.0, current_balance=3000.0,
            interest_rate=0.05, payment_amount=150.0
        ).save()

        assert Loan.get_total_balance() == 8000.0

    def test_get_total_balance_empty(self, temp_db):
        """get_total_balance should return 0 with no loans"""
        assert Loan.get_total_balance() == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
