# HR 专员待办工作台 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the HR-specialist-first recruiting MVP on the direct rebuild stack: queue-first home page, requisition intake from free text, agency dispatch tracking, candidate export, agency scorecards, manager review inbox, and a unified interviews/offers closeout flow.

**Architecture:** Extend the current FastAPI + SQLite backend with three new domain slices: requisition intake, agency dispatch, and review/export analytics. Reuse the existing jobs/candidates/interviews/offers records as the durable workflow spine, then reshape the Next.js shell around action-first task queues instead of overview cards. Keep the manager side lightweight with a dedicated review page instead of a second operator console.

**Tech Stack:** Next.js App Router, React server/client components, TypeScript, FastAPI, Pydantic, SQLite, pytest, pnpm, openpyxl (for Excel export if not already present).

---

## File Map

### Backend

- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/app/store.py`
  - Add SQLite tables for requisition intakes, agency dispatches, and manager review requests.
  - Add read/write helpers for the HR queue, Excel export rows, and agency scorecards.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/app/main.py`
  - Add FastAPI request/response models and endpoints for queue data, requisition intake, JD generation, agency dispatch, export, and agency metrics.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/requirements.txt`
  - Add `openpyxl` if Excel export is not already available transitively.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/shared/demo-data.json`
  - Seed new intake, dispatch, and agency scorecard demo fixtures.

### Frontend

- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/api.ts`
  - Add typed fetch helpers and mutations for queue data, requisition intake, agency dispatch, export, and agency scorecards.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/site-data.ts`
  - Add fallback types and data for queue groups, requisition records, dispatch rows, and agency scorecards.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/chrome.tsx`
  - Rename navigation to `待办 / 岗位需求 / 候选人 / 面试与录用 / 设置与模板`.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/page.tsx`
  - Replace the dashboard with the queue-first home page.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/jobs/page.tsx`
  - Make this the requisition intake + JD + agency dispatch page.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/candidates/page.tsx`
  - Focus on resume intake, candidate review, and export.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/interviews/page.tsx`
  - Combine interview scheduling, feedback follow-up, and offer closeout queues.
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/manager/reviews/page.tsx`
  - Minimal manager review experience.
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/requisition-intake-workbench.tsx`
  - Free-text intake and JD draft editing.
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/agency-dispatch-workbench.tsx`
  - Record which agencies received a JD and when.
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/hr-queue-board.tsx`
  - Reusable queue group renderer for the home page.
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/candidate-export-panel.tsx`
  - Filter and export candidate totals.
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/agency-scorecard-panel.tsx`
  - Show agency metrics and simple ratings.
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/globals.css`
  - Replace dashboard-centric layout classes with queue-centric styles and the new workbench components.

### Tests and Docs

- Modify: `/Users/tony/Documents/GitHub/aihr/tests/test_direct_rebuild_api.py`
  - Add coverage for queue data, requisition intake, JD generation, agency dispatch, export rows, and agency metrics.
- Modify: `/Users/tony/Documents/GitHub/aihr/docs/direct-rebuild-roadmap.md`
  - Update “already in place” and “next migration queue” to reflect the queue-first shell.
- Modify: `/Users/tony/Documents/GitHub/aihr/docs/user-manual.md`
  - Replace the old Frappe-centric manual with the new direct-rebuild usage guide.

## Task 1: Add backend schema for requisition intake, dispatch, and queue data

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/tests/test_direct_rebuild_api.py`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/app/store.py`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/shared/demo-data.json`

- [ ] **Step 1: Write the failing tests for queue and requisition intake**

```python
def test_work_queue_groups_items_by_hr_action(self):
    response = self.client.get("/api/work-queue")
    self.assertEqual(response.status_code, 200)
    payload = response.json()
    self.assertEqual(payload["groups"][0]["key"], "requisition_intake")
    self.assertGreaterEqual(payload["groups"][0]["count"], 1)


