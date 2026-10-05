// "Đội xe" (M33): which vehicles are running, which went quiet. Every device sends a heartbeat
// (edge_agent/runtime.py); the backend calls it offline when none came for a while. A trip that was
// ended is not a lost vehicle. Alerts and the latest event are those of the picked day.
import { useEffect, useState } from "react";
import { getFleet } from "../lib/api";
import { ago, dayKey, formatDateTime, formatNumber } from "../lib/format";
import { FLEET_STATUS, fleetStateText, reasonText } from "../lib/labels";
import type { FleetDevice, FleetStatus, Session } from "../lib/types";
import { LevelBadge } from "./EventLog";

const REFRESH_MS = 15_000;
const STATUS_ORDER: FleetStatus[] = ["offline", "online", "ended", "never"]; // lost vehicles first

export function sortFleet(devices: FleetDevice[]): FleetDevice[] {
  const rank = (d: FleetDevice) => STATUS_ORDER.indexOf(d.status);
  return [...devices].sort((a, b) => rank(a) - rank(b) || a.device_id.localeCompare(b.device_id));
}

export function fleetCounts(devices: FleetDevice[]) {
  const count = (s: FleetStatus) => devices.filter((d) => d.status === s).length;
  const alerts = devices.reduce((n, d) => n + Object.values(d.alerts_by_level).reduce((a, b) => a + b, 0), 0);
  return { total: devices.length, online: count("online"), offline: count("offline"), alerts };
}

export default function FleetView({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const [devices, setDevices] = useState<FleetDevice[] | null>(null);
  const [day, setDay] = useState(dayKey);
  const [status, setStatus] = useState<FleetStatus | "">("");
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      getFleet(session, day)
        .then((list) => {
          if (cancelled) return;
          setDevices(list);
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
  }, [session, day, refreshKey]);

  const all = devices ?? [];
  const counts = fleetCounts(all);
  const shown = sortFleet(status ? all.filter((d) => d.status === status) : all);
  const today = day === dayKey(now);

  return (
    <>
      <section className="tiles" aria-label="Tổng quan đội xe">
        <Tile label="Tổng số xe" value={devices ? counts.total : null} />
        <Tile label={FLEET_STATUS.online.title} value={devices ? counts.online : null} />
        <Tile label={FLEET_STATUS.offline.title} value={devices ? counts.offline : null} />
        <Tile label={today ? "Cảnh báo hôm nay" : "Cảnh báo trong ngày"} value={devices ? counts.alerts : null} />
      </section>
      <section className="card">
        <div className="card-head">
          <h2>Đội xe</h2>
          <label className="field-inline">
            Trạng thái
            <select value={status} onChange={(e) => setStatus(e.target.value as FleetStatus | "")}>
              <option value="">Tất cả</option>
              {STATUS_ORDER.map((s) => (
                <option key={s} value={s}>
                  {FLEET_STATUS[s].title}
                </option>
              ))}
            </select>
          </label>
          <label className="field-inline">
            Ngày
            <input type="date" value={day} max={dayKey(now)} onChange={(e) => e.target.value && setDay(e.target.value)} />
          </label>
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {devices && shown.length === 0 ? (
          <p className="empty">{all.length ? "Không có xe nào khớp bộ lọc." : "Chưa có thiết bị nào."}</p>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Thiết bị</th>
                  <th scope="col">Tài xế</th>
                  <th scope="col">Liên lạc</th>
                  <th scope="col">Lần cuối thấy</th>
                  <th scope="col">Giám sát</th>
                  <th scope="col">Chuyến</th>
                  <th scope="col">{today ? "Cảnh báo hôm nay" : "Cảnh báo trong ngày"}</th>
                  <th scope="col">Sự kiện gần nhất</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((d) => (
                  <tr key={d.device_id}>
                    <td>{d.device_id}</td>
                    <td>{d.driver_id ?? "–"}</td>
                    <td>
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="nowrap" title={d.last_seen ? formatDateTime(d.last_seen) : undefined}>
                      {d.last_seen ? ago((now - Date.parse(d.last_seen)) / 1000) : "–"}
                    </td>
                    <td>{fleetStateText(d)}</td>
                    <td>{d.trip_id ?? "–"}</td>
                    <td className="nowrap">
                      <AlertCounts byLevel={d.alerts_by_level} />
                    </td>
                    <td>
                      {d.last_event ? (
                        <>
                          <span className="muted nowrap">{formatDateTime(d.last_event.ts)}</span>{" "}
                          {d.last_event.type !== "system" && <LevelBadge level={d.last_event.level} />}{" "}
                          {d.last_event.reasons.map(reasonText).join(", ")}
                        </>
                      ) : (
                        "–"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function StatusBadge({ status }: { status: FleetStatus }) {
  const { title, badge } = FLEET_STATUS[status];
  return <span className={badge ? `badge ${badge}` : "tag"}>{title}</span>;
}

function AlertCounts({ byLevel }: { byLevel: Record<string, number> }) {
  const levels = ([1, 2, 3] as const).filter((lv) => byLevel[lv]);
  if (!levels.length) return <span className="muted">0</span>;
  return (
    <>
      {levels.map((lv) => (
        <span key={lv} className={`badge level-${lv}`} style={{ marginRight: 4 }}>
          L{lv} × {byLevel[lv]}
        </span>
      ))}
    </>
  );
}

function Tile({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{formatNumber(value)}</div>
    </div>
  );
}
