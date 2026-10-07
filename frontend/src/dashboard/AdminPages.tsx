// Admin pages (M63, design "Quản trị · Tài khoản và thiết bị"): accounts with their role, a form to add
// one; devices (from the fleet list: the backend has no other device list) with the driver they belong
// to, a form to add one. A new device key is shown once, to copy into the car, and kept only in memory.
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Copy, KeyRound } from "lucide-react";
import { ApiError, createDevice, createUser, getFleet, getUsers, type UserRow } from "../lib/api";
import { dayKey } from "../lib/format";
import { FLEET_STATUS, ROLES } from "../lib/labels";
import type { FleetDevice, Role, Session } from "../lib/types";

const ROLE_TONE: Record<Role, string> = {
  driver: "var(--good)",
  manager: "var(--series-1)",
  engineer: "var(--warning)",
  admin: "#c4b5fd",
};
const ROLE_ORDER: Role[] = ["driver", "manager", "engineer", "admin"];

function errorText(e: unknown): string {
  if (e instanceof ApiError && e.status === 409) return "Tên này đã có, chọn tên khác.";
  if (e instanceof ApiError && e.status === 422) return "Thông tin chưa hợp lệ: tên chỉ gồm chữ không dấu, số, dấu . _ -; mật khẩu ít nhất 8 ký tự.";
  return (e as Error).message;
}

export function AccountsPage({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const [users, setUsers] = useState<UserRow[] | null>(null);
  const [filter, setFilter] = useState<Role | "">("");
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ username: "", password: "", role: "driver" as Role, driver_id: "" });
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getUsers(session)
      .then((list) => {
        setUsers(list);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, refreshKey]);

  const shown = useMemo(
    () => (users ?? []).filter((u) => !filter || u.role === filter).sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role) || a.username.localeCompare(b.username)),
    [users, filter],
  );

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const created = await createUser(session, { ...form, username: form.username.trim(), driver_id: form.role === "driver" ? form.driver_id.trim() : null });
      setUsers((list) => [...(list ?? []), created]);
      setMessage({ ok: true, text: `Đã tạo tài khoản ${created.username} (${ROLES[created.role]}).` });
      setForm({ username: "", password: "", role: form.role, driver_id: "" });
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid-2">
      <section className="dg-card web-card">
        <div className="row-between">
          <h2>
            Danh sách <span className="muted">({users?.length ?? "…"})</span>
          </h2>
          <label className="field-inline">
            Vai trò
            <select value={filter} onChange={(e) => setFilter(e.target.value as Role | "")}>
              <option value="">Tất cả</option>
              {ROLE_ORDER.map((r) => (
                <option key={r} value={r}>
                  {ROLES[r]}
                </option>
              ))}
            </select>
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Tên đăng nhập</th>
                <th>Vai trò</th>
                <th>Mã tài xế</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((u) => (
                <tr key={u.username}>
                  <td>
                    <b>{u.username}</b>
                  </td>
                  <td>
                    <span className="dg-chip" style={{ ["--dot" as string]: ROLE_TONE[u.role] }}>
                      <i />
                      {ROLES[u.role]}
                    </span>
                  </td>
                  <td className="mono muted">{u.driver_id ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <form className="dg-card web-card admin-form" onSubmit={submit}>
        <h2>Thêm tài khoản</h2>
        <label>
          Tên đăng nhập
          <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required autoComplete="off" />
        </label>
        <label>
          Mật khẩu ban đầu
          <input type="password" value={form.password} minLength={8} onChange={(e) => setForm({ ...form, password: e.target.value })} required autoComplete="new-password" />
          <span className="muted small">Ít nhất 8 ký tự</span>
        </label>
        <fieldset className="role-pick">
          <legend>Vai trò</legend>
          {ROLE_ORDER.map((r) => (
            <label key={r} className={form.role === r ? "picked" : undefined}>
              <input type="radio" name="role" checked={form.role === r} onChange={() => setForm({ ...form, role: r })} />
              {ROLES[r]}
            </label>
          ))}
        </fieldset>
        {form.role === "driver" && (
          <label>
            Mã tài xế
            <input value={form.driver_id} onChange={(e) => setForm({ ...form, driver_id: e.target.value })} required placeholder="vd. drv-040" />
            <span className="muted small">Bắt buộc với tài xế: nối tài khoản với cảnh báo của họ</span>
          </label>
        )}
        {message && (
          <p className={message.ok ? "success" : "form-error"} role="status">
            {message.text}
          </p>
        )}
        <button type="submit" className="primary big" disabled={busy}>
          {busy ? "Đang tạo…" : "Tạo tài khoản"}
        </button>
      </form>
    </div>
  );
}

export function DevicesPage({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const [devices, setDevices] = useState<FleetDevice[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ device_id: "", driver_id: "" });
  const [created, setCreated] = useState<{ device_id: string; key: string } | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    getFleet(session, dayKey())
      .then((list) => {
        setDevices([...list].sort((a, b) => a.device_id.localeCompare(b.device_id)));
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [session, refreshKey, reload]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setCopied(false);
    try {
      const d = await createDevice(session, { device_id: form.device_id.trim(), driver_id: form.driver_id.trim() || null });
      setCreated(d.device_key ? { device_id: d.device_id, key: d.device_key } : null);
      setForm({ device_id: "", driver_id: "" });
      setReload((n) => n + 1);
    } catch (err) {
      setMessage(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="grid-2">
      <section className="dg-card web-card">
        <h2>
          Thiết bị <span className="muted">({devices?.length ?? "…"})</span>
        </h2>
        {error && <p className="error">{error}</p>}
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Thiết bị</th>
                <th>Tài xế</th>
                <th>Liên lạc</th>
              </tr>
            </thead>
            <tbody>
              {(devices ?? []).map((d) => (
                <tr key={d.device_id}>
                  <td className="mono">
                    <b>{d.device_id}</b>
                  </td>
                  <td className="mono muted">{d.driver_id ?? "–"}</td>
                  <td>{FLEET_STATUS[d.status].title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">Khoá thiết bị không bao giờ hiện lại sau lúc tạo: mất khoá thì tạo thiết bị mới.</p>
      </section>

      <div className="stack">
        <form className="dg-card web-card admin-form" onSubmit={submit}>
          <h2>Thêm thiết bị</h2>
          <label>
            Mã thiết bị
            <input value={form.device_id} onChange={(e) => setForm({ ...form, device_id: e.target.value })} required placeholder="vd. dev-19" />
          </label>
          <label>
            Mã tài xế của xe
            <input value={form.driver_id} onChange={(e) => setForm({ ...form, driver_id: e.target.value })} placeholder="vd. drv-040 (để trống nếu chưa gắn)" />
            <span className="muted small">Cảnh báo của thiết bị được gán cho tài xế này.</span>
          </label>
          {message && (
            <p className="form-error" role="status">
              {message}
            </p>
          )}
          <button type="submit" className="primary big" disabled={busy}>
            {busy ? "Đang tạo…" : "Tạo thiết bị"}
          </button>
        </form>

        {created && (
          <section className="dg-alert l1 web-card" role="status">
            <h2>
              <KeyRound aria-hidden size={18} /> Thiết bị {created.device_id} vừa được tạo
            </h2>
            <p className="muted">Khoá thiết bị chỉ hiện một lần. Sao chép và cài vào xe ngay (biến DG_DEVICE_KEY).</p>
            <div className="key-row">
              <code>{created.key}</code>
              <button type="button" className="primary" onClick={() => void copy()}>
                <Copy aria-hidden size={16} /> {copied ? "Đã sao chép" : "Sao chép"}
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
