"""Credit Card model"""

from dataclasses import dataclass
from typing import Optional, List
from .database import Database


@dataclass
class CreditCard:
    id: Optional[int]
    pay_type_code: str
    name: str
    credit_limit: float
    current_balance: float = 0.0
    interest_rate: float = 0.0
    due_day: Optional[int] = None
    min_payment_type: str = 'CALCULATED'
    min_payment_amount: Optional[float] = None
    sort_order: int = 0
    login_url: Optional[str] = None

    @property
    def available_credit(self) -> float:
        return self.credit_limit - self.current_balance

    @property
    def utilization(self) -> float:
        if self.credit_limit == 0:
            return 0.0
        return self.current_balance / self.credit_limit

    @property
    def monthly_interest(self) -> float:
        return (self.current_balance * self.interest_rate) / 12

    @property
    def min_payment(self) -> float:
        if self.min_payment_type == 'FULL_BALANCE':
            return self.current_balance
        elif self.min_payment_type == 'FIXED' and self.min_payment_amount:
            return self.min_payment_amount
        else:
            # Default calculation: 1% of balance + monthly interest, minimum $25
            base = self.current_balance * 0.01 + self.monthly_interest
            return max(base, min(25.0, self.current_balance))

    def save(self) -> 'CreditCard':
        db = Database()
        is_new = self.id is None
        if is_new:
            # Auto-assign sort_order = max existing + 1
            result = db.execute("SELECT COALESCE(MAX(sort_order), -1) FROM credit_cards").fetchone()
            self.sort_order = result[0] + 1
            cursor = db.execute("""
                INSERT INTO credit_cards
                (pay_type_code, name, credit_limit, current_balance, interest_rate,
                 due_day, min_payment_type, min_payment_amount, sort_order, login_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.pay_type_code, self.name, self.credit_limit, self.current_balance,
                  self.interest_rate, self.due_day, self.min_payment_type, self.min_payment_amount,
                  self.sort_order, self.login_url))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE credit_cards SET
                pay_type_code = ?, name = ?, credit_limit = ?, current_balance = ?,
                interest_rate = ?, due_day = ?, min_payment_type = ?, min_payment_amount = ?,
                sort_order = ?, login_url = ?
                WHERE id = ?
            """, (self.pay_type_code, self.name, self.credit_limit, self.current_balance,
                  self.interest_rate, self.due_day, self.min_payment_type, self.min_payment_amount,
                  self.sort_order, self.login_url, self.id))
        db.commit()

        # For new cards, create a corresponding recurring charge for payment tracking
        if is_new:
            self._create_recurring_charge()
        else:
            # Sync any linked recurring charges
            self._sync_linked_recurring_charges()
        return self

    def _sync_linked_recurring_charges(self):
        """Sync linked recurring charges with this card's due_day and ensure correct type"""
        if self.id is None:
            return
        db = Database()
        # Update any recurring charges linked to this card:
        # - Set day_of_month to match due_day
        # - Set amount_type to CALCULATED (uses min_payment from card)
        if self.due_day:
            db.execute("""
                UPDATE recurring_charges
                SET day_of_month = ?, amount_type = 'CALCULATED'
                WHERE linked_card_id = ?
            """, (self.due_day, self.id))
            db.commit()

    def _create_recurring_charge(self):
        """Create a recurring charge for this credit card's payment"""
        if self.id is None or self.due_day is None:
            return

        from .recurring_charge import RecurringCharge

        # Check if a recurring charge already exists for this card
        db = Database()
        existing = db.execute(
            "SELECT id FROM recurring_charges WHERE linked_card_id = ?",
            (self.id,)
        ).fetchone()

        if existing:
            # Already has a linked charge, just sync it
            self._sync_linked_recurring_charges()
            return

        # Create new recurring charge for this card's payment
        charge = RecurringCharge(
            id=None,
            name=self.name,
            amount=0,  # Will be calculated from min_payment
            day_of_month=self.due_day,
            payment_method='C',  # Payments come from Chase (bank account)
            frequency='MONTHLY',
            amount_type='CALCULATED',
            linked_card_id=self.id,
            is_active=True
        )
        charge.save()

    def delete(self):
        if self.id:
            db = Database()
            # Unlink any recurring charges that reference this card
            db.execute("UPDATE recurring_charges SET linked_card_id = NULL WHERE linked_card_id = ?", (self.id,))
            # Now safe to delete the card
            db.execute("DELETE FROM credit_cards WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_id(cls, card_id: int) -> Optional['CreditCard']:
        db = Database()
        row = db.execute("SELECT * FROM credit_cards WHERE id = ?", (card_id,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_by_code(cls, code: str) -> Optional['CreditCard']:
        db = Database()
        row = db.execute("SELECT * FROM credit_cards WHERE pay_type_code = ?", (code,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls) -> List['CreditCard']:
        db = Database()
        rows = db.execute("SELECT * FROM credit_cards ORDER BY sort_order, name").fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_total_balance(cls) -> float:
        db = Database()
        result = db.execute("SELECT SUM(current_balance) FROM credit_cards").fetchone()
        return result[0] or 0.0

    @classmethod
    def get_total_credit_limit(cls) -> float:
        db = Database()
        result = db.execute("SELECT SUM(credit_limit) FROM credit_cards").fetchone()
        return result[0] or 0.0

    @classmethod
    def get_total_utilization(cls) -> float:
        total_limit = cls.get_total_credit_limit()
        if total_limit == 0:
            return 0.0
        return cls.get_total_balance() / total_limit

    @classmethod
    def update_sort_orders(cls, card_ids: list[int]):
        """Bulk-update sort_order from an ordered list of card IDs"""
        db = Database()
        for idx, card_id in enumerate(card_ids):
            db.execute("UPDATE credit_cards SET sort_order = ? WHERE id = ?", (idx, card_id))
        db.commit()
