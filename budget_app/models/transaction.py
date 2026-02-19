"""Transaction model"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, date
from .database import Database


@dataclass
class Transaction:
    id: Optional[int]
    date: str  # ISO format: YYYY-MM-DD (due date)
    description: str
    amount: float
    payment_method: str
    recurring_charge_id: Optional[int] = None
    is_posted: bool = False
    posted_date: Optional[str] = None  # ISO format: YYYY-MM-DD (when marked as posted)
    notes: Optional[str] = None

    @property
    def date_obj(self) -> date:
        # Handle dates with optional time component (e.g., "2026-01-15 23:59:59")
        return datetime.strptime(self.date[:10], '%Y-%m-%d').date()

    def save(self) -> 'Transaction':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO transactions
                (date, description, amount, payment_method, recurring_charge_id, is_posted, posted_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.date, self.description, self.amount, self.payment_method,
                  self.recurring_charge_id, int(self.is_posted), self.posted_date, self.notes))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE transactions SET
                date = ?, description = ?, amount = ?, payment_method = ?,
                recurring_charge_id = ?, is_posted = ?, posted_date = ?, notes = ?
                WHERE id = ?
            """, (self.date, self.description, self.amount, self.payment_method,
                  self.recurring_charge_id, int(self.is_posted), self.posted_date, self.notes, self.id))
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
        """Delete all future non-posted auto-generated transactions for regeneration.
        This includes:
        - Transactions linked to recurring charges (recurring_charge_id IS NOT NULL)
        - Payday transactions, LDBPD markers, Lisa payments (known descriptions)
        - Interest charges (description ending with ' Interest')
        Manual transactions (recurring_charge_id IS NULL, unknown description) are preserved.
        """
        if from_date is None:
            from_date = datetime.now().strftime('%Y-%m-%d')
        db = Database()
        db.execute("""
            DELETE FROM transactions
            WHERE date >= ? AND is_posted = 0
              AND (
                recurring_charge_id IS NOT NULL
                OR description IN ('Payday', 'LDBPD', 'Lisa')
                OR description LIKE '% Interest'
              )
        """, (from_date,))
        db.commit()

    @classmethod
    def dedup(cls) -> int:
        """Remove duplicate transactions, keeping the one with the lowest id.
        Duplicates are identified by (date, payment_method, description, amount).
        Returns the number of duplicates removed.
        """
        db = Database()
        cursor = db.execute("""
            DELETE FROM transactions
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM transactions
                GROUP BY date, payment_method, description, amount
            )
        """)
        db.commit()
        return cursor.rowcount

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

    @classmethod
    def get_posted(cls) -> List['Transaction']:
        """Get all posted transactions, ordered by posted_date descending"""
        db = Database()
        rows = db.execute("""
            SELECT * FROM transactions
            WHERE is_posted = 1
            ORDER BY posted_date DESC, date DESC, id DESC
        """).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_posted'] = bool(data['is_posted'])
            result.append(cls(**data))
        return result

    @classmethod
    def clear_posted(cls) -> int:
        """Delete all posted transactions. Returns count of deleted transactions."""
        db = Database()
        result = db.execute("SELECT COUNT(*) FROM transactions WHERE is_posted = 1").fetchone()
        count = result[0] if result else 0
        db.execute("DELETE FROM transactions WHERE is_posted = 1")
        db.commit()
        return count
