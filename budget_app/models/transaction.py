"""Transaction model"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, date
from .database import Database


@dataclass
class Transaction:
    id: Optional[int]
    date: str  # ISO format: YYYY-MM-DD
    description: str
    amount: float
    payment_method: str
    recurring_charge_id: Optional[int] = None
    is_posted: bool = False
    notes: Optional[str] = None

    @property
    def date_obj(self) -> date:
        return datetime.strptime(self.date, '%Y-%m-%d').date()

    def save(self) -> 'Transaction':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO transactions
                (date, description, amount, payment_method, recurring_charge_id, is_posted, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.date, self.description, self.amount, self.payment_method,
                  self.recurring_charge_id, int(self.is_posted), self.notes))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE transactions SET
                date = ?, description = ?, amount = ?, payment_method = ?,
                recurring_charge_id = ?, is_posted = ?, notes = ?
                WHERE id = ?
            """, (self.date, self.description, self.amount, self.payment_method,
                  self.recurring_charge_id, int(self.is_posted), self.notes, self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM transactions WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_id(cls, trans_id: int) -> Optional['Transaction']:
        db = Database()
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (trans_id,)).fetchone()
        if row:
            data = dict(row)
            data['is_posted'] = bool(data['is_posted'])
            return cls(**data)
        return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = 0) -> List['Transaction']:
        db = Database()
        # Sort by date, then amount DESC (positive before negative), then id
        sql = "SELECT * FROM transactions ORDER BY date, amount DESC, id"
        if limit:
            sql += f" LIMIT {limit} OFFSET {offset}"
        rows = db.execute(sql).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_posted'] = bool(data['is_posted'])
            result.append(cls(**data))
        return result

    @classmethod
    def get_by_date_range(cls, start_date: str, end_date: str) -> List['Transaction']:
        db = Database()
        rows = db.execute("""
            SELECT * FROM transactions
            WHERE date >= ? AND date <= ?
            ORDER BY date, amount DESC, id
        """, (start_date, end_date)).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_posted'] = bool(data['is_posted'])
            result.append(cls(**data))
        return result

    @classmethod
    def get_by_payment_method(cls, method: str) -> List['Transaction']:
        db = Database()
        rows = db.execute("""
            SELECT * FROM transactions
            WHERE payment_method = ?
            ORDER BY date, amount DESC, id
        """, (method,)).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_posted'] = bool(data['is_posted'])
            result.append(cls(**data))
        return result

    @classmethod
    def get_future_transactions(cls, from_date: str = None) -> List['Transaction']:
        if from_date is None:
            from_date = datetime.now().strftime('%Y-%m-%d')
        db = Database()
        rows = db.execute("""
            SELECT * FROM transactions
            WHERE date >= ?
            ORDER BY date, amount DESC, id
        """, (from_date,)).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_posted'] = bool(data['is_posted'])
            result.append(cls(**data))
        return result

    @classmethod
    def delete_future_recurring(cls, from_date: str = None):
        """Delete all future non-posted transactions for regeneration.
        This includes:
        - Transactions linked to recurring charges
        - Payday transactions (recurring_charge_id is NULL but auto-generated)
        - LDBPD markers
        - Lisa payment transactions
        """
        if from_date is None:
            from_date = datetime.now().strftime('%Y-%m-%d')
        db = Database()
        # Delete all future non-posted transactions (they are all auto-generated)
        db.execute("""
            DELETE FROM transactions
            WHERE date >= ? AND is_posted = 0
        """, (from_date,))
        db.commit()

    @classmethod
    def get_running_balance(cls, payment_method: str, up_to_date: str,
                           starting_balance: float) -> float:
        """Calculate running balance for a payment method up to a date"""
        db = Database()
        result = db.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE payment_method = ? AND date <= ?
        """, (payment_method, up_to_date)).fetchone()
        return starting_balance + (result[0] or 0)
