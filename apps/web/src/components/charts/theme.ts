// Mirrors the @theme tokens in globals.css (SVG attributes can't read Tailwind classes).
export const C = {
  actual: "#0f172a",
  forecast: "#0e7490",
  band: "#67e8f9",
  adjusted: "#7c3aed",
  short: "#c2410c",
  surplus: "#15803d",
  grid: "#e2e8f0",
  muted: "#64748b",
} as const;

export const axis = {
  stroke: C.muted,
  fontSize: 12,
  tickLine: false,
  axisLine: { stroke: C.grid },
} as const;

export const gwTick = (v: number) => `${(v / 1000).toFixed(0)}`;

/** Wide enough for "−12 GW" so tick labels aren't clipped. */
export const Y_AXIS_WIDTH = 64;
