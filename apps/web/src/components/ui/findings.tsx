export function Findings({ items }: { items: React.ReactNode[] }) {
  if (!items.length) return null;
  return (
    <section className="mb-4 rounded-xl border border-line bg-surface p-4 sm:p-5">
      <h2 className="text-sm font-semibold">Key findings</h2>
      <ul className="mt-2 grid gap-x-6 gap-y-2 text-sm text-ink/90 md:grid-cols-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-forecast" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
