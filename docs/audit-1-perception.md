# Audit 1: khối 1–5 (camera, tiền xử lý, MediaPipe, YOLOv8n, Eye-state CNN)

Ngày 08/10/2026, trên working tree của nhánh `DAQuan` (có thay đổi chưa commit). Chỉ đọc và phân tích: không sửa
code, config hay `eval/results`. Phạm vi là khối 1–5 ở cả hai bản: thiết bị (`edge_agent/`, Python) và web / APK
(`frontend/src/live/` + `edge_agent/web/bridge.py`). Khối ngoài phạm vi chỉ xét dataclass giao tiếp.

Cách kiểm: đọc code và test; chạy 220 test của các file liên quan (đều pass); một script thử chỉ đọc đặt ngoài repo;
đọc trace tự ghi `data/own_traces/quan_v2.pkl` (chỉ có số). Mọi số "đo trong audit" là trên máy Mac dev.

## 1. Tóm tắt

1. Không có phát hiện mức Critical. Các ràng buộc về ảnh (không ghi đĩa, không gửi), pretrained và model nặng ngoài vòng lặp chính đều đạt trên code; 15 FPS đạt trên Mac, không kiểm chứng được trên thiết bị đích.
2. **High:** khối 2 nhận ảnh màu tối thành ảnh hồng ngoại (98–100 % số frame ở hai phiên tự ghi mặt sáng 10–13), nên khối 5 lấy lại quyền quyết định đúng ở vùng mà M54 đã cố ý giao cho EAR.
3. **Medium, đường lỗi:** luồng YOLO chết hẳn sau một exception; bản web không mở lại camera; ảnh camera đứng hình không được phát hiện; một frame EAR là NaN làm hỏng mốc mắt ít nhất 15 s; sau đăng ký, một mặt lạ đứng một mình vẫn được coi là tài xế.
4. Chi phí thật của Eye-state CNN là 0,11 ms mỗi lần gọi (cả cắt ảnh), gọi mỗi frame chỉ khi ảnh bị coi là IR; tiền xử lý không làm méo tỉ lệ ảnh; ánh xạ toạ độ giữa khối 2, 3, 4 nhất quán ở cả hai bản.
5. Còn số magic ngoài `thresholds.yaml` (nhiều nhất ở bản web), một giá trị mặc định trong code lệch với YAML (`low_light_brightness` 60 so với 0), và vài chỗ tài liệu lệch code.

## 2. Bảng ràng buộc

| Ràng buộc (CLAUDE.md) | Kết luận | Bằng chứng |
|---|---|---|
| Xử lý on-device | Đạt | Thiết bị: mọi model chạy tại chỗ (`edge_agent/main.py:143-155`). Web: MediaPipe và YOLO chạy trong trang (`frontend/src/live/agent.ts:541`, `yolo.worker.ts:64-69`). Lưu ý: runtime Pyodide và wasm của MediaPipe tải từ CDN lúc khởi động (`agent.ts:33-34`), xem M6 |
| Không ghi frame ra đĩa / log / cache | Đạt (trên code) | Quét tĩnh `tests/test_edge_agent/test_no_frame_writes.py:11-26` (pass); khối 1 chỉ giữ một frame và bỏ khi dừng (`edge_agent/capture/frame_source.py:128,211`); log lỗi chỉ in tên lớp và thông báo (`main.py:306-307`, `web/bridge.py:230-232`); các file pickle của `tools/` chỉ chứa số (`tools/record_trace.py:629`) |
| Không ghi frame qua crash dump / swap | Không chắc | Ngoài tầm của code, xem mục 4 |
| Chỉ metadata rời thiết bị (phần của khối 1–5) | Đạt | Telemetry của onnxruntime bị tắt trước khi import (`edge_agent/perception/onnx.py:20-23`); Python của bản web chỉ nhận số (`web/bridge.py:239-264`). MediaPipe có gửi gì không: Không chắc, xem mục 4 |
| ≥ 15 FPS | Đạt trên Mac; Không chắc trên thiết bị đích | Thiết bị: 151,8 FPS, p95 7,2 ms (`eval/results/benchmark.md:11`). Web: 30 FPS. Cổng chạy dài 10 phút của M67 chưa sạch (`docs/roadmap.md:1191`); ước lượng 10–13 FPS trên QCM6125 là suy luận (`docs/improvements.md:1773`) |
| Không model nặng trong vòng lặp chính | Đạt | YOLO ở luồng riêng (`edge_agent/perception/phone_detector.py:367-401`) và worker (`agent.ts:596-610`); CNN mắt 46 KB, 0,11 ms |
| Chỉ pretrained, không train | Đạt | Không có code huấn luyện trong `edge_agent/`, `tools/`, `backend/`, notebook (grep `.fit(`, `optimizer`, `backward`, `epochs`: 0 kết quả). Nguồn model: `tools/download_models.py:27-56` |
| Ngưỡng nằm hết trong `thresholds.yaml` | Vi phạm một phần | Xem L1 |
| Mỗi khối một module, giao tiếp qua dataclass | Đạt | `Frame`, `PreprocessedFrame`, `FaceLandmarks`, `PhoneResult`, `EyeState` → `FrameFeatures`. Khối 5 chạy sau khối 6, khác thứ tự ghi trong CLAUDE.md (`main.py:280-283`), xem mục 3.5 |
| Logic theo thời gian test được bằng chuỗi giả | Đạt một phần | Thuần số: `PhoneHealth`, `EyeStateEstimator.decide`, `FaceBoxMemory`, `YoloPacer`, `frameTimeMs`. Dùng luồng và `sleep` thật: `FrameSource`, `AsyncPhoneDetector`, xem L4 |
| Comment và tên biến tiếng Anh | Đạt | Các file trong phạm vi |

