# Audit 4: khối 13 HUD, khối 14 Metadata publisher, lớp web / APK, backend và deploy

Ngày 08/10/2026, trên working tree của nhánh `DAQuan` (có thay đổi chưa commit, coi là trạng thái hiện tại). Chỉ đọc và
phân tích: không sửa code, config hay `eval/results`, không gọi tới backend thật. Phạm vi:

- Khối 13: `edge_agent/hud/` (`hud.py`, `server.py`), `frontend/src/hud/`.
- Khối 14: `edge_agent/io/publisher.py`, `edge_agent/io/remote_config.py`, phần ghi bản ghi của `edge_agent/runtime.py`.
- Lớp web: `edge_agent/web/bridge.py`, `frontend/src/live/`, `frontend/src/lib/api.ts`, `frontend/src/drive/`,
  cấu hình build (`vite.config.ts`, `package.json`, `playwright.config.ts`).
- Backend và deploy: `backend/`, `deploy/railway_app.py`, `Dockerfile*`, `docker-compose.yml`, `railway.json`.
- Khối ngoài phạm vi chỉ xét dataclass giao tiếp và chỗ nối (`ExternalVehicle.sample`, `DecisionResult`).

Cách kiểm:

- Đọc code, test và config. Grep toàn bộ `frontend/src` cho các API lưu trữ, ghi hình, log và vòng đời trang.
- Chạy test: 348 test Python của phạm vi (`tests/test_backend`, `test_publisher`, `test_runtime`, `test_web_bridge`,
  `test_hud_and_remote`, các file M41–M65) và 138 test vitest của `frontend/`: đều pass. Không chạy e2e (cần build, cần
  CDN và ghi vào `frontend/e2e/.cache`).
- "Thử trong audit": một script đặt ngoài repo gọi `backend.db` trên database tạm để kiểm ba ca lệch đồng hồ (mục M2).
- Không mở `#/live` trong trình duyệt, không có thiết bị đích. Mọi số đo thời gian được dẫn lại là của máy Mac dev.

Quy ước: "bản web" là code của `#/live`, cũng là code dự kiến được bọc thành APK. "Bản thiết bị" là `edge_agent.main`
chạy Python. Công sức: S dưới nửa ngày, M một đến hai ngày, L hơn. "Trùng" nghĩa là `docs/improvements.md`,
`docs/safety-fmea.md`, `docs/pilot-readiness.md` hoặc ba audit trước đã có; khi đó chỉ ghi phần bổ sung.

## 1. Tóm tắt

1. Không tìm thấy đường nào trong code của dự án đưa frame, canvas hay landmark xuống đĩa hoặc ra mạng; backend chỉ nhận JSON theo schema cấm trường lạ. Không có phát hiện Critical được chứng minh bằng code.
2. **Repo chưa có APK:** không có Capacitor, không có thư mục Android. Sản phẩm kiểm chứng được là một trang web tải từ Railway, lúc khởi động còn tải Pyodide và wasm của MediaPipe từ `cdn.jsdelivr.net` không có kiểm tra toàn vẹn. Đây là đường duy nhất mà code bên thứ ba chạm được vào camera và token (H3).
3. **High, an toàn:** trên HUD có ba nút một chạm làm ngừng hoặc che việc giám sát mà không hỏi lại, không tiếng (H1). Vòng lặp của bản web từng đứng nhiều phút trong 2 trên 4 lần chạy 10 phút và không có cơ chế tự hồi phục (H4).
4. **High, dữ liệu:** token đăng nhập hết hạn sau 60 phút; từ lúc đó mọi sự kiện, kể cả L3 và nhịp "còn sống", của bản web bị kẹt trong RAM và mất khi đóng trang (H2).
5. Medium và Low: bản web bỏ cả lô khi gặp một lỗi 4xx và không có hạn chờ khi gửi; backend sắp xếp và xoá theo đồng hồ của thiết bị (thử: xe đang chạy hiện "đã kết thúc chuyến", L3 không lên mục khẩn); không có giới hạn tốc độ nào; trang hỏi tốc độ 4 lần mỗi giây suốt chuyến; khoảng 15 hằng số nằm ngoài `thresholds.yaml`; phần JS của vòng lặp và của âm thanh chưa có test.

## 2. Bảng ràng buộc

### 2.1 Ràng buộc của CLAUDE.md

| Ràng buộc | Kết luận | Bằng chứng |
|---|---|---|
| Xử lý on-device | Đạt, kèm một phụ thuộc | Model chạy trong trang (`frontend/src/live/agent.ts:541`, `yolo.worker.ts:64-70`), Python chạy trong Pyodide. Server không chạy model (`Dockerfile.railway:1-3`). Phụ thuộc: runtime tải từ CDN lúc chạy (H3) |
| Frame chỉ ở RAM, không ghi đĩa | Đạt | Bản web: một thẻ `video` và hai canvas không gắn vào trang (`agent.ts:242-245`), `getImageData` (`agent.ts:521`, `604`). Grep `toDataURL`, `toBlob`, `MediaRecorder`, `captureStream`, `indexedDB`, `caches.`, `serviceWorker`: không có. Bản thiết bị: chỉ `cv2.imshow` (`edge_agent/main.py:331`); `tests/test_edge_agent/test_no_frame_writes.py` |
| Chỉ gửi metadata JSON | Đạt | `backend/schemas.py:111-112` (`extra="forbid"`, chuỗi tối đa 64 ký tự), `schemas.py:314-320` (quét ảnh và base64). Bản web thiếu lớp chặn phía thiết bị (M8) |
| Tối thiểu 15 FPS | Đạt trên Mac, có ngoại lệ; Không chắc trên thiết bị đích | Mac: 29,6–29,9 FPS (`eval/results/benchmark_live.md` mục 4). Ngoại lệ: 2 trên 4 lần chạy 10 phút của bản mới có phút 0 FPS (mục 5 của file đó, xem H4). QCM6125: chỉ có suy luận 10–13 FPS (`docs/improvements.md` phụ lục J), không còn cách đo |
| Không thêm model nặng vào vòng lặp chính | Đạt | YOLO chạy trong worker (`agent.ts:374`). Phần chuẩn bị ảnh cho YOLO vẫn ở luồng giao diện, 1,5–2,0 ms mỗi lần trên Mac (`agent.ts:599-604`; đã nêu ở việc 10) |
| Chỉ model pretrained | Đạt | `face_landmarker.task`, `yolov8n.onnx`; phạm vi này không có bước train |
| Ngưỡng nằm hết trong `thresholds.yaml` | Vi phạm một phần | Bảng ở M7: khoảng 15 hằng số thời gian và mức trong JS và Python |
| Mỗi khối một module, giao tiếp qua dataclass | Đạt | `HudState` / `HudConfig` (`edge_agent/hud/server.py:45-58`), `PublisherConfig` (`publisher.py:69-80`), `FrameStep` (`runtime.py:102-107`). Bản ghi khối 14 là `dict`, được backend kiểm bằng pydantic |
| Logic thời gian test bằng chuỗi số giả | Đạt ở Python; thiếu ở JS | `test_publisher.py` (25 test, đồng hồ giả), `test_web_bridge.py` (22 test). Chưa có test cho `flush`, `pollSim`, vòng lặp của `agent.ts` và các hiệu ứng âm thanh của `HudScreen.tsx` (M10) |
| Ưu tiên chống báo sai | Đạt một phần | Âm thanh hệ thống có riêng từng loại. Hở: mạng chập hơn 1 s làm kêu "mất tín hiệu xe" trên bản web (M3) |
| Comment và tên biến tiếng Anh | Đạt | Các file trong phạm vi; chuỗi giao diện tiếng Việt |
| Sản phẩm cuối là APK | Chưa có | `grep -ri capacitor` chỉ ra tài liệu; không có `android/`, không có `capacitor.config.*`. Việc đóng gói đã bỏ ngày 08/10 (`docs/improvements.md` mục "Mọi việc cần hub hoặc xe thật") |

