# 🎙️ AgentCheckout — 5-Minute Buildathon Demo Script

**Track 1: AI Growth & Agentic Commerce**  
**Target Audience:** Razorpay AI Buildathon Judges & Technical Panel  
**Demo Duration:** 5 Minutes  
🌐 **Live Cloud Dashboard:** [https://agentcheckout-dashboard.onrender.com/](https://agentcheckout-dashboard.onrender.com/)

---

## Timeline Overview

| Minute | Phase | Core Message / Screen Action |
| :---: | :--- | :--- |
| **0:00 - 0:45** | **The Problem & Growth Hook** | Traditional checkout vs Agentic Commerce friction; Growth vs Recovery framing. |
| **0:45 - 2:00** | **Live MCP Agent Commerce Walkthrough** | Agent browsing catalog -> creating order -> applying discount -> ML ranking checkout. |
| **2:00 - 3:15** | **Conversion Intelligence & Uplift (+69.57%)** | Showing offline uplift simulation, model metrics, feature importance, and live predictor. |
| **3:15 - 4:15** | **Event-Driven Webhook Architecture** | Demonstrating `payment.captured` HMAC SHA-256 signature verification & SQLite state. |
| **4:15 - 5:00** | **Conclusion & Q&A Defense** | Summarizing impact; answering potential judge questions. |

---

## Detailed Minute-by-Minute Script

### ⏱️ Minute 0:00 – 0:45: The Problem & Growth Hook
*(Screen showing Streamlit Dashboard Main Header or Slide 1)*

**Verbal Pitch:**
> "Good morning judges! We are presenting **AgentCheckout** — an agent-native commerce and payment conversion ranking engine built for Razorpay.
> 
> Here is the core insight: As AI agents increasingly make purchases on behalf of humans, checkout friction drops conversion dramatically if payment options are ordered randomly or statically. Most fintech projects focus on *Revenue Recovery* — trying to salvage dropped payments *after* failure. 
> 
> **AgentCheckout is an AI Growth engine.** We optimize live, first-attempt conversion *before* payment occurs. By predicting which payment method is most likely to succeed for a specific user's context — their device, city tier, network speed, and past failures — our system pre-selects and ranks that optimal method top, driving measurable top-line growth."

---

### ⏱️ Minute 0:45 – 2:00: Live MCP Agent Commerce Walkthrough
*(Switch screen to Streamlit Dashboard -> Tab 3: Live Agent Replay)*

**Verbal Pitch:**
> "Let's watch an AI agent complete a live transaction end-to-end through our FastMCP server.
> *(Click 'Run Live End-to-End Agent Purchase Demo')*
> 
> 1. First, the agent calls `search_products('Headphones')` and finds our UltraSlim Noise-Canceling Headphones.
> 2. Next, it calls `create_order` passing the user's contextual metadata — Android device, Tier 2 city, 4G network.
> 3. It automatically applies a promo offer `WELCOME10` via `apply_offer`, bringing the final price from ₹4,999 down to ₹4,499.10.
> 4. Now, watch what happens when the agent calls `get_checkout_link`. Instead of returning a static link, our Conversion Intelligence ML model evaluates all payment methods for this user's context. It discovers UPI has a **94.2% predicted success probability**, while Card has only 54.8% due to OTP network timeouts on 4G. It places **UPI FIRST** in the Razorpay payment link.
> 5. The payment link is returned instantly to the agent!"

---

### ⏱️ Minute 2:00 – 3:15: Conversion Intelligence & Uplift (+69.57%)
*(Switch screen to Streamlit Dashboard -> Tab 2: Conversion Uplift & ML)*

**Verbal Pitch:**
> "Does method reordering actually move the needle? Let's look at the data.
> 
> We trained a `GradientBoostingClassifier` with SMOTE class balancing on a published Kaggle UPI transaction distribution of 12,000 Indian transactions.
> 
> In our offline simulation on a held-out test split of 2,400 transactions:
> - **Legacy Fixed Order (Card First)** achieved a conversion rate of **50.61%**.
> - **AgentCheckout Model-Ranked Order** achieved a conversion rate of **85.82%**.
> - That is an **absolute gain of +35.21% percentage points** and a **relative conversion uplift of +69.57%**!
> 
> Our feature importance panel reveals *why*: Network speed, past failure count, and device type are major predictors of whether 3-D Secure OTP vs. UPI intent flow succeeds."

---

### ⏱️ Minute 3:15 – 4:15: Event-Driven Webhook Architecture
*(Point to Webhook Verification Log in Tab 3 / terminal)*

**Verbal Pitch:**
> "Next, notice how status verification works. Most naive agent implementations poll the payment gateway repeatedly.
> 
> AgentCheckout is a true **event-driven system**. When a transaction completes, Razorpay dispatches a POST to our `/webhook` endpoint. We verify Razorpay's **HMAC SHA-256 signature** (`X-Razorpay-Signature`) using `RAZORPAY_WEBHOOK_SECRET`. Once verified, the webhook updates the SQLite database transaction record.
> 
> When the agent later calls `check_payment_status(order_id)`, it reads directly from this webhook-updated local state in milliseconds without hammering Razorpay's API."

---

### ⏱️ Minute 4:15 – 5:00: Summary & Q&A Defense
*(Switch to Dashboard Summary or Architecture Diagram)*

**Verbal Pitch:**
> "To summarize: AgentCheckout delivers:
> 1. A complete FastMCP storefront exposing 6 tools.
> 2. An event-driven Razorpay test-mode integration with HMAC signature verification.
> 3. A trained Conversion Intelligence ML model delivering **+69.57% relative uplift**.
> 4. A 3-page Streamlit Growth Dashboard.
> 
> Thank you, and I am happy to take your questions!"

---

## 🛡️ Q&A Defense Cheatsheet for Judges

### Q1: "Is the dataset real transaction data?"
> **Answer:** "We are completely transparent about data provenance: we used the Kaggle UPI Payment Transactions Benchmark 2024 distribution, which is an independently published benchmark statistically modeled on NPCI/RBI statistics. We deliberately chose an independently published open benchmark over writing our own synthetic generator to eliminate author bias while maintaining India-specific payment domain fit."

### Q2: "Why is this Growth and not Revenue Recovery?"
> **Answer:** "Revenue Recovery acts reactively *after* a payment fails. AgentCheckout acts proactively *before* payment initiation by placing the single payment method least likely to fail right at the top of the user's payment link, preventing failure upfront."

### Q3: "How does the webhook signature verification work?"
> **Answer:** "We compute `hmac.new(secret, raw_body, sha256).hexdigest()` on the incoming webhook payload and perform a constant-time comparison against `X-Razorpay-Signature` using `hmac.compare_digest`."
