# Hướng cải tiến DriverGuard

Danh sách để chọn mốc tiếp theo, không phải kế hoạch. Theo CLAUDE.md, không mục nào được làm
trước khi có yêu cầu; mục nào được chọn thì thêm thành mốc trong `docs/roadmap.md`.

Cập nhật: 29/09/2026.

---

## 1. Ánh sáng khó: lái đêm, đèn đường, đèn pha xe ngược chiều

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

## 2. Nhiều khuôn mặt trong khung hình (hành khách)

### Hiện tại
- MediaPipe tìm tối đa `num_faces` = 2 mặt; mỗi frame chọn mặt có khung bao lớn nhất làm tài xế
  (`landmarks.py`, web: `largestFace` trong `frontend/src/live/measure.ts`).
- `num_faces` chỉ đi vào metadata, không logic nào dùng.
- Điện thoại chỉ tính trong vùng quanh mặt tài xế, nên điện thoại hành khách không bị tính.

### Rủi ro
- Tài xế quay ngang (nhìn gương, ngoái lại) → khung bao 2D hẹp lại → mặt hành khách nhìn thẳng có
  thể lớn hơn → theo dõi nhầm hành khách, bỏ lỡ đúng lúc cần báo `off_road`.
- Hành khách nghiêng lại gần camera → chọn nhầm.
- Không nhớ tài xế giữa các frame: hai mặt cỡ gần bằng nhau có thể đổi qua lại, trộn dữ liệu hai
  người vào `closed_duration`, `perclos_60s`, `blink_rate`, mốc EAR / pitch.
- Camera đặt giữa xe (cạnh gương chiếu hậu): giả định "lớn nhất = tài xế" yếu đi nhiều.
- ≥ 3 người: MediaPipe chỉ trả 2 mặt.
- Chưa có test đổi mặt theo thời gian; các dataset eval đều chỉ có một người.

### Hướng đề xuất
- **Bám tài xế giữa các frame:** ưu tiên mặt gần vị trí tài xế frame trước; chỉ đổi khi mặt khác
  vượt rõ trong N frame liên tiếp (hysteresis).
- **Ưu tiên phía ghế lái:** cộng điểm cho mặt ở nửa ảnh phía tài xế (Việt Nam: bên trái; tham số
  trong `thresholds.yaml` vì còn tùy camera có lật ảnh hay không).
- **Chọn theo kích thước ít phụ thuộc góc quay đầu** (khoảng cách hai mắt kết hợp chiều cao mặt)
  thay vì diện tích khung bao.
- **Reset bộ đếm theo thời gian khi phát hiện đổi người.**
- Không thêm model, không ảnh hưởng FPS; test bằng chuỗi khung bao giả.

---

## 3. Model trạng thái mắt thay / bổ sung cho Eye-state CNN (khối 5)

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

## 4. Mắt nhìn lệch khi đầu vẫn thẳng (hướng nhìn)

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
- Dùng cùng tín hiệu để nhánh buồn ngủ phân biệt **"mắt nhìn xuống"** với **"mắt nhắm"**.
- Rủi ro: ước lượng mắt kém khi IR / đeo kính → cần tắt hoặc giảm tin cậy trong các trường hợp đó
  (nối với trigger của khối 5 ở mục 1, 3).
- Test bằng chuỗi số giả (góc đầu + độ lệch mắt theo thời gian); cần thêm clip có nhãn "liếc điện
  thoại, đầu thẳng" để đo báo sai (gộp với clip tự quay ở mục 6).

---

## 5. Metric đánh giá: cảnh báo sai / giờ

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
   bắt sự kiện và time-to-alert (PRD p95 ≤ 3 s, chưa có công cụ đo, xem mục 6).
5. **Số HITL trên dashboard không cùng loại:** `false_alarms / tổng cảnh báo` là precision, không phải
   / giờ, và phụ thuộc tài xế có bấm nút hay không.

### Hướng đề xuất (dễ → khó)
1. **Thêm CI Poisson + số giờ dữ liệu** vào mọi bảng cảnh báo sai / giờ (báo cáo + công cụ eval). Đây là
   yêu cầu có sẵn của PRD.
