/**
 * Scripted product walkthrough, recorded as the README demo video.
 *
 * Each `say()` shows a subtitle bar in the page (burned into the video) and logs its timing,
 * so demo/render.mjs can also write .srt/.vtt files and a soft subtitle track.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

type Cue = { start: number; end: number; text: string };

/** Visible cursor and subtitle bar; injected into every document the page loads. */
function installOverlay() {
  const install = () => {
    if (document.getElementById("__demo_cursor")) return;
    const cursor = document.createElement("div");
    cursor.id = "__demo_cursor";
    Object.assign(cursor.style, {
      position: "fixed",
      width: "22px",
      height: "22px",
      margin: "-11px 0 0 -11px",
      borderRadius: "50%",
      background: "rgba(8, 145, 178, 0.28)",
      border: "2px solid rgb(8, 145, 178)",
      zIndex: "2147483647",
      pointerEvents: "none",
      transition: "transform 120ms ease",
    });
    const last = JSON.parse(sessionStorage.getItem("__demo_pos") ?? "[640,360]");
    cursor.style.left = `${last[0]}px`;
    cursor.style.top = `${last[1]}px`;
    document.documentElement.appendChild(cursor);
    addEventListener(
      "mousemove",
      (e) => {
        cursor.style.left = `${e.clientX}px`;
        cursor.style.top = `${e.clientY}px`;
        sessionStorage.setItem("__demo_pos", JSON.stringify([e.clientX, e.clientY]));
      },
      true,
    );
    addEventListener("mousedown", () => (cursor.style.transform = "scale(0.6)"), true);
    addEventListener("mouseup", () => (cursor.style.transform = ""), true);

    const bar = document.createElement("div");
    bar.id = "__demo_caption";
    Object.assign(bar.style, {
      position: "fixed",
      left: "50%",
      bottom: "28px",
      transform: "translateX(-50%)",
      maxWidth: "1040px",
      padding: "10px 18px",
      borderRadius: "10px",
      background: "rgba(15, 23, 42, 0.88)",
      color: "white",
      font: "500 20px/1.4 ui-sans-serif, system-ui, -apple-system, sans-serif",
      textAlign: "center",
      zIndex: "2147483646",
      pointerEvents: "none",
      opacity: "0",
      transition: "opacity 200ms ease",
      boxShadow: "0 6px 24px rgba(0,0,0,0.25)",
    });
    document.documentElement.appendChild(bar);
  };
  if (document.body) install();
  else document.addEventListener("DOMContentLoaded", install);
}

class Director {
  readonly cues: Cue[] = [];
  private current = "";
  private readonly t0 = Date.now();

  constructor(private readonly page: Page) {
    // Full page loads replace the document: put the current subtitle back.
    page.on("load", () => void this.render().catch(() => {}));
  }

  private now = () => Date.now() - this.t0;

  private async render() {
    await this.page.evaluate((text) => {
      const bar = document.getElementById("__demo_caption");
      if (!bar) return;
      bar.textContent = text;
      bar.style.opacity = text ? "1" : "0";
    }, this.current);
  }

  /** Show a subtitle, run the actions it narrates, and keep it up long enough to read. */
  async say(text: string, action?: () => Promise<void>) {
    this.cue(text);
    await this.render();
    const shownAt = Date.now();
    if (action) await action();
    const readMs = 1400 + text.length * 52;
    const left = readMs - (Date.now() - shownAt);
    if (left > 0) await this.page.waitForTimeout(left);
  }

  async clear() {
    this.cue("");
    await this.render();
  }

  private cue(text: string) {
    const t = this.now();
    const open = this.cues.at(-1);
    if (open && open.end < 0) open.end = t;
    if (text) this.cues.push({ start: t, end: -1, text });
    this.current = text;
  }

  finish() {
    this.cue("");
  }

