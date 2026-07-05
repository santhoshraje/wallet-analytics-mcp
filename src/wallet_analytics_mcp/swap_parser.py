from __future__ import annotations

import os
import json
import asyncio
from solders.pubkey import Pubkey
from datetime import datetime, timezone
import logging
from wallet_analytics_mcp.swap import Swap


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, str(default)) or str(default)
    try:
        return int(raw)
    except ValueError:
        return default


TRANSACTION_LIMIT = _env_int("SOLANA_TX_LIMIT", 500)
PROCESS_TIMEOUT = _env_int("SOLANA_PROCESS_TIMEOUT", 60)

sol_address = "So11111111111111111111111111111111111111112"
usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

BASE_CURRENCIES = {
    sol_address,
    usdc_address,
}

DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium-AMM",
    "JUP4Fb2cqiRUcaDJR5K1odmyNsBgyX76sgDLpRR1QR5": "Jupiter-Aggregator",
    "LBUZKhRxPFcijG9VGsrFkSjjeXAEqEFMvAHLHFGxLQf": "Meteora-DLMM",
    "6EF8rMRonpkNrswhqbqnmLeVdgCq1jgADTmKtbfzFHKv": "Pump-fun",
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


async def _rpc_retry(func, max_attempts: int = 3, logger=None):
    """Retry async RPC call with exponential backoff (1s → 2s → 4s)."""
    last_exception = None
    for attempt in range(max_attempts):
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            last_exception = e
            if logger:
                logger.warning(
                    f"[RPC Retry] Attempt {attempt + 1}/{max_attempts} failed: {type(e).__name__}: {repr(e)}"
                )
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)
    raise last_exception


class SwapParser:
    def __init__(
        self,
        wallet_address: str = "",
        client=None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> None:
        self.wallet_address = wallet_address
        self.signatures = []
        self.solana_client = client
        self.processed_transactions: list[Swap] = []
        self.unprocessed_transactions: list[dict] = []
        self.logger = logging.getLogger(__name__)
        self.start_date = start
        self.end_date = end

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
        try:
            await asyncio.wait_for(self._process_wallet_inner(), timeout=PROCESS_TIMEOUT)
        except asyncio.TimeoutError:
            self.logger.warning(
                f"[Parser] Process timed out after {PROCESS_TIMEOUT}s. "
                f"Returning {len(self.processed_transactions)} partial results."
            )
        return self.processed_transactions

    async def _process_wallet_inner(self) -> None:
        if not await self._get_transaction_signatures():
            return

        semaphore = asyncio.Semaphore(10)
        tasks = []
        for signature in self.signatures:
            tasks.append(self._fetch_with_semaphore(signature.signature, semaphore))
        await asyncio.gather(*tasks, return_exceptions=True)

        for unprocessed in self.unprocessed_transactions:
            transaction = self._process_transaction_details(unprocessed)
            if transaction:
                self.processed_transactions.append(transaction)

    async def _fetch_with_semaphore(self, signature: str | None, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            await self._get_transaction_details(signature)

    async def _get_transaction_signatures(self, max_batches: int = 100) -> bool:
        self.signatures = []
        before_tx = None
        batch_count = 0
        self.signature_count = 0

        while True:
            if batch_count >= max_batches:
                self.logger.info(f"[Parser] Reached max_batches limit ({max_batches}). Stopping pagination.")
                break

            try:
                result = await _rpc_retry(
                    lambda: self.solana_client.get_signatures_for_address(
                        Pubkey.from_string(self.wallet_address),
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

            before_tx = batch[-1].signature

        self.logger.info(f"[Parser] Total signatures: {len(self.signatures)}")

        if len(self.signatures) > TRANSACTION_LIMIT:
            self.logger.info("[Parser] Exceeded transaction limit. Skipping this wallet")
            return False
        return True

    async def _get_transaction_details(self, signature: str | None = None) -> None:
        try:
            result = await _rpc_retry(
                lambda: self.solana_client.get_transaction(signature, max_supported_transaction_version=0),
                logger=self.logger,
            )
            transaction_details = result.value
            json_data = json.loads(transaction_details.to_json())
            self.unprocessed_transactions.append(json_data)
        except Exception as e:
            self.logger.error("Transaction fetch failed after 3 retries: %s", signature)

    def _process_transaction_details(self, json_data: dict) -> Swap | None:
        transaction_status = json_data["meta"]["err"]

        if transaction_status is not None:
            return

        account_keys = json_data["transaction"]["message"]["accountKeys"]

        preTokenBalances = json_data["meta"]["preTokenBalances"]
        postTokenBalances = json_data["meta"]["postTokenBalances"]

        # Not a buy/sell transaction
        if not preTokenBalances or not postTokenBalances:
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
            return

        swap.signature_ = json_data["transaction"]["signatures"][0]
        swap.status_ = "Success"
        swap.blockTime_ = json_data["blockTime"]
        swap.dateTime_ = datetime.fromtimestamp(json_data["blockTime"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        swap.platform_ = self._detect_dex(json_data)
        swap.category_ = self._detect_category(json_data)
        swap.tokenReceivedSymbol_ = TOKEN_SYMBOLS.get(swap.tokenReceived_, None)
        swap.tokenSentSymbol_ = TOKEN_SYMBOLS.get(swap.tokenSent_, None)
        return swap