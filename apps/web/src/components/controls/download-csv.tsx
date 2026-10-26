"use client";

import { type CsvCell, toCsv } from "@/lib/csv";

/** Exports data already on the page; no extra API call. */
export function DownloadCsv({
  filename,
  header,
  rows,
}: {
  filename: string;
  header: string[];
  rows: CsvCell[][];
}) {
  const download = () => {
    const csv = toCsv(header, rows);
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
