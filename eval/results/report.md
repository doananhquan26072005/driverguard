# Evaluation Report

> Báo cáo đánh giá chất lượng sản phẩm theo tiêu chí BTC. Mọi số liệu lấy từ các file kết quả trong `eval/results/` (đường dẫn ghi ở từng mục), đo ngày 25–26/09/2026 với `config/thresholds.yaml` hiện tại, trừ khi ghi khác.

---

## 1. Đối chiếu yêu cầu cơ bản

| Yêu cầu | Trạng thái | Ở đâu / cách kiểm tra |
|---|:---:|---|
| Phát hiện buồn ngủ / mất tập trung trên video mẫu | ✅ | `python -m edge_agent.main --source <video>` (HowToUse.md mục 7). Buồn ngủ: microsleep, PERCLOS, ngáp, gục đầu (khối 7). Mất tập trung: điện thoại, nhìn lệch (khối 8). Mất mặt ≥ 3 s khi chạy: tạm ngưng giám sát (`unavailable`, v2). Đã chạy trên video YawDD, NITYMED (FL3D), SUST-DDD |
| Phân cấp cảnh báo | ✅ | L0–L3 ở khối 9 (risk engine) + 12 (alert manager, cooldown). HUD: màu, icon, âm thanh theo mức; L3 đỏ toàn màn hình, còi lặp tới khi mở mắt |
| Đăng nhập ≥ 2 vai trò | ✅ | 4 vai trò: `driver` (tài xế, chỉ thấy dữ liệu của mình), `engineer` (kỹ sư an toàn, chỉnh ngưỡng), `manager` (fleet manager, xem toàn đội, ngưỡng chỉ đọc), `admin`. JWT + mật khẩu scrypt, phân quyền kiểm ở backend (`backend/app.py`), test ở `tests/test_backend/` |
| HITL cho hiệu chỉnh ngưỡng | ✅ | Vòng lặp: tài xế bấm **"Cảnh báo sai"** trên HUD → backend lưu phản hồi → dashboard tab *Ngưỡng* hiện tỉ lệ báo sai theo từng lý do → kỹ sư sửa ngưỡng (có min/max, backend từ chối bộ ngưỡng thiết bị sẽ bỏ qua) → lưu thành phiên bản mới kèm người sửa → thiết bị tải về khi khởi động |
| Dashboard nhật ký sự kiện | ✅ | Tab *Nhật ký sự kiện* (lọc theo thời gian, mức, tài xế, chỉ báo sai), tab *Timeline mệt mỏi* (drowsy_score theo phút + cảnh báo), ô thống kê theo mức |
| Metric accuracy / precision / recall / tỉ lệ false positive | ✅ | Mục 2 bên dưới. Công cụ: `tools/dataset.py` (từng ảnh), `tools/eval.py` (video có nhãn theo thời gian), `tools/seq_eval.py` (nhãn theo frame / clip). Tỉ lệ báo sai từ thực tế (phản hồi tài xế) hiện trên dashboard |

## 2. Metrics độ chính xác

### 2.1 Theo từng ảnh (Kaggle): accuracy / precision / recall / FPR

Ngưỡng đúng như trong `thresholds.yaml`. FPR = FP / (FP + TN).

| Tín hiệu | Dataset | Ảnh | Accuracy | Precision | Recall | F1 | FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| Mắt nhắm, CNN khối 5 (p ≥ 0.6) | MRL Eye (4000) | 4000 | 99.4% | 99.8% | 99.0% | 0.99 | 0.2% |
| Mắt nhắm, CNN khối 5 | MRL Eye full, split test | 3223 | 95.4% | 91.4% | 100.0% | 0.95 | 8.9% |
| Mắt nhắm, CNN khối 5 | yawn-eye (eyes), test | 218 | 88.1% | 97.7% | 78.0% | 0.87 | 1.8% |
| Ngáp, MAR khối 6 (≥ 0.45) | yawn-eye (mouth), test | 215 | 91.6% | 100.0% | 83.0% | 0.91 | 0.0% |
| Buồn ngủ, EAR hoặc MAR (1 ảnh) | drowsy-detection, test | 1483 | 70.1% | 97.3% | 42.5% | 0.59 | 1.2% |
| Buồn ngủ, EAR hoặc MAR (1 ảnh) | DDD | 3000 | 62.4% | 90.2% | 27.7% | 0.42 | 3.0% |
| Điện thoại, YOLOv8n khối 4 | State Farm | 2000 | 51.0% | 95.5% | 2.1% | 0.04 | 0.1% |

