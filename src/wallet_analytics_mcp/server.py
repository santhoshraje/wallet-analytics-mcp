from __future__ import annotations

import os
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

import wallet_analytics_mcp

LOG_DIR = os.path.join(os.path.dirname(wallet_analytics_mcp.__file__), "..", "log")
LOG_FILE = os.path.join(LOG_DIR, "mcp_server.log")
os.makedirs(LOG_DIR, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
root_logger.addHandler(handler)

logger = logging.getLogger("wallet-analytics-mcp")

from mcp.server.fastmcp import FastMCP
from wallet_analytics_mcp.swap_parser import SwapParser
from wallet_analytics_mcp.provider import get_client, clear_cache
from wallet_analytics_mcp.config import BASE_CURRENCIES, STABLECOIN_MINTS, classify_token


@asynccontextmanager
async def lifespan(server):
    logger.info("Server starting")
    yield
    clear_cache()
    logger.info("Server shutting down, RPC cache cleared")


mcp = FastMCP(
    "wallet-analytics-mcp",
    instructions="Analyze on-chain wallets for copy-trading decisions",
    lifespan=lifespan,
)


@mcp.tool()
async def get_raw_transactions(
    wallet_address: str,
    start_date: str | None = None,
    end_date: str | None = None,
    filter_stablecoin_pairs: bool = False,
    token_type_filter: str | None = None,
    min_amount_sent: float | None = None,
    min_amount_received: float | None = None,
    exclude_categories: list[str] | None = None,
):
    """Fetch raw swap transactions for a Solana wallet address.

    Returns all detected swaps by default. Use optional filters to narrow results.

    Args:
        wallet_address: Solana wallet public key (base58).
        start_date: ISO 8601 date string (default: 30 days ago).
        end_date: ISO 8601 date string (default: now).
        filter_stablecoin_pairs: Drop swaps where both tokens are base currencies (SOL/USDC).
        token_type_filter: Filter by token category. "meme" keeps swaps where at least one token is not a stablecoin/base. "stablecoin" keeps only swaps involving a stablecoin or base currency. Default (None) returns all swaps.
        min_amount_sent: Minimum token quantity sent to include the swap.
        min_amount_received: Minimum token quantity received to include the swap.
        exclude_categories: List of categories to exclude. Valid values: "transfer", "staking", "nft", "other". Default (None) returns all categories.
    """
    t0 = time.time()
    logger.info("=== get_raw_transactions START ===")
    logger.info("wallet=%s, start=%s, end=%s", wallet_address, start_date, end_date)
    logger.info("filters: stablecoin_pairs=%s, token_type=%s, min_sent=%s, min_received=%s, exclude_cats=%s", filter_stablecoin_pairs, token_type_filter, min_amount_sent, min_amount_received, exclude_categories)

    if start_date:
        sd = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    else:
        sd = datetime.now(timezone.utc) - timedelta(days=30)

    if end_date:
        ed = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    else:
        ed = datetime.now(timezone.utc)

    logger.info("date range: %s to %s", sd, ed)

    t_client = time.time()
    client = get_client()
    logger.info("get_client done in %.2fs", time.time() - t_client)

    parser = SwapParser(
        wallet_address=wallet_address,
        client=client,
        start=sd,
        end=ed,
    )

    t_process = time.time()
    swaps = await parser.process_wallet()
    if swaps is None:
        swaps = []
    logger.info("process_wallet done in %.2fs, %d raw swaps", time.time() - t_process, len(swaps))

    # Apply optional filters
    before_count = len(swaps)
    if token_type_filter == "meme":
        swaps = [s for s in swaps if
                 classify_token(s.tokenReceived_) != "stablecoin" or
                 classify_token(s.tokenSent_) != "stablecoin"]
    elif token_type_filter == "stablecoin":
        swaps = [s for s in swaps if
                 classify_token(s.tokenReceived_) in ("stablecoin", "base") or
                 classify_token(s.tokenSent_) in ("stablecoin", "base")]
    if filter_stablecoin_pairs:
        swaps = [s for s in swaps if not (s.tokenReceived_ in BASE_CURRENCIES and s.tokenSent_ in BASE_CURRENCIES)]
    if min_amount_sent is not None:
        swaps = [s for s in swaps if (s.quantitySent_ or 0) >= min_amount_sent]
    if min_amount_received is not None:
        swaps = [s for s in swaps if (s.quantityReceived_ or 0) >= min_amount_received]
    if exclude_categories:
        swaps = [s for s in swaps if s.category_ not in exclude_categories]
    if before_count > len(swaps):
        logger.info("filters applied: %d -> %d swaps", before_count, len(swaps))

    elapsed = time.time() - t0
    logger.info("get_raw_transactions done: %d swaps, total %.1fs", len(swaps), elapsed)
    logger.info("=== get_raw_transactions END ===")

    return {
        "wallet": wallet_address,
        "swap_count": len(swaps),
        "filters_applied": {
            "filter_stablecoin_pairs": filter_stablecoin_pairs,
            "token_type_filter": token_type_filter,
            "min_amount_sent": min_amount_sent,
            "min_amount_received": min_amount_received,
            "exclude_categories": exclude_categories,
        },
        "swaps": [
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
        ],
    }