from __future__ import annotations

import json


def load_fixture(name: str) -> dict:
    """Load a JSON fixture from tests/fixtures/."""
    import pathlib
    path = pathlib.Path(__file__).parent / "fixtures" / name
    return json.loads(path.read_text())


# ── Mock Solana Client ─────────────────────────────────────

from unittest.mock import MagicMock
from solana.rpc.async_api import AsyncClient


def create_mock_client():
    """Return a mock solana.rpc.async_api.AsyncClient."""
    return MagicMock(spec=AsyncClient)


# ── Sample Swap Factory ────────────────────────────────────

from wallet_analytics_mcp.swap import Swap


def make_swap(
    token_received: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    token_sent: str = "So11111111111111111111111111111111111111112",
    qty_received: float = 10.5,
    qty_sent: float = 0.5,
    platform: str = "Raydium-AMM",
    category: str = "swap",
) -> Swap:
    s = Swap()
    s.signature_ = "test-sig-123"
    s.tokenReceived_ = token_received
    s.tokenSent_ = token_sent
    s.quantityReceived_ = qty_received
    s.quantitySent_ = qty_sent
    s.platform_ = platform
    s.category_ = category
    return s


# ── Fixture JSONs (inline for test speed) ─────────────────

RAYDIUM_SWAP_JSON = {
    "transaction": {
        "signatures": ["sig-raydium-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "675kPX9MHTjS2zt1qfrLNYJzRfXWvKHh2Qdwn7NjsZ4E",
            ],
            "instructions": [
                {"programIdIndex": 1},
            ],
        },
    },
    "meta": {
        "err": None,
        "preTokenBalances": [
            {"mint": "So11111111111111111111111111111111111111112", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 5.0}},
            {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0}},
        ],
        "postTokenBalances": [
            {"mint": "So11111111111111111111111111111111111111112", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 4.5}},
            {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 1000}},
        ],
        "preBalances": [5000000000, 0],
        "postBalances": [4500000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000000,
}

JUPITER_INNER_JSON = {
    "transaction": {
        "signatures": ["sig-jupiter-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "some_program",
            ],
            "instructions": [
                {"programIdIndex": 1},
            ],
        },
    },
    "meta": {
        "err": None,
        "preTokenBalances": [
            {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 100.0}},
            {"mint": "7Nz6krBSg4nUqiXBQqJLrAdeRdoKcX5kcnEjCqWdWtBb", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0}},
        ],
        "postTokenBalances": [
            {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 90.0}},
            {"mint": "7Nz6krBSg4nUqiXBQqJLrAdeRdoKcX5kcnEjCqWdWtBb", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 50.0}},
        ],
        "preBalances": [2000000000, 0],
        "postBalances": [2000000000, 0],
        "innerInstructions": [
            {
                "index": 0,
                "instructions": [
                    {"programIdIndex": 1},
                ],
            },
        ],
    },
    "blockTime": 1717000100,
}

# Override inner instruction to point to Jupiter program
JUPITER_INNER_JSON["transaction"]["message"]["accountKeys"].append("JUP6LkbZbjS1jKKwapdHNy74zcW3tLuZ55XkfGPaHaq")
JUPITER_INNER_JSON["meta"]["innerInstructions"][0]["instructions"][0]["programIdIndex"] = 2

TRANSFER_TOKEN_JSON = {
    "transaction": {
        "signatures": ["sig-transfer-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "TokenkegQfeZyi1iAGBsnHNA7mJ6k3F4YK22qfjMKn",
            ],
            "instructions": [
                {"programIdIndex": 1},
            ],
        },
    },
    "meta": {
        "err": None,
        "preTokenBalances": [
            {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 200.0}},
        ],
        "postTokenBalances": [
            {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "owner": "wallet111111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 150.0}},
        ],
        "preBalances": [2000000000, 0],
        "postBalances": [2000000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000200,
}

STAKING_TX_JSON = {
    "transaction": {
        "signatures": ["sig-stake-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "Ck4gqAbeysRR8j6YycZs3wEoQeAmPzJfnghgFvLbVHMT",
            ],
            "instructions": [
                {"programIdIndex": 1},
            ],
        },
    },
    "meta": {
        "err": None,
        "preTokenBalances": [],
        "postTokenBalances": [],
        "preBalances": [5000000000, 0],
        "postBalances": [4000000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000300,
}

NFT_MINT_JSON = {
    "transaction": {
        "signatures": ["sig-nft-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "metaqbxxUerdq28cj1RbAWkZQmYnpuuZqd25Q5Uze",
            ],
            "instructions": [
                {"programIdIndex": 1},
            ],
        },
    },
    "meta": {
        "err": None,
        "preTokenBalances": [],
        "postTokenBalances": [],
        "preBalances": [5000000000, 0],
        "postBalances": [4900000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000400,
}

FAILED_TX_JSON = {
    "transaction": {
        "signatures": ["sig-failed-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "675kPX9MHTjS2zt1qfrLNYJzRfXWvKHh2Qdwn7NjsZ4E",
            ],
            "instructions": [{"programIdIndex": 1}],
        },
    },
    "meta": {
        "err": {"InstructionError": [0, "Custom"]},
        "preTokenBalances": [],
        "postTokenBalances": [],
        "preBalances": [5000000000, 0],
        "postBalances": [5000000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000500,
}

METEORA_SWAP_JSON = {
    "transaction": {
        "signatures": ["sig-meteora-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "MEisE1DhNbaGYZgCpYzjAeF5hYoVjU8f6TbAhPiMihB",
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
        "preBalances": [3000000000, 0],
        "postBalances": [2500000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000600,
}

UNKNOWN_PROGRAM_JSON = {
    "transaction": {
        "signatures": ["sig-unknown-001"],
        "message": {
            "accountKeys": [
                "wallet111111111111111111111111111111111111111",
                "SomeUnknownProgram1111111111111111111111111111",
            ],
            "instructions": [{"programIdIndex": 1}],
        },
    },
    "meta": {
        "err": None,
        "preTokenBalances": [],
        "postTokenBalances": [],
        "preBalances": [5000000000, 0],
        "postBalances": [4900000000, 0],
        "innerInstructions": [],
    },
    "blockTime": 1717000700,
}
