/**
 * Scripted product walkthrough, recorded as the README demo video.
 *
 * Each `say()` shows a lower-third caption in the page (burned into the video) and logs its
 * timing, so demo/render.mjs can also write .srt/.vtt files and a soft subtitle track.
 * In captions, **text** is highlighted.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

type Cue = { start: number; end: number; text: string };

const CHAPTERS = ["Day-ahead decision", "Accuracy backtest", "Horizon explorer"];

/** Cursor, click ripples and the caption card; injected into every document the page loads. */
function installOverlay() {
  const install = () => {
    if (document.getElementById("__demo_cursor")) return;
    const style = document.createElement("style");
    style.textContent = `
      #__demo_cursor { position: fixed; width: 26px; height: 26px; margin: -13px 0 0 -13px;
        border-radius: 50%; background: rgba(34, 211, 238, 0.35); border: 3px solid #fff;
        box-shadow: 0 0 0 2px #0891b2, 0 4px 14px rgba(8, 145, 178, 0.55);
        z-index: 2147483647; pointer-events: none; transition: transform 110ms ease; }
      .__demo_ripple { position: fixed; width: 18px; height: 18px; margin: -9px 0 0 -9px;
        border-radius: 50%; border: 3px solid #22d3ee; z-index: 2147483646; pointer-events: none;
        animation: __demo_ripple 520ms ease-out forwards; }
      @keyframes __demo_ripple { to { transform: scale(3.6); opacity: 0; } }
      #__demo_caption { position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%);
        width: min(1080px, calc(100vw - 64px)); box-sizing: border-box; padding: 14px 22px 16px 26px;
        border-radius: 16px; color: #fff; z-index: 2147483645; pointer-events: none; opacity: 0;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.94));
        box-shadow: 0 18px 50px rgba(2, 6, 23, 0.45), inset 0 0 0 1px rgba(255, 255, 255, 0.08);
        font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
        overflow: hidden; }
      #__demo_caption::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 6px;
        background: linear-gradient(180deg, #22d3ee, #8b5cf6); }
      #__demo_caption .chapter { display: flex; align-items: center; gap: 10px;
        font-weight: 700; font-size: 12px; line-height: 1; letter-spacing: 0.14em; text-transform: uppercase;
        color: #67e8f9; margin-bottom: 7px; }
      #__demo_caption .chapter .num { color: #0f172a; background: #67e8f9; border-radius: 999px;
        padding: 3px 8px; letter-spacing: 0.06em; }
      #__demo_caption .text { font-weight: 600; font-size: 23px; line-height: 1.38; letter-spacing: -0.005em; }
      #__demo_caption mark { color: #0f172a; background: linear-gradient(120deg, #fde047, #fbbf24);
        border-radius: 6px; padding: 0 7px; margin: 0 1px; font-weight: 800;
        box-decoration-break: clone; -webkit-box-decoration-break: clone; }
      #__demo_caption .progress { position: absolute; left: 0; bottom: 0; height: 4px;
        background: linear-gradient(90deg, #22d3ee, #8b5cf6); transition: width 400ms ease; }
      .__demo_card { position: fixed; inset: 0; z-index: 2147483644; display: flex;
        flex-direction: column; align-items: center; justify-content: center; text-align: center;
        color: #fff; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
        background: radial-gradient(1200px 600px at 20% 10%, rgba(34, 211, 238, 0.28), transparent 60%),
          radial-gradient(900px 600px at 85% 90%, rgba(139, 92, 246, 0.32), transparent 60%),
          #0b1222; }
      .__demo_card > * { opacity: 0; animation: __demo_up 600ms cubic-bezier(.2,.8,.2,1) forwards; }
      @keyframes __demo_up { from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: none; } }
      .__demo_card .eyebrow { font-weight: 700; font-size: 14px; line-height: 1; letter-spacing: 0.3em; color: #67e8f9;
        text-transform: uppercase; }
      .__demo_card h1 { font-weight: 800; font-size: 92px; line-height: 1; letter-spacing: -0.04em; margin: 18px 0 14px;
        background: linear-gradient(90deg, #fff, #a5f3fc 55%, #c4b5fd); -webkit-background-clip: text;
        background-clip: text; color: transparent; }
      .__demo_card .lead { font-weight: 500; font-size: 26px; line-height: 1.4; color: #cbd5e1; max-width: 900px; }
      .__demo_card .chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;
        margin-top: 34px; max-width: 960px; }
      .__demo_card .chip { font-weight: 600; font-size: 16px; line-height: 1; padding: 10px 16px; border-radius: 999px;
        background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.16); }
      .__demo_card .stats { display: grid; grid-template-columns: repeat(4, 220px); gap: 16px;
        margin-top: 34px; }
      .__demo_card .stat { padding: 22px 16px; border-radius: 18px; text-align: left;
        background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.14); }
      .__demo_card .stat b { display: block; font-weight: 800; font-size: 46px; line-height: 1; letter-spacing: -0.03em;
        background: linear-gradient(90deg, #fde047, #fbbf24); -webkit-background-clip: text;
        background-clip: text; color: transparent; }
      .__demo_card .stat span { display: block; margin-top: 8px; font-weight: 500; font-size: 16px; line-height: 1.35;
        color: #cbd5e1; }
    `;
    document.documentElement.appendChild(style);

    const cursor = document.createElement("div");
    cursor.id = "__demo_cursor";
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
    addEventListener(
      "mousedown",
      (e) => {
        cursor.style.transform = "scale(0.7)";
        const ripple = document.createElement("div");
        ripple.className = "__demo_ripple";
        ripple.style.left = `${e.clientX}px`;
        ripple.style.top = `${e.clientY}px`;
        document.documentElement.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
      },
      true,
    );
    addEventListener("mouseup", () => (cursor.style.transform = ""), true);

    const card = document.createElement("div");
    card.id = "__demo_caption";
    card.innerHTML =
      '<div class="chapter"><span class="num"></span><span class="name"></span></div>' +
      '<div class="text"></div><div class="progress"></div>';
    document.documentElement.appendChild(card);
  };
  if (document.body) install();
  else document.addEventListener("DOMContentLoaded", install);
}

