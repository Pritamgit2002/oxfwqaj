import { test as base, expect, type Page } from "@playwright/test";

import type { DayAhead, DayAheadAccuracy, Meta, Series } from "@windsight/api-client";

const API_URL = process.env.E2E_API_URL ?? `http://127.0.0.1:${process.env.E2E_API_PORT ?? 8200}`;

/** Direct access to the API, to check the UI shows exactly what the backend computed. */
export const test = base.extend<{
  api: <T extends DayAhead | DayAheadAccuracy | Meta | Series>(path: string) => Promise<T>;
}>({
  api: async ({ request }, provide) => {
    await provide(async (path) => {
      const response = await request.get(`${API_URL}${path}`);
      expect(response.ok(), `${path} -> ${response.status()}`).toBeTruthy();
      return response.json();
    });
  },
});

export { expect };

/** Same formatting as src/lib/format.ts (en-GB, one decimal, MW -> GW). */
const nf1 = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const gwh = (mwh: number) => `${nf1.format(mwh / 1000)} GWh`;
export const gw = (mw: number) => `${nf1.format(mw / 1000)} GW`;

/** A KPI card: its text starts with the label (the info tooltip follows it). */
export const kpi = (page: Page, label: string) =>
  page.locator("div.rounded-xl").filter({ hasText: new RegExp(`^${escapeRe(label)}`) });

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
