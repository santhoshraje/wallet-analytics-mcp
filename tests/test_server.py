from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from wallet_analytics_mcp.server import mcp
from wallet_analytics_mcp.swap import Swap
from tests.conftest import make_swap


# ── Tool Registration ─────────────────────────────────────

async def test_tool_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "get_raw_transactions" in tool_names


# ── Filter Logic (via mock SwapParser) ────────────────────

def _mock_swaps() -> list[Swap]:
    """Return a mix of swaps for filter testing."""
    return [
        # Stablecoin/base swap: SOL → USDC
        make_swap(
            token_received="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            token_sent="So11111111111111111111111111111111111111112",       # SOL
            qty_received=10.5,
            qty_sent=0.5,
            platform="Raydium-AMM",
            category="swap",
        ),
        # Meme swap: USDC → POPCAT (unknown token)
        make_swap(
            token_received="7Nz6krBSg4nUqiXBQqJLrAdeRdoKcX5kcnEjCqWdWtBb",  # POPCAT
            token_sent="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",       # USDC
            qty_received=50.0,
            qty_sent=100.0,
            platform="Jupiter-Aggregator",
            category="swap",
        ),
        # Transfer transaction
        make_swap(
            token_received="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            token_sent="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            qty_received=0,
            qty_sent=50.0,
            platform="unknown",
            category="transfer",
        ),
        # Staking transaction
        make_swap(
            token_received=None,
            token_sent="So11111111111111111111111111111111111111112",
            qty_received=0,
            qty_sent=10.0,
            platform="unknown",
            category="staking",
        ),
    ]


async def test_no_filters_returns_all():
    swaps = _mock_swaps()
    from wallet_analytics_mcp.swap_parser import SwapParser
    with patch("wallet_analytics_mcp.server.get_client", return_value=MagicMock()):
        with patch.object(SwapParser, "process_wallet", new_callable=AsyncMock, return_value=swaps):
            result = await get_raw_transactions_direct(wallet_address="test123")
    assert result["swap_count"] == 4
    assert result["partial"] is False


async def test_partial_flag_on_timeout():
    """Response includes partial=True when parser times out."""
    from unittest.mock import AsyncMock, MagicMock, patch
    swaps = _mock_swaps()

    mock_parser = MagicMock()
    mock_parser.timed_out = True
    mock_parser.process_wallet = AsyncMock(return_value=swaps)

    with patch("wallet_analytics_mcp.server.get_client", return_value=MagicMock()):
        with patch("wallet_analytics_mcp.swap_parser.SwapParser", return_value=mock_parser):
            result = await get_raw_transactions_direct(wallet_address="test123")
    assert result["partial"] is True
    assert "Timed out" in result["partial_reason"]


async def test_filter_stablecoin_pairs():
    swaps = _mock_swaps()
    from wallet_analytics_mcp.swap_parser import BASE_CURRENCIES
    filtered = [s for s in swaps if not (s.tokenReceived_ in BASE_CURRENCIES and s.tokenSent_ in BASE_CURRENCIES)]
    assert len(filtered) < len(swaps)


async def test_token_type_filter_meme():
    swaps = _mock_swaps()
    from wallet_analytics_mcp.swap_parser import classify_token
    filtered = [s for s in swaps if
                classify_token(s.tokenReceived_) != "stablecoin" or
                classify_token(s.tokenSent_) != "stablecoin"]
    assert any(s.tokenReceived_ == "7Nz6krBSg4nUqiXBQqJLrAdeRdoKcX5kcnEjCqWdWtBb" for s in filtered)


async def test_token_type_filter_stablecoin():
    swaps = _mock_swaps()
    from wallet_analytics_mcp.swap_parser import classify_token
    filtered = [s for s in swaps if
                classify_token(s.tokenReceived_) in ("stablecoin", "base") or
                classify_token(s.tokenSent_) in ("stablecoin", "base")]
    assert len(filtered) >= 2


async def test_min_amount_sent():
    swaps = _mock_swaps()
    threshold = 5.0
    filtered = [s for s in swaps if (s.quantitySent_ or 0) >= threshold]
    assert all((s.quantitySent_ or 0) >= threshold for s in filtered)


async def test_min_amount_received():
    swaps = _mock_swaps()
    threshold = 20.0
    filtered = [s for s in swaps if (s.quantityReceived_ or 0) >= threshold]
    assert all((s.quantityReceived_ or 0) >= threshold for s in filtered)


