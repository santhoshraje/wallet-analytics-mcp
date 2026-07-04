from __future__ import annotations

import os
from wallet_analytics_mcp.config import (
    classify_token,
    _env_int,
    _env,
    BASE_CURRENCIES,
    DEX_PROGRAMS,
    STABLECOIN_MINTS,
)

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL = "So11111111111111111111111111111111111111112"


def test_classify_token_stablecoin():
    assert classify_token(USDC) == "stablecoin"
    usdt = "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f"
    assert classify_token(usdt) == "stablecoin"


def test_classify_token_base():
    assert classify_token(SOL) == "base"


def test_classify_token_other():
    unknown = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    assert classify_token(unknown) == "other"


def test_env_int_default():
    os.environ.pop("TEST_NONEXISTENT_VAR", None)
    assert _env_int("TEST_NONEXISTENT_VAR", 42) == 42


def test_env_string_default():
    os.environ.pop("TEST_NONEXISTENT_VAR_2", None)
    assert _env("TEST_NONEXISTENT_VAR_2", "fallback") == "fallback"


def test_constants_non_empty():
    assert len(BASE_CURRENCIES) >= 2
    assert len(DEX_PROGRAMS) >= 6
    assert len(STABLECOIN_MINTS) >= 2
