# FlowState — Agentic Commerce on Razorpay

Built for the **AI Growth & Agentic Commerce** brief: grow a merchant's revenue and make the merchant
transactable by an AI buyer, on Razorpay test-mode APIs, with every money action explainable, bounded, and
gated.

It combines all four example directions into one coherent app rather than four separate demos, plus a
trust layer (gatekeeper + audit trail) that applies uniformly to all of them. A full breakdown of how each
brief requirement maps to a real, working feature — with a system diagram — is on the in-app
**[`/architecture`](http://localhost:5173/architecture)** page once it's running.

- **Conversational in-app checkout** — a [Strands](https://github.com/strands-agents/sdk-python) agent with
  catalog/cart/checkout tools, presented as a ChatGPT-style shopping assistant. Catalog search
  (`agents/search.py`) ranks by keyword relevance across title/description/category/tags, not a single
  substring match - closer to a normal e-commerce search box than a toy demo.
- **Agent-readable catalog** — a machine-readable product feed and discovery manifest
  (`/.well-known/agentic-commerce.json`), in the spirit of ACP/AP2/x402.
- **Upsell & cross-sell agent** — the checkout agent suggests complementary products from the cart, via a
  `get_upsell_suggestions` tool backed by a catalog complements graph.
- **Campaign orchestrator** — a Strands agent drafts honest offer copy for a growth campaign; a
  deterministic policy engine computes recipients and discount exposure and gates the launch. A launched
  campaign sends a real payment link directly to each targeted customer *and* applies that customer's
  discount automatically the moment they show up in chat, so either path — clicking the link, or just
  chatting — leads to a checkout. When a sale closes at a live campaign's price, the resulting order is
  attributed to `campaign_agent` in revenue reporting (not to whichever agent happened to place the call),
  so campaign-driven revenue is a real, queryable number, not a cosmetic label.
- **AI buyer simulator** — an unauthenticated endpoint an external AI shopping agent could hit end to end
  (search → cart → checkout → autonomous payment confirmation via an x402-style handshake), demonstrating
  the merchant is transactable by an AI buyer with no human in the loop.

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
the UI) with the actor, the reasoning, the policy references, and before/after state. The bounds apply the
same way regardless of who's transacting: a human in Checkout Chat and the autonomous AI Buyer hit the
identical `checkout()` tool and the identical ₹5,000-per-order cap — denial and recovery both work the same
on either surface.

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
  invoice instead of double-billing), and the sequence number is derived from the highest issued number
  rather than a row count, so it can't collide if a row is ever removed. Viewable/printable from the Chat
  page right after payment, or later from My Orders / Orders (`components/InvoiceView.tsx`, has a working
  Print/Save-as-PDF button).

**Two built-in graceful failures to try:**
- Campaigns page → set a discount above the configured cap (default 40%) → gatekeeper denies it with a
  plain-language reason, shown in the UI instead of a stack trace.
- Checkout Chat or AI Buyer → try to check out an order over ₹5,000 → the gatekeeper denies it with a warm,
  specific explanation of the cap and an offer to fix the cart, not a generic error - the same cap, the
  same message shape, on both the human and the autonomous-agent checkout path. (Checkout Chat also has a
  manual decline-scenario button - pick a reason like "Insufficient funds" after an approved checkout and
  the cart is preserved for a one-message retry.)

## Trust and visibility, beyond the gatekeeper

- **Dashboard** (`/dashboard`, seller) — revenue by day, by channel (list + pie chart), and by customer
  (table, highest-spend first); a conversion funnel (attempted → approved → paid) broken out by channel;
  and a gatekeeper decisions pie chart (allowed vs. denied) alongside the raw audit feed. Every number on
  it is a live query over real `Order`/`Campaign`/`AuditLogEntry` rows, not a static mock.
- **Real product photography, served locally.** All 25 catalog items have a real product photo
  (`backend/product_images/<SKU>.jpg`), served from this backend at `/static/product_images/` — no
  LoremFlickr or other external image CDN in the loop, so the storefront still looks right with zero
  network access beyond this app and the LLM provider.

## Two logins, two home pages

- **Customer** (`/login/customer`) → lands on the ChatGPT-style shopping assistant (`/chat`). Ask for
  what you want in plain language; the agent searches the catalog and returns product cards inline. Past
  orders and invoices live at `/my-orders`.
- **Seller** (`/login/seller`) → lands on the merchant dashboard (`/dashboard`): revenue, campaign
  activity, and gatekeeper decisions. The full transaction log (all orders, invoices, failure reasons)
  lives at `/orders`.

Auth is JWT-based (`backend/app/auth.py`), two disjoint token scopes — a customer token cannot open seller
endpoints and vice versa (checked by role claim, not just signature validity). The catalog, the
`.well-known` manifest, `/architecture`, and `/ai-buyer/purchase` are intentionally **unauthenticated** —
the last one is the public, agent-facing surface an external AI buyer must be able to reach without a human
login.

