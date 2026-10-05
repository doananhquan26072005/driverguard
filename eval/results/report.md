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

### 2.4 Tỉ lệ báo sai từ thực tế (HITL)

Dashboard (ô *Tài xế báo sai*, tab *Ngưỡng*) tính `false_alarms / tổng cảnh báo`, chia theo từng lý do, từ phản hồi tài xế bấm trên HUD. Đây là số theo dõi khi vận hành. Các số ở mục 2.1–2.3 đo offline trên dataset.

## 3. Hiệu năng

Mac ARM, 10 nhân, video YawDD 640×480 có mặt thật (`benchmark.md`):

| Metric | Mục tiêu | Thực tế | Trạng thái | Nhận định |
|---|---|---|:---:|---|
| FPS vòng lặp chính (khối 2–12) | ≥ 15 | 151.8 (FP32) / 152.2 (INT8) | ✅ | Đạt trên máy dev (Mac ARM, 10 nhân). Không nói gì về hub gắn trên xe: chưa đo |
| Latency / frame | – | p50 6.5 ms, p95 7.2 ms | ✅ | Máy dev, 300 frame; đây là độ trễ xử lý một frame, không phải thời gian tới cảnh báo (chưa đo) |
| Tổng kích thước model | – | 16.7 MB (FP32) / 7.4 MB (INT8) | ✅ | Không phụ thuộc máy |
| Ảnh khuôn mặt ra khỏi RAM | 0 | 0 (chỉ gửi metadata JSON; test `tests/test_backend/test_privacy.py`) | ✅ | Đạt, có test ở cả thiết bị và máy chủ |

Bảng tiêu chí đầy đủ để chạy thử trên xe thật: [`docs/pilot-readiness.md`](../../docs/pilot-readiness.md).

## 4. Test

```
pytest tests/test_edge_agent tests/test_backend -q     # 410 passed (28/09/2026)
cd frontend && npm test                                # 18 passed
```

Logic theo thời gian (khối 7–12) được test bằng chuỗi số giả, không cần video: kịch bản đỗ xe, lái đêm, microsleep liên tiếp, mất camera, v.v. (`tests/test_edge_agent/test_m4_scenarios.py`, `test_drowsiness.py`, `test_decision.py`).

## 5. Giới hạn đã biết

- **Điện thoại (khối 4):** chưa có dataset camera hướng mặt tài xế có nhãn điện thoại, nên chưa đo được precision / recall đúng góc máy. State Farm (camera bên hông) cho recall 2.1%.
- **Nhìn lệch (`off_road`):** nguồn báo sai chính trên SUST-DDD và YawDD, phần lớn khi tài xế quay đầu thật gần ngưỡng.
- **Chưa có video lái thật dài có nhãn theo thời gian:** NITYMED là cảnh diễn lại ban đêm, SUST-DDD chỉ có nhãn theo clip 10 s.
- **Ngưỡng mới từ dashboard** chỉ áp dụng khi edge agent khởi động lại.

## 6. User feedback và demo

Chưa thực hiện. Điền sau buổi demo: ngày, số người tham gia, nhận xét, lỗi phát hiện. Kịch bản demo ở HowToUse.md mục 7.4.
