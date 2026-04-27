"use client";

import { cn } from "@/lib/utils";
import { LineChart, Line, ResponsiveContainer } from "recharts";

interface Props {
  data: number[];
  positive?: boolean;
  className?: string;
  width?: number;
  height?: number;
}

export function Sparkline({ data, positive = true, className, width = 80, height = 32 }: Props) {
  const chartData = data.map((value, i) => ({ i, value }));
  const color = positive ? "#34d399" : "#fb7185";

  return (
    <div className={cn("", className)} style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
