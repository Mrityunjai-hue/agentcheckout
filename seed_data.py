"""
seed_data.py - Database Seeding Script for AgentCheckout

Populates SQLite database with product catalog and initial sample historical transactions
for immediate demo readiness.
"""

import os
import sys
import random
import uuid
import json
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from mcp_server.db import init_db, SessionLocal
from mcp_server.models import Product, Order, TransactionAttempt, CheckoutLink

PRODUCTS = [
    {
        "id": "prod_101",
        "name": "UltraSlim Noise-Canceling Headphones",
        "description": "Premium wireless over-ear headphones with active noise cancellation and 40h battery.",
        "category": "Electronics",
        "price": 4999.0,
        "currency": "INR",
        "stock_quantity": 45,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"
    },
    {
        "id": "prod_102",
        "name": "Smart Fitness Watch Gen 4",
        "description": "AMOLED display watch with SpO2 monitoring, GPS, and multi-sport tracking.",
        "category": "Electronics",
        "price": 2999.0,
        "currency": "INR",
        "stock_quantity": 80,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"
    },
    {
        "id": "prod_103",
        "name": "Ergonomic Mesh Office Chair",
        "description": "High-back ergonomic office chair with adjustable lumbar support and 3D armrests.",
        "category": "Furniture",
        "price": 8499.0,
        "currency": "INR",
        "stock_quantity": 25,
        "image_url": "https://images.unsplash.com/photo-1580481072645-022f9a6d83d0?w=500"
    },
    {
        "id": "prod_104",
        "name": "Organic Arabica Coffee Beans (1kg)",
        "description": "Whole bean single-origin roasted Arabica coffee beans from Chikmagalur.",
        "category": "Grocery",
        "price": 899.0,
        "currency": "INR",
        "stock_quantity": 150,
        "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500"
    },
    {
        "id": "prod_105",
        "name": "Minimalist Leather Backpack",
        "description": "Full-grain genuine leather laptop backpack with water-resistant lining.",
        "category": "Accessories",
        "price": 1899.0,
        "currency": "INR",
        "stock_quantity": 60,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500"
    },
    {
        "id": "prod_106",
        "name": "Mechanical Gaming Keyboard RGB",
        "description": "Hot-swappable mechanical keyboard with custom tactile switches.",
        "category": "Electronics",
        "price": 3499.0,
        "currency": "INR",
        "stock_quantity": 35,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500"
    }
]

def seed_database():
    print("Initializing SQLite database tables...")
    init_db()

    db = SessionLocal()
    try:
        # Seed Products
        print("Seeding catalog products...")
        for p_data in PRODUCTS:
            existing = db.query(Product).filter(Product.id == p_data["id"]).first()
            if not existing:
                prod = Product(**p_data)
                db.add(prod)
        db.commit()

        # Check if existing orders exist
        existing_orders_cnt = db.query(Order).count()
        if existing_orders_cnt < 20:
            print("Seeding sample historical orders and transactions for funnel analytics...")
            devices = ['Android', 'iOS', 'Desktop']
            city_tiers = ['Tier 1', 'Tier 2', 'Tier 3']
            networks = ['4G', '5G', 'Wifi', '3G']
            methods = ['UPI', 'Card', 'Netbanking', 'Wallet', 'PayLater']

            now = datetime.now(timezone.utc)

            for i in range(50):
                prod = random.choice(PRODUCTS)
                is_agent = random.random() < 0.65 # 65% agent-initiated, 35% human-initiated
                status = random.choices(['paid', 'failed', 'created'], weights=[0.72, 0.20, 0.08])[0]

                dt = now - timedelta(hours=random.randint(1, 168))

                order_id = f"ord_{1000 + i}"
                user_ctx = {
                    "device_type": random.choice(devices),
                    "city_tier": random.choice(city_tiers),
                    "network_type": random.choice(networks),
                    "hour_of_day": dt.hour,
                    "past_failed_attempts": random.choice([0, 0, 0, 1, 2])
                }

                discount = 0.0
                offer_code = None
                if random.random() < 0.3:
                    offer_code = random.choice(['WELCOME10', 'AGENT20', 'FESTIVE15'])
                    discount = round(prod['price'] * 0.10, 2)

                order = Order(
                    id=order_id,
                    razorpay_order_id=f"order_rzp_{uuid.uuid4().hex[:10]}",
                    product_id=prod['id'],
                    amount=prod['price'],
                    currency='INR',
                    status=status,
                    user_context_json=json.dumps(user_ctx),
                    offer_code=offer_code,
                    discount_amount=discount,
                    final_amount=max(0.0, prod['price'] - discount),
                    initiated_by='agent' if is_agent else 'human',
                    created_at=dt,
                    updated_at=dt
                )
                db.add(order)

                if status in ['paid', 'failed']:
                    tx_status = 'captured' if status == 'paid' else 'failed'
                    tx = TransactionAttempt(
                        id=f"tx_{2000 + i}",
                        order_id=order_id,
                        razorpay_payment_id=f"pay_rzp_{uuid.uuid4().hex[:10]}",
                        payment_method=random.choice(methods),
                        status=tx_status,
                        amount=order.final_amount,
                        error_description=None if tx_status == 'captured' else 'Bank server timeout / OTP verification failed',
                        created_at=dt + timedelta(seconds=15)
                    )
                    db.add(tx)

            db.commit()
            print("Successfully seeded 50 historical orders & transactions.")
        else:
            print(f"Database already contains {existing_orders_cnt} orders. Skipping sample order seeding.")

    finally:
        db.close()

if __name__ == '__main__':
    seed_database()
