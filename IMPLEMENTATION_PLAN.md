# Implementation Plan: Filter & Output Improvements

## Context

The parser currently returns all swaps using token balance deltas only. The tool-level filters (`filter_stablecoin_pairs`, `require_base_currency`, `min_volume_sol`) are too restrictive and SOL-centric. This plan adds DEX detection, flexible filtering, and token metadata to the output.

---

## Phase 1: Add `dex_program` to Swap Output

**Goal:** Identify which DEX executed each swap (Jupiter, Raydium, Pump.fun, Meteora, Orca, etc.).

### Changes

#### 1a. `config.py` — DEX program ID lookup table

Add a mapping of known Solana DEX program IDs to human-readable names:

```python
DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfrLNYJzRfXWvKHh2Qdwn7NjsZ4E": "Raydium-AMM",
    "JUP6LkbZbjS1jKKwapdHNy74zcW3tLuZ55XkfGPaHaq": "Jupiter-Aggregator",
    "MEisE1DhNbaGYZgCpYzjAeF5hYoVjU8f6TbAhPiMihB": "Meteora-DLMM",
    "LBUZKhRxPFMYrbQiuS16yH15W8VBrXKu69Npa6bF7oj": "Meteora-Whirlpool",
    "TerP7ftemaffewJ4RMSuTzMU28FrY7B8EGCw3TwBNwL": "Pump-fun",
    "DjVE6JNiPYq5pQU9UoKrGBpVeFLWbXkbGEBGsQpA8hCo": "Orca",
}
```

Also add a `STABLECOIN_MINTS` set (expand beyond BASE_CURRENCIES):

```python
STABLECOIN_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f",   # USDT (Solana)
    "7vfCXTUXR512Ls3APYmoG4GqP7jwD6zN1UvWYnJyqBQo",   # USDC (legacy)
}
```

#### 1b. `swap_parser.py` — Extract DEX from transaction instructions

In `__process_transaction_details`, after the balance analysis, add a helper to scan the transaction's compiled instructions for known DEX program IDs:

```python
def __detect_dex(self, json_data: dict) -> str | None:
    """Find which DEX program was called in this transaction."""
    instructions = json_data["transaction"]["message"].get("instructions", [])
    account_keys = json_data["transaction"]["message"]["accountKeys"]
    for ix in instructions:
        prog_idx = ix.get("programIdIndex")
        if prog_idx is not None and prog_idx < len(account_keys):
            prog_id = account_keys[prog_idx]
            if prog_id in DEX_PROGRAMS:
                return DEX_PROGRAMS[prog_id]
    # Fallback: check inner instructions
    inner = json_data["meta"].get("innerInstructions", [])
    for group in inner:
        for ix in group.get("instructions", []):
            prog_idx = ix.get("programIdIndex")
            if prog_idx is not None and prog_idx < len(account_keys):
                prog_id = account_keys[prog_idx]
                if prog_id in DEX_PROGRAMS:
                    return DEX_PROGRAMS[prog_id]
    return "unknown"
```

Set `swap.platform_ = self.__detect_dex(json_data)` before returning the swap.

#### 1c. `server.py` — Include `platform` in tool output

The `platform_` field already exists in the Swap class and JSON serializer. Ensure it's included in the return dict:

```python
{
    "signature": s.signature_,
    "tokenReceived": s.tokenReceived_,
    "tokenSent": s.tokenSent_,
    "quantitySent": s.quantitySent_,
    "quantityReceived": s.quantityReceived_,
    "platform": s.platform_,        # <-- add this
    "dateTime": s.dateTime_,
    "blockTime": s.blockTime_,
}
```

---

## Phase 2: Replace `min_volume_sol` with Currency-Agnostic Filters

**Goal:** Let the LLM filter by minimum amount on either side, regardless of token.

### Changes

#### 2a. Tool signature update (`server.py`)

Replace `min_volume_sol` with two new parameters:

```python
def get_raw_transactions(
    wallet_address: str,
    start_date: str | None = None,
    end_date: str | None = None,
    filter_stablecoin_pairs: bool = False,
    require_base_currency: bool = False,
    min_amount_sent: float | None = None,   # new
    min_amount_received: float | None = None,  # new
):
```

