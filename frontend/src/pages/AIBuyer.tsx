import { useEffect, useMemo, useState } from "react";
import { api, formatInr, type AIBuyerConfirmation, type AIBuyerRun, type TraceItem } from "../api";
import TraceView from "../components/TraceView";
import AutoPaymentPanel from "../components/AutoPaymentPanel";
import { findLatestCheckoutResult, stripMarkdown } from "../utils";

/** Purely a display beat (see AutoPaymentPanel) - not a real processing
 * delay. The actual confirm call below fires immediately and doesn't wait
 * on this; it just keeps the "processing" panel on screen long enough for
 * a viewer to register it before it flips to "authorized". */
const PAYMENT_PANEL_MIN_VISIBLE_MS = 1100;

function historyStatusBadge(status: string) {
  if (status === "paid") return <span className="badge badge-good">paid</span>;
  if (status === "denied") return <span className="badge badge-critical">denied</span>;
  return <span className="badge badge-muted">{status}</span>;
}

const EXAMPLE_INTENTS = [
  { intent: "Buy a good pair of wireless earbuds", budget: 3000 },
  { intent: "I need a smartwatch and whatever goes well with it", budget: 6000 },
  { intent: "Get me the most expensive item you sell, no budget limit", budget: undefined },
];

export default function AIBuyer() {
  const [intent, setIntent] = useState("");
  const [budget, setBudget] = useState<string>("3000");
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [reply, setReply] = useState("");
  const [trace, setTrace] = useState<TraceItem[]>([]);
  const [ran, setRan] = useState(false);
  const [confirmation, setConfirmation] = useState<AIBuyerConfirmation | null>(null);
  const [confirmError, setConfirmError] = useState("");
  const [history, setHistory] = useState<AIBuyerRun[]>([]);

  const checkoutResult = useMemo(() => findLatestCheckoutResult(trace), [trace]);

  function refreshHistory() {
    api.aiBuyerHistory().then(setHistory).catch(() => {});
  }

  useEffect(() => {
    refreshHistory();
  }, []);

  async function run(intentValue: string, budgetValue: string) {
    if (!intentValue.trim() || loading) return;
    setLoading(true);
    setRan(true);
    setReply("");
    setTrace([]);
    setConfirmation(null);
    setConfirmError("");
    try {
      const budgetPaise = budgetValue ? Math.round(parseFloat(budgetValue) * 100) : null;
      const res = await api.aiBuyerPurchase(intentValue, budgetPaise);
      setReply(stripMarkdown(res.reply));
      setTrace(res.trace);

      // No human in the loop means no human clicking the payment link either -
      // an approved quote is phase 1 of the x402 handshake; complete phase 2
      // automatically so "Run AI purchase" demonstrates the full autonomous
      // purchase, not just a quote the demo then leaves dangling.
      const result = findLatestCheckoutResult(res.trace);
      if (result?.status === "approved" && result.order_id) {
        setConfirming(true);
        try {
          const [conf] = await Promise.all([
            api.aiBuyerConfirmPayment(intentValue, result.order_id),
            new Promise((resolve) => setTimeout(resolve, PAYMENT_PANEL_MIN_VISIBLE_MS)),
          ]);
          setConfirmation(conf);
        } catch (e) {
          setConfirmError(String(e));
        } finally {
          setConfirming(false);
        }
      }
      refreshHistory();
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
                    {(confirming || confirmation) && (
                      <AutoPaymentPanel amountPaise={checkoutResult.amount_paise || 0} authorized={!!confirmation} />
                    )}
                    {confirmation && (
                      <p style={{ fontSize: 13, marginTop: 10 }}>
                        <span className="badge badge-good">Payment authorized</span>{" "}
                        {confirmation.invoice_number ? (
                          <>Invoice <code>{confirmation.invoice_number}</code> issued.</>
                        ) : (
                          "Order paid."
                        )}
                      </p>
                    )}
                    {confirmError && (
                      <p style={{ fontSize: 12.5, marginTop: 8, color: "var(--status-critical)" }}>
                        Auto-confirmation failed: {confirmError}
                      </p>
                    )}
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

      <div className="card" style={{ marginTop: 16 }}>
        <div className="section-title">Run history</div>
        <p style={{ fontSize: 11.5, color: "var(--text-muted)", marginBottom: 8 }}>
          Every past run that reached a checkout decision - these orders are never attached to a customer
          account (the AI buyer is intentionally unauthenticated), so this page is their only record.
        </p>
        {history.length === 0 ? (
          <div className="empty-state">No runs yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Intent</th>
                <th>Budget</th>
                <th>Items</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((run) => (
                <tr key={run.order_id}>
                  <td>{new Date(run.created_at).toLocaleString()}</td>
                  <td style={{ maxWidth: 260 }}>{run.buyer_intent || "—"}</td>
                  <td>{run.requested_budget_paise != null ? formatInr(run.requested_budget_paise) : "no limit"}</td>
                  <td>{run.items.map((i) => i.title).join(", ")}</td>
                  <td>{formatInr(run.amount_paise)}</td>
                  <td>{historyStatusBadge(run.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
