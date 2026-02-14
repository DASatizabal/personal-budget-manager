"""Unit tests for DeferredPurchase model"""

import pytest
from datetime import date, timedelta
from budget_app.models.deferred_interest import DeferredPurchase
from budget_app.models.credit_card import CreditCard


def _make_card(temp_db):
    """Helper to create a card for FK constraint"""
    card = CreditCard(
        id=None, pay_type_code='MC', name='MicroCenter',
        credit_limit=5000.0, current_balance=2000.0,
        interest_rate=0.2499, due_day=10
    )
    card.save()
    return card


def _make_purchase(card_id, days_until_expiry=180, remaining=1000.0,
                   min_payment=50.0, purchase_amount=2000.0,
                   standard_apr=0.2499, created_date=None):
    """Helper to build a DeferredPurchase with a calculated promo_end_date"""
    end_date = (date.today() + timedelta(days=days_until_expiry)).strftime("%Y-%m-%d")
    if created_date is None:
        created_date = (date.today() - timedelta(days=180)).strftime("%Y-%m-%d")
    return DeferredPurchase(
        id=None,
        credit_card_id=card_id,
        description='Test Purchase',
        purchase_amount=purchase_amount,
        remaining_balance=remaining,
        promo_apr=0.0,
        standard_apr=standard_apr,
        promo_end_date=end_date,
        min_monthly_payment=min_payment,
        created_date=created_date,
    )