Chi tiết: `dataset_mrl_eye.md`, `dataset_mrl_eye_full.md`, `dataset_yawn_eye_eyes.md`, `dataset_yawn_eye_mouth.md`, `dataset_drowsy_detection.md`, `dataset_ddd.md`, `dataset_state_farm.md`.

Lưu ý khi đọc:
- CNN khối 5 được học trên MRL Eye, nên số trên MRL lạc quan.
- DDD / drowsy-detection là ảnh đơn lẻ, không có mốc EAR riêng của tài xế và luật thời gian của khối 7. Hệ thống thật không cảnh báo dựa trên một ảnh, nên recall thấp ở đây là dự kiến. Hai file này đo lúc MAR còn ngưỡng 0.6 (nay 0.45); cột "EAR hoặc MAR" chủ yếu do EAR quyết định.
- State Farm quay từ bên phải xe, không phải camera hướng mặt tài xế, nên YOLO gần như không thấy điện thoại (recall 2.1%). Đây là giới hạn đã biết của khối 4 (mục 5).

### 2.2 Trên video có nhãn theo frame: FL3D / NITYMED

44 video lái ban đêm, 47.2 phút, chạy toàn bộ pipeline (khối 2–12, YOLO bật, giả lập 60 km/h). Chi tiết: `dataset_fl3d.md`.

Theo frame (mắt nhắm vs tỉnh táo; ngáp vs tỉnh táo):

| Tín hiệu | Precision | Recall | FPR |
|---|---:|---:|---:|
| Mắt nhắm (khối 7, EAR hoặc CNN) | 72.1% | 87.0% | 7.7% |
| Mắt nhắm sâu (EAR ≤ 0.5 × mốc) | 89.3% | 88.9% | 2.4% |
| Ngáp, MAR ≥ 0.45 | 97.9% | 88.7% | 0.3% |

Theo sự kiện:

| Hành vi | Kết quả | Nhận định |
|---|---|---|
| Microsleep ≥ 1.5 s đạt L3 | 75/95 (78.9%) | Chưa đạt mục tiêu ≥ 90% lần của PRD §7 |
| Microsleep ≥ 3 s phát hiện | 11/11 (100%) | Đạt, nhưng chỉ 11 lần và là cảnh diễn |
| Ngáp phát hiện | 76/99 (76.8%), trễ p50 1.56 s | Chưa đạt ≥ 90%; ngáp chỉ là một thành phần của `drowsy_score`, không tự phát cảnh báo |

Cảnh báo đúng / sai (sai = nằm trên đoạn nhãn tỉnh táo, xa mọi đoạn buồn ngủ). Mẫu số là **0,43 giờ**
(26 phút) nhãn tỉnh táo; CI 95% Poisson chính xác:

| Mức | Tổng | Đúng | Sai | Sai / giờ (CI 95%) | Nhận định (mục tiêu PRD ≤ 1,0 / giờ) |
|---|---:|---:|---:|---:|---|
| L1 | 9 | 7 | 2 | 4.6 (0.56–16.7) | Chưa kết luận được: ước lượng trên 1,0 nhưng CI chứa 1,0 |
| L2 | 16 | 11 | 3 | 6.9 (1.43–20.3) | Chưa đạt: cả cận dưới CI đã trên 1,0 |
| L3 | 83 | 81 | 1 | 2.3 (0.06–12.9) | Chưa kết luận được: CI chứa 1,0 |

CI rất rộng: 26 phút không đủ để nói gì về chỉ tiêu PRD ≤ 1,0 / giờ. Bảng tách theo lý do × mức, và
FAR / MAR theo cửa sổ, ở `dataset_fl3d.md` (mục 5, 5b). FAR / MAR trên FL3D không đọc được: video
~1 phút, chỉ 7 cửa sổ hợp lệ sau khi bỏ 30 s khởi động.

→ Precision cảnh báo L3: 81/83 = 97.6%.

v2 (01/10): thêm thành phần chớp chậm vào `drowsy_score` (ngưỡng tạm). Trước đó: L1 10 (9 đúng, 1 sai),
L2 13 (9 đúng, 3 sai). Chớp chậm nâng vài cảnh báo L1 đúng lên L2, và thêm 1 cảnh báo L1
`drowsy_score` sai (P1042787, 77,9 s). Gục đầu giữ nguyên như v1, vì phép thử "giật lên nhanh" đang
tắt mặc định. Nhướn mày chưa đo được, vì trace cũ không có blendshape lông mày. Chi tiết ở
`docs/release-v2.md`.

