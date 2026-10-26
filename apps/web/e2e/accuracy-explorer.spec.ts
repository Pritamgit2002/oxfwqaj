import type { DayAheadAccuracy, Meta, Series } from "@windsight/api-client";

import { expect, gw, kpi, test } from "./fixtures";

test.describe("Accuracy view", () => {
  test("key findings and KPIs come from the backtest", async ({ page, api }) => {
    const acc = await api<DayAheadAccuracy>("/api/v1/accuracy/day-ahead?cutoff=09:00");
    const s = acc.stats!;
    const adj = acc.adjusted_stats!;
    const overDays = acc.daily.filter((d) => (d.bias_mw ?? 0) > 0).length;
    const improvement = ((1 - adj.mae_mw / s.mae_mw) * 100).toFixed(0);

    await page.goto("/accuracy");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "How far can the forecast be trusted?",
    );
    const findings = page.locator("section", { hasText: "Key findings" }).locator("li");
    await expect(findings).toHaveCount(4);
    await expect(findings.nth(0)).toContainText(`${overDays} of ${acc.daily.length} days`);
    await expect(findings.nth(1)).toContainText(`${improvement}%`);
    await expect(findings.nth(1)).toContainText(`${gw(s.mae_mw)} → ${gw(adj.mae_mw)}`);
    await expect(findings.nth(2)).toContainText("against an 80% target");
    await expect(findings.nth(3)).toContainText("Error grows with lead time");

    await expect(kpi(page, "Mean absolute error")).toContainText(gw(s.mae_mw));
    await expect(page.getByText("Hardest day: Wed, 28 Jan 2026")).toBeVisible();
    await expect(page.locator(".recharts-wrapper")).toHaveCount(4);
  });

  test("cutoff selector recomputes the accuracy", async ({ page, api }) => {
    const acc = await api<DayAheadAccuracy>("/api/v1/accuracy/day-ahead?cutoff=12:00");
    await page.goto("/accuracy");

    await page.getByLabel("Decision cutoff").selectOption("12:00");

    await expect(page).toHaveURL(/cutoff=12/);
    await expect(
      page.getByText("Error of the forecast actually in hand at the 12:00"),
    ).toBeVisible();
    await expect(kpi(page, "Mean absolute error")).toContainText(gw(acc.stats!.mae_mw));
  });
});

test.describe("Horizon explorer", () => {
  test("shows the first week at 24 h and follows the horizon slider", async ({ page, api }) => {
    const meta = await api<Meta>("/api/v1/meta");
    const at6 = await api<Series>(
      "/api/v1/series?start=2026-01-02T00:00:00Z&end=2026-01-09T00:00:00Z&horizon_hours=6",
    );

    await page.goto("/explorer");
    await expect(page.getByLabel("From")).toHaveValue(meta.delivery_window.start);
    await expect(page.getByLabel("To")).toHaveValue("2026-01-08");
    await expect(page.getByText("Actual vs forecast published ≥ 24 h ahead")).toBeVisible();

    const slider = page.getByRole("slider");
    await slider.focus();
    for (let i = 0; i < 18; i++) await slider.press("ArrowLeft");

    await expect(page).toHaveURL(/horizon=6/);
    await expect(page.getByText("Actual vs forecast published ≥ 6 h ahead")).toBeVisible();
    await expect(kpi(page, "MAE")).toContainText(gw(at6.stats!.mae_mw));
  });

  test("CSV export follows the selected range", async ({ page }) => {
    await page.goto("/explorer?start=2026-01-10&end=2026-01-10&horizon=12");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "CSV" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("windsight-horizon-12h-2026-01-10-to-2026-01-10.csv");
  });
});

test.describe("App shell", () => {
  test("navigation keeps the active tab marked", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation");
    await expect(nav.getByRole("link", { name: "Day-ahead" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await nav.getByRole("link", { name: "Accuracy" }).click();
    await expect(page).toHaveURL(/\/accuracy$/);
    await expect(nav.getByRole("link", { name: "Accuracy" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await nav.getByRole("link", { name: "Horizon explorer" }).click();
    await expect(page).toHaveURL(/\/explorer$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Horizon explorer");
  });

  test("header shows data freshness from the API", async ({ page, api }) => {
    const meta = await api<Meta>("/api/v1/meta");
    await page.goto("/");
    await expect(
      page.getByTitle("Elexon data coverage and last successful ingestion"),
    ).toContainText(`${meta.data.forecasts.runs} forecast runs`);
  });

  test("web health endpoint responds", async ({ request }) => {
    const response = await request.get("/api/health");
    expect(await response.json()).toEqual({ status: "ok" });
  });

  test("no console errors while using the app", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));
    for (const path of ["/", "/accuracy", "/explorer"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
    }
    expect(errors).toEqual([]);
  });
});
