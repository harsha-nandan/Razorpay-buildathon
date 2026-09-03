import { Fragment, useEffect, useState } from "react";
import { api, formatInr, type Invoice, type Order } from "../api";
import { useAuth } from "../auth";
import InvoiceView from "../components/InvoiceView";
import ProductThumb from "../components/ProductThumb";
import { useCatalogImages } from "../hooks/useCatalogImages";

function statusBadge(status: string) {
  if (status === "paid") return <span className="badge badge-good">paid</span>;
  if (status === "denied" || status === "failed") return <span className="badge badge-critical">{status}</span>;
  return <span className="badge badge-muted">{status}</span>;
}

export default function Orders() {
  const { sellerToken } = useAuth();
  const catalogImages = useCatalogImages();
  const [orders, setOrders] = useState<Order[]>([]);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!sellerToken) return;
    api.listOrders(sellerToken).then(setOrders).catch(() => setOrders([]));
  }, [sellerToken]);

  async function viewInvoice(orderId: string) {
    if (!sellerToken) return;
    try {
      setInvoice(await api.invoiceForOrder(sellerToken, orderId));
    } catch {
      setInvoice(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Orders</h1>
        <p>
          The transaction log: every payment attempt across the checkout chat, the AI buyer, and campaigns
          is its own row - a retry after a failure creates a fresh one rather than overwriting it. Failed
          rows carry a specific decline reason and remedy, never just "failed".
        </p>
      </div>

      <div className="grid-2">
        <div className="card">
          {orders.length === 0 ? (
            <div className="empty-state">No orders yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Source</th>
                  <th>Items</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <Fragment key={o.id}>
                    <tr
                      style={{ cursor: o.status === "failed" ? "pointer" : "default" }}
                      onClick={() => o.status === "failed" && setExpanded(expanded === o.id ? null : o.id)}
                    >
                      <td>{new Date(o.created_at).toLocaleString()}</td>
                      <td className="primary">{o.source}</td>
                      <td>
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          {o.items.map((i) => (
                            <div key={i.sku} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <ProductThumb src={catalogImages[i.sku]} alt={i.title} size={24} />
                              <span>{i.title}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                      <td>{formatInr(o.amount_paise)}</td>
                      <td>{statusBadge(o.status)}</td>
                      <td>
                        {o.status === "paid" && (
                          <button className="link-btn" onClick={() => viewInvoice(o.id)}>
                            View invoice
                          </button>
                        )}
                        {o.status === "failed" && <span className="link-btn">Why?</span>}
                      </td>
                    </tr>
                    {expanded === o.id && o.status === "failed" && (
                      <tr>
                        <td colSpan={6} style={{ background: "var(--surface-2)" }}>
                          <div style={{ padding: "6px 4px", fontSize: 12.5 }}>
                            <strong>{o.failure_code}</strong> — {o.failure_reason}
                            <div style={{ color: "var(--text-secondary)", marginTop: 4 }}>
                              What to do: {o.failure_remedy}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {invoice && <InvoiceView invoice={invoice} onClose={() => setInvoice(null)} />}
      </div>
    </div>
  );
}
