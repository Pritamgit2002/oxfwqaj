"use client";

import { useEffect, useState } from "react";

import { Field, inputClass } from "./field";
import { useQueryState } from "./use-query-state";

export function ExplorerControls({
  start,
  end,
  horizon,
  min,
  max,
  maxHorizon,
}: {
  start: string;
  end: string;
  horizon: number;
  min: string;
  max: string;
  maxHorizon: number;
}) {
  const { set, pending } = useQueryState();
  const [draft, setDraft] = useState(horizon);

  // Debounce the slider so dragging doesn't fire a request per step.
  useEffect(() => {
    if (draft === horizon) return;
    const id = setTimeout(() => set({ horizon: String(draft) }), 250);
    return () => clearTimeout(id);
  }, [draft, horizon, set]);

  return (
    <div className={`flex flex-wrap items-end gap-3 ${pending ? "opacity-60" : ""}`}>
      <Field label="From">
        <input
          type="date"
          className={inputClass}
          value={start}
          min={min}
          max={end}
          onChange={(e) => e.target.value && set({ start: e.target.value })}
        />
      </Field>
      <Field label="To">
        <input
          type="date"
          className={inputClass}
          value={end}
          min={start}
          max={max}
          onChange={(e) => e.target.value && set({ end: e.target.value })}
        />
      </Field>
      <Field label={`Forecast horizon: ≥ ${draft} h ahead`}>
        <input
          type="range"
          className="w-56 accent-forecast"
          min={0}
          max={maxHorizon}
          step={1}
          value={draft}
          onChange={(e) => setDraft(Number(e.target.value))}
        />
      </Field>
    </div>
  );
}
