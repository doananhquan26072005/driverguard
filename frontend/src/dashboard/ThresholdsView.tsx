import { type FormEvent, useEffect, useState } from "react";
import { getThresholds, putThresholds } from "../lib/api";
import { changedValues, formatDateTime, formatPercent } from "../lib/format";
import { REASONS, THRESHOLD_GROUPS, UNITS, reasonText } from "../lib/labels";
import type { Reason, Session, Stats, Thresholds } from "../lib/types";

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

  useEffect(() => {
    getThresholds(session)
      .then(setData)
      .catch((e: Error) => setMessage({ ok: false, text: e.message }));
  }, [session]);

  const { values: changes, invalid } = changedValues(edited, data?.values ?? {});
  const dirty = Object.keys(changes).length > 0;

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!dirty || invalid.length) return;
    setBusy(true);
    setMessage(null);
    try {
      const saved = await putThresholds(session, changes);
      setData(saved);
      setEdited({});
      onSaved(saved);
      setMessage({ ok: true, text: `Đã lưu phiên bản ${saved.version}. Thiết bị áp dụng khi khởi động lại.` });
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
        {THRESHOLD_GROUPS.map((group) => (
          <fieldset key={group.title} disabled={!canEdit || busy}>
            <legend>{group.title}</legend>
            {group.keys.map(({ key, label, hint }) => {
              const spec = data?.specs[key];
              const stored = data?.values[key];
              const id = `th-${key}`;
              return (
                <div className="field-row" key={key}>
                  <label htmlFor={id}>
                    {label}
                    <span className="field-key">{key}</span>
                    {hint && <span className="field-hint">{hint}</span>}
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
        <h2>Cảnh báo sai theo lý do</h2>
        <p className="muted small">Tài xế bấm “Cảnh báo sai” trên HUD. Tỉ lệ cao gợi ý ngưỡng đang quá nhạy.</p>
        {reasonRows.length === 0 ? (
          <p className="empty">Chưa có cảnh báo trong khoảng thời gian này.</p>
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Lý do</th>
                <th scope="col" className="num">
                  Cảnh báo
                </th>
                <th scope="col" className="num">
                  Báo sai
                </th>
                <th scope="col" className="num">
                  Tỉ lệ
                </th>
              </tr>
            </thead>
            <tbody>
              {reasonRows.map(([reason, s]) => (
                <tr key={reason}>
                  <td>{reason in REASONS ? reasonText(reason as Reason) : reason}</td>
                  <td className="num">{s.total}</td>
                  <td className="num">{s.false_alarms}</td>
                  <td className="num">{formatPercent(s.total ? s.false_alarms / s.total : null)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