  async pointAt(target: Locator, dx = 0, dy = 0) {
    await target.scrollIntoViewIfNeeded();
    const box = await target.boundingBox();
    if (!box) return;
    await this.page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy, {
      steps: 28,
    });
    await this.page.waitForTimeout(250);
  }

  async click(target: Locator) {
    await this.pointAt(target);
    await target.click();
  }

  /** Outline the element being talked about. */
  async spotlight(target: Locator, ms = 2200) {
    await target.scrollIntoViewIfNeeded();
    await target.evaluate((el, duration) => {
      const node = el as HTMLElement;
      const before = node.style.boxShadow;
      node.style.transition = "box-shadow 200ms ease";
      node.style.boxShadow = "0 0 0 3px rgb(8, 145, 178), 0 0 0 8px rgba(8, 145, 178, 0.18)";
      setTimeout(() => (node.style.boxShadow = before), duration);
    }, ms);
  }

  async scrollTo(target: Locator) {
    await target.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }));
    await this.page.waitForTimeout(900);
  }

  async scrollTop() {
    await this.page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await this.page.waitForTimeout(700);
  }

  /** Sweep the cursor across a chart so its tooltip follows the data. */
  async sweep(chart: Locator, from = 0.1, to = 0.9) {
    await chart.scrollIntoViewIfNeeded();
    const box = await chart.boundingBox();
    if (!box) return;
    const y = box.y + box.height * 0.45;
    await this.page.mouse.move(box.x + box.width * from, y, { steps: 20 });
    await this.page.mouse.move(box.x + box.width * to, y, { steps: 90 });
  }
}

const h1 = (page: Page) => page.getByRole("heading", { level: 1 });

