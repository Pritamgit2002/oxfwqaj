"use client";

import { addDays } from "@/lib/dates";

import { Field, inputClass } from "./field";
import { useQueryState } from "./use-query-state";

export const CUTOFFS = ["06:00", "08:00", "09:00", "10:00", "11:00", "12:00"];

const stepClass =
  "rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm text-muted shadow-sm hover:text-ink disabled:cursor-not-allowed disabled:opacity-40";

export function DecisionControls({
  decisionDate,
  cutoff,
  min,
  max,
  showDate = true,
}: {
  decisionDate?: string;
  cutoff: string;
  min?: string;
  max?: string;
  showDate?: boolean;
}) {
  const { set, pending } = useQueryState();
  const step = (days: number) => decisionDate && set({ decision: addDays(decisionDate, days) });

  return (
    <div className={`flex flex-wrap items-end gap-3 ${pending ? "opacity-60" : ""}`}>
      {showDate && (
        <Field label="Decision day (D-1)">
          <div className="flex gap-1">
            <button
              type="button"
              aria-label="Previous day"
              className={stepClass}
              disabled={!decisionDate || (!!min && decisionDate <= min)}
              onClick={() => step(-1)}
            >
              ‹
            </button>
            <input
              type="date"
              className={inputClass}
              value={decisionDate}
              min={min}
              max={max}
              onChange={(e) => e.target.value && set({ decision: e.target.value })}
            />
            <button
              type="button"
              aria-label="Next day"
              className={stepClass}
              disabled={!decisionDate || (!!max && decisionDate >= max)}
              onClick={() => step(1)}
            >
              ›
            </button>
          </div>
        </Field>
      )}
      <Field label="Decision cutoff">
        <select
          className={inputClass}
          value={cutoff}
          onChange={(e) => set({ cutoff: e.target.value })}
        >
          {(CUTOFFS.includes(cutoff) ? CUTOFFS : [...CUTOFFS, cutoff].sort()).map((c) => (
            <option key={c} value={c}>
              {c} UK time
            </option>
          ))}
        </select>
      </Field>
    </div>
  );
}
