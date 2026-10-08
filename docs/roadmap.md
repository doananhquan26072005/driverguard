# Lộ trình DriverGuard

Mỗi lần chỉ làm đúng một mốc được yêu cầu (CLAUDE.md). Làm xong thì cập nhật dòng của mốc đó ở
**Tổng quan** và thêm phần **Chi tiết** bên dưới. Những gì đã thêm / sửa / bỏ ở v2 cũng ghi trong
[release-v2.md](release-v2.md), từ M32 (05/10) ghi trong [release-v3.md](release-v3.md); việc chưa làm nằm ở
[improvements.md](improvements.md).

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

### Version 2: cải tiến (M9–M31)

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
| [M30](#m30) | Xe đứng yên (0 km/h) thì không có cảnh báo nào (khối 9) | Dừng xe rồi nhắm mắt / cầm điện thoại: không có chuông; chạy lại thì nhắm mắt vẫn L3 | ✅ Xong · 02/10 |
| [M31](#m31) | Trang điều khiển xe trên web `#/drive` (khối 10, backend, frontend) | `#/live` hiện "Điều khiển xe · mã …"; mở `#/drive?code=…` (cả trên máy khác) để tăng / giảm tốc, dừng, xi nhan; `#/live` chạy theo | ✅ Xong · 02/10 |

### Version 3 (M32–M51)

| Mốc | Làm gì | Xong là thấy gì | Trạng thái |
|---|---|---|---|
| [M32](#m32) | Leo thang cảnh báo theo thời gian: L1 lặp lại thì nâng L2 (khối 12) | Cùng một lý do L1 báo lần thứ 3 trong 10 phút: lần đó là L2 "Đã nhắc nhiều lần: hãy dừng nghỉ"; một L1 đơn lẻ không đổi | ✅ Xong · 05/10 |
| [M33](#m33) | Nhịp "còn sống" và tổng quan đội xe (khối 14, backend, dashboard) | Dashboard có tab "Đội xe": xe nào đang hoạt động, xe nào mất liên lạc, xe nào đã kết thúc chuyến, cảnh báo trong ngày, sự kiện gần nhất | ✅ Xong · 05/10 |
| [M34](#m34) | Test hồi quy bằng trace trong CI (khối 5, 7–12) | Đổi logic hay ngưỡng làm lệch sự kiện / cảnh báo / `drowsy_score` trên 36 video cố định thì `pytest` đỏ, kèm lệnh cập nhật có lý do | ✅ Xong · 05/10 |
| [M35](#m35) | Prototype offline: thời lượng chớp mắt so với chính tài xế (khối 7, chỉ đo) | Báo cáo `eval/results/blink_duration_fl3d.md` trả lời có nên thêm `duration_ratio` hay không | ✅ Xong · 05/10 (kết luận: không thêm) |
| [M36](#m36) | Trang tiêu chí sẵn sàng pilot; cột "Nhận định" trong bảng kết quả | `docs/pilot-readiness.md`: 24 tiêu chí có mục tiêu, số hiện có, trạng thái; lộ trình 4 giai đoạn | ✅ Xong · 05/10 |
| [M37](#m37) | Chính sách dữ liệu và tự xoá theo thời hạn (backend, HUD, dashboard) | `docs/data-policy.md`; cảnh báo cũ hơn 60 ngày và tổng kết cũ hơn 365 ngày tự xoá; lệnh xoá dữ liệu một tài xế; màn hình đồng ý ghi thời hạn | ✅ Xong · 05/10 |
| [M38](#m38) | Khối 8: liếc ngắn cộng dồn (chỉ đo), tách gọi điện / nhắn tin (chỉ ghi), quay hẳn đi rồi mất mặt (khối 4, 8, 9, 11, 14) | Bảng tổng kết chuyến có số lần liếc khỏi đường, thời gian gọi / nhắn tin, thời gian "quay hẳn đi"; quay ra sau 10 s thì HUD giữ L2 "Nhìn về phía trước" thay vì "tạm ngưng giám sát" | ✅ Xong · 06/10 (ngưỡng tạm) |
| [M39](#m39) | Công cụ ghi số trực tiếp từ camera kèm nhãn bấm phím, không lưu ảnh (`tools/record_trace.py`) | `record` mở camera, bấm phím đánh dấu hành động, lưu trace số; `report` ra bảng độ trễ cảnh báo p50 / p95, báo sai, so nhìn xuống với nhắm mắt, so có / không khẩu trang | ✅ Xong (công cụ) · 06/10 · chưa có bản ghi thật |
| [M40](#m40) | Đo offline trên trace sẵn có: PERCLOS P80, theo ánh sáng / kính, cá nhân hoá, theo từng người (khối 7 chỉ đo, `tools/trace_studies.py`, `tools/eval.py`) | Bốn báo cáo mới trong `eval/results/`; `perclos_p80_60s` đo song song với `perclos_60s`; bảng "Per person" và "start-up apart" trong báo cáo eval | ✅ Xong · 06/10 |
| [M41](#m41) | Phiên bản trên nhịp "còn sống" và sự kiện, tag `simulated` / `forced`, nhật ký truy cập (khối 14, backend, dashboard) | Tab "Đội xe" có cột "Phiên bản", tô xe đang chạy bộ ngưỡng cũ; admin có tab "Nhật ký truy cập", tài xế có tab "Ai đã xem dữ liệu của tôi" | ✅ Xong · 06/10 |
| [M42](#m42) | Chạy dài đo CPU / RAM / FPS, image edge và container giới hạn kiểu Jetson, bảng lượng tử hoá (`tools/benchmark.py`, `tools/edge_sim.py`, `Dockerfile.edge`) | `eval/results/benchmark_simulated.md` có bảng máy dev và hai hồ sơ giới hạn gắn nhãn `simulated`; `eval/results/quantization.md` | ✅ Xong · 06/10 (chưa có thiết bị thật) |
| [M43](#m43) | Điểm chất lượng frame: ảnh không đọc được thì "tạm ngưng giám sát" có lý do (giai đoạn của khối 6, khối 9, 13, 14) | Che camera, mặt quá tối / quá chói / ảnh mờ ≥ 5 s khi xe chạy: HUD nói rõ lý do và việc cần làm thay vì đoán; sự kiện và bản tổng kết ghi lý do | ✅ Xong · 06/10 (ngưỡng tạm) |
| [M44](#m44) | Không phản ứng với còi, ngủ gật lặp lại, "Bạn còn ở đó không?"; quản lý được báo ngay (khối 9, 12, 13, 14, backend, dashboard) | Nhắm mắt ≥ 6 s: cảnh báo L3 thứ hai `unresponsive`; mất mặt 8 s: HUD hỏi, 10 s không chạm thì `no_answer`; tab "Đội xe" có mục "Cần chú ý ngay" kèm tiếng | ✅ Xong · 06/10 (ngưỡng tạm) |
| [M45](#m45) | Giảm dung lượng tải lần đầu của `#/live`: bỏ OpenCV khỏi bản web, server nén và đặt cache | Lần đầu tải khoảng 30 MB qua mạng thay vì 42 MB; lần sau file không đổi chỉ tốn một lượt hỏi lại | ✅ Xong · 06/10 (YOLO INT8 chờ đo độ chính xác) |
| [M46](#m46) | Cùng video, ánh sáng khác: làm tối / chói / xám / mờ trong RAM (`tools/light_study.py`) | `eval/results/lighting_transforms.md`: mức nào hệ thống chuyển sang tạm ngưng, mức nào nó im lặng mà sai | ✅ Xong · 06/10 (phát hiện lỗ hổng ở khối 5, chưa sửa) |
| [M47](#m47) | Ngưỡng từ dashboard: tải lại trong chuyến, chỉ áp khi xe đỗ; áp thử cho vài xe; quay lui (khối 14, backend, dashboard) | Lưu ngưỡng cho vài xe thử, xem số báo sai theo phiên bản, bấm "Áp cho cả đội"; xe nhận khi đỗ và gửi `config_applied` | ✅ Xong · 06/10 (OTA model chưa làm) |
| [M48](#m48) | Dữ liệu của tài xế: tự tải về, yêu cầu xoá từ giao diện; database và image; hai mẫu giấy tờ (backend, dashboard, docs) | Tài xế có tab "Dữ liệu của tôi" (tải file JSON, yêu cầu xoá); admin duyệt; `docs/dpia-template.md`, `docs/driver-notice-template.md` | ✅ Xong · 06/10 |
| [M49](#m49) | Tốc độ bản web: công cụ đo khối 6–14 trong Pyodide, `solve_pnp` nhanh hơn, đồng hồ từng chặng của vòng lặp `#/live` (khối 6, 13, 14, backend, dashboard, `tools/bench_web.py`) | `eval/results/benchmark_web.md` có số trước / sau (1,97 → 0,61 ms / frame); "Chi tiết kỹ thuật" của `#/live` và cột "Tốc độ xử lý" ở tab "Đội xe" hiện thời gian từng chặng | ✅ Xong · 06/10 (chưa đo trên Android / hub) |
| [M50](#m50) | Bản web: báo khi model điện thoại không còn cho kết quả, đẩy cảnh báo cho HUD ngay, giờ chụp của frame, tải song song khi khởi động; sửa lỗi frame không có mặt (khối 4, 13, 14, `TripRuntime`, `#/live`) | YOLO chậm hoặc không tải được: HUD hiện "Không phát hiện được điện thoại", backend nhận `phone_detection_lost`; âm thanh cảnh báo của `#/live` không chờ vòng hỏi 300 ms; che camera không còn thành "Lỗi xử lý" | ✅ Xong · 06/10 (ngưỡng tạm; chưa đo độ trễ tới loa) |
| [M51](#m51) | Bản web: model mặt chỉ chạy "GPU" khi có GPU thật, YOLO hai luồng trên trang được cách ly, công cụ đo vòng lặp trong trình duyệt (khối 3, 4, `backend/static.py`, `frontend/bench/live.bench.mjs`) | `eval/results/benchmark_live.md`: máy không có GPU thật 20 → 30 FPS (model mặt 45 → 9 ms), YOLO 172 → 91 ms mỗi lần; "Chi tiết kỹ thuật" ghi WebGL là GPU thật hay vẽ bằng phần mềm | ✅ Xong · 06/10 (đo trong Chromium trên Mac; chưa đo WebView / hub) |
| [M52](#m52) | Bản ghi đầu tiên từ camera: ba phiên ban ngày của một người, có nhãn bấm phím (`eval/results/own_recordings.md`) | Bảng độ trễ cảnh báo thật: ngủ gật p95 1,67 s, điện thoại 2,30–2,77 s, quay đầu 2,83–3,04 s; cúi nhìn điện thoại trên đùi bị báo nhầm là ngủ gật 3 / 4 lần; nhìn bảng đồng hồ không được thấy 0 / 3 | 🟡 Một phần · 06/10 (13 phiên của một người, phân tích ở M54; còn thiếu người thứ hai, liếc bằng mắt, cúi nhẹ kèm nhắm mắt; phiên chói và kính râm đã bỏ) |
| [M53](#m53) | UTA-RLDD: trace 145 video trên Kaggle, chia dev / test theo người, dò ngưỡng và ablation, đo cá nhân hoá; chớp chậm và nhướn mày không còn cộng vào điểm, luật `trend` chỉ ghi nhận (khối 9, `config/thresholds.yaml`, `tools/uta_rldd.py`, `notebooks/uta_rldd_kaggle.ipynb`) | `eval/results/dataset_uta_rldd.md`: trên 24 người giữ riêng, cảnh báo sai nhánh buồn ngủ 8 → 4 lần (1,96 → 0,98 / giờ), số người buồn ngủ đạt L3 không đổi (12 / 24) | ✅ Xong · 06/10 (ngưỡng đổi theo dữ liệu người ngồi trước laptop; chỉ tiêu PRD ≤ 1,0 / giờ chưa kết luận được: cận trên CI 2,51) |
| [M54](#m54) | Nhóm việc 1 của improvements trên các phiên tự ghi: mặt tối thì EAR quyết định thay cho CNN mắt; kết luận INT8; đo nhìn xuống, hướng mắt, cách cầm điện thoại (khối 5, `config/thresholds.yaml`, `tools/record_trace.py`) | Phòng tối vừa (mặt 32–35): ngồi yên mắt mở không còn bị hú còi ngủ gật (8 lần L3 sai → 0), nhắm mắt vẫn L3 27 / 27; `eval/results/own_recordings.md` có 12 phiên | ✅ Xong · 06/10 (ngưỡng tạm, một người; nhìn xuống bị báo ngủ gật chưa sửa được: ngưỡng theo tài xế có sẵn nhưng tắt) |
| [M55](#m55) | Hướng mắt nhìn xuống, chỉ đo: `iris_y` ở khối 6, góc nhìn xuống (góc cúi đầu + mống mắt) và thời gian giữ ở khối 8; đo trên 3MDAD (`tools/gaze_study.py`) | `eval/results/gaze_3mdad.md`: 50 tài xế trong xe thật, 16 hành động; trace có thêm `gaze_down_deg`, `gaze_down_s`; không cảnh báo nào đổi | ✅ Xong · 06/10 (chỉ đo; chưa đủ để thành cảnh báo) |
| [M56](#m56) | Phần làm được ngay của nhóm việc 1: `eyeBlink` có ngưỡng riêng ở khối 7 cho bản web / APK; mốc mống mắt theo tài xế từ bước đăng ký; bốn phép đo không đổi code (khối 5, 6, 7, 8, `config/thresholds.yaml`) | Bản web với camera xám / hồng ngoại: nhắm mắt đạt L3 0 / 48 → 46 / 48 trên bản tự ghi, FL3D 0 / 95 → 64 / 95 (replay); bản thiết bị không đổi | ✅ Xong · 07/10 (ngưỡng tạm: replay trên video màu, chưa đo trên `#/live`, chưa có ảnh IR thật) |

### Version 4: thiết kế lại giao diện (M57–M65)

**Xong cả 9 mốc (07/10)**; e2e `live.e2e.ts` 4 / 4 pass (07/10). Theo hai bản thiết kế: HUD (21 màn hình, "DriverGuard HUD redesign") và web (10 màn hình, "DriverGuard Web redesign").
Nguyên tắc chung: chỉ đổi giao diện (`frontend/`); backend, edge agent và API giữ nguyên; không đổi logic cảnh báo;
tính năng đang có mà thiết kế chưa vẽ thì giữ lại và vẽ theo phong cách mới, không bỏ. Ô nào của bản thiết kế cần dữ liệu
mà backend / edge agent chưa gửi thì ẩn hoặc điều chỉnh cho hợp. Ngoại lệ duy nhất là M65 (07/10): edge agent gửi thêm
cho HUD các số nó đã giữ sẵn (đọc ra, không đổi logic cảnh báo, không đổi backend / API).

| Mốc | Làm gì | Xong là thấy gì | Trạng thái |
|---|---|---|---|
| [M57](#m57) | Nền giao diện chung: màu, font Inter tự đóng gói (không dùng Google Fonts vì HUD có thể không có mạng), cỡ chữ, nút, thẻ "kính"; sửa các lỗi tương phản của bản thiết kế (nền trắng trong giao diện tối, chữ đen trong ô nhập, màu cam tối trên nền tối) | Một bộ token dùng chung cho HUD và web; `#/hud-preview` và dashboard đổi sang nền tối mới; số FPS của `#/live` trước / sau không giảm dưới 15 | ✅ Xong · 07/10 (blur chưa dùng ở HUD / `#/live`: đo lại ở M58) |
| [M58](#m58) | HUD khi đang lái: bình thường, Chú ý (buồn ngủ, mệt tăng dần), Cảnh báo (điện thoại, nhìn lệch), Nguy hiểm; các biến thể chưa có tiếng, máy chậm, chưa đăng ký (khối 13) | `#/hud` và `#/hud-preview` hiện đúng các màn hình đang lái của bản thiết kế, dùng cả dữ liệu M65 (lái liên tục, biểu đồ 15 phút, chi tiết cảnh báo) | ✅ Xong · 07/10 (kèm 2 đợt sửa theo góp ý) |
| [M59](#m59) | HUD sự cố, đăng ký và kết thúc chuyến: mất camera, lỗi xử lý, mất kết nối, tạm ngưng, mất tín hiệu xe, đỗ chưa có tín hiệu; xin đồng ý + 3 bước đăng ký; tổng kết chuyến. Vẽ thêm theo phong cách mới các trạng thái bản thiết kế thiếu: "Bạn còn ở đó không?" (M44), lý do tạm ngưng tối / chói / che camera (M43), mất phát hiện điện thoại (M50), đăng ký thất bại / "Để sau" (khối 13) | Mọi trạng thái của HUD hiện tại đều có màn hình mới, không trạng thái nào quay về giao diện cũ hay bị bỏ | ✅ Xong · 07/10 (làm dần cùng các đợt sửa M58) |
| [M60](#m60) | Một trang đăng nhập chung, sau đăng nhập mỗi vai trò vào trang chủ và menu riêng (thay thanh tab hiện tại); thời hạn giữ dữ liệu lấy từ `/api/v1/policy`, không ghi cứng | Đăng nhập bằng tài xế / quản lý / kỹ sư / admin vào đúng trang chủ của mình; link "Chạy thử bằng camera" sang `#/live` | ✅ Xong · 07/10 (Tổng quan tài xế / quản lý, Tài khoản / Thiết bị tạm dùng trang cũ: M61–M63) |
| [M61](#m61) | Trang tài xế: tổng quan (chuyến gần nhất, 30 ngày qua, gợi ý), chi tiết chuyến, lịch sử cảnh báo; giữ "Dữ liệu của tôi" (tải về, yêu cầu xoá, ai đã xem, M41 / M48) | Tài xế chỉ thấy dữ liệu của mình theo bố cục mới, không mất tính năng nào của M48 | ✅ Xong · 07/10 (Lịch sử cảnh báo / Dữ liệu của tôi giữ bảng cũ trong khung mới) |
| [M62](#m62) | Trang quản lý: tổng quan đội xe (việc cần xử lý, từng xe), duyệt báo cáo chuyến; vẽ mới Nhật ký sự kiện, Timeline mệt mỏi, Đội xe chi tiết (phiên bản, tốc độ xử lý, M41 / M49) | Quản lý thấy "Cần xử lý" (M44) và đánh dấu đã xem báo cáo ở giao diện mới | ✅ Xong · 07/10 (Nhật ký sự kiện, Timeline, Đội xe chi tiết giữ bảng cũ trong khung mới) |
| [M63](#m63) | Trang kỹ sư và admin: ngưỡng + tỉ lệ báo sai theo lý do, giữ áp thử / lịch sử phiên bản / quay lui (M47); tài khoản, thiết bị, nhật ký truy cập, duyệt yêu cầu xoá (M41 / M48). Backend không đổi: trang Thiết bị chỉ có tạo thiết bị + hiện khoá một lần (chưa có API danh sách) | Kỹ sư sửa ngưỡng ở giao diện mới; admin tạo tài khoản / thiết bị và thấy khoá thiết bị đúng một lần | ✅ Xong · 07/10 (danh sách thiết bị lấy từ API đội xe, backend không đổi) |
| [M64](#m64) | `#/live`: thiết lập (ai đang lái, đăng ký, bắt đầu), đang tải; vẽ mới màn hình đang chạy và `#/drive` | `#/live` từ lúc mở tới lúc kết thúc chuyến dùng giao diện mới; FPS không giảm dưới 15 | ✅ Xong · 07/10 (21 FPS; e2e 4 / 4 pass) |
| [M65](#m65) | Dữ liệu HUD từ edge agent (khối 1, 11, 13, 14): thời gian lái liên tục, độ mệt 15 phút gần nhất, số liệu sau mỗi cảnh báo, sự cố từ lúc nào / số lần thử mở lại camera / backend đã nhận sự kiện chưa | Tải lại HUD vẫn thấy ngay đúng số của chuyến (số nằm trong edge agent, không nằm trong trình duyệt); bản tổng kết chuyến không đổi | ✅ Xong · 07/10 (chưa có giao diện: M58 / M59 hiện) |
| [M67](#m67) | Tốc độ vòng lặp `#/live` trên trình duyệt máy tính: YOLO chạy bằng WebGPU khi có GPU thật, chạy đúng nhịp cấu hình và nhận frame trước MediaPipe; vòng lặp không chờ YOLO lúc khởi động; công cụ đo cả lần chạy và chạy dài; đo nhánh điện thoại trên 3MDAD (khối 4, `frontend/src/live/`, `frontend/bench/live.bench.mjs`, `tools/phone_study.py`) | `eval/results/benchmark_live.md` mục 4–5: có GPU thật YOLO 94 → 17 ms mỗi lần, tuổi kết quả p95 333 → 131 ms, CPU của trang 109 → 32 % một nhân; không có GPU 329 → 274 ms; khởi động với cache trống 2,66 → 2,08 s. "Chi tiết kỹ thuật" ghi "WebGPU" hoặc số luồng | 🟡 Xong phần code · 08/10 (đo trong Chromium không giao diện trên một máy Mac, camera giả; **chạy dài 10 phút: bản mới FAIL 2 lần đầu, đạt 2 lần chạy lại, nguyên nhân chưa xác định**; mục tiêu tuổi p95 < 250 ms chưa đạt khi không có GPU; số frame bị bỏ không đổi) |
| [M68](#m68) | Đăng ký xong thì điểm buồn ngủ bắt đầu từ 0: điểm đọc 0 trong bước nhắm mắt, khối 7 bỏ mọi thứ đã gom trước đó, trip memory bỏ phần gom từ lúc xe dừng (khối 7, 9, 11, `edge_agent/decision/pipeline.py`) | Đăng ký khi đỗ: `drowsy_score` là 0 ở mọi frame (trước đó nhảy lên 25 trong bước nhắm mắt); nhắm mắt 1,5 s trước khi đăng ký không còn để lại PERCLOS hay 25 điểm trong 5 phút | ✅ Xong · 08/10 |
| [M69](#m69) | Đọc số UTA-RLDD thêm ba cách, không đổi ngưỡng: khoảng tin cậy báo sai / giờ lấy mẫu lại theo người, một điểm làm việc cố định kèm đường đánh đổi theo `risk.drowsy.l1`, đơn vị + tỉ lệ dương ở mỗi bảng, bảng điểm → tỉ lệ phút buồn ngủ (công cụ eval: `tools/metrics.py`, `tools/uta_rldd.py`, `tools/eval.py`, `tools/dataset.py`) | `eval/results/dataset_uta_rldd.md` mục 8 và `uta_rldd_tradeoff.md`: ở ngưỡng hiện tại, 24 người giữ riêng có 0,98 báo sai / giờ (lấy mẫu lại theo người 0,00–3,02), 15 / 24 người buồn ngủ có cảnh báo, 12 / 24 đạt L3; cả 4 lần báo sai là của 1 người; mỗi bảng ghi đơn vị và tỉ lệ dương | ✅ Xong · 08/10 (không đổi ngưỡng, không đổi hành vi) |
| [M70](#m70) | Số liệu đúng phạm vi (audit 08/10, mục 6.1 việc 1): báo sai nhánh buồn ngủ và mọi nhánh đếm cạnh nhau, nhóm theo FPS của video, luật chấm định trước và nhật ký đọc tập test, báo cáo FL3D / YawDD / SUST chạy lại, sửa `report.md`, `pilot-readiness.md` (công cụ eval: `tools/uta_rldd.py`, `tools/metrics.py`, `tools/seq_eval.py`; `eval/splits/`) | `dataset_uta_rldd.md` mục 9: cùng 24 người giữ riêng, 0,98 là báo sai **nhánh buồn ngủ**; mọi nhánh cả video là 1,2 / giờ (cận trên 2,7); 6 trong 9 lần báo sai nhánh buồn ngủ nằm ở 2 video dưới 15 FPS; `eval/splits/README.md` định luật chấm; báo cáo `dataset_fl3d.md`, `dataset_yawdd.md`, `dataset_sust_ddd.md` có dòng nguồn gốc và ngưỡng hôm nay | ✅ Xong · 08/10 (không đổi ngưỡng, không đổi hành vi) |
| [M71](#m71) | Vòng lặp `#/live` tự hồi phục, và khoảng hở giữa hai frame không còn bị nối thành một đợt (audit 08/10, mục 6.1 việc 3): đồng hồ canh theo `capture.frame_timeout_s`, tự xin lại camera, lỗi frame phía trang đi vào `frame_failed`; khối 7, 8, 12 đếm lại từ đầu sau khoảng hở quá `max_gap_s` (khối 1, 7, 8, 12, `frontend/src/live/`, `edge_agent/web/bridge.py`) | Trên `#/live`: trình duyệt ngừng gọi vòng lặp thì sau 3 s nó tự chạy lại; camera kết thúc thì HUD hiện "Mất camera · Lần thử 1" rồi giám sát lại, không cần tải lại trang; chớp mắt ở hai đầu một lần đứng 2 s không còn là còi L3 | ✅ Xong · 08/10 (chạy 10 phút: 2 / 2 lượt đạt nhưng không lượt nào bị đứng, nên đường tự chạy lại mới được chứng minh bằng e2e; M67 vẫn 🟡; chưa thử webcam thật, Android WebView) |
| [M72](#m72) | Đóng các trạng thái ngừng giám sát mà không ai được báo (audit 08/10, mục 6.1 việc 2): mặt lọt một phần khỏi khung (`bad_angle`) được tính giờ thành "tạm ngưng", "đang nhìn lệch" chỉ được giữ tối đa `distraction.pose_hold_s` khi không còn tư thế, "tạm ngưng" chạy cả ở 1–5 km/h, HUD không còn nút một chạm nào tắt hoặc che giám sát (khối 8, 9, 10, 13; `frontend/src/hud/`, `frontend/src/live/`) | Chuỗi số giả 60 km/h, mặt lọt một phần 60 s: sau 5 s HUD hiện "Tạm ngưng giám sát · camera lệch" (trước: mức 0, không báo gì). Ở 3 km/h mất mặt 3 s cũng "tạm ngưng". Trên `#/live` không còn nút "Chạy mô phỏng" và liên kết Dashboard; "Dừng camera" hỏi lại rồi kết thúc chuyến có tổng kết; rời trang giữa chuyến thì có tiếng báo và chuyến được kết thúc | ✅ Xong · 08/10 (thêm 1 khoá ngưỡng tạm `distraction.pose_hold_s` = 3 s; replay các trace hiện có không đổi số cảnh báo; chưa bấm thử trên giao diện bằng tay, chưa có dữ liệu camera đặt lệch) |
| [M73](#m73) | Ngữ cảnh quanh điểm buồn ngủ (audit 08/10, mục 6.1 việc 5): "lái lâu" tính trên thời gian lái liên tục của tài xế đang lái (về 0 khi nghỉ và khi "Đổi tài xế", cùng bộ đếm với HUD), xe chạy lại sau lần dừng từ `context.short_stop_forget_s` (10 s) thì bỏ phần gom lúc dừng, replay chọn được giờ và thời gian đã lái (khối 9, 10, 11, `edge_agent/decision/pipeline.py`, `tools/seq_eval.py`, `tools/uta_rldd.py`, `tools/eval.py`) | Chuỗi số giả: sau 2 giờ lái rồi nghỉ, `long_drive` tắt và HUD "Lái liên tục" về 0 cùng lúc; dừng đèn đỏ 60 s, nhắm mắt 25 s trong đó, xe lăn bánh: không cảnh báo (trước: L1 sau 1,0 s ban ngày, L2 sau 0,5 s lúc 02:00). `tools/uta_rldd.py compare --split dev --set eval.replay_clock_hour=2 --set eval.replay_drive_time_s=7200` chạy được | ✅ Xong · 08/10 (thêm 1 khoá ngưỡng tạm `context.short_stop_forget_s` = 10 s do anh chốt, 2 khoá `eval.replay_*`; số của mọi báo cáo hiện có không đổi; đêm + lái lâu trên dev: 5 → 11 báo sai, **hai hệ số nhân chồng hay cộng trần còn chờ anh quyết**; chưa có dữ liệu nào có lần dừng) |
| [M74](#m74) | Khối 12 không còn để cooldown nuốt cảnh báo (audit 08/10, mục 6.1 việc 6): lý do còn đó khi hết cooldown thì được nhắc lại, lần nhắc được đếm vào leo thang `repeated_l1` và bộ đếm bắt đầu lại sau mỗi lần leo thang, lý do bắt đầu dưới một mức cao hơn có cảnh báo riêng khi mức hạ; "Bạn còn ở đó không?" không hỏi lặp khi mặt chập chờn (khối 12: `edge_agent/decision/alert_manager.py`, `presence.py`) | Chuỗi số giả: nhìn lệch 3 s, nhìn lại 5 s, nhìn lệch 40 s: có tiếng lần hai (trước: không); L1 đều 30 phút: L1, L1, L2, L1, L1, L2... mỗi ~2 phút (trước: 1 tiếng chuông); điểm cắt ngưỡng 18 lần trong 40 phút: 6 lần L2 (trước: 16); mặt hiện 1 frame mỗi 12 s: hỏi 1 lần (trước: 10) | ✅ Xong · 08/10 (thêm 3 khoá: `alert.remind`, `presence.back_s`, `presence.reask_after_s`, hai khoá sau là tạm; **báo sai tăng**: UTA-RLDD 24 người dùng để dò 5 → 7 lần nhánh buồn ngủ (1,29 → 1,81 / giờ), FL3D L2 sai 3 → 8; **chờ anh quyết: giữ `alert.remind: true` hay tắt, và có sinh lại `eval/results` không**; tập giữ riêng không được đọc) |
| [M75](#m75) | Hành vi dưới 15 FPS, chỉ đo (audit 08/10, mục 6.1 việc 7): replay các video UTA-RLDD quay từ 25 FPS trở lên sau khi bỏ bớt frame xuống 15 / 12 / 10 FPS, khoảng cách đều và không đều; test chuỗi số giả cho khối 7, 8, 9, 12 với tám kiểu vòng lặp (công cụ eval: `tools/seq_eval.py` `resample_trace`, `tools/uta_rldd.py fps`; `tests/test_edge_agent/test_m75_low_fps.py`) | `eval/results/fps_low_uta_rldd.md`: 59 video của 21 người dùng để dò, báo sai nhánh buồn ngủ 5 lần khi giữ nguyên, 2–7 lần ở 10–15 FPS (mỗi dòng 3 lượt, dao động giữa các lượt lớn hơn chênh lệch giữa các tốc độ); người buồn ngủ có cảnh báo 12 / 19 → 12–14, đạt L3 10 → 9–11. Chuỗi số giả: không cảnh báo nào được tạo thêm ở vòng lặp chậm, sự kiện rõ ràng trễ tối đa hai khoảng frame; nhắm mắt 1,6 s (vượt mốc L3 0,1 s) bị bỏ sót ở 10 FPS không đều | ✅ Xong · 08/10 (chỉ đo: không đổi ngưỡng, không đổi hành vi; thêm 4 khoá `eval.fps_study_*`, độ không đều 0,3 là tạm; 7 ca ghi `xfail` là chỗ vòng lặp chậm làm mất độ nhạy; khối 2–5 trên máy chậm và nhánh điện thoại chưa đo; tập giữ riêng không được đọc) |
| [M76](#m76) | Mắt díp rồi mới nhắm hẳn (audit 08/10, mục 6.1 việc 10): khi cả đợt nhắm chưa đạt tỉ lệ nhắm sâu, chuỗi frame nhắm sâu đang chạy được đếm từ frame đầu của chính nó; chuỗi đó cũng mở được phần đếm tiếp khi gục đầu (khối 7: `edge_agent/analysis/drowsiness/eyes.py`; khoá `drowsiness.microsleep_deep.run_gap_s`) | Chuỗi số giả: mí sụp 2 / 4 / 10 / 30 s rồi nhắm hẳn: còi L3 đúng 1,5 s sau khi nhắm (trước: 2,0 / 4,0 / 10,0 s, và không bao giờ với 30 s). UTA-RLDD 24 người dùng để dò: chuỗi nhắm sâu từ 1,5 s có L3 đúng lúc 45 → 47 / 50, báo sai trên video `0` không đổi; YawDD, FL3D, SUST, bản tự ghi không thêm cảnh báo sai nào | ✅ Xong · 08/10 |

### Vận hành (M66–)

| Mốc | Làm gì | Xong là thấy gì | Trạng thái |
|---|---|---|---|
| [M66](#m66) | Deploy lên Railway và tự deploy khi CI pass: `.railwayignore` gửi đúng hai model, job `deploy` trong CI (model lấy từ GitHub Release), hướng dẫn cấu hình | Merge vào `main` → CI pass → bản mới tự lên Railway; test fail thì không deploy | 🟡 Giai đoạn A, B xong · 08/10 (repo, cấu hình Railway / GitHub, deploy tay đầu tiên); chờ lần tự deploy đầu tiên từ CI |

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

<a id="m30"></a>

#### M30: Xe đứng yên (0 km/h) thì không có cảnh báo nào (khối 9)

**Xong là thấy gì:** Dừng xe rồi nhắm mắt / cầm điện thoại: không có chuông; chạy lại thì nhắm mắt vẫn L3

**Trạng thái:** Xong (02/10) (yêu cầu của anh)

- `risk.drowsy.stationary_max_level: 1 → 0` (cả giá trị mặc định trong `RiskConfig`). Dưới `context.stationary_kmh` (1 km/h) không còn luật nào lên mức; mất tập trung đã tắt dưới 5 km/h từ trước. Dấu hiệu buồn ngủ vẫn đo, vẫn vào bản tổng kết
- Đánh đổi: ngủ gật lúc dừng đèn đỏ không còn tiếng chuông (FMEA dòng 12)
- Test: 3 kịch bản mới (đứng yên nhắm mắt / nhìn đi chỗ khác cầm điện thoại: không cảnh báo; cùng lần nhắm khi chạy: L3), 3 test cũ sửa theo (đèn đỏ L1 → 0; hai test đăng ký chuyển sang "đăng ký rồi lái đi")

<a id="m31"></a>

#### M31: Trang điều khiển xe trên web `#/drive` (khối 10, backend, frontend)

**Xong là thấy gì:** `#/live` hiện "Điều khiển xe · mã …"; mở `#/drive?code=…` (cả trên máy khác) để tăng / giảm tốc, dừng, xi nhan; `#/live` chạy theo

**Trạng thái:** Xong (02/10) (việc "Trang điều khiển xe cho bản web" trong docs/improvements.md)

- Backend `backend/drive_link.py`: `PUT` / `GET /api/v1/drive/{code}` (mã 6 ký tự `A-Z0-9`), giữ tốc độ / xi nhan mới nhất trong bộ nhớ, không vào database; hết hạn 10 phút sau lần gửi cuối, tối đa 500 mã. Không cần đăng nhập (chỉ số, mã ngẫu nhiên do `#/live` tạo)
- `frontend/src/drive/`: mô hình xe giống `tools/drive_sim.py` (`sim.ts`, test so thông số với `config/drive_sim.yaml`), trang `DriveScreen` (nút to, phím W / S / Space / C / A / D / X, gửi 5 lần / s)
- `#/live`: mã ghép mỗi phiên, nút "Điều khiển xe · mã …" mở `#/drive?code=…`; mỗi 250 ms đọc kênh, số cũ hơn 1 s không dùng (thành mất tín hiệu xe, M26); không có kênh thì đọc `drive_sim` trên cùng máy như cũ
- Test: 3 test backend, 5 test frontend (mô hình xe, mã ghép), 1 kịch bản e2e (ghép mã, "Chạy đều 50" + xi nhan trái → `#/live` thấy đang chạy, rẽ trái; đóng trang điều khiển → "Mất tín hiệu xe")

### Version 3 (M32–M42)

<a id="m32"></a>

#### M32: Leo thang cảnh báo theo thời gian: L1 lặp lại thì nâng L2 (khối 12)

**Xong là thấy gì:** Cùng một lý do L1 báo lần thứ 3 trong 10 phút: lần đó là L2 "Đã nhắc nhiều lần: hãy dừng nghỉ"; một L1 đơn lẻ không đổi

**Trạng thái:** Xong (05/10) (việc 14 trong docs/improvements.md)

- `AlertManager` (`edge_agent/decision/alert_manager.py`): đếm các cảnh báo L1 **đã phát** theo từng lý do. Lần thứ `alert.l1_repeat_count` (3) của cùng một lý do trong `alert.l1_repeat_window_s` (600 s) được phát ở L2, thêm lý do `repeated_l1`. Mức hiển thị là L2 trong `fall_hold_s` rồi về L1, không phát thêm cảnh báo. `l1_repeat_count: 0` là tắt
- Không làm tăng báo sai đơn lẻ: một hoặc hai L1 không đổi; L1 bị cooldown chặn không được đếm; hai lý do L1 khác nhau không cộng dồn. Với cooldown L1 120 s, 3 lần cần ít nhất 4 phút
- Nghỉ đỗ xe (`context.rest_after_s`) rồi chạy tiếp, hoặc đổi tài xế: đếm lại từ đầu (`DecisionPipeline` gọi `forget_repeats`)
- Backend nhận lý do `repeated_l1`; nhãn dashboard "Đã nhắc nhiều lần"; dòng chính trên HUD "Đã nhắc nhiều lần: hãy dừng nghỉ" (đứng trước lý do gốc). Loại sự kiện vẫn theo lý do gốc (`drowsiness`)
- Ngưỡng tạm: chưa dataset nào có chuyến đủ dài để kiểm chứng. Replay trace FL3D và YawDD có và không có luật này cho cùng một báo cáo (không cảnh báo nào bị nâng)
- Test: 9 test khối 12 bằng chuỗi mức giả, 1 test pipeline (nghỉ thì đếm lại), 1 test backend, 1 test frontend

<a id="m33"></a>

#### M33: Nhịp "còn sống" và tổng quan đội xe (khối 14, backend, dashboard)

**Xong là thấy gì:** Dashboard có tab "Đội xe": xe nào đang hoạt động, xe nào mất liên lạc, xe nào đã kết thúc chuyến, cảnh báo trong ngày, sự kiện gần nhất

**Trạng thái:** Xong (05/10) (việc 24 trong docs/improvements.md, FMEA dòng 3, 4)

- `TripRuntime` phát bản ghi `heartbeat` mỗi `publisher.heartbeat_interval_s` (30 s) và ngay khi trạng thái giám sát đổi: `monitoring`, `unavailable`, `camera_lost`, `stalled`, `error`, `ended`. Nội dung: thời điểm, chuyến, trạng thái, xe đang chạy hay đỗ. Không có vị trí, không có số đo của tài xế
- `idle(clock)` giữ nhịp khi không có frame (mất camera, trang chạy nền). Không có frame quá `publisher.heartbeat_stalled_s` (10 s) mà camera không báo mất: `stalled`, không còn nói "đang giám sát". Kết thúc chuyến gửi `ended`
- Nhịp không vào hàng đợi: chỉ giữ nhịp mới nhất, gửi bằng một POST riêng trước các bản ghi (thiết bị: `MetadataPublisher`; web: `bridge.take_heartbeat` + `agent.ts`). Backend cũ từ chối (422) thì bỏ nhịp, sự kiện vẫn gửi được
- Backend: bảng `device_status` (lần cuối thấy theo giờ máy chủ, trạng thái từ nhịp mới nhất); mọi lô gửi lên đều tính là còn sống. `GET /api/v1/fleet?since&until`: `online` / `offline` (im quá `DG_DEVICE_OFFLINE_AFTER_S`, mặc định 90 s) / `ended` / `never`, cảnh báo theo mức và sự kiện gần nhất trong khoảng hỏi. Tài xế chỉ thấy xe của mình
- Dashboard: tab "Đội xe" cho quản lý / kỹ sư / admin: 4 ô tổng quan, bảng xe (mất liên lạc xếp trước), lọc theo trạng thái và ngày, nhãn tiếng Việt
- Test: 8 test runtime, 4 test publisher, 3 test bridge web, 15 test backend (chuỗi nhịp giả: đến, ngắt, đến lại, đến trễ), 3 test frontend, kịch bản e2e thứ hai thêm bước xem tab "Đội xe". Tổng 627 Python + 54 frontend + 3 e2e pass, ruff / typecheck / build sạch
- Chưa làm: màn hình đội xe trực tiếp có âm báo và "Bạn còn ở đó không?" (improvements: "cảnh báo cần xác nhận"); chưa deploy

<a id="m34"></a>

#### M34: Test hồi quy bằng trace trong CI (khối 5, 7–12)

**Xong là thấy gì:** Đổi logic hay ngưỡng làm lệch sự kiện / cảnh báo / `drowsy_score` trên 36 video cố định thì `pytest` đỏ, kèm lệnh cập nhật có lý do

**Trạng thái:** Xong (05/10) (việc 1 trong docs/improvements.md)

- `tools/regression_traces.py`: `build` chọn video từ trace đầy đủ trên máy (8 FL3D, 12 YawDD, 16 SUST; mỗi loại hành vi một video ngắn nhất, rồi lấp bằng video ngắn nhất còn lại), `check` so với kết quả đã chốt, `update --reason` chốt lại kèm lý do (lưu trong file)
- Dữ liệu trong repo: `tests/fixtures/regression/traces.npz` (563 KB; 36 video, 17 763 frame; 14 cột số mỗi frame như EAR, MAR, góc đầu, eyeBlink, độ sáng; không có ảnh) và `expected.json`
- Mỗi video chốt: số frame, số sự kiện theo loại, từng cảnh báo (frame, mức, lý do), mức cao nhất, `drowsy_score` ở 4 điểm (sai số cho phép 0,05 điểm). Có đủ L1, L2, L3 và 30 video không cảnh báo
- `tests/test_edge_agent/test_trace_regression.py` chạy trong `pytest` (CI có sẵn), khoảng 3 s. Đã thử: đổi 4 ngưỡng (`microsleep_l3_s`, `yawn.min_s`, `off_road_s`, `drowsy.l1`) đều bị bắt
- `tools/seq_eval.py replay` thêm tham số `observe` (không đổi hành vi)
- Chưa kiểm chứng: test mới chạy trên Mac ARM; CI là Linux x86, nếu số thực lệch ở bit cuối làm đổi một frame cảnh báo thì phải chốt lại trên CI
- Test: 11 test (khớp kết quả chốt, bắt 4 ngưỡng, độ phủ, chỉ có số, có lý do, hàm chọn / so / lưu)

<a id="m35"></a>

#### M35: Prototype offline: thời lượng chớp mắt so với chính tài xế (khối 7, chỉ đo)

**Xong là thấy gì:** Báo cáo `eval/results/blink_duration_fl3d.md` trả lời có nên thêm `duration_ratio` hay không

**Trạng thái:** Xong (05/10) (việc 3 trong docs/improvements.md). **Kết luận: không thêm `duration_ratio`**, engine không đổi

- `tools/blink_duration.py` chạy lại khối 5, 7–12 trên `fl3d_v2.pkl` (44 video, 47,2 phút), lấy thời lượng từng lần chớp do khối 7 đo; đo thêm bằng một bộ đếm offline trên EAR và trên eyeBlink
- Khối 7 đo được 482 lần chớp (10,2 / phút), trung vị 304 ms. Chỉ 5 / 44 video có đủ 20 lần chớp làm mốc + 5 lần để so: clip quá ngắn cho một tỉ lệ "so với đầu chuyến"
- FL3D không có nhãn "đoạn buồn ngủ" (chỉ alert / microsleep / yawning), nên dùng hai cách thay thế: video có microsleep so với video không có (AUC 0,54), và trong cùng video, chớp cách microsleep ≤ 10 s so với phần còn lại (AUC 0,54; trung vị tỉ lệ theo video 1,00 trên 5 video)
- Thời lượng và thời gian mở mắt lại gần như cùng một thông tin: Spearman 0,92 trên 482 lần chớp
- Hai mốc quyết định (AUC ≥ 0,65 và |rho| ≤ 0,8) được chọn sau khi đã xem sơ số liệu, không phải đặt trước; kết quả nằm xa cả hai mốc
- Ghi nhận thêm: bộ đếm offline thấy 1 178 lần chớp trên EAR, gấp 2,4 lần khối 7; chưa tìm hiểu vì sao
- Giới hạn: buồn ngủ diễn, ban đêm, 25 FPS (40 ms / frame). UTA-RLDD (cùng một người ở các mức KSS) mới trả lời chắc được
- Test: 9 test bằng chuỗi số giả

<a id="m36"></a>

#### M36: Trang tiêu chí sẵn sàng pilot; cột "Nhận định" trong bảng kết quả

**Xong là thấy gì:** `docs/pilot-readiness.md`: 24 tiêu chí có mục tiêu, số hiện có, trạng thái; lộ trình 4 giai đoạn

**Trạng thái:** Xong (05/10) (việc 24 trong docs/improvements.md). Chỉ tài liệu

- 24 tiêu chí trong 5 nhóm (phát hiện đúng, không im lặng, thiết bị, dữ liệu, con người và vận hành): 4 đạt, 6 một phần, 5 chưa đạt, 9 chưa đo / chưa có. Kết luận ghi ngay đầu trang: chưa sẵn sàng pilot
- Mục tiêu lấy từ PRD §6, §7, CLAUDE.md, và hai quy định EU đã đọc văn bản gốc: 2021/1341 (DDAW: KSS ≥ 8, độ nhạy trung bình > 40 %, cận dưới CI 90 % > 20 %, ≥ 10 người; âm báo 200–8 000 Hz, 50–90 dB) và 2023/2590 (ADDW: cảnh báo trong 3,5 s ở ≥ 50 km/h, 6 s ở 20–50 km/h). Euro NCAP 2026 chỉ có nguồn thứ cấp, ghi rõ
- Lộ trình 5 bậc (0 hiện tại → 4 mở rộng), mỗi bậc có cổng theo mã tiêu chí; bảng những chỗ DriverGuard cố ý làm khác quy định EU
- Cột "Nhận định" thêm vào bảng kết quả của README (và 2 dòng mới: ngủ gật 75/95, cảnh báo sai / giờ) và 3 bảng của `eval/results/report.md`
- Việc trong improvements được dẫn bằng tên + liên kết, không bằng số (số đổi mỗi lần xoá việc)

<a id="m37"></a>

#### M37: Chính sách dữ liệu và tự xoá theo thời hạn (backend, HUD, dashboard)

**Xong là thấy gì:** `docs/data-policy.md`; cảnh báo cũ hơn 60 ngày và tổng kết cũ hơn 365 ngày tự xoá; lệnh xoá dữ liệu một tài xế; màn hình đồng ý ghi thời hạn

**Trạng thái:** Xong (05/10) (việc 25 trong docs/improvements.md)

- `docs/data-policy.md`: dữ liệu nào được thu (theo đúng schema) và không thu, dùng vào việc gì, ai xem được gì, giữ bao lâu, quyền của tài xế, bảo mật, bảng căn cứ, việc của đơn vị triển khai, giới hạn
- Hai quyết định được giao cho mình chọn: (1) thời hạn **60 ngày** cho cảnh báo / sự kiện / mẫu theo phút và **365 ngày** cho bản tổng kết, theo mốc 2 tháng / 1 năm của CNIL cho định vị xe người lao động (luật Việt Nam không đặt con số); (2) **có làm xoá tự động**, bật mặc định
- Backend: `DG_RETENTION_EVENTS_DAYS`, `DG_RETENTION_SUMMARIES_DAYS` (0 = không xoá); xoá lúc khởi động và mỗi ngày một lần khi có thiết bị gửi dữ liệu; `GET /api/v1/policy`; `python -m backend.manage purge` và `delete-driver-data <mã> --yes` (Luật 91/2025/QH15 Điều 25 khoản 2 điểm c)
- Màn hình đồng ý: dòng thứ ba ghi thời hạn lưu (thay câu "Quản lý chỉ biết bạn đã đăng ký", không thêm dòng vì màn hình đã chật ở 1024×600). Dashboard: dòng cuối mọi tab nhắc không dùng một cảnh báo đơn lẻ để kỷ luật, kèm thời hạn lưu đang cấu hình
- Nguồn đã đọc văn bản gốc: Luật 91/2025/QH15 (Điều 3, 14, 25), hai quy định EU, hướng dẫn CNIL. Nguồn thứ cấp (ghi rõ): EDPB 01/2020, ICO
- Chưa làm: mã hoá database, nhật ký truy cập, xuất dữ liệu một tài xế, xoá tài khoản, tự xoá bản sao lưu; chưa có ý kiến pháp lý
- Test: 10 test backend (xoá đúng hạn, 0 ngày giữ nguyên, xoá lúc khởi động và mỗi ngày, endpoint, xoá một tài xế, lệnh `manage`, tài xế đọc được dữ liệu của mình, câu chữ khớp mặc định backend), 2 test frontend. Tổng 657 Python + 56 frontend + 3 e2e pass, ruff / typecheck / build sạch

<a id="m38"></a>

#### M38: Khối 8: liếc ngắn cộng dồn (chỉ đo), tách gọi điện / nhắn tin (chỉ ghi), quay hẳn đi rồi mất mặt (khối 4, 8, 9, 11, 14)

**Xong là thấy gì:** Bảng tổng kết chuyến có số lần liếc khỏi đường, thời gian gọi / nhắn tin, thời gian "quay hẳn đi"; quay ra sau 10 s thì HUD giữ L2 "Nhìn về phía trước" thay vì "tạm ngưng giám sát"

**Trạng thái:** Xong (06/10), mọi ngưỡng mới là tạm (ba việc về mất tập trung từ repo ViDDD trong docs/improvements.md)

- **Liếc ngắn cộng dồn (chỉ đo, không cảnh báo):** khối 8 thêm `off_road_ratio` (phần thời gian nhìn khỏi đường trong `distraction.glance.window_s`, 30 s; bằng 0 đến khi cửa sổ có đủ `min_coverage_s`, 10 s lái) và `glance_count`. Dùng đúng định nghĩa "khỏi đường" đang có (nới theo xi nhan, `gaze_down`). Xoá cửa sổ khi xe dừng, đổi tài xế, hoặc tạm ngưng giám sát. Ghi vào metadata cảnh báo, mẫu mỗi phút (giá trị cao nhất của phút), bảng tổng kết (`glances`, `off_road_ratio_max`), trace. Không luật nào đọc nó
- **Gọi điện hay nhắn tin (chỉ ghi):** khối 4 `phone_kind()` phân loại điện thoại trong vùng tài xế theo vị trí tâm khung so với khung mặt: bên cạnh mặt, từ cằm trở lên là `call`; dưới cằm là `text`; còn lại `unknown` (`phone.kind.*`). Khối 8 lấy loại chiếm đa số trong cửa sổ 2 s. Lý do và mức cảnh báo giữ nguyên (`phone`, L2); metadata có `phone_kind`, bảng tổng kết có `phone_call_s` / `phone_text_s`
- **Quay hẳn đi rồi mất mặt:** viết test tái hiện trước, đúng như mô tả: quay 60° rồi mất mặt 10 s khi xe chạy thì có một L2 ở giây 2,5, sau 3 s mất mặt chuyển sang "tạm ngưng giám sát" và im. Nay mặt mất ngay sau một tư thế tin được (cũ nhất `turned_away.pose_age_s`, 0,5 s) đang nhìn khỏi đường và quay quá `turned_away.yaw_deg` (45°) thì khối 8 đặt `turned_away`, khối 9 giữ luật `off_road` tối đa `turned_away.max_s` (10 s) rồi mới tạm ngưng. Mất mặt khi đang nhìn thẳng, quay nhẹ, hoặc quay về phía đang xi nhan: như cũ. Bảng tổng kết có `turned_away_s`. `yaw_deg: 0` là tắt
- **Không thêm cảnh báo:** replay trace có / không luật mới cho cùng danh sách cảnh báo trên SUST (2 074 clip, 44 cảnh báo), YawDD (319, 11), FL3D (44, 111); luật kích hoạt ở 1 clip SUST, đổi mức hiển thị trong 0,7 s. Test hồi quy trace M34 không phải chốt lại
- **`off_road_ratio` trên người không mất tập trung** (`eval/results/glance_ratio.md`): YawDD 18 / 315 clip (6 %) có lúc ≥ 0,3; FL3D 10 / 44 (23 %, nhưng đó là gục đầu khi diễn buồn ngủ); SUST clip 10 s nên cửa sổ không kịp đầy. Chưa bộ nào là lái bình thường có nhìn gương, chuyển làn
- Backend nhận các trường mới (agent cũ không gửi vẫn được); `fatigue_samples` thêm cột `off_road_ratio` (tự thêm vào database cũ). Dashboard: bảng báo cáo chuyến thêm hai dòng "Điện thoại: gọi / nhắn tin", "Liếc khỏi đường"
- Chưa làm: luật cảnh báo cho liếc cộng dồn (cần đọc nguồn về giới hạn thời gian liếc và dữ liệu có nhãn); đo độ chính xác của `phone_kind` (chưa có dữ liệu đúng góc camera); ghép `text` với `gaze_down` để chắc hơn; quyết định nhắn tin có báo sớm hơn không
- Test: 28 test khối 4, 8, 9, 11 bằng chuỗi số giả, 3 test backend, 3 test frontend

<a id="m39"></a>

#### M39: Công cụ ghi số trực tiếp từ camera kèm nhãn bấm phím, không lưu ảnh (`tools/record_trace.py`)

**Xong là thấy gì:** `record` mở camera, bấm phím đánh dấu hành động, lưu trace số; `report` ra bảng độ trễ cảnh báo p50 / p95, báo sai, so nhìn xuống với nhắm mắt, so có / không khẩu trang

**Trạng thái:** Xong phần công cụ (06/10). **Chưa có bản ghi thật nào**, nên chưa có số time-to-alert, khẩu trang, nhìn xuống (việc "ghi số trực tiếp từ camera" trong docs/improvements.md còn phần ghi)

- `tools/record_trace.py record`: chạy khối 2–12 trên camera (cùng cách nối như `seq_eval`), mỗi frame giữ một dòng số, cửa sổ xem trước chỉ hiển thị. Bấm phím lần một là bắt đầu, lần hai là kết thúc: `e` nhắm mắt, `d` cúi nhìn điện thoại, `b` bảng đồng hồ, `s` nhìn sang bên, `r` quay ra sau, `y` ngáp, `t` nói chuyện, `n` gục đầu, `c` gọi điện, `x` nhắn tin, `a` ngồi yên nhìn đường. `--tag mask=medical` ghi điều kiện của buổi ghi. Trước khi lưu, công cụ từ chối trace có cột không phải dãy số một chiều
- `report`: độ trễ từ lúc bấm phím đến cảnh báo / sự kiện đúng loại (p50, p95, so với PRD ≤ 3 s), cảnh báo ngoài mọi nhãn tính theo giờ kèm CI, phân bố EAR / mốc, eyeBlink, eyeLookDown, pitch, vị trí mống mắt theo từng loại hành động, bảng theo tag `mask` (tỉ lệ thấy mặt, MAR khi ngồi yên, số lần MAR đảo chiều, ngáp đếm được so với nhãn, đợt nhắm ≥ 1,5 s có đạt L3 không), bảng gọi / nhắn tin so với nhãn. `--set` replay khối 7–12 với ngưỡng khác
- Khối 3 giữ thêm 10 blendshape cho trace (`eyeLook*` hai mắt, `jawOpen`, `mouthClose`); chưa khối nào đọc chúng
- `tools/seq_eval.py`: phần trace tách thành lớp `Tracer` dùng chung cho video và camera; trace có thêm cột `roll`, khung mặt, khung / cờ / loại điện thoại, `off_road_ratio`, blendshape hướng nhìn, vị trí mống mắt so với hai khoé mắt, `perclos_p80`. Đã kiểm: trace lại 3 video YawDD cho đúng các cột, sự kiện và cảnh báo của trace đã lưu. `replay` dùng cờ điện thoại nếu trace có
- Ngưỡng khớp nhãn: `eval.label_tolerance_s` (1 s)
- Mới chạy thử trên một video YawDD với nhãn đặt theo kịch bản (`--source clip --script`). Trong test, một chuỗi MAR giả dao động liên tục làm mặt nạ "đang nói" che mất đợt nhắm 3 s khi không có blendshape eyeBlink: rủi ro của khẩu trang có thật về mặt logic, còn có xảy ra với khẩu trang thật hay không thì phải ghi mới biết
- Test: 18 test (nhãn từ phím, độ trễ, báo sai, đếm đảo chiều MAR, báo cáo, chỉ lưu số, mống mắt, replay cờ điện thoại)

<a id="m40"></a>

#### M40: Đo offline trên trace sẵn có: PERCLOS P80, theo ánh sáng / kính, cá nhân hoá, theo từng người (khối 7 chỉ đo, `tools/trace_studies.py`, `tools/eval.py`)

**Xong là thấy gì:** Bốn báo cáo mới trong `eval/results/`; `perclos_p80_60s` đo song song với `perclos_60s`; bảng "Per person" và "start-up apart" trong báo cáo eval

**Trạng thái:** Xong (06/10). Không ngưỡng nào đổi, không cảnh báo nào đổi

- **PERCLOS:** comment trong `thresholds.yaml` ghi rõ `perclos_60s` là biến thể gần "P50" có trộn xác suất CNN và bỏ frame đang ngáp / nói, và các ngưỡng PERCLOS không có nguồn nào được ghi lại (0,15 có từ M2). Khối 7 đo thêm `perclos_p80_60s` (độ mở mắt < `perclos_p80_aperture`, 0,2; chỉ frame EAR), ghi vào metadata (`perclos_p80`) và trace, không vào `drowsy_score`, không sinh sự kiện
- `eval/results/perclos_p80.md`: FL3D theo frame, P80 nhận 77,3 % frame microsleep và 2,0 % frame alert; định nghĩa hiện tại 70,5 % và 2,6 % (nó chỉ xét được 66,5 % số frame có nhãn vì mặt nạ ngáp / nói, P80 xét được 86,9 %). SUST theo clip: AUC 0,669 (hiện tại) so với 0,649 (P80). YawDD clip Normal / Talking có tỉ lệ nhắm ≥ 0,15: 28 / 205 (hiện tại) so với 12 / 201 (P80). Đổi `perclos_close_ratio` sang 0,48 (tương đương P80): số cảnh báo trên SUST và YawDD không đổi, FL3D 111 → 112. Clip quá ngắn để luật PERCLOS chạy, nên chưa kết luận được định nghĩa nào tốt hơn; cần UTA-RLDD
- `eval/results/lighting.md`: kết quả chia theo độ sáng vùng mặt (`eval.brightness_bins`) trong từng dataset, và theo kính của YawDD. FL3D theo frame: mặt tối dưới 60 (466 frame, toàn bộ do CNN quyết định) recall mắt nhắm 40,3 %, so với 92,6 % ở 60–100. YawDD: frame do CNN quyết định 14,9 % (không kính), 26,1 % (kính), 66,7 % (kính râm); báo sai / giờ 4,8 / 10,5 / 6,7, các CI chồng nhau. Không so chéo dataset
- `eval/results/personalization.md` (YawDD, bộ duy nhất ở đây có mã người trong tên file): mốc "đăng ký giả" lấy từ 10 s đầu clip Normal của chính người đó, clip đó không tính điểm. 212 clip của 105 người: cảnh báo sai 7 (tự học) so với 9 (đăng ký giả), toàn `off_road`; clip ngáp có sự kiện ngáp 93 → 97 / 113. **Không thấy cá nhân hoá giảm báo sai trên bộ này**; mốc lấy từ một clip khác nên tư thế có thể lệch. FL3D và SUST không có mã người
- `tools/eval.py`: cột `subject` tuỳ chọn trong CSV nhãn, bảng theo từng người (ai nhận báo sai, vì luật nào, FAR theo cửa sổ) và bảng tách 30 s khởi động khỏi báo sai / giờ. `seq_eval.py yawdd` dùng luôn: 10 cảnh báo sai đến từ 10 / 106 người; 9 / 10 rơi vào 30 s đầu clip (clip chỉ dài khoảng 20 s)
- `eval/results/dataset_yawdd.md` được sinh lại. Bản cũ trong repo đã lệch với code từ trước mốc này (12 cảnh báo, nay 11; chạy lại bằng code ở commit trước cũng ra 11)
- `tools/trace_studies.py glance` cho M38
- Chưa làm: phép thử làm tối / làm chói cùng một video trong RAM; dữ liệu IR / kính râm (NTHU-DDD); cá nhân hoá trên UTA-RLDD; đường đánh đổi FAR ↔ MAR
- Test: 21 test (P80 trong khối 7, bốn báo cáo trên trace giả, đăng ký giả, bảng theo người, tách khởi động)

<a id="m41"></a>

#### M41: Phiên bản trên nhịp "còn sống" và sự kiện, tag `simulated` / `forced`, nhật ký truy cập (khối 14, backend, dashboard)

**Xong là thấy gì:** Tab "Đội xe" có cột "Phiên bản", tô xe đang chạy bộ ngưỡng cũ; admin có tab "Nhật ký truy cập", tài xế có tab "Ai đã xem dữ liệu của tôi"

**Trạng thái:** Xong (06/10) (mục 1 của "OTA ngưỡng và model", phần tag của "phần PRD còn lại", mục 1, 4, 5 của "guardrails dữ liệu" trong docs/improvements.md)

- **Phiên bản:** `edge_agent/version.py`: phiên bản app (`APP_VERSION` = 3.0.0, đặt tay), phiên bản bộ ngưỡng đã tải từ backend (0 = chỉ `thresholds.yaml` trên máy), cờ "bộ ngưỡng từ xa bị bỏ qua", 12 ký tự đầu SHA-256 của từng file model. Gửi trong mọi nhịp "còn sống" và mọi sự kiện. Bản web lấy mã model từ `config/build_info.json` do `tools/build_web_py.py` ghi lúc đóng gói (Dockerfile.railway chép model vào bước đó)
- Backend lưu theo thiết bị và theo sự kiện; `GET /api/v1/fleet` trả `versions`, `thresholds_current`, `thresholds_latest`. Tab "Đội xe": cột "Phiên bản" ("app 3.0.0 · ngưỡng v2"), tô vàng thiết bị chạy bộ ngưỡng cũ hoặc đã từ chối bộ ngưỡng từ xa; rê chuột thấy mã model
- **Tag:** mọi sự kiện mang `tags: ["simulated"]` khi tín hiệu xe là mô phỏng (hiện tại luôn vậy). Backend nhận thêm `forced`, vẫn lưu và liệt kê nhưng loại khỏi thống kê, số cảnh báo đội xe, danh sách chuyến. Agent không có đường nào sinh `forced`: trạng thái ép tay chỉ có ở `#/hud-preview`, trang này nay ghi nhật ký từng lần ép (tag `simulated` + `forced`) và cho tải về file JSON; không gửi lên máy chủ
- **Nhật ký truy cập:** bảng `access_log` chỉ ghi thêm (trigger chặn sửa), ghi ai (tài khoản, vai trò) xem dữ liệu của tài xế / thiết bị nào hay của cả đội, sửa ngưỡng, tạo tài khoản / thiết bị, xoá dữ liệu bằng lệnh `manage`. Cùng một lượt xem của cùng tài khoản ghi một lần mỗi `DG_AUDIT_DEDUPE_S` (600 s); tài xế xem dữ liệu của chính mình không ghi. Giữ `DG_RETENTION_ACCESS_LOG_DAYS` (365 ngày, con số do mình chọn). `GET /api/v1/access-log` (chỉ admin) và `/api/v1/access-log/mine` (tài xế)
- **Giới hạn mục đích:** test chốt danh sách toàn bộ endpoint (thêm endpoint mới phải sửa danh sách có chủ ý), không có trường hay đường dẫn nào xếp hạng tài xế, danh sách đội xe sắp theo mã thiết bị. Dòng nhắc "không dùng một cảnh báo đơn lẻ để kỷ luật" đã có từ M37, nay thêm câu mọi lượt xem đều được ghi
- **Chặn ghi frame bằng test tĩnh:** quét `edge_agent/`, `backend/`, `tools/` và `frontend/src/` tìm `imwrite`, `VideoWriter`, `imencode`, `toDataURL`, `toBlob`, `MediaRecorder`...; hiện không có lời gọi nào, danh sách ngoại lệ đang rỗng
- Thứ tự nâng cấp như các mốc trước: backend trước, thiết bị sau (backend cũ từ chối trường lạ)
- Chưa làm: tải lại ngưỡng không cần khởi động lại, quay lui / triển khai theo nhóm, OTA model; xuất / xoá dữ liệu từ giao diện, mã hoá database, hồ sơ đánh giá tác động
- Test: 25 test backend, 16 test thiết bị, 8 test frontend

<a id="m42"></a>

#### M42: Chạy dài đo CPU / RAM / FPS, image edge và container giới hạn kiểu Jetson, bảng lượng tử hoá (`tools/benchmark.py`, `tools/edge_sim.py`, `Dockerfile.edge`)

**Xong là thấy gì:** `eval/results/benchmark_simulated.md` có bảng máy dev và hai hồ sơ giới hạn gắn nhãn `simulated`; `eval/results/quantization.md`

**Trạng thái:** Xong (06/10) (phần máy dev của "đo tài nguyên phần cứng", "Docker cho edge, mô phỏng Jetson", mục 3 của "chốt lượng tử hoá" trong docs/improvements.md). Chưa có số nào trên thiết bị thật

- `tools/benchmark.py --duration 10m`: vòng lặp chính (khối 2–12, YOLO ở luồng riêng) theo nhịp camera (`--pace-fps`), mỗi giây ghi FPS, độ trễ p95, CPU của tiến trình, RAM, nhiệt độ (nếu đọc được); bảng theo từng phút, CSV từng giây, kết luận theo `eval.soak_min_fps` (15) và `eval.soak_rss_growth_mb_per_h` (20, tạm). `--combine` gộp nhiều lần chạy thành một báo cáo
- `Dockerfile.edge` (linux/arm64, không chứa model, không chứa dữ liệu), `config/edge_profiles.yaml` (Jetson Nano: 4 nhân, 4 GB; Orin Nano: 6 nhân, 8 GB), `tools/edge_sim.py` chạy phép đo trong container với `--cpus` / `--memory` của hồ sơ; báo cáo in giới hạn mà tiến trình thật sự thấy (cgroup) và gắn `simulated`. `docker-compose.yml` thêm dịch vụ `edge` (profile riêng, không bật mặc định)
- Kết quả, nhịp 30 FPS, clip YawDD có mặt: Mac dev 10 phút: 29,9 FPS, p95 10,8 ms, CPU 54 % của một nhân, RAM đỉnh 601 MB. Container 4 CPU / 4 GB 10 phút: 29,9 FPS, p95 11,1 ms, CPU 93 %, 597 MB. Container 6 CPU / 8 GB 5 phút: 30,0 FPS, CPU 89 %. Mọi phút đều ≥ 15 FPS
- **Giới hạn phải đọc cùng số:** container chạy trên chính CPU của Mac, chỉ ít nhân hơn; không tái hiện tốc độ nhân Cortex-A, GPU / TensorRT hay nhiệt. Là cận trên cho bo mạch đó, không phải số đo. Hai chuỗi chạy (máy thật và container) chạy cùng lúc; máy đã ngủ vài phút giữa hai lần chạy 10 phút đầu (đồng hồ dùng để đo không chạy khi ngủ)
- RAM: trong container tăng 21–66 MB / giờ tính trên 5–10 phút, cao hơn ngưỡng tạm; quá ngắn để kết luận, còn nợ một lần chạy cả giờ. Nhiệt độ không đọc được. Điều kiện "có mặt + điện thoại" chưa chạy vì chưa có clip
- Bảng lượng tử hoá: INT8 nhỏ hơn 3,6 lần (12,85 → 3,61 MB). YOLO chạy riêng: Mac FP32 16,6 ms, INT8 19,6 ms; container Linux arm64 FP32 55,1 ms, INT8 19,3 ms (chưa tìm hiểu vì sao FP32 chậm ở đó). Vòng chính gần như không đổi. Độ chính xác INT8 chưa đo, mặc định vẫn FP32
- Đã kiểm chứng điều docs ghi "chưa kiểm chứng": MediaPipe 0.10.21 không có wheel linux/arm64 (có 0.10.18, 1.0.0, 1.0.1); image dùng 1.0.1 + OpenCV 5.0.0 và pipeline chạy được (thấy mặt ở mọi frame)
- Docker Desktop trên macOS không đọc được thư mục Documents nếu chưa cấp quyền: `edge_sim.py` có `--models-dir`, `--out-dir` để dùng thư mục khác
- `psutil` thêm vào `requirements.txt`
- Test: 25 test (đọc thời lượng, hồ sơ, giới hạn cgroup giả, thống kê theo phút, độ dốc RAM, kết luận, báo cáo, lệnh docker). Tổng sau M38–M42: 793 Python + 67 frontend + 3 e2e pass, ruff / typecheck / build sạch

<a id="m43"></a>

#### M43: Điểm chất lượng frame: ảnh không đọc được thì "tạm ngưng giám sát" có lý do (giai đoạn của khối 6, khối 9, 13, 14)

**Xong là thấy gì:** Che camera, mặt quá tối / quá chói / ảnh mờ ≥ 5 s khi xe chạy: HUD nói rõ lý do và việc cần làm thay vì đoán; sự kiện và bản tổng kết ghi lý do

**Trạng thái:** Xong (06/10) (việc "hoàn thiện FR-6: điểm chất lượng frame" trong docs/improvements.md). Ngưỡng tạm

- `edge_agent/perception/quality.py` (mới, giai đoạn của khối 6): từ bốn con số của mỗi frame (độ sáng vùng mặt, độ sáng và độ tương phản cả khung, độ nét vùng mặt = phương sai Laplacian) gọi tên điều làm frame không dùng được: `camera_blocked` (không thấy mặt và cả khung tối / phẳng), `bad_angle` (mặt nằm một phần ngoài khung), `low_light`, `glare`, `blur`. `QualityMonitor` đếm lỗi kéo dài bao lâu và cho `score` = tỉ lệ frame dùng được trong 10 s. Số không đo được (trace cũ, chuỗi số giả) không bao giờ là lỗi
- Khối 9: mặt còn thấy mà `low_light` / `glare` / `blur` suốt `risk.unavailable.low_quality_s` (5 s) khi xe chạy → `unavailable`, không cảnh báo nào (kể cả một lần nhắm mắt đang đếm: số đọc trên mặt đó là đoán). `RiskAssessment.unavailable_reason` cho cả sáu lý do (mất mặt thường là `no_face`)
- Thiết bị đo bằng numpy trên độ sáng trước CLAHE (0,13 ms / frame trên máy dev); `#/live` đo cùng số trong JS (`measure.ts`), ngưỡng vẫn ở Python
- HUD: màn hình "Tạm ngưng giám sát" ghi việc cần làm theo lý do; `#/hud-preview` có thêm bốn trạng thái. Backend: sự kiện `monitoring_unavailable` có `metrics.cause`, bản tổng kết có `unavailable_by_cause`; nhật ký sự kiện và báo cáo chuyến hiện lý do
- Ngưỡng `quality.*` đặt theo số đo: 12 video mỗi bộ (mặt 49–200, độ nét 4,4–670) và phép thử của M46 (FL3D: microsleep đạt L3 18 → 9 / 24 khi mặt sáng 230; 17 → 2 / 24 giữa độ nét 5,1 và 2,3) → tối < 25, chói > 225, mờ < 3,0. Chưa có frame tối / chói / mờ thật nào để kiểm
- Không đổi kết quả cũ: trace cũ có độ sáng mặt (49–200) nên test hồi quy 36 video ra đúng từng số
- Trace mới (`seq_eval`, `record_trace`) ghi thêm `scene_bright`, `scene_contrast`, `sharpness`
- **Chưa che:** mặt tối trong khoảng 25–60 và ảnh xám trên thiết bị (khối 5 giao cho CNN mắt), xem M46
- Test: 15 test khối 6 / 9 / runtime, 2 test backend, 1 test bridge, 3 test đo trong JS

<a id="m44"></a>

#### M44: Không phản ứng với còi, ngủ gật lặp lại, "Bạn còn ở đó không?"; quản lý được báo ngay (khối 9, 12, 13, 14, backend, dashboard)

**Xong là thấy gì:** Nhắm mắt ≥ 6 s: cảnh báo L3 thứ hai `unresponsive`; mất mặt 8 s: HUD hỏi, 10 s không chạm thì `no_answer`; tab "Đội xe" có mục "Cần chú ý ngay" kèm tiếng

**Trạng thái:** Xong (06/10) (việc "cảnh báo cần xác nhận, báo quản lý ngay" trong docs/improvements.md). Ngưỡng tạm

- Khối 9: `closed_duration` ≥ `risk.unresponsive.closed_s` (6 s) → thêm lý do L3 `unresponsive`; vì là lý do mới ở cùng mức, khối 12 phát cảnh báo và sự kiện thứ hai. HUD đổi câu thành "DỪNG XE NGAY!". Hệ thống chỉ đọc tín hiệu xe, không giảm tốc
- Khối 12: cảnh báo L3 thứ `alert.l3_repeat_count` (3) trong `l3_repeat_window_s` (600 s) mang thêm lý do `repeated_l3` (mức vẫn L3). `unresponsive` của cùng một lần nhắm không được đếm; nghỉ hoặc đổi tài xế thì đếm lại
- `edge_agent/decision/presence.py` (mới, giai đoạn của khối 12): tạm ngưng giám sát với lý do `no_face` kéo dài `presence.ask_after_s` (5 s) → HUD hỏi "Bạn còn ở đó không?" bằng cả màn hình (một nút duy nhất) và tiếng lặp lại. Chạm, hoặc mặt hiện lại, là xong; `presence.answer_s` (10 s) không trả lời → sự kiện hệ thống `no_answer`, HUD chuyển sang còi L3. Che camera / ảnh xấu thì không hỏi
- **Không bắt tài xế chạm màn hình khi đang được giám sát:** câu hỏi chỉ hiện khi camera không thấy tài xế; L1 / L2 / L3 không cần xác nhận
- Gửi ngay: sự kiện L3, `unresponsive`, `repeated_l3`, `no_answer` đánh thức luồng gửi của thiết bị và báo trang `#/live` gửi luôn, không chờ chu kỳ 5 s
- Backend: `GET /api/v1/fleet` thêm `urgent` = sự kiện loại trên mới nhất của chuyến đang chạy trong `DG_FLEET_URGENT_WINDOW_S` (300 s), chỉ với xe còn liên lạc; không tính sự kiện `forced`, chuyến cũ
- Dashboard: tab "Đội xe" tự làm mới mỗi 5 s (trước 15 s), có ô và khung "Cần chú ý ngay", xe đó lên đầu bảng, mỗi sự kiện mới kêu một lần
- Test hồi quy trace chốt lại, có lý do: một video FL3D có cảnh báo L3 thứ ba nay mang `repeated_l3`; không mức, thời điểm hay điểm số nào đổi
- Test: 17 test thiết bị, 6 test backend, 2 test frontend

<a id="m45"></a>

#### M45: Giảm dung lượng tải lần đầu của `#/live`: bỏ OpenCV khỏi bản web, server nén và đặt cache

**Xong là thấy gì:** Lần đầu tải khoảng 30 MB qua mạng thay vì 42 MB; lần sau file không đổi chỉ tốn một lượt hỏi lại

**Trạng thái:** Xong (06/10) (việc "tối ưu dung lượng tải lần đầu" trong docs/improvements.md). Mục YOLO INT8 không làm: độ chính xác INT8 chưa đo

- `edge_agent/perception/geometry.py` (mới): bản numpy của ba thứ bản web cần ở OpenCV: góc đầu (`solvePnP` + `Rodrigues` + `RQDecomp3x3`) và lọc khung trùng (`dnn.NMSBoxes`). `edge_agent/cv.py`: OpenCV nếu có, không thì `None`. **Thiết bị vẫn dùng OpenCV, không đổi gì**; chỉ trình duyệt chạy bản numpy
- Kiểm chứng hai bản cho cùng số: 200 tư thế ngẫu nhiên và 120 frame bám theo frame trước lệch dưới 0,05°; 300 ma trận xoay; 5 bộ khung ngẫu nhiên cho NMS; một test chạy cả agent web trong tiến trình không có `cv2` và so từng frame với bản có `cv2`
- `#/live` không còn tải gói `opencv-python` của Pyodide (11,7 MB). E2e (Chrome, Pyodide thật) vẫn qua cả ba kịch bản. Góc đầu bằng numpy tốn khoảng 1 ms / frame trên CPython; **chưa đo FPS trong trình duyệt sau thay đổi**
- `backend/static.py` (mới): file có bản `.gz` đi kèm thì gửi dạng nén cho trình duyệt nhận gzip; bản `.gz` tạo một lần lúc build image (`python -m backend.static`), không nén lại mỗi yêu cầu. File trong `assets/` (tên có mã băm) được cache một năm; model, gói Python, `index.html` thì `no-cache` (trình duyệt hỏi lại, không đổi thì 304 không có thân)
- Số đo trên bản build: ONNX Runtime wasm 14,24 → 3,65 MB, `yolov8n.onnx` 12,85 → 11,06 MB, `face_landmarker.task` 3,76 → 3,33 MB, JS 0,52 → 0,16 MB. Cộng phần lấy từ CDN (số đo 03/10: MediaPipe wasm 3,1, Pyodide 5,1, numpy 3,1 MB): khoảng 30 MB qua mạng. Màn hình tải ghi "khoảng 30 MB"
- **Chưa kiểm chứng trên Railway** (chưa deploy bản này)
- Test: 10 test hình học, 1 test không có OpenCV, 6 test file tĩnh

<a id="m46"></a>

#### M46: Cùng video, ánh sáng khác: làm tối / chói / xám / mờ trong RAM (`tools/light_study.py`)

**Xong là thấy gì:** `eval/results/lighting_transforms.md`: mức nào hệ thống chuyển sang tạm ngưng, mức nào nó im lặng mà sai

**Trạng thái:** Xong (06/10) (mục 3 của việc "eval theo điều kiện ánh sáng" trong docs/improvements.md)

- `tools/light_study.py` (mới): mỗi frame bị biến đổi trong RAM trước khối 2 rồi chạy khối 2–12 như thường; 12 biến đổi (gốc, gamma 1,5 / 2,2 / 3,5 / 5, gain 1,5 / 2,5 / 4, xám, mờ sigma 1,5 / 3 / 6; mức nằm ở `eval.light_*`). Không ghi ảnh nào
- Chạy trên 8 video FL3D (8,3 phút) và 8 clip YawDD (2,4 phút). Mỗi dòng: tỉ lệ thấy mặt, độ sáng / độ nét trung vị, tỉ lệ frame do CNN quyết định, tỉ lệ tạm ngưng và lý do, microsleep đạt L3 / ngáp, recall mắt nhắm theo frame, cảnh báo sai
- **Kết quả chính (FL3D):** gốc 18 / 24 microsleep đạt L3. Làm tối nhẹ (mặt 49): **0 / 24**, recall mắt nhắm 88 % → 0,2 %, hệ thống không báo tạm ngưng. Xám (giả IR): **0 / 24**, recall 9 %. Cả hai là lúc khối 5 giao trạng thái mắt cho CNN. Chói vừa (mặt 187): không đổi; chói mạnh (230): 9 / 24, tạm ngưng 49 % thời gian. Mờ nhẹ: 17 / 24; mờ vừa: tạm ngưng 86 % thời gian
- YawDD: ngáp vẫn bắt được 3 / 4 tới khi mặt tối 35 và ở mọi mức mờ trừ mức nặng nhất (miệng không phụ thuộc CNN mắt)
- Dùng kết quả để đặt ngưỡng `quality.*` của M43, rồi chạy lại cho báo cáo cuối
- **Giới hạn:** biến đổi nhân tạo trên video thật (không nhiễu cảm biến lúc tối, không phải IR thật, không vệt nắng nửa mặt), vài video mỗi bộ. Cho biết pipeline gãy ở đâu, không cho biết ánh sáng đó gặp thường xuyên tới đâu
- **Việc mới, chưa làm:** lỗ hổng của khối 5 ở trên thành việc 28 trong docs/improvements.md và dòng 16 (mức Cao) của docs/safety-fmea.md
- Test: 8 test (phép biến đổi, chọn video, gộp bảng)

<a id="m47"></a>

#### M47: Ngưỡng từ dashboard: tải lại trong chuyến, chỉ áp khi xe đỗ; áp thử cho vài xe; quay lui (khối 14, backend, dashboard)

**Xong là thấy gì:** Lưu ngưỡng cho vài xe thử, xem số báo sai theo phiên bản, bấm "Áp cho cả đội"; xe nhận khi đỗ và gửi `config_applied`

**Trạng thái:** Xong (06/10) (mục 2, 3 của việc "OTA ngưỡng và model" trong docs/improvements.md). OTA model chưa làm

- Thiết bị (`edge_agent/main.py`) và `#/live` hỏi lại backend mỗi `publisher.config_poll_s` (300 s). `ThresholdReloader` (`edge_agent/io/remote_config.py`, logic thuần) giữ phiên bản mới cho tới khi **xe đỗ**; đầu chuyến cũng tính là đỗ. Ngưỡng không bao giờ đổi dưới chân một tài xế đang bị đánh giá
- Khi áp (`DecisionPipeline.reconfigure`): khối 7, 8, 12 và trip memory chạy lại từ đầu với số mới; tài xế **không phải đăng ký lại**, ngữ cảnh xe và bảng tổng kết chuyến đi tiếp. Gửi sự kiện `config_applied`, nhịp "còn sống" mang phiên bản mới ngay
- Bộ không nhất quán: giữ ngưỡng đang dùng, gửi `config_refused`, không thử lại cùng phiên bản. Ngưỡng từ xa luôn áp lên `thresholds.yaml` gốc, không chồng lên bộ trước
- Backend: bảng `threshold_rollout` (phiên bản của cả đội) và `threshold_pins` (phiên bản ghim cho từng thiết bị). `PUT /api/v1/thresholds` nhận thêm `trial_devices`: chỉ các xe đó nhận bản mới, cả đội giữ bản đang dùng. `POST /api/v1/thresholds/rollout` đưa một phiên bản đã lưu thành của cả đội (dùng cho cả quay lui; không chép, không xoá lịch sử). `GET /api/v1/thresholds/versions`: mỗi phiên bản đổi khoá nào, xe nào đang chạy, bao nhiêu cảnh báo và bao nhiêu lần tài xế bấm báo sai
- Thiết bị và trình duyệt (`web-<tên>`) nhận phiên bản dành cho mình. Tab "Đội xe" so mỗi xe với phiên bản nó phải chạy, nên xe đang thử không bị tô là "lệch"
- Dashboard: tab "Ngưỡng" có ô "Chỉ áp thử cho các xe", bảng "Phiên bản ngưỡng" và nút "Áp cho cả đội". Việc áp cho cả đội do người quyết định, không tự động
- Database cũ không cần nâng: chưa có dòng nào trong `threshold_rollout` thì phiên bản mới nhất là của cả đội, như trước
- Test: 9 test thiết bị (khi nào áp, quay lui, bộ sai, còn đăng ký, trình duyệt), 8 test backend, 1 test frontend

<a id="m48"></a>

#### M48: Dữ liệu của tài xế: tự tải về, yêu cầu xoá từ giao diện; database và image; hai mẫu giấy tờ (backend, dashboard, docs)

**Xong là thấy gì:** Tài xế có tab "Dữ liệu của tôi" (tải file JSON, yêu cầu xoá); admin duyệt; `docs/dpia-template.md`, `docs/driver-notice-template.md`

**Trạng thái:** Xong (06/10) (việc "guardrails dữ liệu: phần còn thiếu" trong docs/improvements.md)

- `GET /api/v1/me/data`: mọi thứ lưu về chính tài xế đang đăng nhập (cảnh báo, sự kiện, mẫu theo phút, báo cáo chuyến, ai đã xem, các yêu cầu xoá) thành một file JSON. Chỉ vai trò tài xế, chỉ dữ liệu của mình
- Yêu cầu xoá: tài xế bấm "Yêu cầu xoá dữ liệu" (bảng `deletion_requests`, mỗi tài xế một yêu cầu đang chờ). Admin thấy ở tab "Nhật ký truy cập": "Xoá dữ liệu" (chạy đúng hàm của lệnh quản trị) hoặc "Từ chối" kèm một lý do chọn trong danh sách, không có ô nhập tự do. Cả hai đều vào nhật ký truy cập, tài xế thấy kết quả. Không làm nút tự xoá: đơn vị có thể có lý do phải giữ
- `python -m backend.manage delete-user <tên> --yes [--with-data]`: xoá tài khoản
- Database: quyết định **không mã hoá ở mức ứng dụng**, dựa vào mã hoá ổ đĩa của nơi host (ghi ở data-policy mục 7; chưa kiểm chứng với Railway). Đã làm: file database và `-wal` / `-shm` chỉ chủ sở hữu đọc được (0600)
- Image: `.dockerignore` loại `.env` và `*.db` ở mọi thư mục; test đọc các Dockerfile: không `COPY` nào lấy `data/`, `.env`, file database; không `ENV` / `ARG` nào gán sẵn bí mật
- Test danh sách endpoint (M41) được sửa có chủ ý cho 7 endpoint mới của M47 / M48, kèm lý do từng nhóm
- Tài liệu: `docs/dpia-template.md` (hồ sơ đánh giá tác động, phần kỹ thuật đã điền), `docs/driver-notice-template.md` (thông báo cho tài xế). Bản nháp của nhóm kỹ thuật, không phải tư vấn pháp lý; chưa đối chiếu với biểu mẫu chính thức
- Tab của tài xế đổi tên "Ai đã xem dữ liệu của tôi" → "Dữ liệu của tôi" (bảng cũ vẫn ở trong)
- Test: 8 test backend, 1 test frontend. Tổng sau M43–M48: 879 Python + 75 frontend + 3 e2e pass; ruff, typecheck, build sạch

<a id="m49"></a>

#### M49: Tốc độ bản web: công cụ đo khối 6–14 trong Pyodide, `solve_pnp` nhanh hơn, đồng hồ từng chặng của vòng lặp `#/live`

**Xong là thấy gì:** `eval/results/benchmark_web.md` có số trước / sau; "Chi tiết kỹ thuật" của `#/live` và cột "Tốc độ xử lý" ở tab "Đội xe" hiện thời gian từng chặng

**Trạng thái:** Xong (06/10) (việc "đo từng chặng của vòng lặp bản web / APK", mục 1–4, và việc "góc đầu trong bản web" trong docs/improvements.md). Chưa đo trên điện thoại Android hay hub

- **Công cụ đo** `tools/bench_web.py` + `frontend/bench/bridge.bench.mjs`: cùng một lời gọi `WebAgent.frame()` + JSON trên cùng chuỗi landmark, chạy trong CPython có OpenCV (trường hợp của thiết bị) và trong Pyodide dưới Node (code của `#/live` và APK). Đầu vào mặc định là mặt tổng hợp quay đầu chậm, có rung và chớp mắt; `--clip` lấy landmark thật của một video, chỉ giữ trong RAM. Mỗi lần chạy là một dòng theo `--label` trong `eval/results/benchmark_web.md`. Thêm `pyodide` 0.29.3 (đúng bản trang đang dùng) vào devDependencies của frontend
- **Góc đầu** (`edge_agent/perception/geometry.py`, chỉ bản web dùng): đạo hàm giải tích thay cho sai phân (12 lần chiếu điểm mỗi vòng lặp), dừng khi một bước nhỏ hơn 1e-6 thay vì 1e-10. Kết quả lệch so với bản chạy tới hội tụ hẳn: tối đa 7e-8 độ trên 20 giây mặt tổng hợp. Không đổi ngưỡng nào; bản thiết bị vẫn dùng OpenCV
- **Hai cửa sổ trượt** (`distraction._glances` 30 s, `QualityMonitor` 10 s): tổng cộng dồn như `Perclos` đã làm, thay cho cộng lại toàn bộ mẫu mỗi frame. Test hồi quy trace (M34) không đổi một số nào

| Đo trong Pyodide (Node, Mac ARM) | Trước | Sau |
|---|---:|---:|
| Clip YawDD, 1800 frame: p50 / p95 mỗi frame | 1,97 / 2,70 ms | 0,61 / 0,88 ms |
| Mặt tổng hợp 60 s: p50 / p95 mỗi frame | 1,47 / 1,94 ms | 0,56 / 0,72 ms |
| Số lần duyệt qua các điểm của mô hình mặt mỗi frame (clip YawDD) | 101 | 9,8 |
| So với cùng lời gọi trên thiết bị (clip YawDD) | 10,8 lần | 4,2 lần |

- **Đồng hồ từng chặng** (`frontend/src/live/perf.ts`, `agent.ts`): mỗi frame ghi thời gian lấy ảnh từ camera, MediaPipe, đo pixel, chuẩn bị ảnh cho YOLO, Python, cả frame; mỗi lần YOLO chạy ghi thời gian suy luận; mỗi frame ghi tuổi của kết quả YOLO đang dùng. Giữ 300 mẫu gần nhất, tóm tắt p50 / p95 / max. Ghi thêm MediaPipe được tạo với GPU hay CPU, số luồng wasm của YOLO, số frame camera giao mà vòng lặp không kịp xử lý (`presentedFrames` của `requestVideoFrameCallback`)
- **Hiện ở đâu:** "Chi tiết kỹ thuật" trên thẻ camera của `#/live` (4 dòng, rê chuột để xem đủ); theo heartbeat lên backend (`HeartbeatIn.perf`, cột `device_status.perf`, chỉ giữ bản mới nhất); tab "Đội xe" có cột "Tốc độ xử lý" (p95 cả frame, chi tiết trong tooltip). Chỉ là số mili giây, không có số đo nào về tài xế
- Tên trường tránh chữ `frame` (`total`, `samples`, `camera_delivered`, `camera_dropped`): bộ chặn dữ liệu giống ảnh của backend và publisher từ chối mọi khoá chứa chữ đó, và bộ chặn được giữ nguyên
- `perf_record` (publisher) lọc số đo trước khi gắn vào heartbeat: chặng lạ, số không hữu hạn hay ngoài khoảng bị bỏ, để heartbeat không bao giờ bị backend từ chối vì số đo tốc độ
- **Chưa làm / giới hạn:** Node không phải trình duyệt, Mac không phải hub: chưa có số canvas / MediaPipe / YOLO trên Android hay hub (phải mở `#/live` trên máy đó rồi đọc cột "Tốc độ xử lý"). Bản thiết bị (`edge_agent.main`) chưa gửi `perf`. Chưa cảnh báo khi kết quả YOLO quá cũ (việc riêng trong improvements)
- Test: 8 test Python (`test_m49_perf.py`: lọc số đo, heartbeat qua schema backend, bridge, chuỗi mặt của công cụ, bảng báo cáo), 2 test `test_geometry.py` (đạo hàm so với sai phân; số lần duyệt mỗi frame khi bám theo frame trước < 12), 5 test backend (`test_fleet.py`), 8 test frontend (`perf.test.ts`, nhãn). E2e: kịch bản tài xế đăng nhập kiểm thêm cột "Tốc độ xử lý" có số sau khi kết thúc chuyến. Tổng: 894 Python + 83 frontend + 3 e2e pass; ruff, typecheck, build sạch

<a id="m50"></a>

#### M50: Bản web: báo khi model điện thoại không còn cho kết quả, đẩy cảnh báo ngay, giờ chụp của frame, tải song song

**Xong là thấy gì:** YOLO chậm hoặc không tải được: HUD hiện "Không phát hiện được điện thoại", backend nhận `phone_detection_lost`; âm thanh cảnh báo của `#/live` không chờ vòng hỏi 300 ms; che camera không còn thành "Lỗi xử lý"

**Trạng thái:** Xong (06/10) (phần làm được ngay của ba việc "YOLO trong bản web", "độ trễ cảnh báo", "khởi động: tải song song" trong docs/improvements.md). Ngưỡng `phone.unknown_*` tạm; chưa có phép đo độ trễ tới loa

- **Model điện thoại không còn cho kết quả** (`PhoneHealth` trong `phone_detector.py`, `TripRuntime._track_phone`): frame không có kết quả YOLO mới (YOLO chậm hơn `phone.max_result_age_s`, model không tải được, worker chết) trước đây chỉ là "không rõ", tức không bao giờ có cảnh báo `phone` và không ai biết. Nay ≥ `phone.unknown_ratio` (0,8) của `phone.unknown_window_s` (10 s) gần nhất là "không rõ" thì HUD hiện chip "Không phát hiện được điện thoại" và backend nhận sự kiện hệ thống `phone_detection_lost` kèm tỉ lệ; xuống tới `unknown_clear_ratio` (0,5) thì `phone_detection_restored`. Các nhánh khác chạy như thường, trạng thái giám sát vẫn là `monitoring`. Cả hai bản: `#/live` gọi `expect_phone` (kể cả khi YOLO không tải được), thiết bị bật trừ khi chạy `--no-phone`
- **Đẩy thay cho hỏi** (`HudSource.subscribe`, `hudModel.urgentKey`): `LiveAgent` đưa trạng thái cho HUD ngay trong frame có cảnh báo mới, đổi mức, tạm ngưng giám sát, mất camera, lỗi xử lý, câu hỏi "Bạn còn ở đó không?", lời nhắc đăng ký. Vòng hỏi 300 ms giữ nguyên cho phần hiển thị và phát hiện treo. HUD của bản thiết bị (HTTP) chưa đổi
- **Giờ của frame** (`frontend/src/live/frameTime.ts`): dùng `captureTime` của `requestVideoFrameCallback` (rồi `presentationTime`, rồi giờ hiện tại như cũ) khi nó không ở tương lai, không cũ hơn 1 s và sau frame trước. Mọi thời lượng khối 7–12 đo không còn mang độ rung của thời gian xử lý. Thêm chặng `camera_lag` (từ lúc chụp tới lúc bắt đầu xử lý) vào số đo tốc độ của M49
- **Tải song song** (`LiveAgent.start`): Pyodide, file của MediaPipe (model + runtime wasm vào cache HTTP) và YOLO tải cùng lúc, bắt đầu ngay khi trang hỏi quyền camera; model mặt chỉ còn chờ thiết lập từ Python để khởi tạo. `WebAgent` đọc `thresholds.yaml` một lần thay vì hai
- **Sửa lỗi tìm ra khi chạy bản build thật trong trình duyệt:** frame không có mặt làm Python lỗi ở `bridge._floats`. Pyodide (0.28 trở lên) đưa `null` của JS sang thành giá trị riêng `JsNull`, không phải `None`, nên `points is not None` đúng và phép đổi mảng lỗi. Hậu quả: không có mặt 1 s là HUD báo "Lỗi xử lý" và `agent_error`, thay vì "tạm ngưng giám sát" theo M10 / M43 / M44. Trang nay gửi `undefined`, bridge coi `JsNull` là `None`. E2e trước đây luôn có mặt nên không bắt được; thêm kịch bản không có mặt
- **Chạy thử bản build thật** (MediaPipe + YOLO thật, Chromium không giao diện của Playwright, camera giả, không có mặt, 15 s; script dùng một lần): khởi động 11 s khi đã có cache; MediaPipe p50 11 / p95 44 ms (tạo với GPU), YOLO p50 175 / p95 200 ms một luồng, tuổi kết quả YOLO khi dùng p50 303 / p95 450 ms, Python 0,3 ms, từ lúc chụp tới lúc xử lý p50 11 / p95 16 ms, 85 / 350 frame camera không kịp xử lý; không lỗi, không có chip điện thoại
- **Chưa làm / giới hạn:** chưa đo "từ lúc bấm phím tới lúc loa kêu", nên lợi ích của phần đẩy mới là theo thiết kế (bỏ 0–0,3 s chờ). Chưa thử với camera và khuôn mặt thật. Ngưỡng `phone.unknown_*` đặt theo suy luận. Thời gian không phát hiện được điện thoại chưa vào bảng tổng kết chuyến
- Test: 15 test Python (`test_m50_phone_health.py`: cửa sổ và độ trễ hai chiều, YOLO chậm, khoảng trống frame, runtime, bridge, đọc ngưỡng một lần, `JsNull`), backend nhận hai sự kiện mới, 7 test frontend (`frameTime.test.ts`, `urgentKey`, bước khởi động), 1 kịch bản e2e mới (không có mặt). Tổng: 909 Python + 90 frontend + 4 e2e pass; ruff, typecheck, build sạch

<a id="m51"></a>

#### M51: Bản web: model mặt chỉ chạy "GPU" khi có GPU thật, YOLO hai luồng trên trang được cách ly, công cụ đo vòng lặp trong trình duyệt

**Xong là thấy gì:** `eval/results/benchmark_live.md`: máy không có GPU thật 20 → 30 FPS, YOLO 172 → 91 ms mỗi lần; "Chi tiết kỹ thuật" ghi WebGL là GPU thật hay vẽ bằng phần mềm

**Trạng thái:** Xong (06/10) (mục đa luồng của việc "YOLO trong bản web", một phần việc "đường đi của frame", công cụ của việc "đo bản web trên máy đích" trong docs/improvements.md). Mọi số đo là Chromium không giao diện trên Mac; chưa đo WebView Android hay hub

- **Công cụ đo** `frontend/bench/live.bench.mjs`: mở bản build thật (MediaPipe, YOLO, Pyodide thật) trong Chromium với camera giả của Chrome phát một clip dataset công khai có mặt, rồi đọc "Chi tiết kỹ thuật" của chính trang. Ép được delegate của MediaPipe (`--delegate`, khoá `dg.landmarks.delegate` trong localStorage) và cờ của Chrome (GPU thật hay phần mềm). Kết quả: [`eval/results/benchmark_live.md`](../eval/results/benchmark_live.md)
- **Model mặt (khối 3):** delegate "GPU" của MediaPipe chạy trên WebGL. Khi WebGL do bộ vẽ phần mềm đảm nhiệm (không có GPU dùng được), mỗi frame mất 45 ms so với 9 ms của delegate CPU, vòng lặp còn khoảng 20 FPS và bỏ 30 % frame camera. Trang nay hỏi tên bộ vẽ WebGL (`frontend/src/live/gpu.ts`) và chỉ dùng "GPU" khi đó là GPU thật. Trên GPU thật của máy đo hai delegate gần nhau (12,8 so với 15,4 ms). Số đo tốc độ (M49) thêm trường `gpu`: `hardware` / `software` / `none`
- **YOLO (khối 4):** trang được phục vụ kèm `Cross-Origin-Opener-Policy: same-origin` và `Cross-Origin-Embedder-Policy: require-corp` (`backend/static.py`, kể cả phản hồi 304; `vite.config.ts` cho dev / preview / e2e), nên wasm được dùng luồng. Số luồng lấy từ `phone.num_threads` (2), không quá số nhân. 172 → 91 ms mỗi lần; tuổi kết quả khi dùng p95 400 → 331 ms (hạn 600 ms). Pyodide và MediaPipe tải từ CDN vẫn chạy dưới cả `require-corp` lẫn `credentialless`
- **Lỗi lộ ra khi bật luồng:** ONNX Runtime khởi động các luồng từ chính file chứa mã nối của nó; khi mã đó bị gộp vào worker của trang thì mỗi luồng lại chạy code của worker và phiên không bao giờ sẵn sàng. Nay hai file runtime được phục vụ nguyên bản (`wasmPaths`). Worker tách hai bước: tải model song song với các phần khác (M50), tạo phiên khi đã biết số luồng
- **Đường đi của frame, đo rồi không làm:** đưa thẳng thẻ video cho MediaPipe thay cho canvas không đổi gì đo được (10,4 so với 11,1 ms). Vẽ + đọc lại pixel chỉ 0,5–1,8 ms, đo pixel 0,2 ms: không có gì để cắt trên máy này. Chuyển vòng lặp sang Worker chưa có lý do: sau M51 chỉ 2–7 / 300 frame không kịp xử lý
- `getUserMedia` xin thêm `frameRate: { ideal: 30 }`
- **Chưa làm / giới hạn:** chưa kiểm WebView của Capacitor có đặt được hai header cho file trong app không; nếu không thì YOLO trong APK vẫn một luồng. Chưa đo trên máy 4 nhân (hai luồng YOLO có giành CPU với vòng chính không). Tên bộ vẽ phần mềm nhận theo danh sách (SwiftShader, llvmpipe, …): một GPU thật nhưng rất yếu vẫn được coi là GPU thật. Lần chạy 6–9 s khởi động là khi đã có cache
- Test: 1 test backend (`test_static.py`: header trên mọi file và trên 304), 5 test frontend (`gpu.test.ts`: nhận bộ vẽ, chọn delegate, số luồng), các test `perf` nhận trường `gpu`. E2e chạy trên trang đã cách ly (dashboard, `#/live`, `#/drive`, API khác cổng). Tổng: 911 Python + 95 frontend + 4 e2e pass; ruff, typecheck, build sạch

<a id="m52"></a>

#### M52: Bản ghi đầu tiên từ camera: ba phiên ban ngày của một người, có nhãn bấm phím

**Xong là thấy gì:** [`eval/results/own_recordings.md`](../eval/results/own_recordings.md) có bảng độ trễ từ lúc bấm phím tới cảnh báo cho từng loại hành động, bảng nhìn xuống so với nhắm mắt, bảng gọi / nhắn tin, trên bản ghi thật thay cho một video dataset

**Trạng thái:** Một phần (06/10) (ba phiên ban ngày của việc "ghi số trực tiếp từ camera" trong docs/improvements.md; năm phiên tối đã ghi tối 06/10 nhưng chưa phân tích; còn sáu phiên và người thứ hai; phiên chói / ngược sáng và phiên kính râm đã bỏ theo quyết định 06/10). Chỉ là dữ liệu: không đổi code, không đổi ngưỡng

- **Dữ liệu:** `tools/record_trace.py record` (M39) trên camera laptop, một người, không kính, ban ngày, tốc độ giả lập 60 km/h. Ba phiên, 20,2 phút, 29,8–29,9 FPS, thấy mặt 97–99 %: `day_eyes` (ngồi yên, nhắm mắt, ngáp, nói chuyện, gục đầu), `day_look` (nhìn lệch bốn kiểu, cách nhau 40 s), `day_phone` (gọi và nhắn tin xen kẽ, cách nhau 40 s). File `data/own_traces/quan_v2.pkl` chỉ chứa số, không vào git. Một nhãn `c` bấm nhầm ở cuối phiên đầu (2,5 s, không có điện thoại trong hình) đã được bỏ; bản chưa sửa giữ ở `quan_v2.raw.pkl`
- **Độ trễ, tính từ lúc bấm phím tới lúc khối 12 phát cảnh báo (PRD: p95 ≤ 3 s):** nhắm mắt ≥ 1,5 s 11 / 11, p50 1,56 s, p95 1,67 s. Gọi điện 5 / 5, 2,30–2,77 s. Nhắn tin 3 / 5, 2,33–2,64 s. Nhìn sang bên 3 / 3 và quay ra sau 2 / 2, 2,83–3,04 s, hai lần vượt 3 s (người ghi bấm phím rồi mới quay đầu). Ngáp 5 / 5, khoảng 2,0 s
- **Cúi nhìn điện thoại trên đùi: 0 / 4 ra `off_road`, 3 / 4 ra L3 `microsleep`.** Người ghi nhìn xuống chủ yếu bằng mắt, đầu chỉ cúi khoảng 8,5°, dưới `microsleep_deep.bowed_pitch_deg` (10°) của M25; khối 7 coi 82 % số frame là mắt nhắm. Một lần nhắn tin ở phiên điện thoại cũng ra L3 theo cách này
- **Nhìn bảng đồng hồ: 0 / 3, không cảnh báo nào.** Góc đầu không đổi; `eyeLookDown` trung vị 0,34 so với 0,13 khi ngồi yên, nhưng chưa khối nào dùng tín hiệu này
- **`eyeLookDown` cao cả khi nhắm mắt thật** (trung vị 0,73, cao hơn 0,58 khi nhìn xuống): không dùng riêng nó để tách nhìn xuống với nhắm mắt được. EAR / mốc tách được ở trung vị (0,10 so với 0,33) nhưng biên hẹp (p90 0,18 so với p10 0,19)
- **`phone_kind` đúng ở mọi frame có điện thoại** (gọi 731 / 731, nhắn tin 551 / 551). Hai lần nhắn tin không ra cảnh báo vì YOLO chỉ thấy điện thoại ở 19 % và 28 % số frame của lần đó. Ngoài các nhãn, YOLO không thấy điện thoại ở frame nào
- **Gục đầu: 2 / 9 ra sự kiện `nod`**, 3 lần ra `bow`, 4 lần không ra gì
- **Báo sai:** 0 cảnh báo trong 1,6 phút ngồi yên và nói chuyện. 10 cảnh báo nằm ngoài nhãn (36,4 mỗi giờ trong báo cáo) đều là hệ quả của hành động diễn: 4 lần L3 do cúi nhìn điện thoại bị coi là nhắm mắt, còn lại là điểm buồn ngủ tăng sau 14 lần nhắm mắt liên tiếp. Con số này không phải báo sai mỗi giờ lái
- **Chưa làm / giới hạn:** một người, một buổi, diễn trước laptop; mỗi loại 2–11 mẫu nên p95 chỉ là số tham khảo. Chưa có phiên tối, chói, kính râm. Mục 5 của báo cáo (theo tag `mask`) không có nhóm nào để so. Trace không giữ ảnh nên không chạy lại được model khác (INT8) trên các phiên này. Chưa sửa gì theo các phát hiện trên: đó là việc "nhìn xuống hay nhắm mắt" và "theo dõi hướng mắt" trong docs/improvements.md
- Test: không đổi code nên không chạy lại bộ test

<a id="m53"></a>

#### M53: UTA-RLDD: dò ngưỡng buồn ngủ có tập kiểm tra giữ riêng, ablation, cá nhân hoá (khối 9, `tools/uta_rldd.py`)

**Xong là thấy gì:** [`eval/results/dataset_uta_rldd.md`](../eval/results/dataset_uta_rldd.md) có số trước / sau trên 24 người dùng để dò và 24 người giữ riêng; `python tools/uta_rldd.py compare --split test --set ...` chạy lại được từ trace; `config/thresholds.yaml` có ba khoá đổi kèm lý do

**Trạng thái:** Xong (06/10). Nhóm việc 2 của docs/improvements.md (dò ngưỡng trên UTA-RLDD, tín hiệu tạm, cá nhân hoá). Đổi hành vi theo quyết định của anh ngày 06/10

- **Dữ liệu:** UTA-RLDD bản Kaggle, 48 người (fold 1–4), 145 video, 25,0 giờ, nhãn tự đánh giá theo cả video (`0` tỉnh, `5`, `10` buồn ngủ). Trace khối 2–12 một lần trên Kaggle Notebook (`notebooks/uta_rldd_kaggle.ipynb`, hai phiên, ~16 giờ, 42 frame / s trên 4 CPU), không video nào lỗi. Trace chỉ chứa số, nằm ở `data/eval_traces/uta_rldd/` (không trong repo)
- **Chia theo người:** dev = fold 1–2, test = fold 3–4 (`eval/splits/uta_rldd_{dev,test}.txt`). Dò 57 cấu hình trên dev (mỗi lần 1–2 khoá); test chỉ chấm một lần cho ngưỡng cũ và bộ đã chọn
- **Đổi ba khoá:** `risk.drowsy.weight_slow_blink` 10 → 0, `risk.drowsy.weight_brow` 10 → 0, `risk.trend.level` 1 → 0 (chỉ ghi nhận). Chớp chậm và nhướn mày vẫn được đo và ghi, không cộng vào `drowsy_score`; tổng bốn trọng số còn lại đúng 100
- **Kết quả trên test (4,08 giờ video tỉnh táo):** cảnh báo sai nhánh buồn ngủ 8 → 4 lần, 1,96 → 0,98 / giờ (CI 95 % 0,27–2,51); FAR theo cửa sổ L1 3,9 % → 1,5 %; AUC `drowsy_score` giữa `10` và `0` 0,917 → 0,924; video `10` có cảnh báo 17 → 15 / 24, đạt L3 12 → 12 / 24. Trên dev: 9 → 5 lần, AUC 0,793 → 0,859, 16 → 14 / 24
- **Vì sao bỏ hai tín hiệu:** trên cùng một người (video `0` so với `10`), chớp chậm và nhướn mày không tách được (sign test p = 0,84 / 1,0 trên dev; 0,29 / 0,51 trên test). PERCLOS (AUC 0,82–0,87) và microsleep (0,79–0,80) là hai thành phần có tác dụng
- **Luật `trend`:** có mặt trong 5 / 9 cảnh báo sai trên dev và 3 / 8 trên test. Video chỉ dài 10 phút nên chưa biết nó có ích trên chuyến dài hay không; bật lại bằng một khoá
- **PERCLOS P80** (EAR < 0,48 lần mốc) không tách tốt hơn định nghĩa hiện tại (0,65): AUC 0,873 so với 0,892 trên test. Giữ `perclos_close_ratio`
- **Xấp xỉ EU DDAW** (`10` ≈ KSS ≥ 8, mỗi người một sự kiện): 62,5 % trên test (CI 90 % 45,8–76,7), mốc là trung bình > 40 %, cận dưới > 20 %
- **Cá nhân hoá** ([`eval/results/personalization_uta_rldd.md`](../eval/results/personalization_uta_rldd.md)): mốc đăng ký giả (từ đầu chính video, hoặc từ video `0` của người đó) không giảm báo sai so với mốc tự học: 9 / 9 / 9 lần trên 48 người. Không ghi "đã cá nhân hoá" là lợi ích đã đo
- **Bộ cũ không tệ đi:** FL3D cảnh báo microsleep (83 đúng, 1 sai) và L3 lặp lại không đổi; L2 đúng 15 → 13, báo sai không đổi. YawDD, SUST giống hệt. Test hồi quy trace được ghim lại (hai video FL3D có `drowsy_score` thấp hơn, sự kiện và cảnh báo không đổi)
- **Công cụ:** `tools/uta_rldd.py` (`report`, `signals`, `grid`, `compare`, `personal`); mặc định cho khối 5 quyết định lại theo ngưỡng hiện tại (M54 đổi `low_light_brightness` sau khi trace; số báo sai và số người có cảnh báo không đổi)
- **Chưa làm / giới hạn:** người ngồi trước laptop, không lái xe; nhãn cho cả video và tự đánh giá; chỉ tiêu PRD ≤ 1,0 / giờ chưa kết luận được (cận trên 2,51); `l1` 40 → 50 mới thử trên dev; trọng số gục / ngáp chưa kết luận (sự kiện hiếm); không có thuộc tính đeo kính; MediaPipe trên Kaggle là 1.0.1 (các báo cáo khác 0.10.21, cùng file model); các báo cáo `dataset_fl3d.md` / `dataset_yawdd.md` / `dataset_sust_ddd.md` chưa chạy lại. Phần còn lại: docs/improvements.md mục hoãn "phần còn lại sau UTA-RLDD"
- Test: 12 test mới bằng chuỗi số giả (`test_uta_rldd_tool.py`); 928 Python pass

<a id="m54"></a>

#### M54: Nhóm việc 1 của improvements trên các phiên tự ghi

**Xong là thấy gì:** phòng tối vừa (mặt sáng 32–35 / 255), ngồi yên mắt mở không còn bị hú còi ngủ gật; `eval/results/own_recordings.md` có 12 phiên (phiên INT8 để riêng); mỗi việc 2–8 của nhóm 1 trong docs/improvements.md có số đo và kết luận

**Trạng thái:** Xong (06/10), ngưỡng tạm, một người. Số M54 để tránh trùng với M53 (UTA-RLDD) đang làm song song. Người ghi dừng ở 13 phiên (06/10); còn thiếu người thứ hai, liếc bằng mắt mà đầu đứng yên, cúi nhẹ kèm nhắm mắt

- **Dữ liệu thêm:** năm phiên tối và `phone_holds` trong `data/own_traces/quan_v2.pkl` (9 phiên, 44 phút); `phone_int8` để riêng trong `quan_int8.pkl`. Phiên chói / ngược sáng và kính râm đã bỏ; việc "phát hiện mắt bị che" chuyển sang hoãn, FMEA dòng 5 vẫn mở
- **Đổi ngưỡng duy nhất: `eye_state.low_light_brightness` 60 → 0** (mặt tối thì EAR kèm phiếu `eyeBlink` quyết định, không giao cho CNN mắt). Phiên tự ghi mặt 32–35: ngồi yên mắt mở 5,5 phút có 8 lần L3 sai (CNN nói "nhắm" ở 28 % số frame trong khi EAR 0,71 lần mốc) → 0; nhắm mắt đạt L3 vẫn 27 / 27. FL3D làm tối nhẹ trong RAM (mặt 49): microsleep đạt L3 0 / 24 → 12 / 24. Replay FL3D gốc 72 → 74 / 95 microsleep có L3 mới; YawDD, SUST không đổi cảnh báo. Test hồi quy trace ghim lại kèm lý do; `lighting_transforms.md` chạy lại
- **Không đổi:** `quality.dark_face_brightness` 25 (mặt 10–12 không đọc được: tắt giới hạn thì 5 lần L3 sai trong 2,9 phút); ảnh xám / IR vẫn giao cho CNN (FL3D bỏ màu vẫn 0 / 24, chưa có ảnh IR thật)
- **INT8:** file `yolov8n_int8.onnx` không phát hiện được điện thoại nào (phiên ghi 0 / 14 682 frame; trên 60 ảnh State Farm điểm lớp ra 0 ở mọi ảnh, FP32 trung vị 0,64). Giữ FP32 làm mặc định. Phép so cũ chạy trên clip không có điện thoại nên không lộ
- **Nhìn xuống bị báo ngủ gật (8 / 20 lần), chưa sửa được:** thử bảy bộ ngưỡng hiện có bằng replay, bộ nào bớt báo nhầm cũng mất microsleep thật của FL3D (bớt 2 thì mất 10 / 74). Ngưỡng M25 giữ nguyên
- **Hướng mắt, chỉ đo offline:** blendshape `eyeLookDown` không dùng được (FL3D tỉnh: 12–76 lần sai trong 26 phút); vị trí mống mắt `iris_y` ≥ −0,03 giữ 2 s bắt 15 / 23 lần nhìn xuống với 3 lần sai trong 73 phút. Chưa đưa vào code
- **Điện thoại:** gọi 9 / 9 (hai tay), nhắn tin 6 / 11 và chậm (p50 3,15 s); một lần cầm lệch sang bên nằm ngoài vùng tài xế
- **Liếc cộng dồn:** đã đọc NHTSA 2013 (từng lần ≤ 2 s, tổng ≤ 12 s mỗi tác vụ) và tóm tắt AttenD (bộ đệm 2 s); không nguồn nào cho ngưỡng dùng thẳng được
- **Công cụ:** `tools/record_trace.py` thêm tám phím nhãn (`m g j k l w v p`)
- **Ba phiên ghi sau cùng (`look_down`, `glances`, `head_turn`; 13 phiên, khoảng 80 phút):**
  - Nhìn xuống mà đầu không cúi (giá đỡ thấp, bảng đồng hồ, cần số): 0 / 12 có cảnh báo. `iris_y` ≥ −0,03 giữ 2 s bắt 20 / 30 lần nhìn xuống các kiểu, 4 lần sai trong 93 phút
  - Cúi và nhắm mắt thật: L3 7 / 7. Với người ghi, `microsleep_deep.blink` 0,6 đưa báo nhầm khi nhìn xuống từ 7 / 30 về 1 / 30 mà vẫn bắt 47 / 48 lần nhắm mắt; FL3D mất 16 / 74 nên không đổi
  - Liếc lặp lại 30 s: 0 / 4 có cảnh báo; `off_road_ratio` 0,55–0,67 so với tối đa 0,21 ở mọi lúc khác và 0,00 khi nhìn gương; bộ đệm 2 s kiểu AttenD cạn sau 4–8 s
  - Phiên `eyes_only` ghi ra thành quay đầu 17–70° nên đổi tên `head_turn`; quay đầu 17–30° giữ 4 s chỉ ra `off_road` 1 / 5 lần. Liếc ngang chỉ bằng mắt chưa có dữ liệu
- **Ngưỡng eyeBlink theo từng tài xế (khối 6 đăng ký, khối 7): có sẵn, mặc định tắt.** Bước nhắm mắt của đăng ký ghi `DriverProfile.blink_closed`; `microsleep_deep.enrolled_blink_ratio` > 0 thì frame "nhắm sâu" cần eyeBlink đạt tỉ lệ đó của giá trị riêng. Đo: tỉ lệ 0,85 đưa báo nhầm khi nhìn xuống từ 7 / 30 về 2 / 30 và giữ 47 / 48 lần nhắm mắt của người ghi, nhưng FL3D (lấy lần microsleep đầu của mỗi video thay cho đăng ký) từ 77 / 94 xuống 66 / 94; 0,8: 4 / 30 và 75 / 94. Người ngủ thật nhắm nông hơn lúc cố ý nhắm, nên để 0. Ba test mới
- **Quyết định 06/10:** không bật luật cảnh báo cho liếc ngắn cộng dồn; `off_road_ratio`, `glance_count` vẫn chỉ đo. Việc này chuyển sang phần "đã bỏ" của improvements
- **Phát hiện ngoài phạm vi, chưa làm:** bản web dùng `eyeBlink` với ngưỡng của CNN (0,6 / 0,8) ở các frame khối 5 quyết định; replay cho thấy nó không đạt "nhắm sâu" (0 / 17), chưa đo trên `#/live`
- Test: 931 Python pass

<a id="m55"></a>

#### M55: Hướng mắt nhìn xuống, chỉ đo (khối 6, 8) và phép đo trên 3MDAD

**Xong là thấy gì:** [`eval/results/gaze_3mdad.md`](../eval/results/gaze_3mdad.md) cho biết hệ thống trả lời gì với 16 hành động của 50 tài xế trong xe thật; trace của `seq_eval` / `record_trace` có thêm `gaze_down_deg`, `gaze_down_s`. Không cảnh báo nào đổi

**Trạng thái:** Xong (06/10), chỉ đo. Việc 2 và 3 của nhóm 1 trong docs/improvements.md, làm bằng dữ liệu có sẵn vì không ghi thêm phiên nào nữa

- **Dữ liệu:** LISA Gaze v2 không dùng được (ảnh cắt sát vùng mắt, MediaPipe tìm ra mặt ở 0,7 % số ảnh). 3MDAD bản ngày, góc camera trước (`RGB2`): 50 tài xế × 16 hành động, 111 017 frame; mỗi tài xế chạy qua khối 2–12 như một chuyến, lái bình thường trước. Tốc độ khung hình không được lưu, 30 FPS là giả định; mỗi hành động dài 3–5 s; nhãn phủ cả đoạn. Trace số ở `data/eval_traces/3mdad_day.pkl`
- **Hệ thống hiện tại trên 3MDAD (số tài xế có cảnh báo trong hành động):** lái bình thường 1 / 50 (một L3 sai); nhắn tin tay phải `phone` 20 / 50, `off_road` 4 / 50; **nhắn tin tay trái `phone` 0 / 50, `off_road` 1 / 50** (điện thoại hầu như không lọt vùng tài xế); gọi điện tay phải `phone` 2 / 50, tay trái 0 / 50 (mặt chỉ được thấy ở 42 % số frame khi tay phải che); nói chuyện với hành khách `off_road` 18 / 50. Nhắn tin không lần nào ra L3 `microsleep` (0 / 100)
- **Khối 6:** `FrameFeatures.iris_y` (mống mắt so với đường nối hai khoé mắt, trung bình hai mắt); `iris_offsets` chuyển từ `tools/seq_eval.py` vào `edge_agent/perception/features.py`
- **Khối 8, chỉ đo:** góc nhìn xuống = góc cúi đầu so với tư thế nhìn đường + `distraction.gaze.iris_gain` (100) × độ lệch `iris_y` so với mốc; `gaze_down_duration` = thời gian ở mức `gaze.down_deg` (12°) trở lên. Mốc `iris_y` là trung vị 5 s đầu lúc xe chạy rồi bám theo frame nhìn đường. Frame khối 7 coi là nhắm chặt (`DrowsinessState.deep_closed`, mới) thì bỏ qua; hở dưới `on_road_confirm_s` được nối. Không luật nào của khối 9 đọc
- **Số đo, giữ ≥ 2 s ở 12°:** 3MDAD nhắn tin tay phải 7 / 50, tay trái 13 / 50, chỉnh radio 10 / 50, gọi điện tay phải 10 / 50, lái bình thường và mệt mỏi 0 / 50. Bản tự ghi: điện thoại trên đùi 4 / 7, nhắn tin 1 / 11, nhìn giá đỡ / bảng đồng hồ / cần số 0 / 12, nhắm mắt thật 0 / 48, ngoài nhãn 0 lần trong 67 phút. FL3D 47 phút: 2 lần ngoài nhãn microsleep, 6 lần trong microsleep thật
- **Kết luận:** chưa đủ để thành cảnh báo (bắt 14–26 % số lần nhắn tin; FL3D khoảng 2,6 lần mỗi giờ). Không dùng được để sửa lỗi "nhìn xuống bị báo ngủ gật" vì nó bật cả trong microsleep thật. Mống mắt riêng lẻ tách nhắn tin với lái bình thường kém hơn góc cúi đầu (AUC trung vị theo tài xế 0,75 so với 0,82)
- **Giới hạn:** diễn, đoạn ngắn, một vị trí camera; hệ số `iris_gain` chung không hợp cả người trong xe lẫn người ngồi trước laptop; chưa đo trên chuyến dài của người thật (trace UTA-RLDD hiện có không có cột mống mắt)
- Test: 944 Python pass (9 test chuỗi số giả cho góc nhìn xuống, 4 test cho công cụ); test hồi quy trace không đổi

<a id="m56"></a>

#### M56: Phần làm được ngay của nhóm việc 1 (khối 5, 6, 7, 8)

**Xong là thấy gì:** bản web / APK với camera xám / hồng ngoại không còn bỏ sót mọi lần nhắm mắt (replay: bản tự ghi 0 / 48 → 46 / 48, FL3D 0 / 95 → 64 / 95); `DriverProfile` có `road_iris_y`; các việc 2, 3, 5 của docs/improvements.md chỉ còn phần chờ dữ liệu hoặc quyết định

**Trạng thái:** Xong (07/10), ngưỡng tạm. Mọi số là replay trên trace số (bản tự ghi 12 phiên, FL3D, YawDD, SUST, UTA-RLDD 145 video); chưa đo trên `#/live` và chưa có ảnh IR thật. Bản thiết bị (`eye_state.source: cnn`) không đổi hành vi

- **Lỗi của bản web / APK:** khối 5 ở đó dùng blendshape `eyeBlink` thay CNN mắt, nhưng khối 7 so nó với ngưỡng của CNN (nhắm 0,6, mở 0,4, nhắm sâu 0,8). Mắt nhắm thật cho `eyeBlink` 0,55–0,7, nên không lần nào đạt "nhắm sâu". Camera màu chỉ dính ở frame hai mắt lệch; camera xám / hồng ngoại thì `eyeBlink` quyết định mọi frame: nhắm mắt đạt L3 0 / 48 (bản tự ghi), 0 / 95 (FL3D), 1 / 48 người buồn ngủ của UTA-RLDD có L3
- **Sửa:** khối 5 ghi nguồn điểm vào `FrameFeatures.p_closed_source` (`cnn` / `blendshape`); khối 7 dùng `drowsiness.eye.blendshape_closed` 0,4, `blendshape_open` 0,3, `drowsiness.microsleep_deep.blendshape` 0,55 khi nguồn là `eyeBlink`. `DrowsinessState.eye_source` có thêm giá trị `blendshape`
- **Số đo khi `eyeBlink` quyết định mọi frame (cũ → mới; đường EAR của thiết bị để so):**
  - Bản tự ghi, nhắm mắt đạt L3: 0 / 48 → 46 / 48 (47 / 48); nhìn xuống bị báo L3: 0 / 30 → 3 / 30 (7 / 30)
  - FL3D, microsleep có L3 mới: 0 / 95 → 64 / 95 (74 / 95); L3 ngoài microsleep 0 → 2 (3)
  - YawDD (không có ngủ gật thật), L3: 0 → 1 (1)
  - UTA-RLDD video tỉnh, cảnh báo buồn ngủ: 0 → 4 lần, 0,50 / giờ (1,13 / giờ); video buồn ngủ, người có L3: 1 / 48 → 19 / 48 (24 / 48)
  - Đã thử 0,5 / 0,35 / 0,55 (FL3D 62 / 95), 0,4 / 0,3 / 0,5 (FL3D 72 / 95 nhưng YawDD 5 lần L3), 0,4 / 0,3 / 0,6 (FL3D 57 / 95); bảng ở `config/thresholds.yaml`
- **Camera màu trên bản web (chỉ frame hai mắt lệch):** bản tự ghi và UTA-RLDD video tỉnh không đổi; FL3D 75 → 76 / 95, L3 ngoài microsleep 3 → 4; YawDD sự kiện microsleep 2 → 7, L3 0 → 1 (thiết bị: 4 và 1)
- **Mốc mống mắt theo tài xế (khối 6 đăng ký, khối 8):** bước nhìn đường ghi `DriverProfile.road_iris_y` (trung vị, bỏ frame chớp); `DistractionAnalyzer.set_road_pose` nhận thêm `iris_y` và dùng thay cho 5 s đầu lúc xe chạy. Vẫn chỉ đo. Bản tự ghi và 3MDAD: số lần góc nhìn xuống giữ 2 s không đổi (5 s đầu ở đó cũng là nhìn đường). Mốc của 50 tài xế 3MDAD: p10–p90 từ −0,138 tới −0,051. Hệ số `iris_gain` theo tài xế không lấy được từ bước này
- **Đo, không đổi code:**
  - Ngữ cảnh điện thoại cho lỗi "nhìn xuống bị báo ngủ gật": 3 / 7 lần báo nhầm có điện thoại trong vùng tài xế; thử "thấy điện thoại thì cần `eyeBlink` cao hơn 0,1–0,3" đưa 7 → 6 hoặc 5 / 30. Không có dữ liệu ngủ gật khi cầm điện thoại để kiểm mặt trái. Không làm
  - Quy tắc "đầu cúi" (`gaze_down` của khối 7) trên UTA-RLDD, 145 video, 25 giờ: bật 8 / 19 / 72 s ở ba mức 0 / 5 / 10. Tắt quy tắc: L3 microsleep ở video buồn ngủ 211 → 212, người có L3 vẫn 24 / 48; cảnh báo `off_road` 13 → 11 (buồn ngủ), 4 → 3 (tỉnh)
  - Gục đầu trên bản tự ghi: phiên `look_down` 9 / 9, cúi nhìn 0 / 12 lần ra `nod`, 7 lần cúi kèm nhắm mắt ra `bow` (vẫn L3 7 / 7 nhờ microsleep). 7 lần sót ở phiên `day_eyes`: gục 13–16° so với ngưỡng 15°, mất mặt 11–18 % số frame, mắt không nhắm. 14 bộ ngưỡng `nod.*`: tốt nhất 12 / 18 (`pitch_down_deg` 12) với số `bow` 22 → 37; bộ tốc độ của M12 10 / 18. Giữ nguyên
  - 3MDAD bản đêm hồng ngoại (`IR2`, 19 tài xế, ảnh 16 bit): MediaPipe tìm ra mặt ở 12–30 / 380 frame thử (3–8 %) với bốn cách đổi sang 8 bit. Không dùng được
  - UTA-RLDD có cột mống mắt: trace lại 18 video có sẵn trên máy (6 người, 2,8 giờ; `data/eval_traces/uta_rldd_iris/`). Góc nhìn xuống giữ ≥ 2 s: 19 lần ở video tỉnh (19 / giờ, 4 / 6 video), 2 lần ở mức 5, 11 lần ở video buồn ngủ; 20 / 32 lần của một người. Không có nhãn nhìn xuống. Không trace lại 145 video trên Kaggle
- **Giới hạn:** ngưỡng `eyeBlink` dò trên chính các bộ dùng để báo cáo, không có tập giữ riêng; "mọi frame do `eyeBlink` quyết định" là video màu chạy như thể camera xám, không phải ảnh IR; bản web chưa build lại và chưa chạy `#/live`; các script đo là script tạm, không nằm trong repo (số FL3D lặp lại được bằng `tools/seq_eval.py fl3d --replay block5 --set eye_state.source=blendshape --set eye_state.always_run=true`)
- Test: 953 Python pass (9 test mới bằng chuỗi số giả: 5 khối 5 / 7, 1 bridge web, 2 khối 8, 1 đăng ký); test hồi quy trace không đổi; `ruff` sạch ở `edge_agent/`, `tools/`, `tests/` (8 lỗi có sẵn ở `scripts/`)

### Version 4: thiết kế lại giao diện (M57–M65)

Theo hai bản thiết kế: HUD (21 màn hình, "DriverGuard HUD redesign") và web (10 màn hình, "DriverGuard Web redesign").
Chỉ đổi giao diện (`frontend/`): backend, edge agent và API giữ nguyên, không đổi logic cảnh báo. Tính năng đang có mà
bản thiết kế chưa vẽ thì vẽ theo phong cách mới, không bỏ. Quyết định ngày 07/10: font Inter, nút HUD 56 px như các màn
hình, bỏ nhãn vùng tốc độ "Nhanh" / "Rất nhanh".

<a id="m57"></a>

#### M57: Nền giao diện chung (frontend)

**Xong là thấy gì:** dashboard, trang đăng nhập và HUD dùng nền tối #0A0A0A, chữ Inter; thẻ của dashboard là thẻ "kính"; FPS của `#/live` không đổi (21 → 20, trong sai số đo)

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/`; backend, edge agent và API không đổi. Bố cục từng màn hình chưa đổi (M58–M64)

- **Font:** Inter tự đóng gói (`@fontsource/inter` 400–800, có bộ chữ tiếng Việt), bỏ `@fontsource/be-vietnam-pro`; không tải Google Fonts vì HUD có thể không có mạng
- **Token HUD** (`src/index.css`, `@theme`): nền #0A0A0A, mặt thẻ #141414 / #1F1F1F, chữ #F5F5F5 / #B8C2D0 / #8A8A8A (≥ 4,5 : 1 trên nền và mặt thẻ), bình thường #4ADE80; chú ý / cảnh báo / nguy hiểm / thiết bị / xi nhan giữ màu cũ, trùng bản thiết kế
- **Token dashboard** (`src/styles.css`): chỉ còn giao diện tối (bản thiết kế không có giao diện sáng); nền trang có vệt sáng góc trên trái như bản thiết kế; thẻ, ô số liệu, thanh trên dùng nền kính; nút chính trắng chữ đen, bo 12 px
- **Lớp dùng chung:** `.glass` (thẻ kính) và `.glass-tint` (thẻ ánh màu theo `--tint`, cho ghi chú thiết bị / chú ý / cảnh báo); blur đặt qua biến `--glass-backdrop`, đổi thành `none` là tắt ở nơi tốn frame
- **Sửa lỗi của bản thiết kế:** ô nhập / select luôn có màu chữ sáng và `<option>` nền tối (bản thiết kế để chữ đen trên nền đen); không có nền trắng hay chữ cam tối trên nền tối trong token
- **Đo FPS `#/live`** (`frontend/bench/live.bench.mjs`, Chromium không GPU, camera giả 30 s): trước 21 FPS, cả frame p50 12,9 / p95 23,8 ms; sau 20 FPS, p50 12,6 / p95 23,5 ms. M57 chưa đặt blur nào lên HUD hay `#/live`; M58 dùng thẻ kính trên HUD thì đo lại
- **Giới hạn:** chưa xem dashboard sau đăng nhập có dữ liệu thật (chỉ chụp trang đăng nhập và `#/hud-preview`); biểu đồ, huy hiệu mức dùng token nên đổi màu theo, chưa soát từng tab
- Test: 95 test frontend pass, typecheck sạch, build sạch

<a id="m58"></a>

#### M58: HUD khi đang lái (khối 13)

**Xong là thấy gì:** `#/hud`, `#/hud-preview` và HUD trong `#/live` có các màn đang lái của bản thiết kế: L0 thẻ xanh, L1 thẻ vàng + viền màn hình, L2 thẻ cam đặc + viền, L3 màn đỏ toàn phần; thẻ "Độ mệt và thông số" có biểu đồ 15 phút; thẻ tốc độ hình bát giác có số P / D và xi nhan; dãy nút dưới

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/` (và thêm `window_min` vào `trip` của M65). Màn xin đồng ý / đăng ký / sự cố / "Bạn còn ở đó không?" nằm trong khung mới nhưng ruột vẫn như cũ, làm ở M59

- **Theo Design System "DriverGuard"** (link thứ ba, tài liệu chuẩn khi canvas lệch): token `card-hi / mid / lo`, `tile`, `rim`, kính `blur(18px) saturate(120%)`; xi nhan màu vàng `level-1` (không còn xanh ngọc); đỏ L3 `#ef4444 → #dc2626 → #991b1b`; bo góc tối đa 16 px; chữ tối đa 600, 700 chỉ cho câu L2 / L3; component `.dg-card`, `.dg-tile`, `.dg-alert l0 / l1 / l2 / sys`, `.dg-chip`, `.dg-btn`, `.dg-meter`, `.dg-backdrop`, `.dg-ring-1 / 2` trong `src/styles.css`
- **Bố cục 1280 × 800** như canvas: thanh trên 72 px (DRIVERGUARD, camera, âm thanh, mô phỏng, dashboard, giờ), nội dung `1fr | 400px`, dãy nút dưới (ghi chú hoặc "Cảnh báo này sai? · còn m:ss", "Đổi tài xế ›", "Kết thúc chuyến ›", nút 56 px). Màn hẹp xếp dọc; không tràn ngang ở 390 / 768 / 1280 px
- **Số liệu của chuyến lấy từ edge agent (M65):** ô "Đã lái liên tục", ô "Cảnh báo gần nhất · HH:MM · lý do", biểu đồ `recent_minutes` (cột theo dải `score_l1` / `score_l2` của chuyến, phút nghỉ là khoảng trống, vạch "Nhắc nghỉ" ở `score_l1`), dòng chi tiết L2 "Phát hiện lúc … · nhìn lệch … giây · không bật xi nhan". HUD không giữ ngưỡng nào
- **Giữ:** không hiện mã L0–L3, L3 không có nút, ban đêm L0–L1 dịu 80 %, hiện trong 150 ms / hạ mức mờ dần, L3 nhấp nháy 1 Hz, dải vàng "Âm thanh cảnh báo chưa bật"
- **Khác bản thiết kế:** bỏ nhãn vùng tốc độ (quyết định 07/10), chip tốc độ ghi "Đang chạy" / "Xe dừng" / "Mất tín hiệu xe"; máy chậm ghi "cảnh báo có thể trễ" chứ không ghi "đang giảm tải" (chưa có giảm tải); nút "Chạy mô phỏng" và "Dashboard" giữ thành ô icon trên thanh trên
- **Hàm thuần mới** (`hudModel.ts`, `format.ts`): `fatigueBand`, `trendSlots`, `fatigueSummary`, `splitAction`, `alertDetail`, `footerNote`, `durationText`, `hourMinute`; nhãn ngắn `REASON_SHORT`
- **Đo FPS `#/live`** (Chromium không GPU, camera giả 30 s): 20 FPS như trước; cả frame p50 12,6 → 14,5 ms, p95 23,5 → 23,6 ms. Camera giả không có mặt nên HUD lúc đo ở màn "không thấy mặt", chưa đo màn đang lái có kính mờ trên máy yếu
- **Sửa sau khi xem (07/10, theo ảnh chụp của người dùng):**
  - Khung 1280 × 800 cố định của bản thiết kế, phóng to / thu nhỏ theo màn hình (`HudStage`: màn ngang rộng ≥ 1024 px; viền thừa cùng màu nền). Trước đó bố cục co giãn tự do: màn thấp thì ô tràn khỏi thẻ, màn lớn thì chữ nhỏ và chừa khoảng trống. Điện thoại và màn dọc vẫn xếp dọc
  - Hàng "Độ mệt và thông số" cao 210 px như canvas
  - Kéo sớm phần của M59 được yêu cầu trực tiếp: màn xin đồng ý (thẻ xanh dương, ô icon, "Cho hệ thống làm quen với bạn", danh sách quyền riêng tư trong ô kính, nút xanh dương), 3 bước đăng ký (thẻ xanh dương toàn khung, chữ 76 px, thanh tiến độ, khung căn khuôn mặt `FaceGuide`: oval vạch đứt + điểm mốc của canvas, mặt quay ra đường ở bước 2, mắt nhắm ở bước 3, xanh khi ổn / vàng khi có nhắc), tổng kết chuyến trong khung HUD (thẻ đánh giá theo màu chuyến, 4 ô số liệu, biểu đồ tối đa 65 cột có trục giờ, ô gợi ý, nút "Xong")
  - Khung khuôn mặt là hình hướng dẫn, không phải ảnh camera: HUD không bao giờ nhận ảnh. Không có nút "Huỷ đăng ký" của canvas: edge agent chưa có lệnh huỷ giữa chừng (xe chạy thì tự tạm dừng), backend / edge không đổi
  - e2e `live.e2e.ts` đổi theo chữ mới: "Xe đang đỗ · 0 km/h" lúc đăng ký, "Tổng kết chuyến đi · …" ở màn tổng kết
- **Sửa theo danh sách góp ý "Việc cần làm" (07/10):**
  - Nút tài xế bấm khi lái to hơn: "Đổi tài xế", "Kết thúc chuyến", "Cảnh báo này sai?" cao 72 px, chữ 20 px (`.dg-btn-lg`)
  - Thẻ trạng thái: bỏ tiêu đề "Trạng thái tài xế · Cập nhật liên tục…" và chữ "Đang giám sát" (chỉ còn chấm xanh); huy hiệu mức là vòng tròn đặc (L0 dấu tích, L1 icon lý do); câu trạng thái 96 px (câu dài 72 px); 2 ô "Lái liên tục" và "Cảnh báo gần nhất" chữ 28 px, ít chữ. Thẻ L2 cũng bỏ tiêu đề
  - Thẻ chỉ số: bỏ tiêu đề và chip "Thấp · chưa cần nghỉ"; buồn ngủ / chú ý đường / mắt nói bằng chữ có màu ("Tỉnh táo · Hơi mệt · Rất mệt", "Tập trung · Nhìn lệch · Cầm điện thoại", "Đang mở · Nhắm 1,2 giây"), số chỉ còn là thanh mảnh; biểu đồ 15 phút thu thành một dải mảnh "Độ mệt từng phút" có mốc thời gian bên dưới ("15 phút trước … Bây giờ"). Chữ theo dải `score_l1` / `score_l2` của chuyến; "mắt nhắm" dưới 0,5 s vẫn ghi "Đang mở" (chớp mắt, chỉ để hiển thị)
  - Thẻ xe: bỏ tiêu đề "Tốc độ · Tín hiệu xe đã kết nối" và chip "Đang chạy" (chỉ còn dấu tích xanh, chip chỉ hiện khi mất / chưa có tín hiệu); xi nhan lên trên cùng; ô ô tô thành chữ to "D" (đang lái) / "P" nền xanh dương (đang đỗ); bỏ D / P trong khung bát giác
  - Màn không giám sát (thiết kế "Tạm ngưng", "Mất camera", "Lỗi xử lý", "Mất kết nối"; phần còn lại của M59): thẻ vàng nâu + chip vàng đặc "KHÔNG giám sát", chữ 80 px. "Không thấy mặt" và "hư camera" không còn giống nhau: dòng đầu nói camera còn chạy hay không ("Camera vẫn chạy, nhưng không thấy mặt" / "Không nhận được hình từ camera"), ô "Camera" xanh "Vẫn hoạt động" / đỏ "Không có hình", icon khác nhau; mất camera và lỗi xử lý có "Từ HH:MM", "Lần thử N", "Đã báo" khi M65 gửi; mất kết nối là thẻ xanh dương (lỗi thiết bị, không phải tài xế)
- **Đo FPS `#/live` sau đợt sửa:** vẫn 20 FPS; cả frame p50 17,3 ms, p95 25,8 ms (trước đổi giao diện 12,6 / 23,5 ms). Tăng dần nhưng xa ngân sách 66 ms; theo dõi tiếp trên máy yếu thật
- **Giới hạn:** chưa chạy e2e `live.e2e.ts` (cần backend); chữ trên nút "Kết thúc chuyến", "Đổi tài xế", vùng "Xe" và câu L3 giữ đúng chữ e2e tìm
- Test: 9 test mới (`src/hud/m58.test.ts`), tổng 104 test frontend pass, typecheck / build sạch; 17 test M65 pass

<a id="m59"></a>

#### M59: HUD sự cố, đăng ký và kết thúc chuyến (khối 13)

**Xong là thấy gì:** mọi trạng thái của HUD hiện tại đều có màn hình mới, không trạng thái nào quay về giao diện cũ hay bị bỏ

**Trạng thái:** Xong (07/10). Xin đồng ý, 3 bước đăng ký, tổng kết chuyến, tạm ngưng, mất camera, lỗi xử lý, mất kết nối làm cùng các đợt sửa M58 (chi tiết ở M58); màn "Bạn còn ở đó không?" làm sau cùng: cả thẻ là một nút, vàng khi đang hỏi (đếm ngược "Còn N giây" từ `presence.remaining_s`), đỏ khi không ai trả lời ("đã báo cho quản lý đội xe"), chữ 92 px

- Theo bản thiết kế: mất camera, lỗi xử lý, mất kết nối thiết bị, tạm ngưng (không thấy mặt), mất tín hiệu xe, đỗ chưa có tín hiệu; xin đồng ý + 3 bước đăng ký; tổng kết chuyến
- Vẽ thêm theo phong cách mới (bản thiết kế chưa có): "Bạn còn ở đó không?" (M44), lý do tạm ngưng tối / chói / che camera / ảnh mờ (M43), không phát hiện được điện thoại (M50), đăng ký thất bại và "Để sau", xe đang đỗ, nút "Chạy mô phỏng"
- "Từ HH:MM", "Lần thử N" và "Đã báo cho quản lý" lấy từ `incident` của M65; giá trị `null` (bản web, lỗi xử lý) thì ẩn ô đó
- Test: `hudModel.test.ts`, `tripModel.test.ts`, e2e HUD pass

<a id="m60"></a>

#### M60: Đăng nhập chung và trang chủ theo vai trò (frontend)

**Xong là thấy gì:** một trang đăng nhập theo thiết kế; sau đăng nhập mỗi vai trò vào trang chủ của mình, menu trái chỉ có trang của vai trò đó; mỗi trang có địa chỉ riêng `#/dashboard/<trang>`

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/`; quyền đọc dữ liệu vẫn do backend quyết định (`require_roles`), menu chỉ ẩn những gì sẽ bị từ chối

- **Đăng nhập** (`Login.tsx`): cột trái giới thiệu + hai thẻ "Không lưu ảnh khuôn mặt", "Dữ liệu có hạn dùng" (số ngày lấy từ `/api/v1/policy`, không ghi cứng; backend không trả lời thì không nêu số); cột phải form, nút "Hiện / Ẩn" mật khẩu, lỗi "Sai tên đăng nhập hoặc mật khẩu", thẻ "Chạy thử bằng camera trên máy này" sang `#/live`, ghi chú HUD không cần đăng nhập
- **Menu theo vai trò** (`nav.ts`, hàm thuần có test): tài xế: Tổng quan · Chuyến đi của tôi · Lịch sử cảnh báo · Dữ liệu của tôi; quản lý: Tổng quan · Đội xe · Báo cáo chuyến · Nhật ký sự kiện · Timeline mệt mỏi · Ngưỡng (chỉ xem); kỹ sư: Ngưỡng và báo sai · Nhật ký sự kiện · Timeline · Đội xe · Báo cáo chuyến; quản trị: Tài khoản · Thiết bị · Nhật ký truy cập + mọi mục của kỹ sư. Trang chủ: tài xế / quản lý → Tổng quan, kỹ sư → Ngưỡng, quản trị → Tài khoản. Địa chỉ của trang vai trò không có thì về trang chủ
- **Khung** (`Dashboard.tsx`): menu trái 248 px (tên, vai trò, mã tài xế, Đăng xuất ở đáy; số báo cáo chưa xem trên mục "Báo cáo chuyến"), tiêu đề trang + một câu giải thích + bộ lọc ở đầu trang; màn hẹp thì menu nằm ngang trên cùng. Dòng chính sách dữ liệu dưới mọi trang giữ nguyên
- **Tạm thời:** "Tổng quan" tài xế dùng danh sách chuyến, "Tổng quan" quản lý dùng trang Đội xe, "Tài khoản / Thiết bị" chỉ có hướng dẫn `backend.manage` + duyệt yêu cầu xoá, tới M61 / M62 / M63
- e2e `live.e2e.ts`: mục menu là link ("Đội xe", "Báo cáo chuyến") thay vì tab
- Test: 3 test mới (`dashboard/nav.test.ts`), tổng 109 test frontend pass, typecheck / build sạch; xem bằng backend tạm với database riêng và 2 chuyến giả lập (quản lý, kỹ sư, quản trị, tài xế đăng nhập được, không lỗi trang)

<a id="m61"></a>

#### M61: Trang tài xế (frontend)

**Xong là thấy gì:** tài xế đăng nhập vào "Tổng quan" của mình: chuyến gần nhất, 30 ngày qua, gợi ý, các chuyến gần đây; "Chuyến đi của tôi" có danh sách và trang chi tiết từng chuyến (`#/dashboard/trips/<xe>/<chuyến>`)

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/`; backend vẫn chỉ trả cho tài xế dữ liệu của chính họ

- **Tổng quan** (thiết kế "Tài xế · Tổng quan"): câu "Không ai thấy hình ảnh khuôn mặt của bạn"; thẻ chuyến gần nhất theo màu đánh giá (câu chuyện chuyến, biểu đồ độ mệt cả chuyến, "quản lý đã xem lúc …" hoặc "Quản lý chưa xem", nút "Xem chi tiết chuyến"); 30 ngày qua: số chuyến, giờ lái, lần được nhắc, lần báo sai; gợi ý của chuyến gần nhất; bảng các chuyến gần đây
- **Chi tiết chuyến** (thiết kế "Tài xế · Chi tiết chuyến"): thẻ đánh giá; 6 ô số liệu (thời gian lái, lái liên tục dài nhất, lần nghỉ, tốc độ trung bình, lần ngáp, thời gian được giám sát); biểu đồ độ mệt có trục giờ và chú thích; "Các lần được nhắc" (giờ, lý do, mức, "bạn đã báo sai") từ `/api/v1/timeline`; gợi ý + lúc gửi cho quản lý và ai đã xem
- **Dùng chung với M62** (`TripParts.tsx`): thẻ đánh giá, biểu đồ chuyến, ô số liệu, chip đánh giá; `driverModel.ts` (hàm thuần có test): tổng 30 ngày, sắp xếp mới nhất trước, link chuyến
- "Lịch sử cảnh báo" và "Dữ liệu của tôi" giữ bảng / thẻ hiện có (M41, M48) trong khung mới
- Test: 3 test mới (`dashboard/driverModel.test.ts`), tổng 112 test frontend pass, typecheck / build sạch; xem bằng tài khoản tài xế trên backend tạm, không lỗi trang

<a id="m62"></a>

#### M62: Trang quản lý (frontend)

**Xong là thấy gì:** quản lý đăng nhập vào "Tổng quan đội xe" (số liệu hôm nay, "Cần xử lý", từng xe); "Báo cáo chuyến" là trang duyệt: danh sách bên trái, một báo cáo bên phải, nút "Đánh dấu đã xem"

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/`; cùng các API `/api/v1/fleet`, `/api/v1/trip-reports`, `…/review`

- **Tổng quan** (thiết kế "Quản lý · Tổng quan đội xe"): xe đang hoạt động / tổng, mất liên lạc, cảnh báo hôm nay (L1 · L2 · L3), báo cáo chuyến chưa xem; "Cần xử lý": cần chú ý ngay (L3, không phản ứng, không trả lời: M44, đỏ, có tiếng chuông mỗi sự kiện mới như trang Đội xe), mất liên lạc chưa kết thúc chuyến (vàng), báo cáo mới và số chuyến "Có lúc rất nguy hiểm" (xanh dương), mỗi mục có nút dẫn tới trang xử lý; bảng từng xe có lọc trạng thái và ô tìm xe / tài xế. Làm mới mỗi 5 s như trang Đội xe
- **Duyệt báo cáo** (thiết kế "Quản lý · Duyệt báo cáo chuyến"): lọc "Chưa xem (N)" / "Tất cả"; báo cáo: thẻ đánh giá, 8 ô (thời gian lái, lái liên tục dài nhất, L1 / L2 / L3, nhắm mắt lâu nhất, ngáp / gục đầu, nhìn lệch / điện thoại, được giám sát, tài xế báo sai), biểu đồ độ mệt + "Xem timeline từng phút", gợi ý đã đưa cho tài xế, "Đánh dấu đã xem" (sau đó ghi ai đã xem lúc nào), câu "Cảnh báo có thể sai: không dùng một cảnh báo đơn lẻ để kỷ luật tài xế"
- Kỹ sư và quản trị giữ bản báo cáo kỹ thuật đầy đủ số (`TripReports`); "Nhật ký sự kiện", "Timeline mệt mỏi", "Đội xe" (phiên bản, tốc độ xử lý: M41, M49) giữ bảng hiện có trong khung mới
- Test: 112 test frontend pass, typecheck / build sạch; xem bằng tài khoản quản lý trên backend tạm (2 xe, 2 báo cáo), không lỗi trang

<a id="m63"></a>

#### M63: Trang kỹ sư và admin (frontend)

**Xong là thấy gì:** kỹ sư sửa ngưỡng với thanh "N thay đổi chưa lưu · Hoàn tác · Lưu thành phiên bản N+1" và xem tỉ lệ báo sai theo lý do dạng thanh; quản trị tạo tài khoản / thiết bị ngay trên web, khoá thiết bị hiện đúng một lần có nút sao chép

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/`: gọi các API admin đã có (`GET / POST /api/v1/users`, `POST /api/v1/devices`); danh sách thiết bị lấy từ `/api/v1/fleet` (trả mọi thiết bị, kể cả chưa từng kết nối), không cần API mới

- **Ngưỡng và báo sai** (thiết kế "Kỹ sư · Ngưỡng và báo sai"): giữ nguyên logic M47 (áp thử cho vài xe, phiên bản, "Áp cho cả đội" / quay lui) và đủ 16 khoá; thêm thanh thay đổi chưa lưu luôn nằm trên (ghi tên các ngưỡng đã sửa), ô đã sửa viền xanh + "Đã sửa · trước đó …", nhóm ngưỡng thành thẻ bo tròn, khoá cấu hình bằng JetBrains Mono (tự đóng gói `@fontsource/jetbrains-mono`, như Design System); "Cảnh báo sai theo lý do" thành thanh ngang, từ 20 % trở lên tô cam sáng (bản thiết kế dùng cam tối `#C2410C` trên nền tối, không đọc được)
- **Tài khoản** (thiết kế "Quản trị · Tài khoản và thiết bị"): danh sách có lọc vai trò, chip màu theo vai trò, mã tài xế; form thêm tài khoản (tên, mật khẩu ban đầu ≥ 8 ký tự, 4 ô chọn vai trò, mã tài xế bắt buộc với tài xế), báo lỗi trùng tên / không hợp lệ bằng câu dễ hiểu
- **Thiết bị:** danh sách thiết bị + tài xế + liên lạc; form thêm thiết bị; thẻ vàng "Thiết bị … vừa được tạo" với khoá và nút "Sao chép" (khoá chỉ giữ trong bộ nhớ trang, không lưu); dòng "Khoá thiết bị không bao giờ hiện lại"
- Nhật ký truy cập + duyệt yêu cầu xoá (M41, M48) ở mục "Nhật ký truy cập" của quản trị
- Test: 112 test frontend pass, typecheck / build sạch; thao tác thật trên backend tạm (tạo tài khoản, tạo thiết bị, sửa ngưỡng), không lỗi trang, không tràn ngang ở 1440 / 390 px

<a id="m64"></a>

#### M64: `#/live` và `#/drive` (frontend)

**Xong là thấy gì:** `#/live` từ lúc mở tới lúc kết thúc chuyến dùng giao diện mới: thiết lập, đang tải, HUD (M58 / M59), tổng kết; `#/drive` cùng phong cách

**Trạng thái:** Xong (07/10). Chỉ đổi `frontend/`

- **Thiết lập** (thiết kế "Chạy thử trên trình duyệt · Thiết lập"): cột trái giới thiệu + thẻ xanh "Hình ảnh không rời khỏi máy bạn"; cột phải 3 bước đánh số: "Ai đang lái?" (đăng nhập / "Dùng thử không lưu"), "Đăng ký khuôn mặt · khoảng 10 giây" (3 bước), "Bắt đầu" (nút xanh dương "Cho phép camera và bắt đầu")
- **Đang tải** (thiết kế "… · Đang tải"): "Đang khởi động", các bước "Mở camera · Xong", "Đang chuẩn bị N%" có thanh tiến độ, "Sẵn sàng giám sát". Dung lượng tải ghi theo số đo thật (≈ 30 MB, M45), không ghi 60 MB như bản thiết kế. Bản thiết kế chia bước chuẩn bị thành 3 mục con (môi trường, model mặt, model điện thoại): agent chỉ báo tỉ lệ chung, nên không vẽ mục con
- **Khung camera nhỏ** khi đang chạy: nhỏ lại (176 px), nền tối, "Chỉ xem, không lưu", ba nút icon có nhãn (trang điều khiển xe theo mã, "Chi tiết kỹ thuật", "Dừng camera"), để không che nút của HUD
- **`#/drive`**: thẻ kính, nút ô kính, chip mã ghép, nút "Ghép" xanh dương; cùng nút, cùng phím tắt, cùng chữ
- Chữ mà e2e và `frontend/bench/live.bench.mjs` tìm giữ nguyên ("Dùng thử không lưu", "Cho phép camera và bắt đầu", "Đăng nhập: …", "Chi tiết kỹ thuật", link "Điều khiển xe · mã …", khung `fixed bottom-4`)
- **Đo FPS `#/live`** (Chromium không GPU, camera giả 30 s): 21 FPS; cả frame p50 16,5 ms, p95 29,7 ms
- Test: 112 test frontend pass, typecheck / build sạch; chụp thiết lập, đang tải, đang chạy, `#/drive`, không lỗi trang
- **Sửa sau khi dùng thử (07/10):** giọng đọc tiếng Việt bị đọc bằng giọng Anh: chỉ khai báo `lang = "vi-VN"` thì trình duyệt không có giọng Việt sẽ dùng giọng mặc định (máy thử chỉ có 3 giọng `en-US`). Nay `chime.ts` chọn đúng một giọng `vi` (ưu tiên `vi-VN`, giọng trên máy trước giọng qua mạng; hàm thuần `pickVietnameseVoice` có test); không có giọng Việt thì không đọc (chỉ chữ + tiếng bíp) và màn thiết lập `#/live` cùng màn đăng ký ghi cách cài giọng Tiếng Việt trong Windows hoặc dùng Microsoft Edge. Khung căn mặt khi đăng ký trong `#/live` hiện hình camera thật của trang (lật như gương, ngoài oval tối đi), chỉ hiển thị trong bộ nhớ, không lưu, không gửi; HUD trên thiết bị vẫn là hình minh hoạ (edge agent không đưa ảnh ra màn hình) và nay ghi rõ "Hình minh hoạ · màn hình không nhận ảnh camera"
- **Giọng nói tiếng Việt cho mọi cảnh báo (07/10):** máy thử không có giọng đọc tiếng Việt nào (Chrome và Edge chỉ có 3 giọng `en-US`), và thiết bị trong xe có thể không có mạng. Nên mọi câu nói được thu sẵn thành file: `frontend/src/hud/voice-lines.json` (31 câu: 9 cảnh báo theo lý do chính, 8 thông báo hệ thống, hướng dẫn đăng ký) → `python tools/make_voice.py` (Piper, chạy offline, giọng pretrained `vi_VN-vais1000-medium`, không train gì) → `frontend/public/voice/<key>.wav` (≈ 2 MB) + `manifest.json` (hash của từng câu). HUD nói câu của cảnh báo 0,7 s sau tiếng chuông (L3 nói lại theo nhịp còi), và nói khi mất / có lại camera, tạm ngưng / giám sát lại, mất kết nối, mất / có lại tín hiệu xe, "Bạn còn ở đó không?", các bước đăng ký. Thiếu file thì dùng giọng tiếng Việt của máy nếu có, không bao giờ dùng giọng Anh. Test (`hud/voice.test.ts`): mỗi lý do cảnh báo có câu, câu đăng ký đọc đúng chữ trên màn hình, đổi chữ mà chưa thu lại thì đỏ. Kiểm trên Chrome thật: chế độ mô phỏng tải và phát `alert.drowsy_score.wav`, `alert.off_road.wav`. Nguồn giọng: Piper voices "vais1000", dữ liệu VAIS-1000 Vietnamese speech synthesis corpus (https://ieee-dataport.org/documents/vais-1000-vietnamese-speech-synthesis-corpus), giấy phép CC BY 4.0
- **e2e** (`npx playwright test`, backend + database bỏ đi riêng): 4 / 4 pass sau khi đổi 2 chỗ theo giao diện mới: mã ghép đọc từ nhãn của link (link giờ chỉ hiện mã), quản lý duyệt báo cáo ở trang mới (chọn báo cáo trong danh sách, thấy "đổi tài 1 lần" trong câu chuyện chuyến, bấm "Đánh dấu đã xem")

<a id="m65"></a>

#### M65: Dữ liệu HUD từ edge agent (khối 1, 11, 13, 14)

**Xong là thấy gì:** `GET /state` của server HUD (và trạng thái của `#/live`) có thêm `trip`, `incident` và `alerts[].metrics`; tải lại trang HUD thì số vẫn đúng ngay, vì edge agent giữ chúng suốt chuyến

**Trạng thái:** Xong (07/10). Chỉ đọc ra những gì edge agent đã giữ: không đổi logic cảnh báo, không đổi backend / API, bản tổng kết chuyến không đổi. Chưa có giao diện (M58 / M59)

- **Vì sao ở edge agent, không ở backend:** HUD trong xe đọc server HUD của thiết bị mỗi 0,3 s và phải chạy khi mất mạng; nó không đọc backend. Edge agent giữ dữ liệu chuyến trong bộ nhớ suốt chuyến, nên HUD tải lại chỉ cần đọc lại
- **`trip`** (khối 11, `TripCollector.hud_view`): `drive_run_s` lái liên tục của tài xế hiện tại (về 0 sau một lần nghỉ `context.rest_after_s` hoặc "Đổi tài xế"), `driving_s` cả chuyến, `score_l1` / `score_l2` (dải màu của biểu đồ, lấy từ ngưỡng), `recent_minutes` điểm buồn ngủ trung bình của `hud.trend_minutes` = 15 phút gần nhất (phút đang chạy ở cuối; phút không có frame được chấm như lúc nghỉ hay bước nhắm mắt khi đăng ký là `null`, vẽ thành khoảng trống, không phải 0)
- **"Đổi tài xế"** chỉ đưa `drive_run_s` về 0; `longest_drive_s`, `rests`, các phút của bản tổng kết giữ nguyên (`TripCollector.driver_changed`)
- **`alerts[].metrics`** (`runtime.alert_detail`): `off_road_s`, `eyes_closed_s`, `phone_ratio`, `turn_signal` (theo khối 10, có thời gian ân hạn) lúc cảnh báo bật
- **`incident`**: `kind` (`camera_lost` / `processing_error`), `since`, `event_id` của sự kiện hệ thống đã gửi; `attempts` = số lần thử mở lại camera (`FrameSource.reopen_attempts`, khối 1, về 0 khi có frame lại); `reported` = backend đã nhận sự kiện (`MetadataPublisher.delivered`, khối 14, nhớ 64 `event_id` gần nhất). Bản web và thiết bị chạy không có `--backend`: `reported` là `null`, HUD ẩn dòng "Đã báo cho quản lý" thay vì đoán
- Ngưỡng mới: `hud.trend_minutes: 15` trong `config/thresholds.yaml`
- **Chi phí:** `hud_view(15)` 7,9 µs mỗi frame trên máy dev (một frame ở 15 FPS có 66 ms)
- **Giới hạn:** edge agent khởi động lại giữa chuyến thì mất chuyến như trước đây (không ghi ra đĩa, đúng ràng buộc); "lỗi xử lý" không có số lần thử (mỗi frame là một lần thử), chỉ có `since`
- Test: 17 test mới bằng chuỗi số giả (`tests/test_edge_agent/test_m65_hud_trip.py`); tổng 968 Python pass, 1 lỗi có sẵn trên Windows (`test_a_failing_frame_names_the_error_and_its_code_location` so đường dẫn kiểu `/`); test hồi quy trace không đổi; `ruff` sạch ở `edge_agent/`, `tools/`, `tests/`; frontend typecheck sạch, 95 test pass (kiểu `HudTrip`, `HudIncident` trong `lib/types.ts`)

<a id="m67"></a>

#### M67: Tốc độ vòng lặp `#/live` trên trình duyệt máy tính (khối 4, khởi động, công cụ đo)

**Xong là thấy gì:** [`eval/results/benchmark_live.md`](../eval/results/benchmark_live.md) mục 4–5 có bảng trước / sau trên cùng máy, cùng cách đo; "Chi tiết kỹ thuật" của `#/live` ghi model điện thoại chạy trên "WebGPU" hay bao nhiêu luồng, và thời gian khởi động từng phần; [`eval/results/phone_web_3mdad.md`](../eval/results/phone_web_3mdad.md) có số cảnh báo `phone` đúng / sai theo từng lịch chạy YOLO

**Trạng thái:** Xong phần code (08/10); **cổng chạy dài 10 phút chưa sạch** (xem mục "Chạy dài" bên dưới). Phạm vi là bản web trong trình duyệt máy tính; không làm gì cho Android / hub. Mọi số là Chromium 153 không giao diện trên một máy Mac (Apple M5, 4 nhân nhanh + 6 nhân tiết kiệm, 16 GB), camera giả của Chrome phát một clip YawDD; chưa đo với camera thật, trình duyệt có giao diện, hay máy khác. Bản thiết bị (`edge_agent.main`) không đổi hành vi

- **Đo lại trước khi sửa:** các số trong đề bài ("MediaPipe p95 44 ms, bỏ 24 % frame, khởi động 11 s") là của M50, trước khi M51 sửa delegate. Trên máy này bản hiện tại đã chạy 29,6–29,9 FPS so với camera 30, mỗi frame bận 11–14 ms trên 33 ms, model mặt p95 gấp 1,1–1,3 lần p50, khởi động 2,4–3,6 s (cache trống) và 1,4 s (cache ấm). Hai thứ còn xa mục tiêu: tuổi kết quả YOLO khi dùng (p95 329–333 ms) và chuỗi tải tuần tự lúc khởi động
- **Điểm nghẽn thật của tuổi kết quả YOLO là chu kỳ chạy, không chỉ model.** Một frame dùng kết quả mới nhất, nên tuổi của nó chạy từ "một lần suy luận" tới "một lần suy luận + một chu kỳ + một frame". Với 91 ms mỗi lần và chu kỳ 200–233 ms, chu kỳ chiếm phần lớn
- **Nhịp chạy YOLO** (`frontend/src/live/pace.ts`, `YoloPacer`): luật cũ "ít nhất 200 ms từ lần trước" hay lấy frame thứ 7 thay vì thứ 6 (frame camera cách nhau 33 ms, có rung), nên chỉ chạy 4,5 lần / giây cho mục tiêu 5. Nay lấy frame gần thời điểm tới hạn nhất, không bao giờ khi model còn bận, không chạy dồn sau khi bị treo. Ảnh cũng được đưa cho worker **trước** khi MediaPipe chạy thay vì sau, để hai model chạy cùng lúc. Đúng 5,0 lần / giây; tuổi p50 232 → 197 ms, p95 333 → 267 ms
- **YOLO trên WebGPU** (`yolo.worker.ts`, `gpu.ts`): worker hỏi `navigator.gpu`; có adapter thật và `phone.web_gpu` cho phép thì chạy cùng file `yolov8n.onnx` bằng WebGPU, không thì wasm với `phone.num_threads` như cũ. Adapter phần mềm bị loại như với model mặt (M51). Runtime của bên được chọn mới được tải (worker build thành ES module), nên máy không có GPU không tải thêm gì. Phiên WebGPU hỏng giữa chừng thì worker tự dựng phiên wasm và trang đổi nhịp theo. Trong trang: 94 → 17 ms mỗi lần; CPU của tiến trình trang 109 → 32 % một nhân, tiến trình GPU 15 → 23 %
- **Hai khoá mới trong `config/thresholds.yaml`:** `phone.web_gpu` (true) và `phone.web_gpu_target_fps` (10, số lần / giây khi chạy WebGPU). Trên wasm trang giữ `phone.target_fps` (5). `PhoneDetectorConfig` và `WebAgent.settings()` có thêm hai khoá; bản thiết bị không đọc chúng
- **Kết quả, 5 lần 60 giây mỗi bản, chạy xen kẽ (trung vị):**

| | Không GPU (WebGL phần mềm): trước → sau | GPU thật: trước → sau |
|---|---:|---:|
| Frame xử lý mỗi giây (camera 30,0) | 29,87 → 29,65 | 29,55 → 29,69 |
| Frame camera không được xử lý | 0,44 % (0,06–2,11) → 1,00 % (0,06–4,00) | 1,00 % (0,00–2,17) → 0,94 % (0,78–4,11) |
| Cả frame p50 / p95 | 10,7 / 13,6 → 11,0 / 13,4 ms | 14,3 / 19,3 → 12,3 / 17,7 ms |
| Model mặt p50 / p95 | 9,0 / 10,3 → 9,3 / 10,1 ms | 10,6 / 14,2 → 8,6 / 11,8 ms |
| YOLO mỗi lần p50 | 90,7 → 94,4 ms | 94,5 → 17,0 ms |
| YOLO số lần mỗi giây | 4,55 → 5,00 | 4,55 → 10,00 |
| Tuổi kết quả YOLO khi dùng p50 / p95 | 230 / 329 → 199 / 274 ms | 233 / 333 → 67 / 131 ms |
| CPU của trang (% một nhân) | 125 → 137 | 109 → 32 |
| Tới frame đầu tiên, cache trống | 2,66 → 2,08 s | 2,62 → 2,21 s |
| Tới frame đầu tiên, cache ấm | 1,36 → 1,29 s | 1,44 → 1,40 s |

- **Khởi động** (`LiveAgent.start`, `loadPython`): gói của Pyodide (numpy 3 MB) trước đây chỉ tải sau khi runtime khởi động xong, nay tải song song (`loadPyodide({ packages })`), cùng lúc với gói code và ngưỡng từ backend; vòng lặp chạy ngay khi Python và model mặt sẵn sàng, model điện thoại gắn vào khi phiên của nó xong (0,05–0,13 s sau frame đầu). Cache ấm chỉ nhanh hơn 0,04–0,06 s: phần còn lại là Python khởi động trên luồng chính (runtime khoảng 0,46 s, import numpy và agent khoảng 0,40 s)
- **Công cụ đo** (`frontend/src/live/perf.ts`, `frontend/bench/live.bench.mjs`): trang đếm từ lúc vòng lặp bắt đầu (frame đã xử lý, frame camera không được xử lý, số lần YOLO chạy) và ghi thời gian khởi động từng phần; công cụ lấy mẫu mỗi 10 giây kèm bộ nhớ và CPU của các tiến trình trình duyệt, cho FPS từng phút, và từ 2 phút trở lên thì kết luận theo `eval.soak_min_fps` và `eval.soak_rss_growth_mb_per_h` như `tools/benchmark.py --duration`. Thêm `--duration`, `--profile` (cache ấm), `--think-s`, `--yolo`, `--json`. Chỉ là số mili giây và số đếm
- **Chạy dài 10 phút:** bản cũ đạt ở cả hai cấu hình (29,88 và 29,59 FPS, phút thấp nhất 29,2 và 28,4). **Bản mới: hai lần chạy đầu FAIL, hai lần chạy lại đạt.** Ở hai lần đầu vòng lặp ngừng nhận frame (một lần ngừng rồi tự chạy lại hai lần, lần kia ngừng từ giây 145 tới hết); lúc ngừng tiến trình của trang chỉ dùng 3–4 % một nhân, không lỗi, không crash. Hai lần chạy lại: 29,70 và 29,68 FPS, phút thấp nhất 28,7 và 29,2. Chạy cả hai bản ở cả hai cấu hình cùng lúc 15 phút, có ghi sự kiện của camera, thẻ video và trạng thái hiển thị: không lần ngừng nào. **Nguyên nhân chưa xác định.** Nghiêng về phía máy (trình duyệt ngừng trình chiếu frame video: `requestVideoFrameCallback` không được gọi khi luồng chính rảnh, code của trang không chạy ở giữa; người dùng rời máy khoảng 01:02 và màn hình đã khoá), nhưng nó xảy ra 2 / 2 lần đầu ở bản mới và 0 / 2 ở bản cũ, và không tái hiện được có chủ ý (tắt màn hình 40 giây không làm bản nào ngừng). Bộ nhớ: mọi độ dốc đều âm (hệ điều hành thu hồi), đạt tiêu chí nhưng 10 phút không nói được gì về rò rỉ chậm
- **Cổng chất lượng:**
  - WebGPU so với wasm trên 200 frame 3MDAD (68 frame có điện thoại ≥ 0,35, 39 frame có điểm cao nhất trong 0,25–0,45): điểm lớp điện thoại lệch tối đa 4,7e-6, toạ độ hộp tối đa 7,3e-4 px, không quyết định nào ở ngưỡng 0,35 đổi (0 / 356 hộp)
  - Nhánh điện thoại trên 3MDAD (`tools/phone_study.py`, 50 tài xế, 1,03 giờ, mỗi lịch chạy từ 6 frame bắt đầu khác nhau): chuỗi có điện thoại ra cảnh báo `phone` 134 / 1200 (lịch cũ) → 131 / 1200 (wasm mới) và 130 / 1200 (WebGPU); cảnh báo `phone` sai 0 → 1 và 2 lần trên 6 lượt (0,2 và 0,5 / giờ, CI 95 % 0,0–1,3 và 0,1–1,7), đều ở một tài xế đang uống nước. Lịch đơn giản "mỗi k frame" cho thấy đó là may rủi của việc frame nào được lấy: cùng lần báo sai đó xuất hiện ở 1 / 3, 1 / 6 và 3 / 7 cách lệch pha của 10, 5 và 4,3 lần / giây, và số chuỗi được báo dao động 18–25 / 200. Kết luận: không thấy lịch mới làm đổi recall hay báo sai ngoài mức dao động đó; dữ liệu này không đủ để loại trừ một thay đổi nhỏ. Từ đầu chuỗi tới cảnh báo: trung vị 2,47 s (cũ), 2,47 s (wasm mới), 2,33 s (WebGPU)
  - Bản thiết bị: báo cáo replay của FL3D, YawDD, SUST (`tools/seq_eval.py --replay block5`) và của bản tự ghi (`tools/record_trace.py report`) giống hệt từng byte trước và sau; test hồi quy trace (M34) không đổi. `tools/eval.py` không chạy lại: nó chạy đúng các đoạn code không đổi đó
- **Đã thử, không giữ (có số):**
  - wasm chạy 10 lần / giây: tuổi p95 230–233 ms thay cho 267, nhưng CPU của trang 211–216 % một nhân thay cho 136 %, đúng trên loại máy không có GPU. Vì vậy mục tiêu "tuổi p95 < 250 ms" chưa đạt khi không có GPU (274 ms)
  - Mở sẵn kết nối tới CDN khi vào `#/live`: 2,03 s so với 2,08 s, không tách được khỏi dao động của mạng; đã gỡ
  - Ảnh đầu vào nhỏ hơn (xuất lại cùng trọng số pretrained, không train): wasm 2 luồng 88 → 51 / 38 / 24 ms ở 480 / 416 / 320. Trên 3MDAD, 480 và 416 giữ số cảnh báo (130 và 132 / 1200, không báo sai) nhưng thấy điện thoại lúc gọi ít hơn (frame có điện thoại khi gọi tay phải 7,5 % → 6,8 % / 6,0 %); 320 mất một phần ba (87 / 1200). Không đổi mặc định: là quyết định của anh, và 3MDAD là đoạn diễn 3–5 giây
  - Thêm luồng wasm: 3 / 4 luồng cho 61 / 50 ms, 6 luồng 67 ms. Không đổi `phone.num_threads` (dùng chung với thiết bị, chưa đo máy 4 nhân)
- **Đo rồi thấy không phải chỗ để sửa:** frame camera bị bỏ (0–4 %, dao động giữa các lần chạy của cùng một bản; 20 / 21 lần luồng chính đang rảnh 35–40 ms, do `requestVideoFrameCallback` đi theo nhịp vẽ màn hình); hàm nhận kết quả YOLO trên luồng chính 0,2 ms; các timer dưới 0,5 ms; không có tác vụ dài nào sau frame đầu; đọc lại pixel 0,5–1,9 ms; chuẩn bị ảnh cho YOLO 1,5–2,1 ms mỗi lần. Chuyển vòng lặp sang Worker, bỏ bước đọc lại canvas, dùng lại buffer: không làm vì không có gì đo được để lấy lại
- **Không thử:** FP16 (WebGPU FP32 đã 17 ms); INT8 (file hiện có không phát hiện được gì, M54); đổi `preprocess.target_width` (camera đã là 640, và đổi sẽ làm lệch các số đo chất lượng ảnh)
- **Chưa làm / giới hạn:** một máy, Chromium không giao diện, camera giả; WebGPU mới thử trên Metal của Apple, chưa thử Windows / Linux hay GPU yếu (một GPU thật nhưng chậm vẫn được chọn); đường lùi về wasm mới được thử bằng một bản build cố ý làm lỗi, chưa gặp mất thiết bị thật; bản build nặng thêm một runtime (26,8 MB, nén 6,7 MB) chỉ máy có GPU mới tải; trên mạng rất chậm chip "Không phát hiện được điện thoại" có thể hiện vài giây đầu vì vòng lặp nay chạy trước khi model điện thoại tải xong; `perf.yolo_provider` cần backend mới (backend cũ từ chối trường lạ). Đề xuất mốc sau ở [improvements.md](improvements.md) việc 13, 14
- Test: 965 Python (10 test mới của `tools/phone_study.py`, 1 bridge, 1 `perf_record`, 1 backend) + 115 frontend (20 test mới: nhịp YOLO, chọn nơi chạy, số đếm cả lần chạy, phép tính của chạy dài, nhãn) + 4 e2e pass; ruff, typecheck, build sạch; test hồi quy trace không đổi. Sau khi gộp `main` (M57–M65 của Version 4): 982 Python + 138 frontend + 4 e2e pass, và một lượt đo 60 giây mỗi cấu hình cho cùng kết quả (wasm: 5,0 lần / giây, tuổi p95 268 ms; WebGPU: 16,7 ms mỗi lần, tuổi p95 133 ms). Các bảng số ở trên đo trên nền code trước khi gộp

<a id="m68"></a>

#### M68: Đăng ký xong thì điểm buồn ngủ bắt đầu từ 0 (khối 7, 9, 11)

**Xong là thấy gì:** đăng ký khuôn mặt khi xe đỗ, `drowsy_score` trên HUD là 0 suốt bước nhắm mắt và sau khi đăng ký xong, kể cả khi tài xế đã nhắm mắt hay ngáp trước đó trong lúc đỗ

**Trạng thái:** Xong (08/10). Chỉ đổi `edge_agent/decision/pipeline.py`, `risk_engine.py`, `analysis/drowsiness/eyes.py`; không thêm ngưỡng

- **Trước:** bước nhắm mắt (2 s) và 2 s chờ mở mắt đã không sinh cảnh báo, không vào trip memory / bảng tổng kết, và phần khối 7 gom trong lúc đó bị bỏ. Nhưng `drowsy_score` vẫn được tính trong 4 s đó (mô phỏng: lên 25), và những gì gom **trước** bước nhắm mắt vẫn ở lại: nhắm mắt 1,5 s lúc đang đỗ trước khi đăng ký để lại PERCLOS 0,09 và 25 điểm (số hạng microsleep, nhớ 5 phút)
- **Điểm đọc 0 khi đang tắt đánh giá** (khối 9, `drowsy_muted`): `drowsy_score` và sáu số hạng của nó là 0 trong bước nhắm mắt và thời gian chờ
- **Đăng ký xong, hết thời gian chờ** (`_track_enrollment`): khối 7 bỏ toàn bộ cửa sổ (PERCLOS, chớp, ngáp, gục đầu, chớp chậm, nhướn mày, mẫu baseline), vì chúng đo trên mốc tự học, từ đây dùng mốc của tài xế; trip memory bỏ phần gom từ lúc xe dừng lần này (`forget_since`). Bước bị làm lại hoặc bị huỷ thì như cũ: chỉ bỏ phần của bước đó
- **Cố ý giữ:** trip memory của lúc **đang lái** trước lần dừng. Đăng ký muộn (đã lái, có microsleep thật, rồi mới dừng và đăng ký): điểm vẫn 25 trong 5 phút nhớ microsleep (mô phỏng: microsleep ở giây 5–8 khi chạy 60 km/h, dừng ở giây 22, đăng ký xong: điểm 25). Xoá cả phần này là xoá bằng chứng buồn ngủ thật; cần anh quyết định nếu muốn về 0 cả ở đây
- **Không đổi:** số đo thô của khối 7 trong 4 s đó (PERCLOS trên "Chi tiết kỹ thuật" vẫn lên ~0,26 rồi về 0), bảng tổng kết chuyến, khối 8 (điểm mất tập trung vốn là 0 khi xe đứng yên)
- `Perclos.forget_since`: khi không còn mẫu nào thì đặt lại hai tổng chạy về đúng 0 (trước đó còn sai số làm tròn cỡ 1e-15)
- Test: 2 test mới bằng chuỗi số giả (`tests/test_edge_agent/test_enrollment.py`), cả hai đỏ trước khi sửa; tổng 984 Python pass, ruff / format sạch, test hồi quy trace không đổi. Frontend không đổi, không chạy lại

<a id="m69"></a>

#### M69: Đọc số UTA-RLDD thêm ba cách (công cụ eval)

**Xong là thấy gì:** báo cáo UTA-RLDD có thêm khoảng tin cậy báo sai / giờ lấy mẫu lại theo người, một dòng tiêu đề ở điểm làm việc cố định (kèm đường đánh đổi), bảng điểm → phút của video `0` / `5` / `10`; mỗi bảng của `report.md` và của các `dataset_*.md` ghi đơn vị tính và tỉ lệ mẫu dương

**Trạng thái:** Xong (08/10). Chỉ đổi công cụ eval và số liệu; không đổi ngưỡng nào của hệ thống, không đổi edge_agent. Gồm ba việc của nhóm cũ "đo lại trên trace sẵn có" (nay đã xoá khỏi `docs/improvements.md`)

- **Lấy mẫu lại theo người** (`tools/metrics.py`: `person_rate_ci`, `person_spread`, `person_text`): rút lại người có hoàn lại, mỗi lần tính tổng lần sai / tổng giờ, lấy phân vị 2,5–97,5. Số lần rút và hạt giống ở `eval.bootstrap_resamples` (10 000) và `eval.bootstrap_seed` (0). In cạnh khoảng Poisson ở mục 2 của `tools/uta_rldd.py report` và ở mục "Per person" của `tools/eval.py` (khi nhãn có cột `subject`); `compare` / `grid` có thêm hai cột cận trên
- **Kết quả, 24 người giữ riêng (4,08 giờ):** 4 lần báo sai = 0,98 / giờ; Poisson 0,27–2,51, theo người 0,00–3,02; cả 4 lần là của **một** người trong 24 (F4_S44, video `0` quay 12 FPS). Dev: 5 lần, 3 / 24 người, Poisson 0,42–3,0, theo người 0,00–2,8. Không giúp kết luận chỉ tiêu PRD (cận trên vẫn trên 1,0); giá trị là biết báo sai dồn vào ít người
- **Giới hạn:** không có lần sai nào thì khoảng theo người là 0–0, phải dùng cận trên Poisson (có chú thích trong báo cáo). FL3D không có mã người trong nhãn và bản tự ghi chỉ một người, nên hai bộ này không lấy mẫu theo người được; YawDD và 3MDAD có mã người nhưng không thuộc phạm vi này
- **Một điểm làm việc cố định** (`python tools/uta_rldd.py tradeoff`, `eval.tradeoff_l1`): quét `risk.drowsy.l1` 30–60 chỉ trên dev, đọc đúng một điểm (ngưỡng hiện tại) trên test. Test: 0,98 báo sai / giờ, 15 / 24 video `10` có cảnh báo, 12 / 24 đạt L3. Dev: `l1` ≥ 50 mới xuống dưới 1,0 / giờ (0,5), mất 2 người chỉ có cảnh báo L1 (14 → 12); số người đạt L3 là 12 / 24 ở mọi `l1`. Không đổi `l1` (M53 để ngỏ 40 → 50: quyết định riêng)
- **Đơn vị và tỉ lệ dương ở mỗi bảng:** các bộ sinh báo cáo (`tools/dataset.py`, `tools/eval.py`, `tools/metrics.py window_table`, `tools/uta_rldd.py`) tự in dòng "Unit"; `window_table` thêm cột "Positive share". Dòng tương ứng được thêm tay vào `eval/results/report.md` (9 chỗ) vì file đó viết tay; các `dataset_*.md` của ảnh đơn không chạy lại, dòng mới sẽ có ở lần chạy sau
- **`drowsy_score` ứng với gì** (`tools/uta_rldd.py report`, mục 4b, `eval.score_band_width` 20): đếm phút nguyên (sau 30 s khởi động) của video `0` / `5` / `10` theo khoảng điểm. Tỉ lệ phút của `10` tăng đơn điệu theo điểm ở cả dev và test; chỗ gãy rõ nhất là giữa khoảng 0–20 và 20–40 (phút `0` gần như biến mất), mốc L1 = 40 nằm trên chỗ đó một khoảng. Tỉ lệ tuyệt đối không mang ra đường được (nhãn theo cả video, ba mức bằng số video)
- Kết quả: [`eval/results/dataset_uta_rldd.md`](../eval/results/dataset_uta_rldd.md) mục 8, [`eval/results/uta_rldd_tradeoff.md`](../eval/results/uta_rldd_tradeoff.md); `docs/pilot-readiness.md` A1 thêm khoảng theo người
- Test: 993 Python pass (tổng toàn bộ; 9 test mới bằng chuỗi số giả: lấy mẫu lại theo người rộng hơn Poisson khi lỗi dồn vào một người và gần nhau khi chia đều, lặp lại được, không có giờ, phân bố theo người, điểm làm việc, đếm phút và khoảng điểm); ruff sạch ở phần đã đổi (lỗi cũ ở `scripts/`, 22 file chưa format không do mốc này); test hồi quy trace không đổi. Frontend không đổi

<a id="m70"></a>

#### M70: Số liệu đúng phạm vi (công cụ eval, tài liệu số liệu)

**Xong là thấy gì:** mở `eval/results/dataset_uta_rldd.md` thấy ngay đầu file nói số "báo sai / giờ" là gì và không là gì; mục 9 có bốn cách đếm và bảng theo FPS; `report.md` và `pilot-readiness.md` không còn số FL3D cũ; mỗi lần ai đó đọc 24 người giữ riêng đều để lại một dòng trong `eval/splits/uta_rldd_test_reads.tsv`

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 1 (A5 H2, H3, H4, M4, M7, L4, một phần M1). Không đổi ngưỡng nào của hệ thống, không đổi edge_agent; chỉ công cụ eval, số liệu và tài liệu

- **Bốn cách đếm báo sai** (`tools/uta_rldd.py`: `metrics`, `baseline_report`): nhánh buồn ngủ / mọi nhánh × sau 30 s đầu / cả video, giờ chia tương ứng. Trên 24 người giữ riêng: 1,0 (0,27–2,5), 0,9 (0,25–2,4), 1,0 (0,27–2,5), **1,2 (0,38–2,7)**; trên 24 người dùng để dò: 1,3, 1,5, 2,3, **2,5 (1,18–4,5)**. Chỉ dòng cuối đặt cạnh chỉ tiêu PRD, vì PRD tính mọi cảnh báo. Số "0,98" của M53 / M69 là dòng đầu, gọi đủ tên "báo sai nhánh buồn ngủ"
- **Hai phía cùng một luật 30 s đầu** (A5 M4): mục 5 của báo cáo in thêm số video `10` và `0` có cảnh báo khi chỉ đếm sau 30 s đầu, cạnh số đếm cả video. Hôm nay không đổi (không người nào chỉ có cảnh báo trong 30 s đầu)
- **Theo FPS của video** (A5 M3, H3; `fps_groups`, khoá `eval.min_video_fps` = 15): dev có 5 video dưới 15 FPS, test 8 (13 / 145). 6 trong 9 lần báo sai nhánh buồn ngủ nằm ở 2 video trong đó; 4 video tỉnh táo dưới 15 FPS chiếm khoảng một phần mười số giờ. **Không kết luận do FPS** (2 video, 2 người, camera khác nhau). Không video nào bị loại khỏi số nào
- **Luật chấm định trước** (`eval/splits/README.md`): tính mọi video, FPS thấp báo thêm một hàng, ba cách đếm luôn đi cùng nhau và gọi đủ tên, chỉ dòng "mọi nhánh cả video" so với PRD, quyết định `l1` 40 → 50 không chốt trên tập test đã đọc nhiều lần. Tỉ lệ mặt tin cậy chưa dùng để loại (chưa có ngưỡng chọn trên dev)
- **Nhật ký đọc tập test** (`log_test_read`, `reads_test_subjects`): `report` / `signals` / `compare` với `--split test` hoặc `all`, `tradeoff`, `personal` tự thêm một dòng vào `eval/splits/uta_rldd_test_reads.tsv` (thời gian, commit, cây sạch hay chưa commit, mã băm ngưỡng, lệnh) trước khi chấm. Không có cờ tắt. Bốn lần trước khi có nhật ký lấy từ tài liệu, ghi trong README
- **Nguồn gốc báo cáo** (một phần A5 M1; `tools/metrics.py provenance`): mọi báo cáo `seq_eval.py` và `uta_rldd.py report` có dòng `Source:` (commit, cây sạch hay chưa, sha256 của `thresholds.yaml`, ngày file trace). `seq_eval.py fl3d|yawdd|sust` không có `--replay` giờ in "AS TRACED" thay vì lặng lẽ cho số lúc trace (65 / 95 thay vì 77 / 95). Chưa làm: ghi `meta` vào chính file trace, commit `run_info.json`, checksum model
- **Báo cáo chạy lại với ngưỡng hôm nay** (`--replay block5`, trace `fl3d_v2`, `yawdd_v2`, `sust_v2`): FL3D L3 đạt 77 / 95 (báo cũ 75), L1 10 / 9 / 1 và 2,3 sai / giờ (cũ 9 / 7 / 2 và 4,6), L2 16 / 13 / 3, L3 85 / 83 / 1; SUST 8,8 / giờ (cũ 8,5), off_road 25 / 27 báo sai; YawDD không đổi (6,9 / giờ). Ảnh đơn (MRL, yawn-eye, DDD, State Farm) cần chạy model, không chạy lại
- **Tài liệu sửa**: `report.md` (ngày đo từng mục, 2.2, 2.3, 2.8 thêm bảng bốn cách đếm, AUC 0,920, số test 1000, giới hạn mới), `pilot-readiness.md` (đếm lại 4 / 9 / 5 / 5 / 1, A1, A2 theo `own_recordings.md`: 38 / 59 lần nhắm mắt có cảnh báo, 64 %, p95 2,03 s, A3, E3, ghi thẳng các tiêu chí không còn đường đạt), `dataset_uta_rldd.md` (đầu file, mục 5, 6, 9), `improvements.md` (nhóm 1 và việc 1 dùng đủ tên). `own_recordings.md` chưa tách theo phiên nên chưa rõ vì sao 21 lần nhắm mắt không có cảnh báo
- **Chưa làm, để anh quyết định:** replay trace bỏ bớt frame xuống 10 / 12 FPS (audit 6.1 việc 7); đọc dấu thời gian từng frame của F4_S44 và F2_S24 (`ffprobe`); ghi `meta` vào trace; chạy lại ảnh đơn; chốt `l1` bằng DROZY hoặc k-fold khai báo trước; sửa test đỏ ngẫu nhiên (A5 M8)
- Test: 1000 Python pass (7 test mới bằng chuỗi số giả); ruff sạch ở phần đã đổi; test hồi quy trace không đổi. Frontend không đổi. Tập test được đọc một lần trong mốc này (`report --split test`, có trong nhật ký) để có hai bảng mới, không để chọn ngưỡng

<a id="m71"></a>

#### M71: Vòng lặp `#/live` tự hồi phục; khoảng hở giữa hai frame không phải là một đợt (khối 1, 7, 8, 12)

**Xong là thấy gì:** mở `#/live`, làm cho trình duyệt ngừng gọi vòng lặp (e2e: thay `requestVideoFrameCallback` bằng hàm rỗng): HUD đứng khoảng 3 s rồi chạy tiếp, không tải lại trang. Dừng track camera: HUD hiện "Mất camera", "Lần thử 1", rồi tự giám sát lại. "Chi tiết kỹ thuật" có dòng "Vòng lặp đứng N lần, đã tự chạy lại · mở lại camera M lần". Chuỗi số giả: nhắm mắt 0,1 s, không có frame 2 s, nhắm mắt 0,1 s không còn ra L3

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 3 (top 10 việc 4; A1 M2, A4 H4, A4 M11, A3 L5). Thêm hai khoá ngưỡng (`distraction.max_gap_s`, `alert.max_gap_s`, cùng 0,5 s như `drowsiness.max_gap_s` đã có); không đổi ngưỡng nào đang dùng. Bản thiết bị (`edge_agent.main`) dùng chung khối 7, 8, 12 nên cũng nhận luật khoảng hở

- **Trước:** vòng lặp bản web chỉ chạy khi trình duyệt gọi `requestVideoFrameCallback`; im thì đứng tới khi tải lại trang (M67: 2 trên 4 lần chạy 10 phút). Camera kết thúc chỉ được báo, không bao giờ mở lại; track bị `mute` không được báo. Lỗi ở phía trang chỉ `console.error`. Và khi frame quay lại, khối 7, 8, 12 đo thời lượng bằng hiệu hai dấu thời gian nên nối hai frame hai bên chỗ đứng thành một đợt
- **Khoảng hở giữa hai frame (khối 7, 8, 12):** hai frame liền nhau cách quá `max_gap_s` thì những gì đang đếm kết thúc tại đó, không được tính, giống một lần mất mặt dài bằng vậy. Khối 7 (`DrowsinessAnalyzer._break_episodes`): đợt nhắm mắt (kể cả đợt đang được giữ qua gục đầu), phép đo chớp chậm, miệng đang mở chưa đủ thành ngáp, lần cúi đầu đang theo dõi, lần nhướn mày. Khối 8 (`DistractionAnalyzer._break_episodes`): đồng hồ nhìn lệch, mất mặt, quay hẳn đi, nhìn xuống. Khối 12: xác nhận tăng mức và xác nhận lý do mới bắt đầu lại từ frame sau khoảng hở; mức đang bật không bị đụng tới, L3 vẫn tức thì. Giữ nguyên: mốc mắt / tư thế, cửa sổ PERCLOS, cửa sổ liếc, cửa sổ điện thoại 2 s, các bộ đếm sự kiện đã ghi (đều là quan sát thật)
- **Cùng chuỗi của audit (nhắm 0,1 s · đứng · nhắm 0,1 s, 60 km/h, ngưỡng hiện tại):**

| Khoảng đứng | Trước | Sau |
|---:|---|---|
| 1,0 s | `closed_duration` 1,10 s, ghi một `microsleep` (25 điểm trong 5 phút) | Không sự kiện, điểm 0 |
| 2,0 s | L3 `microsleep` | Không cảnh báo |
| 7,0 s | L3 `microsleep` + `unresponsive` (báo quản lý ngay) | Không cảnh báo |
| Liếc 0,2 s · đứng 3 s · liếc 0,6 s | L2 `off_road` (`off_road_duration` 3,8 s) | Không cảnh báo (tối đa 0,9 s) |

- **Không làm mất cảnh báo thật:** mắt vẫn nhắm sau khi frame quay lại thì L3 sau 1,5 s **kể từ frame đầu tiên thấy lại**; vẫn nhìn lệch thì L2 sau 2,5 s kể từ đó. Hở 0,4 s (dưới `max_gap_s`) không cắt gì. Vòng lặp 5 / 10 / 12 FPS vẫn ra L3 sau khoảng 1,5 s (frame cách nhau 0,08–0,2 s)
- **Đồng hồ canh** (`frontend/src/live/watchdog.ts`, `LoopWatchdog`; `agent.ts` hỏi nó 3 lần mỗi `capture.frame_timeout_s`): không có frame mới trong 3 s khi camera còn sống và trang ở trước mặt thì vòng lặp tự lấy frame bằng timer (`1000 / capture.camera_fps` ms một lần) và đăng ký lại callback; trình duyệt gọi lại thì bỏ timer. Kéo bằng timer thêm 3 s vẫn không có frame mới (video đứng hình), track bị `mute` 3 s, hoặc track kết thúc: mất camera
- **Mở lại camera:** mất camera thì `camera(True)` (HUD "Mất camera", sự kiện `camera_lost`, nhịp `camera_lost`) và trang gọi lại `getUserMedia` mỗi `capture.reconnect_interval_s` (2 s), mỗi lần ghi "Lần thử N" lên HUD; luồng mới được 3 s để ra frame trước lần thử kế. Frame đầu tiên là `camera_restored`. `reconnect_interval_s: 0` thì không mở lại, như bản thiết bị
- **Lỗi frame phía trang** (MediaPipe, canvas, lời gọi sang Python): `WebAgent.frame_error(t, tên lớp lỗi)` đi cùng đường `TripRuntime.frame_failed` với lỗi trong Python, nên quá `hud.processing_error_s` (1 s) là "Lỗi xử lý", `agent_error`, nhịp `error`; frame tốt kế tiếp là `agent_recovered`. Chỉ tên lớp lỗi được chuyển đi
- **Bridge** (`edge_agent/web/bridge.py`): `frame_error`, `camera_attempts`, `hud_state` (HUD lấy trạng thái giữa hai frame, vì lúc mất camera không frame nào mang nó tới), và `settings()` có thêm `capture` (ba số của khối 1), trang không giữ hằng số riêng
- **Công cụ đo:** `LiveStats.recovery` (`pulls`, `reopens`), có trong `data-perf` và trong `bench/live.bench.mjs` (dòng "Loop watch", trường `summary.recovery`)
- **Cổng chất lượng:**
  - Báo cáo replay của FL3D, YawDD, SUST (`seq_eval.py --replay block5`), UTA-RLDD dev (`uta_rldd.py report --split dev`) và bản tự ghi (`record_trace.py report`), in ra ngoài repo trước và sau: giống hệt từng dòng (trừ dòng `Source:` có mã băm ngưỡng). Test hồi quy trace (M34) không đổi. Tập giữ riêng của UTA-RLDD không được đọc
  - 12 trong 19 test mới của `test_m71_frame_gaps.py` đỏ khi tắt luật khoảng hở; 7 test còn lại giữ hành vi cũ (hở ngắn, FPS thấp, ngáp đã đếm, mốc và cửa sổ, mức đang bật)
  - e2e "the loop recovers by itself" chạy cả ba đường trên bản build thật với Pyodide: callback im → đứng hơn 2 s rồi chạy lại và chạy tiếp; lỗi phía trang → "Lỗi xử lý" rồi hết; dừng track → mất camera, "Lần thử 1", giám sát lại
  - Chạy 10 phút bản build thật (`bench/live.bench.mjs --duration 10m`, Chromium không giao diện, camera giả phát hình mẫu 20 FPS, không có mặt, hai lượt chạy cùng lúc): WebGL phần mềm 20,00 FPS, phút thấp nhất 20,0, bỏ 0 / 12001 frame; GPU thật 20,00 FPS, phút thấp nhất 20,0, bỏ 0 / 12000. Cả hai đạt tiêu chí FPS và bộ nhớ. **Không lượt nào bị đứng** (`recovery.pulls` = 0), nên hai lượt này chỉ cho thấy đồng hồ canh không làm hỏng lúc bình thường; chúng không chứng minh nó cứu được lần đứng kiểu M67. Cổng chạy dài của M67 vì vậy chưa đóng: lần đứng thật kế tiếp sẽ hiện ở dòng "Loop watch" của công cụ
- **Cố ý, cần anh biết:**
  - Đợt nhắm mắt đang được giữ qua gục đầu cũng kết thúc ở khoảng hở. Nếu tài xế ngủ gục thật đúng lúc vòng lặp đứng hơn 0,5 s thì khi frame quay lại, đầu vẫn cúi (không đọc được mắt) nên đợt đó không đếm tiếp và `unresponsive` không phát; trước đây nó đếm cả khoảng không nhìn thấy. Chọn phía không báo sai lên quản lý
  - Tab bị che: không kéo frame. Trình duyệt chỉ cho timer khoảng 1 lần / giây, tức mọi frame cách nhau quá `max_gap_s`, không đợt nào đếm được; để nguyên `stalled` là nói thật hơn "đang giám sát"
  - Mất mặt ở hai đầu một lần đứng không còn thành "tạm ngưng: không thấy mặt" và không còn hỏi "Bạn còn ở đó không?" ngay; lần đứng được báo bằng đường riêng của nó (HUD đứng hình sau 3 s, `stalled` sau 10 s)
- **Chưa làm, để anh quyết định:**
  - Tạo lại `FaceLandmarker` (delegate CPU) khi MediaPipe lỗi mãi (đề xuất của A4 H4): chưa có cách gây lỗi này có chủ đích để thử
  - Vòng lặp chậm hơn 2 FPS (mọi frame cách nhau quá 0,5 s) vẫn báo "đang giám sát" kèm `low_fps` dù không luật thời lượng nào chạy được; nên coi là không giám sát
  - `Perclos` và cổng chất lượng vẫn cộng tối đa `max_gap_s` cho frame sau một khoảng hở (chú thích ghi "không cộng gì")
  - Nguyên nhân lần đứng của M67 vẫn chưa biết; mốc này chỉ làm cho nó tự hết
  - Chưa thử trên webcam thật, trình duyệt có giao diện, Android WebView; `mute` và video đứng hình mới có test đơn vị, chưa gặp thật
- Test: 1022 Python pass (22 test mới bằng chuỗi số giả: 19 ở `test_m71_frame_gaps.py`, 3 ở `test_web_bridge.py`), 149 frontend (11 mới: 10 của `watchdog.test.ts`, 1 nhãn), 5 e2e (1 mới); ruff / format, typecheck, build sạch

---

#### M72: Đóng các trạng thái ngừng giám sát mà không ai được báo (khối 8, 9, 10, 13)

**Xong là thấy gì:** chuỗi số giả ở 60 km/h, mặt lọt một phần khỏi khung 60 s (trong đó nhắm mắt 40 s): từ giây thứ 5 là "tạm ngưng giám sát" với lý do `bad_angle` ("camera lệch"), có tiếng báo và sự kiện `monitoring_unavailable` lên backend. Ở 3 km/h, mất mặt 3 s cũng "tạm ngưng" và sau đó hỏi "Bạn còn ở đó không?". Mở `#/live`: thanh trên không có nút "Chạy mô phỏng" và liên kết Dashboard; bấm "Dừng camera" hiện hộp "Kết thúc chuyến đi?", chọn "Tiếp tục lái" thì mọi thứ chạy tiếp, chọn "Kết thúc" thì ra bản tổng kết

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 2 (top 10 việc 2 và 3; A2 H1, A4 H1, A3 M4). Thêm một khoá ngưỡng tạm `distraction.pose_hold_s` (3 s); không đổi ngưỡng nào đang dùng. Bản thiết bị dùng chung khối 8, 9, 10 nên cũng nhận ba thay đổi đầu

- **Trước:** có ba đường mà hệ thống không đo gì nhưng vẫn báo "đang giám sát":
  - Mặt có trong ảnh nhưng lọt một phần ra ngoài (`face_reliable` False): khối 7 và 8 không đọc, đồng hồ mất mặt không chạy (vẫn có mặt), khối 9 chỉ tính giờ `low_light` / `glare` / `blur`. Lý do `bad_angle` không được tính giờ ở đâu. Chiều ngược lại: "đang nhìn lệch" từ trước đó bị giữ vô thời hạn thành L2
  - Xe bò 1–5 km/h: "tạm ngưng" cần `moving` (từ 5 km/h), nên che camera lúc kẹt xe không ai được báo, trong khi L3 vẫn chạy
  - Trên HUD: "Chạy mô phỏng" (ẩn cảnh báo thật sau kịch bản mẫu), liên kết Dashboard và "Dừng camera" (cả hai tắt camera, không tổng kết, không nhịp `ended`), đều một chạm, không hỏi lại, không tiếng
- **Khối 9, `bad_angle` được tính giờ** (`risk_engine.py`, `quality.TIMED_ISSUES`): mặt lọt một phần hoặc không có tư thế đầu suốt `risk.unavailable.low_quality_s` (5 s) thì `unavailable` với lý do `bad_angle`, như ba lý do chất lượng kia. Ngoại lệ gục đầu giữ nguyên: đợt nhắm mắt đang được giữ qua gục đầu (`head_drop`) vẫn được giám sát, vì đầu gục thường lọt một phần khỏi khung. Không hỏi "Bạn còn ở đó không?" (tài xế vẫn trong khung)
- **Khối 8, giới hạn giữ "đang lệch"** (`distraction.pose_hold_s`): không còn tư thế đáng tin (mất mặt hoặc mặt lọt một phần) thì trạng thái nhìn lệch chỉ được giữ tối đa 3 s kể từ tư thế cuối; sau đó kết thúc, `off_road_duration` về 0. Quay hẳn ra sau (`turned_away`, M38) giữ thời hạn riêng 10 s. `0` = không giới hạn (như trước)
- **Khối 10, `rolling`** (`VehicleContext.rolling`): đang chạy, hoặc đang bò giữa `stationary_kmh` (1) và `min_speed_kmh` (5). Khối 9 xét "tạm ngưng" theo `rolling` thay cho `moving`; khối 8 nhận thêm `rolling` và chỉ giữ đồng hồ mất mặt chạy trong lúc bò (luật nhìn lệch, điện thoại vẫn tắt dưới 5 km/h như cũ). Đứng yên (dưới 1 km/h) vẫn không báo gì (M30)
- **Cùng các chuỗi của audit (ngưỡng hiện tại):**

| Chuỗi | Trước | Sau |
|---|---|---|
| 60 km/h, mặt lọt một phần 60 s, nhắm mắt 40 s trong đó | Mức 0, 0 frame `unavailable`, không ai được báo | "Tạm ngưng" `bad_angle` từ giây thứ 5 tới hết; không cảnh báo (không đọc được mắt) |
| Liếc 35° trong 0,5 s rồi mặt lọt một phần 9,5 s | L2 `off_road`, giữ tới khi mặt quay lại | Một L2 ở giây 2,5 (như khi mất hẳn mặt), nhìn lệch kết thúc ở giây 3,5, "tạm ngưng" từ giây 5,5 |
| 3 km/h, mất mặt 60 s | `unavailable` False, HUD báo đang giám sát | "Tạm ngưng" `no_face` từ giây thứ 3, hỏi "Bạn còn ở đó không?" từ giây thứ 8 |
| 0 km/h, mất mặt 60 s | Không báo gì | Không đổi |

- **Vì sao `pose_hold_s` là 3 s chứ không ngắn hơn** (thử 0 / 1 / 1,5 / 2 / 3 s trên trace sẵn có, in ra ngoài repo):

| Trace | Frame có mặt nhưng không có tư thế | Đoạn dài nhất | Cảnh báo `off_road`: không giới hạn → 1 s → 3 s |
|---|---:|---:|---|
| 3MDAD (50 tài xế, có nhãn mất tập trung) | 2,9 % | 1,5 s | 81 → 78 → 81 |
| Bản tự ghi (12 phiên, có phiên nhìn lệch có chủ đích) | 0,28 % | 3,4 s | 12 → 7 → 12 |
| SUST-DDD (không có nhãn mất tập trung) | 0,62 % | 4,3 s | 30 → 21 → 30 |
| YawDD | 0,43 % | 2,9 s | 10 → 9 → 10 |
| FL3D | 0,36 % | 0,9 s | 7 → 7 → 7 |

  Giới hạn 1–2 s làm mất 4–5 trong 12 cảnh báo nhìn lệch **có chủ đích** của bản tự ghi (quay đầu tới mức mất mặt) và 1–3 trên 3MDAD. Ở 3 s số cảnh báo không đổi trên cả năm bộ. Vì vậy mốc này chỉ chặn việc giữ **vô thời hạn**; nó không giảm báo sai `off_road` trên dữ liệu hiện có (audit dự đoán sẽ giảm). Không trace nào có đoạn mặt lọt một phần dài từ 5 s, nên luật `bad_angle` cũng chưa bật lần nào trên FL3D / YawDD / SUST / 3MDAD / bản tự ghi: tác dụng của nó mới được chứng minh bằng chuỗi số giả
- **HUD (khối 13):**
  - "Chạy mô phỏng" và liên kết Dashboard chỉ còn hiện khi **không có thiết bị nào đang giám sát sau màn hình** (`hudModel.hudCanLeave`: `#/hud` chưa nối được edge agent, hoặc đang ở chế độ mô phỏng để có đường quay về). Trên `#/live` không bao giờ hiện. Xem mọi trạng thái vẫn ở `#/hud-preview`
  - Đang ở chế độ mô phỏng mà edge agent kết nối được thì HUD tự về thiết bị thật (trước: kịch bản mẫu che cảnh báo thật tới khi có người bấm)
  - "Dừng camera" (`#/live`) mở cùng hộp "Kết thúc chuyến đi?" và đi cùng đường `endTrip`: có bản tổng kết, có nhịp `ended`
  - Rời `#/live` khi chuyến chưa kết thúc (nút quay lại, gõ địa chỉ khác): phát âm `monitoring_stopped` và câu "Hệ thống đang không giám sát bạn", rồi kết thúc chuyến (tổng kết được gửi, đội xe thấy "Đã kết thúc chuyến" chứ không phải "Mất liên lạc" sau 90 s)
- **Cổng chất lượng:**
  - Replay trước và sau, in ra ngoài repo: FL3D, YawDD, SUST (`seq_eval.py --replay block5`), bản tự ghi (`record_trace.py report`), `trace_studies.py glance`, 3MDAD (`gaze_study.py report`, `phone_study.py report`) giống hệt từng dòng (trừ dòng `Source:`). UTA-RLDD dev (`uta_rldd.py report --split dev`): số cảnh báo, báo sai / giờ, số người có cảnh báo không đổi; bảng cửa sổ 10 s lệch 1–2 cửa sổ (nhãn `10`: ≥ L1 26,6 → 26,5 %, L3 6,4 → 6,3 %; "Distraction ≥ L2" 0,6 → 0,5 % ở nhãn `0`, 0,7 → 0,6 % ở nhãn `10`). Tập giữ riêng không được đọc
  - 7 trong 18 test của `test_m72_silent_states.py` đỏ khi bỏ hai thay đổi của khối 9 và 10; test giới hạn giữ có bản đối chứng `pose_hold_s = 0`
  - e2e trên bản build thật: không có hai nút trên `#/live`; "Dừng camera" → "Tiếp tục lái" thì vòng lặp chạy tiếp, → "Kết thúc" thì ra tổng kết; rời trang giữa chuyến thì quản lý thấy "Đã kết thúc chuyến" và có thêm một báo cáo (test này đỏ khi trả về hành vi cũ)
- **Cố ý, cần anh biết:**
  - Liếc ngắn rồi mặt lọt một phần vẫn ra **một** L2 ở giây 2,5, giống hệt khi mất hẳn mặt từ trước tới nay. Muốn bỏ cả lần đó phải hạ `pose_hold_s` xuống dưới 1,5 s, và số trên cho thấy cái giá
  - Trên UTA-RLDD dev có một cửa sổ L3 của video buồn ngủ biến mất (mặt lọt một phần quá 5 s nên "tạm ngưng" thay cho cảnh báo). Đây là đánh đổi của luật `bad_angle`: không đọc được mặt thì không đoán
  - Có thiết bị đang kết nối thì `#/hud` không vào được chế độ mô phỏng nữa, kể cả khi xe đỗ; dùng `#/hud-preview`
  - Ở 1–5 km/h: mất mặt 8 s thì hỏi "Bạn còn ở đó không?", không trả lời thì còi L3, như khi chạy nhanh
- **Chưa làm, để anh quyết định:**
  - Đóng tab hoặc tải lại trang giữa chuyến: trình duyệt không cho chạy việc bất đồng bộ lúc đó, nên không có tổng kết và không có tiếng; đội xe thấy "Mất liên lạc" sau 90 s như cũ
  - Nhiễu tốc độ quanh 1 km/h lúc dừng (GPS, việc 12 của `improvements.md`) giờ có thể bật "tạm ngưng" khi xe thật ra đang đứng; cần làm mượt tốc độ ở việc đó
  - `eval/results/dataset_uta_rldd.md` chưa sinh lại (lệch 1–2 cửa sổ ở bảng mục 3); sinh lại phải đọc tập giữ riêng thêm một lần
  - HUD chưa hiện gì trong 5 s đầu mặt lọt một phần (`quality.issue` đã có trong snapshot, giao diện chưa đọc)
  - Tần suất mặt lọt một phần khi camera đặt lệch như trên màn hình xe vẫn chưa có số: cần một phiên tự ghi ngồi lệch
  - Chưa bấm thử bằng tay trên trình duyệt có giao diện; đường tự về thiết bị thật từ chế độ mô phỏng của `#/hud` chưa có test (chỉ đọc code)
- Test: 1041 Python pass (19 test mới bằng chuỗi số giả: 18 ở `test_m72_silent_states.py`, 1 ở `test_decision.py`), 151 frontend (2 mới), 6 e2e (1 mới, 1 mở rộng); ruff / format sạch ở phần đã đổi, typecheck, build sạch

#### M73: Ngữ cảnh quanh điểm buồn ngủ: "lái lâu" tắt được, dừng đèn đỏ không mang sang, replay chọn giờ (khối 9, 10, 11)

**Xong là thấy gì:** chuỗi số giả, đã lái 2 giờ: `long_drive` bật; đỗ 2 phút (nghỉ) thì nó tắt và HUD "Lái liên tục" về 0 ở cùng frame; bấm "Đổi tài xế" cũng vậy. Chạy 50 km/h, dừng 60 s, nhắm mắt 25 s trong lúc dừng, chạy lại: không cảnh báo nào, `drowsy_score` về 0. Chạy `tools/uta_rldd.py compare --split dev --set eval.replay_clock_hour=2 --set eval.replay_drive_time_s=7200` ra một dòng "what-if" ở 02:00 sau 2 giờ lái

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 5 (top 10 việc 6; A3 H1, H4). Ngưỡng dừng 10 s là lựa chọn của anh (08/10). Thêm ba khoá: `context.short_stop_forget_s` (tạm), `eval.replay_clock_hour`, `eval.replay_drive_time_s`; không đổi ngưỡng nào đang dùng. Bản web dùng chung khối 9–11 nên nhận cả hai thay đổi hành vi

- **Trước:**
  - `long_drive` đọc `drive_time_s` của nguồn tốc độ, là tổng thời gian xe lăn bánh từ lúc mở app và chỉ cộng dồn. Sau 2 giờ, hệ số lái lâu (×1,2) bật mãi: qua mọi lần nghỉ, cho cả tài xế vừa nhận xe. HUD thì hiện "Lái liên tục" bằng một bộ đếm khác (của bản tổng kết), có đặt lại: tài xế thấy 1 phút, luật vẫn tính 2 giờ
  - Chỉ lần dừng từ `rest_after_s` (120 s) mới bị bỏ khỏi bằng chứng. Dừng ngắn hơn thì PERCLOS và mốc microsleep gom lúc đứng yên được giữ; mức bị chặn về 0 lúc đứng (M30) nhưng trần đó mất ngay khi xe lăn bánh
  - Mọi replay chạy ở 12:00, 0 giờ lái: hai hệ số ngữ cảnh chưa từng được đo
- **Khối 10, `drive_run_s`** (`vehicle_context.py`): `ContextTracker` tự đếm thời gian lái từ lần nghỉ / lần đổi tài xế gần nhất (cộng phần tăng của `drive_time_s`, về 0 khi `resting`, `new_driver()` khi đổi tài xế). `long_drive = drive_run_s >= long_drive_s`. `drive_time_s` vẫn còn trong ngữ cảnh, không luật nào đọc. Số đọc đầu tiên mang cả `initial_drive_time_s` của kịch bản
- **Một bộ đếm cho HUD và luật** (`trip_summary.py`): `trip.drive_run_s` của HUD lấy thẳng `drive_run_s` của khối 10. Hệ quả nhìn thấy được: kịch bản có `initial_drive_time_s` (ví dụ `highway_night` 7000 s) thì HUD hiện luôn phần đó, trước đây bắt đầu từ 0. Nguồn mặc định (`ExternalVehicle`) bắt đầu từ 0 nên `#/live` không đổi. `longest_drive_s` của bản tổng kết giữ cách đếm cũ
- **Dừng từ 10 s** (`pipeline.py` `_track_rest`, `VehicleContext.long_stop`): xe chạy lại sau lần dừng từ `context.short_stop_forget_s` thì khối 7 và trip memory bỏ phần gom từ lúc xe dừng (`forget_since`, đường sẵn có của lần nghỉ). Phần gom **trước** khi dừng được giữ. Dừng ngắn hơn giữ nguyên mọi thứ. Chỉ lần nghỉ mới xoá bộ đếm leo thang `repeated_l1` của khối 12 (tài xế chưa nghỉ). `0` = mọi lần dừng; từ `rest_after_s` trở lên = chỉ lần nghỉ (như trước M73)
- **Cùng các chuỗi của audit** (chạy 50 km/h 60 s, dừng, chạy lại; 30 FPS, ngưỡng hiện tại; "trước" = đặt khoá mới bằng 120):

| Chuỗi | Trước | Sau |
|---|---|---|
| 12:00, dừng 60 s, nhắm 25 s trong đó | Điểm 65 khi lăn bánh, L1 sau 1,0 s, ở L1 41 s | Điểm 0, không cảnh báo |
| 02:00, dừng 60 s, nhắm 25 s trong đó | Điểm 78, L2 sau 0,5 s | Điểm 0, không cảnh báo |
| Dừng 15 s, nhắm 3 s trong đó | 25 điểm (30 lúc 02:00) theo tiếp 5 phút | Điểm 0 |
| Dừng 8 s, nhắm 3 s trong đó | 25 điểm theo tiếp 5 phút | Không đổi (dưới 10 s) |
| Dừng 30 s, mắt vẫn nhắm khi xe lăn bánh | L3 | L3 trong 2,5 s đầu (đợt nhắm đếm lại từ lúc lăn bánh) |

- **Replay chọn giờ và thời gian đã lái** (`tools/seq_eval.py` `replay_vehicle`): `eval.replay_clock_hour` (12) và `eval.replay_drive_time_s` (0) trong YAML; `tools/seq_eval.py`, `tools/uta_rldd.py`, `tools/eval.py` đều dựng xe qua hàm này. Đổi bằng `--set`, nên `compare` cho luôn dòng hiện tại cạnh dòng what-if
- **Số đo đầu tiên của hai hệ số** (UTA-RLDD, 24 người dùng để dò, 3,87 giờ video tỉnh táo, báo sai nhánh buồn ngủ sau 30 s đầu; in ra màn hình, không ghi `eval/results`, **không đọc tập giữ riêng**):

| Điều kiện | Báo sai | / giờ (cận trên rộng hơn) | Cửa sổ `0` ≥ L1 | Video `5` có cảnh báo | Video `10` có cảnh báo |
|---|---:|---:|---:|---:|---:|
| 12:00, 0 giờ lái (mặc định) | 5 | 1,29 (3,02) | 3,7 % | 5 / 24 | 14 / 24 |
| 02:00 (×1,2) | 5 | 1,29 (3,02) | 5,9 % | 8 / 24 | 15 / 24 |
| 02:00, đã lái 2 giờ (×1,44) | 11 | 2,85 (6,02) | 8,0 % | 11 / 24 | 18 / 24 |

  Khớp từng số với phép quy đổi của audit (chia ngưỡng cho hệ số), nay là replay thật. Riêng hệ số đêm không thêm lần báo sai nào; hai hệ số cùng bật thì hơn gấp đôi. Sau mốc này điều kiện ×1,44 chỉ còn đúng với người lái liên tục 2 giờ không nghỉ, không còn áp cho người vừa nghỉ hoặc vừa nhận xe
- **Cổng chất lượng:**
  - Dòng "current" của `compare` giữ nguyên 5 lần / 1,29 / 14 / 5: replay không có lần dừng và bắt đầu từ 0 giờ lái, nên hai thay đổi hành vi không chạm vào số nào đã báo cáo. Test hồi quy trace không phải chốt lại
  - `test_before_m73_the_same_stop_raised_an_alert_as_the_vehicle_rolled` chạy lại hành vi cũ bằng khoá mới = 120 và thấy L1; bản đối chứng cho test "không cảnh báo"
- **Chưa làm / còn hở:**
  - **Hai hệ số nhân chồng (1,44) hay cộng trần: chờ anh quyết**, nay đã có số ở bảng trên
  - Ngưỡng 10 s chưa có dữ liệu đứng sau: không trace nào có lần dừng. Người ngủ gật thật ở đèn đỏ mất phần điểm đó khi xe chạy lại (L3 khi đang chạy không đổi)
  - Bản tổng kết chuyến vẫn đếm lần nhắm mắt ở đèn đỏ là một microsleep (cố ý từ M27); mốc này không đụng tới
  - Trong lúc dừng, điểm vẫn hiện trên HUD (65 ở chuỗi đầu) rồi về 0 khi lăn bánh; phút đó của biểu đồ 15 phút vẫn được tính
  - Bảng ×1,2 / ×1,44 chỉ nói về phía báo sai, trên video 10 phút của người ngồi trước laptop; không nói được hệ số có tăng độ nhạy đúng lúc cần không
  - Khung giờ đêm [0, 5) dùng chung cho điểm và độ sáng HUD (audit X6): chưa đụng
- Test: 1052 Python pass (11 test mới ở `test_m73_context.py`, 1 test của M65 sửa số mong đợi vì HUD nay cộng `initial_drive_time_s`); ruff / format sạch; `frontend/public/py/edge_agent.zip` đóng gói lại. Không đổi code frontend, nên test frontend và e2e không chạy lại

<a id="m74"></a>

#### M74: Khối 12 không còn để cooldown nuốt cảnh báo; câu hỏi hiện diện không lặp (khối 12)

**Xong là thấy gì:** chuỗi số giả với ngưỡng trong YAML: nhìn lệch 3 s (tiếng L2), nhìn lại đường 5 s, rồi nhìn lệch 40 s: có tiếng L2 thứ hai khi cooldown 30 s hết. `drowsy_score` ở L1 đều 30 phút: chuông mỗi khoảng 2 phút, lần thứ ba là L2 "Đã nhắc nhiều lần", rồi đếm lại. Microsleep 4 s, cầm điện thoại từ giây 1 tới giây 60: sau còi L3 có tiếng L2 `phone`. Mặt hiện đúng một frame mỗi 12 s khi xe chạy: "Bạn còn ở đó không?" hỏi một lần

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 6 (top 10 việc 7; A3 H2, H3, M2, M3). Thêm ba khoá: `alert.remind` (true), `presence.back_s` (1 s, tạm), `presence.reask_after_s` (60 s, tạm); không đổi ngưỡng nào đang dùng. Bản web dùng chung khối 12 nên nhận cả các thay đổi này. **Báo sai đo được có tăng, xem bảng; giữ hay tắt `alert.remind` chờ anh quyết**

- **Trước:**
  - `_emit` ghi lý do vào "đã báo" trước khi xét cooldown. Đợt bắt đầu trong cooldown bị giữ lại rồi không bao giờ phát, dù kéo dài bao lâu. Mức đứng yên không có lần nhắc nào: L1 nửa giờ là một tiếng chuông
  - Sau lần leo thang đầu, danh sách đếm `repeated_l1` không được xoá: mọi lần phát L1 sau đó đều ra L2 (âm thanh + rung ghế) tới khi xe nghỉ 2 phút. Vì mức đứng yên không phát lại, thứ được đếm là số lần điểm cắt qua ngưỡng 40, không phải thời gian buồn ngủ
  - Khi mức hạ, lý do của mức thấp được đánh dấu "đã báo": lý do bắt đầu dưới một mức cao hơn không có tiếng và không có sự kiện nào của riêng nó
  - `PresenceCheck` xoá toàn bộ trạng thái ngay khi có một frame thấy mặt, kể cả "đã trả lời"
- **Nhắc lại sau cooldown** (`alert_manager.py`: `_due`, `_check_new_reasons`; khoá `alert.remind`): ở mức đang bật, lý do đang có mà lần phát gần nhất ở mức đó đã cũ hơn `cooldown_s[mức]` (hoặc chưa từng phát ở mức đó) được coi như lý do mới: giữ đủ `rise_confirm_s[mức]` rồi phát. Một cơ chế này đóng ba ca: đợt bắt đầu trong cooldown, mức đứng yên, và lý do nằm dưới mức cao hơn (A3 M3). Chu kỳ nhắc là cooldown + thời gian xác nhận: L1 khoảng 121 s, L2 khoảng 30,5 s. Một lần nhắc mang mọi lý do của frame đó và đặt lại giờ cho tất cả, nên hai lý do đến hạn lệch nhau không thành hai tiếng. Mức có cooldown 0 (L3) không được nhắc: khối 9 đã có `unresponsive` cho lần nhắm kéo dài. Một frame lẻ không đủ để nhắc; khoảng hở giữa hai frame (M71) bắt đầu lại phần xác nhận của lần nhắc. `remind: false` = như trước M74
- **Leo thang `repeated_l1`** (`_repeated`): lần nhắc được đếm như một lần phát L1; lý do nào vừa leo thang thì bộ đếm của nó về rỗng, lý do khác giữ nguyên. Lần nhắc ở L3 (chỉ có khi ai đó đặt cooldown L3 khác 0) không được đếm vào `repeated_l3`
- **Câu hỏi hiện diện** (`presence.py`): khi câu hỏi đã được đặt ra (đang hỏi, đã chạm, hoặc đã hết giờ), mặt phải được thấy liền `presence.back_s` mới coi là đã trở lại; trước khi hỏi thì một frame thấy mặt vẫn xoá ngay như cũ. Sau một lần chạm, không hỏi lại trong `presence.reask_after_s`. Hệ quả nhìn thấy được: mặt hiện lại thì câu hỏi còn trên màn hình thêm tối đa 1 s
- **Cùng các chuỗi của audit** (bước 0,1 s, ngưỡng YAML; "trước" của ba dòng không phải leo thang = `alert.remind=false`, hai dòng leo thang lấy số của audit):

| Chuỗi | Trước | Sau |
|---|---|---|
| Nhìn lệch 3 s, nhìn lại 5 s, nhìn lệch 40 s | 1 tiếng L2 (0,5 s); 40 s sau không tiếng | 2 tiếng L2 (0,5 s và 31,0 s) |
| L1 đều 30 phút | 1 chuông (giây 1) | 15 lần: L1, L1, L2 `repeated_l1`, lặp lại, mỗi ~121 s |
| L1 5 s, hết 10 s, L1 đều 20 phút | 1 chuông | 11 lần, cùng nhịp |
| L1 bật 20 s, tắt 110 s, trong 40 phút (18 đợt) | L1, L1, rồi 16 lần L2 | L1, L1, L2 lặp 6 lượt: 12 L1, 6 L2 |
| Microsleep 4 s, điện thoại giây 1–60 | 1 còi L3; 56 s cầm điện thoại không tiếng | Còi L3, rồi L2 `phone` khi mức hạ (7,5 s) và nhắc mỗi ~30 s |
| Nhìn lệch L2 6 s, `drowsy_score` L1 từ giây 2, 10 phút | Không chuông L1 nào | L1 khi mức hạ (10 s), rồi L1, L2, L1, L1 |
| Mặt hiện 1 frame mỗi 12 s, 2 phút, không chạm | 10 lần hỏi | 1 lần hỏi, 1 `no_answer` |
| Như trên, chạm ngay khi được hỏi | 10 lần hỏi | 1 lần hỏi |

- **Số đo, phía báo sai** (in ra màn hình, `eval/results` không bị ghi, **tập giữ riêng không được đọc**). UTA-RLDD, 24 người dùng để dò, `tools/uta_rldd.py compare --split dev --set alert.remind=false`:

| | `remind: false` (như M73) | `remind: true` (M74) |
|---|---:|---:|
| Báo sai nhánh buồn ngủ trên video `0`, sau 30 s đầu | 5 | 7 |
| / giờ (cận trên rộng hơn) | 1,29 (3,02) | 1,81 (3,90) |
| Trong đó từ L2 trở lên | 1 | 2 |
| Mọi nhánh, cả video (dòng so với PRD) | 10 | 12 |
| Video `0` có cảnh báo | 3 / 24 | 3 / 24 |
| Cảnh báo nhánh buồn ngủ trên video `10` (từ L2) | 103 (88) | 127 (98) |
| Video `10` có cảnh báo / AUC / cửa sổ `0` ≥ L1 | 14 / 24 · 0,859 · 3,7 % | Không đổi |

  Hai lần thêm trên video `0` là một lần nhắc L1 (F1_S01, giây 432) và một `repeated_l1` L2 (F2_S15, giây 277); không người mới nào bị báo sai, ba người vốn đã bị thì bị nhắc thêm. Trên video `10`, 24 lần thêm là lần nhắc và leo thang ở 10 video mà trước đó im sau tiếng đầu
- **FL3D** (`tools/seq_eval.py fl3d --traces data/eval_traces/fl3d_v2.pkl --replay block5 --set alert.remind=…`, chỉ in): L1 10 lần (9 đúng / 1 sai, 2,3 sai / giờ) → 15 (12 / 3, 6,9 / giờ); L2 16 (13 / 3, 6,9 / giờ) → 38 (29 / 8, 18,5 / giờ); L3 không đổi. Phần tăng gần như toàn bộ là `drowsy_score` ở L2 được nhắc mỗi 30 s (sai 1 → 6): điểm nhớ một microsleep trong 5 phút nên đứng trên ngưỡng L2 lâu sau sự kiện, và 0,43 giờ "tỉnh táo" của FL3D là phần giữa các lần diễn. YawDD và SUST không đổi một số nào
- **Cổng chất lượng:**
  - `--set alert.remind=false` cho lại đúng dòng của M73 (5; 1,29; 14 / 24) và đúng bảng FL3D của M70: phần tăng chỉ đến từ lần nhắc; xoá bộ đếm sau leo thang và câu hỏi hiện diện không chạm vào số nào của replay
  - Test hồi quy trace chốt lại có lý do: 2 trong 36 video (FL3D `P1042762`, `P1043115`) thêm lần nhắc L2 `drowsy_score`; 34 video không đổi
  - 6 test mới có bản đối chứng chạy lại hành vi cũ bằng khoá mới (`remind=false`, `back_s=0`, `reask_after_s=0`) và thấy đúng số của audit
- **Test cũ đổi theo hành vi mới:** `test_dropping_a_level_is_not_a_new_alert` (nay kiểm đúng ca nó muốn: lý do đã báo ở mức thấp rồi thì hạ mức không báo lại), `test_flickering_reason_is_not_re_alerted` (thêm một lần nhắc ở 32 s, và bản `remind=false` giữ số cũ), hai test hiện diện của M44 (mặt phải hiện lại đủ `back_s`, hỏi lại sau `reask_after_s`)
- **Chưa làm / còn hở:**
  - **Giữ `alert.remind: true` hay tắt: chờ anh quyết**, nay đã có số. Nhắc L2 mỗi 30 s cho `drowsy_score` là phần tốn nhất; đổi `cooldown_s` của L2 hoặc nhắc theo từng lý do là đổi ngưỡng, em không tự làm
  - Số trong `eval/results` (`dataset_uta_rldd.md`, `dataset_fl3d.md`, `report.md`) và `pilot-readiness.md` là của hành vi trước M74 (đúng với `alert.remind=false`). Sinh lại phải ghi đè `eval/results` và đọc tập giữ riêng một lần: cần anh cho phép
  - Lần nhìn lệch thứ hai trong chuỗi đầu vẫn im 22 s (tới khi cooldown của lần đầu hết); rút cooldown L2 là quyết định ngưỡng
  - Một lý do mới nhập vào ở cùng mức vẫn làm lý do cũ được đếm thêm một lần cho `repeated_l1` (có từ M32), chưa đụng
  - Sau `no_answer`, mặt hiện lại đủ lâu rồi mất tiếp thì vẫn hỏi lại ngay (khoảng chờ chỉ áp sau lần chạm). Hai khoá mới của câu hỏi hiện diện là tạm, chưa có dữ liệu; trong 60 s sau lần chạm, tài xế gục ra khỏi khung sẽ không được hỏi
  - Leo thang L3 (`repeated_l3` không có trần) và bấm "báo sai" không đổi gì ở khối 12: chưa đụng
  - Tiếng trên giao diện thật chưa nghe: không mở `#/live` trong mốc này
- Test: 1072 Python pass (20 test mới ở `test_m74_alert_reminders.py`, 4 test cũ sửa); ruff / format sạch ở phần đã đổi; `frontend/public/py/edge_agent.zip` đóng gói lại. Không đổi code frontend, nên test frontend và e2e không chạy lại

<a id="m75"></a>

#### M75: Hành vi dưới 15 FPS, chỉ đo (công cụ eval, test khối 7, 8, 9, 12)

**Xong là thấy gì:** `python tools/uta_rldd.py fps --out eval/results/fps_low_uta_rldd.md` in ra bốn bảng: cảnh báo, số đo của khối 7, video đổi số cảnh báo, và video vốn quay chậm. `pytest tests/test_edge_agent/test_m75_low_fps.py`: 81 pass, 7 xfail

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 7 (mục 4.4; A2 L6, A5 M3). **Chỉ đo**: không đổi ngưỡng, không đổi dòng nào trong `edge_agent/`. Thêm 4 khoá của công cụ: `eval.fps_study_rates` (15, 12, 10), `eval.fps_study_jitter_cv` (0,3, tạm), `eval.fps_study_repeats` (3), `eval.fps_study_min_source_fps` (25)

- **Câu hỏi:** mọi test thời gian cố định 30 FPS, thiết bị đích ước lượng 11–14 FPS, và trên UTA-RLDD 6 trong 9 lần báo sai nằm ở hai video quay dưới 15 FPS. Hệ thống làm gì ở 10–12 FPS, và FPS thấp có phải là nguyên nhân của các lần báo sai đó không
- **Cách đo trên dataset** (`tools/seq_eval.py` `resample_trace`, `tools/uta_rldd.py` `fps_study`, `fps_report`):
  - Lấy trace của video quay từ 25 FPS trở lên (59 video của 21 người trong 24 người dùng để dò), bỏ bớt frame như một vòng lặp chậm: vòng lặp xin một frame mỗi 1 / tốc độ giây và nhận frame đã ghi đầu tiên từ thời điểm đó, kèm đúng giờ chụp của nó. Không nội suy, không frame nào dùng hai lần
  - "Không đều": khoảng chờ theo log-normal quanh 1 / tốc độ, hệ số biến thiên 0,3 (em chọn, tạm: chưa có phân bố thời gian frame nào của thiết bị)
  - Mỗi tốc độ chạy 3 lượt (lưới bắt đầu lệch nhau, hoặc rút khoảng chờ khác). Dao động giữa các lượt của cùng một dòng là nhiễu của phép đo; chênh lệch giữa hai dòng nhỏ hơn mức đó thì không phải phát hiện
  - Cùng một video được so với chính nó, nên tách được FPS khỏi người và camera. Bảng nhóm theo FPS của M70 không tách được
  - `summarize` nay lấy giờ của cảnh báo từ dấu thời gian của frame thay cho số thứ tự frame / FPS. Với trace gốc hai cách cho cùng một số (test hồi quy trace và mọi báo cáo cũ không đổi)
- **Kết quả trên dataset** (ngưỡng hôm nay, `alert.remind: true`; khối 5 quyết định lại từ đầu vào đã ghi):

| Vòng lặp | Khoảng frame p50 / p95 / lớn nhất (ms) | Báo sai nhánh buồn ngủ | / giờ | Mọi nhánh, cả video | Người `10` có cảnh báo | đạt L3 | AUC điểm trung bình |
|---|---:|---:|---:|---:|---:|---:|---:|
| Như đã quay (30) | 33 / 33 / 40 | 5 | 1,55 | 10 | 12 / 19 | 10 | 0,892 |
| 15 FPS đều | 67 / 67 / 100 | 4–7 | 1,24–2,17 | 9–12 | 12–14 | 10 | 0,874–0,887 |
| 15 FPS không đều | 67 / 100 / 333 | 3–4 | 0,93–1,24 | 7–9 | 13 | 10–11 | 0,876–0,895 |
| 12 FPS đều | 67 / 100 / 120 | 3–5 | 0,93–1,55 | 7–10 | 12–13 | 10–11 | 0,878–0,889 |
| 12 FPS không đều | 67 / 133 / 433 | 3–5 | 0,93–1,55 | 7–10 | 12–13 | 9–10 | 0,875–0,892 |
| 10 FPS đều | 100 / 100 / 133 | 2–6 | 0,62–1,86 | 6–10 | 12–13 | 10–11 | 0,864–0,897 |
| 10 FPS không đều | 100 / 167 / 533 | 3–4 | 0,93–1,24 | 7–9 | 12–13 | 9–10 | 0,882–0,892 |

  - **Báo sai không tăng khi hạ FPS.** Mọi dòng nằm trong nhiễu của nhau: riêng dòng 15 FPS đều đã dao động 4–7 giữa ba lượt chỉ khác nhau ở frame bắt đầu. 20 trong 59 video đổi số cảnh báo buồn ngủ ở ít nhất một lượt, kể cả ở 15 FPS
  - **Nên hai video dưới 15 FPS mang 6 / 9 lần báo sai không giải thích được bằng việc khối 7–12 nhận ít frame.** Khả năng còn lại: người đó, camera đó, hoặc landmark kém đi khi model chạy trên video chậm (phần này không đo được bằng cách bỏ frame). Chưa kết luận được là cái nào
  - **Số đo trôi theo FPS, đều là số không cộng vào điểm:** chớp mắt đếm được trên video tỉnh 12,4 → 10,4–11,8 lần / phút (chớp ngắn rơi giữa hai frame); thời lượng một lần chớp 0,30 → 0,32–0,36 s. PERCLOS trung bình không đổi (0,033 và 0,105), sự kiện microsleep trên video buồn ngủ 25,7 → 24,1–27,0 / giờ, điểm trung bình 22,9 → 21,9–24,1
  - Một khoảng 533 ms (một lần trong mọi lượt) vượt `max_gap_s` 0,5 s nên được coi là lỗ hổng, không phải frame chậm (M71)
- **Chuỗi số giả** (`test_m75_low_fps.py`): cùng một việc trước camera, lấy mẫu bởi 8 vòng lặp: đều 30 / 15 / 12 / 10 FPS, không đều 12 / 10 FPS (hai bộ khoảng chờ), và "giật" (ba frame cách nhau 1 / 30 s rồi 0,3 s không có frame, trung bình 10 FPS). Mỗi ca thử ở 5 thời điểm lệch nhau so với lưới frame
  - **Giữ ở mọi vòng lặp (81 ca pass):**
    - Thời lượng không bao giờ bị đo dài hơn thật: nhắm mắt 1,45 s không ra L3, nhìn lệch 1,95 s không ra cảnh báo, mở miệng 1,3 s không là ngáp
    - Sự kiện rõ ràng có đúng một cảnh báo, trễ tối đa hai khoảng frame: microsleep 3 s → L3, nhìn lệch 4 s → L2 `off_road`, điện thoại 5 s → L2 `phone`
    - Chớp 0,25 s mỗi 3,7 s trong 4 phút: không cảnh báo, không microsleep, PERCLOS trong ±0,02 của 6,8 % dù vòng lặp "giật" lấy ba frame trong 0,1 s rồi không frame nào trong 0,3 s. PERCLOS tính theo thời gian, không theo số frame
    - Ngáp 3 s là một lần ngáp
  - **Cái giá của vòng lặp chậm (7 ca `xfail`, ghi điều mong muốn và chỗ nó chưa đúng):**
    - Thời lượng bị đo **ngắn** đi tối đa hai khoảng frame (frame đầu thấy mắt nhắm tới sau khi mắt nhắm, frame cuối tới trước khi mắt mở). Nhắm mắt 1,6 s, vượt mốc L3 chỉ 0,1 s: mọi vòng lặp đều tới 10 FPS vẫn hú còi; 10 FPS không đều bỏ sót 4 / 5 và 3 / 5 lần thử, vòng lặp "giật" 1 / 5
    - Nhắm mắt 1,1 s (vượt `microsleep_min_s` 0,1 s): sự kiện `microsleep` (25 điểm trong 5 phút) mất ở 5 / 5, 3 / 5 và 5 / 5 lần thử của ba vòng lặp đó
    - Gục đầu ở vòng lặp "giật": 1 / 5 lần thành `bow`. Khoảng 0,3 s không frame rơi vào lúc đầu bật lên; frame đầu sau đó thấy mắt mở và tính cả 0,3 s là "mở", tỉ lệ nhắm của cú gục tụt dưới `nod.eyes_closed_min_frac`
  - **Đo được nhưng không đánh dấu lỗi:** `phone_ratio_2s` là tỉ lệ số frame, không phải thời gian (audit X4). Điện thoại thấy 0,8 s trong 2 s (40 %) đọc ra 36–48 % tuỳ vòng lặp; cảnh báo `phone` ở vòng lặp "giật" tới sớm hơn tối đa 0,1 s. Còn xa mốc 60 % nên không tạo cảnh báo sai trong các ca đã thử
- **Đọc kết quả thế nào:** ở 10–15 FPS khối 7–12 không báo sai nhiều hơn và không bỏ sót sự kiện rõ ràng; cái mất là độ nhạy ở sát mốc, lớn nhất khi frame tới không đều. Chiều hỏng là bỏ sót, không phải báo nhầm
- **Chưa làm / còn hở:**
  - **Khối 2–5 trên máy chậm không nằm trong phép đo.** Landmark ở đây được tính trên mọi frame của một máy nhanh rồi mới bỏ bớt. MediaPipe chạy chế độ video dùng frame trước để bám mặt; ở 10 FPS nó có thể bám kém hơn. Cần video gốc và chạy lại model, hoặc thiết bị thật
  - Nhánh điện thoại không có trong trace UTA-RLDD (model tắt lúc ghi); cổng chất lượng frame và đăng ký cũng không chạy
  - Độ không đều 0,3 là giả định. Chưa có phân bố thời gian frame của Android box; vòng lặp "giật" là hình mẫu em tự đặt
  - Chỉ đo trên 24 người dùng để dò; tập giữ riêng không được đọc (nhật ký `eval/splits/uta_rldd_test_reads.tsv` không thêm dòng)
  - FL3D (25 FPS, có nhãn từng frame) không chạy: nhãn gắn với số thứ tự frame nên bỏ frame phải viết lại phần chấm. Độ trễ và bỏ sót L3 vì vậy mới có số từ chuỗi giả, chưa có số từ microsleep diễn
  - **Không sửa gì** (mốc chỉ đo). Ba chỗ có thể sửa, mỗi chỗ là một quyết định của anh: (1) bù phần thời lượng bị đo ngắn khi khoảng frame lớn, đổi lại có thể tăng báo sai L3; (2) `phone_ratio_2s` và tỉ lệ nhắm sâu (`eyes.py`) tính theo thời gian thay cho số frame; (3) tỉ lệ nhắm của cú gục không tính khoảng hở dài cho frame đứng sau nó
  - Việc 9 của `improvements.md` (rút `rise_confirm_s`): ở vòng lặp chậm cảnh báo vốn đã trễ thêm tới hai khoảng frame (0,2–0,6 s trong các ca đã thử), nên phần trễ do xác nhận không còn là phần lớn nhất
- Test: 1161 Python pass, 7 xfail (88 ca mới ở `test_m75_low_fps.py`, 8 test mới của công cụ ở `test_uta_rldd_tool.py`); ruff / format sạch; `frontend/public/py/edge_agent.zip` đóng gói lại vì `thresholds.yaml` có khoá mới. Không đổi code `edge_agent/` hay frontend, nên test frontend và e2e không chạy lại

<a id="m76"></a>

#### M76: Mắt díp rồi mới nhắm hẳn, L3 tính từ lúc nhắm (khối 7)

**Xong là thấy gì:** `pytest tests/test_edge_agent/test_m76_droop_then_shut.py`: 19 pass. Chuỗi số giả 60 km/h, ngưỡng trong YAML: EAR ở 0,6 lần mốc trong N giây rồi xuống 0,17 lần mốc: còi L3 `microsleep` 1,5 s sau khi mắt nhắm hẳn với mọi N

**Trạng thái:** Xong (08/10). Làm theo [audit-2026-10-08.md](audit-2026-10-08.md) mục 6.1 việc 10 (top 10 việc 9; A2 H2). Thêm một khoá: `drowsiness.microsleep_deep.run_gap_s` (0); không đổi ngưỡng nào đang dùng. Bản web dùng chung khối 7 nên nhận cả thay đổi này

- **Trước:** `closed_duration` chỉ khác 0 khi số frame nhắm sâu đạt `microsleep_deep.min_frac` (50 %) số frame của **cả đợt nhắm**, tính từ lúc EAR xuống dưới 0,65 lần mốc. Cờ trễ giữ đợt đó tới khi EAR vượt 0,75 lần mốc, nên giai đoạn mí sụp (0,5–0,75 lần mốc) nằm trong cùng đợt và làm loãng tỉ lệ: mắt phải nhắm hẳn lâu bằng thời gian đã díp thì luật mới bật. Luật này sinh ra để chặn mắt nheo (YawDD) và vẫn làm đúng việc đó
- **Sau** (`eyes.py`: `EyeClosure.closed_duration`, `_run_s`): khi phần đang đếm chưa đạt tỉ lệ, thời lượng là thời gian từ frame đầu của **chuỗi frame nhắm sâu đang chạy**. Frame "nhắm" mà không sâu kéo dài quá `run_gap_s` thì chuỗi kết thúc (mí đã nhấc lên lại). Với `run_gap_s: 0`, mọi frame của chuỗi phải nhắm sâu. Khi cả đợt đạt tỉ lệ thì đếm từ đầu đợt như cũ
  - "Nhắm sâu" của một frame không đổi: EAR ≤ 0,5 lần mốc và `eyeBlink` đồng ý, đầu cúi thì EAR ≤ 0,35 lần mốc, khối 5 thì theo ngưỡng của nó. Luật mới chỉ đổi cách **gom** các frame đó
  - Mặt nạ ngáp / nói bắt đầu lại chuỗi cùng với phần đang đếm, nên mắt nhắm lúc ngáp vẫn không tính
  - Khoảng hở quá `max_gap_s` giữa hai frame (M71) kết thúc cả đợt lẫn chuỗi
- **Gục đầu sau khi díp** (`EyeClosure.update`): phần đếm tiếp khi đầu gục (mắt không còn đọc được) trước chỉ bắt đầu khi cả đợt đạt tỉ lệ. Nay một chuỗi nhắm sâu dài từ `head_drop.carry_min_closed_s` (0,5 s) cũng bắt đầu được. Mí sụp 4 s, nhắm 0,8 s, rồi đầu gục: trước không có L3, nay L3 1,5 s sau khi nhắm
- **Chuỗi của audit** (EAR 0,6 lần mốc trong N giây, rồi nhắm hẳn 12 s; 30 FPS):

| Díp trước khi nhắm | L3 sau khi nhắm hẳn, trước | Sau |
|---:|---:|---:|
| 0 s | 1,5 s | 1,5 s |
| 0,6 s | 0,9 s (cả 0,6 s díp được đếm) | Không đổi |
| 2 s | 2,0 s | 1,5 s |
| 4 s | 4,0 s | 1,5 s |
| 10 s | 10,0 s | 1,5 s |
| 30 s | Không có trong 12 s | 1,5 s |

- **Chọn `run_gap_s`** (in ra màn hình, `eval/results` không bị ghi, **tập giữ riêng không được đọc**; khối 5 quyết định lại từ đầu vào đã ghi). "Chuỗi nhắm sâu" là các frame liên tiếp mà chính khối 7 gọi là nhắm sâu, dài từ `risk.microsleep_l3_s`; "đúng lúc" là `closed_duration` đạt 1,5 s trong 1,6 s đầu của chuỗi:

| `run_gap_s` | Chuỗi có L3 đúng lúc, video `10` dev | Báo sai nhánh buồn ngủ, video `0` dev, cả video | YawDD: microsleep sai | Bản tự ghi: cảnh báo không khớp nhãn | FL3D: sự kiện microsleep sai |
|---:|---:|---:|---:|---:|---:|
| −1 (tắt, như M75) | 45 / 50 | 8 | 4 | 32 | 4 |
| **0** | **47 / 50** | **8** | **4** | **32** | **4** |
| 0,1 | 47 / 50 | 9 | 4 | 32 | 4 |
| 0,2 | 47 / 50 | 9 | 4 | 32 | 4 |
| 0,4 | 47 / 50 | 10 | 5 | 33 | 5 |

  Nới `run_gap_s` không cứu thêm chuỗi nào mà thêm báo sai (một L3 ở giây 20–21 của người F2_S15, rồi YawDD và bản tự ghi), nên chọn 0
- **Ở `run_gap_s: 0`, so với trước** (cùng các lệnh của M70: `tools/uta_rldd.py report --split dev`, `tools/seq_eval.py fl3d|yawdd|sust --replay block5`, `tools/record_trace.py report --traces data/own_traces/quan_v2.pkl`, mỗi lệnh thêm `--set drowsiness.microsleep_deep.run_gap_s=…`):
  - UTA-RLDD dev, video `10`: hai chuỗi được thêm là của người F2_S18 (1,75 s sau 3,25 s díp và 4,25 s sau 1,75 s díp), đúng hai chuỗi audit nêu. Ba chuỗi còn lại nằm trong mặt nạ ngáp / nói. Người có cảnh báo 14 / 24, đạt L3 12 / 24, AUC: không đổi
  - UTA-RLDD dev, video `0`: báo sai nhánh buồn ngủ sau 30 s đầu 7 (1,8 / giờ), cả video 8, mọi nhánh 12: không đổi. Không có chuỗi nhắm sâu nào từ 1,5 s trên video `0`
  - UTA-RLDD dev, video `5`: 9 / 12 đúng lúc, không đổi (3 chuỗi trong mặt nạ)
  - FL3D: 34 / 34 chuỗi đúng lúc ở cả hai; bảng cảnh báo L1 / L2 / L3 không đổi một số nào; sự kiện `microsleep` 145 → 146, lần thêm rơi vào nhãn buồn ngủ khác, không phải frame `alert`
  - YawDD: báo cáo không đổi một số nào. SUST: không cảnh báo nào đổi
  - Bản tự ghi (12 phiên, 72 phút, có phiên nhìn xuống): báo cáo không đổi một số nào; 67 chuỗi nhắm sâu, đúng lúc 66 → 67 (một lần ở `day_phone` trễ 0,17 s nay đúng lúc)
- **Cổng chất lượng:**
  - Với `run_gap_s: -1` code đi đúng đường cũ (chuỗi không được dùng ở đâu); dòng "tắt" của bảng trên là số trước mốc này
  - Test hồi quy trace (36 video) không phải chốt lại
  - 2 test có bản đối chứng chạy lại luật cũ bằng khoá mới và thấy đúng số của audit; 8 test giữ phía báo sai: chỉ díp 20 s, chuỗi nhắm ngắn hơn 1 s, mí lên xuống 0,5 s / 0,2 s, frame nhắm sâu lẻ, ngáp, cúi nhìn xuống, EAR sập mà `eyeBlink` không đồng ý
- **Chưa làm / còn hở:**
  - Hai người còn lại của audit (41: nhắm 5,7 s sau 13 s díp; 35: trễ 0,6 s) thuộc tập giữ riêng, không đọc trong mốc này. Luật mới về nguyên tắc phủ cả hai, chưa có số
  - Chuỗi bị mặt nạ ngáp / nói che (3 trên video `10`, 3 trên video `5` của dev; ngủ há miệng L3 sớm nhất khoảng 11 s) là phần còn lại của A2 H2: chưa đụng, vì gỡ mặt nạ là đúng chỗ YawDD đang được giữ
  - Bằng chứng mỏng: phần được thêm trên dữ liệu thật là 2 chuỗi của 1 người. Dữ liệu diễn (FL3D, bản tự ghi) không có kiểu mí sụp dần; người ngồi trước laptop không phải lái xe
  - `run_gap_s: 0` đòi mọi frame của chuỗi nhắm sâu: một frame EAR nhiễu vượt 0,5 lần mốc cắt chuỗi và đếm lại từ đầu. Trên dev không thấy chuỗi nào mất vì thế (0 so với 0,1–0,4 đều 47 / 50), nhưng chưa đo ở vòng lặp chậm hay camera nhiễu hơn
  - Việc 5 của `improvements.md` (nhìn xuống bị báo L3) không làm trong mốc này; luật mới không thêm L3 nào ở các phiên nhìn xuống của bản tự ghi
  - Số trong `eval/results` là của hành vi trước M74; mốc này chỉ làm lệch thêm một dòng (sự kiện microsleep của FL3D 145 → 146) và các dòng của F2_S18. Sinh lại vẫn cần anh cho phép
  - Lỗi nhỏ của audit ở `tools/uta_rldd.py` `load_trace` (numpy 2) gặp lại khi viết script đo, chưa sửa: ngoài phạm vi mốc
- Test: 1180 Python pass, 7 xfail (19 test mới ở `test_m76_droop_then_shut.py`, không test cũ nào phải sửa); ruff / format sạch; `frontend/public/py/edge_agent.zip` đóng gói lại. Không đổi code frontend, nên test frontend và e2e không chạy lại

### Vận hành (M66–)

<a id="m66"></a>

#### M66: Deploy lên Railway, tự deploy khi CI pass (`.railwayignore`, `ci.yml`, `docs/deploy-railway.md`)

**Xong là thấy gì:** merge vào `main` → job `python`, `frontend`, `e2e` pass → job `deploy` đưa bản mới lên Railway; một job fail thì không deploy

**Trạng thái:** Giai đoạn A xong (07/10, repo). Giai đoạn B xong (08/10): release `models-v1`, cấu hình Railway (volume `/app/data`, `DG_JWT_SECRET`, domain), secret `RAILWAY_TOKEN` + variable `RAILWAY_SERVICE` trên GitHub, lần deploy tay đầu tiên thành công (08/10 lúc 00:09, service `driveguard` Online). Chưa làm: lần tự deploy đầu tiên từ job `deploy` của CI và kiểm tra trên bản thật (giai đoạn C)

- **Sửa build trên Railway (08/10):** stage `webpy` của `Dockerfile.railway` chạy `tools/build_web_py.py`, file này đọc dấu vân tay model qua `edge_agent.version` → `edge_agent.config` (cần `yaml`). Thiếu `pyyaml` nên ba lần deploy tay đầu tiên fail với `ModuleNotFoundError: No module named 'yaml'`; nay stage này cài `pyyaml>=6.0`
- **Gộp `main` (M67 của nhánh DAQuan):** chỉ đụng `docs/roadmap.md` (cả hai cùng thêm mục mới); sau khi gộp: 980 Python + 138 frontend pass, `ruff` sạch, `vite build` chạy được (e2e để CI chạy)
- **Model không tới được build:** `Dockerfile.railway` chép `models/face_landmarker.task` và `models/yolov8n.onnx`, nhưng `.railwayignore` cũ bỏ cả `models/`, và `railway up` mặc định còn bỏ mọi thứ trong `.gitignore` (có `models/*.task`, `models/*.onnx`). Nay deploy chạy `railway up --no-gitignore`; `.railwayignore` tự liệt kê mọi thứ không được gửi (`.env*`, database, log, `data/`, `.ai-log/`, `.claude/`, model không dùng, `node_modules`, ...)
- **Job `deploy`** trong `.github/workflows/ci.yml`: chỉ khi push lên `main`, `needs: [python, frontend, e2e]` (job `template` của khoá học không chặn); `concurrency` để hai lần deploy không chồng nhau; kiểm tra secret / variable trước và báo đúng cái thiếu; tải hai model từ GitHub Release `models-v1` (`gh release download`), rồi `npx @railway/cli@5 up --ci --no-gitignore --service $RAILWAY_SERVICE`. Railway tự build `Dockerfile.railway`, chỉ chuyển sang bản mới khi `/health` trả 200
- **Hướng dẫn:** `docs/deploy-railway.md` (cấu hình một lần, deploy tay, kiểm tra sau deploy, quay lui)
- **Sửa kèm:** `_error_site` (`edge_agent/web/bridge.py`) đổi `\` thành `/` trước khi cắt đường dẫn, nên test `test_a_failing_frame_names_the_error_and_its_code_location` pass cả trên Windows; trong Pyodide đường dẫn vốn là `/`, không đổi hành vi
- **Chưa kiểm:** chưa chạy job `deploy` thật (cần secret); chưa thử `railway up --no-gitignore` với `.railwayignore` mới trên Railway
- Test: 969 Python pass trên Windows (trước 968 + 1 lỗi do đường dẫn); YAML của CI đọc được, đủ 5 job; `ruff` sạch