type CaptionState = { text: string; chapter: number; progress: number; animate: boolean };

class Director {
  readonly cues: Cue[] = [];
  private state: CaptionState = { text: "", chapter: 0, progress: 0, animate: false };
  private readonly t0 = Date.now();
  trimStart = 0;

  constructor(
    private readonly page: Page,
    private readonly totalSteps: number,
  ) {
    // Full page loads replace the document: put the current caption back, without animating.
    page.on("load", () => void this.render(false).catch(() => {}));
  }

  now = () => Date.now() - this.t0;

  private steps = 0;

  private async render(animate = true) {
    await this.page.evaluate(
      ({ state, chapters }) => {
        const card = document.getElementById("__demo_caption");
        if (!card) return;
        const text = card.querySelector(".text")!;
        text.replaceChildren(
          ...state.text.split("**").map((part, i) => {
            if (i % 2 === 0) return document.createTextNode(part);
            const mark = document.createElement("mark");
            mark.textContent = part;
            return mark;
          }),
        );
        card.querySelector(".num")!.textContent = `${state.chapter + 1} / ${chapters.length}`;
        card.querySelector(".name")!.textContent = chapters[state.chapter] ?? "";
        (card.querySelector(".progress") as HTMLElement).style.width = `${state.progress * 100}%`;
        card.style.opacity = state.text ? "1" : "0";
        if (state.text && state.animate) {
          card.animate(
            [
              { opacity: 0, transform: "translate(-50%, 16px)" },
              { opacity: 1, transform: "translate(-50%, 0)" },
            ],
            { duration: 320, easing: "cubic-bezier(.2,.8,.2,1)" },
          );
        }
      },
      { state: { ...this.state, animate }, chapters: CHAPTERS },
    );
  }

  chapter(index: number) {
    this.state.chapter = index;
  }

