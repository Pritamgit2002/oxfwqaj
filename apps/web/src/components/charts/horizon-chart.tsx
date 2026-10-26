"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HorizonBucket } from "@windsight/api-client";
import { mw } from "@/lib/format";

import { axis, C, gwTick, Y_AXIS_WIDTH } from "./theme";

export function HorizonChart({ buckets, marker }: { buckets: HorizonBucket[]; marker?: number }) {
  const rows = buckets.map((b) => ({
    h: b.horizon_hours,
    mae: b.stats.mae_mw,
    p90: b.stats.p90_abs_error_mw,
    bias: b.stats.bias_mw,
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="h" type="number" domain={[0, "dataMax"]} unit=" h" {...axis} />
        <YAxis tickFormatter={gwTick} width={Y_AXIS_WIDTH} unit=" GW" {...axis} />
        <Tooltip
          labelFormatter={(h) => `${h}–${Number(h) + 1} h ahead`}
          formatter={(v, n) => [mw(Number(v)), n]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {marker != null && <ReferenceLine x={marker} stroke={C.muted} strokeDasharray="3 3" />}
        <Line
          dataKey="p90"
          name="P90 absolute error"
          stroke={C.short}
          dot={false}
          strokeWidth={2}
          isAnimationActive={false}
        />
        <Line
          dataKey="mae"
          name="MAE"
          stroke={C.forecast}
          dot={false}
          strokeWidth={2}
          isAnimationActive={false}
        />
        <Line
          dataKey="bias"
          name="Bias"
          stroke={C.muted}
          dot={false}
          strokeDasharray="4 3"
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
