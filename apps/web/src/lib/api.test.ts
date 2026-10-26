/**
 * Integration of the server-side data layer with the generated, typed API client: real
 * openapi-fetch request building and response handling, with only the network stubbed.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const requests: Request[] = [];
let respond: (req: Request) => Response | Promise<Response>;

beforeEach(() => {
  requests.length = 0;
  vi.stubEnv("API_BASE_URL", "http://api.test:8000");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request) => {
      requests.push(input);
      return respond(input);
    }),
  );
  vi.resetModules(); // api.ts reads API_BASE_URL at import time
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const load = () => import("./api");
const urlOf = (i: number) => new URL(requests[i]!.url);

describe("API data layer", () => {
  it("calls the configured API with typed query parameters", async () => {
    respond = () => json({ delivery_date: "2026-01-15", points: [] });
    const { getDayAhead } = await load();

    const day = await getDayAhead("2026-01-15", "09:00");

    expect(day.delivery_date).toBe("2026-01-15");
    const url = urlOf(0);
    expect(url.origin).toBe("http://api.test:8000");
    expect(url.pathname).toBe("/api/v1/day-ahead");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      delivery_date: "2026-01-15",
      cutoff: "09:00",
    });
    expect(requests[0]!.method).toBe("GET");
  });

  it("builds every endpoint the pages use", async () => {
    respond = () => json({});
    const api = await load();

    await api.getMeta();
    await api.getDayAheadAccuracy("10:00");
    await api.getHorizonAccuracy();
    await api.getSeries("2026-01-02T00:00:00Z", "2026-01-09T00:00:00Z", 24);

    expect(requests.map((r) => new URL(r.url).pathname)).toEqual([
      "/api/v1/meta",
      "/api/v1/accuracy/day-ahead",
      "/api/v1/accuracy/horizon",
      "/api/v1/series",
    ]);
    expect(urlOf(1).searchParams.get("cutoff")).toBe("10:00");
    expect(Object.fromEntries(urlOf(3).searchParams)).toEqual({
      start: "2026-01-02T00:00:00Z",
      end: "2026-01-09T00:00:00Z",
      horizon_hours: "24",
    });
  });

  it("surfaces the API's validation message", async () => {
    respond = () =>
      json({ detail: "delivery_date must be between 2026-01-02 and 2026-02-01" }, 422);
    const { getDayAhead, ApiError } = await load();

    const error = await getDayAhead("2026-03-01", "09:00").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      message: "delivery_date must be between 2026-01-02 and 2026-02-01",
    });
  });

  it("falls back to the status code for non-string error bodies", async () => {
    respond = () => json({ detail: [{ msg: "field required" }] }, 500);
    const { getMeta } = await load();
    await expect(getMeta()).rejects.toMatchObject({
      status: 500,
      message: "API request failed (500)",
    });
  });

  it("reports an unreachable API distinctly", async () => {
    respond = () => {
      throw new TypeError("fetch failed");
    };
    const { getMeta } = await load();
    await expect(getMeta()).rejects.toThrow(/Windsight API is unreachable/);
  });
});
