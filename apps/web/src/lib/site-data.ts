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

export interface OfferRecord {
  id: string;
  candidateId: string;
  jobId: string;
  candidateName: string;
  openingTitle: string;
  status: string;
  onboardingOwner: string;
  payrollOwner: string;
  payrollHandoffStatus: string;
  salaryExpectation: string;
  compensationNotes: string;
  handoffSummary: string;
  payrollHandoffSummary: string;
  nextAction: string;
}

export interface WorkQueueItem {
  id: string;
  title: string;
  stage: string;
  nextAction: string;
  dueLabel: string;
  waitingOn: string;
  href: string;
}

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

export interface WorkQueueData {
  groups: WorkQueueGroup[];
}

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

export interface CandidateExportRow {
  candidateId: string;
  name: string;
  jobTitle: string;
  source: string;
  agency: string;
  receivedAt: string;
  aiScreeningResult: number;
  managerReviewResult: string;
  interviewStages: string;
  finalStatus: string;
  salaryResult: string;
  currentStatus: string;
  remarks: string;
  updatedAt: string;
}

export interface AppData {
  overview: OverviewData;
  jobs: JobRecord[];
  candidates: CandidateRecord[];
  interviews: InterviewRecord[];
  offers: OfferRecord[];
}

export const fallbackRecruitmentData = appData as AppData;
export const recruitmentData = fallbackRecruitmentData;

export const fallbackRequisitionIntakes: RequisitionIntakeRecord[] = [
  {
    id: "req-fallback-001",
    owner: "周岩",
    hiringManager: "张经理",
    rawRequestText: "帮我招一个资深后端，偏 Python、微服务和高并发，越快到岗越好。",
    status: "待整理",
    extractedPayload: {
      岗位名称: "资深后端工程师",
      招聘背景: "平台研发团队需要补充后端主力，支撑交易链路和微服务治理。",
      核心职责: "负责 Python 服务开发、接口稳定性与高并发场景优化。",
      必须具备能力: "Python、微服务、高并发",
      加分项: "FastAPI、PostgreSQL、Redis",
      地点: "待确认",
      职级: "待确认",
    },
    missingFields: ["地点缺失", "职级缺失"],
    jdText: "",
    linkedJobId: "",
  },
];

export const fallbackAgencyScorecards: AgencyScorecard[] = [
  {
    agencyName: "猎头",
    resumeCount: 2,
    screenPassRate: 100,
    managerPassRate: 100,
    interviewConversionRate: 100,
    offerConversionRate: 50,
    hireConversionRate: 50,
    rating: "A",
  },
  {
    agencyName: "Boss 直聘",
    resumeCount: 1,
    screenPassRate: 100,
    managerPassRate: 100,
    interviewConversionRate: 100,
    offerConversionRate: 0,
    hireConversionRate: 0,
    rating: "B",
  },
];

export const fallbackCandidateExportRows: CandidateExportRow[] = fallbackRecruitmentData.candidates.map((candidate) => ({
  candidateId: candidate.id,
  name: candidate.name,
  jobTitle: candidate.role,
  source: candidate.source,
  agency: candidate.source,
  receivedAt: "系统内已录入",
  aiScreeningResult: candidate.score,
  managerReviewResult: candidate.status,
  interviewStages: "视当前记录而定",
  finalStatus: candidate.status,
  salaryResult: "",
  currentStatus: candidate.status,
  remarks: candidate.nextAction,
  updatedAt: "当前",
}));

export const fallbackWorkQueue: WorkQueueData = {
  groups: [
    {
      key: "requisition_intake",
      title: "待整理需求",
      count: 1,
      items: [
        {
          id: "req-fallback-001",
          title: "资深后端工程师",
          stage: "待整理",
          nextAction: "补齐地点和职级后生成 JD",
          dueLabel: "今天",
          waitingOn: "周岩",
          href: "/jobs#requisition-intake",
        },
      ],
    },
    {
      key: "jd_confirmation",
      title: "待生成 / 确认 JD",
      count: 1,
      items: [
        {
          id: "req-fallback-002",
          title: "算法平台工程师",
          stage: "待确认 JD",
          nextAction: "确认用词后发起 AI 润色",
          dueLabel: "今天",
          waitingOn: "刘颖",
          href: "/jobs#jd-confirmation",
        },
      ],
    },
    {
      key: "agency_dispatch",
      title: "待发代理",
      count: 1,
      items: [
        {
          id: "job-backend-01",
          title: "资深后端工程师",
          stage: "待发代理",
          nextAction: "发给 3 家代理并记录时间",
          dueLabel: "今天",
          waitingOn: "周岩",
          href: "/jobs#agency-dispatch",
        },
      ],
    },
    {
      key: "resume_intake",
      title: "待处理简历包",
      count: 1,
      items: [
        {
          id: "intake-fallback-001",
          title: "后端工程师 ZIP 简历包",
          stage: "待处理",
          nextAction: "上传 ZIP 并触发 AI 初筛",
          dueLabel: "本日",
          waitingOn: "周岩",
          href: "/candidates#resume-intake",
        },
      ],
    },
    {
      key: "manager_review",
      title: "待经理复核",
      count: 2,
      items: [
        {
          id: "cand-005",
          title: "周闻笙 · 资深后端工程师",
          stage: "待经理复核",
          nextAction: "发给用人经理确认是否推进",
          dueLabel: "今天",
          waitingOn: "张经理",
          href: "/candidates#candidate-review-panel",
        },
        {
          id: "cand-002",
          title: "梁嘉禾 · 算法平台工程师",
          stage: "待经理复核",
          nextAction: "补充风险说明后再次发起复核",
          dueLabel: "今天",
          waitingOn: "沈珂",
          href: "/candidates#candidate-review-panel",
        },
      ],
    },
    {
      key: "interview_or_closeout",
      title: "待约面试 / 待补录用资料",
      count: 2,
      items: [
        {
          id: "int-001",
          title: "王书衡 · 技术一面",
          stage: "待反馈",
          nextAction: "催收面试反馈并决定下一步",
          dueLabel: "今天 18:00",
          waitingOn: "顾峰",
          href: "/interviews#feedback",
        },
        {
          id: "offer-001",
          title: "王书衡 · Offer 收口",
          stage: "待补资料",
          nextAction: "补齐体验报告和无犯罪记录",
          dueLabel: "本周",
          waitingOn: "林薇",
          href: "/interviews#closeout",
        },
      ],
    },
  ],
};

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

export function selectActiveOffers(items: OfferRecord[]): OfferRecord[] {
  return items.filter((item) => item.status !== "Rejected");
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
export const activeOffers = selectActiveOffers(recruitmentData.offers);
