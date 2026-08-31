import type { TraceItem } from "../api";

function formatInput(input: unknown): string {
  if (input == null) return "";
  try {
    return JSON.stringify(input);
  } catch {
    return String(input);
  }
}

export default function TraceView({ trace }: { trace: TraceItem[] }) {
  const steps = trace.filter((t) => t.type === "tool_call" || t.type === "tool_result");
  if (steps.length === 0) {
    return <div className="empty-state">No tool calls in this turn yet.</div>;
  }
  return (
    <div className="trace-log">
      {steps.map((step, i) => (
        <div key={i} className={`trace-item ${step.type}`}>
          {step.type === "tool_call" ? (
            <>
              <div className="trace-kind">tool call &middot; {step.tool}</div>
              <pre>{formatInput(step.input)}</pre>
            </>
          ) : (
            <>
              <div className="trace-kind">result &middot; {step.status}</div>
              <pre>{step.output}</pre>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
