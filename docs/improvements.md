# Hướng cải tiến DriverGuard

Danh sách để chọn mốc tiếp theo, không phải kế hoạch. Theo CLAUDE.md, không mục nào được làm
trước khi có yêu cầu; mục nào được chọn thì thêm thành mốc trong `docs/roadmap.md`.

Cập nhật: 01/10/2026. Việc làm xong được xoá khỏi file này và ghi vào
[`docs/release-v2.md`](release-v2.md); sau mỗi lần xoá, các việc được đánh số lại liên tục.

- **01/10 đã xong:**
  - đăng ký tài xế (M9);
  - mất mặt ≥ 3 s → `unavailable` (M10);
  - chớp chậm (M11);
  - tách gục đầu / cúi đầu (M12, phép thử tốc độ đang tắt chờ dữ liệu);
  - nhướn mày (M13);
  - giao diện cho tài xế: bỏ thuật ngữ, gộp bước tải (M14);
  - nút "Kết thúc chuyến" + bảng tổng kết chuyến đi, gửi lên quản lý / kỹ sư / admin (M15);
  - một chế độ mặc định thay 3 tình huống, nút Tạm dừng / Tiếp tục lái / Đổi tài xế (M16);
  - sửa cách đo báo sai: CI, giờ đo đúng, tách lý do × mức (M17);
  - FAR / MAR theo cửa sổ trong công cụ eval (M18).
