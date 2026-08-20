"""
test_mcp_tool.py - Unit tests for AgentCheckout MCP Tools
"""

import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from seed_data import seed_database
from mcp_server.tools import (
    search_products,
    get_product,
    create_order,
    apply_offer,
    get_checkout_link,
    check_payment_status
)

@pytest.fixture(autouse=True)
def setup_seed():
    seed_database()

def test_search_and_get_product():
    products = search_products("Headphones")
    assert len(products) >= 1
    assert "Headphones" in products[0]["name"]

    prod_id = products[0]["id"]
    details = get_product(prod_id)
    assert details["id"] == prod_id
    assert "price" in details

def test_end_to_end_mcp_checkout_flow():
    # 1. Search products
    results = search_products("Watch")
    assert len(results) >= 1
    prod = results[0]

    # 2. Create Order with user context
    user_context = {
        "device_type": "Android",
        "city_tier": "Tier 2",
        "network_type": "4G",
        "hour_of_day": 18,
        "past_failed_attempts": 0
    }
    order = create_order(prod["id"], user_context)
    assert "id" in order
    assert order["status"] == "created"

    order_id = order["id"]

    # 3. Apply Offer Code
    updated_order = apply_offer(order_id, "WELCOME10")
    assert updated_order["offer_code"] == "WELCOME10"
    assert updated_order["discount_amount"] > 0
    assert updated_order["final_amount"] < updated_order["amount"]

    # 4. Get Model-Ranked Checkout Link
    chk_response = get_checkout_link(order_id)
    assert "payment_url" in chk_response
    assert "top_ranked_payment_method" in chk_response
    assert len(chk_response["all_ranked_payment_methods"]) == 5

    # 5. Check payment status reading from event DB
    status_res = check_payment_status(order_id)
    assert status_res["order_id"] == order_id
    assert "read_source" in status_res
