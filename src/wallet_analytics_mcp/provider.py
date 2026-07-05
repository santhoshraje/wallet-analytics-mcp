from __future__ import annotations

import os
from solana.rpc.async_api import AsyncClient


def _env(key: str, default: str) -> str:
    val = os.environ.get(key, default)
    return val if val else default


def _env_int(key: str, default: int) -> int:
    raw = _env(key, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


SOLANA_RPC_URL = _env("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
TIMEOUT = _env_int("SOLANA_RPC_TIMEOUT", 30)

_client_cache: dict[str, AsyncClient] = {}


def get_client() -> AsyncClient:
    """Return an AsyncClient using the configured RPC URL."""
    if SOLANA_RPC_URL not in _client_cache:
        _client_cache[SOLANA_RPC_URL] = AsyncClient(SOLANA_RPC_URL, timeout=TIMEOUT)
    return _client_cache[SOLANA_RPC_URL]


def clear_cache() -> None:
    """Reset all cached clients."""
    _client_cache.clear()