Docstring update:
- `min_amount_sent`: Minimum token quantity sent to include the swap.
- `min_amount_received`: Minimum token quantity received to include the swap.

#### 2b. Filter logic update (`server.py`)

Replace the `min_volume_sol` filter block with:

```python
if min_amount_sent is not None:
    swaps = [s for s in swaps if (s.quantitySent_ or 0) >= min_amount_sent]
if min_amount_received is not None:
    swaps = [s for s in swaps if (s.quantityReceived_ or 0) >= min_amount_received]
```

Update `filters_applied` in return dict accordingly.

#### 2c. README update

Document the new parameters and deprecate `min_volume_sol`.

---

## Phase 3: Replace `require_base_currency` with `token_type_filter`

**Goal:** Let the LLM choose what token types to include, rather than hard-coding "base currency" logic.

### Changes

#### 3a. Tool signature update (`server.py`)

Remove `require_base_currency`, add:

```python
token_type_filter: str | None = None,  # "meme", "stablecoin", "all" (default)
```

Docstring: `token_type_filter` — Filter swaps by token category. `"meme"` keeps only swaps where at least one token is NOT a stablecoin/base currency. `"stablecoin"` keeps only swaps involving a stablecoin. Default (`None`) returns all swaps.

#### 3b. Config update (`config.py`)

Add `ALL_KNOWN_TOKENS` — not feasible to maintain statically. Instead, classify tokens at runtime:

```python
def classify_token(mint: str) -> str:
    """Return 'stablecoin', 'base', or 'other' for a mint address."""
    if mint in STABLECOIN_MINTS:
        return "stablecoin"
    if mint in BASE_CURRENCIES:
        return "base"
    return "other"  # meme, governance, etc.
```

#### 3c. Filter logic update (`server.py`)

```python
if token_type_filter == "meme":
    swaps = [s for s in swaps if
             classify_token(s.tokenReceived_) != "stablecoin" or
             classify_token(s.tokenSent_) != "stablecoin"]
elif token_type_filter == "stablecoin":
    swaps = [s for s in swaps if
             classify_token(s.tokenReceived_) in ("stablecoin", "base") or
             classify_token(s.tokenSent_) in ("stablecoin", "base")]
```

---

## Phase 4: Add `exclude_categories` Filter

**Goal:** Let the LLM exclude transaction categories that aren't swaps.

### Changes

#### 4a. Parser: Detect transaction category (`swap_parser.py`)

Add a `category_` field to the Swap class. In `__process_transaction_details`, detect the category by checking program instructions:

```python
def __detect_category(self, json_data: dict) -> str:
    """Classify transaction as 'swap', 'transfer', 'staking', 'nft', or 'other'."""
    # Check for SPL Token transfer instruction (program: TokenkegQfeZyi1iAGBsnHNA7mJ6k3F4YK22qfjMKn)
    token_program = "TokenkegQfeZyi1iAGBsnHNA7mJ6k3F4YK22qfjMKn"
    account_keys = json_data["transaction"]["message"]["accountKeys"]
    
    instructions = json_data["transaction"]["message"].get("instructions", [])
    programs_called = set()
    for ix in instructions:
        prog_idx = ix.get("programIdIndex")
        if prog_idx is not None and prog_idx < len(account_keys):
            programs_called.add(account_keys[prog_idx])
    
    # If only token program called, likely a plain transfer
    if programs_called == {token_program}:
        return "transfer"
    
    # Check for staking program (Ck4gqAbeysRR8j6YycZs3wEoQeAmPzJfnghgFvLbVHMT)
    stake_program = "Ck4gqAbeysRR8j6YycZs3wEoQeAmPzJfnghgFvLbVHMT"
    if stake_program in programs_called:
        return "staking"
    
    # Check for NFT metadata program (metaqbxxUerdq28cj1RbAWkZQmYnpuuZqd25Q5Uze")
    nft_program = "metaqbxxUerdq28cj1RbAWkZQmYnpuuZqd25Q5Uze"
    if nft_program in programs_called:
        return "nft"
    
    # If a DEX program was called, it's a swap
    for prog in programs_called:
        if prog in DEX_PROGRAMS:
            return "swap"
    
    return "other"
```

