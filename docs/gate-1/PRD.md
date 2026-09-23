# DriverGuard — PRD (v2.1, khung SẢN PHẨM)

| | |
|---|---|
| Phiên bản | 2.1 (product-first) |
| Ngày | 20/09/2026 |
| Sở hữu | Team DriverGuard (4 người) — AI in Action, VinUni |
| Trạng thái | Draft chờ duyệt |
| Thay đổi so với v1.0 | Chuyển kết quả chính từ **so sánh B0/M1** sang **sản phẩm chạy được + pilot + impact**; B0/M1 hạ xuống kiểm tra kỹ thuật nội bộ |

## 1. Tóm tắt sản phẩm

DriverGuard dùng **camera có sẵn** để phát hiện dấu hiệu mất tỉnh táo/mất tập trung của tài xế, **cảnh báo đúng lúc và ít cảnh báo sai**, và cho quản lý an toàn một **dashboard nhật ký + báo cáo**. Điểm khác biệt không nằm ở model (model có sẵn), mà ở **trải nghiệm ít cảnh báo sai + trung thực khi không quan sát được**.

## 2. Người dùng & nhu cầu

| Vai trò | Nhu cầu | Câu chuyện người dùng |
|---|---|---|
| Tài xế (user) | Được nhắc khi thật sự mệt, không bị làm phiền | "Khi tôi buồn ngủ, tôi muốn được nhắc kịp, nhưng đừng báo động khi tôi vẫn có thể tập trung." |
| Quản lý an toàn (buyer) | Thấy được sự kiện theo chuyến/tài xế | "Tôi muốn xem lại buổi chạy và biết tài xế nào cần huấn luyện, tạo hệ thống cá nhân hoá cảnh báo cho từng tài xế."  |

## 3. Mục tiêu & phi mục tiêu

**Mục tiêu sản phẩm**
- P-1: Tài xế được cảnh báo với **ít cảnh báo sai**.
- P-2: Sự kiện mệt mỏi được phát hiện kịp (**time-to-alert p95 ≤3s**).
- P-3: Hệ thống **trung thực**: khi không quan sát/dự đoán được thì nhận biết và báo lỗi, không đoán bừa.
- P-4: Quản lý có dashboard + nhật ký dùng được.
- P-5: **Pilot nhỏ** trên người dùng thật (test tại nhiều khung giờ khác nhau trong ngày để đánh giá độ buồn ngủ hoặc hỏi người dùng trước về mức độ buồn ngủ của họ để so sánh với kêt quả của model).

**Phi mục tiêu:** 


- Camera hồng ngoại/night-vision; thiết bị edge thật; 
- Chạy đường thật; chứng nhận an toàn; phát hiện buồn ngủ tự nhiên có ground truth; 
- Lưu video thô lên cloud; nhận diện danh tính
- Train model mới; LLM realtime.


## 4. Yêu cầu chức năng (FR)
**Happy Path:** Khi tài xế có dấu hiệu không tập trung => Màn hình hiện cảnh báo "bạn đang có dấu hiệu không tập trung, vui lòng ", tổng đài ghi lại thông tin về việc tài xế không tập trung (optional) => tài xế tìm cách để tỉnh ngủ hoặc dừng lái xe     
### 4.1 Trải nghiệm tài xế
- **FR-1** Màn cảnh báo trong xe hiển thị 3 trạng thái: **cảnh báo / bình thường / không quan sát được**, khác biệt rõ về màu và chữ.
  - **FR-1.1** Cảnh báo hiện dòng "Bạn đang có dấu hiệu buồn ngủ. Vui lòng dừng xe." khi phát hiện buồn ngủ. Cảnh báo dừng lại khi tài xế dừng xe hoặc không còn dấu hiệu buồn ngủ.
  - **FR-1.2** Cảnh báo hiện dòng "Vui lòng tập trung nhìn đường" khi phát hiện tài xế làm việc khác không tập trung. Cảnh báo dừng lại khi tài xế dừng xe hoặc không còn dấu hiệu không tập trung. 

- **FR-2** Cảnh báo có độ trễ thấp và có giãn cách (cooldown) để không hú liên tục.
  
- **FR-3** Chỉ hiển thị cảnh báo khi xe đang chạy.  