2. **Tách theo lý do và mức** (microsleep, drowsy, off_road, phone, no_face × L1–L3). `off_road` trên
   dataset buồn ngủ thì gán nhãn lại hoặc để riêng "chưa xác định".
3. **Tách giai đoạn khởi động** (vd. 30 s đầu mỗi clip) khỏi số chính, báo cáo riêng.
4. **Đường đánh đổi** cảnh báo sai / giờ ↔ tỉ lệ bắt sự kiện khi đổi ngưỡng, dùng
   `tools/seq_eval.py --replay` (khối 7–12, không cần chạy lại MediaPipe) để thấy ngưỡng hiện tại đứng
   ở đâu thay vì một điểm duy nhất.
5. **Dữ liệu dài, liên tục:** tự quay vài chuyến 30–60 phút (gộp với clip tự quay ở mục 6); xem thêm
   dataset DMD (Driver Monitoring Dataset) *(chưa kiểm chứng: nhớ là có cả nhãn buồn ngủ và mất tập
   trung)*.

Mục 1–2 là việc nhỏ, có thể tách thành một mốc riêng.

---

## 6. PRD yêu cầu nhưng roadmap chưa có mốc

- **LLM tóm tắt + gợi ý (FR-12, FR-13):** chưa có dòng code nào trong DriverGuard.
- **Buổi kiểm tra hiểu cảnh báo 10 người (PRD §7 bậc 3):** chưa diễn ra, số đang là "not evaluated".
- **Clip tự quay có nhãn** theo điều kiện sáng / tối / kính / ngược sáng: chưa có; mọi số hiện tại
  từ dataset công khai. (Gộp được với phần đánh giá ở mục 1.)
- **Time-to-alert p95 ≤ 3 s:** chưa có công cụ đo riêng.
- **Docker cho backend + edge (FR-14):** repo đã có `Dockerfile`, `Dockerfile.railway` và
  `docker-compose.yml`, nhưng compose mới có service `backend`; còn thiếu edge.
- **Nhật ký theo điều kiện**, tag `simulated` / `forced`, phiên bản cấu hình trên sự kiện
  (FR-8, FR-9, FR-17).
- **Nộp bài:** `presentation/` mới có README. (`eval/results/report.md` đã có báo cáo tổng hợp từ
  28/09, cần kiểm tra lại mức đầy đủ so với yêu cầu nộp.)

## 7. Vấn đề kỹ thuật còn mở (worklog 26/09)

- **off_road trên xe thật:** 25 cảnh báo L2 trong 3 giờ SUST là quay đầu thật. Cần xi-nhan / tốc
  độ CAN thật.
- **Clip ngắn:** SUST chỉ 10 s nên PERCLOS và mốc EAR không kịp khởi động, recall 1,6%.
- **Điện thoại:** YOLO bắt 2,1% ảnh State Farm; góc bên không giống camera của mình nên chưa đủ để
  kết luận.
- **B4:** L3 microsleep trong 10 s đầu chuyến vẫn dựa trên mốc EAR mặc định.

## 8. Cần quyết định

- **FR-6:** mất mặt ≥ 3 s khi xe chạy nên báo L2 (như code) hay im lặng ở `unavailable` (như PRD)?
  Liên quan trực tiếp mục 1: nếu giữ L2 thì cần cờ chói để tránh báo sai do đèn pha.
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

## 9. Ý tưởng từ video phân tích DMS thương mại (29/09)

Nguồn: ghi chú `Video.pdf` (bỏ phần camera IR 940 nm, đã có ở mục 1). Đối chiếu với code ngày 29/09,
chưa đo thử.

### Đã có, trùng với video
- EAR từ 6 điểm mỗi mắt (khối 6).
- PERCLOS cửa sổ 60 s, ngưỡng 0,15 (video: ~16%).
- Góc cúi đầu tách "cúi nhìn" khỏi "nhắm mắt": `max_pitch_down_deg`, gục đầu yêu cầu mắt nhắm.
- Nhánh song song đo thời gian nhắm: `closed_duration` ≥ 1,5 s → L3 ngay, không qua `drowsy_score`.
- Con số theo phút: trip memory 1 điểm/phút + cảnh báo xu hướng.

