# DriveGuard — Version 2

> Bản tiếp theo của [Version 1](release-v1.md). Ghi lại mọi cải tiến, chỉnh sửa làm sau v1.1: cái gì
> **thêm**, cái gì **sửa**, cái gì **bỏ**, và đã kiểm chứng tới đâu.
> Nguyên tắc giữ nguyên: mọi xử lý hình ảnh chạy trên thiết bị hoặc trong trình duyệt, không gửi và
> không lưu ảnh khuôn mặt, chỉ gửi metadata JSON.

| | |
|---|---|
| **Phiên bản** | Version 2, dựa trên v1.1. Bản đã deploy: **v2.0.0** (01/10/2026), gồm M9–M18. M19–M29 (01–02/10) vẫn thuộc version 2, **chưa deploy** |
| **Mã nguồn** | nhánh `DAQuan` (commit `679a44a` → `0a47d76` + merge `origin/main`, deploy `c80e7ce`), M19–M29 commit ngày 02/10 (PR `DAQuan` → `main`) |
| **Web v2** | https://driveguard-v2-production.up.railway.app (camera: `/#/live`) |
| **Web v1 (giữ nguyên, chạy song song)** | https://driveguard-production-6b83.up.railway.app |
| **Image Docker** | `quanpk07/driveguard:v2` (cũng là `latest`), 72,7 MB; v1 giữ ở `v1.1` và `v1-backup` (cùng digest `5de7028…`) |
| **Triển khai** | Railway project DriveGuard: service `driveguard-v2` (volume riêng `driveguard-v2-volume`), service v1 `driveguard` không đổi. Database v2 khởi đầu bằng bản sao database v1 lúc 01/10 (tài khoản, lịch sử), sau đó tách riêng |
| **Định hướng sản phẩm** (chốt 02/10) | Sản phẩm cuối là **app APK chạy trên hub gắn trên xe**, bọc chính code web (Capacitor). Bản web chỉ để xem thử app hoạt động và giao diện |
| **Mốc trong lộ trình** | M9 (đăng ký tài xế), M10 (mất mặt → tạm ngưng giám sát), M11 (chớp chậm), M12 (gục đầu / cúi đầu), M13 (nhướn mày), M14 (giao diện cho tài xế), M15 (kết thúc chuyến + bảng tổng kết), M16 (một chế độ mặc định, tạm dừng / đổi tài xế), M17 (sửa cách đo báo sai), M18 (FAR / MAR theo cửa sổ), M19 (đỗ / lái theo tốc độ, công cụ mô phỏng lái xe), M20 (xi nhan theo phía), M21 (trả nợ kỹ thuật, test e2e), M22 (bảng phân tích lỗi các trạng thái im lặng), M23 (âm thanh cảnh báo luôn bật), M24 (xác nhận trước khi đăng ký khuôn mặt), M25 (cúi nhìn xuống không còn bị hiểu là nhắm mắt), M26 (mất tín hiệu xe khi đang chạy), M27 (tổng kết không tính bước nhắm mắt của đăng ký là ngủ gật), M28 (báo khi vòng xử lý dừng hoặc chậm), M29 (tài liệu v2), M30 (0 km/h không cảnh báo), M31 (trang điều khiển xe trên web), xem [roadmap.md](roadmap.md) |

---

## 1. Tóm tắt thay đổi so với v1

| Loại | Thay đổi | Mốc | Ngày |
|---|---|---|---|
| **Thêm** | Đăng ký tài xế lúc dừng xe: 3 bước ~10 s, mốc mắt / miệng / tư thế của riêng tài xế | M9 | 01/10 |
| **Thêm** | Nhận ra tài xế khi có hành khách: chọn mặt theo chữ ký mặt học lúc đăng ký | M9 | 01/10 |
| **Thêm** | HUD hướng dẫn đăng ký bằng chữ, giọng nói và tiếng bíp | M9 | 01/10 |
| **Sửa** | Mất mặt ≥ 3 s khi xe chạy: **tạm ngưng giám sát** (`unavailable`), không còn cảnh báo L2 `no_face` (PRD FR-6) | M10 | 01/10 |
| **Thêm** | Chớp chậm: đo thời gian mở mắt lại và tỉ lệ thời gian chớp, thành phần mới của `drowsy_score` (ngưỡng tạm) | M11 | 01/10 |
| **Thêm** | Tách gục đầu (rơi chậm, giật lên) với cúi đầu chủ động; sự kiện `bow`. Phép thử tốc độ **tắt mặc định** | M12 | 01/10 |
| **Thêm** | Nhướn mày để giữ mắt mở, thành phần mới của `drowsy_score` (ngưỡng tạm) | M13 | 01/10 |
| **Sửa** | Giao diện cho tài xế: bỏ mã L0–L3 trên HUD, gộp 3 bước tải thành 1, ô camera chỉ còn trạng thái dễ hiểu | M14 | 01/10 |
| **Thêm** | Nút "Kết thúc chuyến" → bảng tổng kết + đánh giá chuyến cho tài xế, tự gửi lên quản lý / kỹ sư / admin | M15 | 01/10 |
| **Thêm** | Dashboard: tab "Báo cáo chuyến đi" (bản cho kỹ sư, đánh dấu đã xem, đếm báo cáo mới) | M15 | 01/10 |
| **Sửa** | Bỏ 3 tình huống xe giả lập (phố ban ngày / cao tốc ban đêm / xe đỗ): một chế độ mặc định, bắt đầu ở xe đỗ để đăng ký khuôn mặt | M16 | 01/10 |
| **Thêm** | Nút "Đổi tài xế" (người lái mới đăng ký lại khuôn mặt) trên HUD (nút "Tạm dừng" / "Tiếp tục lái" của M16 đã bỏ ở M19) | M16 | 01/10 |
| **Sửa** | Tắt telemetry của onnxruntime (tự gửi dữ liệu về Microsoft, và làm tiến trình lỗi khi thoát) | M16 | 01/10 |
| **Sửa** | Cách đo báo sai / giờ: kèm số giờ đo và CI 95%, chia đúng mẫu số, tách lý do × mức | M17 | 01/10 |
| **Thêm** | FAR / MAR theo cửa sổ 10 s trong công cụ eval (bổ sung, không thay báo sai / giờ) | M18 | 01/10 |
| **Sửa** | Bỏ nút "Tạm dừng" / "Tiếp tục lái": đỗ hay lái theo tốc độ, 0 km/h = đỗ; không có tín hiệu tốc độ = đứng yên | M19 | 01/10 |
| **Thêm** | Công cụ mô phỏng lái xe `tools/drive_sim.py` (ngoài giao diện): tăng / giảm tốc, dừng, xi nhan trái / phải; thiết bị và `#/live` cùng đọc | M19 | 01/10 |
| **Sửa** | Xi nhan không còn tắt hẳn cảnh báo nhìn lệch: chỉ nới góc quay đầu về **phía bật xi nhan** (30° → 60°), phía kia giữ 30° | M20 | 01/10 |
| **Sửa** | Cấu trúc code, không đổi hành vi: lớp chung `edge_agent/runtime.py` cho thiết bị và web; khối 7 tách thành package `edge_agent/analysis/drowsiness/` | M21 | 02/10 |
| **Thêm** | Test end-to-end Playwright cho `#/live` + dashboard (`npm run e2e`), chạy trong CI | M21 | 02/10 |
| **Thêm** | Tài liệu phân tích lỗi (FMEA) 15 trạng thái im lặng: `docs/safety-fmea.md`. Không đổi code | M22 | 02/10 |
| **Sửa** | Âm thanh cảnh báo luôn bật: bỏ nút tắt tiếng, tự bật ở lần chạm đầu tiên; dải vàng to khi trình duyệt còn chặn | M23 | 02/10 |
| **Thêm** | Màn hình xác nhận trước khi đăng ký khuôn mặt: vì sao cần đăng ký, dữ liệu khuôn mặt không bị lưu / gửi đi; tài xế bấm "Đồng ý" mới bắt đầu, "Để sau" thì hỏi lại ở lần dừng sau | M24 | 02/10 |
| **Sửa** | Cúi nhìn điện thoại / bảng đồng hồ không còn bị báo L3 ngủ gật: đầu cúi thì cần mắt nhắm chặt hơn; mí hạ khi nhìn xuống tính là nhìn khỏi đường (L2). Ngưỡng tạm | M25 | 02/10 |
| **Sửa** | Mất tín hiệu xe khi đang chạy không còn bị coi là đỗ: vẫn giám sát như đang chạy; HUD báo "Mất tín hiệu xe" kèm âm báo; backend nhận sự kiện, tổng kết có thời gian mất tín hiệu | M26 | 02/10 |
| **Sửa** | Bảng tổng kết không còn tính bước nhắm mắt của đăng ký, hay lúc nghỉ đỗ xe nhắm mắt, là "ngủ gật khi đang lái" | M27 | 02/10 |
| **Thêm** | Báo khi vòng xử lý dừng hoặc chậm: lỗi frame không làm dừng thiết bị, "Lỗi xử lý" + âm báo; HUD đứng hình / mất kết nối có âm báo; chip "Máy chậm" | M28 | 02/10 |
| **Sửa** | Tài liệu theo v2: README mở đầu bằng DriverGuard, sơ đồ kiến trúc có phần v2, HowToUse có luồng một chuyến đi | M29 | 02/10 |
| **Sửa** | Xe đứng yên (0 km/h) thì không có cảnh báo nào (trước: microsleep ở đèn đỏ vẫn có chuông L1) | M30 | 02/10 |
| **Thêm** | Trang điều khiển xe trên web `#/drive?code=…` (tốc độ, dừng, xi nhan), mở được trên máy khác; `#/live` chạy theo | M31 | 02/10 |
| **Sửa** | README viết lại theo dự án và yêu cầu khoá: vấn đề / giải pháp, Quick start đủ bước, bảng biến môi trường, API kèm ví dụ `curl`, deliverables, team; bỏ phần template sai với DriverGuard | — | 03/10 |
| **Bỏ** | Chống chói đèn pha bằng phần mềm: giao cho yêu cầu đầu vào camera (camera IR) | — | 01/10 |
| **Bỏ** | Việc "bám tài xế" riêng: do bước đăng ký đảm nhận | — | 01/10 |
| **Bỏ** | Bật lại cảnh báo theo nhịp chớp mắt (`blink_rate`) chuẩn hoá theo tài xế: nguồn dẫn ra không ủng hộ, giữ "chỉ ghi chú" | — | 02/10 |
| **Bỏ** | Giảm xử lý từng frame (lấy mẫu thưa, chạy theo sự kiện): vòng lặp đã gấp ~10 lần 15 FPS, bỏ frame làm hỏng đo chớp / microsleep | — | 02/10 |
| **Bỏ** | Rung điện thoại khi cảnh báo, tự điều chỉnh theo sức máy cho web: sản phẩm là app trên hub, web chỉ để xem thử | — | 02/10 |
| **Bỏ** | Đọc thành tiếng cảnh báo L2 / L3 và trạng thái hệ thống: làm thử trong M23 rồi gỡ ("cảnh báo thôi, không cần nói") | M23 | 02/10 |

