from __future__ import annotations

import os
import json
import time
import asyncio
from solders.pubkey import Pubkey
from solders.signature import Signature
from datetime import datetime, timezone
import logging
from wallet_analytics_mcp.swap import Swap
from wallet_analytics_mcp.provider import get_profile


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, str(default)) or str(default)
    try:
        return int(raw)
    except ValueError:
        return default


TRANSACTION_LIMIT = _env_int("SOLANA_TX_LIMIT", 500)
PROCESS_TIMEOUT = _env_int("SOLANA_PROCESS_TIMEOUT", 120)

sol_address = "So11111111111111111111111111111111111111112"
usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

BASE_CURRENCIES = {
    sol_address,
    usdc_address,
}

DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium-AMM",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter-Aggregator",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "Jupiter-Aggregator",
    "LBUZKhRxPFcijG9VGsrFkSjjeXAEqEFMvAHLHFGxLQf": "Meteora-DLMM",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "Pump-fun",
    "AMM55ShdkoHEeFEvKNEZEJpAvQAQbSHYY9HiZwuqvk2": "Raydium-CLMM",
    "OrcsQ6wkGjsL3hJMshW2aBchTVDafUhmXjaobCZmjqj": "Orca",
}

SPL_TOKEN_PROGRAM = "TokenkegQfeZyi1iAGBsnHNA7mJ6k3F4YK22qfjMKn"
STAKE_PROGRAM = "Ck4gqAbeysRR8j6YycZs3wEoQeAmPzJfnghgFvLbVHMT"
NFT_METADATA_PROGRAM = "metaqbxxUerdq28cj1RbAWkZQmYnpuuZqd25Q5Uze"

STABLECOIN_MINTS = {
    usdc_address,
    "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f",  # USDT
}

TOKEN_SYMBOLS = {
    sol_address: "SOL",
    usdc_address: "USDC",
    "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f": "USDT",
}


def classify_token(mint: str) -> str:
    if mint in STABLECOIN_MINTS:
        return "stablecoin"
    if mint in BASE_CURRENCIES:
        return "base"
    return "other"


async def _rpc_retry(func, max_attempts: int = 3, logger=None) -> tuple:
    """Retry async RPC call with exponential backoff.

    Returns (result, was_rate_limited). Rate-limited errors get flat 5s delay.
    Other errors use standard backoff (1s → 2s). Non-retryable errors (ValueError,
    TypeError) fail immediately without backoff.
    """
    last_exception = None
    was_rate_limited = False
    for attempt in range(max_attempts):
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result, was_rate_limited
            return result, was_rate_limited
        except (ValueError, TypeError) as e:
            # Non-retryable — bad input, not a transient RPC error
            if logger:
                logger.error(f"[RPC Retry] Non-retryable error: {type(e).__name__}: {repr(e)}")
            raise
        except Exception as e:
            last_exception = e
            err_str = f"{type(e).__name__}: {repr(e)}"
            is_rl = "HTTPStatusError" in err_str
            if is_rl:
                was_rate_limited = True
            if logger:
                logger.warning(f"[RPC Retry] Attempt {attempt + 1}/{max_attempts} failed: {err_str}")
            if attempt < max_attempts - 1:
                wait = 5.0 if is_rl else (2 ** attempt)
                await asyncio.sleep(wait)
    raise last_exception


