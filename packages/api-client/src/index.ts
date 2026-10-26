import createClient, { type ClientOptions } from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };

type Schemas = components["schemas"];

export type Meta = Schemas["MetaOut"];
export type ErrorStats = Schemas["ErrorStatsOut"];
export type DayAhead = Schemas["DayAheadOut"];
export type DayAheadPoint = Schemas["DayAheadPoint"];
export type DayAheadSummary = Schemas["DayAheadSummary"];
export type Calibration = Schemas["CalibrationOut"];
export type DayAheadAccuracy = Schemas["DayAheadAccuracyOut"];
export type DailyAccuracy = Schemas["DailyAccuracy"];
export type HourlyAccuracy = Schemas["HourlyAccuracy"];
export type HistogramBin = Schemas["HistogramBinOut"];
export type HorizonAccuracy = Schemas["HorizonAccuracyOut"];
export type HorizonBucket = Schemas["HorizonBucket"];
export type Series = Schemas["SeriesOut"];
export type SeriesPoint = Schemas["SeriesPoint"];

export type ApiClient = ReturnType<typeof createApiClient>;

export function createApiClient(baseUrl: string, options: Omit<ClientOptions, "baseUrl"> = {}) {
  return createClient<paths>({ baseUrl, ...options });
}
