# DriveGuard — Version 3

> Bản tiếp theo của [Version 2](release-v2.md). Ghi lại mọi cải tiến, chỉnh sửa làm từ 05/10/2026: cái gì
> **thêm**, cái gì **sửa**, cái gì **bỏ**, và đã kiểm chứng tới đâu.
> Nguyên tắc giữ nguyên: mọi xử lý hình ảnh chạy trên thiết bị hoặc trong trình duyệt, không gửi và
> không lưu ảnh khuôn mặt, chỉ gửi metadata JSON.

| | |
|---|---|
| **Phiên bản** | Version 3, dựa trên v2.2 (M9–M31). **Chưa deploy**: bản đang chạy vẫn là v2.2 |
| **Mã nguồn** | nhánh `DAQuan`, commit ngày 05/10/2026 (PR `DAQuan` → `main`) |
| **Web đang chạy (v2.2)** | https://driveguard-v2-production.up.railway.app |
| **Mốc trong lộ trình** | M32 (leo thang cảnh báo theo thời gian), M33 (nhịp "còn sống" và tổng quan đội xe), M34 (test hồi quy bằng trace), M35 (prototype thời lượng chớp), M36 (tiêu chí sẵn sàng pilot), M37 (chính sách dữ liệu, tự xoá theo thời hạn), xem [roadmap.md](roadmap.md) |

---

## 1. Tóm tắt thay đổi so với v2

| Loại | Thay đổi | Mốc | Ngày |
|---|---|---|---|
| **Thêm** | Leo thang cảnh báo theo thời gian: cùng một lý do L1 báo lần thứ 3 trong 10 phút thì lần đó phát ở L2, lý do mới `repeated_l1` | M32 | 05/10 |
| **Thêm** | Nhịp "còn sống": thiết bị và `#/live` gửi trạng thái giám sát lên backend mỗi 30 s và ngay khi trạng thái đổi | M33 | 05/10 |
| **Thêm** | Backend: bảng `device_status`, `GET /api/v1/fleet`, biến `DG_DEVICE_OFFLINE_AFTER_S` | M33 | 05/10 |
| **Thêm** | Dashboard: tab "Đội xe" (đang hoạt động / mất liên lạc / đã kết thúc chuyến, cảnh báo trong ngày, sự kiện gần nhất) | M33 | 05/10 |
| **Sửa** | Vòng lặp còn chạy mà không có frame quá 10 s: backend được báo `stalled` thay vì coi như đang giám sát | M33 | 05/10 |
| **Thêm** | Test hồi quy trên 36 video dạng số: lệch sự kiện / cảnh báo / `drowsy_score` là `pytest` đỏ; công cụ `tools/regression_traces.py` | M34 | 05/10 |
| **Thêm** | Công cụ và báo cáo prototype thời lượng chớp mắt (`tools/blink_duration.py`, `eval/results/blink_duration_fl3d.md`) | M35 | 05/10 |
| **Bỏ** | Thêm `duration_ratio` (thời lượng chớp so với chính tài xế) vào `slow_blink_score`: prototype không tách được và trùng với `reopen_ratio` | M35 | 05/10 |
| **Thêm** | Trang tiêu chí sẵn sàng pilot `docs/pilot-readiness.md`; cột "Nhận định" trong bảng kết quả của README và `eval/results/report.md` | M36 | 05/10 |
| **Thêm** | Chính sách dữ liệu `docs/data-policy.md`; backend tự xoá cảnh báo sau 60 ngày, tổng kết chuyến sau 365 ngày; lệnh xoá dữ liệu một tài xế; `GET /api/v1/policy` | M37 | 05/10 |
| **Sửa** | Màn hình đồng ý đăng ký khuôn mặt ghi thời hạn lưu; dashboard có dòng nhắc không dùng một cảnh báo đơn lẻ để kỷ luật | M37 | 05/10 |

---

## 2. Thêm mới

### 2.1 Leo thang cảnh báo theo thời gian (M32)

**Vì sao:** mỗi luật có một mức cố định. Tài xế bị nhắc L1 "nên nghỉ sớm" nhiều lần trong ít phút mà vẫn
chạy tiếp thì lần nhắc sau không mạnh hơn lần trước.