### 4.2 Thị giác máy tính / Giám sát tài xế
- **FR-5** Trích xuất tín hiệu từ RGB (mặt/landmark, mắt, miệng, head pose) bằng model pretrained.
- **FR-6** Logic chống cảnh báo sai: làm mượt tín hiệu theo thời gian, chỉ cảnh báo khi tín hiệu kéo dài, đa tín hiệu. Cá nhân hoá cho từng tài xế (tính năng lâu dài, optional).
- **FR-7** Chuyển `unavailable` khi mất mặt/chất lượng kém/góc xấu/lóa; **không** cảnh báo khi đang `unavailable`.

### 4.3 Dashboard quản lý
- **FR-7** Giám sát live (tài xế đang ở trạng thái nào).
- **FR-8** Nhật ký kiện: thời gian, trạng thái (VD: không tập trung, buồn ngủ), dấu hiệu nhận được (VD: ngáp, mắt rời khỏi đường đi), điều kiện (VD: sáng, tối, đeo kính), phiên bản cấu hình, tag `simulated` hoặc `true`. Không lưu ảnh mặt.

- **FR-9** Báo cáo: số cảnh báo sai/giờ, sự kiện phát hiện, coverage, và **bảng tách theo điều kiện** (sáng/kính/ngược sáng/thiếu sáng).

- **FR-10** Hai vai trò `driver` (chỉ cảnh báo) và `safety/fleet manager` (đầy đủ).
- **FR-11** Chỉnh ngưỡng theo đội, có **version + reset** (optional, tính năng lâu dài). 
### 4.4 Mô hình ngôn ngữ

- **FR-12** Tổng hợp nhật ký và các sự kiện đã phát hiện để tạo tóm tắt hành vi lái xe theo từng tài xế hoặc nhóm tài xế. 
- **FR-13** Đưa ra gợi ý an toàn cá nhân hóa dựa trên các mẫu sự kiện đã ghi nhận, điều kiện quan sát và lịch sử cảnh báo. 

### 4.5 Vận hành
- **FR-13** Chạy **local + Docker** bằng một lệnh.
- **FR-14** Chế độ **replay** video mẫu và **live** webcam.
- **FR-15** **CAN-speed simulation**: tín hiệu tốc độ mô phỏng; hiển thị rõ là mô phỏng.
- **FR-16** **Pilot & Feedback**: màn cho người thử chạy kịch bản và ghi phản hồi ngắn (nếu làm pilot).
- **FR-17** Runtime profile **simulated on-device** (cap CPU/thread, int8), đo p95/FPS/CPU/RAM/kích thước model; mọi số gắn `simulated`.

### 4.6 Optional (sau khi core chạy)
- **FR-17** Cá nhân hóa ngưỡng theo tài xế (neo + reset, chặn khi chất lượng thấp).
- **FR-18** Fleet nhiều thiết bị + OTA (mock).

## 5. Yêu cầu phi chức năng (NFR)

- **NFR-1 Trải nghiệm:** tài xế hiểu cảnh báo ≥95% (đọc đúng 3 trạng thái).
- **NFR-2 Hiệu năng:** p95 ≤200 ms, FPS ≥10 trên máy team (profile `simulated`).
- **NFR-3 Privacy:** không lưu/gửi ảnh mặt; 0 raw frame trong artifact/log; 0 egress.
- **NFR-4 License:** mọi thành phần có license rõ (YuNet MIT; MobileNet OpenVINO Apache-2.0); ghi vào manifest.
- **NFR-5 Trung thực:** S (diễn) ≠ N (tự nhiên); `simulated` ≠ thiết bị thật; số không có thì ghi "not evaluated".
- **NFR-6 Tái lập:** mỗi lần chạy có config/seed/commit/model hash.

## 6. Chỉ số & mục tiêu

| Loại | Chỉ số | Mục tiêu |
|---|---|---|
| Impact chính | Alert burden (cảnh báo sai/giờ) | ≤1,0/giờ |
| Impact chính | Phát hiện sự kiện | không thấp hơn cách ngưỡng thô quá **5 điểm %** |
| Impact chính | Time-to-alert | p95 **≤3s** |
| Sản phẩm | Hiểu cảnh báo | **≥95%** người thử đọc đúng |
| Sản phẩm | Chấp nhận | đa số người thử nói tiếp tục dùng (khảo sát ngắn) |
| Sản phẩm | Coverage | **≥90%** điều kiện thường; **≥85%** từng điều kiện |
| Kỹ thuật (nội bộ) | p95/FPS/CPU/RAM | ≤200ms / ≥10 FPS (`simulated`) |
| Privacy | raw frame / egress | **0** |

