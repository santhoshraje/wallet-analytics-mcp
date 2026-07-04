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
  "mcpServers": {
    "wallet-analytics": {
      "command": "uvx",
      "args": ["wallet-analytics-mcp"]
    }
  }
}
```

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ALCHEMY_URL` | — | Alchemy RPC endpoint (required for default provider) |
| `SOLANA_RPC_PROVIDER` | `ALCHEMY_CLIENT` | Active provider |
| `SOLANA_RPC_TIMEOUT` | `30` | RPC timeout in seconds |
| `SOLANA_TX_LIMIT` | `30000` | Max transactions per wallet |

Available providers: `ALCHEMY_CLIENT`, `QUICKNODE_CLIENT`, `HELIUS_CLIENT`, `CHAINSTACK_CLIENT`, `DRPC_CLIENT`, `SYNDICA_CLIENT`, `SOLANA_PUBLIC_CLIENT`

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
