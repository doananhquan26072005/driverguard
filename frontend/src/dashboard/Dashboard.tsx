// Web app after login (M60): a menu on the left with only this role's pages (nav.ts), the page on the
// right. Pages are #/dashboard/<page>. The data of every page comes from the same backend endpoints as
// before; the backend still decides what each role may read.
import { useCallback, useEffect, useState } from "react";
import { Car, LogOut } from "lucide-react";
import { BrandMark, BrandName } from "../brand/Brand";
import { type EventFilters, getEvents, getPolicy, getStats, getThresholds, getTripReports, loadSession, saveSession } from "../lib/api";
import { RANGES, type RangeKey } from "../lib/format";
import { LEVELS, policyNote, ROLES } from "../lib/labels";
import type { EventRecord, Session, Stats, Thresholds } from "../lib/types";
import { AccountsPage, DevicesPage } from "./AdminPages";
import AuditView from "./AuditView";
import { DriverOverview, DriverTrips } from "./DriverPages";
import { ManagerOverview, ReportReview } from "./ManagerPages";
import { DeletionRequestsCard, MyDataCard } from "./MyDataCard";
import EventLog from "./EventLog";
import FleetView from "./FleetView";
import Login from "./Login";
import { NAV, PAGE_LEAD, pageFromHash, pageHref, pageLabel, type PageKey } from "./nav";
import StatsTiles from "./StatsTiles";
import ThresholdsView from "./ThresholdsView";
import TimelineView from "./TimelineView";
import TripReports from "./TripReports";
import { HUD_DEFAULTS } from "../lib/defaults";

const REFRESH_MS = 15_000;

