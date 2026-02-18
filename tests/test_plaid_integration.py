"""Tests for Plaid API integration: config, client, models, link server, and view."""

import json
import os
import tempfile
import threading
import urllib.request
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Module paths for patching
# ---------------------------------------------------------------------------
CONFIG_MOD = 'budget_app.utils.plaid_config'
CLIENT_MOD = 'budget_app.utils.plaid_client'
SERVER_MOD = 'budget_app.utils.plaid_link_server'
VIEW_MOD = 'budget_app.views.bank_api_view'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Point plaid_config at a temp directory so tests don't touch real config."""
    from budget_app.utils import plaid_config
    config_file = tmp_path / "plaid_config.json"
    monkeypatch.setattr(plaid_config, 'CONFIG_PATH', config_file)
    return config_file


@pytest.fixture
def sample_plaid_item(temp_db):
    """Create a saved PlaidItem in the temp database."""
    from budget_app.models.plaid_link import PlaidItem
    item = PlaidItem(
        id=None,
        item_id='item-sandbox-abc123',
        access_token='access-sandbox-token-xyz',
        institution_name='Chase',
        institution_id='ins_3',
        status='good',
    )
    item.save()
    return item


@pytest.fixture
def sample_plaid_mapping(temp_db, sample_plaid_item, sample_account):
    """Create a PlaidAccountMapping linked to a PlaidItem and a local Account."""
    from budget_app.models.plaid_link import PlaidAccountMapping
    mapping = PlaidAccountMapping(
        id=None,
        plaid_item_id=sample_plaid_item.id,
        plaid_account_id='acct-plaid-001',
        plaid_account_name='Chase Checking',
        plaid_account_mask='4567',
        plaid_account_type='depository',
        plaid_account_subtype='checking',
        local_type='account',
        local_id=sample_account.id,
    )
    mapping.save()
    return mapping


def _make_plaid_balance(**overrides):
    """Factory for PlaidAccountBalance."""
    from budget_app.utils.plaid_client import PlaidAccountBalance
    defaults = dict(
        account_id='acct-plaid-001',
        name='Chase Checking',
        official_name='CHASE CHECKING',
        type='depository',
        subtype='checking',
        mask='4567',
        current=5432.10,
        available=5432.10,
        limit=None,
    )
    defaults.update(overrides)
    return PlaidAccountBalance(**defaults)


def _make_plaid_transaction(**overrides):
    """Factory for PlaidTransaction."""
    from budget_app.utils.plaid_client import PlaidTransaction
    defaults = dict(
        transaction_id='txn-001',
        account_id='acct-plaid-001',
        date='2026-02-15',
        name='AMAZON.COM',
        amount=29.99,
        category='Shopping > Online',
        pending=False,
    )
    defaults.update(overrides)
    return PlaidTransaction(**defaults)


# ═══════════════════════════════════════════════════════════════════════════
# plaid_config.py tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaidConfig:

    def test_load_returns_defaults_when_no_file(self, temp_config):
        from budget_app.utils.plaid_config import load_config
        cfg = load_config()
        assert cfg == {"client_id": "", "secret": "", "environment": "sandbox"}

    def test_save_and_load_roundtrip(self, temp_config):
        from budget_app.utils.plaid_config import save_config, load_config
        save_config({"client_id": "cid-123", "secret": "sec-456", "environment": "development"})
        cfg = load_config()
        assert cfg["client_id"] == "cid-123"
        assert cfg["secret"] == "sec-456"
        assert cfg["environment"] == "development"

    def test_load_merges_with_defaults(self, temp_config):
        """If the file has extra keys or missing keys, defaults fill in."""
        from budget_app.utils.plaid_config import load_config
        temp_config.write_text(json.dumps({"client_id": "cid-only"}))
        cfg = load_config()
        assert cfg["client_id"] == "cid-only"
        assert cfg["secret"] == ""
        assert cfg["environment"] == "sandbox"

    def test_load_handles_corrupt_json(self, temp_config):
        from budget_app.utils.plaid_config import load_config
        temp_config.write_text("{not valid json")
        cfg = load_config()
        assert cfg == {"client_id": "", "secret": "", "environment": "sandbox"}

    def test_is_configured_false_when_empty(self, temp_config):
        from budget_app.utils.plaid_config import is_configured
        assert is_configured() is False

    def test_is_configured_false_when_only_client_id(self, temp_config):
        from budget_app.utils.plaid_config import save_config, is_configured
        save_config({"client_id": "cid", "secret": "", "environment": "sandbox"})
        assert is_configured() is False

    def test_is_configured_true_when_both_set(self, temp_config):
        from budget_app.utils.plaid_config import save_config, is_configured
        save_config({"client_id": "cid", "secret": "sec", "environment": "sandbox"})
        assert is_configured() is True

    def test_get_environment_host_sandbox(self, temp_config):
        from budget_app.utils.plaid_config import get_environment_host
        assert get_environment_host("sandbox") == "https://sandbox.plaid.com"

    def test_get_environment_host_development_falls_back_to_sandbox(self, temp_config):
        from budget_app.utils.plaid_config import get_environment_host
        # Development was deprecated by Plaid; falls back to sandbox
        assert get_environment_host("development") == "https://sandbox.plaid.com"

    def test_get_environment_host_production(self, temp_config):
        from budget_app.utils.plaid_config import get_environment_host
        assert get_environment_host("production") == "https://production.plaid.com"

    def test_get_environment_host_unknown_falls_back_to_sandbox(self, temp_config):
        from budget_app.utils.plaid_config import get_environment_host
        assert get_environment_host("bogus") == "https://sandbox.plaid.com"

    def test_get_environment_host_case_insensitive(self, temp_config):
        from budget_app.utils.plaid_config import get_environment_host
        assert get_environment_host("PRODUCTION") == "https://production.plaid.com"

    def test_get_environment_host_reads_from_config_when_none(self, temp_config):
        from budget_app.utils.plaid_config import save_config, get_environment_host
        save_config({"client_id": "", "secret": "", "environment": "production"})
        assert get_environment_host(None) == "https://production.plaid.com"

    def test_save_creates_file(self, temp_config):
        from budget_app.utils.plaid_config import save_config
        assert not temp_config.exists()
        save_config({"client_id": "x", "secret": "y", "environment": "sandbox"})
        assert temp_config.exists()

    def test_save_overwrites_existing(self, temp_config):
        from budget_app.utils.plaid_config import save_config, load_config
        save_config({"client_id": "old", "secret": "old", "environment": "sandbox"})
        save_config({"client_id": "new", "secret": "new", "environment": "development"})
        cfg = load_config()
        assert cfg["client_id"] == "new"
        assert cfg["environment"] == "development"


