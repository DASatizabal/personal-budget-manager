"""Loan model (401k loans, etc.)"""

from dataclasses import dataclass
from typing import Optional, List
from .database import Database


@dataclass
class Loan:
    id: Optional[int]
    pay_type_code: str
    name: str
    original_amount: float
    current_balance: float
    interest_rate: float
    payment_amount: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @property
    def monthly_interest(self) -> float:
        return (self.current_balance * self.interest_rate) / 12

    @property
    def remaining_payments(self) -> int:
        if self.payment_amount <= 0:
            return 0
        return int(self.current_balance / self.payment_amount) + 1

    def save(self) -> 'Loan':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO loans
                (pay_type_code, name, original_amount, current_balance,
                 interest_rate, payment_amount, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.pay_type_code, self.name, self.original_amount, self.current_balance,
                  self.interest_rate, self.payment_amount, self.start_date, self.end_date))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE loans SET
                pay_type_code = ?, name = ?, original_amount = ?, current_balance = ?,
                interest_rate = ?, payment_amount = ?, start_date = ?, end_date = ?
                WHERE id = ?
            """, (self.pay_type_code, self.name, self.original_amount, self.current_balance,
                  self.interest_rate, self.payment_amount, self.start_date, self.end_date,
                  self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM loans WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_id(cls, loan_id: int) -> Optional['Loan']:
        db = Database()
        row = db.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_by_code(cls, code: str) -> Optional['Loan']:
        db = Database()
        row = db.execute("SELECT * FROM loans WHERE pay_type_code = ?", (code,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls) -> List['Loan']:
        db = Database()
        rows = db.execute("SELECT * FROM loans ORDER BY name").fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_total_balance(cls) -> float:
        db = Database()
        result = db.execute("SELECT SUM(current_balance) FROM loans").fetchone()
        return result[0] or 0.0
