# Windsight

**Day-ahead wind forecast monitoring for UK power procurement.**
For each day-ahead purchase decision, Windsight shows the national wind generation forecast the
buyer actually had at the decision cutoff, and how accurate such forecasts have been, so the
residual volume and a safety buffer can be sized from measured error rather than gut feel.

Pilot scope: national wind only, Elexon BMRS data, purchase decisions made in **January 2026**
(delivery days 2 Jan – 1 Feb 2026).

- **Live app:** _TODO: add the Vercel/Heroku URL after deployment_
- **Architecture & design decisions:** [docs/architecture.md](docs/architecture.md)

## Key findings (January 2026, 09:00 cutoff)

- **The raw forecast runs high.** Day-ahead forecasts over-estimated wind on **27 of 31** days,
  by **1.7 GW** on average (MAE 2.0 GW, 18% of mean outturn). Taken at face value, it leads to
  under-buying.
- **A simple, leakage-free correction cuts error by 30%.** Subtracting the forecast's mean error
  over the previous 28 settled days brings MAE from **2.0 → 1.4 GW**.
- **The uncertainty band is honest.** The P10–P90 band built the same way captured **86%** of
  hours (target 80%), so the "firm wind" floor is safe to size purchases against.
- **Error grows with lead time**, from about 1.7 GW for the freshest forecasts to 2.4 GW at 47 h,
  so every hour of later cutoff buys accuracy.

## What it shows

| View                               | Question it answers                                                                                                                                                                                                                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Day-ahead** (`/`)                | "At 09:00 on D-1, how much wind can I count on tomorrow?" A plain-English decision brief (firm wind at P90, bias-adjusted expectation, lowest-wind window), the forecast vs bias-adjusted vs actual chart with a calibrated P10–P90 band, toggles to hide the hindsight outturn, and CSV export. |
| **Accuracy** (`/accuracy`)         | "How wrong is the decision-time forecast, and does the correction help?" Generated key findings, MAE/bias/P90 cover, the out-of-sample backtest, and daily, hourly and horizon error views.                                                                                                      |
| **Horizon explorer** (`/explorer`) | "How does accuracy change if I use forecasts published N hours ahead?" (0–48 h slider, CSV export).                                                                                                                                                                                              |

The decision cutoff is adjustable (default 09:00 UK time); every view is a shareable URL.

## Stack

|            |                                                                                |
| ---------- | ------------------------------------------------------------------------------ |
| Monorepo   | Turborepo + pnpm workspaces                                                    |
| Frontend   | Next.js 16 (App Router, React 19, server components), Tailwind CSS 4, Recharts |
| Backend    | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, httpx, NumPy, managed with uv     |
| Data       | PostgreSQL 17 (SQLite supported for Docker-less dev and tests)                 |
| Contract   | OpenAPI → `openapi-typescript` → typed `openapi-fetch` client                  |
| Containers | Docker multi-stage images + Docker Compose                                     |
| Quality    | ruff, mypy (strict), pytest · ESLint, TypeScript, Vitest · GitHub Actions      |

## Repository layout

```
.
├── apps/
│   ├── api/                      # Python backend (FastAPI), published as the `windsight` package
│   │   ├── src/windsight/
│   │   │   ├── api/              #   HTTP layer: routes, dependency wiring, request-id middleware
│   │   │   ├── core/             #   settings (env-driven), logging
│   │   │   ├── db/               #   SQLAlchemy models, engine/session
│   │   │   ├── elexon/           #   typed Elexon BMRS client (retries, validation)
│   │   │   ├── repositories/     #   all SQL for generation data, dialect-aware upserts
│   │   │   ├── schemas/          #   Pydantic response models (API contract)
│   │   │   ├── services/         #   use cases + pure domain rules (selection, metrics, calibration, ingestion)
│   │   │   ├── domain.py         #   value objects (ActualPoint, ForecastPoint)
│   │   │   ├── cli.py            #   `windsight ingest | release | export-openapi`
│   │   │   └── main.py           #   FastAPI app factory
│   │   ├── migrations/           # Alembic migrations
│   │   ├── tests/                # pytest: domain rules, calibration (no leakage), API, ingestion
│   │   ├── Dockerfile            # uv multi-stage image (api / migrate / ingest)
│   │   ├── package.json          # Turborepo bridge: scripts delegate to `uv run …`
│   │   └── pyproject.toml / uv.lock
│   └── web/                      # Next.js frontend
│       ├── src/app/              #   routes: / (day-ahead), /accuracy, /explorer, /api/health
│       ├── src/components/       #   charts (client), controls (URL state), ui primitives
│       ├── src/lib/              #   server-only API access, formatting, date helpers (+ Vitest)
│       └── Dockerfile            #   turbo prune → standalone Next.js server
├── packages/
│   ├── api-client/               # generated OpenAPI types + typed fetch client (shared contract)
│   └── typescript-config/        # shared tsconfig presets
├── docs/
│   ├── architecture.md           # architecture, business rules, calibration, limitations
│   └── demo-script.md            # talk track for the 2-part video (client pitch, tech review)
├── docker-compose.yml            # db → migrate → ingest → api → web
├── heroku.yml                    # API container deploy; release phase = `windsight release`
├── turbo.json                    # task pipeline (build, dev, lint, typecheck, test, codegen)
└── .github/workflows/ci.yml      # lint, types, tests, contract drift, docker builds
```

