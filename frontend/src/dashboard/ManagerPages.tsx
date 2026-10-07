// The fleet manager's pages (M62, designs "Quản lý · Tổng quan đội xe" and "Quản lý · Duyệt báo cáo chuyến").
// Overview: today's numbers, what needs a manager now (M44: L3 / no reaction / no answer, a vehicle that
// went quiet, unread reports), every vehicle. Live like the fleet page (every 5 s, a sound per new
// urgent event). Review: the reports list and one report, "Đánh dấu đã xem" tells the driver it arrived.
import { useEffect, useMemo, useRef, useState } from "react";
import { BellRing, Bell, CircleAlert, Clock, Coffee, Eye, Flag, Gauge, Smartphone, Timer, WifiOff, FileText } from "lucide-react";
import { alertSound, play } from "../hud/chime";
import { formatDuration, suggestionText } from "../hud/tripModel";
import { getFleet, getTripReports, reviewTripReport } from "../lib/api";
import { ago, dayKey, formatNumber, formatPercent, type RangeKey } from "../lib/format";
import { FLEET_STATUS, fleetStateText, reasonText } from "../lib/labels";
import type { FleetDevice, Session, TripReport } from "../lib/types";
import { newestFirst } from "./driverModel";
import { fleetCounts, newUrgentIds, sortFleet, urgentDevices } from "./FleetView";
import { RatingCard, RatingChip, Tile, TripBars, dayText, span } from "./TripParts";

const REFRESH_MS = 5_000; // as the fleet page: an unresponsive driver must be seen within seconds

