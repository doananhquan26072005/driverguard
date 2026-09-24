import { formatNumber, formatPercent } from "../lib/format";
import { LEVELS } from "../lib/labels";
import type { Stats } from "../lib/types";

export default function StatsTiles({ stats }: { stats: Stats | null }) {
  const total = stats?.total ?? 0;
  const falseRate = total ? (stats?.false_alarms ?? 0) / total : null;
  return (
    <section className="tiles" aria-label="Tổng quan">
      <Tile label="Tổng cảnh báo" value={formatNumber(stats ? total : null)} />
      {([1, 2, 3] as const).map((lv) => (
        <Tile
          key={lv}
          label={`${LEVELS[lv].short} · ${LEVELS[lv].title}`}
          value={formatNumber(stats ? (stats.by_level[lv] ?? 0) : null)}
          badge={lv}
        />
      ))}
      <Tile
        label="Tài xế báo sai"
        value={formatPercent(falseRate)}
        note={stats ? `${stats.false_alarms} / ${total} cảnh báo` : undefined}
      />
    </section>
  );
}

function Tile({ label, value, note, badge }: { label: string; value: string; note?: string; badge?: 1 | 2 | 3 }) {
  return (
    <div className="tile">
      <div className="tile-label">
        {badge && (
          <span className={`badge-dot level-${badge}`} aria-hidden>
            {LEVELS[badge].icon}
          </span>
        )}
        {label}
      </div>
      <div className="tile-value">{value}</div>
      {note && <div className="tile-note">{note}</div>}
    </div>
  );
}
