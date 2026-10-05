# Hướng cải tiến DriverGuard

Danh sách để chọn mốc tiếp theo, không phải kế hoạch. Theo CLAUDE.md, không mục nào được làm
trước khi có yêu cầu; mục nào được chọn thì thêm thành mốc trong `docs/roadmap.md`.

Cập nhật: 05/10/2026 (xoá sáu việc đã làm: leo thang cảnh báo → M32, nhịp "còn sống" và tổng quan đội xe
→ M33, test hồi quy bằng trace → M34, prototype thời lượng chớp → M35, trang tiêu chí pilot → M36, chính
sách dữ liệu → M37; đánh số lại). Việc làm xong được xoá khỏi file này và ghi vào
[`docs/release-v3.md`](release-v3.md) (trước 05/10: [`docs/release-v2.md`](release-v2.md)); sau mỗi lần
xoá, các việc được đánh số lại liên tục.

Bối cảnh khi xếp: sản phẩm cuối là APK trên hub gắn trên xe (web chỉ để xem thử); chưa có hub, chưa có
CAN thật, chưa có giờ lái thật có nhãn. Phần chi tiết bên dưới theo đúng thứ tự trong bảng.

## Danh sách việc

Bấm tên việc để xuống phần chi tiết. Số thứ tự dùng để gọi tắt khi chọn mốc ("làm việc 1"). Đây chỉ
là đề xuất, bạn quyết định làm việc nào.

