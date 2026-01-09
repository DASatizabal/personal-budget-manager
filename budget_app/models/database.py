"""Database connection and initialization"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
import os

DB_PATH = Path(__file__).parent.parent.parent / "budget_data.db"

# Use standard logging to avoid circular import
_logger = logging.getLogger('budget_app.database')


class Database:
    """SQLite database connection manager"""

    _instance: Optional['Database'] = None
    _connection: Optional[sqlite3.Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            _logger.debug(f"Opening database connection to {DB_PATH}")
            self._connection = sqlite3.connect(str(DB_PATH))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        return self.connection.executemany(sql, params_list)

    def commit(self):
        self.connection.commit()

    def close(self):
        if self._connection:
            _logger.debug("Closing database connection")
            self._connection.close()
            self._connection = None


def init_db():
    """Initialize the database with all required tables"""
    db = Database()

    # Accounts table (Chase, Savings, etc.)
    db.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            account_type TEXT NOT NULL CHECK(account_type IN ('CHECKING', 'SAVINGS', 'CASH')),
            current_balance REAL NOT NULL DEFAULT 0,
            pay_type_code TEXT UNIQUE
        )
    """)

    # Credit Cards table
    db.execute("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pay_type_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            credit_limit REAL NOT NULL,
            current_balance REAL NOT NULL DEFAULT 0,
            interest_rate REAL NOT NULL DEFAULT 0,
            due_day INTEGER,
            min_payment_type TEXT NOT NULL DEFAULT 'CALCULATED'
                CHECK(min_payment_type IN ('FIXED', 'FULL_BALANCE', 'CALCULATED')),
            min_payment_amount REAL
        )
    """)

    # Loans table (401k loans, etc.)
    db.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pay_type_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            original_amount REAL NOT NULL,
            current_balance REAL NOT NULL,
            interest_rate REAL NOT NULL,
            payment_amount REAL NOT NULL,
            start_date TEXT,
            end_date TEXT
        )
    """)

    # Recurring Charges table
    db.execute("""
        CREATE TABLE IF NOT EXISTS recurring_charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            day_of_month INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            frequency TEXT NOT NULL DEFAULT 'MONTHLY'
                CHECK(frequency IN ('MONTHLY', 'BIWEEKLY', 'WEEKLY', 'YEARLY', 'SPECIAL')),
            amount_type TEXT NOT NULL DEFAULT 'FIXED'
                CHECK(amount_type IN ('FIXED', 'CREDIT_CARD_BALANCE', 'CALCULATED')),
            linked_card_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (linked_card_id) REFERENCES credit_cards(id)
        )
    """)

    # Transactions table
    db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            recurring_charge_id INTEGER,
            is_posted INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (recurring_charge_id) REFERENCES recurring_charges(id)
        )
    """)

    # Paycheck Configuration table
    db.execute("""
        CREATE TABLE IF NOT EXISTS paycheck_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gross_amount REAL NOT NULL,
            pay_frequency TEXT NOT NULL DEFAULT 'BIWEEKLY'
                CHECK(pay_frequency IN ('WEEKLY', 'BIWEEKLY', 'SEMIMONTHLY', 'MONTHLY')),
            effective_date TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Paycheck Deductions table
    db.execute("""
        CREATE TABLE IF NOT EXISTS paycheck_deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paycheck_config_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount_type TEXT NOT NULL DEFAULT 'FIXED'
                CHECK(amount_type IN ('FIXED', 'PERCENTAGE')),
            amount REAL NOT NULL,
            FOREIGN KEY (paycheck_config_id) REFERENCES paycheck_configs(id) ON DELETE CASCADE
        )
    """)

    # Shared Expenses table (for Lisa payment splitting)
    db.execute("""
        CREATE TABLE IF NOT EXISTS shared_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            monthly_amount REAL NOT NULL,
            split_type TEXT NOT NULL DEFAULT 'HALF'
                CHECK(split_type IN ('HALF', 'THIRD', 'CUSTOM')),
            custom_split_ratio REAL,
            linked_recurring_id INTEGER,
            FOREIGN KEY (linked_recurring_id) REFERENCES recurring_charges(id)
        )
    """)

    # Create indexes for performance
    db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_payment_method ON transactions(payment_method)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_recurring_day ON recurring_charges(day_of_month)")

    # Migration: Add pay_day_of_week column if not exists (default Friday = 4)
    try:
        db.execute("SELECT pay_day_of_week FROM paycheck_configs LIMIT 1")
    except Exception:
        _logger.info("Running migration: Adding pay_day_of_week column")
        db.execute("ALTER TABLE paycheck_configs ADD COLUMN pay_day_of_week INTEGER NOT NULL DEFAULT 4")

    # Migration: Add posted_date column to transactions if not exists
    try:
        db.execute("SELECT posted_date FROM transactions LIMIT 1")
    except Exception:
        _logger.info("Running migration: Adding posted_date column to transactions")
        db.execute("ALTER TABLE transactions ADD COLUMN posted_date TEXT")

    db.commit()
    _logger.info("Database initialized successfully")
    return db