## 3. Phát hiện

Mỗi mục: vấn đề, bằng chứng, hậu quả, đề xuất, công sức (S dưới nửa ngày, M một đến hai ngày, L hơn), tác động tới FPS
và báo sai. "Trùng" nghĩa là `docs/improvements.md` hoặc `docs/safety-fmea.md` đã có; khi đó chỉ ghi phần bổ sung.

### 3.1 Critical

Không có.

### 3.2 High

#### H1. Ảnh màu tối bị nhận là ảnh hồng ngoại, khối 5 quyết định thay EAR

- **Vấn đề:** `is_ir_image` so độ chênh trung bình giữa các kênh màu của **cả khung hình** với ngưỡng tuyệt đối 2,0
  (`edge_agent/perception/preprocess.py:62-68`, `config/thresholds.yaml:29`). Ảnh màu càng tối thì độ chênh tuyệt đối
  càng nhỏ, nên ảnh màu tối rơi dưới ngưỡng. Khi đó trigger `ir` bật và được giữ thêm `hold_s`
  (`edge_agent/perception/eye_state.py:140-141`, `194-195`). Bản web tính cùng cách (`frontend/src/live/measure.ts:30-43`,
  `edge_agent/web/bridge.py:301`).
- **Bằng chứng:**
  - Trace tự ghi (webcam màu, đọc trong audit): phiên `dark` (mặt sáng p50 10,4) có `is_ir` ở 98,3 % số frame,
    `dark_low` (11,4) 100,0 %; `dark_35` (35,1) 0,2 %, `dark_35_still` (33,8) 0,1 %, các phiên ban ngày 0,0 %.
  - `eval/results/lighting_transforms.md:19-22`: với `low_light_brightness: 0`, FL3D làm tối gamma 2,2 (mặt sáng 24)
    vẫn có 45,7 % số frame do CNN quyết định, gamma 3,5 là 100 %, so với 7,3 % ở video gốc. Trigger còn lại duy nhất
    giải thích được mức tăng đó là `ir`.
  - `tools/trace_studies.py:590` ghi "`is_ir` is 0 on every trace": đúng với dataset, không đúng với bản tự ghi tối.
- **Hậu quả:**
  - M54 đặt `eye_state.low_light_brightness: 0` để mặt tối do EAR quyết định, vì CNN sai cả hai chiều khi tối
    (`config/thresholds.yaml:64-70`: 28 % frame mắt mở bị đọc là nhắm, 8 lần L3 sai trong 5,5 phút; ở video làm tối thì
    bỏ sót mọi lần nhắm). Trigger `ir` đưa CNN trở lại đúng ở các frame tối đó. Bản web thì `eyeBlink` quyết định mọi
    frame với bộ ngưỡng riêng.
  - Ở mặt sáng 10–13 khối chất lượng đã báo `low_light` (dưới 25) và sau 5 s thành "tạm ngưng", nên thiệt hại ở đó có
    giới hạn. Vùng 13–31 **chưa có số đo**: không biết `is_ir` đổi từ 0 % sang 100 % ở đâu. Nếu điểm đổi nằm trên 25
    thì CNN quyết định mà không có cờ chất lượng nào.
  - Ca chưa đo: cabin tối, mặt được màn hình chiếu sáng. `is_ir` tính trên cả khung, độ sáng tính trên mặt, nên mặt đủ
    sáng vẫn bị giao cho CNN.
  - Metadata ghi lý do `ir` cho một camera màu, làm sai các phân tích theo lý do.
