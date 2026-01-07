"""Account model (Checking, Savings, etc.)"""

from dataclasses import dataclass
from typing import Optional, List
from .database import Database


@dataclass
class Account:
    id: Optional[int]
    name: str
    account_type: str  # CHECKING, SAVINGS, CASH
    current_balance: float = 0.0
    pay_type_code: Optional[str] = None

    def save(self) -> 'Account':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO accounts
                (name, account_type, current_balance, pay_type_code)
                VALUES (?, ?, ?, ?)
            """, (self.name, self.account_type, self.current_balance, self.pay_type_code))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE accounts SET
                name = ?, account_type = ?, current_balance = ?, pay_type_code = ?
                WHERE id = ?
            """, (self.name, self.account_type, self.current_balance, self.pay_type_code, self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM accounts WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_id(cls, account_id: int) -> Optional['Account']:
        db = Database()
        row = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_by_code(cls, code: str) -> Optional['Account']:
        db = Database()
        row = db.execute("SELECT * FROM accounts WHERE pay_type_code = ?", (code,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Account']:
        db = Database()
        row = db.execute("SELECT * FROM accounts WHERE name = ?", (name,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls) -> List['Account']:
        db = Database()
        rows = db.execute("SELECT * FROM accounts ORDER BY account_type, name").fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_checking_account(cls) -> Optional['Account']:
        db = Database()
        row = db.execute(
            "SELECT * FROM accounts WHERE account_type = 'CHECKING' LIMIT 1"
        ).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_total_balance(cls) -> float:
        db = Database()
        result = db.execute("SELECT SUM(current_balance) FROM accounts").fetchone()
        return result[0] or 0.0