class TestDeferredPurchaseProperties:
    """Tests for DeferredPurchase computed properties"""

    def test_days_until_expiry_future(self, temp_db):
        """days_until_expiry should be positive for future dates"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=90)
        assert purchase.days_until_expiry == 90

    def test_days_until_expiry_past(self, temp_db):
        """days_until_expiry should be negative for expired promos"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=-30)
        assert purchase.days_until_expiry == -30

    def test_months_until_expiry(self, temp_db):
        """months_until_expiry should be days / 30"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=90)
        assert purchase.months_until_expiry == pytest.approx(3.0, abs=0.1)

    def test_monthly_payment_needed_normal(self, temp_db):
        """monthly_payment_needed = remaining / months_left"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=120, remaining=600.0)
        # 600 / (120/30) = 600 / 4 = 150
        assert purchase.monthly_payment_needed == pytest.approx(150.0, abs=1.0)

    def test_monthly_payment_needed_expired(self, temp_db):
        """monthly_payment_needed should be full balance when expired"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=-10, remaining=500.0)
        assert purchase.monthly_payment_needed == 500.0

    def test_is_expired_true(self, temp_db):
        """is_expired should be True when promo is past"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=-1)
        assert purchase.is_expired is True

    def test_is_expired_false(self, temp_db):
        """is_expired should be False when promo is still active"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=30)
        assert purchase.is_expired is False

    def test_is_at_risk_expired(self, temp_db):
        """is_at_risk should be True when expired"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=-5)
        assert purchase.is_at_risk is True

    def test_is_at_risk_insufficient_min_payment(self, temp_db):
        """is_at_risk should be True when min_payment * months < remaining"""
        card = _make_card(temp_db)
        # 50 * (90/30) = 50 * 3 = 150 < 1000 remaining
        purchase = _make_purchase(card.id, days_until_expiry=90, remaining=1000.0, min_payment=50.0)
        assert purchase.is_at_risk is True

    def test_is_at_risk_sufficient_min_payment(self, temp_db):
        """is_at_risk should be False when min_payment * months >= remaining"""
        card = _make_card(temp_db)
        # 200 * (90/30) = 200 * 3 = 600 >= 500 remaining
        purchase = _make_purchase(card.id, days_until_expiry=90, remaining=500.0, min_payment=200.0)
        assert purchase.is_at_risk is False

    def test_is_at_risk_no_min_payment(self, temp_db):
        """is_at_risk should be True when no min_monthly_payment"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=90, min_payment=None)
        # None min_payment -> always at risk
        assert purchase.is_at_risk is True

    def test_risk_level_expired(self, temp_db):
        """risk_level should be EXPIRED for expired promos"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=-5)
        assert purchase.risk_level == "EXPIRED"

    def test_risk_level_high(self, temp_db):
        """risk_level should be HIGH when < 60 days remaining"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=30)
        assert purchase.risk_level == "HIGH"

    def test_risk_level_medium(self, temp_db):
        """risk_level should be MEDIUM when 60-89 days remaining"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=75)
        assert purchase.risk_level == "MEDIUM"

    def test_risk_level_low(self, temp_db):
        """risk_level should be LOW when >= 90 days remaining"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=120)
        assert purchase.risk_level == "LOW"

    def test_potential_interest_charge(self, temp_db):
        """potential_interest_charge = purchase_amount * daily_rate * days"""
        card = _make_card(temp_db)
        created = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        end = (date.today() + timedelta(days=0)).strftime("%Y-%m-%d")
        purchase = DeferredPurchase(
            id=None, credit_card_id=card.id, description='Test',
            purchase_amount=1000.0, remaining_balance=500.0,
            promo_apr=0.0, standard_apr=0.2499,
            promo_end_date=end, min_monthly_payment=50.0,
            created_date=created,
        )
        # daily_rate = 0.2499 / 365 ≈ 0.000684657
        # interest = 1000 * 0.000684657 * 365 ≈ 249.90
        assert purchase.potential_interest_charge == pytest.approx(249.9, abs=0.1)

    def test_potential_interest_charge_no_created_date(self, temp_db):
        """Should assume 365 days when created_date is None"""
        card = _make_card(temp_db)
        end = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        purchase = DeferredPurchase(
            id=None, credit_card_id=card.id, description='Test',
            purchase_amount=1000.0, remaining_balance=500.0,
            promo_apr=0.0, standard_apr=0.20,
            promo_end_date=end, min_monthly_payment=50.0,
            created_date=None,
        )
        # daily_rate = 0.20 / 365; interest = 1000 * (0.20/365) * 365 = 200.0
        assert purchase.potential_interest_charge == pytest.approx(200.0, abs=0.1)


class TestDeferredPurchaseCRUD:
    """Tests for DeferredPurchase CRUD operations"""

    def test_save_and_retrieve(self, temp_db):
        """DeferredPurchase should be saveable and retrievable"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id, days_until_expiry=180, remaining=1500.0)
        purchase.save()

        retrieved = DeferredPurchase.get_by_id(purchase.id)
        assert retrieved is not None
        assert retrieved.description == 'Test Purchase'
        assert retrieved.remaining_balance == 1500.0

    def test_save_sets_created_date_if_none(self, temp_db):
        """save() should auto-set created_date to today if None"""
        card = _make_card(temp_db)
        end = (date.today() + timedelta(days=90)).strftime("%Y-%m-%d")
        purchase = DeferredPurchase(
            id=None, credit_card_id=card.id, description='Auto date',
            purchase_amount=500.0, remaining_balance=500.0,
            promo_apr=0.0, standard_apr=0.20, promo_end_date=end,
            created_date=None,
        )
        purchase.save()
        assert purchase.created_date == date.today().strftime("%Y-%m-%d")

    def test_delete(self, temp_db):
        """Deleted purchase should not be retrievable"""
        card = _make_card(temp_db)
        purchase = _make_purchase(card.id)
        purchase.save()
        pid = purchase.id

        purchase.delete()
        assert DeferredPurchase.get_by_id(pid) is None

    def test_get_by_card(self, temp_db):
        """get_by_card should return only purchases for that card"""
        card1 = _make_card(temp_db)
        card2 = CreditCard(
            id=None, pay_type_code='WY', name='Wyndham',
            credit_limit=3000.0, current_balance=1000.0,
            interest_rate=0.22, due_day=20
        )
        card2.save()

        p1 = _make_purchase(card1.id, days_until_expiry=60)
        p1.save()
        p2 = _make_purchase(card2.id, days_until_expiry=90)
        p2.save()

        card1_purchases = DeferredPurchase.get_by_card(card1.id)
        assert len(card1_purchases) == 1
        assert card1_purchases[0].credit_card_id == card1.id

    def test_get_all(self, temp_db):
        """get_all should return all purchases"""
        card = _make_card(temp_db)
        _make_purchase(card.id, days_until_expiry=60).save()
        _make_purchase(card.id, days_until_expiry=120).save()

        all_purchases = DeferredPurchase.get_all()
        assert len(all_purchases) == 2

    def test_get_at_risk(self, temp_db):
        """get_at_risk should return only at-risk purchases"""
        card = _make_card(temp_db)
        # At risk: low min payment, high remaining
        _make_purchase(card.id, days_until_expiry=60, remaining=5000.0, min_payment=10.0).save()
        # Not at risk: high min payment, low remaining
        _make_purchase(card.id, days_until_expiry=180, remaining=100.0, min_payment=200.0).save()

        at_risk = DeferredPurchase.get_at_risk()
        assert len(at_risk) == 1
        assert at_risk[0].remaining_balance == 5000.0

    def test_get_expiring_soon(self, temp_db):
        """get_expiring_soon should return purchases expiring within threshold"""
        card = _make_card(temp_db)
        _make_purchase(card.id, days_until_expiry=30).save()  # within 90
        _make_purchase(card.id, days_until_expiry=60).save()  # within 90
        _make_purchase(card.id, days_until_expiry=200).save()  # outside 90

        expiring = DeferredPurchase.get_expiring_soon(days=90)
        assert len(expiring) == 2

    def test_get_total_deferred_balance(self, temp_db):
        """get_total_deferred_balance should sum all remaining balances"""
        card = _make_card(temp_db)
        _make_purchase(card.id, remaining=1000.0).save()
        _make_purchase(card.id, remaining=2500.0).save()

        assert DeferredPurchase.get_total_deferred_balance() == 3500.0

    def test_get_total_potential_interest(self, temp_db):
        """get_total_potential_interest should sum interest across all purchases"""
        card = _make_card(temp_db)
        _make_purchase(card.id, purchase_amount=1000.0, standard_apr=0.20).save()
        _make_purchase(card.id, purchase_amount=2000.0, standard_apr=0.20).save()

        total = DeferredPurchase.get_total_potential_interest()
        # Both have interest > 0
        assert total > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
