// The driver's own pages (M61, designs "Tài xế · Tổng quan" and "Tài xế · Chi tiết chuyến"): the latest
// trip, the last 30 days, suggestions, every trip, one trip in detail. The backend gives a driver only
// their own reports and events; nothing here filters by driver.
import { useEffect, useState } from "react";
import { ArrowLeft, Bell, Clock, Coffee, Eye, Flag, Gauge, Route, ShieldCheck, Timer, Wind } from "lucide-react";
import { getTimeline, getTripReports } from "../lib/api";
import { formatPercent } from "../lib/format";
import { LEVELS, reasonText } from "../lib/labels";
import type { EventRecord, Session, TripReport } from "../lib/types";
import { formatDuration, suggestionText } from "../hud/tripModel";
import { driverMonth, newestFirst, tripFromHash, tripHref } from "./driverModel";
import { RatingCard, RatingChip, Tile, TripBars, dayText, hm, reviewedText, span } from "./TripParts";

function useReports(session: Session, refreshKey: number) {
  const [reports, setReports] = useState<TripReport[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getTripReports(session, "30d")
      .then((list) => {
        setReports(newestFirst(list));
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, refreshKey]);
  return { reports, error };
}

export function DriverOverview({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const { reports, error } = useReports(session, refreshKey);
  if (error) return <p className="error">{error}</p>;
  if (!reports) return <p className="muted">Đang tải…</p>;
  const latest = reports[0];
  const month = driverMonth(reports);
  return (
    <div className="stack">
      <p className="lead-note">
        <ShieldCheck aria-hidden size={18} /> Đây là các ca lái và lời khuyên của riêng bạn. Không ai thấy hình ảnh khuôn mặt của bạn.
      </p>
      {latest ? (
        <div className="grid-2">
          <RatingCard report={latest} title="Ca lái gần nhất">
            <TripBars summary={latest.summary} height={90} />
            <div className="row-between">
              <span className="muted small">{reviewedText(latest)}</span>
              <a className="ghost" href={tripHref("trips", latest)}>
                Xem chi tiết ca lái
              </a>
            </div>
          </RatingCard>
          <div className="stack">
            <section className="dg-card web-card">
              <h2>30 ngày qua</h2>
              <div className="tiles-2">
                <Tile icon={Route} value={String(month.trips)} label="Số ca lái" />
                <Tile icon={Clock} value={formatDuration(month.drivingS)} label="Giờ lái" />
                <Tile icon={Bell} value={String(month.reminders)} label="Lần được nhắc" />
                <Tile icon={Flag} value={String(month.falseAlarms)} label="Cảnh báo bạn báo nhầm" />
              </div>
            </section>
            {latest.summary.suggestions.length > 0 && (
              <section className="dg-card web-card">
                <h2>Gợi ý cho bạn</h2>
                <ul className="plain-list">
                  {latest.summary.suggestions.map((x) => (
                    <li key={x.code}>{suggestionText(x.code, x.minutes)}</li>
                  ))}
                </ul>
                <p className="muted small">Gợi ý dựa trên số liệu ca lái, không phải kết luận về sức khoẻ.</p>
              </section>
            )}
          </div>
        </div>
      ) : (
        <section className="dg-card web-card">
          <p className="muted">Chưa có ca lái nào trong 30 ngày qua. Bấm “Kết thúc ca lái” trên màn hình trong xe để gửi bản tổng kết.</p>
        </section>
      )}
      {reports.length > 0 && <TripTable reports={reports.slice(0, 8)} title="Các ca lái gần đây" more />}
    </div>
  );
}

function TripTable({ reports, title, more }: { reports: TripReport[]; title: string; more?: boolean }) {
  return (
    <section className="dg-card web-card">
      <div className="row-between">
        <h2>{title}</h2>
        {more && (
          <a className="small" href="#/dashboard/trips">
            Xem tất cả
          </a>
        )}
      </div>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Giờ</th>
              <th className="num">Thời gian lái</th>
              <th>Đánh giá</th>
              <th className="num">Lần nhắc</th>
              <th>Quản lý đã xem?</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={`${r.device_id}/${r.trip_id}`}>
                <td>{dayText(r.summary.started_at)}</td>
                <td className="dg-num">{span(r.summary)}</td>
                <td className="num">{formatDuration(r.summary.driving_s)}</td>
                <td>
                  <RatingChip rating={r.rating} />
                </td>
                <td className="num">{Object.values(r.summary.alerts_by_level).reduce((a, b) => a + (b ?? 0), 0)}</td>
                <td className="muted">{r.reviewed_at ? "Đã xem" : "Chưa xem"}</td>
                <td>
                  <a href={tripHref("trips", r)}>Xem</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** "Chuyến đi của tôi": the list, or one trip when the address names it. */
export function DriverTrips({ session, refreshKey, hash }: { session: Session; refreshKey: number; hash: string }) {
  const { reports, error } = useReports(session, refreshKey);
  const picked = tripFromHash(hash);
  if (error) return <p className="error">{error}</p>;
  if (!reports) return <p className="muted">Đang tải…</p>;
  const trip = picked && reports.find((r) => r.device_id === picked.deviceId && r.trip_id === picked.tripId);
  if (picked && trip) return <DriverTrip session={session} report={trip} />;
  if (picked) return <p className="muted">Không tìm thấy ca lái này trong 30 ngày qua.</p>;
  return reports.length ? (
    <TripTable reports={reports} title={`${reports.length} ca lái trong 30 ngày qua`} />
  ) : (
    <section className="dg-card web-card">
      <p className="muted">Chưa có ca lái nào trong 30 ngày qua.</p>
    </section>
  );
}

function DriverTrip({ session, report }: { session: Session; report: TripReport }) {
  const s = report.summary;
  const [alerts, setAlerts] = useState<EventRecord[] | null>(null);
  useEffect(() => {
    getTimeline(session, report.trip_id)
      .then((t) => setAlerts(t.events.filter((e) => e.type !== "system" && e.level > 0)))
      .catch(() => setAlerts([]));
  }, [session, report.trip_id]);

  return (
    <div className="stack">
      <a className="back-link" href="#/dashboard/trips">
        <ArrowLeft aria-hidden size={16} /> Ca lái của tôi
      </a>
      <RatingCard report={report} title="Đánh giá ca lái" />
      <section aria-label="Số liệu chính" className="tiles-3">
        <Tile icon={Clock} value={formatDuration(s.driving_s)} label="Thời gian lái" />
        <Tile icon={Timer} value={formatDuration(s.longest_drive_s)} label="Lái liên tục dài nhất" />
        <Tile icon={Coffee} value={String(s.rests)} label="Lần nghỉ" />
        <Tile icon={Gauge} value={s.avg_speed_kmh != null ? `${Math.round(s.avg_speed_kmh)} km/h` : "–"} label="Tốc độ trung bình" />
        <Tile icon={Wind} value={String(s.yawns)} label="Lần ngáp" />
        <Tile icon={Eye} value={formatPercent(s.monitored_frac)} label="Thời gian camera thấy rõ mặt" />
      </section>
      <div className="grid-2">
        <section className="dg-card web-card">
          <h2>Độ mệt theo thời gian</h2>
          <TripBars summary={s} />
        </section>
        <section className="dg-card web-card">
          <h2>Các lần được nhắc</h2>
          {alerts == null ? (
            <p className="muted">Đang tải…</p>
          ) : alerts.length === 0 ? (
            <p className="muted">Không có lần nhắc nào trong ca lái này.</p>
          ) : (
            <ul className="alert-list">
              {alerts.map((e) => (
                <li key={e.event_id}>
                  <span className="dg-num">{hm(e.ts)}</span>
                  <span>{e.reasons.map(reasonText).join(", ")}</span>
                  <span className={`badge level-${e.level}`}>{LEVELS[e.level].title}</span>
                  {e.feedback && <span className="muted small">bạn đã báo nhầm</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      {s.suggestions.length > 0 && (
        <section className="dg-card web-card">
          <h2>Gợi ý cho lần sau</h2>
          <ul className="plain-list">
            {s.suggestions.map((x) => (
              <li key={x.code}>{suggestionText(x.code, x.minutes)}</li>
            ))}
          </ul>
          <p className="muted small">
            Gợi ý dựa trên số liệu ca lái, không phải kết luận về sức khoẻ. Đã gửi cho quản lý đội xe lúc {hm(report.received_at)} · {reviewedText(report)}.
          </p>
        </section>
      )}
    </div>
  );
}
