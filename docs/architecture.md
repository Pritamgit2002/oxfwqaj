# Architecture

## Problem in one paragraph

A UK utility buys power in the GB **day-ahead** market. For delivery day **D**, the purchase
is committed on **D-1** before the auction's gate closure. Wind output is uncertain, so the
buyer needs (1) the **latest wind forecast available at that decision time** and (2) a
quantified view of **how wrong that forecast tends to be**, so the residual (non-wind) volume
and a safety buffer can be sized. Scope: national wind, Elexon data only, decisions made in
January 2026 (delivery days 2 Jan – 1 Feb 2026).

## System overview

```mermaid
flowchart LR
  subgraph Elexon BMRS
    F[FUELHH stream<br/>half-hourly outturn]
    W[WINDFOR stream<br/>hourly forecast runs]
  end
  subgraph apps/api  (Python 3.12, FastAPI)
    I[windsight ingest<br/>CLI job] -->|idempotent upsert| DB[(Postgres)]
    R[Repository] --> DB
    S[Services<br/>selection + metrics] --> R
    A[REST /api/v1] --> S
  end
  subgraph apps/web  (Next.js 16)
    P[Server components<br/>fetch via typed client] --> A
    C[Client charts<br/>Recharts]
  end
  F --> I
  W --> I
  U[Trader's browser] --> P
  P --> C
```

- **Ingestion is decoupled from serving.** A one-shot job (`windsight ingest`) pulls Elexon in
  7-day chunks with retries and upserts into Postgres, recording each run in `ingestion_run`
  (surfaced as data freshness). Re-running it is safe. The API never calls Elexon on a request
  path, so the UI is fast and resilient to Elexon outages.
- **The browser never calls the API directly.** Next.js server components call it over the
  private network (`API_BASE_URL`), so there's no CORS or public API surface for the UI and
  every view is a shareable, server-rendered URL (`/?decision=2026-01-14&cutoff=09:00`).
- **One contract, generated types.** FastAPI's Pydantic response models → `openapi.json` →
  `openapi-typescript` → `@windsight/api-client`. A backend schema change that breaks the UI
  fails `tsc`, and CI fails if the generated client wasn't regenerated.

## Backend layering (`apps/api/src/windsight`)

| Layer        | Module                                                                    | Responsibility                                                                                                         |
| ------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| API          | `api/routes/*.py`, `api/deps.py`, `api/middleware.py`                     | HTTP, validation, dependency wiring, request id + timing. No business logic.                                           |
| Contracts    | `schemas/analytics.py`                                                    | Pydantic response models (source of the TS types).                                                                     |
| Use cases    | `services/analytics.py`                                                   | Compose repository reads with domain rules per endpoint.                                                               |
| Domain rules | `services/selection.py`, `services/metrics.py`, `services/calibration.py` | **Pure functions**: which forecast was "in hand", error statistics, leakage-free calibration. Unit tested without I/O. |
| Data access  | `repositories/generation.py`                                              | All SQL for generation tables; dialect-aware upserts (Postgres + SQLite).                                              |
| Integration  | `elexon/client.py`                                                        | Typed Elexon client (httpx), retries with backoff, response validation.                                                |
| Persistence  | `db/models.py`, `migrations/`                                             | SQLAlchemy 2 models; Alembic migrations. Timestamps always tz-aware UTC.                                               |
| Jobs         | `services/ingestion.py`, `cli.py`                                         | Chunked, audited, idempotent ingestion; `release` (migrate + ingest); OpenAPI export.                                  |

### Data model

| Table                 | Key                          | Notes                                                            |
| --------------------- | ---------------------------- | ---------------------------------------------------------------- |
| `actual_generation`   | `start_time`                 | FUELHH, `fuelType = WIND`, 30-min resolution                     |
| `forecast_generation` | `(publish_time, start_time)` | every WINDFOR run is kept, hourly targets; index on `start_time` |
| `ingestion_run`       | `id`                         | audit: dataset, window, rows, status, error                      |

Keeping **every forecast run** (not just the latest) is what makes it possible to reconstruct
what the trader knew at any past moment.

## Core business rules

- **Decision time** for delivery day D = D-1 at the cutoff in `Europe/London`
  (`DEFAULT_DECISION_CUTOFF`, default 09:00, adjustable per request because the gate closure
  differs between exchanges/products). Delivery days are local days, so clock-change days are
  23/25 h.
- **Forecast in hand** = the most recent WINDFOR run with `publish_time ≤ decision time` that
  covers day D (`select_run_at`).
- **Horizon view**: for each target time T, the latest forecast with
  `publish_time ≤ T − horizon` (`latest_per_target`).
- **Error = forecast − actual.** Positive = wind under-delivered → shortfall to buy.
  Forecasts are hourly; they are compared with the half-hourly actual starting at the same time.
