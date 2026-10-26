import { DayAheadChart } from "@/components/charts/day-ahead-chart";
import { DecisionControls } from "@/components/controls/decision-controls";
import { Card } from "@/components/ui/card";
import { Kpi, KpiGrid } from "@/components/ui/kpi";
import { PageHeader } from "@/components/ui/page-header";
import { getDayAhead, getMeta } from "@/lib/api";
import { addDays, clampDate, first, isCutoff, type SearchParams } from "@/lib/dates";
import { clock, dateTime, gw, gwh, hours, longDate, mw } from "@/lib/format";

export default async function DayAheadPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams;
  const meta = await getMeta();
  const rawCutoff = first(sp.cutoff);
  const cutoff = isCutoff(rawCutoff) ? rawCutoff : meta.default_decision_cutoff.slice(0, 5);
  // Default to the most recent decision in the pilot: "what do I buy for tomorrow?"
  const decision = clampDate(
    first(sp.decision),
    meta.decision_window.start,
    meta.decision_window.end,
  );
  const delivery = addDays(decision, 1);

  const day = await getDayAhead(delivery, cutoff);
  const { summary, calibration: cal } = day;
  const hourly = day.points.filter((p) => p.forecast_mw != null);

  return (
    <>
      <PageHeader
        title={<>Wind for {longDate(delivery)}</>}
        description={
          <>
            The latest national wind forecast available when the day-ahead purchase is made on{" "}
            {longDate(decision)} at {cutoff}, corrected for its recent bias and compared with what
            was actually generated.
          </>
        }
      >
        <DecisionControls
          decisionDate={decision}
          cutoff={cutoff}
          min={meta.decision_window.start}
          max={meta.decision_window.end}
        />
      </PageHeader>

      {summary && day.forecast_publish_time ? (
        <section className="mb-4 rounded-xl border border-cyan-200 bg-cyan-50/70 p-4 sm:p-5">
          <p className="text-xs font-semibold tracking-wide text-cyan-800 uppercase">
            Decision brief · {longDate(decision)}, {cutoff}
          </p>
          <p className="mt-1 text-lg font-semibold sm:text-xl">
            {summary.firm_mwh != null ? (
              <>
                Plan on at least {gwh(summary.firm_mwh)} of wind for {longDate(delivery)}
              </>
            ) : (
              <>
                Expect {gwh(summary.forecast_mwh)} of wind for {longDate(delivery)}
              </>
            )}
          </p>
          <p className="mt-1 text-sm text-ink/80">
            Raw forecast {gwh(summary.forecast_mwh)}
            {summary.adjusted_mwh != null && <>, bias-adjusted {gwh(summary.adjusted_mwh)}</>}.
            Lowest wind {clock(summary.trough_start)}–{clock(summary.trough_end)} (
            {gw(summary.trough_mw)}): the hours with the most residual demand to buy.
          </p>
          <p className="mt-2 text-xs text-muted">
            Based on the WINDFOR run published {dateTime(day.forecast_publish_time)} (
            {hours(day.forecast_age_hours)} old at the cutoff).{" "}
            {cal
              ? `Calibrated on the last ${cal.days_used} settled days, in which forecasts ran ${gw(Math.abs(cal.bias_mw))} ${cal.bias_mw >= 0 ? "high" : "low"}.`
              : "No settled history yet to calibrate against."}
          </p>
        </section>
      ) : (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          No forecast run covering this delivery day had been published by the cutoff.
        </div>
      )}

      <KpiGrid>
        <Kpi
          label="Expected wind"
          value={gwh(summary?.adjusted_mwh ?? summary?.forecast_mwh)}
          hint={summary ? `raw forecast ${gwh(summary.forecast_mwh)}` : undefined}
          info="Forecast energy for the delivery day after removing the forecast's average error over recent settled days."
        />
        <Kpi
          label="Firm wind (P90)"
          value={gwh(summary?.firm_mwh)}
          tone="short"
          hint="Exceeded in 9 of 10 hours; size purchases against this"
          info="Hour by hour, the wind level the outturn beat in 90% of recent hours, added up over the day. Buying against this floor leaves a 1-in-10 chance of being short in any hour."
        />
        <Kpi
          label="Lowest-wind window"
          value={gw(summary?.trough_mw)}
          hint={
            summary
              ? `${clock(summary.trough_start)}–${clock(summary.trough_end)} · peak ${gw(summary.peak_mw)}`
              : undefined
          }
          info="The two consecutive hours with the least forecast wind: where the most power must be bought from other sources."
        />
        <Kpi
          label="Outturn (hindsight)"
          value={gwh(day.actual_mwh)}
          hint={
            day.stats
              ? `MAE ${mw(day.stats.mae_mw)} · bias ${mw(day.stats.bias_mw)}`
              : "Actuals not yet available"
          }
          info="What wind actually generated, known only after the fact. MAE is the average size of the raw forecast's miss; bias is the average signed miss (positive = forecast too high)."
        />
      </KpiGrid>

      <Card
        className="mt-4"
        title="Forecast at decision time vs actual generation"
        subtitle={
          cal
            ? `Hourly forecast (dashed), bias-adjusted (violet), half-hourly outturn (solid). The band is the P10–P90 range from the last ${cal.days_used} settled days' errors.`
            : "Hourly forecast (dashed) and half-hourly outturn (solid)."
        }
      >
        <DayAheadChart
          points={day.points}
          trough={summary ? [summary.trough_start, summary.trough_end] : undefined}
          calibrationDays={cal?.days_used}
          filename={`windsight-day-ahead-${delivery}-${cutoff.replace(":", "")}.csv`}
        />
      </Card>

      <details className="mt-4 rounded-xl border border-line bg-surface p-4 text-sm">
        <summary className="cursor-pointer font-semibold">Hourly values</summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-right tabular-nums">
            <thead className="text-xs text-muted">
              <tr>
                <th className="py-1 text-left">Hour</th>
                <th>Forecast</th>
                <th>Adjusted</th>
                <th>Actual</th>
                <th>Error (f − a)</th>
              </tr>
            </thead>
            <tbody>
              {hourly.map((p) => (
                <tr key={p.start_time} className="border-t border-line">
                  <td className="py-1 text-left">{clock(p.start_time)}</td>
                  <td>{mw(p.forecast_mw)}</td>
                  <td className="text-adjusted">{mw(p.adjusted_mw)}</td>
                  <td>{mw(p.actual_mw)}</td>
                  <td className={p.error_mw != null && p.error_mw > 0 ? "text-short" : ""}>
                    {mw(p.error_mw)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
