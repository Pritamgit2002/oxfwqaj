"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { mw } from "@/lib/format";

import { axis, C, gwTick, Y_AXIS_WIDTH } from "./theme";

export type DailyErrorRow = { day: string; mae: number | null; bias: number | null };

export function DailyErrorChart({ rows }: { rows: DailyErrorRow[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="day" tickFormatter={(d: string) => d.slice(8)} {...axis} />
        <YAxis tickFormatter={gwTick} width={Y_AXIS_WIDTH} unit=" GW" {...axis} />
        <ReferenceLine y={0} stroke={C.muted} />
        <Tooltip formatter={(v, name) => [mw(Number(v)), name]} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="bias" name="Bias (forecast − actual)" fill={C.short} fillOpacity={0.7} />
        <Line
          dataKey="mae"
          name="Mean absolute error"
          stroke={C.actual}
          strokeWidth={2}
          dot={{ r: 2 }}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