class SwapParser:
    def __init__(
        self,
        wallet_address: str = "",
        client=None,
        start: datetime | None = None,
        end: datetime | None = None,
        profile=None,
    ) -> None:
        self.wallet_address = wallet_address
        self.signatures = []
        self.solana_client = client
        self.processed_transactions: list[Swap] = []
        self.failed_signatures: list[str] = []
        self.logger = logging.getLogger(__name__)
        self.tx_logger = logging.getLogger("wallet_analytics_mcp.tx_debug")
        self.start_date = start
        self.end_date = end
        self.profile = profile or get_profile()
        self.timed_out = False

    def _detect_dex(self, json_data: dict) -> str | None:
        """Find which DEX program was called in this transaction."""
        account_keys = json_data["transaction"]["message"]["accountKeys"]
        instructions = json_data["transaction"]["message"].get("instructions", [])
        for ix in instructions:
            prog_idx = ix.get("programIdIndex")
            if prog_idx is not None and prog_idx < len(account_keys):
                prog_id = account_keys[prog_idx]
                if prog_id in DEX_PROGRAMS:
                    return DEX_PROGRAMS[prog_id]
        inner = json_data["meta"].get("innerInstructions", [])
        for group in inner:
            for ix in group.get("instructions", []):
                prog_idx = ix.get("programIdIndex")
                if prog_idx is not None and prog_idx < len(account_keys):
                    prog_id = account_keys[prog_idx]
                    if prog_id in DEX_PROGRAMS:
                        return DEX_PROGRAMS[prog_id]
        return "unknown"

    def _detect_category(self, json_data: dict) -> str:
        """Classify transaction as 'swap', 'transfer', 'staking', 'nft', or 'other'."""
        account_keys = json_data["transaction"]["message"]["accountKeys"]
        instructions = json_data["transaction"]["message"].get("instructions", [])
        programs_called = set()
        for ix in instructions:
            prog_idx = ix.get("programIdIndex")
            if prog_idx is not None and prog_idx < len(account_keys):
                programs_called.add(account_keys[prog_idx])

        # If only token program called, likely a plain transfer
        if programs_called == {SPL_TOKEN_PROGRAM}:
            return "transfer"

        # Check for staking program
        if STAKE_PROGRAM in programs_called:
            return "staking"

        # Check for NFT metadata program
        if NFT_METADATA_PROGRAM in programs_called:
            return "nft"

        # If a DEX program was called, it's a swap
        for prog in programs_called:
            if prog in DEX_PROGRAMS:
                return "swap"

        return "other"

    async def process_wallet(self) -> list[Swap]:
        # Validate wallet address upfront — fail fast before any RPC calls or timeout
        try:
            Pubkey.from_string(self.wallet_address)
        except ValueError as e:
            self.logger.error(f"[Parser] Invalid wallet address '{self.wallet_address}': {e}")
            return self.processed_transactions

        t0 = time.monotonic()
        await self._process_wallet_inner(t0)
        return self.processed_transactions

    async def _process_wallet_inner(self, start_time: float) -> None:
        self.tx_logger.info(f"=== PROCESSING WALLET {self.wallet_address} | "
                           f"start={self.start_date} end={self.end_date} ===")
        if not await self._get_transaction_signatures():
            return

        sig_list = [s.signature for s in self.signatures]
        await self._fetch_transactions_batched(sig_list, start_time)

        failed = len(self.failed_signatures)
        self.logger.info(
            f"[Parser] Fetch complete: {len(self.processed_transactions)}/{len(sig_list)} transactions fetched, "
            f"{failed} failed after retries"
        )

    async def _fetch_transactions_batched(self, sigs: list[str | Signature], start_time: float) -> None:
        """Fetch transactions using the strategy matched to the RPC rate limits."""
        if self.profile.per_req_delay > 0:
            await self._fetch_sequential(sigs, start_time)
        else:
            await self._fetch_parallel(sigs, start_time)

    async def _fetch_sequential(self, sigs: list[str], start_time: float) -> None:
        """Fetch one at a time with per-request delay — for public RPC.

        On first rate-limit hit, pauses the whole loop to let the window reset.
        Processes each transaction inline so partial results survive timeouts.
        Checks elapsed time before each iteration to avoid exceeding PROCESS_TIMEOUT.
        """
        rate_limited = False
        for idx, sig in enumerate(sigs):
            elapsed = time.monotonic() - start_time
            if elapsed >= PROCESS_TIMEOUT:
                self.timed_out = True
                self.logger.warning(
                    f"[Parser] Process timed out after {PROCESS_TIMEOUT}s. "
                    f"Returning {len(self.processed_transactions)} partial results."
                )
                break
            json_data, was_rl = await self._get_transaction_details(sig)
            if json_data is not None:
                swap = self._process_transaction_details(json_data)
                if swap:
                    self.processed_transactions.append(swap)
            else:
                self.failed_signatures.append(sig)
                self.tx_logger.info(f"FAIL [{sig}] Transaction fetch failed")
            if was_rl and not rate_limited:
                rate_limited = True
                self.logger.warning(
                    f"[Parser] Rate limit hit — pausing {self.profile.rate_limit_pause}s before continuing"
                )
                await asyncio.sleep(self.profile.rate_limit_pause)
            if idx < len(sigs) - 1:
                await asyncio.sleep(self.profile.per_req_delay)

    async def _fetch_parallel(self, sigs: list[str], start_time: float) -> None:
        """Fetch in parallel batches — for paid RPC with generous limits."""
        batch_size = self.profile.batch_size
        for i in range(0, len(sigs), batch_size):
            elapsed = time.monotonic() - start_time
            if elapsed >= PROCESS_TIMEOUT:
                self.timed_out = True
                self.logger.warning(
                    f"[Parser] Process timed out after {PROCESS_TIMEOUT}s. "
                    f"Returning {len(self.processed_transactions)} partial results."
                )
                break
            batch = sigs[i:i + batch_size]
            semaphore = asyncio.Semaphore(len(batch))
            tasks = [self._fetch_with_semaphore(sig, semaphore) for sig in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            if i + batch_size < len(sigs):
                await asyncio.sleep(self.profile.batch_delay)

    async def _fetch_with_semaphore(self, signature: str | None, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            json_data, _ = await self._get_transaction_details(signature)
            if json_data is not None:
                swap = self._process_transaction_details(json_data)
                if swap:
                    self.processed_transactions.append(swap)
            else:
                self.failed_signatures.append(signature)
                self.tx_logger.info(f"FAIL [{signature}] Transaction fetch failed")

    async def _get_transaction_signatures(self, max_batches: int = 100) -> bool:
        pubkey = Pubkey.from_string(self.wallet_address)

        self.signatures = []
        before_tx = None
        batch_count = 0
        self.signature_count = 0

        while True:
            if batch_count >= max_batches:
                self.logger.info(f"[Parser] Reached max_batches limit ({max_batches}). Stopping pagination.")
                break

            try:
                result, _ = await _rpc_retry(
                    lambda: self.solana_client.get_signatures_for_address(
                        pubkey,
                        before=before_tx,
                    ),
                    logger=self.logger,
                )
                batch = result.value
            except Exception as e:
                self.logger.error(f"[Parser] Error fetching signatures (all retries exhausted): {type(e).__name__}: {repr(e)}")
                break

            batch_count += 1

            if not batch:
                self.logger.info("[Parser] Signature batch is empty")
                break
            else:
                self.logger.info(f"Retrieved {len(batch)} for batch")

            if self.start_date and self.end_date:
                filtered = [
                    sig for sig in batch
                    if sig.block_time
                    and self.start_date <= datetime.fromtimestamp(sig.block_time, timezone.utc) <= self.end_date
                ]
            else:
                filtered = [sig for sig in batch if sig.block_time]

            if not filtered:
                self.logger.info(f"[Parser] No more signatures in date range {self.start_date} to {self.end_date}")
                break

            self.signature_count += len(filtered)
            self.signatures.extend(filtered)

            # If the earliest signature in this batch is older than start_date, break early
            if self.start_date:
                oldest_block_time = (
                    datetime.fromtimestamp(batch[-1].block_time, timezone.utc) if batch[-1].block_time else None
                )
                if oldest_block_time and oldest_block_time < self.start_date:
                    break

            raw_sig = batch[-1].signature
            # solana-py 0.40 requires Signature object for pagination
            before_tx = raw_sig if isinstance(raw_sig, Signature) else Signature.from_string(raw_sig)

        self.logger.info(f"[Parser] Total signatures: {len(self.signatures)}")

        if len(self.signatures) > TRANSACTION_LIMIT:
            self.logger.info("[Parser] Exceeded transaction limit. Skipping this wallet")
            return False
        return True

    async def _get_transaction_details(self, signature: str | Signature | None = None) -> tuple[dict | None, bool]:
        """Fetch transaction details. Returns (json_data_or_none, was_rate_limited)."""
        if signature is None:
            return None, False
        # solana-py 0.40 requires Signature object, not string
        if isinstance(signature, str):
            sig_obj = Signature.from_string(signature)
        else:
            sig_obj = signature
        try:
            result, was_rl = await _rpc_retry(
                lambda: self.solana_client.get_transaction(sig_obj, max_supported_transaction_version=0),
                logger=self.logger,
            )
            transaction_details = result.value
            return json.loads(transaction_details.to_json()), was_rl
        except Exception as e:
            self.logger.error("Transaction fetch failed after 3 retries: %s", signature)
            is_rl = "HTTPStatusError" in repr(e)
            return None, is_rl

    def _process_transaction_details(self, json_data: dict) -> Swap | None:
        sig = json_data.get("transaction", {}).get("signatures", [None])[0]

        transaction_status = json_data["meta"]["err"]

        if transaction_status is not None:
            self.tx_logger.info(f"SKIP [{sig}] Failed tx: {transaction_status}")
            return

        account_keys = json_data["transaction"]["message"]["accountKeys"]

        preTokenBalances = json_data["meta"]["preTokenBalances"]
        postTokenBalances = json_data["meta"]["postTokenBalances"]

        # Not a buy/sell transaction
        if not preTokenBalances or not postTokenBalances:
            self.tx_logger.info(f"SKIP [{sig}] No token balances")
            return

        pre_dict: dict[str, float] = {}
        post_dict: dict[str, float] = {}

        for balance in preTokenBalances:
            current_mint = balance["mint"]
            current_owner = balance["owner"]

            if current_owner != str(self.wallet_address):
                continue

            preTokenBalance = balance["uiTokenAmount"]["uiAmount"]
            preTokenBalance = float(preTokenBalance) if preTokenBalance is not None else 0
            pre_dict[current_mint] = preTokenBalance

        for balance in postTokenBalances:
            current_mint = balance["mint"]
            owner = balance["owner"]

            if owner != str(self.wallet_address):
                continue

            postTokenBalance = balance["uiTokenAmount"]["uiAmount"]
            postTokenBalance = float(postTokenBalance) if postTokenBalance is not None else 0
            post_dict[current_mint] = postTokenBalance

        swap = Swap()

        # Classify tokens by balance change direction
        received_tokens = []
        sent_tokens = []
        for token in set(pre_dict.keys()).union(set(post_dict.keys())):
            pre_value = pre_dict.get(token, 0)
            post_value = post_dict.get(token, 0)
            if post_value > pre_value:
                received_tokens.append((token, post_value - pre_value))
            elif post_value < pre_value:
                sent_tokens.append((token, pre_value - post_value))

        # Simple swap: one token received, one sent
        if len(received_tokens) == 1 and len(sent_tokens) == 1:
            swap.tokenReceived_ = received_tokens[0][0]
            swap.quantityReceived_ = received_tokens[0][1]
            swap.tokenSent_ = sent_tokens[0][0]
            swap.quantitySent_ = sent_tokens[0][1]
        # Multi-hop: aggregate received/sent sides
        elif received_tokens and sent_tokens:
            swap.tokenReceived_ = max(received_tokens, key=lambda x: x[1])[0]
            swap.quantityReceived_ = sum(r[1] for r in received_tokens)
            swap.tokenSent_ = max(sent_tokens, key=lambda x: x[1])[0]
            swap.quantitySent_ = sum(s[1] for s in sent_tokens)
        elif received_tokens:
            swap.tokenReceived_ = max(received_tokens, key=lambda x: x[1])[0]
            swap.quantityReceived_ = sum(r[1] for r in received_tokens)
        elif sent_tokens:
            swap.tokenSent_ = max(sent_tokens, key=lambda x: x[1])[0]
            swap.quantitySent_ = sum(s[1] for s in sent_tokens)

        # Handle SOL swaps via lamport balance diff
        index = account_keys.index(str(self.wallet_address))

        preBalances = json_data["meta"]["preBalances"]
        postBalances = json_data["meta"]["postBalances"]

        if swap.tokenReceived_ is None:  # token received was SOL
            pre = preBalances[index]
            post = postBalances[index]
            diff = post - pre
            sol_amount = diff / 1000000000
            swap.tokenReceived_ = sol_address
            swap.quantityReceived_ = sol_amount
        if swap.tokenSent_ is None:  # token sent was SOL
            pre = preBalances[index]
            post = postBalances[index]
            diff = pre - post
            sol_amount = diff / 1000000000
            swap.tokenSent_ = sol_address
            swap.quantitySent_ = sol_amount

        if (swap.quantityReceived_ is not None and swap.quantityReceived_ < 0) or \
           (swap.quantitySent_ is not None and swap.quantitySent_ < 0):
            self.tx_logger.info(f"SKIP [{sig}] Negative quantity: sent={swap.quantitySent_}, recv={swap.quantityReceived_}")
            return

        swap.signature_ = json_data["transaction"]["signatures"][0]
        swap.status_ = "Success"
        swap.blockTime_ = json_data["blockTime"]
        swap.dateTime_ = datetime.fromtimestamp(json_data["blockTime"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        swap.platform_ = self._detect_dex(json_data)
        swap.category_ = self._detect_category(json_data)
        swap.tokenReceivedSymbol_ = TOKEN_SYMBOLS.get(swap.tokenReceived_, None)
        swap.tokenSentSymbol_ = TOKEN_SYMBOLS.get(swap.tokenSent_, None)

        self.tx_logger.info(
            f"SWAP [{sig}] "
            f"{swap.tokenSentSymbol_ or swap.tokenSent_}({swap.quantitySent_}) -> "
            f"{swap.tokenReceivedSymbol_ or swap.tokenReceived_}({swap.quantityReceived_}) "
            f"| platform={swap.platform_} category={swap.category_} time={swap.dateTime_}"
        )
        self.tx_logger.debug(f"RAW [{sig}] {json.dumps(json_data)}")
        return swap