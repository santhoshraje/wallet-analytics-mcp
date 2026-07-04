from __future__ import annotations

import os


def _env(key: str, fallback: str | None = None) -> str | None:
    """Read from environment variable with optional fallback."""
    return os.getenv(key, fallback)


def _env_int(key: str, fallback: int) -> int:
    """Read integer from environment variable with fallback."""
    val = os.getenv(key)
    if val:
        return int(val)
    return fallback


TIMEOUT = _env_int("SOLANA_RPC_TIMEOUT", 30)
TRANSACTION_LIMIT = _env_int("SOLANA_TX_LIMIT", 30000)

# RPC provider URLs (set via env vars)
SOLANA_PUBLIC_RPC = _env("SOLANA_PUBLIC_RPC", "https://api.mainnet-beta.solana.com")
ALCHEMY_URL = _env("ALCHEMY_URL")
QUICKNODE_URL = _env("QUICKNODE_URL")
HELIUS_URL = _env("HELIUS_URL")
CHAINSTACK_URL = _env("CHAINSTACK_URL")
DRPC_URL = _env("DRPC_URL")
SYNDICA_URL = _env("SYNDICA_URL")

# Active provider: SOLANA_PUBLIC_CLIENT, ALCHEMY_CLIENT, QUICKNODE_CLIENT, HELIUS_CLIENT, CHAINSTACK_CLIENT, DRPC_CLIENT, SYNDICA_CLIENT
NODE_PROVIDER = _env("SOLANA_RPC_PROVIDER", "ALCHEMY_CLIENT")
