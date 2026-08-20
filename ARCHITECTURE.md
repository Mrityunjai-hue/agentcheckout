# System Architecture & Technical Specifications — AgentCheckout

## 1. Overview

AgentCheckout is designed around three core architectural pillars:
1. **Agent-Native Storefront (MCP Server)**: An interface built using FastMCP and FastAPI that allows LLM agents to inspect catalogs, construct orders, apply offers, and retrieve conversion-optimized checkout links.
2. **Conversion Intelligence Engine (ML)**: A predictive machine-learning engine trained on public UPI transaction distributions that scores payment success probability per user context and ranks payment methods optimally.
3. **Event-Driven Webhook Processor**: An asynchronous webhook receiver (`POST /webhook`) that validates Razorpay HMAC-SHA256 signatures, updates order statuses in SQLite, and provides true event-driven status tracking for agents.

---

## 2. Component Specifications

### 2.1 Part A: Storefront & Webhook Engine (`mcp_server/`)

#### MCP Tool Definitions (`tools.py`)
- `search_products(query: str) -> list[dict]`: Case-insensitive search across product name, category, and description.
- `get_product(product_id: str) -> dict`: Returns full product specifications and inventory availability.
- `create_order(product_id: str, user_context: dict) -> dict`: Instantiates an `Order` record, extracts user contextual signals (device type, city tier, network speed, hour of day), and integrates with Razorpay Orders API.
- `apply_offer(order_id: str, offer_code: str | None) -> dict`: Applies promotional codes (`WELCOME10`, `AGENT20`, `FESTIVE15`, `AIHARVEST`), recalculating order `final_amount`.
- `get_checkout_link(order_id: str) -> dict`: Queries `predict_best_method` from the ML model, ranks payment methods descending by predicted success probability, places the highest-probability method first, and creates a Razorpay Payment Link.
- `check_payment_status(order_id: str) -> dict`: Reads payment outcome from the local event-driven SQLite database updated by Razorpay webhooks.

#### Razorpay Webhook Event Handler (`webhook.py`)
- **Route**: `POST /webhook`
- **Header**: `X-Razorpay-Signature`
- **HMAC Verification**:
  ```python
  generated_sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
  is_valid = hmac.compare_digest(generated_sig, x_razorpay_signature)
  ```
- **Events Handled**:
  - `payment.captured`: Sets `order.status = 'paid'` and creates `TransactionAttempt(status='captured')`.
  - `payment.failed`: Sets `order.status = 'failed'` and creates `TransactionAttempt(status='failed', error_description=...)`.

---

## 3. Database Schema

SQLite Database located at `data/agentcheckout.db`:

```sql
CREATE TABLE products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    price FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    stock_quantity INTEGER DEFAULT 100,
    image_url VARCHAR(255)
);

CREATE TABLE orders (
    id VARCHAR(50) PRIMARY KEY,
    razorpay_order_id VARCHAR(100),
    product_id VARCHAR(50) REFERENCES products(id),
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    status VARCHAR(20) DEFAULT 'created',
    user_context_json TEXT,
    offer_code VARCHAR(50),
    discount_amount FLOAT DEFAULT 0.0,
    final_amount FLOAT NOT NULL,
    initiated_by VARCHAR(20) DEFAULT 'agent',
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE transaction_attempts (
    id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) REFERENCES orders(id),
    razorpay_payment_id VARCHAR(100),
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    amount FLOAT NOT NULL,
    error_description TEXT,
    created_at DATETIME
);

CREATE TABLE checkout_links (
    id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) REFERENCES orders(id),
    razorpay_payment_link_id VARCHAR(100),
    payment_url VARCHAR(500) NOT NULL,
    ranked_methods_json TEXT NOT NULL,
    top_ranked_method VARCHAR(50) NOT NULL,
    created_at DATETIME
);
```

---

## 4. Part B: Conversion Intelligence ML Architecture (`ml/`)

### Feature Pipeline
- Categorical features: `payment_method`, `device_type`, `city_tier`, `network_type`, `amount_bucket` (One-Hot Encoded).
- Numeric features: `hour_of_day`, `past_failed_attempts`, `amount` (Standard Scaled).

### Classifier & Imbalance Strategy
- Algorithm: `GradientBoostingClassifier` (scikit-learn).
- Imbalance Strategy: **SMOTE (Synthetic Minority Over-sampling Technique)** via `imbalanced-learn`.
- Outcome: Handles class imbalance while maintaining high precision (87.02%) and recall (84.59%).

### Offline Uplift Simulation Methodology
- Held-out test split (2,400 transactions).
- Baseline: Legacy fixed method order (Card shown first).
- Model-Ranked: Dynamic best method predicted per user context shown first.
- Relative Uplift:
  $$\text{Relative Uplift \%} = \frac{\text{Model Conv Rate} - \text{Baseline Conv Rate}}{\text{Baseline Conv Rate}} \times 100$$
- Result: **+69.57% Relative Uplift** (+35.21% absolute percentage points increase).
