"""Plaid API client wrapper — thin layer over plaid-python SDK."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from . import plaid_config

_logger = logging.getLogger('budget_app.plaid_client')


class PlaidClientError(Exception):
    """Raised when a Plaid API call fails."""


@dataclass
class PlaidAccountBalance:
    account_id: str
    name: str
    official_name: Optional[str]
    type: str          # depository, credit, loan, investment, other
    subtype: str       # checking, savings, credit card, mortgage, etc.
    mask: Optional[str]
    current: float
    available: Optional[float]
    limit: Optional[float]


@dataclass
class PlaidTransaction:
    transaction_id: str
    account_id: str
    date: str
    name: str
    amount: float       # positive = debit (money out), negative = credit (money in)
    category: Optional[str]
    pending: bool


@dataclass
class PlaidSyncResult:
    added: List[PlaidTransaction] = field(default_factory=list)
    modified: List[PlaidTransaction] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    next_cursor: str = ""
    has_more: bool = False


def _get_client() -> plaid_api.PlaidApi:
    """Build a PlaidApi client from saved config."""
    cfg = plaid_config.load_config()
    if not cfg.get("client_id") or not cfg.get("secret"):
        raise PlaidClientError("Plaid credentials not configured.")

    host = plaid_config.get_environment_host(cfg.get("environment"))
    configuration = plaid.Configuration(
        host=host,
        api_key={
            "clientId": cfg["client_id"],
            "secret": cfg["secret"],
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def create_link_token() -> str:
    """Create a Plaid Link token for the browser-based auth flow."""
    client = _get_client()
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id="budget-app-user"),
        client_name="Personal Budget Manager",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    try:
        response = client.link_token_create(request)
        return response.link_token
    except plaid.ApiException as e:
        _logger.error("link_token_create failed: %s", e)
        raise PlaidClientError(f"Failed to create link token: {e}") from e


def exchange_public_token(public_token: str) -> tuple:
    """Exchange a public token for an access_token + item_id."""
    client = _get_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    try:
        response = client.item_public_token_exchange(request)
        return response.access_token, response.item_id
    except plaid.ApiException as e:
        _logger.error("public_token_exchange failed: %s", e)
        raise PlaidClientError(f"Token exchange failed: {e}") from e


def get_balances(access_token: str) -> List[PlaidAccountBalance]:
    """Fetch current balances for all accounts under this access_token."""
    client = _get_client()
    request = AccountsBalanceGetRequest(access_token=access_token)
    try:
        response = client.accounts_balance_get(request)
    except plaid.ApiException as e:
        _logger.error("accounts_balance_get failed: %s", e)
        raise PlaidClientError(f"Balance fetch failed: {e}") from e

    results = []
    for acct in response.accounts:
        bal = acct.balances
        results.append(PlaidAccountBalance(
            account_id=acct.account_id,
            name=acct.name,
            official_name=getattr(acct, 'official_name', None),
            type=str(acct.type),
            subtype=str(acct.subtype) if acct.subtype else "",
            mask=getattr(acct, 'mask', None),
            current=float(bal.current) if bal.current is not None else 0.0,
            available=float(bal.available) if bal.available is not None else None,
            limit=float(bal.limit) if getattr(bal, 'limit', None) is not None else None,
        ))
    return results


def sync_transactions(access_token: str, cursor: Optional[str] = None) -> PlaidSyncResult:
    """Incremental transaction sync. Returns new/modified/removed transactions."""
    client = _get_client()
    kwargs = {"access_token": access_token}
    if cursor:
        kwargs["cursor"] = cursor

    request = TransactionsSyncRequest(**kwargs)
    try:
        response = client.transactions_sync(request)
    except plaid.ApiException as e:
        _logger.error("transactions_sync failed: %s", e)
        raise PlaidClientError(f"Transaction sync failed: {e}") from e

    def _to_txn(t) -> PlaidTransaction:
        cat = None
        if hasattr(t, 'category') and t.category:
            cat = " > ".join(t.category)
        return PlaidTransaction(
            transaction_id=t.transaction_id,
            account_id=t.account_id,
            date=str(t.date),
            name=t.name,
            amount=float(t.amount),
            category=cat,
            pending=bool(t.pending),
        )

    return PlaidSyncResult(
        added=[_to_txn(t) for t in response.added],
        modified=[_to_txn(t) for t in response.modified],
        removed=[t.transaction_id for t in response.removed],
        next_cursor=response.next_cursor,
        has_more=response.has_more,
    )
