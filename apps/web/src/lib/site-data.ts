import appData from "../../../shared/demo-data.json";

export type Tone = "accent" | "positive" | "warning" | "neutral";

export interface Stat {
  label: string;
  value: string;
  delta: string;
  tone: Tone;
}

export interface PipelineStep {
  label: string;
  count: number;
}

export interface FocusItem {
  title: string;
  detail: string;
  owner: string;
}

export interface PriorityItem {
  title: string;
  detail: string;
  tag: string;
}

export interface OverviewData {
  title: string;
  subtitle: string;
  stats: Stat[];
  pipeline: PipelineStep[];
  focus: FocusItem[];
  priorities: PriorityItem[];
}

export interface JobRecord {
  id: string;
  title: string;
  team: string;
  location: string;
  mode: string;
  headcount: number;
  stage: string;
  updatedAt: string;
  applicants: number;
  screened: number;
  interviews: number;
  offers: number;
  owner: string;
  urgency: "critical" | "high" | "medium";
  summary: string;
  skills: string[];
}

export interface CandidateRecord {
  id: string;
  name: string;
  role: string;
  score: number;
  status: string;
  city: string;
  experience: string;
  owner: string;
  source: string;
  nextAction: string;
  skills: string[];
  highlights: string[];
  risks: string[];
}

export interface InterviewRecord {
  id: string;
  candidateName: string;
  role: string;
  round: string;
  mode: string;
  time: string;
  interviewer: string;
  status: string;
  decisionWindow: string;
  packStatus: string;
  summary: string;
}

export interface AppData {
  overview: OverviewData;
  jobs: JobRecord[];
  candidates: CandidateRecord[];
  interviews: InterviewRecord[];
}

export const fallbackRecruitmentData = appData as AppData;
export const recruitmentData = fallbackRecruitmentData;

export function sortTopCandidates(items: CandidateRecord[]): CandidateRecord[] {
  return [...items].sort((left, right) => right.score - left.score);
}

export function sortUrgentJobs(items: JobRecord[]): JobRecord[] {
  const order = { critical: 0, high: 1, medium: 2 };
  return [...items].sort((left, right) => order[left.urgency] - order[right.urgency]);
}

export function selectPendingFeedback(items: InterviewRecord[]): InterviewRecord[] {
  return items.filter((item) => item.status === "待反馈");
}

export const topCandidates = sortTopCandidates(recruitmentData.candidates);
export const urgentJobs = sortUrgentJobs(recruitmentData.jobs);
export const pendingFeedback = selectPendingFeedback(recruitmentData.interviews);