- **Metrics**: MAE, RMSE, bias, nMAE (% of mean outturn), P10/P50/P90 of error, P90 absolute
  error, max shortfall. **P90 error** is presented as _shortfall cover_: the extra MW that would
  have covered the wind shortfall in 9 of 10 hours.

## Calibration: bias correction and uncertainty band

January's raw day-ahead forecasts ran about 1.7 GW high. Each decision therefore gets a
calibration learned from the forecast's own recent errors (`services/calibration.py`):

- **Window**: the last `CALIBRATION_WINDOW_DAYS` (default 28) delivery days.
- **Leakage rule**: only days **D-2 and earlier**. At the D-1 cutoff, D-1's own outturn is
  still incomplete. The ingestion window reaches back far enough (December 2025) that the first
  pilot decision already has full history.
- **Bias-adjusted forecast** = forecast − mean error over the window.
- **P10–P90 band** for the outturn = `[forecast − P90 error, forecast − P10 error]`,
  clamped at 0. Its low edge summed over the day is the **firm wind (P90 floor)** shown in the
  decision brief.

Backtest over the 31 pilot delivery days (09:00 cutoff), computed by the API and cross-checked
with an independent script:

| Window                | Raw MAE | Bias-adjusted MAE  | Band coverage (target 80%) |
| --------------------- | ------- | ------------------ | -------------------------- |
| 14 days               | 2.02 GW | 1.49 GW (−26%)     | 82%                        |
| **28 days** (default) | 2.02 GW | **1.41 GW (−30%)** | 86%                        |

The calibration and the summary numbers (firm wind, lowest-wind window) are computed in the
API, so the UI only renders them.

## Frontend (`apps/web`)

- Next.js App Router; pages are **server components** that fetch data, client components only
  where interaction is needed (charts, date/cutoff/horizon controls).
- View state lives in the URL (`useQueryState`), so views are linkable and back/forward work.
- `lib/api.ts` is `server-only`; `lib/format.ts` formats in UK time regardless of the viewer's
  browser timezone.

| Route       | Purpose                                                                                  |
| ----------- | ---------------------------------------------------------------------------------------- |
| `/`         | Decision brief, forecast in hand vs bias-adjusted vs actual, calibrated band, CSV export |
| `/accuracy` | Key findings, backtest of the correction, daily error, distribution, by hour, by horizon |
| `/explorer` | Actual vs forecast at any minimum horizon (0–48 h) over a chosen date range              |

## Monorepo & tooling

- **Turborepo + pnpm workspaces.** The Python app participates through a thin `package.json`
  whose scripts delegate to `uv`, so `pnpm dev | lint | typecheck | test | build | codegen` run
  the whole stack and are cached by Turbo.
- `turbo.json` wires `@windsight/api-client#codegen` after `@windsight/api#codegen`.
- Quality gates: ruff (lint + format), mypy `--strict`, pytest (SQLite in-memory, mocked Elexon
  transport); ESLint (next/core-web-vitals + TS), `tsc --noEmit`, Vitest for UI helpers;
  GitHub Actions runs all of them plus the contract-drift check and Docker builds.
- Observability: every API response carries `X-Request-ID` and `Server-Timing`, with one log
  line per request.

## Containers

| Service   | Image                 | Role                                                            |
| --------- | --------------------- | --------------------------------------------------------------- |
| `db`      | `postgres:17-alpine`  | storage (named volume `pgdata`)                                 |
| `migrate` | `apps/api/Dockerfile` | one-shot `alembic upgrade head`                                 |
| `ingest`  | same image            | one-shot `windsight ingest` for the pilot window                |
| `api`     | same image            | `uvicorn`, non-root, healthcheck on `/health`                   |
| `web`     | `apps/web/Dockerfile` | `turbo prune` → pnpm install → Next standalone server, non-root |

Both Dockerfiles are multi-stage: dependency layers are cached separately from source, and
runtime images contain only what's needed to run. Both honour `$PORT` for PaaS hosting.

## Deployment (target)

- **Web → Vercel** (root directory `apps/web`, env `API_BASE_URL`).
- **API + Postgres → Heroku** via `heroku.yml` (container stack, Heroku Postgres). The release
  phase runs `windsight release` (migrate, then ingest). `postgres://` URLs from the platform are
  normalised to the psycopg driver automatically.

## Known limitations / next steps

- Calibration is a constant shift plus empirical quantiles. Next steps: condition on lead time
  or wind level (errors grow with both), and compare against Elexon's other forecast products.
- The firm-wind floor sums hourly P10s, which is more conservative than a true daily P10.
- Hourly forecasts vs half-hourly actuals: compared on matching start times only.
- No auth (pilot). Add SSO before exposing beyond the pilot team.
- Ingestion is manual/one-shot; productionise as a scheduled job (e.g. every 30 min).