**Hành vi mới (khối 12, `edge_agent/decision/alert_manager.py`):**
- Đếm các cảnh báo L1 **đã phát ra** theo từng lý do (`drowsy_score`, `trend`).
- Lần thứ `alert.l1_repeat_count` (3) của cùng một lý do trong `alert.l1_repeat_window_s` (600 s) được
  phát ở **L2**, giữ lý do gốc và thêm `repeated_l1`.
- Mức hiển thị là L2 trong `alert.fall_hold_s` (3 s) rồi về L1, không phát thêm cảnh báo. Lần L1 tiếp theo
  còn trong cửa sổ cũng là L2.
- Nghỉ đỗ xe (`context.rest_after_s`, 120 s) rồi chạy tiếp, hoặc "Đổi tài xế": đếm lại từ đầu.
- `l1_repeat_count: 0` là tắt.

**Giữ báo sai đơn lẻ không tăng:**
- Một hoặc hai L1 không đổi gì.
- L1 bị cooldown chặn (không có chuông) không được đếm.
- Hai lý do L1 khác nhau không cộng dồn.
- Cooldown L1 là 120 s nên 3 lần cần ít nhất 4 phút có dấu hiệu lặp lại.
- Cùng lý do đó thành L2 thật ngay sau khi nâng: không kêu lần hai (dùng chung cooldown L2).

**Hiển thị:**
- HUD: dòng chính "Đã nhắc nhiều lần: hãy dừng nghỉ" (đứng trước lý do gốc), âm báo L2.
- Dashboard: nhãn "Đã nhắc nhiều lần" cạnh lý do gốc. Loại sự kiện vẫn theo lý do gốc (`drowsiness`).
- Bảng tổng kết chuyến: tính là một cảnh báo L2 (vào luật "cảnh báo thường xuyên" của đánh giá chuyến).

**Kiểm chứng:**
- 9 test khối 12 bằng chuỗi mức giả, 1 test pipeline (nghỉ thì đếm lại), 1 test backend, 1 test frontend.
- Replay trace sẵn có (`fl3d_v2.pkl`, `yawdd_v2.pkl`, `--replay block5`) với luật bật và tắt
  (`--set alert.l1_repeat_count=0`): hai báo cáo giống hệt nhau, không cảnh báo nào bị nâng. Clip ngắn nên
  đây chỉ là kiểm tra "không làm đổi số cũ", không phải bằng chứng luật có ích.

### 2.2 Nhịp "còn sống" (M33, khối 14)

**Vì sao:** app bị hệ điều hành dừng, máy treo hay hết bộ nhớ thì backend không nhận gì nữa và cũng
không biết (FMEA dòng 3, 4). Dashboard không trả lời được "xe nào đang chạy, xe nào mất liên lạc".

**Nội dung một nhịp** (`build_heartbeat`): `ts`, `trip_id`, `state`, `moving` (xe đang chạy / đỗ, `null`
khi không biết tốc độ). Không có vị trí, không có số đo nào của tài xế.

| `state` | Nghĩa |
|---|---|
| `monitoring` | Đang giám sát |
| `unavailable` | Không thấy mặt khi xe chạy (FR-6) |
| `camera_lost` | Mất camera |
| `stalled` | Vòng lặp còn sống nhưng không có frame quá `publisher.heartbeat_stalled_s` (10 s) |
| `error` | Frame lỗi liên tục (M28) |
| `ended` | Tài xế đã kết thúc chuyến |

**Khi nào gửi** (`edge_agent/runtime.py`): mỗi `publisher.heartbeat_interval_s` (30 s), ngay khi `state`
đổi, và khi kết thúc chuyến. `TripRuntime.idle(clock)` giữ nhịp khi không có frame: thiết bị gọi trong
vòng lặp khi chưa đọc được frame, `#/live` gọi theo bộ hẹn giờ gửi dữ liệu (5 s).

**Cách gửi:**
- Chỉ nhịp mới nhất có giá trị nên **không vào hàng đợi offline**: giữ một bản trong bộ nhớ, gửi bằng
  một POST riêng (`{"device_id", "heartbeat"}`) trước các bản ghi. Mất mạng 2 giờ rồi có lại: gửi đúng
  một nhịp, không dồn 240 nhịp cũ.
- Thiết bị: `MetadataPublisher` (cùng nhịp lùi khi backend không trả lời). Web: `bridge.take_heartbeat`,
  `agent.ts` gửi sau các lô đang chờ; lỗi gửi nhịp không đụng tới các lô sự kiện.