- **01/10, nhận xét kiểu mentor:** thêm việc 1–5 (mục "Ưu tiên cao", chi tiết ở [mục 17](#viec-mentor)).
- **01/10, cải tiến thêm:** thêm 11 việc (chi tiết ở [mục 18](#viec-cai-tien-them)).
- **Đã bỏ:**
  - chống chói đèn pha (giao cho yêu cầu đầu vào camera);
  - bám tài xế riêng (do bước đăng ký đảm nhận).

## Danh sách việc theo mức ưu tiên

Bấm tên việc để xuống phần chi tiết. Số thứ tự dùng để gọi tắt khi chọn mốc ("làm việc 2"). Đây chỉ
là đề xuất, bạn quyết định làm việc nào.

### Ưu tiên cao: làm trước
Không thêm tính năng; làm cho các con số đáng tin, hệ thống an toàn hơn và code dễ giữ. Chặn các
việc dò ngưỡng / thêm tín hiệu phía dưới.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 1 | [Tập kiểm tra giữ riêng theo người](#viec-holdout) | Chốt tập test theo người trước khi dò ngưỡng; báo số trên tập chưa từng dùng để chỉnh (hiện chỉnh và báo trên cùng YawDD / FL3D / SUST) |  |
| 2 | [Tín hiệu tạm: chứng minh rồi mới bật](#viec-ablation) | Trọng số 0 cho tín hiệu chưa có bằng chứng (chớp chậm, nhướn mày); bảng ablation bỏ từng tín hiệu; làm cùng việc 11 |  |
| 3 | [Bảng phân tích lỗi (FMEA) các trạng thái im lặng](#viec-fmea) | Mỗi lúc hệ thống không cảnh báo được: tài xế / quản lý được báo thế nào, im lặng tối đa bao lâu |  |
| 4 | [Trả nợ kỹ thuật](#viec-no-ky-thuat) | Gom logic chung `main.py` / `bridge.py` thành một lớp; tách `drowsiness.py`; đưa test e2e (Playwright) vào repo |  |
| 5 | [Cập nhật tài liệu theo v2](#viec-tai-lieu) | README, HowToUse, sơ đồ kiến trúc: chế độ mặc định, đăng ký, kết thúc chuyến, báo cáo |  |
| 6 | [Test hồi quy bằng trace trong CI](#viec-hoi-quy) | Bộ trace nhỏ cố định, chạy lại khối 7–12 trong CI, so với số đã chốt; lệch là đỏ |  |

### Ưu tiên vừa
Thêm tín hiệu / luật mới, vẫn không thêm model.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 7 | [Theo dõi hướng mắt](#viec-huong-nhin) | Hướng nhìn từ blendshape `eyeLook*` + mống mắt |  |
| 8 | [So định nghĩa PERCLOS](#viec-perclos) | Chạy P80 song song với ngưỡng 0,65 hiện tại |  |
| 9 | [Tách giai đoạn khởi động khi đo](#viec-do-bao-sai) | Báo riêng 30 s đầu clip; vẽ đường đánh đổi báo sai ↔ bắt sự kiện khi đổi ngưỡng |  |
| 10 | [Cảnh báo theo độ dài nhắm mắt](#viec-muc-nham-mat) | Thêm mốc nhắm 3 s và 6 s; 6 s sinh sự kiện `unresponsive` |  |
| 11 | [Tối ưu ngưỡng buồn ngủ trên UTA-RLDD](#viec-toi-uu-nguong) | Trace UTA-RLDD một lần (có cột lông mày), dò ngưỡng nhánh buồn ngủ + `drowsy_score` bằng `seq_eval --replay`, gồm các ngưỡng tạm của chớp chậm và nhướn mày; chọn theo fold người |  |
| 12 | [Chỉ số đánh giá theo từng người](#viec-theo-nguoi) | Tách FAR / MAR theo cửa sổ, độ trễ (và báo sai / giờ làm số phụ) theo từng người trong dataset; feedback báo sai theo tài xế khi chạy thật |  |
| 13 | [Tốc độ GPS cho `#/live`](#viec-gps) | Xe chạy / dừng theo tốc độ GPS của điện thoại thay cho nút bấm; suy ra đang rẽ từ hướng GPS để nới `off_road` |  |
| 14 | [Hoàn thiện FR-6: điểm chất lượng frame](#viec-chat-luong) | Ảnh mờ, góc xấu, lóa, mặt bị che → `unavailable`; phân biệt che camera với tài xế rời khung |  |
| 15 | [Cảnh báo cần xác nhận, báo quản lý ngay](#viec-xac-nhan) | L2 / L3 cần tài xế chạm / nói "tôi ổn"; không xác nhận thì báo quản lý theo thời gian thực; màn hình đội xe trực tiếp |  |
| 16 | [Trace số từ chuyến thật (có đồng ý)](#viec-trace-that) | Lưu trace số (không ảnh) + phản hồi "báo sai" của chuyến thật khi tài xế đồng ý, làm dữ liệu dò ngưỡng |  |

### Ưu tiên thấp
Cần công cụ, dữ liệu hoặc model mới, hoặc còn chưa chắc có lợi.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 17 | [Thử model mắt mới](#viec-model-mat) | Sửa `seq_eval` để trace thêm cột → thử `blinkcnn` / OCEC offline |  |
| 18 | [Quay clip + đo độ trễ cảnh báo](#viec-prd) | Clip tự quay có nhãn + công cụ đo time-to-alert; gồm cả cúi nhìn điện thoại / bảng đồng hồ và gục thật, để dò phép thử gục / cúi (đang tắt) |  |
| 19 | [Học vùng nhìn, nhận mặt bằng model](#dang-ky-buoc-c) | Học tư thế nhìn gương / đồng hồ; embedding mặt nếu chữ ký mặt của bước đăng ký không đủ |  |
| 20 | [Tăng tương phản trên web](#viec-choi) | Cân bằng tương phản bằng WebGL |  |
| 21 | [Làm nốt yêu cầu PRD](#viec-prd) | LLM (FR-12/13), Docker edge, nhật ký (FR-8/9/17), test 10 người, nộp bài; phiên bản ngưỡng + hash model trên mỗi sự kiện (FR-17, NFR-6) |  |
| 22 | [Tải thử dataset](#viec-tai-dataset) | Tải thử NTHU-DDD (HF `train.zip`), mở Dropbox Brain4Cars |  |
| 23 | [Ghi nhãn trực tiếp khi demo](#viec-nhan-demo) | Người ngồi cạnh ghi "đúng / sai / bỏ sót" ngay trong chuyến; tính báo sai / giờ theo từng người trên giờ lái thật (vd. 40 giờ / người) |  |
| 24 | [Uống nước / ăn khi lái](#viec-an-uong) | Dùng lớp `cup`, `bottle` có sẵn trong YOLOv8n (COCO), không train |  |
| 25 | [Leo thang cảnh báo theo thời gian](#viec-leo-thang) | L1 lặp lại nhiều lần trong ít phút thì nâng L2 |  |
| 26 | [Mức mệt theo nhịp sinh học](#viec-nhip-sinh-hoc) | Giờ trong ngày (trũng 2–6 h, 14–16 h) + thời gian lái liên tục thay cho hệ số 1,2 cố định |  |
| 27 | [Hàng đợi offline cho web](#viec-outbox-web) | IndexedDB giữ sự kiện / bản tổng kết chưa gửi được, gửi lại khi có mạng |  |

### Không gấp: để cuối
Không đổi độ chính xác, chỉ đổi cách dùng.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 28 | [Đóng gói app APK](#viec-apk) | Gói bản web thành app Android chạy offline |  |
| 29 | [So sánh nhiều chuyến của tài xế](#viec-nhieu-chuyen) | So chuyến này với 5 chuyến gần nhất; biểu đồ nhiều chuyến cho kỹ sư (mệt sau bao lâu, vào giờ nào) |  |
| 30 | [Đọc thành tiếng cảnh báo L2 / L3](#viec-doc-canh-bao) | HUD đọc câu hành động ("Nhìn về phía trước", "Dừng xe nghỉ ngay") bằng giọng tiếng Việt, như màn hình đăng ký |  |
| 31 | [Rung điện thoại khi cảnh báo (web)](#viec-rung) | `navigator.vibrate` song song với âm thanh |  |

### Phụ thuộc phần cứng
Cần thiết bị thật hoặc tín hiệu xe thật.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 32 | [Đo tài nguyên phần cứng](#viec-do-phan-cung) | Đo CPU, RAM, nhiệt độ, FPS khi chạy lâu trên hub gắn trên xe và trên máy chạy project; thêm vào `tools/benchmark.py` |  |
| 33 | [Tự điều chỉnh theo sức máy (web)](#viec-suc-may) | Hạ độ phân giải / tần suất YOLO khi FPS tụt; MediaPipe trong Web Worker |  |
| — | [Phần cứng thật](#viec-phan-cung) | Camera IR, xi-nhan / tốc độ CAN thật |  |

---

<a id="quyet-dinh"></a>

## 1. Cần quyết định

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

## 2. Metric đánh giá: cảnh báo sai / giờ và FAR / MAR

**Chốt (01/10): bổ sung FAR / MAR, không thay "cảnh báo sai / giờ".** Hai loại chỉ số trả lời hai câu
hỏi khác nhau, bỏ bên nào cũng mất một thông tin.

| Chỉ số | Câu hỏi nó trả lời | Ai cần |
|---|---|---|
| **FAR** (theo cửa sổ) | Khi tài xế tỉnh táo, bao nhiêu % thời gian hệ thống đoán nhầm là buồn ngủ? | Kỹ sư, khi dò / so ngưỡng |
| **MAR** (theo cửa sổ) | Khi tài xế buồn ngủ thật, bao nhiêu % thời gian hệ thống bỏ lỡ (tính cả phát hiện trễ)? | Kỹ sư; là chỉ số an toàn |
| **Cảnh báo sai / giờ** | Một giờ lái, tài xế bị làm phiền vô cớ bao nhiêu lần? | Tài xế, sản phẩm (PRD ≤ 1,0 / giờ) |

- **Vì sao không thay bằng FAR:** FAR đo *trạng thái*, báo sai / giờ đo *số lần làm phiền*; giữa hai thứ
  có khối 12 (cooldown, chống lặp). Cùng FAR = 1% trong 1 giờ: đoán sai liền 36 s → 1 lần chuông; đoán
  sai 36 lần × 1 s → 36 lần chuông. Chỉ báo sai / giờ phân biệt được, và PRD đặt chỉ tiêu theo đơn vị này.
- **Vì sao vẫn thêm FAR / MAR:** báo sai / giờ (1) không có vế bỏ sót, hệ thống im lặng đạt 0 / giờ;
  (2) rất dao động trên clip ngắn (1 lần sai trên 26 phút = 2,3 / giờ, CI 0,06 – 12,9); (3) không so
  được với paper (vd. ACM 10.1145/3560821 dùng FAR / MAR). FAR / MAR dùng mọi cửa sổ của clip nên đổi
  ngưỡng nhỏ cũng thấy số thay đổi.

**Dùng chỉ số nào ở giai đoạn nào:**

| Giai đoạn | Chỉ số chính | Dữ liệu |
|---|---|---|
| Dò / so ngưỡng (offline) | **FAR / MAR theo cửa sổ** + độ trễ phát hiện ([M18](#viec-far-mar)) | Dataset video dài (bỏ 30 s khởi động; clip ngắn gần như không còn cửa sổ) |
| Kiểm tra trước khi chốt ngưỡng | **Cảnh báo sai / giờ** gộp nhiều người + CI ([M17](#viec-do-bao-sai)) | UTA-RLDD (~8 giờ tỉnh táo) |
| Kết luận đạt PRD | **Cảnh báo sai / giờ theo từng người**, có nhãn | Chuyến demo có người ghi nhãn ([việc 23](#viec-nhan-demo)) |
| Đã triển khai | Số lần tài xế bấm "báo sai" / giờ, theo tài xế; chỉ để giám sát | Feedback HUD ([mục 14](#viec-theo-nguoi)) |

Clip dataset ngắn nên báo sai / giờ trên dataset chỉ là số kiểm tra phụ; nó cần dữ liệu dài mới có ý
nghĩa (lý do để dời nó sang giai đoạn có dữ liệu dài, không phải để bỏ). **Cách đo báo sai / giờ hiện
tại chưa đủ để kết luận đạt hay chưa đạt:**

### Vấn đề
1. **Quá ít giờ dữ liệu, chưa có khoảng tin cậy.** Khoảng tin cậy 95% theo Poisson (exact):

   | Nguồn | Đang báo | CI 95% |
   |---|---:|---:|
   | FL3D L1 (1 sai / 26 phút tỉnh táo) | 2,3 / giờ | 0,06 – 12,9 / giờ |
   | FL3D L2 (3 sai / 26 phút) | 6,9 / giờ | 1,4 – 20 / giờ |
   | YawDD (~10 sai / 124 phút) | 4,8 / giờ | 2,3 – 8,9 / giờ |

   Một lần sai trên FL3D đã bằng 2,3 / giờ. PRD §6 bắt buộc kèm số giờ clip + CI và cấm kết luận "đạt
   ≤ 1,0 / giờ". **Đã sửa (M17):** mọi bảng báo sai / giờ có số giờ đo và CI 95%. YawDD đổi thành
   6,9 / giờ (CI 3,3–12,7) vì mẫu số mới (vấn đề 6).
2. **Dữ liệu không giống lái thật.** NITYMED diễn lại, YawDD xe đỗ: mật độ hành vi dày hơn lái thật
   (phần lớn là nhìn đường nhàm chán). SUST / YawDD là nhiều clip ngắn ghép lại, clip nào cũng rơi vào
   giai đoạn khởi động (mốc EAR chưa ổn, hiệu chỉnh 5 s đầu) → "một giờ" thực chất là hàng trăm lần
   khởi động. Tốc độ giả lập cố định 60 km/h nên luật ngữ cảnh (dừng đèn đỏ, xi-nhan) không được thử.
3. **Định nghĩa "sai" trộn nhiều loại lỗi.** Sai = cảnh báo trên đoạn nhãn tỉnh táo, nhưng dataset chỉ
   gán nhãn buồn ngủ, không gán mất tập trung. SUST: 24/26 lần "sai" là `off_road` khi tài xế quay đầu
   thật, có thể là cảnh báo đúng hoặc chỉ ngưỡng hơi chặt.
4. **Đứng một mình thì dễ bị lừa:** hệ thống không bao giờ cảnh báo đạt 0 / giờ. Phải đi cùng MAR
   ([M18](#viec-far-mar), đã có), tỉ lệ bắt sự kiện và time-to-alert (PRD p95 ≤ 3 s, chưa có công cụ đo,
   xem mục 10).
5. **Số HITL trên dashboard không cùng loại:** `false_alarms / tổng cảnh báo` là precision, không phải
   / giờ, và phụ thuộc tài xế có bấm nút hay không.
6. **Mẫu số sai trong `tools/eval.py`:** báo sai / giờ = số FP / tổng thời lượng mọi video, gồm cả thời
   gian nằm trong đoạn có nhãn buồn ngủ (ở đó không thể có FP). Dataset nhiều đoạn buồn ngủ (NTHU-DDD
   gần một nửa thời lượng) thì số báo sai / giờ thấp hơn thực tế tới ~2 lần. **Đã sửa (M17):** chia cho
   thời gian thật sự có thể báo sai = tổng thời lượng trừ phần hợp các đoạn có nhãn (đã nới
   `--tolerance`).

<a id="viec-do-bao-sai"></a>

### Đã làm (M17, M18)
- CI 95% Poisson chính xác + số giờ đo trong mọi bảng báo sai / giờ (`tools/eval.py`, `tools/seq_eval.py`,
  `eval/results/report.md`).
- Mẫu số đúng (vấn đề 6).
- Tách theo lý do × mức.
- FAR / MAR theo cửa sổ (xem dưới).
- Hàm dùng chung ở `tools/metrics.py`; chi tiết ở `docs/release-v2.md`.

### Hướng đề xuất còn lại
1. **Tách giai đoạn khởi động** (30 s đầu mỗi clip) khỏi số **báo sai / giờ**, báo cáo riêng. FAR / MAR
   theo cửa sổ đã bỏ 30 s này (M18).
2. **Đường đánh đổi** FAR ↔ MAR (và cảnh báo sai / giờ ↔ tỉ lệ bắt sự kiện) khi đổi ngưỡng, dùng
   `tools/seq_eval.py --replay` (khối 7–12, không cần chạy lại MediaPipe) để thấy ngưỡng hiện tại đứng
   ở đâu thay vì một điểm duy nhất.
3. **Dữ liệu dài, liên tục:** chuyến demo có người ghi nhãn ([việc 23](#viec-nhan-demo)); clip tự quay
   ở mục 10. Dataset đã kiểm tra (mục 3): **UTA-RLDD** cho cảnh báo sai / giờ, **DMD** cho recall theo
   frame và time-to-alert; hai bộ bổ sung cho nhau.

<a id="viec-far-mar"></a>

### FAR / MAR theo cửa sổ (đã làm, M18)

- **Định nghĩa:**
  - FAR = cửa sổ tỉnh táo bị đoán buồn ngủ / tổng cửa sổ tỉnh táo.
  - MAR = cửa sổ buồn ngủ không bị đoán buồn ngủ / tổng cửa sổ buồn ngủ.
  - Dùng cửa sổ, không dùng frame: ở 30 fps các frame liền nhau gần như trùng nhau.
- **Quy ước** (`config/thresholds.yaml` → `eval`, code ở `tools/metrics.py`):
  - cửa sổ 10 s không chồng nhau, bỏ 30 s đầu mỗi clip;
  - cửa sổ buồn ngủ: ≥ 50% nằm trong đoạn có nhãn; cửa sổ tỉnh táo: ≥ 50% thời gian biết là tỉnh và không
    chạm đoạn nào; còn lại bỏ;
  - đoán buồn ngủ: mức của nhánh buồn ngủ ≥ L1 (báo thêm ≥ L2) trong cửa sổ;
  - mất tập trung tính riêng;
  - CI Wilson, lạc quan vì các cửa sổ trong một clip tương quan.
- **Kết quả hiện có** (`eval/results/`): gần như không đọc được trên dataset đang có.
  - FL3D: chỉ 7 cửa sổ hợp lệ.
  - YawDD: 13 cửa sổ.
  - SUST: clip 10 s, không còn cửa sổ nào.
  - Chỉ số này dành cho video dài: UTA-RLDD (việc 11), DMD.

| Dataset | FAR | MAR | Ghi chú |
|---|---|---|---|
| FL3D, YawDD, NTHU-DDD, DMD | Có | Có | Nhãn theo đoạn / theo frame; FL3D, YawDD quá ngắn |
| UTA-RLDD | Có (video `0`) | Chỉ tham khảo | Nhãn cả video: video `10` có đoạn tỉnh, MAR bị thổi phồng |
| SUST | Không | Không | Clip 10 s, bỏ 30 s khởi động thì không còn gì |

---

## 3. Dữ liệu đánh giá

Kiểm tra 30/09/2026 (metadata, trang chính, license), chưa tải, chưa chạy thử. Tất cả chỉ dùng để
đánh giá: không đưa frame / ảnh mặt vào repo, báo cáo hay slide, chỉ số liệu. Muốn dùng bộ nào thì
thêm thành mốc riêng (cần task mới trong `tools/dataset.py`).

| Dataset | Dùng cho | Lấy thế nào | Trạng thái |
|---|---|---|---|
| UTA-RLDD | Cảnh báo sai / giờ (~8 giờ tỉnh táo), buồn ngủ thật theo mức 0 / 5 / 10 | Kaggle 96,6 GB, hoặc Kaggle Notebook | Nên dùng (dò ngưỡng, việc 11) |
| DMD | Recall theo frame, time-to-alert, ngáp che tay, mất tập trung, hướng nhìn | Cổng DMD, CC BY-NC-ND | Nên dùng |
| DROZY | Buồn ngủ thật + KSS / PVT / EEG, IR phụ | ORBi 2,46 GB, tải thẳng | Nên dùng |
| NTHU-DDD | Video IR, kính râm, gục đầu, nói / cười (báo sai) | HF gated `auto` hoặc email NTHU | Cần xem `train.zip` trước |
| Brain4Cars | `off_road` khi rẽ / chuyển làn, tốc độ thật | Dropbox 16 GB | Cần xem độ dài clip trước |

### Phần dữ liệu còn thiếu và nguồn lấp

Đối chiếu dữ liệu đã có / sắp có (FL3D, YawDD, SUST, UTA-RLDD, DMD) với điều kiện PRD FR-9 và các khối.
Đã bỏ khỏi danh sách (chốt 30/09): ngược sáng / đèn pha, mặt người Việt, điện thoại để thấp, khẩu
trang, mũ lưỡi trai, hai người trong khung hình (không cần dataset; chọn mặt tài xế của M9 đã test
bằng landmark giả). Mọi phần còn lại đều đã có nguồn.

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
  mở cố định (đăng ký tài xế M9: học từ video `0` rồi dùng cho `5` / `10`) và trip memory.

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

Dùng để chỉnh ngưỡng buồn ngủ: [việc 11](#viec-toi-uu-nguong).

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
giờ); gộp được với công cụ đo time-to-alert (việc 18).

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
  (giống kết quả đăng ký tài xế, M9).

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

## 4. Đăng ký tài xế: phần còn lại

Bước A (mốc mắt, miệng, tư thế của riêng tài xế) và bước B (chọn đúng mặt tài xế bằng chữ ký mặt +
vị trí) đã làm ở mốc M9 (01/10, xem `docs/roadmap.md` và `edge_agent/perception/enrollment.py`).
Còn lại:

<a id="dang-ky-buoc-c"></a>

**Bước C (tuỳ chọn): các vùng nhìn hợp lệ**
- Tư thế đầu khi nhìn gương / bảng đồng hồ của chính tài xế đó, dùng cho:
  - Gục đầu (M12): cúi đúng về tư thế bảng đồng hồ với mắt mở thì không phải gục đầu.
  - Mục 7 (hướng nhìn): mốc hướng nhìn theo từng vùng.
- **Không** dùng để bỏ qua `off_road`: nhìn gương quá 2 s khi chạy vẫn phải báo.
- Thêm bước vào đăng ký thì đăng ký lâu hơn (đang ~10 s): cân nhắc với yêu cầu "không quá lâu".

**Bước D (chỉ khi chữ ký mặt không đủ): embedding mặt**
- Một model nhận dạng mặt pretrained nhỏ (vd. SFace trong OpenCV Zoo; *chưa kiểm tra license, kích
  thước, tốc độ*) chỉ chạy lúc đăng ký và khi nghi đổi người, không chạy mỗi frame, nên không ảnh
  hưởng 15 FPS. Là model mới nên cần quyết định riêng.

**Giới hạn còn lại của M9**
- Chữ ký mặt (tỉ lệ landmark) chưa đo trên người thật nhiều người trong xe; dataset eval đều chỉ có
  một người.
- Đổi tài xế giữa chuyến: đã có nút "Đổi tài xế" (M16), người lái mới đăng ký lại. Chưa **tự phát
  hiện** người khác ngồi vào: cần chữ ký mặt đủ tin cậy mới làm được.
- MediaPipe chỉ trả `num_faces` = 2 mặt: với ≥ 3 người có thể không thấy tài xế nếu hai mặt khác nổi
  hơn. Tăng lên 3 thì phải đo lại FPS.
- Mốc mắt nhắm (bước 3) mới dùng để kiểm tra đăng ký đúng; chưa dùng để đổi thang `close_ratio`
  (độ mở mắt theo khoảng nhắm → mở): đổi thang thì phải dò lại ngưỡng trên dataset.

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
1. <a id="viec-perclos"></a>**Kiểm tra định nghĩa PERCLOS.** Video dùng P80 (mắt khép ≥ 80%, ≈ EAR < 0,2 × mốc). Code dùng
   `perclos_close_ratio: 0.65` (khép ~35% đã tính) → nhạy hơn, dễ tính cả nheo mắt. Chạy P80 song
   song trên FL3D / YawDD / SUST để so, chưa thay ngay.
2. <a id="viec-muc-nham-mat"></a>**Mức cảnh báo tăng theo thời gian nhắm.** Video: 1–2 s gợi ý trạm dừng; ≥ 3 s còi + rung ghế;
   ≥ 6 s coi là không còn phản ứng → giảm tốc, tấp làn. Hiện chỉ một L3 ở 1,5 s. Thêm mốc
   `closed_duration` ≥ 3 s và ≥ 6 s trong `thresholds.yaml`; mốc 6 s sinh sự kiện `unresponsive`
   lên backend và yêu cầu giảm tốc qua CAN giả lập. Cảnh báo 1–2 s kèm gợi ý dừng nghỉ.
Cả hai không thêm model, chỉ thêm ngưỡng vào `thresholds.yaml`, test được bằng chuỗi số giả. Các đề
xuất khác của video đã làm ở v2, xem `docs/release-v2.md`:
- mốc mắt mở cố định từ đầu chuyến (M9);
- tốc độ mở mắt lại khi chớp (M11);
- gục đầu = rơi chậm rồi giật lên (M12);
- nhướn mày để giữ mắt mở (M13).

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
- **Đèn pha chiếu thẳng** (vùng mắt cháy trắng, landmark lệch): chốt 01/10 không xử lý bằng phần
  mềm, mà bằng **yêu cầu đầu vào camera** (camera IR + đèn LED IR, xem dưới). Mất mặt do chói thì
  thành `unavailable` theo FR-6 (đã làm ở M10), không còn báo L2 sai.
- **Web không có CLAHE.** Webcam / camera điện thoại tự chỉnh phơi sáng chậm khi ánh sáng đổi đột
  ngột; trình duyệt gần như không cho điều khiển.
- **Giới hạn vật lý:** webcam RGB trong cabin tối gần như không thấy mặt; phần mềm không bù được.
- **Chưa có dữ liệu** đèn pha / đèn đường quét qua; chưa đánh giá riêng đường chạy web ban đêm.

<a id="viec-choi"></a>

### Hướng đề xuất
- **Cân bằng tương phản trên web bằng WebGL shader** (nhẹ hơn OpenCV.js ~8 MB); đo lại FPS ≥ 15.
- **Yêu cầu đầu vào camera (thay cho xử lý chói bằng phần mềm):** camera IR + đèn LED IR 850/940 nm
  (chuẩn của DMS thương mại, ít bị đèn pha ảnh hưởng). Code đã nhận biết IR sẵn.
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
- Mốc hướng nhìn theo từng tài xế / từng vùng (đường, gương, bảng đồng hồ) lấy từ bước đăng ký (M9:
  bước nhìn đường; mục 4 bước C) thay vì một ngưỡng chung.
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

- **off_road trên xe thật:** 24 cảnh báo L2 trong 3 giờ SUST là quay đầu thật. Cần xi-nhan / tốc
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
Python qua Pyodide), mở bằng trình duyệt. Lần đầu mỗi máy phải tải khoảng 60 MB (Python, OpenCV, MediaPipe, ONNX Runtime, model).

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
  không được im lặng (dùng lại trạng thái `unavailable` / sự kiện `monitoring_unavailable` của M10).
- APK nặng thêm ~40–50 MB vì chứa sẵn Python và model (*ước lượng*).
- Phát tán APK có YOLO là phân phối phần mềm AGPL: phải kèm mã nguồn (xem License YOLO ở
  [mục 1](#quyet-dinh)).

<a id="viec-doc-canh-bao"></a>

### Đọc thành tiếng cảnh báo L2 / L3

- Giao diện cho tài xế đã làm ở M14: bỏ L0–L3 trên HUD, gộp bước tải, ô camera chỉ còn trạng thái dễ
  hiểu. Xem `docs/release-v2.md`.
- **Còn lại:** đọc câu hành động của L2 / L3 bằng giọng tiếng Việt, dùng lại `say()` trong
  `frontend/src/hud/chime.ts` của màn hình đăng ký.
  - Chỉ đọc khi cảnh báo mới, không lặp theo còi L3.
  - Câu ngắn, trùng với chữ trên màn hình.
- **Kiểm tra với người thật:** gộp với buổi test hiểu cảnh báo 10 người của PRD ([mục 10](#viec-prd)).

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
  ([việc 28](#viec-apk)).
- **Máy chạy project** (máy dev / laptop demo): làm mốc so sánh, và để biết bản `simulated` hiện tại
  đang chiếm bao nhiêu tài nguyên.

| Chỉ số | Vì sao | Cách đo (đề xuất) |
|---|---|---|
| CPU % (cả tiến trình và từng luồng: vòng chính, YOLO) | Còn dư bao nhiêu cho app khác trên hub (bản đồ, camera lùi…) | `psutil` lấy mẫu mỗi giây |
| RAM (RSS, đỉnh, có tăng dần theo thời gian không) | Bắt rò rỉ bộ nhớ khi chạy nhiều giờ; frame chỉ nằm trong RAM nên phải chắc không bị giữ lại | `psutil` |
| Nhiệt độ CPU / SoC | Máy nóng → tự hạ xung → FPS tụt dưới 15 giữa chuyến | Cảm biến của hệ điều hành (Linux: `/sys/class/thermal`; macOS cần công cụ riêng) |
| FPS và độ trễ theo thời gian | Thấy FPS tụt khi máy nóng, không chỉ con số trung bình | Đã có trong `benchmark.py`, thêm ghi theo từng phút |
| Pin / điện năng (điện thoại) | APK chạy cả chuyến | Công cụ của Android, chỉ khi làm việc 28 |

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
(Docker edge ở [việc 21](#viec-prd), hoặc APK ở [việc 28](#viec-apk)). Phần đo trên máy dev thì làm
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
- Khi dò: so các bộ ngưỡng bằng **FAR theo cửa sổ trên video `0`** ([M18](#viec-far-mar)), vì ổn
  định hơn số lần cảnh báo.
- Điều kiện chặn: **cảnh báo sai / giờ gộp trên video `0` ≤ 1,0**, tính cả CI 95% ([M17](#viec-do-bao-sai)).
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
- Đăng ký tài xế (M9) không đổi thang `close_ratio` / `perclos_close_ratio`, và clip eval không có
  bước đăng ký (xe chạy 60 km/h từ đầu), nên dò ngưỡng trên đường tự học như cũ. Mốc mắt mở cố định
  của M9 chỉ có tác dụng khi chạy thật.
- Nhãn KSS là tự đánh giá, video `10` có thể có đoạn tỉnh: dùng số theo phân bố, không kỳ vọng mọi
  video `10` đều có cảnh báo.

---

<a id="viec-theo-nguoi"></a>

## 14. Chỉ số đánh giá theo từng người

**Hiện tại:** `tools/eval.py` và `seq_eval` gộp mọi video thành một con số. Con số trung bình có thể
che mất một nhóm người bị báo sai nhiều (đeo kính, mắt nhỏ, hay ngáp, ngồi lệch camera). Ngưỡng đang
dùng chung cho mọi người; chỉ có mốc mắt / miệng / tư thế là riêng từng tài xế (đăng ký M9).

**Chỉ số nào cho từng người:** theo [mục 2](#viec-far-mar), trên dataset dùng **FAR / MAR theo cửa
sổ** làm chính: 10 phút tỉnh táo vẫn có ~60 cửa sổ, trong khi báo sai / giờ của một người trên 10 phút
gần như vô nghĩa (xem CI bên dưới). Báo sai / giờ theo từng người chỉ kết luận được trên giờ lái thật
có nhãn ([việc 23](#viec-nhan-demo)).

### Đánh giá trên dataset (offline)

Mục tiêu: trả lời "các tài xế khác nhau có cần ngưỡng khác nhau không?" trước khi làm cá nhân hoá.

| Chỉ số theo người | Ghi chú |
|---|---|
| FAR, MAR theo cửa sổ + số cửa sổ, độ trễ phát hiện | Số chính ([M18](#viec-far-mar)) |
| Giờ tỉnh táo, số cảnh báo sai, báo sai / giờ + CI 95% | Số phụ; mẫu số là giờ tỉnh táo ([M17](#viec-do-bao-sai)) |
| Tỉ lệ bắt sự kiện (theo đoạn có nhãn), độ trễ p50 | Chỉ với dataset có nhãn theo đoạn (FL3D, YawDD, NTHU-DDD, DMD) |
| Tách theo lý do (microsleep, drowsy, ngáp, gục đầu, off_road, phone) | Biết người đó bị báo sai vì luật nào |
| `drowsy_score` trung bình / p90 ở mức tỉnh và buồn ngủ, AUC tách 2 mức | Chỉ với UTA-RLDD (cùng người có video `0` và `10`) |
| Thuộc tính người: kính, kính râm, IR / RGB | Lấy từ metadata dataset, để gộp theo nhóm |

- **Báo cáo phân bố, không chỉ trung bình:** trung vị, p90 giữa các người, danh sách 5 người tệ nhất
  kèm lý do; gộp theo nhóm (đeo kính / không đeo kính).
- **Mỗi người có quá ít giờ nên CI rất rộng:** UTA-RLDD ~10 phút tỉnh táo / người → 0 cảnh báo sai
  vẫn có cận trên CI 95% ≈ 22 / giờ; 1 cảnh báo sai = 6 / giờ (CI 0,15 – 33 / giờ). Không kết luận
  từng người đạt / không đạt; so người bằng FAR / MAR theo cửa sổ hoặc chỉ số liên tục (`drowsy_score`,
  AUC), so báo sai / giờ theo nhóm.
- **Mã người** lấy từ dataset: UTA-RLDD theo thư mục người, NTHU-DDD theo mã `001`…, YawDD / SUST /
  FL3D theo tên file (*chưa kiểm tra từng bộ có mã người hay không*). Thêm cột `subject` tuỳ chọn vào
  CSV nhãn của `tools/eval.py`; thiếu thì coi mỗi video là một người.

**Dùng kết quả thế nào:**
- Các người gần nhau → chưa cần cá nhân hoá, giữ ngưỡng chung.
- Một nhóm lệch hẳn (vd. đeo kính) → tìm nguyên nhân trước; nếu cá nhân hoá thì làm qua **mốc của bước
  đăng ký** (M9: chuẩn hoá theo độ mở mắt / miệng lúc tỉnh táo của chính tài xế), không đặt ngưỡng
  riêng cho từng người bằng tay.
- Khi dò ngưỡng ([việc 11](#viec-toi-uu-nguong)): thêm điều kiện "không người nào trong fold kiểm tra
  tệ hơn rõ rệt", không chỉ nhìn trung bình.

### Khi chạy thật (online)

- **Không tính được FAR / MAR đúng nghĩa:** ngoài đường không có nhãn. Lần bỏ sót thì không ai thấy
  (không có cảnh báo để bấm), nên MAR theo từng tài xế không đo được. Muốn có số đúng thì phải là
  chuyến demo có người ghi nhãn ([việc 23](#viec-nhan-demo)).
- **Đo được:** số lần tài xế bấm "báo sai" / giờ lái, theo từng tài xế và từng lý do. Backend đã có
  `driver_id` trên sự kiện và `by_reason` trong `/api/v1/stats`; còn thiếu số giờ lái theo tài xế làm
  mẫu số (lấy từ sample mỗi phút) và phần tách theo tài xế.
- **Tín hiệu bị lệch:** tài xế không bấm mọi lần báo sai (số thấp hơn thực tế), và có thể bấm để tắt
  chuông khi buồn ngủ thật. Vì vậy:
  - Chỉ dùng để **giám sát**: hiện trên dashboard kỹ sư, gắn cờ tài xế có tỉ lệ bấm cao để xem lại
    timeline.
  - **Không tự hạ ngưỡng** theo feedback. Nếu sau này muốn tự chỉnh: có giới hạn cứng, chỉ cho lý do ít
    rủi ro (`phone`, `off_road`), không bao giờ cho microsleep / `drowsy_score`; là quyết định riêng.

**Cách làm (offline):** thêm `subject` vào `Episode` / nhãn, hàm `score` trả thêm một bảng theo người;
test bằng nhãn + prediction giả (giống `tests/test_edge_agent/test_m7_tools.py`). CI, mẫu số đúng và
FAR / MAR theo cửa sổ đã có (M17, M18, `tools/metrics.py`).

---

<a id="viec-nhieu-chuyen"></a>

## 15. So sánh nhiều chuyến của tài xế

Bảng tổng kết một chuyến đã làm ở M15 (xem `docs/release-v2.md`):
- nút "Kết thúc chuyến";
- bản cho tài xế;
- tab "Báo cáo chuyến đi" cho quản lý / kỹ sư / admin, có trạng thái đã xem.

**Còn lại:**
- **So với chính mình:**
  - So khác biệt với trung bình 5 chuyến gần nhất của cùng tài xế. Cần `driver_id`, tức đã đăng nhập
    hoặc thiết bị gắn với tài xế.
  - Tính ở backend từ các bản tổng kết đã lưu.
- **Kỹ sư, nhiều chuyến:**
  - `drowsy_score` theo số giờ lái liên tục và theo giờ trong ngày, để thấy tài xế mệt sau bao lâu và
    vào giờ nào.
  - Số báo sai tài xế bấm / giờ lái ([mục 14](#viec-theo-nguoi)).
- **Sample mỗi phút đầy đủ hơn** (nếu cần biểu đồ chi tiết hơn bản tổng kết): thời gian nhìn khỏi
  đường, cầm điện thoại, ngáp / gục đầu, tốc độ.
- Không chấm điểm hay xếp hạng tài xế. Đánh giá chuyến chỉ mô tả, vì cảnh báo còn có thể sai.

---

<a id="viec-nhan-demo"></a>

## 16. Ghi nhãn trực tiếp khi demo

**Vì sao cần:** báo sai / giờ chỉ kết luận được trên giờ lái dài, liên tục, theo từng người (vd. 40
giờ / người: 0 lần sai thì cận trên CI 95% ≈ 0,09 / giờ; muốn cận trên ≤ 1,0 / giờ cần ≥ 3,7 giờ không
lần sai nào). Nhưng CLAUDE.md cấm ghi frame ra đĩa, nên **sau chuyến không thể xem lại video để gán
nhãn**. Nhãn phải ghi ngay trong chuyến.

**Nguồn nhãn:**

| Nguồn | Đáng tin | Dùng cho |
|---|---|---|
| Người ngồi cạnh bấm "đúng / sai" mỗi lần cảnh báo, và "bỏ sót" khi thấy tài xế có dấu hiệu mà hệ thống im | Cao | Báo sai / giờ theo người; bỏ sót (xấp xỉ) |
| Tài xế tự đánh giá KSS (1–9), người ngồi cạnh hỏi miệng mỗi 15 phút | Vừa | Mức buồn ngủ theo đoạn, so với `drowsy_score` |
| Nút "báo sai" của tài xế trên HUD | Thấp (lệch, xem [mục 14](#viec-theo-nguoi)) | Chỉ để đối chiếu với nhãn của người ngồi cạnh |

**Cách làm (đề xuất):**
- Một màn hình ghi nhãn trên máy thứ hai (điện thoại người ngồi cạnh), nút to: "Đúng", "Sai", "Bỏ
  sót", "KSS = …". Mỗi lần bấm gửi metadata JSON (`trip_id`, thời điểm, nhãn), không có ảnh.
- Ghép nhãn với sự kiện cảnh báo theo `trip_id` + thời gian (dung sai vài giây, nằm trong
  `thresholds.yaml`); cảnh báo không được ai bấm thì để "chưa xác định", không tự coi là đúng.
- Báo cáo theo từng người: giờ lái, báo sai / giờ + CI, số bỏ sót người ngồi cạnh thấy, bảng đối chiếu
  với nút "báo sai" của tài xế (biết tài xế bấm sai lệch bao nhiêu).
- Tài xế không thao tác gì khi đang chạy; KSS hỏi miệng.

**Giới hạn:**
- **An toàn:** không cho người buồn ngủ thật lái để lấy dữ liệu. Chuyến demo chủ yếu đo **báo sai**
  (lái tỉnh táo); MAR / bỏ sót vẫn lấy từ dataset ([M18](#viec-far-mar)). Bỏ sót trong demo chỉ là
  số tham khảo.
- Người ngồi cạnh cũng bỏ sót hoặc phản ứng trễ: dùng dung sai thời gian, và nếu được thì hai người ghi
  độc lập ở vài chuyến để đo độ khớp.
- Cần người tham gia đồng ý; chỉ lưu metadata, gắn nhãn `demo` để không trộn với số production.
- Khi đã triển khai không có người ngồi cạnh: chỉ còn nút "báo sai" của tài xế, dùng để giám sát.

---

<a id="viec-mentor"></a>

## 17. Nhận xét kiểu mentor (01/10): các việc ưu tiên cao

Rà toàn bộ project ngày 01/10 (code, test, eval, docs, git), sau mốc M18. Điểm mạnh giữ nguyên:
kiến trúc 14 khối, logic test bằng chuỗi số giả, ngưỡng tập trung một chỗ, kỷ luật quyền riêng tư,
báo cáo eval trung thực. Năm việc dưới đây là phần còn thiếu để các con số đáng tin và hệ thống đủ an
toàn để đem đi thử thật. (Ngoài phạm vi file này: commit / deploy v2; sẵn sàng cho người dùng thật
như đổi mật khẩu, giới hạn đăng nhập, migration database.)

<a id="viec-holdout"></a>

### Việc 1: tập kiểm tra giữ riêng theo người

**Vấn đề:** chưa kiểm chứng trên lái xe thật, và cách đo hiện tại lạc quan.
- Mọi con số từ clip ngắn hoặc diễn; số giờ lái thật có nhãn bằng 0. FAR / MAR không đọc được trên
  dataset hiện có ([M18](#viec-far-mar)); chỉ tiêu PRD ≤ 1,0 / giờ chưa chứng minh được.
- **Lỗi phương pháp:** ngưỡng được chỉnh trên YawDD, FL3D, SUST (comment trong `thresholds.yaml`), rồi
  kết quả báo trên chính các bộ đó. Như vừa ra đề vừa tự chấm: số báo cáo cao hơn số thật.

**Hướng làm:**
- Trước khi dò ngưỡng tiếp ([việc 11](#viec-toi-uu-nguong)), chốt **tập kiểm tra theo người**: một
  phần người của mỗi dataset (theo mã người; thiếu mã thì theo video), ghi danh sách vào repo
  (`eval/splits/*.txt`), không dùng khi dò.
- Công cụ eval nhận `--split dev|test`. Mọi bảng ghi rõ split. Số trên `test` chỉ chạy khi chốt một bộ
  ngưỡng, không chạy lặp đi lặp lại.
- Các bộ đã dùng để chỉnh (YawDD, FL3D, SUST) ghi rõ là "dev". Số "test" đầu tiên đúng nghĩa sẽ là
  UTA-RLDD / DMD theo người.
- Dữ liệu lái thật: [việc 18](#viec-prd) (clip tự quay), [việc 23](#viec-nhan-demo) (ghi nhãn khi
  demo). Không có hai việc này thì không kết luận được về chỉ tiêu PRD.

<a id="viec-ablation"></a>

### Việc 2: tín hiệu tạm phải chứng minh rồi mới bật

**Vấn đề:** độ phức tạp tăng nhanh hơn bằng chứng.
- Đang có nhiều ngưỡng "tạm": chớp chậm, nhướn mày; các bước đăng ký 2 s / 3 s / 2 s, ngưỡng chữ ký
  mặt 0,08; phép thử gục / cúi đang tắt.
- Tổng trọng số `drowsy_score` đã vượt 100 (điểm bị chặn ở 100).
- Chớp chậm đã thêm 1 cảnh báo sai trên FL3D; nhướn mày chưa đo được.

**Hướng làm:**
- **Nguyên tắc:** tín hiệu chưa có số đo chứng minh thì trọng số 0. Code vẫn chạy, vẫn ghi vào metadata
  và trace để đo, nhưng không cộng vào `drowsy_score`. Bật khi eval cho thấy có lợi trên tập dev và
  không làm tệ tập test.
- **Ablation** sau khi có UTA-RLDD: chạy `seq_eval --replay` lần lượt bỏ từng thành phần (PERCLOS,
  microsleep, ngáp, gục, chớp chậm, nhướn mày). Bảng: FAR, MAR, báo sai / giờ, AUC tách mức 0 / 10.
  Thành phần nào bỏ ra mà không tệ hơn thì bỏ hẳn hoặc để 0.
- Chuẩn hoá lại trọng số để tổng = 100 sau ablation.
- Ghi kết quả từng tín hiệu vào `docs/release-v2.md`.

<a id="viec-fmea"></a>

### Việc 3: bảng phân tích lỗi (FMEA) các trạng thái im lặng

**Vấn đề:** đây là hệ thống liên quan an toàn, nhưng tư duy an toàn chưa được viết thành tài liệu. Chỗ
nguy hiểm nhất là lúc hệ thống im lặng.

| Trạng thái im lặng | Đang có | Cần trả lời |
|---|---|---|
| Tạm ngưng giám sát (`unavailable`, mất mặt ≥ 3 s) | HUD + sự kiện backend (M10) | Kéo dài bao lâu thì nâng mức (vd. quản lý được báo ngay khi > 1 phút)? |
| Tài xế gục ra khỏi khung hình, trước đó không thấy mắt nhắm | Không cảnh báo (đánh đổi FR-6) | Có cần còi nhẹ khi mất mặt lúc đang chạy nhanh? |
| Chưa đăng ký / đăng ký thất bại | Thẻ nhắc trên HUD | Có giới hạn số phút lái khi chưa đăng ký? |
| Mất camera | HUD + sự kiện | Quản lý biết sau bao lâu? |
| YOLO trả kết quả quá trễ (máy yếu) | Đếm, in log | Tài xế / quản lý có biết phát hiện điện thoại đang tắt? |
| Web: tab chạy nền, máy khoá màn hình | Chưa có | Phát hiện và báo "tạm ngưng" ([việc 28](#viec-apk)) |
| Backend mất mạng | Outbox offline trên thiết bị; web chỉ giữ trong RAM | Web mất báo cáo khi rời trang |

**Hướng làm:** một trang `docs/safety-fmea.md`. Mỗi dòng có: nguyên nhân, mức nghiêm trọng, cách phát
hiện, tài xế thấy gì, quản lý thấy gì, thời gian im lặng tối đa, test nào kiểm. Dòng nào chưa có test
hoặc chưa có cách phát hiện thì thành việc riêng. Gộp với đo time-to-alert ([việc 18](#viec-prd)).

<a id="viec-no-ky-thuat"></a>

### Việc 4: trả nợ kỹ thuật

- **Logic bị lặp giữa `edge_agent/main.py` (thiết bị) và `edge_agent/web/bridge.py` (web):**
  `unavailable`, đăng ký, nút xe, đổi tài, kết thúc chuyến, sự kiện hệ thống. M9–M16 đều phải sửa
  hai nơi; sớm muộn sẽ lệch.
  - Gom thành một lớp chung (vd. `edge_agent/runtime.py`), nhận số liệu một frame và trả trạng thái HUD
    + bản ghi metadata. `main.py` và `bridge.py` chỉ còn phần vào / ra riêng (camera, HTTP, Pyodide).
  - Test của lớp chung thay cho test trùng ở hai nơi.
- **`edge_agent/analysis/drowsiness.py` gần 900 dòng:** tách thành module con (mắt / PERCLOS, ngáp,
  gục đầu, chớp chậm, lông mày), giữ `DrowsinessAnalyzer` làm lớp ghép. Không đổi hành vi: replay trace
  trước / sau phải ra đúng cùng số.
- **Test e2e:** các kịch bản Chrome headless đã dùng khi làm M14–M16 (đăng ký, tạm dừng, đổi tài, kết
  thúc chuyến, dashboard báo cáo) đang nằm ngoài repo. Đưa vào thành test Playwright (camera giả từ
  file y4m, backend trên database tạm), chạy trong CI.

<a id="viec-tai-lieu"></a>

### Việc 5: cập nhật tài liệu theo v2

- `README.md`, `HowToUse.md`, `docs/architecture_diagram.md` gần như chưa nhắc tới v2. Người mới đọc
  sẽ chạy sai cách: tưởng còn 3 tình huống, không biết bước đăng ký, nút tạm dừng / đổi tài / kết thúc
  chuyến, tab "Báo cáo chuyến đi".
- Sơ đồ kiến trúc thêm: giai đoạn đăng ký của khối 6, tổng kết chuyến của khối 11, nguồn xe "lái tay"
  của khối 10, các đường HUD → agent (`/vehicle`, `/end-trip`).
- Quy ước từ nay: mốc nào đổi cách dùng thì sửa HowToUse trong cùng thay đổi.

---

<a id="viec-cai-tien-them"></a>

## 18. Cải tiến thêm (01/10)

Các ý từ lần rà project ngày 01/10, chưa có ở các mục trên. Đều giữ ràng buộc của CLAUDE.md: chỉ model
pretrained, không lưu ảnh, ≥ 15 FPS. Năm ý đáng làm trước: việc 13, 14,
6, 15, 16.

<a id="viec-hoi-quy"></a>

### Việc 6: test hồi quy bằng trace trong CI

- **Vì sao:** khi làm M10, replay lệch rất nhẹ (AUC chớp 0,624 → 0,623) vì khối 7 đổi nhịp cache yaw,
  không test nào bắt được; chỉ thấy nhờ so báo cáo bằng tay.
- **Cách làm:**
  - Chọn vài chục video ngắn từ trace sẵn có (FL3D, SUST, YawDD), lưu thành file nhỏ trong repo
    (chỉ số, không ảnh).
  - Test chạy `seq_eval replay` khối 7–12 và so với kết quả đã chốt: số sự kiện, cảnh báo theo mức /
    lý do, vài điểm `drowsy_score`.
  - Đổi ngưỡng có chủ đích thì cập nhật file kết quả trong cùng thay đổi, kèm lý do.
- Làm cùng [việc 1](#viec-holdout) (chọn video từ tập dev).

<a id="viec-gps"></a>

### Việc 13: tốc độ GPS cho `#/live`

- **Vì sao:** web không có CAN; từ M16 xe chạy / dừng theo nút bấm và chạy cố định 50 km/h, nên luật
  ngữ cảnh (đèn đỏ, cao tốc, nghỉ) không phản ánh đường thật. Báo sai chính đang là `off_road` khi quay
  đầu thật (24/26 trên SUST), mà không có xi-nhan để biết đang rẽ.
- **Cách làm:**
  - Nguồn tín hiệu xe mới cho khối 10: tốc độ từ `navigator.geolocation` (`coords.speed`), làm mượt
    vài giây; mất GPS thì quay về nút bấm (chế độ hiện tại).
  - **Đang rẽ:** hướng GPS (`coords.heading`) đổi nhanh hơn một ngưỡng (°/s, trong `thresholds.yaml`)
    thì coi như xi-nhan bật, dùng lại `turn_signal_grace_s` của khối 10.
  - Chỉ gửi số lên Python; không lưu vị trí, không gửi toạ độ lên backend (chỉ tốc độ như hiện tại).
  - Test bằng chuỗi tốc độ / hướng giả.
- **Rủi ro:** GPS điện thoại trễ 1–2 s và nhiễu khi chạy chậm; trong hầm thì mất.

<a id="viec-chat-luong"></a>

### Việc 14: hoàn thiện FR-6, điểm chất lượng frame

- **Vì sao:** PRD FR-6 đòi `unavailable` khi mất mặt **hoặc** chất lượng kém / góc xấu / lóa; M10 mới
  làm phần mất mặt. Ảnh xấu mà vẫn đoán thì sinh báo sai hoặc bỏ sót không ai biết.
- **Cách làm:**
  - Điểm chất lượng mỗi frame từ số đã có: tỉ lệ landmark trong ảnh, góc đầu so với mốc, độ sáng vùng
    mặt, cờ lệch EAR hai mắt của khối 5, độ nét (phương sai Laplacian vùng mặt, chỉ một phép tính
    nhỏ). Ngưỡng trong `thresholds.yaml`.
  - Điểm thấp kéo dài ≥ N giây khi xe chạy → `unavailable` với lý do (`low_quality`, `bad_angle`,
    `glare`), không cảnh báo, HUD nói rõ.
  - **Che camera hay rời khung:** cả khung tối / gần như phẳng (phương sai thấp) → camera bị che;
    khung bình thường mà không thấy mặt → tài xế rời khung. Hai lý do khác nhau trên HUD và backend.
  - Nối với [việc 3](#viec-fmea).

<a id="viec-xac-nhan"></a>

### Việc 15: cảnh báo cần xác nhận, báo quản lý ngay

- **Vì sao:** quản lý hiện chỉ thấy báo cáo sau chuyến (M15). Tài xế ngủ gật lặp lại mà không phản ứng
  thì không ai biết lúc đó.
- **Cách làm:**
  - L2 / L3: tài xế xác nhận bằng một chạm to trên HUD (hoặc nói "tôi ổn" nếu trình duyệt hỗ trợ nhận
    giọng nói); có thời hạn trong `thresholds.yaml`.
  - Không xác nhận, hoặc L3 lặp lại trong ít phút → sự kiện `driver_unresponsive` lên backend ngay
    (nối với mốc 6 s `unresponsive` của [việc 10](#viec-muc-nham-mat)).
  - Dashboard: **màn hình đội xe trực tiếp** (SSE / polling) cho quản lý: ai đang L3, ai tạm ngưng
    giám sát quá lâu, ai mất camera; có âm báo.
  - Không bắt tài xế thao tác ở L1, và nút đủ to để chạm không cần nhìn.

<a id="viec-trace-that"></a>

### Việc 16: trace số từ chuyến thật (có đồng ý)

- **Vì sao:** không lưu frame nên sau chuyến không có gì để dò ngưỡng; dataset công khai thì ngắn hoặc
  diễn ([việc 1](#viec-holdout)). Trace số (EAR, MAR, góc, blendshape, mức, sự kiện
  theo frame) không chứa ảnh nhưng đủ để `seq_eval --replay` dò ngưỡng.
- **Cách làm:**
  - Tài xế bật đồng ý rõ ràng (tắt mặc định); trace nén gửi cuối chuyến kèm bản tổng kết, hoặc giữ trên
    thiết bị đến khi có mạng.
  - Gắn phản hồi "báo sai", nhãn của người ngồi cạnh ([việc 23](#viec-nhan-demo)), KSS
    nếu có.
  - Có thời hạn lưu và xoá theo yêu cầu; chỉ kỹ sư xem được.
- **Cần quyết định:** landmark 3D chi tiết vẫn có thể là dữ liệu sinh trắc; chỉ lưu các số đã tính (EAR,
  góc…), không lưu 478 điểm.

<a id="viec-an-uong"></a>

### Việc 24: uống nước / ăn khi lái

- YOLOv8n đang chạy đã có lớp COCO `cup` (41) và `bottle` (39): thêm vào vùng tài xế như điện thoại, luật
  riêng ở khối 8 (mức thấp hơn điện thoại, vd. L1 khi ≥ vài giây), ngưỡng trong `thresholds.yaml`.
- Không train. Không có lớp thuốc lá trong COCO, nên hút thuốc ngoài phạm vi.
- Cần clip có nhãn để đo báo sai trước khi bật.

<a id="viec-leo-thang"></a>

### Việc 25: leo thang cảnh báo theo thời gian

- Hiện mỗi luật có một mức cố định. L1 lặp lại nhiều lần trong ít phút (vd. ≥ 3 lần / 10 phút) nghĩa là
  tài xế không nghỉ → nâng lên L2. Cửa sổ và số lần trong `thresholds.yaml`, đặt ở khối 12.
- Test bằng chuỗi cảnh báo giả; không làm tăng báo sai đơn lẻ.

<a id="viec-nhip-sinh-hoc"></a>

### Việc 26: mức mệt theo nhịp sinh học

- Hiện `drowsy_score` nhân 1,2 cho đêm (0–5 h) và 1,2 khi lái ≥ 2 giờ.
- Thay bằng một hệ số liên tục: giờ trong ngày (vùng trũng 2–6 h và 14–16 h) × thời gian lái liên tục.
  Là công thức, không train; tham số trong `thresholds.yaml`.
- Gợi ý nghỉ ở bảng tổng kết (M15) dùng cùng hệ số.
- Cần dữ liệu có giờ thật (chuyến demo) để kiểm tra; dataset hiện có không có giờ trong ngày đúng nghĩa.

<a id="viec-outbox-web"></a>

### Việc 27: hàng đợi offline cho web

- Thiết bị có outbox SQLite; web chỉ giữ trong RAM nên bản tổng kết chưa gửi được thì mất khi rời trang
  (M15 đã báo rõ trên HUD).
- IndexedDB giữ các batch chưa gửi, gửi lại khi mở trang / có mạng, có giới hạn số bản ghi. Chỉ metadata.

<a id="viec-rung"></a>

### Việc 31: rung điện thoại khi cảnh báo (web)

- `navigator.vibrate` theo mức (L1 một nhịp ngắn, L2 hai nhịp, L3 lặp như còi). Không hỗ trợ trên iOS
  Safari; chỉ là kênh phụ cạnh âm thanh.

<a id="viec-suc-may"></a>

### Việc 33: tự điều chỉnh theo sức máy (web)

- FPS tụt dưới mức (vd. < 15 trong vài giây) → giảm độ phân giải đưa vào MediaPipe, giảm tần suất YOLO;
  hồi lại khi dư. Ngưỡng trong `thresholds.yaml`.
- Chạy MediaPipe trong Web Worker để giao diện không giật.
- Đo trên điện thoại tầm trung trước và sau; gộp với [việc 28](#viec-apk).

