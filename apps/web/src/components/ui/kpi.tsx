import { InfoTip } from "./info-tip";

type Tone = "default" | "short" | "surplus";

const TONES: Record<Tone, string> = {
  default: "text-ink",
  short: "text-short",
  surplus: "text-surplus",
};

export function Kpi({
  label,
  value,
  hint,
  info,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: React.ReactNode;
  /** Plain-English explanation of the metric, shown on hover/focus. */
  info?: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="relative rounded-xl border border-line bg-surface p-4">
      <div className="flex items-center text-xs font-medium tracking-wide text-muted uppercase">
        {label}
        {info && <InfoTip>{info}</InfoTip>}
      </div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${TONES[tone]}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function KpiGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{children}</div>;
}