- `heartbeat_interval_s: 0` là tắt.

### 2.3 Backend: lần cuối thấy và tổng quan đội xe (M33)

- Bảng mới `device_status`: `last_seen` (giờ máy chủ), và `trip_id` / `state` / `moving` từ nhịp mới nhất.
  Nhịp đến trễ có `ts` cũ hơn nhịp đã lưu thì không ghi đè.
- Mọi lô gửi lên (kể cả từ agent cũ không có nhịp) đều cập nhật `last_seen`.
- `GET /api/v1/fleet?since=&until=`: mỗi thiết bị đã đăng ký hoặc đã từng gửi dữ liệu (trình duyệt
  `web-<tài khoản>` không đăng ký trước) một dòng:

| `status` | Điều kiện |
|---|---|
| `online` | Có tin trong `DG_DEVICE_OFFLINE_AFTER_S` (mặc định 90 s = 3 nhịp) |
| `offline` | Im lặng quá hạn mà chưa kết thúc chuyến |
| `ended` | Nhịp cuối là `ended` |
| `never` | Đã đăng ký, chưa từng gửi gì |

  Kèm `alerts_by_level` (không tính sự kiện hệ thống) và `last_event` trong khoảng `since`–`until`.
- Phân quyền: quản lý / kỹ sư / admin thấy mọi xe; tài xế chỉ thấy thiết bị gắn `driver_id` của mình.
- Nhịp đi qua cùng lớp kiểm tra của lô sự kiện: trường lạ (kể cả toạ độ) bị từ chối 422.

### 2.4 Dashboard: tab "Đội xe" (M33)

- Cho quản lý, kỹ sư, admin. Tự làm mới mỗi 15 s.
- 4 ô: tổng số xe, đang hoạt động, mất liên lạc, cảnh báo hôm nay.
- Bảng: thiết bị, tài xế, liên lạc, lần cuối thấy, giám sát, chuyến, cảnh báo trong ngày theo mức, sự
  kiện gần nhất. Xe mất liên lạc xếp trên cùng; xe mất liên lạc hiện "Lần cuối: …" kèm trạng thái cuối.
- Lọc theo trạng thái liên lạc và theo ngày (ngày theo giờ máy người xem).
- Mọi trạng thái và lý do hiện bằng tiếng Việt, không hiện mã thô.

### 2.5 Test hồi quy bằng trace (M34)

**Vì sao:** một thay đổi ở khối 7 từng làm lệch nhẹ một số đánh giá (AUC chớp 0,624 → 0,623) mà không
test nào bắt được; chỉ thấy khi so báo cáo bằng tay.

- **Dữ liệu trong repo:** `tests/fixtures/regression/traces.npz` (563 KB): 36 video (8 FL3D, 12 YawDD, 16
  SUST), 17 763 frame, mỗi frame 14 con số đầu vào của khối 5, 7–12 (EAR, MAR, góc đầu, eyeBlink, độ sáng
  mặt, …). Không có ảnh.
- **Kết quả đã chốt:** `expected.json`: với mỗi video là số frame, số sự kiện theo loại, từng cảnh báo
  (frame, mức, lý do), mức cao nhất và `drowsy_score` ở 4 điểm. Bộ này có đủ L1, L2, L3, các sự kiện chớp
  / ngủ gật / ngáp / gục đầu / PERCLOS cao, và 30 video không có cảnh báo (để thấy báo sai mới).
- **Trong CI:** `tests/test_edge_agent/test_trace_regression.py` chạy cùng `pytest`, khoảng 3 s. Lệch là
  đỏ, thông báo ghi rõ video nào, lệch gì và lệnh để chốt lại.
- **Khi đổi ngưỡng có chủ đích:** `python tools/regression_traces.py update --reason "<mốc>: <lý do>"`
  trong cùng commit; lý do được lưu trong `expected.json` (có test bắt buộc).
- **Kiểm chứng:** đổi thử 4 ngưỡng (`risk.microsleep_l3_s`, `drowsiness.yawn.min_s`,
  `risk.distraction.off_road_s`, `risk.drowsy.l1`), lần nào test cũng đỏ.

### 2.6 Prototype thời lượng chớp mắt (M35)

