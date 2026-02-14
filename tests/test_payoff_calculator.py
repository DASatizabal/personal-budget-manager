"""Unit tests for Credit Card Payoff Calculator"""

import pytest
from budget_app.utils.payoff_calculator import (
    CardPayoffInfo,
    calculate_minimum_payment,
    calculate_avalanche,
    calculate_snowball,
    calculate_hybrid,
    calculate_high_utilization,
    calculate_cash_on_hand,
    calculate_all_methods,
)


class TestCardPayoffInfo:
    """Tests for CardPayoffInfo dataclass properties"""

    def test_utilization(self):
        """utilization = balance / credit_limit"""
        card = CardPayoffInfo(
            card_id=1, name='Test', balance=2500.0,
            apr=0.20, min_payment=50.0, credit_limit=10000.0
        )
        assert card.utilization == 0.25

    def test_utilization_zero_limit(self):
        """utilization should be 0 when credit_limit is 0"""
        card = CardPayoffInfo(
            card_id=1, name='Test', balance=0,
            apr=0.20, min_payment=50.0, credit_limit=0
        )
        assert card.utilization == 0.0

    def test_monthly_interest_rate(self):
        """monthly_interest_rate = apr / 12"""
        card = CardPayoffInfo(
            card_id=1, name='Test', balance=1000.0,
            apr=0.24, min_payment=50.0, credit_limit=5000.0
        )
        assert card.monthly_interest_rate == pytest.approx(0.02)


class TestCalculateMinimumPayment:
    """Tests for calculate_minimum_payment function"""

    def test_standard_calculation(self):
        """Standard: 1% of balance + monthly interest, min $25"""
        # balance=5000, apr=0.24
        # monthly_interest = 5000 * (0.24/12) = 100
        # calculated = 5000 * 0.01 + 100 = 150
        # max(150, min(25, 5000)) = max(150, 25) = 150
        result = calculate_minimum_payment(5000.0, 0.24)
        assert result == pytest.approx(150.0)

    def test_25_dollar_floor(self):
        """Small balances should still get at least $25 minimum"""
        # balance=1000, apr=0.12
        # monthly_interest = 1000 * (0.12/12) = 10
        # calculated = 1000 * 0.01 + 10 = 20
        # max(20, min(25, 1000)) = max(20, 25) = 25
        result = calculate_minimum_payment(1000.0, 0.12)
        assert result == 25.0

    def test_balance_less_than_25(self):
        """When balance < $25, min payment should be the balance itself"""
        # balance=15, apr=0.20
        # monthly_interest = 15 * (0.20/12) = 0.25
        # calculated = 15 * 0.01 + 0.25 = 0.40
        # max(0.40, min(25, 15)) = max(0.40, 15) = 15
        result = calculate_minimum_payment(15.0, 0.20)
        assert result == 15.0

    def test_fixed_min_payment(self):
        """Fixed min payment should be used when provided"""
        result = calculate_minimum_payment(5000.0, 0.24, fixed_min=100.0)
        assert result == 100.0

    def test_fixed_min_capped_at_balance(self):
        """Fixed min should not exceed balance"""
        result = calculate_minimum_payment(50.0, 0.24, fixed_min=100.0)
        assert result == 50.0


class TestAvalancheStrategy:
    """Tests for Avalanche (highest APR first) strategy"""

    def test_highest_apr_paid_first(self):
        """Card with highest APR should be in payoff order first"""
        cards = [
            CardPayoffInfo(card_id=1, name='Low APR', balance=1000.0,
                          apr=0.10, min_payment=25.0, credit_limit=5000.0),
            CardPayoffInfo(card_id=2, name='High APR', balance=1000.0,
                          apr=0.25, min_payment=25.0, credit_limit=5000.0),
        ]
        result = calculate_avalanche(cards, monthly_extra=200.0)
        assert result.method == "Avalanche"
        assert result.card_payoff_order[0] == 'High APR'

    def test_produces_payoff_result(self):
        """Should produce a complete PayoffResult"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=500.0,
                          apr=0.18, min_payment=25.0, credit_limit=2000.0),
        ]
        result = calculate_avalanche(cards, monthly_extra=100.0)
        assert result.months_to_payoff > 0
        assert result.total_interest > 0
        assert result.total_payments > 0
        assert len(result.payment_schedule) > 0


class TestSnowballStrategy:
    """Tests for Snowball (lowest balance first) strategy"""

    def test_lowest_balance_paid_first(self):
        """Card with lowest balance should be in payoff order first"""
        cards = [
            CardPayoffInfo(card_id=1, name='Big Balance', balance=5000.0,
                          apr=0.20, min_payment=50.0, credit_limit=10000.0),
            CardPayoffInfo(card_id=2, name='Small Balance', balance=200.0,
                          apr=0.15, min_payment=25.0, credit_limit=1000.0),
        ]
        result = calculate_snowball(cards, monthly_extra=200.0)
        assert result.method == "Snowball"
        assert result.card_payoff_order[0] == 'Small Balance'


class TestHybridStrategy:
    """Tests for Hybrid (60% APR + 40% balance) strategy"""

    def test_produces_result(self):
        """Hybrid should produce valid results"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=3000.0,
                          apr=0.22, min_payment=50.0, credit_limit=5000.0),
            CardPayoffInfo(card_id=2, name='Card B', balance=500.0,
                          apr=0.15, min_payment=25.0, credit_limit=2000.0),
        ]
        result = calculate_hybrid(cards, monthly_extra=100.0)
        assert result.method == "Hybrid"
        assert result.months_to_payoff > 0
        assert len(result.card_payoff_order) == 2

    def test_high_apr_low_balance_first(self):
        """A card with high APR and low balance should score well"""
        cards = [
            CardPayoffInfo(card_id=1, name='Low APR Big', balance=5000.0,
                          apr=0.10, min_payment=50.0, credit_limit=10000.0),
            CardPayoffInfo(card_id=2, name='High APR Small', balance=500.0,
                          apr=0.28, min_payment=25.0, credit_limit=2000.0),
        ]
        result = calculate_hybrid(cards, monthly_extra=200.0)
        # High APR + Low balance = highest hybrid score
        assert result.card_payoff_order[0] == 'High APR Small'


