import { Fragment, useEffect, useState } from "react";
import { api, formatInr, type AuditEntry } from "../api";
import { useAuth } from "../auth";

const ACTORS = ["", "checkout_agent", "ai_buyer", "campaign_agent"];
const DECISIONS = ["", "allow", "deny", "n/a"];

function decisionBadge(entry: AuditEntry) {
  if (entry.decision === "allow") return <span className="badge badge-good">allowed</span>;
  if (entry.decision === "deny") return <span className="badge badge-critical">denied</span>;
  return <span className="badge badge-muted">info</span>;
}

export default function Audit() {
  const { sellerToken } = useAuth();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [actor, setActor] = useState("");
  const [decision, setDecision] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  function load() {
    if (!sellerToken) return;
    api
      .listAudit(sellerToken, { actor: actor || undefined, decision: decision || undefined })
      .then(setEntries)
      .catch(() => setEntries([]));
  }

  useEffect(load, [actor, decision, sellerToken]);

  return (
    <div>
      <div className="page-header">
        <h1>Audit trail</h1>
        <p>
          Every money-moving decision any agent proposed - allowed or denied, hard-bound rule or LLM
          gatekeeper - with the reasoning and before/after state. This is the explainability record for
          the whole system.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <div style={{ maxWidth: 200 }}>
          <label>Actor</label>
          <select value={actor} onChange={(e) => setActor(e.target.value)}>
            {ACTORS.map((a) => (
              <option key={a} value={a}>
                {a || "All actors"}
              </option>
            ))}
          </select>
        </div>
        <div style={{ maxWidth: 200 }}>
          <label>Decision</label>
          <select value={decision} onChange={(e) => setDecision(e.target.value)}>
            {DECISIONS.map((d) => (
              <option key={d} value={d}>
                {d || "All decisions"}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        {entries.length === 0 ? (
          <div className="empty-state">No matching audit entries yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Amount</th>
                <th>Decision</th>
                <th>Decided by</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <Fragment key={e.id}>
                  <tr onClick={() => setExpanded(expanded === e.id ? null : e.id)} style={{ cursor: "pointer" }}>
                    <td>{new Date(e.timestamp).toLocaleString()}</td>
                    <td className="primary">{e.actor}</td>
                    <td>{e.action_type}</td>
                    <td>{formatInr(e.amount_paise)}</td>
                    <td>{decisionBadge(e)}</td>
                    <td>{e.decided_by}</td>
                    <td>{e.reasoning}</td>
                  </tr>
                  {expanded === e.id && (
                    <tr>
                      <td colSpan={7} style={{ background: "var(--surface-2)" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: "8px 4px" }}>
                          <div>
                            <div className="trace-kind">policy refs</div>
                            <pre style={{ fontSize: 11.5, whiteSpace: "pre-wrap" }}>{JSON.stringify(e.policy_refs, null, 2)}</pre>
                          </div>
                          <div>
                            <div className="trace-kind">correlation id</div>
                            <pre style={{ fontSize: 11.5 }}>{e.correlation_id}</pre>
                          </div>
                          <div>
                            <div className="trace-kind">before</div>
                            <pre style={{ fontSize: 11.5, whiteSpace: "pre-wrap" }}>{JSON.stringify(e.before_state, null, 2)}</pre>
                          </div>
                          <div>
                            <div className="trace-kind">after</div>
                            <pre style={{ fontSize: 11.5, whiteSpace: "pre-wrap" }}>{JSON.stringify(e.after_state, null, 2)}</pre>
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
    </div>
  );
}
