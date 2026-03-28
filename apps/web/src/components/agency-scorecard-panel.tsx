import { StatusPill } from "@/components/chrome";
import type { AgencyScorecard } from "@/lib/site-data";

function ratingTone(rating: AgencyScorecard["rating"]): "positive" | "warning" | "neutral" {
  if (rating === "A") {
    return "positive";
  }
  if (rating === "B") {
    return "warning";
  }
  return "neutral";
}

export function AgencyScorecardPanel(props: { scorecards: AgencyScorecard[] }) {
  const { scorecards } = props;

  if (!scorecards.length) {
    return <p className="subtle-text">当前还没有代理商评估数据。随着外发、面试和录用记录累积，这里会自动形成评分。</p>;
  }

  return (
    <div className="stack-list">
      {scorecards.map((scorecard) => (
        <article className="list-card" key={scorecard.agencyName}>
          <div className="list-card__headline">
            <div>
              <h4>{scorecard.agencyName}</h4>
              <p className="subtle-text">按事实指标做轻量评级，不做黑盒打分。</p>
            </div>
            <StatusPill tone={ratingTone(scorecard.rating)}>{scorecard.rating} 级</StatusPill>
          </div>
          <div className="agency-scorecard__metrics">
            <div className="mini-stat">
              <strong>{scorecard.resumeCount}</strong>
              <span>推荐简历数</span>
            </div>
            <div className="mini-stat">
              <strong>{scorecard.screenPassRate}%</strong>
              <span>初筛通过率</span>
            </div>
            <div className="mini-stat">
              <strong>{scorecard.managerPassRate}%</strong>
              <span>经理通过率</span>
            </div>
            <div className="mini-stat">
              <strong>{scorecard.interviewConversionRate}%</strong>
              <span>面试转化率</span>
            </div>
            <div className="mini-stat">
              <strong>{scorecard.offerConversionRate}%</strong>
              <span>Offer 转化率</span>
            </div>
            <div className="mini-stat">
              <strong>{scorecard.hireConversionRate}%</strong>
              <span>最终录用率</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