class TestHighUtilizationStrategy:
    """Tests for High Utilization strategy"""

    def test_highest_utilization_paid_first(self):
        """Card with highest utilization should receive extra payments first"""
        cards = [
            CardPayoffInfo(card_id=1, name='Low Util', balance=1000.0,
                          apr=0.20, min_payment=25.0, credit_limit=20000.0),  # 5%
            CardPayoffInfo(card_id=2, name='High Util', balance=900.0,
                          apr=0.18, min_payment=25.0, credit_limit=1000.0),  # 90%
        ]
        result = calculate_high_utilization(cards, monthly_extra=200.0)
        assert result.method == "High Utilization"
        # High Util (90%) should be paid off first because it gets the extra payments
        assert result.card_payoff_order[0] == 'High Util'


class TestCashOnHandStrategy:
    """Tests for Cash on Hand (minimums only) strategy"""

    def test_minimums_only(self):
        """Cash on hand should result in highest interest (no extra payments)"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=3000.0,
                          apr=0.22, min_payment=50.0, credit_limit=5000.0),
        ]
        avalanche_result = calculate_avalanche(cards, monthly_extra=200.0)
        cash_result = calculate_cash_on_hand(cards, monthly_extra=200.0)

        assert cash_result.method == "Cash on Hand"
        # Cash on hand should take longer and cost more interest
        assert cash_result.total_interest >= avalanche_result.total_interest
        assert cash_result.months_to_payoff >= avalanche_result.months_to_payoff


class TestCalculateAllMethods:
    """Tests for calculate_all_methods orchestrator"""

    def test_returns_five_results(self):
        """Should return exactly 5 strategy results"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=2000.0,
                          apr=0.20, min_payment=50.0, credit_limit=5000.0),
        ]
        results = calculate_all_methods(cards, monthly_extra=100.0)
        assert len(results) == 5

    def test_sorted_by_total_interest(self):
        """Results should be sorted by total interest (lowest first)"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=3000.0,
                          apr=0.22, min_payment=50.0, credit_limit=5000.0),
            CardPayoffInfo(card_id=2, name='Card B', balance=1000.0,
                          apr=0.15, min_payment=25.0, credit_limit=3000.0),
        ]
        results = calculate_all_methods(cards, monthly_extra=100.0)
        interests = [r.total_interest for r in results]
        assert interests == sorted(interests)

    def test_all_methods_named(self):
        """Each result should have a method name"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=1000.0,
                          apr=0.18, min_payment=25.0, credit_limit=3000.0),
        ]
        results = calculate_all_methods(cards, monthly_extra=50.0)
        method_names = {r.method for r in results}
        assert method_names == {'Avalanche', 'Snowball', 'Hybrid', 'High Utilization', 'Cash on Hand'}


class TestEdgeCases:
    """Edge case tests for payoff calculator"""

    def test_empty_cards_list(self):
        """Should handle empty card list gracefully"""
        result = calculate_avalanche([], monthly_extra=100.0)
        assert result.months_to_payoff == 0
        assert result.total_interest == 0
        assert result.total_payments == 0

    def test_zero_balance_cards_filtered(self):
        """Cards with $0 balance should be filtered out"""
        cards = [
            CardPayoffInfo(card_id=1, name='Paid Off', balance=0.0,
                          apr=0.20, min_payment=0.0, credit_limit=5000.0),
            CardPayoffInfo(card_id=2, name='Has Balance', balance=1000.0,
                          apr=0.18, min_payment=25.0, credit_limit=3000.0),
        ]
        result = calculate_avalanche(cards, monthly_extra=100.0)
        assert 'Paid Off' not in result.card_payoff_order
        assert 'Has Balance' in result.card_payoff_order

    def test_single_card_payoff(self):
        """Single card should produce clean payoff schedule"""
        cards = [
            CardPayoffInfo(card_id=1, name='Only Card', balance=500.0,
                          apr=0.18, min_payment=25.0, credit_limit=2000.0),
        ]
        result = calculate_avalanche(cards, monthly_extra=500.0)
        assert result.months_to_payoff >= 1
        assert result.card_payoff_order == ['Only Card']

    def test_large_extra_payment_pays_off_quickly(self):
        """Large extra payment should result in fast payoff"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=100.0,
                          apr=0.18, min_payment=25.0, credit_limit=5000.0),
        ]
        result = calculate_avalanche(cards, monthly_extra=1000.0)
        assert result.months_to_payoff == 1

    def test_schedule_entries_have_correct_fields(self):
        """Payment schedule entries should have all required fields"""
        cards = [
            CardPayoffInfo(card_id=1, name='Card A', balance=500.0,
                          apr=0.18, min_payment=25.0, credit_limit=2000.0),
        ]
        result = calculate_avalanche(cards, monthly_extra=100.0)
        entry = result.payment_schedule[0]
        assert hasattr(entry, 'date')
        assert hasattr(entry, 'card_name')
        assert hasattr(entry, 'amount')
        assert hasattr(entry, 'principal')
        assert hasattr(entry, 'interest')
        assert hasattr(entry, 'remaining_balance')
        assert entry.amount > 0
        assert entry.remaining_balance >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
