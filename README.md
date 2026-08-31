# Pulse & Co. — Agentic Commerce on Razorpay

Built for the **AI Growth & Agentic Commerce** brief: grow a merchant's revenue and make the merchant
transactable by an AI buyer, on Razorpay test-mode APIs, with every money action explainable, bounded, and
gated.

It combines all four example directions into one coherent app rather than four separate demos:

- **Conversational in-app checkout** — a [Strands](https://github.com/strands-agents/sdk-python) agent with
  catalog/cart/checkout tools, presented as a ChatGPT-style shopping assistant. Catalog search
  (`agents/search.py`) ranks by keyword relevance across title/description/category/tags, not a single
  substring match - closer to a normal e-commerce search box than a toy demo.
- **Agent-readable catalog** — a machine-readable product feed and discovery manifest
  (`/.well-known/agentic-commerce.json`), in the spirit of ACP/AP2/x402.
- **Upsell & cross-sell agent** — the checkout agent suggests complementary products from the cart, via a
  `get_upsell_suggestions` tool backed by a catalog complements graph.
- **Campaign orchestrator** — a Strands agent drafts honest offer copy for a growth campaign; a
  deterministic policy engine computes recipients and discount exposure and gates the launch.
- **AI buyer simulator** — an unauthenticated endpoint an external AI shopping agent could hit end to end
  (search → cart → checkout), demonstrating the merchant is transactable by an AI buyer with no human in
  the loop.

## The bar: explainable, bounded, gated

Every money-moving action (`checkout`, `launch_campaign_batch`) goes through a two-layer **gatekeeper**
(`backend/app/gatekeeper/`) before it's allowed to touch Razorpay:

1. **Hard bounds** (`policy.py`) — deterministic, code-enforced limits (max order amount, max discount %,
   max orders per session, daily campaign budget, max campaign recipients). These hold even with zero LLM
   configured.
2. **LLM-as-gatekeeper** (`gatekeeper.py`) — a *separate* Strands agent, independent from whichever agent
   proposed the action, reviews it for context a rule can't capture (misleading copy, abusive patterns) and
   returns a structured allow/deny + reason. It fails **closed**: if the LLM errors, the action is denied.

Every gatekeeper decision — allowed or denied — is written to the **audit trail** (`/audit`, seller-only in
the UI) with the actor, the reasoning, the policy references, and before/after state.

## Payments, invoices, and failures

Since this is fundamentally a payments app, the payment lifecycle gets first-class treatment, not just a
pass/fail flag:

- **Orders are the transaction log.** A retry after a failed payment creates a *new* order/payment link
  rather than overwriting the old one (`backend/app/agents/tools.py` - the cart is only cleared once a
  payment is confirmed `paid`, specifically so a failure doesn't lose the cart). So `/orders` (seller) and
  `/my/orders` (customer) already show every attempt, successful and failed, in order.
- **Failures are specific, never generic.** `backend/app/payment_failures.py` is a small catalog of
  realistic decline reasons (insufficient funds, declined by issuer, expired card, incorrect OTP, bank
  timeout) - each with a plain-language reason *and* a concrete remedy. A failed order carries its
  `failure_code`/`failure_reason`/`failure_remedy`, and the Chat, My Orders, and Orders pages all surface
  it (no order in this app is ever just "failed").
- **Invoices are issued exactly once, only on confirmed payment.** `backend/app/invoicing.py` issues a
  sequential invoice (`INV-2026-00001`, ...) with a GST-style subtotal/tax breakdown the moment
  `/payments/simulate` reports `paid`; it's idempotent (a duplicate confirmation returns the existing
  invoice instead of double-billing). Viewable/printable from the Chat page right after payment, or later
  from My Orders / Orders (`components/InvoiceView.tsx`, has a working Print/Save-as-PDF button).

**Two built-in graceful failures to try:**
- Campaigns page → set a discount above the configured cap (default 40%) → gatekeeper denies it with a
  plain-language reason, shown in the UI instead of a stack trace.
- Checkout Chat → after a checkout is approved, pick a decline scenario (e.g. "Insufficient funds") and
  click "Simulate decline" → you get the specific reason and remedy, the cart is preserved, and saying
  "try again" gets a fresh payment link without rebuilding the cart.

## Two logins, two home pages

- **Customer** (`/login/customer`) → lands on the ChatGPT-style shopping assistant (`/chat`). Ask for
  what you want in plain language; the agent searches the catalog and returns product cards inline. Past
  orders and invoices live at `/my-orders`.
- **Seller** (`/login/seller`) → lands on the merchant dashboard (`/dashboard`): revenue, campaign
  activity, and gatekeeper decisions. The full transaction log (all orders, invoices, failure reasons)
  lives at `/orders`.

Auth is JWT-based (`backend/app/auth.py`), two disjoint token scopes — a customer token cannot open seller
endpoints and vice versa (checked by role claim, not just signature validity). The catalog, the
`.well-known` manifest, and `/ai-buyer/purchase` are intentionally **unauthenticated** — that's the public,
agent-facing surface an external AI buyer must be able to reach without a human login.

**Demo credentials** (seeded on first run):
- Customer: `ananya.rao@example.com` / `customer123` (or any other seeded customer, same password)
- Seller: `merchant@pulseandco.test` / `merchant123`

## Architecture

```
backend/                     FastAPI + SQLAlchemy (SQLite) + Strands Agents
  app/
    agents/                  checkout_agent, campaign_agent, ai_buyer + shared tools.py + search.py
    gatekeeper/               policy.py (hard bounds) + gatekeeper.py (LLM review)
    llm/model_factory.py      pluggable model provider (Anthropic or OpenAI, via Strands)
    razorpay_adapter/         MockGateway (default, no keys needed) / LiveGateway (real test-mode API)
    invoicing.py              idempotent invoice issuance with GST subtotal/tax breakdown
    payment_failures.py       catalog of realistic decline codes -> reason + remedy
    routers/                  catalog, chat, campaigns, ai_buyer, audit, orders, invoices, stats, auth
    auth.py                   JWT issuance/verification, get_current_customer / get_current_seller
    models.py, schemas.py, seed.py, main.py

frontend/                    React + TypeScript + Vite
  src/
    pages/                   Landing, CustomerLogin, SellerLogin, Chat, MyOrders, AIBuyer,
                              Dashboard, Orders, Campaigns, Audit
    auth.tsx                 AuthContext - separate customer/seller tokens, persisted in localStorage
    components/               Layout, RequireAuth guards, RevenueChart, ProductCard, TraceView, InvoiceView
```

Every agent (checkout, campaign, AI buyer, and the gatekeeper) is a Strands `Agent`. The LLM provider is
swappable via `LLM_PROVIDER=anthropic|openai` in `backend/.env` — no agent code changes required. Razorpay
is behind the same kind of seam: `RAZORPAY_MODE=mock` (default, fully working with zero keys) or `live`
(real test-mode API via the official SDK) — the agents and gatekeeper never know which one is active.

## Running it

### Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then add an LLM key - see below
uvicorn app.main:app --reload --port 8000
```

The database is a local SQLite file, created and seeded automatically on first run.

**You need one LLM key** for the agents to actually respond (chat, campaigns, AI buyer, and the LLM half of
the gatekeeper). Everything else — catalog, auth, the audit trail, the rule-based half of the gatekeeper —
works with zero keys. In `backend/.env`:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

or

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Razorpay stays in mock mode until you add test-mode keys:

```env
RAZORPAY_MODE=live
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env    # defaults to http://localhost:8000, fine for local dev
npm run dev
```

Open `http://localhost:5173`.

## Known simplifications (hackathon scope)

- Chat conversation history is kept in-process (not persisted to disk) — it resets if the backend restarts.
- "Payment succeeded/failed" in the UI is a demo simulate button (`POST /payments/simulate`) rather than a
  real Razorpay Checkout redirect, since mock mode has no real card flow. In live mode this endpoint just
  reports the payment link's true current status instead of forcing an outcome.
- Single merchant, single catalog - multi-tenant merchant onboarding is out of scope.
