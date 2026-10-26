import { getMeta } from "@/lib/api";
import { dateTime } from "@/lib/format";

/** Header chip showing data freshness; degrades to "API offline" instead of breaking the page. */
export async function DataStatus() {
  let label: string;
  let ok = true;
  try {
    const { data: coverage } = await getMeta();
    label = coverage.last_ingested_at
      ? `${coverage.forecasts.runs} forecast runs · refreshed ${dateTime(coverage.last_ingested_at)}`
      : "No data ingested yet";
    ok = coverage.forecasts.runs > 0;
  } catch {
    label = "API offline";
    ok = false;
  }
  return (
    <span
      className="hidden items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-xs text-muted lg:inline-flex"
      title="Elexon data coverage and last successful ingestion"
    >
      <span aria-hidden className={`size-1.5 rounded-full ${ok ? "bg-surplus" : "bg-short"}`} />
      {label}
    </span>
  );
}
