# Evaluation Evidence — DriverGuard

> Trang này là lối vào. Số liệu không chép lại ở đây để khỏi lệch với nguồn: báo cáo đầy đủ nằm ở
> [eval/results/report.md](../eval/results/report.md), mỗi bảng trong đó ghi file kết quả, ngày đo và commit.

## Đối chiếu checklist Evaluation Evidence (10/10/2026)

| Mục checklist | Trạng thái | Ở đâu |
|---|---|---|
| Bảng test results (pytest output + coverage) | Có | [report.md mục 4](../eval/results/report.md#4-test): 1712 test Python và 293 test frontend pass; coverage theo dòng 93,9 % cho `edge_agent/` + `backend/`, 77,4 % tính cả `tools/` |
| Bảng metrics từ golden dataset | Có, bằng chỉ số khác pass@k (xem dưới) | [report.md mục 2](../eval/results/report.md#2-metrics-độ-chính-xác); tập giữ riêng 24 người ở mục 2.8, danh sách người ở [eval/splits/](../eval/splits/) |
| Benchmark so sánh | Có một phần | [report.md mục 2.9](../eval/results/report.md#29-so-sánh-với-baseline-1010): tín hiệu đơn so với `drowsy_score` trên cùng người; baseline con người 57,8 % của bài báo gốc UTA-RLDD, không so trực tiếp được. Chưa có số của đối thủ |
| User feedback (3–5 người thật) | **Chưa có: 0 người** | [report.md mục 6](../eval/results/report.md#6-user-feedback-và-demo): cách làm và bảng để điền |
| Code traceability (test case → feature) | Có | [traceability.md](traceability.md): 14 khối, ràng buộc bắt buộc, FR / NFR của PRD → file test |

**Vì sao không có pass@k / pass^k hay RAGAS.** Các chỉ số đó chấm câu trả lời của một agent LLM hoặc một hệ RAG trên bộ
câu hỏi mẫu. DriverGuard không có LLM và không có truy hồi tài liệu: đầu ra là mức cảnh báo L0–L3 theo thời gian, sinh
từ model thị giác pretrained và luật. Chỉ số tương ứng là precision / recall / FPR theo frame và theo sự kiện, số cảnh
báo sai mỗi giờ kèm khoảng tin cậy 95 %, AUC, và thời gian tới cảnh báo. "Golden dataset" ở đây là các bộ có nhãn
(FL3D, YawDD, SUST-DDD, UTA-RLDD) và 44 trace ghim kết quả trong `tests/fixtures/regression/`, chạy lại ở mỗi lần
test (`tests/test_edge_agent/test_trace_regression.py`).

## Báo cáo chính

[eval/results/report.md](../eval/results/report.md):

| Mục | Nội dung |
|---|---|
| 1 | Đối chiếu yêu cầu cơ bản của BTC |
| 2.1 | Accuracy / precision / recall / FPR theo từng ảnh (dataset Kaggle) |
| 2.2 | Video có nhãn theo frame: FL3D / NITYMED |
| 2.3 | Video có nhãn theo clip: YawDD, SUST-DDD |
| 2.4 | Theo điều kiện: độ sáng vùng mặt và kính |
| 2.5 | PERCLOS: định nghĩa hiện tại so với P80 |
| 2.6 | Cá nhân hoá theo tài xế có giảm báo sai không |
| 2.7 | Tỉ lệ báo sai từ thực tế (HITL) |
| 2.8 | Buồn ngủ thật, có tập kiểm tra giữ riêng: UTA-RLDD |
| 2.9 | So sánh với baseline: tín hiệu đơn, con người và model của bài báo gốc |
| 3 | Hiệu năng (FPS, thời gian từng khối) |
| 4 | Test và coverage |
| 5 | Giới hạn đã biết |
| 6 | User feedback và demo |

## Kết quả thô

Thư mục [eval/results/](../eval/results/), mỗi file một lần đo:

- Dataset: `dataset_*.md` (MRL Eye, yawn-eye, drowsy-detection, DDD, State Farm, FL3D, YawDD, SUST-DDD, UTA-RLDD).
- Hiệu năng: [benchmark.md](../eval/results/benchmark.md), [benchmark_live.md](../eval/results/benchmark_live.md),
  [benchmark_web.md](../eval/results/benchmark_web.md), [benchmark_simulated.md](../eval/results/benchmark_simulated.md),
  [benchmark_blocks_jetson_nano.md](../eval/results/benchmark_blocks_jetson_nano.md).
- Nghiên cứu riêng: [drozy_l1.md](../eval/results/drozy_l1.md), [lighting.md](../eval/results/lighting.md),
  [perclos_p80.md](../eval/results/perclos_p80.md), [personalization.md](../eval/results/personalization.md),
  [glance_ratio.md](../eval/results/glance_ratio.md), [gaze_3mdad.md](../eval/results/gaze_3mdad.md),
  [phone_web_3mdad.md](../eval/results/phone_web_3mdad.md), [own_recordings.md](../eval/results/own_recordings.md).

## Test tự động

- Python: [tests/](../tests/) (`pytest`), gồm edge agent, backend và tools.
- Frontend: vitest và Playwright ở [frontend/](../frontend/) (`frontend/e2e/`).
- CI: [.github/workflows/ci.yml](../.github/workflows/ci.yml). Từ 12/10 GitHub không khởi động job (lỗi thanh toán của tổ chức); kết quả chạy local 13/10 ở [ci-local.md](ci-local.md).
- Coverage: `make coverage` (pytest-cov); bảng theo gói ở [report.md mục 4.1](../eval/results/report.md#41-coverage-theo-dòng-lệnh).
- Yêu cầu → khối → file test: [traceability.md](traceability.md).

## Tài liệu liên quan

- [pilot-readiness.md](pilot-readiness.md): tiêu chí để chạy thử trên xe thật và trạng thái từng tiêu chí.
- [audit-5-eval-tests.md](audit-5-eval-tests.md): audit 08/10 về phần đánh giá và test.
- [HowToUse.md mục 9](../HowToUse.md#9-đánh-giá-và-benchmark): cách chạy lại từng phép đo.
