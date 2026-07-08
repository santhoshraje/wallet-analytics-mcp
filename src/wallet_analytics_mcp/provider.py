from __future__ import annotations

import os
from dataclasses import dataclass
from solana.rpc.async_api import AsyncClient


# Known public Solana RPC hostnames — conservative rate limits
PUBLIC_RPC_HOSTS = frozenset({
    "api.mainnet-beta.solana.com",
    "api.devnet.solana.com",
    "api.testnet.solana.com",
})


@dataclass
class RpcProfile:
    """Fetch strategy tuned to the RPC endpoint's rate limits."""
    is_public: bool
    batch_size: int       # concurrent requests per batch
    batch_delay: float    # seconds between batches
    per_req_delay: float  # seconds between sequential requests (0 = parallel)
    rate_limit_pause: float = 10.0  # seconds to sleep after first 429, then resume
    client_timeout: int = 5          # HTTP timeout per request in seconds

    @classmethod
    def from_url(cls, url: str) -> RpcProfile:
        """Auto-detect profile from RPC URL. Falls back to paid-node settings."""
        host = url.split("://", 1)[-1].split("/")[0].split(":")[0]
        if host in PUBLIC_RPC_HOSTS:
            # Public RPC: conservative pacing, short timeout to fail fast on hangs
            return cls(is_public=True, batch_size=1, batch_delay=0.5, per_req_delay=1.0,
                       rate_limit_pause=10.0, client_timeout=5)
        # Paid RPC (Helius, Quicknode, Triton, etc.): generous limits
        return cls(is_public=False, batch_size=20, batch_delay=1.0, per_req_delay=0.0,
                   client_timeout=SOLANA_RPC_TIMEOUT_DEFAULT)


def _env(key: str, default: str) -> str:
    val = os.environ.get(key, default)
    return val if val else default


def _env_int(key: str, default: int) -> int:
    raw = _env(key, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


SOLANA_RPC_TIMEOUT_DEFAULT = 30
SOLANA_RPC_URL = _env("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

_client_cache: dict[str, AsyncClient] = {}


def get_client(profile: RpcProfile | None = None) -> AsyncClient:
    """Return an AsyncClient using the configured RPC URL.

    If a profile is provided, uses its client_timeout. Otherwise falls back to env var or default.
    """
    timeout = (profile.client_timeout if profile
               else int(_env("SOLANA_RPC_TIMEOUT", str(SOLANA_RPC_TIMEOUT_DEFAULT))))
    key = f"{SOLANA_RPC_URL}:{timeout}"
    if key not in _client_cache:
        _client_cache[key] = AsyncClient(SOLANA_RPC_URL, timeout=timeout)
    return _client_cache[key]


def get_profile() -> RpcProfile:
    """Return the rate-limit profile for the configured RPC URL."""
    return RpcProfile.from_url(SOLANA_RPC_URL)


def clear_cache() -> None:
    """Reset all cached clients."""
    _client_cache.clear()