export default function Dashboard() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [hash, setHash] = useState(() => window.location.hash);
  const [filters, setFilters] = useState<EventFilters>({ range: "7d", minLevel: 0, driverId: "", falseAlarmOnly: false });
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [tripId, setTripId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [unreviewed, setUnreviewed] = useState(0); // trip reports no higher role has read yet
  const [policy, setPolicy] = useState<string | null>(null); // data policy line under every page

  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const logout = useCallback(() => {
    saveSession(null);
    setSession(null);
    window.location.hash = "#/dashboard";
  }, []);

  function onLogin(s: Session) {
    saveSession(s);
    setSession(s);
    window.location.hash = "#/dashboard"; // the role's home page
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

  // Trip reports no higher role has read yet: counted on the menu from the start, refreshed with the rest.
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

  const page = pageFromHash(hash, session.role);
  const drivers = [...new Set(events.map((e) => e.driver_id).filter(Boolean))] as string[];
  const showRange = !["fleet", "accounts", "devices", "overview", "trips"].includes(page);
  const showEventFilters = page === "events" || page === "alerts";
  const showStats = ["events", "alerts", "timeline", "reports", "thresholds"].includes(page);
  const goTimeline = (id: string) => {
    setTripId(id);
    window.location.hash = pageHref("timeline");
  };

  return (
    <div className="app">
      <nav className="side" aria-label="Menu">
        <div className="brand">
          <BrandMark />
          <span>
            <BrandName />
          </span>
        </div>
        {/* 13/10: a driver starts the next trip from any page (the camera opens at once, #/live?start). */}
        {session.role === "driver" && (
          <a className="side-start" href="#/live?start">
            <Car aria-hidden size={18} /> Bắt đầu ca lái mới
          </a>
        )}
        {NAV[session.role].map((section) => (
          <div key={section.title ?? "main"} className="side-group">
            {section.title && <span className="side-title">{section.title}</span>}
            {section.items.map((item) => (
              <a key={item.page} href={pageHref(item.page)} aria-current={item.page === page ? "page" : undefined}>
                {item.label}
                {item.page === "reports" && unreviewed > 0 && <span className="count">{unreviewed}</span>}
              </a>
            ))}
          </div>
        ))}
        <div className="side-user">
          <b>{session.username}</b>
          <span className="muted">
            {ROLES[session.role]}
            {session.driverId ? ` · mã ${session.driverId}` : ""}
          </span>
          {/* 13/10: a demo account (DG_READ_ONLY_USERS) looks at everything and changes nothing */}
          {session.readOnly && <span className="side-readonly">Tài khoản dùng thử · chỉ xem</span>}
          <button type="button" className="link" onClick={logout}>
            <LogOut aria-hidden size={14} /> Đăng xuất
          </button>
        </div>
      </nav>

      <main className="page">
        <header className="page-head">
          <div>
            <h1>{pageLabel(session.role, page)}</h1>
            {PAGE_LEAD[page] && <p className="muted">{PAGE_LEAD[page]}</p>}
          </div>
          <div className="filters" role="group" aria-label="Bộ lọc">
            {showRange && (
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
            {showEventFilters && (
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
                  Chỉ cảnh báo bị báo sai
                </label>
              </>
            )}
            <button type="button" className="ghost" onClick={() => setRefreshKey((k) => k + 1)}>
              Làm mới
            </button>
            {loading && <span className="muted small">Đang tải…</span>}
          </div>
        </header>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {showStats && <StatsTiles stats={stats} />}

        <PageBody
          page={page}
          session={session}
          events={events}
          loading={loading}
          filtersRange={filters.range}
          refreshKey={refreshKey}
          stats={stats}
          tripId={tripId}
          onTripChange={setTripId}
          onPickTrip={goTimeline}
          l1={thresholds?.values["risk.drowsy.l1"] ?? HUD_DEFAULTS.score_l1}
          l2={thresholds?.values["risk.drowsy.l2"] ?? HUD_DEFAULTS.score_l2}
          onUnreviewed={setUnreviewed}
          onThresholdsSaved={setThresholds}
          hash={hash}
        />
        {policy && <p className="muted small policy">{policy}</p>}
      </main>
    </div>
  );
}

interface PageProps {
  page: PageKey;
  session: Session;
  events: EventRecord[];
  loading: boolean;
  filtersRange: RangeKey;
  refreshKey: number;
  stats: Stats | null;
  tripId: string;
  onTripChange: (id: string) => void;
  onPickTrip: (id: string) => void;
  l1: number;
  l2: number;
  onUnreviewed: (n: number) => void;
  onThresholdsSaved: (t: Thresholds) => void;
  hash: string;
}

function PageBody(p: PageProps) {
  const { session } = p;
  switch (p.page) {
    case "overview":
      // M61 (driver) / M62 (manager) give these their own page; until then the closest one.
      return session.role === "driver" ? (
        <DriverOverview session={session} refreshKey={p.refreshKey} />
      ) : (
        <ManagerOverview session={session} refreshKey={p.refreshKey} />
      );
    case "fleet":
      return <FleetView session={session} refreshKey={p.refreshKey} />;
    case "trips":
      return <DriverTrips session={session} refreshKey={p.refreshKey} hash={p.hash} />;
    case "reports":
      // The manager reviews (design "Duyệt báo cáo chuyến"); engineer and admin keep every number.
      if (session.role === "manager")
        return (
          <ReportReview session={session} range={p.filtersRange} refreshKey={p.refreshKey} onUnreviewed={p.onUnreviewed} onPickTrip={p.onPickTrip} />
        );
      return <TripReports session={session} range={p.filtersRange} refreshKey={p.refreshKey} onUnreviewed={p.onUnreviewed} />;
    case "events":
    case "alerts":
      return (
        <section className="card">
          <EventLog events={p.events} loading={p.loading} onPickTrip={p.onPickTrip} />
        </section>
      );
    case "timeline":
      return (
        <TimelineView
          session={session}
          range={p.filtersRange}
          tripId={p.tripId}
          onTripChange={p.onTripChange}
          l1={p.l1}
          l2={p.l2}
          refreshKey={p.refreshKey}
        />
      );
    case "thresholds":
      return <ThresholdsView session={session} stats={p.stats} onSaved={p.onThresholdsSaved} />;
    case "mydata":
      return (
        <>
          <MyDataCard session={session} />
          <AuditView session={session} range={p.filtersRange} refreshKey={p.refreshKey} />
        </>
      );
    case "access":
      return (
        <>
          <DeletionRequestsCard session={session} refreshKey={p.refreshKey} />
          <AuditView session={session} range={p.filtersRange} refreshKey={p.refreshKey} />
        </>
      );
    case "accounts":
      return <AccountsPage session={session} refreshKey={p.refreshKey} />;
    case "devices":
      return <DevicesPage session={session} refreshKey={p.refreshKey} />;
  }
}
