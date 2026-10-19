"""Tests for the additional Homework 1 store-policy tool."""

from agent.auth import AuthContext
from agent.tools import get_store_policy

MERCHANT_STORE_2 = AuthContext(user_id=9002, role="merchant", store_id=2)
SHOPPER = AuthContext(user_id=1, role="shopper")
SUPPORT = AuthContext(user_id=9501, role="support")


def test_get_store_policy_returns_store_override(world: dict) -> None:
    result = get_store_policy(MERCHANT_STORE_2, 2)

    assert result["ok"] is True
    assert result["store_name"] == "Juniper Home Goods"
    assert result["policy_id"] == "store-juniper-home-goods-policy"
    assert result["uses_platform_default"] is False
    assert "14 days" in result["body"]


def test_get_store_policy_falls_back_to_platform_default(world: dict) -> None:
    result = get_store_policy(SHOPPER, 1)

    assert result["ok"] is True
    assert result["store_name"] == "Blue Heron Ceramics"
    assert result["policy_id"] == "cw-returns"
    assert result["uses_platform_default"] is True


def test_get_store_policy_rejects_unknown_store(world: dict) -> None:
    result = get_store_policy(SUPPORT, 999_999)

    assert result == {
        "ok": False,
        "error": "not_found",
        "reason": "no store with id 999999",
    }
