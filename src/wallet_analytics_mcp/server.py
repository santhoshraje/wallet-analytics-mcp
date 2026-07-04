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
def get_raw_transactions(
    wallet_address: str,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Fetch raw swap transactions for a Solana wallet address.

    Args:
        wallet_address: Solana wallet public key (base58).
        start_date: ISO 8601 date string (default: 30 days ago).
        end_date: ISO 8601 date string (default: now).
    """
    t0 = time.time()
    logger.info("=== get_raw_transactions START ===")
    logger.info("wallet=%s, start=%s, end=%s", wallet_address, start_date, end_date)

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
    swaps = parser.process_wallet()
    if swaps is None:
        swaps = []
    logger.info("process_wallet done in %.2fs", time.time() - t_process)

    elapsed = time.time() - t0
    logger.info("get_raw_transactions done: %d swaps, total %.1fs", len(swaps), elapsed)
    logger.info("=== get_raw_transactions END ===")

    return {
        "wallet": wallet_address,
        "swap_count": len(swaps),
        "swaps": [
            {
                "signature": s.signature_,
                "tokenReceived": s.tokenReceived_,
                "tokenSent": s.tokenSent_,
                "quantitySent": s.quantitySent_,
                "quantityReceived": s.quantityReceived_,
                "dateTime": s.dateTime_,
                "blockTime": s.blockTime_,
            }
            for s in swaps
        ],
    }