### Đo offline, rẻ
Chỉ dùng trace sẵn có, không đổi hành vi.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 1 | [PERCLOS hiện tại không phải P80](#viec-perclos) | Ghi rõ định nghĩa đang dùng (~P50, trộn với CNN); tính `perclos_p80` song song, replay so sánh; chưa đổi ngưỡng |  |

### Dữ liệu và đánh giá
Mốc lớn; mở khoá việc dò ngưỡng và kết luận chỉ tiêu PRD.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 2 | [Ghi số trực tiếp từ camera, đo độ trễ cảnh báo](#viec-prd) | Công cụ ghi trace số + nhãn bấm phím, không quay video; đo time-to-alert p95 (PRD ≤ 3 s); dữ liệu cúi nhìn điện thoại, nhắm thật |  |
| 3 | [Nhìn xuống hay nhắm mắt: phần còn lại](#viec-nhin-xuong) | Cần việc 2. Chốt ngưỡng tạm của M25, thêm `eyeLookDown`, đường CNN, ca EAR rất thấp khi nhìn xuống |  |
| 4 | [Theo dõi hướng mắt](#viec-huong-nhin) | Hướng nhìn từ blendshape `eyeLook*` + mống mắt; làm cùng việc 3 |  |
| 5 | [Tối ưu ngưỡng buồn ngủ trên UTA-RLDD](#viec-toi-uu-nguong) | Mốc dữ liệu lớn (Kaggle Notebook). Gộp: tập kiểm tra giữ riêng theo người, chỉ số theo từng người, tách giai đoạn khởi động, bảng EU DDAW |  |
| 6 | [Tín hiệu tạm: chứng minh rồi mới bật](#viec-ablation) | Cần việc 5. Ablation bỏ từng tín hiệu; chưa chứng minh thì trọng số 0 (chớp chậm, nhướn mày) |  |
| 7 | [Tải thử NTHU-DDD](#viec-tai-dataset) | Tải `train.zip` (HF), xem có video + nhãn; cần cho việc 8 |  |
| 8 | [Phát hiện mắt bị che (kính râm)](#viec-mat-bi-che) | Cần việc 7. Thấy mặt mà lâu không chớp → không tin trạng thái mắt (FMEA dòng 5) |  |

### Tính năng, luật mới
Không thêm model.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 9 | [Tốc độ GPS khi chưa có CAN](#viec-gps) | Tốc độ / đang rẽ từ GPS của hub (app) đến khi đọc được CAN thật |  |
| 10 | [Hoàn thiện FR-6: điểm chất lượng frame](#viec-chat-luong) | Ảnh mờ, góc xấu, lóa, che camera → `unavailable` có lý do |  |
| 11 | [Cảnh báo cần xác nhận, báo quản lý ngay](#viec-xac-nhan) | "Bạn còn ở đó không?", nhắm ≥ 6 s → `unresponsive`, màn hình đội xe trực tiếp; cẩn thận việc bắt chạm màn hình khi lái |  |

<a id="viec-phan-cung"></a>

### Sau khi chọn hub và camera
Cần chốt loại hub (CPU, RAM, hệ điều hành), camera (IR hay RGB) và nguồn tín hiệu xe (CAN thật).

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 12 | [Đo tài nguyên phần cứng](#viec-do-phan-cung) | Phần máy dev làm được ngay; phần hub chờ chọn hub. CPU, RAM, nhiệt độ, FPS khi chạy lâu |  |
| 13 | [Đóng gói app APK](#viec-apk) | Sản phẩm cuối: bọc code web (Capacitor), chạy offline trên hub; cần kết quả việc 12 |  |
| 14 | [Hàng đợi offline cho app](#viec-outbox-web) | Hub mất mạng: lưu sự kiện / tổng kết trong bộ nhớ của app, gửi lại khi có mạng; làm cùng việc 13 |  |
| 15 | [Thử model mắt mới](#viec-model-mat) | `blinkcnn` / OCEC offline; quan trọng nếu hub dùng camera IR |  |
| 16 | [Tăng tương phản (app / web)](#viec-choi) | WebGL; chỉ cần nếu hub dùng camera RGB |  |

### Không gấp: để cuối

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 17 | [So sánh nhiều chuyến của tài xế](#viec-nhieu-chuyen) | So với 5 chuyến gần nhất; cần nhiều chuyến thật |  |
| 18 | [Ghi nhãn trực tiếp khi demo](#viec-nhan-demo) | Người ngồi cạnh ghi đúng / sai / bỏ sót, KSS mỗi 5 phút; cách duy nhất kết luận PRD ≤ 1,0 báo sai / giờ |  |
| 19 | [Phần PRD còn lại](#viec-prd-con-lai) | Quyết định LLM (FR-12/13); phiên bản cấu hình trên sự kiện; test 10 người; nộp bài; Docker edge gần như lỗi thời |  |

### Từ so sánh với nhóm P-196 (03/10)
Nhóm P-196 làm cùng đề tài (YuNet + CNN mắt trên Raspberry Pi 4, còi / LED qua ESP32, dashboard đội
xe). Các việc dưới đây là phần họ có mà DriverGuard chưa có. Việc 20 và 22 phục vụ nộp bài nên gấp
hơn vị trí trong bảng; việc 21 cần chọn hub trước.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 20 | [Pitch deck và video demo](#viec-pitch) | Deliverable 6, 7 còn thiếu. Khung: vấn đề có nguồn → 3 rào cản → giải pháp → người dùng → tính năng → kiến trúc → kết quả đo → giới hạn → lộ trình |  |
| 21 | [Kênh cảnh báo vật lý](#viec-coi-roi) | Còi / LED rời, kêu được khi màn hình hoặc âm thanh của app không hoạt động; cần chọn hub |  |
| 22 | [Tài khoản demo theo vai trò](#viec-tk-demo) | Tài khoản chỉ đọc cho người chấm trên bản deploy, có dữ liệu mẫu |  |

### Từ đo dung lượng tải lần đầu (03/10)
Không cần hub. Mục 1 và 3 của việc này nhỏ, làm được ngay; mục 2 lớn hơn.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 23 | [Tối ưu dung lượng tải lần đầu](#viec-dung-luong) | Hiện ~70 MB (~42 MB qua mạng). YOLO INT8, bỏ OpenCV khỏi bản web, bật nén và cache trên server → còn ~22 MB qua mạng |  |

### Hoãn
Chưa đủ dữ liệu hoặc lý do để làm; xem lại khi có chuyến thật. Lý do ở [phần hoãn](#phan-hoan).

| Task | Vì sao hoãn |
|---|---|
| [Mức mệt theo nhịp sinh học](#viec-nhip-sinh-hoc) | Không có dữ liệu giờ thật để kiểm chứng; thêm tham số chưa chứng minh |
| [Vùng nhìn hợp lệ, nhận mặt bằng model](#dang-ky-buoc-c) | Chưa có bằng chứng chữ ký mặt không đủ; đăng ký sẽ lâu hơn |
| [Trace số từ chuyến thật](#viec-trace-that) | Chưa có chuyến thật; vướng quyền riêng tư |

### Đã bỏ
Lý do ở [phụ lục H](#phu-luc-h): bật lại `blink_rate` theo phân vị tài xế; thêm `duration_ratio` (thời
lượng chớp so với chính tài xế: prototype M35 không tách được drowsy / alert và trùng với `reopen_ratio`,
xem [`eval/results/blink_duration_fl3d.md`](../eval/results/blink_duration_fl3d.md)); giảm xử lý từng frame; đọc
thành tiếng cảnh báo; uống nước / ăn khi lái; Brain4Cars; hai model sóng não + mặt; (trong
`docs/release-v2.md`) chống chói bằng phần mềm, bám tài xế riêng, rung điện thoại, tự điều chỉnh theo
sức máy cho web.

---

## Chi tiết từng việc

<a id="viec-perclos"></a>

### Việc 1: PERCLOS hiện tại không phải P80

Abe 2023 [P1] (tổng quan về PERCLOS) khuyến nghị đầu tiên: *"standardization to minimize differences
in the definition of PERCLOS between studies"*. Định nghĩa gốc P80: phần trăm thời gian mắt nhắm hơn
80 %, tức mí mắt mở dưới 20 % (0 % = nhắm hẳn).

**Hiện trạng:** `perclos_60s` không phải P80, và trộn hai định nghĩa "nhắm" trong cùng cửa sổ 60 s
([analyzer.py:152-156](../edge_agent/analysis/drowsiness/analyzer.py#L152-L156)):
- Frame dùng EAR: nhắm khi `EAR < perclos_close_ratio (0,65) × mốc mắt mở`.
- Frame có CNN (khối 5 chạy vì EAR không tin được): nhắm khi `p_closed ≥ eye.cnn_closed (0,6)`. Đây
  là xác suất, không phải độ mở mí, nên không đổi được sang P80.

Phần frame do CNN quyết định không nhỏ (đo trên trace 02/10):

| Trace | Frame do CNN quyết định | Cao nhất trong một video |
|---|---:|---:|
| FL3D | 8,9 % | 26 % |
| SUST | 7,6 % | 100 % |

**Quy đổi sang độ mở mắt** (thang 0 = mắt nhắm .. 1 = mốc mắt mở, như `slow_blink.py`; chưa đăng ký thì
mức nhắm = `blink_closed_ref_ratio` 0,35 × mốc):
- P80 = độ mở < 0,2 ≈ **EAR < 0,48 × mốc** (0,35 + 0,2 × 0,65). Không phải "EAR < 0,2 × mốc" như ghi
  trước đây: nhắm mắt thì EAR không về 0.
- Ngưỡng hiện tại 0,65 × mốc = độ mở ~46 %, gần với **"P50"**: nhạy hơn P80 nhiều, dễ tính cả nheo mắt.

**Hệ quả:** trên cùng một đoạn, PERCLOS kiểu P50 cao hơn P80. Nếu `perclos_drowsy: 0.15` và
`risk.drowsy.perclos_low / perclos_high: 0.05 / 0.20` lấy từ tài liệu dùng P80 thì hệ thống đang nhạy
hơn mức tài liệu hàm ý, dễ báo sai hơn. Chưa ghi nguồn của các ngưỡng này; cần ghi.

**Literature cũng không thống nhất:** Abe liệt kê các biến thể mí mở < 25 % hoặc < 30 %, nhắm = không
thấy đồng tử, EAR dưới một ngưỡng, có / không bỏ chớp nhanh (< 250, < 400, < 500 ms), tần số mẫu
2–120 Hz. Abe cũng viết *"no single index is currently available as an optimal marker for detecting
drowsiness"* và không đưa ngưỡng PERCLOS đã kiểm chứng. "So với P80" nghĩa là so cùng định nghĩa,
không phải so với một ngưỡng chuẩn.

**Việc cần làm:**
1. **Ghi rõ định nghĩa** trong comment `thresholds.yaml` (cạnh `perclos_close_ratio`) và tài liệu:
   PERCLOS hiện tại là biến thể ~P50, trộn CNN, không phải P80; ghi nguồn của các ngưỡng PERCLOS.
2. **Tính `perclos_p80` song song**, chỉ ghi vào trace / metadata, không vào `drowsy_score`:
   - frame nhắm khi độ mở < 0,2 (ngưỡng trong `thresholds.yaml`);
   - chỉ frame EAR; frame CNN coi là không biết, báo độ phủ riêng;
   - không bỏ chớp nhanh (đúng định nghĩa gốc); thêm một biến thể bỏ chớp < 500 ms để so.
3. **Replay FL3D / YawDD / SUST:** so P80 với định nghĩa hiện tại về khả năng tách drowsy / alert và
   báo sai / giờ. Chưa đổi ngưỡng.
4. Nếu chuyển sang P80 thì dò lại `perclos_drowsy`, `perclos_low / perclos_high` cùng
   [việc 5](#viec-toi-uu-nguong).

Không thêm model, logic theo thời gian test được bằng chuỗi số giả.

#### Nguồn

- [P1] Abe T. PERCLOS-based technologies for detecting drowsiness: current evidence and future
  directions. SLEEP Advances 2023;4(1):zpad006. https://doi.org/10.1093/sleepadvances/zpad006
  (PMC10108649)

---

<a id="viec-prd"></a>

### Việc 2: ghi số trực tiếp từ camera, đo độ trễ cảnh báo

**Vì sao:** mọi con số hiện tại từ dataset công khai (clip ngắn hoặc diễn). Thiếu dữ liệu cho: cúi nhìn
điện thoại / bảng đồng hồ ([việc 3](#viec-nhin-xuong)), phép thử gục / cúi của M12 (đang tắt), các
điều kiện sáng / tối / kính / ngược sáng ([phụ lục C](#phu-luc-c)), và chỉ tiêu PRD **time-to-alert p95
≤ 3 s** (chưa có công cụ đo).

**Ràng buộc:** CLAUDE.md cấm ghi frame ra đĩa, nên **không quay video**. Công cụ ghi số trực tiếp từ
camera: mỗi frame chỉ lưu các số đã tính (EAR, MAR, góc đầu, eyeBlink, eyeLookDown, mức, sự kiện), giống
trace của `tools/seq_eval.py`, kèm **nhãn bấm phím** (vd. "bắt đầu nhắm", "mở mắt", "cúi nhìn điện thoại",
"nhìn bảng đồng hồ").

**Cách làm:**
- Công cụ `tools/record_trace.py` (hoặc chế độ mới của `seq_eval trace` đọc từ camera): ghi trace + nhãn,
  không ghi ảnh.
- Kịch bản tự ghi, vài phút mỗi cảnh: lái giả tỉnh táo, cúi nhìn điện thoại / bảng đồng hồ, nhắm mắt
  (giả ngủ) có / không gục đầu, ngáp, nói chuyện; đeo kính / không; sáng / tối.
- Time-to-alert = thời điểm cảnh báo − thời điểm bấm "bắt đầu"; báo p50 / p95 theo loại.
- Dùng trace này với `seq_eval --replay --set` để chọn ngưỡng (việc 3).
- Chỉ là dữ liệu của team (vài người, diễn): làm tập dev, không thay được UTA-RLDD / DMD.

---

<a id="viec-nhin-xuong"></a>

### Việc 3: nhìn xuống hay nhắm mắt: phần còn lại sau M25

**Đã làm ở M25** (`docs/release-v2.md`): cúi nhìn điện thoại / bảng đồng hồ làm mí trên hạ theo (EAR ~0,5
lần mốc, eyeBlink ~0,6) nên bị báo L3 "Mở mắt!". Nay:
- đầu cúi ≥ `microsleep_deep.bowed_pitch_deg` (10°) so với tư thế quen: frame nhắm sâu cần EAR ≤
  `bowed_ear_ratio` (0,35) lần mốc;
- chỉ "mang theo khi gục" nếu lần nhắm trước đó là nhắm sâu;
- mí hạ mà chưa nhắm chặt khi đầu cúi (`gaze_down`) tính là nhìn khỏi đường (L2 "Nhìn về phía trước").

Hai ngưỡng là **tạm**: chưa dataset nào có cảnh nhìn điện thoại khi lái. Việc có thể làm sau:

1. **Tự ghi số để chốt ngưỡng** (gộp với [việc 2](#viec-prd)): vài phút mỗi cảnh, chỉ ghi số
   (EAR, pitch, eyeBlink, eyeLookDown, nhãn bấm phím), không ghi ảnh:
   - nhìn điện thoại trên đùi, trên giá đỡ thấp, nhìn bảng đồng hồ, nhìn cần số;
   - cúi kèm nhắm mắt thật (giả ngủ), gục chậm;
   - đeo kính / không, ngày / đêm.
   Đo phân bố EAR / mốc khi nhìn xuống so với khi nhắm, rồi chọn `bowed_pitch_deg` /
   `bowed_ear_ratio` bằng `seq_eval --replay --set`.
2. **Blendshape `eyeLookDownLeft/Right`** (cùng model MediaPipe, không tốn thêm): thêm vào đặc trưng và
   trace. Nếu nó cao khi nhìn xuống mà thấp khi nhắm thật thì dùng làm tín hiệu chính thay ngưỡng EAR
   (cùng hướng với [việc 4](#viec-huong-nhin)). *Chưa kiểm chứng*: MediaPipe có thể cũng báo "nhìn
   xuống" khi mắt nhắm.
3. **Ca EAR rất thấp khi nhìn xuống:** SUST `n_368` (đầu cúi 17°, EAR 0,26 lần mốc, eyeBlink 0,7) vẫn lọt
   ngưỡng 0,35. Ngưỡng EAR không đủ cho ca này; cần tín hiệu hướng nhìn ở mục 2, hoặc mống mắt.
4. **Đường CNN:** frame do CNN mắt quyết định (tối, IR, hai mắt lệch) chưa có quy tắc "đầu cúi"; chưa đo
   `p_closed` khi nhìn xuống.
5. **Mặt trái của `gaze_down`:** tài xế buồn ngủ mắt lim dim, đầu gục nhẹ có thể nhận L2 "Nhìn về phía
   trước" thay vì cảnh báo buồn ngủ (vẫn có cảnh báo; PERCLOS vẫn tính). Đo trên UTA-RLDD
   ([việc 5](#viec-toi-uu-nguong)).
6. **Phép thử tốc độ gục / cúi của M12** (đang tắt vì dataset không có cảnh cúi): dữ liệu ở mục 1 cho
   phép thử lại.
7. Đưa hai ngưỡng mới lên tab "Ngưỡng" của dashboard để kỹ sư chỉnh từ xa.

---

<a id="viec-huong-nhin"></a>

### Việc 4: theo dõi hướng mắt

Làm cùng lúc với mục 2 của [việc 3](#viec-nhin-xuong) (cùng blendshape `eyeLook*`).

#### Hiện tại
- Khối 8 (`distraction.py`) chỉ dùng **góc đầu** so với mốc "nhìn đường" của tài xế: lệch yaw > 30°,
  cúi > 20°, ngẩng > 25° liên tục ≥ 2 s (≥ 1,5 s khi tốc độ cao) → L2 `off_road`.
- Điện thoại xử lý riêng qua YOLO: điện thoại trong vùng tài xế ≥ 60% thời gian trong 2 s → L2 `phone`.
- Không dùng hướng nhìn của mắt ở đâu cả.

#### Chưa phát hiện được
- Đầu thẳng, **mắt liếc xuống** điện thoại trên đùi / giá đỡ thấp: góc đầu không đổi, và điện thoại
  trên đùi có thể nằm dưới vùng tài xế (chỉ kéo xuống 1,5 × chiều cao mặt) nên YOLO cũng không tính.
- Đầu thẳng, **mắt liếc sang bên** (màn hình giải trí, hành khách) quá lâu.
- ~~Mắt nhìn xuống làm mí trên hạ theo → EAR giảm → bị hiểu là nhắm mắt~~: đã tái hiện và chặn một phần
  ở M25 (đầu cúi ≥ 10° cần EAR ≤ 0,35 lần mốc mới là nhắm sâu; mí hạ mà chưa nhắm chặt tính là nhìn
  khỏi đường). Phần còn lại ở [việc 3](#viec-nhin-xuong).
- Nhìn thẳng nhưng "mất hồn": ngoài khả năng của camera, không nằm trong hướng này.

#### Hướng đề xuất (không thêm model)
- **Blendshape hướng nhìn** MediaPipe đã xuất sẵn nhưng chưa lấy: `eyeLookDown/Up/In/Out` mỗi mắt.
  Lấy thêm không tốn thời gian, chạy được cả trên web.
- **10 điểm mống mắt** (landmark 468–477): vị trí mống mắt so với hai khoé mắt cho độ lệch của mắt.
- Tính **hướng nhìn = góc đầu + độ lệch mắt**, dùng làm tín hiệu bổ sung cho `off_road` với ngưỡng
  riêng trong `thresholds.yaml`; giữ góc đầu làm tín hiệu chính.
- Mốc hướng nhìn theo từng tài xế / từng vùng (đường, gương, bảng đồng hồ) lấy từ bước đăng ký (M9:
  bước nhìn đường; phần hoãn "vùng nhìn hợp lệ") thay vì một ngưỡng chung.
- Dùng cùng tín hiệu để nhánh buồn ngủ phân biệt **"mắt nhìn xuống"** với **"mắt nhắm"** (xem
  [việc 3](#viec-nhin-xuong)).
- Rủi ro: ước lượng mắt kém khi IR / đeo kính → cần tắt hoặc giảm tin cậy trong các trường hợp đó
  (nối với trigger của khối 5 ở phụ lục C, D).
- Test bằng chuỗi số giả (góc đầu + độ lệch mắt theo thời gian); cần thêm clip có nhãn "liếc điện
  thoại, đầu thẳng" để đo báo sai (gộp với clip tự quay ở việc 3).

---

<a id="viec-toi-uu-nguong"></a>

### Việc 5: tối ưu ngưỡng buồn ngủ trên UTA-RLDD

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
- Báo thêm một bảng theo khung EU DDAW ([phụ lục E](#viec-ddaw)): video `10` ≈ KSS ≥ 8. Chỉ là xấp xỉ
  (một nhãn cho cả video, không có KSS mỗi 5 phút), không dùng để chọn ngưỡng.
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

#### Tập kiểm tra giữ riêng theo người (gộp vào việc này, 02/10)

<a id="viec-holdout"></a>

**Vấn đề:** chưa kiểm chứng trên lái xe thật, và cách đo hiện tại lạc quan.
- Mọi con số từ clip ngắn hoặc diễn; số giờ lái thật có nhãn bằng 0. FAR / MAR không đọc được trên
  dataset hiện có ([M18](#viec-far-mar)); chỉ tiêu PRD ≤ 1,0 / giờ chưa chứng minh được.
- **Lỗi phương pháp:** ngưỡng được chỉnh trên YawDD, FL3D, SUST (comment trong `thresholds.yaml`), rồi
  kết quả báo trên chính các bộ đó. Như vừa ra đề vừa tự chấm: số báo cáo cao hơn số thật.

**Hướng làm:**
- Trước khi dò ngưỡng tiếp ([việc 5](#viec-toi-uu-nguong)), chốt **tập kiểm tra theo người**: một
  phần người của mỗi dataset (theo mã người; thiếu mã thì theo video), ghi danh sách vào repo
  (`eval/splits/*.txt`), không dùng khi dò.
- Công cụ eval nhận `--split dev|test`. Mọi bảng ghi rõ split. Số trên `test` chỉ chạy khi chốt một bộ
  ngưỡng, không chạy lặp đi lặp lại.
- Các bộ đã dùng để chỉnh (YawDD, FL3D, SUST) ghi rõ là "dev". Số "test" đầu tiên đúng nghĩa sẽ là
  UTA-RLDD / DMD theo người.
- Dữ liệu lái thật: [việc 2](#viec-prd) (clip tự quay), [việc 18](#viec-nhan-demo) (ghi nhãn khi
  demo). Không có hai việc này thì không kết luận được về chỉ tiêu PRD.

<a id="viec-theo-nguoi"></a>

#### Chỉ số đánh giá theo từng người (gộp vào việc này, 02/10)

**Hiện tại:** `tools/eval.py` và `seq_eval` gộp mọi video thành một con số. Con số trung bình có thể
che mất một nhóm người bị báo sai nhiều (đeo kính, mắt nhỏ, hay ngáp, ngồi lệch camera). Ngưỡng đang
dùng chung cho mọi người; chỉ có mốc mắt / miệng / tư thế là riêng từng tài xế (đăng ký M9).

**Chỉ số nào cho từng người:** theo [phụ lục A](#viec-far-mar), trên dataset dùng **FAR / MAR theo cửa
sổ** làm chính: 10 phút tỉnh táo vẫn có ~60 cửa sổ, trong khi báo sai / giờ của một người trên 10 phút
gần như vô nghĩa (xem CI bên dưới). Báo sai / giờ theo từng người chỉ kết luận được trên giờ lái thật
có nhãn ([việc 18](#viec-nhan-demo)).

#### Đánh giá trên dataset (offline)

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
- Khi dò ngưỡng ([việc 5](#viec-toi-uu-nguong)): thêm điều kiện "không người nào trong fold kiểm tra
  tệ hơn rõ rệt", không chỉ nhìn trung bình.

#### Khi chạy thật (online)

- **Không tính được FAR / MAR đúng nghĩa:** ngoài đường không có nhãn. Lần bỏ sót thì không ai thấy
  (không có cảnh báo để bấm), nên MAR theo từng tài xế không đo được. Muốn có số đúng thì phải là
  chuyến demo có người ghi nhãn ([việc 18](#viec-nhan-demo)).
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

<a id="viec-do-bao-sai"></a>

#### Tách giai đoạn khởi động, đường đánh đổi (gộp vào việc này, 02/10)

1. **Tách giai đoạn khởi động** (30 s đầu mỗi clip) khỏi số **báo sai / giờ**, báo cáo riêng. FAR / MAR
   theo cửa sổ đã bỏ 30 s này (M18).
2. **Đường đánh đổi** FAR ↔ MAR (và cảnh báo sai / giờ ↔ tỉ lệ bắt sự kiện) khi đổi ngưỡng, dùng
   `tools/seq_eval.py --replay` (khối 7–12, không cần chạy lại MediaPipe) để thấy ngưỡng hiện tại đứng
   ở đâu thay vì một điểm duy nhất.
3. **Dữ liệu dài, liên tục:** chuyến demo có người ghi nhãn ([việc 18](#viec-nhan-demo)); clip tự quay
   ở việc 3. Dataset đã kiểm tra (phụ lục B): **UTA-RLDD** cho cảnh báo sai / giờ, **DMD** cho recall theo
   frame và time-to-alert; hai bộ bổ sung cho nhau.

---

<a id="viec-ablation"></a>

### Việc 6: tín hiệu tạm phải chứng minh rồi mới bật

Cần [việc 5](#viec-toi-uu-nguong) (UTA-RLDD) cho phần ablation. Riêng nguyên tắc "chưa chứng minh thì trọng số 0" áp ngay được (chớp chậm, nhướn mày về 0), nhưng là đổi hành vi: cần quyết định.

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

---

<a id="viec-tai-dataset"></a>

### Việc 7: tải thử NTHU-DDD

1. Đăng ký HF, tải `train.zip` NTHU-DDD, xem có video AVI + nhãn không; không có thì email xin gốc.
2. Cần cho [việc 8](#viec-mat-bi-che) (bối cảnh `Sunglasses`), video IR cả khuôn mặt và gục đầu có nhãn.
   Mô tả dataset ở [phụ lục B](#phu-luc-b).
- Bỏ phần Brain4Cars (02/10): clip 5 s ngắn hơn giai đoạn hiệu chỉnh mốc tư thế đầu, không có xi nhan.

---

<a id="viec-mat-bi-che"></a>

### Việc 8: phát hiện mắt bị che (kính râm)

- **Vì sao (FMEA dòng 5, chưa kiểm chứng):** MediaPipe vẫn trả landmark mắt khi đeo kính râm. CNN mắt
  chỉ chạy khi tối / IR / hai mắt lệch, nên EAR "đoán" có thể luôn là mở: PERCLOS, microsleep, chớp chậm
  đều im mà hệ thống không biết.
- **Cách làm (chưa thử):**
  - Đo trước: chạy NTHU-DDD bối cảnh `Sunglasses` ([việc 7](#viec-tai-dataset)) xem EAR / eyeBlink có
    đổi khi nhắm không.
  - Nếu đúng là "luôn mở": thấy mặt mà không có lần chớp nào trong một khoảng dài (vd. 30 s, trong
    `thresholds.yaml`) → không tin trạng thái mắt, HUD báo "không đọc được mắt", tách khỏi "tạm ngưng
    giám sát" vì nhánh mất tập trung vẫn chạy.
  - Hoặc model SGC (PINTO0309, MIT, 48×48) phân loại kính râm ([việc 15](#viec-model-mat)).

---

<a id="viec-gps"></a>

### Việc 9: tốc độ GPS khi chưa có CAN

- **Vì sao:** app (và bản web xem thử) chưa đọc CAN thật ([phần cứng thật](#viec-phan-cung)); từ M19 tốc độ / xi nhan lấy từ công cụ mô phỏng `tools/drive_sim.py`
  (người ngồi bấm), nên luật ngữ cảnh (đèn đỏ, cao tốc, nghỉ) không phản ánh đường thật. Báo sai chính
  đang là `off_road` khi quay đầu thật (24/26 trên SUST); xi nhan đã nới đúng phía (M20) nhưng trên
  đường thật không ai bấm xi nhan giả.
- **Cách làm:**
  - Nguồn tín hiệu xe mới cho khối 10: tốc độ từ `navigator.geolocation` (`coords.speed`; trong APK
    là GPS của hub), làm mượt vài giây; mất GPS thì quay về công cụ mô phỏng (chế độ hiện tại). Khi đọc
    được CAN thật thì CAN là nguồn chính, GPS chỉ dự phòng.
  - **Đang rẽ:** hướng GPS (`coords.heading`) đổi nhanh hơn một ngưỡng (°/s, trong `thresholds.yaml`)
    thì coi như xi-nhan bật về phía đang rẽ, dùng lại `turn_side` / `turn_signal_grace_s` của khối 10.
  - Chỉ gửi số lên Python; không lưu vị trí, không gửi toạ độ lên backend (chỉ tốc độ như hiện tại).
  - Test bằng chuỗi tốc độ / hướng giả.
- **Rủi ro:** GPS điện thoại trễ 1–2 s và nhiễu khi chạy chậm; trong hầm thì mất.

---

<a id="viec-chat-luong"></a>

### Việc 10: hoàn thiện FR-6, điểm chất lượng frame

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
  - Nối với [bảng FMEA](safety-fmea.md) (dòng 7, 8).

---

<a id="viec-xac-nhan"></a>

### Việc 11: cảnh báo cần xác nhận, báo quản lý ngay

- **Vì sao:** quản lý hiện chỉ thấy báo cáo sau chuyến (M15). Tài xế ngủ gật lặp lại mà không phản ứng
  thì không ai biết lúc đó.
- **Cách làm:**
  - L2 / L3: tài xế xác nhận bằng một chạm to trên HUD (hoặc nói "tôi ổn" nếu trình duyệt hỗ trợ nhận
    giọng nói); có thời hạn trong `thresholds.yaml`.
  - Không xác nhận, hoặc L3 lặp lại trong ít phút → sự kiện `driver_unresponsive` lên backend ngay
    (cùng sự kiện với mốc nhắm mắt 6 s ở cuối việc này).
  - Dashboard: **màn hình đội xe trực tiếp** (SSE / polling) cho quản lý, dựng trên tab "Đội xe" và nhịp
    "còn sống" đã có từ M33 ([release-v3.md](release-v3.md)): ai đang L3, ai không trả lời
    "Bạn còn ở đó không?" ([FMEA dòng 6](safety-fmea.md#6-guc-ra-khoi-khung)); có âm báo. Tạm ngưng giám
    sát và mất camera thì không báo theo thời gian thực (chốt 02/10: mất camera quản lý xem ở bản tổng
    kết).
  - **"Bạn còn ở đó không?"** khi tài xế gục ra khỏi khung mà trước đó không thấy mắt nhắm (chốt 02/10);
    quá hạn không trả lời thì báo quản lý. Còn cần chọn: hỏi sau bao lâu mất mặt, chờ trả lời bao lâu
    (ngưỡng trong `thresholds.yaml`).
  - Không bắt tài xế thao tác ở L1, và nút đủ to để chạm không cần nhìn.
- **Gộp từ việc "cảnh báo theo độ dài nhắm mắt" (02/10):** mắt nhắm liên tục ≥ 6 s (`closed_duration`,
  ngưỡng trong `thresholds.yaml`) → sự kiện `unresponsive` lên backend ngay. Mốc 3 s gần như đã có (còi
  L3 lặp mỗi 1,5 s khi mắt còn nhắm). Không làm "giảm tốc qua CAN": hệ thống chỉ đọc CAN, không điều
  khiển xe.
- **Lưu ý:** bắt tài xế chạm màn hình khi đang lái cũng là mất tập trung. Cân nhắc chỉ hỏi xác nhận cho
  "Bạn còn ở đó không?" và sau L3, nút thật to; hoặc xác nhận bằng hành động không cần nhìn (vd. mở mắt
  nhìn thẳng camera vài giây).

---

<a id="viec-do-phan-cung"></a>

### Việc 12: đo tài nguyên phần cứng

**Hiện tại:**
- `tools/benchmark.py` (M7) chỉ đo FPS, độ trễ p50 / p95 từng khối, kích thước model. Chạy ngắn (vài
  trăm frame), trên máy Mac ARM của team (146 FPS với video YawDD).
- **Chưa đo** CPU, RAM, nhiệt độ; chưa chạy dài; chưa đo trên thiết bị gắn trên xe. PRD FR-18 / NFR-2
  yêu cầu có số CPU / RAM, gắn nhãn `simulated`.
- Số 146 FPS trên Mac không nói được gì về hub trên xe: máy yếu hơn, trong cabin nóng, chạy liên tục
  cả chuyến.

**Cần đo, trên hai nơi:**
- **Hub gắn trên xe**, chạy APK ([việc 13](#viec-apk)): thiết bị đích; *loại máy chưa chốt*.
- **Máy chạy project** (máy dev / laptop demo): làm mốc so sánh, và để biết bản `simulated` hiện tại
  đang chiếm bao nhiêu tài nguyên.

| Chỉ số | Vì sao | Cách đo (đề xuất) |
|---|---|---|
| CPU % (cả tiến trình và từng luồng: vòng chính, YOLO) | Còn dư bao nhiêu cho app khác trên hub (bản đồ, camera lùi…) | `psutil` lấy mẫu mỗi giây |
| RAM (RSS, đỉnh, có tăng dần theo thời gian không) | Bắt rò rỉ bộ nhớ khi chạy nhiều giờ; frame chỉ nằm trong RAM nên phải chắc không bị giữ lại | `psutil` |
| Nhiệt độ CPU / SoC | Máy nóng → tự hạ xung → FPS tụt dưới 15 giữa chuyến | Cảm biến của hệ điều hành (Linux: `/sys/class/thermal`; macOS cần công cụ riêng) |
| FPS và độ trễ theo thời gian | Thấy FPS tụt khi máy nóng, không chỉ con số trung bình | Đã có trong `benchmark.py`, thêm ghi theo từng phút |
| Điện năng của hub | APK chạy cả chuyến, cấp điện từ xe | Công cụ của Android |

**Hướng đề xuất:**
- Thêm chế độ chạy dài vào `tools/benchmark.py` (vd. `--duration 60m`): chạy vòng chính 2–12 như
  `edge_agent.main`, ghi CPU / RAM / nhiệt / FPS mỗi giây, báo cáo p50 / p95 / đỉnh và biểu đồ theo
  thời gian. Chỉ ghi số, không ghi frame.
- Chạy ở ba điều kiện: không có mặt, có mặt, có mặt + điện thoại (YOLO làm việc nhiều nhất).
- Mỗi bảng ghi rõ máy, hệ điều hành, số luồng, có giới hạn CPU không (`simulated` hay máy thật).
- Ngưỡng đạt nằm trong `thresholds.yaml` hoặc báo cáo: ≥ 15 FPS suốt cả lần chạy (CLAUDE.md), RAM
  không tăng dần, không bị hạ xung.
- Hub được chọn để đạt ≥ 15 FPS, không thiết kế để chạy trên máy yếu. Nếu hub vẫn tụt (nóng, hạ xung):
  hạ tải theo thứ tự, hồi lại theo thứ tự ngược khi dư, ngưỡng trong `thresholds.yaml`. Mỗi thay đổi
  phải đo lại độ chính xác.
  1. YOLO INT8 (đã có), giảm tần suất YOLO (`features.target_fps`);
  2. giảm độ phân giải đưa vào MediaPipe;
  3. **không bỏ frame MediaPipe**: hạ hết mà vẫn < 15 FPS thì báo `unavailable` (FR-6), không chạy tiếp
     với ít frame hơn (lý do ở [đã bỏ bên dưới](#bo-subsampling)).
- Chạy MediaPipe trong Web Worker để giao diện app không giật (app bọc code web).

**Tham khảo (03/10):** nhóm P-196 chạy pipeline nhẹ hơn (YuNet + CNN mắt 64×64 + solvePnP, không
MediaPipe, không YOLO) trên Raspberry Pi 4 với camera thật: 10,5–12,76 FPS, 141–216 ms / frame, riêng
dò mặt 119–182 ms, CNN mắt 1,23–2,44 ms. Số của họ, không phải số đo của DriverGuard, nhưng cho thấy
máy cỡ Pi 4 khó đạt 15 FPS với pipeline hiện tại; nên có bảng phân rã độ trễ từng khối như vậy trên hub.

**Cần có trước khi đo trên xe:** chốt loại hub (CPU, RAM, hệ điều hành) và cách mang project lên đó
(APK ở [việc 13](#viec-apk)). Phần đo trên máy dev thì làm được ngay.

---

<a id="viec-apk"></a>

### Việc 13: đóng gói app APK

**Hiện tại:** chỉ có bản web (React + MediaPipe tasks-vision + onnxruntime-web + khối 5–12 bằng
Python qua Pyodide), mở bằng trình duyệt. Lần đầu mỗi máy phải tải khoảng 60 MB (Python, OpenCV, MediaPipe, ONNX Runtime, model); số đo từng file ở [việc 23](#viec-dung-luong).

**Đã chốt (02/10):** APK là sản phẩm cuối, chạy trên hub gắn trên xe. Bản web chỉ để xem thử app hoạt
động và giao diện trước.

**Hướng đề xuất:** gói chính bản web vào một app WebView (vd. Capacitor), không viết lại.
- Đưa sẵn Pyodide, `edge_agent.zip`, `face_landmarker.task`, `yolov8n.onnx` vào APK: mở app là chạy
  ngay, không cần mạng để giám sát. Mạng chỉ dùng để gửi metadata JSON lên backend (đúng CLAUDE.md).
- Giữ một bộ code cho cả web và app; `npm run build` rồi đồng bộ sang project Android.
- Việc riêng của app: xin quyền camera, giữ màn hình sáng, chạy ở chế độ kiosk trên hub (app luôn ở
  trước, không bị chuyển sang nền), hướng màn hình theo hub, địa chỉ backend trong phần cài đặt.
- Đầu mỗi chuyến nhắc tài xế kiểm tra camera (thấy mặt rõ) trước khi chạy ([FMEA dòng 8](safety-fmea.md#8-mat-camera)).
- Cho WebView phát âm thanh không cần chạm (Capacitor / Android WebView, *chưa kiểm chứng*), để âm thanh
  cảnh báo chạy ngay khi app mở; M23 mới làm phần web (bật ở lần chạm đầu, dải nhắc khi còn bị chặn).
- Không chọn: viết lại native (Kotlin + MediaPipe Android + ONNX Runtime Mobile) vì phải chuyển toàn
  bộ logic khối 5–12 từ Python sang Kotlin và giữ hai bản đồng bộ. Cũng không chọn TWA (bọc trang web
  đang host), vì vẫn cần mạng để mở app.

**Rủi ro / cần đo:**
- *(chưa kiểm chứng)* WASM + WebGL trong WebView Android có đạt ≥ 15 FPS trên hub không. Phải đo trên
  hub thật trước khi làm tiếp ([việc 12](#viec-do-phan-cung)), và chọn hub theo kết quả đó.
- Nóng máy khi chạy camera + model liên tục cả chuyến trong cabin.
- Khi app chạy nền hoặc tắt màn hình, Android có thể dừng camera → phải báo "tạm ngưng giám sát",
  không được im lặng (dùng lại trạng thái `unavailable` / sự kiện `monitoring_unavailable` của M10).
- APK nặng thêm ~40–50 MB vì chứa sẵn Python và model (*ước lượng*).
- Phát tán APK có YOLO là phân phối phần mềm AGPL: phải kèm mã nguồn (xem License YOLO ở
  [phụ lục F](#quyet-dinh)).

---

<a id="viec-outbox-web"></a>

### Việc 14: hàng đợi offline cho app

- Bản Python trên thiết bị có outbox SQLite; code web (cũng là code của APK) chỉ giữ trong RAM, nên hub
  mất mạng giữa chuyến rồi app bị tắt thì sự kiện / bản tổng kết chưa gửi được bị mất (M15 đã báo rõ
  trên HUD).
- Lưu các batch chưa gửi trong bộ nhớ của app (IndexedDB trong WebView, hoặc plugin lưu trữ của
  Capacitor), gửi lại khi mở app / có mạng, có giới hạn số bản ghi. Chỉ metadata.
- Làm cùng [việc 13](#viec-apk).

---

<a id="viec-model-mat"></a>

### Việc 15: thử model mắt mới

- **Ưu tiên phụ thuộc camera của hub:** camera IR thì CNN mắt chạy cả chuyến (khối 5 gọi CNN khi IR) và
  việc này quan trọng; camera RGB thì eyeBlink đã AUC 0,986, CNN chỉ là dự phòng, giá trị thấp.
- Nghiên cứu ứng viên ở [phụ lục D](#phu-luc-d).

- Thứ tự: `blinkcnn` → OCEC-S / OCEC-L → (tuỳ chọn) ghép điểm CNN hiện tại với ứng viên thắng
  (thay đổi thiết kế, cần quyết).
- **Cần sửa công cụ eval trước:** `tools/seq_eval.py --replay block5` chỉ phát lại cột đã trace
  (`p_cnn`, `blink`), không chạy lại model. Phải trace thêm cột (vd. `p_blinkcnn`, `p_ocec`), là
  một mốc riêng.
- Đo: NITYMED / FL3D (AUC, FPR, trên mọi frame và chỉ frame khối 5 được gọi); YawDD clip đeo kính
  (false microsleep); MRL Eye chỉ tham khảo (cả `blinkcnn` và CNN hiện tại đều train trên MRL);
  benchmark ms / 2 crop trên máy đích khi trigger bật liên tục.
- Tiêu chí thay: AUC NITYMED > 0,881; FPR ≤ 1,6%; false microsleep YawDD kính ≤ 6; vẫn ≥ 15 FPS.

---

<a id="viec-choi"></a>

### Việc 16: tăng tương phản (app / web)

Chỉ cần nếu hub dùng camera RGB; camera IR thì bỏ. Bối cảnh ở [phụ lục C](#phu-luc-c).

- **Cân bằng tương phản trên web bằng WebGL shader** (nhẹ hơn OpenCV.js ~8 MB); đo lại FPS ≥ 15.
- **Yêu cầu đầu vào camera (thay cho xử lý chói bằng phần mềm):** camera IR + đèn LED IR 850/940 nm
  (chuẩn của DMS thương mại, ít bị đèn pha ảnh hưởng). Code đã nhận biết IR sẵn.
- **Đánh giá:** quay clip lái đêm thật có đèn pha, chạy qua bản web, đếm báo sai.

---

---

<a id="viec-nhieu-chuyen"></a>

### Việc 17: so sánh nhiều chuyến của tài xế

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
  - Số báo sai tài xế bấm / giờ lái ([chỉ số theo từng người](#viec-theo-nguoi)).
- **Sample mỗi phút đầy đủ hơn** (nếu cần biểu đồ chi tiết hơn bản tổng kết): thời gian nhìn khỏi
  đường, cầm điện thoại, ngáp / gục đầu, tốc độ.
- Không chấm điểm hay xếp hạng tài xế. Đánh giá chuyến chỉ mô tả, vì cảnh báo còn có thể sai.
- Cần nhiều chuyến thật mới có ý nghĩa.

---

<a id="viec-nhan-demo"></a>

### Việc 18: ghi nhãn trực tiếp khi demo

Cần xe, hub, người ngồi cạnh và hàng chục giờ lái: khả thi về kỹ thuật, khó về thực tế. Là cách duy nhất kết luận chỉ tiêu PRD ≤ 1,0 báo sai / giờ.

**Vì sao cần:** báo sai / giờ chỉ kết luận được trên giờ lái dài, liên tục, theo từng người (vd. 40
giờ / người: 0 lần sai thì cận trên CI 95% ≈ 0,09 / giờ; muốn cận trên ≤ 1,0 / giờ cần ≥ 3,7 giờ không
lần sai nào). Nhưng CLAUDE.md cấm ghi frame ra đĩa, nên **sau chuyến không thể xem lại video để gán
nhãn**. Nhãn phải ghi ngay trong chuyến.

**Nguồn nhãn:**

| Nguồn | Đáng tin | Dùng cho |
|---|---|---|
| Người ngồi cạnh bấm "đúng / sai" mỗi lần cảnh báo, và "bỏ sót" khi thấy tài xế có dấu hiệu mà hệ thống im | Cao | Báo sai / giờ theo người; bỏ sót (xấp xỉ) |
| Tài xế tự đánh giá KSS (1–9), người ngồi cạnh hỏi miệng mỗi 5 phút (theo EU DDAW, [phụ lục E](#viec-ddaw)) | Vừa | Mức buồn ngủ theo đoạn, so với `drowsy_score`; "cảnh báo đúng lúc" theo mốc KSS ≥ 8 |
| Nút "báo sai" của tài xế trên HUD | Thấp (lệch, xem [chỉ số theo từng người](#viec-theo-nguoi)) | Chỉ để đối chiếu với nhãn của người ngồi cạnh |

**Cách làm (đề xuất):**
- Một màn hình ghi nhãn trên máy thứ hai (điện thoại người ngồi cạnh), nút to: "Đúng", "Sai", "Bỏ
  sót", "KSS = …". Mỗi lần bấm gửi metadata JSON (`trip_id`, thời điểm, nhãn), không có ảnh.
- Ghép nhãn với sự kiện cảnh báo theo `trip_id` + thời gian (dung sai vài giây, nằm trong
  `thresholds.yaml`); cảnh báo không được ai bấm thì để "chưa xác định", không tự coi là đúng.
- Báo cáo theo từng người: giờ lái, báo sai / giờ + CI, số bỏ sót người ngồi cạnh thấy, bảng đối chiếu
  với nút "báo sai" của tài xế (biết tài xế bấm sai lệch bao nhiêu).
- Nếu có lần KSS ≥ 8: chấm theo khung DDAW ([phụ lục E](#viec-ddaw)), luôn kèm báo sai / giờ.
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

<a id="viec-prd-con-lai"></a>

### Việc 19: phần PRD còn lại

Tách từ việc "làm nốt yêu cầu PRD" (02/10):
- **LLM tóm tắt + gợi ý (FR-12, FR-13):** chưa có dòng code nào. Chạy ở backend trên metadata (không ảnh)
  thì vẫn đúng ràng buộc; PRD §2 loại "LLM realtime". **Cần quyết định:** PRD còn là yêu cầu nộp bài không.
- **Nhật ký theo điều kiện**, tag `simulated` / `forced`, phiên bản cấu hình + hash model trên mỗi sự
  kiện (FR-8, FR-9, FR-17, NFR-6): nhỏ, làm được.
- **Buổi kiểm tra hiểu cảnh báo 10 người** (PRD §7 bậc 3): chưa diễn ra, số đang là "not evaluated".
- **Nộp bài:** `presentation/` mới có README; `eval/results/report.md` (28/09) cần kiểm tra lại.
- **Docker cho edge (FR-14):** compose mới có `backend`. Sản phẩm giờ là APK nên phần edge gần như lỗi
  thời; chỉ làm nếu PRD vẫn bắt buộc.

---

<a id="viec-pitch"></a>

### Việc 20: pitch deck và video demo

- **Vì sao:** README ghi deliverable 6 (video demo) và 7 (pitch deck) là "Chưa có"; `presentation/` mới
  có README ([việc 19](#viec-prd-con-lai)). Nhóm P-196 đã có slide 13 trang, video và trang tóm tắt.
- **Khung slide (mượn của P-196, sửa chỗ yếu):**
  1. Vấn đề: số liệu tai nạn do mệt mỏi / mất tập trung, **mỗi số kèm nguồn và năm** (slide của họ
     thiếu, chính họ tự ghi chú).
  2. Rào cản của giải pháp hiện có: báo sai nhiều nên tài xế tắt, không nói khi không giám sát được,
     gửi video khuôn mặt lên cloud.
  3. Giải pháp và người dùng (4 vai trò), một chuyến đi từ đăng ký đến bảng tổng kết.
  4. Kiến trúc 14 khối; phần khác biệt: tốc độ / xi nhan, mốc riêng từng tài xế, nút báo sai, FMEA.
  5. Kết quả đo kèm giờ đo và CI (`eval/results/report.md`), mỗi dòng có nhận định đạt / chưa đạt.
  6. Giới hạn: chưa có hub, chưa có CAN thật, chưa có giờ lái thật; lộ trình ([pilot-readiness.md](pilot-readiness.md)).
- **Video:** quay theo kịch bản ở HowToUse mục 7.4 trên `#/live` + `#/drive` + dashboard.
- Không đưa số nào chưa có trong `eval/results/`; số đo trên Mac ghi rõ là máy dev.

---

<a id="viec-coi-roi"></a>

### Việc 21: kênh cảnh báo vật lý

- **Vì sao:** cảnh báo hiện chỉ đi qua màn hình và loa của HUD. Trình duyệt chặn âm thanh
  ([FMEA dòng 1](safety-fmea.md)) hoặc app bị Android dừng ([FMEA dòng 4](safety-fmea.md)) thì tài xế
  không nghe gì. P-196 dùng còi + LED nối ESP32 qua UART, tách khỏi màn hình và mạng.
- **Cách làm (đề xuất):** khối 12 thêm một đầu ra mức cảnh báo cho thiết bị ngoài (còi / LED qua
  USB-serial hoặc Bluetooth của hub); thiết bị ngoài tự kêu khi mất nhịp từ app quá hạn, để app chết
  cũng có tiếng báo. Âm lượng và nhịp kêu theo mức, ngưỡng trong `thresholds.yaml`.
- **Cần quyết định trước:** hub có cổng nào, có chấp nhận thêm phần cứng ngoài hub không. Thuộc nhóm
  [sau khi chọn hub](#viec-phan-cung).
- *Chưa kiểm chứng* độ trễ dưới 100 ms mà slide của họ nêu.

---

<a id="viec-tk-demo"></a>

### Việc 22: tài khoản demo theo vai trò

- **Vì sao:** người chấm mở Live URL thì xem được `#/live` nhưng không đăng nhập được dashboard nếu
  không có tài khoản. P-196 ghi tài khoản demo ngay trên trang nộp bài.
- **Cách làm:** trên bản deploy tạo tài khoản `manager` và `engineer` dành cho demo, kèm vài chuyến mẫu
  để dashboard không trống; đưa thông tin đăng nhập trong trang nộp bài, **không commit vào repo**.
- **Không làm theo họ:** mật khẩu của họ ngắn và đăng công khai (4–5 chữ số). Tài khoản demo nên chỉ
  đọc: hiện `engineer` sửa được ngưỡng, nên hoặc chỉ phát tài khoản `manager`, hoặc thêm cờ chỉ đọc.
- **Cần quyết định:** có cho người chấm tài khoản `engineer` không.

---

<a id="viec-dung-luong"></a>

### Việc 23: tối ưu dung lượng tải lần đầu

**Hiện tại (đo 03/10):** màn hình `#/live` ghi "khoảng 60 MB"; đo từng file thì là khoảng 70 MB sau giải
nén, khoảng 42 MB qua mạng nếu server có nén. Cột "qua mạng" của file từ server mình là `gzip -9` đo trên
máy dev, *chưa kiểm chứng* server Railway có nén hay không.

| Thành phần | Nguồn | Gốc | Qua mạng |
|---|---|---:|---:|
| ONNX Runtime wasm (chạy YOLO) | server mình | 14,2 MB | 3,7 MB |
| `yolov8n.onnx` | server mình | 12,9 MB | 11,1 MB |
| MediaPipe wasm | CDN jsdelivr | 11,8 MB | 3,1 MB |
| OpenCV cho Pyodide | CDN jsdelivr | 11,7 MB | 11,7 MB |
| Pyodide (Python core + stdlib) | CDN jsdelivr | 11,1 MB | 5,1 MB |
| `face_landmarker.task` | server mình | 3,8 MB | 3,3 MB |
| numpy | CDN jsdelivr | 3,1 MB | 3,1 MB |
| pyyaml, sqlite3, JS của app, `edge_agent.zip` | lẫn lộn | 1,3 MB | 0,9 MB |

Tải xong, file chỉ nằm trong HTTP cache của trình duyệt: không có service worker, code không đặt
`Cache-Control` cho model và wasm. Trình duyệt dọn cache hoặc mở tab ẩn danh là tải lại từ đầu.

**Hướng đề xuất, theo thứ tự đáng làm:**
1. **YOLO INT8:** `models/yolov8n_int8.onnx` đã có (3,6 MB; 2,7 MB qua mạng), tiết kiệm khoảng 8 MB.
   Phải chạy lại eval: `phone_near_face` không được tăng báo sai, vẫn ≥ 15 FPS trên onnxruntime-web
   (*chưa kiểm chứng* bản wasm chạy được model QDQ này).
2. **Bỏ OpenCV khỏi bản web:** tiết kiệm khoảng 11,7 MB, khoản lớn nhất. Viết lại các chỗ `cv2` mà
   `edge_agent/web/bridge.py` gọi tới (tiền xử lý, cắt vùng mắt) bằng numpy hoặc phía JS; gộp được với
   WebGL shader ở [việc 16](#viec-choi). Bản thiết bị vẫn dùng OpenCV.
3. **Nén và cache trên server:** bật gzip / brotli cho `.wasm`, đặt `Cache-Control` dài hạn cho file có
   hash trong tên, model thì thêm phiên bản vào tên file. Không đổi logic.
4. **Sửa dòng chữ trên màn hình tải** theo số đo mới sau khi làm các mục trên.

Làm mục 1–3: còn khoảng 22 MB qua mạng.

**Không chọn:** bỏ Pyodide và numpy (thêm khoảng 8 MB) vì phải viết lại khối 5–12 sang TypeScript và
giữ hai bản logic đồng bộ.

**Liên quan APK ([việc 13](#viec-apk)):** file đóng sẵn trong APK thì không phải tải lần đầu, nên với
app, việc này làm APK nhẹ đi chứ không đổi thời gian mở. Pyodide và MediaPipe wasm hiện lấy từ CDN
jsdelivr (`frontend/src/live/agent.ts`); việc 13 phải chép chúng vào bundle thì app mới chạy offline.

---

<a id="phan-hoan"></a>

## Hoãn

<a id="viec-nhip-sinh-hoc"></a>

### Hoãn: mức mệt theo nhịp sinh học

**Vì sao hoãn (02/10):** không có dữ liệu giờ thật để kiểm chứng; thay hệ số 1,2 bằng công thức nhiều tham số chưa chứng minh là trái nguyên tắc của [việc 6](#viec-ablation). Làm lại khi có chuyến thật.

- Hiện `drowsy_score` nhân 1,2 cho đêm (0–5 h) và 1,2 khi lái ≥ 2 giờ.
- Thay bằng một hệ số liên tục: giờ trong ngày (vùng trũng 2–6 h và 14–16 h) × thời gian lái liên tục.
  Là công thức, không train; tham số trong `thresholds.yaml`.
- Gợi ý nghỉ ở bảng tổng kết (M15) dùng cùng hệ số.
- Cần dữ liệu có giờ thật (chuyến demo) để kiểm tra; dataset hiện có không có giờ trong ngày đúng nghĩa.

<a id="dang-ky-buoc-c"></a>

### Hoãn: vùng nhìn hợp lệ, nhận mặt bằng model

**Vì sao hoãn (02/10):** chưa có bằng chứng chữ ký mặt hiện tại không đủ; thêm bước vào đăng ký thì đăng ký lâu hơn.

**Bước C (tuỳ chọn): các vùng nhìn hợp lệ**
- Tư thế đầu khi nhìn gương / bảng đồng hồ của chính tài xế đó, dùng cho:
  - Gục đầu (M12): cúi đúng về tư thế bảng đồng hồ với mắt mở thì không phải gục đầu.
  - Việc 4 (hướng nhìn): mốc hướng nhìn theo từng vùng.
- **Không** dùng để bỏ qua `off_road`: nhìn gương quá 2 s khi chạy vẫn phải báo.
- Thêm bước vào đăng ký thì đăng ký lâu hơn (đang ~10 s): cân nhắc với yêu cầu "không quá lâu".

**Bước D (chỉ khi chữ ký mặt không đủ): embedding mặt**
- Một model nhận dạng mặt pretrained nhỏ (vd. SFace trong OpenCV Zoo; *chưa kiểm tra license, kích
  thước, tốc độ*) chỉ chạy lúc đăng ký và khi nghi đổi người, không chạy mỗi frame, nên không ảnh
  hưởng 15 FPS. Là model mới nên cần quyết định riêng.

<a id="viec-trace-that"></a>

### Hoãn: trace số từ chuyến thật (có đồng ý)

**Vì sao hoãn (02/10):** chưa có chuyến thật hay đội xe; vướng quyền riêng tư (đồng ý, thời hạn lưu). Làm khi APK chạy trên xe thật.

- **Vì sao:** không lưu frame nên sau chuyến không có gì để dò ngưỡng; dataset công khai thì ngắn hoặc
  diễn ([việc 5](#viec-holdout)). Trace số (EAR, MAR, góc, blendshape, mức, sự kiện
  theo frame) không chứa ảnh nhưng đủ để `seq_eval --replay` dò ngưỡng.
- **Cách làm:**
  - Tài xế bật đồng ý rõ ràng (tắt mặc định); trace nén gửi cuối chuyến kèm bản tổng kết, hoặc giữ trên
    thiết bị đến khi có mạng.
  - Gắn phản hồi "báo sai", nhãn của người ngồi cạnh ([việc 18](#viec-nhan-demo)), KSS
    nếu có.
  - Có thời hạn lưu và xoá theo yêu cầu; chỉ kỹ sư xem được.
- **Cần quyết định:** landmark 3D chi tiết vẫn có thể là dữ liệu sinh trắc; chỉ lưu các số đã tính (EAR,
  góc…), không lưu 478 điểm.

---

## Phụ lục

<a id="phu-luc-a"></a>

### A. Metric đánh giá: cảnh báo sai / giờ và FAR / MAR

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
| Kết luận đạt PRD | **Cảnh báo sai / giờ theo từng người**, có nhãn | Chuyến demo có người ghi nhãn ([việc 18](#viec-nhan-demo)) |
| Đã triển khai | Số lần tài xế bấm "báo sai" / giờ, theo tài xế; chỉ để giám sát | Feedback HUD ([chỉ số theo từng người](#viec-theo-nguoi)) |

Clip dataset ngắn nên báo sai / giờ trên dataset chỉ là số kiểm tra phụ; nó cần dữ liệu dài mới có ý
nghĩa (lý do để dời nó sang giai đoạn có dữ liệu dài, không phải để bỏ). **Cách đo báo sai / giờ hiện
tại chưa đủ để kết luận đạt hay chưa đạt:**

#### Vấn đề
1. **Quá ít giờ dữ liệu, chưa có khoảng tin cậy.** Khoảng tin cậy 95% theo Poisson (exact):

   | Nguồn | Đang báo | CI 95% |
   |---|---:|---:|
   | FL3D L1 (1 sai / 26 phút tỉnh táo) | 2,3 / giờ | 0,06 – 12,9 / giờ |
   | FL3D L2 (3 sai / 26 phút) | 6,9 / giờ | 1,4 – 20 / giờ |
   | YawDD | 6,9 / giờ | 3,3 – 12,7 / giờ |

   Một lần sai trên FL3D đã bằng 2,3 / giờ. PRD §6 bắt buộc kèm số giờ clip + CI và cấm kết luận "đạt
   ≤ 1,0 / giờ".
2. **Dữ liệu không giống lái thật.** NITYMED diễn lại, YawDD xe đỗ: mật độ hành vi dày hơn lái thật
   (phần lớn là nhìn đường nhàm chán). SUST / YawDD là nhiều clip ngắn ghép lại, clip nào cũng rơi vào
   giai đoạn khởi động (mốc EAR chưa ổn, hiệu chỉnh 5 s đầu) → "một giờ" thực chất là hàng trăm lần
   khởi động. Tốc độ giả lập cố định 60 km/h nên luật ngữ cảnh (dừng đèn đỏ, xi-nhan) không được thử.
3. **Định nghĩa "sai" trộn nhiều loại lỗi.** Sai = cảnh báo trên đoạn nhãn tỉnh táo, nhưng dataset chỉ
   gán nhãn buồn ngủ, không gán mất tập trung. SUST: 24/26 lần "sai" là `off_road` khi tài xế quay đầu
   thật, có thể là cảnh báo đúng hoặc chỉ ngưỡng hơi chặt.
4. **Đứng một mình thì dễ bị lừa:** hệ thống không bao giờ cảnh báo đạt 0 / giờ. Phải đi cùng MAR
   ([M18](#viec-far-mar), đã có), tỉ lệ bắt sự kiện và time-to-alert (PRD p95 ≤ 3 s, chưa có công cụ đo,
   xem việc 3).
5. **Số HITL trên dashboard không cùng loại:** `false_alarms / tổng cảnh báo` là precision, không phải
   / giờ, và phụ thuộc tài xế có bấm nút hay không.

<a id="viec-far-mar"></a>

**FAR / MAR theo cửa sổ** (định nghĩa, quy ước ở `docs/release-v2.md`, M18) gần như không đọc được
   trên dataset đang có: FL3D 7 cửa sổ hợp lệ, YawDD 13, SUST 0 (clip 10 s). Cần video dài: UTA-RLDD
   ([việc 5](#viec-toi-uu-nguong)), DMD.


- **Điện thoại (khối 4):** YOLO bắt 2,1 % ảnh State Farm; góc chụp bên cạnh không giống camera của
  mình nên chưa đủ để kết luận (worklog 26/09).
---

<a id="phu-luc-b"></a>

### B. Dữ liệu đánh giá

Kiểm tra 30/09/2026 (metadata, trang chính, license), chưa tải, chưa chạy thử. Tất cả chỉ dùng để
đánh giá: không đưa frame / ảnh mặt vào repo, báo cáo hay slide, chỉ số liệu. Muốn dùng bộ nào thì
thêm thành mốc riêng (cần task mới trong `tools/dataset.py`).

| Dataset | Dùng cho | Lấy thế nào | Trạng thái |
|---|---|---|---|
| UTA-RLDD | Cảnh báo sai / giờ (~8 giờ tỉnh táo), buồn ngủ thật theo mức 0 / 5 / 10 | Kaggle 96,6 GB, hoặc Kaggle Notebook | Nên dùng (dò ngưỡng, việc 5) |
| DMD | Recall theo frame, time-to-alert, ngáp che tay, mất tập trung, hướng nhìn | Cổng DMD, CC BY-NC-ND | Nên dùng |
| DROZY | Buồn ngủ thật + KSS / PVT / EEG, IR phụ | ORBi 2,46 GB, tải thẳng | Nên dùng |
| NTHU-DDD | Video IR, kính râm, gục đầu, nói / cười (báo sai) | HF gated `auto` hoặc email NTHU | Cần xem `train.zip` trước |
| Brain4Cars | `off_road` khi rẽ / chuyển làn, tốc độ thật | Dropbox 16 GB | Cần xem độ dài clip trước |

#### Phần dữ liệu còn thiếu và nguồn lấp

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

#### UTA-RLDD

Nguồn: Kaggle `rishab260/uta-reallife-drowsiness-dataset` [U1], bản gốc [U2], paper Ghoddoosian et
al., CVPRW 2019. Kiểm tra qua Kaggle API, chưa tải, chưa chạy thử.

**Kết luận: nên dùng**, nhưng chỉ cho (a) cảnh báo sai / giờ trên video tỉnh táo và (b) `drowsy_score`
có tăng theo mức buồn ngủ trên cùng một người hay không. Không dùng được để đo tỉ lệ bắt microsleep /
ngáp; không giúp phụ lục C (đêm, chói) hay điện thoại.

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

Dùng để chỉnh ngưỡng buồn ngủ: [việc 5](#viec-toi-uu-nguong).

**Cần làm nếu chọn (mốc riêng):** task mới trong `tools/dataset.py` (vd. `video_drowsy`, nhãn từ tên
file `0` / `5` / `10`, gộp `10_1` / `10_2`), báo cáo cảnh báo sai / giờ + CI trên video `0` và phân
bố `drowsy_score` theo mức. Nên gộp với phần tách khởi động / đường đánh đổi của việc 5. Thử 1 fold (~12 GB) trước.

- U1. https://www.kaggle.com/datasets/rishab260/uta-reallife-drowsiness-dataset
- U2. https://sites.google.com/view/utarldd/home

<a id="dmd"></a>

#### DMD — Driver Monitoring Dataset

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
- **Time-to-alert p95 ≤ 3 s** (việc 2: chưa có công cụ đo).
- **Ngáp che tay:** tay che làm landmark miệng / MAR sai; chưa dataset nào khác có nhãn này.
- Bộ Distraction / Gaze: nhãn gọi điện, nhắn tin, vùng nhìn (gương, cửa sổ, bảng đồng hồ) → đo
  `off_road`, `phone` (khối 8) và việc 4 (hướng nhìn).
- Camera mặt đặt gần trên xe thật, giống bố cục camera taplo.

**Hạn chế:**
- Diễn thì rõ và cường điệu hơn thật → recall lạc quan.
- 14 người, không còn IR → không giúp phụ lục C (đêm).
- Hành động nguy hiểm trên xe thật làm khi **xe đứng yên** → phải giả lập tốc độ, nếu không luật ngữ
  cảnh (khối 10) tắt cảnh báo.
- License **CC BY-NC-ND 4.0, chỉ dùng học thuật**. Dự án không thương mại nên dùng được; ND = không
  phân phối lại dữ liệu đã sửa, công bố số liệu thì được. Không đưa frame vào repo / slide.
- Cần viết phần đọc OpenLABEL JSON và gióng nhãn với frame: nặng hơn task `video_drowsy` cho UTA.
- Wiki có nhắc microsleep, nhưng annotation criteria không có nhãn microsleep riêng → suy ra từ đoạn
  `Closed` đủ dài.
- *Chưa kiểm chứng:* dung lượng bộ Drowsiness, số giờ còn lại sau khi cắt, có cần đăng ký không
  (hỏi info-dmdvicomtech.org).

**Cần làm nếu chọn (mốc riêng):** đọc nhãn OpenLABEL → task video theo frame trong `tools/dataset.py`,
báo cáo recall microsleep / ngáp, độ trễ, time-to-alert p95. Nên làm sau UTA-RLDD (mốc cảnh báo sai /
giờ); gộp được với công cụ đo time-to-alert (việc 2).

- D1. https://dmd.vicomtech.org/
- D2. https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset
- D3. https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-drowsiness-related-action-annotation-criteria
- D4. https://arxiv.org/pdf/2008.12085

#### DROZY (ULg, WACV 2016) [N4][N5]

- 14 người (3 nam, 11 nữ), 3 bài PVT 10 phút, thiếu ngủ thật tăng dần; còn ~36/42 bài (6 bài mất).
- Video NIR Kinect v2 512×424, 8 bit xám, mp4, chủ yếu 30 fps. Có KSS, thời gian phản xạ PVT, PSG /
  EEG, 68 landmark 2D / 3D.
- Tải thẳng `DROZY.zip` **2,46 GB** trên ORBi, không đăng ký.
- License (bản 18/07/2018, đã đọc): chỉ nghiên cứu / đánh giá, không thương mại; không phân phối lại,
  không sửa; không lộ danh tính; **không hiển thị ảnh** (trừ ảnh đánh dấu công bố được); trích dẫn
  Massoz et al., WACV 2016.
- Dùng: so `drowsy_score` / PERCLOS với KSS và thời gian phản xạ. Không phải lái xe (làm test trước
  màn hình); IR Kinect không giống camera DMS.

#### NTHU-DDD (NTHU CVlab, ACCV Workshop 2016) [N1]

- 36 người, ~9,5 giờ, toàn bộ quay bằng camera IR + đèn IR chủ động, AVI 640×480. 5 bối cảnh:
  `BareFace`, `Glasses`, `Night_BareFace`, `Night_Glasses` (15 fps), `Sunglasses` (30 fps).
- Diễn, ngồi ghế chơi game lái xe. Buồn ngủ: ngáp, chớp chậm, gục đầu. Không buồn ngủ: **nói, cười,
  nhìn hai bên** (tốt để đo báo sai).
- Nhãn theo frame (buồn ngủ, mắt, đầu, miệng) theo nguồn thứ cấp [N2], *chưa kiểm chứng*.
- Bản gốc: điền license agreement, email `cvlablai636my.nthu.edu.tw`, chờ duyệt.
- **Không cần email:** Hugging Face `chbh7051/driver-drowsiness-dataset` [N3], gated `auto` (tài
  khoản HF + bấm đồng ý), chỉ có `data/train.zip` (~3 GB) + script loader, không card / license.
  *Chưa biết* bên trong là video hay frame, có file nhãn không; tên gợi ý chỉ phần train (18 người).
  Bản đăng lại dữ liệu cần license agreement: dự án không thương mại nên rủi ro thấp, vẫn trích dẫn;
  muốn chắc thì email song song.
- Preset `ddd` hiện tại là ảnh mặt cắt từ NTHU-DDD, không phải video.

#### Brain4Cars (Cornell, ICCV 2015) [N6] (bỏ khỏi kế hoạch 02/10)

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

- N1. http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/
- N2. https://www.emergentmind.com/topics/nthu-ddd-dataset
- N3. https://huggingface.co/datasets/chbh7051/driver-drowsiness-dataset
- N4. https://www.drozy.uliege.be/
- N5. https://orbi.uliege.be/handle/2268/191620
- N6. https://github.com/asheshjain399/ICCV2015_Brain4Cars

#### Dataset Kaggle đã kiểm tra, không dùng

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

<a id="phu-luc-c"></a>

### C. Ánh sáng khó: lái đêm, đèn đường, đèn pha

#### Đã có (cả thiết bị lẫn web, vì web chạy lại khối 5–12 bằng Python qua Pyodide)
- Mặt quá tối (độ sáng vùng mặt, trước CLAHE, < `low_light_brightness` = 60): khối 5 thay EAR
  bằng điểm nhắm mắt (thiết bị: CNN mắt; web: blendshape `eyeBlink`).
- Giữ nguồn đó thêm `hold_s` = 2 s sau khi hết tối: đi qua đèn đường / chạng vạng không làm
  EAR ↔ điểm nhắm mắt đổi qua lại từng frame, không sinh nhắm mắt giả.
- EAR hai mắt lệch nhiều (lóa kính, che một mắt): dùng điểm nhắm mắt (không giữ).
- Mất mặt ngắn hơn `max_gap_s`: đợt nhắm mắt đang đếm không bị xoá; frame `face_conf` < 0,9 bị bỏ.
- Nhận biết ảnh IR / xám qua độ chênh kênh màu (có cả trên web).
- Đánh giá đêm: 44 video NITYMED (FL3D), nhưng chạy bản Python có CLAHE, không phải bản web.

#### Chưa giải quyết
- **Đèn pha chiếu thẳng** (vùng mắt cháy trắng, landmark lệch): chốt 01/10 không xử lý bằng phần
  mềm, mà bằng **yêu cầu đầu vào camera** (camera IR + đèn LED IR, xem dưới). Mất mặt do chói thì
  thành `unavailable` theo FR-6 (đã làm ở M10), không còn báo L2 sai.
- **Web không có CLAHE.** Webcam / camera điện thoại tự chỉnh phơi sáng chậm khi ánh sáng đổi đột
  ngột; trình duyệt gần như không cho điều khiển.
- **Giới hạn vật lý:** webcam RGB trong cabin tối gần như không thấy mặt; phần mềm không bù được.
- **Chưa có dữ liệu** đèn pha / đèn đường quét qua; chưa đánh giá riêng đường chạy web ban đêm.

Hướng đề xuất: [việc 16](#viec-choi) (tương phản), camera IR (phần cứng, [nhóm sau khi chọn hub](#viec-phan-cung)).

---

<a id="phu-luc-d"></a>

### D. Model trạng thái mắt thay / bổ sung cho Eye-state CNN (khối 5)

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

#### Hiện trạng
- Thiết bị: Intel OMZ `open-closed-eye-0001` (Apache-2.0, 46 KB, BGR 32×32, train MRL Eye), 0,12 ms
  / lần gọi, chỉ gọi khi EAR không tin được. NITYMED: CNN AUC 0,881; blendshape `eyeBlink` 0,986.
- Web: blendshape `eyeBlink`. Blendshape V2 **chỉ nhận 146 landmark làm input, không nhìn pixel**
  [7], nên khi lóa kính làm lệch landmark mí mắt thì `eyeBlink` sai theo, không độc lập với EAR.
  Khớp với việc trên thiết bị blendshape kém CNN khi đeo kính.
- Không có bản mới hơn: Open Model Zoo đang ở chế độ bảo trì [3]; MediaPipe chưa công bố model nào
  sau Blendshape V2 (11/2022) [6][7].

#### Ứng viên đáng thử (license MIT, có ONNX tải được)

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

#### Đã loại
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

Đề xuất thử offline: [việc 15](#viec-model-mat).

#### Nguồn
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

#### YOLO chuyên mắt nhắm / ngáp (research 29/09/2026)

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

<a id="viec-ddaw"></a>

### E. Khung báo cáo EU DDAW

Không phải việc riêng: dùng trong [việc 18](#viec-nhan-demo) (ghi nhãn khi demo) và
[việc 5](#viec-toi-uu-nguong) (UTA-RLDD).

**Vì sao:** bộ eval chưa định nghĩa "cảnh báo đúng lúc" so với lúc tài xế bắt đầu buồn ngủ. `seq_eval`
chấm theo sự kiện (nằm trong đoạn có nhãn ± 1 s) và FAR / MAR theo cửa sổ, nhưng không có luật kiểu
"phải cảnh báo trước hoặc ngay khi KSS đạt 8". EU bắt buộc hệ thống DDAW (driver drowsiness and
attention warning) trên xe mới từ 2022; quy trình thử nằm ở Annex của C/2021/2639 và lấy mốc **KSS ≥ 8**
(Ahlström & Anund 2025 [D1] xác nhận). KSS là thang tự đánh giá 1–9 của Åkerstedt & Gillberg 1990 [D2].

**Chưa kiểm chứng (cần đọc Annex trước khi dùng):** độ nhạy trung bình > 40 %, > 20 % cho > 95 % người,
≥ 10 sự kiện KSS ≥ 8, KSS hỏi mỗi 5 phút. Mới thấy qua bản tóm tắt thứ cấp; PMC và EUR-Lex không đọc
được ngày 02/10. Khoảng thời gian một cảnh báo được tính là "đúng lúc" cũng lấy từ Annex.

**Áp dụng:**
- **Việc 18:** KSS hỏi miệng mỗi 5 phút (thay 15 phút). Cảnh báo đúng = có cảnh báo buồn ngủ trong
  khoảng quanh lần đầu KSS ≥ 8 (độ dài theo Annex, nằm trong `thresholds.yaml` của công cụ eval).
- **Việc 5:** video `10` của UTA-RLDD ≈ KSS ≥ 8 (mức `5` ≈ KSS 6–7). Chỉ là xấp xỉ: một nhãn cho cả
  video, không biết lúc nào đạt 8. Bảng riêng, không dùng để chọn ngưỡng.
- **Luôn kèm báo sai / giờ:** độ nhạy chỉ đếm cảnh báo được, không đếm báo sai. CLAUDE.md đặt chống báo
  sai ngang độ chính xác, nên không báo cáo độ nhạy một mình.

**Giới hạn:**
- **Không tự tạo đủ sự kiện KSS ≥ 8 trên đường thật.** Ahlström & Anund [D1] phải dùng tài xế chuyên
  nghiệp, chạy đêm sau khi thức từ sáng sớm, trong nghiên cứu có kiểm soát, và viết rằng đạt mức này ban
  ngày trên đường thật là *"problematic… from legal and ethical perspectives"*. Khớp với giới hạn an
  toàn của [việc 18](#viec-nhan-demo): demo chủ yếu đo báo sai. Số sự kiện KSS ≥ 8 thật gần như chắc
  dưới 10, chỉ báo cáo tham khảo.
- **Không đo được "rời làn":** Cori 2023 [D3] định nghĩa suy giảm khi lái là > 3,5 lần rời làn / giờ (12
  người, đường đua kín, xe có thiết bị đo). DriverGuard chỉ có camera trong xe và CAN giả lập, không có
  cảm biến làn, dataset hiện có cũng không có vị trí làn. Ghi là giới hạn, không thành việc.

**Không dùng lập luận "KSS không tương quan với tai nạn":** bài JCM 2026 [D4] (Aksoy et al., 51 người,
simulator) kết luận về **ESS** (thang xu hướng buồn ngủ chung), không phải KSS: *"subjective sleepiness
assessed by the ESS showed no significant association"*. Davin 2026 ([phụ lục H](#bo-blink-rate), [B2])
thấy KSS là chỉ số chủ quan dự báo tốt nhất, còn ESS không liên quan. Lưu ý đúng về KSS: là tự đánh giá
nên có thể bị khai thấp, cần đối chiếu với chỉ số khách quan (PERCLOS, microsleep).

#### Nguồn

- [D1] Ahlström C, Anund A. Development of sleepiness in professional truck drivers: real-road testing
  for driver drowsiness and attention warning (DDAW) system evaluation. J Sleep Res 2025;34:e14259.
  https://doi.org/10.1111/jsr.14259 (PMC11911040)
- [D2] Åkerstedt T, Gillberg M. Subjective and objective sleepiness in the active individual. Int J
  Neurosci 1990;52:29–37. https://doi.org/10.3109/00207459008994241
- [D3] Cori JM, Wilkinson VE, Soleimanloo SS, et al. A brief assessment of eye blink drowsiness
  immediately prior to or following driving detects drowsiness related driving impairment. J Sleep Res
  2023. https://doi.org/10.1111/jsr.13785
- [D4] Aksoy E, Arbatli S, Celik Y, Peker NY, Balcan B, Peker Y. Moderate-to-severe OSA and objective
  drowsiness are associated with driving-related accidents, but not subjective sleepiness: a simulator
  study. J Clin Med 2026. https://doi.org/10.3390/jcm15135116
- EU: Commission Delegated Regulation (EU) 2021/1341 (C/2021/2639), Annex: quy trình thử DDAW.

---

<a id="quyet-dinh"></a>

### F. License YOLO (AGPL-3.0)

Ultralytics ghi mọi model YOLO của họ, kể cả model fine-tune và bản
  export ONNX / TFLite, mặc định thuộc AGPL-3.0; sản phẩm thương mại, SaaS / API, triển khai trên
  thiết bị edge hay phần mềm đóng mã thì phải mở mã toàn bộ theo AGPL hoặc mua Enterprise License
  [Y10]. Áp dụng cho `models/yolov8n.onnx` và `yolov8n_int8.onnx` đang dùng cho điện thoại (repo
  đang để LICENSE MIT; `docs/release-v1.md` đã có ghi chú AGPL). **Đã chốt (29/09): dự án học tập,
  không thương mại → giữ YOLO, không mua license.** Việc còn lại nếu muốn làm đúng AGPL: bản web trên
  Railway là dịch vụ mạng có dùng YOLO, nên khi công khai thì để mã nguồn truy cập được (vd. repo
  public, ghi rõ phần YOLO theo AGPL). (Không phải tư vấn pháp lý.)

---

<a id="phu-luc-g"></a>

### G. Đăng ký tài xế: giới hạn còn lại của M9

- Chữ ký mặt (tỉ lệ landmark) chưa đo trên người thật nhiều người trong xe; dataset eval đều chỉ có
  một người.
- Đổi tài xế giữa chuyến: đã có nút "Đổi tài xế" (M16), người lái mới đăng ký lại. Chưa **tự phát
  hiện** người khác ngồi vào: cần chữ ký mặt đủ tin cậy mới làm được.
- MediaPipe chỉ trả `num_faces` = 2 mặt: với ≥ 3 người có thể không thấy tài xế nếu hai mặt khác nổi
  hơn. Tăng lên 3 thì phải đo lại FPS.
- Mốc mắt nhắm (bước 3) mới dùng để kiểm tra đăng ký đúng; chưa dùng để đổi thang `close_ratio`
  (độ mở mắt theo khoảng nhắm → mở): đổi thang thì phải dò lại ngưỡng trên dataset.

---

<a id="phu-luc-h"></a>

### H. Lý do đã bỏ

<a id="bo-blink-rate"></a>

#### Bật lại `blink_rate` theo phân vị của chính tài xế

Đề xuất: thay `risk.blink.normal_min / normal_max` (10 / 30 lần / phút, `level: 0`) bằng ngưỡng theo
phân vị của chính tài xế, như `eye.baseline_percentile: 90`. Bỏ vì:
- **Hai nguồn dẫn ra không ủng hộ nhịp chớp.** Häkkänen 1999 [B1]: *"No significant differences
  between the groups appeared in average blink frequency"*, chỉ thời lượng khác. Davin 2026 [B2]
  (meta-analysis 61 nghiên cứu, 1441 người) không phân tích nhịp chớp: 7 công cụ là ESS, KSS,
  PERCLOS-80, JDS, KDS, công suất EEG, microsleep. Nhịp chớp chỉ được nhắc ở phần mở đầu ("frequent
  blinking", trích Caffier 2003). JDS, thang gần với chớp mắt nhất, không có liên hệ (p = 0,67, độ tin
  cậy rất thấp, hướng đảo chiều). Hai thứ Davin ủng hộ, PERCLOS-80 và microsleep, đã có trong
  `drowsy_score` (trọng số 40, 25) và luật L3.
- **Phân vị 90 dùng sai chỗ.** Ở mắt, phân vị 90 chọn EAR "mắt mở" từ phân bố frame. Lấy phân vị 90
  nhịp chớp của chính tài xế làm ngưỡng thì theo định nghĩa khoảng 10 % cửa sổ luôn vượt ngưỡng:
  báo sai có hệ thống.
- **Hướng không rõ, nhiễu nhiều.** Buồn ngủ có thể làm nhịp chớp tăng hoặc giảm; nói chuyện, điều hoà,
  chói và nhìn gương đều đổi nhịp chớp.
- **Tính trùng.** `blink_time_frac` ≈ nhịp chớp × thời lượng trung bình, đã nằm trong
  `slow_blink_score`.
- **Không có mâu thuẫn trong config.** `level: 0` chính là hệ quả của câu "varies a lot between
  people": ngưỡng 10 / 30 chỉ ghi chú, không cảnh báo.

Nguồn:

- [B1] Häkkänen H, Summala H, Partinen M, Tiihonen M, Silvo J. Blink duration as an indicator of driver
  sleepiness in professional bus drivers. Sleep 1999;22(6):798–802.
  https://doi.org/10.1093/sleep/22.6.798
- [B2] Davin A, Khouri C, Ben Messaoud R, et al. Sleepiness assessment tools for predicting fitness to
  drive: a systematic review and meta-analysis. Sleep Med Rev 2026;90:102380.
  https://doi.org/10.1016/j.smrv.2026.102380
- [B3] Ingre M, Åkerstedt T, Peters B, Anund A, Kecklund G. Subjective sleepiness, simulated driving
  performance and blink duration: examining individual differences. J Sleep Res 2006;15:47–53.
  https://doi.org/10.1111/j.1365-2869.2006.00504.x

<a id="bo-subsampling"></a>

#### Giảm xử lý từng frame

**Đã bỏ (02/10): giảm xử lý từng frame** (lấy mẫu thưa theo thời gian, chỉ chạy khi có sự kiện, gom lô
trong cửa sổ PERCLOS), đề xuất từ tổng quan PRISMA của Salas Yupanqui et al. 2026 [S1]:
- **Nguồn chỉ là lập luận.** Câu *"neither requires that every frame be processed independently"* đúng
  cho PERCLOS, nhưng bài tự ghi *"the reviewed studies rarely evaluate these alternatives"*: không có số
  đo nào cho thấy bỏ frame mà giữ được độ chính xác. Bài nhắm tới 33 hệ deep learning chạy CNN lớn mỗi
  frame. Lời phê bình "chỉ 27,3 % nghiên cứu báo thời gian" không áp dụng: `eval/results/benchmark.md`
  đã có p50 / p95 / max từng khối.
- **Không có vấn đề để giải.** Vòng lặp chính 151,8 FPS (p95 7,2 ms, Mac ARM), gấp ~10 lần 15 FPS;
  phần nặng nhất là MediaPipe 5,8 ms, khối 7–12 0,01 ms.
- **Hai trong ba cách đã có:** YOLO ~5 lần / s trên luồng riêng (`features.target_fps: 5`); CNN mắt chỉ
  chạy khi EAR không tin được (`always_run: false`). Gom lô trong cửa sổ PERCLOS không lợi gì vì phần
  tính PERCLOS gần như không tốn.
- **Bỏ frame MediaPipe làm hỏng tín hiệu khác:** đo chớp (M11) cần
  25–30 FPS, sai số thời gian mở mắt đã ≤ 40 / 60 ms ở 30 / 15 FPS; microsleep → L3 ở 1,5 s trễ thêm mỗi
  frame bị bỏ; phân biệt gục / cúi dựa vào tốc độ hạ đầu.
- Chỗ có ích duy nhất là khi hub tụt FPS: thứ tự hạ tải ở trên.

[S1] Salas Yupanqui et al. Accuracy–latency trade-offs and absent embedded validation in deep learning
driver drowsiness detection: a PRISMA systematic review. Front Artif Intell 2026.
https://doi.org/10.3389/frai.2026.1871926 (PMC13572618)

#### Đọc thành tiếng cảnh báo L2 / L3

- Làm thử trong M23 (đọc câu hành động của L2 / L3, đọc khi mất camera / tạm ngưng giám sát) rồi gỡ theo yêu cầu 02/10: "không cần nói, cảnh báo thôi". Giọng nói của bước đăng ký giữ nguyên.

#### Uống nước / ăn khi lái

- Đề xuất cũ: dùng lớp `cup` / `bottle` có sẵn của YOLOv8n (COCO), không train.
- Bỏ (02/10): hành vi không nguy hiểm rõ ràng, lại thêm một nguồn báo sai, trái ưu tiên chống báo sai.

#### Hai model (sóng não + mặt) để chấm điểm buồn ngủ

- **Hai model (sóng não + mặt → chỉ mặt) để chấm điểm buồn ngủ:** phải train, vi phạm "chỉ dùng
  pretrained". Risk engine dạng luật hiện tại vẫn là lựa chọn đúng.

#### Khác (xem `docs/release-v2.md`, mục 4)

- Chống chói đèn pha bằng phần mềm, bám tài xế thành việc riêng (01/10); rung điện thoại, tự điều chỉnh theo sức máy cho web (02/10, sản phẩm là APK trên hub).
