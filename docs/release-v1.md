# DriveGuard — Version 1

> Hệ thống giám sát tài xế: phát hiện **buồn ngủ** và **mất tập trung** qua camera, cảnh báo theo 4 mức **L0–L3**.
> Mọi xử lý hình ảnh chạy trên thiết bị hoặc trong trình duyệt. Không gửi và không lưu ảnh khuôn mặt, chỉ gửi metadata JSON.

| | |
|---|---|
| **Web** | https://driveguard-production-6b83.up.railway.app |
| **Chạy với camera trên trình duyệt** | https://driveguard-production-6b83.up.railway.app/#/live |
| **Phiên bản** | v1.0 (28/09/2026): backend + dashboard lên Railway · v1.1 (29/09/2026): thêm `#/live` chạy trên trình duyệt |
| **Image Docker** | `quanpk07/driveguard:v1.1` (cũng là `latest`), 72,6 MB |
| **Mã nguồn** | nhánh `main`, PR #5 và #6 |

---

## 1. Tổng quan

DriveGuard gồm 3 phần:

| Phần | Chạy ở đâu | Làm gì |
|---|---|---|
| **Edge agent** (xử lý camera) | Máy tính cạnh camera trên xe (Python), **hoặc ngay trong trình duyệt** (`#/live`) | Đọc camera, chạy các model pretrained, tính mức rủi ro, phát cảnh báo |
| **Backend** (FastAPI + SQLite) | Railway | Nhận sự kiện (metadata), quản lý tài khoản, thiết bị, ngưỡng |
| **Frontend** (React) | Railway, cùng domain với backend | HUD trong xe, dashboard theo vai trò, trang chạy camera trên trình duyệt |

Luồng 14 khối: camera → tiền xử lý → MediaPipe / YOLOv8n / CNN mắt → trích đặc trưng → nhánh buồn ngủ + nhánh mất tập trung → risk engine (+ ngữ cảnh xe, bộ nhớ chuyến đi) → quản lý cảnh báo → HUD + gửi metadata.

Chỉ dùng model pretrained, không train model mới:
- MediaPipe Face Landmarker: 3,8 MB.
- YOLOv8n: 12,9 MB.
- CNN trạng thái mắt Intel open-closed-eye: 46 KB.

---

## 2. Chức năng

### 2.1 Phát hiện

| Hành vi | Dấu hiệu | Kết quả |
|---|---|---|
| **Ngủ gật (microsleep)** | Mắt nhắm **sâu** liên tục (EAR theo mốc riêng từng người, xác nhận bằng eyeBlink của MediaPipe) | ≥ 1,5 s khi xe chạy → **L3** ngay |
| **Buồn ngủ tích luỹ** | PERCLOS 60 s, microsleep gần đây, ngáp, gục đầu → `drowsy_score` 0–100 | ≥ 40 → **L1**, ≥ 70 → **L2**. Ban đêm và khi lái hơn 2 giờ thì điểm được nhân 1,2 |
| **Nhìn lệch khỏi đường** | Góc yaw / pitch so với tư thế "nhìn đường" tự học | ≥ 2 s (≥ 1,5 s khi > 80 km/h) → **L2** |
| **Dùng điện thoại** | YOLOv8n (lớp "cell phone") trong vùng quanh mặt và ngực tài xế | ≥ 60% thời gian của 2 s gần nhất → **L2** |
| **Mất mặt** | Không thấy mặt khi xe đang chạy (gục xuống, che camera) | ≥ 3 s → **L2** |
| **Mệt mỏi tăng dần** | `drowsy_score` tăng đều trong 15 phút | → **L1** (gợi ý nghỉ) |
| **Mất camera** | Camera bị rút hoặc bị thu hồi quyền | HUD báo lỗi thiết bị, gửi sự kiện `camera_lost` / `camera_restored` |

### 2.2 Mức cảnh báo và HUD

| Mức | Ý nghĩa | HUD |
|---|---|---|
| **L0** | Tỉnh táo | Nền tối, khiên xanh. Ban đêm giảm sáng |
| **L1** | Chú ý | Viền và icon vàng, chuông nhẹ |
| **L2** | Cảnh báo | Khối trạng thái tô cam, câu hành động ("Nhìn về phía trước", "Bỏ điện thoại xuống") |
| **L3** | Nguy hiểm | Đỏ toàn màn hình nhấp nháy 1 Hz, chỉ còn "Mở mắt! Dừng xe nghỉ ngay". Còi lặp mỗi 1,5 s tới khi mở mắt |

