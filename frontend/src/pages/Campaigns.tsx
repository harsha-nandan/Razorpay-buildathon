import { useEffect, useState } from "react";
import { api, formatInr, type Campaign, type Product } from "../api";
import { useAuth } from "../auth";
import { stripMarkdown } from "../utils";

const SEGMENTS = ["vip", "repeat", "new", "lapsed", "general"];

function statusBadge(status: string) {
  if (status === "completed" || status === "running") return <span className="badge badge-good">{status}</span>;
  if (status === "denied") return <span className="badge badge-critical">denied</span>;
  if (status === "cancelled") return <span className="badge badge-muted">cancelled</span>;
  return <span className="badge badge-muted">{status}</span>;
}

export default function Campaigns() {
  const { sellerToken } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [expanded, setExpanded] = useState<Campaign | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    goal: "",
    discount_percent: 15,
    target_segment: "repeat",
    product_sku: "",
    max_recipients: 10,
  });

  function refresh() {
    if (!sellerToken) return;
    api.listCampaigns(sellerToken).then(setCampaigns).catch((e) => setError(String(e)));
  }

  useEffect(() => {
    refresh();
    api.catalog().then((c) => {
      setProducts(c.products);
      setForm((f) => (f.product_sku ? f : { ...f, product_sku: c.products[0]?.id || c.products[0]?.sku || "" }));
    });
  }, [sellerToken]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!sellerToken) return;
    setSubmitting(true);
    setError("");
    try {
      await api.createCampaign(sellerToken, form);
      setForm((f) => ({ ...f, name: "", goal: "" }));
      refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function openCampaign(id: string) {
    if (!sellerToken) return;
    const full = await api.getCampaign(sellerToken, id);
    setExpanded(full);
  }

  async function stopCampaign(id: string) {
    if (!sellerToken) return;
    setCancelling(true);
    try {
      const updated = await api.cancelCampaign(sellerToken, id);
      setExpanded(updated);
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setCancelling(false);
    }
  }

  async function deleteCampaign(id: string, name: string) {
    if (!sellerToken) return;
    if (!window.confirm(`Permanently delete campaign "${name}"? This can't be undone.`)) return;
    setDeleting(id);
    try {
      await api.deleteCampaign(sellerToken, id);
      if (expanded?.id === id) setExpanded(null);
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Campaign orchestrator</h1>
        <p>
          Propose a growth campaign; a Strands agent drafts honest offer copy while a deterministic policy
          engine computes recipients and discount exposure. Every launch is gated - try a high discount to
          see it denied.
        </p>
      </div>

      <div className="grid-2">
        <form className="card" onSubmit={submit}>
          <div className="section-title">New campaign</div>
          <div className="form-row">
            <label>Name</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Winback: lapsed customers" />
          </div>
          <div className="form-row">
            <label>Goal</label>
            <input required value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} placeholder="Re-engage customers who haven't ordered in a while" />
          </div>
          <div className="form-grid">
            <div className="form-row">
              <label>Product</label>
              <select value={form.product_sku} onChange={(e) => setForm({ ...form, product_sku: e.target.value })}>
                {products.map((p) => (
                  <option key={p.id || p.sku} value={p.id || p.sku}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Target segment</label>
              <select value={form.target_segment} onChange={(e) => setForm({ ...form, target_segment: e.target.value })}>
                {SEGMENTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Discount %</label>
              <input
                type="number"
                min={0}
                max={100}
                value={form.discount_percent}
                onChange={(e) => setForm({ ...form, discount_percent: Number(e.target.value) })}
              />
            </div>
            <div className="form-row">
              <label>Max recipients</label>
              <input
                type="number"
                min={1}
                value={form.max_recipients}
                onChange={(e) => setForm({ ...form, max_recipients: Number(e.target.value) })}
              />
            </div>
          </div>
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Launching…" : "Propose & launch"}
          </button>
          <p style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 8 }}>
            Tip: set discount % above the merchant's configured cap (default 40%) to see the gatekeeper deny
            it gracefully.
          </p>
          {error && <p style={{ color: "var(--status-critical)", fontSize: 12.5 }}>{error}</p>}
        </form>

        <div className="card">
          <div className="section-title">Campaigns</div>
          {campaigns.length === 0 ? (
            <div className="empty-state">No campaigns yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Discount</th>
                  <th>Reach</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => (
                  <tr key={c.id} onClick={() => openCampaign(c.id)} style={{ cursor: "pointer" }}>
                    <td className="primary">{c.name}</td>
                    <td>{c.discount_percent}%</td>
                    <td>{c.recipients_reached}/{c.max_recipients}</td>
                    <td>{statusBadge(c.status)}</td>
                    <td>
                      <button
                        className="cart-remove-btn"
                        type="button"
                        aria-label={`Delete ${c.name}`}
                        disabled={deleting === c.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteCampaign(c.id, c.name);
                        }}
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {expanded && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="section-title">
            {expanded.name} {statusBadge(expanded.status)}
          </div>
          <p style={{ fontSize: 13.5 }}>
            <strong>Offer copy:</strong> {stripMarkdown(expanded.message_copy)}
          </p>
          <p style={{ fontSize: 13.5, color: "var(--text-secondary)" }}>
            <strong>Reasoning:</strong> {stripMarkdown(expanded.reasoning)}
          </p>
          <p style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
            Discount exposure: {formatInr(expanded.budget_paise)} across up to {expanded.max_recipients} recipients
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            {expanded.status === "completed" && (
              <button className="btn" disabled={cancelling} onClick={() => stopCampaign(expanded.id)}>
                {cancelling ? "Stopping…" : "Stop campaign"}
              </button>
            )}
            <button
              className="btn"
              disabled={deleting === expanded.id}
              onClick={() => deleteCampaign(expanded.id, expanded.name)}
              style={{ color: "var(--status-critical)" }}
            >
              {deleting === expanded.id ? "Deleting…" : "Delete campaign"}
            </button>
          </div>
          {expanded.status === "cancelled" && (
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
              Stopped - this discount no longer applies to any new checkout.
            </p>
          )}
          {expanded.actions && expanded.actions.length > 0 && (
            <table style={{ marginTop: 10 }}>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Offer amount</th>
                  <th>Payment link</th>
                </tr>
              </thead>
              <tbody>
                {expanded.actions.map((a, i) => (
                  <tr key={i}>
                    <td className="primary">{a.customer_name}</td>
                    <td>{formatInr(a.amount_paise)}</td>
                    <td>
                      <a href={a.payment_link_url} target="_blank" rel="noreferrer">
                        {a.payment_link_url}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
