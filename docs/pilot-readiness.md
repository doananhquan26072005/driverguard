# Tiêu chí sẵn sàng pilot

Cập nhật: 05/10/2026 (M36). Một trang để trả lời: **DriverGuard còn thiếu gì để chạy thử trên xe thật?**

**Kết luận hiện tại: chưa sẵn sàng pilot.** Trong 24 tiêu chí dưới đây: 4 đạt, 6 đạt một phần, 5 chưa
đạt, 9 chưa đo hoặc chưa có. Ba khoảng trống lớn nhất: chưa có thiết bị trên xe (hub, tốc độ thật), chưa
có giờ lái thật nào có nhãn, và còn ba trạng thái hệ thống im lặng ở mức Cao.

Cách đọc:
- **Mục tiêu** lấy từ PRD của dự án, từ ràng buộc trong CLAUDE.md, hoặc từ quy định EU về hệ thống cảnh
  báo buồn ngủ (DDAW) và mất tập trung (ADDW). Hai quy định EU không áp dụng cho thiết bị lắp thêm ở
  Việt Nam; chúng được dùng làm mốc vì là yêu cầu đo được, công khai, cho đúng loại hệ thống này.
- **Hiện có** chỉ ghi số đã có trong `eval/results/` hoặc đã có test; không có thì ghi "chưa đo".
- Số đo trên dataset công khai (clip ngắn hoặc diễn) không thay được số đo trên xe thật.

## 1. Bảng tiêu chí

### A. Phát hiện đúng

