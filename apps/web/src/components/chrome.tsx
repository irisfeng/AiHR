import Link from "next/link";
import type { ReactNode } from "react";

import type { DataSource } from "@/lib/api";

type SectionKey = "queue" | "jobs" | "candidates" | "interviews" | "settings";

const navigation = [
  {
    key: "queue",
    label: "待办",
    href: "/",
    caption: "HR 执行台",
  },
  {
    key: "jobs",
    label: "岗位需求",
    href: "/jobs",
    caption: "采集与外发",
  },
  {
    key: "candidates",
    label: "候选人",
    href: "/candidates",
    caption: "导入与复核",
  },
  {
    key: "interviews",
    label: "面试与录用",
    href: "/interviews",
    caption: "安排与收口",
  },
  {
    key: "settings",
    label: "设置与模板",
    href: "/settings",
    caption: "模板与口径",
  },
] as const;

export function AppShell(props: {
  section: SectionKey;
  title: string;
  subtitle: string;
  source?: DataSource;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const { section, title, subtitle, source, actions, children } = props;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-mark">
          <div className="brand-mark__pulse" />
          <div>
            <p className="eyebrow">AIHR HR Specialist MVP</p>
            <h1>待办工作台</h1>
          </div>
        </div>
        <nav className="nav-list" aria-label="Primary">
          {navigation.map((item) => (
            <Link
              key={item.key}
              className={`nav-link ${section === item.key ? "nav-link--active" : ""}`}
              href={item.href}
            >
              <span>{item.label}</span>
              <small>{item.caption}</small>
            </Link>
          ))}
        </nav>
        <div className="sidebar-card">
          <p className="eyebrow">核心原则</p>
          <p>
            默认先看下一步动作，不先看驾驶舱。HR 负责推进，用人经理只负责判断。
          </p>
        </div>
      </aside>

      <main className="main-column">
        <header className="topbar">
          <div>
            <p className="eyebrow">Queue First</p>
            <h2>{title}</h2>
            <p className="subtle-text">{subtitle}</p>
          </div>
          <div className="topbar__actions">
            {source ? <DataSourceBadge source={source} /> : null}
            <div className="identity-pill">
              <strong>周岩</strong>
              <span>HR 专员</span>
            </div>
            {actions}
          </div>
        </header>

        <div className="content-stack">{children}</div>
      </main>
    </div>
  );
}

function DataSourceBadge(props: { source: DataSource }) {
  const live = props.source === "live";

  return (
    <div className={`data-source-pill ${live ? "data-source-pill--live" : "data-source-pill--fallback"}`}>
      <span className="data-source-pill__dot" />
      <strong>{live ? "Live API" : "Fallback Data"}</strong>
      <small>{live ? "页面已接到 FastAPI" : "API 不可达，自动回退"}</small>
    </div>
  );
}

export function Panel(props: { title: string; caption?: string; children: ReactNode; className?: string }) {
  const className = props.className ? `panel ${props.className}` : "panel";
  return (
    <section className={className}>
      <div className="panel__header">
        <div>
          <h3>{props.title}</h3>
          {props.caption ? <p className="subtle-text">{props.caption}</p> : null}
        </div>
      </div>
      {props.children}
    </section>
  );
}

export function StatusPill(props: { children: ReactNode; tone?: "accent" | "positive" | "warning" | "critical" | "neutral" }) {
  const tone = props.tone ?? "neutral";
  return <span className={`status-pill status-pill--${tone}`}>{props.children}</span>;
}

export function TagList(props: { items: string[] }) {
  return (
    <div className="tag-list">
      {props.items.map((item) => (
        <span key={item} className="tag-chip">
          {item}
        </span>
      ))}
    </div>
  );
}

export function StatCard(props: { label: string; value: string; delta: string; tone: "accent" | "positive" | "warning" | "neutral" }) {
  return (
    <article className={`stat-card stat-card--${props.tone}`}>
      <p>{props.label}</p>
      <strong>{props.value}</strong>
      <span>{props.delta}</span>
    </article>
  );
}