### 2.2 Riêng tư: luồng dữ liệu rời thiết bị hoặc xuống đĩa

| # | Đường đi | Nội dung | Kết luận | Bằng chứng |
|---|---|---|---|---|
| 1 | Camera vào thẻ `video`, canvas, `ImageData` | Frame thô | Đạt: chỉ RAM | `agent.ts:310`, `520-521`; canvas tạo bằng `document.createElement`, không gắn vào DOM (`agent.ts:242-244`) |
| 2 | Luồng giao diện sang worker YOLO | Ảnh 640×640 dạng `Float32Array`, chuyển quyền sở hữu | Đạt: chỉ RAM | `agent.ts:604-608`; worker chỉ trả tensor đầu ra (`yolo.worker.ts:109-110`) |
| 3 | JS sang Python (Pyodide) | 478 landmark mỗi mặt, `eyeBlink`, độ sáng, độ nét | Đạt: không ảnh | `agent.ts:572-574`; `bridge.py` dựng `PreprocessedFrame` với ảnh rỗng `np.empty((0, 0, 3))` |
| 4 | Landmark hoặc hồ sơ đăng ký rời Python | Không có | Đạt | Sự kiện đăng ký chỉ mang thời lượng và số lần làm lại (`publisher.py:202-206`). Trạng thái HUD chỉ có EAR, MAR, yaw, pitch đã làm tròn (`bridge.py`, khối `state["measures"]`) và không được gửi đi |
| 5 | `localStorage` | Ba cờ: `dg.landmarks.delegate`, `dg.phone.provider`, `driverguard.live.tech` | Đạt | `agent.ts:188-197`, `LiveScreen.tsx:27-44` |
| 6 | `sessionStorage` | JWT, tên đăng nhập, vai trò, `driverId` | Đạt (không ảnh); lộ nếu có code lạ trong trang | `frontend/src/lib/api.ts:40-58`; xem H3 |
| 7 | IndexedDB, Cache API, service worker | Không dùng | Đạt | Grep không có kết quả trong `frontend/src` |
| 8 | File tải về từ trang | JSON dữ liệu của tài xế, JSON nhật ký "ép tay" | Đạt | `dashboard/MyDataCard.tsx:21`, `hud/HudPreview.tsx:163` |
| 9 | Console của trình duyệt, log của thiết bị | Tên lớp lỗi, vị trí code, traceback | Đạt | `bridge.py:230-241`, `agent.ts:498`, `main.py:307`. Thông điệp lỗi có thể chứa số (kích thước mảng), không chứa ảnh |
| 10 | Báo lỗi tự động, analytics | Không có | Đạt | Grep `Sentry`, `analytics`, `gtag`, `sendBeacon`: không có |
| 11 | Gửi lên backend | Sự kiện, mẫu mỗi phút, tổng kết chuyến, nhịp "còn sống" | Đạt | Schema từng trường ở bảng 2.3 |
| 12 | CDN `cdn.jsdelivr.net` | Trang chỉ tải về (GET). Code tải về chạy trong trang có camera và token | **Rủi ro, xem H3** | `agent.ts:33-34`, `163`, `203`; `frontend/dist/assets/index-*.js` chứa đúng hai URL này |
| 13 | Backend `/api/v1/drive/{code}` | Mã ghép 6 ký tự, 4 lần mỗi giây, kể cả chế độ "Dùng thử" | Không có dữ liệu tài xế; câu "không gửi gì đi" chưa chính xác (M3) | `agent.ts:696-707`; `LiveScreen.tsx:135`, `157` |
| 14 | Đĩa của thiết bị Python | `data/outbox.db`: JSON metadata chưa gửi | Đạt; file không được giới hạn quyền đọc (L2) | `publisher.py:293-316` |
| 15 | Màn hình | Ảnh camera hiện trong ô tự xem suốt chuyến và trong khung đăng ký | Không chắc | `LiveScreen.tsx:354`. Không có gì ngăn chụp màn hình, chia sẻ màn hình hay ghi hình của hệ điều hành; APK chưa có nên chưa có `FLAG_SECURE` |
| 16 | Test đầu cuối, công cụ đo | Playwright giữ trace khi test lỗi; CI tải báo cáo lên | Đạt | Camera là thiết bị giả của Chrome, landmark là số tổng hợp (`playwright.config.ts:2-3`, `23-24`). `bench/live.bench.mjs` phát một clip YawDD công khai, chỉ đọc số |
| 17 | Server HUD `127.0.0.1` | Trạng thái số, không ảnh | Đạt | `server.py:365` chỉ bind `127.0.0.1`; xem M6 về lệnh ghi |

### 2.3 Schema metadata: trường nào gắn với danh tính

