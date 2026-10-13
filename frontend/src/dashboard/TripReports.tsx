// "Báo cáo chuyến đi": end-of-trip summaries sent by the devices / browsers when a driver presses
// "Kết thúc chuyến". The higher roles (manager, engineer, admin) get every driver's, see which ones
// nobody has read yet and mark them read; a driver sees their own (and whether someone read them).
// Engineer version: every number, the per-minute drowsy_score chart with the trip's alerts.
import { useEffect, useMemo, useState } from "react";
import { getTimeline, getTripReports, reviewTripReport } from "../lib/api";
import { formatDateTime, formatNumber, formatPercent, type RangeKey } from "../lib/format";
import { reasonText, unavailableCausesText } from "../lib/labels";
import type { EventRecord, SampleRecord, Session, TripRating, TripReport } from "../lib/types";
import { RATING_REASON_TEXT, RATING_TEXT, formatDuration, glanceText, phoneKindText, suggestionText } from "../hud/tripModel";
import FatigueChart from "./FatigueChart";

const RATING_BADGE: Record<TripRating, string> = { good: "level-0", attention: "level-2", risk: "level-3" };

export function RatingBadge({ rating }: { rating: TripRating }) {
  return <span className={`badge ${RATING_BADGE[rating]}`}>{RATING_TEXT[rating].title}</span>;
}

const key = (r: Pick<TripReport, "device_id" | "trip_id">) => `${r.device_id}/${r.trip_id}`;

interface Props {
  session: Session;
  range: RangeKey;
  refreshKey: number;
  onUnreviewed: (n: number) => void;
}