def test_create_requisition_intake_extracts_missing_fields_and_creates_draft(self):
    response = self.client.post(
        "/api/requisition-intakes",
        json={
            "owner": "周岩",
            "hiring_manager": "张经理",
            "raw_request_text": "想招一个资深后端，偏 Python 和微服务，最好尽快到岗。",
        },
    )
    self.assertEqual(response.status_code, 201)
    payload = response.json()
    self.assertEqual(payload["status"], "待确认 JD")
    self.assertIn("地点缺失", payload["missingFields"])
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_direct_rebuild_api.py -k "work_queue or requisition_intake"
```

Expected: FAIL with `404` for missing endpoints or assertion failure because queue/intake payload does not exist yet.

- [ ] **Step 3: Add SQLite schema and helpers in `store.py`**

Add tables and helper signatures like:

```python
CREATE TABLE IF NOT EXISTS requisition_intakes (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    hiring_manager TEXT NOT NULL,
    raw_request_text TEXT NOT NULL,
    status TEXT NOT NULL,
    extracted_payload_json TEXT NOT NULL,
    missing_fields_json TEXT NOT NULL,
    jd_text TEXT NOT NULL,
    linked_job_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agency_dispatches (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    agency_name TEXT NOT NULL,
    dispatch_status TEXT NOT NULL,
    sent_at_label TEXT NOT NULL,
    first_resume_at_label TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Then implement helpers:

```python
def create_requisition_intake(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> dict[str, Any]:
    extracted = _extract_requisition_fields(payload["raw_request_text"])
    missing_fields = _calculate_missing_fields(extracted)
    record = {
        "id": _next_id("req"),
        "status": "待确认 JD",
        "jd_text": "",
        "linked_job_id": "",
        **payload,
        "extracted_payload": extracted,
        "missing_fields": missing_fields,
    }
    ...
    return serialize_requisition_intake(row)


def build_work_queue(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "groups": [
            _queue_group("requisition_intake", "待整理需求", list_requisition_intakes(...)),
            _queue_group("jd_confirmation", "待生成 / 确认 JD", ...),
            _queue_group("agency_dispatch", "待发代理", ...),
        ]
    }
```

- [ ] **Step 4: Expose queue and requisition endpoints in `main.py`**

Add request models and routes:

```python
class RequisitionIntakeCreateRequest(BaseModel):
    owner: str
    hiring_manager: str
    raw_request_text: str


@app.get("/api/work-queue")
def get_work_queue(connection: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return build_work_queue(connection)


@app.post("/api/requisition-intakes", status_code=status.HTTP_201_CREATED)
def post_requisition_intake(
    payload: RequisitionIntakeCreateRequest,
    connection: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    return create_requisition_intake(connection, payload.model_dump())
```

- [ ] **Step 5: Run the focused tests and then the API suite**

Run:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_direct_rebuild_api.py -k "work_queue or requisition_intake"
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_direct_rebuild_api.py
```

Expected: PASS for the new queue/intake tests and no regressions in the existing direct rebuild API tests.

- [ ] **Step 6: Commit**

```bash
git add tests/test_direct_rebuild_api.py apps/api/app/store.py apps/api/app/main.py apps/shared/demo-data.json
git commit -m "feat: add requisition intake and hr queue api"
```

## Task 2: Add JD generation, agency dispatch tracking, candidate export, and agency scorecards

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/tests/test_direct_rebuild_api.py`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/app/main.py`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/app/store.py`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/api/requirements.txt`

- [ ] **Step 1: Write the failing tests for JD generation, export, and agency metrics**

```python
def test_generate_jd_updates_requisition_and_creates_linked_job(self):
    intake = self.client.post("/api/requisition-intakes", json={...}).json()
    response = self.client.post(f"/api/requisition-intakes/{intake['id']}/generate-jd")
    self.assertEqual(response.status_code, 200)
    payload = response.json()
    self.assertEqual(payload["status"], "待发代理")
    self.assertTrue(payload["jdText"].startswith("岗位名称"))
    self.assertNotEqual(payload["linkedJobId"], "")


def test_candidate_export_returns_all_candidates_with_closed_and_hired_rows(self):
    response = self.client.get("/api/candidate-export?final_status=all")
    self.assertEqual(response.status_code, 200)
    payload = response.json()
    statuses = {item["finalStatus"] for item in payload["rows"]}
    self.assertIn("已录用", statuses)
    self.assertIn("未录用", statuses)


def test_agency_scorecard_aggregates_conversion_metrics(self):
    response = self.client.get("/api/agencies/scorecard")
    self.assertEqual(response.status_code, 200)
    self.assertGreaterEqual(response.json()[0]["resumeCount"], 1)
```

- [ ] **Step 2: Run tests to verify the new coverage fails**

Run:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_direct_rebuild_api.py -k "generate_jd or candidate_export or agency_scorecard"
```

Expected: FAIL with `404` or missing keys because these endpoints do not exist yet.

- [ ] **Step 3: Implement JD generation and agency dispatch writes in `store.py` and `main.py`**

Reuse existing recruiting logic instead of inventing new copy:

```python
def generate_requisition_jd(connection: sqlite3.Connection, requisition_id: str) -> dict[str, Any]:
    requisition = _get_requisition_row(connection, requisition_id)
    payload = build_requisition_payload(requisition["extracted_payload"])
    jd_text = generate_requisition_agency_brief(payload)
    linked_job = _ensure_linked_job(connection, requisition, payload)
    ...
    return serialize_requisition_intake(updated_row)


class AgencyDispatchCreateRequest(BaseModel):
    job_id: str
    agency_name: str
    sent_at_label: str
    notes: str = ""


@app.post("/api/agency-dispatches", status_code=status.HTTP_201_CREATED)
def post_agency_dispatch(...):
    return create_agency_dispatch(connection, payload.model_dump())
```

- [ ] **Step 4: Implement export rows and scorecard aggregation**

Use stable, explainable derived values:

```python
def list_candidate_export_rows(connection: sqlite3.Connection, filters: Mapping[str, str]) -> list[dict[str, Any]]:
    candidates = list_candidates(connection)
    offers = {item["candidateId"]: item for item in list_offers(connection)}
    feedbacks = _load_latest_feedback_by_candidate(connection)
    return [
        {
            "candidateId": candidate["id"],
            "name": candidate["name"],
            "jobTitle": candidate["role"],
            "agency": _resolve_candidate_agency(candidate),
            "managerReviewResult": _resolve_manager_review(candidate["id"]),
            "finalStatus": candidate["status"],
        }
        for candidate in candidates
    ]


def build_agency_scorecards(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "agencyName": agency_name,
            "resumeCount": resume_count,
            "screenPassRate": _rate(screen_pass, resume_count),
            "managerPassRate": _rate(manager_pass, resume_count),
            "rating": _scorecard_rating(offer_rate, hire_rate),
        }
    ]
```

If `openpyxl` is needed for `.xlsx`, add it in `/Users/tony/Documents/GitHub/aihr/apps/api/requirements.txt` and expose `/api/candidate-export.xlsx`.

- [ ] **Step 5: Run API tests, compile the API, and smoke the new endpoints**

Run:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_direct_rebuild_api.py
python3 -m compileall apps/api
python3 - <<'PY'
from fastapi.testclient import TestClient
from apps.api.app import main
client = TestClient(main.app)
print(client.get("/api/work-queue").status_code)
print(client.get("/api/agencies/scorecard").status_code)
PY
```

Expected: tests pass, compileall reports no syntax errors, smoke script prints `200` twice.

- [ ] **Step 6: Commit**

```bash
git add tests/test_direct_rebuild_api.py apps/api/app/main.py apps/api/app/store.py apps/api/requirements.txt
git commit -m "feat: add jd generation exports and agency scorecards"
```

## Task 3: Add frontend data contracts and replace the shell with queue-first navigation

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/api.ts`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/site-data.ts`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/chrome.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/globals.css`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/page.tsx`
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/hr-queue-board.tsx`

- [ ] **Step 1: Write a minimal render test or page-contract assertion for the new queue page**

Add a focused assertion by snapshotting the HTML in a server-rendered smoke test or by checking the built page through Playwright later. The immediate failing unit should target the data contract:

```ts
export interface WorkQueueGroup {
  key:
    | "requisition_intake"
    | "jd_confirmation"
    | "agency_dispatch"
    | "resume_intake"
    | "manager_review"
    | "interview_or_closeout";
  title: string;
  count: number;
  items: WorkQueueItem[];
}
```

- [ ] **Step 2: Add typed API helpers and fallback queue data**

In `api.ts`:

```ts
export interface WorkQueueItem {
  id: string;
  title: string;
  stage: string;
  nextAction: string;
  dueLabel: string;
  waitingOn: string;
  href: string;
}

export interface WorkQueueResponse {
  groups: WorkQueueGroup[];
}

export async function getWorkQueue(): Promise<WorkQueueResponse> {
  try {
    return await fetchJson<WorkQueueResponse>("/api/work-queue");
  } catch {
    return fallbackWorkQueue;
  }
}
```

In `site-data.ts`, add `fallbackWorkQueue` with realistic Chinese queue labels matching the spec.

- [ ] **Step 3: Replace shell navigation and build the reusable queue board**

In `chrome.tsx`, switch to:

```tsx
type SectionKey = "queue" | "jobs" | "candidates" | "interviews" | "settings";

const navigation = [
  { key: "queue", label: "待办", href: "/", caption: "HR 执行台" },
  { key: "jobs", label: "岗位需求", href: "/jobs", caption: "采集与外发" },
  { key: "candidates", label: "候选人", href: "/candidates", caption: "导入与复核" },
  { key: "interviews", label: "面试与录用", href: "/interviews", caption: "安排与收口" },
  { key: "settings", label: "设置与模板", href: "/settings", caption: "模板与口径" },
];
```

Create `hr-queue-board.tsx`:

```tsx
export function HrQueueBoard({ groups }: { groups: WorkQueueGroup[] }) {
  return (
    <div className="queue-grid">
      {groups.map((group) => (
        <section className="queue-column" key={group.key}>
          <header>
            <h3>{group.title}</h3>
            <span>{group.count}</span>
          </header>
          {group.items.map((item) => (
            <a className="queue-card" href={item.href} key={item.id}>
              <strong>{item.title}</strong>
              <p>{item.nextAction}</p>
              <small>{item.stage} · {item.waitingOn} · {item.dueLabel}</small>
            </a>
          ))}
        </section>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Replace `page.tsx` with the queue-first home page**

```tsx
export default async function QueuePage() {
  const [workspace, queue] = await Promise.all([
    getRecruitmentWorkspaceData(),
    getWorkQueue(),
  ]);

  return (
    <AppShell
      section="queue"
      source={workspace.source}
      title="HR 待办工作台"
      subtitle="先处理下一步动作，不先看驾驶舱。"
    >
      <HrQueueBoard groups={queue.groups} />
    </AppShell>
  );
}
```

- [ ] **Step 5: Run frontend checks**

Run:

```bash
pnpm typecheck:web
pnpm build:web
```

Expected: both commands pass without type errors after the navigation and page contract changes.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/site-data.ts apps/web/src/components/chrome.tsx apps/web/src/components/hr-queue-board.tsx apps/web/src/app/page.tsx apps/web/src/app/globals.css
git commit -m "feat: replace dashboard with hr queue shell"
```

## Task 4: Rebuild the jobs page around free-text requisition intake and agency dispatch

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/jobs/page.tsx`
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/requisition-intake-workbench.tsx`
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/agency-dispatch-workbench.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/globals.css`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/api.ts`

- [ ] **Step 1: Add the requisition and dispatch data/mutation contracts**

```ts
export interface RequisitionIntakeRecord {
  id: string;
  owner: string;
  hiringManager: string;
  rawRequestText: string;
  status: string;
  extractedPayload: Record<string, string>;
  missingFields: string[];
  jdText: string;
  linkedJobId: string;
}

export async function createRequisitionIntake(input: RequisitionIntakeCreateRequest) {
  return postJson<RequisitionIntakeRecord>("/api/requisition-intakes", input);
}
```

- [ ] **Step 2: Build the free-text intake workbench**

```tsx
export function RequisitionIntakeWorkbench() {
  const [rawRequestText, setRawRequestText] = useState("");
  const [record, setRecord] = useState<RequisitionIntakeRecord | null>(null);

  async function handleCreate() {
    const created = await createRequisitionIntake({
      owner: "周岩",
      hiring_manager: "张经理",
      raw_request_text: rawRequestText,
    });
    setRecord(created);
  }

  return (
    <section className="split-workbench">
      <textarea value={rawRequestText} onChange={(event) => setRawRequestText(event.target.value)} />
      <div>{record ? <RequisitionDraftPanel record={record} /> : <EmptyDraftState />}</div>
    </section>
  );
}
```

- [ ] **Step 3: Add the agency dispatch recorder**

```tsx
export function AgencyDispatchWorkbench({ jobs }: { jobs: JobRecord[] }) {
  return (
    <form className="dispatch-form">
      <select name="jobId">{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select>
      <input name="agencyName" placeholder="代理商名称" />
      <input name="sentAtLabel" placeholder="03-28 14:30" />
      <button type="submit">记录已外发</button>
    </form>
  );
}
```

- [ ] **Step 4: Rewrite the jobs page**

```tsx
export default async function JobsPage() {
  const data = await getRecruitmentWorkspaceData();
  const queue = await getWorkQueue();

  return (
    <AppShell section="jobs" ...>
      <RequisitionIntakeWorkbench />
      <AgencyDispatchWorkbench jobs={data.jobs} />
      <QueueSummaryPanel group={queue.groups.find((group) => group.key === "agency_dispatch")} />
    </AppShell>
  );
}
```

- [ ] **Step 5: Run typecheck/build and a browser smoke test**

Run:

```bash
pnpm typecheck:web
pnpm build:web
```

Then manually verify or use Playwright against `/jobs` that the page contains:

- `岗位需求采集`
- `经理原始文本`
- `待确认 JD`
- `待发代理`

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/jobs/page.tsx apps/web/src/components/requisition-intake-workbench.tsx apps/web/src/components/agency-dispatch-workbench.tsx apps/web/src/lib/api.ts apps/web/src/app/globals.css
git commit -m "feat: add hr requisition intake and agency dispatch ui"
```

## Task 5: Rebuild the candidates page around resume intake, manager review, and export

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/candidates/page.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/resume-intake-workbench.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/candidate-review-workbench.tsx`
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/candidate-export-panel.tsx`
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/manager/reviews/page.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/api.ts`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/globals.css`

- [ ] **Step 1: Add failing API-contract tests for export filters and manager review listing**

```python
def test_manager_review_requests_are_listed_for_pending_candidates(self):
    response = self.client.get("/api/manager-review-requests")
    self.assertEqual(response.status_code, 200)
    self.assertGreaterEqual(len(response.json()), 1)
```

Then wire the matching TypeScript contracts:

```ts
export interface ManagerReviewRequestRecord {
  id: string;
  candidateId: string;
  candidateName: string;
  role: string;
  status: string;
  hrNote: string;
}
```

- [ ] **Step 2: Add backend listing if missing, then expose frontend helpers**

```ts
export async function getManagerReviewRequests(): Promise<ManagerReviewRequestRecord[]> {
  try {
    return await fetchJson<ManagerReviewRequestRecord[]>("/api/manager-review-requests");
  } catch {
    return [];
  }
}

export async function exportCandidateTotals(params: URLSearchParams) {
  return `${browserApiBaseUrl}/api/candidate-export.xlsx?${params.toString()}`;
}
```

- [ ] **Step 3: Build the export panel and reshape the candidates page**

```tsx
export function CandidateExportPanel() {
  return (
    <section className="export-panel">
      <h3>候选人总表</h3>
      <form>
        <input name="jobTitle" placeholder="岗位名称" />
        <input name="agencyName" placeholder="代理商" />
        <button type="submit">导出 Excel</button>
      </form>
    </section>
  );
}
```

Page structure:

```tsx
<ResumeIntakeWorkbench ... />
<CandidateReviewWorkbench ... />
<CandidateExportPanel />
```

- [ ] **Step 4: Add the minimal manager review page**

```tsx
export default async function ManagerReviewsPage() {
  const requests = await getManagerReviewRequests();
  return (
    <main className="manager-review-page">
      {requests.map((request) => (
        <article key={request.id}>
          <h1>{request.candidateName}</h1>
          <p>{request.hrNote}</p>
          <button>同意推进</button>
          <button>要求补充信息</button>
          <button>暂不推进</button>
        </article>
      ))}
    </main>
  );
}
```

- [ ] **Step 5: Run targeted API tests plus frontend verification**

Run:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_direct_rebuild_api.py -k "manager_review or candidate_export"
pnpm typecheck:web
pnpm build:web
```

Expected: all pass and `/candidates` now exposes resume intake, manager review, and candidate export in one flow.

- [ ] **Step 6: Commit**

```bash
git add tests/test_direct_rebuild_api.py apps/api/app/main.py apps/api/app/store.py apps/web/src/app/candidates/page.tsx apps/web/src/components/resume-intake-workbench.tsx apps/web/src/components/candidate-review-workbench.tsx apps/web/src/components/candidate-export-panel.tsx apps/web/src/app/manager/reviews/page.tsx apps/web/src/lib/api.ts apps/web/src/app/globals.css
git commit -m "feat: refocus candidates flow on review and export"
```

## Task 6: Rebuild interviews page into interview scheduling + offer closeout + agency scorecards

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/interviews/page.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/interview-intake-workbench.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/interview-feedback-workbench.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/offer-handoff-workbench.tsx`
- Create: `/Users/tony/Documents/GitHub/aihr/apps/web/src/components/agency-scorecard-panel.tsx`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/lib/api.ts`
- Modify: `/Users/tony/Documents/GitHub/aihr/apps/web/src/app/globals.css`

- [ ] **Step 1: Add the agency scorecard frontend contract**

```ts
export interface AgencyScorecard {
  agencyName: string;
  resumeCount: number;
  screenPassRate: number;
  managerPassRate: number;
  interviewConversionRate: number;
  offerConversionRate: number;
  hireConversionRate: number;
  rating: "A" | "B" | "C";
}
```

- [ ] **Step 2: Build a reusable agency scorecard panel**

```tsx
export function AgencyScorecardPanel({ scorecards }: { scorecards: AgencyScorecard[] }) {
  return (
    <section className="scorecard-grid">
      {scorecards.map((card) => (
        <article className="scorecard" key={card.agencyName}>
          <h3>{card.agencyName}</h3>
          <p>{card.resumeCount} 份推荐</p>
          <strong>{card.rating}</strong>
        </article>
      ))}
    </section>
  );
}
```

- [ ] **Step 3: Rewrite the interviews page around actions, not lists**

```tsx
export default async function InterviewsPage() {
  const data = await getRecruitmentWorkspaceData();
  const scorecards = await getAgencyScorecards();

  return (
    <AppShell section="interviews" ...>
      <InterviewIntakeWorkbench interviews={data.interviews} />
      <InterviewFeedbackWorkbench interviews={data.interviews} />
      <OfferHandoffWorkbench candidates={data.candidates} jobs={data.jobs} offers={data.offers} />
      <AgencyScorecardPanel scorecards={scorecards} />
    </AppShell>
  );
}
```

- [ ] **Step 4: Align copy and styles with the spec**

Update the component labels to reflect:

- `待约面试`
- `待反馈`
- `待补录用资料`
- `代理商质量`

Replace leftover “dashboard” language in `globals.css` with queue and workbench terminology.

- [ ] **Step 5: Run end-to-end frontend verification**

Run:

```bash
pnpm typecheck:web
pnpm build:web
```

Then smoke with Playwright or manual browser verification for:

- `/interviews`
- `/manager/reviews`
- `/candidates`

Expected: each page loads and exposes the new action-first labels.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/interviews/page.tsx apps/web/src/components/interview-intake-workbench.tsx apps/web/src/components/interview-feedback-workbench.tsx apps/web/src/components/offer-handoff-workbench.tsx apps/web/src/components/agency-scorecard-panel.tsx apps/web/src/lib/api.ts apps/web/src/app/globals.css apps/web/src/app/manager/reviews/page.tsx
git commit -m "feat: combine interview closeout and agency scorecards"
```

## Task 7: Update docs and run full verification

**Files:**
- Modify: `/Users/tony/Documents/GitHub/aihr/docs/direct-rebuild-roadmap.md`
- Modify: `/Users/tony/Documents/GitHub/aihr/docs/user-manual.md`

- [ ] **Step 1: Rewrite the roadmap status to match the new shell**

Update the “already in place” section to describe:

```md
- Queue-first HR specialist home page
- Free-text requisition intake and JD confirmation flow
- Agency dispatch tracking
- Candidate export and agency scorecards
- Minimal manager review page
```

- [ ] **Step 2: Rewrite the user manual for the direct rebuild MVP**

The manual must include concrete sections for:

```md
## HR 日常工作路径
## 用人经理复核路径
## 岗位需求采集
## ZIP / PDF 简历导入
## 候选人总表导出
## 代理商质量评估
## 面试与录用收口
## 常见异常处理
```

- [ ] **Step 3: Run the full verification suite**

Run:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
python3 -m compileall apps/api
pnpm typecheck:web
pnpm build:web
```

Expected:

- `pytest` passes
- `compileall` reports no syntax errors
- `pnpm typecheck:web` passes
- `pnpm build:web` passes

- [ ] **Step 4: Smoke the main paths through the running apps**

Run the apps:

```bash
AIHR_API_DATABASE_PATH=/tmp/aihr-mvp.sqlite3 pnpm dev:api
pnpm dev:web
```

Verify these pages in a real browser:

- `/`
- `/jobs`
- `/candidates`
- `/interviews`
- `/manager/reviews`

Confirm these strings are visible:

- `HR 待办工作台`
- `岗位需求采集`
- `候选人总表`
- `代理商质量`

- [ ] **Step 5: Commit**

```bash
git add docs/direct-rebuild-roadmap.md docs/user-manual.md
git commit -m "docs: add hr specialist mvp manual"
```

## Self-Review

### Spec coverage

- Queue-first home page: covered by Task 3.
- Free-text requisition intake and JD generation: covered by Tasks 1, 2, and 4.
- Agency dispatch tracking: covered by Tasks 2 and 4.
- Resume intake and manager review as candidate flow: covered by Task 5.
- Unified interview and closeout page: covered by Task 6.
- Candidate export and agency quality evaluation: covered by Tasks 2, 5, and 6.
- Overall usage manual: covered by Task 7.

### Placeholder scan

- No `TBD`, `TODO`, or “implement later” placeholders.
- Every task includes exact files, commands, and a concrete target code shape.

### Type consistency

- Queue types use `WorkQueueGroup`/`WorkQueueItem` consistently across page and component tasks.
- Requisition flow uses `RequisitionIntakeRecord` consistently in API and UI steps.
- Agency metrics use `AgencyScorecard` consistently in API and UI steps.
