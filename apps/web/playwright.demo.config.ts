import { defineConfig } from "@playwright/test";

import base from "./playwright.config";

/**
 * Records the subtitled product demo (`pnpm demo`): a scripted walkthrough of the real app,
 * captured as video, then rendered to docs/demo/ by demo/render.mjs.
 */
export default defineConfig({
  ...base,
  testDir: "./demo",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 10 * 60_000,
  reporter: "list",
  projects: [
    {
      name: "demo",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        deviceScaleFactor: 1,
        video: { mode: "on", size: { width: 1280, height: 720 } },
        acceptDownloads: true,
      },
    },
  ],
});