- **Đề xuất:** chỉ tính độ chênh kênh trên các pixel đủ sáng, hoặc chia cho độ sáng trung bình; và chốt loại camera theo
  thời gian (một camera không đổi giữa màu và IR từng frame) thay cho quyết định từng frame. Ngưỡng mới đặt trong
  `preprocess`. Sau đó chạy lại `tools/light_study.py` và test hồi quy trace.
- **Công sức:** S cho code và test; M nếu tính cả đo lại.
- **Tác động:** FPS không đổi. Báo sai: dự kiến giảm ở ánh sáng yếu trên thiết bị; chưa đo.
- **Trùng:** việc 8 và FMEA dòng 16 đã ghi "ảnh xám → CNN yếu". Phần mới là ảnh **màu** tối cũng đi vào đường đó.
- **Không chắc:** camera có chế độ đêm tự chuyển sang ảnh xám thì `ir` là đúng; chưa có camera như vậy để thử.

### 3.3 Medium

#### M1. Luồng YOLO chết hẳn sau một exception (thiết bị); worker treo không có watchdog (web)

- **Bằng chứng:** `phone_detector.py:381` gọi model không có `try`; thử trong audit với model giả ném lỗi ở lần chạy thứ
  hai: luồng dừng (`is_alive()` = False), `latest()` trả `None` mãi. Web: lỗi của worker được xử lý
  (`yolo.worker.ts:111-126`), nhưng worker không trả lời thì `yoloBusy` giữ `true` mãi (`agent.ts:605`, `621`).
- **Hậu quả:** nhánh điện thoại tắt tới hết chuyến. Không im lặng: `PhoneHealth` báo sau khoảng 10 s (FMEA dòng 17),
  nhưng chip không có âm thanh và không tự hồi phục.
- **Đề xuất:** bắt lỗi trong vòng lặp của luồng, đếm, chạy tiếp; ở web thêm hạn chờ cho một lần chạy rồi tạo lại worker.
- **Công sức:** S. **Tác động:** FPS không đổi; báo sai không đổi; giảm bỏ sót `phone`.
- **Trùng:** FMEA 17 có phần phát hiện; phần bổ sung là không tự hồi phục.

#### M2. Bản web không mở lại camera, và không xử lý sự kiện `mute`

- **Bằng chứng:** `agent.ts:474` chỉ báo `camera(true)` khi track `ended`; không có lần gọi `getUserMedia` thứ hai, không
  có `camera(false)`. Thiết bị thì mở lại mỗi 2 s (`frame_source.py:224-240`).
- **Hậu quả:** camera rớt một lần là mất giám sát tới khi tải lại trang. Track bị `mute` (ứng dụng khác lấy camera) không
  báo `camera_lost`; HUD vẫn báo đứng hình sau 3 s (`frontend/src/hud/HudScreen.tsx:15`), nên tài xế được báo nhưng với
  lý do chung.
- **Đề xuất:** khi `ended` thử `getUserMedia` lại theo `capture.reconnect_interval_s`; coi `mute` kéo dài quá
  `capture.frame_timeout_s` là mất camera.
- **Công sức:** M. **Tác động:** FPS và báo sai không đổi.
- **Trùng:** FMEA 8 mô tả bản thiết bị, FMEA 4 mô tả app bị dừng; chưa mục nào nói bản web không mở lại.
- **Liên quan đã biết:** vòng lặp web ngừng nhận frame ở hai lần chạy 10 phút của M67, nguyên nhân chưa rõ
  (`eval/results/benchmark_live.md:181-190`). Bổ sung: vòng lặp không có đường tự khởi động lại khi
  `requestVideoFrameCallback` im quá lâu.

#### M3. Ảnh đứng hình (camera giao lại cùng một ảnh) không được phát hiện

