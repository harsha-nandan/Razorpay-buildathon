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

export default function MyOrders() {
  const { customerToken } = useAuth();
  const catalogImages = useCatalogImages();
  const [orders, setOrders] = useState<Order[]>([]);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!customerToken) return;
    api.myOrders(customerToken).then(setOrders).catch(() => setOrders([]));
  }, [customerToken]);

  async function viewInvoice(orderId: string) {
    if (!customerToken) return;
    try {
      setInvoice(await api.invoiceForOrder(customerToken, orderId));
    } catch {
      setInvoice(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>My orders</h1>
        <p>Everything you've bought from FlowState, with invoices for anything paid and a clear reason for anything that didn't go through.</p>
      </div>

      <div className="grid-2">
        <div className="card">
          {orders.length === 0 ? (
            <div className="empty-state">No orders yet - head to the shopping assistant to buy something.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>When</th>
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
                        <td colSpan={5} style={{ background: "var(--surface-2)" }}>
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
