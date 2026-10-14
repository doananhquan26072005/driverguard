# Hướng cải tiến DriverGuard

Danh sách để chọn mốc tiếp theo, không phải kế hoạch. Theo CLAUDE.md, không mục nào được làm
trước khi có yêu cầu; mục nào được chọn thì thêm thành mốc trong `docs/roadmap.md`. Việc làm xong được xoá
khỏi file này và ghi vào [`docs/release-v4.md`](release-v4.md) (trước M70: [`release-v3.md`](release-v3.md)); sau mỗi lần xoá, các việc được đánh số lại
liên tục.

**Bối cảnh (cập nhật 08/10):** không còn hub của xe và không còn xe thật để kiểm chứng; chỉ còn mô phỏng trên web, máy dev,
webcam, trace có sẵn (UTA-RLDD, FL3D, 3MDAD, bản tự ghi) và người ngồi trước camera. Các việc cần thiết bị đích hoặc chuyến
lái thật đã chuyển sang [Đã bỏ](#bo-hub); thiết bị VF e34 ([phụ lục J](#phu-luc-j)) giữ lại làm rủi ro đã biết, chưa kiểm
chứng. Sản phẩm vẫn được thiết kế cho APK trên màn hình xe, nhưng phần nộp bài là bản web mô phỏng và phải nói rõ giới hạn đó.

## Danh sách việc

Bấm tên việc để xuống phần chi tiết. Số thứ tự dùng để gọi tắt khi chọn mốc ("làm việc 1"). Các việc **xếp theo độ nên
làm**: nhóm trên làm trước. Trong mỗi nhóm cũng theo thứ tự đó. Đây chỉ là đề xuất, anh quyết định làm việc nào.

**Thời gian dự kiến** là ước lượng của tôi (08/10), chưa đo bằng việc đã làm. Chỉ tính **thời gian Claude làm và chạy**
(viết code, chạy test và số đo, viết tài liệu), **không tính công của người**: ngồi ghi trước webcam, quay và dựng video,
tuyển và hỏi 10 người, đọc duyệt, quyết định. Tính bằng giờ làm việc của Claude; mỗi mốc roadmap thường là một việc nên
thời gian của nhóm là tổng, không làm song song. Việc phải đo trước khi biết kết quả (việc 5–7) có thể dài hơn.

**Thứ tự sau audit 08/10** ([audit-2026-10-08.md](audit-2026-10-08.md) mục 6.2, sửa 09/10): tốc độ xe từ GPS lên thành
việc 3, nhóm riêng ngay sau nộp bài; các việc sau nó lùi một số. Ba chỗ khác của mục 6.2 đã hết mâu thuẫn nhờ mốc đã làm:
tên gọi số báo sai (M70), đồng hồ canh trước đường đi của frame (M71), khoảng hở giữa hai frame trước khi thử rút ngắn
`rise_confirm_s` (M71). Việc 10 có thêm điều kiện về phiên đăng nhập; mục hoãn `l1` 40 → 50 có điều kiện về dữ liệu.

**Quyết định 09/10** ([bảng đầy đủ](roadmap.md#quyet-dinh-0910)): anh chốt 31 chỗ còn ngỏ. Các chỗ được chọn làm là mốc
M92–M101 của roadmap, **đều xong ngày 09/10** ([tóm tắt](roadmap.md#ke-hoach-0910)), và không còn nằm trong file này. Bốn việc chuyển sang
[Đã bỏ](#bo-0910): YOLO bản web với ảnh nhỏ hơn, lấy frame thẳng từ camera, SLM giải thích mức cảnh báo, hỏi tài xế bằng
giọng nói. Hàng đợi offline từ việc 13 thành việc 11 (nay là việc 10, sau khi pitch deck và video xong 14/10); nhóm 5 không còn.

| Nhóm | Việc | Độ nên làm | Thời gian dự kiến | Thứ cần có | Vì sao xếp ở đây |
|---|---|---|---|---|---|
| 1. Nộp bài | 1–2 | Cao | 1–1,5 giờ | Không chờ gì (dùng số của M69 và M70, gọi đủ tên: "nhánh buồn ngủ" hay "mọi nhánh") | Bản web mô phỏng là đầu ra; có hạn nộp |
| 2. Tốc độ xe | 3 | Cao | 2–3 giờ | Quyết định về quyền vị trí (09/10: chưa quyết). Hành vi khi chưa từng có tốc độ đã làm ở M95 | Từ M95, chưa có nguồn tốc độ thì sau 30 s thấy tài xế hệ thống giám sát như đang chạy; nhưng các luật cần tốc độ thật (trên 80 km/h, nghỉ khi dừng, đèn đỏ, xi nhan) vẫn không hoạt động |
| 3. Một đợt tự ghi trước camera | 4–8 | Cao đến trung bình | 4–6 giờ | Người ngồi trước webcam | Cách duy nhất còn lại để giảm báo sai và bỏ sót bằng dữ liệu mới |
| 4. Kỹ thuật bản web | 9–10 | Trung bình đến thấp | 2–2,5 giờ | Không chờ gì | Cải tiến thật nhưng lợi nhỏ, không đo được trên máy đích |

### Nhóm 1: nộp bài
Hai việc còn lại của buổi nộp (slide và video đã xong 14/10): phần PRD còn thiếu, tài khoản cho người chấm. Việc 2 lấy ý từ so
sánh với nhóm P-196 (03/10). Không còn hub nên slide phải ghi rõ "mô phỏng trên web, chưa đo trên thiết bị đích".

**Thời gian dự kiến:** 1–1,5 giờ. Việc 1: khoảng 1 giờ (kiểm tra lại `report.md`, tài liệu buổi kiểm tra; người tổ chức buổi 10 người); việc 2: khoảng 30 phút. Không tính công của người.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 1 | [Phần PRD còn lại](#viec-prd-con-lai) | Buổi kiểm tra hiểu cảnh báo 10 người; nộp bài (`presentation/`, kiểm tra lại `report.md`). Tag `simulated` / `forced` đã xong ở M41 |  |
| 2 | [Tài khoản demo theo vai trò](#viec-tk-demo) | Tài khoản chỉ đọc cho người chấm trên bản deploy, có dữ liệu mẫu |  |

### Nhóm 2: tốc độ xe
Một việc, đứng riêng. Trước [M95](roadmap.md#m95) bản web không có bộ giả lập thì đứng "đỗ" cả chuyến, không cảnh báo nào; nay sau
30 s thấy tài xế mà chưa có số đọc thì tốc độ là không rõ và hệ thống giám sát như đang chạy. Phần còn lại của việc này là
một nguồn tốc độ thật, để các luật theo tốc độ hoạt động và xe đỗ thật không bị cảnh báo.

**Thời gian dự kiến:** 2–3 giờ (kể cả `docs/data-policy.md` và màn hình đồng ý vị trí).

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 3 | [Tốc độ xe từ GPS của thiết bị](#viec-gps) | Tốc độ từ `navigator.geolocation`, làm mượt. Hai chiều hỏng phải xử lý riêng: **chưa từng có tốc độ** đã xử lý ở M95 (sau 30 s thấy tài xế thì coi là không rõ, giám sát như đang chạy, báo tài xế); **mất GPS sau khi đã có số đọc lúc đang chạy** thì coi là đang chạy (M26, đã có). Chỉ dùng tốc độ, không lưu và không gửi toạ độ. Làm và thử bằng chuỗi tốc độ giả trên web |  |

### Nhóm 3: một đợt tự ghi trước camera
Phần làm được trên 13 phiên của một người và trên trace sẵn có đã làm ở [M54](roadmap.md#m54), [M55](roadmap.md#m55),
[M56](roadmap.md#m56). Việc còn lại đều chờ một thứ ngoài code: người thứ hai, vài phiên ghi bổ sung, hoặc một quyết định.
Việc 4 là việc ghi; việc 5–7 là nhìn xuống và mất tập trung (ghi xong mới làm được); việc 8 là mắt và ánh sáng.

**Thời gian dự kiến:** 4–6 giờ. Việc 4: khoảng 15 phút chạy báo cáo sau khi có bản ghi (người ghi thì không tính); việc 5: 1–2 giờ; việc 6: khoảng 1 giờ; việc 7: khoảng 1 giờ; việc 8: khoảng 1 giờ. Việc 5–7 chỉ bắt đầu được sau khi người ghi xong dữ liệu của việc 4.

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 4 | [Ghi số trực tiếp từ camera: phần còn thiếu](#viec-prd) | 13 phiên của một người đã ghi (khoảng 80 phút). Còn thiếu: người thứ hai; liếc bằng mắt mà đầu đứng yên; cúi nhẹ kèm nhắm mắt thật. Chỉ người ngồi trước camera làm được |  |
| 5 | [Nhìn xuống hay nhắm mắt](#viec-nhin-xuong) | Nhìn xuống lâu bị báo L3 ngủ gật: 7 / 30 lần ở bản tự ghi, 0 / 100 lần nhắn tin 3–5 s của 50 tài xế 3MDAD. Đã thử bốn đường, không đường nào bật được: ngưỡng chung, ngưỡng eyeBlink theo tài xế (có sẵn, tắt), hướng mắt (bật cả trong microsleep thật), ngữ cảnh điện thoại (chỉ 3 / 7 lần có điện thoại trong khung hình). Còn lại: cúi nhẹ kèm nhắm mắt; người thứ hai; đường CNN |  |
| 6 | [Tách gọi điện với nhắn tin](#viec-goi-nhan) | Một người: `phone_kind` đúng ở mọi frame có điện thoại; gọi 9 / 9, nhắn tin 6 / 11 và chậm (p50 3,15 s). Còn lại: người thứ hai. Chốt 09/10: không báo nhắn tin sớm hơn, không nới vùng tài xế, cho tới khi có người thứ hai |  |
| 7 | [Theo dõi hướng mắt](#viec-huong-nhin) | Đã có ở chế độ chỉ đo (M55): góc nhìn xuống = góc cúi đầu + mống mắt. Giữ 2 s ở 12°: bắt 14–26 % số lần nhắn tin của 50 tài xế 3MDAD (hệ thống hiện tại 2–8 % bằng góc đầu), 0 lần khi lái bình thường và khi nhắm mắt; FL3D khoảng 2,6 lần sai mỗi giờ. Trên 6 người UTA-RLDD (2,8 giờ, không lái xe) tín hiệu bật 32 lần, 20 lần của một người. Chưa đủ để thành cảnh báo. Còn lại: dữ liệu có nhãn nhìn xuống; liếc ngang bằng mắt. Chốt 09/10: không thêm bước "nhìn xuống" vào đăng ký |  |
| 8 | [Khối 5 khi mặt tối, ngưỡng `eyeBlink` trên `#/live`](#viec-cnn-toi) | Phần mặt tối (M54) và ngưỡng `eyeBlink` của bản web (M56) đã sửa. Còn lại: ngưỡng `eyeBlink` mới là tạm và chưa đo trên `#/live` (đo được bằng webcam); chưa có phiên mặt sáng 12–32. Ảnh xám / IR thật không còn nguồn đo (08/10) |  |

### Nhóm 4: kỹ thuật bản web
Phần còn lại sau M49–M51 và M67 ([M49](roadmap.md#m49), [M50](roadmap.md#m50), [M51](roadmap.md#m51),
[M67](roadmap.md#m67)). Đo và thử được trên Chromium của máy dev, không đo được trên máy đích. Không việc nào bỏ frame hay
thêm model. Việc 10 giữ cho sản phẩm chịu được mất mạng. Khối 12 đã đếm lại sau khoảng hở giữa hai frame (M71) trước khi
việc 9 thử rút ngắn `rise_confirm_s`. Hai việc cũ của nhóm (YOLO với ảnh nhỏ hơn, lấy frame thẳng từ camera) đã
[bỏ ngày 09/10](#bo-0910).

**Thời gian dự kiến:** 2–2,5 giờ. Việc 9: 45–60 phút; việc 10: 1–1,5 giờ (mốc M97 về phiên đăng nhập đã xong).

| # | Task | Solution | Người thực hiện |
|---:|---|---|---|
| 9 | [Độ trễ cảnh báo: phần còn lại](#viec-tre-canh-bao) | `#/live` đã đẩy cảnh báo ngay và dùng giờ chụp của frame (M50). Bản ghi M52: ngủ gật p95 1,67 s, điện thoại 2,30–2,77 s, nhìn sang bên / ra sau 2,83–3,04 s (sát mốc 3 s của PRD). Còn lại: thử `rise_confirm_s` 0,5 / 0,25 / 0 s trên bản ghi và trên chuỗi có khoảng hở giữa hai frame, đếm cảnh báo ngoài nhãn; HUD của bản thiết bị vẫn hỏi 300 ms một lần (ưu tiên thấp) |  |
| 10 | [Hàng đợi offline cho app](#viec-outbox-web) | Mất mạng: lưu sự kiện / tổng kết trong IndexedDB, gửi lại khi có mạng; thử bằng cách tắt mạng trong DevTools. Phiên đăng nhập đã được gia hạn trong chuyến (M97) |  |

### Hoãn
Chưa đủ dữ liệu hoặc lý do để làm; xem lại khi có chuyến thật. Lý do ở [phần hoãn](#phan-hoan).

| Task | Vì sao hoãn |
|---|---|
| [Phần còn lại sau UTA-RLDD](#viec-toi-uu-nguong) | Đã đo và đổi ngưỡng ở M53; phần còn lại (chỉ tiêu PRD, `trend` trên chuyến dài, gục / ngáp, chỉ số theo người khi chạy thật) cần dữ liệu lái thật. Riêng `l1` 40 → 50: đã quyết ở M101 bằng DROZY với luật khai báo trước, giữ 40 |
| [Phát hiện mắt bị che (kính râm)](#viec-mat-bi-che) | Phiên kính râm đã bỏ (06/10), không có dữ liệu để đo; FMEA dòng 5 vẫn mở ở mức Cao |
| [Mức mệt theo nhịp sinh học](#viec-nhip-sinh-hoc) | Không có dữ liệu giờ thật để kiểm chứng; thêm tham số chưa chứng minh |
| [Vùng nhìn hợp lệ, nhận mặt bằng model](#dang-ky-buoc-c) | Đăng ký sẽ lâu hơn; từ 08/10 đã có bằng chứng chữ ký mặt không phân biệt được người (M83, phụ lục G) |
| [Trace số từ chuyến thật](#viec-trace-that) | Chưa có chuyến thật; vướng quyền riêng tư |
| [Tín hiệu vô lăng: góc lái qua CAN, cảm biến tay](#viec-vo-lang) | Chưa có CAN thật; cảm biến tay là phần cứng mới; bài báo không có số đo dùng được |
| [Nhịp tim đọc từ camera (rPPG)](#viec-rppg) | Bằng chứng yếu và mâu thuẫn; nhạy với ánh sáng và rung; các bản có số đẹp đều phải train |

### Đã bỏ
<a id="bo-0910"></a>
<a id="viec-yolo-web"></a>
<a id="viec-duong-frame"></a>
<a id="viec-slm"></a>
<a id="viec-hoi-giong-noi"></a>

**Mới 09/10, theo quyết định của anh** ([bảng](roadmap.md#quyet-dinh-0910), chỗ 21–24):
- **YOLO bản web với ảnh đầu vào nhỏ hơn hoặc cắt vùng tài xế:** giữ 640. Số đo trên 3MDAD
  ([`phone_web_3mdad.md`](../eval/results/phone_web_3mdad.md), roadmap [M67](roadmap.md#m67)): 480 và 416 giữ số cảnh báo
  nhưng thấy điện thoại lúc gọi ít hơn, 320 mất một phần ba. Rủi ro đã biết còn nguyên: máy chậm không có WebGPU thì kết
  quả YOLO quá hạn 0,6 s và nhánh điện thoại thành "không rõ" (được báo, không im lặng; [phụ lục J](#phu-luc-j)).
- **Lấy frame thẳng từ camera (`MediaStreamTrackProcessor`):** lợi chỉ 0–3 % frame sau khi vòng lặp đã tự lấy frame bằng
  timer lúc đứng (M71), và nó đổi hành vi khi tab bị che.
- **SLM giải thích mức cảnh báo** (đề bài ghi tuỳ chọn; PRD FR-12, FR-13): không làm. Mức cảnh báo vẫn do luật của khối 9
  quyết định, câu kể cho quản lý là mẫu câu viết sẵn.
- **Hỏi tài xế bằng giọng nói sau cảnh báo nặng:** không làm, ở cả ba bước. Lý do có từ trước: chạm PRD §2 ("LLM
  realtime"), đọc thành tiếng đã bỏ 02/10, giọng nói là loại dữ liệu mới của tài xế.

Lý do của các mục dưới ở [phụ lục H](#phu-luc-h). **Mới 08/10, không còn hub và xe thật** ([lý do và danh sách](#bo-hub)): đo tài nguyên và
bản web trên thiết bị VF e34, bản Python trên thiết bị, đóng gói APK, OTA model, thử model mắt mới cho camera IR, tăng tương phản
cho camera RGB, còi / LED rời, eval ánh sáng bằng ảnh IR thật, ghi nhãn khi chạy thử trên xe, so sánh nhiều chuyến.
Từ trước: bật lại `blink_rate` theo phân vị tài xế; thêm `duration_ratio` (thời
lượng chớp so với chính tài xế: prototype M35 không tách được drowsy / alert và trùng với `reopen_ratio`,
xem [`eval/results/blink_duration_fl3d.md`](../eval/results/blink_duration_fl3d.md)); giảm xử lý từng frame; đưa thẳng thẻ video cho MediaPipe (M51: đo không lợi); đọc
thành tiếng cảnh báo; lượng tử hoá lại YOLO sang INT8 (06/10: file `yolov8n_int8.onnx` hiện có không phát hiện được điện thoại nào, giữ FP32; số đo ở roadmap M54); cảnh báo cho liếc ngắn cộng dồn (06/10, biến đo của M38 vẫn giữ); uống nước / ăn khi lái; Brain4Cars; phiên tự ghi chói / ngược sáng và kính râm (06/10); tải NTHU-DDD (không tải
được); khẩu trang (miệng bị che); hai model sóng não + mặt; (trong
`docs/release-v2.md`) chống chói bằng phần mềm, bám tài xế riêng, rung điện thoại, tự điều chỉnh theo
sức máy cho web; đo bản web trên điện thoại Android thay cho hub (06/10).

---

## Chi tiết từng việc

<a id="viec-prd-con-lai"></a>

### Việc 1: phần PRD còn lại

**Độ nên làm: cao.** Có hạn nộp bài. Buổi kiểm tra 10 người cần người tham gia, phần còn lại làm một mình được.

Tách từ việc "làm nốt yêu cầu PRD" (02/10):
- **LLM tóm tắt + gợi ý (FR-12, FR-13):** [bỏ ngày 09/10](#viec-slm); câu kể trong bảng tổng kết chuyến vẫn là mẫu câu viết sẵn (M15).
- ~~Tag `simulated` / `forced`, phiên bản cấu hình + hash model trên mỗi sự kiện (FR-8, FR-17, NFR-6)~~: đã
  làm ở M41. Bảng tách theo điều kiện (FR-9): có bảng theo độ sáng và theo kính từ M40
  ([`eval/results/lighting.md`](../eval/results/lighting.md)); ngược sáng, thiếu sáng thật thì chưa có dữ liệu.
- **Buổi kiểm tra hiểu cảnh báo 10 người** (PRD §7 bậc 3): chưa diễn ra, số đang là "not evaluated".
  Gợi ý từ [P2] mục 7.3 ([phụ lục I](#phu-luc-i)): trong cùng buổi hỏi thêm mức khó chịu của cảnh báo (thang
  1–5) và bảng SUS 10 câu, để có số về phía con người ngoài "hiểu đúng / sai". Các mốc bài báo nêu (khó chịu
  < 2 / 5, NASA-TLX ≤ 40) là mục tiêu nghiên cứu họ đề xuất, không phải tiêu chuẩn; NASA-TLX dài, chỉ thêm
  nếu còn thời gian.
- **Nộp bài:** `presentation/` mới có README; `eval/results/report.md` (28/09) cần kiểm tra lại.
- ~~Docker cho edge (FR-14)~~: đã làm ở M42 (`Dockerfile.edge`, `tools/edge_sim.py`).

---

<a id="viec-tk-demo"></a>

### Việc 2: tài khoản demo theo vai trò

**Độ nên làm: cao, việc nhỏ.** Người chấm không xem được dashboard nếu không có tài khoản.

- **Vì sao:** người chấm mở Live URL thì xem được `#/live` nhưng không đăng nhập được dashboard nếu
  không có tài khoản. P-196 ghi tài khoản demo ngay trên trang nộp bài.
- **Cách làm:** trên bản deploy tạo tài khoản `manager` và `engineer` dành cho demo, kèm vài chuyến mẫu
  để dashboard không trống; đưa thông tin đăng nhập trong trang nộp bài, **không commit vào repo**.
- **Không làm theo họ:** mật khẩu của họ ngắn và đăng công khai (4–5 chữ số). Tài khoản demo nên chỉ
  đọc: hiện `engineer` sửa được ngưỡng, nên hoặc chỉ phát tài khoản `manager`, hoặc thêm cờ chỉ đọc.
- **Cần quyết định:** có cho người chấm tài khoản `engineer` không.

---

<a id="viec-gps"></a>

### Việc 3: tốc độ xe từ GPS của thiết bị

**Độ nên làm: cao** (sửa 09/10 theo audit 08/10, phát hiện 1; trước đó "trung bình đến thấp"). Ngày 09/10 anh chưa quyết về quyền vị trí và về nguồn nào thắng giữa GPS và `#/drive`, nên phần GPS vẫn mở. Đây là điều kiện để sản phẩm có cảnh báo khi không ai bấm bộ giả lập. Chỉ thử được bằng chuỗi giả.

Bỏ ngày 06/10 ("tốc độ GPS khi chưa có CAN"), thêm lại cùng ngày sau khi chốt thiết bị đích
([phụ lục J](#phu-luc-j)): Android box nối với xe qua cổng USB của CarPlay nên không có CAN (*suy luận, chưa kiểm
chứng*), GPS của thiết bị là nguồn tốc độ duy nhất chứ không còn là tạm thời.

- **Vì sao:** từ M19 tốc độ / xi nhan lấy từ công cụ mô phỏng `tools/drive_sim.py` (người ngồi bấm). Trên xe thật
  không có ai bấm, và có hai chiều hỏng khác nhau:
  - **Chưa từng có số đọc nào (hành vi trước M95): khối 10 coi xe đang đỗ ở 0 km/h** (`ExternalVehicle.sample` trong
    `edge_agent/context/can_sim.py`). Từ M30 xe đỗ thì không có cảnh báo nào, khối 8 tắt, và "tạm ngưng giám sát" cũng
    không bật vì nó cần xe đang lăn bánh. Audit 08/10 thử bằng chuỗi số giả: nhắm mắt 10 s, mất mặt 30 s, cầm điện
    thoại 10 s cho mức 0 và 0 cảnh báo. HUD có màn hình "đỗ chưa có tín hiệu" nhưng không có âm báo, và nhịp gửi
    backend vẫn bình thường. Đây là hành vi của bản web trên xe không có bộ giả lập: im lặng cả chuyến.
  - **Đã có số đọc lúc xe chạy rồi mất tín hiệu:** khối 10 coi là đang chạy
    (`context.assume_moving_when_speed_unknown`, M26) và báo `vehicle_signal_lost`. Khi đó ngưỡng `off_road` trên
    80 km/h và luật nghỉ khi dừng không hoạt động.
  - Bản 08/10 của mục này chỉ ghi chiều thứ hai ("không có tốc độ thì coi là đang chạy"), ngược với chiều thứ nhất.
- **Cách làm:**
  - Nguồn tín hiệu xe mới cho khối 10: tốc độ từ `navigator.geolocation` (`coords.speed`; trong APK có thể cần
    plugin định vị của Capacitor và quyền vị trí), làm mượt vài giây, ngưỡng trong `thresholds.yaml`.
  - Mất GPS quá `context.vehicle_signal_stale_s`: tốc độ không rõ, giám sát như đang chạy và báo
    `vehicle_signal_lost` (hành vi sẵn có của M26), không quay về 0 km/h.
  - ~~Chưa từng có tốc độ~~: đã làm ở [M95](roadmap.md#m95) (`context.vehicle_signal_wait_s`, 30 s), không chờ GPS. Khi có GPS thì
    số đọc đầu tiên của nó chấm dứt trạng thái "không rõ" đó.
  - **Đang rẽ:** hướng GPS (`coords.heading`) đổi nhanh hơn một ngưỡng (°/s) thì coi như xi-nhan bật về phía đang
    rẽ, dùng lại `turn_side` / `turn_signal_grace_s` của khối 10. Tách được thành bước sau.
  - Chỉ gửi số tốc độ sang Python; không lưu vị trí, không gửi toạ độ lên backend. Xin quyền vị trí là điểm mới
    với tài xế: cập nhật `docs/data-policy.md` và màn hình đồng ý.
  - Test bằng chuỗi tốc độ / hướng giả. Làm và xem thử được trên bản web. Từ 08/10 không còn thiết bị để kiểm GPS thật, nên mục *chưa kiểm chứng* ở phần rủi ro vẫn mở.
- **Rủi ro:**
  - GPS trễ 1–2 s và nhiễu khi chạy chậm: xe dừng đèn đỏ có thể bị đọc là 1–3 km/h. `context.stationary_kmh` và
    `min_speed_kmh` (5) phải được kiểm lại với số thật, nếu không M30 lúc bật lúc tắt. Từ [M72](roadmap.md#m72)
    "tạm ngưng giám sát" chạy từ 1 km/h, nên nhiễu đó còn có thể bật "tạm ngưng" khi xe đang đứng: tốc độ GPS phải
    được làm mượt trước khi đưa vào khối 10.
  - Trong hầm và bãi xe ngầm mất GPS: đúng lúc đó hệ thống coi là đang chạy, có thể báo khi xe đang đỗ.
  - Kênh `#/drive` không xác thực: ai có mã ghép cũng đặt được tốc độ 0 và tắt mọi cảnh báo (audit 08/10, A4 M4). Khi
    GPS là nguồn tốc độ thì phải chốt nguồn nào thắng.
  - *Chưa kiểm chứng* GPS của Android box bắt sóng thế nào khi box nằm trong hộc; `coords.speed` có thể là `null`
    trên một số máy, khi đó phải tự tính từ hai vị trí liên tiếp.

---

<a id="viec-prd"></a>

### Việc 4: ghi số trực tiếp từ camera, phần còn thiếu

**Độ nên làm: cao, nếu còn ngồi ghi được.** Là cách duy nhất còn lại để cải thiện độ chính xác và báo sai bằng dữ liệu mới; chỉ cần webcam và người ngồi trước. Việc 5–8 chờ dữ liệu của việc này.

**Đã có ([M52](roadmap.md#m52), [M54](roadmap.md#m54)):** 13 phiên của một người, không kính, một ngày, khoảng 80 phút.
`data/own_traces/quan_v2.pkl` (12 phiên; thư mục `data/` không vào git) và `quan_int8.pkl`; báo cáo
[`eval/results/own_recordings.md`](../eval/results/own_recordings.md). `tools/record_trace.py` chỉ lưu số của từng frame
kèm nhãn bấm phím, không lưu ảnh (HowToUse mục 9.5).

**Còn thiếu** (lệnh: `python tools/record_trace.py record --out data/own_traces/quan_v2.pkl --tag person=<tên> --tag
glasses=no --tag light=day --name <tên phiên>`; mọi phiên bắt đầu bằng 20 s ngồi yên không bấm):
1. **Người thứ hai** (đeo kính thường nếu có), khoảng 40 phút: `day_eyes`, `phone_holds`, `look_down`, `glances`. Mọi ngưỡng
   và kết luận của nhóm này đang dựa trên một người.
2. **`eyes_only2`** (cho [việc 7](#viec-huong-nhin)): tựa đầu vào ghế để đầu không xoay; liếc xuống bàn phím ngay dưới camera
   (`j`) 5 lần, liếc tới mép màn hình (`k`) 5 lần, giữ 5 s, cách nhau 40 s. Phiên `eyes_only` đầu tiên ghi ra thành quay đầu
   17–70°, đã đổi tên `head_turn`.
3. **`bow_light`** (cho [việc 5](#viec-nhin-xuong)): cúi nhẹ đúng như khi nhìn điện thoại trên đùi rồi nhắm mắt (`w`) 5 lần, 3 s
   mỗi lần, nghỉ 5 s. Ở phiên `look_down`, lúc nhắm mắt đầu cúi 14–22°, lúc nhìn điện thoại chỉ 7–10°.
4. Chạy lại `python tools/record_trace.py report --traces data/own_traces/quan_v2.pkl --out
   eval/results/own_recordings.md`.

**Cách ghi (rút ra từ bản ghi thử hỏng và ba phiên đã ghi):**
- Bộ gõ để ABC (phím `e d s r a x` là phím dấu của Telex); bấm phím khi cửa sổ xem trước đang được chọn.
- Mỗi hành động bấm hai lần cùng một phím: lúc bắt đầu và lúc đã về tư thế thường. Giữ hành động tới khi có cảnh
  báo; cảnh báo đến sau khi nhãn đóng quá `eval.label_tolerance_s` (1 s) bị tính là bỏ sót.
- 20 s đầu mỗi phiên ngồi yên nhìn thẳng để hệ thống học mốc mắt và tư thế.
- Nhắm mắt: nhắm 3 s, nghỉ ít nhất 5 s (`alert.fall_hold_s` 3 s: nghỉ ngắn hơn thì lần sau không ra cảnh báo
  mới).
- Nhìn lệch (`d b s r` chung lý do `off_road`) và điện thoại (`c x` chung lý do `phone`): hai lần cùng lý do
  cách nhau ít nhất 35 s (`alert.cooldown_s` của L2 là 30 s).
- Phím: `e` nhắm mắt, `d` cúi nhìn điện thoại, `b` nhìn bảng đồng hồ, `s` nhìn sang bên, `r` nhìn ra sau, `y`
  ngáp, `t` nói chuyện, `n` gục đầu, `c` điện thoại ở tai, `x` cầm nhắn tin, `a` ngồi yên, `q` dừng và lưu.
  Thêm 06/10: `m` nhìn điện thoại trên giá đỡ thấp, `g` nhìn cần số, `j` liếc xuống bằng mắt, `k` liếc sang bên
  bằng mắt, `l` liếc ngắn lặp lại, `w` cúi kèm nhắm mắt thật, `v` nhìn gương bình thường (không mong cảnh báo), `p`
  quay đầu một phần rồi giữ.
- Thêm 06/10: `m` giá đỡ thấp, `g` cần số, `j` / `k` liếc xuống / sang bên bằng mắt, `l` liếc ngắn lặp lại, `w` cúi kèm
  nhắm mắt thật, `v` nhìn gương (không mong cảnh báo), `p` quay đầu một phần rồi giữ.
- Ghi xong nên kiểm góc đầu của từng nhãn trước khi dùng: người ghi dễ quay đầu theo mắt mà không biết.

**Giới hạn của dữ liệu này:** người của team, diễn, ngồi trước laptop: là tập dev để thử ngưỡng bằng replay, không thay được
dataset có nhãn hay chuyến lái thật. Nhãn là lúc người bấm phím, không phải lúc hành động thật bắt đầu.

---

<a id="viec-nhin-xuong"></a>

### Việc 5: nhìn xuống hay nhắm mắt

**Độ nên làm: cao.** Lỗi báo sai lớn nhất còn mở (nhìn xuống bị báo ngủ gật L3). Chờ phiên `bow_light` và người thứ hai của [việc 4](#viec-prd).

**Lỗi còn nguyên:** nhìn xuống (điện thoại trên đùi, nhắn tin) bị khối 7 coi là nhắm sâu và ra còi L3 "Mở mắt!" thay cho L2
"Nhìn về phía trước": 7 / 30 lần trên bản tự ghi của một người. Quy tắc "đầu cúi" của M25 không được áp vì người ghi nhìn
xuống chủ yếu bằng mắt (đầu chỉ cúi 7–10°, ngưỡng `bowed_pitch_deg` là 10°).

**Đã thử ([M54](roadmap.md#m54)), không đường nào bật được:**

| Thay đổi | Nhìn xuống bị báo L3 (30 lần) | Nhắm mắt thật đạt L3 (48 lần) | FL3D microsleep đạt L3 |
|---|---:|---:|---:|
| hiện tại | 7 | 47 | 74 / 95 |
| ngưỡng chung `microsleep_deep.blink` 0,55 | 4 | 47 | 64 / 95 |
| ngưỡng chung `microsleep_deep.blink` 0,6 | 1 | 47 | 58 / 95 |
| `bowed_pitch_deg` 5, `bowed_ear_ratio` 0,25 | 5 | 47 | 64 / 95 |
| theo tài xế, `enrolled_blink_ratio` 0,8 | 4 | 47 | 75 / 94 (hiện tại 77 / 94) |
| theo tài xế, `enrolled_blink_ratio` 0,85 | 2 | 47 | 66 / 94 |
| theo tài xế, `enrolled_blink_ratio` 0,9 | 1 | 43 | 61 / 94 |

- Người ngủ thật trong FL3D nhắm mắt nông hơn người diễn và nông hơn lúc cố ý nhắm: ở frame bị coi là nhắm sâu, FL3D có
  eyeBlink trung vị 0,65 và EAR 0,21 lần mốc; nhìn xuống điện thoại có 0,56 và 0,24; người ghi nhắm thật có 0,67–0,71 và
  0,12–0,18. Hai nhóm đầu chồng lên nhau ở mọi số đo đang có trong trace (AUC tốt nhất 0,81).
- Cơ chế theo tài xế có sẵn và tắt (`microsleep_deep.enrolled_blink_ratio` 0; đăng ký ghi `DriverProfile.blink_closed`). Dòng
  FL3D của nó dùng lần microsleep đầu của mỗi video thay cho bước đăng ký, và đếm theo cách khác hai dòng trên.
- So sánh lẫn khác biệt người và camera: FL3D ban đêm, bản tự ghi là laptop ban ngày.

- **Hướng mắt cũng không gỡ được ([M55](roadmap.md#m55)):** góc nhìn xuống (việc 7) bật cả trong 6 lần microsleep thật của
  FL3D, nên dùng nó để đổi L3 thành "nhìn xuống" sẽ che mất ngủ gật.
- **Trên 50 tài xế 3MDAD lỗi này hiếm hơn nhiều so với bản tự ghi:** nhắn tin 0 / 100 lần ra L3 `microsleep`, dù 12–37 % số
  frame nhắn tin đạt điều kiện "nhắm sâu". Các đoạn đó chỉ dài 3–5 s; ở bản tự ghi người ghi nhìn xuống 5–10 s liền.

- **Ngữ cảnh điện thoại cũng không gỡ được ([M56](roadmap.md#m56)):** chỉ 3 / 7 lần báo nhầm có điện thoại trong vùng tài xế
  (4 lần còn lại là điện thoại trên đùi, ngoài khung hình). Thử "đang thấy điện thoại thì cần eyeBlink cao hơn": 7 → 5 hoặc 6.
  Không có dữ liệu ngủ gật khi đang cầm điện thoại để kiểm mặt trái (0 / 48 lần nhắm mắt của bản tự ghi và 0 frame FL3D có
  điện thoại), nên không làm.
- **Quy tắc "đầu cúi" không che ngủ gật trên UTA-RLDD (M56):** tắt quy tắc thì 145 video chỉ khác 1 cảnh báo L3 (212 → 211 ở
  video buồn ngủ, vẫn 24 / 48 người có L3).
- **Gục đầu với cúi nhìn đã tách được trên bản tự ghi (M56):** phiên `look_down` gục 9 / 9, cúi nhìn 0 / 12 lần ra `nod`. 7 lần
  sót đều ở phiên `day_eyes`, do người ghi gục nông (13–16°, ngưỡng 15°) và mắt không nhắm. Phép thử tốc độ của M12 không
  thêm được gì, vẫn tắt.

**Còn lại:**
1. Ca cúi nhẹ mà nhắm mắt chưa có dữ liệu (phiên `bow_light` của [việc 4](#viec-prd)).
2. Người thứ hai: khoảng cách eyeBlink giữa nhắm thật và nhìn xuống mới đo trên một người.
3. Ca EAR rất thấp khi nhìn xuống: SUST `n_368` (đầu cúi 17°, EAR 0,26 lần mốc, eyeBlink 0,7) vẫn lọt ngưỡng 0,35.
4. Đường CNN: frame do CNN mắt quyết định (ảnh xám / IR, hai mắt lệch) chưa có quy tắc "đầu cúi".

---

<a id="viec-goi-nhan"></a>

### Việc 6: tách gọi điện với nhắn tin

**Độ nên làm: trung bình.** Gọi điện đã đúng 9 / 9; còn lại là nhắn tin chậm (p50 3,15 s), chờ người thứ hai.

**Hiện tại (M38):** `phone_kind` (`call` / `text` / `unknown`) được ghi vào metadata cảnh báo `phone`, bảng tổng kết chuyến và
dashboard. Lý do và mức cảnh báo giữ nguyên (`phone`, L2).

**Đo trên bản tự ghi ([M52](roadmap.md#m52), [M54](roadmap.md#m54); một người, 9 lần gọi và 11 lần nhắn tin):**
- `phone_kind` đúng ở mọi frame có điện thoại trong vùng tài xế, kể cả lần cầm cao nhất (tâm điện thoại ở 0,77 lần chiều cao
  mặt dưới tâm mặt).
- Gọi, tay trái và tay phải: 9 / 9 có cảnh báo, p95 2,75 s.
- Nhắn tin: 6 / 11, p50 3,15 s, p95 4,71 s (PRD: 3 s). Model chỉ thấy điện thoại cầm thấp ở 19–80 % số frame, nên
  `phone_ratio_2s` chậm đạt 0,6 hoặc không đạt.
- Ba lần nhắn tin ra L3 `microsleep` trước khi `phone` kịp đủ 2 s ([việc 5](#viec-nhin-xuong)).
- Một lần model thấy điện thoại ở 92 % số frame nhưng chỉ 7 % nằm trong vùng tài xế: tâm lệch 1,7 lần bề rộng mặt sang bên,
  vùng chỉ rộng 1,5 (`phone.zone_expand_x` 1,0).

**Còn lại:**
1. Người thứ hai và các cách cầm có ghi lại thứ tự (phiên `phone_holds` không ghi kiểu cầm của từng lần).
2. Chốt 09/10: giữ nguyên cả hai cho tới khi có người thứ hai. Không báo nhắn tin sớm hơn hay nâng mức; `phone.zone_expand_x`
   giữ 1,0 (1,3 bắt được lần cầm lệch, đổi lại dễ tính cả điện thoại của hành khách).
3. Giới hạn đã biết: điện thoại trên đùi nằm ngoài khung hình, là phần của [việc 7](#viec-huong-nhin); YOLO thấy kém khi tay
   che điện thoại.

---

<a id="viec-huong-nhin"></a>

### Việc 7: theo dõi hướng mắt

**Độ nên làm: trung bình đến thấp.** Đang ở chế độ chỉ đo, chưa đủ chính xác để thành cảnh báo; chờ dữ liệu có nhãn nhìn xuống.

**Đã có ([M55](roadmap.md#m55)), chỉ đo, không cảnh báo:** khối 6 tính `iris_y` (mống mắt so với đường nối hai khoé mắt);
khối 8 tính **góc nhìn xuống** = góc cúi đầu so với tư thế nhìn đường + `gaze.iris_gain` × độ lệch `iris_y` so với mốc
của tài xế, và `gaze_down_duration` = thời gian góc đó ở mức `gaze.down_deg` (12°) trở lên. Frame bị khối 7 coi là nhắm
chặt thì bỏ qua. Mốc `iris_y` tự học trong 5 s đầu lúc xe chạy. Ghi vào trace; bản web tính được luôn vì đã gửi đủ 478
điểm sang Python.

**Số đo, tín hiệu giữ ≥ 2 s** ([`eval/results/gaze_3mdad.md`](../eval/results/gaze_3mdad.md): 3MDAD, 50 tài xế trong xe thật,
camera hướng mặt, diễn, mỗi hành động 3–5 s; bản tự ghi một người; FL3D):

| | Góc nhìn xuống ≥ 12° | Hệ thống hiện tại |
|---|---:|---:|
| 3MDAD nhắn tin tay phải | 7 / 50 | `off_road` 4 / 50, `phone` 20 / 50 |
| 3MDAD nhắn tin tay trái | 13 / 50 | `off_road` 1 / 50, `phone` 0 / 50 |
| 3MDAD chỉnh radio | 10 / 50 | `off_road` 5 / 50 |
| 3MDAD gọi điện tay phải | 10 / 50 | `off_road` 9 / 50, `phone` 2 / 50 |
| 3MDAD lái bình thường, mệt mỏi | 0 / 50, 0 / 50 | 1 / 50 (L3 sai), 4 / 50 |
| Tự ghi: điện thoại trên đùi | 4 / 7 | 0 / 7 |
| Tự ghi: nhắn tin; giá đỡ thấp, bảng đồng hồ, cần số | 1 / 11; 0 / 12 | 6 / 11 (`phone`); 0 / 12 |
| Tự ghi: nhắm mắt thật (kể cả cúi) | 0 / 48 | – |
| Tự ghi: ngoài mọi nhãn, 67 phút | 0 | – |
| FL3D, 47 phút | 2 lần ngoài microsleep, 6 lần trong microsleep thật | – |

- **Chưa đủ để thành cảnh báo:** bắt 14–26 % số lần nhắn tin; trên FL3D khoảng 2,6 lần mỗi giờ ngoài nhãn microsleep.
- **Không dùng được để gỡ [việc 5](#viec-nhin-xuong):** tín hiệu bật cả trong 6 lần microsleep thật của FL3D (mắt lim dim
  trước khi nhắm), nên lấy nó để đổi L3 thành "nhìn xuống" sẽ che mất ngủ gật.
- Từng tín hiệu riêng, tách nhắn tin với lái bình thường theo từng tài xế (AUC trung vị, 47 người): góc cúi đầu 0,82,
  `iris_y` 0,75, blendshape `eyeLookDown` 0,68. Mống mắt không hơn góc đầu; cộng hai thứ thì đặc hiệu hơn từng thứ.
- Hai bộ dữ liệu khác hình học: người trong xe cúi đầu nhiều hơn (trung vị 5–6°), người ngồi trước laptop gần như chỉ đưa
  mắt. Một hệ số `iris_gain` chung không hợp cả hai.
- LISA Gaze v2 (có nhãn vùng nhìn) không dùng được: ảnh cắt sát vùng mắt, MediaPipe không tìm ra mặt.
- 3MDAD: tốc độ khung hình không được lưu, 30 FPS là giả định; nhãn phủ cả đoạn, kể cả lúc với lấy điện thoại.

- **Video dài của người thật ([M56](roadmap.md#m56)):** 18 video UTA-RLDD có sẵn trên máy (6 người, 2,8 giờ, ngồi trước laptop)
  được trace lại để có cột mống mắt. Tín hiệu giữ ≥ 2 s bật 19 lần ở video tỉnh (19 lần / giờ), 2 lần ở mức 5, 11 lần ở video
  buồn ngủ; 20 / 32 lần là của một người. Dataset không có nhãn nhìn xuống nên không biết lần nào đúng. Trace lại cả 145 video
  trên Kaggle (khoảng 16 giờ) không trả lời thêm được gì khi thiếu nhãn đó.
- **Mốc `iris_y` theo tài xế (M56):** bước nhìn đường của đăng ký ghi `DriverProfile.road_iris_y`, khối 8 dùng nó thay cho 5 s
  đầu lúc xe chạy. Trên bản tự ghi và 3MDAD số đo không đổi, vì 5 s đầu ở đó cũng là nhìn đường. Mốc của 50 tài xế 3MDAD
  trải từ −0,14 tới −0,05, nên một mốc chung cho mọi người là không dùng được.
- **Bản đêm hồng ngoại `IR2` của 3MDAD không dùng được (M56):** MediaPipe tìm ra mặt ở 3–8 % số frame (19 tài xế, thử bốn
  cách đổi ảnh 16 bit sang 8 bit).

**Còn lại:**
1. Dữ liệu lái thật có nhãn lúc nhìn xuống (chuyến thật, hoặc người thứ hai ở [việc 4](#viec-prd)) trước khi nghĩ tới luật.
2. Hệ số `iris_gain` theo từng tài xế: bước nhìn đường không cho được, cần thêm một bước "nhìn xuống" vào đăng ký. Chốt
   09/10: không thêm, đăng ký giữ nguyên; `iris_gain` vẫn là một hệ số chung.
3. Liếc ngang chỉ bằng mắt (màn hình giải trí): chưa có dữ liệu và chưa có tín hiệu.
4. Người đeo kính và ảnh IR: chưa có dữ liệu dùng được.
5. Đưa `gaze_down_duration` vào metadata và bảng tổng kết chuyến (hiện chỉ có trong trace), khi đã quyết định giữ.

---

<a id="viec-viddd"></a>

### Bối cảnh hai việc về mất tập trung: repo ViDDD

Nguồn: [V1], đọc README và code ngày 05/10, không chạy thử.

- **Là gì:** ViT-Base chạy trên từng frame, gom 70 frame một clip rồi bỏ phiếu (code huấn luyện có thêm
  GRU). Train trên bản "lite" của DMD, 2 446 clip, 14 lớp: an toàn, gọi điện trái / phải, nhắn tin trái /
  phải, uống nước, trang điểm, chỉnh radio, với ra ghế sau, với sang bên, nói chuyện với hành khách, sang
  số, đứng chờ, không xác định.
- **Kết quả họ báo:** accuracy 99,6 % train, 94,2 % validation. Không có precision / recall theo lớp,
  không có báo sai / giờ. *Chưa kiểm tra* cách chia train / validation có tách theo người không.
- **Vì sao không dùng lại được:** Raspberry Pi gửi từng frame lên server (trái "không gửi ảnh khuôn
  mặt"); ViT-Base, kết quả trễ 5 s (trái "không model nặng", ≥ 15 FPS); phải tự train, repo không kèm
  trọng số (trái "chỉ pretrained"); camera đặt phía ghế phụ nhìn ngang thân người, không phải camera
  hướng mặt. Repo không có license, cập nhật cuối 10/2022.
- **Lớp của họ không làm:** uống nước (đã bỏ 02/10, [phụ lục H](#phu-luc-h); repo không đưa lý do mới);
  trang điểm, chỉnh radio, sang số (cần thấy tay hoặc bảng điều khiển, camera hướng mặt không thấy, nhận
  diện tay là thêm model); nói chuyện với hành khách (không đáng cảnh báo riêng, quay đầu lâu thì
  `off_road` đã bắt).
- **Về dataset:** xác nhận [DMD](#dmd) là nguồn có nhãn mất tập trung theo clip. Bản "lite" họ dùng là
  camera thân người; DriverGuard cần **camera mặt** của bộ Distraction, nếu không thì gặp lại vấn đề sai
  góc như State Farm. Các lớp uống nước, trang điểm, với tay là ca dễ nhầm để đo báo sai của `phone` và
  `off_road`.

- V1. https://github.com/jackfromeast/ViDDD-Video-based-Distracted-Driver-Detection

---

<a id="viec-cnn-toi"></a>

### Việc 8: khối 5 khi mặt tối, ngưỡng `eyeBlink` trên `#/live`

**Đã sửa ([M54](roadmap.md#m54)):** `eye_state.low_light_brightness` 60 → 0. Mặt tối thì EAR (kèm phiếu `eyeBlink`) quyết
định, không giao cho CNN. Bản tự ghi ở mặt 32–35: 8 lần L3 sai → 0, nhắm mắt đạt L3 27 / 27; FL3D làm tối nhẹ trong RAM:
microsleep đạt L3 0 / 24 → 12 / 24. Một người, một webcam: ngưỡng tạm.

**Còn lại (làm được bằng webcam):**
1. **Ngưỡng `eyeBlink` của bản web:** replay cho nhắm mắt đạt L3 0 / 48 → 46 / 48 và FL3D 0 / 95 → 64 / 95 (đường EAR của thiết bị: 74 / 95), nhưng đo bằng replay trên video màu, *chưa đo trên `#/live`*. Ngưỡng vẫn là tạm.
2. Mặt sáng 12–32 chưa có phiên nào: 32–35 đọc được, 10–12 thì không (tắt giới hạn thì 5 lần L3 sai trong 2,9 phút), nên `quality.dark_face_brightness` 25 vẫn là tạm.
3. Sau mỗi thay đổi: chạy lại `tools/light_study.py` và test hồi quy trace.

**Không còn nguồn đo (08/10, [phụ lục H](#bo-hub)):** ảnh xám / hồng ngoại thật (thiết bị ảnh xám vẫn giao cho CNN và FL3D bỏ màu đạt 0 / 24; chưa quyết định giữ CNN, để EAR quyết định hay báo "không đọc được mắt"), MediaPipe trên ảnh IR (3MDAD chỉ tìm ra mặt ở 3–8 % số frame, camera khác). Muốn quyết thì cần camera IR.

**Đã sửa ([M98](roadmap.md#m98)):** ảnh màu tối không còn bị khối 2 nhận là hồng ngoại (độ chênh kênh phải nhỏ cả so với độ sáng; loại camera giữ theo thời gian). Còn lại của phần đó: một phiên tự ghi giảm sáng dần, có thêm cột độ chênh kênh trong trace, để kiểm mốc 3 % trên webcam thật.

**Liên quan:** [FMEA](safety-fmea.md) dòng 16, [mắt bị che](#viec-mat-bi-che) (hoãn), ánh sáng (đã bỏ).

**Độ nên làm: trung bình.** Đo ngưỡng `eyeBlink` trên `#/live` bằng webcam là việc làm được; phần IR không còn nguồn đo.

---

<a id="nhom-hieu-nang"></a>

### Hiệu năng bản web (việc 9): số đo và cách đọc

**Hai loại độ trễ, tối ưu theo hai cách khác nhau:**
- **Độ trễ xử lý một frame** (PRD NFR-2: p95 ≤ 200 ms; CLAUDE.md: ≥ 15 FPS): do model và code.
- **Độ trễ cảnh báo** (PRD: time-to-alert p95 ≤ 3 s): gần hết là thời gian chờ có chủ ý của luật để chống
  báo sai (nhắm mắt 1,5 s, nhìn lệch 2,0 s + xác nhận 0,5 s). Xử lý nhanh hơn 10 ms không làm cảnh báo đến
  sớm hơn đáng kể; phần cắt được mà không đụng tới báo sai là các khoảng chờ nằm ngoài luật
  ([việc 9](#viec-tre-canh-bao)).

**Thời gian mỗi chặng, trên cùng một máy Mac ARM:**

| Chặng | Bản thiết bị (Python) | Bản web / APK | Ghi chú |
|---|---:|---:|---|
| 2 lấy frame, đổi cỡ | 0,69 ms | 0,5–1,8 ms | Web: vẽ ra canvas rồi đọc lại pixel |
| 3 MediaPipe | 5,8 ms | 8,9 ms (CPU) · 10,4 ms (GPU thật) | Trước M51 trên máy không có GPU thật: 45 ms |
| Đo pixel (độ sáng, IR, độ nét) | trong khối 2 và 6 | 0,2 ms | |
| 6–14 (đặc trưng, quyết định, HUD, JSON) | 0,15 ms | 0,9–1,2 ms | Trong Node: 0,61 ms; trước M49: 1,97 ms |
| 4 YOLO, mỗi lần chạy | 16,8 ms (2 luồng) | **16 ms** (WebGPU, GPU thật) · 91 ms (2 luồng wasm) | Trước M67: 91–94 ms ở cả hai; trước M51: 172 ms, một luồng. Tuổi kết quả khi dùng p95: WebGPU khoảng 100 ms, wasm 267 ms (trước M67: 333; hạn 600) |
| Cả vòng lặp | 107 FPS khi có mặt | 10,7–13,5 ms mỗi frame, 30 FPS | 0–3 % frame camera không được xử lý (nhịp của `requestVideoFrameCallback`, không phải do bận) |

- Cột bản web: [`eval/results/benchmark_live.md`](../eval/results/benchmark_live.md) (M51, M67), bản build thật trong
  Chromium không giao diện với camera giả phát một clip YawDD có mặt; hai giá trị là máy vẽ WebGL bằng
  phần mềm và máy có GPU thật. Số p50.
- Dòng 6–14 trong Node: [`benchmark_web.md`](../eval/results/benchmark_web.md) (M49).
- Node cùng engine V8 với Chrome / WebView nhưng không phải trình duyệt, và Mac không phải hub.
  Phép đo trên máy đích không còn làm được (08/10).

**Đọc bảng:**
- Bản thiết bị không có điểm nghẽn: dư khoảng 7 lần so với 15 FPS, lý do của mục
  [đã bỏ "giảm xử lý từng frame"](#bo-subsampling) vẫn đúng.
- Bản web là sản phẩm (APK). Sau M49–M51 và M67, trên Mac nó chậm hơn bản thiết bị khoảng 1,5–2 lần ở MediaPipe,
  6 lần ở Python; YOLO ngang bản thiết bị khi có GPU thật (WebGPU) và chậm 5 lần khi không có (wasm). Giữ được
  30 FPS của camera. Trên máy đích (nhân chậm hơn, chưa biết có WebGPU) chưa có số nào và sẽ không có (08/10).
- Bài học của M51: cùng một máy, cùng code, model mặt chạy 45 ms hay 9 ms tuỳ WebGL có GPU thật hay không. Máy
  chạy có GPU thật không, và trình duyệt có dùng GPU đó không, là câu hỏi đầu tiên khi đọc số đo
  ("Chi tiết kỹ thuật" của `#/live` nay ghi rõ điều này).
- Không đề xuất nào ở đây bỏ frame của MediaPipe hay thêm model: các việc dưới bỏ phần tính thừa, phần sao
  chép thừa và phần chờ thừa.

**Về độ chính xác:** việc còn lại của nhóm không đụng tới độ chính xác. Đòn bẩy lớn nhất về độ chính xác vẫn là các việc
[5](#viec-prd), [9](#viec-cnn-toi) và [phần còn lại sau UTA-RLDD](#viec-toi-uu-nguong).

---

<a id="viec-tre-canh-bao"></a>

### Việc 9: độ trễ cảnh báo, phần còn lại

**Độ nên làm: trung bình.** Số đo sát mốc 3 s của PRD; thử `rise_confirm_s` làm được ngay trên bản ghi có sẵn.

**Độ trễ theo thiết kế (từ `thresholds.yaml`) và số đo đầu tiên:**

| Cảnh báo | Luật | Xác nhận (`alert.rise_confirm_s`) | Tới lúc phát cảnh báo | Đo M52 (từ lúc bấm phím) | Cộng thêm ở HUD của bản thiết bị |
|---|---|---:|---:|---:|---:|
| `microsleep` L3 | nhắm ≥ 1,5 s | 0 | 1,5 s | p50 1,56 s, p95 1,67 s (11 lần) | 0–0,3 s |
| `off_road` L2 | lệch ≥ 2,0 s (1,5 s trên 80 km/h) | 0,5 s | 2,5 s | 2,83–3,04 s (5 lần quay đầu) | 0–0,3 s |
| `phone` L2 | ≥ 60 % mẫu trong 2 s, tức ≥ 1,2 s | 0,5 s | ≈ 1,7 s + chờ YOLO | 2,30–2,77 s (8 lần) | 0–0,3 s |

- Số đo lấy từ [`own_recordings.md`](../eval/results/own_recordings.md): tính từ lúc bấm phím tới lúc khối 12
  phát cảnh báo, **chưa gồm** thời gian tới tai tài xế. Người ghi bấm phím rồi mới quay đầu, nên số `off_road`
  gồm cả thời gian quay; hai trong năm lần vượt 3 s (3,03 và 3,04 s).
- Bản web / APK đã đẩy cảnh báo ngay và dùng giờ chụp của frame ([M50](roadmap.md#m50)); cột cuối của bảng chỉ
  còn đúng với HUD của bản thiết bị. Lợi ích của phần đẩy chưa đo được bằng số (xem mục 4).

**Còn lại:**
1. **HUD của bản thiết bị** (`#/hud` qua HTTP `127.0.0.1`) vẫn hỏi mỗi `hud.poll_s` (0,3 s, khoá YAML từ M85) rồi mới phát âm thanh:
   hỏi dày hơn khi đang có mức > 0, hoặc `GET /state` giữ kết nối tới khi có thay đổi. Ưu tiên thấp vì sản phẩm
   là APK.
2. **`rise_confirm_s` của L2, chỉ thử nghiệm:** luật `off_road` đã đòi 2,0 s liên tục (có `on_road_confirm_s`
   0,3 s), rồi khối 12 đòi thêm 0,5 s: 20 % độ trễ là lớp lọc thứ hai. Chạy lại bản ghi của
   [việc 4](#viec-prd) bằng `seq_eval --replay --set` với 0,5 / 0,25 / 0 s, đếm cảnh báo ngoài nhãn. Chỉ đổi
   nếu số báo sai không tăng; CLAUDE.md đặt chống báo sai ngang độ chính xác. Xác nhận tăng đo bằng dấu thời gian:
   trước [M71](roadmap.md#m71) hai frame ở hai bên một lần vòng lặp đứng đã đủ xác nhận, nên rút ngắn khi đó sẽ tăng
   báo sai. Từ M71 khối 12 đếm lại sau khoảng hở quá `max_gap_s`; khi thử phải chạy cả các chuỗi có khoảng hở và
   vòng lặp chậm của `tests/test_edge_agent/test_m75_low_fps.py`, không chỉ bản ghi 30 FPS đều.
**Không còn làm (08/10):** đo độ trễ từ lúc có cảnh báo tới lúc loa của hub kêu, và cột "tới tai tài xế" trong báo cáo của `tools/record_trace.py` (cả hai cần thiết bị thật).

**Không đề xuất:** hạ `microsleep_l3_s`, `off_road_s`, `phone_ratio`. Đó là quyết định về báo sai, cần dữ
liệu của [UTA-RLDD (M53)](#viec-toi-uu-nguong) và [việc 4](#viec-prd), không phải việc tối ưu tốc độ.

---

<a id="viec-outbox-web"></a>

### Việc 10: hàng đợi offline cho app

**Độ nên làm: thấp.** Chỉ có ý nghĩa khi app thật chạy trên xe; trên web làm để đóng nốt FMEA mất mạng.

- Bản Python trên thiết bị có outbox SQLite; code web (cũng là code của APK) chỉ giữ trong RAM, nên hub
  mất mạng giữa chuyến rồi app bị tắt thì sự kiện / bản tổng kết chưa gửi được bị mất (M15 đã báo rõ
  trên HUD).
- Lưu các batch chưa gửi trong bộ nhớ của app (IndexedDB trong WebView, hoặc plugin lưu trữ của
  Capacitor), gửi lại khi mở app / có mạng, có giới hạn số bản ghi. Chỉ metadata.
- Làm trên web bằng IndexedDB, thử bằng cách tắt mạng trong DevTools; APK đã bỏ (08/10).
- ~~Phải làm trước: phiên đăng nhập hết hạn sau 60 phút~~: đã làm ở [M97](roadmap.md#m97) (trang gia hạn token trong chuyến,
  lô bị từ chối chỉ mất bản ghi hỏng, `POST` có hạn chờ). Còn một ca mà chỉ hàng đợi bền mới cứu được một phần: mất mạng
  vắt qua lúc token hết hạn thì lô vẫn nhận 401 khi có mạng lại; lưu trong IndexedDB giữ được dữ liệu tới lần đăng nhập sau.

---

<a id="phan-hoan"></a>

## Hoãn

<a id="viec-toi-uu-nguong"></a>
<a id="viec-ablation"></a>
<a id="viec-ca-nhan-hoa"></a>
<a id="viec-holdout"></a>
<a id="viec-do-bao-sai"></a>

### Hoãn: phần còn lại sau UTA-RLDD (M53)

**Đã làm ([M53](roadmap.md#m53), 06/10):** trace 145 video UTA-RLDD (48 người, 25 giờ), chia dev / test theo
người, dò ngưỡng và ablation trên dev, chấm một lần trên test, đo cá nhân hoá. Kết quả:
[`eval/results/dataset_uta_rldd.md`](../eval/results/dataset_uta_rldd.md),
[`eval/results/personalization_uta_rldd.md`](../eval/results/personalization_uta_rldd.md). Đã đổi: trọng số chớp
chậm và nhướn mày về 0, luật `trend` về "chỉ ghi nhận". Công cụ: `tools/uta_rldd.py`.

**Vì sao phần còn lại phải hoãn:** đều cần dữ liệu lái thật hoặc dataset khác, UTA-RLDD (người ngồi trước
laptop, video 10 phút, nhãn cả video) không trả lời được.

- **Chỉ tiêu PRD ≤ 1,0 báo sai / giờ vẫn chưa kết luận được.** Trên 24 người giữ riêng: 0,98 / giờ ở nhánh buồn ngủ (cận trên CI
  95 % là 2,51), 1,2 / giờ khi đếm mọi nhánh cả video (cận trên 2,7). Cần giờ lái thật có nhãn ([ghi nhãn khi demo](#bo-hub)).
- ~~`risk.drowsy.l1` 40 → 50~~: quyết ở [M101](roadmap.md#m101) trên DROZY, bằng luật viết trước khi chạy
  ([`eval/splits/drozy_l1_rule.md`](../eval/splits/drozy_l1_rule.md)): **giữ 40**. Ở cả hai giá trị không có báo sai nào trên 2,33 giờ video
  tỉnh; 50 làm một video buồn ngủ mất cảnh báo ([`drozy_l1.md`](../eval/results/drozy_l1.md)). Mở lại chỉ khi có giờ lái thật có nhãn.
- **Luật `trend` trên chuyến dài:** được thiết kế cho chuyến hàng giờ, UTA-RLDD chỉ 10 phút. Bật lại
  (`risk.trend.level: 1`) khi có chuyến dài cho thấy nó có ích.
- **Trọng số gục đầu và ngáp:** sự kiện quá hiếm khi ngồi trước laptop (AUC 0,46–0,67), không kết luận được.
- **PERCLOS P80:** không tách tốt hơn định nghĩa hiện tại trên UTA-RLDD (AUC 0,873 so với 0,892 trên test), nên
  giữ `perclos_close_ratio` 0,65.
- **Ngưỡng "tạm" khác chưa có số chứng minh:** các bước đăng ký 2 s / 3 s / 2 s, ngưỡng chữ ký mặt 0,08, phép
  thử gục / cúi (đang tắt).
- **Cá nhân hoá:** mốc đăng ký giả không giảm báo sai trên UTA-RLDD (9 / 9 / 9 lần trên 48 người) cũng như trên
  YawDD (M40). Không làm ngưỡng riêng theo tài xế, không giữ mốc qua nhiều chuyến, cho tới khi có số khác.
- **Tập kiểm tra giữ riêng cho dataset khác:** UTA-RLDD đã có (`eval/splits/uta_rldd_{dev,test}.txt`). YawDD,
  FL3D, SUST vẫn là "dev" (đã dùng để chỉnh ngưỡng); `tools/eval.py` chưa có `--split`. DMD nếu dùng thì chia từ đầu.
- **Thuộc tính người (kính, IR / RGB):** bản Kaggle của UTA-RLDD không có, nên chưa gộp được theo nhóm.
- **Microsleep / L3 không chỉnh bằng UTA-RLDD** (không có nhãn theo đoạn): kiểm tra bằng FL3D, bản tự ghi, DMD.

<a id="viec-theo-nguoi"></a>

**Chỉ số theo từng người khi chạy thật (online), chưa làm:**

- **Không tính được FAR / MAR đúng nghĩa:** ngoài đường không có nhãn. Lần bỏ sót thì không ai thấy
  (không có cảnh báo để bấm), nên MAR theo từng tài xế không đo được. Muốn có số đúng thì phải là
  chuyến demo có người ghi nhãn ([việc đã bỏ 08/10](#bo-hub)).
- **Đo được:** số lần tài xế bấm "báo sai" / giờ lái, theo từng tài xế và từng lý do. Backend đã có
  `driver_id` trên sự kiện và `by_reason` trong `/api/v1/stats`; còn thiếu số giờ lái theo tài xế làm
  mẫu số (lấy từ sample mỗi phút) và phần tách theo tài xế.
- **Tín hiệu bị lệch:** tài xế không bấm mọi lần báo sai (số thấp hơn thực tế), và có thể bấm để tắt
  chuông khi buồn ngủ thật. Vì vậy:
  - Chỉ dùng để **giám sát**: hiện trên dashboard kỹ sư, gắn cờ tài xế có tỉ lệ bấm cao để xem lại
    timeline.
  - **Không tự hạ ngưỡng** theo feedback. Nếu sau này muốn tự chỉnh: có giới hạn cứng, chỉ cho lý do ít
    rủi ro (`phone`, `off_road`), không bao giờ cho microsleep / `drowsy_score`; là quyết định riêng.

---

<a id="viec-mat-bi-che"></a>

### Hoãn: phát hiện mắt bị che (kính râm)

**Vì sao hoãn (06/10):** phiên tự ghi có kính râm đã bỏ, NTHU-DDD không tải được, nên không có dữ liệu nào để
đo. Dòng 5 của [FMEA](safety-fmea.md) vẫn mở ở mức Cao, chưa kiểm chứng. Làm lại khi có dữ liệu kính râm.

- **Vì sao (FMEA dòng 5, chưa kiểm chứng):** MediaPipe vẫn trả landmark mắt khi đeo kính râm. CNN mắt
  chỉ chạy khi tối / IR / hai mắt lệch, nên EAR "đoán" có thể luôn là mở: PERCLOS, microsleep, chớp chậm
  đều im mà hệ thống không biết.
- **Cách làm (chưa thử):**
  - Đo trước: một bản ghi có kính râm và nhãn nhắm mắt (phiên tự ghi đã bỏ 06/10), xem EAR / eyeBlink có
    đổi khi nhắm không. Chưa có dataset kính râm nào.
  - Nếu đúng là "luôn mở": thấy mặt mà không có lần chớp nào trong một khoảng dài (vd. 30 s, trong
    `thresholds.yaml`) → không tin trạng thái mắt, HUD báo "không đọc được mắt", tách khỏi "tạm ngưng
    giám sát" vì nhánh mất tập trung vẫn chạy.
  - Hoặc model SGC (PINTO0309, MIT, 48×48) phân loại kính râm ([việc đã bỏ 08/10](#bo-hub)).
- **Thêm 06/10, từ bảng 4 của [P1] ([phụ lục I](#phu-luc-i)):** trên NTHU-DDD, hai phương pháp dựa vào đặc
  trưng mắt / miệng tụt rõ ở cảnh kính râm so với không kính (HTDBN 92,4 → 76,6 %; 3D DNN 89,1 → 84,2 %). Đây
  là số của hệ khác, nhưng cho thấy rủi ro ở dòng 5 của FMEA là có thật chứ không chỉ là suy đoán. Model nhìn
  cả khuôn mặt của [P1] báo 99,1 % ở cảnh này nhưng phải train và không công bố trọng số, nên không phải lối ra.

<a id="viec-nhip-sinh-hoc"></a>

### Hoãn: mức mệt theo nhịp sinh học

**Vì sao hoãn (02/10):** không có dữ liệu giờ thật để kiểm chứng; thay hệ số 1,2 bằng công thức nhiều tham số chưa chứng minh là trái nguyên tắc [chưa chứng minh thì trọng số 0](#viec-ablation). Làm lại khi có chuyến thật.

- Hiện `drowsy_score` nhân 1,2 cho đêm (0–5 h) và 1,2 khi lái ≥ 2 giờ.
- Thay bằng một hệ số liên tục: giờ trong ngày (vùng trũng 2–6 h và 14–16 h) × thời gian lái liên tục.
  Là công thức, không train; tham số trong `thresholds.yaml`.
- Gợi ý nghỉ ở bảng tổng kết (M15) dùng cùng hệ số.
- Cần dữ liệu có giờ thật (chuyến demo) để kiểm tra; dataset hiện có không có giờ trong ngày đúng nghĩa.

<a id="dang-ky-buoc-c"></a>

### Hoãn: vùng nhìn hợp lệ, nhận mặt bằng model

**Vì sao hoãn (02/10):** chưa có bằng chứng chữ ký mặt hiện tại không đủ; thêm bước vào đăng ký thì đăng ký lâu hơn.

**Cập nhật 08/10 (M83):** đã có bằng chứng đó, xem [phụ lục G](#phu-luc-g): chữ ký hiện tại không phân biệt được
người. Bước D là cách duy nhất để chặn người khác ngồi vào chỗ tài xế; mở lại hay không là quyết định của anh.

**Bước C (tuỳ chọn): các vùng nhìn hợp lệ**
- Tư thế đầu khi nhìn gương / bảng đồng hồ của chính tài xế đó, dùng cho:
  - Gục đầu (M12): cúi đúng về tư thế bảng đồng hồ với mắt mở thì không phải gục đầu.
  - Việc 7 (hướng nhìn): mốc hướng nhìn theo từng vùng.
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
  diễn ([tập kiểm tra giữ riêng](#viec-holdout)). Trace số (EAR, MAR, góc, blendshape, mức, sự kiện
  theo frame) không chứa ảnh nhưng đủ để `seq_eval --replay` dò ngưỡng.
- **Cách làm:**
  - Tài xế bật đồng ý rõ ràng (tắt mặc định); trace nén gửi cuối chuyến kèm bản tổng kết, hoặc giữ trên
    thiết bị đến khi có mạng.
  - Gắn phản hồi "báo sai", nhãn của người ngồi cạnh ([việc đã bỏ 08/10](#bo-hub)), KSS
    nếu có.
  - Có thời hạn lưu và xoá theo yêu cầu; chỉ kỹ sư xem được.
- **Cần quyết định:** landmark 3D chi tiết vẫn có thể là dữ liệu sinh trắc; chỉ lưu các số đã tính (EAR,
  góc…), không lưu 478 điểm.

<a id="viec-vo-lang"></a>

### Hoãn: tín hiệu vô lăng (góc lái qua CAN, cảm biến tay)

**Vì sao hoãn (06/10):** chưa có CAN thật, chưa biết CAN của xe / hub có đưa ra góc lái không; cảm biến tay là
phần cứng mới gắn lên vô lăng; hai bài báo không cho số đo nào dùng lại được. Xem lại khi chốt hub và nguồn CAN
([nhóm phần cứng](#bo-hub)).

- **Nguồn ý:** [P1] gắn cảm biến lực FSR lên vô lăng, hú còi khi tay rời vô lăng hoặc khi model báo buồn ngủ;
  [P2] mục 5.3 liệt kê độ lệch chuẩn vị trí ngang (SDLP), chuyển động vô lăng, thời gian tới lúc cắt vạch.
- **Chỗ có thể có ích cho DriverGuard:** các ca camera không đọc được mắt (kính râm, mặt quá tối) hiện chỉ có
  "tạm ngưng giám sát". Một tín hiệu không phụ thuộc camera là thứ duy nhất nói thêm được gì trong lúc đó.
- **Vì sao chưa đáng làm:**
  - [P2] tự kết luận tín hiệu xe bị nhiễu bởi hình dạng đường, giao thông, gió, thói quen từng người; chỉ dùng
    được khi có mốc riêng theo tài xế và ghép với tín hiệu khác. Bảng 8 của bài chỉ mô tả đặc trưng, không có
    số bắt đúng / báo sai.
  - Vị trí làn (SDLP, cắt vạch) cần cảm biến làn, đã ghi là giới hạn ở [phụ lục E](#viec-ddaw).
  - Cảm biến tay của [P1] mới thử định tính với một người lái; tay rời vô lăng không đồng nghĩa buồn ngủ (lái
    một tay, sang số: *suy luận, bài không đo*), nên là một nguồn báo sai mới.
- **Nếu làm sau này:** khối 10 nhận thêm `steering_angle` từ CAN; khối 6 tính độ dao động trong cửa sổ trượt;
  chỉ đo và ghi, trọng số 0 (nguyên tắc [chưa chứng minh thì trọng số 0](#viec-ablation)); test bằng chuỗi góc
  lái giả. Không thêm phần cứng lên vô lăng.

<a id="viec-rppg"></a>

### Hoãn: nhịp tim đọc từ camera (rPPG)

**Vì sao hoãn (06/10):** bằng chứng trong [P2] yếu và trái nhau; phương pháp nhạy với ánh sáng và chuyển động;
các bản có độ chính xác cao đều train model ghép tín hiệu (trái "chỉ pretrained").

- **Là gì:** màu da mặt đổi rất nhẹ theo nhịp tim; lấy trung bình màu một vùng da qua nhiều giây, lọc dải tần,
  ra nhịp tim và độ biến thiên nhịp tim (HRV). Không cần cảm biến đeo; vùng da chỉ nằm trong RAM nên không
  trái ràng buộc về ảnh mặt.
- **Bằng chứng ủng hộ ([P2] mục 5.4, bảng 10; chưa đọc bài gốc):** Bi 2023, 10 người, ngưỡng trên LF / HF,
  không báo độ chính xác; Kong 2024, 98,2 % trên dataset tự làm, camera hồng ngoại, có train; Siyang 2024,
  93,2 % (91,7 % khi ánh sáng khó), có train.
- **Bằng chứng ngược, cũng trong [P2]:** Srinivasan 2024 (84 người, lái mô phỏng, điện tim thật chứ không phải
  camera): RMSSD giải thích 6,4 % phương sai của mệt mỏi, LF / HF 3,7 %. Kundinger 2020 (HRV từ vòng đeo tay):
  92 % khi model biết người đó, 73–79 % với người mới. Tín hiệu gốc đã yếu như vậy thì bản đọc qua camera
  trong xe rung khó tốt hơn (*suy luận*).
- **Ràng buộc kỹ thuật:** cần tốc độ khung hình đều qua cửa sổ hàng chục giây; bản web hiện bỏ 2–7 / 300 frame
  (M51). Camera IR của hub cho ảnh một kênh, *chưa biết* có đủ tín hiệu không.
- **Điều kiện xem lại:** có hub và camera thật, và có một bài đo rPPG trong xe chạy thật với người chưa từng
  thấy. Khi đó vẫn là "chỉ đo, trọng số 0" trước.

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
| Kết luận đạt PRD | **Cảnh báo sai / giờ theo từng người**, có nhãn | Chuyến demo có người ghi nhãn ([việc đã bỏ 08/10](#bo-hub)) |
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
   khởi động. Tốc độ giả lập cố định 60 km/h nên luật ngữ cảnh (dừng đèn đỏ, xi-nhan) không được thử; giờ và thời gian
   đã lái thì từ [M73](roadmap.md#m73) chọn được (`eval.replay_clock_hour`, `eval.replay_drive_time_s`).
3. **Định nghĩa "sai" trộn nhiều loại lỗi.** Sai = cảnh báo trên đoạn nhãn tỉnh táo, nhưng dataset chỉ
   gán nhãn buồn ngủ, không gán mất tập trung. SUST: 24/26 lần "sai" là `off_road` khi tài xế quay đầu
   thật, có thể là cảnh báo đúng hoặc chỉ ngưỡng hơi chặt.
4. **Đứng một mình thì dễ bị lừa:** hệ thống không bao giờ cảnh báo đạt 0 / giờ. Phải đi cùng MAR
   ([M18](#viec-far-mar), đã có), tỉ lệ bắt sự kiện và time-to-alert (PRD p95 ≤ 3 s, công cụ đo là `tools/record_trace.py`,
   xem [việc 9](#viec-tre-canh-bao)).
5. **Số HITL trên dashboard không cùng loại:** `false_alarms / tổng cảnh báo` là precision, không phải
   / giờ, và phụ thuộc tài xế có bấm nút hay không.

<a id="viec-far-mar"></a>

**FAR / MAR theo cửa sổ** (định nghĩa, quy ước ở `docs/release-v2.md`, M18) gần như không đọc được
   trên dataset đang có: FL3D 7 cửa sổ hợp lệ, YawDD 13, SUST 0 (clip 10 s). Cần video dài: UTA-RLDD
   (đã có số ở [M53](#viec-toi-uu-nguong)), DMD.


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
| UTA-RLDD | Cảnh báo sai / giờ (~8 giờ tỉnh táo), buồn ngủ thật theo mức 0 / 5 / 10 | Kaggle 96,6 GB, hoặc Kaggle Notebook | Đã dùng (M53) |
| DMD | Recall theo frame, time-to-alert, ngáp che tay, mất tập trung, hướng nhìn | Cổng DMD, CC BY-NC-ND | Nên dùng |
| DROZY | Buồn ngủ thật + KSS / PVT / EEG, IR phụ | ORBi 2,46 GB, tải thẳng | Nên dùng |
| Brain4Cars | `off_road` khi rẽ / chuyển làn, tốc độ thật | Dropbox 16 GB | Cần xem độ dài clip trước |

#### Phần dữ liệu còn thiếu và nguồn lấp

Đối chiếu dữ liệu đã có / sắp có (FL3D, YawDD, SUST, UTA-RLDD, DMD) với điều kiện PRD FR-9 và các khối.
Đã bỏ khỏi danh sách (chốt 30/09): ngược sáng / đèn pha, mặt người Việt, điện thoại để thấp, khẩu
trang, mũ lưỡi trai, hai người trong khung hình (không cần dataset; chọn mặt tài xế của M9 đã test
bằng landmark giả). Kính râm và video IR kiểu camera DMS không còn nguồn dataset.

| Phần thiếu | Nguồn | Trạng thái |
|---|---|---|
| Kính râm | Không có (phiên tự ghi đã bỏ 06/10) | Hoãn |
| Video IR cả khuôn mặt | DROZY (Kinect NIR, không giống camera DMS) | Chỉ có nguồn phụ |
| Buồn ngủ thật, có số liệu khách quan | DROZY (KSS, PVT, EEG); UTA-RLDD (KSS tự đánh giá) | Có nguồn |
| Gục đầu có nhãn | DMD (diễn) | Có nguồn |
| Xi-nhan, tốc độ, rẽ thật | Brain4Cars | Có nguồn, không có xi-nhan; clip 5 s |

<a id="uta-rldd"></a>

#### UTA-RLDD

Nguồn: Kaggle `rishab260/uta-reallife-drowsiness-dataset` [U1], bản gốc [U2], paper Ghoddoosian et
al., CVPRW 2019. Đã chạy trên Kaggle Notebook ở M53 (06/10): 145 video, 48 người, 25,0 giờ; kết quả ở
[`eval/results/dataset_uta_rldd.md`](../eval/results/dataset_uta_rldd.md). Phần dưới là ghi chú trước khi chạy.

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

Đã dùng để chỉnh ngưỡng buồn ngủ: [M53](#viec-toi-uu-nguong).

**Cần làm nếu chọn (mốc riêng):** task mới trong `tools/dataset.py` (vd. `video_drowsy`, nhãn từ tên
file `0` / `5` / `10`, gộp `10_1` / `10_2`), báo cáo cảnh báo sai / giờ + CI trên video `0` và phân
bố `drowsy_score` theo mức. Nên gộp với phần tách khởi động / đường đánh đổi (đã làm ở M53, `tools/uta_rldd.py`). Thử 1 fold (~12 GB) trước.

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
- **Time-to-alert p95 ≤ 3 s** (việc 6: bản ghi đầu tiên ở M52, một người).
- **Ngáp che tay:** tay che làm landmark miệng / MAR sai; chưa dataset nào khác có nhãn này.
- Bộ Distraction / Gaze: nhãn gọi điện, nhắn tin, vùng nhìn (gương, cửa sổ, bảng đồng hồ) → đo
  `off_road`, `phone` (khối 8) và việc 9 (hướng nhìn).
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
giờ); gộp được với công cụ đo time-to-alert (việc 6).

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

---

<a id="phu-luc-c"></a>

### C. Ánh sáng khó: lái đêm, đèn đường, đèn pha

#### Đã có (cả thiết bị lẫn web, vì web chạy lại khối 5–12 bằng Python qua Pyodide)
- Mặt quá tối (độ sáng vùng mặt, trước CLAHE): từ [M54](roadmap.md#m54) `eye_state.low_light_brightness` = 0, tức
  trigger này tắt và mặt tối vẫn do EAR (kèm phiếu `eyeBlink`) quyết định. Trước M54 ngưỡng là 60: dưới đó khối 5
  thay EAR bằng điểm nhắm mắt (thiết bị: CNN mắt; web: blendshape `eyeBlink`). Mặt dưới
  `quality.dark_face_brightness` (25) thì thành "tạm ngưng giám sát" (M43).
- Ảnh xám / hồng ngoại vẫn giao cho điểm nhắm mắt, và giữ nguồn đó thêm `hold_s` = 2 s sau khi trigger hết: không
  đổi EAR ↔ điểm nhắm mắt qua lại từng frame, không sinh nhắm mắt giả.
- EAR hai mắt lệch nhiều (lóa kính, che một mắt): dùng điểm nhắm mắt (không giữ).
- Mất mặt ngắn hơn `max_gap_s`: đợt nhắm mắt đang đếm không bị xoá; frame `face_conf` < 0,9 bị bỏ.
- Nhận biết ảnh IR / xám qua độ chênh kênh màu (có cả trên web). Ảnh màu rất tối cũng qua phép thử này: hai phiên
  tự ghi tối đọc là IR ở 98–100 % số frame (audit 08/10, A1 H1), chưa sửa.
- Đánh giá đêm: 44 video NITYMED (FL3D), nhưng chạy bản Python có CLAHE, không phải bản web.

#### Chưa giải quyết
- **Đèn pha chiếu thẳng** (vùng mắt cháy trắng, landmark lệch): chốt 01/10 không xử lý bằng phần
  mềm, mà bằng **yêu cầu đầu vào camera** (camera IR + đèn LED IR, xem dưới). Mất mặt do chói thì
  thành `unavailable` theo FR-6 (đã làm ở M10), không còn báo L2 sai.
- **Web không có CLAHE.** Webcam / camera điện thoại tự chỉnh phơi sáng chậm khi ánh sáng đổi đột
  ngột; trình duyệt gần như không cho điều khiển.
- **Giới hạn vật lý:** webcam RGB trong cabin tối gần như không thấy mặt; phần mềm không bù được.
- **Chưa có dữ liệu** đèn pha / đèn đường quét qua; chưa đánh giá riêng đường chạy web ban đêm.

Hướng đề xuất: [việc đã bỏ 08/10](#bo-hub) (tương phản), camera IR (phần cứng, [nhóm sau khi chọn hub](#bo-hub)).

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

Đề xuất thử offline: [việc đã bỏ 08/10](#bo-hub).

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

Không phải việc riêng: dùng trong [việc đã bỏ 08/10](#bo-hub) (ghi nhãn khi demo) và
[M53](#viec-toi-uu-nguong) (UTA-RLDD).

**Vì sao:** bộ eval chưa định nghĩa "cảnh báo đúng lúc" so với lúc tài xế bắt đầu buồn ngủ. `seq_eval`
chấm theo sự kiện (nằm trong đoạn có nhãn ± 1 s) và FAR / MAR theo cửa sổ, nhưng không có luật kiểu
"phải cảnh báo trước hoặc ngay khi KSS đạt 8". EU bắt buộc hệ thống DDAW (driver drowsiness and
attention warning) trên xe mới từ 2022; quy trình thử nằm ở Annex của C/2021/2639 và lấy mốc **KSS ≥ 8**
(Ahlström & Anund 2025 [D1] xác nhận). KSS là thang tự đánh giá 1–9 của Åkerstedt & Gillberg 1990 [D2].

**Chưa kiểm chứng (cần đọc Annex trước khi dùng):** độ nhạy trung bình > 40 %, > 20 % cho > 95 % người,
≥ 10 sự kiện KSS ≥ 8, KSS hỏi mỗi 5 phút. Mới thấy qua bản tóm tắt thứ cấp; PMC và EUR-Lex không đọc
được ngày 02/10. Khoảng thời gian một cảnh báo được tính là "đúng lúc" cũng lấy từ Annex.

**Áp dụng:**
- **Ghi nhãn khi chạy thử (đã bỏ 08/10):** KSS hỏi miệng mỗi 5 phút (thay 15 phút). Cảnh báo đúng = có cảnh báo buồn ngủ trong
  khoảng quanh lần đầu KSS ≥ 8 (độ dài theo Annex, nằm trong `thresholds.yaml` của công cụ eval).
- **UTA-RLDD (M53):** video `10` của UTA-RLDD ≈ KSS ≥ 8 (mức `5` ≈ KSS 6–7). Chỉ là xấp xỉ: một nhãn cho cả
  video, không biết lúc nào đạt 8. Bảng riêng, không dùng để chọn ngưỡng.
- **Luôn kèm báo sai / giờ:** độ nhạy chỉ đếm cảnh báo được, không đếm báo sai. CLAUDE.md đặt chống báo
  sai ngang độ chính xác, nên không báo cáo độ nhạy một mình.

**Giới hạn:**
- **Không tự tạo đủ sự kiện KSS ≥ 8 trên đường thật.** Ahlström & Anund [D1] phải dùng tài xế chuyên
  nghiệp, chạy đêm sau khi thức từ sáng sớm, trong nghiên cứu có kiểm soát, và viết rằng đạt mức này ban
  ngày trên đường thật là *"problematic… from legal and ethical perspectives"*. Khớp với giới hạn an
  toàn của [việc đã bỏ 08/10](#bo-hub): demo chủ yếu đo báo sai. Số sự kiện KSS ≥ 8 thật gần như chắc
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

- Chữ ký mặt (tỉ lệ landmark) **không phân biệt được người** (đo 08/10 ở M83, DROZY 14 người): khoảng cách chữ
  ký / 0,08 của người lạ có p50 0,62, của chính người đó ở ngày khác 0,57. Việc chọn giữa hai mặt và ngưỡng loại
  hành khách (`landmarks.driver_max_distance`, M83) vì vậy chỉ dựa trên vị trí. Vẫn chưa có bản ghi hai người
  trong xe: khoảng cách tới ghế phụ ở góc lắp thật chưa đo.
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

<a id="viec-liec-don"></a>

#### Cảnh báo cho nhiều lần liếc ngắn cộng dồn

Quyết định 06/10: **không bật luật cảnh báo.** `off_road_ratio` và `glance_count` (M38) vẫn được đo và ghi vào metadata,
bảng tổng kết chuyến và trace; không luật nào đọc. Lý do: số đo bắt đúng mới có một người diễn, phía báo sai chưa đo
được trên người lái thật (YawDD xe đỗ đã có 6 % clip vượt 0,3), và không nguồn nào cho ngưỡng dùng thẳng được.

**Phiên `glances` (06/10, một người): số đầu tiên cho phía bắt đúng.**

| | Liếc lặp lại 30 s (4 lần) | Nhìn gương 1 s (12 lần) | Mọi lúc khác của 13 phiên |
|---|---:|---:|---:|
| Cảnh báo hiện tại | 0 | 0 | – |
| `off_road_ratio` cao nhất | 0,55–0,67 | 0,00 | 0,14 (0,21 ngay sau một lần nhìn lệch dài) |
| Số lần liếc đếm được | 14–18 | 0 | tối đa 6 |
| Lần nhìn lệch dài nhất | 1,3–1,8 s | – | – |

- Tỉ lệ vượt 0,3 sau khoảng 15 s, vượt 0,5 sau 23–27 s. Bộ đệm 2 s kiểu AttenD (trừ khi nhìn lệch, cộng lại sau 0,1 s nhìn
  đường) cạn sau 4–8 s: nhanh hơn nhiều, và là dạng có nguồn.
- Cần đọc dè dặt: người ghi nhìn gương chỉ quay đầu 10–21°, dưới ngưỡng 30°, nên không được tính là liếc; liếc lặp lại thì
  quay 40–57°. YawDD (xe đỗ, không ai mất tập trung) có 18 / 315 clip vượt 0,3.

**Nguồn đã đọc tối 06/10:**
- NHTSA, Visual-Manual Driver Distraction Guidelines (Federal Register 26/04/2013) [L1]: một tác vụ trên thiết bị
  trong xe nên làm xong với từng lần rời mắt khỏi đường không quá 2 s và tổng thời gian rời mắt không quá 12 s. Là
  hướng dẫn tự nguyện cho thiết kế thiết bị, tính theo từng tác vụ, không phải theo cửa sổ thời gian. *Chưa đọc được*
  nguyên văn tiêu chí theo tỉ lệ người thử (trang gốc chặn truy cập tự động).
- AttenD, Kircher & Ahlström 2009 [L2]: bộ đệm 2 s, giảm khi nhìn khỏi đường, tăng khi nhìn lại, cạn thì coi là mất
  tập trung; bắt được cả một lần nhìn lâu lẫn nhiều lần liếc ngắn. Mới đọc tóm tắt; *chưa đọc được* các chi tiết về
  độ trễ khi hồi bộ đệm và cách xử lý gương / đồng hồ tốc độ.
- Hệ quả: không nguồn nào cho một ngưỡng `off_road_ratio` trong 30 s. Nếu làm giai đoạn 2, bộ đệm kiểu AttenD là
  dạng luật có nguồn hơn tỉ lệ trong cửa sổ; vẫn cần phiên `glances` hoặc dữ liệu có nhãn để đo báo sai khi nhìn gương.

- L1. https://www.govinfo.gov/content/pkg/FR-2013-04-26/html/2013-09883.htm
- L2. https://bibliotek.vti.se/bib/279091

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
- **Hai trong ba cách đã có:** YOLO ~5 lần / s trên luồng riêng (`phone.target_fps: 5`); CNN mắt chỉ
  chạy khi EAR không tin được (`always_run: false`). Gom lô trong cửa sổ PERCLOS không lợi gì vì phần
  tính PERCLOS gần như không tốn.
- **Bỏ frame MediaPipe làm hỏng tín hiệu khác:** đo chớp (M11) cần
  25–30 FPS, sai số thời gian mở mắt đã ≤ 40 / 60 ms ở 30 / 15 FPS; microsleep → L3 ở 1,5 s trễ thêm mỗi
  frame bị bỏ; phân biệt gục / cúi dựa vào tốc độ hạ đầu.
- Chỗ có ích duy nhất là khi hub tụt FPS: thứ tự hạ tải ở trên.

[S1] Salas Yupanqui et al. Accuracy–latency trade-offs and absent embedded validation in deep learning
driver drowsiness detection: a PRISMA systematic review. Front Artif Intell 2026.
https://doi.org/10.3389/frai.2026.1871926 (PMC13572618)

<a id="bo-video-truc-tiep"></a>

#### Đưa thẳng thẻ video cho MediaPipe (bản web)

- Đề xuất (06/10): `detectForVideo(video)` thay cho `detectForVideo(canvas)`, để bỏ một lần nạp canvas CPU lên
  GPU mỗi frame.
- Bỏ (M51, 06/10) vì đo không thấy lợi, Chromium trên Mac có GPU thật, 12 giây mỗi lần: delegate GPU 10,4 ms
  (canvas) so với 11,1 ms (video); delegate CPU 15,2 so với 14,8 ms
  ([`benchmark_live.md`](../eval/results/benchmark_live.md)). Canvas vẫn cần cho các số đo pixel.
- Xem lại nếu số đo trên máy đích cho thấy bước "lấy ảnh từ camera" chiếm phần đáng kể của frame.

#### Đọc thành tiếng cảnh báo L2 / L3

- Làm thử trong M23 (đọc câu hành động của L2 / L3, đọc khi mất camera / tạm ngưng giám sát) rồi gỡ theo yêu cầu 02/10: "không cần nói, cảnh báo thôi". Giọng nói của bước đăng ký giữ nguyên.

#### Uống nước / ăn khi lái

- Đề xuất cũ: dùng lớp `cup` / `bottle` có sẵn của YOLOv8n (COCO), không train.
- Bỏ (02/10): hành vi không nguy hiểm rõ ràng, lại thêm một nguồn báo sai, trái ưu tiên chống báo sai.

#### Hai model (sóng não + mặt) để chấm điểm buồn ngủ

- **Hai model (sóng não + mặt → chỉ mặt) để chấm điểm buồn ngủ:** phải train, vi phạm "chỉ dùng
  pretrained". Risk engine dạng luật hiện tại vẫn là lựa chọn đúng.

#### Tốc độ GPS, NTHU-DDD, khẩu trang (06/10)

- **Tải thử NTHU-DDD:** bỏ vì không tải được dataset. Kéo theo: kính râm không còn nguồn đo (phiên tự ghi cũng bỏ 06/10), video IR chờ
  camera IR của hub.
- **Phiên tự ghi chói / ngược sáng và phiên kính râm:** bỏ theo quyết định 06/10. Phần chói chỉ có số nhân tạo
  của M46; yêu cầu đầu vào vẫn là camera IR của hub. Việc phát hiện mắt bị che chuyển sang [hoãn](#viec-mat-bi-che).
- **Khẩu trang (miệng bị che):** bỏ theo quyết định 06/10.
- **Tốc độ GPS khi chưa có CAN:** bỏ rồi thêm lại trong ngày 06/10 thành [việc 3](#viec-gps), sau khi chốt thiết bị
  đích là Android box của VF e34 (không có CAN).

<a id="bo-hub"></a>

#### Mọi việc cần hub hoặc xe thật (08/10)

**Quyết định (08/10):** không còn hub của xe và không còn xe thật để kiểm chứng; chỉ mô phỏng trên web. Mười hai việc dưới
đây chỉ làm hoặc kiểm chứng được trên thiết bị đích hoặc trên đường, nên bỏ khỏi danh sách (nội dung chi tiết nằm trong lịch sử git
của file này, trước ngày 08/10). Phần đã làm được thì vẫn nằm trong code và `eval/results/`.

| Việc đã bỏ (số cũ) | Cần gì | Còn lại trong repo |
|---|---|---|
| Đo tài nguyên phần cứng (7), đo bản web / APK trên máy đích (8), bản Python trên thiết bị: camera và chạy dài (9) | Thiết bị Android của VF e34, camera USB | `tools/benchmark.py`, `tools/edge_sim.py` (`simulated`, M42), "Chi tiết kỹ thuật" của `#/live`, `tools/bench_web.py`, `frontend/bench/live.bench.mjs`; số đo đều là Mac |
| Đóng gói app APK (10), OTA model (12) | Thiết bị, và kết quả đo của việc 7–8 | OTA ngưỡng đã xong (M41, M47); OTA model chưa làm |
| Thử model mắt mới (16), tăng tương phản cho camera RGB (17) | Camera IR hoặc RGB của hub | Nghiên cứu ứng viên ở [phụ lục D](#phu-luc-d), [phụ lục C](#phu-luc-c) |
| Còi / LED rời (18) | Cổng USB / Bluetooth của thiết bị | Ý tưởng P-196 (ESP32 qua UART); FMEA dòng 1 và 4 vẫn mở |
| Eval theo ánh sáng bằng ảnh IR thật (6) | Camera IR | Bảng theo độ sáng (M40), cùng video làm tối / chói (M46), mặt tối thật từ năm phiên tự ghi (M54) |
| Ghi nhãn trực tiếp khi chạy thử (24), so sánh nhiều chuyến (25) | Xe, người ngồi cạnh, nhiều giờ lái | Chỉ tiêu PRD ≤ 1,0 báo sai / giờ vẫn **chưa kết luận được**: dựa vào trace UTA-RLDD, FL3D, 3MDAD và bản tự ghi, kèm CI của việc 1 |

**Hệ quả:** thiết bị đích còn lại ở [phụ lục J](#phu-luc-j) như danh sách rủi ro chưa kiểm chứng (ước lượng 10–13 FPS, YOLO có
thể quá hạn, camera USB, chạy nền). Slide và báo cáo nộp bài phải nói thẳng điều này ([pitch deck](pitch-deck.pdf), slide 12). Các tiêu chí
cần thiết bị trong [pilot-readiness.md](pilot-readiness.md) giữ nguyên trạng "Chưa đạt".

#### Khác (xem `docs/release-v2.md`, mục 4)

- Chống chói đèn pha bằng phần mềm, bám tài xế thành việc riêng (01/10); rung điện thoại, tự điều chỉnh theo sức máy cho web (02/10, sản phẩm là APK trên hub).
- Đo bản web trên điện thoại Android tầm trung làm mốc thay cho hub (06/10): đầu ra là APK cho hub trên xe, web chỉ để
  xem thử, không có đầu ra nào chạy trên điện thoại. Từ 08/10 cả việc đo trên thiết bị của VF e34 cũng đã bỏ. Ghi chú: một
  điện thoại cùng chip (Snapdragon 665, cùng họ QCM6125) sẽ cho số CPU gần đúng, nhưng WebView, camera USB và nhiệt vẫn khác.

---

<a id="phu-luc-i"></a>

### I. Hai bài báo đọc ngày 06/10

Đọc toàn văn hai file PDF anh gửi. Không chạy lại, không đọc các bài mà chúng dẫn: số nào lấy qua hai bài này
đều là số dẫn lại.

- **[P1]** Jarndal, Tawfik, Siam, Alsyouf, Cheaitou. *A Real-Time Vision Transformers-Based System for Enhanced
  Driver Drowsiness Detection and Vehicle Safety.* IEEE Access 13:1790–1803, 2025.
  https://doi.org/10.1109/ACCESS.2024.3522111
- **[P2]** Hassan, Ibrahim, Makhlouf, Hafiz, Gomaa. *Intelligent driver monitoring systems: a survey of
  drowsiness detection technologies for road safety.* Artificial Intelligence Review 59:137, 2026.
  https://doi.org/10.1007/s10462-026-11505-w

#### [P1] làm gì

- Cắt mặt bằng dlib, thu về 100×100 ảnh xám, đưa vào một ViT nhỏ (8 lớp, 4 đầu attention, 256 mảnh), ra hai
  lớp tỉnh / buồn ngủ cho **từng frame**. Hú còi khi quá nửa số frame trong một giây là "buồn ngủ".
- Train và chấm trên NTHU-DDD (98,89 %, năm cảnh 98,6–99,1 %) và UTA-RLDD (99,4 %, gộp mức `5` vào buồn ngủ,
  năm fold).
- Phần cứng: Raspberry Pi 4B, camera hồng ngoại, cảm biến lực trên vô lăng, còi, module GSM / GPS nhắn tin kèm
  vị trí cho chủ xe khi tài xế không phản ứng. Chạy **4 FPS**; bài viết rằng nhiều hơn thì quá tải.
- Tự nhận giới hạn: mới thử trong phòng trên dataset công khai, bản mẫu trên xe chỉ thử định tính; chưa dùng
  thông tin theo thời gian; mặt bị che nhiều thì hỏng. Trọng số không công bố, dữ liệu "theo yêu cầu".

**Không áp dụng được phần lõi:** phải tự train (trái "chỉ pretrained"); 4 FPS (chỉ tiêu ≥ 15); một nhãn cho mỗi
frame, không có báo sai / giờ, không nêu lý do cảnh báo. Cùng loại với ViDDD ở [phần mất tập trung](#viec-viddd)
và model ViT đã loại ở [phụ lục D](#phu-luc-d).

**Đọc con số 99,4 % thế nào:** nhãn UTA-RLDD là một nhãn tự đánh giá cho cả video 10 phút, [P1] gán nhãn đó cho
từng frame. Một frame của người tỉnh đang chớp mắt và một frame của người buồn ngủ đang mở mắt trông như nhau,
nên đúng 99,4 % số frame khó giải thích chỉ bằng trạng thái buồn ngủ; khả năng là model tách được video này với
video kia (phòng, ánh sáng, quần áo: ba video của một người quay ở ba lúc khác nhau). *Đây là suy luận, bài
không cho đủ chi tiết để kiểm.* [P2] xếp chính bài này vào nhóm số cao do chấm trong cùng dataset.

**Lấy được gì:**
- Bằng chứng ngoài cho rủi ro kính râm → ghi ở [mắt bị che](#viec-mat-bi-che).
- Mốc tham khảo trên UTA-RLDD (người chấm 57,8 %, HM-LSTM 65,2 %) → chưa đưa lên slide, còn phải
  đọc bài gốc.
- Cảm biến tay trên vô lăng → [hoãn](#viec-vo-lang).

#### [P2] làm gì

Tổng quan 70 nghiên cứu 2020–2025 theo PRISMA, bốn nhóm tín hiệu: ảnh / video, sinh lý (điện não, điện tim,
PPG, điện mắt, điện cơ), hành vi xe, ghép nhiều nguồn. Phần có giá trị cho dự án là mục 6 (cách đo) và 8 (nguyên
tắc thiết kế), không phải các bảng liệt kê model.

**Luận điểm chính, trùng với cách dự án đang làm:**
- Accuracy 97–99 % trong các bài thường là chấm trong cùng dataset hoặc cùng người; chấm trên người / dataset
  khác thì tụt khoảng 10–20 % (bài nêu con số này ở mục 1, không kèm phân tích riêng; mục 8.1 chỉ nói là tụt). Số của hai
  bài khác giao thức thì không so được.
- Nên báo: tỉ lệ bắt ở mức báo sai cố định (ví dụ 1 lần / giờ), độ trễ phát hiện, báo sai / giờ, số bỏ sót, có
  khoảng tin cậy, tách theo ánh sáng / kính, chia theo người. Dự án đã có gần hết (M17, M18, M40, M53); phần
  thiếu đã làm ở M69.
- Thiết kế: xử lý trên thiết bị, chỉ lưu sự kiện, cảnh báo leo thang, nêu lý do, cá nhân hoá phần âm lượng /
  kiểu nhắc chứ không nới ngưỡng an toàn. Đã có; dùng làm nguồn dẫn cho phần kiến trúc khi trình bày.
- Phương pháp luật / logic mờ dễ giải thích và ít báo sai hơn: bảng 5 dẫn Magán 2022 trên UTA-RLDD, bản CNN +
  GRU báo sai 40 %, bản logic mờ 7 %, độ chính xác hai bản ngang nhau (55–65 %). Ủng hộ việc giữ risk engine
  dạng luật; *chưa đọc bài gốc*.

**Đã ghi vào việc có sẵn:** κ ≥ 0,70 cho người ghi nhãn và mốc KSS ≥ 7 ([việc đã bỏ 08/10](#bo-hub)); câu hỏi
khó chịu và SUS ([việc 1](#viec-prd-con-lai)); ràng buộc cho hỏi đáp bằng giọng nói ([bỏ ngày 09/10](#viec-hoi-giong-noi)).

**Đã xem, không đề xuất (anh quyết định nếu muốn khác):**

| Ý trong bài | Vì sao không đề xuất |
|---|---|
| Cảm biến đeo: điện não, điện tim, điện mắt, điện cơ, vòng tay PPG | Tài xế phải đeo; bài tự ghi là rào cản lớn nhất. Cùng hướng với "hai model sóng não + mặt" đã bỏ |
| Nhịp tim đọc từ camera | [Hoãn](#viec-rppg), bằng chứng yếu |
| Tín hiệu vô lăng, vị trí làn | [Hoãn](#viec-vo-lang), chờ CAN; vị trí làn cần cảm biến làn |
| Tỉ số biên độ / vận tốc mí mắt (AVR, thang Johns) | Cần đo vận tốc khép mí; pha khép của một lần chớp chỉ dài vài frame ở 30 FPS (*ước lượng*). Tín hiệu cùng họ (thời gian mở mắt lại, M11) đã về trọng số 0 ở M53 |
| Học mốc tài xế bằng model tự giám sát; mạng nơ-ron có ràng buộc sinh lý | Phải train |
| Hệ số theo nhịp sinh học (mô hình hai quá trình) | Bài chỉ nêu là câu hỏi mở, không có số; [mục hoãn](#viec-nhip-sinh-hoc) giữ nguyên |
| Ngưỡng siết dần theo thời gian lái (Essel 2024) | Bảng 5: độ chính xác 98,2 % nhưng độ nhạy 64,3 %. Hệ số 1,2 sau 2 giờ lái hiện có là đủ cho tới khi có chuyến dài |
| Hệ thống giành quyền lái, tự dừng xe | DriverGuard chỉ đọc tín hiệu xe (M44) |
| Nhắn SMS kèm vị trí GPS cho chủ xe ([P1]) | M44 đã báo quản lý qua backend; mất mạng là phần của [việc 10](#viec-outbox-web). Vị trí là loại dữ liệu mới, chưa có trong `docs/data-policy.md` |
| PR-AUC, Brier / ECE đúng nghĩa | Lý do ở M69 (`dataset_uta_rldd.md` mục 8): trên UTA-RLDD hai lớp cân bằng theo cách dựng |
| Dataset mới | Không có: các bộ dùng được (UTA-RLDD, YawDD, NITYMED, DROZY, DMD) đều đã ở [phụ lục B](#phu-luc-b); SEED-VIG là điện não |

**Độ tin cậy của chính [P2]:** dùng làm bản đồ, không làm nguồn số. Thấy khi đọc:
- Mục 6.6.2 còn nguyên chữ giữ chỗ "[Insert ICC value here, e.g., ICC(2,k) = 0.87]".
- Mục 6.4 ghi "99 % trên NTHU-DDD bằng Random Forest" cho Hassan 2024, trong khi bảng 5 của chính bài ghi kết
  quả đó cho Albadawi 2023.
- Bài nói bảng 5 và 7 có cột số người, giao thức chấm, nguồn nhãn; bảng in ra không có ba cột đó.
- Ed-Doughmi 2020: bảng 5 ghi 82,0 % trên tập test, phần chữ ghi 97,3 %. Magán 2022: bảng và chữ lệch nhau
  vài điểm.

Vì vậy mọi số dẫn qua [P2] ở file này đều kèm ghi chú chưa đọc bài gốc.

---

<a id="phu-luc-j"></a>

### Phụ lục J: thiết bị đích, màn hình xe VinFast VF e34 (06/10)

**Quyết định (06/10), đổi ngày 08/10:** đầu ra từng là một file APK chạy trên màn hình của xe VinFast VF e34, bản web chỉ để
xem thử. Từ 08/10 không còn thiết bị, nên bản web mô phỏng là phần kiểm chứng được duy nhất.

**Cấu hình anh tra được** (chưa có thiết bị trong tay; là một dải, chưa phải một máy cụ thể):

| | |
|---|---|
| Hệ điều hành | Android 10 / 11 / 12 / 13 |
| Chip | 8 nhân, vd. Qualcomm Snapdragon QCM6125 |
| RAM | 4 / 6 / 8 GB |
| ROM | 64 / 128 GB, có khe thẻ nhớ |
| Kết nối | SIM 4G / 5G, Wi-Fi 2,4 / 5 GHz, Bluetooth 5.0, GPS / GLONASS |

**Tra cứu 06/10** (đọc trang web, không có thiết bị để thử; nguồn [J1]–[J7]):

| Câu hỏi | Tìm được | Độ chắc |
|---|---|---|
| Cấu hình trên là của cái gì | Màn hình zin 10 inch đặt dọc của VF e34 không cài được app ngoài [J1]. Cấu hình trên (Android 10–13, QCM6125, khe SIM) khớp với **Android box** cắm vào cổng USB CarPlay của xe, giữ màn hình zin [J1], hoặc màn hình Android thay thế. Anh chọn giữ nguyên bản nhất (06/10), tức Android box | Nguồn là trang của nơi bán, chưa có nguồn của VinFast |
| QCM6125 mạnh tới đâu | 4 nhân Cortex-A73 2,0 GHz + 4 nhân Cortex-A53 1,8 GHz, GPU Adreno 610, 11 nm; cùng họ Snapdragon 665 [J2]. Geekbench 6: 334 một nhân / 1 170 nhiều nhân; Apple M1: 2 369 / 8 576, tức khoảng 7 lần [J3] | Số benchmark tổng hợp, không phải số của WASM hay model của DriverGuard |
| YOLO hai luồng (M51) có chạy trong APK không | Không. WebView của Android không hỗ trợ trang cách ly dù trang có đặt header, nên không có `SharedArrayBuffer`; Chromium đóng yêu cầu ở trạng thái không sửa [J4]. ONNX Runtime Web chỉ bật nhiều luồng khi `crossOriginIsolated` là `true` [J5] | Khá chắc; vẫn kiểm trên thiết bị |
| App có thấy camera USB không | Android chỉ đưa camera USB (UVC) vào API camera khi nhà sản xuất bật phần "external camera" trong kernel và HAL; tài liệu ghi phần này dành cho việc nhẹ như gọi video, không cho stream tốc độ cao [J6] | Chưa biết thiết bị này có bật không |
| WebGPU | GPU Adreno 6xx phần lớn chạy được WebGPU trong trình duyệt Android [J7] | Chưa tìm được yêu cầu về phiên bản WebView và Android; chưa biết onnxruntime-web chạy YOLO trên Adreno 610 nhanh tới đâu |

**Từ 08/10 không còn thiết bị** nên phụ lục này không còn đi kèm phép đo nào; nó là danh sách rủi ro chưa kiểm chứng và
phải được nói thẳng khi nộp bài ([pitch deck](pitch-deck.pdf), slide 12).

**Hệ quả với các việc (đã sửa vào từng việc):**
- Ước lượng 10–13 FPS nếu model mặt chạy trên CPU, dưới mốc 15 FPS của CLAUDE.md, là *suy luận từ số của Mac*, không còn
  cách đo ([phụ lục H](#bo-hub)). Giả định "hub được chọn cho vừa app" không còn. Khối 7–12 ở 10–15 FPS đã đo bằng
  replay bỏ bớt frame ([M75](roadmap.md#m75)): báo sai không tăng, sự kiện rõ ràng vẫn được báo, lần nhắm mắt vượt mốc
  L3 dưới 0,2–0,3 s có thể bị bỏ sót khi frame tới không đều. Model mặt và model mắt trên máy chậm thì chưa đo.
- YOLO bản web (việc [bỏ ngày 09/10](#viec-yolo-web)): YOLO một luồng, ước lượng khoảng 1,2 s mỗi lần, quá hạn 0,6 s: nhánh điện thoại có thể không
  hoạt động trong APK nếu không cắt vùng hay không có WebGPU. Trang vẫn báo khi model không còn cho kết quả (M50).
- Đóng gói APK, chạy khi không ở trước (foreground service), màn hình dọc, phiên bản WebView, camera USB, tốc độ xe: đã
  bỏ cùng việc APK; tốc độ xe còn [việc 3](#viec-gps) bằng GPS, thử bằng chuỗi giả.
- Bản Python không chạy trên Android (đã nêu), nên không có phép đo tài nguyên nào thay thế.

**Anh đã trả lời (06/10):**
1. Giữ xe nguyên bản nhất: giữ màn hình zin, thêm Android box (không thay màn hình).
2. Tốc độ xe: thêm lại tốc độ GPS, thành [việc 3](#viec-gps).
3. Plugin native cho model: để sau; nay không còn cách đo để xét lại.

**Câu hỏi còn mở, chỉ thiết bị thật trả lời được (và sẽ không có câu trả lời):**
1. Mẫu box nào, RAM bao nhiêu, bản Android thật là mấy.
2. Box có cổng USB trống cho camera không, và app có thấy camera đó không.
3. Xe đang chuyển sang nguồn khác (radio, camera lùi) thì hình và âm thanh của box còn tới tài xế không.

**Nguồn:**
- J1. Zestech, Android box cho VinFast VF e34: https://zestech.vn/tin-tuc/android-box-vinfast-vf-e34-2021-2025.html ;
  Gotech: https://gotech.vn/android-box-cho-xe-vinfast-vfe34/
- J2. Thundercomm, CM6125 / C6125 SoM: https://www.thundercomm.com/ja/product/cm6125-c6125-som/ (thông số đọc qua kết quả
  tìm kiếm, chưa mở datasheet của Qualcomm)
- J3. cpu-monkey, Snapdragon 665 so với Apple M1: https://www.cpu-monkey.com/en/compare_cpu-qualcomm_snapdragon_665-vs-apple_m1_7_gpu
- J4. Chromium issue 40914606, "SharedArrayBuffer is unavailable in Android WebView because crossOriginIsolated is false":
  https://issues.chromium.org/issues/40914606 (đọc qua kết quả tìm kiếm, chưa mở được trang gốc)
- J5. ONNX Runtime Web, env flags: https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html
- J6. Android Open Source Project, External USB cameras: https://source.android.com/docs/core/camera/external-usb-cameras
- J7. Web3D Survey, WebGPU trên Android: https://web3dsurvey.com/webgpu/features/core-features-and-limits/platform/Android
