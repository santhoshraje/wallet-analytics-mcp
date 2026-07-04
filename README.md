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

Fetch swap transactions for a wallet address.

**Parameters:**
- `wallet_address` (required): Solana wallet public key (base58)
- `start_date` (optional): ISO 8601 date string (default: 30 days ago)
- `end_date` (optional): ISO 8601 date string (default: now)

**Returns:** List of swaps with token pairs, quantities, timestamps, and signatures.

## Logging

Logs written to `log/mcp_server.log` in the package directory.

## License

MIT
