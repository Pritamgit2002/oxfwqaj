"use client";

export default function ErrorBoundary({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-950">
      <h1 className="text-lg font-semibold">Couldn’t load this view</h1>
      <p className="mt-1 text-sm">{error.message}</p>
      <p className="mt-1 text-sm">
        Check the API is running and that data has been ingested (<code>windsight ingest</code>).
      </p>
      <button
        onClick={reset}
        className="mt-4 rounded-md bg-ink px-3 py-1.5 text-sm text-white hover:opacity-90"
      >
        Try again
      </button>
    </div>
  );
}