---

## 2. Thêm mới

### 2.1 Đăng ký tài xế lúc dừng xe (M9)

Trước v2, mọi mốc đều tự học trong lúc lái:
- Mốc mắt mở dùng giá trị mặc định 0,28 trong 10 s đầu, sau đó trôi theo cơn buồn ngủ.
- Ngưỡng ngáp là một con số chung cho mọi người.
- Mốc "nhìn đường" lấy từ 5 s đầu khi xe chạy.

v2 thêm một bước đăng ký ngắn lúc xe đứng yên:

| Bước | Tài xế làm | Thời gian | Học được |
|---|---|---|---|
| 1 | Nhìn thẳng vào camera | 2 s | Độ mở mắt (EAR), độ mở miệng khi khép (MAR), chữ ký mặt |
| 2 | Nhìn ra đường phía trước | 3 s (+ 1 s để đưa mắt về) | Tư thế đầu khi nhìn đường |
| 3 | Nhắm mắt đến khi nghe tiếng bíp | 2 s | EAR khi nhắm (để kiểm tra đăng ký đúng) |

- **Bắt buộc nhưng không chặn giám sát:** chưa đăng ký thì vẫn giám sát bằng mốc tự học như v1. HUD
  nhắc "Dừng xe để đăng ký, nhận diện sẽ chính xác hơn".
- **Không quá lâu, không quá khó:**
  - Mỗi bước chỉ đếm frame tốt. Chớp mắt hoặc quay đi chỉ tạm dừng đồng hồ, không phải làm lại.
  - Bước nào không đạt thì chỉ làm lại bước đó, kèm câu nhắc ngắn ("Giữ đầu yên", "Ngậm miệng lại").
  - Một bước lỗi 3 lần thì dừng, thử lại ở lần dừng xe sau.
  - Tài xế làm theo hướng dẫn: xong trong khoảng **10 s** (đo bằng chuỗi số giả ở 15 FPS).
- **Không học sai:** sau mỗi bước, số đo được kiểm tra trước khi nhận:
  - EAR mở nằm trong khoảng hợp lý và ổn định;
  - miệng khép;
  - đầu giữ yên, góc không quá xa;
  - bước 3: mắt phải nhắm rõ so với lúc mở. Kính bị lóa thì bước 3 hết giờ, không học giá trị sai.
- **Chỉ trong một chuyến:** mốc nằm trong RAM, hết chuyến là xoá. Chuyến sau đăng ký lại. Không lưu
  dữ liệu sinh trắc.

**Sau khi đăng ký:**

| Khối | v1 | v2 (đã đăng ký) |
|---|---|---|
| 3: chọn mặt tài xế | Mặt to nhất | Mặt khớp chữ ký + gần vị trí tài xế (xem 2.2) |
| 7: mốc mắt mở | Mặc định 0,28, rồi trôi theo 120 s gần nhất | Bắt đầu từ mắt của tài xế, chỉ trôi trong −10 % / +25 %: mắt híp dần vì buồn ngủ không kéo mốc xuống |
| 7: ngưỡng ngáp | MAR 0,45 / 0,34 cho mọi người | MAR khép của tài xế + 0,40 / + 0,29 (môi hé tự nhiên không bị tính là ngáp) |
| 7: tư thế đầu thường ngày | 5 s đầu lấy mọi frame | Bắt đầu từ tư thế nhìn đường, sau đó chỉ học lúc mắt mở |
| 8: tư thế nhìn đường | Hiệu chỉnh 5 s đầu khi xe chạy | Lấy từ bước 2, không còn giai đoạn hiệu chỉnh |

**Không tự gây báo sai:** trong bước nhắm mắt và 2 s sau đó (lúc tài xế mở mắt khi nghe bíp) không có
cảnh báo buồn ngủ. Dữ liệu của đoạn này bị bỏ, giống lúc nghỉ đỗ xe.

**Vị trí trong kiến trúc:** một giai đoạn của khối 6, module riêng
[`edge_agent/perception/enrollment.py`](../edge_agent/perception/enrollment.py). Kiến trúc vẫn 14 khối.

### 2.2 Nhận ra tài xế khi có hành khách (M9)

- **Chữ ký mặt:** 7 tỉ lệ khoảng cách giữa các điểm landmark 3D cố định (mắt, mũi, gò má, trán), chia
  cho khoảng cách hai mắt. Gần như không đổi khi quay đầu, không phụ thuộc mặt to hay nhỏ trong ảnh.
- **Chọn mặt:** trước khi đăng ký vẫn lấy mặt to nhất. Sau khi đăng ký thì lấy mặt khớp chữ ký nhất,
  cộng điểm cho mặt gần vị trí tài xế ở frame trước. Chỉ có một mặt thì luôn lấy mặt đó.
- **Thiết bị và web dùng chung code:** trên `#/live`, trình duyệt gửi mọi mặt sang Python, Python chọn.
- **Chi phí:** 0,02–0,04 ms mỗi frame.

### 2.3 HUD hướng dẫn đăng ký (M9)

- Màn hình hướng dẫn thay chỗ khung trạng thái:
  - "Bước 1/3", tiêu đề lớn, thanh tiến độ, câu nhắc màu vàng khi có vấn đề.
  - Chỉ hiện khi không có cảnh báo: **cảnh báo luôn được ưu tiên**.
- **Giọng nói tiếng Việt + tiếng bíp:** ở bước 2 và 3 tài xế không nhìn màn hình, nên mỗi bước được
  đọc to, và hết mỗi bước có tiếng bíp. Ở bước 3, tiếng bíp là tín hiệu mở mắt. Cần bật "Âm thanh".
- Chưa đăng ký: một thẻ nhỏ bên cạnh nhắc dừng xe để đăng ký.
- `#/live`: khung camera nhỏ hiện tiến độ đăng ký, và khi xong thì hiện thời gian đăng ký và số bước
  phải làm lại (để thử xem có quá lâu, quá khó không).
- `#/hud-preview` có thêm các trạng thái: Đăng ký 1, 2, 3, Chưa đăng ký.

### 2.4 Metadata mới gửi backend

| Sự kiện / trường | Khi nào | Nội dung |
|---|---|---|
| `driver_enrolled` (sự kiện hệ thống) | Đăng ký xong | `enroll_s` (thời gian), `enroll_redo` (số bước làm lại) |
| `metrics.enrolled` (trong mọi cảnh báo) | Mỗi cảnh báo | 1 = đã đăng ký, 0 = đang dùng mốc tự học |

Không gửi chữ ký mặt, EAR hay bất kỳ mốc nào của tài xế. Có test kiểm tra JSON gửi đi.

Từ M11 / M13, mọi cảnh báo có thêm `metrics.blink_time_frac`, `metrics.reopen_ratio`,
`metrics.brow_raise_count_5min` (xem 2.5–2.7).

### 2.5 Chớp chậm: tốc độ mở mắt lại (M11)

Cơ sở và nguồn: [docs/research/2026-10-01-blink-nod-brow.md](research/2026-10-01-blink-nod-brow.md).
- Caffier et al. 2003: khi buồn ngủ, thời gian mở mắt lại tăng từ 162 ms lên 273 ms.
- Schleicher et al. 2008: độ dài chớp và độ trễ mở mi là chỉ báo tốt nhất.

**Cách đo:**
- Mỗi lần chớp được đo trên **độ mở mắt chuẩn hoá**: 0 = mắt nhắm, 1 = mắt mở.
  - Đã đăng ký: dùng EAR nhắm (bước 3) và EAR mở (bước 1) của chính tài xế. Mốc mắt nhắm từ bước
    đăng ký giờ có thêm công dụng này.
  - Chưa đăng ký: lấy 0,35 × mốc mở làm mốc nhắm.
- Thời điểm cắt ngưỡng được nội suy giữa hai frame, để đo được ở 15–30 FPS.
- Hai số đo trên cửa sổ 60 s:
  - **Tỉ lệ thời gian chớp** = tổng độ dài các lần chớp / thời gian đo được mắt. Tỉnh khoảng 5–8 %.
    Thành phần điểm tăng dần từ 10 % đến **16 %**.
  - **Tỉ lệ thời gian mở lại** = trung vị thời gian mở mắt lại (từ lúc mi khép nhất đến lúc mở 80 %)
    / trung vị của 20 lần chớp đầu chuyến của chính tài xế. Thành phần điểm tăng dần từ ×1,3 đến
    **×1,7** (theo Caffier).
- `slow_blink_score` = giá trị lớn hơn trong hai thành phần, nhân trọng số **10** trong `drowsy_score`.
  Chỉ bật sau 30 s dữ liệu mắt, như PERCLOS.
- **Tất cả ngưỡng là tạm**, chờ dò trên UTA-RLDD (việc 7 trong improvements).

**Ảnh hưởng trên FL3D / NITYMED** (replay trace):

| | Trước M11 | Sau M11 |
|---|---|---|
| L1: tổng (đúng / sai) | 10 (9 / 1) | 9 (7 / 2) |
| L2: tổng (đúng / sai) | 13 (9 / 3) | 16 (11 / 3) |
| Cảnh báo `drowsy_score` sai | 2 | 3 |

- Vài cảnh báo L1 đúng được nâng lên L2. Có thêm 1 cảnh báo L1 sai (video P1042787, 77,9 s).
- SUST-DDD không đổi: clip 10 s ngắn hơn 30 s cần để tín hiệu bật.

### 2.6 Tách gục đầu và cúi đầu (M12)

- **Gục đầu do buồn ngủ:** đầu rủ xuống từ từ, rồi **giật lên nhanh** khi tỉnh lại.
- **Cúi đầu chủ động** (nhìn đồng hồ, điện thoại): xuống và lên đều có kiểm soát.
- **Cách đo:**
  - Pha xuống tính từ lúc rời tư thế thường đến lúc chạm đáy; pha lên tính từ lúc rời đáy đến lúc về.
    Đoạn giữ đầu ở dưới không bị tính vào.
  - Tư thế thường lấy từ bước 2 của đăng ký (nếu đã đăng ký).
- **Luật:** tốc độ lên ≥ `rise_speed_ratio` × tốc độ xuống và ≥ `min_rise_deg_s`. Dip không đạt
  luật thành sự kiện `bow`, không tính vào điểm buồn ngủ.
- **Mặc định: phép thử tốc độ TẮT.** Replay cho thấy không bộ ngưỡng nào tốt hơn v1:

| Cấu hình | FL3D: gục đúng / sai | SUST: precision sự kiện gục |
|---|---|---|
| v1 = mặc định v2 | 115 / 1 | 48,3 % |
| Lên nhanh ≥ 1,0 × xuống | 91 / 3 | 33 % |
| Lên nhanh ≥ 1,5 × xuống và ≥ 40 °/s | 51 / 1 | 25 % |

