from __future__ import annotations

import json
from wallet_analytics_mcp.swap import Swap


def test_swap_to_json_fields():
    s = Swap()
    s.signature_ = "sig-001"
    s.tokenReceived_ = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    s.tokenSent_ = "So11111111111111111111111111111111111111112"
    s.quantityReceived_ = 10.5
    s.quantitySent_ = 0.5
    s.platform_ = "Raydium-AMM"
    s.category_ = "swap"
    s.tokenReceivedSymbol_ = "USDC"
    s.tokenSentSymbol_ = "SOL"

    data = json.loads(s.to_json())
    assert data["signature"] == "sig-001"
    assert data["platform"] == "Raydium-AMM"
    assert data["category"] == "swap"
    assert data["tokenReceivedSymbol"] == "USDC"
    assert data["tokenSentSymbol"] == "SOL"


def test_swap_str_repr():
    s = Swap()
    s.signature_ = "sig-test"
    s.platform_ = "Jupiter-Aggregator"
    s.category_ = "swap"
    txt = str(s)
    assert "sig-test" in txt
    assert "Jupiter-Aggregator" in txt


def test_swap_defaults_none():
    s = Swap()
    assert s.signature_ is None
    assert s.tokenReceived_ is None
    assert s.tokenSent_ is None
    assert s.quantitySent_ is None
    assert s.quantityReceived_ is None
    assert s.platform_ is None
    assert s.category_ is None
    assert s.tokenReceivedSymbol_ is None
    assert s.tokenSentSymbol_ is None
