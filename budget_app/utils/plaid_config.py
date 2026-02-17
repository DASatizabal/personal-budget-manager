"""Plaid API configuration manager — stores credentials in a JSON file."""

import json
import logging
from pathlib import Path
from typing import Optional

_logger = logging.getLogger('budget_app.plaid_config')

CONFIG_PATH = Path(__file__).parent.parent.parent / "plaid_config.json"

_DEFAULT_CONFIG = {
    "client_id": "",
    "secret": "",
    "environment": "sandbox",
}


def load_config() -> dict:
    """Load Plaid config from JSON file, returning defaults if missing."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
            # Merge with defaults so new keys are always present
            merged = {**_DEFAULT_CONFIG, **data}
            return merged
        except (json.JSONDecodeError, OSError) as e:
            _logger.warning("Failed to read plaid config: %s", e)
    return dict(_DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Save Plaid config to JSON file."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    _logger.info("Plaid config saved to %s", CONFIG_PATH)


def is_configured() -> bool:
    """Return True if client_id and secret are both non-empty."""
    cfg = load_config()
    return bool(cfg.get("client_id")) and bool(cfg.get("secret"))


def get_environment_host(environment: Optional[str] = None) -> str:
    """Map environment name to Plaid API host string.

    Returns the host string expected by plaid-python's Configuration.
    """
    env = (environment or load_config().get("environment", "sandbox")).lower()
    hosts = {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }
    return hosts.get(env, hosts["sandbox"])
