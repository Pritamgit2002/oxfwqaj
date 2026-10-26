# Demo script (video, max 10 minutes)

Two parts of up to 5 minutes each. Numbers are from the January 2026 pilot at the 09:00 cutoff.
Before recording: `docker compose up --build`, open http://localhost:3000, browser at full
width, zoom 110%.

---

## Part 1: Client pitch (≈ 5 min)

**Goal:** the buying team should leave thinking "this changes how much we buy each morning."

| Time | Screen                                               | Say                                                                                                                                                                                                                                               |
| ---- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00 | Day-ahead, decision day **31 Jan**                   | "Every morning before the day-ahead auction, your team decides how much power to buy for tomorrow. The big unknown is wind. This is what Windsight shows at 09:00 on the decision day."                                                           |
| 0:30 | Decision brief card                                  | "One sentence: plan on at least _X_ GWh of wind tomorrow. That's the P90 floor, wind we've beaten in 9 of 10 hours. Below it, the bias-adjusted expectation and the lowest-wind window, the hours where you'll need the most from other sources." |
| 1:15 | Chart → turn **Show actuals** off                    | "This is exactly what you'd have seen at 09:00: the official forecast (dashed), our adjusted forecast (violet), and the range."                                                                                                                   |
| 1:40 | Turn **Show actuals** back on                        | "And this is what actually happened. The official forecast was too high; the adjusted line and the band were much closer."                                                                                                                        |
| 2:00 | Click **‹** to step back to 27 Jan (delivery 28 Jan) | "We don't hide the bad days. 28 January was the worst of the month: wind collapsed below even our floor. The tool shows how often that happens, so you can price that risk."                                                                      |
| 2:40 | **Accuracy** page, Key findings                      | "Across January: the official forecast over-estimated wind on 27 of 31 days, by 1.7 GW on average. A team trusting it at face value was systematically short."                                                                                    |
| 3:20 | Backtest KPI + tooltip                               | "Our correction learns from the last 4 weeks, using only data you'd actually have had that morning. It cuts the forecast error by 30%, from 2.0 to 1.4 GW."                                                                                       |
| 3:50 | Horizon chart                                        | "Error grows the further ahead the forecast is made. If your process can move the decision later, it buys accuracy."                                                                                                                              |
| 4:20 | CSV button                                           | "Everything exports to CSV for your own models."                                                                                                                                                                                                  |
| 4:40 | Close                                                | "Next steps for a production rollout: add your demand forecast to turn this into a buy recommendation in MW, run it live every 30 minutes, and extend it to solar."                                                                               |

---

## Part 2: Tech-lead review (≈ 5 min)

**Goal:** make review easy. Show the structure, the key rules, and how quality is enforced.

| Time | Screen                                                                        | Say                                                                                                                                                                                                             |
| ---- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00 | `docs/architecture.md` diagram                                                | "Turborepo monorepo: a FastAPI service and a Next.js app, plus a shared generated API client. Postgres in Docker. Ingestion is a separate idempotent job, so requests never hit Elexon."                        |
| 0:45 | `apps/api/src/windsight` tree                                                 | "Layered: routes → services → pure domain rules → repository → SQLAlchemy. Business rules are pure functions with no I/O, so they're unit tested directly."                                                     |
| 1:20 | `services/selection.py`                                                       | "The core rule: the forecast in hand is the latest run published at or before the D-1 cutoff, in UK local time so clock-change days work."                                                                      |
| 1:50 | `services/calibration.py`                                                     | "Calibration uses only D-2 and earlier. D-1 isn't settled at decision time. That's what makes the 30% backtest honest; there's a test that fails if D-1 leaks in."                                              |
| 2:30 | `schemas/analytics.py` → `pnpm codegen` → `packages/api-client/src/schema.ts` | "Pydantic models are the contract. They generate the OpenAPI schema, which generates TypeScript types. A breaking API change fails the frontend's type check, and CI fails if the generated client is stale."   |
| 3:10 | `apps/web/src/app/page.tsx`                                                   | "Pages are server components that call the API over the private network; the browser never talks to the API. State lives in the URL, so every view is shareable. The UI only renders numbers the API computes." |
| 3:40 | `docker-compose.yml`, Dockerfiles                                             | "Compose runs db → migrate → ingest → api → web. Multi-stage, non-root images; the web image uses `turbo prune`. `heroku.yml` deploys the API, with `windsight release` as the release phase."                  |
| 4:15 | Terminal: `pnpm lint typecheck test build`                                    | "One command checks both stacks: ruff, strict mypy, pytest, ESLint, tsc, Vitest, Next build. The same runs in GitHub Actions."                                                                                  |
| 4:40 | `curl -i localhost:8000/health`                                               | "Request IDs and server timing on every response. Known limitations and next steps are listed at the end of the architecture doc."                                                                              |

---

### Tips

- Record each part in one take, with the browser and editor already open on the right files.
- Keep the cursor still while talking; move it only to point.
- Mention AI-assisted development briefly in Part 2, as the README does.
