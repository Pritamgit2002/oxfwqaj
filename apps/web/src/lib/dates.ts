/** Calendar-date helpers on "YYYY-MM-DD" strings (UTC arithmetic, no local-time drift). */

export const addDays = (isoDate: string, days: number) => {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
};

export const clampDate = (isoDate: string | undefined, min: string, max: string) => {
  if (!isoDate || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return max;
  return isoDate < min ? min : isoDate > max ? max : isoDate;
};

export const isCutoff = (value: string | undefined): value is string =>
  !!value && /^([01]\d|2[0-3]):[0-5]\d$/.test(value);

export type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export const first = (value: string | string[] | undefined) =>
  Array.isArray(value) ? value[0] : value;
