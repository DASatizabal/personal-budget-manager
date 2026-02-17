"""PlaidItem and PlaidAccountMapping models — persistence for Plaid link data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from .database import Database


@dataclass
class PlaidAccountMapping:
    id: Optional[int]
    plaid_item_id: int
    plaid_account_id: str
    plaid_account_name: Optional[str] = None
    plaid_account_official_name: Optional[str] = None
    plaid_account_type: Optional[str] = None
    plaid_account_subtype: Optional[str] = None
    plaid_account_mask: Optional[str] = None
    local_type: Optional[str] = None     # 'account', 'credit_card', 'loan'
    local_id: Optional[int] = None
    is_synced: bool = True

    def save(self) -> 'PlaidAccountMapping':
        db = Database()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO plaid_account_mappings
                (plaid_item_id, plaid_account_id, plaid_account_name,
                 plaid_account_official_name, plaid_account_type, plaid_account_subtype,
                 plaid_account_mask, local_type, local_id, is_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.plaid_item_id, self.plaid_account_id, self.plaid_account_name,
                  self.plaid_account_official_name, self.plaid_account_type,
                  self.plaid_account_subtype, self.plaid_account_mask,
                  self.local_type, self.local_id, int(self.is_synced)))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE plaid_account_mappings SET
                plaid_item_id = ?, plaid_account_id = ?, plaid_account_name = ?,
                plaid_account_official_name = ?, plaid_account_type = ?,
                plaid_account_subtype = ?, plaid_account_mask = ?,
                local_type = ?, local_id = ?, is_synced = ?
                WHERE id = ?
            """, (self.plaid_item_id, self.plaid_account_id, self.plaid_account_name,
                  self.plaid_account_official_name, self.plaid_account_type,
                  self.plaid_account_subtype, self.plaid_account_mask,
                  self.local_type, self.local_id, int(self.is_synced), self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            db.execute("DELETE FROM plaid_account_mappings WHERE id = ?", (self.id,))
            db.commit()

    @classmethod
    def get_by_item(cls, plaid_item_id: int) -> List['PlaidAccountMapping']:
        db = Database()
        rows = db.execute(
            "SELECT * FROM plaid_account_mappings WHERE plaid_item_id = ? ORDER BY plaid_account_name",
            (plaid_item_id,)
        ).fetchall()
        return [cls(**{**dict(row), 'is_synced': bool(dict(row)['is_synced'])}) for row in rows]

    @classmethod
    def get_all_synced(cls) -> List['PlaidAccountMapping']:
        db = Database()
        rows = db.execute(
            "SELECT * FROM plaid_account_mappings WHERE is_synced = 1 AND local_type IS NOT NULL AND local_id IS NOT NULL"
        ).fetchall()
        return [cls(**{**dict(row), 'is_synced': bool(dict(row)['is_synced'])}) for row in rows]

    def get_local_display_name(self) -> str:
        """Return a human-readable name for the mapped local account."""
        if not self.local_type or not self.local_id:
            return "(unmapped)"
        if self.local_type == 'account':
            from .account import Account
            obj = Account.get_by_id(self.local_id)
        elif self.local_type == 'credit_card':
            from .credit_card import CreditCard
            obj = CreditCard.get_by_id(self.local_id)
        elif self.local_type == 'loan':
            from .loan import Loan
            obj = Loan.get_by_id(self.local_id)
        else:
            return "(unknown type)"
        return obj.name if obj else "(deleted)"


@dataclass
class PlaidItem:
    id: Optional[int]
    item_id: str
    access_token: str
    institution_name: Optional[str] = None
    institution_id: Optional[str] = None
    status: str = 'good'
    consent_expiration: Optional[str] = None
    transaction_cursor: Optional[str] = None
    created_at: Optional[str] = None
    last_sync: Optional[str] = None

    def save(self) -> 'PlaidItem':
        db = Database()
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.id is None:
            cursor = db.execute("""
                INSERT INTO plaid_items
                (item_id, access_token, institution_name, institution_id,
                 status, consent_expiration, transaction_cursor, created_at, last_sync)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.item_id, self.access_token, self.institution_name,
                  self.institution_id, self.status, self.consent_expiration,
                  self.transaction_cursor, self.created_at, self.last_sync))
            self.id = cursor.lastrowid
        else:
            db.execute("""
                UPDATE plaid_items SET
                item_id = ?, access_token = ?, institution_name = ?, institution_id = ?,
                status = ?, consent_expiration = ?, transaction_cursor = ?,
                created_at = ?, last_sync = ?
                WHERE id = ?
            """, (self.item_id, self.access_token, self.institution_name,
                  self.institution_id, self.status, self.consent_expiration,
                  self.transaction_cursor, self.created_at, self.last_sync, self.id))
        db.commit()
        return self

    def delete(self):
        if self.id:
            db = Database()
            # CASCADE will remove mappings
            db.execute("DELETE FROM plaid_items WHERE id = ?", (self.id,))
            db.commit()

    def load_mappings(self) -> List[PlaidAccountMapping]:
        if self.id is None:
            return []
        return PlaidAccountMapping.get_by_item(self.id)

    @classmethod
    def get_by_id(cls, item_db_id: int) -> Optional['PlaidItem']:
        db = Database()
        row = db.execute("SELECT * FROM plaid_items WHERE id = ?", (item_db_id,)).fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls) -> List['PlaidItem']:
        db = Database()
        rows = db.execute("SELECT * FROM plaid_items ORDER BY institution_name").fetchall()
        return [cls(**dict(row)) for row in rows]