Câu hỏi: có nên thêm `duration_ratio` (thời lượng chớp so với đầu chuyến của chính tài xế) cạnh
`reopen_ratio` không. Trả lời trên trace sẵn có `fl3d_v2.pkl`, không đổi engine.

| Câu hỏi | Kết quả |
|---|---|
| Đo được bao nhiêu lần chớp | 482 lần trong 47,2 phút (khối 7), trung vị 304 ms. Chỉ 5 / 44 video đủ 20 lần làm mốc + 5 lần để so |
| Chớp ở đoạn buồn ngủ có dài hơn không | Video có microsleep so với video không có: 310 so với 280 ms, AUC 0,54. Cùng video, gần microsleep (≤ 10 s) so với xa: 311 so với 296 ms, AUC 0,54 |
| EAR và eyeBlink có khớp không | Cùng bộ đếm offline: 1 178 lần trên EAR (trung vị 264 ms), 1 101 lần trên eyeBlink (199 ms); tương quan hạng của trung vị theo video 0,72 |
| Thời lượng có thêm thông tin so với thời gian mở mắt lại không | Không: Spearman 0,92 |

**Kết luận: không thêm `duration_ratio`.** Lưu ý khi đọc: FL3D không có nhãn "đoạn buồn ngủ" nên hai phép
so trên là cách thay thế; hai mốc quyết định (AUC ≥ 0,65, |rho| ≤ 0,8) được chọn sau khi đã xem sơ số
liệu; buồn ngủ trong bộ này là diễn. Chi tiết: `eval/results/blink_duration_fl3d.md`.

### 2.7 Trang tiêu chí sẵn sàng pilot (M36)

- [pilot-readiness.md](pilot-readiness.md): 24 tiêu chí, mỗi dòng có mục tiêu (kèm nguồn), số hiện có,
  trạng thái, việc cần làm. Hiện tại: 4 đạt, 6 một phần, 5 chưa đạt, 9 chưa đo / chưa có.
- Mục tiêu từ PRD, CLAUDE.md và hai quy định EU về cảnh báo buồn ngủ (2021/1341) và mất tập trung
  (2023/2590), đã đọc văn bản gốc. Hai quy định này không áp dụng cho thiết bị lắp thêm ở Việt Nam; chúng
  là mốc đo được, công khai, cho đúng loại hệ thống.
- Lộ trình 5 bậc có cổng; bảng những chỗ DriverGuard cố ý làm khác quy định EU.
- Bảng kết quả ở README và `eval/results/report.md` có thêm cột "Nhận định": số đó đạt hay chưa, đo trên
  máy nào.

### 2.8 Chính sách dữ liệu và tự xoá theo thời hạn (M37)

- [data-policy.md](data-policy.md): thu gì và không thu gì, dùng vào việc gì, ai xem được, giữ bao lâu,
  quyền của tài xế, căn cứ, việc của đơn vị triển khai.
- **Thời hạn lưu (mặc định, bật sẵn):**

| Dữ liệu | Thời hạn | Biến cấu hình |
|---|---|---|
| Cảnh báo, sự kiện hệ thống, phản hồi "Cảnh báo sai", mẫu theo phút | 60 ngày | `DG_RETENTION_EVENTS_DAYS` |
| Bản tổng kết chuyến | 365 ngày | `DG_RETENTION_SUMMARIES_DAYS` |

  Đặt 0 là không tự xoá. Backend xoá lúc khởi động và mỗi ngày một lần khi có thiết bị gửi dữ liệu.
- **Vì sao hai con số này:** Luật 91/2025/QH15 chỉ yêu cầu lưu "trong khoảng thời gian phù hợp với mục
  đích xử lý" (Điều 3). Mốc tham chiếu gần nhất tìm được là hướng dẫn của CNIL về định vị xe người lao
  động: 2 tháng, tối đa 1 năm. Là lựa chọn của nhóm, chưa có ý kiến pháp lý.
- **Xoá dữ liệu một tài xế** (nghỉ việc hoặc yêu cầu xoá):
  `python -m backend.manage delete-driver-data <mã tài xế> --yes`. Xoá ngay: `python -m backend.manage purge`.
- `GET /api/v1/policy` (không cần đăng nhập): hai con số đang cấu hình.
- Nguyên tắc **không kỷ luật chỉ từ một cảnh báo đơn lẻ**: ghi trong chính sách kèm lý do (số báo sai đã
  đo, các lúc không giám sát được), và hiện ở cuối mọi tab của dashboard.