- **Liếc là hiểu:** HUD được thiết kế để liếc 0,5 s là biết tình trạng. Mức càng cao, màn hình càng ít chữ.
- **Âm thanh:** mỗi loại cảnh báo có tiếng riêng (buồn ngủ, nhìn lệch, điện thoại, mất mặt, L3, mất camera), không cần nhìn màn hình.
- **Không chỉ dựa vào màu:** icon mức đổi hình tròn → tam giác → bát giác, luôn kèm chữ L0–L3.
- **Báo sai:** nút **"Cảnh báo sai"** dùng được trong 120 giây sau mỗi cảnh báo.

### 2.3 Chống cảnh báo sai

- **Mốc riêng từng người:** ngưỡng mắt tính theo mốc của từng tài xế, nên người mắt hẹp không bị báo nhắm mắt liên tục.
- **Loại trừ trường hợp giống nhắm mắt:** nheo mắt vì nắng, lúc nhìn xuống, lúc ngáp hay đang nói đều không bị tính là nhắm mắt.
- **Camera lắp lệch:** mốc "nhìn đường" tự hiệu chỉnh trong 5 giây đầu chuyến.
- **Theo ngữ cảnh xe:**
  - Xe dừng (< 5 km/h): tắt nhánh mất tập trung.
  - Bật xi-nhan: nhìn ngang không bị tính.
  - Đỗ xe ≥ 120 s: coi là đang nghỉ, không báo buồn ngủ.
- **Không nhấp nháy, không lặp:** một mức phải giữ đủ lâu mới báo, giữ mức một lúc trước khi hạ, và có cooldown.
- **HITL (con người điều chỉnh):**
  1. Tài xế bấm "Cảnh báo sai".
  2. Dashboard hiện tỷ lệ báo sai theo từng lý do.
  3. Kỹ sư chỉnh ngưỡng (có giới hạn min/max, backend kiểm tra tính nhất quán).
  4. Ngưỡng được lưu thành phiên bản mới kèm người sửa, và thiết bị tải về khi khởi động.

### 2.4 Vai trò và dashboard

| Vai trò | Được làm gì |
|---|---|
| **Tài xế** (`driver`) | HUD, bấm "Cảnh báo sai", xem sự kiện **của mình**, chạy `#/live` và lưu vào tài khoản |
| **Quản lý đội xe** (`manager`) | Nhật ký sự kiện, timeline mệt mỏi, thống kê toàn đội; xem ngưỡng (chỉ đọc) |
| **Kỹ sư** (`engineer`) | Như quản lý, cộng thêm **chỉnh ngưỡng** |
| **Quản trị** (`admin`) | Mọi quyền, tạo tài khoản, đăng ký thiết bị |

Dashboard (`#/dashboard`) có:
- **Nhật ký sự kiện:** lọc theo thời gian, mức, tài xế, chỉ hiện báo sai.
- **Timeline mệt mỏi:** `drowsy_score` theo phút, kèm các cảnh báo.
- **Ô thống kê** theo mức.
- **Tab Ngưỡng.**

Đăng nhập bằng JWT, mật khẩu băm scrypt, phân quyền kiểm ở backend.

---

## 3. Cách sử dụng

Có 3 cách chạy phần camera. Dashboard thì dùng chung cho cả 3.

### Cách A — Chạy ngay trên trình duyệt (khuyên dùng để thử)

Không cần cài gì. Dùng Chrome hoặc Edge trên máy tính có webcam.

1. Mở https://driveguard-production-6b83.up.railway.app/#/live
2. **Ai đang lái?** Đăng nhập (cảnh báo sẽ được lưu vào tài khoản), hoặc bấm **"Dùng thử không lưu"** (không gửi gì đi).
3. **Tình huống xe** (tốc độ giả lập):
   - Trong phố ban ngày: có lúc dừng đèn đỏ.
   - Cao tốc ban đêm, đã lái gần 2 giờ: dễ thấy L1/L2 nhất.
   - Xe đỗ: không cảnh báo mất tập trung.
4. Bấm **"Cho phép camera và bắt đầu"**, rồi cho phép camera khi trình duyệt hỏi.
5. Nhìn thẳng vào camera 10–20 giây đầu để hệ thống học mắt và tư thế đầu của bạn.
6. Màn hình HUD hiện ra. Khung nhỏ ở góc trái hiển thị camera của bạn (chỉ trên máy bạn), EAR, góc đầu, FPS và thời gian YOLO. Bấm **"Dừng camera"** để kết thúc.