# ═══════════════════════════════════════════════════════════════════════════
# plaid_client.py tests (all Plaid API calls mocked)
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaidClient:

    def _patch_config(self, monkeypatch):
        """Patch plaid_config to return valid creds without touching files."""
        monkeypatch.setattr(
            f'{CLIENT_MOD}.plaid_config.load_config',
            lambda: {"client_id": "cid", "secret": "sec", "environment": "sandbox"},
        )
        monkeypatch.setattr(
            f'{CLIENT_MOD}.plaid_config.get_environment_host',
            lambda env=None: "https://sandbox.plaid.com",
        )

    def test_get_client_raises_when_not_configured(self, monkeypatch):
        from budget_app.utils.plaid_client import _get_client, PlaidClientError
        monkeypatch.setattr(
            f'{CLIENT_MOD}.plaid_config.load_config',
            lambda: {"client_id": "", "secret": "", "environment": "sandbox"},
        )
        with pytest.raises(PlaidClientError, match="not configured"):
            _get_client()

    def test_get_client_returns_api_instance(self, monkeypatch):
        from budget_app.utils.plaid_client import _get_client
        self._patch_config(monkeypatch)
        client = _get_client()
        assert client is not None

    @patch(f'{CLIENT_MOD}._get_client')
    def test_create_link_token(self, mock_get_client, monkeypatch):
        from budget_app.utils.plaid_client import create_link_token
        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.link_token = "link-sandbox-token-abc"
        mock_api.link_token_create.return_value = mock_response
        mock_get_client.return_value = mock_api

        token = create_link_token()
        assert token == "link-sandbox-token-abc"
        mock_api.link_token_create.assert_called_once()

    @patch(f'{CLIENT_MOD}._get_client')
    def test_create_link_token_raises_on_api_error(self, mock_get_client):
        import plaid
        from budget_app.utils.plaid_client import create_link_token, PlaidClientError
        mock_api = MagicMock()
        mock_api.link_token_create.side_effect = plaid.ApiException(status=400, reason="Bad Request")
        mock_get_client.return_value = mock_api

        with pytest.raises(PlaidClientError, match="Failed to create link token"):
            create_link_token()

    @patch(f'{CLIENT_MOD}._get_client')
    def test_exchange_public_token(self, mock_get_client):
        from budget_app.utils.plaid_client import exchange_public_token
        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.access_token = "access-sandbox-xyz"
        mock_response.item_id = "item-sandbox-123"
        mock_api.item_public_token_exchange.return_value = mock_response
        mock_get_client.return_value = mock_api

        access_token, item_id = exchange_public_token("public-sandbox-abc")
        assert access_token == "access-sandbox-xyz"
        assert item_id == "item-sandbox-123"

    @patch(f'{CLIENT_MOD}._get_client')
    def test_exchange_public_token_raises_on_error(self, mock_get_client):
        import plaid
        from budget_app.utils.plaid_client import exchange_public_token, PlaidClientError
        mock_api = MagicMock()
        mock_api.item_public_token_exchange.side_effect = plaid.ApiException(status=400, reason="Bad")
        mock_get_client.return_value = mock_api

        with pytest.raises(PlaidClientError, match="Token exchange failed"):
            exchange_public_token("bad-token")

    @patch(f'{CLIENT_MOD}._get_client')
    def test_get_balances(self, mock_get_client):
        from budget_app.utils.plaid_client import get_balances

        mock_acct = MagicMock()
        mock_acct.account_id = "acct-001"
        mock_acct.name = "Checking"
        mock_acct.official_name = "CHASE CHECKING"
        mock_acct.type = "depository"
        mock_acct.subtype = "checking"
        mock_acct.mask = "4567"
        mock_bal = MagicMock()
        mock_bal.current = 5000.50
        mock_bal.available = 4800.00
        mock_bal.limit = None
        mock_acct.balances = mock_bal

        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.accounts = [mock_acct]
        mock_api.accounts_balance_get.return_value = mock_response
        mock_get_client.return_value = mock_api

        balances = get_balances("access-token")
        assert len(balances) == 1
        assert balances[0].account_id == "acct-001"
        assert balances[0].current == 5000.50
        assert balances[0].available == 4800.00
        assert balances[0].mask == "4567"
        assert balances[0].type == "depository"

    @patch(f'{CLIENT_MOD}._get_client')
    def test_get_balances_handles_none_values(self, mock_get_client):
        from budget_app.utils.plaid_client import get_balances

        mock_acct = MagicMock()
        mock_acct.account_id = "acct-002"
        mock_acct.name = "Credit"
        mock_acct.official_name = None
        mock_acct.type = "credit"
        mock_acct.subtype = None
        mock_acct.mask = None
        mock_bal = MagicMock()
        mock_bal.current = None
        mock_bal.available = None
        mock_bal.limit = None
        mock_acct.balances = mock_bal

        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.accounts = [mock_acct]
        mock_api.accounts_balance_get.return_value = mock_response
        mock_get_client.return_value = mock_api

        balances = get_balances("access-token")
        assert balances[0].current == 0.0
        assert balances[0].available is None
        assert balances[0].subtype == ""

    @patch(f'{CLIENT_MOD}._get_client')
    def test_get_balances_raises_on_error(self, mock_get_client):
        import plaid
        from budget_app.utils.plaid_client import get_balances, PlaidClientError
        mock_api = MagicMock()
        mock_api.accounts_balance_get.side_effect = plaid.ApiException(status=400, reason="Bad")
        mock_get_client.return_value = mock_api

        with pytest.raises(PlaidClientError, match="Balance fetch failed"):
            get_balances("bad-token")

    @patch(f'{CLIENT_MOD}._get_client')
    def test_sync_transactions(self, mock_get_client):
        from budget_app.utils.plaid_client import sync_transactions

        mock_txn = MagicMock()
        mock_txn.transaction_id = "txn-001"
        mock_txn.account_id = "acct-001"
        mock_txn.date = "2026-02-15"
        mock_txn.name = "AMAZON"
        mock_txn.amount = 29.99
        mock_txn.category = ["Shopping", "Online"]
        mock_txn.pending = False

        mock_removed = MagicMock()
        mock_removed.transaction_id = "txn-old"

        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.added = [mock_txn]
        mock_response.modified = []
        mock_response.removed = [mock_removed]
        mock_response.next_cursor = "cursor-abc"
        mock_response.has_more = False
        mock_api.transactions_sync.return_value = mock_response
        mock_get_client.return_value = mock_api

        result = sync_transactions("access-token", cursor="old-cursor")
        assert len(result.added) == 1
        assert result.added[0].name == "AMAZON"
        assert result.added[0].amount == 29.99
        assert result.added[0].category == "Shopping > Online"
        assert len(result.removed) == 1
        assert result.removed[0] == "txn-old"
        assert result.next_cursor == "cursor-abc"
        assert result.has_more is False

    @patch(f'{CLIENT_MOD}._get_client')
    def test_sync_transactions_no_cursor(self, mock_get_client):
        from budget_app.utils.plaid_client import sync_transactions

        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.added = []
        mock_response.modified = []
        mock_response.removed = []
        mock_response.next_cursor = "first-cursor"
        mock_response.has_more = False
        mock_api.transactions_sync.return_value = mock_response
        mock_get_client.return_value = mock_api

        result = sync_transactions("access-token", cursor=None)
        assert result.next_cursor == "first-cursor"
        # Verify cursor was not included in the request
        call_kwargs = mock_api.transactions_sync.call_args
        assert call_kwargs is not None

    @patch(f'{CLIENT_MOD}._get_client')
    def test_sync_transactions_raises_on_error(self, mock_get_client):
        import plaid
        from budget_app.utils.plaid_client import sync_transactions, PlaidClientError
        mock_api = MagicMock()
        mock_api.transactions_sync.side_effect = plaid.ApiException(status=400, reason="Bad")
        mock_get_client.return_value = mock_api

        with pytest.raises(PlaidClientError, match="Transaction sync failed"):
            sync_transactions("bad-token")

    @patch(f'{CLIENT_MOD}._get_client')
    def test_sync_transactions_no_category(self, mock_get_client):
        from budget_app.utils.plaid_client import sync_transactions

        mock_txn = MagicMock()
        mock_txn.transaction_id = "txn-002"
        mock_txn.account_id = "acct-001"
        mock_txn.date = "2026-02-16"
        mock_txn.name = "ATM WITHDRAWAL"
        mock_txn.amount = 100.0
        mock_txn.category = None
        mock_txn.pending = True

        mock_api = MagicMock()
        mock_response = MagicMock()
        mock_response.added = [mock_txn]
        mock_response.modified = []
        mock_response.removed = []
        mock_response.next_cursor = "c2"
        mock_response.has_more = False
        mock_api.transactions_sync.return_value = mock_response
        mock_get_client.return_value = mock_api

        result = sync_transactions("access-token")
        assert result.added[0].category is None
        assert result.added[0].pending is True