## Getting started

### Option A: Docker (whole stack, one command)

Requires Docker Desktop.

```bash
docker compose up --build
```

This starts Postgres, applies migrations, ingests the January 2026 window from Elexon (about
23k rows, a few seconds), and serves:

- Web: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs

To re-ingest later (idempotent): `docker compose run --rm ingest`.

### Option B: local development (hot reload)

Requires Node ≥ 20.9 with pnpm (`corepack enable`), [uv](https://docs.astral.sh/uv/), and either
Docker (for Postgres) or nothing at all (SQLite).

```bash
pnpm install
cp .env.example apps/api/.env        # use DATABASE_URL=sqlite:///./windsight.db to skip Postgres
docker compose up -d db              # only if using Postgres
pnpm --filter @windsight/api db:migrate
pnpm --filter @windsight/api ingest
pnpm dev                             # API on :8000 and web on :3000, via Turborepo
```

### Common tasks

| Command                                      | What it does                                                          |
| -------------------------------------------- | --------------------------------------------------------------------- |
| `pnpm dev`                                   | Run API (uvicorn `--reload`) and web (Next dev) together              |
| `pnpm lint` / `pnpm typecheck` / `pnpm test` | Run across all workspaces (Python via uv)                             |
| `pnpm build`                                 | Production build of the web app                                       |
| `pnpm codegen`                               | Export FastAPI OpenAPI, then regenerate `@windsight/api-client` types |
| `pnpm --filter @windsight/api ingest`        | Load or refresh Elexon data                                           |

## Deploying

**API + Postgres (Heroku, container stack)**

```bash
heroku create <app-name> --stack container
heroku addons:create heroku-postgresql:essential-0 -a <app-name>
heroku config:set CORS_ORIGINS='["https://<web>.vercel.app"]' -a <app-name>
git push heroku main          # builds apps/api/Dockerfile; release runs migrate + ingest
```

Heroku's `postgres://` `DATABASE_URL` is normalised to the psycopg driver automatically.

**Web (Vercel)**: import the repo, set **Root Directory** to `apps/web` (Vercel detects
Next.js and the pnpm workspace), and set `API_BASE_URL=https://<app-name>.herokuapp.com`.

## API

| Endpoint                                                      | Description                                                                                                    |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/meta`                                            | Pilot window, defaults, data coverage and freshness                                                            |
| `GET /api/v1/day-ahead?delivery_date=YYYY-MM-DD&cutoff=HH:MM` | Forecast in hand at the D-1 cutoff, bias-adjusted values, P10–P90 band, decision summary, actuals              |
| `GET /api/v1/accuracy/day-ahead?cutoff=HH:MM`                 | Decision-time error over the pilot (raw and bias-corrected backtest, band coverage), daily, by hour, histogram |
| `GET /api/v1/accuracy/horizon`                                | Error by lead time (0–48 h)                                                                                    |
| `GET /api/v1/series?start=&end=&horizon_hours=`               | Actual vs latest forecast published ≥ N h ahead                                                                |
| `GET /health`, `GET /health/ready`                            | Liveness / readiness (DB)                                                                                      |

Every response carries `X-Request-ID` and `Server-Timing` headers. Interactive docs: `/docs`.

Error convention: **error = forecast − actual** (positive means wind under-delivered).

## Data sources

- Actuals: Elexon [FUELHH stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), `fuelType = WIND`, 30-minute resolution.
- Forecasts: Elexon [WINDFOR stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream), hourly targets, about 8 runs per day.

## AI tools

This project was built with help from AI coding tools (Claude Code, Anthropic) for scaffolding,
implementation and documentation. All code was reviewed, run and tested by the author.
