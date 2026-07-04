# wallet-analytics-mcp

MCP server for analyzing on-chain wallet swap transactions. Fetches and parses swap data from Solana wallets for copy-trading decisions.

## Installation

```bash
pip install wallet-analytics-mcp
```

Or via uv:

```bash
uv pip install wallet-analytics-mcp
```

## Usage with opencode

Add to your `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "wallet-analytics": {
      "type": "local",
      "command": ["uvx", "wallet-analytics-mcp"],
      "environment": {
        "SOLANA_RPC_URL": "https://your-rpc-endpoint"
      }
    }
  }
}
```

The `environment` block passes env vars directly to the MCP server process — no need to export them globally.

## Configuration

All settings via environment variables (set in `opencode.json` under `"environment"`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SOLANA_RPC_URL` | Solana public RPC | Any Solana RPC endpoint (Alchemy, Helius, etc.) |
| `SOLANA_RPC_TIMEOUT` | `30` | RPC timeout in seconds |
| `SOLANA_TX_LIMIT` | `30000` | Max transactions per wallet |

Point `SOLANA_RPC_URL` at any provider — Alchemy, Helius, QuickNode, etc. Falls back to Solana public if not set.

## Available Tools

### `get_raw_transactions`

Fetch all detected swap transactions for a wallet address. By default returns every swap regardless of token pair. Optional filters let the LLM narrow results.

**Parameters:**
- `wallet_address` (required): Solana wallet public key (base58)
- `start_date` (optional): ISO 8601 date string (default: 30 days ago)
- `end_date` (optional): ISO 8601 date string (default: now)
- `filter_stablecoin_pairs` (optional, default: `False`): Drop swaps where both tokens are base currencies (SOL/USDC). Use to remove SOL→USDC and USDC→SOL noise.
- `require_base_currency` (optional, default: `False`): Keep only swaps involving at least one base currency (SOL or USDC). Drops meme-to-meme swaps like BONK→WIF.
- `min_volume_sol` (optional): Minimum SOL amount received or sent to include the swap.

**Returns:** List of swaps with token pairs, quantities, timestamps, and signatures. Response includes `filters_applied` showing which filters were active.

## Design

The parser returns all detected swaps — no hard-coded drops. Filtering happens at the tool level so the LLM decides what's relevant. This catches USDC→meme swaps, meme-to-meme trades, and any other token pair.

## Logging

Logs written to `log/mcp_server.log` in the package directory.

## License

MIT
