# Phân tích lỗi (FMEA): các trạng thái im lặng của DriverGuard

Tài liệu cho team và người review. Mỗi dòng là một lúc hệ thống **không cảnh báo được** dù tài xế có
thể đang buồn ngủ hoặc mất tập trung: vì sao, có tự biết không, tài xế và quản lý thấy gì, im lặng tối
đa bao lâu, test nào kiểm. Đối chiếu với code ngày 02/10/2026 (sau M21), mốc M22; dòng 1 cập nhật
theo M23, dòng 2 theo M26, dòng 3 và 9 theo M28.

Sản phẩm là **APK bọc code web, chạy trên hub gắn trên xe**; bản web chỉ để xem thử. Bản Python trên
thiết bị (`edge_agent.main`) dùng cùng logic khối 6–14 (`edge_agent/runtime.py`).

## Mức nghiêm trọng

| Mức | Nghĩa |
|---|---|
| **Cao** | Xe đang chạy, tài xế có thể buồn ngủ / mất tập trung thật mà không có cảnh báo; im lặng không giới hạn, hoặc hệ thống không tự biết mình đang im |
| **Vừa** | Im lặng có giới hạn, chỉ một nhánh bị tắt, hoặc nhánh khác che phần lớn |
| **Thấp** | Theo thiết kế khi xe đỗ / thời gian ngắn, hoặc chỉ ảnh hưởng quản lý (không ảnh hưởng cảnh báo tài xế) |

## Tổng quan