  /** Show a caption, run the actions it narrates, and keep it up long enough to read. */
  async say(text: string, action?: () => Promise<void>) {
    this.steps += 1;
    this.cue(text);
    this.state = { ...this.state, text, progress: this.steps / this.totalSteps };
    await this.render();
    const shownAt = Date.now();
    if (action) await action();
    const readMs = 900 + plain(text).length * 36;
    const left = readMs - (Date.now() - shownAt);
    if (left > 0) await this.page.waitForTimeout(left);
  }

  async clear() {
    this.cue("");
    this.state = { ...this.state, text: "" };
    await this.render(false);
  }

  private cue(text: string) {
    const t = this.now();
    const open = this.cues.at(-1);
    if (open && open.end < 0) open.end = t;
    if (text) this.cues.push({ start: t, end: -1, text: plain(text) });
  }

  /** Full-screen title or results card, shown over the app. */
  async card(html: string, ms: number, caption: string) {
    this.cue(caption);
    await this.page.evaluate((markup) => {
      const card = document.createElement("div");
      card.className = "__demo_card";
      card.id = "__demo_card";
      card.innerHTML = markup;
      document.getElementById("__demo_cursor")?.style.setProperty("opacity", "0");
      [...card.children].forEach(
        (el, i) => ((el as HTMLElement).style.animationDelay = `${120 + i * 160}ms`),
      );
      document.documentElement.appendChild(card);
    }, html);
    await this.page.waitForTimeout(ms);
    this.cue("");
  }

  async dismissCard() {
    await this.page.evaluate(async () => {
      const card = document.getElementById("__demo_card");
      if (!card) return;
      await card.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 450, fill: "forwards" })
        .finished;
      card.remove();
      document.getElementById("__demo_cursor")?.style.setProperty("opacity", "1");
    });
  }

  async pointAt(target: Locator, dx = 0, dy = 0) {
    await target.scrollIntoViewIfNeeded();
    const box = await target.boundingBox();
    if (!box) return;
    await this.page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy, {
      steps: 14,
    });
    await this.page.waitForTimeout(120);
  }

  async click(target: Locator) {
    await this.pointAt(target);
    await target.click();
  }

  /** Glow around the element being talked about. */
  async spotlight(target: Locator, ms = 2000) {
    await target.scrollIntoViewIfNeeded();
    await target.evaluate((el, duration) => {
      const node = el as HTMLElement;
      const before = node.style.boxShadow;
      node.style.transition = "box-shadow 200ms ease";
      node.style.boxShadow =
        "0 0 0 3px #fbbf24, 0 0 0 9px rgba(251, 191, 36, 0.25), 0 12px 40px rgba(251, 191, 36, 0.35)";
      setTimeout(() => (node.style.boxShadow = before), duration);
    }, ms);
  }

  async scrollTo(target: Locator) {
    await target.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }));
    await this.page.waitForTimeout(600);
  }

  async scrollTop() {
    await this.page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await this.page.waitForTimeout(450);
  }

  /** Sweep the cursor across a chart so its tooltip follows the data. */
  async sweep(chart: Locator, from = 0.1, to = 0.9) {
    await chart.scrollIntoViewIfNeeded();
    const box = await chart.boundingBox();
    if (!box) return;
    const y = box.y + box.height * 0.45;
    await this.page.mouse.move(box.x + box.width * from, y, { steps: 10 });
    await this.page.mouse.move(box.x + box.width * to, y, { steps: 45 });
  }
}

const plain = (text: string) => text.replaceAll("**", "");
const h1 = (page: Page) => page.getByRole("heading", { level: 1 });

const INTRO = `
  <div class="eyebrow">UK power procurement · Pilot January 2026</div>
  <h1>Windsight</h1>
  <div class="lead">Day-ahead wind forecast monitoring: how much wind you can count on
    tomorrow, and how far the forecast can be trusted.</div>
  <div class="chips">
    <span class="chip">Real Elexon BMRS data</span><span class="chip">FastAPI · Python 3.12</span>
    <span class="chip">Next.js 16 · React 19</span><span class="chip">PostgreSQL</span>
    <span class="chip">Docker · CI</span>
  </div>`;

