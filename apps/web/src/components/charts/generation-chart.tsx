"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { clock, dateTime, mw } from "@/lib/format";

import { axis, C, gwTick, Y_AXIS_WIDTH } from "./theme";

export type GenerationRow = {
  t: number;
  actual: number | null;
  forecast: number | null;
  /** Optional bias-corrected forecast. */
  adjusted?: number | null;
  /** Optional uncertainty band for the outturn, [low, high] MW. */
  band?: [number, number] | null;
};

export function GenerationChart({
  rows,
  multiDay = false,
  bandLabel = "P10–P90 range",
  height = 340,
  showActual = true,
  showAdjusted = true,
  highlight,
}: {
  rows: GenerationRow[];
  multiDay?: boolean;
  bandLabel?: string;
  height?: number;
  showActual?: boolean;
  showAdjusted?: boolean;
  /** Shaded time window [start, end] in epoch ms, e.g. the lowest-wind hours. */
  highlight?: [number, number];
}) {
  const hasBand = rows.some((r) => r.band);
  const hasAdjusted = showAdjusted && rows.some((r) => r.adjusted != null);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(t: number) => (multiDay ? dateTime(t).split(",")[0]! : clock(t))}
          minTickGap={multiDay ? 40 : 24}
          {...axis}
        />
        <YAxis tickFormatter={gwTick} width={Y_AXIS_WIDTH} {...axis} unit=" GW" />
        <Tooltip
          labelFormatter={(t) => dateTime(Number(t))}
          formatter={(value, name) => [
            Array.isArray(value)
              ? `${mw(Number(value[0]))} – ${mw(Number(value[1]))}`
              : mw(Number(value)),
            name,
          ]}
        />
        <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
        {highlight && (
          <ReferenceArea
            x1={highlight[0]}
            x2={highlight[1]}
            fill={C.short}
            fillOpacity={0.07}
            stroke="none"
            label={{ value: "lowest wind", position: "insideTop", fontSize: 11, fill: C.short }}
          />
        )}
        {hasBand && (
          <Area
            dataKey="band"
            name={bandLabel}
            stroke="none"
            fill={C.band}
            fillOpacity={0.25}
            connectNulls
            isAnimationActive={false}
          />
        )}
        <Line
          dataKey="forecast"
          name="Forecast"
          stroke={C.forecast}
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={false}
          connectNulls
          isAnimationActive={false}
        />
        {hasAdjusted && (
          <Line
            dataKey="adjusted"
            name="Bias-adjusted"
            stroke={C.adjusted}
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        )}
        {showActual && (
          <Line
            dataKey="actual"
            name="Actual"
            stroke={C.actual}
            strokeWidth={1.75}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