export function ManagerOverview({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const [devices, setDevices] = useState<FleetDevice[] | null>(null);
  const [unread, setUnread] = useState<TripReport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"" | "online" | "offline">("");
  const [search, setSearch] = useState("");
  const [now, setNow] = useState(Date.now);
  const rung = useRef(new Set<string>());

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      Promise.all([getFleet(session, dayKey()), getTripReports(session, "7d", true)])
        .then(([list, reports]) => {
          if (cancelled) return;
          setDevices(list);
          setUnread(reports);
          const fresh = newUrgentIds(list, rung.current);
          fresh.forEach((id) => rung.current.add(id));
          if (fresh.length) play(alertSound(3, [])); // silent if the browser still blocks sound
          setNow(Date.now());
          setError(null);
        })
        .catch((e: Error) => !cancelled && setError(e.message));
    void load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, refreshKey]);

  const all = devices ?? [];
  const counts = fleetCounts(all);
  const byLevel = all.reduce(
    (acc, d) => {
      for (const lv of ["1", "2", "3"] as const) acc[lv] += d.alerts_by_level[lv] ?? 0;
      return acc;
    },
    { "1": 0, "2": 0, "3": 0 },
  );
  const urgent = urgentDevices(all);
  const offline = all.filter((d) => d.status === "offline" && !d.urgent);
  const rows = sortFleet(all).filter(
    (d) => (!status || d.status === status) && (!search || `${d.device_id} ${d.driver_id ?? ""}`.toLowerCase().includes(search.toLowerCase())),
  );
  const seen = (iso: string | null) => (iso ? ago((now - Date.parse(iso)) / 1000) : "–");

  if (error) return <p className="error">{error}</p>;
  if (!devices) return <p className="muted">Đang tải…</p>;

  return (
    <div className="stack">
      <section aria-label="Số liệu hôm nay" className="tiles-4">
        <Tile icon={Gauge} value={`${counts.online} / ${counts.total}`} label="Xe đang hoạt động" accent="var(--good)" />
        <Tile icon={WifiOff} value={String(counts.offline)} label="Mất liên lạc" accent={counts.offline ? "#f87171" : undefined} />
        <Tile
          icon={Bell}
          value={String(byLevel["1"] + byLevel["2"] + byLevel["3"])}
          label={`Cảnh báo hôm nay · L1 ${byLevel["1"]} · L2 ${byLevel["2"]} · L3 ${byLevel["3"]}`}
        />
        <Tile icon={FileText} value={String(unread.length)} label="Báo cáo chuyến chưa xem" accent={unread.length ? "var(--series-1)" : undefined} />
      </section>

      <section className="dg-card web-card" aria-live="polite">
        <h2>Cần xử lý</h2>
        {urgent.length + offline.length + (unread.length ? 1 : 0) === 0 ? (
          <p className="muted">Không có việc cần xử lý lúc này.</p>
        ) : (
          <ul className="todo-list">
            {urgent.map((d) => (
              <li key={`u-${d.device_id}`} className="todo danger">
                <BellRing aria-hidden size={22} />
                <span>
                  <b>{d.urgent!.level === 3 ? "L3 Nguy hiểm" : "Cần chú ý ngay"}</b>
                  <span className="muted">
                    {d.device_id} · {d.driver_id ?? "chưa gắn tài xế"} · {d.urgent!.reasons.map(reasonText).join(", ")} · {seen(d.urgent!.ts)}
                  </span>
                </span>
                <a className="ghost" href="#/dashboard/fleet">
                  Xem xe
                </a>
              </li>
            ))}
            {offline.map((d) => (
              <li key={`o-${d.device_id}`} className="todo caution">
                <WifiOff aria-hidden size={22} />
                <span>
                  <b>Mất liên lạc</b>
                  <span className="muted">
                    {d.device_id} · {d.driver_id ?? "chưa gắn tài xế"} · không có tín hiệu {seen(d.last_seen)}, chưa kết thúc chuyến
                  </span>
                </span>
                <a className="ghost" href="#/dashboard/fleet">
                  Xem xe
                </a>
              </li>
            ))}
            {unread.length > 0 && (
              <li className="todo info">
                <FileText aria-hidden size={22} />
                <span>
                  <b>Báo cáo mới</b>
                  <span className="muted">
                    {unread.length} báo cáo chuyến chưa ai xem
                    {unread.some((r) => r.rating === "risk") ? `, ${unread.filter((r) => r.rating === "risk").length} chuyến "Có lúc rất nguy hiểm"` : ""}
                  </span>
                </span>
                <a className="ghost" href="#/dashboard/reports">
                  Mở báo cáo
                </a>
              </li>
            )}
          </ul>
        )}
      </section>

      <section className="dg-card web-card">
        <div className="row-between">
          <h2>Từng xe</h2>
          <div className="filters">
            <label className="field-inline">
              Trạng thái
              <select value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
                <option value="">Tất cả</option>
                <option value="online">Đang hoạt động</option>
                <option value="offline">Mất liên lạc</option>
              </select>
            </label>
            <label className="field-inline">
              Tìm
              <input type="search" value={search} placeholder="Xe hoặc tài xế" onChange={(e) => setSearch(e.target.value)} />
            </label>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Xe</th>
                <th>Tài xế</th>
                <th>Liên lạc</th>
                <th>Giám sát</th>
                <th className="num">Cảnh báo hôm nay</th>
                <th>Sự kiện gần nhất</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.device_id} className={d.urgent ? "row-urgent" : undefined}>
                  <td>
                    <b>{d.device_id}</b>
                  </td>
                  <td>{d.driver_id ?? "–"}</td>
                  <td>
                    <span className="dot-text">
                      <i style={{ background: d.status === "online" ? "var(--good)" : d.status === "offline" ? "#f87171" : "rgba(255,255,255,0.3)" }} />
                      {FLEET_STATUS[d.status].title}
                      {d.status === "offline" ? ` ${seen(d.last_seen)}` : ""}
                    </span>
                  </td>
                  <td>{fleetStateText(d)}</td>
                  <td className="num dg-num">
                    {(["1", "2", "3"] as const)
                      .filter((lv) => d.alerts_by_level[lv])
                      .map((lv) => `L${lv} ${d.alerts_by_level[lv]}`)
                      .join(" · ") || "0"}
                  </td>
                  <td>{d.last_event ? `${seen(d.last_event.ts)} · ${d.last_event.reasons.map(reasonText).join(", ")}` : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

const key = (r: Pick<TripReport, "device_id" | "trip_id">) => `${r.device_id}/${r.trip_id}`;

export function ReportReview({
  session,
  range,
  refreshKey,
  onUnreviewed,
  onPickTrip,
}: {
  session: Session;
  range: RangeKey;
  refreshKey: number;
  onUnreviewed: (n: number) => void;
  onPickTrip: (tripId: string) => void;
}) {
  const [reports, setReports] = useState<TripReport[] | null>(null);
  const [onlyNew, setOnlyNew] = useState(true);
  const [picked, setPicked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTripReports(session, range)
      .then((list) => {
        setReports(newestFirst(list));
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, range, refreshKey]);

  useEffect(() => {
    if (reports) onUnreviewed(reports.filter((r) => !r.reviewed_at).length);
  }, [reports, onUnreviewed]);

  const unread = useMemo(() => (reports ?? []).filter((r) => !r.reviewed_at), [reports]);
  const shown = onlyNew ? unread : (reports ?? []);
  const current = (reports ?? []).find((r) => key(r) === picked) ?? shown[0] ?? null;

  async function markReviewed(r: TripReport) {
    try {
      const updated = await reviewTripReport(session, r);
      setReports((list) => (list ?? []).map((x) => (key(x) === key(updated) ? updated : x)));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!reports) return <p className="muted">Đang tải…</p>;
  const s = current?.summary;

  return (
    <div className="review">
      <section className="dg-card web-card review-list" aria-label="Danh sách báo cáo">
        <div className="seg" role="group" aria-label="Lọc báo cáo">
          <button type="button" aria-pressed={onlyNew} onClick={() => setOnlyNew(true)}>
            Chưa xem ({unread.length})
          </button>
          <button type="button" aria-pressed={!onlyNew} onClick={() => setOnlyNew(false)}>
            Tất cả
          </button>
        </div>
        {shown.length === 0 && <p className="muted">{onlyNew ? "Đã xem hết báo cáo." : "Chưa có báo cáo nào."}</p>}
        <ul className="review-items">
          {shown.map((r) => (
            <li key={key(r)}>
              <button type="button" aria-current={current && key(current) === key(r) ? "true" : undefined} onClick={() => setPicked(key(r))}>
                <span className="row-between">
                  <b>
                    {r.driver_id ?? "–"} · {r.device_id}
                  </b>
                  <RatingChip rating={r.rating} />
                </span>
                <span className="muted small">
                  {dayText(r.summary.started_at)} · {span(r.summary)} · {r.reviewed_at ? `${r.reviewed_by} đã xem` : "Chưa xem"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {current && s ? (
        <div className="stack">
          <RatingCard report={current} title={`Tài xế ${current.driver_id ?? "–"}`} />
          <section aria-label="Số liệu" className="tiles-3">
            <Tile icon={Clock} value={formatDuration(s.driving_s)} label="Thời gian lái" />
            <Tile icon={Timer} value={formatDuration(s.longest_drive_s)} label="Lái liên tục dài nhất" />
            <Tile icon={Bell} value={`${s.alerts_by_level["1"]} / ${s.alerts_by_level["2"]} / ${s.alerts_by_level["3"]}`} label="Cảnh báo L1 / L2 / L3" />
            <Tile icon={CircleAlert} value={`${formatNumber(s.longest_closure_s, 1)} giây`} label="Nhắm mắt lâu nhất" />
            <Tile icon={Coffee} value={`${s.yawns} / ${s.nods}`} label="Ngáp / gục đầu" />
            <Tile icon={Smartphone} value={`${formatNumber(s.off_road_s)} giây / ${formatNumber(s.phone_s)} giây`} label="Nhìn lệch / điện thoại" />
            <Tile icon={Eye} value={formatPercent(s.monitored_frac)} label="Được giám sát" />
            <Tile icon={Flag} value={String(s.false_alarms)} label="Tài xế báo sai" />
          </section>
          <section className="dg-card web-card">
            <div className="row-between">
              <h2>Độ mệt theo thời gian</h2>
              <button type="button" className="link" onClick={() => onPickTrip(current.trip_id)}>
                Xem timeline từng phút
              </button>
            </div>
            <TripBars summary={s} />
          </section>
          {s.suggestions.length > 0 && (
            <section className="dg-card web-card">
              <h2>Gợi ý đã đưa cho tài xế</h2>
              <ul className="plain-list">
                {s.suggestions.map((x) => (
                  <li key={x.code}>{suggestionText(x.code, x.minutes)}</li>
                ))}
              </ul>
            </section>
          )}
          <div className="row-between">
            {current.reviewed_at ? (
              <span className="muted">
                {current.reviewed_by} đã xem lúc {new Date(current.reviewed_at).toLocaleString("vi-VN")}
              </span>
            ) : (
              <button type="button" className="primary big" onClick={() => void markReviewed(current)}>
                Đánh dấu đã xem
              </button>
            )}
            <span className="muted small">Cảnh báo có thể sai: không dùng một cảnh báo đơn lẻ để kỷ luật tài xế.</span>
          </div>
        </div>
      ) : (
        <section className="dg-card web-card">
          <p className="muted">Chọn một báo cáo ở bên trái.</p>
        </section>
      )}
    </div>
  );
}