| Trường | Ở đâu | Gắn với danh tính tới mức nào |
|---|---|---|
| `device_id` | Mọi lô | Bản web: `web-<tên đăng nhập>` (`api.ts:206-208`, `backend/app.py:120-122`), tức là tên tài khoản. Bản thiết bị: mã xe, backend gắn với `driver_id` |
| `driver_id` | Do backend gắn, không nằm trong payload | Trực tiếp. Tài xế chỉ đọc được của mình (`app.py:98-102`) |
| `trip_id` | Sự kiện, mẫu, tổng kết, nhịp | Giờ địa phương lúc bắt đầu chuyến, tới giây (`agent.ts:149-152`, `main.py:172`). Không định danh nếu đứng riêng |
| `ts`, `started_at`, `ended_at` | Mọi bản ghi | Thời điểm; cùng `speed_kmh` cho biết lịch di chuyển, không có vị trí |
| `level`, `reasons`, `drowsy_score`, `distraction_score` | Sự kiện | Hành vi và mức mệt của một người đã biết tên: nhạy cảm, không tái dựng được khuôn mặt |
| `metrics.*` (PERCLOS, `blink_rate`, `reopen_ratio`, `closed_duration`, `phone_kind`...) | Sự kiện | Số tổng hợp theo cửa sổ thời gian. Không có landmark, không có chữ ký khuôn mặt, không có embedding |
| `metrics.enroll_s`, `enroll_redo`, `enrolled` | Sự kiện hệ thống | Không định danh |
| `summary.minutes[]` | Tổng kết chuyến | Mỗi phút: điểm, mức cao nhất, xe có chạy không. Tối đa 1 441 dòng |
| `versions` | Sự kiện, nhịp | Phiên bản app, phiên bản ngưỡng, 8–16 ký tự hash của model |
| `heartbeat.perf` | Nhịp | Thời gian từng chặng, loại GPU, số luồng: mô tả máy, không mô tả người |

Không trường nào đủ để tái dựng khuôn mặt. Backend từ chối mọi trường ngoài danh sách (`schemas.py:112`), nên một lỗi
code đưa nhầm landmark vào payload sẽ bị trả 422 chứ không được lưu.

## 3. Phát hiện

### 3.1 Critical

Không có phát hiện nào được chứng minh bằng code. Hai mục có thể thành Critical khi lên thiết bị thật và hiện không
còn cách đo: FPS trên QCM6125 (bảng 2.1) và việc hệ điều hành dừng app khi chạy nền (FMEA dòng 4, đã có).

### 3.2 High

#### H1. Ba nút một chạm trên HUD làm ngừng hoặc che việc giám sát, không hỏi lại, không tiếng

- **Vấn đề:** "Kết thúc chuyến" và "Đổi tài xế" có hộp xác nhận, ba nút sau thì không.
- **Bằng chứng:**
  - Nút "Chạy mô phỏng" trên thanh trên của HUD thật (`frontend/src/hud/HudView.tsx:353-361`, hiện từ 640 px). Vào chế
    độ này màn hình chạy kịch bản 90 giây (`HudScreen.tsx:55-59`), còn kênh đẩy cảnh báo thật chỉ đăng ký ở chế độ
    `live` (`HudScreen.tsx:80-89`) và tiếng cảnh báo phát theo trạng thái đang hiện (`HudScreen.tsx:98-107`). Vòng lặp
    thật vẫn chạy nhưng tài xế không thấy và không nghe gì từ nó. Dấu hiệu duy nhất là một chip "Mô phỏng".
  - Liên kết "Dashboard" ngay bên cạnh (`HudView.tsx:362-364`). Trên `#/live`, đổi route làm `LiveScreen` bị gỡ và gọi
    `agent.stop()` (`LiveScreen.tsx:65`): camera tắt, không có tổng kết chuyến, không có nhịp `ended`
    (`agent.ts:726-738` không gọi `end_trip`).
  - Nút "Dừng camera" của ô tự xem, 36 px (`LiveScreen.tsx:414-423`, và `357` khi đang L3): cùng đường `stop()`.
- **Hậu quả:** một lần chạm nhầm lúc đang lái là hết giám sát hoặc thành cảnh báo giả, không có âm báo "ngừng giám
  sát". Backend chỉ thấy xe "mất liên lạc" sau 90 giây. Ở chế độ mô phỏng nhịp vẫn báo `monitoring`, nên quản lý cũng
  không biết.
- **Đề xuất:** bỏ hai nút "mô phỏng" và "Dashboard" khỏi HUD khi nguồn là thiết bị thật hoặc khi xe đang chạy (đã có
  `#/hud-preview` cho việc xem thử); "Dừng camera" đi qua cùng hộp xác nhận và cùng `endTrip` như "Kết thúc chuyến";
  rời trang khi chuyến chưa kết thúc thì phát âm `monitoring_stopped`.
- **Công sức:** S. **Tác động:** FPS không đổi; báo sai không đổi; đóng một trạng thái im lặng chưa có trong FMEA.
- **Trùng:** không. FMEA dòng 3 nói về vòng lặp treo, không nói về nút bấm.

#### H2. Token hết hạn sau 60 phút: bản web ngừng gửi mọi thứ và mất khi đóng trang

- **Bằng chứng:** `backend/settings.py:15` (`token_ttl_min` mặc định 60, tối đa 24 giờ); `.env.example:50` cũng là 60.
  `LiveAgent` giữ `session` nhận lúc bắt đầu và không bao giờ làm mới (`agent.ts:259`, `645-676`). Gặp 401, lô đầu hàng
  không bị bỏ và cũng không gửi lại được (`agent.ts:668`), nên mọi lô sau xếp phía sau nó; nhịp "còn sống" cũng bị giữ
  (`agent.ts:687`). Hàng đợi chỉ nằm trong RAM (`agent.ts:235`).
- **Hậu quả:** chuyến dài hơn phần còn lại của token thì từ phút đó backend không nhận sự kiện nào, kể cả `unresponsive`,
  `repeated_l3`, `no_answer`. Tab "Đội xe" hiện xe "mất liên lạc". Tài xế chỉ thấy một dòng chữ 12 px trong ô tự xem
  (`LiveScreen.tsx:393`), và dòng này bị ẩn khi đang L3. Đóng trang là mất hết; cuối chuyến bản tổng kết báo "gửi thất
  bại". Cảnh báo tại chỗ không bị ảnh hưởng.
- **Đề xuất:** thiết bị trên xe nên dùng khoá thiết bị như bản Python, không dùng phiên đăng nhập của người. Nếu giữ
  JWT: làm mới token trước hạn (`expiresAt` đã có ở `api.ts:88`), và khi 401 thì hiện trạng thái rõ trên HUD kèm nút
  đăng nhập lại mà không dừng vòng lặp.
- **Công sức:** M. **Tác động:** FPS và báo sai không đổi.
- **Trùng:** không. Việc 13 (hàng đợi offline) không giải quyết: token hết hạn thì hàng đợi trên đĩa cũng không gửi được.
- **Không chắc:** giá trị `DG_TOKEN_TTL_MIN` trên Railway. Kiểm bằng cách đọc biến môi trường của dịch vụ.

#### H3. Runtime tải từ CDN chạy trong trang có camera và token, không kiểm tra toàn vẹn, không có CSP

- **Bằng chứng:** `agent.ts:163` nạp `pyodide.mjs` bằng `import()` từ `cdn.jsdelivr.net`; `agent.ts:169` tải thêm
  `numpy`, `pyyaml`, `sqlite3`; `agent.ts:203` lấy wasm của MediaPipe từ cùng CDN. Không có SRI (không dùng được với
  `import()` động). Backend không gửi `Content-Security-Policy` (grep trong `backend/`, `deploy/`: không có), chỉ có COOP
  và COEP (`backend/static.py:40-43`).
