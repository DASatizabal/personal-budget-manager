"""Paycheck configuration and deductions models"""

from dataclasses import dataclass, field
from typing import Optional, List
from .database import Database


@dataclass
class PaycheckDeduction:
    id: Optional[int]
    paycheck_config_id: int
    name: str
    amount_type: str  # FIXED or PERCENTAGE
    amount: float

    def save(self) -> 'PaycheckDeduction':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO paycheck_deductions
                (paycheck_config_id, name, amount_type, amount)
                VALUES (?, ?, ?, ?)
            """, (self.paycheck_config_id, self.name, self.amount_type, self.amount))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE paycheck_deductions SET
                paycheck_config_id = ?, name = ?, amount_type = ?, amount = ?
                WHERE id = ?
            """, (self.paycheck_config_id, self.name, self.amount_type, self.amount, self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM paycheck_deductions WHERE id = ?", (self.id,))
            db.commit()

    def calculate_amount(self, gross_pay: float) -> float:
        if self.amount_type == 'PERCENTAGE':
            return gross_pay * self.amount
        return self.amount


@dataclass
class PaycheckConfig:
    id: Optional[int]
    gross_amount: float
    pay_frequency: str = 'BIWEEKLY'
    effective_date: str = ''
    is_current: bool = True
    deductions: List[PaycheckDeduction] = field(default_factory=list)

    @property
    def total_deductions(self) -> float:
        return sum(d.calculate_amount(self.gross_amount) for d in self.deductions)

    @property
    def net_pay(self) -> float:
        return self.gross_amount - self.total_deductions

    @property
    def annual_gross(self) -> float:
        multipliers = {'WEEKLY': 52, 'BIWEEKLY': 26, 'SEMIMONTHLY': 24, 'MONTHLY': 12}
        return self.gross_amount * multipliers.get(self.pay_frequency, 26)

    @property
    def annual_net(self) -> float:
        multipliers = {'WEEKLY': 52, 'BIWEEKLY': 26, 'SEMIMONTHLY': 24, 'MONTHLY': 12}
        return self.net_pay * multipliers.get(self.pay_frequency, 26)

    def save(self) -> 'PaycheckConfig':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO paycheck_configs
                (gross_amount, pay_frequency, effective_date, is_current)
                VALUES (?, ?, ?, ?)
            """, (self.gross_amount, self.pay_frequency, self.effective_date, int(self.is_current)))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE paycheck_configs SET
                gross_amount = ?, pay_frequency = ?, effective_date = ?, is_current = ?
                WHERE id = ?
            """, (self.gross_amount, self.pay_frequency, self.effective_date,
                  int(self.is_current), self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM paycheck_configs WHERE id = ?", (self.id,))
            db.commit()

    def load_deductions(self):
        if self.id:
            db = Database()
            rows = db.execute(
                "SELECT * FROM paycheck_deductions WHERE paycheck_config_id = ?",
                (self.id,)
            ).fetchall()
            self.deductions = [PaycheckDeduction(**dict(row)) for row in rows]

    @classmethod
    def get_by_id(cls, config_id: int) -> Optional['PaycheckConfig']:
        db = Database()
        row = db.execute("SELECT * FROM paycheck_configs WHERE id = ?", (config_id,)).fetchone()
        if row:
            data = dict(row)
            data['is_current'] = bool(data['is_current'])
            config = cls(**data)
            config.load_deductions()
            return config
        return None

    @classmethod
    def get_current(cls) -> Optional['PaycheckConfig']:
        db = Database()
        row = db.execute(
            "SELECT * FROM paycheck_configs WHERE is_current = 1 ORDER BY effective_date DESC LIMIT 1"
        ).fetchone()
        if row:
            data = dict(row)
            data['is_current'] = bool(data['is_current'])
            config = cls(**data)
            config.load_deductions()
            return config
        return None

    @classmethod
    def get_all(cls) -> List['PaycheckConfig']:
        db = Database()
        rows = db.execute(
            "SELECT * FROM paycheck_configs ORDER BY effective_date DESC"
        ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data['is_current'] = bool(data['is_current'])
            config = cls(**data)
            config.load_deductions()
            result.append(config)
        return result
