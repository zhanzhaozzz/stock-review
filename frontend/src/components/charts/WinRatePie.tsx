import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  wins: number;
  losses: number;
  draws?: number;
  size?: number;
}

const COLORS = ["#ef4444", "#22c55e", "#6b7280"];

export default function WinRatePie({ wins, losses, draws = 0, size = 200 }: Props) {
  const data = [
    { name: "盈利", value: wins },
    { name: "亏损", value: losses },
  ];
  if (draws > 0) data.push({ name: "持平", value: draws });

  const total = wins + losses + draws;
  if (total === 0) {
    return <div className="text-gray-500 text-sm text-center py-8">暂无数据</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={size}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={40}
          outerRadius={70}
          paddingAngle={2}
          dataKey="value"
          label={({ name, percent }) => `${name} ${(((percent ?? 0) as number) * 100).toFixed(0)}%`}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