#### 4b. Swap class update (`swap.py`)

Add `category_` field:

```python
self.category_ = None
```

Include in `to_json()` and `__str__()`.

#### 4c. Tool parameter (`server.py`)

Add `exclude_categories: list[str] | None = None`:

Docstring: `exclude_categories` — List of categories to exclude. Valid values: `"transfer"`, `"staking"`, `"nft"`, `"other"`. Default (`None`) returns all categories.

Filter logic:

```python
if exclude_categories:
    swaps = [s for s in swaps if s.category_ not in exclude_categories]
```

---

## Phase 5: Token Symbol Mapping (Basic)

**Goal:** Return token symbols alongside mint addresses so the LLM can understand what it's seeing.

### Changes

#### 5a. Config: Common token mapping (`config.py`)

Add a static lookup for well-known tokens:

```python
TOKEN_SYMBOLS = {
    "So11111111111111111111111111111111111111112": "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCMLkB7BdEJm3oAwbQXkFpKZbPVH4gVjR5f": "USDT",
}  # Extended with more known mints as needed
```

#### 5b. Parser: Resolve symbols (`swap_parser.py`)

After determining `tokenReceived_` and `tokenSent_`, resolve symbols:

```python
swap.tokenReceivedSymbol_ = TOKEN_SYMBOLS.get(swap.tokenReceived_, None)
swap.tokenSentSymbol_ = TOKEN_SYMBOLS.get(swap.tokenSent_, None)
```

#### 5c. Swap class update (`swap.py`)

Add fields:

```python
self.tokenReceivedSymbol_ = None
self.tokenSentSymbol_ = None
```

Include in `to_json()` and `__str__()`.

#### 5d. Tool output (`server.py`)

Add symbols to return dict:

```python
{
    "signature": s.signature_,
    "tokenReceived": s.tokenReceived_,
    "tokenReceivedSymbol": s.tokenReceivedSymbol_,
    "tokenSent": s.tokenSent_,
    "tokenSentSymbol": s.tokenSentSymbol_,
    ...
}
```

---

## Execution Order

| Step | Files | Effort |
|------|-------|--------|
| 1. Add DEX program IDs to config | `config.py` | Small |
| 2. Detect DEX in parser, set `platform_` | `swap_parser.py` | Medium |
| 3. Include `platform` in tool output | `server.py` | Small |
| 4. Add token symbols to config | `config.py` | Small |
| 5. Resolve symbols in parser | `swap_parser.py`, `swap.py` | Small |
| 6. Include symbols in tool output | `server.py` | Small |
| 7. Detect transaction category in parser | `swap_parser.py`, `swap.py` | Medium |
| 8. Replace `min_volume_sol` → `min_amount_sent/received` | `server.py`, `README.md` | Small |
| 9. Replace `require_base_currency` → `token_type_filter` | `server.py`, `config.py`, `README.md` | Medium |
| 10. Add `exclude_categories` filter | `server.py`, `README.md` | Small |
| 11. Update README with all new params | `README.md` | Medium |

---

## Final Tool Signature (After All Changes)

```python
def get_raw_transactions(
    wallet_address: str,                           # required
    start_date: str | None = None,                 # ISO 8601, default 30d ago
    end_date: str | None = None,                   # ISO 8601, default now
    filter_stablecoin_pairs: bool = False,         # drop base↔base swaps
    token_type_filter: str | None = None,          # "meme" | "stablecoin" | None
    min_amount_sent: float | None = None,          # min qty sent
    min_amount_received: float | None = None,      # min qty received
    exclude_categories: list[str] | None = None,   # ["transfer", "staking", "nft"]
):
```

## Final Swap Output (Per Item)

```json
{
  "signature": "...",
  "tokenReceived": "mint_address",
  "tokenReceivedSymbol": "USDC",
  "tokenSent": "mint_address",
  "tokenSentSymbol": "BONK",
  "quantitySent": 1500000,
  "quantityReceived": 42.5,
  "platform": "Raydium-AMM",
  "category": "swap",
  "dateTime": "2025-06-15 14:32:01",
  "blockTime": 1718454721
}
```