Cách nhận biết cảnh báo sai: 

 - Cảnh báo trên đoạn không mệt, cooldown 10s, tính trên mỗi giờ.

 - Feed back từ tài xế + HITL tracking dữ liệu theo thời gian (VD: số lần cảnh báo liên tục, số lần nháy mắt, ngáp) 
## 7. Kiểm chứng với người dùng (thay cho "experiment cards")

| Bậc | Làm gì | Pass/fail |
|---|---|---|
| 1. Concierge | 2–3 thành viên xem clip và tự gọi trạng thái để hiểu tiêu chí | Thống nhất được định nghĩa 3 trạng thái |
| 2. Wizard-of-Oz | Giả lập cảnh báo, đo người xem có hiểu đúng không | ≥95% đọc đúng 3 trạng thái |
| 3. Prototype với người dùng thật | 10 tình nguyện viên có consent chạy kịch bản (mắt nhắm kéo dài, quay đầu, mất mặt, kính) | Phát hiện đúng ≥90% tình huống buồn ngủ |
| 4. Pilot nhỏ trong lab/xe đỗ | Chạy liên tục ~15–30 phút/người | Không crash; phản hồi chấp nhận; ghi rõ không phải đường thật |
| 5. (Sau chương trình) | Đo giảm tai nạn/chi phí | Ngoài phạm vi 4 tuần |

B0/M1 chỉ là **kiểm tra kỹ thuật nội bộ** để đảm bảo logic chống hú oan thực sự có tác dụng — không đưa vào kết quả chính.

## 8. Kế hoạch 4 tuần (sản phẩm)

| Tuần | Việc chính | Mốc |
|---|---|---|
| **Tuần 1** | Chốt license/dữ liệu/máy; dựng pipeline + app + dashboard chạy được (vertical slice); Docker; CAN-sim; privacy | Sản phẩm chạy end-to-end trên video mẫu |
| **Tuần 2** | Chống hú oan (thời gian + cooldown + `unavailable`); màn cảnh báo tài xế; nhật ký; Wizard-of-Oz | Người thử hiểu đúng 3 trạng thái |
| **Tuần 3** | Đo trên điều kiện (kính/ánh sáng); nếu có người thật thì chạy prototype; tinh chỉnh UX | Số hú oan/giờ + phát hiện + time-to-alert |
| **Tuần 4** | Pilot nhỏ (nếu kịp + consent); demo 6 case; báo cáo impact + giới hạn; phụ lục privacy/license | Demo hoàn chỉnh + kết quả pilot (hoặc "demo, chưa pilot") |

**Cắt scope khi trễ (theo thứ tự):** pilot → fleet/OTA & cá nhân hóa → runtime int8 → trang trí UI. **Không cắt:** privacy, `unavailable`, chống hú oan, dashboard + nhật ký.

**Phân công gợi ý:** R1 dữ liệu/quyền/nhãn · R2 CV/runtime · R3 logic chống hú oan + đo · R4 app/dashboard/Docker/UX.

## 9. Tiêu chí nghiệm thu

1. Sản phẩm chạy qua Docker: app cảnh báo + dashboard, replay + live.
2. Demo 6 case: đúng / cảnh báo sai (chớp mắt, ngáp, quay đầu) / không quan sát được / đeo kính / thiếu sáng / runtime simulated.
3. Có số **alert burden, phát hiện, time-to-alert**; nếu có pilot thì kèm **hiểu cảnh báo + phản hồi**.
4. Không lưu/gửi ảnh mặt; license rõ; giới hạn được ghi rõ.
5. Không claim đêm/edge/buồn ngủ tự nhiên/giảm tai nạn.

## 10. Rủi ro & câu hỏi mở

| Rủi ro | Xử lý |
|---|---|
| Không kịp pilot | Cắt pilot, gọi đúng là demo |
| Không có người thật/consent | Demo + nói rõ chưa có impact thật |
| Hú oan khi kính/lóa | `unavailable` + báo riêng điều kiện |
| Máy yếu | Giảm feature / measurement-only |

**Câu hỏi mở:** buyer là đội xe (B2B, mặc định) hay tài xế (B2C)? Impact ưu tiên: rủi ro/chi phí, trải nghiệm tài xế, hay quản lý? Có người thật để pilot không? Skill mix 4 người?

## 11. Phụ lục

- Thuật ngữ: `unavailable`, `S` (diễn), `N` (tự nhiên), `simulated`, alert burden.
- Giới hạn: chưa có benchmark máy thật, chưa có số người/phiên, chưa freeze license dữ liệu, chưa có kết quả pilot. Mọi ngưỡng là mục tiêu đặt trước.