**Demo credentials** (seeded on first run - all customer accounts share the same password):

| Name | Email | Password | Segment |
| --- | --- | --- | --- |
| Kabir Shah | `kabir.shah@example.com` | `customer123` | new |
| Priya Nair | `priya.nair@example.com` | `customer123` | new |
| Rohit Verma | `rohit.verma@example.com` | `customer123` | repeat |
| Meera Iyer | `meera.iyer@example.com` | `customer123` | repeat |
| Ananya Rao | `ananya.rao@example.com` | `customer123` | vip |
| Sara Khan | `sara.khan@example.com` | `customer123` | vip |
| Devansh Gupta | `devansh.gupta@example.com` | `customer123` | lapsed |
| Arjun Menon | `arjun.menon@example.com` | `customer123` | lapsed |

Segment matters for campaigns - a campaign targets one segment (e.g. "vip"), so which customer you log in
as determines whether you'll see that campaign's discount applied automatically in chat.

| Role | Email | Password |
| --- | --- | --- |
| Seller | `merchant@flowstate.test` | `merchant123` |

## Architecture

```
backend/                     FastAPI + SQLAlchemy (SQLite) + Strands Agents
  app/
    agents/                  checkout_agent, campaign_agent, ai_buyer + shared tools.py + search.py
    gatekeeper/               policy.py (hard bounds) + gatekeeper.py (LLM review)
    llm/
      model_factory.py        pluggable model provider (ollama/groq/gemini/openai/anthropic via Strands)
      fallback_model.py        sticky Groq-key rotation -> Anthropic fallback (see below)
    campaign_pricing.py       resolves a customer's live campaign discount at chat/checkout time
    razorpay_adapter/         MockGateway (default, no keys needed) / LiveGateway (real test-mode API)
    invoicing.py              idempotent invoice issuance with GST subtotal/tax breakdown
    payment_failures.py       catalog of realistic decline codes -> reason + remedy
    product_images/           real photo per SKU, served at /static/product_images/
    routers/                  catalog, chat, campaigns, ai_buyer, audit, orders, invoices, stats, auth
    auth.py                   JWT issuance/verification, get_current_customer / get_current_seller
    models.py, schemas.py, seed.py, main.py

frontend/                    React + TypeScript + Vite
  src/
    pages/                   Landing, CustomerLogin, SellerLogin, Chat, MyOrders, AIBuyer, Architecture,
                              Dashboard, Orders, Campaigns, Audit
    auth.tsx                 AuthContext - separate customer/seller tokens, persisted in localStorage
    components/               Layout, RequireAuth guards, RevenueChart, PieStatChart, FunnelChart,
                              ProductCard, ProductThumb, TraceView, InvoiceView, PaymentMethodPanel
```

Every agent (checkout, campaign, AI buyer, and the gatekeeper) is a Strands `Agent`. The LLM provider is
swappable via `LLM_PROVIDER=ollama|groq|gemini|openai|anthropic` in `backend/.env` — no agent code changes
required. Razorpay is behind the same kind of seam: `RAZORPAY_MODE=mock` (default, fully working with zero
keys) or `live` (real test-mode API via the official SDK) — the agents and gatekeeper never know which one
is active.

**Multi-provider LLM fallback.** Groq's free tier is fast but rate-limited (a shared daily token cap per
key). Set `LLM_PROVIDER=groq` with one or more `GROQ_API_KEY`/`GROQ_API_KEY_2`/`_3`/`_4` plus an
`ANTHROPIC_API_KEY`, and `backend/app/llm/fallback_model.py` chains them: a throttled key rotates to the
next Groq key in order, and once every Groq key is throttled, falls over to Anthropic - automatically, per
request, with no code change or restart. The rotation is **sticky**: once a key is seen throttled, later
requests skip straight past it instead of re-trying a key that's still going to be dead, so a degraded
provider doesn't also mean a slow one. It only ever triggers on a genuine rate-limit signal
(`ModelThrottledException`), never on a real error, and never splices a partial response from one provider
with another's - a mid-stream failure is raised as-is rather than silently patched over.

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
the gatekeeper). Everything else — catalog, product images, auth, the audit trail, the rule-based half of
the gatekeeper — works with zero keys. `LLM_PROVIDER` defaults to `ollama` (fully local, zero keys, as long
as `ollama serve` is running). To use a hosted provider instead, in `backend/.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
# optional: GROQ_API_KEY_2 / _3 / _4, plus ANTHROPIC_API_KEY as the eventual fallback
```

or simply

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
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
  reports the payment link's true current status instead of forcing an outcome. The AI Buyer's "payment
  panel" step is the same kind of simulated beat, made visible on purpose so the autonomous handshake is
  something a viewer can actually see happen, rather than an instant jump to "done."
- Single merchant, single catalog - multi-tenant merchant onboarding is out of scope.
