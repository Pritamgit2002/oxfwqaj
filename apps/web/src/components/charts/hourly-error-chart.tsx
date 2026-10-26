"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HourlyAccuracy } from "@windsight/api-client";
import { mw } from "@/lib/format";

import { axis, C, gwTick, Y_AXIS_WIDTH } from "./theme";

export function HourlyErrorChart({ rows }: { rows: HourlyAccuracy[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis
          dataKey="hour"
          tickFormatter={(h: number) => `${String(h).padStart(2, "0")}h`}
          {...axis}
        />
        <YAxis tickFormatter={gwTick} width={Y_AXIS_WIDTH} unit=" GW" {...axis} />
        <Tooltip
          labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`}
          formatter={(v, n) => [mw(Number(v)), n]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="mae_mw" name="MAE" fill={C.forecast} isAnimationActive={false} />
        <Bar
          dataKey="bias_mw"
          name="Bias"
          fill={C.short}
          fillOpacity={0.6}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
