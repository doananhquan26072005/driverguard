# Spec: Risk Engine (khối 9)

Code: `edge_agent/decision/risk_engine.py`. Ngưỡng: mục `risk` trong `config/thresholds.yaml`.

## 1. Mục đích
Gộp đầu ra của nhánh buồn ngủ (7), nhánh mất tập trung (8), ngữ cảnh xe (10) và trip memory (11)
thành **một mức rủi ro L0–L3** kèm lý do. Kết quả này đưa sang Alert manager (12).

## 2. Ràng buộc
- **Stateless:** cùng đầu vào thì luôn ra cùng đầu ra. Mọi thông tin theo thời gian lấy từ
  `DrowsinessState` và `TripState`.
- **Dùng luật, không dùng ML:** đúng quy định "chỉ dùng pretrained, không train".
- **Không hardcode ngưỡng:** mọi ngưỡng nằm trong `RiskConfig`, đọc từ `config/thresholds.yaml`.
- **Test bằng chuỗi số giả**, không cần video.

## 3. Giao diện
```python
RiskEngine(config: RiskConfig).assess(
    d: DrowsinessState, x: DistractionState, ctx: VehicleContext,
    trip: TripState | None = None, drowsy_muted: bool = False,
) -> RiskAssessment
```
`RiskAssessment` gồm: `t`, `level` (0–3), `hits` (các `RuleHit(level, reason, value)` xếp từ mức
cao xuống), `drowsy_score`, `distraction_score` (thang 0–100), `drowsy_terms` (6 thành phần),
`unavailable`.

## 4. Bảng luật
| Luật | Điều kiện | Mức |
|---|---|---|
| microsleep | `closed_duration ≥ 1.5 s` | L3 |
| drowsy_score | `≥ 70` / `≥ 40` | L2 / L1 |
| trend | độ dốc 15 phút ≥ 2/phút, có ≥ 5 điểm, điểm cuối ≥ 20 | L1 |
| blink_rate | ngoài khoảng [10, 30] lần/phút, sau ≥ 60 s quan sát | L0 (chỉ ghi nhận) |
| off_road | `off_road_duration ≥ 2 s` (1,5 s khi chạy nhanh) | L2 |
| phone | `phone_ratio_2s ≥ 0.6` | L2 |

**Mức cuối cùng = mức cao nhất trong các luật bật.**

**Cách tính drowsy_score:**

`drowsy_score = 40·perclos + 25·microsleep + 15·yawn + 20·nod + 10·slow_blink + 10·brow`

- Mỗi thành phần nằm trong khoảng 0..1. Riêng perclos được nội suy tuyến tính trong khoảng 5%→20%.
- Microsleep vẫn tính trong 5 phút sau khi xảy ra.
- Nhân thêm 1.2 nếu là ban đêm, nhân 1.2 nếu đã lái lâu. Tối đa 100. "Lái lâu" = thời gian lái từ lần nghỉ /
  lần "Đổi tài xế" gần nhất (`drive_run_s` của khối 10) ≥ `context.long_drive_s` (M73; trước đó là tổng thời gian
  lăn bánh từ lúc mở app, không bao giờ tắt).

## 5. Ngữ cảnh
- **Mất tập trung:** chỉ xét khi xe đang chạy. Xi nhan không tắt luật off_road; khối 8 chỉ nới
  góc quay đầu về phía bật xi nhan.
- **Buồn ngủ:** mức tối đa bị giới hạn theo trạng thái xe:
  - xe chạy: tối đa L3
  - xe dừng: tối đa `stationary_max_level` (mặc định L1)
  - xe chạy lại sau lần dừng từ `context.short_stop_forget_s` (10 s) hoặc sau lần nghỉ: phần khối 7 và trip memory
    gom từ lúc dừng bị bỏ (M73; trước đó chỉ sau lần nghỉ)
  - nghỉ hẳn, hoặc đang đăng ký tài xế (bước nhắm mắt): L0; riêng lúc đăng ký `drowsy_score` và các số hạng đọc 0 (M68)

## 6. Mất giám sát (FR-6)
Xe không đứng yên (`rolling`: từ `context.stationary_kmh`, kể cả lúc bò dưới 5 km/h; M72) mà mất mặt ≥ 3 s thì
`unavailable = True`: xoá mọi hit, không cảnh báo, và báo cho HUD/backend biết là "không giám sát được".
Thấy mặt nhưng không đọc được suốt `risk.unavailable.low_quality_s` (5 s) cũng vậy: `low_light`, `glare`, `blur`
(M43) và `bad_angle` (mặt lọt một phần khỏi khung hoặc không có tư thế đầu; M72).
**Ngoại lệ:** nếu đang đếm một lần nhắm mắt và đầu gục ra khỏi khung hình (`head_drop`), engine
vẫn giám sát và còi L3 vẫn kêu.

## 7. Chống báo sai
- Đổi cấu hình chỉ cần sửa `thresholds.yaml`, không sửa code.
- Chất lượng đo bằng FAR/MAR theo cửa sổ 10 s và số lần báo sai/giờ (M17, M18).
- Cooldown và chống lặp cảnh báo thuộc khối 12, không nằm trong engine.

## 8. Tiêu chí nghiệm thu
- Unit test cho từng luật, cho giới hạn mức theo ngữ cảnh và cho trường hợp unavailable/head_drop.
- Chạy theo kịch bản giả lập ra đúng mức L0–L3 (`tests/test_edge_agent/test_decision.py`,
  `tools/drive_sim.py`).
- Không làm FPS giảm dưới 15 (engine chỉ toán số học, chi phí không đáng kể).

## 9. Câu hỏi mở
- `slow_blink` và `brow` đang có trọng số tạm, chưa được hiệu chỉnh bằng dữ liệu.
- Tổng trọng số tối đa là 120 rồi mới cắt ở 100, nên chỉ riêng perclos + nod (60) đã đủ L1. Có cần
  chuẩn hoá lại không?
- `distraction_score` hiện chỉ dùng để hiển thị, chưa có luật nào dựa vào nó để lên mức.