const OUTRO = `
  <div class="eyebrow">Built end to end</div>
  <h1>Windsight</h1>
  <div class="stats">
    <div class="stat"><b>−30%</b><span>forecast error with the leakage-free bias correction</span></div>
    <div class="stat"><b>86%</b><span>of hours inside the P10–P90 band (target 80%)</span></div>
    <div class="stat"><b>125</b><span>automated tests: unit, integration, browser end-to-end</span></div>
    <div class="stat"><b>3</b><span>decision views, every one a shareable URL</span></div>
  </div>
  <div class="chips">
    <span class="chip">Typed API contract</span><span class="chip">SQLite + Postgres tested</span>
    <span class="chip">Docker Compose · Heroku · Vercel</span>
  </div>`;

test("Windsight product demo", async ({ page }) => {
  await page.addInitScript(installOverlay);
  const d = new Director(page, 16);

  await page.goto("/");
  await expect(h1(page)).toHaveText("Wind for Sun, 1 Feb 2026");

  // --- Title -------------------------------------------------------------------------------
  d.trimStart = d.now();
  await d.card(
    INTRO,
    3600,
    "Windsight: day-ahead wind forecast monitoring for UK power procurement.",
  );
  await d.dismissCard();

  // --- 1. Day-ahead decision ---------------------------------------------------------------
  d.chapter(0);
  const brief = page.locator("section", { hasText: "Decision brief" });
  await d.say(
    "Every morning the team buys tomorrow's power. At the **09:00 cutoff**, Windsight shows the forecast they actually had.",
    async () => {
      await d.spotlight(brief, 3200);
      await d.pointAt(brief.getByText("Plan on at least"), -120);
    },
  );

  const firm = page.locator("div.rounded-xl").filter({ hasText: /^Firm wind \(P90\)/ });
  await d.say(
    "**Firm wind (P90)**: the level beaten in 9 of 10 recent hours, a safe floor to buy against.",
    async () => {
      await d.spotlight(firm, 2600);
      await d.pointAt(firm.getByRole("button", { name: "What does this mean?" }));
    },
  );

  const chart = page.locator(".recharts-wrapper").first();
  await d.say(
    "Official forecast (dashed) vs **bias-adjusted** (violet), with a calibrated **P10–P90 band**.",
    async () => {
      await d.scrollTo(chart);
      await d.sweep(chart, 0.08, 0.6);
    },
  );

  const actuals = page.getByRole("button", { name: "Show actuals" });
  await d.say(
    "Hide the outturn to see **exactly what the buyer saw**… then reveal it.",
    async () => {
      await d.click(actuals);
      await page.waitForTimeout(900);
      await d.click(actuals);
      await d.sweep(chart, 0.6, 0.92);
    },
  );

  await d.scrollTop();
  const prev = page.getByLabel("Previous day");
  await d.say(
    "**28 Jan**, the worst day of the month: wind fell **below the floor in all 24 hours**.",
    async () => {
      for (let i = 0; i < 4; i++) {
        await d.click(prev);
        await page.waitForTimeout(220);
      }
      await expect(h1(page)).toHaveText("Wind for Wed, 28 Jan 2026");
      await d.scrollTo(chart);
      await d.sweep(chart, 0.1, 0.85);
    },
  );

  await d.scrollTop();
  await d.say(
    "Move the cutoff and it switches to the **newest forecast run** at that time.",
    async () => {
      const cutoff = page.getByLabel("Decision cutoff");
      await d.pointAt(cutoff);
      await cutoff.selectOption("12:00");
      await expect(page).toHaveURL(/cutoff=12/);
      await d.spotlight(page.getByText("Based on the WINDFOR run"), 2000);
    },
  );

  await d.say("Hourly values and **one-click CSV export**.", async () => {
    const table = page.locator("summary", { hasText: "Hourly values" });
    await d.scrollTo(table);
    await d.click(table);
    await page.mouse.wheel(0, 260);
    await page.waitForTimeout(350);
    const csv = page.getByRole("button", { name: "CSV" });
    await d.scrollTo(csv);
    await Promise.all([page.waitForEvent("download"), d.click(csv)]);
  });

  // --- 2. Accuracy -------------------------------------------------------------------------
  d.chapter(1);
  await d.say("How far can the forecast be **trusted**?", async () => {
    await d.scrollTop();
    await d.click(page.getByRole("navigation").getByRole("link", { name: "Accuracy" }));
    await expect(h1(page)).toHaveText("How far can the forecast be trusted?");
  });

  const findings = page.locator("section", { hasText: "Key findings" });
  await d.say(
    "In January the official forecast ran high on **27 of 31 days**, by **1.7 GW** on average.",
    async () => {
      await d.spotlight(findings.locator("li").nth(0), 2600);
      await d.pointAt(findings.locator("li").nth(0), -150);
    },
  );
  await d.say(
    "A leakage-free bias correction cuts error by **30%**. The P10–P90 band held **86%** of hours.",
    async () => {
      await d.spotlight(findings.locator("li").nth(1), 1800);
      await d.pointAt(findings.locator("li").nth(1), -150);
      await page.waitForTimeout(700);
      await d.spotlight(findings.locator("li").nth(2), 1800);
      await d.pointAt(findings.locator("li").nth(2), -150);
    },
  );

  const daily = page.locator(".recharts-wrapper").first();
  await d.say(
    "Daily, hourly and lead-time charts show **where the misses come from**.",
    async () => {
      await d.scrollTo(daily);
      await d.sweep(daily, 0.1, 0.9);
    },
  );
  const horizon = page.locator(".recharts-wrapper").nth(3);
  await d.say("Error **grows with lead time**: a later decision buys accuracy.", async () => {
    await d.scrollTo(horizon);
    await d.sweep(horizon, 0.1, 0.9);
  });

  // --- 3. Horizon explorer -----------------------------------------------------------------
  d.chapter(2);
  await d.say("Replay any range with forecasts published **N hours ahead**.", async () => {
    await d.scrollTop();
    await d.click(page.getByRole("navigation").getByRole("link", { name: "Horizon explorer" }));
    await expect(h1(page)).toHaveText("Horizon explorer");
  });

  const slider = page.getByRole("slider");
  const box = (await slider.boundingBox())!;
  const xAt = (hours: number) => box.x + 8 + ((box.width - 16) * hours) / 48;
  const y = box.y + box.height / 2;
  await d.say("**2 hours** ahead: the forecast hugs the outturn…", async () => {
    await page.mouse.move(xAt(24), y, { steps: 10 });
    await page.mouse.down();
    await page.mouse.move(xAt(2), y, { steps: 22 });
    await page.mouse.up();
    await expect(page).toHaveURL(/horizon=[0-3]\b/);
    await page.waitForTimeout(500);
  });
  await d.say("…**48 hours** ahead: the misses grow, and the MAE with them.", async () => {
    await page.mouse.move(xAt(2), y, { steps: 6 });
    await page.mouse.down();
    await page.mouse.move(xAt(48), y, { steps: 26 });
    await page.mouse.up();
    await expect(page).toHaveURL(/horizon=4[5-8]\b/);
    await d.spotlight(page.locator("div.rounded-xl").filter({ hasText: /^MAE/ }), 2000);
  });

  await d.clear();

  // --- Results -----------------------------------------------------------------------------
  await d.card(
    OUTRO,
    5200,
    "Built end to end: −30% forecast error, 86% band coverage, 125 automated tests.",
  );

  // --- Save --------------------------------------------------------------------------------
  const out = path.join(test.info().project.testDir, "out");
  mkdirSync(out, { recursive: true });
  const trim = d.trimStart;
  const cues = d.cues.map((c) => ({ ...c, start: c.start - trim, end: c.end - trim }));
  writeFileSync(path.join(out, "captions.json"), JSON.stringify({ trimMs: trim, cues }, null, 2));
  const video = page.video()!;
  await page.close();
  await video.saveAs(path.join(out, "raw.webm"));
});
