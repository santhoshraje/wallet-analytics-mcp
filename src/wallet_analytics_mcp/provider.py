from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from wallet_analytics_mcp.config import SOLANA_RPC_URL, TIMEOUT

_client_cache: dict[str, AsyncClient] = {}


def get_client() -> AsyncClient:
    """Return an AsyncClient using the configured RPC URL."""
    if SOLANA_RPC_URL not in _client_cache:
        _client_cache[SOLANA_RPC_URL] = AsyncClient(SOLANA_RPC_URL, timeout=TIMEOUT)
    return _client_cache[SOLANA_RPC_URL]


def clear_cache() -> None:
    """Reset all cached clients."""
    _client_cache.clear()