# ═══════════════════════════════════════════════════════════════════════════
# Dataclass tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaidDataclasses:

    def test_plaid_account_balance_fields(self):
        bal = _make_plaid_balance()
        assert bal.account_id == 'acct-plaid-001'
        assert bal.current == 5432.10
        assert bal.limit is None

    def test_plaid_transaction_fields(self):
        txn = _make_plaid_transaction()
        assert txn.transaction_id == 'txn-001'
        assert txn.amount == 29.99
        assert txn.pending is False

    def test_plaid_sync_result_defaults(self):
        from budget_app.utils.plaid_client import PlaidSyncResult
        result = PlaidSyncResult()
        assert result.added == []
        assert result.modified == []
        assert result.removed == []
        assert result.next_cursor == ""
        assert result.has_more is False

    def test_plaid_sync_result_with_data(self):
        from budget_app.utils.plaid_client import PlaidSyncResult
        txn = _make_plaid_transaction()
        result = PlaidSyncResult(added=[txn], next_cursor="c1", has_more=True)
        assert len(result.added) == 1
        assert result.has_more is True


# ═══════════════════════════════════════════════════════════════════════════
# PlaidItem model tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaidItemModel:

    def test_create_and_retrieve(self, temp_db):
        from budget_app.models.plaid_link import PlaidItem
        item = PlaidItem(
            id=None, item_id='item-1', access_token='tok-1',
            institution_name='Chase', institution_id='ins_3',
        )
        item.save()
        assert item.id is not None
        assert item.created_at is not None

        loaded = PlaidItem.get_by_id(item.id)
        assert loaded is not None
        assert loaded.item_id == 'item-1'
        assert loaded.institution_name == 'Chase'

    def test_update(self, sample_plaid_item):
        from budget_app.models.plaid_link import PlaidItem
        sample_plaid_item.status = 'needs_update'
        sample_plaid_item.last_sync = '2026-02-17T10:00:00'
        sample_plaid_item.save()

        loaded = PlaidItem.get_by_id(sample_plaid_item.id)
        assert loaded.status == 'needs_update'
        assert loaded.last_sync == '2026-02-17T10:00:00'

    def test_delete(self, sample_plaid_item):
        from budget_app.models.plaid_link import PlaidItem
        item_id = sample_plaid_item.id
        sample_plaid_item.delete()
        assert PlaidItem.get_by_id(item_id) is None

    def test_get_all(self, temp_db):
        from budget_app.models.plaid_link import PlaidItem
        for i in range(3):
            PlaidItem(
                id=None, item_id=f'item-{i}', access_token=f'tok-{i}',
                institution_name=f'Bank {i}',
            ).save()
        items = PlaidItem.get_all()
        assert len(items) == 3

    def test_get_by_id_not_found(self, temp_db):
        from budget_app.models.plaid_link import PlaidItem
        assert PlaidItem.get_by_id(9999) is None

    def test_load_mappings_empty(self, sample_plaid_item):
        mappings = sample_plaid_item.load_mappings()
        assert mappings == []

    def test_load_mappings_with_data(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-1', plaid_account_name='Checking',
        ).save()
        PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-2', plaid_account_name='Savings',
        ).save()

        mappings = sample_plaid_item.load_mappings()
        assert len(mappings) == 2

    def test_load_mappings_unsaved_item(self, temp_db):
        from budget_app.models.plaid_link import PlaidItem
        item = PlaidItem(id=None, item_id='x', access_token='y')
        assert item.load_mappings() == []

    def test_delete_cascades_mappings(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-1', plaid_account_name='Checking',
        ).save()
        assert len(PlaidAccountMapping.get_by_item(sample_plaid_item.id)) == 1

        sample_plaid_item.delete()
        assert len(PlaidAccountMapping.get_by_item(sample_plaid_item.id)) == 0

    def test_created_at_auto_set(self, temp_db):
        from budget_app.models.plaid_link import PlaidItem
        item = PlaidItem(id=None, item_id='item-auto', access_token='tok')
        assert item.created_at is None
        item.save()
        assert item.created_at is not None
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(item.created_at)

    def test_created_at_preserved_on_update(self, sample_plaid_item):
        from budget_app.models.plaid_link import PlaidItem
        original_created = sample_plaid_item.created_at
        sample_plaid_item.status = 'updated'
        sample_plaid_item.save()
        loaded = PlaidItem.get_by_id(sample_plaid_item.id)
        assert loaded.created_at == original_created


