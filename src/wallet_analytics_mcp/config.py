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

# RPC endpoint (set via env var, any provider URL)
SOLANA_RPC_URL = _env("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# Base currencies for optional filtering
BASE_CURRENCIES = {
    "So11111111111111111111111111111111111111112",  # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
}

