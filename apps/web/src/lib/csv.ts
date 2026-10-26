export type CsvCell = string | number | null | undefined;

/** RFC 4180 quoting; numbers rounded to 2 dp, missing values left empty. */
export const csvCell = (cell: CsvCell) => {
  if (cell == null) return "";
  const s = typeof cell === "number" ? String(Math.round(cell * 100) / 100) : cell;
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export const toCsv = (header: string[], rows: CsvCell[][]) =>
  [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\n");
