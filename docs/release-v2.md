# DriveGuard — Version 2

> Bản tiếp theo của [Version 1](release-v1.md). Ghi lại mọi cải tiến, chỉnh sửa làm sau v1.1: cái gì
> **thêm**, cái gì **sửa**, cái gì **bỏ**, và đã kiểm chứng tới đâu.
> Nguyên tắc giữ nguyên: mọi xử lý hình ảnh chạy trên thiết bị hoặc trong trình duyệt, không gửi và
> không lưu ảnh khuôn mặt, chỉ gửi metadata JSON.

| | |
|---|---|
| **Phiên bản** | v2.0.0, deploy 01/10/2026, dựa trên v1.1 |
| **Mã nguồn** | nhánh `DAQuan` (commit `679a44a` → `0a47d76` + merge `origin/main`), chưa PR vào `main` |
| **Web v2** | https://driveguard-v2-production.up.railway.app (camera: `/#/live`) |
| **Web v1 (giữ nguyên, chạy song song)** | https://driveguard-production-6b83.up.railway.app |
| **Image Docker** | `quanpk07/driveguard:v2` (cũng là `latest`), 72,7 MB; v1 giữ ở `v1.1` và `v1-backup` (cùng digest `5de7028…`) |
| **Triển khai** | Railway project DriveGuard: service `driveguard-v2` (volume riêng `driveguard-v2-volume`), service v1 `driveguard` không đổi. Database v2 khởi đầu bằng bản sao database v1 lúc 01/10 (tài khoản, lịch sử), sau đó tách riêng |
| **Mốc trong lộ trình** | M9 (đăng ký tài xế), M10 (mất mặt → tạm ngưng giám sát), M11 (chớp chậm), M12 (gục đầu / cúi đầu), M13 (nhướn mày), M14 (giao diện cho tài xế), M15 (kết thúc chuyến + bảng tổng kết), M16 (một chế độ mặc định, tạm dừng / đổi tài xế), M17 (sửa cách đo báo sai), M18 (FAR / MAR theo cửa sổ), xem [roadmap.md](roadmap.md) |

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
| **Thêm** | Nút "Tạm dừng" (đỗ xe), "Tiếp tục lái", "Đổi tài xế" (người lái mới đăng ký lại khuôn mặt) trên HUD | M16 | 01/10 |
| **Sửa** | Tắt telemetry của onnxruntime (tự gửi dữ liệu về Microsoft, và làm tiến trình lỗi khi thoát) | M16 | 01/10 |
| **Sửa** | Cách đo báo sai / giờ: kèm số giờ đo và CI 95%, chia đúng mẫu số, tách lý do × mức | M17 | 01/10 |
| **Thêm** | FAR / MAR theo cửa sổ 10 s trong công cụ eval (bổ sung, không thay báo sai / giờ) | M18 | 01/10 |
| **Bỏ** | Chống chói đèn pha bằng phần mềm: giao cho yêu cầu đầu vào camera (camera IR) | — | 01/10 |
| **Bỏ** | Việc "bám tài xế" riêng: do bước đăng ký đảm nhận | — | 01/10 |

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
- **Tất cả ngưỡng là tạm**, chờ dò trên UTA-RLDD (việc 6 trong improvements).

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
- Cần clip có nhãn gồm cả cúi và gục (việc 9 trong improvements).

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

---

## 4. Bỏ, không làm

- **Chống chói đèn pha bằng phần mềm** (cờ chói, trigger `overexposed` ở khối 5): giải quyết bằng yêu
  cầu đầu vào camera (camera IR + đèn LED IR 850/940 nm, như DMS thương mại). Mất mặt do chói thì
  thành "Tạm ngưng giám sát" (mục 3.1).
- **Bám tài xế thành việc riêng:** nhận ra tài xế do bước đăng ký xác định (mục 2.2).

---

## 5. Tương thích khi nâng cấp từ v1

- **`config/thresholds.yaml`:**
  - Thêm nhóm `enrollment:`.
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
- **Backend:** nhận thêm 3 lý do hệ thống (`driver_enrolled`, `monitoring_unavailable`,
  `monitoring_restored`) và 6 trường metrics (`enrolled`, `enroll_s`, `enroll_redo`,
  `blink_time_frac`, `reopen_ratio`, `brow_raise_count_5min`).
  - Batch nhận thêm `summaries` (bản tổng kết chuyến) và trả `summaries_accepted`.
  - Có bảng mới `trip_summaries`, tự tạo khi khởi động.
  - Có API `/api/v1/trip-reports`.
