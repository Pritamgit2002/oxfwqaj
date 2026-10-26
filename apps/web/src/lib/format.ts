export const MARKET_TZ = "Europe/London";

const nf0 = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const mw = (value: number | null | undefined) =>
  value == null ? "–" : `${nf0.format(value)} MW`;

export const gw = (valueMw: number | null | undefined) =>
  valueMw == null ? "–" : `${nf1.format(valueMw / 1000)} GW`;

export const gwh = (valueMwh: number | null | undefined) =>
  valueMwh == null ? "–" : `${nf1.format(valueMwh / 1000)} GWh`;

export const pct = (value: number | null | undefined) =>
  value == null ? "–" : `${nf1.format(value)}%`;

export const hours = (value: number | null | undefined) =>
  value == null ? "–" : `${nf1.format(value)} h`;

const dateFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: MARKET_TZ,
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});
const timeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: MARKET_TZ,
  hour: "2-digit",
  minute: "2-digit",
});
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: MARKET_TZ,
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

/** Formats a calendar date ("2026-01-15") without shifting it through a timezone. */
export const longDate = (isoDate: string) => dateFmt.format(new Date(`${isoDate}T12:00:00Z`));
export const clock = (iso: string | number) => timeFmt.format(new Date(iso));
export const dateTime = (iso: string | number) => dateTimeFmt.format(new Date(iso));
