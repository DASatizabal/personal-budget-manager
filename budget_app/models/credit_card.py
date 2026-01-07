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
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO credit_cards
                (pay_type_code, name, credit_limit, current_balance, interest_rate,
                 due_day, min_payment_type, min_payment_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.pay_type_code, self.name, self.credit_limit, self.current_balance,
                  self.interest_rate, self.due_day, self.min_payment_type, self.min_payment_amount))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE credit_cards SET
                pay_type_code = ?, name = ?, credit_limit = ?, current_balance = ?,
                interest_rate = ?, due_day = ?, min_payment_type = ?, min_payment_amount = ?
                WHERE id = ?
            """, (self.pay_type_code, self.name, self.credit_limit, self.current_balance,
                  self.interest_rate, self.due_day, self.min_payment_type, self.min_payment_amount,
                  self.id))
        db.commit()
        return self

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
        rows = db.execute("SELECT * FROM credit_cards ORDER BY name").fetchall()
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
