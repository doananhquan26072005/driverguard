// "Nhật ký truy cập" (M41): who read whose data, who changed thresholds / accounts, who deleted data.
// Admins see every row; a driver sees who looked at their own data (and reads of the whole fleet).
import { useEffect, useState } from "react";
import { getAccessLog } from "../lib/api";
import { formatDateTime, type RangeKey } from "../lib/format";
import { ROLES, auditActionText, auditScopeText } from "../lib/labels";
import type { AccessLogRow, Role, Session } from "../lib/types";

export default function AuditView({ session, range, refreshKey }: { session: Session; range: RangeKey; refreshKey: number }) {
  const [rows, setRows] = useState<AccessLogRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mine = session.role === "driver";

  useEffect(() => {
    let cancelled = false;
    getAccessLog(session, range)
      .then((list) => {
        if (cancelled) return;
        setRows(list);
        setError(null);
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [session, range, refreshKey]);

  return (
    <section className="card">
      <div className="card-head">
        <h2>{mine ? "Ai đã xem dữ liệu của tôi" : "Nhật ký truy cập"}</h2>
      </div>
      <p className="muted small">
        {mine
          ? "Mỗi lần quản lý, kỹ sư hay quản trị xem dữ liệu của bạn (hoặc của cả đội xe) đều được ghi lại ở đây."
          : "Chỉ ghi thêm, không sửa được. Cùng một thao tác xem của cùng một tài khoản được ghi một lần trong mỗi khoảng thời gian ngắn."}
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {rows && rows.length === 0 ? (
        <p className="empty">Chưa có lượt truy cập nào trong khoảng thời gian này.</p>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Thời gian</th>
                <th scope="col">Tài khoản</th>
                <th scope="col">Vai trò</th>
                <th scope="col">Thao tác</th>
                <th scope="col">Dữ liệu của</th>
                <th scope="col">Chi tiết</th>
              </tr>
            </thead>
            <tbody>
              {(rows ?? []).map((r, i) => (
                <tr key={`${r.ts}-${i}`}>
                  <td className="nowrap">{formatDateTime(r.ts)}</td>
                  <td>{r.username}</td>
                  <td>{ROLES[r.role as Role] ?? r.role}</td>
                  <td>{auditActionText(r.action)}</td>
                  <td>{auditScopeText(r)}</td>
                  <td>{r.detail ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
