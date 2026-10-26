"use client";

import { useState } from "react";

import type { DayAheadPoint } from "@windsight/api-client";
import { DownloadCsv } from "@/components/controls/download-csv";
import { Toggle } from "@/components/ui/toggle";

import { GenerationChart } from "./generation-chart";
import { C } from "./theme";

export function DayAheadChart({
  points,
  trough,
  calibrationDays,
  filename,
}: {
  points: DayAheadPoint[];
  trough?: [string, string];
  calibrationDays?: number;
  filename: string;
}) {
  const [showAdjusted, setShowAdjusted] = useState(true);
  // Hide the outturn to see exactly what the buyer saw at the cutoff, then reveal it.
  const [showActual, setShowActual] = useState(true);
  const hasCalibration = points.some((p) => p.adjusted_mw != null);

  const rows = points.map((p) => ({
    t: Date.parse(p.start_time),
    actual: p.actual_mw,
    forecast: p.forecast_mw,
    adjusted: p.adjusted_mw,
    band:
      p.band_low_mw != null && p.band_high_mw != null
        ? ([p.band_low_mw, p.band_high_mw] as [number, number])
        : null,
  }));

  return (
    <>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {hasCalibration && (
          <Toggle pressed={showAdjusted} onChange={setShowAdjusted} color={C.adjusted}>
            Bias-adjusted
          </Toggle>
        )}
        <Toggle pressed={showActual} onChange={setShowActual} color={C.actual}>
          Show actuals
        </Toggle>
        <span className="ml-auto">
          <DownloadCsv
            filename={filename}
            header={[
              "start_time_utc",
              "forecast_mw",
              "adjusted_mw",
              "p10_mw",
              "p90_mw",
              "actual_mw",
              "error_mw",
            ]}
            rows={points.map((p) => [
              p.start_time,
              p.forecast_mw,
              p.adjusted_mw,
              p.band_low_mw,
              p.band_high_mw,
              p.actual_mw,
              p.error_mw,
            ])}
          />
        </span>
      </div>
      <GenerationChart
        rows={rows}
        showActual={showActual}
        showAdjusted={showAdjusted}
        bandLabel={calibrationDays ? `P10–P90 range (last ${calibrationDays} days)` : undefined}
        highlight={trough ? [Date.parse(trough[0]), Date.parse(trough[1])] : undefined}
      />
    </>
  );
}