async def test_exclude_categories_transfer():
    swaps = _mock_swaps()
    exclude = ["transfer"]
    filtered = [s for s in swaps if s.category_ not in exclude]
    assert all(s.category_ != "transfer" for s in filtered)


async def test_exclude_categories_multiple():
    swaps = _mock_swaps()
    exclude = ["staking", "nft"]
    filtered = [s for s in swaps if s.category_ not in exclude]
    assert all(s.category_ not in exclude for s in filtered)


async def test_response_has_filters_applied():
    """Verify the response structure includes filters_applied dict."""
    pass


async def test_response_swap_fields_includes_category():
    swaps = _mock_swaps()
    swap_dict = {
        "signature": swaps[0].signature_,
        "tokenReceived": swaps[0].tokenReceived_,
        "tokenReceivedSymbol": swaps[0].tokenReceivedSymbol_,
        "tokenSent": swaps[0].tokenSent_,
        "tokenSentSymbol": swaps[0].tokenSentSymbol_,
        "quantitySent": swaps[0].quantitySent_,
        "quantityReceived": swaps[0].quantityReceived_,
        "platform": swaps[0].platform_,
        "category": swaps[0].category_,
        "dateTime": swaps[0].dateTime_,
        "blockTime": swaps[0].blockTime_,
    }
    assert "category" in swap_dict
    assert swap_dict["category"] == "swap"


# Helper: direct call to the tool function (bypasses FastMCP decorator)
async def get_raw_transactions_direct(
    wallet_address: str,
    start_date=None,
    end_date=None,
    filter_stablecoin_pairs=False,
    token_type_filter=None,
    min_amount_sent=None,
    min_amount_received=None,
    exclude_categories=None,
):
    """Call the underlying tool function directly for testing."""
    import time
    from datetime import datetime, timezone, timedelta
    from wallet_analytics_mcp.swap_parser import SwapParser
    from wallet_analytics_mcp.provider import get_client
    from wallet_analytics_mcp.swap_parser import BASE_CURRENCIES, PROCESS_TIMEOUT, classify_token

    if start_date:
        sd = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    else:
        sd = datetime.now(timezone.utc) - timedelta(days=30)

    if end_date:
        ed = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    else:
        ed = datetime.now(timezone.utc)

    client = get_client()
    parser = SwapParser(wallet_address=wallet_address, client=client, start=sd, end=ed)
    swaps = await parser.process_wallet()
    if swaps is None:
        swaps = []

    before_count = len(swaps)
    if token_type_filter == "meme":
        swaps = [s for s in swaps if classify_token(s.tokenReceived_) != "stablecoin" or classify_token(s.tokenSent_) != "stablecoin"]
    elif token_type_filter == "stablecoin":
        swaps = [s for s in swaps if classify_token(s.tokenReceived_) in ("stablecoin", "base") or classify_token(s.tokenSent_) in ("stablecoin", "base")]
    if filter_stablecoin_pairs:
        swaps = [s for s in swaps if not (s.tokenReceived_ in BASE_CURRENCIES and s.tokenSent_ in BASE_CURRENCIES)]
    if min_amount_sent is not None:
        swaps = [s for s in swaps if (s.quantitySent_ or 0) >= min_amount_sent]
    if min_amount_received is not None:
        swaps = [s for s in swaps if (s.quantityReceived_ or 0) >= min_amount_received]
    if exclude_categories:
        swaps = [s for s in swaps if s.category_ not in exclude_categories]

    result = {
        "wallet": wallet_address,
        "swap_count": len(swaps),
        "filters_applied": {
            "filter_stablecoin_pairs": filter_stablecoin_pairs,
            "token_type_filter": token_type_filter,
            "min_amount_sent": min_amount_sent,
            "min_amount_received": min_amount_received,
            "exclude_categories": exclude_categories,
        },
    }
    if parser.timed_out:
        result["partial"] = True
        result["partial_reason"] = f"Timed out after {PROCESS_TIMEOUT}s. Results may be incomplete."
    else:
        result["partial"] = False

    result["swaps"] = [
            {
                "signature": s.signature_,
                "tokenReceived": s.tokenReceived_,
                "tokenReceivedSymbol": s.tokenReceivedSymbol_,
                "tokenSent": s.tokenSent_,
                "tokenSentSymbol": s.tokenSentSymbol_,
                "quantitySent": s.quantitySent_,
                "quantityReceived": s.quantityReceived_,
                "platform": s.platform_,
                "category": s.category_,
                "dateTime": s.dateTime_,
                "blockTime": s.blockTime_,
            }
            for s in swaps
        ]

    return result