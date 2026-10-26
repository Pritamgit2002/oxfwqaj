"use client";

export function Toggle({
  pressed,
  onChange,
  color,
  children,
}: {
  pressed: boolean;
  onChange: (next: boolean) => void;
  /** Swatch colour matching the chart series this toggle controls. */
  color: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={() => onChange(!pressed)}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
        pressed ? "border-ink/20 bg-canvas text-ink" : "border-line text-muted hover:text-ink"
      }`}
    >
      <span
        className="size-2 rounded-full"
        style={{
          background: pressed ? color : "transparent",
          boxShadow: `inset 0 0 0 1.5px ${color}`,
        }}
      />
      {children}
    </button>
  );
}
