import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatInr } from "../api";

interface Props {
  data: { date: string; revenue_paise: number }[];
}

export default function RevenueChart({ data }: Props) {
  if (data.length === 0) {
    return <div className="empty-state">No paid orders yet - revenue will appear here once a checkout completes.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--gridline)" />
        <XAxis
          dataKey="date"
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={{ stroke: "var(--baseline)" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `₹${(v / 100).toLocaleString("en-IN")}`}
          width={64}
        />
        <Tooltip
          cursor={{ fill: "var(--surface-2)" }}
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12.5,
          }}
          formatter={(value) => [formatInr(Number(value)), "Revenue"]}
        />
        <Bar dataKey="revenue_paise" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}
