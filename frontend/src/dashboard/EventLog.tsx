import { formatDateTime, formatNumber } from "../lib/format";
import { EVENT_TAGS, LEVELS, eventReasonText } from "../lib/labels";
import type { EventRecord } from "../lib/types";

export function LevelBadge({ level }: { level: 0 | 1 | 2 | 3 }) {
  return (
    <span className={`badge level-${level}`}>
      <span aria-hidden>{LEVELS[level].icon}</span> {LEVELS[level].short}
    </span>
  );
}

export default function EventLog({
  events,
  loading,
  onPickTrip,
}: {
  events: EventRecord[];
  loading: boolean;
  onPickTrip: (tripId: string) => void;
}) {
  if (!loading && events.length === 0) {
    return <p className="empty">Không có cảnh báo nào khớp bộ lọc.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Thời gian</th>
            <th scope="col">Mức</th>
            <th scope="col">Lý do</th>
            <th scope="col">Tài xế</th>
            <th scope="col">Thiết bị</th>
            <th scope="col">Chuyến</th>
            <th scope="col" className="num">
              Buồn ngủ
            </th>
            <th scope="col" className="num">
              Mất tập trung
            </th>
            <th scope="col" className="num">
              km/h
            </th>
            <th scope="col">Phản hồi</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.event_id}>
              <td className="nowrap">{formatDateTime(e.ts)}</td>
              <td>
                <LevelBadge level={e.level} />
              </td>
              <td>
                {e.reasons.map((r) => eventReasonText(r, e.metrics)).join(", ")}
                {(e.tags ?? []).map((t) => (
                  <span key={t} className="tag" title={EVENT_TAGS[t].hint} style={{ marginLeft: 6 }}>
                    {EVENT_TAGS[t].title}
                  </span>
                ))}
              </td>
              <td>{e.driver_id ?? "–"}</td>
              <td>{e.device_id}</td>
              <td>
                <button type="button" className="link" onClick={() => onPickTrip(e.trip_id)} title="Xem timeline chuyến này">
                  {e.trip_id}
                </button>
              </td>
              <td className="num">{formatNumber(e.drowsy_score)}</td>
              <td className="num">{formatNumber(e.distraction_score)}</td>
              <td className="num">{formatNumber(e.speed_kmh)}</td>
              <td>{e.feedback === "false_alarm" ? <span className="tag">Tài xế báo sai</span> : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