- **Bằng chứng:** khối 1 chỉ xét đọc lỗi và hết giờ (`frame_source.py:176-194`), không so nội dung; bản web chỉ xét
  `currentTime` đổi (`agent.ts:487`).
- **Hậu quả:** nếu driver camera lặp lại frame cuối, hệ thống thấy một khuôn mặt mắt mở đứng yên: im lặng không giới
  hạn, không có cờ nào bật.
- **Không chắc:** camera USB thực tế có lỗi kiểu này thường xuyên không; chưa có thiết bị để thử. Kiểm chứng: rút nguồn
  cảm biến hoặc dùng `capture_factory` giả trả cùng một mảng.
- **Đề xuất:** so một mẫu thưa của độ sáng với frame trước; giống hệt liên tục quá `capture.frame_timeout_s` thì coi là
  mất camera. Ảnh thật luôn có nhiễu cảm biến nên phép so bằng tuyệt đối không tự báo sai.
- **Công sức:** S. **Tác động:** dưới 0,1 ms mỗi frame; báo sai không đổi.

#### M4. Landmark NaN không bị chặn ở khối 3; một frame EAR NaN làm hỏng mốc mắt

- **Bằng chứng (thử trong audit):** điểm NaN ở mí mắt: `face_conf` 0,992, `face_reliable` True, `ear` = NaN đi tiếp sang
  khối 7. Chuỗi 30 s EAR 0,30 với **một** frame NaN ở giây 15: tới giây 30 `ear_open_baseline` vẫn là NaN. NaN ở điểm
  dùng cho tư thế đầu thì `cv2.solvePnP` ném lỗi, được bắt ở `main.py:305-309` (đường này đúng). Khối 3 không kiểm
  (`landmarks.py:238-241`, `web/bridge.py:267-268`).
- **Hậu quả:** mọi phép so với mốc NaN đều sai, nên mắt đọc là mở: nhánh buồn ngủ im ít nhất 15 s. Tối đa có thể tới
  `drowsiness.eye.baseline_window_s` (120 s): chưa đo.
- **Không chắc:** MediaPipe có bao giờ trả NaN không; chưa thấy trong trace. Hậu quả lớn, cách chặn rẻ.
- **Đề xuất:** ở khối 3 (cả hai bản), mặt có điểm không hữu hạn thì coi là không có mặt.
- **Công sức:** S. **Tác động:** FPS không đổi; báo sai không đổi.

#### M5. Sau đăng ký, một mặt đứng một mình luôn được coi là tài xế

- **Bằng chứng:** `landmarks.py:154-155`: có anchor mà chỉ một mặt thì lấy mặt đó, không tính điểm;
  `tests/test_edge_agent/test_enrollment.py:390` khẳng định hành vi này. Khi có hai mặt, mặt điểm thấp nhất thắng, không
  có ngưỡng loại (`landmarks.py:157`). Thử trong audit: mặt lạ có điểm 17,0 (tài xế 3,78) vẫn được chọn khi đứng một mình.
- **Hậu quả:** tài xế bị che (điện thoại trước mặt, tấm chắn nắng) hoặc ra khỏi khung mà còn thấy hành khách: mắt và tư
  thế của hành khách thành tín hiệu của tài xế (hành khách ngủ → L3 sai); "mất mặt → tạm ngưng → hỏi tài xế" (FMEA 6)
  không chạy; vùng tài xế của khối 4 dời theo mặt hành khách.
- **Đề xuất:** thêm ngưỡng điểm tối đa trong `landmarks`; vượt thì trả "không có mặt".
- **Không chắc:** giá trị ngưỡng. Chữ ký mặt chưa đo trên nhiều người trong xe; đặt chặt thì tài xế quay đầu mạnh bị
  loại, thêm "tạm ngưng".
- **Công sức:** S cho code; cần dữ liệu hai người để đặt ngưỡng.
- **Tác động:** FPS không đổi; giảm báo sai do hành khách, có thể tăng "tạm ngưng".
- **Trùng:** phụ lục G của improvements có "chữ ký chưa đo" và `num_faces` = 2; chưa có điểm "không có ngưỡng loại".

#### M6. Bản web cần CDN lúc khởi động

- **Bằng chứng:** `agent.ts:33-34`: Pyodide và wasm của MediaPipe tải từ `cdn.jsdelivr.net` khi chạy, không đóng gói và
  không có kiểm tra toàn vẹn; không có service worker.
