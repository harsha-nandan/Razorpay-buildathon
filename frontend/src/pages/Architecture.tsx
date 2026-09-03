export default function Architecture() {
  return (
    <div>
      <div className="page-header">
        <h1>Architecture</h1>
        <p>How a money action actually flows through this app, and where each Track 1 requirement is satisfied.</p>
      </div>

      <div className="card">
        <div className="section-title">System diagram</div>
        <div className="arch-diagram">
          <div className="arch-tier-label">Frontend</div>
          <div className="arch-row">
            <div className="arch-box">
              <div className="arch-box-title">Checkout Chat</div>
              <div className="arch-box-sub">ChatGPT-style shopping assistant · /chat</div>
            </div>
            <div className="arch-box">
              <div className="arch-box-title">Seller Dashboard</div>
              <div className="arch-box-sub">Revenue, campaigns, gatekeeper decisions · /dashboard, /campaigns</div>
            </div>
            <div className="arch-box">
              <div className="arch-box-title">AI Buyer Simulator</div>
              <div className="arch-box-sub">Unauthenticated, agent-facing · /ai-buyer</div>
            </div>
          </div>

          <div className="arch-arrow">↓</div>
          <div className="arch-arrow-note">each surface talks to its own Strands agent, sharing the same cart/checkout tools</div>

          <div className="arch-tier-label">Backend agents (Strands)</div>
          <div className="arch-row">
            <div className="arch-box">
              <div className="arch-box-title">checkout_agent</div>
              <div className="arch-box-sub">search · cart · upsell · checkout</div>
            </div>
            <div className="arch-box">
              <div className="arch-box-title">campaign_agent</div>
              <div className="arch-box-sub">drafts offer copy · sends payment links</div>
            </div>
            <div className="arch-box">
              <div className="arch-box-title">ai_buyer</div>
              <div className="arch-box-sub">same tools, autonomous, no login</div>
            </div>
          </div>

          <div className="arch-arrow">↓</div>
          <div className="arch-arrow-note">every money-moving call (checkout, launch_campaign_batch) is proposed to the gatekeeper before it can touch Razorpay</div>

          <div className="arch-tier-label">Gatekeeper</div>
          <div className="arch-row" style={{ maxWidth: 560 }}>
            <div className="arch-box arch-accent">
              <div className="arch-box-title">Hard bounds</div>
              <div className="arch-box-sub">policy.py · deterministic caps, works with zero LLM</div>
            </div>
            <div className="arch-box arch-accent">
              <div className="arch-box-title">LLM review</div>
              <div className="arch-box-sub">separate agent · context rules can't capture · fails closed</div>
            </div>
          </div>

          <div className="arch-arrow">↓</div>

          <div className="arch-branch">
            <div className="arch-branch-col">
              <div className="arch-box arch-good">
                <div className="arch-box-title">Razorpay</div>
                <div className="arch-box-sub">test-mode API, or MockGateway - agents never know which</div>
              </div>
            </div>
            <div className="arch-branch-col">
              <div className="arch-box">
                <div className="arch-box-title">Audit trail</div>
                <div className="arch-box-sub">every decision - allowed or denied - actor, reasoning, before/after state · /audit</div>
              </div>
            </div>
          </div>

          <div className="arch-llm-panel">
            <div className="arch-llm-title">LLM layer</div>
            <div className="arch-llm-chain">
              <span className="arch-llm-chip">Groq key-1</span>
              <span className="arch-llm-chain-arrow">→</span>
              <span className="arch-llm-chip">key-2</span>
              <span className="arch-llm-chain-arrow">→</span>
              <span className="arch-llm-chip">key-3</span>
              <span className="arch-llm-chain-arrow">→</span>
              <span className="arch-llm-chip">key-4</span>
              <span className="arch-llm-chain-arrow">→</span>
              <span className="arch-llm-chip arch-fallback">Anthropic</span>
            </div>
            <div className="arch-llm-note">
              Sticky rotation: a throttled key is skipped on every later request, not re-tried, until it falls all
              the way to Anthropic. Feeds every backend agent above and the gatekeeper's LLM review - never masks a
              real error, never splices a partial response across providers.
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="section-title">Track 1 requirements</div>
        <div className="track-brief-quote">
          <strong>Track 01 — AI Growth &amp; Agentic Commerce.</strong> "Grow the merchant's revenue, and make them
          sellable to AI buyers. Build an agent that grows revenue for a merchant on Razorpay test-mode APIs, or
          that makes a merchant transactable by an AI buyer end to end."
        </div>

        <div className="track-req">
          <div className="track-req-direction">Conversational in-app checkout</div>
          <div className="track-req-feature">
            <strong>Checkout Chat</strong> (<code>/chat</code>) - a Strands <code>checkout_agent</code> with real
            catalog/cart/checkout tools, not a scripted flow. <code>agents/search.py</code> ranks results by
            keyword relevance across title/description/category/tags rather than a single substring match.
          </div>
        </div>

        <div className="track-req">
          <div className="track-req-direction">Agent-readable catalog</div>
          <div className="track-req-feature">
            <code>GET /.well-known/agentic-commerce.json</code> - a machine-readable manifest describing the
            merchant, currency, and policy caps, in the spirit of ACP/AP2/x402 - plus <code>GET /catalog</code> as
            the plain product feed and the unauthenticated <code>/ai-buyer/purchase</code> endpoint as the actual
            transact surface an external agent can call end to end.
          </div>
        </div>

        <div className="track-req">
          <div className="track-req-direction">Upsell &amp; cross-sell agent</div>
          <div className="track-req-feature">
            <code>get_upsell_suggestions</code> - called automatically by <code>checkout_agent</code> after a
            shopper's first item is added, backed by a real product <code>complements</code> graph in the catalog,
            not a random "customers also bought."
          </div>
        </div>

        <div className="track-req">
          <div className="track-req-direction">Campaign orchestrator</div>
          <div className="track-req-feature">
            <code>campaign_agent</code> drafts honest offer copy; a deterministic policy engine computes recipients
            and discount exposure and the gatekeeper gates the launch. It sends a real payment link directly to
            each targeted customer <em>and</em> applies their discount automatically the moment they show up in
            chat - and when a sale closes at that price, the order is attributed to <code>campaign_agent</code> in
            revenue reporting (<code>Revenue by channel</code> on the Dashboard), not just logged as a launch event.
          </div>
        </div>

        <div className="track-req">
          <div className="track-req-direction">The bar: every money action explainable, bounded and gated</div>
          <div className="track-req-feature">
            <strong>Show the audit trail and one failure handled gracefully</strong> → <code>/audit</code> (every
            gatekeeper decision, allowed or denied, with actor, reasoning, and before/after state) + the ₹5,000
            per-order cap's denial-and-recovery flow, enforced identically on both surfaces: a human in Checkout
            Chat and the autonomous AI Buyer hit the exact same <code>checkout()</code> tool and the exact same
            cap, and both get a plain-language reason and a concrete way to fix it, not a stack trace.
          </div>
        </div>
      </div>
    </div>
  );
}