---

## 3. Sửa đổi

### 3.1 Không có frame thì không còn bị coi là đang giám sát (M33)

Trước: trang `#/live` chạy nền hoặc luồng camera kẹt mà không báo mất camera thì backend không nhận gì
và không phân biệt được với một chuyến bình thường không có cảnh báo. Nay nhịp báo `stalled` sau 10 s
không có frame; tab "Đội xe" hiện "Không nhận khung hình: không giám sát".

### 3.2 Màn hình đồng ý ghi thời hạn lưu (M37)

Dòng thứ ba của màn hình "Đăng ký khuôn mặt" đổi từ "… Quản lý chỉ biết bạn đã đăng ký." thành "… Số
liệu cảnh báo tự xoá sau 60 ngày, bản tổng kết chuyến sau 365 ngày." Không thêm dòng mới vì màn hình đã
chật ở 1024×600. Hai con số lấy từ `RETENTION_DAYS` trong `frontend/src/lib/labels.ts`; một test Python so
chúng với mặc định của backend và với `docs/data-policy.md`.

---

## 4. Tương thích khi nâng cấp từ v2.2

- **Deploy backend trước, rồi mới tới agent.** Backend v2.2 từ chối trường `heartbeat` và lý do
  `repeated_l1` (422):
  - nhịp bị bỏ (thiết bị ghi một dòng cảnh báo vào log), sự kiện khác vẫn gửi được;
  - sự kiện L2 có `repeated_l1` bị backend cũ từ chối và mất.
  Bản web không gặp vì frontend và backend nằm chung một image.
- Database: bảng `device_status` tự tạo khi backend khởi động; không đổi bảng cũ.
- Agent cũ gửi lên backend mới: vẫn nhận; xe hiện "Đang hoạt động" khi có dữ liệu, cột giám sát ghi
  "Không rõ".
- Thiết bị đã có dữ liệu trước M33 nhưng chưa đăng ký trong bảng `devices` (trình duyệt) chỉ hiện ở tab
  "Đội xe" sau lần gửi đầu tiên với bản mới.
- Ngưỡng mới trong `config/thresholds.yaml`: `alert.l1_repeat_count`, `alert.l1_repeat_window_s`,
  `publisher.heartbeat_interval_s`, `publisher.heartbeat_stalled_s`. Chưa đưa lên tab "Ngưỡng".
- Web: phải build lại `#/live` (`npm run prepare-live`) để trình duyệt nhận code Python mới.
- **Tự xoá dữ liệu bật mặc định (M37).** Sau khi deploy, backend xoá cảnh báo / mẫu cũ hơn 60 ngày và
  bản tổng kết cũ hơn 365 ngày ngay lúc khởi động, không khôi phục được ngoài bản sao lưu. Bản ghi
  cũ nhất trong database trên máy dev là 25/09/2026, tức khoảng 24/11/2026 mới có bản ghi đầu tiên quá
  hạn; database đang chạy trên Railway chưa được kiểm tra. Muốn giữ tất cả: đặt `DG_RETENTION_EVENTS_DAYS=0` và `DG_RETENTION_SUMMARIES_DAYS=0` trước khi
  deploy.
- Test hồi quy (M34) mới chạy trên Mac ARM. Nếu CI (Linux x86) cho kết quả lệch ở mức làm tròn số thực,
  chạy `tools/regression_traces.py update` trên CI / Linux và ghi lý do.

---

## 5. Kiểm thử

| | v2.2 | v3 |
|---|---:|---:|
| Test Python | 585 | **657** |
| Test frontend | 50 | **56** |
| Test end-to-end (Playwright) | 3 | **3** (kịch bản thứ hai thêm bước xem tab "Đội xe") |

- Số v3 gồm cả 1 test của thay đổi "Lỗi gần nhất" trên `#/live` làm sau v2.2 (chưa commit).
- M32: 9 test khối 12, 1 test pipeline, 1 test backend, 1 test frontend.
- M33: 8 test runtime (nhịp đầu và theo chu kỳ, đổi trạng thái, mất camera, không có frame, frame lỗi,
  kết thúc chuyến, tắt, xe đỗ), 4 test publisher (gửi riêng, chỉ giữ nhịp mới nhất khi mất mạng, backend
  cũ, chặn dữ liệu giống ảnh), 3 test bridge web, 15 test backend (chưa từng kết nối, đến / ngắt / đến lại,
  ngưỡng từ cấu hình, kết thúc chuyến, nhịp đến trễ, agent cũ, đếm cảnh báo theo ngày, phân quyền tài xế,
  trình duyệt, nhịp sai định dạng), 3 test frontend.