- **Hậu quả:** xe không có mạng lúc khởi động thì không giám sát được; code chạy trong trang phụ thuộc bên thứ ba. Ảnh
  không rời máy, nên không vi phạm ràng buộc về ảnh.
- **Đề xuất:** đóng gói hai runtime vào bản build.
- **Công sức:** M (bản build nặng thêm). **Tác động:** FPS và báo sai không đổi.
- **Trùng:** việc đóng gói APK đã bỏ 08/10; ghi lại như rủi ro của sản phẩm.

### 3.4 Low

#### L1. Số magic ngoài `thresholds.yaml`, và mặc định trong code lệch YAML

| Chỗ | Giá trị | Ghi chú |
|---|---|---|
| `edge_agent/perception/eye_state.py:73` | `low_light_brightness` mặc định 60,0 | YAML là 0 (`thresholds.yaml:71`). `config_from_dict` chỉ từ chối khoá lạ, khoá **thiếu** lấy mặc định im lặng (`edge_agent/config.py:162-167`); `EyeStateConfig()` không tham số cũng ra 60, tức hành vi trước M54 |
| `frontend/src/live/agent.ts:302` | camera 640×480, 30 FPS | `capture.camera_*` của YAML (1280×720) không tới bản web; `bridge.settings()` không gửi (`web/bridge.py:166-190`) |
| `frontend/src/live/agent.ts:548` | `eyeBlink` thiếu thì coi là 0,05 | Giá trị thay thế đi vào luật của khối 7 |
| `frontend/src/live/frameTime.ts:14` | `MAX_FRAME_AGE_MS` 1000 | Quyết định giờ của frame |
| `preprocess.py:66`, `quality.py:42`, `measure.ts:34` | bước lấy mẫu 4 pixel | Ba chỗ phải khớp nhau, không có test giữ chúng khớp |
| `web/bridge.py:72` | ép `eye_state.source` = blendshape | Có ghi chú, nhưng là cấu hình nằm trong code |
| `main.py:251`, `frame_source.py:123,189`, `phone_detector.py:341,376` | hạn chờ 0,5 / 2,0 / 0,01 s | Tham số vận hành, không phải ngưỡng quyết định |
| `phone_detector.py:241` | màu đệm 114 | Quy ước của YOLO, nên giữ trong code |

- **Đề xuất:** sửa mặc định của `EyeStateConfig` cho khớp YAML, hoặc bắt buộc khoá có mặt; đưa ba dòng của bản web vào
  `settings()`. **Công sức:** S. **Tác động:** không.

#### L2. `face_conf` không phải độ tin cậy

- **Bằng chứng:** là tỉ lệ landmark nằm trong ảnh (`landmarks.py:179-182`, `256`); MediaPipe Tasks không trả điểm theo
  mặt. Trace tự ghi: 99,5–100 % số frame có mặt đạt `reliable`, nên ngưỡng 0,9 chỉ bắt ca mặt bị cắt ở mép ảnh.
- **Hậu quả:** tay che, khẩu trang, kính râm không làm giảm `face_conf`; landmark bị đoán vẫn được tin. Ngưỡng 0,9 có số
  đo đứng sau (YawDD, `docs/roadmap.md:143`), nên phần mép ảnh là ổn.
- **Đề xuất:** ghi rõ nghĩa ở chỗ dùng; chưa đề xuất đổi logic khi không có dữ liệu che mặt. **Công sức:** S.
- **Trùng:** kính râm là FMEA dòng 5 (hoãn), khẩu trang đã bỏ 06/10.

#### L3. Model không nạp được

- `make_estimator` và `main.py:152-155` chỉ bắt `FileNotFoundError` (`eye_state.py:239-243`): file hỏng hoặc thiếu
  onnxruntime làm agent dừng lúc khởi động với traceback.
- Thiếu file CNN mắt thì chạy "EAR only" và chỉ in ra terminal; HUD và backend không được báo (dấu vân tay model để
  `None`, `main.py:187`). Model điện thoại thì có báo (`main.py:201`).
- `face_landmarker.task` tải từ kênh `latest`, không có checksum (`tools/download_models.py:29-33`): hai lần cài có thể
  ra hai model khác nhau. Dấu vân tay ở M41 giúp nhận ra sau đó.
