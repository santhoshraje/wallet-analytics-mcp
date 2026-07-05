from __future__ import annotations

import asyncio
from wallet_analytics_mcp.swap_parser import SwapParser, _rpc_retry
from tests.conftest import (
    create_mock_client,
    RAYDIUM_SWAP_JSON,
    JUPITER_INNER_JSON,
    TRANSFER_TOKEN_JSON,
    STAKING_TX_JSON,
    NFT_MINT_JSON,
    FAILED_TX_JSON,
    METEORA_SWAP_JSON,
    UNKNOWN_PROGRAM_JSON,
)


# ── DEX Detection ─────────────────────────────────────────

def test_detect_dex_raydium_top_level():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    result = parser._detect_dex(RAYDIUM_SWAP_JSON)
    assert result == "Raydium-AMM"


def test_detect_dex_jupiter_inner():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    result = parser._detect_dex(JUPITER_INNER_JSON)
    assert result == "Jupiter-Aggregator"


def test_detect_dex_meteora():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    result = parser._detect_dex(METEORA_SWAP_JSON)
    assert result == "Meteora-DLMM"


def test_detect_dex_unknown():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    result = parser._detect_dex(UNKNOWN_PROGRAM_JSON)
    assert result == "unknown"


# ── Category Detection ────────────────────────────────────

def test_detect_category_swap():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    assert parser._detect_category(RAYDIUM_SWAP_JSON) == "swap"


def test_detect_category_transfer():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    assert parser._detect_category(TRANSFER_TOKEN_JSON) == "transfer"


def test_detect_category_staking():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    assert parser._detect_category(STAKING_TX_JSON) == "staking"


def test_detect_category_nft():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    assert parser._detect_category(NFT_MINT_JSON) == "nft"


def test_detect_category_other():
    parser = SwapParser(wallet_address="wallet111111111111111111111111111111111111111", client=create_mock_client())
    assert parser._detect_category(UNKNOWN_PROGRAM_JSON) == "other"


# ── RPC Retry ─────────────────────────────────────────────

async def test_rpc_retry_success_first_try():
    call_count = 0

    async def func():
        nonlocal call_count
        call_count += 1
        return 42

    result = await _rpc_retry(lambda: func(), max_attempts=3)
    assert result == 42
    assert call_count == 1


async def test_rpc_retry_succeeds_after_failures():
    call_count = 0

    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("timeout")
        return "ok"

    result = await _rpc_retry(lambda: func(), max_attempts=5)
    assert result == "ok"
    assert call_count == 3


async def test_rpc_retry_exhausted_raises():
    async def func():
        raise ValueError("always fails")

    try:
        await _rpc_retry(lambda: func(), max_attempts=2)
        assert False, "Should have raised"
    except ValueError as e:
        assert str(e) == "always fails"


# ── Transaction Processing ───────────────────────────────

def test_process_simple_swap():
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(RAYDIUM_SWAP_JSON)
    assert swap is not None
    assert swap.tokenSent_ == "So11111111111111111111111111111111111111112"  # SOL sent
    assert swap.tokenReceived_ == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK received
    assert swap.quantitySent_ == 0.5
    assert swap.quantityReceived_ == 1000.0


def test_process_failed_transaction():
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(FAILED_TX_JSON)
    assert swap is None


# ── Multi-hop Swap ───────────────────────────────────────

def test_process_multi_hop_swap():
    """Swap with 2 tokens received, 1 sent (multi-hop via Jupiter)."""
    multi_hop_json = {
        "transaction": {
            "signatures": ["sig-multi-001"],
            "message": {
                "accountKeys": [
                    "wallet111111111111111111111111111111111111111",
                    "JUP4Fb2cqiRUcaDJR5K1odmyNsBgyX76sgDLpRR1QR5",
                ],
                "instructions": [{"programIdIndex": 1}],
            },
        },
        "meta": {
            "err": None,
            "preTokenBalances": [
                {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 100.0}},
                {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0}},
                {"mint": "7Nz6krBSg4nUqiXBQqJLrAdeRdoKcX5kcnEjCqWdWtBb", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0}},
            ],
            "postTokenBalances": [
                {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 90.0}},
                {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 500.0}},
                {"mint": "7Nz6krBSg4nUqiXBQqJLrAdeRdoKcX5kcnEjCqWdWtBb", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 200.0}},
            ],
            "preBalances": [5000000000, 0],
            "postBalances": [5000000000, 0],
            "innerInstructions": [],
        },
        "blockTime": 1717000800,
    }
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(multi_hop_json)
    assert swap is not None
    # Sent: USDC (10.0 dropped), Received: BONK(500) + POPCAT(200) → max=BONK, sum=700
    assert swap.tokenSent_ == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert swap.quantitySent_ == 10.0
    assert swap.quantityReceived_ == 700.0


# ── SOL-only Swaps (lamport diff) ────────────────────────

def test_process_sol_received_swap():
    """Token sent, SOL received via lamport balance increase."""
    sol_recv_json = {
        "transaction": {
            "signatures": ["sig-solrecv-001"],
            "message": {
                "accountKeys": [
                    "wallet111111111111111111111111111111111111111",
                    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                ],
                "instructions": [{"programIdIndex": 1}],
            },
        },
        "meta": {
            "err": None,
            "preTokenBalances": [
                {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 50.0}},
            ],
            "postTokenBalances": [
                {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 40.0}},
            ],
            "preBalances": [2000000000, 0],
            "postBalances": [3500000000, 0],  # +1.5 SOL
            "innerInstructions": [],
        },
        "blockTime": 1717000900,
    }
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(sol_recv_json)
    assert swap is not None
    assert swap.tokenSent_ == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert swap.quantitySent_ == 10.0
    assert swap.tokenReceived_ == "So11111111111111111111111111111111111111112"
    assert swap.quantityReceived_ == 1.5