- **Hậu quả:**
  - Riêng tư: đây là đường duy nhất mà code không thuộc repo chạy cùng ngữ cảnh với `MediaStream` và với JWT trong
    `sessionStorage`. CDN bị chiếm, hoặc một bản phát hành bị thay, thì code đó đọc được frame và gửi đi đâu cũng được
    vì không có CSP giới hạn nơi nhận. Ràng buộc "không gửi ảnh" lúc này dựa vào bên thứ ba.
  - Offline: không có mạng lúc khởi động thì không giám sát được. File của chính trang (model, `edge_agent.zip`) đặt
    `Cache-Control: no-cache` (`static.py:71-73`), tức mỗi lần mở đều phải hỏi lại server.
- **Đề xuất:** đưa cả hai runtime vào bản build. `pyodide` 0.29.3 đã là devDependency (`package.json:33`) và gói
  `@mediapipe/tasks-vision` có sẵn thư mục `wasm`, nên chỉ cần chép sang `public/` và đổi hai URL. Sau đó thêm CSP với
  `script-src 'self' 'wasm-unsafe-eval'` và `connect-src 'self'`. Test e2e khi đó cũng hết phụ thuộc mạng.
- **Công sức:** M (bản build nặng thêm khoảng 15–20 MB). **Tác động:** FPS và báo sai không đổi; khởi động lần đầu
  không còn phụ thuộc CDN.
- **Trùng:** audit 1 mục M6 nêu phần offline; `docs/data-policy.md:219` nêu CDN thấy địa chỉ IP. Bổ sung ở đây: góc
  riêng tư và chuỗi cung ứng, thiếu CSP, cách đóng gói cụ thể, và FMEA dòng 15 đang ghi sai (mục 3.5).

#### H4. Vòng lặp bản web có thể đứng nhiều phút và không tự hồi phục

- **Bằng chứng:**
  - `eval/results/benchmark_live.md` mục 5: bản M67 đứng trong 2 trên 4 lần chạy 10 phút (không GPU: đứng 20 s, 70 s,
    rồi 5 phút cuối; có GPU: đứng từ giây 145 tới hết). Không lỗi, không crash, nguyên nhân chưa rõ.
  - Vòng lặp chỉ chạy khi `requestVideoFrameCallback` gọi (`agent.ts:479-503`). Không có đồng hồ canh nào phát hiện
    "không có frame trong N giây" để thử đường khác.
  - Lỗi ở phía JS (MediaPipe ném lỗi, mất ngữ cảnh WebGL, Pyodide chết) chỉ được `console.error` (`agent.ts:495-499`).
    Đường này không tới `frame_failed` của Python, nên không có sự kiện `agent_error`, và không có bước tạo lại model.
- **Hậu quả:** tài xế vẫn được báo: sau 3 giây HUD hiện "KHÔNG giám sát" kèm tiếng (`HudScreen.tsx:136`, `195-204`),
  backend nhận `stalled` sau 10 giây. Nhưng hệ thống cứ đứng yên cho tới khi có người tải lại trang, và lý do hiện ra
  là "không nhận dữ liệu từ camera" dù camera vẫn tốt.
- **Đề xuất:** thêm đồng hồ canh trong `agent.ts`: quá `capture.frame_timeout_s` (3 s, đã có trong YAML) không có frame
  thì tự lấy frame bằng timer, và nếu vẫn lỗi thì tạo lại `FaceLandmarker` với delegate CPU. Lỗi JS liên tiếp thì gọi
  một hàm của bridge để vào đúng đường `frame_failed`.
- **Công sức:** M. **Tác động:** FPS không đổi lúc bình thường; báo sai không đổi; giảm thời gian không giám sát.
- **Trùng:** việc 11 đề xuất `MediaStreamTrackProcessor` cho 0–3 % frame bị bỏ và FMEA dòng 3 nói về lỗi frame trong
  Python. Chưa có: đồng hồ canh, và lỗi phía JS không đi qua cơ chế M28.

### 3.3 Medium

#### M1. Bản web gửi không có hạn chờ, và bỏ cả lô khi gặp một lỗi 4xx

- **Bằng chứng:** `api.ts:60-79` gọi `fetch` không có `AbortSignal`; `publisher.timeout_s` (5 s) chỉ bản Python dùng
  (`publisher.py:362`). Trong `flush`, cờ `sending` chỉ hạ khi `fetch` trả về (`agent.ts:656-675`). Mọi mã từ 400 tới
  499 trừ 401 làm bỏ lô đầu hàng (`agent.ts:669-671`), tối đa 100 bản ghi (`bridge.py:59`). Bản Python gặp
  400 / 413 / 422 thì gửi lại từng bản ghi và chỉ bỏ bản bị từ chối, các mã khác thì thử lại (`publisher.py:59`,
  `515-536`).
- **Hậu quả:** kết nối 4G bị treo thì không lô nào được gửi nữa cho tới khi trình duyệt tự cắt. Một bản ghi lỗi (ví dụ
  trang cũ gửi lý do mà backend mới chưa biết, hoặc 403, 404, 429 thoáng qua) kéo theo tới 99 bản ghi tốt, có thể gồm L3.
- **Đề xuất:** `AbortSignal.timeout(publisher.timeout_s)`; chỉ bỏ ở 400 / 413 / 422 và khi đó tách từng bản ghi như
  bản Python; các mã còn lại thử lại có giãn cách.
- **Công sức:** S. **Tác động:** FPS và báo sai không đổi.
- **Trùng:** không (việc 13 chỉ nói lưu xuống IndexedDB).

#### M2. Backend sắp xếp, lọc và xoá theo đồng hồ của thiết bị

- **Bằng chứng (thử trong audit, database tạm):**
  - `backend/db.py:260-270`: nhịp chỉ được nhận khi `ts` không cũ hơn nhịp đã lưu. Thử: nhịp `ended` với đồng hồ nhanh
    một ngày, sau đó đồng hồ đúng lại và xe chạy chuyến mới: nhịp `monitoring` bị bỏ, tab "Đội xe" hiện "đã kết thúc
    chuyến" cho xe đang chạy (`app.py:125-132`).
  - `db.py:319-335`: mục "cần chú ý ngay" lọc theo `ts` của sự kiện so với giờ server. Thử: đồng hồ chậm 10 phút, L3
    `unresponsive` vừa nhận không hiện.
  - `db.py:340-355`: tự xoá theo `ts`. Thử: sự kiện mang năm 1970 bị xoá ngay lần dọn đầu tiên. Ngược lại, `ts` ở
    tương lai thì quá hạn lưu vẫn còn.
  - Nơi nhận không giới hạn độ lệch của `ts` (`schemas.py:163`); `received_at` đã được lưu nhưng không dùng cho ba việc trên.
