import { GenerationChart } from "@/components/charts/generation-chart";
import { DownloadCsv } from "@/components/controls/download-csv";
import { ExplorerControls } from "@/components/controls/explorer-controls";
import { Card } from "@/components/ui/card";
import { Kpi, KpiGrid } from "@/components/ui/kpi";
import { PageHeader } from "@/components/ui/page-header";
import { getMeta, getSeries } from "@/lib/api";
import { addDays, clampDate, first, type SearchParams } from "@/lib/dates";
import { gw, mw, pct } from "@/lib/format";

export default async function ExplorerPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams;
  const meta = await getMeta();
  const { start: min, end: max } = meta.delivery_window;

  const start = clampDate(first(sp.start) ?? min, min, max);
  const end = clampDate(first(sp.end) ?? addDays(start, 6), start, max);
  const parsed = Number(first(sp.horizon) ?? 24);
  const horizon = Number.isFinite(parsed)
    ? Math.min(Math.max(Math.round(parsed), 0), meta.max_horizon_hours)
    : 24;

  // January is GMT, so UK midnight == UTC midnight for the pilot window.
  const series = await getSeries(`${start}T00:00:00Z`, `${addDays(end, 1)}T00:00:00Z`, horizon);
  const s = series.stats;

  return (
    <>
      <PageHeader
        title="Horizon explorer"
        description="For each hour, the latest forecast published at least the chosen number of hours before it. Slide the horizon to see how accuracy degrades with lead time."
      >
        <ExplorerControls
          start={start}
          end={end}
          horizon={horizon}
          min={min}
          max={max}
          maxHorizon={meta.max_horizon_hours}
        />
      </PageHeader>

      <KpiGrid>
        <Kpi label="MAE" value={gw(s?.mae_mw)} hint={`${pct(s?.nmae_pct)} of mean outturn`} />
        <Kpi label="RMSE" value={gw(s?.rmse_mw)} />
        <Kpi label="Bias" value={gw(s?.bias_mw)} tone={s && s.bias_mw > 0 ? "short" : "surplus"} />
        <Kpi
          label="P90 shortfall"
          value={gw(s?.p90_error_mw)}
          tone="short"
          hint={`${s?.count ?? 0} hours compared · max ${mw(s?.max_shortfall_mw)}`}
        />
      </KpiGrid>

      <Card
        className="mt-4"
        title={`Actual vs forecast published ≥ ${horizon} h ahead`}
        action={
          <DownloadCsv
            filename={`windsight-horizon-${horizon}h-${start}-to-${end}.csv`}
            header={["start_time_utc", "forecast_mw", "forecast_publish_time_utc", "actual_mw"]}
            rows={series.points.map((p) => [
              p.start_time,
              p.forecast_mw,
              p.forecast_publish_time,
              p.actual_mw,
            ])}
          />
        }
      >
        <GenerationChart
          multiDay
          height={380}
          rows={series.points.map((p) => ({
            t: Date.parse(p.start_time),
            actual: p.actual_mw,
            forecast: p.forecast_mw,
          }))}
        />
      </Card>
    </>
  );
}
