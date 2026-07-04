from __future__ import annotations

from wallet_analytics_mcp.provider import get_client, clear_cache


def test_get_client_caches_by_url():
    c1 = get_client()
    c2 = get_client()
    assert c1 is c2


def test_clear_cache():
    get_client()
    clear_cache()
    c_after = get_client()
    # New instance after clear
    assert c_after is not None


def test_get_client_recreates_after_clear():
    c1 = get_client()
    clear_cache()
    c2 = get_client()
    assert c1 is not c2
