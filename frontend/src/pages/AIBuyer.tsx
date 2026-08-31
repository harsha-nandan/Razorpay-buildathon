import { useMemo, useState } from "react";
import { api, formatInr, type TraceItem } from "../api";
import TraceView from "../components/TraceView";
import { findLatestCheckoutResult, stripMarkdown } from "../utils";

const EXAMPLE_INTENTS = [
  { intent: "Buy a good pair of wireless earbuds", budget: 3000 },
  { intent: "I need a smartwatch and whatever goes well with it", budget: 6000 },
  { intent: "Get me the most expensive item you sell, no budget limit", budget: undefined },
];

export default function AIBuyer() {
  const [intent, setIntent] = useState("");
  const [budget, setBudget] = useState<string>("3000");
  const [loading, setLoading] = useState(false);
  const [reply, setReply] = useState("");
  const [trace, setTrace] = useState<TraceItem[]>([]);
  const [ran, setRan] = useState(false);

  const checkoutResult = useMemo(() => findLatestCheckoutResult(trace), [trace]);

  async function run(intentValue: string, budgetValue: string) {
    if (!intentValue.trim() || loading) return;
    setLoading(true);
    setRan(true);
    setReply("");
    setTrace([]);
    try {
      const budgetPaise = budgetValue ? Math.round(parseFloat(budgetValue) * 100) : null;
      const res = await api.aiBuyerPurchase(intentValue, budgetPaise);
      setReply(stripMarkdown(res.reply));
      setTrace(res.trace);
    } catch (e) {
      setReply(`⚠️ ${String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>AI buyer simulator</h1>
        <p>
          Simulates an external AI shopping agent discovering this merchant via the agent-readable catalog
          (<code>/.well-known/agentic-commerce.json</code>) and transacting end to end - no human in the
          loop. It uses the exact same tools, gatekeeper, and Razorpay flow as the human checkout chat.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="form-row">
          <label>Buyer intent</label>
          <textarea
            rows={2}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. Buy the best noise-cancelling earbuds you have"
          />
        </div>
        <div className="form-row" style={{ maxWidth: 220 }}>
          <label>Budget (INR, optional)</label>
          <input value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="e.g. 3000" />
        </div>
        <button className="btn btn-primary" disabled={loading} onClick={() => run(intent, budget)}>
          {loading ? "AI buyer is shopping…" : "Run AI purchase"}
        </button>
        <div className="pill-row" style={{ marginTop: 12 }}>
          {EXAMPLE_INTENTS.map((ex) => (
            <button
              key={ex.intent}
              type="button"
              className="pill"
              disabled={loading}
              onClick={() => {
                setIntent(ex.intent);
                setBudget(ex.budget ? String(ex.budget) : "");
                run(ex.intent, ex.budget ? String(ex.budget) : "");
              }}
            >
              {ex.intent}
            </button>
          ))}
        </div>
      </div>

      {ran && (
        <div className="grid-2">
          <div className="card">
            <div className="section-title">Agent's final report</div>
            {loading ? <div className="empty-state">Working…</div> : <p style={{ fontSize: 13.5, lineHeight: 1.5 }}>{reply}</p>}

            {checkoutResult && (
              <div style={{ marginTop: 14 }}>
                {checkoutResult.status === "approved" ? (
                  <>
                    <span className="badge badge-good">Gatekeeper approved</span>
                    <p style={{ fontSize: 13, marginTop: 8 }}>
                      Order <code>{checkoutResult.order_id}</code> for {formatInr(checkoutResult.amount_paise || 0)}.{" "}
                      <a href={checkoutResult.payment_link} target="_blank" rel="noreferrer">
                        Payment link
                      </a>
                    </p>
                  </>
                ) : (
                  <>
                    <span className="badge badge-critical">Gatekeeper denied</span>
                    <p style={{ fontSize: 13, marginTop: 8 }}>{checkoutResult.reason}</p>
                  </>
                )}
              </div>
            )}
          </div>
          <div className="card">
            <div className="section-title">Full autonomous transcript</div>
            <TraceView trace={trace} />
          </div>
        </div>
      )}
    </div>
  );
}
