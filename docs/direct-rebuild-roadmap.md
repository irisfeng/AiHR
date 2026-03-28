# Direct Rebuild Roadmap

## Goal

Stop extending the old Frappe shell. Keep the reusable recruiting logic and ship a direct-rebuild MVP that serves one primary operator: the HR specialist.

## Current product shape

The standalone stack is now:

- `apps/web`: Next.js HR-specialist-first workspace
- `apps/api`: FastAPI + SQLite recruiting API
- `apps/shared/demo-data.json`: fallback/demo contract

The MVP navigation is:

- `/` `待办`
- `/jobs` `岗位需求`
- `/candidates` `候选人`
- `/manager/reviews` `用人经理复核入口`
- `/interviews` `面试与录用`
- `/settings` `设置与模板`

## Local commands

Install dependencies:

```bash
pnpm install
pnpm install:api
```

Run the API:

```bash
pnpm dev:api
```

Run the web app:

```bash
pnpm dev:web
```

Default API base URL is `http://127.0.0.1:8000`. If you need another port, set `NEXT_PUBLIC_AIHR_API_BASE_URL` before building or running the web app.

## What is already in place

- Queue-first home page for HR execution instead of a dashboard-first shell
- Requisition intake from free-text hiring-manager requests
- JD generation that links the intake to a job record
- Agency dispatch tracking
- ZIP resume intake with background parsing and candidate creation
- Candidate export JSON + Excel download
- Lightweight agency scorecards
- Minimal hiring-manager review page
- Interview scheduling, feedback follow-up, and offer closeout
- SQLite-backed persistence with seeded demo data

## Core API coverage

The direct rebuild API now exposes:

- `GET /api/work-queue`
- `GET /api/requisition-intakes`
- `POST /api/requisition-intakes`
- `POST /api/requisition-intakes/{id}/generate-jd`
- `GET /api/agency-dispatches`
- `POST /api/agency-dispatches`
- `POST /api/intake-jobs`
- `GET /api/intake-jobs`
- `GET /api/intake-jobs/{id}`
- `GET /api/manager-review-requests`
- `POST /api/candidates/{id}/review`
- `GET /api/candidate-export`
- `GET /api/candidate-export.xlsx`
- `GET /api/agencies/scorecard`
- `GET /api/interviews`
- `POST /api/interviews`
- `POST /api/interviews/{id}/feedback`
- `GET /api/offers`
- `POST /api/offers`
- `POST /api/offers/{id}/payroll-ready`

## What remains after this MVP

1. Add authentication and role-scoped access instead of the current demo-open flows.
2. Replace SQLite with Postgres once deployment and multi-user usage become a priority.
3. Add filtered export downloads and saved report presets.
4. Add richer intake sources such as voice transcription and direct PDF upload.
5. Replace remaining shared demo fallbacks once the API covers all live scenarios.
6. Retire the legacy Frappe UI after the new stack becomes the default operating path.
