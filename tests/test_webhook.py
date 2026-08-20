"""
test_webhook.py - Unit tests for Razorpay Webhook signature verification & event handler
"""

import os
import sys
import hmac
import hashlib
import json
import uuid
import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_server.server import app
from mcp_server.webhook import verify_razorpay_signature, WEBHOOK_SECRET
from mcp_server.db import init_db, SessionLocal
from mcp_server.models import Order, Product

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_signature_verification_valid():
    raw_body = b'{"event":"payment.captured"}'
    secret = "sample_webhook_secret_key"
    valid_sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(raw_body, valid_sig, secret) is True

def test_signature_verification_invalid():
    raw_body = b'{"event":"payment.captured"}'
    secret = "sample_webhook_secret_key"
    assert verify_razorpay_signature(raw_body, "invalid_sig_123", secret) is False

def test_webhook_payment_captured_flow():
    db = SessionLocal()

    # Ensure a product exists
    prod = db.query(Product).first()
    if not prod:
        prod = Product(id="prod_test_wh", name="Test Product", category="Test", price=999.0)
        db.add(prod)
        db.commit()

    unique_id = uuid.uuid4().hex[:8]
    order_id = f"ord_wh_{unique_id}"
    rzp_order_id = f"order_rzp_wh_{unique_id}"

    order = Order(
        id=order_id,
        razorpay_order_id=rzp_order_id,
        product_id=prod.id,
        amount=999.0,
        currency="INR",
        status="created",
        final_amount=999.0
    )
    db.add(order)
    db.commit()
    db.close()

    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_test_cap_{unique_id}",
                    "order_id": rzp_order_id,
                    "method": "UPI",
                    "amount": 99900,
                    "notes": {"internal_order_id": order_id}
                }
            }
        }
    }

    raw_bytes = json.dumps(payload).encode('utf-8')
    valid_sig = hmac.new(WEBHOOK_SECRET.encode('utf-8'), raw_bytes, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=raw_bytes,
        headers={"X-Razorpay-Signature": valid_sig, "Content-Type": "application/json"}
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["event"] == "payment.captured"
    assert res_data["order_status"] == "paid"

    # Verify database state update
    db = SessionLocal()
    updated_order = db.query(Order).filter(Order.id == order_id).first()
    assert updated_order.status == "paid"
    db.close()