- **HUD server trên thiết bị:** thêm `POST /end-trip`; `/state` có `trip_ended`. Lý do
  `no_face` vẫn được nhận để không lỗi với sự kiện cũ trong database. Sự kiện hệ thống không tính vào
  thống kê cảnh báo.
- **Eval:** công cụ eval cho xe chạy 60 km/h từ đầu nên không bao giờ đăng ký: số đo vẫn dùng mốc tự
  học như v1. SUST-DDD đổi vì mục 3.1. FL3D đổi vì chớp chậm (mục 2.5). Gục đầu giữ như v1.
- **Edge agent v1 gửi lên backend v2:** vẫn chạy. Edge agent v2 gửi lên backend v1 thì sự kiện mới
  bị từ chối, nên deploy backend trước.

---

## 6. Kiểm thử

| | v1 | v2 |
|---|---:|---:|
| Test Python | 434 | **519** |
| Test frontend | 25 | **38** |

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
- Đo lường (M17, M18): 13 test.
  - CI Poisson so với bảng Garwood (k = 0, 1, 3, 10), Wilson, ví dụ FL3D 2,3 / giờ (0,06–12,9).
  - Hợp đoạn, giờ đo, mức theo giây.
  - Cửa sổ: bỏ khởi động, bỏ đoạn biên, phần chưa gắn nhãn không tính là tỉnh.
  - FAR / MAR từ mức đã ghi; chấm YawDD từ trace giả theo đúng preset.
- **End-to-end trên Chrome** (headless, camera giả từ clip SUST `n_10`, tình huống "Xe đỗ"):
  - Python mới chạy trong Pyodide, 30 FPS, HUD hiện màn hình đăng ký.
  - Bước 1 qua. Bước 2 báo "Giữ đầu yên" rồi dừng sau 3 lần, vì người trong clip vừa nói vừa quay
    đầu (yaw 19–30°), không làm theo lời nhắc. HUD chuyển sang "Chưa đăng ký được", giám sát vẫn chạy.
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

## 8. Giới hạn đã biết

- **Đăng ký chưa thử với người thật trước camera.** Các con số sau là đề xuất, chưa đo:
  - thời lượng mỗi bước: 2 s / 3 s / 2 s;
  - ngưỡng mắt nhắm: 0,6;
  - ngưỡng chữ ký mặt: 0,08.
- **Chữ ký mặt chưa đo trên nhiều người thật trong xe.** Đổi tài xế mới làm bằng nút, chưa tự phát
  hiện người khác ngồi vào.
- **Chế độ mặc định giả lập tốc độ cố định 50 km/h khi lái.** Chưa có cao tốc (> 80 km/h, ngưỡng nhìn
  lệch chặt hơn) hay xi-nhan. Muốn thử thì dùng kịch bản CAN trên thiết bị.
- **Mốc mắt nhắm** dùng để kiểm tra đăng ký và làm thang đo tốc độ chớp. Chưa dùng để đổi thang
  `close_ratio`.
- **Chớp chậm, nhướn mày: ngưỡng tạm**, chưa dò trên dataset.
  - Chớp chậm thêm 1 cảnh báo L1 sai trên FL3D.
  - Nhướn mày chưa đo được.
  - Đo bằng camera 15–30 FPS chỉ có vài frame mỗi lần mở mi, thô hơn nhiều so với thiết bị hồng
    ngoại trong các nghiên cứu.
- **Phép thử gục / cúi đang tắt**, chờ clip có nhãn cúi nhìn điện thoại / bảng đồng hồ.
- **Bảng tổng kết:**
  - Chưa so với các chuyến trước của cùng tài xế, chưa có biểu đồ nhiều chuyến cho kỹ sư (việc 15 trong
    improvements).
  - Trên web, bản tổng kết chưa gửi được (mất mạng lúc kết thúc) thì mất khi rời trang, vì trình duyệt
    không có outbox lâu dài. HUD nói rõ điều này.
  - Luật đánh giá chưa được thử với quản lý thật.
- **Cảnh báo L2 / L3 chưa được đọc thành tiếng** (việc 16). Mới có câu chữ và âm báo.
- **Giao diện mới chưa test với tài xế thật** (buổi test 10 người của PRD).
- **Web: độ sáng cho khối 5** vẫn đo trên mặt to nhất, không theo mặt tài xế được chọn.
- **Giọng nói** phụ thuộc trình duyệt có giọng tiếng Việt hay không.
- **"Tạm ngưng giám sát" mới áp dụng cho mất mặt.** FR-6 còn nêu chất lượng ảnh kém, góc xấu, lóa:
  chưa làm.
