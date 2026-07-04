from __future__ import annotations

from solana.rpc.api import Client
from wallet_analytics_mcp.config import SOLANA_RPC_URL, TIMEOUT

_client_cache: dict[str, Client] = {}


def get_client() -> Client:
    """Return a solana.rpc.api.Client using the configured RPC URL."""
    if SOLANA_RPC_URL not in _client_cache:
        _client_cache[SOLANA_RPC_URL] = Client(SOLANA_RPC_URL, timeout=TIMEOUT)
    return _client_cache[SOLANA_RPC_URL]


def clear_cache() -> None:
    """Reset all cached clients."""
    _client_cache.clear()