- Cảnh báo ở `phone_detector.py:399` khuyên dùng model INT8, trong khi file INT8 hiện có không phát hiện được điện thoại
  nào (improvements, mục Đã bỏ).
- **Công sức:** S. **Tác động:** không.

#### L4. Test yếu hoặc thiếu

- `test_phone_detector.py:115-128` và `test_frame_source.py:108-147` dùng `sleep` và luồng thật với khoảng chấp nhận rộng
  (`6 <= calls <= 12`): chậm và dễ lung lay trên CI bận; lịch chạy của YOLO không được kiểm bằng đồng hồ giả.
- Chưa có test cho: luồng YOLO gặp exception (M1); landmark NaN (M4); ảnh đứng hình (M3); ảnh màu tối không phải IR (H1,
  `test_preprocess.py:22-35` chỉ có ba kênh bằng nhau và ảnh màu sáng); `resize` giữ tỉ lệ; camera web `ended` rồi có lại.
- Ba bản tính độ chênh kênh và độ nét (Python, `measure.ts`) không có test so chéo trên cùng một ảnh.

#### L5. Việc nhỏ khác

- Bản web đo độ sáng và độ nét trên mặt **lớn nhất**, trong khi Python chọn tài xế theo đăng ký (`agent.ts:556-562`).
- MediaPipe của bản web nhận giờ xử lý chứ không phải giờ chụp (`agent.ts:531`), khác với giờ dùng ở khối 6–12.
- Kết quả YOLO cũ tới 0,6 s được so với hộp mặt của frame hiện tại (`main.py:273-279`): lệch khi đầu đang chuyển động.
- `stop()` giải phóng camera khi luồng đọc có thể còn kẹt trong `read()` (`frame_source.py:118-127`).
- Độ sáng vùng mặt được tính hai lần mỗi frame (`quality.py:94-95`, `eye_state.py:121-131`): tổng 0,075 ms, không đáng sửa.

### 3.5 Các điểm kiểm riêng của phiên này

**Chạy mỗi frame hay thưa, và độ trễ.** Thiết bị: `eval/results/benchmark.md:19-27`; web: `docs/improvements.md:430-439`.

| Khối | Lịch chạy | Thiết bị | Web |
|---|---|---:|---:|
| 1 Camera | Mỗi frame, luồng riêng, chỉ giữ frame mới nhất | – | – |
| 2 Tiền xử lý | Mỗi frame | 0,69 ms (đo lại: 0,56 ms, trong đó CLAHE 0,22 ms) | 0,5–1,8 ms, không CLAHE |
| 3 MediaPipe | Mỗi frame | 5,8 ms | 8,9–10,4 ms |
| 4 YOLOv8n 640 | 5 lần / giây (10 trên WebGPU), luồng riêng | 16,8 ms | 16 ms (WebGPU), 91 ms (wasm 2 luồng) |
| 5 CNN mắt | Chỉ khi có trigger; mỗi frame khi ảnh bị coi là IR | 0,11 ms (đo lại, gồm cắt ảnh 0,016 ms) | Không chạy, dùng `eyeBlink` |

- **Nguy cơ dưới 15 FPS:** không thấy trên Mac (dư khoảng 7 lần). Trên thiết bị đích chỉ có ước lượng. Khối duy nhất
  đáng kể là MediaPipe; improvements đã cân nhắc và bỏ việc giảm tần suất của nó.
- **Rò bộ nhớ:** không thấy cấu trúc nào lớn dần trong khối 1–5 (một frame, một kết quả, cửa sổ theo thời gian). Số đo
  chưa kết luận được, xem mục 4.
- **Tỉ lệ ảnh:** `resize` chỉ thu nhỏ và giữ tỉ lệ (`preprocess.py:70-76`). Thử: 1280×720 → 640×360, 1920×1080 → 640×360,
  640×480 giữ nguyên, sai số 0 %; kích thước lẻ 1281×721 sai 0,06 %. Letterbox của YOLO chỉ đệm (`phone_detector.py:234-243`).
- **Ánh xạ toạ độ:** landmark, hộp mặt và hộp điện thoại cùng ở hệ pixel của ảnh sau khối 2 (`landmarks.py:239`,
  `phone_detector.py:262-275`). Web gửi kèm hình học letterbox của đúng frame đã chạy (`agent.ts:606`, `626-627`).
  `PreprocessedFrame.scale` không có nơi nào đọc.
