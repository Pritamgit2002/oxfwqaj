export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-muted">
      {label}
      {children}
    </label>
  );
}

export const inputClass =
  "rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm text-ink shadow-sm focus:border-forecast focus:outline-none";
