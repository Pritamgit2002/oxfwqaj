export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: React.ReactNode;
  /** Right-aligned controls in the header (toggles, downloads). */
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-4 sm:p-5 ${className}`}>
      {title && (
        <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div className="max-w-2xl">
            <h2 className="text-sm font-semibold">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {action && <div className="flex flex-wrap items-center gap-2">{action}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
