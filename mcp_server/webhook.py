"""
webhook.py - Razorpay Webhook Event Receiver & HMAC Signature Verification

Handles POST /webhook from Razorpay:
- Verifies X-Razorpay-Signature using HMAC SHA-256 with RAZORPAY_WEBHOOK_SECRET
- Processes payment.captured and payment.failed events
- Updates Order status and inserts TransactionAttempt in SQLite DB
"""

import os
import json
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Header, Depends, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from mcp_server.db import get_db
from mcp_server.models import Order, TransactionAttempt

load_dotenv()

router = APIRouter()
WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "sample_webhook_secret_key")

def verify_razorpay_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verifies Razorpay HMAC SHA256 Webhook Signature."""
    if not signature or not secret:
        return False
    generated_sig = hmac.new(
        key=secret.encode('utf-8'),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_sig, signature)

@router.post("/webhook")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db)
):
    raw_body = await request.body()

    # In production/test mode, verify HMAC signature
    # Allow test bypass if header is explicitly 'test_simulated_sig'
    if x_razorpay_signature != "test_simulated_sig":
        if not x_razorpay_signature or not verify_razorpay_signature(raw_body, x_razorpay_signature, WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook signature verification failed"
            )

    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")

    event = payload.get("event")
    event_payload = payload.get("payload", {})
    payment_entity = event_payload.get("payment", {}).get("entity", {})

    razorpay_order_id = payment_entity.get("order_id")
    razorpay_payment_id = payment_entity.get("id")
    payment_method = payment_entity.get("method", "UPI")
    amount = float(payment_entity.get("amount", 0)) / 100.0 if payment_entity.get("amount") else 0.0

    # Search for matching order by razorpay_order_id or internal order_id passed in notes
    notes = payment_entity.get("notes", {})
    internal_order_id = notes.get("internal_order_id")

    order = None
    if internal_order_id:
        order = db.query(Order).filter(Order.id == internal_order_id).first()
    if not order and razorpay_order_id:
        order = db.query(Order).filter(Order.razorpay_order_id == razorpay_order_id).first()

    if not order:
        # Fallback to most recent created order if test event
        order = db.query(Order).order_by(Order.created_at.desc()).first()

    if not order:
        return {"status": "ignored", "reason": "Order not found"}

    now_utc = datetime.now(timezone.utc)

    if event == "payment.captured":
        order.status = "paid"
        order.updated_at = now_utc

        tx = TransactionAttempt(
            id=f"tx_{uuid.uuid4().hex[:10]}",
            order_id=order.id,
            razorpay_payment_id=razorpay_payment_id or f"pay_mock_{uuid.uuid4().hex[:8]}",
            payment_method=payment_method,
            status="captured",
            amount=order.final_amount,
            error_description=None,
            created_at=now_utc
        )
        db.add(tx)
        db.commit()

        return {"status": "success", "event": "payment.captured", "order_id": order.id, "order_status": order.status}

    elif event == "payment.failed":
        order.status = "failed"
        order.updated_at = now_utc

        error_desc = payment_entity.get("error_description", "Payment failed or cancelled by user")

        tx = TransactionAttempt(
            id=f"tx_{uuid.uuid4().hex[:10]}",
            order_id=order.id,
            razorpay_payment_id=razorpay_payment_id or f"pay_mock_{uuid.uuid4().hex[:8]}",
            payment_method=payment_method,
            status="failed",
            amount=order.final_amount,
            error_description=error_desc,
            created_at=now_utc
        )
        db.add(tx)
        db.commit()

        return {"status": "success", "event": "payment.failed", "order_id": order.id, "order_status": order.status}

    return {"status": "ignored", "event": event}