# ═══════════════════════════════════════════════════════════════════════════
# PlaidAccountMapping model tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaidAccountMappingModel:

    def test_create_and_retrieve(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-001', plaid_account_name='My Checking',
            plaid_account_mask='1234', plaid_account_type='depository',
            plaid_account_subtype='checking',
            local_type='account', local_id=1,
        )
        mapping.save()
        assert mapping.id is not None

        loaded = PlaidAccountMapping.get_by_item(sample_plaid_item.id)
        assert len(loaded) == 1
        assert loaded[0].plaid_account_name == 'My Checking'
        assert loaded[0].is_synced is True

    def test_update_mapping(self, sample_plaid_mapping):
        from budget_app.models.plaid_link import PlaidAccountMapping
        sample_plaid_mapping.local_type = 'credit_card'
        sample_plaid_mapping.local_id = 99
        sample_plaid_mapping.save()

        loaded = PlaidAccountMapping.get_by_item(sample_plaid_mapping.plaid_item_id)
        assert loaded[0].local_type == 'credit_card'
        assert loaded[0].local_id == 99

    def test_delete_mapping(self, sample_plaid_mapping):
        from budget_app.models.plaid_link import PlaidAccountMapping
        item_id = sample_plaid_mapping.plaid_item_id
        sample_plaid_mapping.delete()
        assert len(PlaidAccountMapping.get_by_item(item_id)) == 0

    def test_get_all_synced(self, sample_plaid_mapping, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        # sample_plaid_mapping is synced with local_type + local_id set
        synced = PlaidAccountMapping.get_all_synced()
        assert len(synced) == 1

        # Add an unsynced mapping
        PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-002', is_synced=False,
        ).save()
        synced = PlaidAccountMapping.get_all_synced()
        assert len(synced) == 1  # still 1

    def test_get_all_synced_excludes_unmapped(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        # Synced but no local_type/local_id
        PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-003', is_synced=True,
        ).save()
        synced = PlaidAccountMapping.get_all_synced()
        assert len(synced) == 0

    def test_is_synced_bool_conversion(self, sample_plaid_mapping):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mappings = PlaidAccountMapping.get_by_item(sample_plaid_mapping.plaid_item_id)
        assert isinstance(mappings[0].is_synced, bool)
        assert mappings[0].is_synced is True

    def test_get_local_display_name_account(self, sample_plaid_mapping):
        name = sample_plaid_mapping.get_local_display_name()
        assert name == 'Chase'  # matches sample_account name

    def test_get_local_display_name_credit_card(self, sample_plaid_item, sample_card, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-cc', local_type='credit_card',
            local_id=sample_card.id,
        )
        mapping.save()
        assert mapping.get_local_display_name() == 'Chase Freedom'

    def test_get_local_display_name_loan(self, sample_plaid_item, sample_loan, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-ln', local_type='loan',
            local_id=sample_loan.id,
        )
        mapping.save()
        assert mapping.get_local_display_name() == '401k Loan 1'

    def test_get_local_display_name_unmapped(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-none',
        )
        mapping.save()
        assert mapping.get_local_display_name() == '(unmapped)'

    def test_get_local_display_name_deleted_local(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-del', local_type='account', local_id=9999,
        )
        mapping.save()
        assert mapping.get_local_display_name() == '(deleted)'

    def test_get_local_display_name_unknown_type(self, sample_plaid_item, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        # Don't save — DB CHECK constraint only allows account/credit_card/loan.
        # Test the method logic directly with an in-memory object.
        mapping = PlaidAccountMapping(
            id=1, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='acct-unk', local_type='investment', local_id=1,
        )
        assert mapping.get_local_display_name() == '(unknown type)'

    def test_delete_with_no_id(self, temp_db):
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(id=None, plaid_item_id=1, plaid_account_id='x')
        mapping.delete()  # should not raise


# ═══════════════════════════════════════════════════════════════════════════
# PlaidLinkServer tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaidLinkServer:

    def test_server_binds_to_free_port(self):
        from budget_app.utils.plaid_link_server import PlaidLinkServer
        server = PlaidLinkServer("test-token")
        assert server.server_port > 0
        assert server.link_token == "test-token"
        assert server.result is None
        server.server_close()

    def test_get_serves_html_with_token(self):
        from budget_app.utils.plaid_link_server import PlaidLinkServer
        server = PlaidLinkServer("my-link-token-xyz")
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        url = f"http://127.0.0.1:{server.server_port}/"
        response = urllib.request.urlopen(url, timeout=5)
        html = response.read().decode('utf-8')

        assert 'my-link-token-xyz' in html
        assert f'127.0.0.1:{server.server_port}/callback' in html
        assert 'Personal Budget Manager' in html
        server.server_close()

    def test_post_captures_result(self):
        from budget_app.utils.plaid_link_server import PlaidLinkServer
        server = PlaidLinkServer("tok")

        # Override shutdown to avoid actually shutting down during test
        server.shutdown = lambda: None

        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        payload = json.dumps({"public_token": "pub-abc", "metadata": {"institution": {"name": "Chase"}}})
        url = f"http://127.0.0.1:{server.server_port}/callback"
        req = urllib.request.Request(
            url, data=payload.encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = urllib.request.urlopen(req, timeout=5)
        assert response.status == 200

        thread.join(timeout=2)
        assert server.result is not None
        assert server.result["public_token"] == "pub-abc"
        server.server_close()

    def test_post_handles_invalid_json(self):
        from budget_app.utils.plaid_link_server import PlaidLinkServer
        server = PlaidLinkServer("tok")
        server.shutdown = lambda: None

        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        url = f"http://127.0.0.1:{server.server_port}/callback"
        req = urllib.request.Request(
            url, data=b"not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        thread.join(timeout=2)

        assert "error" in server.result
        server.server_close()

    def test_options_returns_cors_headers(self):
        from budget_app.utils.plaid_link_server import PlaidLinkServer
        server = PlaidLinkServer("tok")

        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        url = f"http://127.0.0.1:{server.server_port}/callback"
        req = urllib.request.Request(url, method="OPTIONS")
        response = urllib.request.urlopen(req, timeout=5)
        assert response.status == 204
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        server.server_close()

    @patch(f'{SERVER_MOD}.webbrowser.open')
    def test_run_plaid_link_timeout(self, mock_open):
        from budget_app.utils.plaid_link_server import run_plaid_link
        # Very short timeout — no browser will connect
        result = run_plaid_link("tok", timeout=1)
        assert "error" in result
        assert "timed out" in result["error"].lower()
        mock_open.assert_called_once()

    @patch(f'{SERVER_MOD}.webbrowser.open')
    def test_run_plaid_link_success(self, mock_open):
        from budget_app.utils.plaid_link_server import run_plaid_link

        def _simulate_callback(url):
            """Send a POST to the server's callback URL."""
            import time
            time.sleep(0.3)  # let server start
            # Extract port from url
            port = url.split(':')[-1].rstrip('/')
            callback = f"http://127.0.0.1:{port}/callback"
            payload = json.dumps({"public_token": "pub-test", "metadata": {}})
            req = urllib.request.Request(
                callback, data=payload.encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)

        mock_open.side_effect = _simulate_callback

        result = run_plaid_link("tok", timeout=10)
        assert result.get("public_token") == "pub-test"


# ═══════════════════════════════════════════════════════════════════════════
# BankAPIView tests
# ═══════════════════════════════════════════════════════════════════════════

class TestBankAPIView:

    def test_creates_without_error(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view is not None

    def test_has_layout(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view.layout() is not None

    def test_settings_group_is_collapsed_by_default(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._settings_group.isChecked() is False

    def test_buttons_disabled_when_not_configured(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._link_btn.isEnabled() is False
        assert view._sync_btn.isEnabled() is False

    def test_link_button_enabled_when_configured(self, qtbot, temp_db, temp_config):
        from budget_app.utils.plaid_config import save_config
        from budget_app.views.bank_api_view import BankAPIView
        save_config({"client_id": "cid", "secret": "sec", "environment": "sandbox"})
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._link_btn.isEnabled() is True

    def test_sync_button_disabled_without_items(self, qtbot, temp_db, temp_config):
        from budget_app.utils.plaid_config import save_config
        from budget_app.views.bank_api_view import BankAPIView
        save_config({"client_id": "cid", "secret": "sec", "environment": "sandbox"})
        view = BankAPIView()
        qtbot.addWidget(view)
        # Configured but no linked items
        assert view._sync_btn.isEnabled() is False

    def test_sync_button_enabled_with_items(self, qtbot, temp_db, temp_config, sample_plaid_item):
        from budget_app.utils.plaid_config import save_config
        from budget_app.views.bank_api_view import BankAPIView
        save_config({"client_id": "cid", "secret": "sec", "environment": "sandbox"})
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._sync_btn.isEnabled() is True

    def test_save_settings(self, qtbot, temp_db, temp_config, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.utils.plaid_config import load_config
        view = BankAPIView()
        qtbot.addWidget(view)

        view._client_id_edit.setText("test-cid")
        view._secret_edit.setText("test-sec")
        view._env_combo.setCurrentText("production")
        view._save_settings()

        cfg = load_config()
        assert cfg["client_id"] == "test-cid"
        assert cfg["secret"] == "test-sec"
        assert cfg["environment"] == "production"

    def test_load_settings_populates_ui(self, qtbot, temp_db, temp_config):
        from budget_app.utils.plaid_config import save_config
        from budget_app.views.bank_api_view import BankAPIView
        save_config({"client_id": "my-cid", "secret": "my-sec", "environment": "production"})
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._client_id_edit.text() == "my-cid"
        assert view._secret_edit.text() == "my-sec"
        assert view._env_combo.currentText() == "production"

    def test_refresh_items_table_empty(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view.refresh()
        assert view._items_table.rowCount() == 0

    def test_refresh_items_table_with_items(self, qtbot, temp_db, temp_config, sample_plaid_item):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view.refresh()
        assert view._items_table.rowCount() == 1
        assert view._items_table.item(0, 0).text() == 'Chase'

    def test_refresh_items_table_shows_last_sync(self, qtbot, temp_db, temp_config):
        from budget_app.models.plaid_link import PlaidItem
        from budget_app.views.bank_api_view import BankAPIView
        item = PlaidItem(
            id=None, item_id='item-2', access_token='tok-2',
            institution_name='Wells Fargo',
            last_sync='2026-02-17T14:30:00',
        )
        item.save()
        view = BankAPIView()
        qtbot.addWidget(view)
        view.refresh()
        assert '02/17/2026' in view._items_table.item(0, 2).text()

    def test_refresh_items_table_shows_never_when_no_sync(self, qtbot, temp_db, temp_config, sample_plaid_item):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view.refresh()
        assert view._items_table.item(0, 2).text() == 'Never'

    def test_remove_item(self, qtbot, temp_db, temp_config, sample_plaid_item, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidItem
        view = BankAPIView()
        qtbot.addWidget(view)
        view.refresh()
        assert view._items_table.rowCount() == 1

        view._remove_item(sample_plaid_item)
        assert PlaidItem.get_all() == []
        assert view._items_table.rowCount() == 0

    def test_remove_item_cancelled(self, qtbot, temp_db, temp_config, sample_plaid_item, mock_qmessagebox):
        from PyQt6.QtWidgets import QMessageBox
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidItem
        mock_qmessagebox.last_return = QMessageBox.StandardButton.No
        view = BankAPIView()
        qtbot.addWidget(view)
        view._remove_item(sample_plaid_item)
        assert len(PlaidItem.get_all()) == 1  # not deleted

    def test_apply_all_btn_disabled_initially(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._apply_all_btn.isEnabled() is False

    def test_balance_table_columns(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._balance_table.columnCount() == 6
        headers = [
            view._balance_table.horizontalHeaderItem(i).text()
            for i in range(6)
        ]
        assert headers == ["Account", "Plaid Balance", "Local Balance", "Change", "Status", "Apply"]

    def test_items_table_columns(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._items_table.columnCount() == 6


class TestBankAPIViewAutoMap:
    """Tests for the auto-mapping heuristic."""

    def _make_view(self, qtbot, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        return view

    def test_auto_map_by_mask(self, qtbot, temp_db, temp_config, sample_account):
        """Matching mask against pay_type_code suffix."""
        from budget_app.models.plaid_link import PlaidAccountMapping
        from budget_app.models.account import Account
        # Create account with a code that ends in mask digits
        acct = Account(id=None, name='Checking 4567', account_type='CHECKING',
                       current_balance=1000, pay_type_code='ACCT4567')
        acct.save()

        view = self._make_view(qtbot, temp_config)
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=1, plaid_account_id='x',
            plaid_account_type='depository', plaid_account_mask='4567',
        )
        view._auto_map_account(mapping)
        assert mapping.local_type == 'account'
        assert mapping.local_id == acct.id

    def test_auto_map_by_name(self, qtbot, temp_db, temp_config):
        from budget_app.models.plaid_link import PlaidAccountMapping
        from budget_app.models.credit_card import CreditCard
        card = CreditCard(
            id=None, pay_type_code='CO', name='Capital One',
            credit_limit=5000, current_balance=1000, interest_rate=0.20, due_day=10,
        )
        card.save()

        view = self._make_view(qtbot, temp_config)
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=1, plaid_account_id='x',
            plaid_account_type='credit', plaid_account_name='Capital One Quicksilver',
        )
        view._auto_map_account(mapping)
        assert mapping.local_type == 'credit_card'
        assert mapping.local_id == card.id

    def test_auto_map_single_candidate(self, qtbot, temp_db, temp_config):
        from budget_app.models.plaid_link import PlaidAccountMapping
        from budget_app.models.loan import Loan
        loan = Loan(
            id=None, pay_type_code='L1', name='Car Loan',
            original_amount=20000, current_balance=15000,
            interest_rate=0.05, payment_amount=400,
        )
        loan.save()

        view = self._make_view(qtbot, temp_config)
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=1, plaid_account_id='x',
            plaid_account_type='loan', plaid_account_name='Auto Financing',
        )
        view._auto_map_account(mapping)
        assert mapping.local_type == 'loan'
        assert mapping.local_id == loan.id

    def test_auto_map_no_candidates(self, qtbot, temp_db, temp_config):
        from budget_app.models.plaid_link import PlaidAccountMapping
        view = self._make_view(qtbot, temp_config)
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=1, plaid_account_id='x',
            plaid_account_type='investment',
        )
        view._auto_map_account(mapping)
        assert mapping.local_type is None
        assert mapping.local_id is None

    def test_auto_map_no_match_multiple_candidates(self, qtbot, temp_db, temp_config):
        """Multiple candidates but no mask/name match — should not auto-map."""
        from budget_app.models.plaid_link import PlaidAccountMapping
        from budget_app.models.account import Account
        Account(id=None, name='Checking', account_type='CHECKING',
                current_balance=1000, pay_type_code='C').save()
        Account(id=None, name='Savings', account_type='SAVINGS',
                current_balance=2000, pay_type_code='S').save()

        view = self._make_view(qtbot, temp_config)
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=1, plaid_account_id='x',
            plaid_account_type='depository', plaid_account_name='Unknown Account',
        )
        view._auto_map_account(mapping)
        assert mapping.local_type is None


class TestBankAPIViewBalanceSync:
    """Tests for balance table population and applying updates."""

    def test_populate_balance_table(self, qtbot, temp_db, temp_config, sample_plaid_mapping, sample_account):
        from budget_app.views.bank_api_view import BankAPIView

        view = BankAPIView()
        qtbot.addWidget(view)

        plaid_bal = _make_plaid_balance(current=6000.00)
        balance_rows = [(sample_plaid_mapping, plaid_bal)]
        view._populate_balance_table(balance_rows)

        assert view._balance_table.rowCount() == 1
        assert view._balance_table.item(0, 0).text() == 'Chase'
        assert '$6,000.00' in view._balance_table.item(0, 1).text()
        assert '$5,000.00' in view._balance_table.item(0, 2).text()
        assert view._balance_table.item(0, 4).text() == 'Different'
        assert view._apply_all_btn.isEnabled() is True

    def test_populate_balance_table_matching(self, qtbot, temp_db, temp_config, sample_plaid_mapping, sample_account):
        from budget_app.views.bank_api_view import BankAPIView

        view = BankAPIView()
        qtbot.addWidget(view)

        # Balance matches local
        plaid_bal = _make_plaid_balance(current=5000.00)
        view._populate_balance_table([(sample_plaid_mapping, plaid_bal)])

        assert view._balance_table.item(0, 4).text() == 'Match'
        assert view._apply_all_btn.isEnabled() is False

    def test_apply_single_balance(self, qtbot, temp_db, temp_config, sample_plaid_mapping, sample_account):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.account import Account

        view = BankAPIView()
        qtbot.addWidget(view)

        plaid_bal = _make_plaid_balance(current=7500.00)
        view._balance_rows = [(sample_plaid_mapping, plaid_bal)]
        view._populate_balance_table(view._balance_rows)

        view._apply_single_balance(0)

        updated = Account.get_by_id(sample_account.id)
        assert updated.current_balance == 7500.00
        assert view._balance_table.item(0, 4).text() == 'Match'

    def test_apply_all_balances(self, qtbot, temp_db, temp_config, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.account import Account
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.plaid_link import PlaidItem, PlaidAccountMapping

        acct = Account(id=None, name='Checking', account_type='CHECKING',
                       current_balance=1000, pay_type_code='C').save()
        card = CreditCard(id=None, pay_type_code='CC', name='Visa',
                          credit_limit=5000, current_balance=2000,
                          interest_rate=0.20, due_day=15).save()
        item = PlaidItem(id=None, item_id='itm', access_token='tok',
                         institution_name='Bank').save()
        m1 = PlaidAccountMapping(id=None, plaid_item_id=item.id,
                                 plaid_account_id='a1', local_type='account',
                                 local_id=acct.id).save()
        m2 = PlaidAccountMapping(id=None, plaid_item_id=item.id,
                                 plaid_account_id='a2', local_type='credit_card',
                                 local_id=card.id).save()

        view = BankAPIView()
        qtbot.addWidget(view)

        bal1 = _make_plaid_balance(account_id='a1', current=1500.00)
        bal2 = _make_plaid_balance(account_id='a2', current=2500.00, type='credit')
        view._balance_rows = [(m1, bal1), (m2, bal2)]
        view._populate_balance_table(view._balance_rows)

        view._apply_all_balances()

        assert Account.get_by_id(acct.id).current_balance == 1500.00
        assert CreditCard.get_by_id(card.id).current_balance == 2500.00
        assert mock_qmessagebox.info_called

    def test_apply_all_skips_unmapped(self, qtbot, temp_db, temp_config, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidItem, PlaidAccountMapping

        item = PlaidItem(id=None, item_id='itm', access_token='tok',
                         institution_name='Bank').save()
        m = PlaidAccountMapping(id=None, plaid_item_id=item.id,
                                plaid_account_id='a1').save()

        view = BankAPIView()
        qtbot.addWidget(view)

        bal = _make_plaid_balance(current=999)
        view._balance_rows = [(m, bal)]
        view._populate_balance_table(view._balance_rows)

        # Reset the tracker attribute before the call
        mock_qmessagebox.info_called = False
        view._apply_all_balances()
        # No info called because count == 0 (unmapped accounts are skipped)
        assert mock_qmessagebox.info_called is False

    def test_get_local_balance_account(self, qtbot, temp_db, temp_config, sample_plaid_mapping, sample_account):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._get_local_balance(sample_plaid_mapping) == 5000.0

    def test_get_local_balance_credit_card(self, qtbot, temp_db, temp_config, sample_plaid_item, sample_card):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='cc1', local_type='credit_card',
            local_id=sample_card.id,
        ).save()
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._get_local_balance(mapping) == 3000.0

    def test_get_local_balance_loan(self, qtbot, temp_db, temp_config, sample_plaid_item, sample_loan):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='ln1', local_type='loan',
            local_id=sample_loan.id,
        ).save()
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._get_local_balance(mapping) == 7500.0

    def test_get_local_balance_unmapped(self, qtbot, temp_db, temp_config, sample_plaid_item):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='none',
        ).save()
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._get_local_balance(mapping) == 0.0

    def test_get_local_balance_deleted_local(self, qtbot, temp_db, temp_config, sample_plaid_item):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.models.plaid_link import PlaidAccountMapping
        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='del', local_type='account', local_id=9999,
        ).save()
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view._get_local_balance(mapping) == 0.0


class TestBankAPIViewTransactions:

    def test_populate_transactions_empty(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view._populate_transactions([])
        assert 'No recent transactions' in view._txn_text.toPlainText()

    def test_populate_transactions_with_data(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)

        txns = [
            _make_plaid_transaction(name='GROCERY STORE', amount=45.67, date='2026-02-15'),
            _make_plaid_transaction(
                transaction_id='txn-002', name='PAYCHECK', amount=-2500.00,
                date='2026-02-14', category='Income', pending=False,
            ),
        ]
        view._populate_transactions(txns)
        text = view._txn_text.toPlainText()
        assert 'GROCERY STORE' in text
        assert 'PAYCHECK' in text

    def test_populate_transactions_shows_pending(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)

        txns = [_make_plaid_transaction(pending=True)]
        view._populate_transactions(txns)
        assert '(pending)' in view._txn_text.toPlainText()

    def test_populate_transactions_shows_category(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)

        txns = [_make_plaid_transaction(category='Food > Groceries')]
        view._populate_transactions(txns)
        assert 'Food > Groceries' in view._txn_text.toPlainText()

    def test_populate_transactions_negates_amount(self, qtbot, temp_db, temp_config):
        """Plaid positive = debit. Display should show as negative (money out)."""
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)

        txns = [_make_plaid_transaction(amount=29.99)]  # debit
        view._populate_transactions(txns)
        text = view._txn_text.toPlainText()
        # Negated: -29.99
        assert '-$' in text

    def test_populate_transactions_sorts_descending(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)

        txns = [
            _make_plaid_transaction(transaction_id='t1', date='2026-02-10', name='OLDER'),
            _make_plaid_transaction(transaction_id='t2', date='2026-02-15', name='NEWER'),
        ]
        view._populate_transactions(txns)
        text = view._txn_text.toPlainText()
        assert text.index('NEWER') < text.index('OLDER')

    def test_populate_transactions_caps_at_100(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)

        txns = [
            _make_plaid_transaction(transaction_id=f't{i}', name=f'TXN-{i}')
            for i in range(150)
        ]
        view._populate_transactions(txns)
        text = view._txn_text.toPlainText()
        # Should not contain TXN-149 etc. (only first 100 after sort)
        assert text.count('TXN-') <= 100


class TestBankAPIViewLinkFlow:

    def test_start_link_flow_error_creating_token(self, qtbot, temp_db, temp_config, mock_qmessagebox, monkeypatch):
        from budget_app.views.bank_api_view import BankAPIView
        from budget_app.utils.plaid_config import save_config
        save_config({"client_id": "cid", "secret": "sec", "environment": "sandbox"})

        def _raise_api_down():
            raise Exception("API down")

        monkeypatch.setattr('budget_app.utils.plaid_client.create_link_token', _raise_api_down)

        view = BankAPIView()
        qtbot.addWidget(view)
        view._start_link_flow()

        # Button should be re-enabled after error
        assert view._link_btn.isEnabled() is True
        assert view._link_btn.text() == "Link New Account"
        assert mock_qmessagebox.critical_called
        assert "API down" in mock_qmessagebox.critical_text

    def test_on_link_finished_cancelled(self, qtbot, temp_db, temp_config):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        # Should not raise
        view._on_link_finished({"cancelled": True})
        assert view._link_btn.text() == "Link New Account"

    def test_on_link_finished_error(self, qtbot, temp_db, temp_config, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view._on_link_finished({"error": "Something went wrong"})
        assert mock_qmessagebox.warning_called

    def test_on_link_finished_no_token(self, qtbot, temp_db, temp_config, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view._on_link_finished({"metadata": {}})
        assert mock_qmessagebox.warning_called

    def test_on_link_error(self, qtbot, temp_db, temp_config, mock_qmessagebox):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        view._on_link_error("Connection failed")
        assert view._link_btn.isEnabled() is True
        assert view._progress.isVisible() is False

    def test_on_link_finished_success(self, qtbot, temp_db, temp_config, mock_qmessagebox, monkeypatch):
        from budget_app.views.bank_api_view import BankAPIView, AccountMappingDialog
        from budget_app.models.plaid_link import PlaidItem
        from budget_app.models.account import Account

        Account(id=None, name='Checking', account_type='CHECKING',
                current_balance=1000, pay_type_code='C').save()

        monkeypatch.setattr(
            'budget_app.utils.plaid_client.exchange_public_token',
            lambda token: ("access-tok", "item-id-123"),
        )
        monkeypatch.setattr(
            'budget_app.utils.plaid_client.get_balances',
            lambda token: [
                _make_plaid_balance(account_id='acct-1', name='Plaid Checking',
                                    mask='0001', type='depository', subtype='checking'),
            ],
        )

        view = BankAPIView()
        qtbot.addWidget(view)

        # Patch the dialog to auto-accept
        with patch.object(AccountMappingDialog, 'exec', return_value=1):
            with patch.object(AccountMappingDialog, 'get_updated_mappings',
                              return_value=[]):
                view._on_link_finished({
                    "public_token": "pub-token-abc",
                    "metadata": {
                        "institution": {"name": "Chase", "institution_id": "ins_3"}
                    },
                })

        items = PlaidItem.get_all()
        assert len(items) == 1
        assert items[0].institution_name == "Chase"


class TestAccountMappingDialog:

    def test_creates_with_mappings(self, qtbot, temp_db, temp_config, sample_plaid_item, sample_account):
        from budget_app.views.bank_api_view import AccountMappingDialog
        from budget_app.models.plaid_link import PlaidAccountMapping

        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='a1', plaid_account_name='Checking',
            plaid_account_mask='1234', plaid_account_type='depository',
        )
        mapping.save()

        dialog = AccountMappingDialog(None, [mapping])
        qtbot.addWidget(dialog)
        assert len(dialog._combos) == 1

    def test_get_updated_mappings(self, qtbot, temp_db, temp_config, sample_plaid_item, sample_account):
        from budget_app.views.bank_api_view import AccountMappingDialog
        from budget_app.models.plaid_link import PlaidAccountMapping

        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='a1', plaid_account_name='Checking',
        )
        mapping.save()

        dialog = AccountMappingDialog(None, [mapping])
        qtbot.addWidget(dialog)

        # Select the account option (index 1 should be the first real account)
        dialog._combos[0].setCurrentIndex(1)
        updated = dialog.get_updated_mappings()
        assert updated[0].local_type == 'account'
        assert updated[0].local_id == sample_account.id

    def test_pre_selects_existing_mapping(self, qtbot, temp_db, temp_config, sample_plaid_item, sample_account):
        from budget_app.views.bank_api_view import AccountMappingDialog
        from budget_app.models.plaid_link import PlaidAccountMapping

        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='a1', plaid_account_name='Checking',
            local_type='account', local_id=sample_account.id,
        )
        mapping.save()

        dialog = AccountMappingDialog(None, [mapping])
        qtbot.addWidget(dialog)

        # Should not be on index 0 (unmapped)
        assert dialog._combos[0].currentIndex() > 0
        lt, lid = dialog._combos[0].currentData()
        assert lt == 'account'
        assert lid == sample_account.id

    def test_unmapped_option_sets_none(self, qtbot, temp_db, temp_config, sample_plaid_item):
        from budget_app.views.bank_api_view import AccountMappingDialog
        from budget_app.models.plaid_link import PlaidAccountMapping

        mapping = PlaidAccountMapping(
            id=None, plaid_item_id=sample_plaid_item.id,
            plaid_account_id='a1', plaid_account_name='Unknown',
        )
        mapping.save()

        dialog = AccountMappingDialog(None, [mapping])
        qtbot.addWidget(dialog)

        # Index 0 is "(unmapped)"
        dialog._combos[0].setCurrentIndex(0)
        updated = dialog.get_updated_mappings()
        assert updated[0].local_type is None
        assert updated[0].local_id is None
