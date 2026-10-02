# Lộ trình DriverGuard

Mỗi lần chỉ làm đúng một mốc được yêu cầu (CLAUDE.md). Làm xong thì cập nhật dòng của mốc đó ở
**Tổng quan** và thêm phần **Chi tiết** bên dưới. Những gì đã thêm / sửa / bỏ ở v2 cũng ghi trong
[release-v2.md](release-v2.md); việc chưa làm nằm ở [improvements.md](improvements.md).

## Tổng quan

### Version 1: hệ thống cơ bản (M0–M8)

| Mốc | Làm gì | Xong là thấy gì | Trạng thái |
|---|---|---|---|
| [M0](#m0) | Khối 1, 2: đọc video, resize, CLAHE | Cửa sổ hiện video chạy được | ✅ Xong · `abca755` |
| [M1](#m1) | Khối 3, 6: MediaPipe, tính EAR, MAR, head pose | In ra EAR mỗi frame, vẽ landmark lên ảnh debug | ✅ Xong · `e1a58d8` |
| [M2](#m2) | Khối 7: PERCLOS, microsleep, ngáp, gục đầu (+ khối 5 Eye-state CNN) | Terminal in ra khi phát hiện ngủ gật | ✅ Xong · `4077bd5` |
| [M3](#m3) | Khối 4, 8: YOLO điện thoại, nhìn lệch | Phát hiện được mất tập trung | ✅ Xong · `6dd7f99` |
| [M4](#m4) | Khối 9, 10, 11, 12: risk engine, CAN giả lập, cooldown | Ra mức L0–L3 đúng theo kịch bản | ✅ Xong |
| [M5](#m5) | Khối 14 + backend FastAPI | Sự kiện hiện trong database | ✅ Xong |
| [M6](#m6) | Dashboard React + HUD | Giao diện 3 vai trò, nhật ký sự kiện | ✅ Xong |
| [M7](#m7) | Script eval + benchmark FPS | Bảng precision/recall/FP mỗi giờ, bảng FPS | ✅ Xong (công cụ) |
| [M8](#m8) | Chạy toàn bộ trên trình duyệt (#/live): khối 1 camera, 3 MediaPipe JS, 4 YOLO onnxruntime-web, 6–12 Python thật qua Pyodide | Người khác mở web, cho phép camera là chạy, cảnh báo lưu theo tài khoản | ✅ Xong · 28/09 |

### Version 2: cải tiến (M9–M29)

| Mốc | Làm gì | Xong là thấy gì | Trạng thái |
|---|---|---|---|
| [M9](#m9) | Đăng ký tài xế lúc dừng xe (giai đoạn của khối 6): 3 bước nhìn camera / nhìn đường / nhắm mắt → mốc của riêng tài xế cho khối 3, 7, 8 | HUD hướng dẫn từng bước (chữ, giọng nói, tiếng bíp), xong thì giám sát bằng mốc của tài xế và chọn đúng mặt tài xế khi có hành khách | ✅ Xong · 01/10 |
| [M10](#m10) | Mất mặt ≥ 3 s khi xe chạy → tạm ngưng giám sát (PRD FR-6), bỏ cảnh báo L2 no_face | HUD hiện "Tạm ngưng giám sát" thay vì cảnh báo, backend nhận monitoring_unavailable / monitoring_restored | ✅ Xong · 01/10 |
| [M11](#m11) | Chớp chậm (khối 7): thời gian mở mắt lại + tỉ lệ thời gian chớp → thành phần slow_blink của drowsy_score | drowsy_score tăng khi chớp nhiều / mở mắt chậm so với chính tài xế lúc đầu chuyến | ✅ Xong · 01/10 · ngưỡng tạm |
| [M12](#m12) | Tách gục đầu (rơi chậm, giật lên) với cúi đầu chủ động (khối 7) | Sự kiện bow cho cúi đầu; phép thử tốc độ bật được trong thresholds.yaml | ✅ Xong · 01/10 · phép thử tốc độ tắt |
| [M13](#m13) | Nhướn mày để giữ mắt mở (khối 3 browOuterUp → khối 7) → thành phần brow của drowsy_score | Sự kiện brow_raise khi lông mày nhướn trong lúc mắt sụp | ✅ Xong · 01/10 · ngưỡng tạm |
| [M14](#m14) | Giao diện cho tài xế: bỏ thuật ngữ (HUD, #/live) | Tài xế không thấy L0–L3, EAR, FPS, tên model; 2 bước khởi động thay 4 | ✅ Xong · 01/10 |
| [M15](#m15) | Nút "Kết thúc chuyến" + bảng tổng kết chuyến, gửi lên quản lý / kỹ sư / admin | Tài xế bấm kết thúc → thấy đánh giá, câu kể, biểu đồ từng phút, gợi ý; quản lý thấy "Báo cáo chuyến đi (n mới)" trên dashboard | ✅ Xong · 01/10 |
| [M16](#m16) | Một chế độ mặc định thay 3 tình huống giả lập; nút Tạm dừng / Tiếp tục lái / Đổi tài xế | #/live và thiết bị: bắt đầu xe đỗ + đăng ký khuôn mặt, tự lái khi xong; tạm dừng đỗ xe; đổi tài xế thì người mới đăng ký lại | ✅ Xong · 01/10 |
| [M17](#m17) | Sửa cách đo báo sai / giờ: số giờ đo + CI 95%, mẫu số đúng, tách lý do × mức | Mọi bảng báo sai / giờ trong eval/results có giờ đo và CI | ✅ Xong · 01/10 |
| [M18](#m18) | FAR / MAR theo cửa sổ 10 s trong công cụ eval | Báo cáo eval có bảng FAR / MAR (nhánh buồn ngủ, mất tập trung) | ✅ Xong · 01/10 · dataset hiện có quá ngắn |
| [M19](#m19) | Bỏ nút Tạm dừng / Tiếp tục lái: đỗ / lái theo tốc độ; công cụ mô phỏng lái xe `tools/drive_sim.py` (khối 10) | Chạy công cụ trong terminal, bấm phím tăng / giảm tốc, xi nhan → HUD thiết bị và #/live đổi theo; 0 km/h hoặc không chạy công cụ = xe đỗ | ✅ Xong · 01/10 |
| [M20](#m20) | Xi nhan nới góc quay đầu về đúng phía bật (khối 8, 10): trái → được nhìn trái tới 60°, phía kia giữ 30° | Bật xi nhan trái nhìn trái không bị cảnh báo; nhìn phải lâu vẫn bị | ✅ Xong · 01/10 · ngưỡng tạm |
| [M21](#m21) | Trả nợ kỹ thuật: lớp chung `edge_agent/runtime.py` cho thiết bị + web; tách khối 7 thành module con; test e2e Playwright trong CI | Không đổi hành vi (replay 2437 trace ra đúng từng số); `npm run e2e` chạy #/live + dashboard thật, CI có job e2e | ✅ Xong · 02/10 |
| [M22](#m22) | Bảng phân tích lỗi (FMEA) các trạng thái im lặng: `docs/safety-fmea.md` | Mỗi lúc hệ thống không cảnh báo được có nguyên nhân, mức nghiêm trọng, tài xế / quản lý thấy gì, im lặng tối đa, test; khoảng trống thành việc mới | ✅ Xong · 02/10 · chỉ tài liệu |
| [M23](#m23) | Âm thanh cảnh báo luôn bật (khối 13): bỏ nút tắt tiếng, tự bật ở lần chạm đầu tiên | Mở HUD là có tiếng sau lần chạm đầu; trình duyệt còn chặn thì dải vàng to "Chạm vào màn hình để bật" trên mọi màn hình | ✅ Xong · 02/10 · APK còn cấu hình WebView |
| [M24](#m24) | Xác nhận trước khi đăng ký khuôn mặt (giai đoạn đăng ký của khối 6, HUD khối 13) | Xe dừng: HUD giải thích vì sao đăng ký và dữ liệu khuôn mặt không bị lưu / gửi đi; bấm "Đồng ý" mới vào 3 bước, "Để sau" thì hỏi lại ở lần dừng sau | ✅ Xong · 02/10 |
| [M25](#m25) | Cúi nhìn xuống không còn bị hiểu là nhắm mắt (khối 7, 8) | Cúi nhìn điện thoại / bảng đồng hồ: L2 "Nhìn về phía trước" thay vì L3 "Mở mắt!"; nhắm mắt thật khi đầu gục vẫn L3 | ✅ Xong · 02/10 · ngưỡng tạm |
| [M26](#m26) | Mất tín hiệu xe khi đang chạy không còn bị coi là đỗ; báo tài xế (khối 10, 13) | Tắt công cụ mô phỏng khi xe đang chạy: HUD báo "Mất tín hiệu xe" kèm âm báo, vẫn giám sát như đang chạy (nhắm mắt vẫn L3); backend nhận sự kiện, tổng kết có thời gian mất tín hiệu | ✅ Xong · 02/10 |
| [M27](#m27) | Bảng tổng kết không còn tính bước nhắm mắt của đăng ký (và lúc nghỉ đỗ xe) là ngủ gật (khối 11) | Đăng ký rồi kết thúc chuyến: đánh giá "Tốt", 0 lần ngủ gật; microsleep ở đèn đỏ vẫn được tính | ✅ Xong · 02/10 |
| [M28](#m28) | Báo khi vòng xử lý dừng hoặc chậm (khối 13, 14, `TripRuntime`) | Lỗi frame liên tục ≥ 1 s: HUD "Lỗi xử lý" + âm báo to, backend nhận `agent_error`; HUD đứng hình / mất kết nối có âm báo; FPS < 14,5 trong 5 s: chip "Máy chậm" | ✅ Xong · 02/10 |
| [M29](#m29) | Cập nhật tài liệu theo v2: README, sơ đồ kiến trúc, HowToUse | README mở đầu bằng DriverGuard; sơ đồ có phần v2; HowToUse có luồng một chuyến đi và các trạng thái không giám sát | ✅ Xong · 02/10 |

---

## Chi tiết từng mốc

### Version 1: hệ thống cơ bản (M0–M8)

<a id="m0"></a>

#### M0: Khối 1, 2: đọc video, resize, CLAHE

**Xong là thấy gì:** Cửa sổ hiện video chạy được

**Trạng thái:** Xong (abca755)

- Mất camera (25/09): mở lại mỗi 2 s thay vì thoát, `lost` khi 3 s không có frame
- Hiệu năng (25/09): CLAHE trên kênh Y của YCrCb thay cho LAB, tiền xử lý 1,03 → 0,64 ms (−38%), brightness giữ nguyên

<a id="m1"></a>

#### M1: Khối 3, 6: MediaPipe, tính EAR, MAR, head pose

**Xong là thấy gì:** In ra EAR mỗi frame, vẽ landmark lên ảnh debug

**Trạng thái:** Xong (e1a58d8)

- Blendshapes (26/09): khối 3 xuất eyeBlink của MediaPipe (cùng model, không tốn thời gian đo được: 151,8 FPS)

<a id="m2"></a>

#### M2: Khối 7: PERCLOS, microsleep, ngáp, gục đầu (+ khối 5 Eye-state CNN)

**Xong là thấy gì:** Terminal in ra khi phát hiện ngủ gật

**Trạng thái:** Xong (4077bd5)

- Sửa an toàn: nhắm mắt rồi gục đầu vẫn đếm tiếp closed_duration → L3
- Mốc pitch/yaw chỉ học lúc mắt mở (không trôi khi gật nhiều)
- Giảm báo sai: không tính thời gian nhắm mắt lúc ngáp / đang nói (+1,5 s) vào closed_duration, MAR ngáp 0,45/0,34 (YawDD: L3 ở clip Yawning 13 → 1, Talking 20 → 4)
- Giảm báo sai (25/09): PERCLOS bỏ qua frame ngáp/nói, microsleep chỉ tính nhắm sâu (EAR ≤ 0,5 × mốc), ngưỡng face_conf 0,9 (YawDD: cảnh báo sai 23 → 9, microsleep sai 35 → 6, drowsy sai 33 → 0)
- Giảm báo sai (25/09 chiều): PERCLOS xét từng frame thay vì trạng thái có hysteresis (nheo mắt vì nắng + chớp bình thường: L1 sau 11 s → không cảnh báo), CNN mắt được giữ 2 s khi gọi vì tối / IR (chạng vạng: PERCLOS giả 0,36 → 0), không giữ khi lệch EAR (kính: microsleep sai 6 → 18 nếu giữ)
- YawDD cuối: microsleep sai 6 → 5, cảnh báo sai 9 → 10 (1 off_road quay đầu thật sát ngưỡng)
- Sửa theo eval FL3D / SUST (26/09): khối 5 xét độ sáng vùng mặt (trước CLAHE) thay cả khung, lệch EAR chia theo mắt còn mở (không bật lúc hai mắt cùng nhắm), nhắm sâu phải được eyeBlink ≥ 0,5 xác nhận, nói chuyện không che đợt nhắm sâu đã được xác nhận
- FL3D microsleep ≥ 1,5 s đạt L3 17,9% → 78,9%, SUST L3 đúng/sai 6/4 → 12/2, YawDD không hồi quy (10 cảnh báo sai, 5 microsleep sai)
- Thử blendshape thay CNN: tệ hơn với kính, giữ CNN

<a id="m3"></a>

#### M3: Khối 4, 8: YOLO điện thoại, nhìn lệch

**Xong là thấy gì:** Phát hiện được mất tập trung

**Trạng thái:** Xong (6dd7f99)

- Sửa an toàn: điện thoại che mặt vẫn tính (nhớ khung mặt 3 s), thêm no_face_duration
- Hiệu chỉnh mốc nhìn đường 5 s đầu chuyến (camera lắp lệch > 30°)
- Hiệu năng (25/09): onnxruntime của YOLO không busy-wait nữa (CPU luồng YOLO -22%, latency không đổi)
- Kết quả YOLO đến trễ hơn max_result_age_s (CPU yếu) được đếm, cảnh báo 1 lần và hiện trên dòng trạng thái, thay vì phát hiện điện thoại tắt âm thầm

<a id="m4"></a>

#### M4: Khối 9, 10, 11, 12: risk engine, CAN giả lập, cooldown

**Xong là thấy gì:** Ra mức L0–L3 đúng theo kịch bản

**Trạng thái:** Xong

- Sửa an toàn: mất mặt ≥ 3 s khi chạy → L2 (no_face), lý do mới cùng mức → alert mới, cooldown theo (mức, lý do)
- Sửa cấu hình: thiếu tín hiệu tốc độ không còn crash (coi là đang chạy), key lạ trong thresholds.yaml dừng agent (ConfigError), bỏ ngưỡng trùng: min_speed_kmh chỉ ở context, perclos_min_coverage_s chỉ ở drowsiness
- Giảm báo sai (25/09): xe đứng yên (< 1 km/h, xe bò lúc kẹt xe không tính) thì buồn ngủ tối đa L1, đứng yên ≥ 120 s là nghỉ: không cảnh báo buồn ngủ, chạy lại thì xoá dữ liệu gom từ lúc dừng (chuỗi giả: đỗ xe nhắm mắt nghỉ L3 → chime L1 trong 2 phút đầu rồi im; ngủ xong lái đi L1 ngày / L2 đêm → không cảnh báo)
- Cooldown L3 10 → 0 s (26/09): mỗi microsleep mới sau ≥ 3 s mở mắt có còi + sự kiện riêng (FL3D 55% → 76%)

<a id="m5"></a>

#### M5: Khối 14 + backend FastAPI

**Xong là thấy gì:** Sự kiện hiện trong database

**Trạng thái:** Xong

- Sự kiện system camera_lost / camera_restored (25/09), luật nhất quán ngưỡng dùng chung thiết bị + backend

<a id="m6"></a>

#### M6: Dashboard React + HUD

**Xong là thấy gì:** Giao diện 3 vai trò, nhật ký sự kiện

**Trạng thái:** Xong

- Cửa sổ báo sai lấy từ hud.feedback_window_s (25/09), HUD hiện mất camera
- HUD làm lại (25/09, tối): Tailwind v4 + design token, liếc 0,5 s là hiểu (màu theo mức + icon theo lý do + câu hành động), mức càng cao màn hình càng ít chữ, L3 đỏ toàn màn hình nhấp nháy 1 Hz, ban đêm L0–L1 giảm sáng
- `#/hud-preview` xem từng trạng thái
- Dashboard không đổi (so ảnh từng pixel)
- Âm thanh HUD (25/09): mỗi loại cảnh báo một tiếng riêng (buồn ngủ, xu hướng, microsleep lúc dừng, nhìn lệch, điện thoại, mất mặt, mất camera), mức quyết định độ to, còi L3 lặp mỗi 1,5 s tới khi mắt mở
- Demo 90 s phát đủ các loại

<a id="m7"></a>

#### M7: Script eval + benchmark FPS

**Xong là thấy gì:** Bảng precision/recall/FP mỗi giờ, bảng FPS

**Trạng thái:** Công cụ xong, bảng FPS đo trên video YawDD có mặt thật (146 FPS, Mac ARM)

- Tools/dataset.py đo từng ảnh trên dataset Kaggle
- Eval FL3D + SUST-DDD (26/09): tools/seq_eval.py (trace từng frame, chấm nhãn frame / clip, replay khối 7–12 với ngưỡng khác), FL3D trên video NITYMED: microsleep ≥ 1,5 s đạt L3 17,9%, ngáp 76,8%, 0 báo sai buồn ngủ
- SUST: 11,5 cảnh báo/giờ trên clip không buồn ngủ (off_road khi quay đầu thật)
- Tìm ra 2 lỗi trigger CNN khối 5 (low_light theo cả khung, ear_asymmetry chia EAR trung bình), đã sửa (xem M1, M2, M4), chi tiết docs/worklog/2026-09-26-DAQuan.md
- Tools/seq_eval.py --replay block5 thử ngưỡng khối 5, 7–12 không cần chạy lại MediaPipe
- Báo cáo tổng hợp (28/09): eval/results/report.md đối chiếu 6 yêu cầu cơ bản với code, gom accuracy / precision / recall / FPR của mọi dataset, FPS, test (410 + 18 pass)

<a id="m8"></a>

#### M8: Chạy toàn bộ trên trình duyệt (#/live): khối 1 camera, 3 MediaPipe JS, 4 YOLO onnxruntime-web, 6–12 Python thật qua Pyodide

**Xong là thấy gì:** Người khác mở web, cho phép camera là chạy, cảnh báo lưu theo tài khoản

**Trạng thái:** Xong (28/09, ngoài lộ trình gốc, theo yêu cầu)

- Edge_agent/web/bridge.py nối trình duyệt với khối 6–12 không đổi logic (khối 3 import mediapipe lười để chạy được trong Pyodide)
- Khác thiết bị: không CLAHE, khối 5 dùng blendshape
- Backend thêm POST /api/v1/web/events + GET /api/v1/web/thresholds (token người dùng, thiết bị web-<username>)
- Test: 13 test bridge (chạy cả trong Pyodide thật: 0,15 ms/frame), 5 test API, 7 test đo JS
- Chrome + camera giả từ clip SUST d_325: 30 FPS, YOLO 172 ms, lên L3 microsleep, sự kiện vào database
- Deploy Railway v1.1 (quanpk07/driveguard:v1.1)
- Chưa đo trên điện thoại / máy yếu, chưa thử điện thoại thật trước camera

### Version 2: cải tiến (M9–M21)

<a id="m9"></a>

#### M9: Đăng ký tài xế lúc dừng xe (giai đoạn của khối 6): 3 bước nhìn camera / nhìn đường / nhắm mắt → mốc của riêng tài xế cho khối 3, 7, 8

**Xong là thấy gì:** HUD hướng dẫn từng bước (chữ, giọng nói, tiếng bíp), xong thì giám sát bằng mốc của tài xế và chọn đúng mặt tài xế khi có hành khách

**Trạng thái:** Xong (01/10, việc 2 trong docs/improvements.md)

- Edge_agent/perception/enrollment.py, bắt buộc nhưng không chặn giám sát (chưa đăng ký thì chạy mốc tự học như cũ, HUD nhắc dừng xe), chỉ trong RAM một chuyến, backend chỉ nhận driver_enrolled (thời gian, số bước làm lại) + metrics.enrolled
- ~7 s thu thập, ~10 s cả chuyển bước, mỗi bước chỉ đếm frame tốt (chớp mắt / quay đi thì tạm dừng), kiểm tra rồi làm lại đúng bước lỗi, 3 lần lỗi thì chờ lần dừng sau
- Khối 3: chữ ký mặt (7 tỉ lệ landmark 3D) + vị trí, thiết bị và web dùng chung DriverSelector (web gửi mọi mặt sang Python)
- Khối 7: mốc EAR mở cố định (chỉ trôi −10 % / +25 %), ngưỡng ngáp = MAR khép + 0,40 / 0,29, mốc tư thế từ bước nhìn đường
- Khối 8: bỏ hiệu chỉnh 5 s đầu khi đã đăng ký
- Bước nhắm mắt + 2 s sau không cảnh báo buồn ngủ, dữ liệu bị bỏ như lúc nghỉ
- Ngưỡng ở enrollment: trong thresholds.yaml
- Eval không đổi (xe chạy 60 km/h từ đầu nên không đăng ký)
- Chữ ký mặt 0,02 ms/frame
- Test: 25 test mới (chuỗi số giả 15 FPS), tổng 459 Python + 30 frontend pass
- Chưa thử với người thật trước camera, chưa đo chữ ký mặt trên nhiều người thật

<a id="m10"></a>

#### M10: Mất mặt ≥ 3 s khi xe chạy → tạm ngưng giám sát (PRD FR-6), bỏ cảnh báo L2 no_face

**Xong là thấy gì:** HUD hiện "Tạm ngưng giám sát" thay vì cảnh báo, backend nhận monitoring_unavailable / monitoring_restored

**Trạng thái:** Xong (01/10)

- Risk engine trả unavailable, không luật nào báo trong lúc đó (kể cả off_road giữ từ trước), trừ đợt nhắm mắt đang được đếm tiếp qua cú gục đầu (còi L3 không bị tắt)
- Ngưỡng risk.distraction.no_face_s → risk.unavailable.no_face_s (key cũ dừng agent kèm gợi ý)
- Thiết bị + web gửi sự kiện hệ thống khi chuyển trạng thái, HUD có màn hình + tiếng riêng, demo / preview thay L2 mất mặt bằng tạm ngưng
- Backend vẫn nhận no_face cho sự kiện cũ
- Replay trace SUST-DDD: clip không buồn ngủ FPR 2,9 % → 2,4 %, 10,8 → 8,5 cảnh báo sai / giờ (bớt 7 no_face + 1 off_road), recall không đổi, FL3D không đổi
- Test: 462 Python + 32 frontend pass
- Ghi ở docs/release-v2.md

<a id="m11"></a>

#### M11: Chớp chậm (khối 7): thời gian mở mắt lại + tỉ lệ thời gian chớp → thành phần slow_blink của drowsy_score

**Xong là thấy gì:** drowsy_score tăng khi chớp nhiều / mở mắt chậm so với chính tài xế lúc đầu chuyến

**Trạng thái:** Xong (01/10, ngưỡng tạm chờ eval)

- Đo trên độ mở mắt chuẩn hoá giữa EAR nhắm / mở (của tài xế khi đã đăng ký), nội suy thời điểm cắt ngưỡng giữa frame
- Blink_time_frac 60 s ramp 10 % → 16 %, reopen_ratio (so 20 lần chớp đầu chuyến) ramp ×1,3 → ×1,7 (Caffier 2003), trọng số 10, chỉ bật sau 30 s dữ liệu mắt
- Metadata blink_time_frac / reopen_ratio
- Replay FL3D: L2 13 → 16 (đúng 9 → 11), thêm 1 L1 sai (drowsy_score sai 2 → 3), SUST không đổi (clip 10 s)
- Nguồn ở docs/research/2026-10-01-blink-nod-brow.md

<a id="m12"></a>

#### M12: Tách gục đầu (rơi chậm, giật lên) với cúi đầu chủ động (khối 7)

**Xong là thấy gì:** Sự kiện bow cho cúi đầu; phép thử tốc độ bật được trong thresholds.yaml

**Trạng thái:** Xong (01/10), phép thử tốc độ TẮT mặc định

- Replay FL3D / SUST không bộ ngưỡng nào hơn v1 (ratio 1,5 + 40 °/s: FL3D gục đúng 115 → 51, SUST precision 48 % → 25 %), dataset thiếu cảnh cúi nhìn điện thoại
- Mặc định giống hệt v1 (đã kiểm bằng replay)
- Pha xuống / lên đo từ tư thế thường (đăng ký) đến đáy, bỏ đoạn giữ đầu

<a id="m13"></a>

#### M13: Nhướn mày để giữ mắt mở (khối 3 browOuterUp → khối 7) → thành phần brow của drowsy_score

**Xong là thấy gì:** Sự kiện brow_raise khi lông mày nhướn trong lúc mắt sụp

**Trạng thái:** Xong (01/10, ngưỡng tạm chờ eval)

- Vural et al. 2007 (AU2)
- Lông mày cao hơn mức bình thường (từ bước 1 đăng ký, hoặc trung vị 120 s) ≥ 0,2, EAR < 0,85 × mốc, ≥ 0,5 s, không lúc ngáp / nói, không khi mắt mở to
- 3 lần / 5 phút = đủ thành phần, trọng số 10
- Thiết bị + web (JS gửi browOuterUp mỗi mặt)
- Seq_eval trace thêm cột brow (trace cũ không có nên chưa đo được)
- Test: 483 Python + 32 frontend pass

<a id="m14"></a>

#### M14: Giao diện cho tài xế: bỏ thuật ngữ (HUD, #/live)

**Xong là thấy gì:** Tài xế không thấy L0–L3, EAR, FPS, tên model; 2 bước khởi động thay 4

**Trạng thái:** Xong (01/10)

- HUD chỉ còn màu + hình + câu hành động (mã L0–L3 vẫn ở dashboard / metadata), mô tả L1 / L2 nói việc cần làm
- #/live gộp 3 bước tải thành "Đang chuẩn bị" có thanh tiến độ, ô camera chỉ "Đang theo dõi" / "Không thấy mặt, hãy chỉnh camera", số đo kỹ thuật sau nút "Chi tiết kỹ thuật"
- Chưa đọc thành tiếng L2 / L3, chưa test với tài xế thật

<a id="m15"></a>

#### M15: Nút "Kết thúc chuyến" + bảng tổng kết chuyến, gửi lên quản lý / kỹ sư / admin

**Xong là thấy gì:** Tài xế bấm kết thúc → thấy đánh giá, câu kể, biểu đồ từng phút, gợi ý; quản lý thấy "Báo cáo chuyến đi (n mới)" trên dashboard

**Trạng thái:** Xong (01/10)

- Khối 11 thêm edge_agent/decision/trip_summary.py (cộng dồn mỗi frame, dựng TripSummary: thời gian, nghỉ, cảnh báo theo mức / lý do, báo sai, microsleep, ngáp, gục, nhướn mày, nhìn khỏi đường, điện thoại, độ phủ, drowsy_score từng phút, phút mệt đầu tiên, đánh giá good / attention / risk theo trip_summary trong thresholds.yaml, gợi ý)
- Thiết bị: POST /end-trip trên HUD server (vòng lặp chính dựng, gửi qua outbox, trả HUD), cũng tạo khi agent dừng
- Web: bridge.end_trip
- Backend: batch summaries, bảng trip_summaries (device, trip), GET /api/v1/trip-reports (+ chi tiết), POST …/review cho quản lý / kỹ sư / admin
- Frontend: hộp xác nhận, TripSummaryView, tab Báo cáo chuyến đi (bản kỹ sư, đánh dấu đã xem, đếm mới)
- Kiểm bằng Chrome headless với backend thật
- Test: 499 Python + 38 frontend pass

<a id="m16"></a>

#### M16: Một chế độ mặc định thay 3 tình huống giả lập; nút Tạm dừng / Tiếp tục lái / Đổi tài xế

**Xong là thấy gì:** #/live và thiết bị: bắt đầu xe đỗ + đăng ký khuôn mặt, tự lái khi xong; tạm dừng đỗ xe; đổi tài xế thì người mới đăng ký lại

**Trạng thái:** Xong (01/10)

- Khối 10 thêm ManualVehicle (config/scenarios/manual.yaml, 50 km/h, đồng hồ thật), mặc định của edge_agent.main và bridge web (kịch bản CAN vẫn dùng được qua --scenario)
- DecisionPipeline.change_driver bỏ mốc người cũ (khối 7, 8, trip memory, alert, đăng ký), khối 3 bỏ chữ ký, tổng kết chuyến đếm driver_changes, sự kiện driver_changed
- HUD: thẻ Xe + hộp xác nhận đổi tài, HUD server POST /vehicle
- #/live bỏ phần chọn tình huống, thêm mục đăng ký khuôn mặt
- Kiểm bằng Chrome headless với camera giả
- Sửa kèm: tắt telemetry onnxruntime (1DS gửi về Microsoft, gây abort lúc thoát 4–5/10 lần chạy test) qua edge_agent/perception/onnx.py load_ort (ORT_DISABLE_TELEMETRY + disable_telemetry_events), sau sửa 0/18
- Test: 506 Python + 38 frontend pass

<a id="m17"></a>

#### M17: Sửa cách đo báo sai / giờ: số giờ đo + CI 95%, mẫu số đúng, tách lý do × mức

**Xong là thấy gì:** Mọi bảng báo sai / giờ trong eval/results có giờ đo và CI

**Trạng thái:** Xong (01/10, việc 1 trong docs/improvements.md)

- `tools/metrics.py` (mới, hàm thuần): CI Poisson chính xác (Garwood), Wilson, hợp đoạn, giờ có thể báo sai
- `tools/eval.py`: báo sai / giờ chia cho thời lượng trừ các đoạn có nhãn của hàng đó (± tolerance), cột Giờ + CI, thêm hàng "tất cả cảnh báo" L1 / L2 / L3
- `tools/seq_eval.py`: FL3D bảng sai / giờ có CI + bảng lý do × mức; SUST cảnh báo / giờ có CI + bảng lý do × mức; lệnh mới `yawdd` chấm YawDD từ trace bằng hàm của eval.py
- Kết quả: YawDD "tất cả cảnh báo" 4,8 → 6,9 / giờ (CI 3,3–12,7) do mẫu số đúng; FL3D L1 4,6 / giờ (CI 0,56–16,7) trên 0,43 giờ; SUST `off_road` L2 7,9 / giờ (CI 5,0–11,7)
- Cập nhật `eval/results/dataset_fl3d.md`, `dataset_sust_ddd.md`, `dataset_yawdd.md`, `report.md`; không đổi khối 2–14, FPS

<a id="m18"></a>

#### M18: FAR / MAR theo cửa sổ 10 s trong công cụ eval

**Xong là thấy gì:** Báo cáo eval có bảng FAR / MAR (nhánh buồn ngủ, mất tập trung)

**Trạng thái:** Xong (01/10, việc 2 trong docs/improvements.md)

- Cửa sổ 10 s không chồng nhau, bỏ 30 s đầu, nhãn cửa sổ ≥ 50 %, đoán theo mức của nhánh ≥ L1 (và ≥ L2); tham số ở `config/thresholds.yaml` → `eval`
- `run_video` / `seq_eval replay` ghi mức cao nhất của nhánh buồn ngủ và mất tập trung theo từng giây (chỉ số, không ảnh); file predictions lưu thêm `levels`
- Kết quả: FL3D 7 cửa sổ hợp lệ, YawDD 13, SUST 0: dataset hiện có quá ngắn, FAR / MAR dành cho UTA-RLDD / DMD
- Test: 13 test mới (metrics + eval), tổng 519 Python pass

<a id="m19"></a>

#### M19: Bỏ nút Tạm dừng / Tiếp tục lái: đỗ / lái theo tốc độ; công cụ mô phỏng lái xe `tools/drive_sim.py` (khối 10)

**Xong là thấy gì:** Chạy công cụ trong terminal, bấm phím tăng / giảm tốc, xi nhan → HUD thiết bị và #/live đổi theo; 0 km/h hoặc không chạy công cụ = xe đỗ

**Trạng thái:** Xong (01/10)

- `tools/drive_sim.py` (mới, ngoài giao diện): phím tăng / giảm tốc, dừng, chạy 50 km/h, xi nhan trái / phải (giữ bật đến khi tắt); tốc độ đổi dần; `--scenario` chạy lại kịch bản CAN; thông số ở `config/drive_sim.yaml`
- Công cụ mở `GET 127.0.0.1:8766/can`; thiết bị (`SignalLink`, `--sim-url`) và #/live (mỗi 250 ms, `bridge.vehicle_signal`) cùng đọc
- Khối 10: `ExternalVehicle` thay `ManualVehicle`; không có tín hiệu / tín hiệu cũ hơn `context.vehicle_signal_stale_s` = 0 km/h; bỏ `config/scenarios/manual.yaml`
- HUD: dải "Tín hiệu xe" dưới thanh trên cùng (mũi tên xi nhan to nhấp nháy, km/h chữ to, "Đang lái" / "P Đang đỗ", báo chưa có tín hiệu xe); thẻ Xe chỉ còn nút "Đổi tài xế"; `POST /vehicle` chỉ nhận `change_driver`
- Xi nhan của công cụ giữ bật đến khi người dùng tắt (không tự tắt)
- Test: 17 test (thay 7 test M16), tổng 529 Python + 38 frontend pass

<a id="m20"></a>

#### M20: Xi nhan nới góc quay đầu về đúng phía bật (khối 8, 10)

**Xong là thấy gì:** Bật xi nhan trái nhìn trái không bị cảnh báo; nhìn phải lâu vẫn bị

**Trạng thái:** Xong (01/10, ngưỡng tạm)

- Khối 10: `VehicleContext.turn_side` (phía xi nhan cuối, giữ qua `context.turn_signal_grace_s`)
- Khối 8: giới hạn yaw phía xi nhan = `yaw_off_road_deg` + `turn_signal_extra_yaw_deg` (30 + 30), phía kia và góc cúi giữ nguyên; `left_yaw_sign` cho camera lật gương; mốc nhìn đường không học từ dải được nới
- Khối 9: bỏ luật "đang rẽ = bỏ nhìn lệch"
- Dashboard: thêm ngưỡng "Góc nới thêm về phía bật xi nhan"
- Test: 15 test mới, tổng 544 Python + 38 frontend pass

<a id="m21"></a>

#### M21: Trả nợ kỹ thuật: lớp chung cho thiết bị + web, tách khối 7, test e2e trong CI

**Xong là thấy gì:** Không đổi hành vi (replay 2437 trace ra đúng từng số); `npm run e2e` chạy #/live + dashboard thật, CI có job e2e

**Trạng thái:** Xong (02/10)

- `edge_agent/runtime.py` (mới): `TripRuntime` gom phần `main.py` và `web/bridge.py` từng viết hai lần: lấy mẫu khối 10, chạy `DecisionPipeline`, gắn mốc mặt tài xế cho khối 3 sau đăng ký, `unavailable`, cập nhật HUD, bản ghi khối 14 (cảnh báo, sự kiện hệ thống, mẫu mỗi phút, báo sai, tổng kết), đổi tài xế, mất camera, kết thúc chuyến. Bản ghi đi qua `emit(kind, data)`: thiết bị → `MetadataPublisher.publish_record`, web → hàng đợi gửi của trình duyệt. `main.py` / `bridge.py` chỉ còn phần vào / ra riêng (camera, HTTP, cửa sổ; Pyodide)
- Khối 7 thành package `edge_agent/analysis/drowsiness/`: `eyes.py` (mốc mắt mở, nhắm / mở, chớp, microsleep, gục mang theo, PERCLOS), `mouth.py` (ngáp, che khi ngáp / nói), `head.py` (tư thế quen, gục / cúi), `slow_blink.py`, `brow.py`, `analyzer.py` (lớp ghép `DrowsinessAnalyzer`). Import cũ giữ nguyên
- Kiểm tra không đổi hành vi: replay 2437 trace (FL3D, YawDD, SUST) qua khối 7 và khối 7–12, so mọi trường của `DrowsinessState`, mức, điểm, sự kiện, cảnh báo trước / sau: giống hệt
- Test e2e (`frontend/e2e/`, Playwright): backend trên database tạm, bản build frontend có cổng test (`VITE_E2E=1`, bản production không có), camera giả của Chrome, khối 3 nhận landmark số tổng hợp (`tools/e2e_setup.py`) thay MediaPipe. Không ảnh khuôn mặt, không cần file model. 2 kịch bản: dùng thử (đăng ký → lái → nhắm mắt L3 → tổng kết); tài xế đăng nhập (đổi tài xế → đăng ký lại → tổng kết gửi lên → quản lý thấy báo cáo). CI: job `e2e`
- Test: 10 test mới cho `TripRuntime`, tổng 554 Python + 38 frontend + 2 e2e pass

<a id="m22"></a>

#### M22: Bảng phân tích lỗi (FMEA) các trạng thái im lặng

**Xong là thấy gì:** `docs/safety-fmea.md`: mỗi lúc hệ thống không cảnh báo được có nguyên nhân, mức nghiêm trọng, cách phát hiện, tài xế / quản lý thấy gì, im lặng tối đa, test đang kiểm; khoảng trống thành việc mới

**Trạng thái:** Xong (02/10), chỉ tài liệu, không đổi code (việc 3 trong docs/improvements.md)

- 15 trạng thái đối chiếu với code sau M21: 6 Cao, 4 Vừa, 5 Thấp. Mỗi dòng dẫn tên test đang kiểm (đã kiểm tra từng tên có trong `tests/`)
- Mức Cao, chưa sửa: HUD khởi động tắt tiếng (chưa chạm "Bật âm thanh" thì còi L3 không kêu); mất tín hiệu tốc độ khi đang chạy bị coi là đỗ (tắt nhánh mất tập trung, sau 120 s tắt cảnh báo buồn ngủ); vòng xử lý dừng chỉ hiện chữ, không tiếng, backend không biết; app bị Android dừng (chưa có app); kính râm (chưa kiểm chứng); gục ra khỏi khung khi chưa thấy mắt nhắm
- Ghi lại các quyết định đã chốt 02/10 (tạm ngưng giám sát, mất camera, gục ra khỏi khung, chưa đăng ký) và bảng thời gian cảnh báo bình thường tính từ cấu hình
- docs/improvements.md: xoá việc 3; thêm việc 5 (âm thanh luôn bật trên app), 6 (mất tín hiệu xe không coi là đỗ), 7 (báo khi vòng xử lý dừng / chậm), 30 (phát hiện mắt bị che), chi tiết ở mục 22; đánh số lại 1–34. Việc "cảnh báo cần xác nhận" giữ câu hỏi còn mở (hỏi sau bao lâu, chờ bao lâu) và bỏ "báo mất camera theo thời gian thực" cho khớp quyết định
- Không đổi code nên không chạy lại test

<a id="m23"></a>

#### M23: Âm thanh cảnh báo luôn bật (khối 13)

**Xong là thấy gì:** Mở HUD là có tiếng sau lần chạm đầu tiên bất kỳ; trình duyệt còn chặn thì dải vàng to "Âm thanh cảnh báo chưa bật. Chạm vào màn hình để bật." trên mọi màn hình

**Trạng thái:** Xong (02/10) (việc 5 trong docs/improvements.md, FMEA dòng 1)

- `frontend/src/hud/chime.ts`: `armAudio()` tạo audio context khi HUD mở, bật lại ở lần `pointerdown` / `touchstart` / `keydown` đầu tiên bất kỳ, báo mỗi lần đổi trạng thái; `play()` không phát khi còn bị chặn (tránh dồn tiếng rồi kêu cùng lúc)
- `HudScreen.tsx`: âm thanh luôn bật, `sound` chỉ còn nghĩa "trình duyệt đã cho phát"; bỏ nút tắt tiếng. `HudView.tsx`: dải vàng nhắc (hàng riêng trong lưới, cả L3 và màn hình hệ thống); biểu tượng loa ở góc chỉ báo trạng thái, vàng khi còn chặn. `#/hud-preview` thêm trạng thái "Chưa có tiếng"
- Đọc thành tiếng cảnh báo L2 / L3 và trạng thái hệ thống: làm thử rồi bỏ theo quyết định 02/10 ("không cần nói, cảnh báo thôi"). Lời nhắc giọng nói của bước đăng ký giữ nguyên
- Còn lại: APK cho WebView phát âm thanh không cần chạm (*chưa kiểm chứng*), ghi vào việc đóng gói APK
- docs/improvements.md: xoá việc 5, đánh số lại 1–33. docs/safety-fmea.md: dòng 1 từ Cao xuống Vừa
- Test: 1 test frontend mới, tổng 39 frontend pass; typecheck, build sạch; 2 e2e pass. Python không đổi

<a id="m24"></a>

#### M24: Xác nhận trước khi đăng ký khuôn mặt (giai đoạn đăng ký của khối 6, HUD khối 13)

**Xong là thấy gì:** Xe dừng: HUD hiện "Đăng ký khuôn mặt" với lý do và cam kết về dữ liệu; bấm "Đồng ý, bắt đầu đăng ký" mới vào 3 bước, "Để sau" thì vẫn lái được và được hỏi lại ở lần dừng sau

**Trạng thái:** Xong (02/10)

- `edge_agent/perception/enrollment.py`: trạng thái `consent` (đang hỏi) và `later` (đã chọn "Để sau", tới lần dừng sau); `consent(agree)`. Trước khi trả lời không đo frame nào. Hỏi một lần cho mỗi tài xế: đã đồng ý thì đăng ký dở / thất bại làm lại ở lần dừng sau mà không hỏi lại; "Đổi tài xế" thì hỏi lại
- Đường bấm: HUD → `POST /vehicle` `enroll_start` / `enroll_later` (thiết bị, `main.py` áp vào `TripRuntime.enrollment_answer`) hoặc `bridge.vehicle` (web). `DecisionPipeline.enrollment_answer`
- `config/thresholds.yaml`: `enrollment.require_consent: true`. `main.py` tự tắt khi chạy không có HUD (`--hud-port 0`)
- HUD: `ConsentPanel` thay khung trạng thái khi xe đỗ và không có cảnh báo; câu chữ ở `ENROLL_CONSENT` (`labels.ts`), viết theo đúng code: không lưu ảnh, vài con số trong RAM xoá khi hết chuyến, backend chỉ nhận "đã đăng ký" + thời gian + số bước làm lại. Thẻ nhắc khi "Để sau". `#/hud-preview` thêm "Đăng ký: xác nhận"
- Test: 8 test Python mới (7 đăng ký, 1 runtime), 3 test cũ sửa theo hành vi mới; 2 test frontend; 2 kịch bản e2e bấm "Đồng ý", pass. Tổng 562 Python + 41 frontend pass, ruff / format / typecheck / build sạch

<a id="m25"></a>

#### M25: Cúi nhìn xuống không còn bị hiểu là nhắm mắt (khối 7, 8)

**Xong là thấy gì:** Cúi nhìn điện thoại / bảng đồng hồ khi xe chạy: L2 "Nhìn về phía trước" thay vì L3 "Mở mắt! Dừng xe nghỉ ngay"; nhắm mắt thật khi đầu gục vẫn L3

**Trạng thái:** Xong (02/10), hai ngưỡng tạm (chưa dataset nào có cảnh nhìn điện thoại)

- Chẩn đoán (chuỗi số giả qua code trước M25): mí trên hạ theo hướng nhìn (EAR ~0,5 lần mốc, eyeBlink ~0,6) nên thành "nhắm sâu". Hai đường lên L3 sau ~1,7 s: (A) đầu cúi 15–24°, dưới `eye.max_pitch_down_deg` nên mắt vẫn được đánh giá; (B) cúi chậm quá 25°, mí hạ ≥ 0,5 s trước đó nên "mang theo khi gục". L2 nhìn lệch có bật nhưng L3 lấn át. eyeBlink không tách được: FL3D ngủ thật p50 0,63; SUST `n_368` (cúi 17°) 0,7
- Sửa 1: đầu cúi ≥ `drowsiness.microsleep_deep.bowed_pitch_deg` (10°) so với tư thế quen thì frame nhắm sâu cần EAR ≤ `bowed_ear_ratio` (0,35) lần mốc (FL3D ngủ thật khi cúi: EAR p90 0,33–0,41 lần mốc)
- Sửa 2: chỉ "mang theo khi gục" khi lần nhắm trước đó là nhắm sâu (đếm theo cả lần nhắm, mặt nạ ngáp / nói không xoá)
- Sửa 3: `DrowsinessState.gaze_down` (đầu cúi, mí hạ, chưa nhắm chặt) → khối 8 tính là nhìn khỏi đường, mốc "nhìn đường" không học từ các frame đó
- Replay (chỉ bật / tắt cách sửa): FL3D L3 đúng 81 / sai 1 không đổi, nhắm ≥ 1,5 s lên L3 72/95 không đổi, thêm 3 L2 nhìn lệch trong đoạn buồn ngủ; YawDD tổng báo sai 10 → 10 (microsleep 5 → 4, L1 buồn ngủ 2 → 0, nhìn lệch 9 → 10); SUST tỉnh táo 8,5 → 8,8 / giờ (+1 nhìn lệch), L3 sai 2 → 2
- Việc còn lại (tự ghi số để chốt ngưỡng, `eyeLookDown`, đường CNN, ca EAR rất thấp khi nhìn xuống) ở docs/improvements.md việc 5
- Test: 5 test mới (4 kịch bản pipeline: cúi nhìn xuống → L2 không L3, cúi chậm không mang theo, nhắm thật khi cúi vẫn L3, nhắm rồi gục chậm vẫn mang theo; 1 test khối 8). Tắt `bowed_pitch_deg` thì 2 kịch bản đầu đỏ lại. Tổng 567 Python pass, ruff / format sạch

<a id="m26"></a>

#### M26: Mất tín hiệu xe khi đang chạy không còn bị coi là đỗ; báo tài xế (khối 10, 13)

**Xong là thấy gì:** Tắt công cụ mô phỏng khi xe đang chạy: HUD báo "Mất tín hiệu xe: vẫn giám sát như đang chạy" kèm âm báo, vẫn giám sát như đang chạy (nhắm mắt vẫn L3); backend nhận sự kiện, tổng kết có thời gian mất tín hiệu

**Trạng thái:** Xong (02/10) (việc 1 trong docs/improvements.md, FMEA dòng 2)

- `ExternalVehicle` (`edge_agent/context/can_sim.py`): `signal_lost` = không có số mới quá `context.vehicle_signal_stale_s` mà lần đọc cuối ≥ `context.stationary_kmh`. Khi đó tốc độ `None` (không biết), khối 10 coi là đang chạy (`assume_moving_when_speed_unknown`), không thành "nghỉ"; thời gian lái vẫn cộng. Lần đọc cuối là đỗ hoặc chưa từng có tín hiệu: vẫn 0 km/h như M19
- `TripRuntime`: sự kiện hệ thống `vehicle_signal_lost` / `vehicle_signal_restored`, `vehicle_signal_lost_s` trong bản tổng kết (đếm theo thời gian frame); HUD `vehicle.signal_lost`, `speed_kmh: null`
- Bổ sung theo yêu cầu (02/10): mất tín hiệu **lúc đỗ** cũng báo tài xế (`ExternalVehicle.link_lost`; dải vàng "coi như đang đỗ đến khi có lại tốc độ", cùng âm báo, có sự kiện); xe vẫn là đỗ, khi có lại tốc độ thì biết xe đang chạy
- Backend: 2 lý do hệ thống mới; `vehicle_signal_lost_s` tuỳ chọn trong bản tổng kết (agent cũ không gửi vẫn nhận). Dashboard: dòng "Giám sát được" thêm thời gian mất tín hiệu
- HUD: dải xe hiện "Mất tín hiệu xe: vẫn giám sát như đang chạy" (vàng), tốc độ "–"; âm báo to riêng khi mất, nhẹ khi có lại. `#/hud-preview` thêm "Mất tín hiệu xe"
- Test: 5 test Python mới (nguồn tín hiệu: mất khi chạy / khi đỗ; runtime: mất lúc đỗ vẫn báo; runtime: 5 phút mất tín hiệu ở 60 km/h vẫn L3, có sự kiện, tổng kết 299 s; backend: lý do mới, trường tuỳ chọn), 2 test cũ sửa theo hành vi mới; 2 test frontend. Tổng 572 Python + 43 frontend + 2 e2e pass, ruff / typecheck / build sạch

<a id="m27"></a>

#### M27: Bảng tổng kết không còn tính bước nhắm mắt của đăng ký (và lúc nghỉ đỗ xe) là ngủ gật (khối 11)

**Xong là thấy gì:** Đăng ký rồi kết thúc chuyến: đánh giá "Tốt", 0 lần ngủ gật; microsleep ở đèn đỏ vẫn được tính

**Trạng thái:** Xong (02/10) (việc 1 trong docs/improvements.md; lỗi tìm ra ở M21)

- Nguyên nhân: pipeline đã không đánh giá buồn ngủ trong bước nhắm mắt của đăng ký (+ `reopen_grace_s`) và lúc nghỉ đỗ xe (`context.rest_after_s`), và trip memory đã bỏ qua các frame đó (`observed`). Nhưng bản tổng kết (`TripCollector`) không nhận cờ này, nên vẫn đếm `microsleep`, lần nhắm dài nhất và điểm buồn ngủ từng phút; luật đánh giá thấy `microsleeps > 0` nên xếp "rủi ro: nhắm mắt ngủ gật khi đang lái" dù 0 giây lái
- Sửa: `DecisionResult.observed` (cùng cờ đưa cho trip memory); `TripCollector` bỏ qua sự kiện buồn ngủ (microsleep, ngáp, gục, nhướn mày), lần nhắm dài nhất và điểm từng phút ở các frame đó. Thời gian, cảnh báo, độ phủ vẫn đếm như cũ
- Cùng một nguyên nhân nên sửa luôn trường hợp nghỉ đỗ xe nhắm mắt (trước cũng bị tính là ngủ gật). Microsleep ở đèn đỏ (đứng yên nhưng chưa là "nghỉ") vẫn tính
- Test: 3 test mới (đăng ký rồi tổng kết: 0 microsleep, "Tốt"; nghỉ đỗ xe nhắm mắt 5 s: 0 microsleep; đèn đỏ: vẫn 1 microsleep, "rủi ro"); 2 test đầu đỏ trước khi sửa. Tổng 575 Python + 2 e2e pass, ruff / format sạch. Eval không đổi (công cụ eval cho xe chạy 60 km/h, không đăng ký, không nghỉ)

<a id="m28"></a>

#### M28: Báo khi vòng xử lý dừng hoặc chậm (khối 13, 14, `TripRuntime`)

**Xong là thấy gì:** Lỗi frame liên tục ≥ 1 s: HUD "Lỗi xử lý" + âm báo to, backend nhận `agent_error`; HUD đứng hình / mất kết nối có âm báo; FPS < 14,5 trong 5 s: chip "Máy chậm"

**Trạng thái:** Xong (02/10) (việc 1 trong docs/improvements.md, FMEA dòng 3, 9)

- `edge_agent/main.py`, `edge_agent/web/bridge.py`: bắt lỗi từng frame (khối 2–14), chạy tiếp, gọi `TripRuntime.frame_failed` (chỉ tên lớp lỗi, in log trên máy một lần mỗi đợt)
- `TripRuntime`: lỗi liên tục ≥ `hud.processing_error_s` (1 s) → HUD `processing_error`, sự kiện `agent_error`; frame tốt → `agent_recovered`. FPS làm mượt < `hud.low_fps_below` (14,5) liên tục `hud.low_fps_s` (5 s) → HUD `low_fps`, sự kiện `low_fps` kèm `metrics.fps`; hồi lại → `fps_restored`. 15 FPS đúng mức tối thiểu không bị coi là chậm
- Backend: 4 lý do hệ thống mới, `metrics.fps`. HUD: trạng thái "Lỗi xử lý" (màn hình không giám sát), âm báo to `monitoring_stopped` khi vào "Lỗi xử lý" / "Không nhận dữ liệu" / "Mất kết nối" (không kêu sau khi kết thúc chuyến), chip "Máy chậm". `#/hud-preview` thêm 2 trạng thái
- Chưa làm: hạ tải khi máy chậm (chờ hub); nhịp "còn sống" lên backend khi tiến trình chết hẳn
- Test: 5 test Python (lỗi ngắn bỏ qua / lỗi kéo dài báo rồi hồi; FPS thấp báo rồi hết; 15 FPS không thấp; bridge web không ném lỗi ra trang; backend nhận lý do mới), 2 test frontend. Tổng 580 Python + 45 frontend + 2 e2e pass, ruff / typecheck / build sạch

<a id="m29"></a>

#### M29: Cập nhật tài liệu theo v2: README, sơ đồ kiến trúc, HowToUse

**Xong là thấy gì:** README mở đầu bằng DriverGuard; sơ đồ có phần v2; HowToUse có luồng một chuyến đi và các trạng thái không giám sát

**Trạng thái:** Xong (02/10) (việc 2 trong docs/improvements.md)

- `README.md`: phần DriverGuard ở đầu (là gì, phiên bản, sản phẩm cuối là APK trên hub, URL web, luồng một chuyến đi, bảng tài liệu, chạy nhanh); README của template khoá giữ phía dưới cho phần cài hook / nộp bài
- `docs/architecture_diagram.md`: mục 5 "Phần thêm ở v2" (sơ đồ: nguồn tín hiệu xe, `TripRuntime`, đăng ký, tổng kết chuyến, sức khoẻ vòng lặp, các đường HUD → agent), ghi chú deploy v2 và hướng APK, 5 dòng mới trong bảng thành phần
- `HowToUse.md`: mục 2.5 "Một chuyến đi ở v2" (đồng ý + đăng ký, cảnh báo, cúi nhìn xuống, đổi tài xế, báo sai, kết thúc chuyến + báo cáo) và bảng các trạng thái HUD khi không giám sát được; bảng trạng thái dự án thêm M8, M9–M29
- Chỉ tài liệu, không đổi code

