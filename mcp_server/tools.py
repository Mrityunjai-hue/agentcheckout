"""
tools.py - MCP Tools implementation for AgentCheckout Storefront
"""

import os
import sys
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import razorpay
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_server.db import SessionLocal
from mcp_server.models import Product, Order, TransactionAttempt, CheckoutLink
from ml.predict import predict_best_method

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_sample_key_id")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "sample_razorpay_secret_key")

def _get_razorpay_client():
    if RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith("rzp_test_sample"):
        return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    return None

def search_products(query: str) -> List[Dict[str, Any]]:
    """
    Search product catalog by name, category, or description query.
    Returns list of matching product dicts.
    """
    db = SessionLocal()
    try:
        q_lower = f"%{query.lower()}%"
        products = db.query(Product).filter(
            (Product.name.ilike(q_lower)) |
            (Product.category.ilike(q_lower)) |
            (Product.description.ilike(q_lower))
        ).all()
        return [p.to_dict() for p in products]
    finally:
        db.close()

def get_product(product_id: str) -> Dict[str, Any]:
    """
    Get detailed product information for a given product_id.
    """
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": f"Product with ID '{product_id}' not found."}
        return product.to_dict()
    finally:
        db.close()

def create_order(product_id: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Creates an order for a product with user context. Integrates with Razorpay Test Mode Orders API.
    """
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": f"Product with ID '{product_id}' not found."}

        ctx = user_context or {
            "device_type": "Android",
            "city_tier": "Tier 2",
            "network_type": "4G",
            "hour_of_day": datetime.now().hour,
            "past_failed_attempts": 0
        }

        order_id = f"ord_{uuid.uuid4().hex[:8]}"
        rzp_order_id = f"order_{uuid.uuid4().hex[:12]}"

        rzp_client = _get_razorpay_client()
        if rzp_client:
            try:
                rzp_order = rzp_client.order.create({
                    "amount": int(product.price * 100), # amount in paise
                    "currency": "INR",
                    "receipt": order_id,
                    "notes": {"internal_order_id": order_id, "initiated_by": "agent"}
                })
                rzp_order_id = rzp_order.get("id", rzp_order_id)
            except Exception as e:
                print(f"Razorpay Order creation API note: {e}")

        order = Order(
            id=order_id,
            razorpay_order_id=rzp_order_id,
            product_id=product.id,
            amount=product.price,
            currency=product.currency,
            status="created",
            user_context_json=json.dumps(ctx),
            offer_code=None,
            discount_amount=0.0,
            final_amount=product.price,
            initiated_by="agent"
        )
        db.add(order)
        db.commit()

        return order.to_dict()
    finally:
        db.close()

def apply_offer(order_id: str, offer_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Applies a promo/discount offer code to an order and updates final_amount.
    Supports model-driven dynamic discount selection if offer_code is 'AUTO' or None.
    Available explicit codes: WELCOME10 (10% off), AGENT20 (20% off), FESTIVE15 (15% off), AIHARVEST (25% off).
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"error": f"Order with ID '{order_id}' not found."}

        if offer_code and offer_code.upper() != "AUTO":
            code_upper = offer_code.upper().strip()
            discount_rates = {
                "WELCOME10": 0.10,
                "AGENT20": 0.20,
                "FESTIVE15": 0.15,
                "AIHARVEST": 0.25
            }

            if code_upper not in discount_rates:
                return {"error": f"Invalid offer code '{offer_code}'. Valid codes: {list(discount_rates.keys())} or 'AUTO'"}

            rate = discount_rates[code_upper]
            discount = round(order.amount * rate, 2)
            order.offer_code = code_upper
            order.discount_amount = discount
            order.final_amount = max(0.0, order.amount - discount)
        else:
            # Model-driven dynamic offer calculation (PART D Stretch Feature)
            # Evaluates price sensitivity based on cart amount, past failures, and city tier
            user_ctx = order.user_context
            amount = order.amount
            past_failures = int(user_ctx.get("past_failed_attempts", 0))
            city_tier = user_ctx.get("city_tier", "Tier 2")

            # High sensitivity / friction -> higher discount nudge to ensure conversion
            if past_failures >= 1 or (amount > 3000 and city_tier in ['Tier 2', 'Tier 3']):
                selected_code = "AGENT20"
                rate = 0.20
            elif amount > 1500:
                selected_code = "FESTIVE15"
                rate = 0.15
            else:
                selected_code = "WELCOME10"
                rate = 0.10

            discount = round(amount * rate, 2)
            order.offer_code = f"{selected_code}_AUTO"
            order.discount_amount = discount
            order.final_amount = max(0.0, amount - discount)

        order.updated_at = datetime.now(timezone.utc)
        db.commit()

        return order.to_dict()
    finally:
        db.close()

def get_checkout_link(order_id: str) -> Dict[str, Any]:
    """
    Generates Razorpay payment checkout link.
    Crucially: uses Conversion Intelligence Model to predict and rank payment methods,
    placing the method most likely to succeed FIRST in the ranked payment options.
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"error": f"Order with ID '{order_id}' not found."}

        cart = {"amount": order.final_amount}
        user_ctx = order.user_context

        # Use Part B Conversion Intelligence Model to rank payment methods
        ranked_methods = predict_best_method(cart, user_ctx)
        top_method = ranked_methods[0]['method'] if ranked_methods else "UPI"

        payment_url = f"https://api.razorpay.com/v1/checkout/test_link?order_id={order.id}&prefill_method={top_method}"
        rzp_link_id = f"plink_{uuid.uuid4().hex[:10]}"

        rzp_client = _get_razorpay_client()
        if rzp_client:
            try:
                plink = rzp_client.payment_link.create({
                    "amount": int(order.final_amount * 100),
                    "currency": "INR",
                    "accept_partial": False,
                    "description": f"AgentCheckout Order {order.id}",
                    "customer": {
                        "name": "Agent User",
                        "contact": "+919999999999",
                        "email": "agent@checkout.ai"
                    },
                    "notify": {"sms": False, "email": False},
                    "reminder_enable": False,
                    "notes": {
                        "internal_order_id": order.id,
                        "top_ranked_method": top_method
                    }
                })
                payment_url = plink.get("short_url", payment_url)
                rzp_link_id = plink.get("id", rzp_link_id)
            except Exception as e:
                print(f"Razorpay Payment Link API note: {e}")

        chk_link = CheckoutLink(
            id=f"chk_{uuid.uuid4().hex[:8]}",
            order_id=order.id,
            razorpay_payment_link_id=rzp_link_id,
            payment_url=payment_url,
            ranked_methods_json=json.dumps(ranked_methods),
            top_ranked_method=top_method
        )
        db.add(chk_link)
        db.commit()

        return {
            "order_id": order.id,
            "final_amount": order.final_amount,
            "payment_url": payment_url,
            "top_ranked_payment_method": top_method,
            "predicted_success_confidence": ranked_methods[0]['predicted_success_prob'],
            "all_ranked_payment_methods": ranked_methods,
            "status": order.status
        }
    finally:
        db.close()

def check_payment_status(order_id: str) -> Dict[str, Any]:
    """
    Checks payment status of an order. Reads directly from webhook-updated database state
    (event-driven) rather than polling Razorpay API on every call.
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"error": f"Order with ID '{order_id}' not found."}

        attempts = db.query(TransactionAttempt).filter(TransactionAttempt.order_id == order_id).all()
        attempt_list = [a.to_dict() for a in attempts]

        return {
            "order_id": order.id,
            "status": order.status, # created, paid, failed
            "final_amount": order.final_amount,
            "transaction_attempts": attempt_list,
            "last_updated": order.updated_at.isoformat() if order.updated_at else None,
            "read_source": "SQLite Webhook Event Database State"
        }
    finally:
        db.close()
