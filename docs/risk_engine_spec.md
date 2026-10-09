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
    quality: QualityState | None = None,
) -> RiskAssessment
```
`quality` là kết quả giai đoạn chất lượng của khối 6 (M43); không truyền thì chỉ còn luật mất mặt ở mục 6.

`RiskAssessment` gồm: `t`, `level` (0–3), `hits` (các `RuleHit(level, reason, value)` xếp từ mức
cao xuống), `drowsy_score`, `distraction_score` (thang 0–100), `drowsy_terms` (6 thành phần, hai thành phần
cuối có trọng số 0), `unavailable`, `unavailable_reason` (`no_face`, `camera_blocked`, `bad_angle`, `low_light`,
`glare`, `blur`; `None` khi đang giám sát).

## 4. Bảng luật
| Luật | Điều kiện | Mức |
|---|---|---|
| microsleep | `closed_duration ≥ 1.5 s` | L3 |
| unresponsive | `closed_duration ≥ 6 s` (`risk.unresponsive.closed_s`): còi đã kêu mà mắt vẫn nhắm; lý do thứ hai, báo quản lý ngay (M44) | L3 |
| drowsy_score | `≥ 70` / `≥ 40` | L2 / L1 |
| trend | độ dốc 15 phút ≥ 2/phút, có ≥ 5 điểm, điểm cuối ≥ 20 | L0 (chỉ ghi nhận từ M53, `risk.trend.level: 0`; đặt 1 để bật lại) |
| blink_rate | ngoài khoảng [10, 30] lần/phút, sau ≥ 60 s quan sát | L0 (chỉ ghi nhận) |
| off_road | `off_road_duration ≥ 2 s` (1,5 s khi chạy nhanh) | L2 |
| phone | `phone_ratio_2s ≥ 0.6` | L2 |

**Mức cuối cùng = mức cao nhất trong các luật bật.**

**Cách tính drowsy_score:**

`drowsy_score = 40·perclos + 25·microsleep + 15·yawn + 20·nod`

- Mỗi thành phần nằm trong khoảng 0..1. Riêng perclos được nội suy tuyến tính trong khoảng 5%→20%.
- Chớp chậm (`slow_blink`) và nhướn mày (`brow`) vẫn được đo và nằm trong `drowsy_terms`, nhưng trọng số là 0 từ M53
  (`risk.drowsy.weight_slow_blink`, `weight_brow`; trước đó mỗi cái 10). Tổng bốn trọng số còn lại là 100.
- Microsleep vẫn tính trong 5 phút sau khi xảy ra.
- Nhân thêm 1.2 nếu là ban đêm, nhân 1.2 nếu đã lái lâu; cả hai cùng bật thì tích bị chặn ở
  `risk.drowsy.context_factor_cap` (1,2 từ M92; trước là 1,44). Tối đa 100. "Lái lâu" = thời gian lái từ lần nghỉ /
  lần "Đổi tài xế" gần nhất (`drive_run_s` của khối 10) ≥ `context.long_drive_s` (M73; trước đó là tổng thời gian
  lăn bánh từ lúc mở app, không bao giờ tắt).

## 5. Ngữ cảnh
- **Mất tập trung:** chỉ xét khi xe đang chạy. Xi nhan không tắt luật off_road; khối 8 chỉ nới
  góc quay đầu về phía bật xi nhan.
- **Buồn ngủ:** mức tối đa bị giới hạn theo trạng thái xe:
  - xe chạy: tối đa L3
  - xe dừng (dưới `context.stationary_kmh`): tối đa `risk.drowsy.stationary_max_level`, là 0 từ M30, tức không cảnh
    báo nào khi đứng yên (trước M30 là L1: ngủ gật ở đèn đỏ còn có chuông). Dấu hiệu buồn ngủ vẫn được đo
  - xe chạy lại sau lần dừng từ `context.short_stop_forget_s` (10 s) hoặc sau lần nghỉ: phần khối 7 và trip memory
    gom từ lúc dừng bị bỏ (M73; trước đó chỉ sau lần nghỉ)
  - nghỉ hẳn, hoặc đang đăng ký tài xế (bước nhắm mắt): L0; riêng lúc đăng ký `drowsy_score` và các số hạng đọc 0 (M68)

## 6. Mất giám sát (FR-6)
Xe không đứng yên (`rolling`: từ `context.stationary_kmh`, kể cả lúc bò dưới 5 km/h; M72) mà mất mặt ≥ 3 s thì
`unavailable = True`: xoá mọi hit, không cảnh báo, và báo cho HUD/backend biết là "không giám sát được".
Thấy mặt nhưng không đọc được suốt `risk.unavailable.low_quality_s` (5 s) cũng vậy: `low_light`, `glare`, `blur`
(M43) và `bad_angle` (mặt lọt một phần khỏi khung hoặc không có tư thế đầu; M72).
`unavailable_reason` nói lý do nào; mất mặt thì là `camera_blocked` hoặc `bad_angle` khi ảnh cho thấy vậy, còn lại
là `no_face`.
**Hai ngoại lệ:**
- Đang đếm một lần nhắm mắt và đầu gục ra khỏi khung hình (`head_drop`): engine vẫn giám sát và còi L3 vẫn kêu.
- Mất mặt ngay sau một lần quay đầu lớn (`turned_away` của khối 8, tối đa `distraction.turned_away.max_s`): tài xế
  đang nhìn ra sau, luật `off_road` chạy tiếp thay cho "tạm ngưng" (M38).

## 7. Chống báo sai
- Đổi cấu hình chỉ cần sửa `thresholds.yaml`, không sửa code.
- Chất lượng đo bằng FAR/MAR theo cửa sổ 10 s và số lần báo sai/giờ (M17, M18).
- Cooldown và chống lặp cảnh báo thuộc khối 12, không nằm trong engine.

## 8. Tiêu chí nghiệm thu
- Unit test cho từng luật, cho giới hạn mức theo ngữ cảnh và cho trường hợp unavailable / `head_drop` / `turned_away`.
- Chạy theo kịch bản giả lập ra đúng mức L0–L3 (`tests/test_edge_agent/test_decision.py`,
  `tools/drive_sim.py`).
- Không làm FPS giảm dưới 15 (engine chỉ toán số học, chi phí không đáng kể).

## 9. Câu hỏi mở
- ~~`slow_blink` và `brow` có trọng số tạm~~: đã đo trên UTA-RLDD và đặt về 0 ở M53. Tổng trọng số nay là 100 (trước
  là 120 rồi cắt ở 100); perclos + nod (60) vẫn đủ L1.
- ~~Hai hệ số ngữ cảnh nhân chồng (1,44) hay có trần~~: chốt 09/10, trần 1,2 (M92). Trên 24 người dùng để dò của
  UTA-RLDD, đêm + lái lâu: báo sai 11 → 5 lần, người buồn ngủ có cảnh báo 18 → 15 / 24.
- Luật `trend` trên chuyến dài hàng giờ chưa có dữ liệu để bật lại.
- `distraction_score` hiện chỉ dùng để hiển thị, chưa có luật nào dựa vào nó để lên mức.