### 2.3 Trên video có nhãn theo clip

**YawDD** (319 video, 124 phút; `dataset_yawdd.md`, chấm từ trace):

| Hành vi | Precision | Recall | F1 | Giờ đo | FP / giờ (CI 95%) |
|---|---:|---:|---:|---:|---:|
| Ngáp | 100.0% | 82.5% | 0.90 | 1.45 | 0.0 (0.00–2.5) |
| Cảnh báo L1–L3 bất kỳ (clip không ngáp) | – | – | – | 1.45 | 6.9 (3.31–12.7) |

Trước 01/10 số này là 4,8 / giờ vì chia cho cả 124 phút, gồm cả clip ngáp (ở đó không thể có cảnh
báo sai). Nay chia cho 1,45 giờ clip không ngáp. 10 cảnh báo sai không đổi.

**SUST-DDD** (2074 clip ~10 s quay trên xe thật; `dataset_sust_ddd.md`):

| Luật | Recall (clip buồn ngủ) | FPR (clip không buồn ngủ) | Precision | Cảnh báo / giờ trên clip không buồn ngủ (CI 95%) |
|---|---:|---:|---:|---:|
| Đạt L3 | 1.1% | 0.2% | 84.6% | |
| Cảnh báo L1–L3 bất kỳ | 1.6% | 2.4% | 38.1% | 8.5 (5.56–12.5), trên 3,05 giờ |

Clip SUST chỉ dài 10 s, ngắn hơn thời gian khởi động PERCLOS (30 s) và mốc EAR riêng (10 s), nên recall thấp là do dataset, không phải hệ thống bỏ sót khi lái lâu. Cảnh báo sai chủ yếu là `off_road` khi tài xế quay đầu thật (24/26). Từ 01/10 (v2) mất mặt ≥ 3 s khi xe chạy là `unavailable`, không cảnh báo (PRD FR-6): bớt 7 cảnh báo L2 `no_face` và 1 `off_road` được giữ trong lúc mất mặt (trước: FPR 2,9 %, 34 cảnh báo sai).

Theo từng người (YawDD, mã người từ tên file; `dataset_yawdd.md`, M40): 10 cảnh báo sai đến từ 10 / 106 người, mỗi người một lần; 9 / 10 rơi vào 30 s đầu clip, lúc mốc tư thế đầu còn đang học (clip chỉ dài khoảng 20 s).

### 2.4 Theo điều kiện: độ sáng vùng mặt và kính (M40)

Chia lại kết quả sẵn có, không ghi thêm dữ liệu (`lighting.md`). Độ sáng = độ chói trung bình (0–255) của vùng mặt trước CLAHE; dưới 60 là ngưỡng mà khối 5 không còn tin EAR. **Không so chéo dataset**: mỗi bộ là người khác, camera khác. Trong cùng một bộ, các nhóm vẫn là những người khác nhau.

| Bộ, điều kiện | Lượng dữ liệu | Frame do CNN quyết định | Chỉ số | Nhận định |
|---|---|---:|---|---|
| FL3D, frame có mặt tối < 60 | 466 frame có nhãn | 100 % | Mắt nhắm: recall 40,3 %, FPR 2,4 % | Ít frame, từ vài video; hướng: mặt rất tối thì bắt nhắm mắt kém hẳn |
| FL3D, frame 60–100 | 46 448 frame | 8,8 % | Mắt nhắm: recall 92,6 %, FPR 7,8 % | Toàn bộ video đêm của bộ này nằm ở nhóm này |
| YawDD, không kính | 181 video; 0,82 giờ clip không ngáp | 14,9 % | Báo sai 4,8 / giờ (CI 95 % 1,32–12,4); ngáp bắt được 52/65 | CI của ba nhóm kính chồng nhau: chưa kết luận được |
| YawDD, kính | 102 video; 0,47 giờ | 26,1 % | Báo sai 10,5 / giờ (3,42–24,6); ngáp 31/36 | |
| YawDD, kính râm | 36 video; 0,15 giờ | 66,7 % | Báo sai 6,7 / giờ (0,17–37,2); ngáp 11/13 | Nhãn chỉ có ngáp: không nói gì về mắt nhắm sau kính râm |
| SUST, mặt 100–140 | 1 185 clip; 1,76 giờ clip không buồn ngủ | 5,4 % | Báo sai 9,7 / giờ (5,64–15,5) | |
| SUST, mặt ≥ 140 | 728 clip; 0,99 giờ | 6,4 % | Báo sai 8,1 / giờ (3,48–15,9) | |