| # | Trạng thái im lặng | Mức | Tự phát hiện? | Tài xế được báo? | Im lặng tối đa | Có test? |
|---|---|---|---|---|---|---|
| 1 | [Trình duyệt còn chặn âm thanh](#1-am-thanh-chua-bat) | Vừa (M23, trước là Cao) | Có | Dải vàng to "chạm để bật" | Đến lần chạm đầu tiên vào HUD | Một phần |
| 2 | [Mất tín hiệu xe](#2-mat-tin-hieu-xe) | Vừa (M26, trước là Cao) | Có | Dải vàng + âm báo (lúc chạy và lúc đỗ); đang chạy thì vẫn giám sát | Không im; đỗ rồi chạy đi thì giám sát hạn chế tới khi có lại tốc độ | Có |
| 3 | [Vòng xử lý dừng hoặc treo](#3-vong-xu-ly-dung) | Vừa (M28, trước là Cao) | Có (HUD; backend khi lỗi frame) | Chữ + âm báo to | Lỗi frame: 1 s; tiến trình chết: backend không biết ngay | Có |
| 4 | [App bị Android dừng (APK)](#4-app-bi-android-dung) | **Cao** | Chưa | Chưa | Không giới hạn | Không (chưa có app) |
| 5 | [Mắt bị che mà vẫn đọc là mở (kính râm)](#5-mat-bi-che) | **Cao** *(chưa kiểm chứng)* | Không | Không | Không giới hạn | Không |
| 6 | [Gục ra khỏi khung, trước đó không thấy mắt nhắm](#6-guc-ra-khoi-khung) | Vừa (M44, trước là Cao) | Có (tạm ngưng sau 3 s, hỏi tài xế sau 8 s) | Có: "Bạn còn ở đó không?" kèm tiếng lặp lại | 18 s đến khi quản lý được báo (`no_answer`) | Có |
| 7 | [Tạm ngưng giám sát: mất mặt ≥ 3 s, hoặc mặt không đọc được ≥ 5 s khi chạy](#7-tam-ngung-giam-sat) | Vừa | Có, kèm lý do (M43) | Có (chữ nói rõ lý do + tiếng) | Đến khi thấy lại mặt / ảnh dùng được | Có |
| 8 | [Mất camera](#8-mat-camera) | Vừa | Có | Có (chữ + tiếng) | Đến khi camera về | Có |
| 9 | [FPS tụt kéo dài](#9-fps-tut) | Vừa | Có (M28) | Chip "Máy chậm" | Không im (vẫn giám sát, trễ hơn) | Có |
| 10 | [Mắt không đánh giá được (đầu quay / cúi nhiều)](#10-mat-khong-danh-gia-duoc) | Vừa | Có | Nhánh mất tập trung thay | Đến khi đầu về | Có |
| 11 | [Đầu chuyến: mốc chưa đủ dữ liệu](#11-dau-chuyen) | Thấp | Có | Không cần | 5 s – 5 phút tuỳ luật | Có |
| 12 | [Đứng yên / nghỉ](#12-dung-yen-nghi) | Thấp | Có | Theo thiết kế: 0 km/h không cảnh báo (M30) | Suốt lúc đỗ | Có |
| 13 | [Chưa đăng ký / đăng ký thất bại / đang đăng ký](#13-dang-ky) | Thấp | Có | Có (thẻ nhắc) | Bước nhắm mắt: ~2 s + 2 s | Có |
| 14 | [Cooldown chặn cảnh báo lặp](#14-cooldown) | Thấp | Có | HUD vẫn hiện mức | L1 120 s, L2 30 s, L3 không | Có |
| 15 | [Hub mất mạng giữa chuyến](#15-mat-mang) | Thấp | Có | Không cần | Không ảnh hưởng cảnh báo | Thiết bị có; app chưa |
| 16 | [Thiết bị: mặt tối hoặc ảnh xám, CNN mắt đọc là mở](#16-cnn-mat-toi) | **Cao** *(đo trên video biến đổi, chưa có dữ liệu thật)* | Không | Không | Không giới hạn | Không (có phép đo: `tools/light_study.py`) |
| 17 | [Model điện thoại không còn cho kết quả](#17-yolo-qua-han) | Vừa | Có (M50) | Có (chip trên HUD, không âm thanh) | 10 s rồi được báo; nhánh điện thoại tắt tới khi có lại kết quả | Có |

Không xét: trạng thái riêng của trình duyệt (tab chạy nền) vì web chỉ để xem thử. YOLO trả kết quả quá trễ
trước đây cũng không xét ("hub được chọn đủ mạnh"); từ M50 là dòng 17, vì bản web chạy YOLO chậm gấp 10 lần
bản thiết bị và hub chưa chọn.

## Đường cảnh báo bình thường (để so)

Tính từ cấu hình `config/thresholds.yaml`, **chưa đo trên video**. Đo thật là việc time-to-alert ở
[improvements.md](improvements.md#viec-prd).

| Dấu hiệu | Từ lúc bắt đầu đến cảnh báo |
|---|---|
| Nhắm mắt (microsleep) | `risk.microsleep_l3_s` 1,5 s, L3 không cần giữ thêm (`rise_confirm_s[3] = 0`) → **~1,5 s** |
| Nhìn khỏi đường | `off_road_s` 2,0 s (1,5 s khi ≥ 80 km/h) + `rise_confirm_s[2]` 0,5 s → **~2,5 s** (2,0 s) |
| Điện thoại gần mặt | `phone_ratio` 0,6 trên cửa sổ 2 s (~1,2 s) + 0,5 s → **~1,7 s**, cộng độ trễ YOLO (~5 lần / s) |
| `drowsy_score` ≥ 40 / 70 | Tuỳ PERCLOS 60 s, ngáp, gục; L1 giữ 1 s, L2 giữ 0,5 s |

---

## Chi tiết

<a id="1-am-thanh-chua-bat"></a>

### 1. Trình duyệt còn chặn âm thanh — Vừa (M23; trước là Cao)

- **Trước M23:** HUD khởi động tắt tiếng; chưa chạm "Bật âm thanh" thì mọi cảnh báo, kể cả còi L3, chỉ
  có hình, cả chuyến.
- **Từ M23:** âm thanh luôn bật, không còn nút tắt. `armAudio()` (`frontend/src/hud/chime.ts`) tạo âm
  thanh ngay khi HUD mở và bật ở **lần chạm / phím đầu tiên bất kỳ**. Phần còn lại: trình duyệt vẫn chặn
  cho tới lần chạm đó. `#/live` có sẵn lần bấm "Bắt đầu" nên có tiếng ngay; HUD trên thiết bị mở mà
  chưa ai chạm thì còn im.
- **Phát hiện:** có (trạng thái của audio context).
- **Tài xế thấy:** dải vàng to dưới thanh trên cùng, trên mọi màn hình kể cả L3: "Âm thanh cảnh báo chưa
  bật. Chạm vào màn hình để bật." Tiếng không bị dồn lại rồi phát cùng lúc khi được bật.
- **Quản lý thấy:** không gì.
- **Im lặng tối đa:** đến lần chạm đầu tiên vào HUD.
- **Test:** `lib.test.ts` ("reports sound as blocked where there is no audio, and plays nothing"); e2e
  chạy qua `#/live`. Chưa có test hiển thị dải nhắc.
- **Còn lại:** trong APK cho WebView phát âm thanh không cần chạm (*chưa kiểm chứng*), thuộc việc
  [Đóng gói app APK](improvements.md#viec-apk).

<a id="2-mat-tin-hieu-xe"></a>

### 2. Mất tín hiệu xe — Vừa (M26; trước là Cao)

- **Trước M26:** `ExternalVehicle` trả **0 km/h** khi không có số mới trong `context.vehicle_signal_stale_s`
  (1 s), kể cả khi xe đang chạy. 0 km/h là "đỗ": nhánh mất tập trung tắt ngay, buồn ngủ bị giới hạn L1,
  sau `rest_after_s` (120 s) tắt hết; không tiếng, không sự kiện.
- **Từ M26:**
  - Mất tín hiệu khi lần đọc cuối là **đang chạy** (≥ `context.stationary_kmh`): tốc độ thành "không biết"
    (`None`), khối 10 coi là đang chạy (`assume_moving_when_speed_unknown`), không bao giờ thành "nghỉ".
    Cả hai nhánh vẫn giám sát: microsleep vẫn L3, nhìn lệch vẫn L2.
  - HUD: dải xe hiện "Mất tín hiệu xe: vẫn giám sát như đang chạy" (vàng), tốc độ "–", âm báo to; có lại
    tín hiệu thì âm báo nhẹ.
  - Backend: sự kiện hệ thống `vehicle_signal_lost` / `vehicle_signal_restored`; bản tổng kết có
    `vehicle_signal_lost_s` (dashboard hiện ở dòng "Giám sát được").
  - Mất tín hiệu khi lần đọc cuối là **đang đỗ**: vẫn coi là đỗ, nhưng tài xế **cũng được báo** (dải vàng
    "Mất tín hiệu xe: coi như đang đỗ đến khi có lại tốc độ" + cùng âm báo) và có sự kiện. Xe chạy đi thì
    khi đồng hồ tốc độ có tín hiệu lại, hệ thống biết xe đang chạy và báo "có lại tín hiệu".
- **Còn lại:**
  - Đỗ, mất tín hiệu rồi chạy đi: trong lúc chưa có lại tốc độ, hệ thống vẫn coi là đỗ (tắt nhánh mất tập
    trung, buồn ngủ tối đa L1). Tài xế đã được báo mất tín hiệu từ lúc đỗ (chốt 02/10: chấp nhận).
  - Chưa từng có tín hiệu (không chạy công cụ): coi là đỗ, HUD hiện "Chưa có tín hiệu xe", không tiếng.
  - Âm báo cần âm thanh đã bật (dòng 1).
- **Im lặng tối đa:** không còn im lặng: mất tín hiệu lúc chạy hay lúc đỗ đều được báo. Đỗ rồi chạy đi khi
  chưa có lại tín hiệu thì giám sát bị hạn chế (như xe đỗ) tới khi có lại tốc độ.
- **Test:** `test_external_vehicle_follows_the_signal_and_is_lost_when_it_goes_stale_while_driving`,
  `test_external_vehicle_lost_while_parked_stays_parked`,
  `test_vehicle_signal_lost_while_parked_tells_the_driver_and_the_speed_coming_back_shows_driving`,
  `test_vehicle_signal_lost_while_driving_keeps_monitoring_and_tells_driver_and_backend` (5 phút mất tín
  hiệu ở 60 km/h, nhắm mắt vẫn L3, có sự kiện, tổng kết 299 s),
  `test_vehicle_signal_lost_and_restored_are_system_events`,
  `test_vehicle_signal_lost_time_is_kept_and_older_agents_may_omit_it`; frontend: cờ trên HUD, âm báo riêng.

<a id="3-vong-xu-ly-dung"></a>

### 3. Vòng xử lý dừng hoặc treo — Vừa (M28; trước là Cao)

- **Trước M28:** `main.py` chỉ bắt `KeyboardInterrupt`: một lỗi trong khối 2–14 làm thiết bị dừng hẳn. Web
  chỉ `console.error` rồi bỏ qua mọi frame. HUD hiện "Không nhận dữ liệu từ camera" / "Mất kết nối" sau 3 s
  nhưng không tiếng; backend không biết.
- **Từ M28:**
  - Thiết bị và web (`bridge.frame`) bắt lỗi từng frame và chạy tiếp; `TripRuntime.frame_failed`. Lỗi liên
    tục ≥ `hud.processing_error_s` (1 s): HUD hiện **"Lỗi xử lý: hệ thống đang KHÔNG giám sát"**, sự kiện
    `agent_error`; frame tốt tiếp theo: `agent_recovered`. Chỉ ghi tên lớp lỗi vào log trên máy.
  - HUD vào "Lỗi xử lý", "Không nhận dữ liệu từ camera" hoặc "Mất kết nối": **âm báo to** riêng
    (`monitoring_stopped`); hết thì âm "giám sát lại". Không kêu sau khi đã kết thúc chuyến.
- **Từ M33:** nhịp "còn sống" mỗi 30 s lên backend. Tiến trình chết hẳn (máy treo, hết bộ nhớ, app bị hệ
  điều hành dừng): sau 90 s tab "Đội xe" của dashboard hiện xe đó **"Mất liên lạc"**, khác với "Đã kết thúc
  chuyến". Vòng lặp còn sống mà không có frame: nhịp báo `stalled`.
- **Từ M71 (bản web):**
  - Trình duyệt ngừng gọi `requestVideoFrameCallback` quá `capture.frame_timeout_s` (3 s) khi trang đang ở
    trước mặt: vòng lặp tự lấy frame bằng timer cho tới khi trình duyệt gọi lại. Tab bị che thì không kéo
    (trình duyệt chỉ cho khoảng 1 frame / giây), nhịp vẫn báo `stalled` như trước.
  - Lỗi ở phía trang (MediaPipe, canvas, lời gọi sang Python) đi cùng đường `frame_failed` với lỗi trong
    Python: quá 1 s là "Lỗi xử lý" và `agent_error`. Trước đó chỉ là một dòng trong console.
  - Hai frame cách nhau quá `max_gap_s` (0,5 s) không còn bị nối thành một đợt: khối 7, 8 bắt đầu đếm lại,
    khối 12 xác nhận lại. Trước đó chớp mắt ở hai đầu một lần đứng 2 s cho còi L3, 7 s cho "không phản ứng".
- **Còn lại:** quản lý phải đang mở tab "Đội xe" mới thấy; chưa có âm báo hay thông báo đẩy (improvements:
  "cảnh báo cần xác nhận, báo quản lý ngay"). Bản web chưa tự tạo lại model mặt khi MediaPipe lỗi mãi; vòng
  lặp rất chậm (dưới 2 FPS) vẫn báo "đang giám sát" kèm `low_fps` dù không đợt nào đếm được. Tài xế trong xe vẫn không được báo khi tiến trình chết hẳn
  (improvements: "kênh cảnh báo vật lý").
- **Test:** `test_frames_failing_for_a_while_are_a_processing_error_then_recover`,
  `test_a_failing_frame_is_caught_and_a_lasting_failure_shows_on_the_hud`,
  `test_loop_health_events_are_system_events`; frontend: trạng thái "error", âm báo dừng giám sát. M71:
  `tests/test_edge_agent/test_m71_frame_gaps.py`, `test_a_frame_failing_in_the_page_takes_the_same_path`,
  `frontend/src/live/watchdog.test.ts`, e2e "the loop recovers by itself".

<a id="4-app-bi-android-dung"></a>

### 4. App bị Android dừng (APK) — Cao

- **Nguyên nhân:** app chạy nền, tắt màn hình, hệ điều hành tắt app để lấy bộ nhớ: camera ngừng.
- **Phát hiện:** chưa có (chưa có app).
- **Hướng sửa:** chế độ kiosk, giữ màn hình sáng; bắt sự kiện vòng đời của app (tạm dừng / tiếp tục) →
  `monitoring_unavailable` + tiếng; lần mở sau gửi sự kiện "chuyến bị ngắt". Thuộc việc
  [Đóng gói app APK](improvements.md#viec-apk).

<a id="5-mat-bi-che"></a>

### 5. Mắt bị che mà vẫn đọc là mở (kính râm) — Cao, chưa kiểm chứng

- **Nguyên nhân:** MediaPipe vẫn trả landmark mắt khi đeo kính râm (đoán theo hình mặt). Khối 5 chỉ gọi
  CNN khi trời tối, camera IR hoặc hai mắt lệch nhau (`eye_state`), nên EAR "đoán" có thể luôn ở mức mở.
  Khi đó PERCLOS, microsleep, chớp chậm đều im mà **hệ thống không biết mình đang im**. Chưa đo: dataset
  hiện có không có kính râm.
- **Phát hiện:** không có.
- **Hướng sửa (chưa thử):** không có lần chớp nào trong một khoảng dài khi vẫn thấy mặt → không tin trạng
  thái mắt, báo "không đọc được mắt"; hoặc model phân loại kính râm SGC (PINTO0309, MIT) đã ghi ở
  improvements. Chưa có dữ liệu để thử: NTHU-DDD không tải được, phiên tự ghi có kính râm đã bỏ (06/10). →
  việc "Phát hiện mắt bị che", đang hoãn; dòng này vẫn mở.

<a id="6-guc-ra-khoi-khung"></a>

### 6. Gục ra khỏi khung, trước đó không thấy mắt nhắm — Cao

- **Nguyên nhân:** khối 7 chỉ "mang theo" lần nhắm mắt qua lúc gục khi mắt đã nhắm ≥
  `head_drop.carry_min_closed_s` (0,5 s) trước đó. Gục nhanh / gục khi mắt không đọc được → mất mặt,
  sau 3 s thành tạm ngưng giám sát (dòng 7), không có cảnh báo.
- **Phát hiện:** có, như dòng 7.
- **Đã làm (M44):** tạm ngưng giám sát với lý do `no_face` (ảnh bình thường mà không thấy mặt) kéo dài
  `presence.ask_after_s` (5 s) thì HUD hỏi "Bạn còn ở đó không?" bằng cả màn hình và tiếng lặp lại mỗi 2 s.
  Chạm một lần bất kỳ đâu, hoặc mặt hiện lại, là xong. Không trả lời trong `presence.answer_s` (10 s): sự kiện
  `no_answer` gửi lên backend ngay, tab "Đội xe" đưa xe lên mục "Cần chú ý ngay" kèm tiếng; HUD chuyển sang
  còi L3 (người ngồi cạnh nghe được). Không hỏi khi camera bị che / lệch / ảnh xấu (lỗi của camera, dòng 7).
- **Từ M74:** mặt chập chờn không còn bị hỏi dồn. Đã hỏi rồi thì mặt phải hiện lại liền `presence.back_s` (1 s)
  mới coi là trở lại; sau một lần chạm thì `presence.reask_after_s` (60 s) sau mới hỏi lại. Mặt hiện một frame mỗi
  12 s: 10 lần hỏi trong 2 phút thành một. Đánh đổi: trong 60 s sau lần chạm, tài xế gục ra khỏi khung không được
  hỏi. Test: `tests/test_edge_agent/test_m74_alert_reminders.py`.
- **Còn lại:** bốn ngưỡng là tạm (chưa có số liệu tài xế rời khung có chủ ý trong bao lâu); tài xế bất tỉnh mà
  mặt vẫn trong khung, mắt mở thì ngoài khả năng của camera.
- **Test thêm:** `tests/test_edge_agent/test_m44_unresponsive.py` (hỏi, chạm, không trả lời, che camera thì
  không hỏi), `tests/test_backend/test_m44_urgent.py`; frontend `hudModel.test.ts`, `lib.test.ts`.
- **Test:** `test_closure_carried_through_a_head_drop_stays_monitored`, `test_eyes_close_then_head_drops_is_l3`,
  `test_closure_carried_through_head_drop`, `test_blink_then_head_down_is_not_carried`,
  `test_head_drop_carry_goes_on_when_the_face_slides_out_of_frame`.

<a id="7-tam-ngung-giam-sat"></a>

### 7. Tạm ngưng giám sát: mất mặt ≥ 3 s khi chạy — Vừa

- **Nguyên nhân:** che camera, tài xế ra khỏi khung, chói (PRD FR-6, M10).
  `risk.unavailable.no_face_s` = 3 s, khi xe không đứng yên (từ M72: từ 1 km/h, trước đó từ 5 km/h). Từ M43 còn
  có: thấy mặt nhưng mặt quá tối, quá chói hoặc ảnh mờ suốt `risk.unavailable.low_quality_s` (5 s); giai đoạn
  chất lượng của khối 6 (`edge_agent/perception/quality.py`, ngưỡng `quality.*`, tạm). Từ M72 mặt lọt một phần
  khỏi khung (`bad_angle`) cũng được tính 5 s đó; trước M72 ca này không đo, không tạm ngưng, không giới hạn.
- **Phát hiện:** có, `RiskAssessment.unavailable` kèm `unavailable_reason`: `no_face`, `camera_blocked` (không
  thấy mặt và cả khung tối / phẳng), `bad_angle` (mặt nằm một phần ngoài khung), `low_light`, `glare`, `blur`.
  Mọi luật bị tắt trong lúc đó (đoán sẽ là báo sai).
- **Tài xế thấy:** "Tạm ngưng giám sát" kèm việc cần làm theo lý do (ngồi đúng vị trí, kiểm tra ống kính, chỉnh
  camera, bật đèn, hạ tấm che nắng, lau ống kính), tiếng báo to (nếu đã bật âm thanh, dòng 1).
- **Quản lý thấy:** sự kiện `monitoring_unavailable` (có lý do) / `monitoring_restored`; bản tổng kết có độ
  phủ và số giây tạm ngưng theo từng lý do, dưới `trip_summary.min_monitored_frac` (60 %) thì ghi "số liệu
  không đủ".
- **Lỗ hổng đã biết:** mặt tối trong khoảng 25–60 và ảnh xám không bị coi là không đọc được, xem dòng 16.
- **Đã chốt (02/10):** không báo quản lý theo thời gian thực (tài xế có thể đang đi đâu đó).
- **Im lặng tối đa:** đến khi thấy lại mặt.
- **Test:** `test_no_face_3s_while_moving_is_unavailable_not_an_alert`, `test_unavailable_mutes_every_rule`,
  `test_not_unavailable_when_parked`, `test_face_lost_while_moving_is_unavailable_then_restored`,
  `test_face_lost_while_moving_is_unavailable_without_alert`, `test_no_face_while_driving_is_unavailable`,
  `test_face_lost_lowers_coverage_without_blaming_the_driver`; frontend `hudModel.test.ts`,
  `lib.test.ts` (demo mất mặt).

- **Test thêm (M43):** `tests/test_edge_agent/test_quality.py`, `tests/test_backend/test_m43_unavailable_cause.py`.
- **Test thêm (M72):** `tests/test_edge_agent/test_m72_silent_states.py` (mặt lọt một phần, giới hạn giữ nhìn lệch,
  xe bò 1–5 km/h), `test_unavailable_in_a_crawl_below_min_speed`.
- **Từ M72 (nút trên HUD):** không còn nút một chạm nào tắt hoặc che giám sát. "Chạy mô phỏng" và liên kết Dashboard
  chỉ hiện khi chưa có thiết bị nào đang giám sát sau màn hình; "Dừng camera" của bản web hỏi lại và kết thúc chuyến
  có tổng kết; rời trang giữa chuyến có âm `monitoring_stopped`. Còn hở: đóng tab hoặc tải lại trang giữa chuyến
  (không tiếng, đội xe thấy "Mất liên lạc" sau 90 s). Test: `hudModel.test.ts` ("ways out of the HUD"), e2e
  `live.e2e.ts`.

<a id="8-mat-camera"></a>

### 8. Mất camera — Vừa

- **Nguyên nhân:** camera rút ra / hỏng / treo. `capture.max_consecutive_failures` (30 lần đọc lỗi) hoặc
  không có frame trong `frame_timeout_s` (3 s); mở lại mỗi `reconnect_interval_s` (2 s).
- **Bản web (từ M71):** track camera kết thúc thì báo mất ngay; track bị `mute` hoặc video đứng hình quá
  `frame_timeout_s` (kể cả khi đã kéo frame bằng timer) cũng là mất camera. Trang xin lại camera mỗi
  `reconnect_interval_s`, HUD hiện "Lần thử N"; frame đầu tiên của luồng mới là `camera_restored`. Trước M71
  bản web chỉ báo khi track kết thúc và không bao giờ mở lại.
- **Phát hiện:** có.
- **Tài xế thấy:** "Mất camera: ngừng giám sát", tiếng báo to.
- **Quản lý thấy:** sự kiện `camera_lost` / `camera_restored`; bản tổng kết có `camera_lost_s`.
- **Đã chốt (02/10):** quản lý biết **sau chuyến**, qua bản tổng kết. Đầu mỗi chuyến nhắc tài xế kiểm tra
  camera (thấy mặt rõ) trước khi chạy: **chưa có**, thuộc việc
  [Đóng gói app APK](improvements.md#viec-apk). Bước đăng ký (bước 1 cần thấy rõ mặt) đã kiểm camera
  gián tiếp, nhưng tài xế được phép lái khi chưa đăng ký.
- **Im lặng tối đa:** đến khi camera về.
- **Test:** `test_lost_camera_is_reopened_and_frames_resume`, `test_camera_that_cannot_be_reopened_stays_lost`,
  `test_hanging_camera_counts_as_lost_after_timeout`, `test_camera_lost_is_shown_recorded_and_counted_in_the_summary`,
  `test_hud_reports_camera_lost`, `test_camera_lost_is_a_system_event`,
  `test_camera_lost_event_is_listed_but_not_counted_as_an_alert`.

<a id="9-fps-tut"></a>

### 9. FPS tụt kéo dài — Vừa

- **Nguyên nhân:** hub nóng, hạ xung, app khác chiếm CPU. Dưới 15 FPS: microsleep trễ hơn, đo chớp sai
  (cần 25–30 FPS).
- **Từ M28:** FPS (làm mượt) dưới `hud.low_fps_below` (14,5) liên tục `hud.low_fps_s` (5 s): HUD hiện chip
  **"Máy chậm: cảnh báo có thể trễ"**, sự kiện `low_fps` kèm số FPS; hồi lại thì `fps_restored`. Vẫn giám
  sát (chỉ trễ hơn), không tạm ngưng.
- **Còn lại:** hạ tải theo thứ tự (YOLO thưa hơn, giảm độ phân giải) chờ có hub
  ([việc đo phần cứng](improvements.md#viec-do-phan-cung)).
- **Test:** `test_low_fps_for_a_while_warns_and_clears`, `test_fps_at_the_15_fps_minimum_is_not_low`.

<a id="10-mat-khong-danh-gia-duoc"></a>

### 10. Mắt không đánh giá được (đầu quay / cúi nhiều) — Vừa

- **Nguyên nhân:** `|yaw|` > `eye.max_yaw_deg` (35°) hoặc cúi > `eye.max_pitch_down_deg` (25°) so với tư
  thế quen: mắt "không biết", không tính nhắm / PERCLOS.
- **Che bởi:** nhánh mất tập trung (`off_road` sau 2 s khi xe chạy); gục mang theo lần nhắm (dòng 6).
- **Test:** `test_eyes_not_judged_when_head_turned_or_down`,
  `test_short_face_dropout_keeps_closure_long_dropout_ends_it`.

<a id="11-dau-chuyen"></a>

### 11. Đầu chuyến: mốc chưa đủ dữ liệu — Thấp

- Microsleep → L3 chạy **từ frame đầu**. Các luật chậm hơn:
  - PERCLOS: cần `perclos_min_coverage_s` (30 s) dữ liệu mắt;
  - nhìn khỏi đường: không xét trong `baseline.calibrate_s` (5 s) đầu khi xe chạy (bỏ qua nếu đã đăng ký);
  - chớp chậm: so với 20 lần chớp đầu chuyến; xu hướng: cần 5 phút; mốc mắt: `baseline_min_data_s` 10 s.
- **Test:** `test_perclos_needs_coverage`, `test_perclos_high_after_coverage_only`,
  `test_no_off_road_while_calibrating_and_median_ignores_glances`, `test_calibration_waits_for_driving_and_is_clamped`.

<a id="12-dung-yen-nghi"></a>

### 12. Đứng yên / nghỉ — Thấp (theo thiết kế)

- Dưới `min_speed_kmh` (5 km/h): tắt mất tập trung. Dưới `stationary_kmh` (1 km/h, tức 0 km/h): **không
  cảnh báo nào** (M30, 02/10: `risk.drowsy.stationary_max_level: 0`; trước là tối đa L1, microsleep ở đèn đỏ
  vẫn có chuông). Dấu hiệu buồn ngủ vẫn được đo (bản tổng kết). Đứng ≥ `rest_after_s` (120 s) là nghỉ. Đúng
  khi xe thật sự đỗ; sai khi tín hiệu tốc độ sai (dòng 2).
- **Đánh đổi (chốt 02/10):** ngủ gật lúc dừng đèn đỏ không còn tiếng chuông; khi xe chạy lại thì mọi luật
  hoạt động bình thường (microsleep vẫn L3 ngay).
- **Từ M73 (chốt 08/10):** xe chạy lại sau lần dừng từ `context.short_stop_forget_s` (10 s, tạm) thì phần PERCLOS /
  microsleep gom lúc dừng bị bỏ, như sau lần nghỉ. Trước M73 phần đó được mang sang: nhắm mắt 25 s ở đèn đỏ thành L1
  sau 1,0 s lăn bánh (L2 ban đêm), lúc tài xế đã mở mắt. Đánh đổi thêm: người ngủ gật thật ở đèn đỏ bắt đầu đoạn kế
  tiếp không có phần điểm đó; mắt còn nhắm khi xe lăn bánh vẫn L3. Dừng dưới 10 s giữ nguyên bằng chứng. Cũng từ M73
  hệ số "lái lâu" tắt khi nghỉ và khi đổi tài xế. Test: `tests/test_edge_agent/test_m73_context.py`.
- **Test:** `test_standing_still_raises_no_alert_at_all`, `test_standing_still_looking_away_with_a_phone_raises_nothing`,
  `test_the_same_closure_while_driving_is_l3`, `test_resting_the_eyes_after_parking_is_never_l3_and_goes_silent`, `test_driving_off_after_a_rest_raises_nothing`,
  `test_microsleep_after_a_rest_is_still_l3`, `test_stationary_cap_from_config`, `test_standing_still_becomes_a_rest`,
  `test_crawling_in_a_jam_or_unknown_speed_is_never_a_rest`, `test_parked_phone_and_looking_around_no_alert`.

<a id="13-dang-ky"></a>

### 13. Chưa đăng ký / đăng ký thất bại / đang đăng ký — Thấp

- Chưa đăng ký / thất bại / chọn "Để sau" ở màn hình xác nhận (M24): vẫn giám sát bằng mốc tự học (kém
  chính xác hơn, không im). Thất bại thì thử lại, "Để sau" thì hỏi lại, ở lần dừng sau (`max_attempts` 3).
  Màn hình xác nhận chỉ hiện khi xe đỗ và không có cảnh báo nào.
- Bước 3 (nhắm mắt): tắt cảnh báo buồn ngủ trong lúc bước chạy và `reopen_grace_s` (2 s) sau đó. Chỉ chạy
  khi xe đỗ.
- **Đã chốt (02/10):** không giới hạn lái; chỉ đề xuất đăng ký để có kết quả tốt nhất.
- **Test:** `test_failed_enrollment_retries_at_the_next_stop`, `test_closing_the_eyes_for_enrollment_raises_no_alert`,
  `test_eyes_that_never_read_shut_give_up_instead_of_learning_a_bad_value`; frontend "reminds an unenrolled
  driver, quietly".
- ~~Lỗi bước nhắm mắt làm bảng tổng kết tính là ngủ gật~~: đã sửa ở M27 (bản tổng kết bỏ qua dấu hiệu buồn
  ngủ trong bước nhắm mắt của đăng ký và lúc nghỉ đỗ xe).

<a id="14-cooldown"></a>

### 14. Cooldown chặn cảnh báo lặp — Thấp

- Cùng (mức, lý do) không phát lại trong `alert.cooldown_s`: L1 120 s, L2 30 s, L3 0 s. HUD vẫn hiện mức
  đang bật; chỉ không có tiếng / sự kiện mới. Mức cao hơn luôn được phát. Còi L3 lặp lại khi mắt còn nhắm.
- **Từ M74:** cooldown chỉ giữ lại, không nuốt. Lý do còn đó khi cooldown hết thì được phát lại (`alert.remind`).
  Trước M74 có ba ca mất tiếng: đợt bắt đầu trong cooldown (nhìn lệch 40 s không tiếng vì 5 s trước có một lần
  ngắn), mức đứng yên (L1 nửa giờ một chuông), lý do bắt đầu dưới một mức cao hơn. Còn lại: lần nhìn lệch thứ hai
  vẫn im tới khi cooldown của lần đầu hết (tối đa 30 s). Cái giá: báo sai trên UTA-RLDD dev 1,29 → 1,81 / giờ.
- **Test:** `test_cooldown_suppresses_same_level`, `test_escalation_bypasses_lower_cooldown`,
  `test_cooldown_is_per_reason`, `test_dropping_a_level_is_not_a_new_alert`; M74:
  `tests/test_edge_agent/test_m74_alert_reminders.py`.

<a id="15-mat-mang"></a>

### 15. Hub mất mạng giữa chuyến — Thấp

- Giám sát và cảnh báo chạy offline, không ảnh hưởng. Chỉ quản lý biết trễ.
- Thiết bị: outbox SQLite giữ qua khởi động lại, tối đa `publisher.max_queue` (10 000). App (bọc code web):
  chỉ giữ trong RAM, app tắt là mất → việc [Hàng đợi offline cho app](improvements.md#viec-outbox-web).
- **Test:** `test_offline_keeps_events_and_backs_off`, `test_queue_survives_restart`, `test_queue_is_capped`,
  `test_server_error_is_retried_not_dropped`.

---

<a id="16-cnn-mat-toi"></a>

### 16. Thiết bị: mặt tối hoặc ảnh xám, CNN mắt đọc là mở — Cao (chưa có dữ liệu thật)

- **Nguyên nhân:** khi mặt tối hơn `eye_state.low_light_brightness` (60) hoặc ảnh là xám / IR, khối 5 giao
  trạng thái mắt cho CNN `open-closed-eye-0001`. Trên 8 video FL3D bị làm tối nhẹ (mặt 49 / 255) hoặc bỏ màu,
  CNN gần như không bao giờ nói "nhắm": microsleep đạt L3 18 / 24 → 0 / 24, recall mắt nhắm theo frame 88 % →
  0,2 % (tối) và 9 % (xám) ([lighting_transforms.md](../eval/results/lighting_transforms.md), M46).
- **Phát hiện:** không. Hệ thống vẫn báo "đang giám sát"; chỉ khi mặt tối hơn 25 mới thành `low_light` (dòng 7).
- **Tài xế / quản lý thấy:** không gì cả.
- **Im lặng tối đa:** không giới hạn (cả đoạn đường tối).
- **Phạm vi:** bản thiết bị (`eye_state.source = cnn`). `#/live` dùng blendshape nên không dính lỗi của CNN, nhưng tới
  M56 nó dính một lỗi khác cùng hậu quả: `eyeBlink` bị so với ngưỡng của CNN nên camera xám / IR bỏ sót mọi lần nhắm
  mắt (replay: 0 / 48, FL3D 0 / 95). M56 (07/10) cho `eyeBlink` ngưỡng riêng: 46 / 48 và 64 / 95. Ngưỡng tạm, chưa đo
  trên `#/live`, chưa có ảnh IR thật.
- **Mức chắc chắn:** thấp hơn các dòng khác: ánh sáng được biến đổi nhân tạo trên video ban đêm đã sáng sẵn,
  không phải cabin tối thật hay camera IR thật. Frame tối thật duy nhất có trong tay (FL3D, 466 frame mặt
  < 60) cho recall 40 %, cùng hướng.
- **Cập nhật M54 (06/10):** phần mặt tối đã đổi: `eye_state.low_light_brightness` = 0, EAR quyết định. Bản ghi thật
  ở mặt 32–35: nhắm mắt đạt L3 27 / 27, và 8 lần L3 sai do CNN mất đi; FL3D làm tối nhẹ 0 / 24 → 12 / 24. **Phần ảnh
  xám / IR còn nguyên** (0 / 24), nên dòng này vẫn mở ở mức Cao. Replay còn cho thấy bản web không miễn nhiễm như
  ghi ở trên: `eyeBlink` với ngưỡng của CNN không đạt "nhắm sâu" ở các frame khối 5 quyết định (chưa đo trên `#/live`).
- **Việc tiếp:** [Khối 5: CNN mắt với ảnh xám / hồng ngoại](improvements.md#viec-cnn-toi).

<a id="17-yolo-qua-han"></a>

### 17. Model điện thoại không còn cho kết quả — Vừa

- **Nguyên nhân:** kết quả YOLO cũ hơn `phone.max_result_age_s` (0,6 s) là "không rõ" và không được tính vào
  `phone_ratio_2s`. YOLO luôn chậm hơn thế (bản web: một luồng wasm, 175 ms mỗi lần trên Mac, máy chậm hơn
  khoảng 3,5 lần là chạm ngưỡng), model không tải được, hoặc worker chết: không bao giờ có cảnh báo `phone`.
- **Phát hiện:** từ M50. ≥ `phone.unknown_ratio` (0,8) của `phone.unknown_window_s` (10 s) gần nhất không có
  kết quả mới → `phone_detection_lost`; xuống `unknown_clear_ratio` (0,5) → `phone_detection_restored`.
- **Tài xế / quản lý thấy:** chip "Không phát hiện được điện thoại" trên HUD (không âm thanh: các nhánh khác vẫn
  chạy); sự kiện hệ thống trong nhật ký. Trạng thái giám sát vẫn là "đang giám sát".
- **Im lặng tối đa:** khoảng 10 s trước khi được báo. Sau đó nhánh điện thoại vẫn tắt, nhưng có người biết.
- **Phạm vi:** cả hai bản. Thiết bị chạy `--no-phone` là tắt có chủ ý, không báo.
- **Còn hở:** nhìn xuống điện thoại vẫn được nhánh hướng đầu bắt (`off_road`); cầm điện thoại ngang tầm mắt thì
  không. Ngưỡng tạm, chưa có dữ liệu. Thời gian mất nhánh chưa vào bảng tổng kết chuyến.
- **Test:** `test_m50_phone_health.py` (14 test: cửa sổ, hồi lại, YOLO chậm, khoảng trống frame, runtime, bridge).
- **Việc tiếp:** [YOLO trong bản web](improvements.md#viec-yolo-web).

## Khoảng trống thành việc riêng

Dòng chưa có test hoặc chưa có cách phát hiện (ghi ở [improvements.md](improvements.md)):

| Dòng | Việc |
|---|---|
| 1 | Âm thanh cảnh báo luôn bật: xong ở M23; phần APK thuộc Đóng gói app APK (đã có) |
| 2 | Mất tín hiệu xe khi đang chạy: xong ở M26 |
| 3, 9 | Báo khi vòng xử lý dừng hoặc chậm: xong ở M28 (hạ tải chờ hub) |
| 5 | Phát hiện mắt bị che (mới) |
| 4, 8 (nhắc kiểm tra camera) | Đóng gói app APK (đã có) |
| 6 | Cảnh báo cần xác nhận, báo quản lý ngay: xong ở M44 |
| 7 | Điểm chất lượng frame: xong ở M43 (ngưỡng tạm) |
| 16 | Khối 5 trên thiết bị: CNN mắt bỏ sót nhắm mắt khi mặt tối / ảnh xám (mới, từ M46) |
| 15 | Hàng đợi offline cho app (đã có) |

Khi sửa code liên quan tới một dòng, cập nhật dòng đó ở đây (mức, im lặng tối đa, test).
