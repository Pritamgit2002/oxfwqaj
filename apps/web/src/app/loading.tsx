export default function Loading() {
  return (
    <div className="animate-pulse space-y-4" aria-busy="true" aria-label="Loading">
      <div className="h-8 w-1/3 rounded bg-line" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="h-24 rounded-xl bg-line" />
        ))}
      </div>
      <div className="h-96 rounded-xl bg-line" />
    </div>
  );
}
