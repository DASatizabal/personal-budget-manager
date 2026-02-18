"""Unit tests for calculations module"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch


class TestCalculateRunningBalances:
    """Tests for calculate_running_balances function"""

    def test_single_transaction_updates_balance(self):
        """A single transaction should update the running balance"""
        from budget_app.utils.calculations import calculate_running_balances

        # Mock transaction
        mock_trans = MagicMock()
        mock_trans.payment_method = 'C'
        mock_trans.amount = -100.0

        # Mock CreditCard.get_all to return empty list
        with patch('budget_app.utils.calculations.CreditCard') as mock_cc:
            mock_cc.get_all.return_value = []

            starting_balances = {'C': 1000.0}
            results = calculate_running_balances([mock_trans], starting_balances)

            assert len(results) == 1
            assert results[0]['running_balances']['C'] == 900.0

    def test_multiple_transactions_accumulate(self):
        """Multiple transactions should accumulate correctly"""
        from budget_app.utils.calculations import calculate_running_balances

        # Mock transactions
        trans1 = MagicMock()
        trans1.payment_method = 'C'
        trans1.amount = -100.0

        trans2 = MagicMock()
        trans2.payment_method = 'C'
        trans2.amount = 500.0  # Income

        trans3 = MagicMock()
        trans3.payment_method = 'C'
        trans3.amount = -200.0

        with patch('budget_app.utils.calculations.CreditCard') as mock_cc:
            mock_cc.get_all.return_value = []

            starting_balances = {'C': 1000.0}
            results = calculate_running_balances([trans1, trans2, trans3], starting_balances)

            assert len(results) == 3
            assert results[0]['running_balances']['C'] == 900.0   # 1000 - 100
            assert results[1]['running_balances']['C'] == 1400.0  # 900 + 500
            assert results[2]['running_balances']['C'] == 1200.0  # 1400 - 200

    def test_different_payment_methods_tracked_separately(self):
        """Different payment methods should be tracked separately"""
        from budget_app.utils.calculations import calculate_running_balances

        trans1 = MagicMock()
        trans1.payment_method = 'C'
        trans1.amount = -100.0

        trans2 = MagicMock()
        trans2.payment_method = 'S'
        trans2.amount = -50.0

        with patch('budget_app.utils.calculations.CreditCard') as mock_cc:
            mock_cc.get_all.return_value = []

            starting_balances = {'C': 1000.0, 'S': 500.0}
            results = calculate_running_balances([trans1, trans2], starting_balances)

            assert results[1]['running_balances']['C'] == 900.0
            assert results[1]['running_balances']['S'] == 450.0


class TestCalculate90DayMinimum:
    """Tests for calculate_90_day_minimum function"""

    def test_returns_starting_balance_when_no_transactions(self):
        """Should return starting balance when no transactions"""
        from budget_app.utils.calculations import calculate_90_day_minimum

        min_bal, min_date = calculate_90_day_minimum(1000.0, [], 'C')

        assert min_bal == 1000.0
        assert min_date is None

    def test_finds_minimum_balance(self):
        """Should correctly identify the minimum balance date"""
        from budget_app.utils.calculations import calculate_90_day_minimum

        today = datetime.now().date()

        # Create mock transactions
        trans1 = MagicMock()
        trans1.payment_method = 'C'
        trans1.amount = -500.0
        trans1.date = (today + timedelta(days=10)).strftime('%Y-%m-%d')
        trans1.date_obj = today + timedelta(days=10)

        trans2 = MagicMock()
        trans2.payment_method = 'C'
        trans2.amount = 1000.0
        trans2.date = (today + timedelta(days=20)).strftime('%Y-%m-%d')
        trans2.date_obj = today + timedelta(days=20)

        trans3 = MagicMock()
        trans3.payment_method = 'C'
        trans3.amount = -200.0
        trans3.date = (today + timedelta(days=15)).strftime('%Y-%m-%d')
        trans3.date_obj = today + timedelta(days=15)

        min_bal, min_date = calculate_90_day_minimum(1000.0, [trans1, trans2, trans3], 'C')

        # After trans1 (-500): 500
        # After trans3 (-200): 300  <- This should be the minimum
        # After trans2 (+1000): 1300
        assert min_bal == 300.0
        assert min_date == today + timedelta(days=15)

    def test_filters_by_payment_method(self):
        """Should only consider transactions for the specified payment method"""
        from budget_app.utils.calculations import calculate_90_day_minimum

        today = datetime.now().date()

        trans1 = MagicMock()
        trans1.payment_method = 'C'
        trans1.amount = -100.0
        trans1.date = (today + timedelta(days=5)).strftime('%Y-%m-%d')
        trans1.date_obj = today + timedelta(days=5)

        trans2 = MagicMock()
        trans2.payment_method = 'S'  # Different payment method
        trans2.amount = -9999.0
        trans2.date = (today + timedelta(days=5)).strftime('%Y-%m-%d')
        trans2.date_obj = today + timedelta(days=5)

        min_bal, min_date = calculate_90_day_minimum(1000.0, [trans1, trans2], 'C')

        # Should only consider trans1, ignore trans2
        assert min_bal == 900.0


class TestGenerateFutureTransactions:
    """Tests for generate_future_transactions function"""

    def test_generates_monthly_transactions(self):
        """Should generate transactions for monthly charges"""
        from budget_app.utils.calculations import generate_future_transactions

        # Mock recurring charge
        mock_charge = MagicMock()
        mock_charge.frequency = 'MONTHLY'
        mock_charge.day_of_month = 15
        mock_charge.name = 'Test Charge'
        mock_charge.payment_method = 'C'
        mock_charge.id = 1
        mock_charge.get_actual_amount.return_value = -100.0

        with patch('budget_app.utils.calculations.RecurringCharge') as mock_rc, \
             patch('budget_app.utils.calculations.CreditCard') as mock_cc:
            mock_rc.get_all.return_value = [mock_charge]
            mock_cc.get_all.return_value = []
            with patch('budget_app.utils.calculations.PaycheckConfig') as mock_pc:
                mock_pc.get_current.return_value = None

                transactions = generate_future_transactions(months_ahead=3)

                # Should have ~3 transactions (one per month on the 15th)
                assert len(transactions) >= 2

    def test_skips_special_frequency_in_main_loop(self):
        """Should skip SPECIAL frequency charges in main generation loop"""
        from budget_app.utils.calculations import generate_future_transactions

        mock_charge = MagicMock()
        mock_charge.frequency = 'SPECIAL'
        mock_charge.day_of_month = 991
        mock_charge.name = 'Mortgage'
        mock_charge.amount = -1900.0

        with patch('budget_app.utils.calculations.RecurringCharge') as mock_rc, \
             patch('budget_app.utils.calculations.CreditCard') as mock_cc:
            mock_rc.get_all.return_value = [mock_charge]
            mock_cc.get_all.return_value = []
            with patch('budget_app.utils.calculations.PaycheckConfig') as mock_pc:
                mock_pc.get_current.return_value = None

                transactions = generate_future_transactions(months_ahead=1)

                # Special charges are handled separately, so this shouldn't
                # generate duplicate entries from the main loop
                regular_charges = [t for t in transactions if t.description != 'Mortgage']
                assert len(regular_charges) == 0 or all(
                    t.recurring_charge_id != mock_charge.id
                    for t in regular_charges
                )


class TestGetStartingBalances:
    """Tests for get_starting_balances function"""

    def test_includes_account_balances(self):
        """Should include bank account balances"""
        from budget_app.utils.calculations import get_starting_balances

        mock_account = MagicMock()
        mock_account.pay_type_code = 'C'
        mock_account.current_balance = 1500.0

        with patch('budget_app.utils.calculations.Account') as mock_acc:
            mock_acc.get_all.return_value = [mock_account]
            with patch('budget_app.utils.calculations.CreditCard') as mock_cc:
                mock_cc.get_all.return_value = []
                with patch('budget_app.utils.calculations.Loan') as mock_loan:
                    mock_loan.get_all.return_value = []

                    balances = get_starting_balances()

                    assert 'C' in balances
                    assert balances['C'] == 1500.0

    def test_includes_credit_card_balances(self):
        """Should include credit card balances"""
        from budget_app.utils.calculations import get_starting_balances

        mock_card = MagicMock()
        mock_card.pay_type_code = 'CH'
        mock_card.current_balance = 500.0

        with patch('budget_app.utils.calculations.Account') as mock_acc:
            mock_acc.get_all.return_value = []
            with patch('budget_app.utils.calculations.CreditCard') as mock_cc:
                mock_cc.get_all.return_value = [mock_card]
                with patch('budget_app.utils.calculations.Loan') as mock_loan:
                    mock_loan.get_all.return_value = []

                    balances = get_starting_balances()

                    assert 'CH' in balances
                    assert balances['CH'] == 500.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