| # | Tiêu chí | Mục tiêu | Hiện có | Trạng thái | Việc cần làm |
|---|---|---|---|---|---|
| A1 | Cảnh báo sai mỗi giờ lái | ≤ 1,0 / giờ, tính cả cận trên CI 95 % (PRD §6). Cần ≥ 3,7 giờ lái tỉnh táo không lần sai nào | Dataset: FL3D L1 4,6 (0,56–16,7), L2 6,9 (1,43–20,3), L3 2,3 (0,06–12,9) trên 0,43 giờ; YawDD 6,9 (3,31–12,7) trên 1,45 giờ; SUST 8,5 (5,56–12,5) trên 3,05 giờ. Giờ lái thật có nhãn: 0 | **Chưa đạt** | [ghi nhãn khi chạy thử](improvements.md#viec-nhan-demo), [dò ngưỡng trên UTA-RLDD](improvements.md#viec-toi-uu-nguong) |
| A2 | Thời gian từ lúc bắt đầu nhắm mắt / nhìn lệch đến cảnh báo | p95 ≤ 3 s (PRD §6) | Chưa có công cụ đo. Theo cấu hình: L3 phát ngay khi mắt nhắm đủ 1,5 s | Chưa đo | [ghi số từ camera](improvements.md#viec-prd) |
| A3 | Bắt được ngủ gật ngắn | ≥ 90 % số lần (PRD §7 bậc 2) | FL3D: nhắm ≥ 1,5 s đạt L3 75/95 (78,9 %); nhắm ≥ 3 s 11/11 | **Chưa đạt** (với 1,5 s) | [nhìn xuống / nhắm mắt](improvements.md#viec-nhin-xuong), [dò ngưỡng trên UTA-RLDD](improvements.md#viec-toi-uu-nguong) |
| A4 | Độ nhạy khi tài xế buồn ngủ thật (KSS ≥ 8) | Trung bình > 40 %, cận dưới CI 90 % > 20 %, ≥ 10 người, ≥ 10 sự kiện [E1 Phần 2, điểm 3.1 và tiêu chí chấp nhận] | Mọi dữ liệu buồn ngủ đang có là diễn | Chưa đo | [dò ngưỡng trên UTA-RLDD](improvements.md#viec-toi-uu-nguong) (UTA-RLDD, xấp xỉ), [ghi nhãn khi chạy thử](improvements.md#viec-nhan-demo) |
| A5 | Cảnh báo nhìn khỏi đường đủ sớm | Trong 3,5 s ở ≥ 50 km/h; trong 6 s ở 20–50 km/h [E2 điểm 3.3.2.1–3.3.2.2] | Cấu hình: 1,5 s khi chạy nhanh, 2,0 s còn lại, từ 5 km/h. Đo bằng góc đầu: đầu thẳng mà mắt liếc xuống thì không bắt được | Một phần | [hướng mắt](improvements.md#viec-huong-nhin) |
| A6 | Chạy được ngày và đêm | Hoạt động hiệu quả cả ngày lẫn đêm [E1 điểm 3.2.1, E2 điểm 3.2.1] | Đã đo trên video lái đêm (FL3D / NITYMED, diễn) và ngày (YawDD, SUST). Chưa thử camera hồng ngoại, chưa xử lý chói đèn pha | Một phần | [model mắt mới](improvements.md#viec-model-mat), [tăng tương phản](improvements.md#viec-choi) |
| A7 | Phát hiện dùng điện thoại | Chưa đặt mục tiêu số | Không có dataset đúng góc camera. State Farm (camera bên hông): recall 2,1 % | Chưa đo | [ghi số từ camera](improvements.md#viec-prd) |

### B. Không im lặng khi không giám sát được

| # | Tiêu chí | Mục tiêu | Hiện có | Trạng thái | Việc cần làm |
|---|---|---|---|---|---|
| B1 | Các trạng thái im lặng mức Cao đã đóng | 0 dòng mức Cao trong [safety-fmea.md](safety-fmea.md) | Còn 3: app bị hệ điều hành dừng (dòng 4), kính râm (dòng 5), gục ra khỏi khung khi chưa thấy mắt nhắm (dòng 6) | **Chưa đạt** | [kính râm](improvements.md#viec-mat-bi-che), [cảnh báo cần xác nhận](improvements.md#viec-xac-nhan), [APK](improvements.md#viec-apk), [kênh cảnh báo vật lý](improvements.md#viec-coi-roi) |
| B2 | Ảnh xấu thì báo "không giám sát được", không đoán | Mất mặt, ảnh mờ, góc xấu, lóa (PRD FR-6) | Mới có mất mặt ≥ 3 s khi xe chạy, mất camera, lỗi xử lý | Một phần | [chất lượng frame](improvements.md#viec-chat-luong) |
| B3 | Máy chủ biết xe mất liên lạc | Trong 90 s | Nhịp "còn sống" 30 s, tab "Đội xe" (M33; test backend và e2e trên web). Chưa chạy trên thiết bị thật | Đạt | – |

### C. Thiết bị trên xe

| # | Tiêu chí | Mục tiêu | Hiện có | Trạng thái | Việc cần làm |
|---|---|---|---|---|---|
| C1 | Tốc độ xử lý trên hub | ≥ 15 FPS suốt chuyến (CLAUDE.md) | Chưa có hub. Máy dev (Mac ARM): 151,8 FPS, p95 7,2 ms ([benchmark.md](../eval/results/benchmark.md)); số này không nói gì về hub | Chưa đo | [đo phần cứng](improvements.md#viec-do-phan-cung) |
| C2 | Chạy lâu không xuống cấp | RAM không tăng dần, không bị hạ xung vì nóng | Chưa chạy dài ở đâu cả | Chưa đo | [đo phần cứng](improvements.md#viec-do-phan-cung) |
| C3 | Tốc độ và xi nhan thật | Đọc từ xe (CAN) hoặc GPS | Giả lập bằng tay (`tools/drive_sim.py`, `#/drive`) | **Chưa đạt** | [tốc độ GPS](improvements.md#viec-gps) |
| C4 | App chạy trên hub không cần mạng | APK, mở là chạy | Chỉ có bản web xem thử | Chưa có | [APK](improvements.md#viec-apk) |
| C5 | Tiếng cảnh báo nghe được trong cabin | Phần lớn âm trong 200–8 000 Hz, 50–90 dB [E1 điểm 3.4.3.2] | Âm báo trong code: 196–1 568 Hz. Chưa đo độ to trên loa của hub; chưa có còi rời | Một phần | [đo phần cứng](improvements.md#viec-do-phan-cung), [kênh cảnh báo vật lý](improvements.md#viec-coi-roi) |

### D. Dữ liệu và quyền riêng tư

| # | Tiêu chí | Mục tiêu | Hiện có | Trạng thái | Việc cần làm |
|---|---|---|---|---|---|
| D1 | Không ảnh nào rời thiết bị | 0 (CLAUDE.md; PRD NFR-3; vòng kín theo [E1 điểm 2.3.2]) | Thiết bị chặn trước khi gửi, máy chủ từ chối nội dung giống ảnh (`tests/test_backend/test_privacy.py`, `test_publisher.py`) | Đạt | – |
| D2 | Có chính sách dữ liệu và thời hạn lưu được thực thi | Văn bản + tự xoá | [data-policy.md](data-policy.md); tự xoá sau 60 / 365 ngày (M37, có test) | Đạt | – |
| D3 | Tài xế biết rõ biện pháp giám sát trước khi áp dụng | Luật 91/2025/QH15 Điều 25 khoản 3 | Màn hình đồng ý trước khi đăng ký khuôn mặt. Thông báo chính thức của đơn vị vận tải: chưa có | Một phần | data-policy mục 9 |
| D4 | Mất mạng không mất sự kiện | 0 sự kiện mất | Thiết bị Python: hàng đợi SQLite, có test. App / web: chỉ giữ trong bộ nhớ | Một phần | [hàng đợi offline](improvements.md#viec-outbox-web) |
| D5 | Hồ sơ đánh giá tác động xử lý dữ liệu | Có trước khi thu dữ liệu tài xế thật | Chưa làm | Chưa có | data-policy mục 9 |

### E. Con người và vận hành

| # | Tiêu chí | Mục tiêu | Hiện có | Trạng thái | Việc cần làm |
|---|---|---|---|---|---|
| E1 | Người xem hiểu đúng cảnh báo | ≥ 9/10 người gọi đúng 3 trạng thái (PRD NFR-1) | Chưa tổ chức | Chưa đo | [phần PRD còn lại](improvements.md#viec-prd-con-lai) |
| E2 | Thay đổi code không lặng lẽ đổi hành vi cảnh báo | Test hồi quy trên trace chạy trong CI | 36 video, 17 763 frame, so sự kiện / cảnh báo / điểm (M34) | Đạt | – |
| E3 | Tín hiệu và ngưỡng "tạm" đã được chứng minh hoặc tắt | Không còn ngưỡng tạm góp vào cảnh báo | Còn tạm: chớp chậm, nhướn mày, cúi nhìn xuống, leo thang L1 → L2, các bước đăng ký | **Chưa đạt** | [tín hiệu tạm](improvements.md#viec-ablation), [nhìn xuống / nhắm mắt](improvements.md#viec-nhin-xuong) |
| E4 | Quy trình chạy thử an toàn | Có người ngồi cạnh sẵn sàng can thiệp; không để người buồn ngủ thật lái để lấy dữ liệu [E1 Phần 2, điểm 2.2] | Chưa viết | Chưa có | [ghi nhãn khi chạy thử](improvements.md#viec-nhan-demo) |

## 2. Lộ trình theo giai đoạn

Mỗi giai đoạn có cổng: chưa qua cổng thì không sang giai đoạn sau.

| Giai đoạn | Làm gì | Cổng để qua |
|---|---|---|
| **0. Bản xem thử (hiện tại)** | Web `#/live`, dashboard, tốc độ giả lập, đo trên dataset công khai | Đã có: D1, D2, B3, E2 |
| **1. Đo và dữ liệu** | Công cụ ghi số từ camera + nhãn bấm phím ([ghi số từ camera](improvements.md#viec-prd)); dò ngưỡng trên UTA-RLDD có tập kiểm tra giữ riêng ([dò ngưỡng trên UTA-RLDD](improvements.md#viec-toi-uu-nguong)); chứng minh hoặc tắt tín hiệu tạm ([tín hiệu tạm](improvements.md#viec-ablation)); hướng mắt ([hướng mắt](improvements.md#viec-huong-nhin)); chất lượng frame ([chất lượng frame](improvements.md#viec-chat-luong)); kính râm ([tải NTHU-DDD](improvements.md#viec-tai-dataset), [kính râm](improvements.md#viec-mat-bi-che)); buổi 10 người ([phần PRD còn lại](improvements.md#viec-prd-con-lai)) | A2 đo được và ≤ 3 s; A3 ≥ 90 % trên tập kiểm tra; A4 có số xấp xỉ; E1, E3 đạt; B2 đạt |
| **2. Hub và app** | Chọn hub và camera; đo tài nguyên ([đo phần cứng](improvements.md#viec-do-phan-cung)); APK + hàng đợi offline ([APK](improvements.md#viec-apk), [hàng đợi offline](improvements.md#viec-outbox-web)); tốc độ thật ([tốc độ GPS](improvements.md#viec-gps)); xác nhận cảnh báo và báo quản lý ([cảnh báo cần xác nhận](improvements.md#viec-xac-nhan)); kênh cảnh báo vật lý ([kênh cảnh báo vật lý](improvements.md#viec-coi-roi)) | C1–C5 đạt trên hub; B1 không còn dòng Cao; D4 đạt |
| **3. Pilot 1–3 xe** | Tài xế tình nguyện, có người ngồi cạnh ghi nhãn ([ghi nhãn khi chạy thử](improvements.md#viec-nhan-demo)), chỉ lái khi tỉnh táo, mỗi xe ≥ 4 giờ | D3, D5, E4 đạt **trước khi** bắt đầu. Kết quả cần: A1 cận trên CI ≤ 1,0 / giờ; không có lần "im lặng" nào ngoài bảng FMEA |
| **4. Mở rộng** | Thêm xe, bỏ người ngồi cạnh, so nhiều chuyến ([so nhiều chuyến](improvements.md#viec-nhieu-chuyen)) | A1 giữ được theo từng tài xế; có quy trình xử lý yêu cầu dữ liệu của tài xế |

Giai đoạn 3 đo **báo sai**, không đo bỏ sót: không được để người buồn ngủ thật cầm lái. Độ nhạy (A4) lấy
từ dataset có buồn ngủ thật hoặc từ mô phỏng lái có giám sát.

## 3. Những mốc EU mà DriverGuard cố ý làm khác

| Quy định | DriverGuard | Vì sao |
|---|---|---|
| DDAW bật trên 70 km/h, hoạt động 65–130 km/h [E1 điểm 3.1.4–3.1.5] | Nhánh buồn ngủ chạy ở mọi tốc độ trên 0 km/h | Xe tải, xe khách ở Việt Nam chạy phần lớn dưới 70 km/h |
| ADDW bật trên 20 km/h [E2 điểm 3.1.1] | Nhánh mất tập trung chạy từ 5 km/h | Nhìn điện thoại lúc bò trong phố vẫn nguy hiểm |
| Chỉ ghi và giữ dữ liệu trong vòng kín [E1, E2 điểm 2.3.2] | Xử lý ảnh là vòng kín; số liệu cảnh báo được gửi lên cho quản lý | Mục đích quản lý đội xe, nằm ngoài hai quy định, theo [data-policy.md](data-policy.md) |
| DDAW có thể đánh giá gián tiếp qua tay lái | Nhìn trực tiếp mắt và đầu bằng camera | Thiết bị lắp thêm không đọc được góc lái |

Tham khảo thêm, **nguồn thứ cấp, chưa đọc protocol gốc**: Euro NCAP 2026 được mô tả là phân biệt ngủ gật
ngắn (nhắm mắt 1–2 s), ngủ (≥ 3 s) và không phản ứng (nhắm ≥ 6 s hoặc không nhìn lại đường trong 3 s
sau cảnh báo) [N1]. DriverGuard có mốc 1,5 s (L3); mốc 6 s "không phản ứng" chưa làm ([cảnh báo cần xác nhận](improvements.md#viec-xac-nhan)).

## Nguồn

- [E1] Commission Delegated Regulation (EU) 2021/1341 (driver drowsiness and attention warning), văn bản
  gốc: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R1341
- [E2] Commission Delegated Regulation (EU) 2023/2590 (advanced driver distraction warning), văn bản gốc:
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2590
- [N1] Smart Eye, "What's Changing in Euro NCAP's 2026 Safety Ratings?":
  https://smarteye.se/blog/euro-ncap-2026-whats-changing/ và Anyverse, "Euro NCAP 2026":
  https://anyverse.ai/euro-ncap-2026-how-leading-automakers-are-preparing-for-in-cabin-safety-standards/
- Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và các nguồn về dữ liệu: xem [data-policy.md](data-policy.md).
- Trong dự án: [PRD.md](PRD.md) §6, §7, §9; [safety-fmea.md](safety-fmea.md);
  [eval/results/report.md](../eval/results/report.md) (đo 25–26/09 và 01/10/2026);
  [improvements.md](improvements.md) (các việc được dẫn bằng tên, vì số thứ tự đổi mỗi lần xoá việc).
