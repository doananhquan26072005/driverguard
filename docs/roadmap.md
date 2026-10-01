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

### Version 2: cải tiến (M9–M18)

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

### Version 2: cải tiến (M9–M18)

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

