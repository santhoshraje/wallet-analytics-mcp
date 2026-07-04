from __future__ import annotations

from solana.rpc.api import Client
from wallet_analytics_mcp.config import (
    SOLANA_PUBLIC_RPC,
    ALCHEMY_URL,
    QUICKNODE_URL,
    HELIUS_URL,
    CHAINSTACK_URL,
    DRPC_URL,
    SYNDICA_URL,
    NODE_PROVIDER,
    TIMEOUT,
)

_PROVIDER_MAP = {
    "SOLANA_PUBLIC_CLIENT": SOLANA_PUBLIC_RPC,
    "ALCHEMY_CLIENT": ALCHEMY_URL,
    "QUICKNODE_CLIENT": QUICKNODE_URL,
    "HELIUS_CLIENT": HELIUS_URL,
    "CHAINSTACK_CLIENT": CHAINSTACK_URL,
    "DRPC_CLIENT": DRPC_URL,
    "SYNDICA_CLIENT": SYNDICA_URL,
}

_client_cache: dict[str, Client] = {}


def get_client(provider: str | None = None) -> Client:
    """Return a solana.rpc.api.Client for the given provider (or NODE_PROVIDER default)."""
    key = provider or NODE_PROVIDER or "SYNDICA_CLIENT"
    if key not in _client_cache:
        url = _PROVIDER_MAP.get(key, SOLANA_PUBLIC_RPC)
        if not url:
            raise ValueError(f"Provider {key} URL not configured")
        _client_cache[key] = Client(url, timeout=TIMEOUT)
    return _client_cache[key]


def get_all_clients() -> dict[str, Client]:
    """Return a dict of provider name -> Client for every configured RPC."""
    clients: dict[str, Client] = {}
    for name, url in _PROVIDER_MAP.items():
        if url:
            clients[name] = get_client(name)
    return clients


def clear_cache() -> None:
    """Reset all cached clients."""
    _client_cache.clear()
