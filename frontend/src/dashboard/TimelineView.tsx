import { useEffect, useRef, useState } from "react";
import { getTimeline, getTrips } from "../lib/api";
import { formatDateTime, formatNumber, formatPercent, formatTime, type RangeKey } from "../lib/format";
import { LEVELS } from "../lib/labels";
import type { Session, Timeline, Trip } from "../lib/types";
import { LevelBadge } from "./EventLog";
import FatigueChart from "./FatigueChart";

interface Props {
  session: Session;
  range: RangeKey;
  tripId: string;
  onTripChange: (tripId: string) => void;
  l1: number;
  l2: number;
  refreshKey: number;
}

export default function TimelineView({ session, range, tripId, onTripChange, l1, l2, refreshKey }: Props) {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asTable, setAsTable] = useState(false);
  const current = useRef({ tripId, onTripChange });
  current.current = { tripId, onTripChange };

  useEffect(() => {
    getTrips(session, range)
      .then((list) => {
        setTrips(list);
        // Pick the newest trip when none is selected yet.
        if (!current.current.tripId && list.length) current.current.onTripChange(list[0].trip_id);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, range, refreshKey]);

  useEffect(() => {
    if (!tripId) {
      setTimeline(null);
      return;
    }
    getTimeline(session, tripId)
      .then((tl) => {
        setTimeline(tl);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, tripId, refreshKey]);

  const trip = trips.find((t) => t.trip_id === tripId);
  const samples = timeline?.samples ?? [];
  const peak = samples.reduce((m, s) => Math.max(m, s.drowsy_score), 0);

  return (
    <section className="card">
      <div className="card-head">
        <h2>Timeline mệt mỏi</h2>
        <label className="field-inline">
          Chuyến đi
          <select value={tripId} onChange={(e) => onTripChange(e.target.value)}>
            {!trips.some((t) => t.trip_id === tripId) && tripId && <option value={tripId}>{tripId}</option>}
            {trips.length === 0 && !tripId && <option value="">Chưa có chuyến nào</option>}
            {trips.map((t) => (
              <option key={`${t.trip_id}-${t.device_id}`} value={t.trip_id}>
                {t.trip_id} · {t.driver_id ?? t.device_id} · {formatDateTime(t.start)}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="ghost" onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}>
          {asTable ? "Xem biểu đồ" : "Xem bảng"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {trip && (
        <p className="muted">
          {trip.driver_id ?? "–"} · {trip.device_id} · {formatDateTime(trip.start)} → {formatTime(trip.end)} ·{" "}
          {trip.events} cảnh báo · cao nhất <LevelBadge level={trip.max_level} /> · drowsy_score đỉnh{" "}
          {formatNumber(peak, 1)}
        </p>
      )}
      {timeline && samples.length === 0 && timeline.events.length === 0 && (
        <p className="empty">Chuyến này chưa có dữ liệu. Mỗi phút lái, thiết bị gửi 1 điểm drowsy_score.</p>
      )}
      {timeline && (samples.length > 0 || timeline.events.length > 0) &&
        (asTable ? (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Phút kết thúc</th>
                  <th scope="col" className="num">
                    drowsy_score
                  </th>
                  <th scope="col" className="num">
                    PERCLOS
                  </th>
                  <th scope="col">Mức cao nhất</th>
                </tr>
              </thead>
              <tbody>
                {samples.map((s) => (
                  <tr key={s.ts}>
                    <td>{formatTime(s.ts)}</td>
                    <td className="num">{formatNumber(s.drowsy_score, 1)}</td>
                    <td className="num">{formatPercent(s.perclos_60s, 1)}</td>
                    <td>
                      {LEVELS[s.max_level].icon} {LEVELS[s.max_level].short}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <FatigueChart samples={samples} events={timeline.events} l1={l1} l2={l2} />
        ))}
    </section>
  );
}