Chưa có: IR, ngược sáng, chói; ngày / đêm theo từng clip không có nhãn ở bộ nào. Phép thử làm tối / làm chói cùng một video trong RAM (so được trên cùng người) chưa làm.

### 2.5 PERCLOS: định nghĩa hiện tại so với P80 (M40)

`perclos_60s` không phải P80 của tài liệu: frame tính là nhắm khi EAR < 0,65 × mốc mắt mở (độ mở dưới khoảng 46 %, gần "P50"), có trộn xác suất của CNN và bỏ frame đang ngáp / nói. Từ M40 khối 7 đo thêm `perclos_p80_60s` (độ mở < 20 %, chỉ frame EAR), không dùng để cảnh báo. So hai định nghĩa trên trace sẵn có (`perclos_p80.md`):

| Phép so | Hiện tại | P80 | Nhận định |
|---|---:|---:|---|
| FL3D theo frame: frame microsleep được tính là nhắm | 70,5 % | 77,3 % | Định nghĩa hiện tại chỉ xét được 66,5 % số frame có nhãn (bỏ frame ngáp / nói), P80 xét 86,9 % |
| FL3D theo frame: frame alert bị tính là nhắm | 2,6 % | 2,0 % | |
| SUST theo clip: AUC tách buồn ngủ / không | 0,669 | 0,649 | Khác biệt nhỏ, clip 10 s |
| YawDD clip Normal / Talking có tỉ lệ nhắm ≥ 0,15 | 28 / 205 | 12 / 201 | Định nghĩa hiện tại đọc cao hơn trên người tỉnh |

Clip quá ngắn để cửa sổ 60 s đầy, nên chưa kết luận được định nghĩa nào phát hiện buồn ngủ tốt hơn; ngưỡng không đổi. Trên UTA-RLDD (M53, video 10 phút, cùng một người tỉnh và buồn ngủ) P80 không tách tốt hơn định nghĩa hiện tại: AUC 0,873 so với 0,892 trên 24 người giữ riêng, nên giữ định nghĩa hiện tại. Các ngưỡng PERCLOS hiện tại không có nguồn tài liệu nào được ghi lại.

### 2.6 Cá nhân hoá theo tài xế có giảm báo sai không (M40)

YawDD, mốc "đăng ký giả" lấy từ clip Normal của chính người đó (`personalization.md`): 212 clip của 105 người, cảnh báo sai 7 (mốc tự học) so với 9 (mốc đăng ký giả), toàn `off_road`; clip ngáp có sự kiện ngáp 93 → 97 / 113. **Chưa có số nào cho thấy cá nhân hoá giảm báo sai.** Bộ này là xe đỗ, clip ~20 s, mốc lấy từ một clip khác của cùng người; số chính phải đo trên UTA-RLDD.

UTA-RLDD (M53, `personalization_uta_rldd.md`): 48 người, mốc đăng ký giả lấy từ đầu chính video hoặc từ video tỉnh táo của người đó. Cảnh báo sai nhánh buồn ngủ 9 (tự học), 9 và 9 (hai kiểu đăng ký giả) trên 7,94 giờ tỉnh táo. Vẫn chưa có số nào cho thấy cá nhân hoá giảm báo sai.

### 2.7 Tỉ lệ báo sai từ thực tế (HITL)

Dashboard (ô *Tài xế báo sai*, tab *Ngưỡng*) tính `false_alarms / tổng cảnh báo`, chia theo từng lý do, từ phản hồi tài xế bấm trên HUD. Đây là số theo dõi khi vận hành. Các số ở mục 2.1–2.6 đo offline trên dataset.

### 2.8 Buồn ngủ thật, có tập kiểm tra giữ riêng: UTA-RLDD (M53)

48 người ngồi trước laptop (không lái xe), 145 video ~10 phút, nhãn tự đánh giá cho cả video: `0` tỉnh, `5`, `10` buồn ngủ. Ngưỡng được dò trên 24 người, số dưới đây chấm một lần trên 24 người còn lại (`dataset_uta_rldd.md`).

