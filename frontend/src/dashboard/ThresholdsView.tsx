import { type FormEvent, useEffect, useState } from "react";
import { getThresholdVersions, getThresholds, putThresholds, rolloutThresholds } from "../lib/api";
import { changedValues, formatDateTime, formatPercent } from "../lib/format";
import { REASONS, THRESHOLD_GROUPS, UNITS, reasonText } from "../lib/labels";
import type { Reason, Session, Stats, ThresholdVersion, Thresholds } from "../lib/types";

// A false-alarm share from here is drawn orange: a hint, not a rule (thresholds change only by hand).
const FALSE_ALARM_HIGH = 0.2;

/** "cam-001, cam-007 web-an" -> ["cam-001", "cam-007", "web-an"] */
export function parseDeviceList(text: string): string[] {
  return [...new Set(text.split(/[\s,;]+/).filter(Boolean))];
}

interface Props {
  session: Session;
  stats: Stats | null;
  onSaved: (t: Thresholds) => void;
}

export default function ThresholdsView({ session, stats, onSaved }: Props) {
  const canEdit = session.role === "engineer" || session.role === "admin";
  const [data, setData] = useState<Thresholds | null>(null);
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [versions, setVersions] = useState<ThresholdVersion[]>([]);
  const [trial, setTrial] = useState("");

  const loadVersions = () =>
    getThresholdVersions(session)
      .then(setVersions)
      .catch(() => setVersions([]));

  useEffect(() => {
    getThresholds(session)
      .then(setData)
      .catch((e: Error) => setMessage({ ok: false, text: e.message }));
    void getThresholdVersions(session)
      .then(setVersions)
      .catch(() => setVersions([]));
  }, [session]);

  async function rollout(version: number) {
    if (!window.confirm(`Áp phiên bản ${version} cho cả đội xe? Các xe đang thử phiên bản khác cũng chuyển sang phiên bản này.`)) return;
    setBusy(true);
    setMessage(null);
    try {
      const saved = await rolloutThresholds(session, version);
      setData(saved);
      onSaved(saved);
      setMessage({ ok: true, text: `Cả đội dùng phiên bản ${version}. Mỗi xe nhận khi đỗ lần tới.` });
      await loadVersions();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  const { values: changes, invalid } = changedValues(edited, data?.values ?? {});
  const dirty = Object.keys(changes).length > 0;

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!dirty || invalid.length) return;
    setBusy(true);
    setMessage(null);
    try {
      const devices = parseDeviceList(trial);
      const saved = await putThresholds(session, changes, devices);
      setData(saved);
      setEdited({});
      setTrial("");
      onSaved(saved);
      setMessage({
        ok: true,
        text: devices.length
          ? `Đã lưu phiên bản ${saved.version}, chỉ áp thử cho ${devices.join(", ")}. Cả đội vẫn dùng phiên bản ${saved.fleet_version ?? "cũ"}.`
          : `Đã lưu phiên bản ${saved.version} cho cả đội. Mỗi xe nhận khi đỗ lần tới (hỏi lại mỗi vài phút).`,
      });
      await loadVersions();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  const reasonRows = Object.entries(stats?.by_reason ?? {}).sort((a, b) => b[1].total - a[1].total);

  return (
    <div className="split">
      <form className="card" onSubmit={save}>
        <div className="card-head">
          <h2>Ngưỡng cảnh báo</h2>
          <span className="muted small">
            {data?.version
              ? `Phiên bản ${data.version} · ${data.updated_by} · ${formatDateTime(data.updated_at ?? "")}`
              : "Chưa chỉnh: thiết bị dùng thresholds.yaml của nó"}
          </span>
        </div>
        {!canEdit && <p className="muted">Chỉ kỹ sư được chỉnh ngưỡng. Bạn đang xem ở chế độ chỉ đọc.</p>}
        {/* M63 (design "Kỹ sư · Ngưỡng và báo sai"): what is not saved yet, always in view. */}
        {canEdit && dirty && (
          <div className="unsaved" role="status">
            <span>
              <b>{Object.keys(changes).length} thay đổi chưa lưu</b>
              {" · "}
              {THRESHOLD_GROUPS.flatMap((g) => g.keys)
                .filter((k) => k.key in changes)
                .map((k) => k.label)
                .join(", ")}
            </span>
            <button type="button" className="ghost" onClick={() => setEdited({})} disabled={busy}>
              Hoàn tác
            </button>
            <button type="submit" className="primary" disabled={invalid.length > 0 || busy}>
              {busy ? "Đang lưu…" : `Lưu thành phiên bản ${(versions[0]?.version ?? data?.version ?? 0) + 1}`}
            </button>
          </div>
        )}
        {THRESHOLD_GROUPS.map((group) => (
          <fieldset key={group.title} disabled={!canEdit || busy}>
            <legend>{group.title}</legend>
            {group.keys.map(({ key, label, hint }) => {
              const spec = data?.specs[key];
              const stored = data?.values[key];
              const id = `th-${key}`;
              const changed = key in changes;
              return (
                <div className={`field-row${changed ? " edited" : ""}`} key={key}>
                  <label htmlFor={id}>
                    {label}
                    <span className="field-key">{key}</span>
                    {changed ? (
                      <span className="field-hint changed">Đã sửa · trước đó {stored != null ? String(stored) : "mặc định"}</span>
                    ) : (
                      hint && <span className="field-hint">{hint}</span>
                    )}
                  </label>
                  <div className="field-input">
                    <input
                      id={id}
                      inputMode="decimal"
                      value={edited[key] ?? (stored != null ? String(stored) : "")}
                      placeholder="mặc định"
                      aria-invalid={invalid.includes(key)}
                      onChange={(e) => setEdited((prev) => ({ ...prev, [key]: e.target.value }))}
                    />
                    <span className="field-unit">
                      {spec ? `${UNITS[spec.unit] ?? spec.unit} · ${spec.min}–${spec.max}` : ""}
                    </span>
                  </div>
                </div>
              );
            })}
          </fieldset>
        ))}
        {message && (
          <p className={message.ok ? "success" : "error"} role="status">
            {message.text}
          </p>
        )}
        {canEdit && (
          <div className="field-row">
            <label htmlFor="th-trial">
              Chỉ áp thử cho các xe
              <span className="field-hint">Mã thiết bị, cách nhau bằng dấu phẩy. Để trống = áp cho cả đội.</span>
            </label>
            <div className="field-input">
              <input id="th-trial" value={trial} placeholder="vd. cam-001, cam-007" onChange={(e) => setTrial(e.target.value)} />
            </div>
          </div>
        )}
        {canEdit && (
          <div className="actions">
            <button type="button" className="ghost" onClick={() => setEdited({})} disabled={!dirty || busy}>
              Hoàn tác
            </button>
            <button type="submit" className="primary" disabled={!dirty || invalid.length > 0 || busy}>
              {busy ? "Đang lưu…" : `Lưu ${Object.keys(changes).length || ""} thay đổi`}
            </button>
          </div>
        )}
      </form>

      <section className="card">
        <h2>Phiên bản ngưỡng</h2>
        <p className="muted small">
          Thử một phiên bản trên vài xe, xem số cảnh báo và số lần tài xế bấm “Cảnh báo sai”, rồi mới áp cho cả đội. Áp
          lại một phiên bản cũ là quay lui. Xe chỉ đổi ngưỡng khi đang đỗ.
        </p>
        {versions.length === 0 ? (
          <p className="empty">Chưa có phiên bản nào.</p>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Phiên bản</th>
                  <th scope="col">Thay đổi</th>
                  <th scope="col">Đang chạy trên</th>
                  <th scope="col" className="num">
                    Cảnh báo
                  </th>
                  <th scope="col" className="num">
                    Báo sai
                  </th>
                  <th scope="col" />
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.version}>
                    <td className="nowrap">
                      {v.version} {v.fleet && <span className="badge level-0">Cả đội</span>}
                      {v.pinned_devices.length > 0 && (
                        <span className="tag" title={v.pinned_devices.join(", ")}>
                          Thử: {v.pinned_devices.length} xe
                        </span>
                      )}
                      <div className="muted small">
                        {v.updated_by} · {formatDateTime(v.updated_at)}
                      </div>
                    </td>
                    <td className="small">{v.changed.map((k) => `${k} = ${v.values[k]}`).join(", ") || "–"}</td>
                    <td className="small">{v.running_devices.join(", ") || "–"}</td>
                    <td className="num">{v.alerts}</td>
                    <td className="num">
                      {v.false_alarms}
                      {v.alerts > 0 && <span className="muted"> ({formatPercent(v.false_alarms / v.alerts)})</span>}
                    </td>
                    <td>
                      {canEdit && !v.fleet && (
                        <button type="button" className="ghost" disabled={busy} onClick={() => void rollout(v.version)}>
                          Áp cho cả đội
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Cảnh báo sai theo lý do</h2>
        <p className="muted small">Tài xế bấm “Cảnh báo sai” trên HUD. Tỉ lệ cao gợi ý ngưỡng đang quá nhạy.</p>
        {reasonRows.length === 0 ? (
          <p className="empty">Chưa có cảnh báo trong khoảng thời gian này.</p>
        ) : (
          <ul className="fa-bars">
            {reasonRows.map(([reason, s]) => {
              const share = s.total ? s.false_alarms / s.total : 0;
              const high = share >= FALSE_ALARM_HIGH;
              return (
                <li key={reason}>
                  <span className="row-between">
                    <b>{reason in REASONS ? reasonText(reason as Reason) : reason}</b>
                    <span className="muted dg-num">
                      {s.false_alarms} / {s.total} cảnh báo · <strong className={high ? "fa-high" : undefined}>{formatPercent(share)}</strong>
                    </span>
                  </span>
                  <span className="fa-track">
                    <span style={{ width: `${Math.max(2, Math.round(share * 100))}%` }} className={high ? "fa-high-bar" : undefined} />
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
