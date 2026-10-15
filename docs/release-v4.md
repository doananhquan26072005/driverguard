# DriveGuard — Version 4

> Bản tiếp theo của [Version 3](release-v3.md). Ghi lại [audit cả 14 khối ngày 08/10/2026](audit-2026-10-08.md) và mọi việc
> làm theo nó, từ M70 trở đi: cái gì **thêm**, cái gì **sửa**, cái gì **bỏ**, và đã kiểm chứng tới đâu. Các mục này nằm
> trong `release-v3.md` tới sáng 09/10, rồi được tách ra thành file này; nội dung từng mục giữ nguyên, chỉ đánh số lại.
> Nguyên tắc giữ nguyên: mọi xử lý hình ảnh chạy trên thiết bị hoặc trong trình duyệt, không gửi và
> không lưu ảnh khuôn mặt, chỉ gửi metadata JSON.

| | |
|---|---|
| **Phiên bản** | Version 4, dựa trên v3 (M32–M69). Chưa deploy. `APP_VERSION` trong `edge_agent/version.py` còn là `3.0.0`, chưa đổi |
| **Mã nguồn** | nhánh `DAQuan`. Audit và M70–M76 đã commit và gộp `main` (PR #21, 08/10/2026); M77–M90 đã commit và gộp `main` (PR #22, 09/10/2026). Số mốc M91 và M92–M94 chưa commit (09/10) |
| **Web đang chạy** | https://c4-app-135.up.railway.app/#/live (deploy tay 13/10 từ `main`, gồm tới M105; `/health` 200; tài khoản `taixe_demo` và `kysu_demo` đã tạo). Địa chỉ v3 cũ `driveguard-production-5093` không trả lời khi kiểm 13/10 |
| **Mốc trong lộ trình** | M70 (số liệu đúng phạm vi: báo sai nhánh buồn ngủ và mọi nhánh, nhóm theo FPS, luật chấm định trước, nhật ký đọc tập test, báo cáo FL3D / YawDD / SUST chạy lại), M71 (vòng lặp `#/live` tự hồi phục; khoảng hở giữa hai frame không còn bị nối thành một đợt), M72 (đóng các trạng thái ngừng giám sát mà không ai được báo: mặt lọt một phần khỏi khung, xe bò 1–5 km/h, nút một chạm trên HUD), M73 (ngữ cảnh quanh điểm buồn ngủ: "lái lâu" tắt được, dừng đèn đỏ không mang sang), M74 (khối 12 nhắc lại sau cooldown, leo thang đếm lại, câu hỏi hiện diện không lặp), M75 (đo hành vi dưới 15 FPS, không đổi hành vi), M76 (mắt díp rồi mới nhắm hẳn: còi L3 tính từ lúc nhắm), M77 (chặn số NaN / inf ở khối 3, 9, 11), M78 (nhánh điện thoại tự hồi phục: luồng YOLO sống qua exception, worker web có hạn chờ), M79 (nạp lại ngưỡng chỉ khi nghỉ, mẫu mỗi phút không đứt sau "Đổi tài xế"), M80 (khối 8 hiệu chuẩn lại mốc "nhìn đường" bị sai, mốc tư thế khối 7 chỉ học khi xe chạy), M81 (gục đầu cần mắt nhắm sâu, một lần ngáp đếm một, MAR quy về chính diện), M82 (backend không dựa vào đồng hồ thiết bị, `trip_id` có phần ngẫu nhiên), M83 (hành khách đứng một mình không còn là tài xế, camera lặp lại một ảnh là mất camera), M84 (một lớp chặn ảnh cho thiết bị, bản web và backend; server HUD kiểm ai gọi), M85 (ngưỡng về hết `thresholds.yaml`, trang web không giữ số riêng, test chặn hardcode), M86 (vệ sinh eval: giờ của video, ghim thư viện và model, fixture cho đường web), M87 (CI trên nhánh `DAQuan`, model thật, đo FPS), M88 (bù test còn thiếu: `agent.ts`, âm thanh HUD, worker YOLO, lịch chạy của khối 1 và 4 trên đồng hồ giả), M89 (khung giờ làm mờ HUD tách khỏi khung giờ nhân điểm, bố cục cho màn hình dọc), M90 (các phát hiện Low còn lại của audit: `blink_rate`, trần cho các cấu trúc, outbox, hàng đợi web), và lần sửa tài liệu theo audit (không đánh số); xem [roadmap.md](roadmap.md), M91 (tài liệu khớp lại với code theo audit), M92 (`drowsy_score` không được nhắc lại; đêm và lái lâu cùng bật nhân tối đa 1,2), M93 (ba tỉ lệ đếm theo frame thành tỉ lệ theo thời gian), M94 (số liệu sinh lại theo code sau M71–M93), M95 (chưa từng có số đọc tốc độ thì giám sát như đang chạy), M96 (vòng lặp chậm hơn 2 FPS là không giám sát), M97 (phiên đăng nhập sống qua chuyến, lô bị từ chối chỉ mất bản ghi hỏng, gửi có hạn chờ), M98 (ảnh màu tối không còn bị nhận là hồng ngoại), M99 (runtime đóng gói vào bản build, Content-Security-Policy), M100 (ô tự xem kéo và đổi cỡ được, đóng tab giữa chuyến vẫn kết thúc chuyến, âm thanh HUD), M101 (`l1` giữ 40, quyết trên DROZY bằng luật khai báo trước), M102 (hướng dẫn sử dụng, trang `#/guide`) |
| **Tên gọi** | Trong `roadmap.md`, tiêu đề "Version 4: thiết kế lại giao diện" là tên đợt thiết kế lại M57–M65; các mốc đó thuộc [release-v3.md](release-v3.md), không thuộc file này |

---

## Có gì mới (xem nhanh)

Phần này dành cho người dùng muốn biết ngay v4 khác v3 ở đâu. Bảng đầy đủ theo từng mốc ở
[mục 1](#1-tóm-tắt-thay-đổi-so-với-v3).

- **Bản web tự chạy lại khi bị đứng**: trình duyệt ngừng đưa frame thì sau 3 giây trang tự lấy frame; camera
  rớt thì trang tự xin lại, không cần tải lại. Sau một lần đứng, hệ thống không còn hú còi vì "nhắm mắt" suốt
  quãng nó không nhìn thấy (M71).
- **Không còn lúc ngừng giám sát mà không ai biết**: mặt lọt một phần khỏi khung quá 5 giây thì màn hình báo "tạm
  ngưng giám sát · camera lệch"; xe bò 1–5 km/h mà mất mặt cũng được báo; trên màn hình không còn nút nào tắt
  hoặc che giám sát chỉ bằng một chạm, "Dừng camera" hỏi lại rồi mới kết thúc chuyến (M72).
- **"Lái lâu" tắt khi nghỉ, đèn đỏ không còn thành cảnh báo**: nghỉ từ 2 phút hoặc đổi tài xế thì thời gian lái
  liên tục về 0, cả trên màn hình lẫn trong luật; nhắm mắt nghỉ lúc dừng từ 10 giây không còn bị nhắc khi xe
  lăn bánh (M73).
- **Cảnh báo còn đó thì được nhắc lại**: nhìn khỏi đường hay cầm điện thoại kéo dài thì cứ khoảng 30 giây có
  tiếng lại, buồn ngủ nhẹ kéo dài thì khoảng 2 phút một chuông và lần thứ ba thành "Đã nhắc nhiều lần"; trước
  đây cả đợt chỉ có một tiếng, và có đợt không có tiếng nào. "Bạn còn ở đó không?" không còn hỏi dồn khi camera
  thấy mặt chập chờn (M74).
- **Ngủ gật kiểu mí sụp dần không còn bị báo trễ**: mắt díp vài giây rồi mới nhắm hẳn thì còi "Mở mắt!" đến
  1,5 s sau khi nhắm; trước đó còi trễ bằng đúng thời gian đã díp, có khi không kêu (M76).
- **Nhận diện điện thoại tự chạy lại**: một lần chạy lỗi không còn tắt nhánh điện thoại tới hết chuyến; trên bản
  web, model không trả lời quá 5 giây thì được khởi động lại, không cần tải lại trang (M78).
- **Hành khách không còn bị đọc thành tài xế**: sau đăng ký, một mặt ở xa chỗ thấy tài xế lần cuối bị bỏ qua và màn hình
  báo "tạm ngưng giám sát"; camera lặp lại một ảnh suốt 3 giây được coi là mất camera và được mở lại (M83).
- **Mốc "nhìn đường" tự sửa**: hiệu chuẩn đầu chuyến bị sai hoặc camera xê dịch thì hệ thống hiệu chuẩn lại sau 60 giây
  lái xe, thay vì kẹt cảnh báo "nhìn về phía trước" tới hết chuyến (M80).
- **Màn hình dọc và làm mờ buổi tối**: HUD có bố cục cho màn hình dọc, không phải cuộn; màn hình mờ từ 18 tới 6 giờ,
  tách khỏi khung giờ đêm dùng để nhân điểm buồn ngủ (M89).
- **Câu chữ viết lại cho tài xế**: "Kết thúc ca lái" thay "Kết thúc chuyến", "Làm quen khuôn mặt" thay "Đăng ký khuôn
  mặt", "Bạn vẫn ổn chứ?" thay "Bạn còn ở đó không?"; màn hình lỗi không còn từ kỹ thuật và nói rõ việc cần làm khi
  dừng xe (mục 3.39, 12/10).
- **Số liệu gọi đúng tên**: "0,98 báo sai / giờ" là riêng nhánh buồn ngủ; tính mọi nhánh trên cả video là 1,2 / giờ
  (cận trên 2,7), và chỉ con số này so được với chỉ tiêu PRD (M70).

---

## 1. Tóm tắt thay đổi so với v3

| Loại | Thay đổi | Mốc | Ngày |
|---|---|---|---|
| **Thêm** | Audit cả 14 khối, chỉ đọc: `docs/audit-2026-10-08.md` gộp năm báo cáo `docs/audit-1` … `audit-5` (khối 1–5, 6–8, 9–12, 13–14 và nền tảng, eval và test). 15 phát hiện High, không có Critical; mục 6.1 xếp 10 việc nên làm trước, M70–M76 là bảy việc trong đó. Không đổi code | — | 08/10 |
| **Thêm** | Báo cáo `tools/uta_rldd.py report`: bảng "đếm bốn cách" (nhánh buồn ngủ / mọi nhánh × sau 30 s đầu / cả video), bảng theo FPS của video (`eval.min_video_fps`, không loại video nào), đếm "video có cảnh báo" theo cả hai luật 30 s đầu. Mọi báo cáo `seq_eval.py` có dòng `Source:` (commit, mã băm `thresholds.yaml`, ngày file trace) và ghi "AS TRACED" khi chạy không có `--replay` | M70 | 08/10 |
| **Thêm** | `eval/splits/README.md` (luật chấm định trước: không loại video, ba cách đếm báo sai, 30 s đầu đếm hai phía) và `eval/splits/uta_rldd_test_reads.tsv`, mỗi lần chạy đọc 24 người giữ riêng tự ghi một dòng, không tắt được | M70 | 08/10 |
| **Sửa** | Số liệu cũ: `dataset_fl3d.md`, `dataset_yawdd.md`, `dataset_sust_ddd.md` sinh lại với ngưỡng 08/10 (FL3D L3 77 / 95, L1 sai 2,3 / giờ; SUST 8,8 / giờ); `report.md`, `pilot-readiness.md` (A1, A2, A3, E3, đếm tiêu chí) và `dataset_uta_rldd.md` (đầu file, mục 9) đổi theo; "0,98 báo sai / giờ" gọi đủ tên là nhánh buồn ngủ, mọi nhánh cả video là 1,2 / giờ (cận trên 2,7) | M70 | 08/10 |
| **Sửa** | Khối 7, 8, 12: hai frame cách nhau quá `max_gap_s` (0,5 s) không còn bị nối thành một đợt. Đợt nhắm mắt, ngáp, cúi đầu, nhìn lệch, mất mặt bắt đầu đếm lại; xác nhận tăng mức bắt đầu lại. Trước: chớp mắt hai đầu một lần đứng 2 s là còi L3, 7 s là `unresponsive` | M71 | 08/10 |
| **Thêm** | `#/live` canh vòng lặp của chính nó (`frontend/src/live/watchdog.ts`): callback im 3 s thì tự lấy frame bằng timer; camera kết thúc, bị `mute` hoặc đứng hình thì báo mất và tự xin lại mỗi 2 s (HUD "Lần thử N"); khoá mới `distraction.max_gap_s`, `alert.max_gap_s` | M71 | 08/10 |
| **Sửa** | Lỗi frame ở phía trang (MediaPipe, canvas) đi vào `frame_failed` như lỗi trong Python: "Lỗi xử lý" trên HUD, `agent_error` lên backend. Trước chỉ là một dòng trong console | M71 | 08/10 |
| **Sửa** | Khối 9: mặt lọt một phần khỏi khung / không có tư thế (`bad_angle`) suốt `risk.unavailable.low_quality_s` (5 s) là "tạm ngưng giám sát" với lý do đó. Trước không được tính giờ ở đâu: không đo, không báo, không giới hạn | M72 | 08/10 |
| **Sửa** | Khối 9, 10: "tạm ngưng" xét khi xe không đứng yên (`VehicleContext.rolling`, từ 1 km/h) thay cho khi đang chạy (từ 5 km/h); khối 8 giữ đồng hồ mất mặt chạy lúc xe bò. Trước: che camera ở 1–5 km/h không ai được báo | M72 | 08/10 |
| **Thêm** | Khoá `distraction.pose_hold_s` (3 s, tạm): không còn tư thế đầu thì "đang nhìn lệch" chỉ được giữ chừng đó, trước đây vô thời hạn. Số cảnh báo trên các trace hiện có không đổi | M72 | 08/10 |
| **Sửa** | HUD: "Chạy mô phỏng" và liên kết Dashboard chỉ hiện khi không có thiết bị nào đang giám sát (không bao giờ trên `#/live`); chế độ mô phỏng tự về thiết bị thật khi thiết bị kết nối; "Dừng camera" hỏi lại và kết thúc chuyến có tổng kết; rời `#/live` giữa chuyến có tiếng báo và chuyến được kết thúc | M72 | 08/10 |
| **Sửa** | Khối 10: "lái lâu" tính trên `drive_run_s`, thời gian lái từ lần nghỉ / lần "Đổi tài xế" gần nhất, cùng bộ đếm với "Lái liên tục" của HUD. Trước: tổng thời gian lăn bánh từ lúc mở app, bật rồi không tắt | M73 | 08/10 |
| **Thêm** | Khoá `context.short_stop_forget_s` (10 s, tạm): xe chạy lại sau lần dừng từ chừng đó thì bỏ PERCLOS, microsleep gom lúc dừng. Trước chỉ lần nghỉ từ 120 s mới bỏ, nên nhắm mắt ở đèn đỏ thành L1 / L2 khi lăn bánh | M73 | 08/10 |
| **Thêm** | Khoá `eval.replay_clock_hour`, `eval.replay_drive_time_s`: replay của `tools/seq_eval.py`, `tools/uta_rldd.py`, `tools/eval.py` chọn được giờ và thời gian đã lái (mặc định 12:00, 0: số cũ không đổi) | M73 | 08/10 |
| **Sửa** | Khối 12: lý do còn đó ở mức đang bật khi `cooldown_s` của nó đã hết thì được phát lại (khoá `alert.remind`, mặc định bật). Trước: đợt bắt đầu trong cooldown không bao giờ phát, mức đứng yên chỉ có một tiếng, lý do bắt đầu dưới một mức cao hơn không có tiếng riêng. **Số cảnh báo tăng**: UTA-RLDD 24 người dùng để dò 5 → 7 báo sai nhánh buồn ngủ, FL3D L2 sai 3 → 8 | M74 | 08/10 |
| **Sửa** | Khối 12: lần nhắc được đếm vào leo thang `repeated_l1`; sau mỗi lần leo thang bộ đếm của lý do đó bắt đầu lại. Trước: từ lần thứ ba mọi lần phát L1 đều ra L2 tới khi xe nghỉ | M74 | 08/10 |
| **Thêm** | Khoá `presence.back_s` (1 s, tạm), `presence.reask_after_s` (60 s, tạm): đã hỏi "Bạn còn ở đó không?" thì mặt phải hiện lại đủ lâu mới coi là trở lại, và sau một lần chạm thì chờ rồi mới hỏi lại. Trước: mặt hiện một frame mỗi 12 s là 10 lần hỏi trong 2 phút | M74 | 08/10 |
| **Thêm** | Công cụ `tools/uta_rldd.py fps` và `resample_trace` (`tools/seq_eval.py`): replay cùng các video sau khi bỏ bớt frame xuống 15 / 12 / 10 FPS, đều và không đều, mỗi tốc độ 3 lượt để thấy nhiễu; báo cáo `eval/results/fps_low_uta_rldd.md`. Khoá `eval.fps_study_rates`, `fps_study_jitter_cv` (0,3, tạm), `fps_study_repeats`, `fps_study_min_source_fps`. Chỉ đo, không đổi hành vi | M75 | 08/10 |
| **Sửa** | `tools/uta_rldd.py` `summarize`: giờ của cảnh báo và sự kiện lấy từ dấu thời gian của frame, không từ số thứ tự frame / FPS (hai cách bằng nhau trên trace gốc; cần cho trace đã bỏ frame); thêm cột khoảng cách frame `gap_p50`, `gap_p95`, `gap_max` | M75 | 08/10 |
| **Sửa** | Khối 7: mí sụp dần rồi mới nhắm hẳn thì chuỗi frame nhắm sâu được đếm từ frame đầu của chính nó (khoá `drowsiness.microsleep_deep.run_gap_s`, 0); chuỗi đó cũng mở được phần đếm tiếp khi gục đầu. Trước: còi L3 trễ bằng thời gian đã díp, hoặc không bật | M76 | 08/10 |
| **Sửa** | Số không hữu hạn (audit A1 M4, A3 L1): khối 3 bỏ mặt có landmark NaN / inf và điểm blendshape NaN (bản thiết bị và bản web, `finite_faces`, `finite_scores`); khối 9 đọc số đo NaN / inf của khối 7, 8 là 0 cho riêng số hạng đó và ghi log `driverguard.risk` một lần; trip memory không gom điểm NaN. Trước: một frame landmark NaN làm mốc mắt NaN (mắt đọc là mở), một số đo NaN làm `drowsy_score` NaN, mức 0 và bản ghi gửi backend không hợp lệ | M77 | 08/10 |
| **Sửa** | Khối 4 tự hồi phục (audit A1 M1): luồng `AsyncPhoneDetector` của bản thiết bị bắt lỗi của từng lần chạy, đếm (`errors`) và chạy tiếp; worker YOLO của `#/live` không trả lời quá `phone.web_run_timeout_s` (5 s) thì bị thay, tối đa `phone.web_restart_limit` (3) lần liên tiếp (`frontend/src/live/yoloWatch.ts`). Trước: một exception làm luồng dừng hẳn, một worker treo giữ `yoloBusy` mãi; cả hai đều tắt nhánh điện thoại tới hết chuyến. Thêm 3 khoá `phone.web_*` (tạm) | [M78](roadmap.md#m78) | 08/10 |
| **Sửa** | Nạp lại ngưỡng giữa chuyến (audit A3 M1, M5): mẫu mệt mỏi mỗi phút gửi tiếp sau "Đổi tài xế" và sau lần nạp (trước: ngừng cho tới khi bộ đếm phút mới vượt số cũ, timeline trống đúng bằng số phút đã chạy); ngưỡng mới chỉ nạp khi đang nghỉ (đỗ từ `context.rest_after_s`), không nạp ở đèn đỏ, và trip memory đi tiếp qua lần nạp (trước: mọi lần dừng dưới 1 km/h, xoá microsleep và xu hướng); phiên bản đổi mục ngoài `drowsiness`, `distraction`, `trip_memory`, `alert`, `presence`, `risk` bị từ chối cả bộ bằng `config_refused` (trước: báo `config_applied` dù phần đó không có hiệu lực). Nhãn `config_refused` trên dashboard thêm "hoặc cần mở lại ứng dụng" | [M79](roadmap.md#m79) | 08/10 |
| **Sửa** | Hai mốc "nhìn đường" của tư thế đầu (audit A2 M1, M2): khối 8 hiệu chuẩn lại khi đầu ở ngoài vùng "nhìn đường" suốt 60 s lái xe mà gần như đứng yên (trước: hiệu chuẩn 5 s đầu sai quá 30°, hoặc camera xê dịch giữa chuyến, thì L2 "nhìn về phía trước" kẹt tới hết chuyến và nhánh nhìn lệch thực tế bị tắt), kèm sự kiện mới `road_pose_recalibrated`; mốc tư thế của khối 7 chỉ học khi xe đang chạy (trước: nhìn màn hình lúc dừng dưới 10 s làm mốc cúi lệch trong khoảng 20 s đầu sau khi chạy). Hai khoá mới `distraction.baseline.recalibrate_s` (60), `recalibrate_spread_deg` (10), đều tạm | [M80](roadmap.md#m80) | 08/10 |
| **Sửa** | Gục đầu và ngáp (audit A2 M3, M4): frame "mắt nhắm" của một cú cúi phải là nhắm sâu theo phép thử đầu cúi (EAR ≤ 0,35 lần mốc kèm `eyeBlink`, hoặc điểm nhắm sâu của khối 5), trước là EAR dưới ngưỡng nhắm thường nên cúi nhìn bảng đồng hồ 1 s thành `nod`; lần ngáp đã đếm được giữ qua lúc mất mặt tới khi thấy miệng khép hoặc tối đa 8 s, trước là đếm hai; ngáp đếm trên MAR × cos(yaw), trước là miệng hé 0,37 đọc thành 0,45 khi quay đầu 35°. Thêm 2 khoá công tắc `drowsiness.nod.eyes_deep`, `drowsiness.yawn.yaw_correct` (đều bật). Đánh đổi đã đo: FL3D `nod` đúng 118 → 83, YawDD ngáp đúng 94 → 91 | [M81](roadmap.md#m81) | 08/10 |
| **Sửa** | Backend không dựa vào đồng hồ thiết bị (audit A4 M2, X7): nhịp tới sau là trạng thái hiện tại (trước: nhịp có `ts` cũ hơn bị bỏ, một nhịp `ended` mang giờ tương lai làm xe đang chạy hiện "đã kết thúc chuyến"); mục "cần chú ý ngay" tính theo giờ nhận, bỏ sự kiện đã nằm chờ trên thiết bị quá cửa sổ (`events.delay_s`); thời hạn tự xoá 60 / 365 ngày tính từ lúc nhận (`fatigue_samples.received_at` mới). `ts` của thiết bị vẫn được lưu nguyên để hiển thị | [M82](roadmap.md#m82) | 08/10 |
| **Thêm** | Backend lưu độ lệch đồng hồ của mỗi thiết bị (`device_status.clock_skew_s`); `GET /api/v1/fleet` thêm `clock_skew_s`, `clock_wrong`; tab "Đội xe" hiện nhãn "Đồng hồ thiết bị chậm / nhanh N phút"; biến `DG_CLOCK_SKEW_WARN_S` (120) | [M82](roadmap.md#m82) | 08/10 |
| **Sửa** | `trip_id` thêm 6 ký tự hex ngẫu nhiên (`trip-20261008-070509-a1b2c3`, audit A4 L1): hai chuyến cùng một giây địa phương (đồng hồ lùi, đổi múi giờ) không còn ghi đè bản tổng kết của nhau | [M82](roadmap.md#m82) | 08/10 |
| **Sửa** | Chọn mặt tài xế và camera đứng hình (audit A1 M5, M3): sau đăng ký, mặt khớp nhất vẫn bị bỏ khi tâm của nó cách chỗ thấy tài xế lần cuối quá 4 lần khoảng cách hai mắt đã đăng ký, khối 3 trả "không có mặt" (trước: một mặt đứng một mình luôn là tài xế, nên tài xế bị che mà hành khách ngủ thì ra còi L3 sai và "tạm ngưng" không chạy); ảnh camera giống hệt frame trước suốt 3 s là mất camera, được mở lại, cả bản thiết bị và `#/live` (trước: driver camera lặp frame cuối thì hệ thống thấy một mặt mắt mở đứng yên, im lặng không giới hạn). Thêm 2 khoá `landmarks.driver_max_distance` (4, tạm), `capture.frozen_stride` (8). Đo trên DROZY (14 người): chữ ký hình dạng mặt không phân biệt được người, nên ngưỡng đặt trên vị trí | [M83](roadmap.md#m83) | 08/10 |
| **Sửa** | Lớp chặn ảnh và server HUD (audit A4 M8, M6, L6): thiết bị, bản web và backend dùng chung một danh sách từ cấm và một hàm quét (`edge_agent/io/metadata_guard.py`); bản web quét mọi bản ghi trước khi trang gửi đi (trước: chỉ bản thiết bị quét, và danh sách của nó thiếu 6 từ so với backend); server HUD từ chối `Host` lạ, `POST` có `Origin` lạ và `POST` có thân không phải JSON (trước: trang web bất kỳ mở trên cùng máy kết thúc được chuyến, đổi được tài xế) | [M84](roadmap.md#m84) | 08/10 |
| **Sửa** | Ngưỡng về hết `thresholds.yaml` (audit A1 L1, A2 L5, A3 L4, A4 M7, A5 M6, X5, X8): 31 khoá mới mang đúng giá trị code đang dùng (bước lấy mẫu ảnh, mức của từng luật, nhịp và âm lượng của HUD, nhịp hỏi tín hiệu xe, ...); 6 mặc định trong code lệch YAML được sửa cho bằng YAML; HUD và `#/live` nhận số từ agent (`display` trong state, `settings()`) hoặc từ `defaults.gen.json` sinh từ YAML, không còn chép tay (trước: đổi `risk.microsleep_l3_s` thì ô "Mắt" vẫn đổi màu ở 1,5 s); bản tổng kết cắt phút theo `trip_memory.bin_s`; test mới làm đỏ CI khi có số viết thẳng trong `edge_agent/` hoặc hằng số mới trong `frontend/src/` | [M85](roadmap.md#m85) | 08/10 |
| **Sửa** | Công cụ eval (audit A5 M1, M2, H1 đã hạ; A1 L3): thời gian của video lấy từ dấu thời gian của container (trước: số thứ tự frame / FPS trung bình, nên một đoạn không có frame bị dàn đều ra cả video); `opencv-python`, `numpy`, `mediapipe`, `onnxruntime` ghim `==` (trước: `>=`, máy mới sẽ cài OpenCV 5.0); `face_landmarker.task` tải từ kênh phiên bản 1 và mọi model có sha256 (trước: kênh `latest`, không checksum); `load_trace` đọc được trace numpy 2 sau khi `edge_agent` đã nạp; trace cũ không đổi một số nào | [M86](roadmap.md#m86) | 09/10 |
| **Thêm** | Test hồi quy trace ghim thêm đường web (`eyeBlink`, cả khi mọi frame là hồng ngoại), cổng chất lượng frame và nhánh điện thoại: 8 video 3MDAD mới, mỗi video replay trên ba đường; trace ghi lại môi trường tạo ra nó (`meta`); `tools/uta_rldd.py clock` đo độ lệch giờ từng video; `tools/download_models.py --verify`; bản ghi hai phiên Kaggle vào `eval/provenance/uta_rldd/` | [M86](roadmap.md#m86) | 09/10 |
| **Thêm** | CI (audit A5 M5, M8): chạy khi push lên `DAQuan`; job mới `models` tải ba model có kiểm sha256, chạy khối 3–6 trên model thật với một khuôn mặt vẽ bằng hình học (`tools/drawn_face.py`, không phải ảnh người) và đo vòng lặp chính 90 s, đỏ khi dưới 15 FPS (`tools/benchmark.py --condition drawn_face --check`); ở job đó test model thật thiếu file thì đỏ thay vì tự bỏ qua; bốn test so với đồng hồ bấm giờ được viết lại. Chưa chạy lần nào trên GitHub | [M87](roadmap.md#m87) | 09/10 |
| **Thêm** | Test còn thiếu (audit A1 L4, A3 L5, A4 M10), không đổi code đang chạy: `agent.ts`, âm thanh của `HudScreen.tsx` và worker YOLO lần đầu có test (94 test vitest mới, trên jsdom với Python, camera, backend và đồng hồ giả); lịch chạy của khối 1 và khối 4 kiểm trên đồng hồ giả thay cho `sleep`; một fixture so số đo của trang với số đo của thiết bị trên cùng điểm ảnh (`tools/measure_fixture.py`); khối 12 với ngưỡng của YAML; hệ số đêm / lái lâu trên 44 video fixture. Bốn chỗ test nêu ra việc chưa sửa: `stop()` chờ backend mới nhả camera, lô bị bỏ cả khi 4xx, 401 kẹt hàng đợi, ảnh màu tối bị nhận là hồng ngoại | [M88](roadmap.md#m88) | 09/10 |
| **Sửa** | Khung giờ làm mờ HUD tách khỏi khung giờ nhân điểm (audit X6, A4 M9): khoá mới `hud.dim_hours` (18–6 giờ, tạm), agent gửi cờ `dim` riêng trong mỗi state; `context.night_hours` (0–5 giờ) chỉ còn nhân điểm buồn ngủ và không đổi, nên không số báo sai nào đổi. Trước: một khung giờ làm cả hai việc, HUD sáng nguyên từ chập tối tới nửa đêm | M89 | 09/10 |
| **Thêm** | HUD cho màn hình dọc (audit A4 M9): màn hình dọc rộng từ 640 px được vẽ trên stage 800 × 1 280 co theo màn hình, không phải cuộn; điểm ngắt và cỡ chữ của HUD tính theo bề rộng stage thay cho bề rộng màn hình. Trước: 800 × 1 280 tràn 64–140 px (nút "Kết thúc chuyến" dưới mép), 1 200 × 1 920 dùng bố cục ngang kéo dài | M89 | 09/10 |
| **Sửa** | Các phát hiện Low của audit (A2 L1–L3, A3 L2 / L3 / L6): `blink_rate` chia cho số giây đọc được mắt (trước: thời gian đồng hồ, thấy mắt nửa thời gian thì đọc nửa nhịp); `phone_ratio_2s` đọc 0 cho tới khi có 0,5 s kết quả YOLO trong cửa sổ; lần nhắm mắt đếm tiếp qua lúc gục kết thúc sau 30 s không thấy gì, rồi "tạm ngưng" và hỏi tài xế; `drowsy_score` đọc 0 khi nghỉ; xi nhan bật quá 30 s lái xe thì hết nới góc; độ dốc 15 phút chỉ tính lại khi một phút đóng và tính trên số phút thật | [M90](roadmap.md#m90) | 09/10 |
| **Sửa** | Outbox và hàng đợi (audit A4 L2–L5): bản thiết bị ghi outbox trên luồng gửi, không còn trên luồng của vòng lặp; file outbox chỉ chủ sở hữu đọc được; giãn cách thử lại có phần ngẫu nhiên; hàng đợi của bản web dừng ở `publisher.max_queue`; trang không còn tải gói `sqlite3`; backend trả `conflicts` cho sự kiện mang `event_id` của thiết bị khác (trước: đếm lẫn vào `duplicates`) | [M90](roadmap.md#m90) | 09/10 |
| **Sửa** | Khối 1–5 (audit A1 L5): bản web đo độ sáng và độ nét trên mặt của tài xế (trước: mặt lớn nhất); MediaPipe của trang nhận giờ chụp của frame; kết quả YOLO so với hộp mặt của frame nó chạy trên; `FrameSource.stop()` không giải phóng camera đang được đọc | [M90](roadmap.md#m90) | 09/10 |
| **Sửa** | Khối 12: `drowsy_score` không còn được nhắc lại sau cooldown (`alert.remind_skip_reasons`); các lý do khác giữ lần nhắc của M74. UTA-RLDD dev: báo sai nhánh buồn ngủ 7 → 5 (1,81 → 1,29 / giờ) | [M92](roadmap.md#m92) | 09/10 |
| **Sửa** | Khối 9: đêm và lái lâu cùng bật nhân điểm buồn ngủ tối đa `risk.drowsy.context_factor_cap` (1,2) thay cho 1,44. UTA-RLDD dev ở 02:00 sau 2 giờ lái: báo sai 11 → 5, người buồn ngủ có cảnh báo 18 → 15 / 24 | [M92](roadmap.md#m92) | 09/10 |
| **Sửa** | Lần sửa tài liệu theo audit có số mốc M91; 31 chỗ còn ngỏ của audit và M68–M90 được chốt, bảng ở [roadmap](roadmap.md#quyet-dinh-0910), các mốc đã chọn là M93–M101 | [M91](roadmap.md#m91) | 09/10 |
| **Sửa** | Khối 7, 8: `phone_ratio_2s`, tỉ lệ nhắm sâu của một đợt nhắm và tỉ lệ nhắm mắt của một cú gục tính theo thời gian thay cho số frame (audit X4). Tốc độ khung đều: không đổi, test hồi quy trace không chốt lại. Vòng lặp "giật": cú gục không còn bị đọc thành `bow` | [M93](roadmap.md#m93) | 09/10 |
| **Sửa** | Số liệu sinh lại theo code sau M71–M93: FL3D, YawDD, SUST, vòng lặp chậm; `dataset_uta_rldd.md` mục 10; `report.md`, `pilot-readiness.md`. Tập giữ riêng của UTA-RLDD đọc một lần. Số đếm cảnh báo trên UTA-RLDD không đổi | [M94](roadmap.md#m94) | 09/10 |
| **Sửa** | Khối 10: chưa từng có số đọc tốc độ và camera đã thấy tài xế 30 s (`context.vehicle_signal_wait_s`) thì tốc độ là không rõ, giám sát như đang chạy, tài xế và backend được báo; trước là "đỗ" cả chuyến, không cảnh báo nào (audit phát hiện 1). Đăng ký không bị đếm | [M95](roadmap.md#m95) | 09/10 |
| **Sửa** | Vòng lặp dưới 2 FPS suốt 5 s: HUD hiện "tạm ngưng giám sát" với lý do mới `slow_loop`, backend nhận `monitoring_unavailable`, nhịp "còn sống" báo `unavailable`; trước vẫn báo "đang giám sát" dù không luật thời lượng nào chạy được | [M96](roadmap.md#m96) | 09/10 |
| **Thêm** | Backend: `POST /auth/refresh`, token còn hạn đổi lấy token mới; `#/live` gia hạn phiên trong chuyến (trước: chuyến dài hơn 60 phút mất phần sau). Lô bị từ chối vì nội dung chỉ mất bản ghi hỏng (trước: cả lô); `POST` của trang có hạn chờ; `stop()` nhả camera trước vòng gửi cuối | [M97](roadmap.md#m97) | 09/10 |
| **Sửa** | Khối 2, 5: ảnh màu tối không còn bị nhận là hồng ngoại (độ chênh kênh phải nhỏ cả so với độ sáng, `preprocess.ir_channel_rel_max`); loại camera giữ theo thời gian (`preprocess.ir_switch_s`). FL3D làm tối (gamma 2,2): frame do CNN quyết định 45,7 → 11,2 %, mắt nhắm bắt được 27,8 → 63,9 % | [M98](roadmap.md#m98) | 09/10 |
| **Sửa** | `#/live` không còn tải code từ CDN: Pyodide và wasm của MediaPipe là file của bản build (hai gói Python tải lúc build, kiểm sha256). Backend gửi Content-Security-Policy: script chỉ từ chính origin, không `eval`, chỉ nối tới chính server và máy của tài xế | [M99](roadmap.md#m99) | 09/10 |
| **Thêm** | `#/live`: ô tự xem kéo và đổi cỡ được (trước che nút "Cảnh báo này sai?"). **Sửa:** đóng tab giữa chuyến vẫn kết thúc chuyến và gửi tổng kết; cảnh báo tới lúc bị chặn tiếng được phát với lần chạm đầu; mở HUD giữa chuyến không kêu lại cảnh báo cũ | [M100](roadmap.md#m100) | 09/10 |
| **Thêm** | `tools/drozy.py`, luật khai báo trước `eval/splits/drozy_l1_rule.md`, báo cáo `eval/results/drozy_l1.md`: `risk.drowsy.l1` 40 hay 50 trên DROZY. Kết luận theo luật: giữ 40 (0 báo sai ở cả hai giá trị; 50 mất 1 / 7 video buồn ngủ có cảnh báo). Không ngưỡng nào đổi | [M101](roadmap.md#m101) | 09/10 |
| **Thêm** | Trang `#/guide`: hướng dẫn sử dụng, 24 màn hình có thể hiện do chính HUD vẽ trên số liệu mẫu, mỗi màn hình kèm ý nghĩa và việc nên làm; các trang web theo vai trò. `HudStage` vẽ được trong một hộp (`StageFrame`) | [M102](roadmap.md#m102) | 12/10 |

---

## 2. Thêm mới

### 2.1 Audit cả 14 khối (08/10)

- Chỉ đọc và phân tích, không đổi code, config hay số liệu. Năm báo cáo theo cụm:
  [khối 1–5](audit-1-perception.md), [khối 6–8 và đăng ký](audit-2-features.md), [khối 9–12](audit-3-risk-alert.md),
  [khối 13–14, web / APK, backend](audit-4-output-platform.md), [công cụ eval, số liệu, test](audit-5-eval-tests.md);
  bản gộp [audit-2026-10-08.md](audit-2026-10-08.md) mở lại code của cả 15 phát hiện High và chạy lại test (993 pass lúc đó).
- Kết luận: phần lõi đúng thiết kế, không có Critical. Chưa sẵn sàng pilot trên xe thật vì ba khoảng trống ghép lại: sản
  phẩm không có nguồn tốc độ (chưa từng nhận tốc độ thì xe bị coi là đỗ, không cảnh báo nào); còn trạng thái ngừng giám
  sát mà không ai được báo; bằng chứng báo sai hẹp hơn tên gọi của nó.
- Bảng ràng buộc: không gửi / không lưu ảnh và chỉ gửi metadata đạt trên code của dự án (điểm hở là runtime tải từ CDN,
  không kiểm tra toàn vẹn, không CSP); 15 FPS chỉ đạt trên Mac; chống báo sai "không chắc, nghiêng về chưa đạt".
- Mục 6.1 của bản gộp xếp 10 việc nên làm trước. Đã làm: việc 1 (M70, [mục 2.2](#22-số-liệu-đúng-phạm-vi-m70)), 2 (M72, mục 3.2),
  3 (M71, mục 3.1), 5 (M73, mục 3.3), 6 (M74, mục 3.4), 7 (M75, mục 3.5), 10 (M76, mục 3.6). Chưa làm: việc 4, 8, 9,
  xem [mục 6](#6-giới-hạn-đã-biết).
- Các phát hiện Medium / Low ở mục 7 của bản gộp và các chỗ lệch xuyên cụm (mục 4): làm ở M77–M90 và lần sửa tài liệu,
  mục 3.7–3.21.

### 2.2 Số liệu đúng phạm vi (M70)

- Không đổi ngưỡng, không đổi edge_agent. Làm theo audit 08/10 ([audit-2026-10-08.md](audit-2026-10-08.md), mục 6.1 việc 1).
- **"0,98 báo sai / giờ" là báo sai nhánh buồn ngủ**, sau 30 s đầu, trên người ngồi trước laptop, không đăng ký, không cổng chất
  lượng. Cùng 24 người giữ riêng, bốn cách đếm: nhánh buồn ngủ sau 30 s 1,0 (0,27–2,5); nhánh buồn ngủ cả video 0,9; mọi nhánh
  sau 30 s 1,0; **mọi nhánh cả video 1,2 (0,38–2,7)**. Chỉ dòng cuối so với chỉ tiêu PRD. Trên 24 người dùng để dò dòng cuối là 2,5.
- 6 trong 9 lần báo sai nhánh buồn ngủ (dev + test) nằm ở 2 video dưới 15 FPS (4 video tỉnh táo dưới 15 FPS chiếm khoảng một
  phần mười số giờ). Chưa rõ do FPS; cách kiểm (bỏ bớt frame xuống 10 / 12 FPS) chưa làm.
- Luật định trước ở `eval/splits/README.md`: không video nào bị loại khỏi số chính; tập giữ riêng đã đọc nhiều lần (4 lần ghi lại
  từ tài liệu + nhật ký từ M70), nên không chốt thêm ngưỡng trên đó.
- Báo cáo FL3D / YawDD / SUST chạy lại với ngưỡng hôm nay (trace `fl3d_v2`, `yawdd_v2`, `sust_v2`, `--replay block5`): FL3D L3 đạt 77 / 95
  (cũ 75), L1 10 / 9 / 1 và 2,3 sai / giờ (cũ 9 / 7 / 2 và 4,6), L3 85 / 83 / 1; SUST 8,8 / giờ (cũ 8,5); YawDD không đổi. Mọi báo cáo
  `seq_eval.py` có dòng nguồn gốc ở đầu. `seq_eval.py fl3d` không có `--replay` giờ ghi rõ là số lúc trace.
- `pilot-readiness.md`: đếm lại tiêu chí (4 đạt, 9 một phần, 5 chưa đạt, 5 chưa đo, 1 số xấp xỉ), A2 theo `own_recordings.md`
  (38 / 59 lần nhắm mắt có cảnh báo, 64 %, p95 2,03 s), ghi thẳng các tiêu chí không còn đường đạt.
- Chi tiết: [roadmap M70](roadmap.md#m70).

---

## 3. Sửa đổi

### 3.1 Vòng lặp `#/live` tự hồi phục; khoảng hở giữa hai frame không phải một đợt (M71)

Trước: vòng lặp bản web chỉ chạy khi trình duyệt gọi `requestVideoFrameCallback`. Im thì trang đứng tới khi có người tải
lại (M67: 2 trên 4 lần chạy 10 phút); camera kết thúc không được mở lại; lỗi phía trang chỉ vào console. Khi frame quay lại,
khối 7, 8, 12 đo thời lượng bằng hiệu hai dấu thời gian, nên hai frame nhắm mắt hai bên một lần đứng 2 s thành một lần nhắm
2,1 s (L3), 7 s thành `unresponsive` (báo quản lý ngay); liếc 0,2 s, đứng 3 s, liếc 0,6 s thành L2 `off_road`.

Nay:

- Hai frame cách nhau quá `max_gap_s` (0,5 s; `drowsiness`, `distraction`, `alert` mỗi phần một khoá) thì mọi đợt đang đếm
  kết thúc ở đó, không được tính, và bắt đầu lại từ frame vừa thấy. Bốn chuỗi trên không còn cảnh báo. Mắt vẫn nhắm sau khi
  frame quay lại thì L3 sau 1,5 s kể từ lúc thấy lại. Hở dưới 0,5 s và vòng lặp 5–12 FPS không đổi.
- Trang canh vòng lặp: không có frame mới trong `capture.frame_timeout_s` (3 s) khi trang ở trước mặt thì tự lấy frame bằng
  timer. Kéo vẫn không có frame, track bị `mute`, hoặc track kết thúc: "Mất camera", xin lại camera mỗi
  `capture.reconnect_interval_s` (2 s), giám sát lại khi có frame.
- Lỗi phía trang đi cùng đường với lỗi trong Python (M28): "Lỗi xử lý" sau 1 s, `agent_error`, tự hết khi frame tốt.

Kiểm chứng: báo cáo replay của FL3D, YawDD, SUST, UTA-RLDD dev và bản tự ghi giống hệt trước và sau (các trace không có
khoảng hở dài); e2e chạy cả ba đường trên bản build thật. Chạy 10 phút bản build thật ở hai cấu hình: đạt cả hai (20,0 FPS mọi phút với camera giả 20 FPS), không lượt nào bị đứng nên đồng hồ canh chưa được thử bằng một lần đứng thật. Đánh đổi: đợt nhắm mắt đang được giữ qua gục
đầu cũng kết thúc ở khoảng hở; tab bị che thì không kéo frame (vẫn báo `stalled`). Chưa thử webcam thật, Android WebView.
Chi tiết: [roadmap M71](roadmap.md#m71).

### 3.2 Không còn trạng thái ngừng giám sát mà không ai được báo (M72)

Audit 08/10 (mục 6.1 việc 2) chỉ ra ba đường hệ thống không đo gì mà vẫn báo "đang giám sát". Cả ba được đóng:

- **Mặt lọt một phần khỏi khung** (`bad_angle`): trước đây không khối nào tính giờ nó. Nay sau 5 s
  (`risk.unavailable.low_quality_s`) là "Tạm ngưng giám sát · camera lệch", có tiếng báo và sự kiện
  `monitoring_unavailable` (cause `bad_angle`). Đợt nhắm mắt đang giữ qua gục đầu vẫn được giám sát.
- **"Đang nhìn lệch" bị giữ vô thời hạn** khi không còn tư thế đầu: nay tối đa `distraction.pose_hold_s` (3 s, tạm)
  kể từ tư thế cuối; quay hẳn ra sau giữ thời hạn riêng 10 s (M38). Thử 1–2 s trên trace thì mất 4–5 trong 12 cảnh
  báo nhìn lệch có chủ đích của bản tự ghi, nên chọn 3 s: số cảnh báo trên các trace hiện có không đổi.
- **Xe bò 1–5 km/h**: "tạm ngưng" và câu hỏi "Bạn còn ở đó không?" chạy từ 1 km/h (`rolling`). Luật nhìn lệch và điện
  thoại vẫn tắt dưới 5 km/h; đứng yên vẫn không báo gì.
- **HUD**: không còn nút một chạm nào tắt hoặc che giám sát. "Chạy mô phỏng" và Dashboard chỉ hiện khi `#/hud` chưa nối
  được thiết bị; "Dừng camera" của `#/live` mở hộp "Kết thúc chuyến đi?" và kết thúc chuyến có tổng kết; rời trang giữa
  chuyến thì có tiếng "Hệ thống đang không giám sát bạn" và chuyến được kết thúc, không còn thành "Mất liên lạc".

Kiểm: replay FL3D / YawDD / SUST / 3MDAD / bản tự ghi trước và sau giống hệt; UTA-RLDD dev không đổi số cảnh báo,
bảng cửa sổ 10 s lệch 1–2 cửa sổ (một cửa sổ L3 của video buồn ngủ thành "tạm ngưng"). Không trace nào có mặt lọt một
phần từ 5 s, nên luật `bad_angle` mới được chứng minh bằng chuỗi số giả. Chưa xử lý: đóng tab / tải lại trang giữa
chuyến; HUD chưa nhắc gì trong 5 s đầu. Chi tiết: [roadmap M72](roadmap.md#m72).

### 3.3 "Lái lâu" tắt được; dừng đèn đỏ không mang sang lúc chạy (M73)

Audit 08/10 (mục 6.1 việc 5) chỉ ra hai chỗ ngữ cảnh làm tăng báo sai. Cả hai được sửa, và replay nay đo được chúng:

- **Lái lâu**: trước đây đọc tổng thời gian xe lăn bánh từ lúc mở app, nên sau 2 giờ hệ số ×1,2 bật mãi, kể cả sau
  khi nghỉ và với tài xế vừa nhận xe, trong khi HUD hiện "Lái liên tục" bằng bộ đếm khác. Nay khối 10 đếm
  `drive_run_s` (về 0 khi nghỉ từ `context.rest_after_s` và khi "Đổi tài xế"); luật và HUD đọc cùng số đó.
- **Dừng ngắn**: xe chạy lại sau lần dừng từ `context.short_stop_forget_s` (10 s, tạm, anh chốt 08/10) thì bỏ phần
  khối 7 và trip memory gom từ lúc dừng. Dừng 60 s, nhắm mắt 25 s: trước là L1 sau 1,0 s lăn bánh (L2 lúc 02:00),
  nay không cảnh báo. Dừng dưới 10 s giữ nguyên; mắt còn nhắm khi xe lăn bánh vẫn là L3.
- **Replay chọn giờ**: `--set eval.replay_clock_hour=2 --set eval.replay_drive_time_s=7200`. UTA-RLDD, 24 người dùng
  để dò: 5 báo sai nhánh buồn ngủ ở 12:00, 5 ở 02:00, **11 ở 02:00 sau 2 giờ lái** (2,85 / giờ, cận trên 6,02).

Số của mọi báo cáo hiện có không đổi (replay không có lần dừng, bắt đầu từ 0 giờ lái). Đánh đổi: người ngủ gật thật ở
đèn đỏ mất phần điểm đó khi xe chạy lại. Hai hệ số nhân chồng (1,44) hay có trần: chốt 09/10, trần 1,2
([mục 3.22](#322-drowsy_score-không-được-nhắc-lại-đêm-và-lái-lâu-cùng-bật-nhân-tối-đa-12-m92)). Chi tiết:
[roadmap M73](roadmap.md#m73).

### 3.4 Cooldown giữ lại chứ không nuốt cảnh báo; câu hỏi hiện diện không lặp (M74)

Audit 08/10 (mục 6.1 việc 6) chỉ ra khối 12 làm mất cảnh báo ở ba chỗ và phạt nhầm người ở một chỗ:

- **Nhắc lại**: lý do còn đó ở mức đang bật khi `alert.cooldown_s` của nó đã hết (hoặc chưa từng phát ở mức đó) được
  phát lại sau khi giữ đủ `rise_confirm_s`. Nhìn lệch 3 s, nhìn lại 5 s, nhìn lệch 40 s: trước chỉ có tiếng đầu, nay
  có tiếng thứ hai ở giây 31. L1 đều 30 phút: trước một chuông, nay một chuông mỗi khoảng 2 phút. Điện thoại cầm
  lên trong lúc còi L3: nay có tiếng L2 `phone` khi mức hạ. L3 (cooldown 0) không được nhắc.
- **Leo thang**: lần nhắc được đếm; sau L2 `repeated_l1` bộ đếm của lý do đó bắt đầu lại. Điểm cắt ngưỡng 18 lần
  trong 40 phút: trước L1, L1 rồi 16 lần L2, nay L1, L1, L2 lặp sáu lượt.
- **Câu hỏi hiện diện**: `presence.back_s` (1 s) và `presence.reask_after_s` (60 s), cả hai là ngưỡng tạm. Mặt hiện một
  frame mỗi 12 s: trước 10 lần hỏi trong 2 phút, nay một.
- **Cái giá đo được** (in ra màn hình, không ghi `eval/results`, không đọc tập giữ riêng): UTA-RLDD 24 người dùng để
  dò, báo sai nhánh buồn ngủ 5 → 7 (1,29 → 1,81 / giờ, cận trên 3,02 → 3,90), không người mới nào bị báo sai; FL3D
  L1 sai 1 → 3, L2 sai 3 → 8 (gần hết là `drowsy_score` L2 được nhắc mỗi 30 s); YawDD, SUST không đổi.

`alert.remind: false` cho lại đúng số trước M74. Các số trong `eval/results` và `pilot-readiness.md` vẫn là số trước
M74. Chốt 09/10: giữ lần nhắc cho các lý do khác, bỏ cho `drowsy_score`
([mục 3.22](#322-drowsy_score-không-được-nhắc-lại-đêm-và-lái-lâu-cùng-bật-nhân-tối-đa-12-m92)); sinh lại báo cáo là mốc M94 của roadmap. Chi tiết: [roadmap M74](roadmap.md#m74).

### 3.5 Đo hành vi dưới 15 FPS: báo sai không tăng, độ nhạy sát mốc giảm (M75)

Audit 08/10 (mục 6.1 việc 7) hỏi hệ thống làm gì ở 10–12 FPS, vì mọi test thời gian cố định 30 FPS và thiết bị đích
ước lượng 11–14 FPS. Mốc này chỉ đo, không đổi hành vi nào:

- **Dataset**: 59 video UTA-RLDD (21 người dùng để dò) quay từ 25 FPS trở lên, replay qua khối 7–12 sau khi bỏ bớt
  frame. Báo sai nhánh buồn ngủ 5 lần khi giữ nguyên, 2–7 lần ở 10–15 FPS đều và không đều; người buồn ngủ có cảnh
  báo 12 / 19 → 12–14, đạt L3 10 → 9–11. Mỗi dòng chạy 3 lượt và dao động giữa các lượt lớn hơn chênh lệch giữa các
  tốc độ: không thấy FPS thấp làm tăng báo sai. Hai video quay dưới 15 FPS mang 6 / 9 lần báo sai vì vậy không
  giải thích được bằng số frame mà khối 7–12 nhận.
- **Chuỗi số giả**, 8 kiểu vòng lặp: không cảnh báo nào được tạo thêm; sự kiện rõ ràng (microsleep 3 s, nhìn lệch 4 s,
  điện thoại 5 s) có đúng một cảnh báo, trễ tối đa hai khoảng frame; PERCLOS theo thời gian nên không lệch.
- **Cái mất**: thời lượng bị đo ngắn đi tối đa hai khoảng frame. Nhắm mắt 1,6 s (vượt mốc L3 0,1 s) bị bỏ sót ở
  10 FPS không đều (3–4 trong 5 lần thử); sự kiện `microsleep` của lần nhắm 1,1 s cũng vậy. 7 ca như thế được ghi
  `xfail` trong `test_m75_low_fps.py`.

Chưa đo: model mặt và model mắt chạy trên máy chậm (landmark ở đây tính trên mọi frame rồi mới bỏ bớt), nhánh điện
thoại, thiết bị thật. Chi tiết: [roadmap M75](roadmap.md#m75), [fps_low_uta_rldd.md](../eval/results/fps_low_uta_rldd.md).

### 3.6 Mắt díp rồi mới nhắm hẳn: còi L3 tính từ lúc nhắm (M76)

Trước: một lần nhắm chỉ được đếm khi ít nhất nửa số frame của **cả đợt** là nhắm sâu, tính từ lúc mí bắt đầu sụp.
Kiểu ngủ gật điển hình (mí sụp dần vài giây rồi nhắm) vì vậy có còi L3 trễ bằng thời gian đã díp: díp 4 s thì còi
đến 4 s sau khi nhắm hẳn, díp 30 s thì 12 s nhắm vẫn chưa có còi. Audit 08/10 (A2 H2) đếm được 3 lần không có L3 và
1 lần trễ trên UTA-RLDD.

Sau: khi cả đợt chưa đạt tỉ lệ, chuỗi frame nhắm sâu đang chạy được đếm từ frame đầu của chính nó, nên còi đến
1,5 s sau khi mắt nhắm hẳn, díp bao lâu cũng vậy. Chuỗi đó cũng đủ để tiếp tục đếm khi đầu gục xuống. Thế nào là
một frame "nhắm sâu" không đổi; mắt nheo, nhìn xuống, ngáp vẫn không tính.

- UTA-RLDD, 24 người dùng để dò: chuỗi nhắm sâu từ 1,5 s có L3 đúng lúc 45 → 47 / 50 (ba chuỗi còn lại nằm trong lúc
  ngáp / nói). Báo sai trên video tỉnh táo không đổi (7 sau 30 s đầu, 8 cả video).
- YawDD, FL3D, SUST, 12 phiên tự ghi: không thêm cảnh báo sai nào.
- Khoá `run_gap_s` cho phép chuỗi chịu vài frame không sâu; mọi giá trị trên 0 đã thử đều thêm báo sai mà không cứu
  thêm chuỗi nào, nên để 0. −1 là luật cũ.

Chi tiết: [roadmap M76](roadmap.md#m76).

### 3.7 Số NaN không còn làm tắt nhánh buồn ngủ trong im lặng (M77)

Trước: nếu model mặt trả một toạ độ NaN ở mí mắt, EAR của frame đó là NaN và mốc mắt mở của khối 7 thành NaN chừng
nào frame đó còn trong cửa sổ, nên mắt nhắm vẫn đọc là mở. Ở khối 9, một số đo NaN làm `drowsy_score` NaN: mức 0 dù
các dấu hiệu khác đã đầy, và bản ghi gửi backend không phải JSON hợp lệ nên cả lô bị bỏ (audit 08/10, mục 4.3 chuỗi 4).

Sau: khối 3 coi mặt có toạ độ NaN / inf là không có mặt (bản thiết bị và bản web dùng chung một hàm), nên frame đó
đi đường "mất mặt" đã có. Khối 9 đọc số đo NaN / inf là 0 cho riêng số hạng của nó, ghi một dòng log, các luật khác
vẫn chạy. Trip memory không gom điểm NaN vào phút.

- Bản web, chuỗi số giả: 30 s mắt mở có một frame NaN ở giây 15, rồi nhắm 2,5 s: còi L3 (không có lớp chặn: mức 0).
- Khối 9: `perclos_60s` NaN cùng microsleep, ngáp, gục: 60 điểm, L1 (trước: điểm NaN, mức 0).
- Chi phí khoảng 2 µs mỗi frame trên Mac. Không đổi ngưỡng, không đổi số nào trên trace.
- Đây là phòng thủ: chưa thấy NaN trong trace nào, và chưa ai thấy MediaPipe trả NaN.

Chi tiết: [roadmap M77](roadmap.md#m77).

### 3.8 Nhánh điện thoại tự hồi phục (M78)

Trước: ở bản thiết bị, một exception trong một lần chạy YOLO kết thúc luồng của model; ở bản web, một worker không
trả lời để cờ "đang bận" bật mãi. Cả hai ca đều tắt nhánh điện thoại tới hết chuyến. Tài xế được báo sau khoảng 10 s
bằng chip "Không phát hiện được điện thoại" (M50), nhưng không có gì tự chạy lại (audit 08/10, A1 M1).

Sau: luồng của bản thiết bị bắt lỗi của từng lần chạy, đếm, in một dòng cho mỗi chuỗi lỗi và đi tiếp với frame sau.
Bản web canh giờ của lần chạy đang chờ: quá `phone.web_run_timeout_s` (5 s) thì dừng worker và dựng worker mới bên
cạnh vòng lặp đang chạy; tối đa `phone.web_restart_limit` (3) lần liên tiếp mà không có kết quả nào ở giữa, rồi thôi
và báo như một model không tải được.

- Thiết bị, model giả ném lỗi ở lần chạy thứ hai: luồng sống, các lần sau có kết quả (trước: `None` mãi).
- `#/live` trong Chromium, một lần chạy bị nuốt có chủ ý: đứng 5–6 s, thay 1 lần, chạy tiếp. Mọi lần chạy đều bị
  nuốt: thay 3 lần trong khoảng 20 s rồi bỏ; vòng lặp chính không chậm đi.
- Số lần thay hiện ở "Chi tiết kỹ thuật" của `#/live`. HUD không có gì mới.
- Ba khoá `phone.web_*` là tạm: chưa có lần treo thật nào được ghi lại.

Chi tiết: [roadmap M78](roadmap.md#m78).

### 3.9 Nạp lại ngưỡng chỉ khi nghỉ; mẫu mỗi phút không đứt (M79)

Trước: sau "Đổi tài xế" hoặc sau một lần nạp ngưỡng, thiết bị ngừng gửi mẫu mệt mỏi mỗi phút trong đúng số phút
chuyến đã chạy (đổi tài xế ở phút 25 thì timeline của người mới trống tới phút 51). Ngưỡng mới được nạp ở bất kỳ lần
dừng nào, kể cả đèn đỏ, và lần nạp xoá những gì hệ thống đang nhớ về tài xế. Thiết bị báo `config_applied` kể cả khi
một phần của phiên bản không có hiệu lực (audit 08/10, A3 M1 và M5).

Sau:

- Mẫu mỗi phút đi tiếp: 60 phút lái có đổi tài xế ở phút 25,2 cho 59 mẫu (trước 34).
- Ngưỡng mới chờ tới lần nghỉ (xe đỗ từ 120 s). Microsleep và xu hướng mệt từ trước lần nghỉ vẫn được nhớ qua lần nạp.
- Phiên bản đổi một mục mà chuyến đang chạy không nhận được (`context.*`, `quality.*`, `hud.*`, ...) bị từ chối cả
  bộ: `config_refused`, số phiên bản báo về giữ nguyên. Nó được áp ở lần mở app sau.
- Dashboard hiện chỉ cho sửa 16 khoá thuộc bốn mục nạp được, nên với dashboard hôm nay đường từ chối không chạy.
- Xe không đỗ đủ 120 s trong chuyến thì chạy bộ cũ tới hết chuyến.

Chi tiết: [roadmap M79](roadmap.md#m79).

### 3.10 Mốc "nhìn đường" tự sửa khi bị sai; khối 7 không học lúc dừng (M80)

Trước: tài xế chưa đăng ký mà nhìn sang bên hơn 30° trong phần lớn 5 s đầu xe chạy (ra khỏi chỗ đỗ, nhập làn) thì hệ
thống lấy hướng đó làm "nhìn đường". Từ đó mọi lúc nhìn thẳng đều là "nhìn lệch": HUD đứng ở L2 "Nhìn về phía trước"
tới hết chuyến (từ M74 kèm một lần nhắc mỗi 30 s), và một lần nhìn lệch thật không được báo riêng. Camera hoặc ghế xê dịch hơn 30° giữa chuyến cũng
vậy, kể cả đã đăng ký. Riêng khối 7 (buồn ngủ) học tư thế đầu cả lúc xe dừng, nên nhìn màn hình ở một lần dừng ngắn
làm ngưỡng gục đầu lệch trong khoảng 20 s đầu sau khi chạy (audit 08/10, A2 M1 và M2).

Sau:

- Đầu ở ngoài vùng "nhìn đường" suốt 60 s lái xe, gần như đứng yên, không một lần nhìn lại vào vùng: tư thế đó thành
  mốc mới, cảnh báo L2 hết, backend nhận `road_pose_recalibrated` (dashboard: "Hiệu chuẩn lại hướng nhìn đường").
- Chuỗi số giả 10 phút, nhìn sang 40° trong 6 s đầu: L2 ở 9,7 % số frame và 2 cảnh báo (trước 98,7 %, 20 cảnh báo).
  Sau khi tự sửa, nhìn lệch thật 10 s lại được báo.
- Không học nhầm: nhìn lại đường 0,3 s là đếm lại từ đầu; đầu cúi mà mí hạ (nhìn điện thoại trên đùi) không được
  tính; đầu không đứng yên thì không tính; xe dừng thì bộ đếm tạm dừng.
- Khối 7 chỉ học tư thế khi xe chạy từ 5 km/h: đã đăng ký, nhìn màn hình 12° lúc dừng 8 s, mốc cúi giữ 0,0 (trước 12,0).
- 23 giờ trace hiện có (2571 trace): 0 lần hiệu chuẩn lại, cảnh báo không đổi.
- Hai khoá mới là tạm: chưa có chuyến thật nào bị hiệu chuẩn sai để chỉnh theo. Ca kẹt vẫn cho 2 cảnh báo L2 sai
  trước khi tự hết.

Chi tiết: [roadmap M80](roadmap.md#m80).

### 3.11 Gục đầu cần mắt nhắm sâu; một lần ngáp đếm một; MAR quy về chính diện (M81)

Trước: một cú cúi được tính là gục đầu (`nod`) khi mắt "nhắm" ít nhất 30 % thời gian cúi, và "nhắm" là EAR dưới
ngưỡng nhắm thường. Cúi nhìn thì mí hạ theo, EAR còn khoảng nửa mốc, nên cúi nhìn bảng đồng hồ 1 s cũng là `nod`. Một
lần ngáp bị tay che hoặc ngửa đầu làm mất mặt hơn 0,5 s thì được đếm hai. MAR tăng khi quay đầu: miệng hé 0,37 đọc
thành 0,45 (ngưỡng ngáp) ở 35° (audit 08/10, A2 M3 và M4).

Sau:

- Frame "nhắm" của cú cúi phải là nhắm sâu, cùng phép thử với `closed_duration` khi đầu cúi. Cúi nhìn 20° trong 1 s
  với EAR 0,6 và 0,5 lần mốc: `bow` thay vì `nod`.
- Lần ngáp đã đếm được giữ qua lúc mất mặt tới khi thấy miệng khép, tối đa 8 s từ lúc miệng mở. Há 2 s, mất mặt
  0,6 s, há tiếp 2,4 s: 1 `yawn` (trước 2).
- Ngáp được đếm trên MAR × cos(yaw), yaw so với camera. Mặt nạ ngáp / nói vẫn dùng MAR gốc (sửa cả mặt nạ thì trên
  trace có thêm báo sai).
- Đánh đổi đã đo trên trace có sẵn: FL3D `nod` đúng 118 → 83, `nod` sai 1 → 0, mất 1 cảnh báo L1 đúng và 1 L2 đúng,
  L3 và số cảnh báo sai không đổi; YawDD `nod` sai 5 → 2, ngáp đúng 94 → 91 trong 114; UTA-RLDD dev không đổi (7 lần
  báo sai, 14 / 24). Luật "ngáp đếm một" không đổi số nào trên ba tập.
- Hai khoá công tắc mới, đều bật: `drowsiness.nod.eyes_deep`, `drowsiness.yawn.yaw_correct`.

Chi tiết: [roadmap M81](roadmap.md#m81).

### 3.12 Backend không dựa vào đồng hồ thiết bị; `trip_id` có phần ngẫu nhiên (M82)

Trước: backend so `ts` do thiết bị ghi với giờ của nó ở ba chỗ. Android box không có pin giữ giờ, chưa đồng bộ lúc
khởi động, cho ra đúng ba ca audit đã thử (08/10, A4 M2): nhịp `ended` mang giờ tương lai làm xe đang chạy hiện "đã
kết thúc chuyến"; đồng hồ chậm 10 phút thì L3 `unresponsive` vừa nhận không lên mục "cần chú ý ngay"; sự kiện mang
năm 1970 bị xoá ngay lần dọn đầu tiên. `trip_id` là giờ địa phương tới giây nên có thể trùng (A4 L1).

Sau:

- Nhịp tới sau là trạng thái hiện tại (thiết bị chỉ gửi nhịp mới nhất, không xếp hàng).
- "Cần chú ý ngay" tính theo giờ nhận. L3 cũ từ hàng đợi offline vẫn không khẩn: backend lưu thời gian sự kiện nằm
  chờ trên thiết bị (`delay_s`, đã trừ sai số đồng hồ đo từ nhịp).
- Thời hạn tự xoá tính từ lúc backend nhận.
- Độ lệch đồng hồ của từng xe được lưu và hiện ở tab "Đội xe" khi quá `DG_CLOCK_SKEW_WARN_S` (120 s). Không lô nào
  bị từ chối vì giờ lệch.
- `trip_id`: `trip-<ngày>-<giờ>-<6 hex ngẫu nhiên>`.
- Giờ hiển thị của từng cảnh báo, thứ tự danh sách và việc lọc theo ngày vẫn là giờ thiết bị ghi.

Database cũ được thêm cột lúc khởi động (`delay_s`, `clock_skew_s`, `fatigue_samples.received_at`).

Chi tiết: [roadmap M82](roadmap.md#m82).

### 3.13 Hành khách đứng một mình không còn là tài xế; camera lặp lại một ảnh là mất camera (M83)

Trước: sau đăng ký, khung chỉ có một mặt thì mặt đó là tài xế, ở đâu cũng vậy. Tài xế bị che (điện thoại giơ trước
mặt, tấm chắn nắng) mà còn thấy hành khách thì mắt của hành khách thành mắt của tài xế: hành khách ngủ là còi L3 sai,
và "tạm ngưng giám sát" không chạy. Camera mà driver giao lại mãi frame cuối thì không lỗi đọc nào xảy ra, hệ thống
thấy một khuôn mặt mắt mở đứng yên và im lặng (audit 08/10, A1 M5 và M3).

Sau:

- Đã đăng ký: mặt khớp nhất vẫn bị bỏ khi tâm của nó cách chỗ thấy tài xế lần cuối quá
  `landmarks.driver_max_distance` (4 lần khoảng cách hai mắt đã đăng ký, khoảng 0,3–0,4 chiều ngang ảnh). Khối 3 trả
  "không có mặt", nên khi xe chạy là "tạm ngưng: không thấy mặt" rồi câu hỏi "Bạn còn ở đó không?". Chỗ thấy tài xế
  lần cuối đi theo tài xế từng frame; mặt bị loại không dời nó.
- Ngưỡng đặt trên **vị trí**, không trên điểm tổng như audit đề xuất. Đo trên DROZY (14 người, 5,6 giờ): chữ ký hình
  dạng của người lạ gần mốc ngang với chính tài xế ở ngày khác (p50 0,62 so với 0,57), nên không ngưỡng nào trên
  điểm tổng loại được hành khách. Tâm mặt tài xế thì xê dịch nhiều nhất 3,0 so với lúc đăng ký và 1,8 qua một
  khoảng mất mặt.
- Ảnh camera được so với frame trước trên mỗi điểm ảnh thứ `capture.frozen_stride` (8). Giống hệt suốt
  `capture.frame_timeout_s` (3 s): `camera_lost`, frame không vào vòng lặp, camera được mở lại như khi mất hẳn; chỉ
  một ảnh khác mới là `camera_restored`. Ảnh một màu (che kín ống kính) không tính, bước chất lượng lo ca đó. Bản
  thiết bị và `#/live` cùng luật.
- Chuỗi số giả: tài xế bị che, hành khách nhắm mắt ở ghế bên 4 s khi xe chạy cho "tạm ngưng", mức 0 (trước: L3
  `microsleep`). `#/live` trong Chromium với video chiếu một canvas đứng yên: `camera_lost` sau 3 s, tự xin lại camera.
- Còn hở: người khác ngồi vào đúng chỗ tài xế, hoặc hành khách trong vòng 4 lần khoảng cách hai mắt, vẫn được đọc
  là tài xế. Giá trị 4 là tạm: chưa có bản ghi hai người trong xe.

Chi tiết: [roadmap M83](roadmap.md#m83).

### 3.14 Một lớp chặn ảnh cho thiết bị, bản web và backend; server HUD kiểm ai gọi (M84)

Trước: chỉ bản thiết bị quét bản ghi trước khi gửi; bản web giao thẳng cho trang, nên một payload sai sẽ rời máy rồi
mới bị backend từ chối. Thiết bị và backend mỗi bên một danh sách từ cấm, lệch nhau 6 từ. Server HUD ở `127.0.0.1`
nhận lệnh ghi từ mọi trang web đang mở trên máy và không kiểm `Host` (audit 08/10, A4 M8, M6, L6).

Sau:

- Một module `edge_agent/io/metadata_guard.py` giữ danh sách từ cấm (16 từ) và hàm quét; `publisher.py`,
  `bridge.py` và `backend/schemas.py` cùng gọi nó. Luật là hợp của hai bên cũ.
- Bản web quét mọi bản ghi và nhịp "còn sống" trước khi giao cho trang. Bản ghi bị từ chối thì bỏ, đếm vào
  `refused_records`, in ra console; frame không bị ảnh hưởng.
- Server HUD: `Host` phải là `127.0.0.1` hoặc `localhost` (403); `POST` có `Origin` ngoài danh sách cho phép bị từ
  chối (403); `POST /feedback`, `/vehicle` phải là `application/json` (415).
- Còn hở: chương trình không phải trình duyệt chạy trên cùng máy vẫn gọi được; `--hud-origin` nay cho cả quyền gửi lệnh.

Chi tiết: [roadmap M84](roadmap.md#m84).

### 3.15 Ngưỡng về hết `thresholds.yaml`; trang web không giữ số riêng (M85)

Trước: khoảng 30 số nằm trong code thay vì `thresholds.yaml`, phần lớn ở bản web (thời gian coi là "đứng hình", nhịp
lặp còi, âm lượng, mốc đổi màu của ô "Mắt" chép tay từ `risk.microsleep_l3_s`). Mặc định trong dataclass lệch YAML
ở 6 trường, nên xoá một dòng YAML là đổi hành vi mà không có lỗi nào. Không test nào chặn việc viết thêm một ngưỡng
vào code (audit 08/10: A1 L1, A2 L5, A3 L4, A4 M7, A5 M6, X5, X8).

Sau:

- 31 khoá mới, mỗi khoá mang đúng giá trị code đang dùng; không đổi số nào trên trace. Một giá trị đổi: bản thiết bị
  hỏi tín hiệu xe 0,25 s một lần (trước 0,2 s), chung khoá `context.vehicle_poll_s` với bản web.
- Mặc định của mọi config bằng YAML, và mọi trường phải có dòng trong YAML.
- HUD nhận 13 số của nó trong mỗi state (`display`); ngưỡng chỉnh trên dashboard tới được màn hình. Trước state đầu
  tiên trang dùng `frontend/src/lib/defaults.gen.json`, sinh từ YAML bằng `python tools/web_defaults.py`.
- Mức của các luật `microsleep`, `unresponsive`, `off_road`, `phone` và mức đích của `repeated_l1` là khoá YAML
  (0 = chỉ ghi chú). Bản tổng kết chuyến cắt phút theo `trip_memory.bin_s`.
- Thêm luật nhất quán: nhịp hỏi tín hiệu xe phải nhỏ hơn thời gian coi là mất tín hiệu; leo thang `repeated_l1` phải
  có thể xảy ra với cooldown hiện tại.
- `tests/test_edge_agent/test_m85_no_hardcode.py` (76 test) quét mọi số trong `edge_agent/` và hằng số trong
  `frontend/src/`; số nào là định nghĩa (thang 100, chỉ số landmark, mã HTTP) nằm trong danh sách kèm lý do.
- Còn hở: phía web chỉ bắt hằng số đặt tên in hoa và `?? số`; giá trị 0, 1, 2 không bị quét; `tools/` và `backend/`
  ngoài phép quét.

Chi tiết: [roadmap M85](roadmap.md#m85).

### 3.16 Vệ sinh eval (M86)

Trước: frame thứ i của một video được coi là ở giây `i / FPS`, với FPS là số trung bình của file, nên một đoạn
không có frame bị dàn đều ra cả video. Thư viện ghi `>=` và model mặt tải từ kênh `latest`, nên hai lần cài cho
hai bộ số khác nhau. Test hồi quy chỉ ghim đường thiết bị (CNN mắt), trong khi sản phẩm là trang web (`eyeBlink`);
đổi ngưỡng `blendshape_*`, `quality.*`, `phone.*` không làm đỏ test nào.

Nay: giờ của frame là dấu thời gian trong file video; bốn thư viện quyết định số đo và ba model được ghim, và mỗi
trace mới ghi lại nó được tạo bằng gì; test hồi quy replay 44 video trên ba đường (thiết bị, web, web với mọi frame
hồng ngoại), có cả cờ điện thoại và chất lượng frame.

- Đo trên 18 video UTA-RLDD có ở máy: lệch cuối video nhiều nhất 0,07 s; một video có đoạn 2,63 s không có frame.
  Replay hai video có khoảng hở bằng giờ thật: không cảnh báo nào đổi.
- Trace cũ và mọi số đã công bố không đổi. Chưa trace lại video nào bằng đồng hồ mới.
- `yolov8n.onnx` trên release `models-v1` khác sha256 với file đã đo ở máy (cùng kích thước); CI mới chỉ cảnh báo.

Chi tiết: [roadmap M86](roadmap.md#m86).

### 3.17 CI trên nhánh làm việc, có model thật và đo FPS (M87)

Trước: CI chỉ chạy khi push lên `main` / `develop` hoặc mở PR vào `main`, nên nhánh `DAQuan` không được kiểm cho tới
lúc mở PR. CI không tải model: test duy nhất chạy model thật tự bỏ qua, khối 3, 4, 5 với model thật không bao giờ
chạy, và không có bước nào đo FPS. Bốn test so thời gian thật với một ngưỡng (0,1 s, 0,5 s) hoặc tìm chuỗi `"1.5"`
trong JSON có dấu thời gian thật, nên thỉnh thoảng đỏ.

Nay: push lên `DAQuan` là CI chạy. Job mới `models` tải ba model (sha256 đã ghim), chạy khối 3–6 trên một khuôn mặt
vẽ bằng elip và đường thẳng (`tools/drawn_face.py`, dựng trong RAM, không phải ảnh người; MediaPipe thật tìm thấy
nó ở mọi frame), rồi đo vòng lặp chính 90 s và đỏ khi một phút dưới `eval.soak_min_fps` (15). Bốn test trên không
còn ngưỡng thời gian: model / backend giả bị giữ trong một lần chạy và mọi lần gọi phải trả về trong lúc đó.

- Trên Mac: lệnh đo của CI cho 138,6 FPS, mặt vẽ được tìm thấy ở 12 472 / 12 472 frame.
- FPS của CI là của máy chạy GitHub trên mặt vẽ: bắt được việc thêm model hay bước chậm vào vòng lặp chính, không
  phải FPS của màn hình xe và không đo bản web.
- Chưa push, nên job `models` chưa chạy lần nào trên GitHub.

Chi tiết: [roadmap M87](roadmap.md#m87).

### 3.18 Bù test còn thiếu (M88)

Trước: `agent.ts` (vòng lặp, gửi lô, đọc tốc độ, dừng), các hiệu ứng âm thanh của `HudScreen.tsx` và worker YOLO của
`#/live` không có test nào; ba phát hiện High / Medium của audit 4 nằm đúng vùng đó. Luồng của khối 1 và khối 4 chỉ được
test bằng `sleep` thật với khoảng chấp nhận rộng. Phép đo ảnh viết hai lần (Python, `measure.ts`) không có test so chéo.

Nay, không đổi dòng code nào đang chạy:

- **`agent.ts`, 38 test:** lớp thật trên jsdom; Python, camera, canvas, backend và đồng hồ là giả. Phủ thứ tự và chính
  sách gửi (khách, không gửi được, bị từ chối, 401, hai vòng chồng nhau, nhịp, hàng đợi đầy), nguồn tốc độ (`#/drive`,
  bộ giả lập, không có gì), dừng và kết thúc chuyến, và vòng lặp khi trình duyệt ngừng gọi, camera đứng hình / kết thúc
  / có lại, frame lỗi ở trang hoặc ở Python.
- **Âm thanh của `HudScreen.tsx`, 22 test:** mount thật, ghi lại cái gì sẽ kêu và khi nào: cảnh báo, còi L3 lặp, mất /
  có lại camera, mặt, kết nối, tín hiệu xe, câu hỏi hiện diện, đăng ký. Trả lời câu hỏi của audit: ở chế độ mô phỏng,
  thiết bị bắt đầu giám sát thì màn hình về chế độ thật trong một lần hỏi (0,3 s) và cảnh báo thật kêu.
- **Worker YOLO, 15 test:** chọn WebGPU hay wasm, và lùi về wasm lúc khởi động hoặc khi session WebGPU chết.
- **Khối 1 và khối 4:** vòng lặp của luồng chạy trong chính luồng của test trên một đồng hồ do test đẩy. YOLO chạy đúng
  mỗi chu kỳ trên frame mới nhất, không chạy bù sau khi chậm; camera mất được xin lại đúng mỗi
  `capture.reconnect_interval_s`.
- **Trang so với thiết bị trên cùng một ảnh:** độ chênh kênh bằng nhau; độ sáng lệch tới 0,23 trên thang 255; độ nét
  lệch khoảng 1 ở ảnh tối (10,4 so với 9,4, ngưỡng mờ là 3) và 1,6 % ở ảnh có vân, vì thiết bị làm tròn độ sáng từng
  điểm ảnh còn trang thì không.
- **Khối 12** với ngưỡng của `thresholds.yaml` (L3 không cooldown) và frame không đều; **hệ số đêm × lái lâu** trên 44
  video fixture: điểm ban đêm đúng bằng điểm ban ngày × 1,44 (trần 100), không luật nào khác đổi.

Test nêu ra bốn việc chưa sửa, không sửa ở mốc này: `stop()` chờ vòng gửi cuối (không có hạn chờ) rồi mới nhả camera;
lô bị từ chối 4xx bị bỏ cả lô; token hết hạn làm mọi lô kẹt sau lô đầu; ảnh màu tối bị nhận là hồng ngoại (cả trang
lẫn thiết bị).

Chi tiết: [roadmap M88](roadmap.md#m88).

### 3.19 Khung giờ của màn hình và bố cục dọc (M89)

**Khung giờ.** `context.night_hours` từng vừa nhân điểm buồn ngủ vừa làm mờ HUD. Nay màn hình có khung giờ riêng:

| Khoá | Giá trị | Quyết định |
|---|---|---|
| `context.night_hours` | `[[0, 5]]` (không đổi) | Hệ số `risk.drowsy.night_factor` trên điểm buồn ngủ |
| `hud.dim_hours` (mới) | `[[18, 6]]`, tạm | L0–L1 mờ 20 %, mặt trăng cạnh đồng hồ; `[]` = không bao giờ mờ |

State của HUD có thêm `dim`; `night` vẫn còn nhưng trang không đọc nữa. Lúc 20:00: `dim` bật, điểm bằng đúng ban ngày.

**Bố cục dọc.** Stage thứ hai 800 × 1 280 cho màn hình dọc rộng từ 640 px (điện thoại giữ bố cục co giãn). Trong stage dọc:
thẻ trạng thái nhận phần chiều cao còn lại, thanh dưới chia hai hàng, ô của màn hình sự cố xếp dọc. Điểm ngắt của HUD
(`hud-sm` / `hud-md` / `hud-lg`) và cỡ chữ (`cqw`) nay theo stage, nên stage ngang cũng đúng bản vẽ ở mọi cỡ màn hình.

Chi tiết: [roadmap M89](roadmap.md#m89).

### 3.20 Các phát hiện Low còn lại của audit (M90)

Các việc nhỏ ở khối 1, 4, 7–11, 14 và backend. Không kết quả nào của test hồi quy trace đổi.

**Đổi cách đọc số.** `blink_rate` là số lần chớp mỗi phút **dữ liệu mắt** (trước: mỗi phút đồng hồ). `phone_ratio_2s`
đọc 0 cho tới khi cửa sổ có 0,5 s kết quả YOLO. `drowsy_score` đọc 0 khi xe nghỉ. `trend_15min` tính trên số phút thật,
phút bị bỏ vẫn là một phút.

**Có trần.** Lần nhắm mắt đếm tiếp qua lúc gục: 30 s không thấy mắt lẫn đầu cúi thì kết thúc, hệ thống chuyển sang
"tạm ngưng" và hỏi tài xế. Xi nhan bật quá 30 s lái xe: hết nới góc. Danh sách microsleep, phút của bản tổng kết,
vết của một cú cúi đầu, hàng đợi của bản web: đều có giới hạn.

**Gửi dữ liệu.** Bản thiết bị ghi outbox trên luồng gửi; file outbox ở chế độ 0600; thử lại có phần ngẫu nhiên. Câu trả
lời của `POST /api/v1/events` có thêm `conflicts`.

Chi tiết: [roadmap M90](roadmap.md#m90).

### 3.21 Tài liệu khớp lại với code (M91, 09/10)

Không đổi logic, không đổi ngưỡng. Chi tiết ở [roadmap M91](roadmap.md#m91) (số mốc đặt ngày 09/10).

- **Sửa:** `docs/risk_engine_spec.md` (chữ ký `assess`, luật `unresponsive`, trọng số chớp chậm / nhướn mày là 0, `trend`
  chỉ ghi nhận, đứng yên là mức 0, ngoại lệ `turned_away`); docstring của `risk_engine.py`, `alert_manager.py`,
  `hud/hud.py`; comment trong `thresholds.yaml`; `safety-fmea.md` dòng 14, 15 và bốn liên kết gãy; `README.md`,
  `architecture_diagram.md` (APK đã bỏ 08/10, ba địa chỉ Railway đang chạy, file INT8 không dùng); `CLAUDE.md` (khối 5 chạy
  sau khối 6, nghĩa của `face_conf`).
- **Sửa trên giao diện:** chế độ "Dùng thử" của `#/live` ghi "không gửi số liệu giám sát" thay cho "không gửi gì đi" (trang
  vẫn hỏi máy chủ tốc độ xe mô phỏng).
- **Đổi thứ tự trong `improvements.md`:** tốc độ xe từ GPS lên việc 4 (độ nên làm cao) và sửa chiều hỏng: chưa từng có tốc
  độ thì khối 10 coi xe đang đỗ, không có cảnh báo nào. Việc 4–11 cũ thành 5–12. Việc 13 có điều kiện về phiên đăng nhập;
  `l1` 40 → 50 có điều kiện về dữ liệu.
- **`pilot-readiness.md`:** giai đoạn 2–4 ghi rõ không có trong kế hoạch từ 08/10 và tiêu chí nào không có đường để đạt.
- **`roadmap.md`:** ghi chú M66 nằm ở mục "Vận hành", bảng không thiếu mốc.

### 3.22 `drowsy_score` không được nhắc lại; đêm và lái lâu cùng bật nhân tối đa 1,2 (M92)

Hai chỗ M73 và M74 để ngỏ, anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 1 và 2).

- **Sửa, khối 12:** lý do trong `alert.remind_skip_reasons` (`[drowsy_score]`) không được nhắc lại sau cooldown; với lý do
  đó khối 12 chạy đúng như trước M74 (một cảnh báo cho mỗi đợt). `off_road`, `phone` và các lý do khác giữ lần nhắc của
  M74. `drowsy_score` ở L1 đều 30 phút: M74 cho 15 lần (L1, L1, L2 lặp lại), nay một chuông. Cầm điện thoại 100 s: vẫn 4
  tiếng L2.
- **Sửa, khối 9:** tích của hệ số đêm và hệ số lái lâu bị chặn ở `risk.drowsy.context_factor_cap` (1,2). Cả hai cùng bật:
  ×1,2 thay cho ×1,44. 02:00 sau 2 giờ lái, một lần nhắm 1,1 s và một lần ngáp: điểm 36, không cảnh báo (trước: 43,2 và
  L1 kéo dài 4 phút, ca của audit 08/10).
- **Số đo** (in ra màn hình, không ghi `eval/results`, không đọc tập giữ riêng): UTA-RLDD 24 người dùng để dò, báo sai
  nhánh buồn ngủ 7 → 5 (1,81 → 1,29 / giờ, cận trên 3,90 → 3,02), vẫn 14 / 24 người buồn ngủ có cảnh báo. Replay ở 02:00
  sau 2 giờ lái: báo sai 11 → 5 (2,85 → 1,29 / giờ).
- **Cái giá đo được:** ở "đêm + lái lâu", người buồn ngủ có cảnh báo 18 → 15 trên 24. Và `drowsy_score` trở lại ba ca
  mất tiếng M74 đã đóng (điểm đứng trên ngưỡng lâu, đợt bắt đầu trong cooldown, điểm vượt ngưỡng dưới một mức cao hơn);
  HUD vẫn hiện mức.
- **Test hồi quy trace** chốt lại: 2 trong 44 video (FL3D) mất đúng các lần nhắc L2 `drowsy_score` của M74.

`alert.remind_skip_reasons: []` và `risk.drowsy.context_factor_cap: 1.44` cho lại hành vi trước M92. Chi tiết:
[roadmap M92](roadmap.md#m92).

### 3.23 Ba tỉ lệ đếm theo frame thành tỉ lệ theo thời gian (M93)

Chỗ M75 đo ra và để ngỏ, anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 7): sửa hai trong ba
chỗ, không bù thời lượng bị đo ngắn.

- **Sửa, khối 8:** `phone_ratio_2s` là tỉ lệ **thời gian** của cửa sổ có điện thoại, không còn là tỉ lệ số kết quả YOLO.
- **Sửa, khối 7:** tỉ lệ nhắm sâu của một đợt nhắm (`microsleep_deep.min_frac`) và tỉ lệ nhắm mắt của một cú gục
  (`nod.eyes_closed_min_frac`) cũng tính theo thời gian.
- **Cách tính chung:** một frame đại diện cho nửa khoảng chờ trước nó và nửa khoảng chờ sau nó, nên frame đầu sau một
  quãng chậm không gánh cả quãng đó, và một chùm frame liền nhau không nặng hơn thời gian nó chiếm.
- **Ở tốc độ khung đều không đổi gì:** test hồi quy trace (44 video × ba đường) khớp bản đã chốt, không chốt lại; số
  UTA-RLDD dev giữ nguyên.
- **Ở vòng lặp không đều** (chuỗi số giả): điện thoại thấy 0,7 s đúng lúc vòng lặp chạy nhanh, 70 % số frame nhưng 35 %
  thời gian: không còn vượt mốc 60 %. Cú gục có nhắm mắt ở vòng lặp "giật": luôn là `nod` (trước: 1 / 5 lần thành `bow`).
- **Chưa thấy trên dataset:** replay UTA-RLDD ở 10–15 FPS vẫn nằm trong nhiễu giữa các lượt; trace đó không có nhánh
  điện thoại.

Không khoá mới. Các lần nhắm mắt vượt mốc dưới 0,2–0,3 s vẫn có thể bị bỏ sót ở vòng lặp chậm không đều (không bù, theo
quyết định). Chi tiết: [roadmap M93](roadmap.md#m93).

### 3.24 Số liệu sinh lại theo code sau M71–M93 (M94)

Anh cho phép ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 6): ghi đè các báo cáo và đọc tập giữ riêng
của UTA-RLDD đúng một lần. Không đổi code, không đổi ngưỡng.

- **Sinh lại bằng công cụ:** `dataset_fl3d.md`, `dataset_yawdd.md`, `dataset_sust_ddd.md`, `fps_low_uta_rldd.md`.
- **Viết thêm:** mục 10 của `dataset_uta_rldd.md`; `report.md` và `pilot-readiness.md` sửa theo.
- **UTA-RLDD: mọi số đếm cảnh báo không đổi** trên cả hai tập. Giữ riêng: 0,98 báo sai nhánh buồn ngủ / giờ (0,27–2,5),
  mọi nhánh cả video 1,2 / giờ (0,38–2,7), 15 / 24 người buồn ngủ có cảnh báo, 12 / 24 đạt L3. AUC 0,920 → 0,929.
- **FL3D:** microsleep ≥ 1,5 s đạt L3 vẫn 77 / 95; cảnh báo sai không đổi; L1 10 → 9 và L2 16 → 15, đều bớt một cảnh báo
  đúng.
- **YawDD:** ngáp 94 → 91 / 114 (recall 82,5 → 79,8 %); `nod` sai 5 → 2; cảnh báo sai / giờ vẫn 6,9.
- **Không sinh lại:** `uta_rldd_tradeoff.md`, `personalization_uta_rldd.md` (mỗi cái đọc tập giữ riêng thêm một lần),
  `own_recordings.md` và các báo cáo ảnh đơn, ánh sáng, điện thoại.

Chi tiết: [roadmap M94](roadmap.md#m94).

### 3.25 Chưa từng có số đọc tốc độ thì giám sát như đang chạy (M95)

Phát hiện 1 của audit 08/10; anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 8). Không làm GPS.

- **Sửa, khối 10:** camera đã thấy tài xế đủ `context.vehicle_signal_wait_s` (30 s, tạm) mà chưa có số đọc tốc độ nào thì
  tốc độ là không rõ thay cho 0 km/h: giám sát như đang chạy, tài xế nghe tiếng báo, backend nhận `vehicle_signal_lost`.
  Trước: trang không có bộ giả lập đứng "đỗ" cả chuyến và không có cảnh báo nào.
- **Đăng ký không bị cắt:** thời gian ở màn hình đồng ý và ba bước đăng ký không được đếm.
- **Sửa, HUD:** chip "Chưa có tín hiệu xe · giám sát như đang chạy" và dòng chân trang riêng cho ca này.
- **Đánh đổi đã chấp nhận:** mở `#/live` trên bàn mà không chạy bộ giả lập thì sau 30 s thấy mặt có cảnh báo như đang chạy.
- **Còn hở:** vẫn không có nguồn tốc độ thật; các luật cần tốc độ (trên 80 km/h, nghỉ khi dừng, xi nhan) không hoạt động
  khi tốc độ không rõ.

Chi tiết: [roadmap M95](roadmap.md#m95).

### 3.26 Vòng lặp chậm hơn 2 FPS là không giám sát (M96)

Chỗ M71 để ngỏ; anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 11).

- **Sửa:** mọi frame suốt `hud.low_fps_s` (5 s) tới muộn hơn `max_gap_s` (0,5 s, tức dưới 2 FPS) thì không luật thời lượng
  nào chạy được. Trước: HUD vẫn hiện bảng tài xế kèm chip "máy chậm", backend nhận `monitoring`. Nay: màn hình "Tạm
  ngưng giám sát: máy xử lý quá chậm", sự kiện `monitoring_unavailable` với lý do mới `slow_loop`, nhịp "còn sống" báo
  `unavailable`. Một frame tới kịp là hết.
- **Không đổi:** 2–14,5 FPS vẫn là "đang giám sát, cảnh báo có thể trễ"; một lần đứng dài rồi chạy lại không tính.

Chi tiết: [roadmap M96](roadmap.md#m96).

### 3.27 Phiên đăng nhập sống qua chuyến; lô bị từ chối chỉ mất bản ghi hỏng; gửi có hạn chờ (M97)

Audit 08/10 A4 H2 và M1; anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 12).

- **Thêm, backend:** `POST /auth/refresh` đổi token còn hạn lấy token mới. Token đã hết hạn và tài khoản đã xoá bị từ chối.
- **Sửa, `#/live`:** trang đổi token ở vòng gửi đầu rồi mỗi nửa thời hạn. Trước: chuyến dài hơn `DG_TOKEN_TTL_MIN` (60
  phút) mất mọi thứ sau đó, vì mỗi lô đều nhận 401.
- **Sửa:** lô bị từ chối vì nội dung (400 / 413 / 422) được gửi lại từng bản ghi; chỉ bản ghi hỏng bị bỏ. Trước: mất cả lô,
  tới 100 bản ghi. 403 / 404 / 429 nay được giữ và thử lại, như bản thiết bị.
- **Sửa:** mọi `POST` của trang có hạn chờ `publisher.timeout_s` (5 s); `stop()` nhả camera trước vòng gửi cuối. Trước:
  backend treo thì camera không tắt.
- **Còn hở:** mất mạng hơn nửa thời hạn token, vắt qua lúc hết hạn, thì vẫn 401 và không đăng nhập lại được giữa chuyến.

Chi tiết: [roadmap M97](roadmap.md#m97).

### 3.28 Ảnh màu tối không còn bị nhận là hồng ngoại (M98)

Audit 08/10 A1 H1 (top 10 việc 8); anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 13).

- **Sửa, khối 2:** một frame là hồng ngoại khi độ chênh giữa các kênh màu vừa dưới mốc tuyệt đối 2,0 vừa dưới 3 % độ sáng
  của khung (`preprocess.ir_channel_rel_max`, tạm). Trước: ảnh màu trong cabin tối lọt dưới mốc tuyệt đối và bị coi là
  hồng ngoại ở 98–100 % số frame, nên CNN mắt (thiết bị) hoặc `eyeBlink` (web) quyết định thay cho EAR.
- **Thêm:** loại camera được giữ theo thời gian, chỉ đổi sau `preprocess.ir_switch_s` (2 s) các frame liên tục nói khác.
- **Bản web cùng luật**, trên đúng hai số trang đã gửi sẵn.
- **Đo lại** (`lighting_transforms.md`, 8 video FL3D làm tối trong RAM): ở gamma 2,2, frame do CNN quyết định 45,7 → 11,2 %,
  mắt nhắm theo frame bắt được 27,8 → 63,9 %, microsleep đạt L3 0 → 3 / 24. Dòng ảnh xám không đổi.
- **Còn hở:** chưa đo trên webcam thật trong tối và chưa có camera hồng ngoại thật; 3 % là của một webcam.

Chi tiết: [roadmap M98](roadmap.md#m98).

### 3.29 Runtime đóng gói vào bản build; Content-Security-Policy (M99)

Audit 08/10 A4 H3 (điểm hở riêng tư duy nhất được tìm thấy); anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 14).

- **Sửa:** `#/live` nạp Pyodide và wasm của MediaPipe từ chính bản build thay cho `cdn.jsdelivr.net`. Script
  `frontend/scripts/web-runtime.mjs` chép chúng từ `node_modules` và tải hai gói numpy / pyyaml có đối chiếu sha256 với
  `pyodide-lock.json`.
- **Thêm:** backend gửi `Content-Security-Policy` ở mọi file tĩnh: script chỉ từ chính origin (không `eval`, không script
  nội tuyến), chỉ nối tới chính server và `127.0.0.1` / `localhost`.
- **Đã kiểm:** bản build thật mở dưới CSP trong Chromium với camera giả: Pyodide và MediaPipe chạy, 0 yêu cầu ra ngoài,
  0 lần CSP chặn. E2e 11 / 11 chạy dưới cùng CSP.
- **Còn hở:** trang vẫn cần chính server của nó lúc mở; bước kiểm trên trình duyệt thật chưa thành test tự động; chưa deploy.

Chi tiết: [roadmap M99](roadmap.md#m99).

### 3.30 Ô tự xem kéo và đổi cỡ được; đóng tab giữa chuyến vẫn kết thúc chuyến; âm thanh HUD (M100)

Ba chỗ M72, M88, M89 để ngỏ; anh chốt ngày 09/10 ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 15 theo ý của anh, 16, 17).

- **Thêm:** ô tự xem của `#/live` kéo được tới bất cứ đâu và có ba cỡ (112 / 176 / 264 px), nhớ vị trí trong trình duyệt.
  Trước: cố định ở góc dưới trái, che 62 % nút "Cảnh báo này sai?".
- **Sửa:** đóng tab hoặc tải lại giữa chuyến: trình duyệt hỏi lại; khi trang đi thật thì chuyến kết thúc ngay (tổng kết và
  nhịp `ended` gửi bằng yêu cầu `keepalive`). Trước: không tổng kết, đội xe thấy "Mất liên lạc" sau 90 s.
- **Sửa, âm thanh HUD:** cảnh báo và trạng thái "không giám sát" tới lúc trình duyệt còn chặn tiếng được phát với lần chạm
  đầu tiên nếu còn đúng (trước: mất hẳn); mở HUD giữa chuyến không kêu lại một cảnh báo cũ (trước: có, khi danh sách có
  đúng một cảnh báo).
- **Đã kiểm:** e2e 13 / 13, có kịch bản đóng tab với backend thật và kịch bản kéo / đổi cỡ.
- **Còn hở:** chưa thử trên màn hình cảm ứng thật; bản tổng kết lớn hơn 60 000 byte không gửi được lúc đóng tab.

Chi tiết: [roadmap M100](roadmap.md#m100).

### 3.31 `risk.drowsy.l1` giữ 40, quyết trên DROZY bằng luật khai báo trước (M101)

Câu hỏi M53 và M69 để ngỏ; anh chốt ngày 09/10 cách quyết ([bảng quyết định](roadmap.md#quyet-dinh-0910), chỗ 5).

- **Thêm:** `eval/splits/drozy_l1_rule.md` (luật, viết trước khi chạy), `tools/drozy.py`, `eval/results/drozy_l1.md`.
- **Kết quả:** DROZY (36 video hồng ngoại, 14 người, nhãn KSS) đủ điều kiện để quyết (mặt tin cậy 98,5 %, AUC 0,809). Đường
  `web`: 0 báo sai trên 2,33 giờ tỉnh ở cả 40 lẫn 50; video buồn ngủ có cảnh báo 7 / 15 ở 40, 6 / 15 ở 50.
- **Kết luận theo luật: giữ 40.** 50 không bớt được báo sai nào và mất một video. Không ngưỡng nào đổi.
- **Thấy thêm:** trên camera hồng ngoại thật, đường `eyeBlink` của bản web tách tốt hơn CNN mắt của bản thiết bị (AUC 0,809 so
  với 0,738).

Chi tiết: [roadmap M101](roadmap.md#m101).

---

### 3.32 Sơ đồ kiến trúc tổng quan dạng SVG / PNG; `ARCHITECTURE.md` viết theo code (09/10)

Chỉ đổi tài liệu, không đổi code chạy, không có số mốc.

- **Thêm:** `docs/diagrams/architecture.svg` và `png/architecture.png`: một hình gồm Frontend, Agent, Backend API, Database,
  External và mũi tên luồng dữ liệu; sinh từ `docs/diagrams/build_architecture.py` (PNG chụp bằng Chrome headless). Hình
  ghi rõ hệ thống không có LLM, LangGraph, Vector Store. Nhúng vào `README.md` (kèm mô tả ngắn) và mục 0 mới của
  `architecture_diagram.md`.
- **Sửa:** hai hình Mermaid 14 khối (README, `architecture_diagram.md` hình 1) vẽ khối 5 trước khối 6; code chạy khối 5 sau
  khối 6 và chỉ khi EAR không tin được. `architecture_diagram.md` ghi ngưỡng "tải một lần lúc khởi động"; đúng là lúc khởi
  động và mỗi 5 phút, áp khi xe nghỉ (M47, M79).
- **Sửa:** `ARCHITECTURE.md` ở gốc repo vẫn là mẫu khoá học chưa điền (vẽ LangGraph, Vector Store); viết lại theo code.
- **Sửa:** `docs/kich-ban-demo.md` phần 3 (kiến trúc) theo hình mới: mở bằng hình tổng quan năm phần, khối 5 sau khối 6,
  ranh giới "chỉ còn con số" là khối 7 (trước ghi khối 6), thêm luồng ngưỡng mỗi 5 phút.

### 3.33 Development journal và worklog thật thay cho mẫu khoá học (09/10)

Chỉ đổi tài liệu, không đổi code chạy, không có số mốc.

- **Thêm:** `docs/JOURNAL.md`: 11 mục theo ngày làm việc (24/09–09/10), mỗi mục 2–3 câu về quyết định, khó khăn, bài
  học, và một bảng tổng hợp cho slide "Challenges & Learnings". `docs/WORKLOG.md`: bảng theo ngày (ai, việc, kết quả, PR)
  và bảng 108 commit lấy từ `git log`.
- **Sửa:** `JOURNAL.md` và `WORKLOG.md` ở gốc repo vẫn là mẫu khoá học chưa điền, trong khi README đánh dấu ✅; nay chỉ
  còn một dòng trỏ sang `docs/`. Bảng Deliverables của README trỏ thẳng tới hai file mới.

### 3.34 README: ảnh chụp màn hình, chạy bằng Docker, vai trò thành viên (09/10)

Soát README theo checklist của khoá học. Chỉ đổi tài liệu.

- **Thêm** mục "Ảnh chụp màn hình" và năm ảnh ở `docs/screenshots/`: HUD L0 / L2 điện thoại / L3 (trang `#/hud-preview`,
  ẩn thanh chọn kịch bản) và hai trang dashboard (nhật ký sự kiện, timeline) trên database tạm với một chuyến mô phỏng
  gắn nhãn `simulated`. Không ảnh nào có khuôn mặt.
- **Thêm** bước "Chạy bằng Docker" với `Dockerfile.railway`. Lệnh viết theo Dockerfile, **chưa chạy thử** trên máy này
  (Docker không bật lúc viết).
- **Sửa** bảng Team: thêm họ tên và vai trò lấy từ `docs/WORKLOG.md`; họ tên của `hddung-vinai` còn trống.
- **Sửa** mục "Cấu trúc thư mục" thành dạng cây.

### 3.35 Hình của video demo: 21 clip chưa lồng tiếng (09/10)

Không đổi code chạy, không có số mốc.

- **Thêm** `presentation/demo-clips/` (chưa đưa vào git): 21 clip 1920 × 1080 (20 theo từng dòng của
  `docs/kich-ban-demo.md`, 1 cảnh thêm về các trạng thái khác của HUD lấy từ `#/hud-preview`), bản nối theo từng phần,
  bản xem trước cả video không có và có cảnh thêm (4 phút 46 giây và 5 phút) và bảng lồng tiếng
  `LOI-THOAI.md`. Phần 2 và 4 quay trên bản build production của nhánh `DAQuan` với camera thật, backend chạy trên
  database tạm; phần 1, 3, 5 là slide và hình kiến trúc.
- **Sửa** `docs/kich-ban-demo.md`: ở phần 2, cảnh nhắm mắt (L3) chuyển xuống sau cảnh điện thoại và nhìn lệch. Lý do
  đo được khi quay: sau một lần nhắm mắt 4 giây, điểm buồn ngủ (25 của microsleep + phần PERCLOS) vượt ngưỡng L1 nên
  màn hình giữ "Hãy tìm chỗ dừng nghỉ" khoảng 40 giây. Thêm ghi chú về góc quay đầu ở cảnh xi nhan (38–56°).
- **Sửa** `docs/improvements.md` việc 1: phần video chỉ còn lồng tiếng và ghép.
- **Thêm** bốn clip tuỳ chọn `6-1` … `6-4` (tối 09/10, 42,8 giây): kỹ sư chỉnh ngưỡng và áp thử một xe, trang
  "Dữ liệu của tôi" của tài xế, nhật ký truy cập của quản trị, bốn trạng thái HUD khác từ `#/hud-preview`. Lời thoại ở
  mục "Clip thêm" của `LOI-THOAI.md`; thêm cả bốn thì video quá 5 phút.

### 3.36 Tên và vị trí file nộp theo cấu trúc của khoá học (10/10)

Chỉ đổi tên và đường dẫn tài liệu, không đổi code chạy, không có số mốc.

- **Sửa** tên file: `docs/JOURNAL.md` → `docs/journal.md`, `docs/WORKLOG.md` → `docs/worklog.md`, `docs/vdeo-demo.md` →
  `docs/video-demo.md`, `ARCHITECTURE.md` (gốc repo) → `docs/architecture.md`. Ở gốc repo, `ARCHITECTURE.md`,
  `JOURNAL.md`, `WORKLOG.md` còn một dòng trỏ sang `docs/`. Các mục cũ hơn trong file này vẫn ghi tên cũ.
- **Thêm** `docs/evaluation.md`: trang lối vào trỏ tới `eval/results/report.md`, các file kết quả và bộ test; không chép
  số liệu.
- **Sửa** bảng Deliverables của README theo đường dẫn mới; video demo chuyển sang ✅.
- **Còn thiếu:** `docs/pitch-deck.pdf`. Code vẫn ở `edge_agent/`, `backend/`, `frontend/`, không ở `src/` (`src/` là code
  mẫu của khoá học).

### 3.37 Phiên bản dependency ghim cứng; docstring cho hàm public (10/10)

Theo checklist nộp bài (mục Source Code). Không đổi hành vi chạy, không có số mốc.

- **Sửa** `requirements.txt`, `requirements-dev.txt`, `requirements-template.txt`, `packaging/edge/requirements.txt`:
  mọi dòng `>=` thành `==`, lấy đúng phiên bản đang cài trong `.venv` (Python 3.12) đã chạy qua bộ test, ví dụ
  `fastapi==0.141.1`, `pydantic==2.13.5`, `pyjwt==2.15.0`, `pytest==9.1.1`, `ruff==0.16.8`. Bốn thư viện của khối 2–6
  (opencv, numpy, mediapipe, onnxruntime) đã ghim từ trước, giữ nguyên.
- **Sửa** `packaging/edge/requirements.txt`: MediaPipe ghim `0.10.21`, riêng linux/arm64 ghim `1.0.1` vì `0.10.21`
  không có wheel ở đó (cùng lý do ghi trong `Dockerfile.edge`).
- **Thêm** docstring một dòng (tiếng Anh) cho 346 hàm public còn thiếu: `backend/` 43 % → 99 %, `edge_agent/`
  55 % → 98 %, `tools/` 54 % → 95 %. Gồm cả các route của `backend/app.py`, nên mô tả hiện ở trang `/docs` (Swagger).
- **Kiểm:** `ruff check`, `ruff format --check`, 1712 test qua, 6 xfail.
- **Còn lại:** `piper-tts==1.8.0` là bản mới nhất lúc ghim, chưa chạy thử (`.venv` không cài; chỉ `tools/make_voice.py`
  dùng). Nhánh Python 3.13 (ảnh Kaggle) chưa cài thử với các phiên bản mới ghim. `Dockerfile.edge` và
  `Dockerfile.railway` vẫn tự ghi `>=` trong lệnh `pip install`. Hàm lồng trong hàm và vài hàm phụ chưa có docstring.

### 3.38 Bằng chứng đánh giá: coverage, baseline so sánh, bảng traceability (10/10)

Theo checklist nộp bài (mục Evaluation Evidence). Không đổi code của 14 khối, không đổi ngưỡng, không chạy phép đo mới
trên dataset, không đọc lại tập giữ riêng. Không có số mốc.

- **Thêm** `pytest-cov==7.1.0` vào `requirements-dev.txt` và lệnh `make coverage`. Coverage theo dòng lệnh, đo trên cả bộ
  test: `edge_agent/` + `backend/` 93,9 % (6743 dòng), `tools/` 58,8 %, tổng 77,4 %. Bảng theo gói ở `report.md` mục 4.1.
- **Sửa** `eval/results/report.md` mục 4: bảng kết quả theo bộ test thay cho hai dòng lệnh (số cũ 1643 Python / 67
  frontend đã lệch; nay 1712 pass, 6 xfail và 293 pass).
- **Thêm** `report.md` mục 2.9, so sánh với baseline từ số đã có: bốn tín hiệu đơn (AUC 0,872–0,892) so với
  `drowsy_score` (0,924) trên 24 người giữ riêng của UTA-RLDD; baseline con người 57,8 % và HM-LSTM 65,2 % của bài báo
  gốc, ghi rõ là không so trực tiếp được (3 lớp, 60 người).
- **Thêm** `docs/traceability.md`: 14 khối, ràng buộc của CLAUDE.md, FR-1 đến FR-20 và NFR-1 đến NFR-6 → file test.
- **Sửa** `docs/evaluation.md`: bảng đối chiếu checklist và lý do không dùng pass@k / RAGAS. `report.md` mục 6 có cách
  làm và bảng để điền phản hồi người dùng.
- **Còn lại:** phản hồi người dùng thật vẫn là 0 người. Chưa có số của sản phẩm thương mại, chưa có bảng so với "ngưỡng
  thô" của PRD §6, chưa tính khoảng tin cậy cho AUC. `edge_agent/main.py` và `edge_agent/hud/hud.py` ở 0 % coverage;
  FR-14 và NFR-4 không có test tự động. CI chưa chạy coverage. E2e không chạy lại.

### 3.39 Câu chữ trên màn hình viết lại cho tài xế (12/10)

Rà toàn bộ chữ và lời nói mà tài xế gặp theo bốn tiêu chí: rõ, ngắn, nói được việc cần làm, không trách người lái.
Chỉ đổi chuỗi hiển thị, file giọng nói và test; không đổi logic, ngưỡng hay key gửi lên backend. Không có số mốc.
Chưa hỏi tài xế thật nào về cách gọi mới.

- **Sửa** năm cách gọi dùng chung:
  - "chuyến" → **"ca lái"** trên HUD, bảng tổng kết, trang tài xế và trang quản lý ("Kết thúc ca lái", "Tổng kết ca
    lái", "Báo cáo ca lái"). Với tài xế công nghệ "chuyến" là một lần chở khách, còn một phiên của hệ thống có nhiều lần
    nghỉ. Tên biến, API và `trip_id` giữ nguyên.
  - Với tài xế, "giám sát" → **"theo dõi"** và gọi người lái là "bạn" ("Hiện chưa theo dõi được bạn"). Trang quản lý và
    nhật ký sự kiện vẫn dùng "giám sát".
  - "Đăng ký tài xế" / "Đăng ký khuôn mặt" → **"Làm quen khuôn mặt"**: "đăng ký" gợi ý lưu sinh trắc học, trái với cam
    kết không lưu ảnh.
  - Thang độ mệt còn một bộ: **Tỉnh táo · Hơi mệt · Rất mệt** (trước có bốn bộ khác nhau giữa các màn hình).
  - "Nhìn lệch" → **"Rời mắt (khỏi đường)"**; "báo sai" → **"báo nhầm"** ở phía tài xế.
- **Sửa** tiêu đề cảnh báo, chỉ còn hành động: L3 "Dừng xe nghỉ ngay", `unresponsive` "Tấp vào lề, dừng xe ngay!" (bỏ chữ
  hoa toàn bộ), `off_road` "Nhìn đường!", `trend` "Xong cuốc này nên nghỉ" (thay "trạm dừng tới"), `repeated_l1` "Bạn cần
  nghỉ rồi. Tìm chỗ dừng xe". Câu hỏi hiện diện thành "Bạn vẫn ổn chứ?".
- **Sửa** màn hình lỗi, bỏ từ kỹ thuật ("HUD", "edge agent", "khung hình/giây", "vòng xử lý"): "Mất kết nối với thiết bị",
  "Camera bị đứng hình", "Hệ thống gặp lỗi", "Máy đang chậm · cảnh báo có thể trễ". Việc phải dùng tay (chỉnh camera, lau
  ống kính, khởi động lại) ghi rõ "khi dừng xe". "Không phát hiện được điện thoại" → "Tạm chưa nhận biết được điện thoại"
  (câu cũ đọc được thành tin tốt). "Mất tín hiệu xe" → "Mất tín hiệu tốc độ xe".
- **Sửa** dòng ghi chú có lệnh `python -m edge_agent.main` trên màn hình mất kết nối: chỉ còn hiện ở bản dev.
- **Sửa** lỗi đăng nhập không phải sai mật khẩu: "Không đăng nhập được. Kiểm tra mạng rồi thử lại." thay cho thông báo
  lỗi thô. Hộp xác nhận xoá dữ liệu nói rõ "Xoá rồi không khôi phục được".
- **Sửa** 17 trong 31 dòng của `frontend/src/hud/voice-lines.json`.
- **Sửa** giọng đọc: từ Piper `vi_VN-vais1000-medium` sang giọng nam `vi-VN-NamMinhNeural` của Microsoft, đọc nhanh hơn 12 %
  và trầm hơn 6 Hz so với mặc định để câu cảnh báo nghe dứt khoát. Chọn bằng tai trong 9 kiểu đọc thử (ba giọng Piper,
  giọng Linh của macOS, HoaiMy, NamMinh, Google). `tools/make_voice.py` gọi qua gói `edge-tts` (`requirements-dev.txt`
  thay `piper-tts`), ghi lại cả 31 câu thành `.mp3` thay cho `.wav` (thư mục `frontend/public/voice/` từ 2,1 MB còn
  0,6 MB); `chime.ts` phát file `.mp3`. Ứng dụng vẫn chỉ phát file có sẵn, không gửi gì đi lúc chạy.
  - `edge-tts` dùng dịch vụ đọc to của Microsoft Edge, không phải API chính thức: hôm 12/10 khoảng một nửa số yêu cầu bị
    trả về rỗng, nên script thử lại tới 10 lần mỗi câu và chạy lại thì làm tiếp các câu còn thiếu. Lúc ghi cần mạng, và
    chữ của 31 câu được gửi tới Microsoft. Chưa đọc điều khoản dùng audio này trong sản phẩm; đường chính thức là Azure
    Speech (cần key).
  - Chưa ai nghe 31 file mới trong xe, và chưa đo lại khoảng cách giữa chuông và lời nói với file mới.
- **Sửa** chữ trích từ màn hình trong `HowToUse.md`, `README.md`, `docs/kich-ban-demo.md` theo chữ mới.
- **Sửa** năm ảnh ở `docs/screenshots/` của README: chụp lại bằng Playwright theo cách của mục 3.34 (HUD ở
  `#/hud-preview`, dashboard trên database tạm với một ca lái mô phỏng 5 cảnh báo, 45 mẫu theo phút).
- **Sửa** ô "Chú ý đường" của HUD thành "Nhìn đường" (giá trị: Tập trung / Rời mắt / Cầm điện thoại).
- **Còn lại:** pitch deck vẫn là chữ cũ; 15 clip demo có giao diện đã quay lại ([mục 3.41](#341-clip-demo-quay-lại-trên-giao-diện-và-giọng-nói-mới-1210)), 6 clip slide thì chưa. Trang `#/live` (bản
  chạy thử) còn vài chỗ dùng "giám sát". Chú thích trong code Python và các tài liệu lịch sử (roadmap, release cũ, audit)
  vẫn trích chữ cũ.
- Test: vitest 293 pass (13 kỳ vọng đổi theo chữ mới), `tsc` sạch, e2e 13 pass (9 `live.e2e.ts`, 4 `portrait.e2e.ts`: chữ
  mới vẫn vừa bố cục dọc), `test_data_policy.py` 10 pass. Cả bộ test Python không chạy lại vì không đổi file Python nào.

### 3.40 Hướng dẫn sử dụng trong sản phẩm, `#/guide` (M102, 12/10)

- **Thêm** trang `#/guide`, không cần đăng nhập, camera hay backend: 24 màn hình chia năm chương (bắt đầu ca lái, bốn
  mức khi đang lái, camera không thấy rõ, thiết bị trục trặc, kết thúc ca lái). Mỗi màn hình có "nghĩa là gì" và "nên
  làm gì", địa chỉ riêng `#/guide/<tên>`, nút "Tiếp" / "Trước" và phím mũi tên. Cuối trang là các trang web của từng
  vai trò.
- **Thêm** `StageFrame` cho `HudStage`: HUD vẽ được trong một hộp thay vì cả cửa sổ. Màn hình trong hướng dẫn là
  `HudView` / `TripSummaryView` thật trên kịch bản của `#/hud-preview`, không phải ảnh chụp; hình `inert`.
- **Thêm** một lối vào: thẻ "Hướng dẫn sử dụng" ở trang đăng nhập (trang đầu tiên của sản phẩm).
- **Sửa** (12/10) thẻ đó chuyển từ cuối cột form (dưới nút "Đăng nhập", phải cuộn mới thấy) lên cột giới thiệu, ngay
  dưới đoạn mô tả: viền và icon màu accent, thấy ngay không cần cuộn ở 1280 x 800 và 390 x 800.
- **Sửa** `PAGE_LEAD` chuyển từ `Dashboard.tsx` sang `nav.ts` (chữ không đổi).
- **Sửa** (12/10) bố cục `#/guide` từ một trang cuộn dọc thành kiểu app: khung cao bằng cửa sổ, không cuộn trang; hàng
  tab (Giới thiệu, năm chương, Trang web), một màn hình cạnh lời giải thích, thanh dưới có "Trước" / chấm của chương /
  "Tiếp". `#/guide` nay mở màn hình giới thiệu (trước là màn hình đầu tiên), thêm `#/guide/web`. Hình HUD thu nhỏ theo
  cả rộng lẫn cao của ô (trước: tối đa 62 % chiều cao cửa sổ).
- **Bỏ** danh sách 24 màn hình ở cột trái của `#/guide` và phần vai trò ở cuối trang (nay là tab "Trang web").
- Tương thích: không đổi API, ngưỡng, code Python hay CSP. `#/hud`, `#/live`, `#/hud-preview` vẽ như trước.
- Giới hạn: lời giải thích chưa có tài xế nào đọc; trang web sau đăng nhập mới có chữ, chưa có hình; HUD đang chạy
  không có nút mở hướng dẫn; chưa xem trên thiết bị thật.
- Đo: vitest 307 pass, e2e `guide.e2e.ts` 4 / 4 ở 1280 x 800, 800 x 1280, 390 x 800 (cả 24 màn hình, giới thiệu và
  trang web không cuộn cửa sổ). Ở 360 x 640 ô chữ phải cuộn bên trong (dài nhất thừa 137 px).

Chi tiết: [roadmap M102](roadmap.md#m102).

### 3.41 Clip demo quay lại trên giao diện và giọng nói mới (12/10)

Không đổi code chạy, không có số mốc.

- **Sửa** 15 clip ở `presentation/demo-clips/` (chưa đưa vào git): 2-1 … 2-9 và 4-1 … 4-6, quay lại trên bản build
  nhánh `DAQuan` ngày 12/10 (chữ của mục 3.39, giọng `vi-VN-NamMinhNeural`). Không quay lại khuôn mặt: hình lấy từ ô
  "Camera tài xế" của các clip cũ (440 × 330 px, lật lại cho hết soi gương, bỏ góc bo) và đưa vào `#/live` thay cho
  camera; pipeline thật chạy lại trên hình đó, backend trên database tạm. Độ dài từng clip giữ nguyên.
- Kết quả trên hình cắt lại, một lượt mỗi cảnh: làm quen khuôn mặt xong ở giây 13; điện thoại L2, rời mắt L2, nhắm mắt
  L3 đều báo; xe đỗ không báo; bật xi nhan trái thì lần nhìn trái không báo, tắt đi thì báo L2; che camera, rời khung
  hình ("Bạn vẫn ổn chứ?"), mất tín hiệu tốc độ đều hiện. Clip 4-3 hiện "không thấy mặt" khoảng 1,5 giây rồi mới đổi
  thành "camera bị che" (bản 09/10 hiện "camera bị che" ngay).
- **Sửa** `phan-2.mp4`, `phan-4.mp4`, hai bản `xem-truoc-toan-bo…mp4` (ghép lại), hai file `.srt` và `LOI-THOAI.md`
  (mốc giây, chữ trích từ màn hình, ghi chú 14). Bản 09/10 giữ ở `presentation/demo-clips/ban-cu-2026-10-09/`.
- **Còn lại:** 6 clip slide (phần 1, 3, 5) chưa xem lại chữ; bốn clip `6-…` không còn trong thư mục nên không quay
  lại; chưa lồng tiếng. Script quay nằm ngoài repo.

### 3.42 Trang đầu tiên là trang đăng nhập, vào thẳng bước tiếp (12/10)

Việc anh giao 12/10 sau khi chạy thử, chưa có số mốc.

- **Sửa** màn hình đầu của `#/live`: bỏ màn hình thiết lập ba bước (M64), thay bằng chính trang đăng nhập
  (`dashboard/Login.tsx`, có thẻ "Hướng dẫn sử dụng"). Bấm "Đăng nhập" (tài xế) hoặc "Dùng thử không lưu" là xin
  camera và chạy các bước khởi động ngay, không còn nút "Cho phép camera và bắt đầu" ở giữa.
- **Sửa** địa chỉ không có `#/...` nay mở trang này (trước: `#/dashboard`). `#/dashboard` giữ nguyên.
- **Thêm** quản lý, kỹ sư, quản trị đăng nhập ở trang đầu thì sang `#/dashboard`, không mở camera. Tài xế còn phiên
  đăng nhập thấy "Cho phép camera và bắt đầu", "Mở Dashboard", "Đổi tài khoản" thay cho form.
- **Bỏ** ở màn hình đầu của `#/live`: ba bước làm quen khuôn mặt viết sẵn, câu "Đặt camera ngang mặt", link "Xem lại
  lịch sử cảnh báo trên Dashboard". Màn hình đồng ý của HUD và `#/guide` vẫn nói các ý này.
- **Sửa** màn hình "Đang khởi động" dùng khung của `#/guide`; nút "Chạy thử bằng camera" trong `#/guide` bỏ, mũi tên
  quay lại về trang đầu.
- Tương thích: không đổi API, ngưỡng, code Python. `bench/live.bench.mjs` bấm một nút thay vì hai.
- Giới hạn: tài khoản không phải tài xế không còn chạy thử camera bằng tài khoản mình từ trang này (dùng "Dùng thử
  không lưu"); trang đăng nhập trên điện thoại 390 x 800 vẫn phải cuộn (như trước); chưa xem trên màn hình xe.
- Đo: `tsc` sạch, vitest 307 pass, Playwright 18 / 18 (1 bài mới: quản lý sang Dashboard, tài xế còn phiên).

### 3.43 Tư liệu dựng video demo bản 3 phút (12/10)

Không đổi code chạy, không có số mốc.

- **Thêm** [kich-ban-demo-3-phut.md](kich-ban-demo-3-phut.md): bảng dựng 21 đoạn (180 giây), lời thoại, các bước dựng
  còn lại, nguồn của số liệu trên slide vấn đề.
- **Thêm** `presentation/demo-clips/3-phut/` (chưa đưa vào git): 21 đoạn đã cắt từ các clip của mục 3.41, bản xem
  trước `xem-truoc-3-phut.mp4` chưa có lời, file `.srt`, một ảnh overlay, và nguồn để dựng lại (`slides.html`,
  `cat.json`, `render.cjs`, `dung.swift`).
- **Thêm** bảy slide nền tối: vấn đề bằng ba số (9 549; 3 200+; 6 300+), kiến trúc tổng quan, ba nguyên tắc (ảnh ở
  lại trong xe, quyết định bằng con số, chỉ JSON rời thiết bị), thời gian từng khối, và slide kết. Năm slide kiến
  trúc thay các clip `3-1` … `3-5` nền sáng; slide kết thay `5-1`, thêm khẩu hiệu và đổi địa chỉ bản chạy thử thành
  `c4-app-135.up.railway.app`.
- **Sửa** (cùng ngày, sau khi anh nghe thử) tiếng của các đoạn cắt: bản đầu xuất bằng `AVAssetExportSession` giữ
  các điểm cắt dưới dạng edit list, phần mềm dựng bỏ qua edit list nên tiếng của đoạn 18 và 20 lệch chỗ hoặc mất.
  Nay giải mã rồi mã hoá lại, mỗi file một track tiếng liền. Đoạn 19 dài thêm 1 giây và đoạn 20 cắt lại để không
  cắt ngang câu nhắc.
- **Sửa** thứ tự mở đầu: cảnh nhắm mắt L3 lên trước, rồi vấn đề, rồi mới tới team.
- **Bỏ** khỏi bản 3 phút: `2-8`, `2-9`, `4-5`, `4-6`, tab Đội xe và tab Ngưỡng của `2-7`.
- **Còn lại:** chưa có giọng và nhạc; slide team chưa có ảnh; số 3 275 của NHTSA chưa mở văn bản gốc.

### 3.44 Bản 3 phút dựng bằng HyperFrames, slide có chuyển động (12/10)

Không đổi code chạy, không có số mốc.

- **Thêm** `presentation/demo-clips/3-phut/dung-hf/` (chưa đưa vào git): một composition HyperFrames 180 giây. 14
  đoạn hình là các file đã cắt ở mục 3.43; bảy cảnh slide (02, 12–16, 21) viết lại thành HTML có timeline GSAP: khối
  trượt vào lệch nhịp, mũi tên tự vẽ, ba số đếm lên, thanh thời gian mọc từ trái, khung sáng ở slide kiến trúc
  chuyển mượt. Chữ, số và mốc giây giữ nguyên như `slides.html` và `cat.json`.
- **Thêm** bản xem trước `xem-truoc-3-phut-motion.mp4` (1920 × 1080, 30 FPS, 180,0 giây). Đo: âm lượng từng đoạn
  trùng bản cũ (tám đoạn, lệch 0,0 dB); `hyperframes check` 0 lỗi, 10 cảnh báo về cách chia file.
- **Thêm** công cụ trên máy dựng: FFmpeg (Homebrew) và ba bộ skill ở `~/.claude/skills` (HyperFrames, GSAP,
  motion-design). Không thêm dependency nào vào sản phẩm.
- **Thêm** (cùng ngày, lần dựng thứ hai) vào composition:
  - zoom và vòng khoanh trên năm đoạn quay màn hình: nút "Cảnh báo nhầm?" (08), hai tab dashboard và nhãn "Tài xế
    báo sai" (11), số 0 km/h, ô "Mắt" và ô camera (17), đèn xi nhan bật rồi tắt (18), ô camera bị che rồi thẻ "Tạm
    ngưng theo dõi" (19);
  - dải chữ 108 px ở đáy mọi đoạn hình: nhãn chương và chú thích cỡ 40 px, che dòng chú thích in sẵn (cỡ khoảng
    28 px);
  - nhãn bốn chương (Vấn đề, Demo, Kiến trúc, Edge case) ở góc trên phải các slide; chuyển cảnh kiểu hai khối quét
    ngang ở năm chỗ đổi chương (0:08, 0:39, 1:25, 2:04, 2:44), slide đẩy slide trong cùng một chương;
  - mã QR trỏ tới `https://c4-app-135.up.railway.app` trên slide kết.
- **Sửa** đoạn 03 và 04: hai clip cũ thay bằng hai cảnh HTML cùng chữ, các dòng hiện có chuyển động. Đoạn 16: sáu
  thanh thời gian (3 giây, không đọc kịp) thay bằng một con số "≈ 7 ms" và một thanh chia ba phần (5,83 + 0,69 +
  0,17 ms); số của YOLOv8n chuyển xuống dòng nguồn.
- **Bỏ** các lần mờ ra ở cuối slide của lần dựng đầu (chuyển cảnh thay cho chúng).
- Đo bản thứ hai: 180,0 giây; âm lượng 14 đoạn trùng bản không chuyển động (một đoạn lệch 0,1 dB ở đỉnh); mã QR đọc
  được từ khung hình đã render ở 1080p và 720p; `hyperframes check` 0 lỗi, 16 cảnh báo về cách chia file. Bản đầu
  giữ lại thành `xem-truoc-3-phut-motion-v1.mp4`.
- **Thêm** (cùng ngày, lần dựng thứ ba) giọng và nhạc: `demo-3-phut-co-loi.mp4`. 21 file giọng trong `3-phut/ghi am`
  cắt thành 24 mảnh, đưa về khoảng −16 LUFS; nhạc nền (Aylex, Innovating Care, freetouse.com) nối vòng một lần cho đủ
  180 giây, nhỏ hơn giọng khoảng 18 dB và hạ thêm khi sản phẩm phát tiếng; tiếng sản phẩm hạ xuống ở bốn đoạn có lời
  đè lên (01, 09, 19, 20). Mốc hiện của slide dời theo mốc từng từ (Whisper large-v3).
- **Sửa** độ dài slide theo giọng: 02 dài thêm 0,5 giây, 03 ngắn đi 0,5; trong chương kiến trúc 13 còn 10,5 giây,
  14 còn 9, 15 thành 6,5, 16 thành 6 (trước là 3). Các đoạn hình không đổi chỗ, tổng vẫn 180,0 giây.
- **Bỏ** khỏi giọng: phần chỉ dẫn "rồi im, để giọng nhắc của sản phẩm tự nói" bị đọc thành lời ở file 7; câu "Giọng
  đọc được tạo bởi…" ở cuối file 18.
- Đo bản thứ ba: −15,2 LUFS, đỉnh −1,6 dBFS; phiên âm lại bản ghép: đủ 21 câu đúng thứ tự, 15 từ khoá lệch mốc dự
  tính dưới 0,5 giây (một từ lệch 1,1 giây, nhiều khả năng do máy phiên âm). Chưa ai nghe bằng tai.
- **Sửa** (lần dựng thứ tư) chương edge case: bốn đoạn chạy lần lượt (40 giây, có zoom và vòng khoanh) thay bằng
  lưới 2 × 2 dài 21,5 giây: ô đang được lời thoại nói tới thì sáng và chạy, các ô khác mờ và đứng hình. Tiếng sản
  phẩm trong chương này tắt. Bản có lời còn 161,5 giây; phần dôi ra để dành cho đoạn mở đầu sẽ quay lại. Bản tuần tự
  giữ ở `demo-3-phut-co-loi-v2-edge-tuan-tu.mp4`.
- **Sửa** (13/10, sau khi xem lại cả video) cho người xem lần đầu: màn xin đồng ý giữ 1,6 giây ở tốc độ thật; đoạn
  làm quen khuôn mặt dừng trước khi màn "Tỉnh táo" hiện lại lúc mắt còn nhắm; vòng khoanh "Giả lập tín hiệu xe" ở
  đoạn 06; chú giải bốn mức L0–L3 trong dải chữ; chú thích "Mở mắt → hạ về mức L1" cho màn vàng sau L3; slide tốc độ
  còn 4,4 giây; địa chỉ và mã QR hiện sớm hơn 8,6 giây trên slide kết. Tổng vẫn 179,0 giây. Bản trước giữ ở
  `demo-3-phut-co-loi-v5-truoc-gop-y.mp4`.
- **Sửa** (13/10, theo góp ý của người xem) bố cục: vấn đề → demo → edge case → kiến trúc → kết, 169,3 giây. **Bỏ**
  slide ba vấn đề và slide "Ba phần, ba nguyên tắc". **Thêm** dòng viền đỏ sau ba con số và slide "Bảo mật thông tin
  người dùng: không lưu ảnh trên cloud" đặt sau sơ đồ. Khẩu hiệu trong video đổi thành "Nhắc đúng lúc, để bạn về nhà
  an toàn." Ba câu thoại mới chưa thu (`02b`, `15`, `22`). Bản trước giữ ở `demo-3-phut-co-loi-v6-thu-tu-cu.mp4`.
- **Thêm** (13/10) 36 hiệu ứng âm thanh nhỏ ở slide, thẻ chương và chỗ chuyển chương (`dung-hf/assets/sfx/`, CC0,
  nguồn ở `NGUON.md`, danh sách ở `cues.json`); không có cue nào trong các đoạn sản phẩm phát tiếng. **Sửa** sáu chỗ
  tìm được khi soát từng khung hình: zoom ở đoạn 08 và 19 không còn cắt đồng hồ tốc độ, khối 12–13 vào sớm 0,45 giây,
  dòng phạm vi dưới ba con số và nhãn "Cảnh minh hoạ" to hơn, hai sơ đồ kiến trúc hạ xuống 110 px. Vẫn 177,4 giây,
  −15,7 LUFS. Bản trước ở `nguon/index-truoc-sfx.html`.
- **Còn lại:** ảnh team, dữ liệu dashboard, hình khuôn mặt nén hai lần. Vị trí zoom và
  vòng khoanh tính theo hình hiện tại: quay lại hình thì phải đo lại. File 18 cần tạo lại bản không có câu ghi công
  hoặc kiểm điều khoản của dịch vụ đọc; nhạc cần ghi nguồn. Anh chưa xem bản thứ ba.

### 3.45 Kịch bản video sản phẩm 3 phút, quay người thật trong phòng (12/10)

Không đổi code chạy, không có số mốc.

- **Thêm** [kich-ban-video-san-pham.md](kich-ban-video-san-pham.md): kịch bản 23 cảnh, 2 phút 56 giây, theo kiểu
  video giới thiệu DMS thương mại. Sáu chương: vấn đề, sản phẩm và team, một ca lái, kiến trúc, edge case, kết. Kèm
  phân vai cho bốn người, thiết bị, bố trí bàn quay, buổi thử trước ngày quay, thứ tự quay 13 lượt, các bước dựng
  và các nhãn bắt buộc trên hình.
- Tham khảo: video DMS của STONKAM (video mẫu) và sáu video khác, xem bằng khung hình cắt mỗi 2–3 giây, phụ đề và
  mô tả; chưa nghe tiếng. Chỉ mượn cấu trúc và kỹ thuật.
- Ba loại hình: cảnh người lái, bản quay màn hình HUD của điện thoại chạy sản phẩm, và hình hệ thống lấy từ
  `tools/debug_view.py` chạy trên camera laptop cùng lúc (không sửa công cụ).
- Đo bằng script đọc bảng cảnh từ chính file: 23 cảnh nối liền, kết thúc ở 176 giây; lời đọc 480 âm tiết, dòng nào
  cũng vừa cảnh của nó ở 4 âm tiết mỗi giây.
- Dùng lại số liệu và câu chữ đã kiểm của mục 3.43, và các cảnh đồ hoạ 14, 15, 16, 21 của `dung-hf` (mục 3.44).
- **Sửa** (cùng ngày, sau khi anh chốt): bản đầu quay trong xe đang đỗ; nay không dùng xe, vì hệ thống chưa chạy trên
  xe thật. Quay trong phòng, cả bốn người có mặt trên hình (tài xế, người điều khiển xe, quản lý, kỹ sư). Nhãn trên
  hình là "Quay trong phòng · tốc độ và xi nhan giả lập"; câu kết giữ "chưa chạy trên xe thật" như slide đang có.
- **Còn lại:** chưa quay gì. Chưa kiểm trên điện thoại: bản web chạy trên điện thoại, quay màn hình có tiếng. Buổi
  thử làm sau khi bản trong máy được deploy lên Railway. Giọng đọc chưa chốt. `dung-hf` chưa sửa theo mốc giây mới.

### 3.46 File nộp Demo Day về đúng chỗ (13/10)

Chỉ đổi tài liệu và đường dẫn, không đổi code chạy, không có số mốc. Đối chiếu với chương 13 của Technical Book.

- **Thêm** `docs/pitch-deck.pdf` (12 slide, 3,6 MB): chuyển từ `presentation/DRIVERGUARD - Pitch Deck.pdf`.
- **Sửa** `docs/video-demo.md`: link <https://youtu.be/dyHXOouJTM4> (2 phút 57 giây; bản tải lên chiều 13/10 có số 7 198 của 9 tháng năm 2026, thay bản `0oqCKmL8ODk` còn số 9 549) thay link cũ, kèm bảng nội
  dung theo kịch bản 3 phút. Bảng này viết theo kịch bản, chưa đối chiếu với từng giây của video.
- **Thêm** `presentation/demo_script.md`: một dòng trỏ sang `docs/kich-ban-demo-3-phut.md`.
- **Sửa** `presentation/README.md`: bỏ nội dung mẫu của khoá học (`pitch_deck.pptx`, `video_demo.mp4`), trỏ tới file thật.
- **Sửa** `.gitignore`: `presentation/demo-clips/` (khoảng 1,4 GB clip, giọng đọc, project dựng) không vào git.
- **Sửa** README: Live URL là https://c4-app-135.up.railway.app ở cả bốn chỗ; dòng pitch deck chuyển sang ✅; số ngủ
  gật đạt L3 trên FL3D là 77/95 (81,1 %) theo `eval/results/report.md` (trước ghi số cũ 75/95).
- **Còn thiếu:** user feedback (0 người); CI trên GitHub không chạy vì tài khoản của tổ chức bị chặn thanh toán; số
  liệu trong pitch deck, video và README chưa cùng một nguồn. Trang quyền riêng tư, ảnh dự phòng và ảnh mobile làm ở
  mục 3.47.

### 3.47 Trang quyền riêng tư `#/privacy`; ảnh dự phòng và ảnh mobile; kết quả kiểm tra local (M106, 13/10)

- **Thêm** trang `#/privacy` trong sản phẩm (M106): thu gì, không thu gì, giữ bao lâu, ai xem được, quyền của tài xế,
  giới hạn. Không cần đăng nhập. Hai thời hạn lưu đọc từ `GET /api/v1/policy`. Vào từ `#/guide`. Bản rút gọn của
  `docs/data-policy.md`.
- **Sửa** bản deploy: `/privacy` chuyển tới `/#/privacy` (trước trả 404). Có hiệu lực từ lần deploy sau.
- **Thêm** `docs/demo-backup.md`: ba tầng dự phòng của demo; 16 ảnh từng bước có chú thích
  (`docs/screenshots/demo-steps/`) và 8 ảnh ở cỡ điện thoại 390 × 844 (`docs/screenshots/mobile/`). HUD từ
  `#/hud-preview`, dashboard trên database tạm với một ca lái mô phỏng; không ảnh nào có khuôn mặt. Script chụp nằm
  ngoài repo, như ở mục 3.34.
- **Thêm** `docs/ci-local.md` và ba ảnh ở `docs/screenshots/ci-local/`: ruff, `pytest` (1713 pass, 6 xfail), `tsc`,
  vitest (310 pass), build, e2e (21 / 21) chạy trên máy dev ngày 13/10, vì GitHub không khởi động job nào từ 12/10.
- **Sửa** README (trang `#/privacy`, liên kết tới hai tài liệu trên), `docs/evaluation.md`, `docs/data-policy.md`,
  `docs/video-demo.md`.
- Tương thích: không đổi API, ngưỡng, code của 14 khối hay CSP.
- **Giới hạn:** ảnh mobile là Chromium giả lập,
  chưa phải điện thoại thật; ảnh chụp trước khi gộp M103–M105 của `main`, nên chưa có giao diện của các mốc đó.

### 3.48 Pitch deck bản cuối; file nộp cập nhật theo (14/10)

Chỉ đổi tài liệu, không đổi code chạy, không có số mốc.

- **Sửa** `docs/pitch-deck.pdf`: bản 14 slide (9,1 MB) thay bản 12 slide của mục 3.46. Số Mỹ năm 2024 theo NHTSA
  (3.208 người chết, 315.167 người bị thương do mất tập trung); tỉ lệ buồn ngủ (AAA, 17,6 %) và mất tập trung (NHTSA,
  8 %) tách thành hai thanh có nguồn; kết quả trên dữ liệu công khai (slide 9: nhắm ≥ 1,5 s → L3 77/95, báo L3 đúng 83/85, nhắm ≥ 3 s 11/11, AUC 0,93,
  ngáp 79,8 % trên YawDD, báo sai 1,2 / giờ CI 0,38–2,7, DROZY 0/15 video tỉnh bị báo) tách khỏi thử nghiệm nội bộ
  (slide 10: 38/59, 7/7, trễ trung vị 1,9 s, 9/9, 8/8, 6/11, 0/13); thêm ~152 FPS, 30 FPS, 1.712 test; slide cuối có mã QR tới video và bản deploy (đã giải mã, đúng địa chỉ).
- **Sửa** README: deliverable 7 ghi 14 slide; hàng ảnh HUD thêm mức L1 (`docs/screenshots/hud-l1.png`).
- **Sửa** `presentation/README.md` (14 slide), `.gitignore` (`graphify-out/`).
- **Sửa** `docs/worklog.md` (10–14/10, commit tới `ae0c9e8`), `docs/journal.md` (10, 12, 13, 14/10).
- **Bỏ** việc "Pitch deck và video demo" khỏi `docs/improvements.md`, đánh số lại các việc còn lại.
- **Còn lại:** logo Xanh SM trên nhân vật minh hoạ; slide 4 chưa có bảng đối thủ; user feedback vẫn 0 người.

### 3.49 Audit `CLAUDE.md` theo model hiện tại (14/10)

Chỉ đổi hướng dẫn cho agent, không đổi code chạy, không có số mốc.

- **Sửa** `CLAUDE.md`: mục quy ước code ghi rõ bản `#/live` / APK làm khối 1–4, 13, 14 bằng TypeScript
  (`frontend/src/live`), khối 6–12 là Python qua Pyodide; các chữ `KHÔNG` / `CHỈ` viết hoa hạ về chữ thường, giữ
  nguyên ràng buộc; ràng buộc ảnh khuôn mặt trỏ tới `docs/data-policy.md`.
- **Còn lại:** 11 skill trùng tên giữa `.claude/skills` (`skills-lock.json`) và plugin `mattpocock-skills` 1.3.1,
  6 cái khác nội dung (`pr`, `domain-modeling` dùng `CONTEXT.md` thay vì `GLOSSARY.md`); chưa chọn giữ bản nào.

### 3.50 Vai trò Khuê thêm "Draft PRD" ở slide 13 và README (14/10)

Chỉ đổi tài liệu, không đổi code chạy, không có số mốc.

- **Sửa** `docs/pitch-deck.pdf`: bản mới (9,3 MB) thay bản của mục 3.48. So chữ từng slide với bản cũ: chỉ slide 13
  khác, vai trò Ngô Hoàng Thụy Khuê thêm "Draft PRD"; số liệu và QR không đổi.
- **Sửa** README, bảng team: vai trò Khuê thêm "Draft PRD", khớp slide 13.

### 3.51 README: tiêu đề kiểu repo nghiên cứu, badge và ảnh thumbnail (14/10)

Chỉ đổi tài liệu, không đổi code chạy, không có số mốc.

- **Thêm** `docs/screenshots/thumbnail.jpg` (ảnh bìa DriverGuard của nhóm, thu về 1600 px, 318 KB) và ba badge ở đầu
  README: YouTube demo (`https://youtu.be/dyHXOouJTM4`), slide trên Google Drive, live URL `https://c4-app-135.up.railway.app`.
- **Sửa** tiêu đề README thành "DriverGuard: Hệ thống cảnh báo buồn ngủ & mất tập trung on-device"; phần còn lại giữ nguyên.

### 3.52 Video demo: giọng đọc mới cho ba câu, link YouTube mới (14/10)

Chỉ đổi tài liệu và video, không đổi code chạy, không có số mốc.

- **Sửa** video demo 3 phút: ba câu 03 (giới thiệu DriverGuard), 15 (quyền riêng tư), 21 (câu kết) thay bằng bản thu
  lại 14/10, lời giữ nguyên theo `docs/kich-ban-demo-3-phut.md`. Câu 03 rút hai chỗ ngắt để không đè câu giới thiệu
  team; slide kết dời dòng "báo nhầm" và slogan theo nhịp đọc mới. Project dựng ở `presentation/demo-clips/` (không vào git).
- **Sửa** README (badge và dòng deliverable 6), `docs/video-demo.md`: link <https://youtu.be/V75TaUnJaug> (công khai,
  177 giây, 1080p) thay `dyHXOouJTM4`.
- **Còn lại:** mã QR video ở slide 13 của `docs/pitch-deck.pdf` vẫn trỏ tới link cũ `dyHXOouJTM4`; cần sửa trong Canva.

### 3.53 Video demo v9: khoảng lặng trước còi L3, tường 20 trạng thái HUD (15/10)

Chỉ đổi video, không đổi code chạy, không có số mốc. Học theo một video giới thiệu sản phẩm được đánh giá cao về
chuyển động; hình vẫn là clip quay thật, lời đọc giữ nguyên, không thu lại câu nào.

- **Sửa** câu 09 tách sau "giây rưỡi" (chỗ ngắt có sẵn trong bản thu): nhạc và lời dừng 0,5 giây, còi L3 kêu một mình,
  rồi "mức ba. Đỏ toàn màn hình…". Còi chỉ hạ âm lượng dưới nửa sau của câu.
- **Thêm** đoạn 3,7 giây trước slide kết: tường 5 × 4 gồm 20 trạng thái HUD, đều là khung hình cắt từ clip thật (thêm
  `4-6-cac-trang-thai-hud.mp4`), mở ở "Mở mắt!" rồi lùi ra, dòng "Mỗi tình huống, một lời nhắc rõ ràng.", không lời.
- **Sửa** độ dài 177,4 → 180,0 giây: đoạn tường vào ngay khi câu 16 dứt, slide kết giữ 1,05 giây sau chữ cuối (trước là 1,95).
- Đã thử rồi bỏ: caption dạng hỏi–đáp và zoom vào thẻ cảnh báo lúc nó bật; caption và zoom giữ như v8 (bản thử ở
  `3-phut/nguon/index-truoc-bo-hoi-dap.html`).
- File: `presentation/demo-clips/3-phut/demo-3-phut-co-loi-v9-tuong-hud.mp4`; bản v8 giữ ở
  `demo-3-phut-co-loi-v8-giong-14-10.mp4`, composition v8 ở `3-phut/nguon/index-truoc-v9.html` (không vào git).
- **Sửa** README (badge và dòng deliverable 6), `docs/video-demo.md`: link <https://youtu.be/3y0aOBudGyk> (công khai,
  180 giây, 1080p) thay `V75TaUnJaug`.
- **Sửa** `docs/pitch-deck.pdf` bản 15/10 (14 slide): mã QR video ở slide 14 trỏ link mới; chữ slide 2, 3, 5, 8 sửa
  lại (số liệu tai nạn viết gọn, tiêu đề slide 5, "Tài xế bấm “báo sai”" ở slide 8). Badge Slides trong README trỏ bản Google Drive mới.
- **Sửa** badge Slides trong README trỏ bản Google Drive mới (`1VNYH5vy…`) thay `1Vhwiv5e…`.

## 4. Tương thích khi nâng cấp từ v3

- **M85:** 31 khoá mới trong `thresholds.yaml` (danh sách ở [roadmap M85](roadmap.md#m85)). File YAML cũ thiếu
  chúng vẫn chạy với mặc định trong code, nay bằng đúng YAML đi kèm; nhưng `test_m85_no_hardcode.py` sẽ đỏ trên
  một YAML thiếu khoá, nên file YAML riêng của một thiết bị cần được thêm đủ. Bản thiết bị hỏi tín hiệu xe 0,25 s
  một lần (trước 0,2 s). State của server HUD có thêm trường `display`; HUD cũ bỏ qua nó. Bản web phải build lại
  (`npm run prepare-live` rồi `vite build`): trang mới đọc `sample_stride`, `vehicle`, `eye_blink_missing` từ
  `settings()` của gói Python mới, hai bên phải cùng bản. Sửa một khoá mà trang dùng trước state đầu tiên
  (`hud.*`, `capture.web_camera_*`, `context.vehicle_send_s`) thì chạy `python tools/web_defaults.py` rồi commit
  file sinh ra; quên thì test đỏ.
- **M89:** một khoá mới `hud.dim_hours`; file YAML cũ thiếu khoá này thì dùng mặc định 18–6 giờ. Ai đã nới
  `context.night_hours` để HUD mờ sớm hơn thì nên trả nó về và đặt `hud.dim_hours`. State của HUD có thêm trường `dim`;
  một HUD cũ đọc agent mới vẫn mờ theo `night` như trước.
- **M90:** sáu khoá mới (`drowsiness.head_drop.carry_max_lost_s`, `distraction.phone_min_coverage_s`,
  `context.turn_signal_max_s`, `trip_memory.microsleep_history`, `trip_summary.max_minutes`,
  `publisher.backoff_jitter`); file YAML cũ thiếu chúng thì dùng mặc định. `risk.blink.min_observed_s` nay là số giây
  dữ liệu mắt trong `drowsiness.blink_window_s` và phải ≤ cửa sổ đó: ai đã đặt lớn hơn 60 cần hạ xuống. Câu trả lời của
  `POST /api/v1/events` và `/api/v1/web/events` thêm trường `conflicts`.
- **M95:** một khoá mới `context.vehicle_signal_wait_s` (30). File YAML cũ thiếu nó dùng mặc định 30, tức thiết bị nâng
  cấp **đổi hành vi**: không có nguồn tốc độ thì sau 30 s thấy tài xế sẽ giám sát như đang chạy. Đặt 0 để giữ hành vi cũ.
  State của HUD có thêm `vehicle.never_received`; HUD cũ bỏ qua nó và hiện chữ "Mất tín hiệu xe".
- **M96:** lý do mới `slow_loop` của `monitoring_unavailable`. Backend cũ từ chối sự kiện mang lý do này (422): deploy
  backend cùng lúc với trang. Không khoá mới.
- **M97:** backend có thêm `POST /auth/refresh`. Trang mới với backend cũ (404) vẫn chạy như trước M97; backend mới
  với trang cũ không đổi gì. `WebAgent.settings()` có thêm `send_timeout_s`: trang và gói Python phải cùng bản.
- **M98:** hai khoá mới `preprocess.ir_channel_rel_max` (0,03) và `preprocess.ir_switch_s` (2,0). File YAML cũ thiếu chúng
  dùng mặc định, tức **đổi hành vi**: camera màu trong tối không còn bị coi là hồng ngoại. Đặt `ir_channel_rel_max: 0` để
  giữ luật cũ. Bản web phải đóng gói lại.
- **M99:** build bản web nay cần `npm run prepare-live` (hoặc `node scripts/web-runtime.mjs`) trước `vite build`, và cần
  mạng một lần để tải hai gói Python. Thiếu bước đó thì `#/live` không khởi động được (404 ở `runtime/pyodide/`).
  Trang và API ở hai tên miền khác nhau sẽ bị CSP chặn: thêm tên miền API vào `connect-src` của `backend/static.py`.
- **M93:** không khoá mới. Bản web phải đóng gói lại (`npm run prepare-live`). Ai gọi thẳng
  `EyeClosure.closed_duration` thì hàm có thêm tham số `dt`.
- **M92:** hai khoá mới `alert.remind_skip_reasons` và `risk.drowsy.context_factor_cap`. File YAML cũ thiếu chúng thì
  dùng mặc định trong code, bằng YAML đi kèm: tức là thiết bị nâng cấp sẽ **đổi hành vi** (không nhắc `drowsy_score`,
  trần 1,2). Muốn giữ hành vi M74 / M73 thì đặt `[]` và `1.44`. Bản web phải đóng gói lại (`npm run prepare-live`).
- Các mốc còn lại thêm khoá mới vào `config/thresholds.yaml` (liệt kê ở bảng [mục 1](#1-tóm-tắt-thay-đổi-so-với-v3) và ở từng
  mục của roadmap). Từ M85, một file YAML thiếu khoá làm `test_m85_no_hardcode.py` đỏ.

---

## 5. Kiểm thử

| | v3 (sau M69) | v4 (sau M101; M92, M93 chưa commit) |
|---|---:|---:|
| Test Python | 993 | **1712** pass, 6 xfail có chủ ý |
| Test frontend (vitest) | 138 | **293** pass |
| Test end-to-end (Playwright) | 4 | **9** của `live.e2e.ts`, **4** của `portrait.e2e.ts`, chạy dưới CSP |

- Test Python và vitest chạy lại cả bộ sau M93 (09/10), trên cây làm việc có M92, M93 chưa commit, không phiên nào khác
  đang sửa. E2e là số các phiên M88 và M89 báo sáng 09/10, chưa chạy lại sau M92, M93 (hai mốc không đổi code frontend).
- CI trên GitHub chưa chạy lần nào với các thay đổi này (xem M87).
- 10/10: cả bộ Python chạy lại kèm coverage (1712 pass, 6 xfail; 93,9 % dòng lệnh của `edge_agent/` + `backend/`), vitest
  293 pass; e2e không chạy lại (mục 3.38).
- 12/10: sau khi viết lại câu chữ (mục 3.39), vitest 293 pass, e2e 13 pass; cả bộ Python không chạy lại.
- 12/10: sau M102 (mục 3.40), vitest **305** pass; e2e `guide.e2e.ts` 4 / 4 (mới) và `portrait.e2e.ts` 4 / 4; `live.e2e.ts`
  không chạy lại; Python 1712 pass, 6 xfail.

**Sau M70 (08/10):** 1000 test Python pass (7 test mới bằng chuỗi số giả: đếm mọi nhánh và 30 s đầu, nhóm FPS, nhật ký đọc tập test, báo cáo có bảng mới, dòng nguồn gốc); ruff sạch ở phần đã đổi; test hồi quy trace không phải chốt lại. Frontend không đổi, không chạy lại.

**Sau M71 (08/10):** 1022 test Python (22 mới bằng chuỗi số giả; 12 trong 19 test khoảng hở đỏ khi tắt luật), 149 test frontend (11 mới), 5 e2e (1 mới) pass; ruff / format, typecheck, build sạch; test hồi quy trace không phải chốt lại. Báo cáo replay của FL3D / YawDD / SUST / UTA-RLDD dev / bản tự ghi giống hệt trước và sau. Chạy 10 phút bản build thật ở hai cấu hình: đạt cả hai (20,0 FPS mọi phút với camera giả 20 FPS), không lượt nào bị đứng nên đồng hồ canh chưa được thử bằng một lần đứng thật.

**Sau M72 (08/10):** 1041 test Python (19 mới bằng chuỗi số giả; 7 trong 18 test của `test_m72_silent_states.py` đỏ khi bỏ thay đổi ở khối 9, 10), 151 test frontend (2 mới), 6 e2e (1 mới, 1 mở rộng; test rời trang đỏ với hành vi cũ) pass; ruff / format sạch ở phần đã đổi, typecheck, build sạch; test hồi quy trace không phải chốt lại. Replay FL3D / YawDD / SUST / 3MDAD / bản tự ghi giống hệt trước và sau; UTA-RLDD dev lệch 1–2 cửa sổ 10 s, số cảnh báo không đổi.

**Sau M73 (08/10):** 1052 test Python (11 mới bằng chuỗi số giả, có bản đối chứng chạy lại hành vi cũ) pass; ruff / format sạch; không đổi code frontend nên test frontend và e2e không chạy lại; test hồi quy trace không phải chốt lại.

**Sau M74 (08/10):** 1072 test Python (20 mới bằng chuỗi số giả, 6 trong đó có bản đối chứng chạy lại hành vi cũ; 4 test cũ sửa theo hành vi mới) pass; ruff / format sạch; test hồi quy trace chốt lại có lý do (2 / 36 video thêm lần nhắc); không đổi code frontend nên test frontend và e2e không chạy lại.

**Sau M75 (08/10):** 1161 test Python pass, 7 xfail có chủ ý (88 ca chuỗi số giả cho 8 kiểu vòng lặp, 8 test của công cụ); ruff / format sạch; test hồi quy trace không phải chốt lại; không đổi code `edge_agent/` hay frontend nên test frontend và e2e không chạy lại.

**Sau M76 (08/10):** 1180 test Python pass, 7 xfail có chủ ý của M75 (19 test mới bằng chuỗi số giả, 2 trong đó có bản đối chứng chạy lại luật cũ); ruff / format sạch; test hồi quy trace không phải chốt lại; không đổi code frontend nên test frontend và e2e không chạy lại.

**Sau M77 (08/10):** 1209 test Python pass, 7 xfail có chủ ý của M75 (29 test mới bằng số giả và một model mặt giả, 1 trong đó là bản đối chứng tắt lớp chặn của khối 3); ruff / format sạch trên `edge_agent/` và `tests/`; test hồi quy trace không phải chốt lại; không đổi code frontend nên test frontend và e2e không chạy lại.

**Sau M78 (08/10):** 1213 test Python pass, 7 xfail có chủ ý của M75 (4 test mới cho luồng YOLO với model giả ném lỗi); 158 test frontend pass (7 mới của `YoloWatch` bằng số giả); e2e 6 / 6; `tsc`, ruff / format sạch. Đường thay worker được kiểm tay trong Chromium (camera giả, wasm) bằng một script tạm nuốt lần chạy YOLO; không có test tự động nào phủ đường đó.

**Sau M79 (08/10):** 1225 test Python pass, 7 xfail có chủ ý của M75 (12 test mới bằng chuỗi số giả; 3 test của M47 đổi từ "dừng" sang "nghỉ"); 158 test frontend pass (chỉ đổi một chuỗi nhãn); e2e không chạy lại; ruff / format sạch. Chưa thử với backend thật.

**Sau M80 (08/10):** 1246 test Python pass, 7 xfail có chủ ý của M75 (21 test mới bằng chuỗi số giả, 14 trong đó đỏ khi tắt hai thay đổi); 158 test frontend pass (thêm hai dòng nhãn); e2e không chạy lại; `tsc`, ruff / format sạch. Chưa thử với backend thật và `#/live` thật.

**Sau M81 (08/10):** 1275 test Python pass, 7 xfail có chủ ý của M75 (29 test mới bằng chuỗi số giả); test hồi quy trace chốt lại (`fl3d/P1042762` `nod` 9 → 6, `sust/drowsiness/d_781.mp4` mất 1 `yawn`); 158 test frontend pass (không đổi code frontend); e2e không chạy lại; ruff / format sạch. Replay FL3D, YawDD, SUST và UTA-RLDD dev chỉ in ra màn hình, `eval/results` không sinh lại. Chưa thử trên `#/live` thật.

**Sau M82 (08/10):** 1324 test Python pass, 7 xfail có chủ ý của M75 (28 test mới của backend bằng chuỗi nhịp và sự kiện giả, không cần thiết bị); 170 test frontend pass (5 test mới); e2e không chạy lại.

**Sau M83 (08/10):** 1324 test Python pass, 7 xfail có chủ ý của M75, chạy trên cây làm việc đang có cả M81 và M82 chưa commit (21 test mới của M83 bằng số giả, một model mặt giả và một camera giả; 1 trong đó là bản đối chứng tắt ngưỡng); 170 test frontend pass (7 test mới); e2e chạy lại cả bộ, 7 / 7 (1 test mới: camera đứng hình trong Chromium); `tsc`, ruff / format sạch. Test hồi quy trace không phải chốt lại (trace không có landmark, không đi qua khối 1). Chưa thử trên camera thật và backend thật.

**Sau M84 (08/10):** 39 test mới pass (lớp chặn ở ba nơi, bản web, server HUD trên cổng tự do); ruff / format sạch. Cả bộ Python chưa chạy lại được tới xanh: `config/thresholds.yaml` đang được sửa dở ở một việc khác trong cùng cây làm việc (khoá mới chưa có code đọc), mọi test nạp ngưỡng đỏ vì `ConfigError`. Không đổi code frontend nên test frontend và e2e không chạy lại.

**Sau M85 (08/10):** 1439 test Python pass, 7 xfail có chủ ý của M75, trên cây làm việc có cả M81–M84 chưa commit (76 test mới của M85; 39 test của M84 chạy xanh cùng cả bộ, tức phần "chưa chạy lại tới xanh" ở dòng trên đã được chạy); 171 test frontend pass (1 mới, 3 sửa); e2e 7 / 7; `tsc`, ruff / format sạch; `tests/fixtures/regression/expected.json` không đổi. 39 test cũ dựa vào mặc định lệch YAML nay ghi rõ giá trị chúng cần.

**Sau M86 (09/10):** 1467 test Python pass, 7 xfail (19 test mới của M86, 9 test mới của test hồi quy trace); ruff / format sạch trên `tools/`, `tests/`; `expected.json` ghim lại có lý do, 36 video cũ không đổi kết quả nào trên đường thiết bị. Frontend và e2e không chạy lại (không đổi code frontend). CI chưa chạy với `requirements.txt` đã ghim.

**Sau M87 (09/10):** 10 test mới (`test_m87_ci_real_models.py`) pass với `DG_REQUIRE_MODELS=1`, không test nào bị bỏ qua; bốn file test của A5 M8 chạy 3 lần liền 88 / 88 pass; ruff / format sạch. Cả bộ Python: 1480 pass, 8 đỏ ở bốn file thuộc việc các phiên khác đang sửa dở (`risk_engine.py`, `thresholds.yaml`, `publisher.py`), chưa chạy lại được trên cây đứng yên. CI trên GitHub chưa chạy (chưa push).

**Sau M88 (09/10):** 72 test Python mới (`test_m88_missing_tests.py`: 69 pass, 3 xfail có chủ ý cho A1 H1) và 94 test vitest mới (`agent.test.ts`, `HudScreen.test.tsx`, `yolo.worker.test.ts`, `measureCross.test.ts`; 1 ca `it.fails` có chủ ý cho A4 M1). Cả bộ trên cây làm việc có M87, M89, M90 chưa commit: 1589 test Python pass, 10 xfail; vitest 267 pass; `tsc`, `vite build`, ruff / format sạch. E2E không chạy lại (không đổi code frontend ngoài test). Thêm devDependency `jsdom` 29.

**Sau M89 (09/10):** 11 test Python mới (`test_m89_dim_hours.py`), 2 test vitest mới, 4 test e2e mới (`e2e/portrait.e2e.ts`) pass; vitest 266 pass, `tsc` sạch. Cả bộ Python 1483 pass, 5 fail ở phần các phiên chạy song song đang sửa dở (không thuộc M89), chưa chạy lại sau đó.

**Sau M90 (09/10):** 32 test Python mới (`test_m90_small_findings.py`, `test_m90_event_id_conflict.py`), 1 test vitest mới; cả bộ 1589 test Python pass, 267 vitest pass, e2e `live.e2e.ts` 7 / 7; test hồi quy trace không đổi.

---

## 6. Giới hạn đã biết

- **Chưa deploy.** M70–M76 đã commit và gộp `main` (PR #21, 08/10) nhưng lần gộp đó không tự deploy; M77–M90 đã commit và gộp
  `main` (PR #22, 09/10 06:43), M92 và M93 chưa commit. Các dòng dưới đây ghi "Mxx chưa commit" là đúng tới sáng 09/10,
  trước PR #22.
- **Audit 08/10, ba việc của mục 6.1 chưa làm** (đã chốt làm ngày 09/10, là M95, M98, M99 và M97 trong
  [kế hoạch](roadmap.md#ke-hoach-0910))**:** tốc độ xe (việc 4: chưa từng nhận tốc độ thì khối 10 coi xe đang đỗ ở
  0 km/h và không có cảnh báo nào); ảnh màu tối bị nhận là hồng ngoại (việc 8); runtime từ CDN chạy cùng trang với camera
  và token, không kiểm tra toàn vẹn, không CSP (việc 9). Ngoài top 10 còn A4 H2 (token đăng nhập hết hạn sau 60 phút).
- **Mục 7 của audit chưa được rà lại từng dòng** sau M77–M90 để biết còn sót phát hiện Medium / Low nào. M88 nêu bốn chỗ
  còn nguyên: `stop()` chờ backend mới nhả camera, lô bị bỏ cả khi gặp 4xx, 401 làm kẹt hàng đợi, ảnh màu tối bị nhận là
  hồng ngoại.
- **Số trong `eval/results`:** FL3D, YawDD, SUST, vòng lặp chậm và mục 10 của `dataset_uta_rldd.md` là của code ngày 09/10
  (M94); `lighting_transforms.md` chạy lại sau M98. Chưa sinh lại: `uta_rldd_tradeoff.md` (08/10), `personalization_uta_rldd.md` (06/10), `own_recordings.md` (06/10) và
  các báo cáo ảnh đơn, ánh sáng, điện thoại. Báo cáo sinh từ cây làm việc chưa commit.
- **Màn hình (M89):** ô tự xem của `#/live` che 62 % nút "Cảnh báo này sai?" ở chiều ngang (có từ M64) và 44 % nút
  "Đổi tài xế" ở chiều dọc, từ M100 ô này kéo và đổi cỡ được; 18–6 giờ là theo đồng hồ, không đọc ánh sáng; chưa ai xem
  trên màn hình 10 inch thật hay trong cabin tối; `#/live` thật chưa mở ở khổ dọc. M89 chưa commit.
- **Test (M88):** `LiveAgent.start` (xin camera, tải song song, lùi GPU → CPU) chưa có test; e2e chưa có kịch bản tắt
  mạng, token hết hạn, camera rớt (các ca đó mới được phủ ở mức lớp, trên jsdom); số cảnh báo ban đêm trên trace không
  được ghim, chỉ kiểm quan hệ với ban ngày; hai test ghim hành vi chưa chắc là mong muốn của HUD (cảnh báo tới lúc
  trình duyệt chặn tiếng không được phát bù; mở HUD khi có đúng một cảnh báo cũ thì nó kêu lại). M88 chưa commit.
- **CI (M87):** job `models` chưa chạy lần nào trên GitHub; FPS của nó là của máy chạy CI trên một khuôn mặt vẽ, không
  phải của màn hình xe; YOLO của CI là file trên release (khác sha256 với bản đã đo); `deploy` chưa phụ thuộc job
  này; một PR đang mở từ `DAQuan` làm mỗi lần push chạy CI hai lần. M87 chưa commit.
- **Vệ sinh eval (M86):** chưa trace lại video nào bằng đồng hồ mới, nên mọi số đã công bố vẫn theo `i / FPS`;
  127 / 145 video UTA-RLDD (trong đó hai video 12 FPS mang 6 / 9 lần báo sai) chưa đo được độ lệch giờ vì không có ở
  máy; fixture không ghim MediaPipe JS và bộ giải góc đầu của trang; `yolov8n.onnx` của bản deploy khác sha256 với
  bản đã đo; CI chưa chạy với thư viện đã ghim. M86 chưa commit.
- **Ngưỡng trong YAML (M85):** phép quét phía web chỉ bắt hằng số đặt tên in hoa và `?? số`, số viết thẳng trong
  biểu thức thì không; giá trị 0, 1, 2 không bị quét ở cả hai phía; `tools/` và `backend/` ngoài phép quét. Các
  khoá mức mới cho phép cấu hình vô nghĩa (`risk.microsleep_level: 0` tắt còi L3), chỉ sửa được bằng file YAML,
  không qua dashboard. `trip_memory.bin_s` khác 60 thì "phút" của bản tổng kết và của HUD là số ô. Camera của
  trang lấy kích thước từ bản build, không từ ngưỡng chỉnh trên dashboard. Chưa mở `#/live` bằng tay sau mốc này.
  M85 chưa commit.
- **Lớp chặn ảnh, server HUD (M84):** bản web bỏ bản ghi bị từ chối mà không báo về backend (chỉ console và
  `refused_records`); chương trình không phải trình duyệt trên cùng máy vẫn gọi được server HUD; chưa thử trên trình
  duyệt thật; cả bộ test chưa chạy lại tới xanh sau mốc này. M84 chưa commit.
- **Chọn mặt tài xế, camera đứng hình (M83):** ngưỡng loại chỉ dựa trên vị trí: người khác ngồi vào chỗ tài xế,
  hoặc hành khách trong vòng 4 lần khoảng cách hai mắt (ghế giữa hàng sau, người chồm sang), vẫn được đọc là tài xế;
  chữ ký hình dạng mặt đo được là không phân biệt người. Camera bị xoay hoặc tài xế đổi chỗ hơn mức đó **trong lúc
  không thấy mặt** thì mặt tài xế bị loại (có báo "tạm ngưng") tới khi về gần chỗ cũ hoặc bấm "Đổi tài xế". Giá trị 4
  chỉ dựa trên DROZY (người ngồi trước màn hình, camera cố định), chưa có bản ghi hai người trong xe. Chưa camera
  thật nào được thấy lặp frame; camera ảo chiếu ảnh tĩnh sẽ bị coi là mất camera; `camera_lost` không nói lý do.
  M83 chưa commit.
- **Giờ thiết bị sai** (M82): không còn ảnh hưởng trạng thái xe, mục "cần chú ý ngay" và thời hạn tự xoá (đều
  theo giờ máy chủ). Giờ hiển thị của từng cảnh báo, thứ tự danh sách và việc lọc theo ngày vẫn là giờ thiết bị
  ghi; xe lệch quá 120 s có nhãn ở tab "Đội xe". Chưa thử trên Railway. M82 chưa commit.
- **Gục đầu và ngáp (M81):** hai khoá mới đổi độ nhạy lấy báo sai mà chưa tập nào cho thấy cảnh báo sai giảm (FL3D
  mất 30 % `nod` đúng, YawDD mất 3 lần ngáp đúng); MAR vẫn giảm khi cúi nên ngáp khi cúi dễ sót; mặt nạ ngáp / nói
  vẫn nới ra khi quay đầu; lợi ích của "ngáp đếm một" chỉ có trên chuỗi số giả (không tập nào có nhãn ngáp che tay).
  `eval/results` mang số của hành vi trước M81. M81 chưa commit.
- **Mốc "nhìn đường" (M80):** ca kẹt vẫn cho 2 cảnh báo L2 sai trong khoảng 60 s trước khi tự hết; nhìn về phía mốc
  sai từ 0,3 s thì bộ đếm bắt đầu lại; một tư thế lệch thật giữ yên 60 s lái liên tục, mí không hạ, sẽ bị học thành
  mốc; ca "mắt không đọc được" khi camera lệch dọc hơn 25° (A2 M2) chưa sửa; khối 7 và 8 vẫn có hai mốc riêng;
  backend cũ từ chối `road_pose_recalibrated`. Hai khoá mới chưa được chỉnh trên chuyến thật. M80 chưa commit.
- **Nạp lại ngưỡng (M79):** xe không đỗ đủ 120 s trong chuyến thì chạy bộ ngưỡng cũ tới hết chuyến; lần nạp vẫn dựng
  lại khối 7, 8, 12 (tài xế chưa đăng ký mất mốc tự học); `config_refused` không nói lý do trong sự kiện. M79 chưa
  commit, chưa deploy.
- **Nhánh điện thoại tự hồi phục (M78):** bản thiết bị không dựng lại session ONNX và không có hạn chờ cho một lần
  gọi model bị treo; bản web chưa có hạn chờ cho bước tải model lúc khởi động, hết 3 lần thay thì tắt tới hết chuyến,
  chưa thử trên WebGPU. Ba khoá `phone.web_*` là tạm. M78 chưa commit, chưa deploy.
- **Số NaN (M77):** chỉ chặn ở khối 3 và khối 9. Khối 7 vẫn nhận EAR NaN nếu khối 6 tính ra từ landmark hữu hạn
  (chưa kiểm có ca đó không); bản ghi gửi backend vẫn lấy `perclos_60s`, `closed_duration`, `off_road_duration` gốc
  của khối 7 / 8, nên NaN ở đó vẫn làm hỏng lô. Mặt tài xế NaN mà còn mặt hành khách thì hành khách được đo trong
  frame đó. M77 chưa commit, chưa deploy.
- **Mắt díp rồi nhắm (M76):** phần được thêm trên dữ liệu thật là 2 chuỗi của 1 người (24 người dùng để dò); hai người
  khác mà audit nêu thuộc tập giữ riêng, chưa đọc. Lần nhắm bị che vì đang ngáp / nói vẫn không có L3. Chuỗi phải
  nhắm sâu ở mọi frame: một frame EAR nhiễu cắt chuỗi và đếm lại từ đầu.
- **Dưới 15 FPS (M75):** số đo là replay trace đã bỏ bớt frame, tức chỉ khối 7–12 nhận ít frame; model mặt và model
  mắt chưa chạy trên máy chậm, nhánh điện thoại không có trong trace. Ở vòng lặp chậm và không đều, thời lượng bị đo
  ngắn tối đa hai khoảng frame: lần nhắm mắt vượt mốc L3 dưới 0,2–0,3 s có thể không hú còi. `phone_ratio_2s` và tỉ lệ
  nhắm sâu đếm theo số frame chứ không theo thời gian. Chưa sửa chỗ nào; độ không đều 0,3 là giả định.
- Các giới hạn của v3 ([release-v3.md mục 6](release-v3.md#6-giới-hạn-đã-biết)) vẫn còn nguyên, trừ những gì các mốc trên đã sửa.