- M34: 11 test (khớp kết quả chốt, 4 ngưỡng đổi đều bị bắt, độ phủ, fixture chỉ có số, mỗi lần chốt có lý
  do, các hàm chọn / so / lưu).
- M35: 9 test bằng chuỗi số giả (nội suy thời điểm cắt, bỏ nheo mắt và nhắm dài, khoảng trống, thang EAR
  và eyeBlink, gần / xa microsleep, tương quan hạng, khối 7 trên trace giả).
- M37: 10 test backend, 2 test frontend.
- `ruff check`, `ruff format --check`, `tsc`, `vite build` sạch.
- E2e chạy trên máy dev (Chrome, camera giả): `#/live` đăng nhập tài xế → tab "Đội xe" của quản lý hiện
  `web-an` "Đang hoạt động", kết thúc chuyến thì thành "Đã kết thúc chuyến".

---

## 6. Giới hạn đã biết

- **Chưa deploy, chưa thử trên thiết bị thật.** Nhịp trên thiết bị (`edge_agent.main`) mới qua test bằng
  chuỗi số giả và transport giả; đường web đã qua e2e.
- **Leo thang L1 → L2: ngưỡng tạm** (3 lần / 10 phút). Chưa dataset nào có chuyến đủ dài để đo.
- **L1 kéo dài liên tục không được tính là lặp lại.** Khối 12 chỉ phát L1 mới khi mức đã hạ rồi lên lại
  (có từ trước M32), nên `drowsy_score` nằm trong vùng L1 suốt 10 phút chỉ có một cảnh báo và không leo
  thang.
- **Tab "Đội xe" không có âm báo, không đẩy thông báo:** quản lý phải đang mở tab mới thấy xe mất liên
  lạc. Màn hình trực tiếp có âm báo thuộc việc "cảnh báo cần xác nhận, báo quản lý ngay" trong improvements.
- **Trang `#/live` chạy nền:** trình duyệt có thể giãn bộ hẹn giờ tới 1 phút, vẫn trong hạn 90 s nhưng sát;
  trang bị đóng băng hẳn thì hiện "Mất liên lạc" (đúng: không còn giám sát).
- **Tài xế trong xe vẫn không được báo khi tiến trình chết hẳn** (cần kênh cảnh báo vật lý, có trong improvements).
- **Giờ thiết bị sai** không ảnh hưởng `online` / `offline` (tính theo giờ máy chủ), nhưng nhịp có `ts`
  lùi về quá khứ sẽ không ghi đè trạng thái đã lưu.
- **Test hồi quy (M34):** 36 video là một mẫu nhỏ chọn từ chính các bộ đã dùng để chỉnh ngưỡng; nó bắt
  thay đổi hành vi, không chứng minh hành vi đúng. Không có cột lông mày (trace cũ) nên tín hiệu nhướn
  mày không được phủ; không có cờ điện thoại.
- **Prototype thời lượng chớp (M35):** kết luận chỉ đúng với FL3D (diễn, clip ngắn). Khối 7 đo được chưa
  tới một nửa số lần chớp mà bộ đếm offline thấy; chưa tìm hiểu nguyên nhân.
- **Chính sách dữ liệu (M37):** chưa có ý kiến pháp lý; chưa mã hoá database, chưa có nhật ký truy cập,
  chưa xuất được dữ liệu một tài xế, chưa xoá được tài khoản; bản sao lưu lúc deploy không tự xoá. Nếu
  đổi thời hạn bằng biến môi trường thì câu trên màn hình đồng ý vẫn ghi con số mặc định cho tới khi sửa
  `RETENTION_DAYS` và build lại.
- **Tiêu chí pilot (M36):** bảng phản ánh số đo tới 05/10/2026; phải cập nhật tay khi có số mới.
- Các giới hạn của v2 ([release-v2.md mục 8](release-v2.md)) vẫn còn nguyên.
