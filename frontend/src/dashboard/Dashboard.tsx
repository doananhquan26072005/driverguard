import { useCallback, useEffect, useState } from "react";
import { type EventFilters, getEvents, getPolicy, getStats, getThresholds, getTripReports, loadSession, saveSession } from "../lib/api";
import { RANGES, type RangeKey } from "../lib/format";
import { LEVELS, policyNote, ROLES } from "../lib/labels";
import type { EventRecord, Session, Stats, Thresholds } from "../lib/types";
import AuditView from "./AuditView";
import { DeletionRequestsCard, MyDataCard } from "./MyDataCard";
import EventLog from "./EventLog";
import FleetView from "./FleetView";
import Login from "./Login";
import StatsTiles from "./StatsTiles";
import ThresholdsView from "./ThresholdsView";
import TimelineView from "./TimelineView";
import TripReports from "./TripReports";

type Tab = "events" | "fleet" | "timeline" | "reports" | "thresholds" | "audit";
const REFRESH_MS = 15_000;
const DEFAULT_L1 = 40; // config/thresholds.yaml risk.drowsy.l1 / l2
const DEFAULT_L2 = 70;

export default function Dashboard() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [tab, setTab] = useState<Tab>("events");
  const [filters, setFilters] = useState<EventFilters>({ range: "7d", minLevel: 0, driverId: "", falseAlarmOnly: false });
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [tripId, setTripId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [unreviewed, setUnreviewed] = useState(0); // trip reports no higher role has read yet
  const [policy, setPolicy] = useState<string | null>(null); // data policy line under every tab

  const logout = useCallback(() => {
    saveSession(null);
    setSession(null);
  }, []);

  function onLogin(s: Session) {
    saveSession(s);
    setSession(s);
  }

  const canReadThresholds = session != null && session.role !== "driver";

  // Events + stats for the current filters, refreshed periodically.
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const [ev, st] = await Promise.all([getEvents(session, filters), getStats(session, filters.range, filters.driverId)]);
        if (cancelled) return;
        setEvents(ev);
        setStats(st);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        const err = e as Error & { status?: number };
        if (err.status === 401) logout();
        else setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, filters, refreshKey, logout]);

  useEffect(() => {
    if (session) getPolicy().then((p) => setPolicy(policyNote(p))).catch(() => undefined);
  }, [session]);

  useEffect(() => {
    if (session && canReadThresholds) getThresholds(session).then(setThresholds).catch(() => undefined);
  }, [session, canReadThresholds]);

  // Trip reports no higher role has read yet: counted on the tab from the start, refreshed with the rest.
  useEffect(() => {
    if (!session || session.role === "driver") return;
    let cancelled = false;
    const load = () =>
      getTripReports(session, filters.range, true)
        .then((list) => !cancelled && setUnreviewed(list.length))
        .catch(() => undefined);
    void load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, filters.range, refreshKey]);

  if (!session) return <Login onLogin={onLogin} />;

  const tabs: { key: Tab; label: string }[] = [
    { key: "events", label: "Nhật ký sự kiện" },
    ...(canReadThresholds ? [{ key: "fleet" as Tab, label: "Đội xe" }] : []),
    { key: "timeline", label: "Timeline mệt mỏi" },
    { key: "reports", label: unreviewed ? `Báo cáo chuyến đi (${unreviewed} mới)` : "Báo cáo chuyến đi" },
    ...(canReadThresholds ? [{ key: "thresholds" as Tab, label: "Ngưỡng" }] : []),
    ...(session.role === "admin" ? [{ key: "audit" as Tab, label: "Nhật ký truy cập" }] : []),
    ...(session.role === "driver" ? [{ key: "audit" as Tab, label: "Dữ liệu của tôi" }] : []),
  ];
  const drivers = [...new Set(events.map((e) => e.driver_id).filter(Boolean))] as string[];

  return (
    <div className="dash">
      <header className="dash-bar">
        <span className="dash-brand">DriverGuard</span>
        <nav className="tabs" role="tablist">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              className={tab === t.key ? "tab active" : "tab"}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <span className="dash-user">
          {session.username} · {ROLES[session.role]}
          {session.driverId ? ` · ${session.driverId}` : ""}
        </span>
        <a className="ghost small" href="#/hud">
          HUD
        </a>
        <button type="button" className="ghost small" onClick={logout}>
          Đăng xuất
        </button>
      </header>

      <main className="dash-main">
        <div className="filters" role="group" aria-label="Bộ lọc">
          {tab !== "fleet" && (
            <label className="field-inline">
              Thời gian
              <select value={filters.range} onChange={(e) => setFilters({ ...filters, range: e.target.value as RangeKey })}>
                {RANGES.map((r) => (
                  <option key={r.key} value={r.key}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {tab === "events" && (
            <>
              <label className="field-inline">
                Mức từ
                <select value={filters.minLevel} onChange={(e) => setFilters({ ...filters, minLevel: Number(e.target.value) })}>
                  {([0, 1, 2, 3] as const).map((lv) => (
                    <option key={lv} value={lv}>
                      {lv === 0 ? "Tất cả" : `${LEVELS[lv].short} ${LEVELS[lv].title}`}
                    </option>
                  ))}
                </select>
              </label>
              {session.role !== "driver" && (
                <label className="field-inline">
                  Tài xế
                  <input
                    list="drivers"
                    value={filters.driverId}
                    placeholder="Tất cả"
                    onChange={(e) => setFilters({ ...filters, driverId: e.target.value.trim() })}
                  />
                  <datalist id="drivers">
                    {drivers.map((d) => (
                      <option key={d} value={d} />
                    ))}
                  </datalist>
                </label>
              )}
              <label className="field-inline check">
                <input
                  type="checkbox"
                  checked={filters.falseAlarmOnly}
                  onChange={(e) => setFilters({ ...filters, falseAlarmOnly: e.target.checked })}
                />
                Chỉ cảnh báo tài xế báo sai
              </label>
            </>
          )}
          <button type="button" className="ghost" onClick={() => setRefreshKey((k) => k + 1)}>
            Làm mới
          </button>
          {loading && <span className="muted small">Đang tải…</span>}
        </div>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {tab !== "fleet" && tab !== "audit" && <StatsTiles stats={stats} />}
        {tab === "fleet" && canReadThresholds && <FleetView session={session} refreshKey={refreshKey} />}

        {tab === "events" && (
          <section className="card">
            <h2>Nhật ký sự kiện</h2>
            <EventLog
              events={events}
              loading={loading}
              onPickTrip={(id) => {
                setTripId(id);
                setTab("timeline");
              }}
            />
          </section>
        )}
        {tab === "timeline" && (
          <TimelineView
            session={session}
            range={filters.range}
            tripId={tripId}
            onTripChange={setTripId}
            l1={thresholds?.values["risk.drowsy.l1"] ?? DEFAULT_L1}
            l2={thresholds?.values["risk.drowsy.l2"] ?? DEFAULT_L2}
            refreshKey={refreshKey}
          />
        )}
        {tab === "reports" && (
          <TripReports session={session} range={filters.range} refreshKey={refreshKey} onUnreviewed={setUnreviewed} />
        )}
        {tab === "thresholds" && canReadThresholds && (
          <ThresholdsView session={session} stats={stats} onSaved={setThresholds} />
        )}
        {tab === "audit" && (session.role === "admin" || session.role === "driver") && (
          <>
            {session.role === "driver" && <MyDataCard session={session} />}
            {session.role === "admin" && <DeletionRequestsCard session={session} refreshKey={refreshKey} />}
            <AuditView session={session} range={filters.range} refreshKey={refreshKey} />
          </>
        )}
        {policy && <p className="muted small">{policy}</p>}
      </main>
    </div>
  );
}