Lần mở đầu tiên phải tải khoảng 60 MB (bộ xử lý Python, OpenCV, MediaPipe, ONNX Runtime, model). Các lần sau trình duyệt đã có cache.

### Cách B — Edge agent Python trên máy, HUD trên web

Dùng khi muốn chạy đúng bản trên thiết bị (có CLAHE và CNN mắt). Cần có repo và môi trường Python (xem `HowToUse.md`).

```bash
DG_DEVICE_KEY=<device key> python -m edge_agent.main --source 0 \
  --scenario config/scenarios/highway_night.yaml \
  --backend https://driveguard-production-6b83.up.railway.app --device-id <device id> \
  --hud-origin https://driveguard-production-6b83.up.railway.app
```

Sau đó mở `https://driveguard-production-6b83.up.railway.app/#/hud` trên **cùng máy**, và bấm Allow nếu Chrome hỏi quyền truy cập mạng cục bộ.

### Cách C — Gói cài đặt cho người khác (không cần repo)

1. Người dùng nhận file `driveguard-edge-v1.zip` (14 MB; build bằng `packaging/edge/build_bundle.sh v1`).
2. Cài Python 3.11 hoặc 3.12.
3. Chạy `./install.sh` (Windows: `install.ps1`).
4. Điền device ID và device key vào `edge.env`.
5. Chạy `./run.sh`. Trình duyệt sẽ tự mở HUD.

Hướng dẫn chi tiết cho người dùng cuối: [packaging/edge/README.md](../packaging/edge/README.md).

### Kịch bản demo nhanh

Dùng tình huống "Cao tốc ban đêm":
1. Nhìn thẳng 20 giây: **L0**.
2. Quay đầu sang ngang 2 giây: **L2 nhìn lệch**.
3. Ngáp 3 lần (há to miệng ≥ 1,5 s mỗi lần), rồi gục đầu nhanh 2 lần với mắt nhắm: **L1 buồn ngủ**.
4. Nhắm chặt mắt 2 giây: **L3 ngủ gật**.

Nếu chỉ muốn xem giao diện từng mức mà không cần camera, bấm **"Chạy mô phỏng"** trên HUD.

### Việc của admin

Dashboard chưa có màn hình tạo tài khoản, nên admin dùng `railway ssh`. Máy chạy lệnh cần có SSH key đã đăng ký bằng `railway ssh keys add`.

```bash
railway ssh -- python -m backend.manage create-user <tên> --role driver --driver-id <drv-xxx> --password '<mật khẩu mạnh>'
railway ssh -- python -m backend.manage create-device <cam-xxx> --driver-id <drv-xxx>   # in device key một lần
```

- Người dùng `#/live` chỉ cần tài khoản. Thiết bị của họ tự là `web-<tên đăng nhập>`.
- Cách B và C cần thêm device ID và device key, mỗi người một bộ riêng.

---

## 4. Những gì đã có trong v1

### 4.1 Chất lượng (đo offline trên dataset; chi tiết ở [eval/results/report.md](../eval/results/report.md))

| Phép đo | Kết quả |
|---|---|
| FL3D / NITYMED (47 phút lái đêm): microsleep ≥ 1,5 s đạt L3 | **78,9%** (75/95) |
| FL3D: microsleep ≥ 3 s được phát hiện | **100%** (11/11) |
| FL3D: precision cảnh báo L3 | **97,6%** (81/83) |
| FL3D: ngáp theo frame | precision 97,9%, recall 88,7%, FPR 0,3% |
| YawDD (319 video): ngáp | precision 100%, recall 82,5% |
| MRL Eye: CNN mắt | accuracy 99,4% (tập 4000 ảnh), 95,4% (tập test đầy đủ) |
| SUST-DDD: precision L3 | 84,6% (clip 10 s ngắn hơn thời gian khởi động PERCLOS nên recall thấp) |

### 4.2 Hiệu năng