- **Ổn định landmark (trace tự ghi, một người, một webcam):** thay đổi EAR giữa hai frame liền nhau, tính theo mốc mắt
  mở: p50 0,009–0,016, p95 0,045–0,16 (p95 gồm cả chớp mắt thật). Góc đầu: p95 0,3–0,9° mỗi frame khi ngồi yên. Không có
  bước làm mượt landmark nào trong khối 3; khoảng trễ đóng / mở là 0,10 lần mốc (`close_ratio` 0,65, `open_ratio` 0,75).
  Mặt sáng 34–35 không rung hơn ban ngày. Chưa tách được nhiễu khỏi chuyển động thật.
- **Kính, kính râm, khẩu trang, chói, đêm, IR:** không có dữ liệu mới. Đã biết trong improvements: kính râm (hoãn), chói
  (bỏ), khẩu trang (bỏ), IR (không còn nguồn đo). Phần mới của audit là H1.
- **Thứ tự khối 5:** chạy sau khối 6 vì trigger cần EAR từng mắt (`main.py:280-283`), khác chuỗi "3 / 4 / 5 → 6" trong
  CLAUDE.md. Đây là lệch tài liệu, không phải lỗi.

### 3.6 Tài liệu lệch code

| Tài liệu | Ghi | Code hiện tại |
|---|---|---|
| `docs/improvements.md:1241` | `low_light_brightness` = 60 | 0 (`thresholds.yaml:71`) |
| `docs/improvements.md:1574` | `features.target_fps: 5` | `phone.target_fps` |
| `tools/trace_studies.py:590` | `is_ir` bằng 0 ở mọi trace | Hai phiên tự ghi tối: 98–100 % (H1) |
| `edge_agent/perception/eye_state.py:73` | mặc định 60,0 | YAML 0 (L1) |
| `docs/architecture_diagram.md:292` | INT8 3,61 MB như một lựa chọn | File INT8 không phát hiện được gì |
| `config/thresholds.yaml:7-10` | cài đặt camera | Không áp dụng cho bản web (L1) |
| CLAUDE.md, kiến trúc | 5 chạy song song với 3, 4, trước 6 | 5 chạy sau 6 |
| `docs/safety-fmea.md` dòng 8 | camera được mở lại mỗi 2 s | Chỉ đúng với bản thiết bị (M2) |

## 4. Không kiểm tra được, và vì sao

| Việc | Vì sao | Cách kiểm chứng |
|---|---|---|
| FPS, độ trễ, nhiệt trên thiết bị đích (QCM6125, WebView) | Không còn thiết bị (08/10) | Chạy `#/live` trên máy cùng chip |
| Ảnh IR thật, kính râm, khẩu trang, đèn pha, ngược sáng | Không có dữ liệu; các phiên ghi đã bỏ | Camera IR; phiên tự ghi có nhãn |
| Điểm `is_ir` đổi trạng thái theo độ sáng (mặt sáng 13–31) | Trace không lưu độ chênh kênh, chỉ lưu cờ | Ghi thêm cột độ chênh kênh, một phiên giảm sáng dần |
| MediaPipe có trả NaN, camera có lặp frame | Chưa từng gặp trong trace; không có phần cứng lỗi | Test bằng dữ liệu giả; chạy dài trên camera thật |
| Frame có vào crash dump hoặc swap | Thuộc hệ điều hành, không thuộc code | Kiểm cấu hình core dump và swap của thiết bị |
| MediaPipe (Python, JS) có gửi dữ liệu ra ngoài | Không đọc mã nguồn thư viện, không bắt gói mạng | Chạy với mạng bị chặn hoặc ghi lưu lượng |
| Rò bộ nhớ khi chạy nhiều giờ | Lần chạy dài nhất 10 phút; container +21 đến +66 MB / giờ, trên ngưỡng 20 (`eval/results/benchmark_simulated.md:233`) | `tools/benchmark.py --duration` từ một giờ trở lên |
| Hành vi khi có hai người trong khung (M5) | Mọi dataset chỉ có một người | Phiên tự ghi hai người |
| Nhiễu landmark tách khỏi chuyển động thật | Trace gồm cả chớp mắt và cử động | Phiên ngồi yên với mắt giả hoặc ảnh tĩnh |
| Test frontend và e2e | Audit chỉ chạy test Python của khối 1–5 | `npm test`, Playwright |
