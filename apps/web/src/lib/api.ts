import {
  buildFallbackCandidateTimeline,
  fallbackAgencyScorecards,
  fallbackCandidateExportRows,
  fallbackRequisitionIntakes,
  fallbackRecruitmentData,
  fallbackWorkQueue,
  selectActiveOffers,
  selectPendingFeedback,
  sortTopCandidates,
  sortUrgentJobs,
  type AgencyScorecard,
  type CandidateRecord,
  type CandidateExportRow,
  type CandidateTimelineEvent,
  type InterviewRecord,
  type JobRecord,
  type OfferRecord,
  type OverviewData,
  type RequisitionIntakeRecord,
  type WorkQueueData,
} from "@/lib/site-data";

export type DataSource = "live" | "fallback";

export interface RecruitmentWorkspaceData {
  overview: OverviewData;
  jobs: JobRecord[];
  candidates: CandidateRecord[];
  interviews: InterviewRecord[];
  offers: OfferRecord[];
  source: DataSource;
}

export interface ScreeningPreviewRequest {
  name: string;
  city: string;
  skills: string[];
  years_of_experience: number;
  requirements: string;
  preferred_skills: string;
  preferred_city: string;
}

export interface ScreeningPreviewResponse {
  overall_score: number;
  recommended_status: string;
  matched_skills: string[];
  matched_preferred_skills: string[];
  missing_skills: string[];
  summary: string;
  strengths: string[];
  risks: string[];
  suggested_questions: string[];
  next_action: string;
}

export interface CandidateReviewRequest {
  decision: "advance" | "hold" | "reject";
  summary: string;
  actor: string;
  next_step: string;
  schedule_interview: boolean;
  interview_round: string;
  interview_time: string;
  interviewer: string;
  interview_mode: string;
  interview_summary: string;
  decision_window: string;
  pack_status: string;
}

export interface CandidateReviewResponse {
  candidate: CandidateRecord;
  interview: InterviewRecord | null;
  timeline: CandidateTimelineEvent[];
}

export interface AgencyBriefRequest {
  job_title: string;
  designation: string;
  department: string;
  aihr_work_city: string;
  aihr_work_mode: string;
  aihr_work_schedule: string;
  aihr_salary_currency: string;
  aihr_salary_min: string;
  aihr_salary_max: string;
  aihr_must_have_skills: string;
  aihr_nice_to_have_skills: string;
  reason_for_requesting: string;
}

export interface AgencyBriefResponse {
  payload: Record<string, unknown>;
  brief: string;
}

export interface OfferCreateRequest {
  candidate_id: string;
  job_id: string;
  status: string;
  salary_expectation: string;
  compensation_notes: string;
  onboarding_owner: string;
  payroll_owner: string;
}

export interface ResumeIntakeJobItem {
  id: string;
  fileName: string;
  fileExtension: string;
  status: string;
  reason: string;
  parserEngine: string;
  parsedResume: Record<string, unknown>;
  candidateId: string;
  candidateSummary?: CandidateRecord;
}

export interface ResumeIntakeJobRecord {
  id: string;
  archiveName: string;
  jobId: string;
  jobTitle: string;
  owner: string;
  source: string;
  status: string;
  summary: {
    totalFiles: number;
    parsedCount: number;
    unsupportedCount: number;
    failedCount: number;
    createdCandidateCount: number;
  };
  errorMessage: string;
  updatedAt: string;
  items: ResumeIntakeJobItem[];
}

export interface RequisitionIntakeCreateRequest {
  owner: string;
  hiring_manager: string;
  raw_request_text: string;
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const serverApiBaseUrl =
  process.env.AIHR_API_BASE_URL ?? process.env.NEXT_PUBLIC_AIHR_API_BASE_URL ?? DEFAULT_API_BASE_URL;

export const browserApiBaseUrl =
  process.env.NEXT_PUBLIC_AIHR_API_BASE_URL ?? process.env.AIHR_API_BASE_URL ?? DEFAULT_API_BASE_URL;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${serverApiBaseUrl}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(2000),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${browserApiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to post ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getRecruitmentWorkspaceData(): Promise<RecruitmentWorkspaceData> {
  try {
    const [overview, jobs, candidates, interviews, offers] = await Promise.all([
      fetchJson<OverviewData>("/api/overview"),
      fetchJson<JobRecord[]>("/api/jobs"),
      fetchJson<CandidateRecord[]>("/api/candidates"),
      fetchJson<InterviewRecord[]>("/api/interviews"),
      fetchJson<OfferRecord[]>("/api/offers"),
    ]);

    return {
      overview,
      jobs,
      candidates,
      interviews,
      offers,
      source: "live",
    };
  } catch {
    return {
      ...fallbackRecruitmentData,
      source: "fallback",
    };
  }
}

export async function getCandidateTimeline(
  candidate: CandidateRecord,
  interviews: InterviewRecord[],
): Promise<CandidateTimelineEvent[]> {
  const fallbackTimeline = buildFallbackCandidateTimeline(candidate, interviews);

  try {
    return await fetchJson<CandidateTimelineEvent[]>(`/api/candidates/${candidate.id}/timeline`);
  } catch {
    return fallbackTimeline;
  }
}

export async function getResumeIntakeJobs(): Promise<ResumeIntakeJobRecord[]> {
  try {
    return await fetchJson<ResumeIntakeJobRecord[]>("/api/intake-jobs");
  } catch {
    return [];
  }
}

export async function getResumeIntakeJob(intakeJobId: string): Promise<ResumeIntakeJobRecord | null> {
  try {
    return await fetchJson<ResumeIntakeJobRecord>(`/api/intake-jobs/${intakeJobId}`);
  } catch {
    return null;
  }
}

export async function getWorkQueue(): Promise<WorkQueueData> {
  try {
    return await fetchJson<WorkQueueData>("/api/work-queue");
  } catch {
    return fallbackWorkQueue;
  }
}

export async function getRequisitionIntakes(): Promise<RequisitionIntakeRecord[]> {
  try {
    return await fetchJson<RequisitionIntakeRecord[]>("/api/requisition-intakes");
  } catch {
    return fallbackRequisitionIntakes;
  }
}

export async function createRequisitionIntake(payload: RequisitionIntakeCreateRequest): Promise<RequisitionIntakeRecord> {
  return postJson<RequisitionIntakeRecord>("/api/requisition-intakes", payload);
}

export async function generateRequisitionJd(requisitionId: string): Promise<RequisitionIntakeRecord> {
  return postJson<RequisitionIntakeRecord>(`/api/requisition-intakes/${requisitionId}/generate-jd`, {});
}

export async function getCandidateExportRows(): Promise<CandidateExportRow[]> {
  try {
    const payload = await fetchJson<{ rows: CandidateExportRow[] }>("/api/candidate-export");
    return payload.rows;
  } catch {
    return fallbackCandidateExportRows;
  }
}

export async function getAgencyScorecards(): Promise<AgencyScorecard[]> {
  try {
    return await fetchJson<AgencyScorecard[]>("/api/agencies/scorecard");
  } catch {
    return fallbackAgencyScorecards;
  }
}

export function deriveWorkspaceSlices(data: RecruitmentWorkspaceData) {
  return {
    urgentJobs: sortUrgentJobs(data.jobs),
    topCandidates: sortTopCandidates(data.candidates),
    pendingFeedback: selectPendingFeedback(data.interviews),
    activeOffers: selectActiveOffers(data.offers),
  };
}
