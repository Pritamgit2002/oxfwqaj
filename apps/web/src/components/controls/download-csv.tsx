"use client";

type Cell = string | number | null | undefined;

const escape = (cell: Cell) => {
  if (cell == null) return "";
  const s = typeof cell === "number" ? String(Math.round(cell * 100) / 100) : cell;
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

/** Exports data already on the page; no extra API call. */
export function DownloadCsv({
  filename,
  header,
  rows,
}: {
  filename: string;
  header: string[];
  rows: Cell[][];
}) {
  const download = () => {
    const csv = [header, ...rows].map((r) => r.map(escape).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <button
      type="button"
      onClick={download}
      className="inline-flex items-center gap-1 rounded-md border border-line px-2.5 py-1 text-xs font-medium text-muted hover:border-muted hover:text-ink"
    >
      <span aria-hidden>↓</span> CSV
    </button>
  );
}
