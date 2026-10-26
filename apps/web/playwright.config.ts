import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests: the real stack (Elexon -> ingestion -> FastAPI -> Next.js -> browser).
 *
 * Starts the API on a scratch SQLite database (migrated and loaded with the January 2026
 * pilot from Elexon; idempotent, so reruns are quick) and a production build of the web app.
 * Ports differ from `pnpm dev` so tests can run next to a dev session.
 *
 * To smoke-test a deployment instead, set E2E_BASE_URL (web) and E2E_API_URL (API):
 * no local servers are started.
 */
const API_PORT = Number(process.env.E2E_API_PORT ?? 8200);
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 3200);
const API_URL = `http://127.0.0.1:${API_PORT}`;
const REMOTE = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  timeout: 30_000,
  use: {
    baseURL: REMOTE ?? `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: REMOTE
    ? undefined
    : [
        {
          name: "api",
          cwd: "../api",
          command:
            "uv run alembic upgrade head && uv run windsight ingest && " +
            `uv run uvicorn windsight.main:app --host 127.0.0.1 --port ${API_PORT}`,
          env: {
            DATABASE_URL: process.env.E2E_DATABASE_URL ?? "sqlite:///./e2e.db",
            LOG_LEVEL: "WARNING",
          },
          url: `${API_URL}/health/ready`,
          timeout: 180_000,
          reuseExistingServer: !process.env.CI,
        },
        {
          name: "web",
          command: `pnpm exec next build && pnpm exec next start --port ${WEB_PORT}`,
          env: { API_BASE_URL: API_URL },
          url: `http://127.0.0.1:${WEB_PORT}/api/health`,
          timeout: 240_000,
          reuseExistingServer: !process.env.CI,
        },
      ],
});