- Hai dataset này gần như không có cảnh cúi nhìn điện thoại với mắt nhìn xuống, tức đúng trường hợp
  luật muốn chặn. Vì vậy chưa đo được lợi ích, chỉ đo được phần bỏ sót.
- Cách bật thử: trong `thresholds.yaml` đặt `drowsiness.nod.rise_speed_ratio: 1.5`,
  `min_rise_deg_s: 40`, `max_drop_s: 3`, `max_rise_s: 1`, `max_s: 3`.
- Cần clip có nhãn gồm cả cúi và gục (việc 4 trong improvements).

### 2.7 Nhướn mày để giữ mắt mở (M13)

- **Nguồn:** Vural et al. 2007 ghi nhận tài xế buồn ngủ **nhướn đuôi mày (AU2) để cố giữ mắt mở**.
  Đây là một trong các biểu hiện dự báo buồn ngủ tốt nhất của nghiên cứu.
- **Tín hiệu:** blendshape `browOuterUp` của MediaPipe (trung bình hai bên). Cùng model đang chạy, không
  tốn thêm FPS. Có trên cả thiết bị lẫn web.
- **Một lần "nhướn mày chống buồn ngủ"** khi đủ cả các điều kiện:
  - lông mày cao hơn mức bình thường của tài xế ≥ 0,2;
  - mắt đang sụp nhưng chưa nhắm (EAR < 0,85 × mốc);
  - kéo dài ≥ 0,5 s;
  - không đang ngáp hoặc nói chuyện (lúc ngáp lông mày cũng nhướn);
  - mắt không mở to (nếu mở to thì là ngạc nhiên, không tính).
- **Mức lông mày bình thường:** lấy từ bước 1 của đăng ký. Người có lông mày tự nhiên cao không bị
  tính sai. Chưa đăng ký thì lấy trung vị 120 s gần nhất.
- **Điểm:** đếm trong 5 phút, 3 lần là đủ thành phần, trọng số **10** trong `drowsy_score`.
- **Ngưỡng là tạm.** Chưa đo được trên dataset, vì trace cũ không có cột lông mày. `seq_eval` đã
  thêm cột `brow`, từ lần trace sau sẽ đo được.

### 2.8 Kết thúc chuyến và bảng tổng kết (M15)

**Luồng:**
1. Tài xế bấm **"Kết thúc chuyến"** trên thanh trên cùng của HUD, rồi xác nhận lần nữa ("Tiếp tục lái" /
   "Kết thúc"), để không lỡ tay khi đang chạy. Nút ẩn khi đang L3.
2. Khối 11 dựng **bản tổng kết** từ số liệu đã cộng dồn mỗi frame. Dữ liệu chỉ là số, không có ảnh.
3. Bản tổng kết **gửi lên backend** cùng hàng đợi với các sự kiện.
   - Thiết bị: qua outbox offline, mất mạng thì gửi khi có lại.
   - Web: gửi bằng token đăng nhập.
   - Dùng thử: không gửi gì.
4. HUD chuyển sang **màn hình tổng kết** cho tài xế. Agent dừng.

Thiết bị còn tạo bản tổng kết khi agent dừng vì lý do khác (q, hết video, Ctrl+C).

**Bản cho tài xế** (không tên biến, không L0–L3):
- **Đánh giá chuyến:** "Chuyến đi an toàn" / "Cần chú ý" / "Có lúc rất nguy hiểm", kèm lý do.
- **Một đoạn kể:** "Chuyến 2 giờ 10 phút, nghỉ 1 lần. Bạn có dấu hiệu mệt từ phút lái thứ 95. Có 2 lần
  nhắc nghỉ, 1 lần nhắc nhìn đường."
- **4 số lớn:** thời gian lái, số lần nghỉ, số lần nhắc nhở, số lần bấm báo sai.
- **Biểu đồ từng phút** với 3 màu "Tỉnh táo / Hơi mệt / Mệt" theo ngưỡng L1 / L2 của chuyến; đoạn dừng
  xe tô xám.
- **Gợi ý**, ví dụ "Lần sau nên dừng nghỉ sau khoảng 1 giờ 25 phút lái", kèm câu "đây là gợi ý,
  không phải chẩn đoán".
- **Trạng thái gửi**, nói thật: "Đã gửi cho quản lý đội xe" / "Chưa gửi được (mất kết nối)" /
  "Chế độ dùng thử: không gửi".

**Đánh giá** (luật trong `thresholds.yaml` → `trip_summary`; chỉ mô tả chuyến, không chấm điểm tài xế):

| Đánh giá | Khi nào |
|---|---|
| Có lúc rất nguy hiểm (`risk`) | Có cảnh báo L3 / microsleep |
| Cần chú ý (`attention`) | Từ 2 cảnh báo L2+ trở lên và ≥ 2 lần / giờ lái, hoặc ≥ 5 phút có `drowsy_score` ≥ L1 |
| Chuyến đi an toàn (`good`) | Còn lại |

Nếu thấy mặt dưới 60 % thời gian lái thì thêm ghi chú "số liệu chưa đầy đủ" (`low_coverage`). Ghi chú
này không làm đánh giá xấu đi.

**Số liệu trong bản tổng kết:**
- thời gian chạy / dừng, số lần nghỉ, đoạn lái liên tục dài nhất, tốc độ trung bình (ghi rõ giả lập);
- cảnh báo theo mức và lý do, số lần tài xế bấm báo sai;
- microsleep, lần nhắm lâu nhất, ngáp, gục đầu, nhướn mày;
- thời gian nhìn khỏi đường / cầm điện thoại;
- độ phủ giám sát (thấy mặt, tạm ngưng, mất camera), đã đăng ký hay chưa;
- `drowsy_score` trung bình / p90 / cao nhất, phút lái đầu tiên bị mệt;
- `drowsy_score` từng phút.

**Gửi lên tài khoản cao hơn (dashboard, tab "Báo cáo chuyến đi"):**
- **Quản lý / kỹ sư / admin:**
  - Thấy báo cáo của mọi tài xế. Tab hiện **"(n mới)"** ngay khi mở dashboard.
  - Có lọc "Chỉ báo cáo chưa xem".
  - Bản chi tiết cho kỹ sư: mọi con số, biểu đồ `drowsy_score` kèm các cảnh báo của chuyến, các gợi ý
    đã đưa.
  - Nút **"Đánh dấu đã xem"** ghi lại ai xem, lúc nào.
- **Tài xế:** chỉ thấy báo cáo của mình, và biết đã có người xem.
- **Backend:**
  - Bảng `trip_summaries`, khoá theo (thiết bị, chuyến), gửi lại không bị trùng.
  - `GET /api/v1/trip-reports`, `GET /api/v1/trip-reports/{device}/{trip}`,
    `POST …/review` (chỉ quản lý / kỹ sư / admin).

### 2.9 Một chế độ mặc định, tạm dừng, đổi tài xế (M16)

> **Đã thay ở M19 (mục 2.10):** bỏ nút "Tạm dừng" / "Tiếp tục lái" và xe tự chạy 50 km/h; đỗ / lái
> nay theo tốc độ từ công cụ mô phỏng lái xe. Phần đăng ký và "Đổi tài xế" giữ nguyên.

**Trước:** `#/live` bắt chọn 1 trong 3 tình huống giả lập tốc độ: phố ban ngày, cao tốc ban đêm (giờ
giả 02:30, đã lái gần 2 giờ), xe đỗ. Ánh sáng do camera đầu vào lo, nên các tình huống này không cần.

**Bây giờ, chế độ mặc định (`manual`, cả web lẫn thiết bị):**
1. Chuyến **bắt đầu ở trạng thái xe đỗ**, nên phần **đăng ký khuôn mặt** chạy ngay. Trang bắt đầu có mục
   "2. Đăng ký khuôn mặt (khoảng 10 giây)" thay cho phần chọn tình huống.
2. Đăng ký xong, xe **tự chuyển sang lái** (tốc độ giả lập 50 km/h, `config/scenarios/manual.yaml`).
3. Thẻ **"Xe"** trên HUD:
   - **"Tạm dừng"**: đỗ xe. Không cảnh báo mất tập trung; buồn ngủ tối đa L1; đỗ quá 2 phút là đang
     nghỉ.
   - **"Tiếp tục lái"**.
   - **"Đổi tài xế"**, có hộp xác nhận.
4. **Đổi tài xế:**
   - Xe dừng.
   - Bỏ toàn bộ mốc của người cũ: mắt / miệng / tư thế, PERCLOS, chớp, xu hướng mệt, mốc nhìn đường,
     đăng ký, chữ ký mặt ở khối 3.
   - Người mới đăng ký lại. Xong thì tiếp tục lái.
   - Backend nhận sự kiện hệ thống `driver_changed`. Bản tổng kết chuyến ghi số lần đổi tài.
5. **Giờ trong ngày lấy theo đồng hồ thật**, nên hệ số ban đêm chỉ áp dụng khi thật sự là ban đêm.

- **Trên thiết bị:**
  - `python -m edge_agent.main` mặc định là chế độ này.
  - HUD gửi lệnh qua `POST /vehicle`.
  - Vẫn chạy được kịch bản CAN dựng sẵn bằng `--scenario`. Khi đó chỉ có nút "Đổi tài xế", vì tốc độ
    do kịch bản quyết định.
- **Kiểm tra trên Chrome** (camera giả từ clip SUST) theo đúng thứ tự: vào trang, không còn phần chọn
  tình huống → xe đỗ + màn hình đăng ký → "Tiếp tục lái" → "Đang lái" → "Tạm dừng" → "Đổi tài xế" →
  hộp xác nhận → màn hình đăng ký mở lại.

---

### 2.10 Công cụ mô phỏng lái xe, đỗ / lái theo tốc độ (M19)

**Trước (M16):** xe "lái tay" (`ManualVehicle`): đăng ký xong tự chạy 50 km/h, nút "Tạm dừng" /
"Tiếp tục lái" trên HUD đổi qua lại. Không có tăng / giảm tốc hay xi nhan.

**Bây giờ:**
- **Không còn nút "Tạm dừng" / "Tiếp tục lái".** Đỗ hay lái **theo tốc độ**: dưới
  `context.stationary_kmh` (1 km/h), tức 0 km/h, là **xe đang dừng / đỗ**.
- Dải **"Tín hiệu xe"** ngay dưới thanh trên cùng của HUD (thiết bị và `#/live`):
  - mũi tên xi nhan trái / phải to, **nhấp nháy** màu xanh như đồng hồ xe khi bật (đứng yên nếu máy
    bật giảm chuyển động), mờ khi tắt;
  - tốc độ chữ to, nhãn **"Đang lái"** hoặc **"P Đang đỗ"**;
  - khi xi nhan bật: dòng "Xi nhan trái · được nhìn sang trái nhiều hơn" (M20);
  - khi chưa có tín hiệu xe: "Chưa có tín hiệu xe: coi như đang đỗ";
  - ẩn ở mức nguy hiểm cao nhất như mọi thứ khác.
