"""Shared Expense model for Lisa payment splitting"""

from dataclasses import dataclass
from typing import Optional, List
from .database import Database


@dataclass
class SharedExpense:
    id: Optional[int]
    name: str
    monthly_amount: float
    split_type: str = 'HALF'  # HALF, THIRD, CUSTOM
    custom_split_ratio: Optional[float] = None
    linked_recurring_id: Optional[int] = None

    def get_split_amount(self, paycheck_count: int = 2) -> float:
        """
        Calculate the split amount based on paycheck count.

        Args:
            paycheck_count: Number of paychecks in the month (2 or 3)

        Returns:
            The amount to pay per paycheck
        """
        if self.split_type == 'CUSTOM' and self.custom_split_ratio:
            return self.monthly_amount * self.custom_split_ratio / paycheck_count
        elif self.split_type == 'THIRD' or paycheck_count == 3:
            return self.monthly_amount / 3
        else:  # HALF or default
            return self.monthly_amount / 2

    def save(self) -> 'SharedExpense':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO shared_expenses
                (name, monthly_amount, split_type, custom_split_ratio, linked_recurring_id)
                VALUES (?, ?, ?, ?, ?)
            """, (self.name, self.monthly_amount, self.split_type,
                  self.custom_split_ratio, self.linked_recurring_id))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE shared_expenses SET
                name = ?, monthly_amount = ?, split_type = ?,
                custom_split_ratio = ?, linked_recurring_id = ?
                WHERE id = ?
            """, (self.name, self.monthly_amount, self.split_type,
                  self.custom_split_ratio, self.linked_recurring_id, self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM shared_expenses WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_id(cls, expense_id: int) -> Optional['SharedExpense']:
        db = Database()
        row = db.execute("SELECT * FROM shared_expenses WHERE id = ?", (expense_id,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls) -> List['SharedExpense']:
        db = Database()
        rows = db.execute("SELECT * FROM shared_expenses ORDER BY name").fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_total_monthly(cls) -> float:
        db = Database()
        result = db.execute("SELECT SUM(monthly_amount) FROM shared_expenses").fetchone()
        return result[0] or 0.0

    @classmethod
    def calculate_lisa_payment(cls, paycheck_count: int = 2) -> float:
        """Calculate total Lisa payment for a pay period"""
        expenses = cls.get_all()
        return sum(e.get_split_amount(paycheck_count) for e in expenses)