test("Windsight product demo", async ({ page }) => {
  await page.addInitScript(installOverlay);
  const d = new Director(page);

  // --- Day-ahead decision ------------------------------------------------------------------
  await page.goto("/");
  await expect(h1(page)).toHaveText("Wind for Sun, 1 Feb 2026");
  await page.waitForTimeout(600);

  await d.say("Windsight: day-ahead wind forecast monitoring for UK power procurement.");
  await d.say(
    "Every morning the buying team decides how much power to buy for tomorrow. The big unknown is wind.",
  );

  const brief = page.locator("section", { hasText: "Decision brief" });
  await d.say(
    "At the 09:00 cutoff, Windsight shows the latest forecast the buyer actually had, in one sentence.",
    async () => {
      await d.spotlight(brief, 3500);
      await d.pointAt(brief.getByText("Plan on at least"), -120);
    },
  );

  const firm = page.locator("div.rounded-xl").filter({ hasText: /^Firm wind \(P90\)/ });
  await d.say(
    "Firm wind (P90) is the level beaten in 9 of 10 recent hours: a safe floor to size purchases against.",
    async () => {
      await d.spotlight(firm, 3000);
      await d.pointAt(firm.getByRole("button", { name: "What does this mean?" }));
    },
  );

  const chart = page.locator(".recharts-wrapper").first();
  await d.say(
    "The chart compares the official forecast (dashed), the bias-adjusted forecast (violet) and a P10–P90 band.",
    async () => {
      await d.scrollTo(chart);
      await d.sweep(chart, 0.08, 0.6);
    },
  );

  const actuals = page.getByRole("button", { name: "Show actuals" });
  await d.say("Hide the outturn to see exactly what the buyer saw at 09:00…", async () => {
    await d.click(actuals);
    await page.waitForTimeout(800);
  });
  await d.say(
    "…then reveal what actually happened. The adjusted line was closer than the raw forecast.",
    async () => {
      await d.click(actuals);
      await d.sweep(chart, 0.6, 0.92);
    },
  );

  await d.scrollTop();
  const prev = page.getByLabel("Previous day");
  await d.say(
    "Step back through January. 28 Jan was the worst day of the month: wind collapsed below the floor.",
    async () => {
      for (let i = 0; i < 4; i++) {
        await d.click(prev);
        await page.waitForTimeout(450);
      }
      await expect(h1(page)).toHaveText("Wind for Wed, 28 Jan 2026");
      await d.scrollTo(chart);
      await d.sweep(chart, 0.1, 0.85);
    },
  );

  await d.scrollTop();
  await d.say(
    "Change the decision cutoff and Windsight switches to the newest forecast run published by then.",
    async () => {
      const cutoff = page.getByLabel("Decision cutoff");
      await d.pointAt(cutoff);
      await cutoff.selectOption("12:00");
      await expect(page).toHaveURL(/cutoff=12/);
      await d.spotlight(page.getByText("Based on the WINDFOR run"), 2500);
    },
  );

  await d.say("Hourly values and a CSV export are one click away.", async () => {
    const table = page.locator("summary", { hasText: "Hourly values" });
    await d.scrollTo(table);
    await d.click(table);
    await page.waitForTimeout(500);
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(500);
    const csv = page.getByRole("button", { name: "CSV" });
    await d.scrollTo(csv);
    await Promise.all([page.waitForEvent("download"), d.click(csv)]);
  });

  // --- Accuracy ----------------------------------------------------------------------------
  await d.say("The Accuracy view answers: how far can this forecast be trusted?", async () => {
    await d.scrollTop();
    await d.click(page.getByRole("navigation").getByRole("link", { name: "Accuracy" }));
    await expect(h1(page)).toHaveText("How far can the forecast be trusted?");
  });

  const findings = page.locator("section", { hasText: "Key findings" });
  await d.say(
    "In January the official forecast ran high on 27 of 31 days, by 1.7 GW on average.",
    async () => {
      await d.spotlight(findings.locator("li").nth(0), 3500);
      await d.pointAt(findings.locator("li").nth(0), -150);
    },
  );
  await d.say(
    "A leakage-free trailing bias correction cuts the error by 30%, and the P10–P90 band held 86% of hours.",
    async () => {
      await d.spotlight(findings.locator("li").nth(1), 2500);
      await d.pointAt(findings.locator("li").nth(1), -150);
      await page.waitForTimeout(1200);
      await d.spotlight(findings.locator("li").nth(2), 2500);
      await d.pointAt(findings.locator("li").nth(2), -150);
    },
  );

  const daily = page.locator(".recharts-wrapper").first();
  await d.say(
    "Daily, hourly and lead-time error charts show where the misses come from.",
    async () => {
      await d.scrollTo(daily);
      await d.sweep(daily, 0.1, 0.9);
    },
  );
  const horizon = page.locator(".recharts-wrapper").nth(3);
  await d.say(
    "Error grows with lead time, so a later decision, where the market allows, buys accuracy.",
    async () => {
      await d.scrollTo(horizon);
      await d.sweep(horizon, 0.1, 0.9);
    },
  );

  // --- Horizon explorer --------------------------------------------------------------------
  await d.say(
    "The Horizon explorer replays any range with forecasts published N hours ahead.",
    async () => {
      await d.scrollTop();
      await d.click(page.getByRole("navigation").getByRole("link", { name: "Horizon explorer" }));
      await expect(h1(page)).toHaveText("Horizon explorer");
    },
  );

  const slider = page.getByRole("slider");
  const box = (await slider.boundingBox())!;
  const xAt = (hours: number) => box.x + 8 + ((box.width - 16) * hours) / 48;
  await d.say("Drag the horizon down to 2 hours: the forecast hugs the outturn…", async () => {
    await page.mouse.move(xAt(24), box.y + box.height / 2, { steps: 20 });
    await page.mouse.down();
    await page.mouse.move(xAt(2), box.y + box.height / 2, { steps: 40 });
    await page.mouse.up();
    await expect(page).toHaveURL(/horizon=[0-3]\b/);
    await page.waitForTimeout(800);
  });
  await d.say("…and out to 48 hours: the misses grow, and the MAE with them.", async () => {
    await page.mouse.move(xAt(2), box.y + box.height / 2, { steps: 10 });
    await page.mouse.down();
    await page.mouse.move(xAt(48), box.y + box.height / 2, { steps: 50 });
    await page.mouse.up();
    await expect(page).toHaveURL(/horizon=4[5-8]\b/);
    await d.spotlight(page.locator("div.rounded-xl").filter({ hasText: /^MAE/ }), 2500);
  });

  await d.say(
    "Every view is a shareable URL. Data: Elexon BMRS FUELHH and WINDFOR. Thanks for watching!",
  );
  await d.clear();
  await page.waitForTimeout(600);

  // --- Save --------------------------------------------------------------------------------
  d.finish();
  const out = path.join(test.info().project.testDir, "out");
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, "captions.json"), JSON.stringify(d.cues, null, 2));
  const video = page.video()!;
  await page.close();
  await video.saveAs(path.join(out, "raw.webm"));
});