def test_process_sol_sent_swap():
    """SOL sent via lamport decrease, token received."""
    sol_send_json = {
        "transaction": {
            "signatures": ["sig-solsend-001"],
            "message": {
                "accountKeys": [
                    "wallet111111111111111111111111111111111111111",
                    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                ],
                "instructions": [{"programIdIndex": 1}],
            },
        },
        "meta": {
            "err": None,
            "preTokenBalances": [
                {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0}},
            ],
            "postTokenBalances": [
                {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 500.0}},
            ],
            "preBalances": [4000000000, 0],
            "postBalances": [2500000000, 0],  # -1.5 SOL
            "innerInstructions": [],
        },
        "blockTime": 1717001000,
    }
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(sol_send_json)
    assert swap is not None
    assert swap.tokenReceived_ == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    assert swap.quantityReceived_ == 500.0
    assert swap.tokenSent_ == "So11111111111111111111111111111111111111112"
    assert swap.quantitySent_ == 1.5


# ── Edge Cases ───────────────────────────────────────────

def test_process_no_token_balances():
    """Transaction with no token balances should return None."""
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(STAKING_TX_JSON)
    assert swap is None


def test_process_owner_mismatch():
    """Token balances belonging to a different owner are skipped."""
    mismatch_json = {
        "transaction": {
            "signatures": ["sig-mismatch-001"],
            "message": {
                "accountKeys": [
                    "wallet111111111111111111111111111111111111111",
                    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                ],
                "instructions": [{"programIdIndex": 1}],
            },
        },
        "meta": {
            "err": None,
            "preTokenBalances": [
                {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "other_wallet_address", "uiTokenAmount": {"uiAmount": 100.0}},
            ],
            "postTokenBalances": [
                {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "other_wallet_address", "uiTokenAmount": {"uiAmount": 90.0}},
            ],
            "preBalances": [5000000000, 0],
            "postBalances": [5000000000, 0],
            "innerInstructions": [],
        },
        "blockTime": 1717001100,
    }
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(mismatch_json)
    # Both pre and post dicts empty → no tokens to classify → swap has None fields
    assert swap is not None  # reaches SOL lamport check but diff=0


def test_process_receive_only():
    """Transaction where wallet only receives a token (no send)."""
    recv_only_json = {
        "transaction": {
            "signatures": ["sig-recvonly-001"],
            "message": {
                "accountKeys": [
                    "wallet111111111111111111111111111111111111111",
                    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                ],
                "instructions": [{"programIdIndex": 1}],
            },
        },
        "meta": {
            "err": None,
            "preTokenBalances": [
                {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0}},
            ],
            "postTokenBalances": [
                {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 100.0}},
            ],
            "preBalances": [3000000000, 0],
            "postBalances": [2500000000, 0],  # -0.5 SOL
            "innerInstructions": [],
        },
        "blockTime": 1717001200,
    }
    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=create_mock_client(),
    )
    swap = parser._process_transaction_details(recv_only_json)
    assert swap is not None
    assert swap.tokenReceived_ == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    assert swap.quantityReceived_ == 100.0
    assert swap.tokenSent_ == "So11111111111111111111111111111111111111112"
    assert swap.quantitySent_ == 0.5


# ── Async process_wallet (mocked RPC) ────────────────────

async def test_process_wallet_full_flow():
    """End-to-end process_wallet with mocked RPC responses."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_client = create_mock_client()

    sig_obj = MagicMock()
    sig_obj.signature = "sig-raydium-001"
    sig_obj.block_time = int(now.timestamp())
    result_obj = MagicMock()
    result_obj.value = [sig_obj]
    # First call returns 1 sig, second call returns empty (pagination terminates)
    empty_result = MagicMock()
    empty_result.value = []
    mock_client.get_signatures_for_address = AsyncMock(side_effect=[result_obj, empty_result])

    tx_wrapper = MagicMock()
    tx_wrapper.to_json.return_value = __import__('json').dumps(RAYDIUM_SWAP_JSON)
    tx_result = MagicMock()
    tx_result.value = tx_wrapper
    mock_client.get_transaction = AsyncMock(return_value=tx_result)

    with patch("wallet_analytics_mcp.swap_parser.Pubkey"):
        parser = SwapParser(
            wallet_address="wallet111111111111111111111111111111111111111",
            client=mock_client,
            start=now.replace(day=1),
            end=now,
        )
        swaps = await parser.process_wallet()

        assert swaps is not None
        assert len(swaps) == 1
        assert swaps[0].platform_ == "Raydium-AMM"


async def test_process_wallet_empty_signatures():
    """process_wallet returns empty list when RPC returns no signatures."""
    from unittest.mock import AsyncMock, MagicMock

    mock_client = create_mock_client()
    result_obj = MagicMock()
    result_obj.value = []
    mock_client.get_signatures_for_address = AsyncMock(return_value=result_obj)

    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=mock_client,
    )
    swaps = await parser.process_wallet()
    assert swaps == []


async def test_process_wallet_rpc_error():
    """process_wallet handles RPC errors gracefully."""
    from unittest.mock import AsyncMock

    mock_client = create_mock_client()
    mock_client.get_signatures_for_address = AsyncMock(side_effect=ConnectionError("rpc down"))

    parser = SwapParser(
        wallet_address="wallet111111111111111111111111111111111111111",
        client=mock_client,
    )
    swaps = await parser.process_wallet()
    assert swaps == []


# ── rpc_retry with sync return ───────────────────────────

async def test_rpc_retry_sync_return():
    """_rpc_retry handles a function that returns a plain value (not a coroutine)."""
    result = await _rpc_retry(lambda: "sync_value", max_attempts=1)
    assert result == "sync_value"