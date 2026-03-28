import type { WorkQueueGroup } from "@/lib/site-data";

export function HrQueueBoard(props: { groups: WorkQueueGroup[] }) {
  return (
    <section className="queue-board">
      {props.groups.map((group) => (
        <article className="queue-group" key={group.key}>
          <header className="queue-group__header">
            <div>
              <p className="eyebrow">{group.title}</p>
              <h3>{group.count} 项待处理</h3>
            </div>
          </header>
          <div className="queue-group__body">
            {group.items.length ? (
              group.items.map((item) => (
                <a className="queue-card" href={item.href} key={item.id}>
                  <div className="queue-card__top">
                    <strong>{item.title}</strong>
                    <span>{item.stage}</span>
                  </div>
                  <p>{item.nextAction}</p>
                  <small>
                    {item.waitingOn} · {item.dueLabel}
                  </small>
                </a>
              ))
            ) : (
              <div className="queue-card queue-card--empty">
                <strong>当前为空</strong>
                <p>这一组暂时没有积压，可以继续处理其他动作。</p>
              </div>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}
