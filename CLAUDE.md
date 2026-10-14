# DriverGuard — hệ thống giám sát tài xế on-device

## Ràng buộc bắt buộc
- Toàn bộ xử lý chạy on-device. Không gửi hoặc lưu ảnh khuôn mặt (xem docs/data-policy.md).
  Frame chỉ tồn tại trong RAM, không bao giờ ghi ra đĩa.
- Chỉ gửi metadata JSON lên backend.
- Phải đạt tối thiểu 15 FPS. Không thêm model nặng vào vòng lặp chính.
- Chỉ dùng model pretrained, không train model mới.
- Ưu tiên chống false positive ngang với độ chính xác.

## Kiến trúc: 14 khối, chạy theo thứ tự
1 Frame camera → 2 Tiền xử lý → 3 MediaPipe / 4 YOLOv8n
→ 6 Feature extractor → 5 Eye-state CNN (sau khối 6: chỉ chạy khi EAR không tin được)
→ 7 Nhánh buồn ngủ + 8 Nhánh mất tập trung
→ 9 Risk engine (+ 10 Ngữ cảnh, 11 Trip memory) → 12 Alert manager
→ 13 HUD + 14 Metadata publisher

## Quy ước code
- Mỗi khối là một module riêng trong edge_agent/, giao tiếp qua dataclass.
  Bản chạy trong trình duyệt/APK (#/live) làm khối 1–4, 13, 14 bằng TypeScript
  trong frontend/src/live; khối 6–12 vẫn là Python edge_agent chạy qua Pyodide
  (edge_agent/web/bridge.py). Sửa logic một khối thì kiểm tra cả hai phía.
- Tất cả ngưỡng nằm trong config/thresholds.yaml, không hardcode trong logic.
- Logic theo thời gian phải test được bằng chuỗi số giả, không cần video.
- Comment và tên biến bằng tiếng Anh, giải thích cho tôi bằng tiếng Việt.

## Các biến chính
ear, mar, pitch/yaw/roll, eye_closed, phone_near_face,
face_conf (tỉ lệ landmark nằm trong ảnh, không phải độ tin cậy của model)
→ closed_duration, perclos_60s, blink_rate, yawn_count_10min,
  nod_count_5min, off_road_duration, phone_ratio_2s
→ drowsy_score, distraction_score → level L0–L3

## Cách làm việc
- Workflow nằm ở docs/workflow
- Lộ trình ở docs/roadmap.md. Mỗi lần chỉ làm đúng một mốc tôi yêu cầu.
- Làm xong thì cập nhật trạng thái mốc đó trong docs/roadmap.md.
- Không làm trước các mốc sau, kể cả khi thấy cần thiết. Cứ nói ra để tôi quyết định.