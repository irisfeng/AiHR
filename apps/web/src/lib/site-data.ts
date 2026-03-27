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

export interface CandidateTimelineEvent {
  id: string;
  eventType: string;
  title: string;
  detail: string;
  actor: string;
  happenedAt: string;
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

export function buildFallbackCandidateTimeline(
  candidate: CandidateRecord,
  interviews: InterviewRecord[],
): CandidateTimelineEvent[] {
  const matchedInterviews = interviews.filter(
    (item) => item.candidateName === candidate.name && item.role === candidate.role,
  );

  return [
    {
      id: `${candidate.id}-status`,
      eventType: "candidate_status",
      title: "当前状态",
      detail: `${candidate.status} · ${candidate.nextAction}`,
      actor: candidate.owner,
      happenedAt: "当前",
    },
    {
      id: `${candidate.id}-intake`,
      eventType: "candidate_seeded",
      title: "候选人已入池",
      detail: `来自${candidate.source}，当前匹配分 ${candidate.score}。`,
      actor: candidate.owner,
      happenedAt: "初始数据",
    },
    ...matchedInterviews.map((item) => ({
      id: `${candidate.id}-${item.id}`,
      eventType: "interview",
      title: `${item.round}：${item.status}`,
      detail: `${item.time} · ${item.interviewer} · ${item.summary}`,
      actor: item.interviewer,
      happenedAt: item.time,
    })),
  ];
}

export const topCandidates = sortTopCandidates(recruitmentData.candidates);
export const urgentJobs = sortUrgentJobs(recruitmentData.jobs);
export const pendingFeedback = selectPendingFeedback(recruitmentData.interviews);
