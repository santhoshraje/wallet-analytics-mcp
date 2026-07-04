# Unit Testing Plan — wallet-analytics-mcp

## Overview

Robust, layered test suite using **pytest** + **pytest-asyncio**. Follows FastMCP best practices: in-memory `Client(server)` for tool tests, mocked RPC for parser tests, fixture JSON data for transaction parsing.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures: mock client, sample tx JSONs
├── test_config.py           # classify_token(), env helpers, constants
├── test_provider.py         # Client caching, clear_cache
├── test_swap.py             # Swap class, to_json(), __str__()
├── test_swap_parser.py      # detect_dex, detect_category, rpc_retry, process_transaction_details
├── test_server.py           # Tool registration, tool execution via FastMCP Client, filter logic
└── fixtures/
    ├── swap_raydium.json    # Real-style Raydium AMM swap JSON
    ├── swap_jupiter.json    # Jupiter aggregator multi-hop swap JSON
    ├── transfer_token.json  # SPL Token transfer (no DEX program)
    ├── staking_tx.json      # Stake program transaction JSON
    └── nft_mint.json        # NFT metadata program transaction JSON
```

Mirrors `src/wallet_analytics_mcp/` package structure — one test file per module.

## Testing Layers

### Layer 1: Unit Tests (no network, fully mocked)
- Test pure functions and isolated methods
- Mock RPC client; feed fixture JSON data directly to parser methods
- Fast execution (<1s total)

### Layer 2: Tool Integration Tests (in-memory FastMCP Client)
- Use `async with Client(mcp_server)` pattern from FastMCP docs
- Mock `SwapParser.process_wallet()` to return controlled Swap list
- Verify tool returns correct JSON structure and filter behavior

### Layer 3: Integration Tests (marked `@pytest.mark.integration`)
- Optional: real RPC call against public endpoint
- Skip in CI unless `SOLANA_RPC_URL` env var is set
- Smoke test only — verify end-to-end flow

## Test Coverage by Module

### `test_config.py` (6 tests)
| Test | What it verifies |
|------|------------------|
| `test_classify_token_stablecoin` | USDC → "stablecoin" |
| `test_classify_token_base` | SOL → "base" |
| `test_classify_token_other` | Unknown mint → "other" |
| `test_env_int_default` | `_env_int` falls back correctly |
| `test_env_string_default` | `_env` returns fallback when unset |
| `test_constants_non_empty` | BASE_CURRENCIES, DEX_PROGRAMS, STABLECOIN_MINTS all populated |

### `test_provider.py` (4 tests)
| Test | What it verifies |
|------|------------------|
| `test_get_client_caches_by_url` | Same URL → same Client instance |
| `test_get_client_different_urls` | Different URLs → different instances |
| `test_clear_cache` | Cache emptied after call |
| `test_get_client_recreates_after_clear` | New client created after cache cleared |

### `test_swap.py` (3 tests)
| Test | What it verifies |
|------|------------------|
| `test_swap_to_json_fields` | All fields present in JSON output including `category`, `platform` |
| `test_swap_str_repr` | `__str__` includes all fields |
| `test_swap_defaults_none` | Fresh Swap has all fields as None |

### `test_swap_parser.py` (14 tests) — **Core logic**

#### DEX Detection (`__detect_dex`)
| Test | What it verifies |
|------|------------------|
| `test_detect_dex_raydium_top_level` | Raydium program in top-level instructions |
| `test_detect_dex_jupiter_inner` | Jupiter program in innerInstructions only |
| `test_detect_dex_unknown` | No known DEX → returns "unknown" |
| `test_detect_dex_meteora` | Meteora-DLMM detected correctly |

#### Category Detection (`__detect_category`)
| Test | What it verifies |
|------|------------------|
| `test_detect_category_swap` | DEX program present → "swap" |
| `test_detect_category_transfer` | Only SPL Token program → "transfer" |
| `test_detect_category_staking` | Stake program present → "staking" |
| `test_detect_category_nft` | NFT metadata program → "nft" |
| `test_detect_category_other` | Unrecognized programs → "other" |

#### RPC Retry (`_rpc_retry`)
| Test | What it verifies |
|------|------------------|
| `test_rpc_retry_success_first_try` | No retry on success |
| `test_rpc_retry_succeeds_after_failures` | Retries until success |
| `test_rpc_retry_exhausted_raises` | Raises after max_attempts |

#### Transaction Processing (`__process_transaction_details`)
| Test | What it verifies |
|------|------------------|
| `test_process_simple_swap` | One token sent, one received → correct fields |
| `test_process_failed_transaction` | Error in meta.err → returns None |

### `test_server.py` (10 tests) — **Tool-level integration**

Uses FastMCP's in-memory `Client(mcp)` pattern. Mocks `SwapParser.process_wallet()` to return controlled Swap lists.

#### Tool Registration
| Test | What it verifies |
|------|------------------|
| `test_tool_registered` | `get_raw_transactions` appears in `mcp.list_tools()` |

#### Filter Logic (via Client.call_tool)
| Test | What it verifies |
|------|------------------|
| `test_no_filters_returns_all` | No optional filters → all swaps returned |
| `test_filter_stablecoin_pairs` | filter_stablecoin_pairs=True drops SOL↔USDC swaps |
| `test_token_type_filter_meme` | token_type_filter="meme" keeps only non-stablecoin/base swaps |
| `test_token_type_filter_stablecoin` | token_type_filter="stablecoin" keeps stablecoin/base swaps |
| `test_min_amount_sent` | Swaps below threshold filtered out |
| `test_min_amount_received` | Swaps below threshold filtered out |
| `test_exclude_categories_transfer` | exclude_categories=["transfer"] removes transfers |
| `test_exclude_categories_multiple` | exclude_categories=["staking","nft"] removes both |

#### Response Structure
| Test | What it verifies |
|------|------------------|
| `test_response_has_filters_applied` | Response includes `filters_applied` dict with all filter keys |
| `test_response_swap_fields_includes_category` | Each swap in response has `category` field |

## Fixture Strategy (`conftest.py`)

### Mock Solana Client
```python
@pytest.fixture
def mock_solana_client():
    """Mock solana.rpc.api.Client that returns fixture data."""
    client = MagicMock(spec=Client)
    # Pre-configured to return signature list and transaction details
    return client
