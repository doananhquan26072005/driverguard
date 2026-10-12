# Traceability: yêu cầu → khối → test

> Bảng này nối từng yêu cầu của [PRD.md](PRD.md) và từng khối của kiến trúc với file test kiểm nó.
> Lập ngày 10/10/2026 từ docstring của 88 file test Python và 25 file test frontend. Kết quả chạy và coverage:
> [eval/results/report.md mục 4](../eval/results/report.md#4-test).

Đường dẫn viết tắt: `edge/` = `tests/test_edge_agent/`, `be/` = `tests/test_backend/`, `fe/` = `frontend/src/`,
`e2e/` = `frontend/e2e/`. Một file test có thể xuất hiện ở nhiều dòng.

Cách tìm ngược từ test về yêu cầu: file tên `test_m<số>_*.py` thuộc mốc `M<số>` trong [roadmap.md](roadmap.md), ở đó
ghi khối bị đổi và lý do; docstring đầu file ghi mốc và phát hiện của audit mà test đó chặn.

## 1. Theo 14 khối của kiến trúc

| Khối | Code | File test |
|---|---|---|
| 1 Frame camera | `edge_agent/capture/` | `edge/test_frame_source.py`, `test_m71_frame_gaps.py`, `test_m83_passenger_and_frozen_camera.py`, `test_m88_missing_tests.py`; `fe/live/frozen.test.ts`, `frameTime.test.ts`, `watchdog.test.ts` |
| 2 Tiền xử lý | `perception/preprocess.py` | `edge/test_preprocess.py`, `test_m98_dark_colour_is_not_infrared.py` |
| 3 MediaPipe | `perception/landmarks.py`, `geometry.py` | `edge/test_geometry.py`, `test_m87_ci_real_models.py` (model thật), `test_m77_non_finite.py`, `test_m83_passenger_and_frozen_camera.py` |
| 4 YOLOv8n | `perception/phone_detector.py` | `edge/test_phone_detector.py`, `test_m50_phone_health.py`, `test_phone_study_tool.py`; `fe/live/yolo.worker.test.ts`, `yoloWatch.test.ts` |
| 5 Eye-state CNN | `perception/eye_state.py` | `edge/test_eye_state.py` (có một test trên model thật), `test_m87_ci_real_models.py` |
| 6 Feature extractor (gồm đăng ký tài xế, chất lượng frame) | `perception/features.py`, `enrollment.py`, `quality.py` | `edge/test_features.py`, `test_enrollment.py`, `test_quality.py` |
| 7 Nhánh buồn ngủ | `analysis/drowsiness/` | `edge/test_drowsiness.py`, `test_drowsy_signals_v2.py`, `test_m76_droop_then_shut.py`, `test_m81_nod_yawn.py`, `test_m93_time_shares.py`, `test_m75_low_fps.py` |
| 8 Nhánh mất tập trung | `analysis/distraction.py` | `edge/test_distraction.py`, `test_m38_distraction.py`, `test_gaze_down.py`, `test_m80_pose_baselines.py` |
| 9 Risk engine | `decision/risk_engine.py` | `edge/test_decision.py`, `test_m4_scenarios.py`, `test_m73_context.py`, `test_m92_reminders_and_context_cap.py`, `test_m77_non_finite.py` |
| 10 Ngữ cảnh | `context/` | `edge/test_context.py`, `test_vehicle_controls.py`, `test_drive_sim.py`, `test_m95_never_a_speed_reading.py`, `test_m89_dim_hours.py`; `be/test_drive_link.py` |
| 11 Trip memory | `decision/trip_memory.py`, `trip_summary.py` | `edge/test_decision.py`, `test_trip_summary.py`, `test_m79_reload_and_samples.py` |
| 12 Alert manager | `decision/alert_manager.py`, `presence.py` | `edge/test_decision.py`, `test_m74_alert_reminders.py`, `test_m44_unresponsive.py`, `test_m92_reminders_and_context_cap.py` |
| 13 HUD | `hud/server.py`, `frontend/src/hud/` | `edge/test_hud_and_remote.py`, `test_m65_hud_trip.py`, `test_m84_metadata_guard_and_hud_callers.py`; `fe/hud/HudScreen.test.tsx`, `hudModel.test.ts`, `m58.test.ts`, `tripModel.test.ts`, `voice.test.ts`; `e2e/portrait.e2e.ts` |
| 14 Metadata publisher | `io/publisher.py`, `metadata_guard.py`, `remote_config.py` | `edge/test_publisher.py`, `test_m84_metadata_guard_and_hud_callers.py`, `test_m47_reload.py`; `be/test_privacy.py`, `test_m82_device_clock.py`, `test_m90_event_id_conflict.py` |
| Cả chuỗi 7–12 | `runtime.py`, `decision/pipeline.py` | `edge/test_m4_scenarios.py`, `test_runtime.py`, `test_trace_regression.py` (trace ghim kết quả), `test_m72_silent_states.py`, `test_m96_slow_loop.py` |
| Bản chạy trên trình duyệt (`#/live`) | `edge_agent/web/`, `frontend/src/live/` | `edge/test_web_bridge.py`, `test_web_without_opencv.py`; `be/test_web_api.py`; `fe/live/agent.test.ts`; `e2e/live.e2e.ts` |
| Backend và dashboard | `backend/`, `frontend/src/dashboard/` | `be/` (19 file); `fe/dashboard/nav.test.ts`, `driverModel.test.ts` |

## 2. Theo ràng buộc bắt buộc (CLAUDE.md)

| Ràng buộc | File test |
|---|---|
| Frame chỉ ở trong RAM, không ghi ra đĩa | `edge/test_no_frame_writes.py` (quét tĩnh mọi lệnh ghi / mã hoá ảnh), `test_record_trace.py` (trace chỉ chứa số) |
| Chỉ gửi metadata JSON | `be/test_privacy.py`, `edge/test_publisher.py`, `test_m84_metadata_guard_and_hud_callers.py`, `be/test_m48_my_data.py` |
| Tối thiểu 15 FPS | `edge/test_m87_ci_real_models.py` và job `models` của CI (đo trên runner, không phải trên xe), `test_m42_soak.py`, `test_m49_perf.py` |
| Mọi ngưỡng ở `config/thresholds.yaml` | `edge/test_m85_no_hardcode.py`, `test_config_strict.py` |
| Logic theo thời gian test bằng chuỗi số giả | Mọi file ở khối 7–12 của bảng 1 |
| Chỉ dùng model pretrained | `edge/test_m86_eval_hygiene.py` (ghim sha256 của file model) |

## 3. Theo yêu cầu của PRD

| Yêu cầu | Nội dung | Khối | File test |
|---|---|---|---|
| FR-1, 1.1, 1.2 | Màn hình 3 trạng thái, câu cảnh báo buồn ngủ / mất tập trung | 13 | `fe/hud/HudScreen.test.tsx`, `hudModel.test.ts`, `m58.test.ts`; `edge/test_hud_and_remote.py`; `e2e/live.e2e.ts` |
| FR-2 | Độ trễ thấp, có cooldown | 12 | `edge/test_decision.py`, `test_m74_alert_reminders.py`, `test_m92_reminders_and_context_cap.py`, `test_record_trace.py` (thời gian tới cảnh báo) |
| FR-3 | Chỉ cảnh báo khi xe chạy | 10 | `edge/test_context.py`, `test_vehicle_controls.py`, `test_m95_never_a_speed_reading.py`, `test_m4_scenarios.py` (kịch bản đỗ xe) |
| FR-4 | Tín hiệu từ ảnh RGB bằng model pretrained | 3–6 | `edge/test_features.py`, `test_geometry.py`, `test_eye_state.py`, `test_phone_detector.py`, `test_m87_ci_real_models.py` |
| FR-5 | Chống cảnh báo sai: làm mượt, kéo dài, đa tín hiệu | 7, 8, 9 | `edge/test_drowsiness.py`, `test_distraction.py`, `test_decision.py`, `test_m4_scenarios.py`, `test_trace_regression.py` |
| FR-6 | `unavailable` khi mất mặt / chất lượng kém, không cảnh báo | 6, 9 | `edge/test_quality.py`, `test_m72_silent_states.py`, `test_m96_slow_loop.py`; `be/test_m43_unavailable_cause.py`; `e2e/live.e2e.ts` (không có mặt) |
| FR-7 | Giám sát live | backend | `be/test_fleet.py`, `test_m44_urgent.py` |
| FR-8 | Nhật ký sự kiện, phiên bản cấu hình, tag `simulated`, không ảnh | 14, backend | `be/test_api.py`, `test_m6_api.py`, `test_m41_versions_audit.py`, `test_privacy.py`; `edge/test_m41_versions.py` |
| FR-9 | Báo cáo: báo sai, sự kiện, coverage, bảng theo điều kiện | backend, công cụ | `be/test_m6_api.py` (thống kê, lọc báo sai); `edge/test_metrics.py`, `test_trace_studies.py`, `test_light_study.py`, `test_m7_tools.py` |
| FR-10 | Vai trò `driver` và quản lý | backend | `be/test_api.py`, `test_m6_api.py`; `fe/dashboard/nav.test.ts` |
| FR-11 | Chỉnh ngưỡng có phiên bản | backend, 14 | `be/test_m6_api.py`, `test_m47_rollout.py`; `edge/test_m47_reload.py`, `test_m79_reload_and_samples.py` |
| FR-12, FR-13 | Tóm tắt chuyến và gợi ý an toàn (bằng luật, không dùng LLM) | 11 | `edge/test_trip_summary.py`; `be/test_trip_reports.py`; `fe/hud/tripModel.test.ts` |
| FR-14 | Chạy local và Docker bằng một lệnh | | **Không có test tự động.** |
| FR-15 | Replay video mẫu và live webcam | 1 | `edge/test_frame_source.py`, `test_trace_regression.py`; `e2e/live.e2e.ts` (camera giả của Chrome) |
| FR-16 | Tốc độ mô phỏng | 10 | `edge/test_drive_sim.py`, `test_context.py`; `be/test_drive_link.py`; `fe/drive/sim.test.ts` |
| FR-17 | Màn hình mô phỏng trong xe, trạng thái ép tay được gắn nhãn | 13 | `fe/hud/forcedLog.test.ts`, `HudScreen.test.tsx` (kịch bản demo); `be/test_m41_versions_audit.py`; `e2e/portrait.e2e.ts` |
| FR-18 | Profile `simulated on-device`, đo p95 / FPS / CPU / RAM | công cụ | `edge/test_m42_soak.py`, `test_m49_perf.py`, `test_m7_tools.py` |
| FR-19 | Cá nhân hoá theo tài xế | 6 | `edge/test_enrollment.py`, `test_m80_pose_baselines.py` |
| FR-20 | Nhiều thiết bị, phiên bản ngưỡng theo thiết bị | backend | `be/test_fleet.py`, `test_m47_rollout.py` |
| NFR-1 | ≥ 9 / 10 người gọi đúng 3 trạng thái | | **Không test tự động được, và chưa làm với người thật** ([report.md mục 6](../eval/results/report.md#6-user-feedback-và-demo)). |
| NFR-2 | p95 ≤ 200 ms, FPS ≥ 10 (`simulated`) | công cụ | `edge/test_m42_soak.py`, `test_m87_ci_real_models.py`; số đo ở [report.md mục 3](../eval/results/report.md#3-hiệu-năng) |
| NFR-3 | Không lưu / gửi ảnh mặt | 14, backend | `edge/test_no_frame_writes.py`, `test_publisher.py`, `test_m84_metadata_guard_and_hud_callers.py`; `be/test_privacy.py`, `test_data_policy.py`, `test_m48_my_data.py` |
| NFR-4 | License rõ cho mọi thành phần | | **Không có test tự động.** |
| NFR-5 | `simulated` khác thiết bị thật; trạng thái ép tay không vào bảng số | backend, 13 | `be/test_m41_versions_audit.py`; `fe/hud/forcedLog.test.ts` |
| NFR-6 | Tái lập: config / commit / hash model theo mỗi lần chạy | công cụ | `edge/test_m86_eval_hygiene.py`, `test_m41_versions.py` |

## 4. Chỗ chưa có test

- FR-14 (Docker), NFR-4 (license): không có test tự động.
- NFR-1 và các chỉ tiêu "hiểu cảnh báo", "chấp nhận" của PRD §6: cần người thật, chưa làm.
- `edge_agent/main.py` (điểm vào của bản thiết bị) và `edge_agent/hud/hud.py`: 0 % coverage.
- Chỉ tiêu trên dataset (báo sai / giờ, recall, thời gian tới cảnh báo) không phải test pass / fail: chúng là phép đo, nằm ở
  [report.md mục 2](../eval/results/report.md#2-metrics-độ-chính-xác). Test chỉ kiểm công cụ đo trên số giả.
