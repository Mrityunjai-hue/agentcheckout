"""
models.py - SQLAlchemy Database Models for AgentCheckout Storefront
"""

import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default='INR')
    stock_quantity = Column(Integer, default=100)
    image_url = Column(String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "price": self.price,
            "currency": self.currency,
            "stock_quantity": self.stock_quantity,
            "image_url": self.image_url
        }

class Order(Base):
    __tablename__ = 'orders'

    id = Column(String(50), primary_key=True)
    razorpay_order_id = Column(String(100), nullable=True)
    product_id = Column(String(50), ForeignKey('products.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='INR')
    status = Column(String(20), default='created') # created, paid, failed
    user_context_json = Column(Text, nullable=True)
    offer_code = Column(String(50), nullable=True)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    initiated_by = Column(String(20), default='agent') # agent vs human
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    product = relationship("Product")

    @property
    def user_context(self):
        if self.user_context_json:
            try:
                return json.loads(self.user_context_json)
            except Exception:
                return {}
        return {}

    @user_context.setter
    def user_context(self, val):
        self.user_context_json = json.dumps(val)

    def to_dict(self):
        return {
            "id": self.id,
            "razorpay_order_id": self.razorpay_order_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "user_context": self.user_context,
            "offer_code": self.offer_code,
            "discount_amount": self.discount_amount,
            "final_amount": self.final_amount,
            "initiated_by": self.initiated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class TransactionAttempt(Base):
    __tablename__ = 'transaction_attempts'

    id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey('orders.id'), nullable=False)
    razorpay_payment_id = Column(String(100), nullable=True)
    payment_method = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False) # captured, failed
    amount = Column(Float, nullable=False)
    error_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("Order")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "razorpay_payment_id": self.razorpay_payment_id,
            "payment_method": self.payment_method,
            "status": self.status,
            "amount": self.amount,
            "error_description": self.error_description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class CheckoutLink(Base):
    __tablename__ = 'checkout_links'

    id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey('orders.id'), nullable=False)
    razorpay_payment_link_id = Column(String(100), nullable=True)
    payment_url = Column(String(500), nullable=False)
    ranked_methods_json = Column(Text, nullable=False)
    top_ranked_method = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("Order")

    @property
    def ranked_methods(self):
        try:
            return json.loads(self.ranked_methods_json)
        except Exception:
            return []

    @ranked_methods.setter
    def ranked_methods(self, val):
        self.ranked_methods_json = json.dumps(val)

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "razorpay_payment_link_id": self.razorpay_payment_link_id,
            "payment_url": self.payment_url,
            "ranked_methods": self.ranked_methods,
            "top_ranked_method": self.top_ranked_method,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
