import type { DayAhead } from "@windsight/api-client";

import { expect, gw, gwh, kpi, test } from "./fixtures";

test.describe("Day-ahead decision view", () => {
  test("opens on the latest decision with the forecast in hand at 09:00", async ({ page, api }) => {
    const day = await api<DayAhead>("/api/v1/day-ahead?delivery_date=2026-02-01&cutoff=09:00");

    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Wind for Sun, 1 Feb 2026");
    const brief = page.locator("section", { hasText: "Decision brief" });
    await expect(brief).toContainText("Sat, 31 Jan 2026, 09:00");
    await expect(brief).toContainText(`Plan on at least ${gwh(day.summary!.firm_mwh!)} of wind`);
    await expect(brief).toContainText(`bias-adjusted ${gwh(day.summary!.adjusted_mwh!)}`);
    await expect(brief).toContainText("published 31 Jan, 07:30 (1.5 h old at the cutoff)");
    await expect(brief).toContainText(
      `last ${day.calibration!.days_used} settled days, in which forecasts ran ${gw(day.calibration!.bias_mw)} high`,
    );

    await expect(kpi(page, "Expected wind")).toContainText(gwh(day.summary!.adjusted_mwh!));
    await expect(kpi(page, "Firm wind (P90)")).toContainText(gwh(day.summary!.firm_mwh!));
    await expect(kpi(page, "Outturn (hindsight)")).toContainText(gwh(day.actual_mwh!));
    await expect(page.locator(".recharts-surface").first()).toBeVisible();
    await expect(page.getByLabel("Next day")).toBeDisabled(); // last day of the pilot
  });

  test("stepping back a day reloads the brief for that delivery day", async ({ page, api }) => {
    const day = await api<DayAhead>("/api/v1/day-ahead?delivery_date=2026-01-31&cutoff=09:00");
    await page.goto("/");

    await page.getByLabel("Previous day").click();

    await expect(page).toHaveURL(/decision=2026-01-30/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Wind for Sat, 31 Jan 2026");
    await expect(page.getByText("Plan on at least")).toContainText(gwh(day.summary!.firm_mwh!));
  });

  test("a later cutoff picks a newer forecast run", async ({ page, api }) => {
    const at9 = await api<DayAhead>("/api/v1/day-ahead?delivery_date=2026-01-15&cutoff=09:00");
    const at12 = await api<DayAhead>("/api/v1/day-ahead?delivery_date=2026-01-15&cutoff=12:00");
    expect(at12.forecast_publish_time! > at9.forecast_publish_time!).toBeTruthy();
    // January is GMT, so UK clock time == UTC
    const runAt = (iso: string) => `14 Jan, ${iso.slice(11, 16)}`;

    await page.goto("/?decision=2026-01-14");
    const source = page.getByText("Based on the WINDFOR run");
    await expect(source).toContainText(runAt(at9.forecast_publish_time!));

    await page.getByLabel("Decision cutoff").selectOption("12:00");

    await expect(page).toHaveURL(/cutoff=12%3A00|cutoff=12:00/);
    await expect(source).toContainText(runAt(at12.forecast_publish_time!));
    await expect(page.getByText("Decision brief")).toContainText("12:00");
  });

  test("decision date picker navigates and invalid links fall back safely", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Decision day (D-1)").fill("2026-01-10");
    await expect(page).toHaveURL(/decision=2026-01-10/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Wind for Sun, 11 Jan 2026");

    await page.goto("/?decision=2030-01-01&cutoff=99:99");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Wind for Sun, 1 Feb 2026");
    await expect(page.getByLabel("Decision cutoff")).toHaveValue("09:00");

    await page.goto("/?decision=2025-06-01");
    await expect(page.getByLabel("Previous day")).toBeDisabled();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Wind for Fri, 2 Jan 2026");
  });

  test("toggles hide the hindsight outturn and the adjusted line", async ({ page }) => {
    await page.goto("/");
    const actuals = page.getByRole("button", { name: "Show actuals" });
    const adjusted = page.getByRole("button", { name: "Bias-adjusted" });
    const lines = page.locator(".recharts-line");
    await expect(lines).toHaveCount(3); // forecast, bias-adjusted, actual
    const before = 3;

    await actuals.click();
    await expect(actuals).toHaveAttribute("aria-pressed", "false");
    await expect(lines).toHaveCount(before - 1);

    await adjusted.click();
    await expect(adjusted).toHaveAttribute("aria-pressed", "false");
    await expect(lines).toHaveCount(before - 2);

    await actuals.click();
    await expect(actuals).toHaveAttribute("aria-pressed", "true");
    await expect(lines).toHaveCount(before - 1);
  });

  test("hourly table and CSV export match the API", async ({ page, api }) => {
    const day = await api<DayAhead>("/api/v1/day-ahead?delivery_date=2026-02-01&cutoff=09:00");
    await page.goto("/");

    await page.getByText("Hourly values").click();
    await expect(page.locator("details tbody tr")).toHaveCount(24);

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "CSV" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("windsight-day-ahead-2026-02-01-0900.csv");
    const lines = (await readDownload(download)).split("\n");
    expect(lines[0]).toBe(
      "start_time_utc,forecast_mw,adjusted_mw,p10_mw,p90_mw,actual_mw,error_mw",
    );
    expect(lines).toHaveLength(day.points.length + 1);
    expect(lines[1]?.split(",")[0]).toBe(day.points[0]?.start_time);
  });
});

async function readDownload(download: import("@playwright/test").Download) {
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks).toString("utf8");
}