- Thẻ "Xe" chỉ còn trạng thái và nút **"Đổi tài xế"**.
- **Công cụ `tools/drive_sim.py`** chạy trong terminal, **không nằm trên giao diện**. Nó đứng thay CAN bus
  của xe:
  - phím `w` / `↑` tăng tốc, `s` / `↓` giảm tốc (mỗi lần ±10 km/h mục tiêu), `space` dừng, `c` chạy
    50 km/h;
  - `a` / `←`, `d` / `→` xi nhan trái / phải, **giữ bật đến khi tắt** (bấm lại cùng phím, bấm bên kia,
    hoặc `x`; không tự tắt),
    `q` thoát;
  - tốc độ tăng / giảm dần như xe thật (tăng 8 km/h/s, phanh 15 km/h/s), các thông số nằm ở
    `config/drive_sim.yaml`;
  - `--scenario config/scenarios/city_day.yaml`: chạy lại một kịch bản CAN dựng sẵn thay cho bàn phím.
- **Một công cụ điều khiển cả hai:** công cụ mở `GET http://127.0.0.1:8766/can` (chỉ localhost, trả
  `speed_kmh`, `turn_signal`, `t`). Thiết bị (`edge_agent.main`, `--sim-url`) và `#/live` trên trình
  duyệt (đọc mỗi 250 ms) cùng đọc. Chỉ có số, không có ảnh.
- **Không chạy công cụ = xe đứng yên 0 km/h** (đỗ). Công cụ tắt giữa chừng thì sau
  `context.vehicle_signal_stale_s` (1 s) xe cũng về 0 km/h. Thời gian lái liên tục không tính lúc đứng.
- Khối 10: `ExternalVehicle` + `SignalLink` thay `ManualVehicle`; bỏ `config/scenarios/manual.yaml`.
  HUD server `POST /vehicle` chỉ nhận `change_driver`.
- `edge_agent.main --scenario ...` vẫn chạy kịch bản CAN trực tiếp như cũ.

### 2.11 Xi nhan nới góc nhìn về đúng phía đó (M20)

**Trước:** bật xi nhan (cộng 2 s sau khi tắt) là **bỏ hẳn** cảnh báo nhìn lệch, bất kể tài xế nhìn
về phía nào, xa bao nhiêu.

**Bây giờ:**
- Xi nhan **trái**: được quay đầu sang **trái** tới 60° (30° thường + 30° nới thêm) mà không tính là
  nhìn lệch. Xi nhan **phải** thì ngược lại.
- Phía **kia** vẫn giữ 30°: bật xi nhan trái mà nhìn sang phải lâu vẫn bị cảnh báo.
- Quay quá 60° về phía xi nhan, hoặc cúi xuống (điện thoại, đùi) vẫn tính như cũ.
- Vẫn giữ 2 s sau khi tắt xi nhan (`context.turn_signal_grace_s`), rồi về lại 30°.
- Mốc "nhìn đường" của tài xế không học từ những lúc quay đầu theo xi nhan.
- Ngưỡng mới trong `config/thresholds.yaml`:
  - `distraction.turn_signal_extra_yaw_deg: 30`, ngưỡng tạm, chờ đo trên chuyến thật có rẽ / chuyển làn.
    Kỹ sư chỉnh được trên dashboard (tab Ngưỡng).
  - `distraction.left_yaw_sign: 1`: chiều nào là bên trái của tài xế. Đổi thành `-1` nếu camera lật
    gương.
- Khối 10 thêm `turn_side` (phía xi nhan, giữ qua 2 s), khối 8 nhận nó; khối 9 bỏ luật "đang rẽ =
  không tính nhìn lệch".

### 2.12 Bảng phân tích lỗi các trạng thái im lặng (M22)

[`docs/safety-fmea.md`](safety-fmea.md): mỗi lúc hệ thống không cảnh báo được, với nguyên nhân, mức
nghiêm trọng, cách phát hiện, tài xế / quản lý thấy gì, thời gian im lặng tối đa và test đang kiểm. Đối
chiếu với code sau M21, **không đổi code**.

- 15 trạng thái: 6 mức Cao, 4 Vừa, 5 Thấp. Kèm bảng thời gian cảnh báo bình thường tính từ cấu hình
  (nhắm mắt ~1,5 s, nhìn khỏi đường ~2,5 s), chưa đo trên video.
- Ghi lại các quyết định đã chốt (02/10): tạm ngưng giám sát và mất camera không báo quản lý theo thời
  gian thực (mất camera xem ở bản tổng kết); gục ra khỏi khung thì hỏi "Bạn còn ở đó không?"; chưa đăng
  ký vẫn được lái.
