import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface KLineData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  data: KLineData[];
  height?: number;
}

export default function MiniKLine({ data, height = 280 }: Props) {
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-sm text-center py-8">暂无K线数据</div>;
  }

  const chartData = data.map((d) => ({
    date: d.date.slice(5),
    close: d.close,
    volume: d.volume,
    color: d.close >= d.open ? "#ef4444" : "#22c55e",
  }));

  const prices = data.map((d) => d.close);
  const minP = Math.min(...prices) * 0.98;
  const maxP = Math.max(...prices) * 1.02;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval={Math.floor(data.length / 8)} />
        <YAxis
          yAxisId="price"
          domain={[minP, maxP]}
          tick={{ fill: "#6b7280", fontSize: 10 }}
          width={55}
          tickFormatter={(v: number) => v.toFixed(2)}
        />
        <YAxis yAxisId="vol" orientation="right" tick={false} axisLine={false} />
        <Tooltip
          contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
          formatter={(value: any, name: any) => {
            const v = typeof value === "number" ? value : 0;
            if (name === "close") return [v.toFixed(2), "收盘价"];
            return [(v / 10000).toFixed(0) + "万", "成交量"];
          }}
        />
        <Bar yAxisId="vol" dataKey="volume" fill="#374151" opacity={0.3} />
        <Line
          yAxisId="price"
          type="monotone"
          dataKey="close"
          stroke="#3b82f6"
          strokeWidth={1.5}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
