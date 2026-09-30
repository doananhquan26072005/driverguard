# Hướng cải tiến DriverGuard

Danh sách để chọn mốc tiếp theo, không phải kế hoạch. Theo CLAUDE.md, không mục nào được làm
trước khi có yêu cầu; mục nào được chọn thì thêm thành mốc trong `docs/roadmap.md`.

Cập nhật: 30/09/2026 (bảng việc theo mức ưu tiên, mỗi task có link xuống chi tiết và cột người thực
hiện; thêm việc để cuối: đóng gói APK, giao diện cho tài xế; thêm việc đo tài nguyên phần cứng;
thêm việc tối ưu ngưỡng buồn ngủ trên UTA-RLDD).

## Danh sách việc theo mức ưu tiên

Bấm tên việc để xuống phần chi tiết. Số thứ tự dùng để gọi tắt khi chọn mốc ("làm việc 2"). Đây chỉ
là đề xuất, bạn quyết định làm việc nào.

### Cần quyết định trước
Chưa phải việc code, nhưng chặn các việc khác.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| A | [Chốt mất mặt 3 s](#quyet-dinh) | FR-6: mất mặt ≥ 3 s khi xe chạy báo L2 (như code) hay im lặng ở `unavailable` (như PRD) (chặn việc 3, 11) |  |
| B | [Chốt cách đăng ký tài xế](#quyet-dinh) | Bắt buộc hay bỏ qua được; chữ ký mặt có giữ qua chuyến không; khối mới hay gộp vào khối cũ (chặn việc 2, 4) |  |

### Ưu tiên cao: làm trước
Nhỏ, giảm báo sai hoặc sửa lỗi đo, không thêm model, không ảnh hưởng FPS, test được bằng chuỗi số giả.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 1 | [Sửa cách đo báo sai](#viec-do-bao-sai) | Thêm khoảng tin cậy (CI Poisson) + số giờ dữ liệu vào mọi bảng; tách theo lý do / mức |  |
| 2 | [Học mặt tài xế lúc khởi động](#dang-ky-buoc-a) | Màn hình hướng dẫn nhìn thẳng / nhìn đường / nhắm mắt → mốc mắt, miệng, tư thế đầu của riêng tài xế |  |
| 3 | [Chống chói đèn pha](#viec-choi) | Cờ chói + trigger `overexposed` ở khối 5 |  |
| 4 | [Nhận ra tài xế](#dang-ky-buoc-b) | Bám tài xế giữa các frame bằng chữ ký mặt + vị trí ghế lái + hysteresis |  |

### Ưu tiên vừa
Thêm tín hiệu / luật mới, vẫn không thêm model.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 5 | [Đo tốc độ chớp mắt](#viec-chop-mat) | Thời lượng chớp, thời gian mở mắt lại, tỉ lệ chớp dài |  |
| 6 | [Tách gục đầu với liếc đồng hồ](#viec-guc-dau) | Gục đầu = cúi chậm rồi ngẩng nhanh |  |
| 7 | [Theo dõi hướng mắt](#viec-huong-nhin) | Hướng nhìn từ blendshape `eyeLook*` + mống mắt |  |
| 8 | [So định nghĩa PERCLOS](#viec-perclos) | Chạy P80 song song với ngưỡng 0,65 hiện tại |  |
| 9 | [Tách giai đoạn khởi động khi đo](#viec-do-bao-sai) | Báo riêng 30 s đầu clip; vẽ đường đánh đổi báo sai ↔ bắt sự kiện khi đổi ngưỡng |  |
| 10 | [Cảnh báo theo độ dài nhắm mắt](#viec-muc-nham-mat) | Thêm mốc nhắm 3 s và 6 s; 6 s sinh sự kiện `unresponsive` |  |
| 11 | [Báo tạm ngưng giám sát](#viec-mat-mat-10s) | Mất mặt 10 s → `monitoring_unavailable` |  |
| 22 | [Tối ưu ngưỡng buồn ngủ trên UTA-RLDD](#viec-toi-uu-nguong) | Trace UTA-RLDD một lần, dò ngưỡng nhánh buồn ngủ + `drowsy_score` bằng `seq_eval --replay`, chọn theo fold người; làm sau việc 1 |  |

### Ưu tiên thấp
Cần công cụ, dữ liệu hoặc model mới, hoặc còn chưa chắc có lợi.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 12 | [Thử model mắt mới](#viec-model-mat) | Sửa `seq_eval` để trace thêm cột → thử `blinkcnn` / OCEC offline |  |
| 13 | [Quay clip + đo độ trễ cảnh báo](#viec-prd) | Clip tự quay có nhãn + công cụ đo time-to-alert |  |
| 14 | [Học vùng nhìn, nhận mặt bằng model](#dang-ky-buoc-c) | Học tư thế nhìn gương / đồng hồ; embedding mặt nếu việc 4 không đủ |  |
| 15 | [Nhướn mày](#viec-nhuon-may) | Nhướn mày làm thành phần phụ của `drowsy_score` |  |
| 16 | [Tăng tương phản trên web](#viec-choi) | Cân bằng tương phản bằng WebGL |  |
| 17 | [Làm nốt yêu cầu PRD](#viec-prd) | LLM (FR-12/13), Docker edge, nhật ký (FR-8/9/17), test 10 người, nộp bài |  |
| 18 | [Tải thử dataset](#viec-tai-dataset) | Tải thử NTHU-DDD (HF `train.zip`), mở Dropbox Brain4Cars |  |

### Không gấp: để cuối
Không đổi độ chính xác, chỉ đổi cách dùng.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 19 | [Đóng gói app APK](#viec-apk) | Gói bản web thành app Android chạy offline |  |
| 20 | [Giao diện cho tài xế](#viec-giao-dien) | Bỏ thuật ngữ chuyên ngành, gộp các bước tải thành một |  |

### Phụ thuộc phần cứng
Cần thiết bị thật hoặc tín hiệu xe thật.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 21 | [Đo tài nguyên phần cứng](#viec-do-phan-cung) | Đo CPU, RAM, nhiệt độ, FPS khi chạy lâu trên hub gắn trên xe và trên máy chạy project; thêm vào `tools/benchmark.py` |  |
| — | [Phần cứng thật](#viec-phan-cung) | Camera IR, xi-nhan / tốc độ CAN thật |  |

---

<a id="quyet-dinh"></a>

## 1. Cần quyết định

- **FR-6:** mất mặt ≥ 3 s khi xe chạy nên báo L2 (như code) hay im lặng ở `unavailable` (như PRD)?
  Liên quan trực tiếp mục 6: nếu giữ L2 thì cần cờ chói để tránh báo sai do đèn pha.
- **Đăng ký tài xế (mục 4):**
  - Bắt buộc lúc khởi động, hay cho phép bỏ qua và quay về cách tự học hiện tại?
  - Chữ ký mặt (dãy số, không phải ảnh) chỉ giữ trong RAM trong một chuyến, hay được lưu lại để lần
    sau tài xế quen không phải đăng ký lại? Lưu lại là lưu dữ liệu sinh trắc, dù không vi phạm chữ
    "ảnh" trong CLAUDE.md.
  - Làm thành khối mới trong kiến trúc 14 khối, hay là một giai đoạn của khối 6 / 7 / 8?
- **Cooldown L3:** HUD vẫn đỏ khi cảnh báo bị cooldown giữ lại. Worklog ghi là thiết kế, đang chờ
  xác nhận.
- **License YOLO (AGPL-3.0):** Ultralytics ghi mọi model YOLO của họ, kể cả model fine-tune và bản
  export ONNX / TFLite, mặc định thuộc AGPL-3.0; sản phẩm thương mại, SaaS / API, triển khai trên
  thiết bị edge hay phần mềm đóng mã thì phải mở mã toàn bộ theo AGPL hoặc mua Enterprise License
  [Y10]. Áp dụng cho `models/yolov8n.onnx` và `yolov8n_int8.onnx` đang dùng cho điện thoại (repo
  đang để LICENSE MIT; `docs/release-v1.md` đã có ghi chú AGPL). **Đã chốt (29/09): dự án học tập,
  không thương mại → giữ YOLO, không mua license.** Việc còn lại nếu muốn làm đúng AGPL: bản web trên
  Railway là dịch vụ mạng có dùng YOLO, nên khi công khai thì để mã nguồn truy cập được (vd. repo
  public, ghi rõ phần YOLO theo AGPL). (Không phải tư vấn pháp lý.)

---

## 2. Metric đánh giá: cảnh báo sai / giờ

**Nhận định:** giữ "cảnh báo sai / giờ" (alert burden) làm metric chính. Nó đo đúng thứ tài xế cảm
nhận (bị làm phiền bao nhiêu lần / giờ), khớp PRD (≤ 1,0 / giờ) và ưu tiên chống báo sai. Nhưng **cách
đo hiện tại chưa đủ để kết luận đạt hay chưa đạt.**

### Vấn đề
1. **Quá ít giờ dữ liệu, chưa có khoảng tin cậy.** Khoảng tin cậy 95% theo Poisson (exact):

   | Nguồn | Đang báo | CI 95% |
   |---|---:|---:|
   | FL3D L1 (1 sai / 26 phút tỉnh táo) | 2,3 / giờ | 0,06 – 12,9 / giờ |
   | FL3D L2 (3 sai / 26 phút) | 6,9 / giờ | 1,4 – 20 / giờ |
   | YawDD (~10 sai / 124 phút) | 4,8 / giờ | 2,3 – 8,9 / giờ |

   Một lần sai trên FL3D đã bằng 2,3 / giờ. PRD §6 bắt buộc kèm số giờ clip + CI và cấm kết luận "đạt
   ≤ 1,0 / giờ"; `eval/results/report.md` chưa có CI.
2. **Dữ liệu không giống lái thật.** NITYMED diễn lại, YawDD xe đỗ: mật độ hành vi dày hơn lái thật
   (phần lớn là nhìn đường nhàm chán). SUST / YawDD là nhiều clip ngắn ghép lại, clip nào cũng rơi vào
   giai đoạn khởi động (mốc EAR chưa ổn, hiệu chỉnh 5 s đầu) → "một giờ" thực chất là hàng trăm lần
   khởi động. Tốc độ giả lập cố định 60 km/h nên luật ngữ cảnh (dừng đèn đỏ, xi-nhan) không được thử.
3. **Định nghĩa "sai" trộn nhiều loại lỗi.** Sai = cảnh báo trên đoạn nhãn tỉnh táo, nhưng dataset chỉ
   gán nhãn buồn ngủ, không gán mất tập trung. SUST: 25/34 lần "sai" là `off_road` khi tài xế quay đầu
   thật, có thể là cảnh báo đúng hoặc chỉ ngưỡng hơi chặt.
4. **Đứng một mình thì dễ bị lừa:** hệ thống không bao giờ cảnh báo đạt 0 / giờ. Phải đi cùng tỉ lệ
   bắt sự kiện và time-to-alert (PRD p95 ≤ 3 s, chưa có công cụ đo, xem mục 10).
5. **Số HITL trên dashboard không cùng loại:** `false_alarms / tổng cảnh báo` là precision, không phải
   / giờ, và phụ thuộc tài xế có bấm nút hay không.

<a id="viec-do-bao-sai"></a>

### Hướng đề xuất (dễ → khó)
1. **Thêm CI Poisson + số giờ dữ liệu** vào mọi bảng cảnh báo sai / giờ (báo cáo + công cụ eval). Đây là
   yêu cầu có sẵn của PRD.
2. **Tách theo lý do và mức** (microsleep, drowsy, off_road, phone, no_face × L1–L3). `off_road` trên
   dataset buồn ngủ thì gán nhãn lại hoặc để riêng "chưa xác định".
3. **Tách giai đoạn khởi động** (vd. 30 s đầu mỗi clip) khỏi số chính, báo cáo riêng.
4. **Đường đánh đổi** cảnh báo sai / giờ ↔ tỉ lệ bắt sự kiện khi đổi ngưỡng, dùng
   `tools/seq_eval.py --replay` (khối 7–12, không cần chạy lại MediaPipe) để thấy ngưỡng hiện tại đứng
   ở đâu thay vì một điểm duy nhất.
5. **Dữ liệu dài, liên tục:** tự quay vài chuyến 30–60 phút (gộp với clip tự quay ở mục 10). Dataset
   đã kiểm tra (mục 3): **UTA-RLDD** cho cảnh báo sai / giờ, **DMD** cho recall theo frame và
   time-to-alert; hai bộ bổ sung cho nhau.

Đề xuất 1–2 là việc nhỏ, có thể tách thành một mốc riêng.

---

## 3. Dữ liệu đánh giá

Kiểm tra 30/09/2026 (metadata, trang chính, license), chưa tải, chưa chạy thử. Tất cả chỉ dùng để
đánh giá: không đưa frame / ảnh mặt vào repo, báo cáo hay slide, chỉ số liệu. Muốn dùng bộ nào thì
thêm thành mốc riêng (cần task mới trong `tools/dataset.py`).

| Dataset | Dùng cho | Lấy thế nào | Trạng thái |
|---|---|---|---|
| UTA-RLDD | Cảnh báo sai / giờ (~8 giờ tỉnh táo), buồn ngủ thật theo mức 0 / 5 / 10 | Kaggle 96,6 GB, hoặc Kaggle Notebook | Nên dùng (việc 1) |
| DMD | Recall theo frame, time-to-alert, ngáp che tay, mất tập trung, hướng nhìn | Cổng DMD, CC BY-NC-ND | Nên dùng |
| DROZY | Buồn ngủ thật + KSS / PVT / EEG, IR phụ | ORBi 2,46 GB, tải thẳng | Nên dùng |
| NTHU-DDD | Video IR, kính râm, gục đầu, nói / cười (báo sai) | HF gated `auto` hoặc email NTHU | Cần xem `train.zip` trước |
| Brain4Cars | `off_road` khi rẽ / chuyển làn, tốc độ thật | Dropbox 16 GB | Cần xem độ dài clip trước |

### Phần dữ liệu còn thiếu và nguồn lấp

Đối chiếu dữ liệu đã có / sắp có (FL3D, YawDD, SUST, UTA-RLDD, DMD) với điều kiện PRD FR-9 và các khối.
Đã bỏ khỏi danh sách (chốt 30/09): ngược sáng / đèn pha, mặt người Việt, điện thoại để thấp, khẩu
trang, mũ lưỡi trai, hai người trong khung hình (không cần dataset; mục 4 bước B nếu làm thì test
bằng chuỗi landmark / khung bao giả). Mọi phần còn lại đều đã có nguồn.

| Phần thiếu | Nguồn | Trạng thái |
|---|---|---|
| Kính râm | NTHU-DDD (bối cảnh `Sunglasses`) | Có nguồn |
| Video IR cả khuôn mặt | NTHU-DDD (camera + đèn IR, 640×480); DROZY (Kinect NIR, phụ) | Có nguồn |
| Buồn ngủ thật, có số liệu khách quan | DROZY (KSS, PVT, EEG); UTA-RLDD (KSS tự đánh giá) | Có nguồn |
| Gục đầu có nhãn | NTHU-DDD (nhãn đầu, *chưa kiểm chứng*), DMD (diễn) | Có nguồn |
| Xi-nhan, tốc độ, rẽ thật | Brain4Cars | Có nguồn, không có xi-nhan; clip 5 s |

<a id="uta-rldd"></a>

### UTA-RLDD

Nguồn: Kaggle `rishab260/uta-reallife-drowsiness-dataset` [U1], bản gốc [U2], paper Ghoddoosian et
al., CVPRW 2019. Kiểm tra qua Kaggle API, chưa tải, chưa chạy thử.

**Kết luận: nên dùng**, nhưng chỉ cho (a) cảnh báo sai / giờ trên video tỉnh táo và (b) `drowsy_score`
có tăng theo mức buồn ngủ trên cùng một người hay không. Không dùng được để đo tỉ lệ bắt microsleep /
ngáp; không giúp mục 6 (đêm, chói) hay điện thoại.

| | Bản gốc | Bản Kaggle |
|---|---|---|
| Người | 60 | **48** (thiếu Fold 5) |
| Video | 180 × ~10 phút | 145 file, ~24 giờ; `.mov` / `.mp4` / `.m4v` |
| Dung lượng | 111 GB | **96,6 GB** (21 MB – 1,6 GB / file) |
| Nhãn | theo tên file `0` tỉnh, `5` hơi buồn ngủ, `10` buồn ngủ (KSS tự đánh giá) | như gốc; người 32 có `10_1` + `10_2` |

- Tự quay bằng điện thoại / webcam cách một sải tay, < 30 fps, lúc đọc / xem laptop. Buồn ngủ thật,
  không diễn. 21/180 video đeo kính.

**Vì sao cần:**
- ~8 giờ video tỉnh táo liên tục, 48 người (FL3D chỉ 26 phút). 0 cảnh báo sai trên 8 giờ → cận trên
  CI 95% ≈ 0,46 / giờ: lần đầu kết luận được mục tiêu PRD ≤ 1,0 / giờ.
- Video 10 phút: giai đoạn khởi động chỉ là phần nhỏ (khác SUST / YawDD).
- Cùng người có đủ 3 mức: so `drowsy_score`, `perclos_60s` giữa 0 / 5 / 10; kiểm tra được mốc mắt
  mở cố định (mục 4, học từ video `0` rồi dùng cho `5` / `10`) và trip memory.

**Hạn chế:**
- Nhãn cả video, là trạng thái "phần lớn thời gian": video `10` có thể không có microsleep → không đo
  được recall sự kiện hay time-to-alert, chỉ so phân bố điểm.
- Mức `5` (KSS 6–7) không rõ đúng / sai: báo riêng (L1 hợp lý, L3 đáng xem lại).
- Không lái xe, nhìn laptop hơi cúi: tách `off_road` / `phone` khỏi số báo sai của nhánh buồn ngủ;
  tốc độ giả lập như các dataset khác.
- Chủ yếu RGB, trong nhà, ban ngày.
- License: bản Kaggle ghi CC0 nhưng là bản đăng lại; trang gốc không ghi CC0. Dự án không thương mại
  nên không chặn, cần trích dẫn paper.
- Quyền riêng tư: chỉ 36/60 người đồng ý công khai mặt → không đưa frame vào báo cáo / slide / repo,
  chỉ số liệu.
- Nặng: chạy đủ pipeline trên 24 giờ video mất nhiều giờ → trace một lần rồi `seq_eval --replay`.

**Chạy mà không tải về máy:**
- **Kaggle Notebook (đề xuất):** "New Notebook" từ trang dataset, dữ liệu gắn sẵn ở
  `/kaggle/input/uta-reallife-drowsiness-dataset/` (đọc trực tiếp, không tốn quota tải). Clone repo,
  `pip install` (bật Internet cho notebook, cần xác minh số điện thoại), chạy với
  `--root /kaggle/input/...`. `models/` không nằm trong git → upload thành Kaggle Dataset riêng (private)
  rồi gắn vào notebook. Giới hạn: phiên CPU tối đa 12 giờ, output 20 GB → chia theo fold, chỉ lưu
  metric / trace CSV (không lưu frame, đúng ràng buộc CLAUDE.md). *(Giới hạn phiên / output theo tài
  liệu Kaggle, chưa kiểm tra lại.)*
- **Tải từng file rồi xoá:** `kagglehub.dataset_download(..., path="Fold1_part1/.../0.mov")` lấy từng
  video (0,02–1,6 GB), chạy xong xoá. Vẫn là tải, nhưng không cần 97 GB trống.
- Không nên đọc stream qua URL bằng OpenCV: file `.mov` / `.mp4` thường đặt chỉ mục ở cuối file, dễ lỗi.

Dùng để chỉnh ngưỡng buồn ngủ: [việc 22](#viec-toi-uu-nguong).

**Cần làm nếu chọn (mốc riêng):** task mới trong `tools/dataset.py` (vd. `video_drowsy`, nhãn từ tên
file `0` / `5` / `10`, gộp `10_1` / `10_2`), báo cáo cảnh báo sai / giờ + CI trên video `0` và phân
bố `drowsy_score` theo mức. Nên gộp với đề xuất 1–2 ở mục 2. Thử 1 fold (~12 GB) trước.

- U1. https://www.kaggle.com/datasets/rishab260/uta-reallife-drowsiness-dataset
- U2. https://sites.google.com/view/utarldd/home

<a id="dmd"></a>

### DMD — Driver Monitoring Dataset

Nguồn: trang chính [D1], GitHub + wiki [D2][D3], paper Ortega et al., ECCV Workshops 2020 [D4]. Đọc tài
liệu, chưa tải, chưa chạy thử.

**Kết luận: nên dùng, bổ sung đúng chỗ UTA-RLDD thiếu.** Buồn ngủ là **diễn**, nhưng có **nhãn theo
từng frame**: đo được recall sự kiện, độ trễ và time-to-alert. Cảnh báo sai / giờ vẫn lấy từ UTA-RLDD.

- Gốc: 37 tài xế, ~41 giờ, 3 camera (mặt / thân / tay) × RGB + IR + Depth, xe thật + mô phỏng.
- **Bản hiện tại đã cắt:** chỉ RGB, chỉ xe thật, chỉ **14 người** (ID 1, 5, 6, 7, 9, 10, 13, 14, 23,
  28, 29, 33, 36, 37) do quyền riêng tư. Chia 3 bộ: Drowsiness, Distraction, Gaze & Hands. Nhãn
  OpenLABEL / VCD (JSON), video mp4.
- Nhãn bộ Drowsiness [D3]: trạng thái mắt **mọi frame** (Opened / Closed / Opening / Closing /
  Undefined); chớp mắt (từ lúc bắt đầu nhắm đến lúc mở hẳn); ngáp **có / không che tay**; che khuất
  camera. Tài xế được yêu cầu diễn: mí mắt hạ, microsleep, ngáp, gục đầu.

| | UTA-RLDD | DMD |
|---|---|---|
| Buồn ngủ | Thật | Diễn |
| Nhãn | Cả video (0 / 5 / 10) | Từng frame |
| Đo tốt nhất | Cảnh báo sai / giờ (~8 giờ tỉnh táo) | Recall sự kiện, time-to-alert, chớp mắt, ngáp che tay |
| Mất tập trung | Không | Có (bộ riêng) |

**Dùng cho:**
- Khối 5, 7 theo frame: so `eye_closed`, `closed_duration`, `blink_rate` với nhãn; đo độ trễ phát hiện
  nhắm / mở, độ chính xác đếm chớp.
- **Time-to-alert p95 ≤ 3 s** (mục 10: chưa có công cụ đo).
- **Ngáp che tay:** tay che làm landmark miệng / MAR sai; chưa dataset nào khác có nhãn này.
- Bộ Distraction / Gaze: nhãn gọi điện, nhắn tin, vùng nhìn (gương, cửa sổ, bảng đồng hồ) → đo
  `off_road`, `phone` (khối 8) và mục 7 (hướng nhìn).
- Camera mặt đặt gần trên xe thật, giống bố cục camera taplo.

**Hạn chế:**
- Diễn thì rõ và cường điệu hơn thật → recall lạc quan.
- 14 người, không còn IR → không giúp mục 6 (đêm).
- Hành động nguy hiểm trên xe thật làm khi **xe đứng yên** → phải giả lập tốc độ, nếu không luật ngữ
  cảnh (khối 10) tắt cảnh báo.
- License **CC BY-NC-ND 4.0, chỉ dùng học thuật**. Dự án không thương mại nên dùng được; ND = không
  phân phối lại dữ liệu đã sửa, công bố số liệu thì được. Không đưa frame vào repo / slide.
- Cần viết phần đọc OpenLABEL JSON và gióng nhãn với frame: nặng hơn task `video_drowsy` cho UTA.
- Wiki có nhắc microsleep, nhưng annotation criteria không có nhãn microsleep riêng → suy ra từ đoạn
  `Closed` đủ dài.
- *Chưa kiểm chứng:* dung lượng bộ Drowsiness, số giờ còn lại sau khi cắt, có cần đăng ký không
  (hỏi info-dmd@vicomtech.org).

**Cần làm nếu chọn (mốc riêng):** đọc nhãn OpenLABEL → task video theo frame trong `tools/dataset.py`,
báo cáo recall microsleep / ngáp, độ trễ, time-to-alert p95. Nên làm sau UTA-RLDD (mốc cảnh báo sai /
giờ); gộp được với công cụ đo time-to-alert (việc 13).

- D1. https://dmd.vicomtech.org/
- D2. https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset
- D3. https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-drowsiness-related-action-annotation-criteria
- D4. https://arxiv.org/pdf/2008.12085

### DROZY (ULg, WACV 2016) [N4][N5]

- 14 người (3 nam, 11 nữ), 3 bài PVT 10 phút, thiếu ngủ thật tăng dần; còn ~36/42 bài (6 bài mất).
- Video NIR Kinect v2 512×424, 8 bit xám, mp4, chủ yếu 30 fps. Có KSS, thời gian phản xạ PVT, PSG /
  EEG, 68 landmark 2D / 3D.
- Tải thẳng `DROZY.zip` **2,46 GB** trên ORBi, không đăng ký.
- License (bản 18/07/2018, đã đọc): chỉ nghiên cứu / đánh giá, không thương mại; không phân phối lại,
  không sửa; không lộ danh tính; **không hiển thị ảnh** (trừ ảnh đánh dấu công bố được); trích dẫn
  Massoz et al., WACV 2016.
- Dùng: so `drowsy_score` / PERCLOS với KSS và thời gian phản xạ. Không phải lái xe (làm test trước
  màn hình); IR Kinect không giống camera DMS.

### NTHU-DDD (NTHU CVlab, ACCV Workshop 2016) [N1]

- 36 người, ~9,5 giờ, toàn bộ quay bằng camera IR + đèn IR chủ động, AVI 640×480. 5 bối cảnh:
  `BareFace`, `Glasses`, `Night_BareFace`, `Night_Glasses` (15 fps), `Sunglasses` (30 fps).
- Diễn, ngồi ghế chơi game lái xe. Buồn ngủ: ngáp, chớp chậm, gục đầu. Không buồn ngủ: **nói, cười,
  nhìn hai bên** (tốt để đo báo sai).
- Nhãn theo frame (buồn ngủ, mắt, đầu, miệng) theo nguồn thứ cấp [N2], *chưa kiểm chứng*.
- Bản gốc: điền license agreement, email `cvlablai636@my.nthu.edu.tw`, chờ duyệt.
- **Không cần email:** Hugging Face `chbh7051/driver-drowsiness-dataset` [N3], gated `auto` (tài
  khoản HF + bấm đồng ý), chỉ có `data/train.zip` (~3 GB) + script loader, không card / license.
  *Chưa biết* bên trong là video hay frame, có file nhãn không; tên gợi ý chỉ phần train (18 người).
  Bản đăng lại dữ liệu cần license agreement: dự án không thương mại nên rủi ro thấp, vẫn trích dẫn;
  muốn chắc thì email song song.
- Preset `ddd` hiện tại là ảnh mặt cắt từ NTHU-DDD, không phải video.

### Brain4Cars (Cornell, ICCV 2015) [N6]

- 10 tài xế, ~1.180 dặm lái thật phố + cao tốc, 700 sự kiện: đi thẳng, rẽ trái / phải, chuyển làn
  trái / phải. Mỗi sự kiện: video mặt + video đường 5 s, 30 fps; mỗi frame có **tốc độ**, làn,
  ngã tư phía trước.
- Tải 16 GB qua Dropbox (link trong README repo; *chưa kiểm tra link còn sống*). License: miễn phí
  cho giáo dục / phi thương mại, trích dẫn paper.
- Dùng: đo `off_road` báo bao nhiêu lần khi quay đầu hợp lệ trước khi rẽ / chuyển làn (nguồn báo sai
  chính trên SUST), clip đi thẳng làm đối chứng.
- Hạn chế: **không có xi-nhan** (phải giả lập); **clip 5 s** ngắn hơn giai đoạn hiệu chỉnh mốc tư
  thế đầu → cần video cả chuyến (*chưa biết có trong 16 GB không*) hoặc nạp sẵn mốc từng tài xế
  (giống kết quả đăng ký ở mục 4).

<a id="viec-tai-dataset"></a>

### Việc tiếp theo (chưa làm)

1. Đăng ký HF, tải `train.zip` NTHU-DDD, xem có video AVI + nhãn không; không có thì email xin gốc.
2. Mở Dropbox Brain4Cars, xem có video dài hơn 5 s không.

- N1. http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/
- N2. https://www.emergentmind.com/topics/nthu-ddd-dataset
- N3. https://huggingface.co/datasets/chbh7051/driver-drowsiness-dataset
- N4. https://www.drozy.uliege.be/
- N5. https://orbi.uliege.be/handle/2268/191620
- N6. https://github.com/asheshjain399/ICCV2015_Brain4Cars

### Dataset Kaggle đã kiểm tra, không dùng

Kiểm tra qua Kaggle API, chưa tải. Ảnh mắt cắt sẵn chỉ đo được CNN dự phòng của khối 5 (EAR /
blendshape cần cả mặt để chạy MediaPipe), phần này đã có 3 dataset đo.

| Dataset | Nội dung | Lý do không dùng |
|---|---|---|
| `harshilpatel2711/drowsiness2` | 2.900 jpg: Closed / Open / yawn / no_yawn | **Trùng hoàn toàn** `serenaraju/yawn-eye-dataset-new` (đang dùng; 2900/2900 file khớp kích thước), gộp train + test, không license |
| `prasadvpatil/mrl-dataset` | 4.000 ảnh mắt MRL | **Đang dùng** (preset `mrl_eye`) |
| `kutaykutlu/drowsiness-detection` | Tập con MRL Eye (IR), `closed_eye` / `open_eye`, ~0,18 GB | MRL lần thứ ba; CNN khối 5 train trên MRL nên lạc quan. Tên file có thuộc tính kính / phản xạ / ánh sáng, nhưng `mrl_eye` cũng có |
| `hazemfahmy/openned-closed-eyes` | ~4.100 ảnh mắt **tổng hợp UnityEyes** + JSON, nhãn theo ngưỡng openness = 20 tùy ý | Ảnh render, chỉ vùng mắt, nhãn tùy ý; không đo được báo sai ngoài đời |
| `samymesbah/nthu-dataset-ddd-multi-class` | 2,34 GB, không mô tả, license Unknown | Chưa rõ video hay frame; không thay được NTHU-DDD gốc |

---

## 4. Đăng ký tài xế lúc khởi động (học khuôn mặt người lái)

Ý tưởng 30/09, chưa làm, chưa đo. Đây là một giai đoạn chạy **trước** khi bắt đầu giám sát, không
phải khối 2 (tiền xử lý ảnh, CLAHE).

### Hiện tại: mọi mốc đều tự học trong lúc lái
| Mốc | Cách học hiện tại | Vấn đề |
|---|---|---|
| Mắt mở (EAR) | Percentile 90 của 120 s gần nhất (`drowsiness.eye.baseline_*`) | Trong 10 s đầu dùng giá trị mặc định 0,28: L3 microsleep đầu chuyến dựa trên mốc sai. Buồn ngủ dần vài chục phút → mắt hẹp lại → mốc tụt theo → PERCLOS và "nhắm sâu" bị đánh giá thấp đúng lúc cần báo |
| Miệng (MAR) | Không có mốc: ngưỡng tuyệt đối `yawn.mar_open` 0,45 / `mar_close` 0,34 | Người miệng to / môi hé tự nhiên dễ bị tính là ngáp; miệng nhỏ thì khó đạt ngưỡng ngáp |
| Tư thế đầu (gục đầu) | Median của yaw / pitch trong 60 s, chỉ học lúc mắt mở | Cần vài giây dữ liệu, trước đó so với mốc chưa ổn |
| Tư thế "nhìn đường" | 5 s đầu có mặt khi xe chạy → median, sau đó trôi chậm (`distraction.baseline`) | Nếu 5 s đầu tài xế đang nhìn điện thoại / gương thì mốc sai cả chuyến (chỉ được trôi ±20°) |
| Ai là tài xế | Mỗi frame chọn mặt có khung bao lớn nhất (`landmarks.py`, web: `largestFace` trong `frontend/src/live/measure.ts`), `num_faces` = 2 | Xem "Rủi ro nhiều khuôn mặt" bên dưới |

**Rủi ro nhiều khuôn mặt (hành khách):**
- Tài xế quay ngang (nhìn gương, ngoái lại) → khung bao 2D hẹp lại → mặt hành khách nhìn thẳng có
  thể lớn hơn → theo dõi nhầm hành khách, bỏ lỡ đúng lúc cần báo `off_road`.
- Hành khách nghiêng lại gần camera → chọn nhầm.
- Không nhớ tài xế giữa các frame: hai mặt cỡ gần bằng nhau có thể đổi qua lại, trộn dữ liệu hai
  người vào `closed_duration`, `perclos_60s`, `blink_rate`, mốc EAR / pitch.
- Camera đặt giữa xe (cạnh gương chiếu hậu): giả định "lớn nhất = tài xế" yếu đi nhiều.
- Điện thoại thì đã ổn: chỉ tính trong vùng quanh mặt tài xế, nên điện thoại của hành khách không bị
  tính (với điều kiện chọn đúng mặt tài xế).

### Đề xuất: các bước đăng ký lúc khởi động
Chỉ chạy khi xe đứng yên (khối 10). HUD / web hướng dẫn từng bước, mỗi bước chỉ nhận khi mặt đủ tin
cậy (`face_conf`, `face_reliable`, không tối / chói) và số đo ổn định (độ lệch nhỏ). Không đạt thì làm
lại bước đó.

| Bước | Tài xế làm | Học được | Thay cho |
|---|---|---|---|
| A1 | Nhìn thẳng vào camera ~2 s | EAR mắt mở, MAR miệng khép, kích thước và vị trí mặt, chữ ký mặt (bước B) | Mốc EAR mặc định 0,28; ngưỡng MAR tuyệt đối |
| A2 | Nhìn ra đường phía trước như khi lái ~3 s | Tư thế "nhìn đường" (yaw / pitch) + mốc tư thế đầu cho gục đầu | Hiệu chỉnh 5 s tự động của khối 8; mốc pose 60 s của khối 7 |
| A3 | Nhắm mắt ~2 s | EAR mắt nhắm của chính người đó | Chưa có: hiện chỉ biết mốc mắt mở |
| C (tuỳ chọn) | Liếc gương trái, gương phải, bảng đồng hồ | Tư thế đầu hợp lệ của từng vùng nhìn | Chưa có |

<a id="dang-ky-buoc-a"></a>

**Bước A: mốc của riêng tài xế (không thêm model)**
- **Mắt to / mắt nhỏ:** độ mở mắt tính theo khoảng giữa mốc nhắm (A3) và mốc mở (A1), thay vì chỉ theo
  tỉ lệ của mốc mở. Các ngưỡng tương đối hiện tại (`close_ratio`, `perclos_close_ratio`,
  `microsleep_deep.ear_ratio`) tính trên thang mới này.
- **Mốc mắt mở gần như cố định:** lấy từ A1, sau đó chỉ được trôi rất chậm hoặc chỉ được trôi lên,
  không trôi theo cơn buồn ngủ. Có giới hạn trôi trong `thresholds.yaml`, giống `baseline.max_deg`
  của khối 8. (Video DMS thương mại ở mục 5 cũng dùng 5–10 phút đầu để làm quen mắt tài xế.)
- **Miệng to / miệng nhỏ:** ngưỡng ngáp = mốc MAR khép (A1) + một khoảng tương đối, thay cho 0,45 /
  0,34 cố định.
- **Tư thế nhìn đường:** lấy từ A2 làm tâm, giữ cơ chế trôi chậm ±20° hiện tại.
- **Giám sát có mốc ngay từ giây đầu**, nên không còn giai đoạn "L3 microsleep dựa trên mốc mặc định".

<a id="dang-ky-buoc-b"></a>

**Bước B: phân biệt tài xế với hành khách (không thêm model)**
- **Chữ ký mặt = một dãy tỉ lệ hình học** tính từ landmark 3D của MediaPipe, gần như không đổi khi quay
  đầu: khoảng cách hai mắt / chiều rộng mặt, chiều dài mũi / chiều cao mặt, độ rộng miệng / khoảng cách
  hai mắt, độ rộng mắt… Học ở A1 và A2.
- Mỗi frame chọn mặt theo điểm tổng hợp: giống chữ ký + gần vị trí tài xế ở frame trước + ở phía ghế
  lái (Việt Nam: bên trái; để tham số trong `thresholds.yaml` vì còn tùy camera có lật ảnh không). Kích
  thước mặt đo bằng khoảng cách hai mắt kết hợp chiều cao mặt, ít phụ thuộc góc quay đầu hơn diện tích
  khung bao.
- Chỉ đổi sang mặt khác khi mặt đó vượt rõ trong N frame liên tiếp (hysteresis). Nếu thật sự đổi
  người (xe dừng, tài xế mới ngồi vào) thì reset các bộ đếm theo thời gian và đề nghị đăng ký lại.
- *(suy luận, chưa kiểm chứng)* Tỉ lệ landmark không đủ để nhận dạng người lạ, nhưng trong xe chỉ cần
  phân biệt 2–3 người, lại kết hợp với vị trí và sự liên tục giữa các frame, nên có thể đủ. Cần đo.

<a id="dang-ky-buoc-c"></a>

**Bước C (tuỳ chọn): các vùng nhìn hợp lệ**
- Tư thế đầu khi nhìn gương / bảng đồng hồ của chính tài xế đó, dùng cho:
  - Đề xuất 5.2 (gục đầu): cúi đúng về tư thế bảng đồng hồ với mắt mở thì không phải gục đầu.
  - Mục 7 (hướng nhìn): mốc hướng nhìn theo từng vùng.
- **Không** dùng để bỏ qua `off_road`: nhìn gương quá 2 s khi chạy vẫn phải báo.

**Bước D (chỉ khi bước B không đủ): embedding mặt**
- Một model nhận dạng mặt pretrained nhỏ (vd. SFace trong OpenCV Zoo; *chưa kiểm tra license, kích
  thước, tốc độ*) chỉ chạy lúc đăng ký và khi nghi đổi người, không chạy mỗi frame, nên không ảnh
  hưởng 15 FPS. Là model mới nên cần quyết định riêng.

### Ràng buộc và chống báo sai
- **Không lưu ảnh:** chỉ giữ số (EAR, MAR, góc, dãy tỉ lệ / embedding) trong RAM. Metadata gửi backend
  chỉ có trạng thái đăng ký (`enrolled`, chất lượng mốc), không có chữ ký mặt. Giữ qua chuyến hay
  không: chờ quyết định ở mục 1.
- **Đăng ký sai là rủi ro lớn nhất:** mốc sai thì sai cả chuyến. Mỗi bước phải có kiểm tra (độ lệch
  thấp, giá trị nằm trong khoảng hợp lý như `baseline_min` / `baseline_max`, nhìn đường thì góc không
  quá `calibrate_max_deg`). Không đạt thì làm lại. Bỏ qua hoặc hết thời gian thì quay về cách tự học
  hiện tại.
- **Luôn giữ đường dự phòng tự học:** các dataset eval không có bước đăng ký, nên công cụ eval dùng
  đường dự phòng, hoặc giả lập đăng ký từ N giây đầu clip (báo cáo riêng hai cách).
- **Đổi tư thế ngồi / chỉnh ghế / đổi camera giữa chuyến:** mốc nhìn đường vẫn trôi chậm như hiện tại;
  lệch quá xa thì đề nghị đăng ký lại lúc xe dừng.
- **Test bằng chuỗi số giả:** bộ đăng ký nhận chuỗi `FrameFeatures` giả (EAR / MAR / góc / tỉ lệ
  landmark theo thời gian). Bước B test bằng hai chuỗi mặt giả đổi chỗ, cỡ và góc.

### Còn lại sau khi làm
- MediaPipe chỉ trả `num_faces` = 2 mặt: với ≥ 3 người có thể không thấy tài xế nếu hai mặt khác nổi
  hơn. Tăng lên 3 thì phải đo lại FPS.
- Chưa có dữ liệu nhiều người trong xe để đo bước B; dataset eval đều chỉ có một người.
- Không giải quyết mắt liếc khi đầu thẳng (mục 7), ánh sáng (mục 6), `off_road` hợp lệ khi rẽ (mục 9).

### Nên tách thành mốc
1. **Bước A** + màn hình hướng dẫn trên HUD / web + đường dự phòng (việc 2).
2. **Bước B** bám tài xế bằng chữ ký + vị trí + hysteresis (việc 4). Làm được riêng, không cần A.
3. **Bước C / D** tuỳ chọn, sau khi có hướng nhìn (mục 7) hoặc khi B đo ra không đủ (việc 14).

Màn hình hướng dẫn đăng ký nên theo cùng cách nói của [giao diện cho tài xế](#viec-giao-dien) (việc 20).

---

## 5. Ý tưởng từ video phân tích DMS thương mại (29/09)

Nguồn: ghi chú `Video.pdf` (bỏ phần camera IR 940 nm, đã có ở mục 6). Đối chiếu với code ngày 29/09,
chưa đo thử.

### Đã có, trùng với video
- EAR từ 6 điểm mỗi mắt (khối 6).
- PERCLOS cửa sổ 60 s, ngưỡng 0,15 (video: ~16%).
- Góc cúi đầu tách "cúi nhìn" khỏi "nhắm mắt": `max_pitch_down_deg`, gục đầu yêu cầu mắt nhắm.
- Nhánh song song đo thời gian nhắm: `closed_duration` ≥ 1,5 s → L3 ngay, không qua `drowsy_score`.
- Con số theo phút: trip memory 1 điểm/phút + cảnh báo xu hướng.

### Hướng đề xuất (xếp theo ưu tiên)
1. <a id="viec-chop-mat"></a>**Tốc độ mở mắt lại, không chỉ số lần chớp.** Video: buồn ngủ thì khép lâu hơn và mở lại chậm.
   Hiện chỉ có `blink_rate`; `blink_max_s` chỉ phân biệt chớp / nhắm. Thêm: thời lượng chớp trung
   bình mỗi phút, thời gian mở lại (từ khép sâu đến mở hẳn), tỉ lệ chớp dài. Là dấu hiệu sớm, trước
   khi PERCLOS kịp tăng.
2. <a id="viec-guc-dau"></a>**Gục đầu = cúi chậm rồi giật lên nhanh.** Hiện: dip > 15°, quay lại trong 0,2–2 s, mắt nhắm.
   Thêm điều kiện tốc độ ngẩng lên nhanh hơn rõ so với tốc độ cúi (liếc bảng đồng hồ thì hai chiều
   gần đối xứng) → bớt báo sai. Xem lại `nod.max_s`: cú gục thật có thể cúi chậm hơn 2 s.
3. <a id="viec-perclos"></a>**Kiểm tra định nghĩa PERCLOS.** Video dùng P80 (mắt khép ≥ 80%, ≈ EAR < 0,2 × mốc). Code dùng
   `perclos_close_ratio: 0.65` (khép ~35% đã tính) → nhạy hơn, dễ tính cả nheo mắt. Chạy P80 song
   song trên FL3D / YawDD / SUST để so, chưa thay ngay.
4. <a id="viec-muc-nham-mat"></a>**Mức cảnh báo tăng theo thời gian nhắm.** Video: 1–2 s gợi ý trạm dừng; ≥ 3 s còi + rung ghế;
   ≥ 6 s coi là không còn phản ứng → giảm tốc, tấp làn. Hiện chỉ một L3 ở 1,5 s. Thêm mốc
   `closed_duration` ≥ 3 s và ≥ 6 s trong `thresholds.yaml`; mốc 6 s sinh sự kiện `unresponsive`
   lên backend và yêu cầu giảm tốc qua CAN giả lập. Cảnh báo 1–2 s kèm gợi ý dừng nghỉ.
5. <a id="viec-mat-mat-10s"></a>**10 s không thấy mặt → báo hệ thống tạm ngưng giám sát.** Hiện mất mặt 3 s khi chạy → L2
   `no_face`. Tách hai trường hợp: tài xế gục (giữ L2) và camera bị che (sự kiện
   `monitoring_unavailable` lên HUD / backend, như `camera_lost`). Liên quan quyết định FR-6 ở mục 1.
6. <a id="viec-nhuon-may"></a>**Nhướn mày để giữ mắt mở.** Blendshape `browInnerUp` / `browOuterUp` đã có sẵn từ MediaPipe,
   không tốn FPS. Mày nhướn trong lúc EAR thấp / đang giảm = đang chống cơn buồn ngủ → thành phần
   phụ của `drowsy_score`.

Ưu tiên đề xuất: 1 → 2. Cả hai không thêm model, chỉ thêm ngưỡng vào `thresholds.yaml`, test được
bằng chuỗi số giả. (Đề xuất "mốc mắt mở học lúc đầu chuyến rồi giữ gần cố định" đã chuyển sang mục 4,
bước A.)

### Không áp dụng
- **Hai model (sóng não + mặt → chỉ mặt) để chấm điểm buồn ngủ:** phải train, vi phạm "chỉ dùng
  pretrained". Risk engine dạng luật hiện tại vẫn là lựa chọn đúng.

---

## 6. Ánh sáng khó: lái đêm, đèn đường, đèn pha xe ngược chiều

### Đã có (cả thiết bị lẫn web, vì web chạy lại khối 5–12 bằng Python qua Pyodide)
- Mặt quá tối (độ sáng vùng mặt, trước CLAHE, < `low_light_brightness` = 60): khối 5 thay EAR
  bằng điểm nhắm mắt (thiết bị: CNN mắt; web: blendshape `eyeBlink`).
- Giữ nguồn đó thêm `hold_s` = 2 s sau khi hết tối: đi qua đèn đường / chạng vạng không làm
  EAR ↔ điểm nhắm mắt đổi qua lại từng frame, không sinh nhắm mắt giả.
- EAR hai mắt lệch nhiều (lóa kính, che một mắt): dùng điểm nhắm mắt (không giữ).
- Mất mặt ngắn hơn `max_gap_s`: đợt nhắm mắt đang đếm không bị xoá; frame `face_conf` < 0,9 bị bỏ.
- Nhận biết ảnh IR / xám qua độ chênh kênh màu (có cả trên web).
- Đánh giá đêm: 44 video NITYMED (FL3D), nhưng chạy bản Python có CLAHE, không phải bản web.

### Chưa giải quyết
- **Không có kiểm tra "quá sáng" hay độ sáng tăng đột ngột.** Đèn pha chiếu thẳng làm vùng mắt
  cháy trắng, landmark có thể lệch, EAR vẫn được tin → có thể báo nhắm mắt sai.
- **Chói làm mất mặt ≥ 3 s khi xe chạy → L2 `no_face`** (`risk_engine.py`): nguồn báo sai tiềm ẩn.
- **Web không có CLAHE.** Webcam / camera điện thoại tự chỉnh phơi sáng chậm khi ánh sáng đổi đột
  ngột; trình duyệt gần như không cho điều khiển.
- **Giới hạn vật lý:** webcam RGB trong cabin tối gần như không thấy mặt; phần mềm không bù được.
- **Chưa có dữ liệu** đèn pha / đèn đường quét qua; chưa đánh giá riêng đường chạy web ban đêm.

<a id="viec-choi"></a>

### Hướng đề xuất
- **Cờ chói / cháy sáng:** tỉ lệ pixel bão hoà trong vùng mặt + bước nhảy độ sáng giữa các frame.
  Vượt ngưỡng → trạng thái mắt = "không biết" (`None`) trong một khoảng ngắn thay vì đoán, và tạm
  nới ngưỡng `no_face`. Nhẹ, ngưỡng để trong `thresholds.yaml`, test được bằng chuỗi số giả.
- **Khối 5 thêm trigger `overexposed`** bên cạnh `low_light`, giữ `hold_s` như hiện tại.
- **Cân bằng tương phản trên web bằng WebGL shader** (nhẹ hơn OpenCV.js ~8 MB); đo lại FPS ≥ 15.
- **Phần cứng khi triển khai thật:** camera IR + đèn LED IR 850/940 nm (chuẩn của DMS thương mại,
  ít bị đèn pha ảnh hưởng). Code đã nhận biết IR sẵn.
- **Đánh giá:** quay clip lái đêm thật có đèn pha, chạy qua bản web, đếm báo sai.

---

<a id="viec-huong-nhin"></a>

## 7. Mắt nhìn lệch khi đầu vẫn thẳng (hướng nhìn)

### Hiện tại
- Khối 8 (`distraction.py`) chỉ dùng **góc đầu** so với mốc "nhìn đường" của tài xế: lệch yaw > 30°,
  cúi > 20°, ngẩng > 25° liên tục ≥ 2 s (≥ 1,5 s khi tốc độ cao) → L2 `off_road`.
- Điện thoại xử lý riêng qua YOLO: điện thoại trong vùng tài xế ≥ 60% thời gian trong 2 s → L2 `phone`.
- Không dùng hướng nhìn của mắt ở đâu cả.

### Chưa phát hiện được
- Đầu thẳng, **mắt liếc xuống** điện thoại trên đùi / giá đỡ thấp: góc đầu không đổi, và điện thoại
  trên đùi có thể nằm dưới vùng tài xế (chỉ kéo xuống 1,5 × chiều cao mặt) nên YOLO cũng không tính.
- Đầu thẳng, **mắt liếc sang bên** (màn hình giải trí, hành khách) quá lâu.
- *(suy luận, chưa kiểm chứng)* Mắt nhìn xuống làm mí trên hạ theo → EAR giảm → có thể bị hiểu là
  **nhắm mắt**, thành báo sai ở nhánh buồn ngủ thay vì mất tập trung.
- Nhìn thẳng nhưng "mất hồn": ngoài khả năng của camera, không nằm trong hướng này.

### Hướng đề xuất (không thêm model)
- **Blendshape hướng nhìn** MediaPipe đã xuất sẵn nhưng chưa lấy: `eyeLookDown/Up/In/Out` mỗi mắt.
  Lấy thêm không tốn thời gian, chạy được cả trên web.
- **10 điểm mống mắt** (landmark 468–477): vị trí mống mắt so với hai khoé mắt cho độ lệch của mắt.
- Tính **hướng nhìn = góc đầu + độ lệch mắt**, dùng làm tín hiệu bổ sung cho `off_road` với ngưỡng
  riêng trong `thresholds.yaml`; giữ góc đầu làm tín hiệu chính.
- Mốc hướng nhìn theo từng tài xế / từng vùng (đường, gương, bảng đồng hồ) lấy từ bước đăng ký ở
  mục 4 (bước A2, C) thay vì một ngưỡng chung.
- Dùng cùng tín hiệu để nhánh buồn ngủ phân biệt **"mắt nhìn xuống"** với **"mắt nhắm"**.
- Rủi ro: ước lượng mắt kém khi IR / đeo kính → cần tắt hoặc giảm tin cậy trong các trường hợp đó
  (nối với trigger của khối 5 ở mục 6, 8).
- Test bằng chuỗi số giả (góc đầu + độ lệch mắt theo thời gian); cần thêm clip có nhãn "liếc điện
  thoại, đầu thẳng" để đo báo sai (gộp với clip tự quay ở mục 10).

---

## 8. Model trạng thái mắt thay / bổ sung cho Eye-state CNN (khối 5)

Research 29/09/2026 từ nguồn gốc (model card, repo, paper), chưa chạy thử. **[n]** = số do nguồn
công bố; *(suy luận)* = nhận định chưa kiểm chứng. Số đo trên dataset khác nhau không so trực tiếp
được với số của mình trên NITYMED.

> **Ưu tiên thử (chốt 29/09):**
> 1. **BlinkLinMulT `blinkcnn`** (v2, MIT, ONNX 19,1 MB, input 64×64): dữ liệu train đa dạng nhất,
>    có cả IR (MRL Eye) và video RGB thật; crop gần như crop hiện tại. Đổi lại nặng hơn (~4 ms / mắt).
> 2. **OCEC** (PINTO0309, MIT, ONNX 115 KB – 6,4 MB, input 24×40): nhẹ ngang CNN hiện tại; cần adapter
>    crop hộp mắt; dữ liệu train chủ yếu ảnh AI sinh, chưa rõ với IR / kính.
>
> Cả hai phải qua thử offline (xem "Đề xuất thử offline" bên dưới) trước khi thay CNN Intel; bước
> đầu là sửa `tools/seq_eval.py` để trace thêm cột điểm của model mới.

### Hiện trạng
- Thiết bị: Intel OMZ `open-closed-eye-0001` (Apache-2.0, 46 KB, BGR 32×32, train MRL Eye), 0,12 ms
  / lần gọi, chỉ gọi khi EAR không tin được. NITYMED: CNN AUC 0,881; blendshape `eyeBlink` 0,986.
- Web: blendshape `eyeBlink`. Blendshape V2 **chỉ nhận 146 landmark làm input, không nhìn pixel**
  [7], nên khi lóa kính làm lệch landmark mí mắt thì `eyeBlink` sai theo, không độc lập với EAR.
  Khớp với việc trên thiết bị blendshape kém CNN khi đeo kính.
- Không có bản mới hơn: Open Model Zoo đang ở chế độ bảo trì [3]; MediaPipe chưa công bố model nào
  sau Blendshape V2 (11/2022) [6][7].

### Ứng viên đáng thử (license MIT, có ONNX tải được)

| | BlinkLinMulT `blinkcnn` (v2) [12][13] | OCEC (PINTO0309, 11/2025) [8][9] |
|---|---|---|
| Đầu ra | Điểm đóng mắt 0–1 mỗi frame | `prob_open` |
| Input | RGB 64×64, crop vuông 2,0 × khoảng cách khoé mắt (gần crop 1,8× hiện tại) | RGB 24×40, crop sát hộp mắt, cần adapter dựng hộp từ landmark |
| Kích thước | 5,0 M tham số, 19,1 MB | 115 KB – 6,4 MB (6 cỡ P→L) |
| Tốc độ [nguồn] | 4,15 ms / frame ONNX CPU (không rõ cấu hình), ~8 ms cho 2 mắt | 0,16–0,80 ms (không rõ CPU / runtime) |
| Dữ liệu train | CEW, **MRL Eye (IR)**, RN15, RN30, HUST-LEBW, chia theo người; thẻ HF tự cảnh báo có thể kém với IR, mặt nghiêng | Chủ yếu **ảnh mắt do AI sinh** [11] + video riêng của tác giả; không nhắc IR hay kính |
| Số công bố | AP 0,789 chớp mắt trên RN30 test | F1 0,992–0,995 trên split ngẫu nhiên 80/20 của chính dataset (có thể lạc quan) |

- `blinkcnn` hợp nhất với điểm yếu IR / ban đêm, crop gần như không phải đổi, nhưng nặng hơn CNN
  hiện tại ~35–80 lần; khi IR bật cả chuyến thì tốn ~8 ms / frame trong ngân sách 66 ms.
- OCEC nhẹ ngang CNN hiện tại nhưng dữ liệu train không nói gì về IR / kính.
- License *(suy luận)*: trọng số MIT, nhưng các dataset train có license riêng. Vùng xám này giống
  model hiện tại (train trên MRL).
- PINTO0309 còn có **SGC**: phân loại đeo / không đeo kính râm, 48×48, MIT [8]. Có thể dùng làm tín
  hiệu "không tin trạng thái mắt" khi đeo kính râm. Chưa kiểm tra kỹ.

### Đã loại
- **License phi thương mại / chỉ nghiên cứu:** OpenFace 2.0 / 3.0 (CMU) [19][21], LibreFace (USC
  research license) [22], InsightFace [23], RT-BENE (CC BY-NC-SA, train không kính) [18],
  MichalMlodawski mobilev2 (CC BY-NC-ND) [16].
- **Quá nặng / dữ liệu không rõ:** dima806 ViT 85,8 M tham số [17]; BlinkVideoMAE (không có file
  license) [29].
- **Không có đầu ra độ mở mắt:** L2CS-Net [24], OMZ `gaze-estimation-adas-0002` [4].
- **Kém hơn:** BlinkLinMulT 1.x (AP 0,36–0,43 trên RN30, model chuỗi 77 ms / lần) [12].
- **Không có trọng số công khai:** mEBAL / mEBAL2 [28].
- **Landmark mí mắt** (OMZ 98 điểm [5], 3DDFA_V2 [25], SPIGA [26], PIPNet [27]): vẫn phải tính
  kiểu EAR nên không giải quyết lóa kính; MediaPipe đã có 16 điểm / mắt + iris. Ưu tiên thấp.
- **Fine-tune bất kỳ model nào:** là train, ngoài phạm vi theo CLAUDE.md.

<a id="viec-model-mat"></a>

### Đề xuất thử offline
- Thứ tự: `blinkcnn` → OCEC-S / OCEC-L → (tuỳ chọn) ghép điểm CNN hiện tại với ứng viên thắng
  (thay đổi thiết kế, cần quyết).
- **Cần sửa công cụ eval trước:** `tools/seq_eval.py --replay block5` chỉ phát lại cột đã trace
  (`p_cnn`, `blink`), không chạy lại model. Phải trace thêm cột (vd. `p_blinkcnn`, `p_ocec`), là
  một mốc riêng.
- Đo: NITYMED / FL3D (AUC, FPR, trên mọi frame và chỉ frame khối 5 được gọi); YawDD clip đeo kính
  (false microsleep); MRL Eye chỉ tham khảo (cả `blinkcnn` và CNN hiện tại đều train trên MRL);
  benchmark ms / 2 crop trên máy đích khi trigger bật liên tục.
- Tiêu chí thay: AUC NITYMED > 0,881; FPR ≤ 1,6%; false microsleep YawDD kính ≤ 6; vẫn ≥ 15 FPS.

### Nguồn
3. Open Model Zoo (maintenance mode): https://github.com/openvinotoolkit/open_model_zoo
4. OMZ Intel models index: https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/intel/index.md
5. OMZ facial-landmarks-98-detection-0001: https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/intel/facial-landmarks-98-detection-0001/README.md
6. MediaPipe Face Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
7. MediaPipe Blendshape V2 model card: https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf
8. PINTO0309/OCEC: https://github.com/PINTO0309/OCEC
9. OCEC release `onnx`: https://github.com/PINTO0309/OCEC/releases/tag/onnx
11. Open and Closed Eyes Dataset (Młodawski, ODC-By): https://huggingface.co/datasets/MichalMlodawski/closed-open-eyes
12. fodorad/BlinkLinMulT: https://github.com/fodorad/BlinkLinMulT
13. HF fodorad/blink_detection: https://huggingface.co/fodorad/blink_detection
16. HF MichalMlodawski/open-closed-eye-classification-mobilev2: https://huggingface.co/MichalMlodawski/open-closed-eye-classification-mobilev2
17. HF dima806/closed_eyes_image_detection: https://huggingface.co/dima806/closed_eyes_image_detection
18. RT-GENE / RT-BENE: https://github.com/Tobias-Fischer/rt_gene
19. OpenFace 3.0: https://github.com/CMU-MultiComp-Lab/OpenFace-3.0
21. OpenFace 2.0 license: https://github.com/TadasBaltrusaitis/OpenFace/blob/master/OpenFace-license.txt
22. LibreFace: https://github.com/ihp-lab/LibreFace
23. InsightFace python-package: https://github.com/deepinsight/insightface/tree/master/python-package
24. L2CS-Net: https://github.com/Ahmednull/L2CS-Net
25. 3DDFA_V2: https://github.com/cleardusk/3DDFA_V2
26. SPIGA: https://github.com/andresprados/SPIGA
27. PIPNet: https://github.com/jhb86253817/PIPNet
28. mEBAL2: https://github.com/BiDAlab/mEBAL2
29. BlinkVideoMAE: https://github.com/belkacem-hedadi/BlinkVideoMAE

### YOLO chuyên mắt nhắm / ngáp (research 29/09/2026)

**Kết luận: không dùng thay nhánh chính.** Chỉ có dự án cá nhân nhỏ, số liệu đều đo trên tập val chia
ngẫu nhiên theo ảnh (dễ rò rỉ cùng người giữa train / val nên số bị thổi phồng), không nguồn nào có số
theo đêm / IR / kính hay báo sai mỗi giờ trên video lái thật. Không ứng viên nào có dấu hiệu hơn
blendshape `eyeBlink` (0,986); cùng lắm chỉ so được với CNN Intel dự phòng (0,881).

| Model | Lớp | Kiến trúc / input | Dữ liệu train | Số công bố [nguồn] | License | Kết luận |
|---|---|---|---|---|---|---|
| tyrerodr/real-time-drowsy-driving-detection [Y1] | mắt open/closed; model ngáp riêng yawn/no_yawn | 2 × YOLOv8n ~6,2 MB, .pt; chạy trên **crop mắt / miệng từ MediaPipe** | Kaggle Eyes + MRL Eye (~53 k ảnh), box gán tự động bằng GroundingDINO; ngáp: Kaggle Yawning | val: mắt mAP50 0,784; ngáp 0,789 | Repo không có LICENSE; AGPL theo Ultralytics | Đáng thử offline nhất (có MRL / IR), nhưng số thấp, license chưa rõ |
| Jaemani/eye-closure-detector-yolo-tflite [Y2][Y3] | openeyes / closedeyes | YOLOv5n/v5s/v8n, input 320, TFLite (int8 2,0–2,8 MB) | Roboflow "rmbg_all" > 9 200 ảnh; **đã loại ảnh lóa và mắt nửa nhắm** | mAP50 0,963 (split không nêu) | HF ghi MIT; AGPL theo Ultralytics | Thử được, nhưng dễ yếu đúng chỗ đang yếu (kính lóa, lim dim) |
| MichalMlodawski/open-closed-eye-detection [Y4] | open / closed | YOLOv8, ONNX 12 MB | ~126 k ảnh **do AI sinh** | val mAP50 0,968 | **CC BY-NC-SA 4.0** | Loại (phi thương mại, không có IR thật) |
| yeeeengyu/YOLO-drowsiness-detector [Y5] | open, closed, face | YOLO 3,2 MB | Không nêu | Không có | MIT / AGPL | Loại (không có thông tin) |
| mosesb/drowsiness-detection-yolo-cls [Y6] | Drowsy / Non Drowsy (cả khung) | yolo11x-cls, 224 | Frame cắt từ video Kaggle DDD | Acc 99,8% (gần như chắc rò rỉ) | MIT / AGPL | Loại (nặng, không cho thời lượng nhắm mắt) |
| hwkim-dev/Driver-drowsiness-detection [Y7] | mắt / mặt / miệng | YOLOv8m 52 MB | AIHub Hàn Quốc | Chỉ có biểu đồ | MIT / AGPL | Loại (quá nặng) |
| Roboflow Universe (nhiều project drowsiness) [Y8] | eye_open/closed, yawn… | Roboflow Train | Dataset CC BY 4.0 | — | — | Loại: **không cho tải trọng số**, chỉ gọi API (trái on-device) hoặc tự train (trái "không train") |
| AndreaPorri/Yolo12n_Eyes_Detection [Y9] | eye (không phân nhắm / mở) | YOLOv12n | — | — | CC BY-NC-SA | Loại (không có file trọng số) |

**Vì sao không hợp pipeline:**
- Mắt chỉ ~10–25 px trong khung 640: detector chạy cả khung sẽ kém; muốn dùng thì vẫn phải lấy crop
  từ MediaPipe, tức chỉ thay được vai CNN dự phòng.
- YOLO trong dự án chạy ~5 lần / s: với microsleep 1,5 s chỉ ~7 mẫu, sai số biên ±200 ms.
- Đầu ra là nhãn nhắm / mở, không có độ mở liên tục như EAR / blendshape → khó làm PERCLOS, lim dim,
  không có mốc riêng từng tài xế.
- Ngáp: MAR đã chỉnh trên YawDD; model ngáp YOLO (mAP50 0,79) không có bằng chứng giảm báo sai khi
  nói chuyện / hát.

**Nếu thử offline (chỉ đề xuất):** tyrerodr và Jaemani, chạy trên đúng crop mắt đang đưa cho CNN
Intel, lấy confidence lớp closed làm điểm liên tục. Chỉ cân nhắc thay CNN Intel nếu AUC đêm ≥ ~0,93 và
báo sai / giờ không tăng; latency p95 < 5 ms / crop. Phải giải quyết license trước. Nếu phải chọn,
`blinkcnn` / OCEC ở trên (MIT) vẫn là ứng viên tốt hơn.

**Chưa kiểm chứng:** trang Roboflow bị Cloudflare chặn (số ảnh / license lấy từ đoạn trích tìm kiếm,
chưa đọc được mAP); số người và tỉ lệ IR / kính trong dữ liệu của tyrerodr, Jaemani; license của MRL
và Kaggle Eyes; điều khoản AIHub.

**Nguồn:**
- Y1. https://github.com/tyrerodr/real-time-drowsy-driving-detection
- Y2. https://huggingface.co/Jaemani/eye-closure-detector-yolo-tflite
- Y3. https://github.com/Jaemani/wakeup_app
- Y4. https://huggingface.co/MichalMlodawski/open-closed-eye-detection
- Y5. https://huggingface.co/yeeeengyu/YOLO-drowsiness-detector
- Y6. https://huggingface.co/mosesb/drowsiness-detection-yolo-cls
- Y7. https://github.com/hwkim-dev/Driver-drowsiness-detection
- Y8. https://universe.roboflow.com/faseeh-f2cpp/drowsiness-driver-yqss9 ; https://discuss.roboflow.com/t/download-model-weights/3934 (nhân viên Roboflow: Universe không cho tải trọng số)
- Y9. https://huggingface.co/AndreaPorri/Yolo12n_Eyes_Detection
- Y10. Ultralytics license: https://www.ultralytics.com/license ; https://github.com/ultralytics/ultralytics/blob/main/LICENSE

---

<a id="viec-phan-cung"></a>

## 9. Vấn đề kỹ thuật còn mở (worklog 26/09)

- **off_road trên xe thật:** 25 cảnh báo L2 trong 3 giờ SUST là quay đầu thật. Cần xi-nhan / tốc
  độ CAN thật.
- **Clip ngắn:** SUST chỉ 10 s nên PERCLOS và mốc EAR không kịp khởi động, recall 1,6%.
- **Điện thoại:** YOLO bắt 2,1% ảnh State Farm; góc bên không giống camera của mình nên chưa đủ để
  kết luận.

---

<a id="viec-prd"></a>

## 10. PRD yêu cầu nhưng roadmap chưa có mốc

- **LLM tóm tắt + gợi ý (FR-12, FR-13):** chưa có dòng code nào trong DriverGuard.
- **Buổi kiểm tra hiểu cảnh báo 10 người (PRD §7 bậc 3):** chưa diễn ra, số đang là "not evaluated".
- **Clip tự quay có nhãn** theo điều kiện sáng / tối / kính / ngược sáng: chưa có; mọi số hiện tại
  từ dataset công khai. (Gộp được với phần đánh giá ở mục 6.)
- **Time-to-alert p95 ≤ 3 s:** chưa có công cụ đo riêng.
- **Docker cho backend + edge (FR-14):** repo đã có `Dockerfile`, `Dockerfile.railway` và
  `docker-compose.yml`, nhưng compose mới có service `backend`; còn thiếu edge.
- **Nhật ký theo điều kiện**, tag `simulated` / `forced`, phiên bản cấu hình trên sự kiện
  (FR-8, FR-9, FR-17).
- **Nộp bài:** `presentation/` mới có README. (`eval/results/report.md` đã có báo cáo tổng hợp từ
  28/09, cần kiểm tra lại mức đầy đủ so với yêu cầu nộp.)

---

## 11. Đóng gói app và giao diện cho tài xế (không gấp)

Không làm thay đổi độ chính xác hay số báo sai, chỉ làm app dễ dùng hơn. Để cuối.

<a id="viec-apk"></a>

### Đóng gói thành app Android (APK)

**Hiện tại:** chỉ có bản web (React + MediaPipe tasks-vision + onnxruntime-web + khối 5–12 bằng
Python qua Pyodide), mở bằng trình duyệt. Lần đầu mỗi máy phải tải ~25 MB Python cùng các model.

**Hướng đề xuất:** gói chính bản web vào một app WebView (vd. Capacitor), không viết lại.
- Đưa sẵn Pyodide, `edge_agent.zip`, `face_landmarker.task`, `yolov8n.onnx` vào APK: mở app là chạy
  ngay, không cần mạng để giám sát. Mạng chỉ dùng để gửi metadata JSON lên backend (đúng CLAUDE.md).
- Giữ một bộ code cho cả web và app; `npm run build` rồi đồng bộ sang project Android.
- Việc riêng của app: xin quyền camera, giữ màn hình sáng, khoá màn hình ngang (điện thoại gắn trên
  taplo), địa chỉ backend trong phần cài đặt.
- Không chọn: viết lại native (Kotlin + MediaPipe Android + ONNX Runtime Mobile) vì phải chuyển toàn
  bộ logic khối 5–12 từ Python sang Kotlin và giữ hai bản đồng bộ. Cũng không chọn TWA (bọc trang web
  đang host), vì vẫn cần mạng để mở app.

**Rủi ro / cần đo:**
- *(chưa kiểm chứng)* WASM + WebGL trong WebView Android có đạt ≥ 15 FPS trên điện thoại tầm trung
  không. Phải đo trên máy thật trước khi làm tiếp.
- Nóng máy và hao pin khi chạy camera + model liên tục cả chuyến.
- Khi app chạy nền hoặc tắt màn hình, Android có thể dừng camera → phải báo "tạm ngưng giám sát",
  không được im lặng (nối với [việc 11](#viec-mat-mat-10s)).
- APK nặng thêm ~40–50 MB vì chứa sẵn Python và model (*ước lượng*).
- Phát tán APK có YOLO là phân phối phần mềm AGPL: phải kèm mã nguồn (xem License YOLO ở
  [mục 1](#quyet-dinh)).

<a id="viec-giao-dien"></a>

### Giao diện cho tài xế: bỏ thuật ngữ, gộp bước tải

**Hiện tại, những chỗ tài xế thấy thuật ngữ kỹ thuật:**

| Chỗ | Đang hiện | Vấn đề |
|---|---|---|
| Màn hình chuẩn bị (`STEPS` trong `frontend/src/live/agent.ts`) | 4 bước: "Mở camera", "Tải bộ xử lý Python (lần đầu khoảng 25 MB)", "Tải MediaPipe nhận diện khuôn mặt", "Tải YOLO phát hiện điện thoại" | Tài xế không cần biết Python / MediaPipe / YOLO; 3 bước tải là một việc |
| Ô camera nhỏ (`SelfView` trong `LiveScreen.tsx`) | `EAR 0.28 · 30 FPS`, `Yaw 5° · Pitch -3°`, `ĐT không (40 ms)` | Số đo cho kỹ sư, tài xế không hiểu và dễ bị phân tâm khi lái |
| Mức cảnh báo (`LEVELS` trong `frontend/src/lib/labels.ts`) | Nhãn `L0`–`L3`; mô tả L1 / L2 là "Biểu tượng + chuông nhẹ", "Âm thanh + rung ghế" | Mô tả cách hệ thống báo, không nói tài xế nên làm gì |
| Dashboard, trang ngưỡng | `drowsy_score`, PERCLOS, microsleep… | Dành cho kỹ sư / quản lý: giữ nguyên, chỉ ẩn khỏi vai trò tài xế |

**Hướng đề xuất:**
- **Gộp các bước tải thành một:** "Mở camera" (cần tài xế cho phép) + "Đang chuẩn bị (lần đầu
  khoảng … MB)" với một thanh tiến độ chung. Trong APK ([việc 19](#viec-apk)) bước này gần như biến mất.
- **Ô camera nhỏ chỉ còn trạng thái dễ hiểu:** "Đang theo dõi" / "Không thấy mặt, hãy chỉnh camera".
  Chuyển EAR, FPS, góc đầu, ms sang một chế độ kỹ sư (bật trong cài đặt), mặc định tắt.
- **Mức cảnh báo nói việc cần làm:** bỏ `L0`–`L3` khỏi màn hình tài xế, dùng màu + câu ngắn, vd. "Bạn
  có vẻ mệt, nghỉ ở trạm dừng gần nhất", "Nhìn về phía trước", "Dừng xe nghỉ ngay". Mã mức vẫn giữ
  trong metadata và dashboard.
- **Nhìn một lần là hiểu:** chữ lớn, ít chữ, nút to, không cần chạm khi đang chạy. Cân nhắc đọc
  thành tiếng cho L2 / L3.
- **Màn hình đăng ký** ([việc 2](#dang-ky-buoc-a)) dùng cùng cách nói: "Nhìn thẳng vào camera",
  "Nhìn ra đường như khi lái", "Nhắm mắt 2 giây".
- **Kiểm tra với người thật:** gộp với buổi test hiểu cảnh báo 10 người của PRD ([mục 10](#viec-prd)).
- Chỉ đổi phần chữ / bố cục ở frontend, không đổi logic phát hiện; vẫn ≥ 15 FPS.

---

<a id="viec-do-phan-cung"></a>

## 12. Đo tài nguyên phần cứng: CPU, RAM, nhiệt độ

**Hiện tại:**
- `tools/benchmark.py` (M7) chỉ đo FPS, độ trễ p50 / p95 từng khối, kích thước model. Chạy ngắn (vài
  trăm frame), trên máy Mac ARM của team (146 FPS với video YawDD).
- **Chưa đo** CPU, RAM, nhiệt độ; chưa chạy dài; chưa đo trên thiết bị gắn trên xe. PRD FR-18 / NFR-2
  yêu cầu có số CPU / RAM, gắn nhãn `simulated`.
- Số 146 FPS trên Mac không nói được gì về hub trên xe: máy yếu hơn, trong cabin nóng, chạy liên tục
  cả chuyến.

**Cần đo, trên hai nơi:**
- **Hub gắn trên xe** (thiết bị đích; *loại máy chưa chốt*) và điện thoại nếu làm APK
  ([việc 19](#viec-apk)).
- **Máy chạy project** (máy dev / laptop demo): làm mốc so sánh, và để biết bản `simulated` hiện tại
  đang chiếm bao nhiêu tài nguyên.

| Chỉ số | Vì sao | Cách đo (đề xuất) |
|---|---|---|
| CPU % (cả tiến trình và từng luồng: vòng chính, YOLO) | Còn dư bao nhiêu cho app khác trên hub (bản đồ, camera lùi…) | `psutil` lấy mẫu mỗi giây |
| RAM (RSS, đỉnh, có tăng dần theo thời gian không) | Bắt rò rỉ bộ nhớ khi chạy nhiều giờ; frame chỉ nằm trong RAM nên phải chắc không bị giữ lại | `psutil` |
| Nhiệt độ CPU / SoC | Máy nóng → tự hạ xung → FPS tụt dưới 15 giữa chuyến | Cảm biến của hệ điều hành (Linux: `/sys/class/thermal`; macOS cần công cụ riêng) |
| FPS và độ trễ theo thời gian | Thấy FPS tụt khi máy nóng, không chỉ con số trung bình | Đã có trong `benchmark.py`, thêm ghi theo từng phút |
| Pin / điện năng (điện thoại) | APK chạy cả chuyến | Công cụ của Android, chỉ khi làm việc 19 |

**Hướng đề xuất:**
- Thêm chế độ chạy dài vào `tools/benchmark.py` (vd. `--duration 60m`): chạy vòng chính 2–12 như
  `edge_agent.main`, ghi CPU / RAM / nhiệt / FPS mỗi giây, báo cáo p50 / p95 / đỉnh và biểu đồ theo
  thời gian. Chỉ ghi số, không ghi frame.
- Chạy ở ba điều kiện: không có mặt, có mặt, có mặt + điện thoại (YOLO làm việc nhiều nhất).
- Mỗi bảng ghi rõ máy, hệ điều hành, số luồng, có giới hạn CPU không (`simulated` hay máy thật).
- Ngưỡng đạt nằm trong `thresholds.yaml` hoặc báo cáo: ≥ 15 FPS suốt cả lần chạy (CLAUDE.md), RAM
  không tăng dần, không bị hạ xung.
- Nếu hub không đạt: dùng YOLO INT8 (đã có), giảm tần suất YOLO, giảm độ phân giải đầu vào. Mỗi
  thay đổi phải đo lại độ chính xác.

**Cần có trước khi đo trên xe:** chốt loại hub (CPU, RAM, hệ điều hành) và cách mang project lên đó
(Docker edge ở [việc 17](#viec-prd), hoặc APK ở [việc 19](#viec-apk)). Phần đo trên máy dev thì làm
được ngay.

---

<a id="viec-toi-uu-nguong"></a>

## 13. Tối ưu ngưỡng buồn ngủ trên UTA-RLDD

**Hiện tại:** ngưỡng nhánh buồn ngủ (khối 7) và `drowsy_score` (khối 9) được chỉnh tay trên YawDD,
NITYMED (FL3D), SUST: toàn clip ngắn, buồn ngủ diễn. [UTA-RLDD](#uta-rldd) là bộ đầu tiên có buồn ngủ
thật, video 10 phút, cùng một người có cả 3 mức 0 / 5 / 10.

**Chỉnh được gì (chỉ thay số trong `thresholds.yaml`, không đổi logic):**

| Nhóm | Khoá |
|---|---|
| PERCLOS | `drowsiness.perclos_close_ratio`, `perclos_drowsy`, `perclos_rearm`; `risk.drowsy.perclos_low` / `perclos_high` |
| Điểm buồn ngủ | `risk.drowsy.weight_*`, `l1`, `l2`, `yawn_full`, `nod_full` |
| Ngáp, gục đầu | `drowsiness.yawn.*`, `drowsiness.nod.*` |
| Mốc mắt | `drowsiness.eye.baseline_*`, `close_ratio`, `open_ratio` |

**Không chỉnh bằng UTA-RLDD:** ngưỡng microsleep / L3 (`microsleep_min_s`, `microsleep_deep.*`,
`risk.microsleep_l3_s`). Nhãn chỉ có cho cả video, không biết microsleep nằm ở đâu, nên không đo được
bắt đúng hay bỏ sót. Giữ số hiện tại, kiểm tra bằng FL3D / DMD.

**Thế nào là "tối ưu":**
- Chỉ tiêu chính: **cảnh báo sai / giờ trên video `0` (tỉnh táo) ≤ 1,0**, tính cả CI 95% ([việc 1](#viec-do-bao-sai)).
- Trong các bộ ngưỡng đạt chỉ tiêu trên, chọn bộ **tách mức 0 và 10 tốt nhất**: AUC của `drowsy_score`
  (trung bình hoặc p90 mỗi video) giữa video `0` và `10`; tỉ lệ video `10` có ít nhất một L1.
- Video `5` báo riêng, không tính đúng / sai (L1 hợp lý, L3 đáng xem lại).
- Phải so trên **cùng một người** (0 so với 10 của chính họ), vì mắt mỗi người khác nhau.

**Cách làm:**
1. Thêm UTA-RLDD vào `tools/seq_eval.py trace` (hiện chỉ có `fl3d`, `sust`, `yawdd`), nhãn lấy từ tên
   file. Chạy MediaPipe một lần, lưu trace số theo frame (không lưu frame). Nặng: ~24 giờ video, nên
   chạy trên Kaggle Notebook (xem [UTA-RLDD](#uta-rldd)).
2. Dò ngưỡng bằng `seq_eval --replay --set ...`: chỉ chạy lại khối 7–12 trên trace nên rất nhanh. Dò
   lưới nhỏ, mỗi lần 1–2 khoá, không dò tất cả cùng lúc.
3. **Chống học thuộc dữ liệu:** chia theo người (UTA có sẵn fold). Chọn ngưỡng trên một số fold, báo
   số trên các fold còn lại. Không bao giờ chọn và báo số trên cùng một người.
4. **Không được làm tệ bộ cũ:** chạy lại FL3D (microsleep ≥ 1,5 s đạt L3), YawDD (báo sai), SUST với
   bộ ngưỡng mới. Tụt thì không nhận.
5. Ghi bảng trước / sau vào `eval/results/`, mỗi khoá đổi kèm lý do trong comment `thresholds.yaml`
   (giống các comment YawDD / NITYMED hiện có).

**Lưu ý:**
- Người trong UTA nhìn laptop, hơi cúi, không lái xe: tắt hoặc báo riêng `off_road` / `phone`. Luật
  gục đầu có thể khác khi lái thật.
- Nếu làm [việc 2](#dang-ky-buoc-a) (mốc mắt từ đăng ký) thì ý nghĩa của `close_ratio` /
  `perclos_close_ratio` đổi → phải dò lại. Nên chốt thứ tự: làm việc 2 trước rồi mới dò, hoặc dò
  trước rồi dò lại sau.
- Nhãn KSS là tự đánh giá, video `10` có thể có đoạn tỉnh: dùng số theo phân bố, không kỳ vọng mọi
  video `10` đều có cảnh báo.