- **Hậu quả:** thiết bị Android không có pin giữ giờ, chưa đồng bộ lúc khởi động, sẽ cho ra đúng các ca trên. Hệ quả là
  quản lý không thấy cảnh báo khẩn và thời hạn lưu bị sai theo cả hai chiều.
- **Đề xuất:** dùng giờ server cho thứ tự nhịp, cho cửa sổ khẩn và cho việc xoá; giữ `ts` của thiết bị để hiển thị; ghi
  độ lệch `received_at - ts` và từ chối hoặc đánh dấu khi quá một ngưỡng.
- **Công sức:** S. **Tác động:** FPS và báo sai không đổi.
- **Trùng:** không.

#### M3. Trang hỏi tốc độ 4 lần mỗi giây suốt chuyến, tới hai nơi

- **Bằng chứng:** `agent.ts:158` (`SIM_POLL_MS = 250`), `478`, `696-719`: mỗi nhịp gọi backend
  `/api/v1/drive/{code}`; không có điều khiển từ xa thì nhận 404 rồi gọi tiếp `http://127.0.0.1:8766/can`. Vòng này chạy
  cả khi chưa ai mở `#/drive`, và cả ở chế độ "Dùng thử · không lưu, không gửi gì đi" (`LiveScreen.tsx:135`).
- **Hậu quả:** khoảng 14 400 yêu cầu mỗi giờ mỗi xe tới backend và chừng đó lần gọi hỏng tới máy cục bộ; modem 4G
  không được nghỉ. Khi có điều khiển từ xa, một lần mạng chập hơn 1 giây (`agent.ts:161`) thành "mất tín hiệu xe" kèm âm
  báo to và một sự kiện hệ thống: báo động phiền do mạng, không phải do xe.
- **Đề xuất:** chỉ hỏi backend sau khi mã ghép đã được dùng, và giãn nhịp khi nhận 404; bản không phải bản xem thử thì
  tắt hẳn hai nguồn giả lập. Khi làm việc 12 (GPS) vòng này mất đi.
- **Công sức:** S. **Tác động:** bớt việc cho luồng giao diện, không đổi FPS đo được; giảm âm báo sai loại hệ thống.
- **Trùng:** việc 12 thay nguồn tốc độ nhưng không nêu chi phí của vòng hỏi hiện tại.
- **Không chắc:** Chrome mới có hỏi quyền "truy cập mạng cục bộ" khi trang công khai gọi `127.0.0.1` không. Kiểm bằng
  cách mở bản deploy trên Chrome hiện hành và xem có hộp hỏi quyền không.

#### M4. Không có giới hạn tốc độ nào; kênh điều khiển xe không xác thực có thể tắt mọi cảnh báo

- **Bằng chứng:** grep `rate`, `429`, `throttl` trong `backend/` và `deploy/`: không có. `PUT` và `GET`
  `/api/v1/drive/{code}` không cần đăng nhập (`app.py:290-302`). Bộ nhớ giữ tối đa 500 mã, quá thì bỏ mã cũ nhất
  (`backend/drive_link.py:28`, `33-38`). `/auth/login` không giới hạn số lần thử (`app.py:313-320`); chỉ có scrypt làm chậm.
- **Hậu quả:**
  - Ai biết mã 6 ký tự đang hiện trên màn hình thì đặt được tốc độ 0. Với `risk.drowsy.stationary_max_level: 0` và
    nhánh mất tập trung tắt dưới 5 km/h, mọi cảnh báo tắt mà HUD vẫn hiện bình thường.
  - Gửi 500 mã bất kỳ đẩy hết mã đang dùng ra khỏi bộ nhớ: mọi phiên `#/live` có điều khiển từ xa chuyển sang "mất tín
    hiệu xe".
  - Dò mật khẩu và dò mã không bị chặn.
- **Đề xuất:** giới hạn tốc độ theo địa chỉ cho `/auth/login` và `/api/v1/drive/*`; mã ghép chỉ ghi được bởi phiên đã
  mở nó (token ngắn hạn do `#/live` cấp). Đường này không được có mặt trong bản chạy trên xe.
- **Công sức:** S đến M. **Tác động:** FPS và báo sai không đổi.
- **Trùng:** `docs/data-policy.md` ghi `#/drive` không cần đăng nhập và không mang dữ liệu tài xế. Chưa có: hệ quả an
  toàn (tắt cảnh báo), việc đẩy mã, và thiếu giới hạn tốc độ.

#### M5. Bảo mật cơ bản của bản deploy

- **Bằng chứng và hậu quả:**
  - Container chạy bằng root: `Dockerfile.railway` không có `USER` (so với `Dockerfile:20-28` của app mẫu thì có).
  - Thư viện Python không ghim phiên bản (`Dockerfile.railway:19-21` dùng `>=`), image nền không ghim digest: hai lần
    build cho hai bản khác nhau.
  - `--forwarded-allow-ips='*'` (`Dockerfile.railway:58`): mọi nguồn đều đặt được `X-Forwarded-For`. Hiện chưa có gì dựa
    vào địa chỉ khách; sẽ thành lỗ hổng ngay khi thêm giới hạn tốc độ theo địa chỉ ở M4.
  - Không có header bảo mật (CSP, `X-Content-Type-Options`, HSTS); Swagger mở công khai ở `/docs` (`README.md:205`).
  - Thiếu `DG_JWT_SECRET` thì backend tự sinh khoá và vẫn chạy (`app.py:221-224`): mỗi lần khởi động lại mọi phiên chết,
    cộng với H2 thành mất dữ liệu.
  - CORS: danh sách origin cụ thể, không dùng cookie (`app.py:271-276`): ổn.
  - Secret trong repo: `.env` được bỏ qua (`.gitignore:16`), `git ls-files` chỉ có ba file `.example`; `.dockerignore`
    và `.railwayignore` loại `.env` và mọi file database: ổn.
- **Đề xuất:** thêm `USER`, ghim phiên bản bằng file khoá, giới hạn `forwarded-allow-ips` về proxy của Railway, tắt
  `/docs` ở bản deploy, từ chối khởi động khi thiếu `DG_JWT_SECRET` nếu có biến đánh dấu môi trường thật.
- **Công sức:** S. **Tác động:** không.
- **Không chắc:** database trên Railway có nằm trên volume bền không (`docs/data-policy.md:150` cũng ghi chưa kiểm
  chứng). Kiểm trong cấu hình dịch vụ.

#### M6. Server HUD của bản thiết bị nhận lệnh ghi từ mọi trang web đang mở trên máy

