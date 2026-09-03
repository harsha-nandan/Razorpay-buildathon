import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface Slice {
  name: string;
  value: number;
}

export default function PieStatChart({
  data,
  colors,
  valueFormatter,
  emptyMessage = "No data yet.",
}: {
  data: Slice[];
  /** One color per slice, in the same order as `data`. */
  colors: string[];
  valueFormatter?: (value: number) => string;
  emptyMessage?: string;
}) {
  const nonZero = data.filter((d) => d.value > 0);
  if (nonZero.length === 0) {
    return <div className="empty-state">{emptyMessage}</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={nonZero} dataKey="value" nameKey="name" innerRadius={48} outerRadius={80} paddingAngle={2} strokeWidth={0}>
          {nonZero.map((entry, i) => (
            <Cell key={entry.name} fill={colors[i % colors.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12.5,
          }}
          formatter={(value, name) => [valueFormatter ? valueFormatter(Number(value)) : value, name]}
        />
        <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: 12.5, color: "var(--text-secondary)" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
