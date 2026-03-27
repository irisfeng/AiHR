# Direct Rebuild Roadmap

## Goal

Stop fighting Frappe for the product shell. Keep the reusable recruiting logic, rebuild the operator experience as a standalone product.

## New structure

- `apps/web`: Next.js recruiting workspace
- `apps/api`: FastAPI recruiting API
- `apps/shared/demo-data.json`: shared demo payload for UI and API

## Commands

Install web dependencies:

```bash
pnpm --dir apps/web install
```

Install API dependencies:

```bash
pnpm install:api
```

Optional environment override:

```bash
cp apps/web/.env.example apps/web/.env.local
```

By default the web app talks to the FastAPI server at `http://127.0.0.1:8000`, which matches `pnpm dev:api`.

Run the new web app:

```bash
pnpm dev:web
```

Run the new API:

```bash
pnpm dev:api
```

## What is already in place

- Warm, simplified recruiting dashboard outside Frappe
- Dedicated pages for `总览 / 岗位 / 候选人 / 面试`
- Shared JSON data contract for front-end and API
- API endpoints for overview data, jobs, candidates, interviews
- Web pages prefer live FastAPI data and automatically fall back when API is down
- API preview endpoints that already reuse existing business logic:
  - `POST /api/screening/preview`
  - `POST /api/requisitions/agency-brief`

## Next migration queue

1. Replace shared JSON with Postgres-backed persistence.
2. Port resume intake and parsing into background jobs.
3. Add authentication and role-scoped views.
4. Migrate candidate timeline, interview feedback, and offer handoff into the new API.
5. Retire Frappe UI once the new flow covers the daily happy path.