- **Bằng chứng:** `edge_agent/hud/server.py:283-292` chỉ thêm header CORS, không từ chối yêu cầu có `Origin` lạ.
  `POST /end-trip` không cần thân (`server.py:316-324`); `POST /vehicle` đọc JSON mà không kiểm `Content-Type`
  (`server.py:332-340`), nên là "yêu cầu đơn giản", trình duyệt gửi đi mà không hỏi trước.
- **Hậu quả:** một trang web bất kỳ mở trên cùng máy có thể kết thúc chuyến (vòng lặp dừng, `main.py:248-250`), đổi tài
  xế (mất hồ sơ đăng ký), hoặc trả lời hộ "Bạn còn ở đó không?". Rủi ro thấp trên hub chỉ mở HUD; có thật trên máy dev.
- **Đề xuất:** từ chối `POST` khi `Origin` có mặt mà không thuộc danh sách cho phép, và đòi `Content-Type:
  application/json`.
- **Công sức:** S. **Tác động:** không.
- **Trùng:** không.

#### M7. Hằng số nằm ngoài `thresholds.yaml`

| Hằng số | Giá trị | Ở đâu | Ghi chú |
|---|---:|---|---|
| `STALE_S` | 3 s | `frontend/src/hud/HudScreen.tsx:15` | Quyết định lúc nào báo "không giám sát"; trùng nghĩa với `capture.frame_timeout_s` |
| `POLL_MS` | 300 ms | `HudScreen.tsx:14` | Đã nêu ở việc 9 |
| `CHIME_TO_VOICE_MS` | 700 ms | `HudScreen.tsx:11` | |
| Hạn chờ một lần hỏi trạng thái, số lần lỗi thành "mất kết nối" | 1 000 ms, 3 | `HudScreen.tsx:61`, `71` | |
| `ALARM_REPEAT_S`, `PRESENCE_REPEAT_S` | 1,5 s, 2,0 s | `frontend/src/hud/chime.ts:55`, `58` | Nhịp lặp còi L3 và câu hỏi |
| `GAIN` theo mức | 0,12 / 0,25 / 0,35 | `chime.ts:60` | Độ to từng mức; tiêu chí C5 của pilot-readiness chưa đo |
| Mốc màu đỏ của ô "mắt" | 1,5 s | `frontend/src/hud/hudModel.ts:246` | Chép tay `risk.microsleep_l3_s`; đổi YAML thì HUD lệch |
| `EYES_SHOWN_CLOSED_S` | 0,5 s | `hudModel.ts:240` | Chép tay `drowsiness.blink_max_s` |
| `SIM_POLL_MS`, `REMOTE_FRESH_S` | 250 ms, 1,0 s | `agent.ts:158`, `161` | Comment tự ghi "same as context.vehicle_signal_stale_s"; không có test giữ hai số bằng nhau |
| `MAX_FRAME_AGE_MS` | 1 000 ms | `frontend/src/live/frameTime.ts:14` | |
| Yêu cầu camera | 640×480, 30 FPS | `agent.ts:302` | YAML có `capture.camera_width` 1280, `camera_height` 720 cho bản thiết bị; bản web không đọc |
| `MAX_RECORDS_PER_BATCH` | 100 | `edge_agent/web/bridge.py:59` | Bản thiết bị dùng `publisher.batch_size` 20 |
| `DELIVERED_KEEP`, thời gian chờ luồng dừng | 64, `timeout_s + 2.0` | `publisher.py:66`, `454` | |
| `MAX_BODY`, `END_TRIP_WAIT_S`, số cảnh báo giữ lại | 1 024, 10 s, 10 | `server.py:40-42`, `61` | |
| Nhịp hỏi bộ giả lập của bản thiết bị | 0,2 s | `edge_agent/context/can_sim.py:237` | Ngoài phạm vi, ghi để đối chiếu với 250 ms của web |

- **Hậu quả:** phần lớn là hằng số giao diện. Ba dòng có tác động thật: `STALE_S` (thời gian im lặng trước khi báo),
  hai mốc chép tay trong `hudModel.ts` (HUD nói khác luật khi YAML đổi), và `GAIN`.
- **Đề xuất:** đưa `STALE_S`, hai nhịp lặp và `GAIN` vào mục `hud:` của YAML và gửi qua `settings()` như các số khác
  (`bridge.py`, hàm `settings`); hai mốc của `hudModel.ts` lấy từ snapshot như `score_l1` / `score_l2` đã làm.
- **Công sức:** S. **Tác động:** không.
- **Trùng:** việc 9 nêu `POLL_MS`. Phần còn lại chưa có.

#### M8. Bản web không có lớp chặn ảnh phía thiết bị; hai danh sách từ cấm lệch nhau

- **Bằng chứng:** `check_metadata_only` chỉ được gọi trong `MetadataPublisher` (`publisher.py:422`, `430`). Bản web đưa
  bản ghi thẳng vào danh sách (`bridge.py`, hàm `_queue`) rồi gửi. Danh sách từ cấm của thiết bị (`publisher.py:60`)
  thiếu `jpg`, `base64`, `b64`, `video`, `blob`, `face_crop` so với của backend (`schemas.py:58-75`).
- **Hậu quả:** chưa có rò rỉ: backend vẫn từ chối. Nhưng câu "thiết bị chặn trước khi gửi" (`docs/pilot-readiness.md`
  dòng D1) chỉ đúng cho bản Python, và trên bản web một payload sai sẽ rời máy trước khi bị từ chối.
- **Đề xuất:** gọi `check_metadata_only` trong `WebAgent._queue`; dùng chung một danh sách từ cấm.
- **Công sức:** S. **Tác động:** dưới 0,1 ms cho mỗi bản ghi, không theo frame.
- **Trùng:** không.

#### M9. HUD: bố cục cho màn hình dọc chưa kiểm, và ảnh camera hiện suốt lúc lái

- **Bằng chứng:**
  - `frontend/src/hud/HudStage.tsx:11-14`: bố cục 1280×800 chỉ dùng khi màn hình ngang (rộng từ 1 024 px, tỉ lệ từ 1,2).
    Màn hình zin của VF e34 là 10 inch đặt dọc (`docs/improvements.md` phụ lục J), khi đó HUD rơi về bố cục xếp chồng
    của điện thoại. Test chỉ có một ca cho nhánh này (`m58.test.ts:110`, cỡ 390×844).
  - Ô tự xem luôn hiện ảnh camera động, trừ lúc L3 (`LiveScreen.tsx:354`), kèm chữ 12 px.
  - Chế độ đêm chỉ làm mờ 20 % ở L0–L1 (`HudView.tsx:160`) và theo `context.night_hours` là 0–5 giờ: từ chập tối tới
    nửa đêm không được coi là đêm. Không đọc ánh sáng môi trường.
- **Hậu quả:** trên màn hình đích, kích thước chữ và vị trí nút là của bố cục chưa ai xem; video động trong tầm mắt là
  nguồn xao nhãng mà chính hệ thống đang đo.
