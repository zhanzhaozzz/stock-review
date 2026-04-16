import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const PHASE_Y: Record<string, number> = {
  "冰点": 1,
  "退潮": 2,
  "启动": 3,
  "发酵": 4,
  "高潮": 6,
  "高位混沌": 5,
};

interface SentimentLog {
  date: string;
  cycle_phase: string;
  market_height: number;
}

interface Props {
  data: SentimentLog[];
  height?: number;
}

export default function SentimentTrend({ data, height = 200 }: Props) {
  const chartData = data.map((d) => ({
    date: d.date.slice(5),
    phase: d.cycle_phase,
    phaseY: PHASE_Y[d.cycle_phase] || 3,
    height: d.market_height,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 10 }} />
        <YAxis
          yAxisId="left"
          domain={[0, 8]}
          tick={{ fill: "#6b7280", fontSize: 10 }}
          label={{ value: "高度", angle: -90, position: "insideLeft", fill: "#6b7280", fontSize: 10 }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          domain={[0, 7]}
          tick={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
          formatter={(value: any, name: any, props: any) => {
            const v = typeof value === "number" ? value : 0;
            if (name === "height") return [`${v}板`, "市场高度"];
            return [props?.payload?.phase || "", "情绪周期"];
          }}
        />
        <Area
          yAxisId="left"
          type="monotone"
          dataKey="height"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.15}
          strokeWidth={2}
        />
        <Area
          yAxisId="right"
          type="stepAfter"
          dataKey="phaseY"
          stroke="#a855f7"
          fill="#a855f7"
          fillOpacity={0.08}
          strokeWidth={1}
          strokeDasharray="4 2"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
