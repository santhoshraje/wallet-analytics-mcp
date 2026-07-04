from __future__ import annotations

import os


def _env(key: str, fallback: str | None = None) -> str | None:
    """Read from environment variable with optional fallback."""
    val = os.getenv(key)
    if val and val.strip():
        return val
    return fallback


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

# Known DEX program IDs mapped to human-readable names
DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfrLNYJzRfXWvKHh2Qdwn7NjsZ4E": "Raydium-AMM",
    "JUP6LkbZbjS1jKKwapdHNy74zcW3tLuZ55XkfGPaHaq": "Jupiter-Aggregator",
    "MEisE1DhNbaGYZgCpYzjAeF5hYoVjU8f6TbAhPiMihB": "Meteora-DLMM",
    "LBUZKhRxPFMYrbQiuS16yH15W8VBrXKu69Npa6bF7oj": "Meteora-Whirlpool",
    "TerP7ftemaffewJ4RMSuTzMU28FrY7B8EGCw3TwBNwL": "Pump-fun",
    "DjVE6JNiPYq5pQU9UoKrGBpVeFLWbXkbGEBGsQpA8hCo": "Orca",
}

# Program IDs used for transaction category detection
SPL_TOKEN_PROGRAM = "TokenkegQfeZyi1iAGBsnHNA7mJ6k3F4YK22qfjMKn"
STAKE_PROGRAM = "Ck4gqAbeysRR8j6YycZs3wEoQeAmPzJfnghgFvLbVHMT"
NFT_METADATA_PROGRAM = "metaqbxxUerdq28cj1RbAWkZQmYnpuuZqd25Q5Uze"

# Stablecoin mint addresses
STABLECOIN_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f",   # USDT (Solana)
}

# Well-known token mint → symbol mapping
TOKEN_SYMBOLS = {
    "So11111111111111111111111111111111111111112": "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f": "USDT",
}


def classify_token(mint: str) -> str:
    """Return 'stablecoin', 'base', or 'other' for a mint address."""
    if mint in STABLECOIN_MINTS:
        return "stablecoin"
    if mint in BASE_CURRENCIES:
        return "base"
    return "other"

