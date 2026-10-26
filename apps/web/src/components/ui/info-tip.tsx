/**
 * Plain-English explanation on hover/focus. Positions against the nearest `relative`
 * ancestor (e.g. a KPI card), so it never overflows the viewport on small screens.
 */
export function InfoTip({ children }: { children: React.ReactNode }) {
  return (
    <span className="group inline-flex align-middle">
      <button
        type="button"
        aria-label="What does this mean?"
        className="ml-1 inline-flex size-4 cursor-help items-center justify-center rounded-full border border-line text-[10px] leading-none font-semibold text-muted normal-case hover:border-muted hover:text-ink focus-visible:ring-2 focus-visible:ring-forecast focus-visible:outline-none"
      >
        i
      </button>
      <span
        role="tooltip"
        className="absolute inset-x-2 top-full z-20 mt-1 hidden rounded-md bg-ink px-3 py-2 text-xs font-normal tracking-normal text-white normal-case shadow-lg group-focus-within:block group-hover:block"
      >
        {children}
      </span>
    </span>
  );
}
