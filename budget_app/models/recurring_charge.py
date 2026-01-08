"""Recurring Charge model"""

from dataclasses import dataclass
from typing import Optional, List
from .database import Database


@dataclass
class RecurringCharge:
    id: Optional[int]
    name: str
    amount: float
    day_of_month: int
    payment_method: str
    frequency: str = 'MONTHLY'
    amount_type: str = 'FIXED'
    linked_card_id: Optional[int] = None
    is_active: bool = True

    def save(self) -> 'RecurringCharge':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO recurring_charges
                (name, amount, day_of_month, payment_method, frequency,
                 amount_type, linked_card_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.name, self.amount, self.day_of_month, self.payment_method,
                  self.frequency, self.amount_type, self.linked_card_id, int(self.is_active)))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE recurring_charges SET
                name = ?, amount = ?, day_of_month = ?, payment_method = ?,
                frequency = ?, amount_type = ?, linked_card_id = ?, is_active = ?
                WHERE id = ?
            """, (self.name, self.amount, self.day_of_month, self.payment_method,
                  self.frequency, self.amount_type, self.linked_card_id, int(self.is_active),
                  self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM recurring_charges WHERE id = ?", (self.id,))
            db.commit()

    def get_actual_amount(self) -> float:
        """Get the actual amount, resolving linked card minimum payments if needed"""
        if self.amount_type == 'CREDIT_CARD_BALANCE' and self.linked_card_id:
            from .credit_card import CreditCard
            card = CreditCard.get_by_id(self.linked_card_id)
            if card:
                return -card.min_payment  # Negative because it's a payment (uses minimum payment, not full balance)
        return self.amount

    @classmethod
    def get_by_id(cls, charge_id: int) -> Optional['RecurringCharge']:
        db = Database()
        row = db.execute("SELECT * FROM recurring_charges WHERE id = ?", (charge_id,)).fetchone()
        if row:
            data = dict(row)
            data['is_active'] = bool(data['is_active'])
            return cls(**data)
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional['RecurringCharge']:
        db = Database()
        row = db.execute("SELECT * FROM recurring_charges WHERE name = ?", (name,)).fetchone()
        if row:
            data = dict(row)
            data['is_active'] = bool(data['is_active'])
            return cls(**data)
        return None

    @classmethod
    def get_all(cls, active_only: bool = False) -> List['RecurringCharge']:
        db = Database()
        if active_only:
            rows = db.execute("SELECT * FROM recurring_charges WHERE is_active = 1 ORDER BY day_of_month").fetchall()
        else:
            rows = db.execute("SELECT * FROM recurring_charges ORDER BY day_of_month").fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_active'] = bool(data['is_active'])
            result.append(cls(**data))
        return result

    @classmethod
    def get_by_day(cls, day: int) -> List['RecurringCharge']:
        db = Database()
        rows = db.execute(
            "SELECT * FROM recurring_charges WHERE day_of_month = ? AND is_active = 1",
            (day,)
        ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_active'] = bool(data['is_active'])
            result.append(cls(**data))
        return result

    @classmethod
    def get_special_charges(cls) -> List['RecurringCharge']:
        """Get charges with special day codes (991-999)"""
        db = Database()
        rows = db.execute(
            "SELECT * FROM recurring_charges WHERE day_of_month >= 991 AND is_active = 1"
        ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_active'] = bool(data['is_active'])
            result.append(cls(**data))
        return result
