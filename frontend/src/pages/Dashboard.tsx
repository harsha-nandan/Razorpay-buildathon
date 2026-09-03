import { useEffect, useState } from "react";
import { api, formatInr, type AuditEntry, type DashboardStats } from "../api";
import StatTile from "../components/StatTile";
import RevenueChart from "../components/RevenueChart";
import FunnelChart from "../components/FunnelChart";
import PieStatChart from "../components/PieStatChart";
import { useAuth } from "../auth";

// Fixed per-channel color so a channel's slice is always the same color
// regardless of the order the backend happens to return sources in.
const CHANNEL_COLORS: Record<string, string> = {
  checkout_agent: "var(--series-1)",
  ai_buyer: "var(--series-2)",
  campaign_agent: "var(--series-3)",
};
const FALLBACK_CHANNEL_COLOR = "var(--series-1)";

function decisionBadge(entry: AuditEntry) {
  if (entry.decision === "allow") return <span className="badge badge-good">allowed</span>;
  if (entry.decision === "deny") return <span className="badge badge-critical">denied</span>;
  return <span className="badge badge-muted">info</span>;
}

export default function Dashboard() {
  const { seller, sellerToken } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentAudit, setRecentAudit] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sellerToken) return;
    Promise.all([api.dashboardStats(sellerToken), api.listAudit(sellerToken, {})])
      .then(([s, a]) => {
        setStats(s);
        setRecentAudit(a.slice(0, 8));
      })
      .catch((e) => setError(String(e)));
  }, [sellerToken]);

  return (
    <div>
      <div className="page-header">
        <h1>Welcome back{seller ? `, ${seller.name}` : ""}</h1>
        <p>
          Revenue, campaign activity, and every gated money decision the merchant's agents have made -
          allowed and denied - in one place.
        </p>
      </div>

      {error && <div className="card" style={{ marginBottom: 16, color: "var(--status-critical)" }}>{error}</div>}

      {stats && (
        <>
          <div className="stat-grid">
            <StatTile label="Revenue (paid)" value={formatInr(stats.total_revenue_paise)} />
            <StatTile
              label="Orders"
              value={String(stats.orders_created)}
              sub={`${stats.orders_paid} paid · ${stats.orders_denied} denied · ${stats.orders_failed} failed`}
            />
            <StatTile
              label="Campaigns"
              value={String(stats.campaigns_total)}
              sub={`${stats.campaigns_running_or_completed} launched · ${stats.campaigns_denied} denied`}
            />
            <StatTile
              label="Gatekeeper decisions"
              value={String(stats.gatekeeper_allows + stats.gatekeeper_denies)}
              sub={`${stats.gatekeeper_allows} allowed · ${stats.gatekeeper_denies} denied`}
            />
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="section-title">Revenue by day</div>
              <RevenueChart data={stats.revenue_by_day} />
            </div>
            <div className="card">
              <div className="section-title">Revenue by channel</div>
              {stats.revenue_by_source.length === 0 ? (
                <div className="empty-state">No paid orders yet.</div>
              ) : (
                <>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {stats.revenue_by_source.map((s) => (
                      <div key={s.source} className="cart-item">
                        <span>{s.source}</span>
                        <strong>{formatInr(s.revenue_paise)}</strong>
                      </div>
                    ))}
                  </div>
                  <PieStatChart
                    data={stats.revenue_by_source.map((s) => ({ name: s.source, value: s.revenue_paise }))}
                    colors={stats.revenue_by_source.map((s) => CHANNEL_COLORS[s.source] ?? FALLBACK_CHANNEL_COLOR)}
                    valueFormatter={(v) => formatInr(v)}
                  />
                </>
              )}
            </div>
          </div>

          <div className="grid-2" style={{ marginTop: 16 }}>
            <div className="card">
              <div className="section-title">Revenue by customer</div>
              {stats.revenue_by_customer.length === 0 ? (
                <div className="empty-state">No paid orders from a known customer yet.</div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Customer</th>
                      <th>Total spent</th>
                      <th>Orders</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.revenue_by_customer.map((c) => (
                      <tr key={c.customer_name}>
                        <td className="primary">{c.customer_name}</td>
                        <td>{formatInr(c.revenue_paise)}</td>
                        <td>{c.order_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="card">
              <div className="section-title">Gatekeeper decisions</div>
              <PieStatChart
                data={[
                  { name: "Allowed", value: stats.gatekeeper_allows },
                  { name: "Denied", value: stats.gatekeeper_denies },
                ]}
                colors={["var(--status-good)", "var(--status-critical)"]}
                emptyMessage="No gated decisions yet."
              />
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="section-title">Conversion funnel</div>
            <FunnelChart stages={stats.funnel.stages} />
            {stats.funnel.by_source.length > 0 && (
              <table style={{ marginTop: 16 }}>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Attempted</th>
                    <th>Approved</th>
                    <th>Paid</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.funnel.by_source.map((s) => (
                    <tr key={s.source}>
                      <td className="primary">{s.source}</td>
                      <td>{s.attempted}</td>
                      <td>{s.approved}</td>
                      <td>{s.paid}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <div className="section-title">Recent gatekeeper activity</div>
        {recentAudit.length === 0 ? (
          <div className="empty-state">No agent activity yet - try the Checkout Chat or AI Buyer pages.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Amount</th>
                <th>Decision</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {recentAudit.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.timestamp).toLocaleString()}</td>
                  <td className="primary">{e.actor}</td>
                  <td>{e.action_type}</td>
                  <td>{formatInr(e.amount_paise)}</td>
                  <td>{decisionBadge(e)}</td>
                  <td>{e.reasoning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
