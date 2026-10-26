import "server-only";

import { createApiClient } from "@windsight/api-client";

/**
 * Server-side API access. Pages are server components, so the browser only ever talks to
 * Next.js; the Python API can stay on a private network (e.g. `http://api:8000` in Docker).
 */
const api = createApiClient(process.env.API_BASE_URL ?? "http://localhost:8000", {
  cache: "no-store",
});

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result: Awaited<typeof request>;
  try {
    result = await request;
  } catch (cause) {
    throw new ApiError(`Windsight API is unreachable (${String(cause)})`);
  }
  if (result.data === undefined) {
    const detail = (result.error as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(
      typeof detail === "string" ? detail : `API request failed (${result.response.status})`,
      result.response.status,
    );
  }
  return result.data;
}

export const getMeta = () => unwrap(api.GET("/api/v1/meta"));

export const getDayAhead = (deliveryDate: string, cutoff: string) =>
  unwrap(
    api.GET("/api/v1/day-ahead", { params: { query: { delivery_date: deliveryDate, cutoff } } }),
  );

export const getDayAheadAccuracy = (cutoff: string) =>
  unwrap(api.GET("/api/v1/accuracy/day-ahead", { params: { query: { cutoff } } }));

export const getHorizonAccuracy = () => unwrap(api.GET("/api/v1/accuracy/horizon"));

export const getSeries = (start: string, end: string, horizonHours: number) =>
  unwrap(
    api.GET("/api/v1/series", {
      params: { query: { start, end, horizon_hours: horizonHours } },
    }),
  );