### Hướng đề xuất (xếp theo mức đáng làm)
1. **Mốc mắt mở học lúc đầu chuyến rồi giữ gần cố định.** Hiện mốc EAR = percentile 90 của 120 s
   gần nhất (`ear_baseline`, `drowsiness.py`). Buồn ngủ dần vài chục phút → mắt hẹp lại → mốc tụt
   theo → PERCLOS và "nhắm sâu" bị đánh giá thấp đúng lúc cần. Video: dùng 5–10 phút đầu để làm quen
   mắt tài xế. Hướng: học mốc trong N phút đầu, sau đó chỉ trôi rất chậm hoặc chỉ trôi lên. Test
   bằng chuỗi EAR giả giảm dần.
2. **Tốc độ mở mắt lại, không chỉ số lần chớp.** Video: buồn ngủ thì khép lâu hơn và mở lại chậm.
   Hiện chỉ có `blink_rate`; `blink_max_s` chỉ phân biệt chớp / nhắm. Thêm: thời lượng chớp trung
   bình mỗi phút, thời gian mở lại (từ khép sâu đến mở hẳn), tỉ lệ chớp dài. Là dấu hiệu sớm, trước
   khi PERCLOS kịp tăng.
3. **Mức cảnh báo tăng theo thời gian nhắm.** Video: 1–2 s gợi ý trạm dừng; ≥ 3 s còi + rung ghế;
   ≥ 6 s coi là không còn phản ứng → giảm tốc, tấp làn. Hiện chỉ một L3 ở 1,5 s. Thêm mốc
   `closed_duration` ≥ 3 s và ≥ 6 s trong `thresholds.yaml`; mốc 6 s sinh sự kiện `unresponsive`
   lên backend và yêu cầu giảm tốc qua CAN giả lập. Cảnh báo 1–2 s kèm gợi ý dừng nghỉ.
4. **Gục đầu = cúi chậm rồi giật lên nhanh.** Hiện: dip > 15°, quay lại trong 0,2–2 s, mắt nhắm.
   Thêm điều kiện tốc độ ngẩng lên nhanh hơn rõ so với tốc độ cúi (liếc bảng đồng hồ thì hai chiều
   gần đối xứng) → bớt báo sai. Xem lại `nod.max_s`: cú gục thật có thể cúi chậm hơn 2 s.
5. **Nhướn mày để giữ mắt mở.** Blendshape `browInnerUp` / `browOuterUp` đã có sẵn từ MediaPipe,
   không tốn FPS. Mày nhướn trong lúc EAR thấp / đang giảm = đang chống cơn buồn ngủ → thành phần
   phụ của `drowsy_score`.
6. **10 s không thấy mặt → báo hệ thống tạm ngưng giám sát.** Hiện mất mặt 3 s khi chạy → L2
   `no_face`. Tách hai trường hợp: tài xế gục (giữ L2) và camera bị che (sự kiện
   `monitoring_unavailable` lên HUD / backend, như `camera_lost`). Liên quan quyết định FR-6 ở mục 8.
7. **Kiểm tra định nghĩa PERCLOS.** Video dùng P80 (mắt khép ≥ 80%, ≈ EAR < 0,2 × mốc). Code dùng
   `perclos_close_ratio: 0.65` (khép ~35% đã tính) → nhạy hơn, dễ tính cả nheo mắt. Chạy P80 song
   song trên FL3D / YawDD / SUST để so, chưa thay ngay.

Ưu tiên đề xuất: 1 → 2 → 4. Cả ba không thêm model, chỉ thêm ngưỡng vào `thresholds.yaml`, test được
bằng chuỗi số giả.

### Không áp dụng
- **Hai model (sóng não + mặt → chỉ mặt) để chấm điểm buồn ngủ:** phải train, vi phạm "chỉ dùng
  pretrained". Risk engine dạng luật hiện tại vẫn là lựa chọn đúng.
