"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HistogramBin } from "@windsight/api-client";

import { axis, C } from "./theme";

const label = (b: HistogramBin) => `${(b.lower_mw / 1000).toFixed(1)}`;

export function HistogramChart({ bins }: { bins: HistogramBin[] }) {
  const rows = bins.map((b) => ({ ...b, label: label(b) }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }} barCategoryGap={1}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="label" unit=" GW" interval="preserveStartEnd" {...axis} />
        <YAxis allowDecimals={false} {...axis} />
        <Tooltip
          labelFormatter={(_, payload) => {
            const b = payload?.[0]?.payload as HistogramBin | undefined;
            return b ? `${b.lower_mw} to ${b.upper_mw} MW` : "";
          }}
          formatter={(v) => [`${v} hours`, "Count"]}
        />
        <Bar dataKey="count" isAnimationActive={false}>
          {rows.map((b) => (
            <Cell
              key={b.lower_mw}
              fill={b.lower_mw >= 0 ? C.short : C.surplus}
              fillOpacity={0.75}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