```

### Sample Transaction Fixtures
Each fixture JSON mimics the structure of `transaction.to_json()` output:
- `swap_raydium.json`: SOL → BONK swap on Raydium AMM
- `swap_jupiter.json`: USDC → POPCAT multi-hop via Jupiter
- `transfer_token.json`: USDC transfer (Token program only)
- `staking_tx.json`: Stake delegation transaction
- `nft_mint.json`: NFT mint with metadata program

### Swap Fixture Factory
```python
@pytest.fixture
def sample_swap():
    """Create a Swap with known values for assertions."""
    return Swap(
        signature="abc123...",
        tokenReceived="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        tokenSent="So11111111111111111111111111111111111111112",
        quantityReceived=10.5,
        quantitySent=0.5,
        platform="Raydium-AMM",
        category="swap",
    )
```

## pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "integration: tests that require a real RPC endpoint (deselect with '-m \"not integration\"')",
]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support (auto mode) |
| `mcp` | FastMCP Client for in-memory tool testing |

## Running Tests

```bash
# All unit tests (fast, no network)
pytest -v

# Skip integration tests
pytest -v -m "not integration"

# With coverage
pytest --cov=wallet_analytics_mcp --cov-report=term-missing
```

## Coverage Targets

| Module | Target |
|--------|--------|
| `config.py` | 100% |
| `provider.py` | 95%+ |
| `swap.py` | 100% |
| `swap_parser.py` | 80%+ (parser logic covered; RPC pagination not) |
| `server.py` | 90%+ (filter logic covered; logging/lifespan not) |

## Key Design Decisions

1. **No real RPC in unit tests** — all network calls mocked or skipped. Tests are deterministic and fast.
2. **Fixture JSON data** — realistic transaction structures without depending on live blockchain data.
3. **FastMCP Client for tool tests** — follows the official FastMCP testing pattern; tests full tool lifecycle including parameter validation.
4. **Single behavior per test** — each test verifies one thing, making failures easy to diagnose.
5. **Self-contained tests** — no shared state; runnable in any order or parallel.