- **Đề xuất:** ẩn ô tự xem khi xe chạy (chỉ hiện lúc đỗ và lúc đăng ký); thêm ca test và ảnh chụp cho màn hình dọc
  10 inch; tách khung giờ làm mờ của HUD khỏi `night_hours` của khối 10.
- **Công sức:** S đến M. **Tác động:** bớt một thẻ `video` phải vẽ, có lợi nhẹ cho FPS trên máy yếu (chưa đo); báo sai
  không đổi.
- **Trùng:** phụ lục J có "màn hình dọc" trong danh sách đã bỏ cùng APK; không nêu `stageScale`.
- **Không chắc:** Android box xuất hình ngang hay dọc lên màn hình xe. Chỉ thiết bị trả lời được.

#### M10. Phần JS của vòng lặp và của âm thanh chưa có test

- **Bằng chứng:** 15 file test vitest phủ `hudModel`, `tripModel`, `voice`, `measure`, `pace`, `perf`, `gpu`,
  `frameTime`, `sim`, `forcedLog`. Không có test cho `agent.ts` (`flush`, xử lý 401 / 4xx, `pollSim`, `stop`), cho
  `yolo.worker.ts` (lùi từ WebGPU về wasm), cho các `useEffect` phát tiếng của `HudScreen.tsx` (ví dụ: vào chế độ mô
  phỏng có còn nghe cảnh báo thật không). E2E có 4 kịch bản, không kịch bản nào tắt mạng, để token hết hạn hay làm
  camera rớt, và cần CDN để chạy (`playwright.config.ts:3`).
- **Hậu quả:** H1, H2 và M1 đều nằm đúng vùng này.
- **Đề xuất:** tách phần gửi của `LiveAgent` thành một lớp thuần (hàng đợi, trạng thái gửi, quy tắc bỏ hay giữ) và test
  bằng transport giả như `test_publisher.py`; thêm test thành phần cho `HudScreen` với nguồn giả.
- **Công sức:** M. **Tác động:** không.
- **Trùng:** không.

#### M11. Bản web không mở lại camera

- **Trùng audit 1 mục M2** (`agent.ts:474`, không có `getUserMedia` lần hai, không xử lý `mute`). Bổ sung: HUD khi đó
  hiện "Đang kết nối lại…" (`frontend/src/lib/labels.ts:431`), câu này chỉ đúng với bản thiết bị; trên bản web không có
  ai kết nối lại.
- **Công sức:** M (phần mở lại), S (phần chữ).

### 3.4 Low

- **L1. Định danh chuyến và thiết bị.** `trip_id` là giờ địa phương tới giây (`agent.ts:149-152`, `main.py:172`), bản
  tổng kết có khoá `(device_id, trip_id)` (`db.py:76`): đồng hồ sai hoặc đổi múi giờ có thể ghi đè chuyến cũ. Một tài
  khoản mở `#/live` trên hai máy là cùng một `web-<tên>`: nhịp của hai máy đè nhau. Đề xuất: thêm phần ngẫu nhiên vào
  `trip_id`. Công sức S.
- **L2. Outbox của bản thiết bị.** Mỗi lần `publish` chạy trên luồng của vòng lặp làm một `INSERT`, một `COUNT(*)`, một
  `commit` rồi thêm một `COUNT(*)` (`publisher.py:306-316`, `435`): trên bộ nhớ eMMC một lần ghi đồng bộ có thể mất
  hàng chục ms, đúng frame có cảnh báo (*chưa đo*). File `data/outbox.db` không được giới hạn quyền đọc như database của
  backend (`db.py:198-207`). Giãn cách thử lại không có phần ngẫu nhiên (`publisher.py:558-565`): cả đội xe thử lại cùng
  lúc sau khi backend sập. Công sức S.
- **L3. Hàng đợi của bản web không có trần** (`agent.ts:235`, `bridge.py` danh sách `_records`); `publisher.max_queue`
  không được dùng ở đây. Một chuyến 8 giờ offline chỉ khoảng 500 bản ghi nên chưa là vấn đề bộ nhớ. Nêu để việc 13 đặt
  trần khi làm.
- **L4. `sqlite3` được tải vào Pyodide** (`agent.ts:35`) chỉ vì `publisher.py` import nó ở đầu file; bản web không dùng
  outbox. Bỏ được một gói tải về nếu tách phần dựng bản ghi khỏi phần outbox. Công sức S.
- **L5. `event_id` là khoá duy nhất toàn cục** (`db.py:32`, `493-496`): sự kiện trùng id của thiết bị khác bị bỏ lặng
  lẽ. Xác suất trùng UUID4 không đáng kể; chỉ là điểm một thiết bị xấu có thể lợi dụng.
- **L6. Server HUD không kiểm header `Host`** (`server.py:309-313`): kỹ thuật DNS rebinding đọc được `/state`, chỉ gồm
  số. Công sức S nếu làm cùng M6.

### 3.5 Tài liệu lệch code

| Tài liệu | Ghi | Code |
|---|---|---|
| `docs/safety-fmea.md:306` (dòng 15) | Hub mất mạng: "giám sát và cảnh báo chạy offline, không ảnh hưởng" | Bản web cần CDN và server lúc khởi động (H3). Chỉ đúng khi trang đã chạy rồi mới mất mạng |
| `docs/improvements.md:613` (việc 12) | "Không có tốc độ thì khối 10 coi là đang chạy" | Chưa từng có số đọc nào thì là đỗ, 0 km/h (`ExternalVehicle.sample` trong `can_sim.py`; `thresholds.yaml:453-456`; `LiveScreen.tsx:179-181`). Trên bản web không có bộ giả lập thì không có cảnh báo nào |
| `docs/safety-fmea.md:79`, `145`, `220` | Liên kết `improvements.md#viec-apk` | Anchor không còn trong `improvements.md` |
| `README.md:12`, `docs/architecture_diagram.md:222` | Sản phẩm cuối là APK bọc code web (Capacitor) | Không có code APK; `improvements.md` ghi đã bỏ 08/10 và bản web là đầu ra |
| `README.md:11`, `docs/release-v3.md:12`, `edge_agent/main.py:115` | Ba địa chỉ Railway khác nhau | Không biết địa chỉ nào đang chạy |
| `docs/pilot-readiness.md` dòng D1 | "Thiết bị chặn trước khi gửi" | Chỉ bản Python (M8) |
| `frontend/src/lib/labels.ts:431` | Mất camera: "Đang kết nối lại…" | Bản web không kết nối lại (M11) |
| `LiveScreen.tsx:135`, `157` | "Dùng thử: không lưu, không gửi gì đi" | Vẫn hỏi backend mã ghép 4 lần mỗi giây và tải từ CDN (M3) |
| `edge_agent/hud/hud.py:1-6` | "HUD (minimal, M4)... full HUD is milestone M6" | HUD đầy đủ đã có từ lâu; docstring cũ |