- Bốn khoảng trống mức Cao **chưa có cách phát hiện hoặc chưa có test** thành việc mới trong
  `docs/improvements.md` (lúc đó việc 5, 6, 7, 30); việc âm thanh đã làm ở M23 (mục 3.6). Xem
  [Giới hạn đã biết](#8-giới-hạn-đã-biết).

### 2.13 Xác nhận trước khi đăng ký khuôn mặt (M24)

**Trước:** xe vừa dừng là HUD vào thẳng bước 1 "Nhìn thẳng vào camera", tài xế không được giải thích vì
sao, và không được hỏi.

**Bây giờ:** xe dừng thì HUD hiện màn hình **"Đăng ký khuôn mặt"** trước:
- Vì sao: để nhận biết buồn ngủ và mất tập trung chính xác nhất; mất khoảng 10 giây, khi xe đang dừng.
- Dữ liệu khuôn mặt (đúng với code):
  - không chụp, không lưu ảnh; hình ảnh camera chỉ được xử lý trên thiết bị;
  - chỉ ghi nhớ vài con số (độ mở mắt, miệng, tư thế đầu), xoá khi kết thúc chuyến;
  - không gửi khuôn mặt hay các con số đó lên máy chủ; quản lý chỉ biết đã đăng ký (và mất bao lâu, làm
    lại mấy bước).
- **"Đồng ý, bắt đầu đăng ký"**: 3 bước bắt đầu ngay như trước. **"Để sau"**: vẫn lái được (giám sát bằng
  mốc tự học), thẻ nhắc "Sẽ hỏi lại ở lần dừng xe sau".
- Chưa trả lời mà xe chạy thì màn hình đóng, hỏi lại ở lần dừng sau. Trước khi trả lời không đo gì.
- Hỏi **một lần cho mỗi tài xế**: đã đồng ý mà đăng ký bị dở (xe chạy giữa chừng) hoặc thất bại thì lần
  dừng sau làm lại các bước, không hỏi lại. "Đổi tài xế" thì người mới được hỏi lại.
- Không đọc thành tiếng màn hình này; giọng nói của các bước đăng ký giữ như cũ.
- Code: trạng thái mới `consent` / `later` ở `edge_agent/perception/enrollment.py`; HUD gửi
  `enroll_start` / `enroll_later` qua `POST /vehicle` (thiết bị) hoặc `bridge.vehicle` (web).
  `enrollment.require_consent: true` trong `thresholds.yaml`; thiết bị chạy không có HUD
  (`--hud-port 0`) thì tự tắt bước này, vì không ai đọc hay trả lời được.
- `#/hud-preview` có thêm "Đăng ký: xác nhận".

---

## 3. Sửa đổi

### 3.1 Mất mặt ≥ 3 s khi xe chạy → tạm ngưng giám sát (M10, PRD FR-6)

| | v1 | v2 |
|---|---|---|
| Mất mặt ≥ 3 s khi xe chạy | Cảnh báo **L2 `no_face`** | Trạng thái **`unavailable`**, **không cảnh báo** |
| Trong lúc mất mặt | Các luật khác vẫn có thể báo (vd. `off_road` giữ từ trước khi mất mặt) | Không luật nào báo |
| HUD | Khối cam "Ngồi đúng vị trí lái" | Màn hình hệ thống "Tạm ngưng giám sát", tiếng báo riêng |
| Backend | Sự kiện cảnh báo L2 | Sự kiện hệ thống `monitoring_unavailable` / `monitoring_restored` (như `camera_lost`) |

- **Lý do:** không có mặt thì không đánh giá được gì. Báo L2 lúc đó là đoán, và là nguồn báo sai
  (che camera, chói đèn, tài xế cúi ra ngoài khung).
- **Ngoại lệ an toàn:** nếu mắt đã nhắm **rồi** đầu gục ra khỏi khung hình (khối 7 đang đếm tiếp đợt
  nhắm), thì đó là ngủ gật chứ không phải mất mặt. Hệ thống vẫn giám sát, và còi L3 không bị tắt.
- **Đánh đổi đã chấp nhận:** tài xế gục ra khỏi khung hình mà trước đó không thấy mắt nhắm thì không
  được báo, chỉ hiện "Tạm ngưng giám sát".
- **Ngưỡng:** `risk.distraction.no_face_s` đổi thành `risk.unavailable.no_face_s` (3,0 s). File
  ngưỡng cũ còn key cũ thì agent dừng và chỉ ra key mới.

**Ảnh hưởng đo được** (chạy lại khối 5, 7–12 trên trace có sẵn, cùng ngưỡng):

| Dataset | v1 | v2 |
|---|---|---|
| SUST-DDD, clip không buồn ngủ: cảnh báo bất kỳ (FPR) | 2,9 % | **2,4 %** |
| SUST-DDD: cảnh báo sai / giờ | 10,8 | **8,5** |
| SUST-DDD: cảnh báo sai theo lý do | 25 `off_road`, 7 `no_face`, 2 microsleep | 24 `off_road`, 2 microsleep |
| SUST-DDD: precision "cảnh báo bất kỳ" | 33,3 % | 38,1 % |
| FL3D / NITYMED | — | Không đổi |

Recall trên clip buồn ngủ không đổi (1,6 %). Chi tiết ở
[`eval/results/dataset_sust_ddd.md`](../eval/results/dataset_sust_ddd.md).

### 3.2 Giao diện cho tài xế: bỏ thuật ngữ (M14)

| Chỗ | v1 | v2 |
|---|---|---|
| HUD: nhãn mức | "L1 · Chú ý", badge "L2" | "Chú ý", "Cảnh báo" (màu + hình + câu hành động; mã L0–L3 vẫn có trên dashboard và metadata) |
| Mô tả mức L1 / L2 | "Biểu tượng + chuông nhẹ", "Âm thanh + rung ghế" | "Bạn có vẻ mệt, nên nghỉ sớm", "Tập trung lái xe ngay" |
| `#/live`: màn hình tải | 4 bước: Python, MediaPipe, YOLO… | 2 bước: "Mở camera", "Đang chuẩn bị (lần đầu khoảng 60 MB)" kèm thanh tiến độ |
| `#/live`: ô camera nhỏ | EAR, FPS, yaw / pitch, ms của YOLO | "Đang theo dõi" / "Không thấy mặt, hãy chỉnh camera". Số đo kỹ thuật ẩn sau nút "Chi tiết kỹ thuật" (trình duyệt nhớ lựa chọn) |
| `#/live`: lời giới thiệu | "cảnh báo theo 4 mức L0–L3" | Nói bằng lời thường; nhắc bật âm thanh và bước đăng ký; có nút "Kết thúc chuyến" |

### 3.3 Tắt telemetry của onnxruntime (M16)

- **Phát hiện:** test bắt đầu bị lỗi khi thoát (abort, exit 134), khoảng 4–5 trên 10 lần chạy. Backtrace
  chỉ vào client telemetry "Microsoft Applications Events" (1DS) có sẵn trong onnxruntime.
  - Client này tự gửi dữ liệu dùng lên `mobile.events.data.microsoft.com` từ một thread nền.
  - Nếu phản hồi về đúng lúc Python đang thoát, nó khoá một mutex đã bị huỷ.
  - Bản v1 có cùng client này; chỉ là test chạy ngắn hơn nên ít gặp.
- **Vấn đề lớn hơn:** thiết bị đang **gửi dữ liệu ra ngoài mà không ai biết**, trái với "chỉ gửi
  metadata JSON lên backend" (CLAUDE.md).
- **Sửa:** mọi session onnxruntime (YOLO điện thoại, CNN mắt, công cụ benchmark) tạo qua
  `edge_agent/perception/onnx.py::load_ort()`. Hàm này đặt `ORT_DISABLE_TELEMETRY=1` trước khi import và
  gọi `disable_telemetry_events()`. Chỉ gọi `disable_telemetry_events()` thì chưa đủ (vẫn lỗi 5/12 lần).
- **Sau khi sửa:** 0 / 18 lần chạy toàn bộ test bị lỗi.

### 3.4 Cách đo báo sai / giờ (M17) và FAR / MAR theo cửa sổ (M18)

Hai chỉ số trả lời hai câu hỏi khác nhau nên dùng song song (`docs/improvements.md` mục 2):
- **Báo sai / giờ:** tài xế bị làm phiền vô cớ bao nhiêu lần (chỉ tiêu PRD ≤ 1,0 / giờ).
- **FAR / MAR:** bao nhiêu phần trăm thời gian hệ thống đoán nhầm / bỏ lỡ. Dùng khi dò ngưỡng.

**M17, sửa cách đo báo sai / giờ** (`tools/eval.py`, `tools/seq_eval.py`, `eval/results/`):
- **Luôn kèm số giờ đo và CI 95%** (Poisson chính xác). Ví dụ FL3D L1: 2 lần sai trên 0,43 giờ =
  4,6 / giờ, CI **0,56–16,7**. Với CI rộng như vậy thì không kết luận đạt hay không đạt PRD.
- **Mẫu số đúng:** chia cho thời gian thật sự có thể báo sai, tức tổng thời lượng trừ các đoạn có nhãn
  (± tolerance). Trước đây chia cho cả thời lượng.
  - YawDD, "tất cả cảnh báo": **4,8 → 6,9 / giờ (CI 3,3–12,7)**. Vẫn là 10 cảnh báo sai, nhưng chia cho
    1,45 giờ clip không ngáp, thay vì 2,07 giờ.
- **Tách theo lý do × mức:** thêm hàng L1 / L2 / L3 cho "tất cả cảnh báo" (YawDD), bảng lý do × mức cho
  cảnh báo sai (FL3D) và cho cảnh báo trên clip không buồn ngủ (SUST). Ví dụ SUST: `off_road` L2
  7,9 / giờ (CI 5,0–11,7), microsleep L3 0,7 / giờ.
- YawDD giờ chấm từ trace (`seq_eval yawdd`), không phải chạy lại video. Khác bản cũ chạy từ video ở 1
  sự kiện gục (4 → 5).

**M18, FAR / MAR theo cửa sổ** (`tools/metrics.py`, `thresholds.yaml` → `eval`):
- Cửa sổ 10 s không chồng nhau, bỏ 30 s đầu mỗi clip.
- Cửa sổ buồn ngủ: ≥ 50 % trong đoạn có nhãn. Cửa sổ tỉnh táo: ≥ 50 % thời gian biết là tỉnh và không
  chạm đoạn nào. Còn lại bỏ.
- Đoán buồn ngủ khi mức của **nhánh buồn ngủ** ≥ L1 (báo thêm ≥ L2) trong cửa sổ. Mất tập trung tính
  riêng.
- CI Wilson; lạc quan vì các cửa sổ trong một clip tương quan.
- **Kết quả: dataset hiện có quá ngắn để đọc được.**
  - FL3D: chỉ 7 cửa sổ hợp lệ. Frame "alert" ở FL3D lại nằm giữa các lần ngủ gật của cùng một người,
    nên FAR không có nghĩa "báo nhầm người tỉnh".
  - YawDD: 13 cửa sổ.
  - SUST (10 s): không còn cửa sổ nào.
  - FAR / MAR sẽ dùng được với UTA-RLDD, DMD.

**Không đổi:** khối 2–14, FPS, các con số phát hiện (recall, precision, độ trễ).

### 3.5 Trả nợ kỹ thuật (M21)

Chỉ đổi cấu trúc code, **không đổi hành vi**.

- **Lớp chung `edge_agent/runtime.py` (`TripRuntime`):** từ M9 đến M20, phần quanh khối 6–14 được viết
  hai lần, ở `edge_agent/main.py` (thiết bị) và `edge_agent/web/bridge.py` (web). Phần này gồm:
  `unavailable`, đăng ký, đổi tài xế, mất camera, báo sai, mẫu mỗi phút, kết thúc chuyến. Mỗi mốc phải
  sửa cả hai nơi. Nay chỉ còn một lớp:
  - nhận đặc trưng của một frame, trả kết quả, cập nhật HUD, tạo bản ghi khối 14;
  - bản ghi đi qua `emit(kind, data)`: trên thiết bị vào `MetadataPublisher.publish_record` (mới), trên
    web vào hàng đợi gửi của trình duyệt;
  - `main.py` / `bridge.py` chỉ còn phần vào / ra riêng: camera, HTTP, cửa sổ xem trước; Pyodide.
- **Khối 7 thành package `edge_agent/analysis/drowsiness/`** (file cũ gần 900 dòng):

  | File | Nội dung |
  |---|---|
  | `eyes.py` | mốc mắt mở, nhắm / mở có trễ, chớp, microsleep (nhắm sâu), gục mang theo, PERCLOS |
  | `mouth.py` | ngáp, che thời gian nhắm khi ngáp / nói |
  | `head.py` | tư thế đầu quen, gục / cúi |
  | `slow_blink.py` | chớp chậm |
  | `brow.py` | nhướn mày |
  | `analyzer.py` | `DrowsinessAnalyzer` ghép các phần theo đúng thứ tự cũ |

  `from edge_agent.analysis.drowsiness import ...` giữ nguyên.
- **Cách kiểm tra:** replay 2437 trace (FL3D, YawDD, SUST) trước và sau khi tách. So mọi trường của
  `DrowsinessState` mỗi frame, và mức, điểm, sự kiện, cảnh báo của khối 7–12: **giống hệt**. Chạy thật
  trên thiết bị với một clip YawDD: 30 FPS, có cảnh báo và bảng tổng kết như trước.

### 3.6 Âm thanh cảnh báo luôn bật (M23)

**Trước:** HUD khởi động **tắt tiếng**. Trình duyệt chỉ cho phát tiếng sau một lần chạm, nên HUD có nút
"Bật âm thanh". Chưa ai bấm thì mọi cảnh báo, kể cả còi L3, chỉ có hình, cả chuyến (FMEA dòng 1, mức Cao).

**Bây giờ:**
- Âm thanh **luôn bật**, không còn nút tắt tiếng (cảnh báo an toàn phải nghe được).
- HUD tạo âm thanh ngay khi mở, và bật ở **lần chạm / phím đầu tiên bất kỳ** trên màn hình, không cần tìm
  đúng nút. `#/live` có sẵn lần bấm "Bắt đầu" nên có tiếng ngay.
- Khi trình duyệt còn chặn: **dải vàng to** dưới thanh trên cùng, trên mọi màn hình kể cả L3 và màn hình
  mất camera: "Âm thanh cảnh báo chưa bật. Chạm vào màn hình để bật." Biểu tượng loa ở góc chuyển vàng.
- Tiếng không phát khi còn bị chặn, để các cảnh báo không dồn lại rồi kêu cùng lúc lúc được bật.
- `#/hud-preview` có thêm trạng thái "Chưa có tiếng" để xem dải nhắc.
- Không đọc thành tiếng cảnh báo (đã cân nhắc rồi bỏ, 02/10); lời nhắc giọng nói của bước đăng ký giữ
  như cũ.

**Còn lại:** trong APK cho WebView phát âm thanh không cần chạm (*chưa kiểm chứng*), thuộc việc đóng gói
APK. Chỉ sửa frontend; backend, edge agent không đổi.

### 3.7 Cúi nhìn xuống không còn bị hiểu là nhắm mắt (M25)

**Trước:** cúi nhìn điện thoại / bảng đồng hồ quá ~1,5 s thì có thể bị báo **L3 "Mở mắt! Dừng xe nghỉ
ngay"**. Khi nhìn xuống, mí trên hạ theo: EAR còn ~0,5 lần mốc và eyeBlink của MediaPipe ~0,6, đủ để
thành "nhắm sâu". Hai đường:
- đầu cúi 15–24° (dưới 25°, mắt vẫn được đánh giá): thành microsleep;
- cúi chậm quá 25°: mí hạ ≥ 0,5 s trước đó nên bị "mang theo khi gục", đếm suốt lúc cúi.

**Bây giờ:**
- Đầu cúi ≥ 10° so với tư thế quen: phải nhắm chặt hơn (EAR ≤ 0,35 lần mốc, bình thường 0,5) mới tính
  là nhắm sâu. Ngủ gật thật khi cúi trên FL3D có EAR p90 0,33–0,41 lần mốc: giữ đủ 83 cảnh báo L3.
- Chỉ "mang theo khi gục" khi lần nhắm trước đó là nhắm sâu.
- Mí hạ mà chưa nhắm chặt khi đầu cúi: tính là **nhìn khỏi đường**, nên sau 2 s là L2 "Nhìn về phía
  trước", kể cả khi đầu chỉ cúi 10–20° (trước đây chưa tới ngưỡng cúi 20° của khối 8 thì không tính).
- Ngưỡng mới trong `config/thresholds.yaml`: `drowsiness.microsleep_deep.bowed_pitch_deg: 10`,
  `bowed_ear_ratio: 0.35` (0 = tắt). **Tạm:** chưa dataset nào có cảnh nhìn điện thoại khi lái.

**Kết quả replay** (cùng code, chỉ bật / tắt cách sửa):

| Dataset | Trước | Sau |
|---|---|---|
| FL3D (ngủ thật) | L3 đúng 81, sai 1; nhắm ≥ 1,5 s lên L3 72/95 | không đổi; thêm 3 L2 nhìn lệch trong đoạn buồn ngủ |
| YawDD (tỉnh táo) | 10 báo sai: microsleep 5, buồn ngủ L1 2, nhìn lệch 9 | 10 báo sai: microsleep 4, buồn ngủ 0, nhìn lệch 10 |
| SUST clip tỉnh táo | 8,5 báo sai / giờ, L3 sai 2 | 8,8 / giờ (+1 nhìn lệch), L3 sai 2 |

### 3.8 Mất tín hiệu xe khi đang chạy (M26)

**Trước:** công cụ mô phỏng (sau này là đường CAN) im quá 1 s thì xe bị coi là **đỗ ở 0 km/h**, kể cả khi
đang chạy 60 km/h. Hệ quả (FMEA dòng 2, mức Cao): tắt ngay cảnh báo nhìn lệch / điện thoại, buồn ngủ tối
đa L1, sau 120 s thành "nghỉ" và tắt hết; tài xế và quản lý không được báo gì.

**Bây giờ:**
- Lần đọc cuối là **đang chạy** (≥ 1 km/h) mà tín hiệu im: tốc độ thành **"không biết"**, hệ thống vẫn
  giám sát **như đang chạy** (không bao giờ thành "nghỉ"). Lần đọc cuối là đỗ, hoặc chưa từng có tín hiệu:
  vẫn là đỗ như trước (M19).
- **Tài xế:** dải xe trên HUD hiện "Mất tín hiệu xe: vẫn giám sát như đang chạy" (vàng), tốc độ "–", âm báo
  to; có lại tín hiệu thì âm báo nhẹ. Mất tín hiệu lúc đỗ **cũng được báo** ("coi như đang đỗ đến khi có
  lại tốc độ", cùng âm báo); xe chạy đi thì khi có lại tốc độ hệ thống biết xe đang chạy.
- **Quản lý:** sự kiện hệ thống `vehicle_signal_lost` / `vehicle_signal_restored`; bản tổng kết có
  `vehicle_signal_lost_s`, dashboard hiện ở dòng "Giám sát được".
- Kiểm bằng chuỗi số giả: 5 phút mất tín hiệu ở 60 km/h, nhắm mắt cuối đoạn vẫn L3; tổng kết ghi 299 s.

**Còn lại:** đỗ, mất tín hiệu rồi chạy đi: tới khi có lại tốc độ, hệ thống vẫn coi là đỗ (giám sát hạn
chế). Tài xế đã được báo mất tín hiệu từ lúc đỗ; chấp nhận theo quyết định 02/10.

### 3.9 Bảng tổng kết không tính nhắm mắt có chủ ý là ngủ gật (M27)

**Trước:** chuyến chỉ đỗ và đăng ký (0 giây lái) bị ghi "Có lúc rất nguy hiểm: Đã có lúc nhắm mắt ngủ gật
khi đang lái". Bước 3 của đăng ký (nhắm mắt ~2 s) sinh sự kiện `microsleep` ở khối 7; cảnh báo đã bị tắt
đúng thiết kế, nhưng bản tổng kết vẫn đếm. Nghỉ đỗ xe rồi nhắm mắt cũng bị tính như vậy. (Lỗi tìm ra khi
viết test e2e ở M21.)

**Bây giờ:** bản tổng kết bỏ qua dấu hiệu buồn ngủ (microsleep, ngáp, gục, nhướn mày), lần nhắm dài nhất và
điểm buồn ngủ từng phút ở những lúc hệ thống không đánh giá buồn ngủ: bước nhắm mắt của đăng ký (+ 2 s mở
mắt) và lúc nghỉ đỗ xe (đứng yên ≥ 120 s). Đúng như trip memory đã làm từ trước. Microsleep ở đèn đỏ (đứng
yên nhưng chưa là nghỉ) vẫn được tính. Thời gian, cảnh báo, độ phủ giám sát không đổi.

### 3.10 Báo khi vòng xử lý dừng hoặc chậm (M28)

**Trước:** một lỗi trong khối 2–14 làm edge agent trên thiết bị **dừng hẳn**; trên web, frame lỗi chỉ bị bỏ
qua trong console. HUD hiện "Không nhận dữ liệu từ camera" / "Mất kết nối" nhưng **không có tiếng**, backend
không biết. FPS tụt dưới 15 kéo dài cũng không ai biết (FMEA dòng 3, 9).

**Bây giờ:**
- Frame lỗi được bắt, vòng lặp chạy tiếp. Lỗi liên tục ≥ 1 s: HUD **"Lỗi xử lý: hệ thống đang KHÔNG giám
  sát"**, âm báo to, sự kiện `agent_error`; xử lý được lại thì `agent_recovered`. Chỉ tên lớp lỗi được ghi
  vào log trên máy, không gửi đi.
- HUD vào "Lỗi xử lý", "Không nhận dữ liệu từ camera" hoặc "Mất kết nối": **âm báo to** riêng; hết thì âm
  "giám sát lại".
- FPS dưới 14,5 liên tục 5 s: chip **"Máy chậm: cảnh báo có thể trễ"**, sự kiện `low_fps` (kèm FPS); hồi lại
  thì `fps_restored`. Vẫn giám sát.
- Ngưỡng mới trong `config/thresholds.yaml`: `hud.processing_error_s: 1.0`, `hud.low_fps_below: 14.5`,
  `hud.low_fps_s: 5.0`.

**Còn lại:** hạ tải khi máy chậm (chờ có hub); tiến trình chết hẳn thì backend chưa biết ngay (chưa có nhịp
"còn sống").

### 3.12 Xe đứng yên thì không cảnh báo (M30)

**Trước:** đứng yên (dưới 1 km/h) thì mất tập trung đã tắt, nhưng buồn ngủ vẫn tới L1: nhắm mắt ở đèn đỏ có
tiếng chuông; đứng ≥ 120 s mới tắt hẳn.

**Bây giờ:** `risk.drowsy.stationary_max_level: 0`: xe đứng yên thì **không có cảnh báo nào**. Dấu hiệu buồn
ngủ vẫn được đo và vào bản tổng kết. Xe chạy lại thì mọi luật như cũ (nhắm mắt vẫn L3 ngay). Đánh đổi: ngủ gật
lúc dừng đèn đỏ không còn chuông (FMEA dòng 12).

### 2.14 Trang điều khiển xe trên web (M31)

- Khung camera của `#/live` có nút **"Điều khiển xe · mã XXXXXX"**, mở `#/drive?code=XXXXXX`; link này mở được
  trên **máy khác** (vd. điện thoại người ngồi cạnh).
- Nút **Tăng tốc / Giảm tốc / Chạy đều 50 / Dừng xe**, xi nhan **Trái / Tắt / Phải**; phím như
  `tools/drive_sim.py`. Tốc độ tăng giảm dần như xe thật (cùng thông số `config/drive_sim.yaml`).
- Backend chuyển tiếp tốc độ / xi nhan mới nhất theo mã (`/api/v1/drive/{code}`): chỉ số, trong bộ nhớ, không
  vào database, hết hạn 10 phút. `#/live` ưu tiên kênh này, không có thì đọc công cụ terminal như cũ.
- Đóng trang điều khiển khi xe đang chạy: `#/live` báo "Mất tín hiệu xe" (M26).

### 3.11 Tài liệu theo v2 (M29)

README mở đầu bằng DriverGuard (README template khoá giữ phía dưới); `docs/architecture_diagram.md` thêm
mục 5 "Phần thêm ở v2"; `HowToUse.md` thêm mục 2.5 "Một chuyến đi ở v2" và các trạng thái HUD khi không
giám sát được.

README viết lại (03/10): theo khung `README_boilerplate.md` và checklist chương 9 của guide. Thêm vấn đề /
giải pháp, vai trò và mức cảnh báo, sơ đồ 14 khối (Mermaid), tech stack thật (không LLM), Quick start 4 bước
có khởi tạo backend, bảng biến môi trường (`DG_*`, `VITE_*`, cả `DG_MAX_BODY_BYTES`, `DG_STATIC_DIR` trước chưa
ghi ở đâu), bảng endpoint + 8 ví dụ `curl`, bảng deliverables, team. Phần template khoá thu gọn còn hook ghi
log AI và ghi chú `src/`, `Dockerfile` là code mẫu. Video demo và pitch deck vẫn chưa có.

---

## 4. Bỏ, không làm

- **Chống chói đèn pha bằng phần mềm** (cờ chói, trigger `overexposed` ở khối 5): giải quyết bằng yêu
  cầu đầu vào camera (camera IR + đèn LED IR 850/940 nm, như DMS thương mại). Mất mặt do chói thì
  thành "Tạm ngưng giám sát" (mục 3.1).
- **Bám tài xế thành việc riêng:** nhận ra tài xế do bước đăng ký xác định (mục 2.2).
- **Bật lại cảnh báo theo nhịp chớp mắt** (`risk.blink.level` > 0, ngưỡng theo phân vị của chính tài xế),
  02/10. Giữ `level: 0` (chỉ ghi chú):
  - Häkkänen 1999: nhịp chớp không khác giữa tài xế buồn ngủ và nhóm đối chứng, chỉ **thời lượng** chớp
    khác. Davin 2026 (meta-analysis 61 nghiên cứu) không phân tích nhịp chớp.
  - Ngưỡng ở phân vị 90 của chính tài xế thì theo định nghĩa ~10 % cửa sổ luôn vượt: báo sai có hệ thống.
  - `blink_time_frac` (M11) đã chứa nhịp × thời lượng. Hướng thay thế: thời lượng chớp so với chính tài
    xế (improvements).
- **Giảm xử lý từng frame** (lấy mẫu thưa, chạy theo sự kiện, gom lô trong cửa sổ PERCLOS), 02/10: vòng
  lặp chính 151,8 FPS; YOLO đã chạy ~5 lần / s và CNN mắt chỉ chạy khi cần. Bỏ frame MediaPipe làm hỏng đo
  chớp (cần 25–30 FPS) và làm microsleep trễ. Chỉ giữ thứ tự hạ tải khi hub tụt FPS (improvements).
- **Rung điện thoại khi cảnh báo** và **tự điều chỉnh theo sức máy cho web**, 02/10: sản phẩm cuối là
  APK trên hub gắn trên xe (rung không tới tài xế; hub được chọn đủ mạnh); web chỉ để xem thử.
- **Đọc thành tiếng cảnh báo**, 02/10: làm thử trong M23 (L2 / L3 đọc câu hành động, mất camera / tạm
  ngưng giám sát) rồi gỡ theo yêu cầu: chỉ dùng âm báo. Giọng nói của bước đăng ký giữ nguyên.

---

## 5. Tương thích khi nâng cấp từ v1

- **`config/thresholds.yaml`:**
  - Thêm nhóm `enrollment:` (M24 thêm `enrollment.require_consent`).
  - M24: HUD và edge agent phải cùng phiên bản. Agent mới với HUD cũ thì HUD không có màn hình xác nhận,
    bước đăng ký không bao giờ bắt đầu (giám sát vẫn chạy bằng mốc tự học).
  - Thêm `landmarks.driver_shape_tol`, `landmarks.driver_position_tol`,
    `drowsiness.eye.enrolled_max_drop` / `enrolled_max_rise`,
    `drowsiness.yawn.enrolled_open_above` / `enrolled_close_above`.
  - Đổi `risk.distraction.no_face_s` → `risk.unavailable.no_face_s`.
  - M11–M13 thêm:
    - `drowsiness.blink_closed_ref_ratio`, `blink_open_level`, nhóm `drowsiness.slow_blink`;
    - nhóm `drowsiness.brow`;
    - `drowsiness.nod.max_drop_s` / `max_rise_s` / `rise_speed_ratio` / `min_rise_deg_s`
      (mặc định tắt);
    - `risk.drowsy.weight_slow_blink`, `weight_brow`, `brow_full`;
    - nhóm `trip_summary:` (luật đánh giá chuyến, M15).
  - Tổng trọng số `drowsy_score` giờ có thể vượt 100; điểm vẫn bị chặn ở 100.
  - M25 thêm `drowsiness.microsleep_deep.bowed_pitch_deg` / `bowed_ear_ratio` (0 = tắt, về như trước).
  - M28 thêm `hud.processing_error_s`, `hud.low_fps_below`, `hud.low_fps_s`.
  - M26 không thêm khoá; đổi nghĩa: hết `vehicle_signal_stale_s` khi đang chạy = mất tín hiệu, không còn là đỗ.
  - Agent cũ không biết các khoá mới của M24 / M25: có trong `thresholds.yaml` thì agent dừng lúc khởi
    động (khoá lạ bị chặn); gửi từ dashboard thì **cả bộ ngưỡng chỉnh từ xa bị bỏ qua** (log "IGNORED"),
    agent chạy bằng `thresholds.yaml` của nó.
- **Backend:** nhận thêm 3 lý do hệ thống (`driver_enrolled`, `monitoring_unavailable`,
  `monitoring_restored`) và 6 trường metrics (`enrolled`, `enroll_s`, `enroll_redo`,
  `blink_time_frac`, `reopen_ratio`, `brow_raise_count_5min`).
  - Batch nhận thêm `summaries` (bản tổng kết chuyến) và trả `summaries_accepted`.
  - Có bảng mới `trip_summaries`, tự tạo khi khởi động.
  - Có API `/api/v1/trip-reports`.
- **HUD server trên thiết bị:** thêm `POST /end-trip`; `/state` có `trip_ended`. M24: `POST /vehicle` nhận
  thêm `enroll_start` / `enroll_later`; `enrollment.status` có thêm `consent` / `later`. M23: HUD không
  còn nút tắt tiếng. Lý do
  `no_face` vẫn được nhận để không lỗi với sự kiện cũ trong database. Sự kiện hệ thống không tính vào
  thống kê cảnh báo.
- **Eval:** công cụ eval cho xe chạy 60 km/h từ đầu nên không bao giờ đăng ký: số đo vẫn dùng mốc tự
  học như v1. SUST-DDD đổi vì mục 3.1. FL3D đổi vì chớp chậm (mục 2.5). Gục đầu giữ như v1.
- **M31:** backend thêm `PUT` / `GET /api/v1/drive/{code}` (không cần đăng nhập, không đụng database).
- **M30:** đổi `risk.drowsy.stationary_max_level` 1 → 0 (bộ ngưỡng chỉnh từ dashboard có giá trị cũ thì vẫn ghi
  đè: kiểm tra lại tab Ngưỡng).
- **M28:** backend nhận thêm lý do `agent_error`, `agent_recovered`, `low_fps`, `fps_restored` và
  `metrics.fps`; HUD nhận `processing_error`, `low_fps`. Deploy backend trước.
- **M26:** backend nhận thêm lý do `vehicle_signal_lost` / `vehicle_signal_restored` và trường tuỳ chọn
  `vehicle_signal_lost_s` trong bản tổng kết; HUD nhận `vehicle.speed_kmh: null` và `vehicle.signal_lost`.
  Agent mới gửi lên backend cũ thì hai lý do mới bị từ chối: deploy backend trước.
- **Edge agent v1 gửi lên backend v2:** vẫn chạy. Edge agent v2 gửi lên backend v1 thì sự kiện mới
  bị từ chối, nên deploy backend trước.

---

## 6. Kiểm thử

| | v1 | v2 |
|---|---:|---:|
| Test Python | 434 | **585** |
| Test frontend | 25 | **50** |
| Test end-to-end (Playwright, CI) | 0 | **3** |

- Đăng ký tài xế: 23 test bằng chuỗi số giả ở 15 FPS, với tài xế giả làm theo lời nhắc. Các trường
  hợp đã test:
  - chớp mắt, quay đi, tối;
  - đầu không yên, miệng mở;
  - kính lóa;
  - xe chạy giữa chừng;
  - đăng ký lại ở lần dừng sau;
  - không có cảnh báo do bước nhắm mắt;
  - mốc không trôi theo buồn ngủ;
  - môi hé không bị tính là ngáp;
  - metadata không chứa chữ ký.
- Mất mặt: 5 test risk engine, gồm ngoại lệ đầu gục khi đang nhắm mắt. Thêm 1 test kịch bản, 1 test
  bridge web, 1 test backend.
- Chớp chậm và nhướn mày: 16 test bằng chuỗi số giả, gồm:
  - đo thời gian mở lại ở **30 và 15 FPS** (sai số ≤ 40 / 60 ms);
  - chớp lúc tỉnh không cho điểm;
  - tỉ lệ thời gian chớp ≥ 16 %;
  - mốc mở lại riêng từng tài xế;
  - thang theo mắt nhắm khi đã đăng ký;
  - lông mày nhướn khi mắt mở to, khi ngáp, quá ngắn: không tính;
  - mức lông mày bình thường lấy từ đăng ký.
- Gục / cúi: 5 test, gồm cúi có kiểm soát, rơi chậm hơn 2 s, rơi quá chậm, phép thử tắt thì giống v1.
- Kết thúc chuyến / tổng kết (M15):
  - 11 test edge: cộng dồn, đánh giá, gợi ý, độ phủ, nút kết thúc trên HUD server, `end_trip` của
    bridge web;
  - 5 test backend: gửi lại không trùng, tài xế chỉ thấy của mình, đánh dấu đã xem, web token, từ
    chối trường lạ;
  - 6 test frontend: câu chữ, bước tải gộp.
- **Kiểm tra giao diện M14 / M15 trên Chrome** (headless):
  - màn hình tổng kết, hộp xác nhận kết thúc;
  - dashboard với backend thật: một bản tổng kết thật gửi bằng device key → quản lý thấy "Báo cáo chuyến
    đi (1 mới)" → mở chi tiết → "Đánh dấu đã xem" → hết "mới", cột "Đã xem" ghi `boss`.
  - Lỗi tìm ra khi xem ảnh chụp và đã sửa: 1 cảnh báo trong chuyến 10 phút từng bị ghi là "nhiều lần
    được nhắc". Nay cần ít nhất 2 cảnh báo.
- Chế độ mặc định / đổi tài xế (M16): 7 test.
  - Xe lái tay: đỗ / lái, tự lái sau khi đăng ký.
  - Đổi tài xế: bỏ mốc người cũ, giữ tổng kết chuyến.
  - Bridge web: mặc định xe đỗ + đăng ký, các nút, sự kiện `driver_changed`.
  - Kịch bản dựng sẵn: không có nút đỗ.
  - HUD server xếp lệnh.
- Công cụ mô phỏng lái xe (M19): 17 test (thay 7 test của M16).
  - Xe tăng / giảm tốc dần, dừng hẳn về 0, giới hạn tốc độ, xi nhan bật / đổi bên / giữ bật đến khi tắt, phím, chạy lại
    kịch bản, `GET /can` (CORS + Private-Network).
  - `ExternalVehicle`: không có tín hiệu = 0 km/h, tín hiệu cũ quá 1 s = đỗ, thời gian lái không tính lúc
    đứng; `SignalLink` đọc công cụ thật, công cụ tắt thì không lỗi.
  - Bridge web: mặc định đỗ, tốc độ và xi nhan từ công cụ, 0 km/h = đỗ, chỉ còn nút đổi tài xế.
  - HUD server chỉ xếp lệnh `change_driver`.
- Xi nhan theo phía (M20): 15 test. Chỉ nới phía xi nhan (trái / phải, trong và quá 60°), phía kia vẫn
  30°, không nới góc cúi, camera lật gương, tắt xi nhan về 30°, mốc không học, và cả pipeline từ tín hiệu
  xe tới cảnh báo.
- Đo lường (M17, M18): 13 test.
  - CI Poisson so với bảng Garwood (k = 0, 1, 3, 10), Wilson, ví dụ FL3D 2,3 / giờ (0,06–12,9).
  - Hợp đoạn, giờ đo, mức theo giây.
  - Cửa sổ: bỏ khởi động, bỏ đoạn biên, phần chưa gắn nhãn không tính là tỉnh.
  - FAR / MAR từ mức đã ghi; chấm YawDD từ trace giả theo đúng preset.
- **End-to-end trên Chrome** (headless, camera giả từ clip SUST `n_10`, tình huống "Xe đỗ"):
  - Python mới chạy trong Pyodide, 30 FPS, HUD hiện màn hình đăng ký.
  - Bước 1 qua. Bước 2 báo "Giữ đầu yên" rồi dừng sau 3 lần, vì người trong clip vừa nói vừa quay
    đầu (yaw 19–30°), không làm theo lời nhắc. HUD chuyển sang "Chưa đăng ký được", giám sát vẫn chạy.
- Trả nợ kỹ thuật (M21):
  - 10 test cho `TripRuntime`: cảnh báo, mất mặt → tạm ngưng / trở lại, mẫu mỗi phút, đăng ký gắn mốc
    mặt và đổi tài xế bỏ mốc, báo sai, mất camera tính vào tổng kết, xe chưa có tín hiệu, FPS theo đồng
    hồ, publisher nhận bản ghi.
  - Replay 2437 trace trước / sau khi tách khối 7: giống hệt (mục 3.5).
- **Test end-to-end trong repo** (M21, `frontend/e2e/`, Playwright, CI job `e2e`):
  - Backend chạy trên database tạm. Frontend là bản build có cổng test (`VITE_E2E=1`); bản production
    không chứa cổng này (đã kiểm trong bundle).
  - Camera là camera giả của Chrome. Khối 3 nhận landmark số tổng hợp thay MediaPipe, YOLO tắt. Không có
    ảnh khuôn mặt nào, không cần file model. Khối 6–14 chạy thật trong Pyodide.
  - Kịch bản 1, dùng thử: đăng ký khi đỗ → lái 60 km/h → nhắm mắt thành L3 microsleep → kết thúc chuyến.
  - Kịch bản 2, tài xế đăng nhập: đổi tài xế → đăng ký lại → kết thúc chuyến, tổng kết gửi lên → quản lý
    thấy báo cáo trên dashboard, chi tiết ghi "Đổi tài xế 1 lần".
  - 2/2 pass, khoảng 1 phút.
- 0 km/h không cảnh báo (M30): 3 kịch bản mới, 3 test cũ sửa theo. Trang điều khiển xe (M31): 3 test
  backend, 5 test frontend, kịch bản e2e thứ 3 (ghép mã, lái từ `#/drive`, đóng trang → mất tín hiệu xe).
- Vòng xử lý dừng / chậm (M28): 5 test Python (lỗi frame ngắn / kéo dài / hồi lại, FPS thấp / đúng 15 FPS,
  bridge web không ném lỗi ra trang, backend nhận 4 lý do mới), 2 test frontend.
- Tổng kết không tính nhắm mắt có chủ ý (M27): 3 test (đăng ký rồi tổng kết; nghỉ đỗ xe nhắm mắt; microsleep
  ở đèn đỏ vẫn tính); 2 test đầu đỏ trước khi sửa.
- Mất tín hiệu xe (M26): 5 test Python mới (nguồn tín hiệu mất khi chạy / khi đỗ; runtime 5 phút mất tín
  hiệu vẫn L3, có sự kiện, tổng kết; mất lúc đỗ vẫn báo, có lại tốc độ thì biết xe chạy; backend nhận lý do và trường mới, agent cũ bỏ trường vẫn nhận), 2 test
  cũ sửa theo hành vi mới, 2 test frontend.
- Cúi nhìn xuống (M25): 4 kịch bản pipeline bằng chuỗi số giả (cúi nhìn xuống → L2 không L3; cúi chậm
  không bị mang theo; nhắm thật khi cúi vẫn L3; nhắm rồi gục chậm vẫn mang theo), 1 test khối 8. Tắt
  ngưỡng mới thì 2 kịch bản đầu đỏ lại.
- Xác nhận trước khi đăng ký (M24): 8 test Python (chờ đồng ý, "Để sau" hỏi lại ở lần dừng sau, hỏi
  một lần cho mỗi tài xế, đóng khi xe chạy, tắt được bằng cấu hình, tài xế mới được hỏi lại), 2 test
  frontend; hai kịch bản e2e bấm "Đồng ý" trên màn hình mới và kiểm tra lời cam kết hiện ra.
- Âm thanh luôn bật (M23): 1 test frontend (không có âm thanh thì báo "bị chặn" và không phát gì). Hai
  kịch bản e2e vẫn pass với HUD mới.
- Ruff, format, typecheck sạch.

---

## 7. Triển khai v2 (01/10/2026)

- **Backup v1 trước khi làm gì:**
  - Bản chụp nhất quán của database v1 (SQLite backup API, chỉ đọc) và bản file gốc:
    `data/backups/driverguard-v1.1-2026-10-01.db` / `.raw.db` (trên máy, không vào git).
  - Integrity ok: 2 tài khoản, 1 thiết bị, 11 sự kiện, 5 điểm timeline.
  - Image v1 thêm tag `v1-backup`.
- **v1 chạy song song, không đổi gì:** service `driveguard`, image `v1.1`, volume và URL cũ.
- **v2 là service mới** `driveguard-v2`:
  - image `quanpk07/driveguard:v2`, volume riêng, JWT secret riêng (đăng nhập v1 và v2 độc lập);
  - `APP_VERSION=2.0.0`, `PORT=8000`.
  - Database bắt đầu từ bản sao v1: tài khoản cũ dùng được ngay; bảng `trip_summaries` tự tạo khi khởi
    động.
- **Kiểm tra trước khi đẩy:** container v2 chạy trên bản sao database v1: nâng cấp schema giữ nguyên dữ
  liệu; e2e Chrome (đăng nhập tài xế → đăng ký → lái → kết thúc chuyến → quản lý thấy "Báo cáo chuyến đi
  (1 mới)").
- **Kiểm tra sau khi đẩy:** URL v2 trả health ok và đủ file cho `#/live`; e2e chế độ dùng thử trên URL
  thật; database v2 có dữ liệu v1 + bảng mới; v1 vẫn trả 200.
- **Lỗi gặp khi deploy:** domain v2 tạo với cổng 8000 nhưng Railway cấp `PORT=8080` → 502. Sửa bằng biến
  `PORT=8000` cho service v2.
- **Quay về v1:** v1 vẫn chạy; nếu cần dựng lại thì dùng image `v1-backup` + file backup database.
- **Sau v2.0.0:** M19–M31 (đỗ / lái theo tốc độ, xi nhan theo phía, lớp chung + e2e, FMEA, âm thanh luôn
  bật, xác nhận trước khi đăng ký, cúi nhìn xuống, mất tín hiệu xe, sửa tổng kết, sức khoẻ vòng lặp, tài liệu,
  0 km/h không cảnh báo, trang điều khiển xe) đã deploy lên cùng service `driveguard-v2`, cùng URL:
  - **v2.1** (02/10, M19–M29): backup `data/backups/driverguard-v2.0.0-2026-10-02.db`, image `v2.1`,
    `APP_VERSION=2.1.0`.
  - **v2.2** (02/10, + M30, M31): backup `data/backups/driverguard-v2.1-2026-10-02.db` (integrity ok),
    image `v2.2` (= `v2` = `latest`), `APP_VERSION=2.2.0`. Sau khi đẩy: health ok, `PUT` / `GET
    /api/v1/drive/{mã}` chạy, mã sai trả 422, `#/live` có `stationary_max_level: 0`, trang `#/drive` có
    giao diện; v1 vẫn 200.
  - Quay lại bản trước: `railway service source connect --image docker.io/quanpk07/driveguard:v2.1` (hoặc
    `v2.0.0`) + file backup database tương ứng.

## 8. Giới hạn đã biết

- **Đăng ký chưa thử với người thật trước camera.** Các con số sau là đề xuất, chưa đo:
  - thời lượng mỗi bước: 2 s / 3 s / 2 s;
  - ngưỡng mắt nhắm: 0,6;
  - ngưỡng chữ ký mặt: 0,08.
- **Chữ ký mặt chưa đo trên nhiều người thật trong xe.** Đổi tài xế mới làm bằng nút, chưa tự phát
  hiện người khác ngồi vào.
- **Tốc độ vẫn là giả lập** (`tools/drive_sim.py`), chưa đọc CAN / OBD-II của xe thật. `#/live` chỉ đọc
  được công cụ chạy trên cùng máy với trình duyệt, hoặc trang `#/drive` (M31, mở được trên máy khác).
- **Trang `#/drive` không cần đăng nhập:** ai biết mã ghép 6 ký tự của một phiên `#/live` thì chỉnh được tốc độ
  của phiên đó (chỉ trong bản xem thử; không đụng dữ liệu).
- **Mốc mắt nhắm** dùng để kiểm tra đăng ký và làm thang đo tốc độ chớp. Chưa dùng để đổi thang
  `close_ratio`.
- **Chớp chậm, nhướn mày: ngưỡng tạm**, chưa dò trên dataset.
  - Chớp chậm thêm 1 cảnh báo L1 sai trên FL3D.
  - Nhướn mày chưa đo được.
  - Đo bằng camera 15–30 FPS chỉ có vài frame mỗi lần mở mi, thô hơn nhiều so với thiết bị hồng
    ngoại trong các nghiên cứu.
- **Phép thử gục / cúi đang tắt**, chờ clip có nhãn cúi nhìn điện thoại / bảng đồng hồ.
- **Bảng tổng kết:**
  - Chưa so với các chuyến trước của cùng tài xế, chưa có biểu đồ nhiều chuyến cho kỹ sư (việc 21 trong
    improvements).
  - Trên web, bản tổng kết chưa gửi được (mất mạng lúc kết thúc) thì mất khi rời trang, vì trình duyệt
    không có outbox lâu dài. HUD nói rõ điều này.
  - Luật đánh giá chưa được thử với quản lý thật.
- **Cảnh báo L2 / L3 không đọc thành tiếng:** đã cân nhắc rồi bỏ (mục 4), chỉ dùng câu chữ và âm báo.
- **Giao diện mới chưa test với tài xế thật** (buổi test 10 người của PRD).
- **Web: độ sáng cho khối 5** vẫn đo trên mặt to nhất, không theo mặt tài xế được chọn.
- **Giọng nói** phụ thuộc trình duyệt có giọng tiếng Việt hay không.
- ~~**Bảng tổng kết tính bước "nhắm mắt" của đăng ký là ngủ gật**~~ (đã sửa ở M27; tìm ra khi viết test e2e ở M21, có từ
  trước M21). Bước 3 khi xe đỗ sinh sự kiện `microsleep` ở khối 7. Không có cảnh báo, nhưng khối 11
  vẫn đếm nên chuyến bị xếp "Có lúc rất nguy hiểm: nhắm mắt ngủ gật khi đang lái", dù 0 giây lái.
  Chưa sửa.
- **Test e2e không kiểm MediaPipe JS và YOLO trên web** (landmark do test đưa vào). Hai phần này vẫn
  phải thử tay với camera thật.
- **Các trạng thái im lặng mức Cao (M22, `docs/safety-fmea.md`):**
  - ~~HUD khởi động tắt tiếng~~: đã sửa ở M23. Còn lại: HUD trên thiết bị mở mà chưa ai chạm thì trình
    duyệt vẫn chặn tiếng (có dải vàng nhắc).
  - ~~Mất tín hiệu tốc độ khi đang chạy = xe đỗ~~: đã sửa ở M26 (mất tín hiệu lúc đỗ cũng được báo). Còn
    lại: đỗ, mất tín hiệu rồi chạy đi thì giám sát hạn chế tới khi có lại tốc độ.
  - ~~Vòng xử lý dừng / lỗi lặp lại: không tiếng, backend không biết~~: đã sửa ở M28. Còn lại: tiến trình
    chết hẳn thì backend chưa biết ngay.
  - **Kính râm** (chưa kiểm chứng): EAR có thể luôn đọc là mắt mở mà hệ thống không biết.
- **Cúi nhìn xuống (M25): ngưỡng tạm.** Chưa đo EAR thật khi nhìn điện thoại. Ca SUST `n_368` (cúi 17°,
  EAR 0,26 lần mốc) vẫn lọt; frame do CNN mắt quyết định chưa có quy tắc "đầu cúi"; tài xế buồn ngủ mắt
  lim dim, đầu gục nhẹ có thể nhận L2 nhìn lệch thay vì cảnh báo buồn ngủ. Xem improvements việc 5.
- **"Tạm ngưng giám sát" mới áp dụng cho mất mặt.** FR-6 còn nêu chất lượng ảnh kém, góc xấu, lóa:
  chưa làm.
