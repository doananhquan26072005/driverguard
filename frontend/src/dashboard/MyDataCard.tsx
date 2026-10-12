// "Dữ liệu của tôi" (M48, docs/data-policy.md): a driver downloads everything stored about them and
// may ask for it to be deleted; an admin sees the requests and deletes the data or refuses with a
// reason. Nothing here ever held an image: the export is the numbers and codes the backend stores.
import { useEffect, useState } from "react";
import { decideDeletion, getDeletionRequests, getMyData, getMyDeletionRequest, requestMyDeletion } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { DELETION_STATUS, REFUSAL_REASONS } from "../lib/labels";
import type { DeletionRequest, RefusalReason, Session } from "../lib/types";

/** File name of an export: driverguard-<driver>-<yyyy-mm-dd>.json */
export function exportFileName(driverId: string, now: Date): string {
  return `driverguard-${driverId.replace(/[^A-Za-z0-9_.-]/g, "_")}-${now.toISOString().slice(0, 10)}.json`;
}

export function deletionStatusText(r: DeletionRequest): string {
  const base = DELETION_STATUS[r.status];
  return r.status === "refused" && r.reason ? `${base}: ${REFUSAL_REASONS[r.reason]}` : base;
}

function saveJson(data: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function MyDataCard({ session }: { session: Session }) {
  const [request, setRequest] = useState<DeletionRequest | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getMyDeletionRequest(session)
      .then(setRequest)
      .catch(() => setRequest(null));
  }, [session]);

  async function run(work: () => Promise<void>) {
    setBusy(true);
    setMessage(null);
    try {
      await work();
    } catch (e) {
      setMessage({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  const download = () =>
    run(async () => {
      const data = await getMyData(session);
      saveJson(data, exportFileName(String(data.driver_id ?? session.username), new Date()));
      setMessage({ ok: true, text: "Đã tải file dữ liệu của bạn." });
    });

  const askDeletion = () => {
    if (!window.confirm("Xoá toàn bộ cảnh báo, số đo và báo cáo ca lái của bạn? Xoá rồi không khôi phục được. Quản trị viên sẽ xử lý yêu cầu.")) return;
    void run(async () => {
      setRequest(await requestMyDeletion(session));
      setMessage({ ok: true, text: "Đã gửi yêu cầu xoá dữ liệu." });
    });
  };

  return (
    <section className="card">
      <div className="card-head">
        <h2>Dữ liệu của tôi</h2>
      </div>
      <p className="muted small">
        Hệ thống chỉ lưu số đo và cảnh báo, không lưu ảnh hay video. Bạn có thể tải toàn bộ dữ liệu của mình về máy
        hoặc yêu cầu xoá.
      </p>
      {request && (
        <p className="small">
          Yêu cầu xoá gửi {formatDateTime(request.requested_at)}: <strong>{deletionStatusText(request)}</strong>
        </p>
      )}
      {message && (
        <p className={message.ok ? "success" : "error"} role="status">
          {message.text}
        </p>
      )}
      <div className="actions">
        <button type="button" className="primary" disabled={busy} onClick={() => void download()}>
          Tải dữ liệu của tôi
        </button>
        <button type="button" className="ghost" disabled={busy || request?.status === "pending"} onClick={askDeletion}>
          Yêu cầu xoá dữ liệu
        </button>
      </div>
    </section>
  );
}

export function DeletionRequestsCard({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const [rows, setRows] = useState<DeletionRequest[]>([]);
  const [reasons, setReasons] = useState<Record<number, RefusalReason>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getDeletionRequests(session)
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, [session, refreshKey]);

  async function decide(r: DeletionRequest, refuse: boolean) {
    const text = refuse
      ? `Từ chối yêu cầu xoá của ${r.driver_id}?`
      : `Xoá toàn bộ dữ liệu đã lưu của ${r.driver_id}? Không khôi phục được.`;
    if (!window.confirm(text)) return;
    setBusy(true);
    setError(null);
    try {
      const done = await decideDeletion(session, r.id, refuse ? (reasons[r.id] ?? "other") : undefined);
      setRows((list) => list.map((x) => (x.id === done.id ? done : x)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (rows.length === 0 && !error) return null;
  return (
    <section className="card">
      <div className="card-head">
        <h2>Yêu cầu xoá dữ liệu</h2>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Gửi lúc</th>
              <th scope="col">Tài xế</th>
              <th scope="col">Tài khoản</th>
              <th scope="col">Trạng thái</th>
              <th scope="col" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="nowrap">{formatDateTime(r.requested_at)}</td>
                <td>{r.driver_id}</td>
                <td>{r.requested_by}</td>
                <td>
                  {deletionStatusText(r)}
                  {r.handled_by && <span className="muted small"> · {r.handled_by}</span>}
                </td>
                <td className="nowrap">
                  {r.status === "pending" && (
                    <>
                      <button type="button" className="primary" disabled={busy} onClick={() => void decide(r, false)}>
                        Xoá dữ liệu
                      </button>{" "}
                      <select
                        aria-label="Lý do từ chối"
                        value={reasons[r.id] ?? "other"}
                        onChange={(e) => setReasons((m) => ({ ...m, [r.id]: e.target.value as RefusalReason }))}
                      >
                        {(Object.keys(REFUSAL_REASONS) as RefusalReason[]).map((k) => (
                          <option key={k} value={k}>
                            {REFUSAL_REASONS[k]}
                          </option>
                        ))}
                      </select>{" "}
                      <button type="button" className="ghost" disabled={busy} onClick={() => void decide(r, true)}>
                        Từ chối
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