| | Kết quả |
|---|---|
| Edge agent Python (Mac ARM, video 640×480) | **152 FPS**, latency p50 6,5 ms (yêu cầu ≥ 15 FPS) |
| `#/live` trên Chrome (máy Mac, camera giả từ clip thật) | **30 FPS** (bằng tốc độ camera), YOLO 172–178 ms mỗi lần |
| Logic khối 6–12 trong trình duyệt (Pyodide) | 0,15 ms mỗi frame |
| Server Railway (1 giờ demo) | CPU < 0,01 vCPU, RAM trung bình 20 MB (cao nhất 78 MB), p50 latency 5 ms |

### 4.3 Chạy trên trình duyệt (`#/live`)

- **Dùng lại đúng các thành phần của thiết bị:**
  - Cùng file model (MediaPipe Tasks JS, YOLO qua onnxruntime-web trong Web Worker).
  - **Cùng code Python** cho khối 6–12, chạy bằng Pyodide.
  - Ngưỡng vẫn lấy từ `config/thresholds.yaml`, cộng các ngưỡng kỹ sư đã chỉnh trên dashboard.
- **Khác bản thiết bị:**
  - Không có CLAHE (tăng tương phản).
  - Trạng thái mắt khi EAR không tin cậy dùng eyeBlink của MediaPipe thay cho CNN mắt. Riêng trường hợp đeo kính, CNN từng cho kết quả tốt hơn.
- **Sự kiện gửi bằng token đăng nhập:** `POST /api/v1/web/events`, gắn vào `driver_id` của chính người dùng.

### 4.4 Quyền riêng tư và bảo mật

- Frame chỉ nằm trong RAM của thiết bị hoặc trình duyệt, không bao giờ ghi ra đĩa, không gửi đi.
- Backend từ chối mọi payload có dạng ảnh hoặc base64. Database không có cột nào để chứa ảnh (có test riêng).
- Tài xế chỉ xem được dữ liệu của mình, và không thể gửi sự kiện thay người khác.

### 4.5 Triển khai

- **Railway**, project **DriveGuard**: một service, volume `/app/data` cho SQLite, HTTPS sẵn có.
- **Image Docker multi-stage:** Node build frontend → venv Python chỉ gồm thư viện backend → runtime slim. Server không chạy model nào.
- **Quy trình phát hành:**
  1. `docker build --platform linux/amd64 -f Dockerfile.railway`
  2. Push lên Docker Hub `quanpk07/driveguard:<tag>`.
  3. `railway service source connect --image ...`

### 4.6 Kiểm thử

- **434 test Python:** edge agent, backend, bridge web. Logic theo thời gian được test bằng chuỗi số giả, không cần video.
- **25 test frontend** (vitest). Ruff và typecheck sạch.
- **End-to-end trên Chrome** (camera giả từ clip ngủ gật SUST `d_325`): lên L3 và sự kiện vào database. Đã chạy trên máy, trong container và trên server Railway.

---

## 5. Giới hạn đã biết

- **Tốc độ xe là giả lập** (kịch bản CAN), chưa nối CAN thật.
- **Phát hiện điện thoại** chưa có dataset camera hướng mặt tài xế để đo đúng góc máy. Trên State Farm (camera bên hông), recall chỉ 2,1%.
- **Nhìn lệch** là nguồn báo sai chính, phần lớn khi tài xế quay đầu thật gần ngưỡng.
- **`#/live` chưa được thử** trên điện thoại, máy cấu hình yếu, Safari và Firefox. Chưa thử cầm điện thoại thật trước camera trên bản web.
- **Gói cài đặt** mới thử trên macOS, chưa thử Windows và Linux.
- **Quản trị:** chưa có màn hình tạo tài khoản và thiết bị trong dashboard, chưa có lệnh đổi mật khẩu.
- **Ngưỡng mới từ dashboard** chỉ áp dụng khi edge agent khởi động lại, hoặc khi bấm bắt đầu lại trên `#/live`.
- **SQLite chỉ có một luồng ghi.** Nếu số xe tăng lên hàng trăm thì nên chuyển sang Postgres.
- **Giấy phép:** YOLOv8n dùng AGPL-3.0. Nếu phát hành rộng rãi thì phải công khai mã nguồn theo giấy phép này.

## 6. Hướng tiếp theo (đề xuất)

- Màn hình quản lý tài khoản và thiết bị trong dashboard.
- Đo `#/live` trên điện thoại và máy yếu; thử phát hiện điện thoại thật trên web.
- Buổi demo với người dùng thật, để điền mục "User feedback" trong báo cáo đánh giá.
- Sửa thanh toán GitHub Actions của tổ chức để CI chạy lại.
