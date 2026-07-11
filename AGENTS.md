# wallet-analytics-mcp

MCP server that parses Solana wallet swap transactions via JSON-RPC. Outputs structured swap data for copy-trading workflows.

## Environment

- Python 3.10+ required (`mcp` SDK minimum). System Python 3.9 is too old — use a venv with Python 3.12.
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -e ".[test]"`

## Commands

- **Test**: `pytest` (all mocks, no RPC) or `pytest -m "not integration"` to skip integration tests
- **Coverage**: `pytest --cov=wallet_analytics_mcp --cov-report=term-missing`
- **Run server**: `SOLANA_RPC_URL=https://api.mainnet-beta.solana.com wallet-analytics-mcp`

## Config

All RPC config via env vars — no hardcoded URLs. See README.md for full parameter table.

| Var | Default | Purpose |
|-----|---------|---------|
| `SOLANA_RPC_URL` | Solana public RPC | JSON-RPC endpoint |
| `SOLANA_TX_LIMIT` | 500 | Max signatures per wallet |
| `SOLANA_PROCESS_TIMEOUT` | 120 | Seconds before partial return |

## RPC Rate-Limit Strategy

`RpcProfile` in `provider.py` auto-detects public vs paid RPC and applies adaptive settings:

- **Public RPC** (`api.mainnet-beta.solana.com` etc.): sequential fetching, 0.5s per-request delay, 5s HTTP timeout (fail fast on hangs), 10s loop-level pause on first 429
- **Paid RPC** (Helius, QuickNode, etc.): parallel batching of 20 requests, 30s HTTP timeout

`get_client(profile)` caches clients by `url:timeout` key — public and paid profiles get separate client instances.

## Timeout Strategy

Wallet address is validated with `Pubkey.from_string()` in `process_wallet()` **before** any RPC calls or timeout tracking — invalid addresses fail immediately, not after the full process timeout.

Timeout is tracked per-iteration using `time.monotonic()` in `_fetch_sequential` and `_fetch_parallel`. When elapsed time exceeds `PROCESS_TIMEOUT` (default 120s):

- The fetch loop breaks gracefully
- `SwapParser.timed_out` is set to `True`
- Server response includes `"partial": true` and `"partial_reason"` describing the timeout
- Already-processed swaps are returned; un-fetched signatures are silently dropped

Swaps are processed inline during the fetch loop (`_fetch_sequential`, `_fetch_with_semaphore`) — not in a post-fetch batch pass. This ensures partial results survive timeouts.

## Architecture

```
src/wallet_analytics_mcp/
  __init__.py       — package entry, calls main()
  server.py         — FastMCP server, file logging, tool registration
  provider.py       — RPC URL config, AsyncClient caching, RpcProfile
  swap_parser.py    — all constants + async parser (DEX detection, category classification)
  swap.py           — Swap dataclass with JSON serialization
```

Constants (DEX_PROGRAMS, TOKEN_SYMBOLS, etc.) live in `swap_parser.py`, not a separate config module.

## Code Conventions

- All code is async — `solana 0.40.0` removed sync `Client`; only `AsyncClient` exists
- `from __future__ import annotations` at top of every file (union type syntax for Python 3.9+ compat)
- Parser returns all raw swaps unfiltered; filtering happens at tool level as optional parameters
- Private methods use single underscore prefix (`_detect_dex`, `_process_wallet_inner`) — never `__`
- Logging: `logger.warning` for RPC retries, `logger.error` for exhausted retries (no tracebacks), `logger.info` for progress

## Testing Rules

- Test file mirrors source module: `test_swap_parser.py` → `swap_parser.py`
- Fixtures in `tests/conftest.py`: inline JSON transaction data, mock `AsyncClient` factory
- Never call real RPC in unit tests — always use `MagicMock(spec=AsyncClient)`
- Async tests rely on `pytest-asyncio` with `asyncio_mode = "auto"`
- Mock signature objects must return a real `solders.signature.Signature` for `.signature` attribute (not a string) to work with solana-py 0.40 API

## Key Gotchas

- Solana public RPC rate-limits to 10 requests/window — sequential fetching with 0.5s delay is used for public RPC
- Swaps are processed inline during fetch loop — `processed_transactions` accumulate as each transaction is fetched, not after all fetches complete
- `_get_transaction_details` returns `(dict | None, bool)` — callers must check `is not None`, not truthiness of first element
- `_env()` in provider.py returns fallback when env var is empty string (not just unset)
- DEX program IDs in `swap_parser.py` must match actual on-chain addresses — stale IDs break detection
- **solana-py 0.40 requires `Signature` objects**: `get_transaction()` and `get_signatures_for_address()` require `solders.signature.Signature`, not strings. Convert via `Signature.from_string(sig_str)` before passing to RPC calls.
- **Response parsing uses `.value`**: `GetSignaturesForAddressResp` and `GetTransactionResp` both use `.value` attribute (not `.result`). Never check `hasattr(result, 'result')` for signatures response.
- **Upfront wallet validation**: `process_wallet()` validates with `Pubkey.from_string()` before any RPC calls or timeout tracking — invalid addresses fail immediately.
- **Timeout via `time.monotonic()`**: `_fetch_sequential` and `_fetch_parallel` check `time.monotonic() - start_time >= PROCESS_TIMEOUT` per iteration. When mocking for tests, patch `wallet_analytics_mcp.swap_parser.time.monotonic` with increasing values to simulate elapsed time.
- **MagicMock陷阱**: `MagicMock(spec=AsyncClient)` auto-creates `.result` attribute, causing `hasattr(result, 'result')` to return True even when the real response uses `.value`. Access `.value` directly.