export default function TripReports({ session, range, refreshKey, onUnreviewed }: Props) {
  const [reports, setReports] = useState<TripReport[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  const [onlyNew, setOnlyNew] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reviewer = session.role !== "driver";

  useEffect(() => {
    getTripReports(session, range)
      .then((list) => {
        setReports(list);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, range, refreshKey]);

  useEffect(() => {
    if (reviewer) onUnreviewed(reports.filter((r) => !r.reviewed_at).length);
  }, [reports, reviewer, onUnreviewed]);

  const shown = onlyNew ? reports.filter((r) => !r.reviewed_at) : reports;
  const current = reports.find((r) => key(r) === picked) ?? null;

  async function markReviewed(r: TripReport) {
    try {
      const updated = await reviewTripReport(session, r);
      setReports((list) => list.map((x) => (key(x) === key(updated) ? updated : x)));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <section className="card">
        <div className="card-head">
          <h2>Báo cáo ca lái</h2>
          {reviewer && (
            <label className="field-inline check">
              <input type="checkbox" checked={onlyNew} onChange={(e) => setOnlyNew(e.target.checked)} />
              Chỉ báo cáo chưa xem
            </label>
          )}
        </div>
        <p className="muted small">
          Tài xế bấm “Kết thúc ca lái” trên HUD thì bản tổng kết được gửi về đây. Đánh giá mô tả ca lái, không
          chấm điểm tài xế: cảnh báo có thể sai và tài xế có thể đã bấm “báo sai”.
        </p>
        {error && <p className="error">{error}</p>}
        {shown.length === 0 ? (
          <p className="empty">{onlyNew ? "Không còn báo cáo chưa xem." : "Chưa có báo cáo ca lái nào trong khoảng thời gian này."}</p>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Bắt đầu</th>
                  <th scope="col">Tài xế</th>
                  <th scope="col">Đánh giá</th>
                  <th scope="col" className="num">
                    Thời gian lái
                  </th>
                  <th scope="col" className="num">
                    L1 / L2 / L3
                  </th>
                  <th scope="col" className="num">
                    Giám sát được
                  </th>
                  <th scope="col">Đã xem</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => {
                  const s = r.summary;
                  const a = s.alerts_by_level;
                  return (
                    <tr key={key(r)} aria-selected={key(r) === picked}>
                      <td className="nowrap">
                        <button type="button" className="link" onClick={() => setPicked(key(r))}>
                          {formatDateTime(s.started_at)}
                        </button>
                      </td>
                      <td>{r.driver_id ?? r.device_id}</td>
                      <td>
                        <RatingBadge rating={r.rating} />
                      </td>
                      <td className="num">{formatDuration(s.driving_s)}</td>
                      <td className="num">
                        {a["1"]} / {a["2"]} / {a["3"]}
                      </td>
                      <td className="num">{formatPercent(s.monitored_frac, 0)}</td>
                      <td>{r.reviewed_at ? <span className="tag">{r.reviewed_by}</span> : <strong>Chưa</strong>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {current && <ReportDetail session={session} report={current} reviewer={reviewer} onReviewed={markReviewed} />}
    </>
  );
}

function ReportDetail({
  session,
  report,
  reviewer,
  onReviewed,
}: {
  session: Session;
  report: TripReport;
  reviewer: boolean;
  onReviewed: (r: TripReport) => void;
}) {
  const s = report.summary;
  const [events, setEvents] = useState<EventRecord[]>([]);
  useEffect(() => {
    getTimeline(session, s.trip_id)
      .then((tl) => setEvents(tl.events.filter((e) => e.device_id === report.device_id)))
      .catch(() => setEvents([]));
  }, [session, s.trip_id, report.device_id]);

  // The summary's minutes as timeline samples (the chart is shared with "Timeline mệt mỏi").
  const samples: SampleRecord[] = useMemo(() => {
    const t0 = Date.parse(s.started_at);
    return s.minutes.map((m) => ({
      ts: new Date(t0 + (m.minute + 1) * 60_000).toISOString(),
      trip_id: s.trip_id,
      device_id: report.device_id,
      driver_id: report.driver_id,
      drowsy_score: m.drowsy_score,
      perclos_60s: null,
      max_level: m.max_level,
    }));
  }, [s, report.device_id, report.driver_id]);

  const rows: [string, string][] = [
    ["Thời gian", `${formatDateTime(s.started_at)} → ${formatDateTime(s.ended_at)} (${formatDuration(s.duration_s)})`],
    ["Lái / dừng", `${formatDuration(s.driving_s)} / ${formatDuration(s.stopped_s)}, nghỉ ${s.rests} lần`],
    ["Đoạn lái liên tục dài nhất", formatDuration(s.longest_drive_s)],
    ["Tốc độ trung bình", `${formatNumber(s.avg_speed_kmh, 0)} km/h (${s.speed_source === "simulated" ? "giả lập" : "CAN"})`],
    ["Cảnh báo L1 / L2 / L3", `${s.alerts_by_level["1"]} / ${s.alerts_by_level["2"]} / ${s.alerts_by_level["3"]}`],
    [
      "Theo lý do",
      Object.entries(s.alerts_by_reason)
        .map(([r, n]) => `${reasonText(r)} ${n}`)
        .join(", ") || "–",
    ],
    ["Tài xế bấm báo sai", String(s.false_alarms)],
    ["drowsy_score trung bình / p90 / cao nhất", `${s.drowsy_mean} / ${s.drowsy_p90} / ${s.drowsy_max} (L1 ${s.score_l1}, L2 ${s.score_l2})`],
    ["Mệt lần đầu", s.first_tired_min == null ? "–" : `phút lái thứ ${s.first_tired_min}`],
    ["Microsleep / nhắm lâu nhất", `${s.microsleeps} / ${formatNumber(s.longest_closure_s, 1)} s`],
    ["Ngáp / gục đầu / nhướn mày", `${s.yawns} / ${s.nods} / ${s.brow_raises}`],
    ["Nhìn khỏi đường / cầm điện thoại", `${formatNumber(s.off_road_s, 0)} s / ${formatNumber(s.phone_s, 0)} s`],
    ["Điện thoại: gọi / nhắn tin", phoneKindText(s)],
    ["Liếc khỏi đường", glanceText(s)],
    [
      "Giám sát được",
      `${formatPercent(s.monitored_frac, 0)} thời gian lái; tạm ngưng ${formatNumber(s.unavailable_s, 0)} s${unavailableCausesText(s.unavailable_by_cause) ? ` (${unavailableCausesText(s.unavailable_by_cause)})` : ""}, mất camera ${formatNumber(s.camera_lost_s, 0)} s` +
        (s.turned_away_s ? `, quay hẳn đi rồi mất mặt ${formatNumber(s.turned_away_s, 0)} s` : "") +
        (s.vehicle_signal_lost_s ? `, mất tín hiệu xe ${formatNumber(s.vehicle_signal_lost_s, 0)} s` : ""),
    ],
    ["Đăng ký tài xế", s.enrolled ? "Có" : "Không (mốc tự học)"],
    ["Đổi tài xế", `${s.driver_changes ?? 0} lần`],
    ["Thiết bị / ca lái", `${report.device_id} / ${s.trip_id}`],
  ];

  return (
    <section className="card">
      <div className="card-head">
        <h2>
          {report.driver_id ?? report.device_id} · {formatDateTime(s.started_at)}
        </h2>
        <RatingBadge rating={report.rating} />
        {reviewer &&
          (report.reviewed_at ? (
            <span className="muted small">
              Đã xem bởi {report.reviewed_by}, {formatDateTime(report.reviewed_at)}
            </span>
          ) : (
            <button
              type="button"
              className="primary"
              onClick={() => onReviewed(report)}
              disabled={session.readOnly}
              title={session.readOnly ? "Tài khoản dùng thử chỉ được xem" : undefined}
            >
              Đánh dấu đã xem
            </button>
          ))}
      </div>
      {s.rating_reasons.length > 0 && (
        <p>
          <strong>Lý do đánh giá:</strong> {s.rating_reasons.map((r) => RATING_REASON_TEXT[r]).join("; ")}
        </p>
      )}
      <FatigueChart samples={samples} events={events} l1={s.score_l1} l2={s.score_l2} />
      <div className="table-wrap">
        <table className="data">
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}>
                <th scope="row">{k}</th>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {s.suggestions.length > 0 && (
        <>
          <h3>Gợi ý đã đưa cho tài xế</h3>
          <ul>
            {s.suggestions.map((x) => (
              <li key={x.code}>{suggestionText(x.code, x.minutes)}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
