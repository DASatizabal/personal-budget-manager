"""Deferred Interest Purchase model for 0% APR promotional periods"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import date, datetime
from .database import Database


@dataclass
class DeferredPurchase:
    """Tracks purchases with deferred interest promotional periods"""
    id: Optional[int]
    credit_card_id: int
    description: str
    purchase_amount: float
    remaining_balance: float
    promo_apr: float  # Usually 0.0 for deferred interest
    standard_apr: float  # APR that kicks in after promo ends
    promo_end_date: str  # YYYY-MM-DD format
    min_monthly_payment: Optional[float] = None
    created_date: Optional[str] = None

    @property
    def promo_end_as_date(self) -> date:
        """Convert promo_end_date string to date object"""
        return datetime.strptime(self.promo_end_date, "%Y-%m-%d").date()

    @property
    def days_until_expiry(self) -> int:
        """Number of days until promotional period ends"""
        today = date.today()
        delta = self.promo_end_as_date - today
        return delta.days

    @property
    def months_until_expiry(self) -> float:
        """Approximate months until promo ends"""
        return self.days_until_expiry / 30.0

    @property
    def monthly_payment_needed(self) -> float:
        """Calculate monthly payment needed to pay off before promo ends"""
        months = self.months_until_expiry
        if months <= 0:
            return self.remaining_balance  # Past due - pay it all now
        return self.remaining_balance / months

    @property
    def is_expired(self) -> bool:
        """Check if promotional period has expired"""
        return self.days_until_expiry < 0

    @property
    def is_at_risk(self) -> bool:
        """Check if balance won't be paid off before promo ends at current min payment"""
        if self.is_expired:
            return True
        if not self.min_monthly_payment or self.min_monthly_payment == 0:
            return True
        months = self.months_until_expiry
        projected_payoff = self.min_monthly_payment * months
        return projected_payoff < self.remaining_balance

    @property
    def risk_level(self) -> str:
        """Return risk level: EXPIRED, HIGH, MEDIUM, LOW"""
        if self.is_expired:
            return "EXPIRED"
        days = self.days_until_expiry
        if days < 60:
            return "HIGH"
        elif days < 90:
            return "MEDIUM"
        else:
            return "LOW"

    @property
    def potential_interest_charge(self) -> float:
        """Calculate potential retroactive interest if promo expires with balance"""
        # Deferred interest = full interest on original purchase amount
        # from purchase date to promo end date
        if self.created_date:
            created = datetime.strptime(self.created_date, "%Y-%m-%d").date()
            promo_end = self.promo_end_as_date
            days_of_interest = (promo_end - created).days
        else:
            days_of_interest = 365  # Assume 1 year if unknown

        # Calculate interest on ORIGINAL purchase amount (not remaining balance)
        daily_rate = self.standard_apr / 365
        return self.purchase_amount * daily_rate * days_of_interest

    def save(self) -> 'DeferredPurchase':
        """Save this deferred purchase to the database"""
        db = Database()
        if self.created_date is None:
            self.created_date = date.today().strftime("%Y-%m-%d")

        if self.id is None:
            cursor = db.execute("""
                INSERT INTO deferred_purchases
                (credit_card_id, description, purchase_amount, remaining_balance,
                 promo_apr, standard_apr, promo_end_date, min_monthly_payment, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.credit_card_id, self.description, self.purchase_amount,
                  self.remaining_balance, self.promo_apr, self.standard_apr,
                  self.promo_end_date, self.min_monthly_payment, self.created_date))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE deferred_purchases SET
                credit_card_id = ?, description = ?, purchase_amount = ?,
                remaining_balance = ?, promo_apr = ?, standard_apr = ?,
                promo_end_date = ?, min_monthly_payment = ?, created_date = ?
                WHERE id = ?
            """, (self.credit_card_id, self.description, self.purchase_amount,
                  self.remaining_balance, self.promo_apr, self.standard_apr,
                  self.promo_end_date, self.min_monthly_payment, self.created_date,
                  self.id))
        db.commit()
        return self

    def delete(self):
        """Delete this deferred purchase from the database"""
        if self.id:
            db = Database()
            db.execute("DELETE FROM deferred_purchases WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_id(cls, purchase_id: int) -> Optional['DeferredPurchase']:
        """Get a deferred purchase by its ID"""
        db = Database()
        row = db.execute("SELECT * FROM deferred_purchases WHERE id = ?", (purchase_id,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls) -> List['DeferredPurchase']:
        """Get all deferred purchases ordered by promo end date"""
        db = Database()
        rows = db.execute("""
            SELECT * FROM deferred_purchases ORDER BY promo_end_date ASC
        """).fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_by_card(cls, credit_card_id: int) -> List['DeferredPurchase']:
        """Get all deferred purchases for a specific credit card"""
        db = Database()
        rows = db.execute("""
            SELECT * FROM deferred_purchases
            WHERE credit_card_id = ?
            ORDER BY promo_end_date ASC
        """, (credit_card_id,)).fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_at_risk(cls) -> List['DeferredPurchase']:
        """Get all deferred purchases that are at risk of incurring interest"""
        all_purchases = cls.get_all()
        return [p for p in all_purchases if p.is_at_risk]

    @classmethod
    def get_expiring_soon(cls, days: int = 90) -> List['DeferredPurchase']:
        """Get deferred purchases expiring within specified days"""
        all_purchases = cls.get_all()
        return [p for p in all_purchases if 0 <= p.days_until_expiry <= days]

    @classmethod
    def get_total_deferred_balance(cls) -> float:
        """Get total remaining balance across all deferred purchases"""
        db = Database()
        result = db.execute("SELECT SUM(remaining_balance) FROM deferred_purchases").fetchone()
        return result[0] or 0.0

    @classmethod
    def get_total_potential_interest(cls) -> float:
        """Get total potential retroactive interest if all promos expire"""
        all_purchases = cls.get_all()
        return sum(p.potential_interest_charge for p in all_purchases)
