import { DailyErrorChart } from "@/components/charts/daily-error-chart";
import { HistogramChart } from "@/components/charts/histogram-chart";
import { HorizonChart } from "@/components/charts/horizon-chart";
import { HourlyErrorChart } from "@/components/charts/hourly-error-chart";
import { DecisionControls } from "@/components/controls/decision-controls";
import { Card } from "@/components/ui/card";
import { Findings } from "@/components/ui/findings";
import { Kpi, KpiGrid } from "@/components/ui/kpi";
import { PageHeader } from "@/components/ui/page-header";
import { getDayAheadAccuracy, getHorizonAccuracy, getMeta } from "@/lib/api";
import { first, isCutoff, type SearchParams } from "@/lib/dates";
import { gw, longDate, mw, pct } from "@/lib/format";

export default async function AccuracyPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams;
  const meta = await getMeta();
  const rawCutoff = first(sp.cutoff);
  const cutoff = isCutoff(rawCutoff) ? rawCutoff : meta.default_decision_cutoff.slice(0, 5);

  const [acc, horizon] = await Promise.all([getDayAheadAccuracy(cutoff), getHorizonAccuracy()]);
  const s = acc.stats;
  const scored = acc.daily.filter((d) => d.bias_mw != null);
  const overDays = scored.filter((d) => d.bias_mw! > 0).length;
  const worst = scored.reduce<(typeof scored)[number] | undefined>(
    (w, d) => (w == null || d.mae_mw! > w.mae_mw! ? d : w),
    undefined,
  );
  const adj = acc.adjusted_stats;
  const improvement = s && adj ? (1 - adj.mae_mw / s.mae_mw) * 100 : null;
  const coverage = acc.band_coverage_pct;
  const [nearest, farthest] = [horizon.buckets.at(0), horizon.buckets.at(-1)];

  const findings: React.ReactNode[] = [];
  if (s) {
    findings.push(
      <>
        Forecasts ran {s.bias_mw >= 0 ? "high" : "low"} on{" "}
        <strong>
          {s.bias_mw >= 0 ? overDays : scored.length - overDays} of {scored.length} days
        </strong>
        , by <strong>{gw(Math.abs(s.bias_mw))}</strong> on average. Taken at face value, the raw
        forecast leads to {s.bias_mw >= 0 ? "under" : "over"}-buying.
      </>,
    );
  }
  if (improvement != null && adj && s) {
    findings.push(
      <>
        A trailing {acc.calibration_window_days}-day bias correction cuts day-ahead error by{" "}
        <strong>{improvement.toFixed(0)}%</strong> (MAE {gw(s.mae_mw)} → {gw(adj.mae_mw)}), using
        only data available at each decision.
      </>,
    );
  }
  if (coverage != null) {
    findings.push(
      <>
        The P10–P90 band captured <strong>{pct(coverage)}</strong> of hours against an 80% target
        {coverage >= 78
          ? ", so it is reliable for sizing cover."
          : ": treat it as optimistic and widen the cover."}
      </>,
    );
  }
  if (nearest && farthest && farthest !== nearest) {
    findings.push(
      <>
        Error grows with lead time: MAE <strong>{gw(nearest.stats.mae_mw)}</strong> for forecasts{" "}
        {nearest.horizon_hours} h ahead vs <strong>{gw(farthest.stats.mae_mw)}</strong> at{" "}
        {farthest.horizon_hours} h. A later cutoff, if the market allows, buys accuracy.
      </>,
    );
  }

  return (
    <>
      <PageHeader
        title="How far can the forecast be trusted?"
        description={
          <>
            Error of the forecast actually in hand at the {cutoff} cutoff, for every delivery day
            from {longDate(acc.delivery_window.start)} to {longDate(acc.delivery_window.end)}. Error
            = forecast − actual; positive means wind under-delivered and the shortfall had to be
            bought.
          </>
        }
      >
        <DecisionControls cutoff={cutoff} showDate={false} />
      </PageHeader>

      <Findings items={findings} />

      <KpiGrid>
        <Kpi
          label="Mean absolute error"
          value={gw(s?.mae_mw)}
          hint={`${pct(s?.nmae_pct)} of mean outturn · RMSE ${gw(s?.rmse_mw)}`}
          info="The average size of the raw forecast's miss, in either direction. RMSE weights big misses more heavily."
        />
        <Kpi
          label="Bias-corrected MAE"
          value={gw(adj?.mae_mw)}
          tone="surplus"
          hint={
            improvement != null
              ? `${improvement.toFixed(0)}% lower than raw · out of sample`
              : undefined
          }
          info={`Backtest: each day's forecast minus its average error over the previous ${acc.calibration_window_days} settled days (D-2 and earlier), so no hindsight is used.`}
        />
        <Kpi
          label="Bias"
          value={gw(s?.bias_mw)}
          tone={s && s.bias_mw > 0 ? "short" : "surplus"}
          hint={`Forecast ran high on ${overDays} of ${scored.length} days`}
          info="Average signed miss. Positive means the forecast promised more wind than arrived."
        />
        <Kpi
          label="P90 shortfall cover"
          value={gw(s?.p90_error_mw)}
          tone="short"
          hint={`Worst hour: ${mw(s?.max_shortfall_mw)} short`}
          info="Extra capacity that would have covered the wind shortfall in 9 of 10 hours this month."
        />
      </KpiGrid>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card
          title="Daily error"
          subtitle={
            worst
              ? `Hardest day: ${longDate(worst.delivery_date)} (MAE ${mw(worst.mae_mw)})`
              : undefined
          }
        >
          <DailyErrorChart
            rows={acc.daily.map((d) => ({ day: d.delivery_date, mae: d.mae_mw, bias: d.bias_mw }))}
          />
        </Card>
        <Card
          title="Distribution of hourly errors"
          subtitle="Orange: wind short of forecast (buy more). Green: wind above forecast."
        >
          <HistogramChart bins={acc.error_histogram} />
        </Card>
        <Card title="Error by hour of the delivery day" subtitle="UK local time">
          <HourlyErrorChart rows={acc.by_hour} />
        </Card>
        <Card
          title="Error vs forecast horizon"
          subtitle="All January forecasts, bucketed by how far ahead they were published. Day-ahead decisions use forecasts roughly 15–40 h ahead."
        >
          <HorizonChart buckets={horizon.buckets} marker={24} />
        </Card>
      </div>
    </>
  );
}
