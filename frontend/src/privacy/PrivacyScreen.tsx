// #/privacy (M106): what DriverGuard does with a driver's data, in the product itself. No login, no camera.
// A short form of docs/data-policy.md: every sentence here must stay true to that file and to the code.
// The two retention periods are read from /api/v1/policy (the server's settings); with no backend the
// page shows the defaults of labels.ts (RETENTION_DAYS, the numbers the consent screen states).
// Unlike #/guide this is a document: the window scrolls.
import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { BrandMark } from "../brand/Brand";
import { getPolicy } from "../lib/api";
import { RETENTION_DAYS } from "../lib/labels";
import "./privacy.css";

const keep = (days: number) => (days > 0 ? `${days} ngày` : "tới khi quản trị viên xoá");

export default function PrivacyScreen() {
  const [days, setDays] = useState(RETENTION_DAYS);

  useEffect(() => {
    getPolicy()
      .then((p) => setDays({ events: p.retention_events_days, summaries: p.retention_summaries_days }))
      .catch(() => undefined); // no backend (try-out, guide): the defaults stay
  }, []);

  return (
    <div className="privacy">
      <header className="guide-bar">
        <a className="guide-back" href="#/live" aria-label="Về trang đăng nhập">
          <ArrowLeft aria-hidden size={20} />
        </a>
        <BrandMark />
        <h1>Quyền riêng tư</h1>
      </header>

      <main className="privacy-main">
        <section className="privacy-lead">
          <h2>Ảnh khuôn mặt của bạn không rời thiết bị</h2>
          <p>
            DriverGuard nhìn khuôn mặt người lái qua camera để nhắc khi buồn ngủ hoặc mất tập trung. Hình từ camera chỉ nằm trong bộ nhớ của thiết bị
            trên xe (hoặc của trình duyệt) trong lúc xử lý. Không ảnh hay video nào được lưu hoặc gửi đi.
          </p>
        </section>

        <section className="privacy-grid">
          <article className="dg-card">
            <h3>Được gửi lên máy chủ</h3>
            <ul>
              <li>Cảnh báo: thời điểm, mức, lý do, tốc độ xe lúc đó và các số đo như thời gian nhắm mắt.</li>
              <li>Điểm buồn ngủ theo từng phút lái và bản tổng kết ca lái.</li>
              <li>Trạng thái thiết bị và những lần bạn chạm “Cảnh báo nhầm?”.</li>
            </ul>
          </article>
          <article className="dg-card">
            <h3>Không thu, không lưu, không gửi</h3>
            <ul>
              <li>Ảnh, video hay ảnh cắt vùng mắt, khuôn mặt. Máy chủ từ chối mọi nội dung giống ảnh.</li>
              <li>Các con số học được lúc làm quen khuôn mặt: xoá khi kết thúc ca lái.</li>
              <li>Vị trí, hành trình của xe và âm thanh trong xe.</li>
              <li>Hệ thống không nhận dạng bạn là ai từ khuôn mặt.</li>
            </ul>
          </article>
        </section>

        <section>
          <h3>Giữ bao lâu</h3>
          <dl className="privacy-keep">
            <div className="dg-card">
              <dt>Cảnh báo và điểm theo phút</dt>
              <dd data-keep="events">{keep(days.events)}</dd>
            </div>
            <div className="dg-card">
              <dt>Bản tổng kết ca lái</dt>
              <dd data-keep="summaries">{keep(days.summaries)}</dd>
            </div>
          </dl>
          <p className="muted">Hết hạn, máy chủ tự xoá. Ở chế độ “Dùng thử không lưu”, không số liệu giám sát nào rời trình duyệt.</p>
        </section>

        <section>
          <h3>Ai xem được</h3>
          <ul>
            <li>Tài xế: chỉ số liệu của chính mình.</li>
            <li>Quản lý đội xe và kỹ sư an toàn: số liệu của các tài xế trong đội. Mỗi lượt xem được ghi vào nhật ký truy cập.</li>
            <li>Không chuyển cho bên thứ ba. Không dùng để tự động kỷ luật, trừ lương hay xếp hạng tài xế.</li>
          </ul>
        </section>

        <section>
          <h3>Quyền của tài xế</h3>
          <ul>
            <li>Xem toàn bộ số liệu của mình và biết ai đã xem nó, ở trang “Dữ liệu của tôi” sau khi đăng nhập.</li>
            <li>Tải một bản sao số liệu của mình.</li>
            <li>Gửi yêu cầu xoá số liệu; quản trị viên của đội xe trả lời kèm lý do.</li>
            <li>Báo một cảnh báo là nhầm. Cảnh báo có thể sai, nên không ai được kết luận về bạn từ một cảnh báo đơn lẻ.</li>
            <li>Chọn “Để sau” ở bước làm quen khuôn mặt: vẫn lái được, cảnh báo kém chính xác hơn.</li>
          </ul>
        </section>

        <section>
          <h3>Giới hạn cần biết</h3>
          <ul>
            <li>Số liệu gắn với mã tài xế nên vẫn là dữ liệu cá nhân, dù không có ảnh.</li>
            <li>Đây là sản phẩm của một dự án học tập, chưa được rà soát pháp lý. Đơn vị dùng trên xe thật phải tự thông báo và thoả thuận với tài xế.</li>
          </ul>
        </section>

        <p className="muted small">
          Câu hỏi về dữ liệu của bạn: liên hệ quản trị viên của đội xe. Xem thêm <a href="#/guide">Hướng dẫn sử dụng</a>.
        </p>
      </main>
    </div>
  );
}
