"""
server.py - AgentCheckout FastMCP Server & FastAPI Webhook Dispatcher
"""

import os
import sys
import uvicorn
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from sqlalchemy.orm import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_server.db import init_db, get_db
from mcp_server.models import Product, Order, TransactionAttempt
from mcp_server.webhook import router as webhook_router
import mcp_server.tools as mcp_tools

# Initialize FastMCP application
mcp = FastMCP("AgentCheckout Engine")

# Register MCP Tools
@mcp.tool()
def search_products(query: str) -> List[Dict[str, Any]]:
    """Search product catalog by query term."""
    return mcp_tools.search_products(query)

@mcp.tool()
def get_product(product_id: str) -> Dict[str, Any]:
    """Get detailed information for a specific product ID."""
    return mcp_tools.get_product(product_id)

@mcp.tool()
def create_order(product_id: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new Razorpay order for a product with user context."""
    return mcp_tools.create_order(product_id, user_context)

@mcp.tool()
def apply_offer(order_id: str, offer_code: Optional[str] = None) -> Dict[str, Any]:
    """Apply a promotional discount code to an existing order."""
    return mcp_tools.apply_offer(order_id, offer_code)

@mcp.tool()
def get_checkout_link(order_id: str) -> Dict[str, Any]:
    """Generate checkout link with payment methods ranked using Conversion ML Model."""
    return mcp_tools.get_checkout_link(order_id)

@mcp.tool()
def check_payment_status(order_id: str) -> Dict[str, Any]:
    """Check payment status reading from webhook-updated database state."""
    return mcp_tools.check_payment_status(order_id)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# Initialize FastAPI app for HTTP endpoints & Razorpay Webhooks
app = FastAPI(
    title="AgentCheckout MCP & Webhook Engine",
    description="Agentic Commerce Storefront & Payment Conversion Engine",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount webhook router
app.include_router(webhook_router, prefix="", tags=["Webhooks"])

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AgentCheckout MCP & Webhook Engine",
        "mcp_tools_count": 6
    }

@app.get("/api/products")
def list_products_api(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [p.to_dict() for p in products]

@app.get("/api/orders")
def list_orders_api(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return [o.to_dict() for o in orders]

@app.get("/api/transactions")
def list_transactions_api(db: Session = Depends(get_db)):
    txs = db.query(TransactionAttempt).order_by(TransactionAttempt.created_at.desc()).all()
    return [t.to_dict() for t in txs]

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting AgentCheckout FastAPI Server on http://{host}:{port}...")
    uvicorn.run("mcp_server.server:app", host=host, port=port, reload=True)
