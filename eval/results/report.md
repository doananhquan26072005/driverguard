# Evaluation Report

> Báo cáo đánh giá chất lượng sản phẩm theo tiêu chí BTC. Mọi số liệu lấy từ các file kết quả trong `eval/results/` (đường dẫn ghi ở từng mục), đo ngày 25–26/09/2026 với `config/thresholds.yaml` hiện tại, trừ khi ghi khác.

---

## 1. Đối chiếu yêu cầu cơ bản

| Yêu cầu | Trạng thái | Ở đâu / cách kiểm tra |
|---|:---:|---|
| Phát hiện buồn ngủ / mất tập trung trên video mẫu | ✅ | `python -m edge_agent.main --source <video>` (HowToUse.md mục 7). Buồn ngủ: microsleep, PERCLOS, ngáp, gục đầu (khối 7). Mất tập trung: điện thoại, nhìn lệch, mất mặt (khối 8). Đã chạy trên video YawDD, NITYMED (FL3D), SUST-DDD |
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

| Hành vi | Kết quả |
|---|---|
| Microsleep ≥ 1.5 s đạt L3 | 75/95 (78.9%) |
| Microsleep ≥ 3 s phát hiện | 11/11 (100%) |
| Ngáp phát hiện | 76/99 (76.8%), trễ p50 1.56 s |

Cảnh báo đúng / sai (sai = nằm trên đoạn nhãn tỉnh táo, xa mọi đoạn buồn ngủ; 26 phút nhãn tỉnh táo):

| Mức | Tổng | Đúng | Sai | Sai / giờ |
|---|---:|---:|---:|---:|
| L1 | 10 | 9 | 1 | 2.3 |
| L2 | 13 | 9 | 3 | 6.9 |
| L3 | 83 | 81 | 1 | 2.3 |

→ Precision cảnh báo L3: 81/83 = 97.6%.

### 2.3 Trên video có nhãn theo clip

**YawDD** (319 video, 124 phút; `dataset_yawdd.md`):

| Hành vi | Precision | Recall | F1 | FP / giờ |
|---|---:|---:|---:|---:|
| Ngáp | 100.0% | 82.5% | 0.90 | 0.0 |
| Cảnh báo L1–L3 bất kỳ (clip không buồn ngủ) | – | – | – | 4.8 |

**SUST-DDD** (2074 clip ~10 s quay trên xe thật; `dataset_sust_ddd.md`):

| Luật | Recall (clip buồn ngủ) | FPR (clip không buồn ngủ) | Precision |
|---|---:|---:|---:|
| Đạt L3 | 1.1% | 0.2% | 84.6% |
| Cảnh báo L1–L3 bất kỳ | 1.6% | 2.9% | 33.3% |

Clip SUST chỉ dài 10 s, ngắn hơn thời gian khởi động PERCLOS (30 s) và mốc EAR riêng (10 s), nên recall thấp là do dataset, không phải hệ thống bỏ sót khi lái lâu. Cảnh báo sai chủ yếu là `off_road` khi tài xế quay đầu thật (25/34).

### 2.4 Tỉ lệ báo sai từ thực tế (HITL)

Dashboard (ô *Tài xế báo sai*, tab *Ngưỡng*) tính `false_alarms / tổng cảnh báo`, chia theo từng lý do, từ phản hồi tài xế bấm trên HUD. Đây là số theo dõi khi vận hành. Các số ở mục 2.1–2.3 đo offline trên dataset.

## 3. Hiệu năng

Mac ARM, 10 nhân, video YawDD 640×480 có mặt thật (`benchmark.md`):

| Metric | Mục tiêu | Thực tế | Trạng thái |
|---|---|---|:---:|
| FPS vòng lặp chính (khối 2–12) | ≥ 15 | 151.8 (FP32) / 152.2 (INT8) | ✅ |
| Latency / frame | – | p50 6.5 ms, p95 7.2 ms | ✅ |
| Tổng kích thước model | – | 16.7 MB (FP32) / 7.4 MB (INT8) | ✅ |
| Ảnh khuôn mặt ra khỏi RAM | 0 | 0 (chỉ gửi metadata JSON; test `tests/test_backend/test_privacy.py`) | ✅ |

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
