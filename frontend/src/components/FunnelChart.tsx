interface Stage {
  stage: string;
  count: number;
}

/** A simple ordinal funnel: each stage is a stop on the same "how many
 * checkouts made it this far" scale, so a single sequential hue and a
 * direct count + conversion-from-previous label are enough - no need for
 * a categorical palette since there's only one series here. */
export default function FunnelChart({ stages }: { stages: Stage[] }) {
  if (stages.length === 0 || stages[0].count === 0) {
    return <div className="empty-state">No checkout attempts yet.</div>;
  }

  const max = stages[0].count;

  return (
    <div className="funnel-chart">
      {stages.map((s, i) => {
        const widthPct = Math.max((s.count / max) * 100, 4);
        const prev = i > 0 ? stages[i - 1].count : null;
        const conversion = prev && prev > 0 ? Math.round((s.count / prev) * 100) : null;
        return (
          <div key={s.stage} className="funnel-row">
            <div className="funnel-row-label">
              <span>{s.stage}</span>
              <span className="funnel-row-count">
                {s.count}
                {conversion !== null && <span className="funnel-row-conversion"> ({conversion}% of prior stage)</span>}
              </span>
            </div>
            <div className="funnel-bar-track">
              <div className="funnel-bar-fill" style={{ width: `${widthPct}%`, opacity: 1 - i * 0.22 }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