### 3.6 FPS, khởi động, bộ nhớ, nhiệt và pin trên phần cứng đích

Không có số đo nào trên QCM6125 và từ 08/10 không còn cách đo. Những gì đọc được từ code và từ số của Mac:

- **FPS:** phụ lục J suy luận 10–13 FPS nếu model mặt chạy trên CPU. Phép tính của audit trên cùng giả định (chậm
  khoảng 7 lần mỗi nhân, theo Geekbench, không phải số wasm): MediaPipe 8,9 ms thành khoảng 62 ms, lấy frame và Python
  thêm 10–20 ms, tức 11–14 FPS, dưới mốc 15. Ngoài ra luồng giao diện còn gánh React (HUD hỏi trạng thái mỗi 300 ms, ô
  tự xem mỗi 500 ms, `LiveScreen.tsx:335`) và phần chuẩn bị ảnh YOLO 5 lần mỗi giây. Kết luận: **Không chắc, nghiêng về
  không đạt nếu không có GPU cho model mặt.** HUD có báo `low_fps` (`thresholds.yaml:585-589`), nên trạng thái này
  không im lặng.
- **WebGPU và luồng wasm:** code tự lùi về wasm khi không có adapter thật hoặc khi phiên WebGPU lỗi
  (`yolo.worker.ts:95-103`, `113-126`), có test cho phần chọn (`gpu.test.ts`). WebView của Android không cho trang cách
  ly nên wasm chỉ một luồng (phụ lục J, nguồn J4): ước lượng khoảng 1,2 s mỗi lần YOLO, quá hạn 0,6 s, nhánh điện
  thoại thành "không rõ" và được báo sau 10 s (M50). Đã có trong việc 10.
- **Khởi động:** trên Mac, sau M67, 2,1–2,7 s với bộ nhớ đệm trống và server cục bộ (`benchmark_live.md` mục 4); phép
  đo trước M67 là 6,7–9,1 s dù đã có bộ nhớ đệm (mục 3). Lần đầu tải khoảng 30 MB. Trên thiết bị đích qua 4G: chưa đo.
- **Bộ nhớ:** tiến trình của trang chiếm 725–1 078 MB lúc bắt đầu trên Mac (`benchmark_live.md` mục 5). Hai trong sáu
  lần chạy 10 phút kết thúc cao hơn lúc đầu 141 và 169 MB (746 lên 887, 782 lên 951), trong khi file ghi "mọi độ dốc
  đều âm". Mười phút không đủ để kết luận có rò hay không. Trên máy 4 GB, trang cỡ 1 GB là ứng viên bị hệ điều hành
  tắt (FMEA dòng 4).
- **Rò bộ nhớ nhìn từ code:** không thấy cấu trúc nào tăng theo frame. `PerfWindow`, `seenAlerts` (theo số cảnh báo),
  10 cảnh báo gần nhất của `HudState` (`server.py:65`) đều bị chặn hoặc tăng rất chậm. Mỗi frame cấp phát một
  `ImageData` 640×480 (1,2 MB) và mỗi lần YOLO một `Float32Array` 4,9 MB: áp lực lên bộ gom rác, không phải rò.
- **Nhiệt và pin:** trang dùng 109–137 % một nhân trên Mac khi YOLO chạy wasm, 32 % khi có WebGPU. Không có khoá giữ
  màn hình sáng (grep `wakeLock`: không có) và không xử lý `visibilitychange`: màn hình tắt hoặc app ra nền thì vòng lặp
  dừng. Bản web có báo tiếng khi vòng lặp dừng; trong WebView bị tạm dừng thì không (FMEA dòng 4, đã có).

## 4. Không kiểm tra được, và vì sao

| Điều chưa kiểm | Vì sao | Cách kiểm chứng |
|---|---|---|
| FPS, nhiệt, pin, bộ nhớ trên QCM6125 và trong WebView | Không có thiết bị (quyết định 08/10) | Chạy `frontend/bench/live.bench.mjs --duration` trên điện thoại cùng chip (Snapdragon 665) cho số CPU gần đúng |
| WebGPU trên Adreno 610, phiên bản WebView của Android 10–13 | Không có thiết bị | Mở `#/live`, bật "Chi tiết kỹ thuật", đọc `yolo_provider` và `gpu` |
| Hành vi khi app bị đưa ra nền hoặc bị thu hồi camera | Chưa có APK; không mở trình duyệt trong audit này | Trên Chrome Android: chuyển app, khoá màn hình, mở app camera khác, xem HUD và tab "Đội xe" |
| H1 chạy thật (chế độ mô phỏng có làm mất tiếng cảnh báo thật) | Kết luận từ đọc `HudScreen.tsx`, không chạy giao diện | Mở `#/live`, bấm nút mô phỏng, nhắm mắt 2 giây khi xe "chạy" |
| H2 chạy thật | Không gọi backend | Đặt `DG_TOKEN_TTL_MIN=1` trên backend cục bộ, chạy `#/live` 2 phút, xem dòng lỗi và hàng đợi |
| Cấu hình thật trên Railway (TTL token, secret, CORS, volume, địa chỉ đang chạy) | Quy tắc không gọi backend thật; không đọc được biến môi trường | Xem trang cấu hình dịch vụ |
| Vòng lặp đứng ở H4 có lặp lại không, do máy hay do code | `benchmark_live.md` ghi chưa tái hiện có chủ đích | Chạy lại `--duration 10m` nhiều lần, có ghi sự kiện của track camera |
| Rò bộ nhớ chậm | Chỉ có số 10 phút | Chạy 2–4 giờ, đọc bộ nhớ của trang mỗi phút |
| Độ to và tần số của âm báo trong cabin, đường âm thanh từ Android box tới loa xe | Cần thiết bị và xe (tiêu chí C5) | Đo bằng máy đo âm lượng ở ghế lái |
| Bố cục HUD trên màn hình dọc 10 inch, cỡ chữ ở khoảng cách lái | Không chạy giao diện | Ảnh chụp ở viewport dọc, ví dụ 800×1280 |
| Test e2e | Cần build, cần CDN, ghi vào `frontend/e2e/.cache` | `npm run e2e` (CI có chạy) |
| Toàn bộ test Python (993 theo audit 3) | Chỉ chạy 348 test của phạm vi | `pytest tests/` |
| Múi giờ của `time.localtime()` trong Pyodide (ảnh hưởng `night_factor`) | Ngoài phạm vi, chưa chạy trong trình duyệt | In `clock_hour` của snapshot và so với đồng hồ máy |
| Hộp hỏi quyền mạng cục bộ của Chrome (M3) | Phụ thuộc phiên bản trình duyệt | Mở bản deploy trên Chrome hiện hành |
