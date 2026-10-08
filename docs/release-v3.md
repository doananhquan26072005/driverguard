# DriveGuard — Version 3

> Bản tiếp theo của [Version 2](release-v2.md). Ghi lại mọi cải tiến, chỉnh sửa làm từ 05/10/2026 tới M69
> (08/10/2026): cái gì **thêm**, cái gì **sửa**, cái gì **bỏ**, và đã kiểm chứng tới đâu. Các việc làm theo
> [audit 08/10](audit-2026-10-08.md), từ M70 trở đi, ghi ở [Version 4](release-v4.md) (tách ra ngày 09/10).
> Nguyên tắc giữ nguyên: mọi xử lý hình ảnh chạy trên thiết bị hoặc trong trình duyệt, không gửi và
> không lưu ảnh khuôn mặt, chỉ gửi metadata JSON.

| | |
|---|---|
| **Phiên bản** | Version 3, dựa trên v2.2 (M9–M31). Deploy tay lần đầu 08/10 (M66) lên một service riêng; v2.2 và v1.1 vẫn chạy song song ở địa chỉ cũ |
| **Mã nguồn** | nhánh `DAQuan`; M32–M69 đã commit và đã gộp `main` (lần gộp gần nhất: PR #21, 08/10/2026) |
| **Web đang chạy (v3)** | https://driveguard-production-5093.up.railway.app/#/live (kiểm 09/10: `/health` 200, API có `/api/v1/policy`, `/api/v1/fleet`; chưa kiểm bản đó gồm tới mốc nào). v2.2: https://driveguard-v2-production.up.railway.app; v1.1: https://driveguard-production-6b83.up.railway.app |
| **Mốc trong lộ trình** | M32 (leo thang cảnh báo theo thời gian), M33 (nhịp "còn sống" và tổng quan đội xe), M34 (test hồi quy bằng trace), M35 (prototype thời lượng chớp), M36 (tiêu chí sẵn sàng pilot), M37 (chính sách dữ liệu, tự xoá theo thời hạn), M38 (khối 8: liếc cộng dồn, gọi / nhắn tin, quay hẳn đi), M39 (công cụ ghi số từ camera), M40 (đo offline: PERCLOS P80, ánh sáng, cá nhân hoá, theo người), M41 (phiên bản, tag, nhật ký truy cập), M42 (chạy dài, container giới hạn kiểu Jetson), M43 (chất lượng frame), M44 (không phản ứng, "Bạn còn ở đó không?", báo quản lý ngay), M45 (dung lượng tải lần đầu), M46 (cùng video, ánh sáng khác), M47 (tải lại ngưỡng khi đỗ, áp thử, quay lui), M48 (dữ liệu của tài xế), M49 (tốc độ bản web: công cụ đo, góc đầu, đồng hồ từng chặng), M50 (báo khi model điện thoại không cho kết quả, đẩy cảnh báo ngay, giờ chụp của frame, tải song song), M51 (model mặt chọn GPU / CPU, YOLO hai luồng, công cụ đo trong trình duyệt), M52–M55 (bản tự ghi, UTA-RLDD, hướng mắt), M56 (ngưỡng `eyeBlink` cho bản web, mốc mống mắt theo tài xế), M57–M65 (thiết kế lại toàn bộ giao diện; roadmap gọi đợt này là "Version 4", không phải bản phát hành [v4](release-v4.md); xem [mục 2.30](#230-giao-diện-mới-so-với-v2-m57m65)), M67 (tốc độ `#/live`: YOLO trên WebGPU, nhịp chạy, khởi động), M68 (đăng ký xong thì điểm buồn ngủ bắt đầu từ 0), M69 (đọc số UTA-RLDD thêm ba cách: theo người, điểm làm việc cố định, đơn vị mỗi bảng). Các mốc từ M70 (làm theo audit 08/10) thuộc [Version 4](release-v4.md); xem [roadmap.md](roadmap.md) |

---

## Có gì mới (xem nhanh)

Phần này dành cho người dùng muốn biết ngay v3 nâng cấp gì so với v2. Bảng đầy đủ theo từng mốc ở
[mục 1](#1-tóm-tắt-thay-đổi-so-với-v2).

- **Nhanh hơn và nhẹ hơn trên web**: lần đầu tải khoảng 30 MB thay vì 42 MB. Trên máy không có GPU
  thật, tốc độ tăng từ khoảng 20 lên 30 FPS. Nhận diện điện thoại mỗi lần còn 91 ms thay vì 172 ms,
  và còn 17 ms trên máy có GPU thật (M67). Cảnh báo hiện ngay trong frame đó, không chờ 300 ms.
- **Ít cảnh báo sai hơn**: chớp chậm và nhướn mày chỉ còn được ghi nhận, không tự gây cảnh báo. Đo
  trên 24 người giữ riêng của UTA-RLDD, cảnh báo sai giảm từ 8 xuống 4 lần.
- **Cảnh báo mạnh dần khi tài xế không phản ứng**: nhắc nhẹ lặp lại 3 lần trong 10 phút thì lần thứ
  ba lên mức cao hơn. Nhắm mắt từ 6 giây có thêm cảnh báo "không phản ứng". Camera không thấy tài xế
  8 giây khi xe chạy thì màn hình hỏi "Bạn còn ở đó không?".
- **Quay hẳn ra sau vẫn bị nhắc**: cảnh báo nhìn khỏi đường được giữ tới 10 giây, trước đây im sau 3 giây.
- **Nói rõ vì sao tạm ngưng giám sát**: camera bị che, mặt ngoài khung, quá tối, quá chói hay ảnh
  mờ, kèm việc tài xế cần làm. Cũng báo khi không phát hiện được điện thoại.
- **Quản lý theo dõi cả đội xe**: tab "Đội xe" cho biết xe nào đang hoạt động, xe nào mất liên lạc,
  và mục "Cần chú ý ngay" có tiếng báo khi có cảnh báo nặng.
- **Đổi ngưỡng an toàn hơn**: áp thử cho vài xe trước, xem số cảnh báo rồi mới áp cho cả đội, quay
  lui được. Xe chỉ nhận ngưỡng mới khi đang đỗ.
- **Tài xế nắm dữ liệu của mình**: tải toàn bộ dữ liệu, yêu cầu xoá, và xem ai đã xem dữ liệu của
  mình. Cảnh báo tự xoá sau 60 ngày, tổng kết chuyến sau 365 ngày.
- **Giao diện thiết kế lại hoàn toàn**: HUD trong xe và web đều chuyển sang nền tối, font Inter, thẻ "kính".
  HUD có khung cố định 1280 × 800, chữ to, nút 72 px, chữ có màu thay cho số. Web có một trang đăng nhập chung,
  menu trái và trang chủ riêng cho từng vai trò (tài xế, quản lý, kỹ sư, quản trị) thay cho thanh tab. Mọi
  tính năng của v2 vẫn còn, backend và logic cảnh báo không đổi. Chi tiết ở [mục 2.30](#230-giao-diện-mới-so-với-v2-m57m65).
- **Kiểm chứng trên dữ liệu thật nhiều hơn**: đánh giá trên UTA-RLDD (48 người, 25 giờ buồn ngủ
  thật) và trên các phiên tự ghi từ camera.

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
| **Thêm** | Khối 8 đo `off_road_ratio` / `glance_count` (nhiều lần liếc ngắn cộng dồn trong 30 s). Chỉ đo và ghi vào metadata, mẫu theo phút, bảng tổng kết; không cảnh báo | M38 | 06/10 |
| **Thêm** | Khối 4 phân loại điện thoại đang gọi / nhắn tin / không rõ theo vị trí khung so với khung mặt (`phone_kind`); chỉ ghi, lý do và mức cảnh báo giữ nguyên | M38 | 06/10 |
| **Sửa** | Mặt mất ngay sau khi quay đầu quá 45° khỏi đường: giữ `off_road` (L2) tối đa 10 s rồi mới "tạm ngưng giám sát"; trước đây im sau 3 s. Không thêm cảnh báo nào trên SUST / YawDD / FL3D | M38 | 06/10 |
| **Thêm** | `tools/record_trace.py`: ghi số trực tiếp từ camera kèm nhãn bấm phím (không lưu ảnh), báo cáo time-to-alert p50 / p95, khẩu trang, nhìn xuống, gọi / nhắn tin. Chưa có bản ghi thật | M39 | 06/10 |
| **Thêm** | Trace có thêm blendshape hướng nhìn và miệng, vị trí mống mắt, khung mặt, khung / loại điện thoại; `seq_eval` tách lớp `Tracer`, `replay` dùng cờ điện thoại và nhận mốc "đăng ký giả" | M39, M40 | 06/10 |
| **Thêm** | `perclos_p80_60s` đo song song với `perclos_60s` (không vào điểm, không sinh sự kiện); comment `thresholds.yaml` ghi rõ định nghĩa PERCLOS đang dùng và việc các ngưỡng PERCLOS không có nguồn | M40 | 06/10 |
| **Thêm** | `tools/trace_studies.py` và bốn báo cáo: `perclos_p80.md`, `lighting.md`, `personalization.md`, `glance_ratio.md`; `tools/eval.py` có cột `subject`, bảng theo từng người, bảng tách 30 s khởi động | M40 | 06/10 |
| **Sửa** | `eval/results/dataset_yawdd.md` sinh lại (bản cũ đã lệch với code: 12 cảnh báo, nay 11), thêm bảng theo người và bảng khởi động | M40 | 06/10 |
| **Thêm** | Mọi nhịp "còn sống" và sự kiện mang phiên bản app, phiên bản bộ ngưỡng, mã rút gọn của model; tab "Đội xe" có cột "Phiên bản", tô xe chạy bộ ngưỡng cũ | M41 | 06/10 |
| **Thêm** | Tag `simulated` trên mọi sự kiện khi tín hiệu xe là mô phỏng; backend loại sự kiện `forced` khỏi mọi thống kê; `#/hud-preview` ghi và cho tải nhật ký các trạng thái ép tay | M41 | 06/10 |
| **Thêm** | Nhật ký truy cập chỉ ghi thêm (`access_log`, `GET /api/v1/access-log`, `/access-log/mine`), tab "Nhật ký truy cập" cho admin và "Ai đã xem dữ liệu của tôi" cho tài xế; giữ 365 ngày | M41 | 06/10 |
| **Thêm** | Test chốt danh sách endpoint (không có xếp hạng tài xế) và test tĩnh quét lời gọi ghi / quay ảnh camera trong toàn bộ mã nguồn | M41 | 06/10 |
| **Thêm** | `tools/benchmark.py --duration`: chạy dài theo nhịp camera, ghi FPS / độ trễ / CPU / RAM mỗi giây; `Dockerfile.edge`, `tools/edge_sim.py`, `config/edge_profiles.yaml`: cùng phép đo trong container giới hạn kiểu Jetson Nano / Orin Nano (`simulated`); bảng lượng tử hoá `eval/results/quantization.md` | M42 | 06/10 |
| **Thêm** | Giai đoạn chất lượng frame của khối 6: che camera, mặt ngoài khung, mặt quá tối / quá chói, ảnh mờ. Mặt còn thấy mà không đọc được ≥ 5 s khi xe chạy thì "tạm ngưng giám sát"; mọi lần tạm ngưng có lý do trên HUD, trong sự kiện và bản tổng kết | M43 | 06/10 |
| **Sửa** | Màn hình "Tạm ngưng giám sát" không còn luôn ghi "không thấy mặt": ghi việc tài xế cần làm theo lý do | M43 | 06/10 |
| **Thêm** | Nhắm mắt ≥ 6 s (còi L3 đã kêu vài giây): cảnh báo L3 thứ hai với lý do `unresponsive`; cảnh báo L3 thứ 3 trong 10 phút mang lý do `repeated_l3` | M44 | 06/10 |
| **Thêm** | "Bạn còn ở đó không?": camera không thấy tài xế 8 s khi xe chạy thì HUD hỏi bằng cả màn hình và tiếng; 10 s không chạm thì sự kiện `no_answer` | M44 | 06/10 |
| **Thêm** | Sự kiện L3, `unresponsive`, `repeated_l3`, `no_answer` được gửi ngay; tab "Đội xe" có mục "Cần chú ý ngay" kèm tiếng, tự làm mới mỗi 5 s | M44 | 06/10 |
| **Sửa** | `#/live` không còn tải OpenCV (11,7 MB): góc đầu và lọc khung trùng chạy bằng numpy trong trình duyệt, đã so với OpenCV. Thiết bị không đổi | M45 | 06/10 |
| **Thêm** | Server gửi file đã nén sẵn (gzip) và đặt `Cache-Control`; lần đầu tải khoảng 30 MB qua mạng thay vì 42 MB | M45 | 06/10 |
| **Thêm** | `tools/light_study.py` và `eval/results/lighting_transforms.md`: cùng video bị làm tối / chói / xám / mờ trong RAM | M46 | 06/10 |
| **Thêm** | Thiết bị và `#/live` hỏi lại ngưỡng mỗi 5 phút, chỉ áp khi xe đỗ, gửi `config_applied` / `config_refused` | M47 | 06/10 |
| **Thêm** | Backend và dashboard: lưu ngưỡng chỉ cho vài xe thử, bảng phiên bản kèm số cảnh báo / báo sai, nút "Áp cho cả đội" (cũng là quay lui) | M47 | 06/10 |
| **Sửa** | Tab "Ngưỡng" không còn ghi "thiết bị áp dụng khi khởi động lại"; tab "Đội xe" so mỗi xe với phiên bản nó phải chạy | M47 | 06/10 |
| **Thêm** | Tài xế: tab "Dữ liệu của tôi" có nút tải toàn bộ dữ liệu của mình (JSON) và nút yêu cầu xoá; admin duyệt hoặc từ chối kèm lý do; lệnh `delete-user` | M48 | 06/10 |
| **Thêm** | File database chỉ chủ sở hữu đọc được; `.dockerignore` và test chặn bí mật / database lọt vào image; mẫu hồ sơ đánh giá tác động và mẫu thông báo cho tài xế | M48 | 06/10 |
| **Thêm** | `tools/bench_web.py`: đo khối 6–14 của bản web trong Pyodide, cạnh cùng lời gọi trên thiết bị; bảng trước / sau `eval/results/benchmark_web.md` | M49 | 06/10 |
| **Sửa** | Góc đầu của bản web (`geometry.solve_pnp`): đạo hàm giải tích, dừng sớm khi đã hội tụ. Khối 6–14 trong Pyodide 1,97 → 0,61 ms / frame; góc lệch tối đa 7e-8 độ, không đổi ngưỡng | M49 | 06/10 |
| **Sửa** | Cửa sổ liếc 30 s (khối 8) và cửa sổ chất lượng 10 s (khối 6) dùng tổng cộng dồn thay cho cộng lại mỗi frame; kết quả trên trace hồi quy không đổi | M49 | 06/10 |
| **Thêm** | `#/live` đo thời gian từng chặng của vòng lặp (camera, MediaPipe, đo pixel, Python, YOLO, tuổi kết quả YOLO, frame bị bỏ), ghi MediaPipe chạy GPU hay CPU và số luồng YOLO; hiện ở "Chi tiết kỹ thuật" | M49 | 06/10 |
| **Thêm** | Heartbeat mang số đo tốc độ (`perf`), backend giữ bản mới nhất mỗi thiết bị, tab "Đội xe" có cột "Tốc độ xử lý" | M49 | 06/10 |
| **Thêm** | Model điện thoại không còn cho kết quả mới (chậm, không tải được) trong ≥ 80 % của 10 s: HUD hiện "Không phát hiện được điện thoại", sự kiện `phone_detection_lost` / `phone_detection_restored`. Trước đây im lặng | M50 | 06/10 |
| **Sửa** | `#/live`: frame không có mặt làm Python lỗi (`null` của JS không phải `None` trong Pyodide), 1 s sau HUD báo "Lỗi xử lý" thay vì "tạm ngưng giám sát" | M50 | 06/10 |
| **Sửa** | `#/live` đẩy cảnh báo mới cho HUD ngay trong frame đó, không chờ vòng hỏi 300 ms | M50 | 06/10 |
| **Sửa** | `#/live` lấy giờ camera chụp frame làm giờ của frame thay cho giờ xử lý; thêm chặng `camera_lag` vào số đo tốc độ | M50 | 06/10 |
| **Sửa** | `#/live` tải Python, model mặt, model điện thoại song song, ngay khi hỏi quyền camera; `thresholds.yaml` đọc một lần mỗi chuyến | M50 | 06/10 |
| **Thêm** | `frontend/bench/live.bench.mjs`: đo vòng lặp của bản build thật trong Chromium với camera giả; bảng `eval/results/benchmark_live.md` | M51 | 06/10 |
| **Sửa** | `#/live`: model mặt chỉ dùng delegate GPU khi WebGL do GPU thật vẽ. Máy vẽ WebGL bằng phần mềm: 45 → 9 ms mỗi frame, khoảng 20 → 30 FPS | M51 | 06/10 |
| **Sửa** | Web app được phục vụ kèm header cách ly (COOP / COEP); YOLO của `#/live` chạy `phone.num_threads` luồng: 172 → 91 ms mỗi lần | M51 | 06/10 |
| **Sửa** | Worker YOLO: file runtime của ONNX Runtime phục vụ nguyên bản (bật luồng với bản gộp làm phiên không bao giờ sẵn sàng) | M51 | 06/10 |
| **Thêm** | Bản ghi đầu tiên từ camera (ba phiên ban ngày, một người, 20 phút) và báo cáo `eval/results/own_recordings.md`: độ trễ cảnh báo thật, nhìn xuống so với nhắm mắt, gọi / nhắn tin. Không đổi code | M52 | 06/10 |
| **Sửa** | Chớp chậm và nhướn mày không còn cộng vào `drowsy_score` (trọng số 10 → 0), luật `trend` chỉ ghi nhận (mức 1 → 0): đo trên UTA-RLDD, 24 người giữ riêng, cảnh báo sai 8 → 4 lần | M53 | 06/10 |
| **Thêm** | Đánh giá trên UTA-RLDD (48 người, 25 giờ, buồn ngủ thật): `tools/uta_rldd.py`, notebook Kaggle để trace, tập dev / test theo người, báo cáo `eval/results/dataset_uta_rldd.md` và `personalization_uta_rldd.md` | M53 | 06/10 |
| **Sửa** | Bản web / APK: `eyeBlink` có ngưỡng riêng ở khối 7 (0,4 / 0,3 / 0,55) thay cho ngưỡng của CNN mắt. Camera xám / hồng ngoại trước đó bỏ sót mọi lần nhắm mắt (replay 0 / 48 → 46 / 48, FL3D 0 / 95 → 64 / 95). Bản thiết bị không đổi | M56 | 07/10 |
| **Thêm** | Bước nhìn đường của đăng ký ghi mốc mống mắt của tài xế (`DriverProfile.road_iris_y`); khối 8 dùng nó cho góc nhìn xuống. Vẫn chỉ đo | M56 | 07/10 |
| **Thêm** | `#/live`: model điện thoại chạy bằng WebGPU khi trình duyệt có GPU thật (94 → 17 ms mỗi lần, 10 lần / giây), không thì wasm như cũ; tự lùi về wasm khi WebGPU lỗi. Khoá `phone.web_gpu`, `phone.web_gpu_target_fps` | M67 | 08/10 |
| **Sửa** | `#/live`: model điện thoại chạy đúng `phone.target_fps` (trước đó 4,5 lần / giây cho mục tiêu 5) và nhận frame trước khi model mặt chạy. Tuổi kết quả khi dùng p95 333 → 267 ms (wasm), → 131 ms (WebGPU) | M67 | 08/10 |
| **Sửa** | `#/live` khởi động: gói của Pyodide tải song song với runtime, vòng lặp không chờ model điện thoại. Cache trống 2,66 → 2,08 s, cache ấm 1,36 → 1,29 s | M67 | 08/10 |
| **Thêm** | `frontend/bench/live.bench.mjs`: số đếm cả lần chạy, thời gian khởi động từng phần, chạy dài có kết luận (`--duration`), cache ấm (`--profile`), ép nơi chạy YOLO (`--yolo`). "Chi tiết kỹ thuật" ghi "WebGPU" / số luồng và thời gian khởi động | M67 | 08/10 |
| **Thêm** | `tools/phone_study.py` và `eval/results/phone_web_3mdad.md`: nhánh điện thoại trên 3MDAD theo tần số YOLO, độ trễ kết quả và cỡ ảnh đầu vào | M67 | 08/10 |
| **Bỏ** | Ba thứ đã đo rồi không giữ: wasm chạy 10 lần / giây (CPU 216 % so với 136 %), mở sẵn kết nối tới CDN (không đo được lợi), ảnh đầu vào nhỏ hơn cho YOLO (chờ quyết định) | M67 | 08/10 |
| **Sửa** | Đăng ký khuôn mặt: `drowsy_score` đọc 0 trong bước nhắm mắt (trước đó nhảy lên 25); đăng ký xong thì khối 7 bỏ mọi thứ đã gom và trip memory bỏ phần gom từ lúc xe dừng, điểm bắt đầu từ 0 | M68 | 08/10 |
| **Thêm** | Công cụ eval: khoảng tin cậy báo sai / giờ lấy mẫu lại theo người (`person_rate_ci`) và phân bố theo người; `python tools/uta_rldd.py tradeoff` (đường đánh đổi theo `risk.drowsy.l1` trên dev, một điểm trên test); mục 4b "điểm → phút"; dòng đơn vị + tỉ lệ dương trong báo cáo; khoá cấu hình `eval.bootstrap_resamples`, `bootstrap_seed`, `tradeoff_l1`, `score_band_width` | M69 | 08/10 |
| **Sửa** | Nền giao diện chung: nền tối #0A0A0A, font Inter tự đóng gói (thay Be Vietnam Pro), thẻ "kính"; bỏ giao diện sáng của dashboard | M57 | 07/10 |
| **Sửa** | HUD khi đang lái viết lại theo khung 1280 × 800: thẻ trạng thái L0–L3, thẻ "Độ mệt và thông số" (dải 15 phút), thẻ tốc độ, nút 72 px; chữ có màu thay cho số | M58 | 07/10 |
| **Sửa** | HUD sự cố, xin đồng ý, 3 bước đăng ký có khung căn mặt, tổng kết chuyến, "Bạn còn ở đó không?" vẽ lại; thêm màn cho các trạng thái bản thiết kế chưa vẽ (lý do tạm ngưng, mất phát hiện điện thoại, đăng ký thất bại) | M59 | 07/10 |
| **Sửa** | Web: một trang đăng nhập chung; menu trái và trang chủ theo vai trò thay cho thanh tab; mỗi trang có địa chỉ `#/dashboard/<trang>` | M60 | 07/10 |
| **Thêm** | Trang tài xế (tổng quan, chi tiết chuyến), trang quản lý (tổng quan đội xe, duyệt báo cáo), trang kỹ sư (thanh thay đổi chưa lưu, báo sai dạng thanh), trang quản trị (tạo tài khoản và thiết bị trên web, khoá hiện một lần) | M61–M63 | 07/10 |
| **Sửa** | `#/live` và `#/drive`: màn thiết lập 3 bước, màn đang tải, khung camera nhỏ 176 px, cùng phong cách mới | M64 | 07/10 |
| **Thêm** | Giọng nói tiếng Việt thu sẵn (Piper, 31 câu, ≈ 2 MB) cho mọi cảnh báo và thông báo; chạy offline, không dùng giọng đọc của trình duyệt (máy thử chỉ có giọng Anh) | M64 | 07/10 |
| **Thêm** | Edge agent đưa ra cho HUD `trip` (lái liên tục, độ mệt 15 phút), `incident` (từ lúc nào, số lần thử, đã báo chưa) và `alerts[].metrics`; khoá `hud.trend_minutes`. Tải lại HUD vẫn thấy đúng số | M65 | 07/10 |

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

### 2.9 Khối 8: liếc cộng dồn, gọi / nhắn tin, quay hẳn đi (M38)

- **Liếc ngắn cộng dồn:** liếc 1,5 s, nhìn lại 0,5 s, lặp mãi thì bộ đếm `off_road` liên tục về 0 mỗi lần và
  không bao giờ có cảnh báo. Nay khối 8 đo `off_road_ratio` (phần thời gian nhìn khỏi đường trong 30 s) và
  `glance_count`. **Chỉ đo:** ghi vào metadata cảnh báo, mẫu theo phút, bảng tổng kết chuyến, trace. Trên
  YawDD (xe đỗ, không ai mất tập trung theo nhãn) 6 % số clip có lúc tỉ lệ ≥ 0,3
  (`eval/results/glance_ratio.md`), nên chưa bật cảnh báo.
- **Gọi hay nhắn tin:** `phone_kind` = `call` (khung điện thoại bên cạnh mặt, từ cằm trở lên), `text` (dưới
  cằm), `unknown`. Ghi trong metadata cảnh báo `phone` và bảng tổng kết (`phone_call_s`, `phone_text_s`).
  Chưa đo được độ chính xác vì chưa có dữ liệu đúng góc camera.
- **Quay hẳn đi rồi mất mặt:** xem mục 3.3.
- Mọi ngưỡng mới (`distraction.glance.*`, `distraction.turned_away.*`, `phone.kind.*`) là tạm.

### 2.10 Công cụ ghi số từ camera (M39)

- `tools/record_trace.py record`: camera → khối 2–12 → mỗi frame một dòng số; bấm phím để đánh dấu hành
  động; `--tag` ghi điều kiện (khẩu trang, kính, ánh sáng). Không có ảnh nào được lưu, và công cụ từ chối
  lưu trace có cột không phải dãy số.
- `report`: độ trễ từ lúc bấm phím đến cảnh báo (p50 / p95, PRD ≤ 3 s), cảnh báo ngoài nhãn, nhìn xuống so
  với nhắm mắt, có / không khẩu trang, gọi / nhắn tin. Cách dùng: HowToUse mục 9.5.
- Bản ghi thật đầu tiên: mục 2.23 (M52).

### 2.11 Đo offline trên trace sẵn có (M40)

| Câu hỏi | Kết quả | Nhận định |
|---|---|---|
| `perclos_60s` có phải P80 không | Không: gần "P50", trộn xác suất CNN, bỏ frame ngáp / nói. FL3D theo frame: P80 nhận 77,3 % frame microsleep và 2,0 % frame alert; hiện tại 70,5 % và 2,6 % | Clip quá ngắn để luật PERCLOS chạy: chưa kết luận, ngưỡng không đổi |
| Tối thì kém đi bao nhiêu | FL3D, frame mặt tối < 60: recall mắt nhắm 40,3 % (466 frame) so với 92,6 % ở 60–100 | Ít frame; không so chéo dataset |
| Kính có làm tăng báo sai không | YawDD: 4,8 / 10,5 / 6,7 mỗi giờ (không kính / kính / kính râm), CI chồng nhau | Chưa kết luận được |
| Cá nhân hoá có giảm báo sai không | YawDD, 105 người: 7 cảnh báo sai (tự học) so với 9 (mốc đăng ký giả) | Chưa thấy lợi; cần UTA-RLDD |
| Báo sai tập trung ở ai, lúc nào | YawDD: 10 cảnh báo sai từ 10 / 106 người; 9 / 10 trong 30 s đầu clip | Clip chỉ dài ~20 s |

### 2.12 Phiên bản, tag, nhật ký truy cập (M41)

- `edge_agent/version.py`: app 3.0.0, phiên bản bộ ngưỡng đã tải, cờ bỏ qua bộ ngưỡng từ xa, 12 ký tự đầu
  SHA-256 của từng model. Backend lưu theo thiết bị và theo sự kiện; `GET /api/v1/fleet` thêm `versions`,
  `thresholds_current`, `thresholds_latest`.
- Sự kiện có `tags`. `forced` không bao giờ vào thống kê, số cảnh báo đội xe hay danh sách chuyến.
- Nhật ký truy cập: ai xem dữ liệu của tài xế nào (hoặc cả đội), sửa ngưỡng, tạo tài khoản / thiết bị, xoá
  dữ liệu. Database chặn lệnh sửa bảng này. Tài xế xem được ai đã xem dữ liệu của mình. Cùng một lượt xem
  ghi một lần mỗi 10 phút. Chi tiết: [data-policy.md](data-policy.md) mục 4.

### 2.13 Chạy dài và container giới hạn kiểu Jetson (M42)

Mọi số dưới đây đo trên CPU của máy dev (Mac ARM). Các dòng `simulated` chỉ giới hạn số nhân và RAM, không
tái hiện tốc độ từng nhân, GPU hay nhiệt của Jetson: là cận trên, không phải số đo của thiết bị
([`eval/results/benchmark_simulated.md`](../eval/results/benchmark_simulated.md)).

| Lần chạy (nhịp 30 FPS, clip YawDD có mặt) | Phút | FPS đạt | Độ trễ p95 | CPU trung bình (100 % = một nhân) | RAM đỉnh |
|---|---:|---:|---:|---:|---:|
| Mac dev, YOLO FP32 | 10 | 29,9 | 10,8 ms | 54 % | 601 MB |
| Container 4 CPU / 4 GB (`simulated`, kiểu Jetson Nano), FP32 | 10 | 29,9 | 11,1 ms | 93 % | 597 MB |
| Container 6 CPU / 8 GB (`simulated`, kiểu Orin Nano), FP32 | 5 | 30,0 | 10,9 ms | 89 % | 594 MB |
| Container 4 CPU / 4 GB (`simulated`), INT8 | 5 | 30,0 | 11,1 ms | 57 % | 562 MB |

- Mọi phút đều giữ được nhịp 30 FPS (ngưỡng `eval.soak_min_fps` là 15). RAM trong container tăng 21–66 MB / giờ
  tính trên tối đa 10 phút, cao hơn ngưỡng tạm 20 MB / giờ: quá ngắn để nói có rò rỉ hay không, cần chạy cả giờ.
  Không đọc được nhiệt độ ở cả hai nơi. Chưa có clip có điện thoại nên chưa chạy điều kiện đó.
- Lượng tử hoá ([`quantization.md`](../eval/results/quantization.md)): INT8 nhỏ hơn 3,6 lần. Trên macOS FP32
  nhanh hơn (16,6 so với 19,6 ms); trong container Linux arm64, FP32 mất 55 ms còn INT8 19 ms (chưa tìm hiểu
  vì sao). Độ chính xác của INT8 vẫn chưa đo, mặc định vẫn là FP32.
- MediaPipe 0.10.21 (bản máy dev đang dùng) không có wheel linux/arm64; image dùng 1.0.1 và OpenCV 5.0.0, chạy
  được với code hiện tại.
- `docker compose --profile edge up edge` chạy agent trên một video mẫu với giới hạn tài nguyên; dịch vụ
  `backend` trong compose vẫn là app mẫu của template, không phải backend DriverGuard.

### 2.14 Chất lượng frame: tạm ngưng giám sát có lý do (M43)

**Vì sao:** PRD FR-6 đòi báo "không giám sát được" khi ảnh xấu; trước đây chỉ có trường hợp mất mặt. Mặt quá
tối, quá chói hay mờ vẫn có landmark, và hệ thống cứ đoán từ đó.

- Sáu lý do: `no_face`, `camera_blocked`, `bad_angle` (ba lý do của việc mất mặt ≥ 3 s), `low_light`, `glare`,
  `blur` (mặt còn thấy, kéo dài ≥ 5 s). Chỉ khi xe chạy; khi đó không luật nào báo.
- Ngưỡng tạm trong `quality.*`, đặt theo phép thử của M46. Chưa có frame tối / chói / mờ thật để kiểm.
- Không đổi kết quả trên trace cũ (test hồi quy 36 video giữ nguyên).
- Chi tiết: [roadmap M43](roadmap.md#m43), [FMEA dòng 7](safety-fmea.md#7-tam-ngung-giam-sat).

### 2.15 Không phản ứng, ngủ gật lặp lại, "Bạn còn ở đó không?" (M44)

**Vì sao:** quản lý chỉ thấy báo cáo sau chuyến. Tài xế ngủ gật qua tiếng còi, hoặc gục ra khỏi khung hình,
thì lúc đó không ai biết ([FMEA dòng 6](safety-fmea.md#6-guc-ra-khoi-khung)).

- `unresponsive` (nhắm ≥ 6 s), `repeated_l3` (L3 lần thứ 3 trong 10 phút), `no_answer` (không trả lời câu hỏi
  trong 10 s). Cả ba và mọi L3 được gửi ngay, hiện ở "Cần chú ý ngay" của tab "Đội xe" trong 5 phút.
- Câu hỏi chỉ hiện khi camera **không thấy** tài xế, nên không bắt người đang lái và đang được giám sát phải
  nhìn hay chạm màn hình. Cả màn hình là một nút.
- Ngưỡng tạm: 6 s, 3 lần / 10 phút, hỏi sau 5 s tạm ngưng, chờ 10 s.
- Chi tiết: [roadmap M44](roadmap.md#m44).

### 2.16 Dung lượng tải lần đầu (M45)

- Bản web bỏ OpenCV; phần nó cần được viết bằng numpy (`edge_agent/perception/geometry.py`) và so với OpenCV
  trong test (lệch góc đầu < 0,05°). Thiết bị vẫn dùng OpenCV.
- `backend/static.py`: gzip làm sẵn lúc build image, cache một năm cho file có mã băm, `no-cache` cho phần còn
  lại.
- Khoảng 42 → 30 MB qua mạng ở lần đầu. YOLO INT8 (thêm ~8 MB nữa) không làm vì độ chính xác chưa đo.
- Chi tiết: [roadmap M45](roadmap.md#m45).

### 2.17 Cùng video, ánh sáng khác (M46)

- Báo cáo [`eval/results/lighting_transforms.md`](../eval/results/lighting_transforms.md): 8 video FL3D và 8
  clip YawDD, mỗi video chạy 12 lần với ánh sáng bị biến đổi trong RAM.
- **Phát hiện đáng lo nhất của đợt này:** trên thiết bị, khi mặt hơi tối (dưới 60 / 255) hoặc ảnh là xám, khối
  5 giao trạng thái mắt cho CNN và CNN gần như không bao giờ nói "nhắm": microsleep đạt L3 18 / 24 → 0 / 24,
  hệ thống vẫn báo đang giám sát. Chưa sửa; thành việc 7 trong [improvements.md](improvements.md#viec-cnn-toi)
  và [FMEA dòng 16](safety-fmea.md#16-cnn-mat-toi). Bản web không dính (dùng blendshape).
- Đây là ánh sáng nhân tạo trên video thật, chưa phải cabin tối hay camera IR thật.
- Chi tiết: [roadmap M46](roadmap.md#m46).

### 2.18 Ngưỡng: tải lại khi đỗ, áp thử, quay lui (M47)

- Xe hỏi lại mỗi `publisher.config_poll_s` (300 s) và chỉ đổi ngưỡng khi đỗ; tài xế không phải đăng ký lại.
- Kỹ sư lưu một phiên bản cho vài xe thử (nhập mã thiết bị), xem số cảnh báo và số lần báo sai của phiên bản
  đó, rồi bấm "Áp cho cả đội". Áp lại một phiên bản cũ là quay lui. Mọi bước vào nhật ký truy cập.
- OTA model chưa làm.
- Chi tiết: [roadmap M47](roadmap.md#m47).

### 2.19 Dữ liệu của tài xế (M48)

- Tài xế tự tải toàn bộ dữ liệu về mình và gửi yêu cầu xoá từ dashboard; admin xoá hoặc từ chối kèm lý do.
- Database không mã hoá ở mức ứng dụng (dựa vào nơi host); file chỉ chủ sở hữu đọc được; image không chứa bí
  mật hay database (có test).
- Hai mẫu giấy tờ cho đơn vị triển khai: [dpia-template.md](dpia-template.md),
  [driver-notice-template.md](driver-notice-template.md). Không phải tư vấn pháp lý.
- Chi tiết: [roadmap M48](roadmap.md#m48), [data-policy.md](data-policy.md) mục 5–7.

### 2.20 Tốc độ bản web: công cụ đo, góc đầu, đồng hồ từng chặng (M49)

- **Vì sao:** sản phẩm là APK bọc code web, nhưng `tools/benchmark.py` chỉ đo vòng lặp Python của thiết bị. Ở bản
  web, khối 6–14 chạy trong Pyodide và chậm hơn bản thiết bị khoảng 11 lần; ba phần tư thời gian đó là phép tính
  góc đầu viết bằng numpy (từ M45, khi bỏ OpenCV khỏi bản web).
- `tools/bench_web.py` đo đúng lời gọi mỗi frame của trang, trong CPython và trong Pyodide (Node), trên cùng chuỗi
  landmark; mỗi lần chạy là một dòng trong [`eval/results/benchmark_web.md`](../eval/results/benchmark_web.md).
- Góc đầu: đạo hàm giải tích và dừng sớm. Trên clip YawDD: 101 → 9,8 lần duyệt điểm mỗi frame, 1,97 → 0,61 ms
  (p95 2,70 → 0,88 ms). Kết quả lệch tối đa 7e-8 độ; test so với OpenCV giữ nguyên sai số cho phép 0,05 độ.
- `#/live` tự đo từng chặng của vòng lặp và gửi số theo heartbeat; quản lý / kỹ sư đọc ở cột "Tốc độ xử lý" của
  tab "Đội xe". Đây là cách lấy số của hub mà không cần cắm máy tính vào.
- **Chưa có:** số của điện thoại Android và hub. Số trong bảng là Node trên Mac, dùng để so các phiên bản code.
- Chi tiết: [roadmap M49](roadmap.md#m49).

### 2.21 Không phát hiện được điện thoại (M50)

- Kết quả YOLO cũ hơn 0,6 s vốn bị coi là "không rõ". Trên máy mà YOLO luôn chậm hơn thế, hoặc khi model không
  tải được, nhánh điện thoại tắt hẳn và không ai biết. Bản web chạy YOLO một luồng wasm, 175 ms mỗi lần trên Mac.
- Nay khi phần lớn 10 giây gần nhất không có kết quả mới, tài xế thấy chip "Không phát hiện được điện thoại",
  quản lý / kỹ sư thấy sự kiện hệ thống trong nhật ký. Mắt và hướng đầu vẫn được giám sát như thường.
- Ngưỡng `phone.unknown_window_s`, `unknown_ratio`, `unknown_clear_ratio` trong `thresholds.yaml`, tạm.
- Chi tiết: [roadmap M50](roadmap.md#m50), [safety-fmea.md](safety-fmea.md#17-yolo-qua-han) dòng 17.

---

### 2.22 Tốc độ `#/live` trong trình duyệt thật (M51)

- Lần đầu vòng lặp của bản web được đo trong trình duyệt thật, có mặt trong khung:
  [`eval/results/benchmark_live.md`](../eval/results/benchmark_live.md).
- Hai thứ đổi theo số đo: model mặt chọn CPU khi không có GPU thật; YOLO chạy hai luồng nhờ trang được cách ly.
- Hai thứ đo rồi không làm: đưa thẳng video cho MediaPipe (không lợi), chuyển vòng lặp sang Worker (chưa cần).
- Chi tiết: [roadmap M51](roadmap.md#m51).

### 2.23 Bản ghi đầu tiên từ camera (M52)

- Ba phiên ban ngày của một người (mắt và miệng, nhìn lệch, điện thoại), 20,2 phút, ghi bằng công cụ của M39.
  Báo cáo: [`eval/results/own_recordings.md`](../eval/results/own_recordings.md). Không đổi code hay ngưỡng.
- Độ trễ từ lúc bấm phím tới cảnh báo: ngủ gật p95 1,67 s (11 / 11); gọi điện 2,30–2,77 s (5 / 5); nhắn tin
  2,33–2,64 s (3 / 5); nhìn sang bên và quay ra sau 2,83–3,04 s (5 / 5).
- Hai chỗ hệ thống xử lý sai, chưa sửa: cúi nhìn điện thoại trên đùi bị báo L3 ngủ gật 3 / 4 lần và không lần
  nào ra "nhìn lệch"; nhìn bảng đồng hồ bằng mắt (đầu không đổi góc) không được thấy 0 / 3.
- `phone_kind` đúng ở mọi frame có điện thoại; gục đầu chỉ ra sự kiện `nod` 2 / 9 lần.
- Còn thiếu: người thứ hai và sáu phiên trong `docs/improvements.md` việc 1. Năm phiên tối đã ghi tối 06/10
  (chưa phân tích). Phiên chói / ngược sáng và phiên kính râm đã bỏ (06/10); việc phát hiện mắt bị che chuyển
  sang hoãn, FMEA dòng 5 vẫn mở.
- `tools/record_trace.py` thêm bảy phím nhãn cho các phiên còn lại: `m` giá đỡ thấp, `g` cần số, `j` / `k` liếc
  xuống / sang bên bằng mắt, `l` liếc ngắn lặp lại, `w` cúi kèm nhắm mắt thật, `v` nhìn gương (không mong cảnh
  báo). Bảng 4 của báo cáo có thêm các hàng này; số của các phiên đã ghi không đổi.

### 2.24 Đo trên 13 phiên tự ghi (M54)

- Thêm năm phiên tối, hai phiên điện thoại, nhìn xuống, liếc lặp lại, quay đầu một phần; báo cáo
  `eval/results/own_recordings.md` gồm 12 phiên, phiên INT8 để riêng. `tools/record_trace.py` thêm phím `p`.
- Nhìn xuống mà đầu không cúi (giá đỡ, bảng đồng hồ, cần số) không được thấy 0 / 12; liếc lặp lại 30 s không có cảnh
  báo 0 / 4, trong khi `off_road_ratio` của M38 tách nó rất rõ (0,55–0,67 so với tối đa 0,21).
- **Model INT8 không dùng được:** `yolov8n_int8.onnx` không phát hiện điện thoại nào (điểm lớp ra 0). Mặc định vẫn
  là FP32; không đổi gì trong bản web.
- Nhìn xuống bị báo L3 ngủ gật 7 / 30 lần: không ngưỡng hiện có nào sửa được mà không mất microsleep
  thật của FL3D, nên chưa đổi.
- Ngưỡng eyeBlink theo từng tài xế cho lỗi trên: thêm `DriverProfile.blink_closed` (bước nhắm mắt của đăng ký) và
  `drowsiness.microsleep_deep.enrolled_blink_ratio`, **mặc định 0 (tắt)**: ở 0,85 báo nhầm còn 2 / 30 nhưng FL3D mất 11
  / 77 microsleep thật. Không đổi hành vi khi để mặc định.
- Liếc ngắn cộng dồn: quyết định không bật luật cảnh báo; hai biến của M38 vẫn chỉ đo.
- Hướng mắt: `eyeLookDown` không dùng được, vị trí mống mắt có triển vọng; mới đo offline.
- Gọi điện 9 / 9 có cảnh báo, nhắn tin 6 / 11 và chậm hơn mốc 3 s.
- Chi tiết từng việc: `docs/improvements.md` nhóm 1.

### 2.26 Hướng mắt nhìn xuống, chỉ đo (M55)

- Khối 6 có thêm `iris_y`; khối 8 có thêm góc nhìn xuống (góc cúi đầu + mống mắt) và `gaze_down_duration`, ngưỡng ở
  `distraction.gaze.*`. Chỉ ghi vào trace; không cảnh báo, sự kiện hay metadata nào đổi.
- `tools/gaze_study.py` và [`eval/results/gaze_3mdad.md`](../eval/results/gaze_3mdad.md): 50 tài xế 3MDAD trong xe thật.
  Giữ 2 s ở 12°: bắt 7 / 50 và 13 / 50 lần nhắn tin (tay phải, tay trái), 0 / 50 khi lái bình thường; FL3D khoảng 2,6
  lần mỗi giờ ngoài microsleep. Chưa đủ để thành cảnh báo.
- Cũng từ phép đo này: nhắn tin tay trái gần như không được hệ thống thấy (`phone` 0 / 50, `off_road` 1 / 50).

### 2.27 Mốc mống mắt theo tài xế và bốn phép đo (M56)

- Bước nhìn đường của đăng ký ghi `DriverProfile.road_iris_y`; khối 8 dùng nó làm mốc cho góc nhìn xuống thay cho 5 s đầu
  lúc xe chạy (tài xế không đăng ký: như cũ). Vẫn chỉ đo. Trên bản tự ghi và 3MDAD số đo không đổi.
- Đo, không đổi code (chi tiết ở [roadmap M56](roadmap.md#m56)):
  - Ngữ cảnh điện thoại không gỡ được lỗi "nhìn xuống bị báo ngủ gật": chỉ 3 / 7 lần báo nhầm có điện thoại trong khung hình.
  - Quy tắc "đầu cúi" không che ngủ gật trên UTA-RLDD: tắt nó chỉ khác 1 / 212 cảnh báo L3.
  - Gục đầu và cúi nhìn đã tách được trên bản tự ghi (9 / 9 và 0 / 12); các lần sót là gục nông hơn ngưỡng 15°.
  - Góc nhìn xuống trên 6 người UTA-RLDD (2,8 giờ): bật 32 lần, 20 lần của một người, không có nhãn để biết đúng sai.
  - Bản đêm hồng ngoại của 3MDAD không dùng được: MediaPipe tìm ra mặt ở 3–8 % số frame.

### 2.28 Tốc độ `#/live`: YOLO trên WebGPU, nhịp chạy, khởi động (M67)

- Đo lại trước khi sửa: vòng lặp đã chạy theo tốc độ camera (30 FPS, mỗi frame bận 11–14 ms). Chỗ còn xa mục
  tiêu là kết quả của model điện thoại đã cũ bao lâu khi một frame dùng nó (p95 333 ms), và thứ tự tải lúc khởi động.
- Model điện thoại chạy bằng WebGPU khi trình duyệt có GPU thật: 94 → 17 ms mỗi lần, 10 lần / giây, CPU của trang
  109 → 32 % một nhân. Kết quả giống wasm tới 5 phần triệu trên 200 frame thật; không quyết định nào đổi.
- Máy không có GPU thật vẫn chạy wasm, nay đúng 5 lần / giây: tuổi kết quả p95 329 → 274 ms.
- Khởi động với cache trống nhanh hơn 0,4–0,6 s; cache ấm gần như không đổi (1,36 → 1,29 s).
- Số frame camera bị bỏ (0–4 %) không đổi: nguyên nhân là nhịp vẽ của trình duyệt, không phải vòng lặp bận.
- Bảng trước / sau: [`eval/results/benchmark_live.md`](../eval/results/benchmark_live.md) mục 4–5. Nhánh điện thoại
  trên 3MDAD: [`eval/results/phone_web_3mdad.md`](../eval/results/phone_web_3mdad.md).
- Chi tiết, những gì đã thử và bỏ: [roadmap M67](roadmap.md#m67).

### 2.29 UTA-RLDD đọc thêm ba cách (M69)

- Không đổi ngưỡng nào. Tập 24 người giữ riêng, ngưỡng hiện tại: **0,98 báo sai / giờ** (Poisson 0,27–2,51), **15 / 24**
  video `10` có cảnh báo buồn ngủ, **12 / 24** đạt L3.
- Lấy mẫu lại theo người: khoảng 0,00–3,02. Cả 4 lần báo sai là của một người trong 24, nên cỡ mẫu thật gần một người hơn
  bốn sự kiện. Không làm chỉ tiêu PRD (≤ 1,0 / giờ, tính cả cận trên) tới gần hơn.
- Quét `risk.drowsy.l1` chỉ trên dev: số người đạt L3 không đổi (12 / 24) từ 30 tới 60; `l1` ≥ 50 xuống dưới 1,0 báo sai
  / giờ và mất 2 người chỉ có cảnh báo L1. Không đổi `l1`.
- Tỉ lệ phút của video `10` tăng theo `drowsy_score`; chỗ gãy rõ nhất ở khoảng 20–40, một khoảng dưới mốc L1 = 40.
- Mỗi bảng báo cáo ghi đơn vị tính và tỉ lệ mẫu dương. Bảng và cách đọc: [`eval/results/dataset_uta_rldd.md`](../eval/results/dataset_uta_rldd.md)
  mục 8, [`eval/results/uta_rldd_tradeoff.md`](../eval/results/uta_rldd_tradeoff.md); chi tiết: [roadmap M69](roadmap.md#m69).

### 2.25 Đánh giá trên UTA-RLDD (M53)

Bộ đầu tiên có buồn ngủ thật, video dài và cùng một người ở ba mức (`0` tỉnh, `5`, `10` buồn ngủ).

- **Cách chạy:** trace khối 2–12 một lần trên Kaggle Notebook (`notebooks/uta_rldd_kaggle.ipynb`, ~16 giờ), giữ
  trace số ở `data/eval_traces/uta_rldd/`; mọi phép đo sau đó là replay khối 7–12 bằng `tools/uta_rldd.py`.
- **Tập kiểm tra giữ riêng theo người:** dò trên 24 người (fold 1–2), chấm một lần trên 24 người còn lại.
- **Số trước khi đổi ngưỡng, trên 24 người giữ riêng:** cảnh báo sai nhánh buồn ngủ 1,96 / giờ (CI 95 % 0,85–3,87)
  trên 4,08 giờ tỉnh táo; cùng người, điểm ở `10` cao hơn ở `0` với 22 / 24; video `10` có cảnh báo 17 / 24.
- **Tín hiệu:** PERCLOS và microsleep tách được hai mức; chớp chậm, nhướn mày, gục đầu thì không. PERCLOS theo P80
  không tốt hơn định nghĩa hiện tại. Thời lượng chớp yếu (16 / 24 người), khớp kết luận M35.
- **Cá nhân hoá:** mốc đăng ký giả không giảm báo sai (9 / 9 / 9 lần trên 48 người), như trên YawDD.
- **Xấp xỉ EU DDAW** sau khi đổi ngưỡng: 62,5 % (CI 90 % 45,8–76,7) trên 24 người giữ riêng.
- Chi tiết: `eval/results/dataset_uta_rldd.md`.

### 2.30 Giao diện mới so với v2 (M57–M65)

Theo hai bản thiết kế (HUD 21 màn hình, web 10 màn hình) và Design System "DriverGuard". Chỉ đổi `frontend/`, trừ M65
(edge agent đưa thêm số liệu ra HUD). Không đổi logic cảnh báo, backend và API. Tính năng v2 mà bản thiết kế chưa vẽ
(lý do tạm ngưng, "Bạn còn ở đó không?", mất phát hiện điện thoại, đăng ký thất bại) được vẽ thêm theo phong cách mới, không bỏ.

**Nền chung (M57)**

| Chỗ | v2 | v3 |
|---|---|---|
| Màu nền | Dashboard có giao diện sáng và tối theo máy; HUD nền #0A0C10 | Chỉ giao diện tối, nền #0A0A0A cho cả HUD và web; thẻ "kính" (`.glass`) và vệt sáng góc trên trái |
| Font | Be Vietnam Pro (HUD), font hệ thống (dashboard) | Inter tự đóng gói cho cả hai (có bộ chữ tiếng Việt, chạy được khi không có mạng); JetBrains Mono cho khoá cấu hình |
| Màu mức cảnh báo | xanh L0, vàng L1, cam L2, đỏ L3; xi nhan màu xanh ngọc | giữ bốn màu, xi nhan đổi sang vàng, đỏ L3 theo dải `#ef4444 → #991b1b`; chữ đậm 700 chỉ cho câu L2 / L3 |
| Lỗi tương phản | — | bỏ chữ đen trong ô nhập, nền trắng trong giao diện tối, chữ cam tối trên nền tối (có trong bản thiết kế) |

**HUD trong xe (M58, M59)**

| Chỗ | v2 | v3 |
|---|---|---|
| Bố cục | co giãn tự do theo màn hình | khung cố định 1280 × 800, phóng to / thu nhỏ theo màn hình; màn hình dọc từ 640 px có khung 800 × 1 280 riêng (từ v4, M89), điện thoại xếp dọc |
| Thanh trên | tên, trạng thái, âm thanh, kết thúc chuyến | cao 72 px: DRIVERGUARD, camera, âm thanh, mô phỏng, dashboard, giờ |
| Thẻ trạng thái | tiêu đề và mô tả | huy hiệu tròn đặc, câu trạng thái 96 px, hai ô "Lái liên tục" và "Cảnh báo gần nhất"; L1 thẻ vàng, L2 thẻ cam đặc, L3 màn đỏ toàn phần |
| Độ mệt, thông số | — | thẻ mới: buồn ngủ, chú ý đường, mắt nói bằng chữ có màu ("Tỉnh táo · Hơi mệt · Rất mệt", "Tập trung · Nhìn lệch · Cầm điện thoại"), dải 15 phút "Độ mệt từng phút" lấy từ edge agent (M65) |
| Thẻ xe | dải "Tín hiệu xe" dưới thanh trên | thẻ tốc độ hình bát giác, xi nhan, ô "D" (đang lái) / "P" (đang đỗ); chip chỉ hiện khi mất hoặc chưa có tín hiệu xe |
| Nút khi lái | nút thường | cao 72 px, chữ 20 px ("Cảnh báo này sai?", "Đổi tài xế", "Kết thúc chuyến") |
| Xin đồng ý, đăng ký | màn xin đồng ý và 3 bước chữ + giọng nói | thẻ xanh dương toàn khung, chữ 76 px, thanh tiến độ, khung căn mặt (oval vạch đứt, mặt quay ra đường ở bước 2, mắt nhắm ở bước 3) |
| Không giám sát | một kiểu "Tạm ngưng" | thẻ vàng nâu + chip "KHÔNG giám sát", chữ 80 px; phân biệt "camera vẫn chạy nhưng không thấy mặt" với "không nhận được hình"; mất camera, lỗi xử lý có "Từ HH:MM", "Lần thử N", "Đã báo"; mất kết nối là thẻ xanh dương (lỗi thiết bị, không phải tài xế) |
| "Bạn còn ở đó không?" | (chưa có, thêm ở M44) | cả thẻ là một nút, vàng khi đang hỏi và đếm ngược, đỏ khi không ai trả lời, chữ 92 px |
| Tổng kết chuyến | bảng tổng kết | thẻ đánh giá theo màu chuyến, 4 ô số liệu, biểu đồ tối đa 65 cột có trục giờ, ô gợi ý, nút "Xong" |
| Giọng nói | giọng đọc của trình duyệt (có thể ra giọng Anh) | file thu sẵn tiếng Việt, nói sau tiếng chuông 0,7 s; thiếu file thì dùng giọng Việt của máy, không bao giờ dùng giọng Anh |

Giữ nguyên: không hiện mã L0–L3 trên HUD, L3 không có nút, ban đêm L0–L1 dịu 80 %, L3 nhấp nháy 1 Hz, dải vàng
"Âm thanh cảnh báo chưa bật". Bỏ nhãn vùng tốc độ "Nhanh" / "Rất nhanh". Khung khuôn mặt trên HUD thiết bị là hình
minh hoạ (ghi rõ trên màn hình): HUD không bao giờ nhận ảnh camera. Trong `#/live` khung này hiện hình camera thật của
trang, chỉ trong bộ nhớ.

**Web (M60–M64)**

| Chỗ | v2 | v3 |
|---|---|---|
| Đăng nhập | một thẻ nhỏ giữa trang | hai cột: giới thiệu + "Không lưu ảnh khuôn mặt" + "Dữ liệu có hạn dùng" (số ngày lấy từ `/api/v1/policy`); nút Hiện / Ẩn mật khẩu; thẻ "Chạy thử bằng camera trên máy này" |
| Điều hướng | thanh tab chung (Nhật ký sự kiện, Đội xe, Timeline mệt mỏi, Báo cáo chuyến đi, Ngưỡng) | menu trái 248 px theo vai trò, mỗi trang có địa chỉ `#/dashboard/<trang>`; số báo cáo chưa xem hiện trên menu |
| Tài xế | vào tab Nhật ký sự kiện | Tổng quan (chuyến gần nhất, 30 ngày qua, gợi ý), Chuyến đi của tôi và chi tiết từng chuyến (6 ô số liệu, biểu đồ có trục giờ, "Các lần được nhắc"), Lịch sử cảnh báo, Dữ liệu của tôi |
| Quản lý | tab Đội xe, bảng báo cáo | Tổng quan đội xe (số liệu hôm nay, mục "Cần xử lý" có tiếng chuông, bảng từng xe có lọc và tìm kiếm); Báo cáo chuyến thành trang duyệt: danh sách bên trái, một báo cáo bên phải, "Đánh dấu đã xem" |
| Kỹ sư | tab Ngưỡng | thanh "N thay đổi chưa lưu · Hoàn tác · Lưu thành phiên bản N+1", ô đã sửa viền xanh kèm giá trị trước, báo sai theo lý do dạng thanh ngang (từ 20 % tô cam sáng); giữ áp thử / quay lui (M47) |
| Quản trị | tạo tài khoản và thiết bị bằng lệnh `backend.manage` | tạo tài khoản và thiết bị ngay trên web; khoá thiết bị hiện đúng một lần kèm nút "Sao chép", không lưu lại |
| `#/live` | một trang giới thiệu, tải 2 bước | thiết lập 3 bước đánh số ("Ai đang lái?", "Đăng ký khuôn mặt · khoảng 10 giây", "Bắt đầu"), màn đang tải ghi dung lượng thật (≈ 30 MB), khung camera nhỏ 176 px, ba nút icon có nhãn |
| `#/drive` | trang điều khiển | cùng nút, cùng phím tắt, đổi sang thẻ kính |

Trang "Nhật ký sự kiện", "Timeline mệt mỏi", "Đội xe" chi tiết, "Lịch sử cảnh báo" và "Dữ liệu của tôi" giữ nguyên bảng
của v2 trong khung mới (chỉ đổi màu và khung), chưa vẽ lại theo bản thiết kế.

**Số liệu hỗ trợ giao diện (M65)** nằm ở edge agent, không ở trình duyệt, vì HUD trong xe phải chạy khi mất mạng và
tải lại trang phải thấy ngay số đúng: `trip` (`drive_run_s`, `driving_s`, `score_l1`, `score_l2`, `recent_minutes`),
`incident` (`kind`, `since`, `attempts`, `reported`) và `alerts[].metrics` (`off_road_s`, `eyes_closed_s`,
`phone_ratio`, `turn_signal`). Phút không có frame hoặc bước nhắm mắt của đăng ký là `null`, vẽ thành khoảng trống chứ
không phải 0. Bản web và thiết bị chạy không có `--backend`: `reported` là `null` và HUD ẩn dòng "Đã báo cho quản lý".
Chi phí `hud_view(15)` 7,9 µs mỗi frame.

**Tốc độ `#/live` sau khi đổi giao diện** (Chromium không GPU, camera giả 30 s): 21 → 20 FPS ở M57, 21 FPS ở M64; cả
frame p50 12,9 → 16,5 ms, p95 23,8 → 29,7 ms. Vẫn xa ngân sách 66 ms của 15 FPS, nhưng chưa đo màn đang lái có kính mờ
trên máy yếu thật.

Chi tiết từng mốc: [roadmap M57–M65](roadmap.md#m57).

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

### 3.3 Quay hẳn ra sau không còn bị coi là "tạm ngưng giám sát" sau 3 s (M38)

Trước: tài xế quay hẳn ra ghế sau, camera mất mặt; sau một cảnh báo L2 `off_road`, đủ 3 s mất mặt thì hệ
thống chuyển sang "tạm ngưng giám sát" và im, dù tài xế vẫn chưa nhìn đường (đã viết test tái hiện). Nay
nếu mặt mất ngay sau một tư thế còn tin được (cũ nhất 0,5 s) đang nhìn khỏi đường và quay quá 45°, khối 8
coi là đang quay đi: `off_road` chạy tiếp, HUD giữ L2 "Nhìn về phía trước" tối đa 10 s, rồi mới tạm ngưng.
Mất mặt khi đang nhìn thẳng (che camera, chói), quay nhẹ, hoặc quay về phía đang xi nhan: như cũ. Không
thêm cảnh báo mới: replay SUST, YawDD, FL3D cho cùng danh sách cảnh báo. Bảng tổng kết tách `turned_away_s`
khỏi `unavailable_s`. Ngưỡng tạm; `distraction.turned_away.yaw_deg: 0` là tắt.

---

### 3.4 Frame không có mặt trên `#/live` không còn là "Lỗi xử lý" (M50)

- **Trước:** trang đưa `null` cho Python khi không có mặt. Trong Pyodide `null` là một giá trị riêng (`JsNull`),
  không phải `None`, nên mỗi frame không có mặt lỗi ở bước đổi mảng; sau 1 s HUD báo "Lỗi xử lý" kèm âm báo to
  và backend nhận `agent_error`. Các trạng thái "tạm ngưng giám sát: không thấy mặt / camera bị che" và câu hỏi
  "Bạn còn ở đó không?" vì thế không xuất hiện trên bản web.
- **Nay:** trang gửi `undefined`, và bridge coi `JsNull` là `None`.
- Lỗi lộ ra khi chạy bản build thật trong trình duyệt với camera không có mặt; e2e trước đó luôn có mặt tổng hợp.

### 3.5 Âm thanh cảnh báo của `#/live` không chờ vòng hỏi; giờ của frame là giờ chụp (M50)

- HUD vẫn hỏi trạng thái 300 ms một lần để hiển thị, nhưng cảnh báo mới được đẩy sang ngay trong frame phát ra nó.
- Giờ của frame lấy từ camera (`captureTime`) khi trình duyệt cho; không có thì như cũ.

### 3.6 Mặt tối không còn giao trạng thái mắt cho CNN (M54)

Trước: mặt tối hơn 60 / 255 thì khối 5 dùng CNN mắt thay EAR. Trên bản ghi thật ở mức sáng 32–35, CNN nói "nhắm" khi
mắt đang mở: 8 lần còi L3 sai trong 5,5 phút ngồi yên; trên video làm tối nhân tạo thì nó bỏ sót mọi lần nhắm mắt.
Nay `eye_state.low_light_brightness` = 0: EAR quyết định. Cùng bản ghi: 0 lần L3 sai, nhắm mắt vẫn L3 27 / 27; FL3D
làm tối 0 / 24 → 12 / 24. Mặt tối hơn 25 vẫn là "tạm ngưng giám sát". Ảnh xám / hồng ngoại không đổi (vẫn CNN).
Ngưỡng tạm: một người, một webcam.

### 3.8 Bản web / APK: `eyeBlink` có ngưỡng riêng (M56)

Trước: bản web dùng blendshape `eyeBlink` thay CNN mắt ở các frame khối 5 quyết định, nhưng khối 7 so nó với ngưỡng của
CNN (0,6 / 0,4 / 0,8). Mắt nhắm thật chỉ cho `eyeBlink` 0,55–0,7. Với camera xám / hồng ngoại, nơi mọi frame đi đường này,
replay cho nhắm mắt đạt L3 0 / 48 trên bản tự ghi và 0 / 95 trên FL3D. Nay khối 5 ghi nguồn điểm
(`FrameFeatures.p_closed_source`) và khối 7 dùng `drowsiness.eye.blendshape_closed` 0,4, `blendshape_open` 0,3,
`drowsiness.microsleep_deep.blendshape` 0,55: 46 / 48 và 64 / 95 (đường EAR của thiết bị: 47 / 48 và 74 / 95); UTA-RLDD video
tỉnh 0,50 cảnh báo buồn ngủ mỗi giờ (thiết bị 1,13). Camera màu: gần như không đổi (FL3D 75 → 76 / 95, YawDD L3 0 → 1).
Bản thiết bị không đổi. Ngưỡng tạm: replay trên video màu, chưa đo trên `#/live`, chưa có ảnh IR thật.

### 3.9 Đăng ký xong thì điểm buồn ngủ bắt đầu từ 0 (M68)

Trước: bước nhắm mắt của đăng ký không sinh cảnh báo và không vào trip memory, nhưng `drowsy_score` vẫn được tính trong
4 s đó (lên 25 trên HUD), và những gì khối 7 gom trước bước nhắm mắt vẫn ở lại sau khi đăng ký: nhắm mắt 1,5 s lúc đang
đỗ để lại PERCLOS 0,09 và 25 điểm trong 5 phút. Nay điểm và các số hạng đọc 0 khi đánh giá buồn ngủ đang tắt; đăng ký
xong (hết `enrollment.reopen_grace_s`) thì khối 7 bỏ toàn bộ cửa sổ và trip memory bỏ phần gom từ lúc xe dừng lần đó.
Phần trip memory của lúc đang lái trước lần dừng được giữ: đăng ký muộn sau một microsleep thật thì điểm vẫn 25 trong
5 phút. Số đo thô (PERCLOS) trong 4 s đó và bảng tổng kết chuyến không đổi. Chi tiết: [roadmap M68](roadmap.md#m68).

### 3.7 Chớp chậm, nhướn mày không còn cộng vào điểm; `trend` chỉ ghi nhận (M53)

Trước: `drowsy_score` cộng thêm chớp chậm và nhướn mày (mỗi cái trọng số 10, ghi là tạm), và điểm tăng dần qua
nhiều phút thì phát L1 "nên nghỉ ở trạm dừng tới" (`trend`). Trên UTA-RLDD, hai tín hiệu không phân biệt được tỉnh
với buồn ngủ trên cùng một người, và `trend` có mặt trong 5 / 9 cảnh báo sai (dev), 3 / 8 (giữ riêng). Nay
`risk.drowsy.weight_slow_blink` = 0, `risk.drowsy.weight_brow` = 0, `risk.trend.level` = 0. Trên 24 người giữ
riêng: cảnh báo sai 8 → 4 lần (1,96 → 0,98 / giờ), số người buồn ngủ đạt L3 vẫn 12 / 24; có cảnh báo bất kỳ 17 → 15.
FL3D: cảnh báo microsleep không đổi, L2 đúng 15 → 13. Hai tín hiệu vẫn được đo và ghi vào metadata. Tài xế không
còn nhận cảnh báo "Mệt mỏi tăng dần"; sự kiện cũ vẫn hiển thị được. Video UTA-RLDD chỉ 10 phút: `trend` có ích
trên chuyến dài hay không thì chưa đo, bật lại bằng `risk.trend.level: 1`.

## 4. Tương thích khi nâng cấp từ v2.2

- **M67:** hai khoá mới `phone.web_gpu` (true) và `phone.web_gpu_target_fps` (10); file `thresholds.yaml` cũ thiếu
  chúng vẫn chạy với giá trị mặc định trong code. Muốn giữ cách cũ: `phone.web_gpu: false`. Bản web phải build lại
  (`npm run prepare-live` rồi `vite build`); bản build có thêm một runtime của ONNX Runtime (26,8 MB, nén 6,7 MB),
  chỉ trình duyệt có GPU thật mới tải. Nhịp "còn sống" của trang có thêm `perf.yolo_provider`: **backend trước**,
  vì backend cũ từ chối trường lạ và nhịp đó bị bỏ (frontend và backend chung một image thì không gặp).
  Trang cần trình duyệt chạy được worker dạng module. Bản thiết bị không đổi.

- **Giao diện mới (M57–M65):** không cần backend mới, không đổi bảng database. Bản web phải build lại (`npm run build`).
  Dashboard mất giao diện sáng (không còn tuỳ chọn theo máy). Địa chỉ của trang mà vai trò không có thì về trang chủ của vai trò. Server HUD của thiết bị trả thêm `trip`, `incident`, `alerts[].metrics` ở `GET /state` (HUD cũ bỏ qua);
  khoá mới `hud.trend_minutes` (15), file `thresholds.yaml` cũ thiếu khoá vẫn chạy. Giọng nói thu sẵn nằm ở
  `frontend/public/voice/` (≈ 2 MB, đã commit); đổi câu trong `voice-lines.json` thì phải chạy lại
  `python tools/make_voice.py`, test `voice.test.ts` đỏ nếu quên. Font Inter và JetBrains Mono nằm trong bản build, không
  tải từ Google Fonts.

- **Ngưỡng mới (M56):** `drowsiness.eye.blendshape_closed`, `drowsiness.eye.blendshape_open`,
  `drowsiness.microsleep_deep.blendshape`. File `thresholds.yaml` cũ thiếu ba khoá này vẫn chạy với giá trị mặc định
  trong code (0,4 / 0,3 / 0,55). Bản web phải build lại gói Python (`npm run prepare-live`) mới có thay đổi.

- **Header cách ly (M51):** mọi file của web app nay có COOP `same-origin` và COEP `require-corp`. Tài nguyên
  nhúng từ nguồn khác phải cho phép CORS hoặc có `Cross-Origin-Resource-Policy`; hiện chỉ có Pyodide và
  MediaPipe từ jsDelivr, đã thử chạy được. Thêm ảnh / script từ nguồn khác về sau phải kiểm điều này.

- **Deploy backend trước, rồi mới tới agent.** Backend v2.2 từ chối trường `heartbeat` và lý do
  `repeated_l1` (422):
  - nhịp bị bỏ (thiết bị ghi một dòng cảnh báo vào log), sự kiện khác vẫn gửi được;
  - sự kiện L2 có `repeated_l1` bị backend cũ từ chối và mất.
  Bản web không gặp vì frontend và backend nằm chung một image.
- **M38–M41 cũng cần backend trước.** Sự kiện mới có thêm `tags`, `versions` và các số đo `phone_kind`,
  `off_road_ratio`, `glance_count`, `perclos_p80`; bản tổng kết có thêm `phone_call_s`, `phone_text_s`,
  `glances`, `off_road_ratio_max`, `turned_away_s`. Backend cũ từ chối (422) và thiết bị bỏ các bản ghi đó.
  Backend mới vẫn nhận agent cũ.
- Database: bảng `device_status` tự tạo khi backend khởi động; không đổi bảng cũ. M38 / M41 thêm cột
  (`fatigue_samples.off_road_ratio`, `events.tags`, `events.versions`, `device_status.versions`) và bảng
  `access_log`; database cũ được nâng tự động lúc khởi động, có test.
- Agent cũ gửi lên backend mới: vẫn nhận; xe hiện "Đang hoạt động" khi có dữ liệu, cột giám sát ghi
  "Không rõ".
- Thiết bị đã có dữ liệu trước M33 nhưng chưa đăng ký trong bảng `devices` (trình duyệt) chỉ hiện ở tab
  "Đội xe" sau lần gửi đầu tiên với bản mới.
- Ngưỡng mới trong `config/thresholds.yaml`: `alert.l1_repeat_count`, `alert.l1_repeat_window_s`,
  `publisher.heartbeat_interval_s`, `publisher.heartbeat_stalled_s`. Chưa đưa lên tab "Ngưỡng".
- Web: phải build lại `#/live` (`npm run prepare-live`) để trình duyệt nhận code Python mới. Từ M41 bước
  này còn ghi mã model vào gói (`config/build_info.json`); `Dockerfile.railway` đã chép model vào bước đó.
- Biến môi trường mới của backend: `DG_RETENTION_ACCESS_LOG_DAYS` (365), `DG_AUDIT_DEDUPE_S` (600).
- Ngưỡng mới (M38–M42), chưa đưa lên tab "Ngưỡng": `distraction.glance.*`, `distraction.turned_away.*`,
  `phone.kind.*`, `drowsiness.perclos_p80_aperture`, và các khoá chỉ dùng cho công cụ đo trong `eval`.
- Công cụ `tools/benchmark.py --duration` cần `psutil` (đã thêm vào `requirements.txt`).
- **M43–M48 cũng cần backend trước.** Lý do mới (`unresponsive`, `repeated_l3`, `no_answer`, `config_applied`,
  `config_refused`), `metrics.cause` và `unavailable_by_cause` bị backend cũ từ chối (422). Backend mới vẫn
  nhận agent cũ.
- Database (M47, M48): ba bảng mới tự tạo (`threshold_rollout`, `threshold_pins`, `deletion_requests`); không
  đổi bảng cũ. Chưa có dòng nào trong `threshold_rollout` thì phiên bản ngưỡng mới nhất là của cả đội, như
  trước. Lúc khởi động backend đặt quyền file database thành 0600.
- **Hành vi đổi với tài xế (M43, M44):** ảnh quá tối / chói / mờ ≥ 5 s khi xe chạy nay là "tạm ngưng giám
  sát" thay vì tiếp tục cảnh báo; nhắm mắt ≥ 6 s có thêm một cảnh báo L3; mất mặt 8 s thì màn hình hỏi. Muốn
  tắt từng phần: `quality.enabled: false`, `risk.unavailable.low_quality_s: 0`, `risk.unresponsive.closed_s: 0`,
  `alert.l3_repeat_count: 0`, `presence.enabled: false`.
- **Ngưỡng đổi giữa chuyến (M47):** trước đây chỉ áp khi khởi động lại; nay xe đang chạy bản này sẽ nhận
  phiên bản mới ở lần đỗ kế tiếp (trong vòng 5 phút sau khi lưu). `publisher.config_poll_s: 0` để giữ cách cũ.
- Ngưỡng mới (M43–M47), chưa đưa lên tab "Ngưỡng": `quality.*`, `risk.unavailable.low_quality_s`,
  `risk.unresponsive.closed_s`, `alert.l3_repeat_count`, `alert.l3_repeat_window_s`, `presence.*`,
  `publisher.config_poll_s`, `eval.light_*`.
- Biến môi trường mới của backend: `DG_FLEET_URGENT_WINDOW_S` (300).
- Deploy (M45): `deploy/railway_app.py` dùng `backend.static.CachedStaticFiles`; `Dockerfile.railway` thêm bước
  `python -m backend.static /app/static`. Bản web phải build lại (`npm run prepare-live`): gói Python mới không
  còn cần OpenCV, gói cũ chạy với trang mới sẽ lỗi vì trang không tải OpenCV nữa.
- Tab của tài xế đổi tên: "Ai đã xem dữ liệu của tôi" → "Dữ liệu của tôi".
- **Tự xoá dữ liệu bật mặc định (M37).** Sau khi deploy, backend xoá cảnh báo / mẫu cũ hơn 60 ngày và
  bản tổng kết cũ hơn 365 ngày ngay lúc khởi động, không khôi phục được ngoài bản sao lưu. Bản ghi
  cũ nhất trong database trên máy dev là 25/09/2026, tức khoảng 24/11/2026 mới có bản ghi đầu tiên quá
  hạn; database đang chạy trên Railway chưa được kiểm tra. Muốn giữ tất cả: đặt `DG_RETENTION_EVENTS_DAYS=0` và `DG_RETENTION_SUMMARIES_DAYS=0` trước khi
  deploy.
- **Ba ngưỡng đổi mặc định (M53):** `risk.drowsy.weight_slow_blink` và `weight_brow` 10 → 0, `risk.trend.level`
  1 → 0. Ba khoá này không nằm trong nhóm chỉnh được từ dashboard, nên mọi xe nhận số mới khi cập nhật bản này.
  Bản web phải build lại gói Python (`npm run prepare-live`).
- Test hồi quy (M34) mới chạy trên Mac ARM. Nếu CI (Linux x86) cho kết quả lệch ở mức làm tròn số thực,
  chạy `tools/regression_traces.py update` trên CI / Linux và ghi lý do.

---

## 5. Kiểm thử

| | v2.2 | v3 |
|---|---:|---:|
| Test Python | 585 | **657** |
| Test frontend | 50 | **56** |
| Test end-to-end (Playwright) | 3 | **3** (kịch bản thứ hai thêm bước xem tab "Đội xe") |

- Cột v3 của bảng là số ngày 05/10. **Số cuối của v3 (08/10, sau M69):** 993 test Python pass; lần chạy cả ba bộ gần
  nhất là sau khi gộp `main` và M67: 982 Python + 138 frontend + 4 e2e pass. Số của các mốc sau đó ở
  [release-v4.md mục 5](release-v4.md#5-kiểm-thử).
- Số v3 gồm cả 1 test của thay đổi "Lỗi gần nhất" trên `#/live` làm sau v2.2 (chưa commit).
- M57–M65 (giao diện): frontend 50 → 95 (M57) → 112 (M63); thêm `m58.test.ts`, `nav.test.ts`, `driverModel.test.ts`,
  `voice.test.ts`; e2e 4 / 4 pass sau khi đổi theo giao diện mới. Sau khi gộp `main` và M67: 982 Python + 138 frontend + 4 e2e pass.
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

**Sau M69 (08/10):** 993 test Python pass (9 test mới bằng chuỗi số giả, trong đó khoảng tin cậy theo người, điểm làm việc, khoảng điểm); ruff sạch ở phần đã đổi; test hồi quy trace không phải chốt lại. Frontend không đổi, không chạy lại.

**Sau M68 (08/10):** 984 test Python pass (2 test mới bằng chuỗi số giả, đỏ trước khi sửa); ruff / format sạch; test hồi quy trace không phải chốt lại. Frontend không đổi, không chạy lại.

**Sau M67 (08/10):** 965 test Python, 115 test frontend, 4 e2e pass; ruff, typecheck, build sạch; test hồi quy trace không phải chốt lại. Báo cáo replay của FL3D / YawDD / SUST và của bản tự ghi giống hệt trước và sau. Chạy dài 10 phút của `#/live`: bản mới FAIL hai lần đầu (vòng lặp ngừng nhận frame), đạt hai lần chạy lại; nguyên nhân chưa xác định ([`benchmark_live.md`](../eval/results/benchmark_live.md) mục 5).

**Sau M56 (07/10):** 953 test Python pass (9 test mới bằng chuỗi số giả); test hồi quy trace không phải chốt lại. `ruff`
sạch ở `edge_agent/`, `tools/`, `tests/`; 8 lỗi có sẵn ở `scripts/` chưa sửa. Test frontend và e2e không chạy lại: không đổi
code frontend, và bản web chưa build lại.

**Sau M53 (06/10):** 928 test Python pass (12 test mới của `tools/uta_rldd.py` bằng chuỗi số giả); ruff sạch. Test
hồi quy trace được chốt lại một lần có lý do (hai video FL3D có `drowsy_score` thấp hơn, sự kiện và cảnh báo không
đổi). Test frontend và e2e không chạy lại: không đổi code frontend.

---

**Sau M38–M42 (06/10):** 793 test Python, 67 test frontend, 3 e2e đều pass; ruff, typecheck, build sạch. Một test có sẵn từ trước, `test_backend_gets_the_status_not_the_profile`, thỉnh thoảng đỏ vì chuỗi "1.5" tình cờ xuất hiện trong dấu thời gian của sự kiện; không liên quan các mốc này và chưa sửa.

**Sau M43–M48 (06/10):** 879 test Python, 75 test frontend, 3 e2e đều pass; ruff, typecheck, build sạch. E2e chạy
trên máy dev với Pyodide thật, không có OpenCV. Test hồi quy trace được chốt lại một lần có lý do (M44:
`repeated_l3` trên một video). Test danh sách endpoint được sửa có chủ ý cho 7 endpoint mới.

**Sau M49 (06/10):** 894 test Python, 83 test frontend, 3 e2e đều pass; ruff, typecheck, build sạch. Test hồi
quy trace không phải chốt lại. E2e kiểm thêm: số đo tốc độ của `#/live` tới được cột "Tốc độ xử lý".

**Sau M50 (06/10):** 909 test Python, 90 test frontend, 4 e2e đều pass; ruff, typecheck, build sạch. Thêm một
lần chạy tay bản build thật (MediaPipe + YOLO) trong Chromium không giao diện với camera giả.

**Sau M51 (06/10):** 911 test Python, 95 test frontend, 4 e2e đều pass (e2e chạy trên trang đã cách ly); ruff,
typecheck, build sạch.

## 6. Giới hạn đã biết

- **Audit 08/10** nêu thêm giới hạn của chính các mốc trong file này; kết quả audit, các việc đã làm theo nó (M70–M90)
  và giới hạn còn lại ghi ở [release-v4.md](release-v4.md).
- **M68, M69 đã commit và gộp `main` (08/10), chưa deploy.**

- **Giao diện mới (M57–M65):** chưa ai thử trên màn hình thật của xe VF e34 (1280 × 800 phóng to / thu nhỏ theo màn
  hình; kính mờ chưa đo FPS trên máy yếu). Dashboard mới chỉ xem bằng backend tạm với dữ liệu giả lập. Năm trang
  (Nhật ký sự kiện, Timeline, Đội xe chi tiết, Lịch sử cảnh báo, Dữ liệu của tôi) còn bảng cũ trong khung mới. Màn đăng
  ký không có nút "Huỷ" của bản thiết kế vì edge agent chưa có lệnh huỷ giữa chừng. Màn đang chạy của `#/live`
  không chia bước chuẩn bị thành môi trường / model mặt / model điện thoại như bản thiết kế, vì agent chỉ báo tỉ lệ chung.

- **M67, chưa giải thích được:** hai lần chạy dài 10 phút đầu tiên của bản mới ngừng nhận frame giữa chừng; bốn lần chạy
  sau đó (2 lần 10 phút, 2 lần 15 phút chạy cùng bản cũ) không lặp lại. Dấu hiệu nghiêng về trình duyệt ngừng trình chiếu
  video khi máy không ai dùng, nhưng chưa chứng minh được.
- **M67:** mọi số là Chromium không giao diện trên một máy Mac với camera giả; chưa đo camera thật, trình duyệt có
  giao diện, Windows / Linux, GPU yếu, hay hub. WebGPU mới chạy trên Metal. Không có GPU thật thì tuổi kết quả
  điện thoại p95 vẫn 274 ms (mục tiêu đề ra 250). Frame camera bị bỏ 0–4 % chưa sửa. Phép đo nhánh điện thoại trên
  3MDAD là đoạn diễn 3–5 giây: không thấy lịch chạy mới làm đổi recall hay báo sai, nhưng cũng không đủ để loại
  trừ một thay đổi nhỏ (1–2 cảnh báo sai trên 6 lượt so với 0, cùng một tài xế đang uống nước).

- **M56:** ngưỡng `eyeBlink` dò và báo cáo trên cùng các bộ dữ liệu, bằng replay video màu chạy như thể camera xám; chưa
  chạy trên `#/live`, chưa có ảnh IR thật. Với camera xám / IR bản web vẫn kém đường EAR của thiết bị (FL3D 64 so với
  74 / 95; UTA-RLDD 19 so với 24 / 48 người buồn ngủ có L3). Trên ảnh IR của 3MDAD MediaPipe gần như không tìm ra mặt:
  chưa biết camera IR sẽ dùng có như vậy không.

- **M53:** ngưỡng đổi theo UTA-RLDD, là người ngồi trước laptop, video 10 phút, nhãn tự đánh giá cho cả video. Chỉ
  tiêu PRD ≤ 1,0 báo sai / giờ chưa kết luận được (0,98 / giờ, cận trên CI 2,51). Mỗi fold có 2 / 24 người buồn
  ngủ mất cảnh báo duy nhất. `trend` chưa được đo trên chuyến dài. Kaggle chạy MediaPipe 1.0.1, các báo cáo khác
  0.10.21.

- **M52:** một người, một buổi, diễn trước laptop, mỗi loại hành động 2–11 mẫu. Cúi nhìn điện thoại bị báo nhầm
  là ngủ gật và nhìn bảng đồng hồ không được thấy: đã đo, chưa sửa (việc 2, 3 trong improvements.md).

- **M51:** số đo là Chromium không giao diện trên Mac. Chưa kiểm header cách ly trong WebView của APK; chưa đo
  máy 4 nhân; một GPU thật nhưng rất yếu vẫn được chọn delegate GPU.

- **M50:** ngưỡng `phone.unknown_*` chưa có dữ liệu; lợi ích của việc đẩy cảnh báo chưa đo được bằng số (chưa có
  phép đo tới lúc loa kêu); HUD của bản thiết bị vẫn hỏi 300 ms một lần.

- **M49: số đo tốc độ chưa có trên máy đích.** Bảng `benchmark_web.md` là Node trên Mac; canvas, MediaPipe và
  YOLO của bản web chỉ được đo khi mở `#/live` trên chính máy đó. Bản Python trên thiết bị chưa gửi `perf`.

- **M43–M48 chưa deploy, chưa thử với người thật trước camera.** Mọi hành vi mới mới qua chuỗi số giả, trace
  cũ và e2e với khuôn mặt tổng hợp. Chưa ai nhìn màn hình "Bạn còn ở đó không?" khi đang lái.
- **Khối 5 trên thiết bị (từ M46, chưa sửa):** mặt hơi tối hoặc ảnh xám thì CNN mắt gần như không bắt được
  nhắm mắt, và hệ thống không biết. Xem mục 2.17.
- **Ngưỡng tạm của M43 / M44** đặt theo video bị biến đổi nhân tạo và theo suy luận, chưa theo dữ liệu thật:
  có thể tạm ngưng giám sát quá sớm (đường hầm, bóng cây kéo dài) hoặc quá muộn.
- **Độ nét phụ thuộc camera:** clip điện thoại SUST có độ nét xuống 4,4 mà vẫn đọc được; ngưỡng mờ 3,0 có thể
  sai với camera khác. Độ sáng trung bình của mặt cũng không bắt được vệt nắng trên nửa mặt.
- **`#/live` sau khi bỏ OpenCV:** đúng số (test, e2e) nhưng **chưa đo FPS trong trình duyệt**; góc đầu bằng numpy
  tốn khoảng 1 ms / frame trên CPython, trong Pyodide chưa đo.
- **Nén và cache của server chưa kiểm trên Railway.** Con số 30 MB gồm phần lấy từ CDN theo số đo ngày 03/10.
- **Áp thử theo nhóm (M47)** nhập mã thiết bị bằng tay, chưa có khái niệm nhóm xe; số cảnh báo / báo sai theo
  phiên bản là tổng thô, không có khoảng tin cậy, không chia theo giờ lái.
- **Yêu cầu xoá (M48)** không tự xoá các dòng nhật ký truy cập về tài xế đó và không đụng tới bản sao lưu.

- **Chưa deploy, chưa thử trên thiết bị thật.** Nhịp trên thiết bị (`edge_agent.main`) mới qua test bằng
  chuỗi số giả và transport giả; đường web đã qua e2e.
- **Leo thang L1 → L2: ngưỡng tạm** (3 lần / 10 phút). Chưa dataset nào có chuyến đủ dài để đo.
- **L1 kéo dài liên tục không được tính là lặp lại.** Khối 12 chỉ phát L1 mới khi mức đã hạ rồi lên lại
  (có từ trước M32), nên `drowsy_score` nằm trong vùng L1 suốt 10 phút chỉ có một cảnh báo và không leo
  thang.
- **Tab "Đội xe" không đẩy thông báo:** quản lý phải đang mở tab. Từ M44 có âm báo cho xe "cần chú ý ngay";
  xe mất liên lạc vẫn không có âm báo.
- **Trang `#/live` chạy nền:** trình duyệt có thể giãn bộ hẹn giờ tới 1 phút, vẫn trong hạn 90 s nhưng sát;
  trang bị đóng băng hẳn thì hiện "Mất liên lạc" (đúng: không còn giám sát).
- **Tài xế trong xe vẫn không được báo khi tiến trình chết hẳn** (cần kênh cảnh báo vật lý, có trong improvements).
- **Giờ thiết bị sai** không ảnh hưởng `online` / `offline` (tính theo giờ máy chủ), nhưng nhịp có `ts`
  lùi về quá khứ sẽ không ghi đè trạng thái đã lưu. Sửa ở v4 (M82).
- **Test hồi quy (M34):** 36 video là một mẫu nhỏ chọn từ chính các bộ đã dùng để chỉnh ngưỡng; nó bắt
  thay đổi hành vi, không chứng minh hành vi đúng. Không có cột lông mày (trace cũ) nên tín hiệu nhướn
  mày không được phủ; không có cờ điện thoại.
- **Prototype thời lượng chớp (M35):** kết luận chỉ đúng với FL3D (diễn, clip ngắn). Khối 7 đo được chưa
  tới một nửa số lần chớp mà bộ đếm offline thấy; chưa tìm hiểu nguyên nhân.
- **Chính sách dữ liệu (M37):** chưa có ý kiến pháp lý; database không mã hoá ở mức ứng dụng (M48: dựa vào
  nơi host); bản sao lưu lúc deploy không tự xoá. Nhật ký truy cập có từ M41, xuất dữ liệu và xoá tài khoản từ M48. Nếu
  đổi thời hạn bằng biến môi trường thì câu trên màn hình đồng ý vẫn ghi con số mặc định cho tới khi sửa
  `RETENTION_DAYS` và build lại.
- **Tiêu chí pilot (M36):** bảng phản ánh số đo tới 05/10/2026; phải cập nhật tay khi có số mới.
- Các giới hạn của v2 ([release-v2.md mục 8](release-v2.md)) vẫn còn nguyên.