| 24 người giữ riêng, 4,08 giờ video tỉnh táo | Trước M53 | Sau M53 | Nhận định |
|---|---:|---:|---|
| Cảnh báo sai nhánh buồn ngủ mỗi giờ (CI 95 %) | 1,96 (0,85–3,87) | 0,98 (0,27–2,51) | Giảm một nửa; cận trên vẫn trên chỉ tiêu 1,0 |
| FAR theo cửa sổ 10 s, mức L1 | 3,9 % | 1,5 % | |
| AUC `drowsy_score`, video `10` so với `0` | 0,917 | 0,924 | Điểm tách được hai mức |
| Cùng người: điểm ở `10` cao hơn ở `0` | 22 / 24 | 22 / 24 | |
| Video `10` có cảnh báo buồn ngủ / đạt L3 | 17 / 12 trên 24 | 15 / 12 trên 24 | Mất 2 người chỉ có cảnh báo nhẹ |

M53 đưa trọng số chớp chậm và nhướn mày về 0 và để luật `trend` chỉ ghi nhận: hai tín hiệu không phân biệt được tỉnh với buồn ngủ trên cùng một người. Đây không phải dữ liệu lái xe; kết luận về chỉ tiêu PRD vẫn cần giờ lái thật có nhãn.

## 3. Hiệu năng

Mac ARM, 10 nhân, video YawDD 640×480 có mặt thật (`benchmark.md`):

| Metric | Mục tiêu | Thực tế | Trạng thái | Nhận định |
|---|---|---|:---:|---|
| FPS vòng lặp chính (khối 2–12) | ≥ 15 | 151.8 (FP32) / 152.2 (INT8) | ✅ | Đạt trên máy dev (Mac ARM, 10 nhân). Không nói gì về hub gắn trên xe: chưa đo |
| Latency / frame | – | p50 6.5 ms, p95 7.2 ms | ✅ | Máy dev, 300 frame; đây là độ trễ xử lý một frame, không phải thời gian tới cảnh báo (chưa đo) |
| Tổng kích thước model | – | 16.7 MB (FP32) / 7.4 MB (INT8) | ✅ | Không phụ thuộc máy |
| Ảnh khuôn mặt ra khỏi RAM | 0 | 0 (chỉ gửi metadata JSON; test `tests/test_backend/test_privacy.py`) | ✅ | Đạt, có test ở cả thiết bị và máy chủ |

Chạy dài theo nhịp camera 30 FPS (M42, `benchmark_simulated.md`): máy dev 10 phút giữ 29,9 FPS, CPU 54 % của một nhân, RAM đỉnh 601 MB; container giới hạn 4 CPU / 4 GB (`simulated`) 10 phút giữ 29,9 FPS, p95 11,1 ms, CPU 93 %. Container dùng chính CPU của máy dev nên đây là cận trên cho bo mạch 4 nhân, không phải số đo thiết bị. Bảng FP32 / INT8: `quantization.md` (độ chính xác INT8 chưa đo).

Bảng tiêu chí đầy đủ để chạy thử trên xe thật: [`docs/pilot-readiness.md`](../../docs/pilot-readiness.md).

## 4. Test

```
pytest tests/test_edge_agent tests/test_backend -q     # 793 passed (06/10/2026)
cd frontend && npm test                                # 67 passed
```

Logic theo thời gian (khối 7–12) được test bằng chuỗi số giả, không cần video: kịch bản đỗ xe, lái đêm, microsleep liên tiếp, mất camera, v.v. (`tests/test_edge_agent/test_m4_scenarios.py`, `test_drowsiness.py`, `test_decision.py`).

## 5. Giới hạn đã biết

- **Điện thoại (khối 4):** chưa có dataset camera hướng mặt tài xế có nhãn điện thoại, nên chưa đo được precision / recall đúng góc máy. State Farm (camera bên hông) cho recall 2.1%.
- **Nhìn lệch (`off_road`):** nguồn báo sai chính trên SUST-DDD và YawDD, phần lớn khi tài xế quay đầu thật gần ngưỡng.
- **Chưa có video lái thật dài có nhãn theo thời gian:** NITYMED là cảnh diễn lại ban đêm, SUST-DDD chỉ có nhãn theo clip 10 s.
- **Ngưỡng mới từ dashboard** chỉ áp dụng khi edge agent khởi động lại.

## 6. User feedback và demo

Chưa thực hiện. Điền sau buổi demo: ngày, số người tham gia, nhận xét, lỗi phát hiện. Kịch bản demo ở HowToUse.md mục 7.4.
