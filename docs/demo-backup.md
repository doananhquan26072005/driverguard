# Dự phòng khi demo trực tiếp gặp sự cố

Ba tầng, theo chương 13 của Technical Book:

| Tầng | Là gì | Ở đâu |
|---|---|---|
| 1 | Demo trực tiếp | <https://c4-app-135.up.railway.app> |
| 2 | Video quay sẵn | [video-demo.md](video-demo.md) (YouTube; file gốc ở `presentation/demo-clips/` trên máy của team) |
| 3 | Ảnh từng bước có chú thích | Trang này, 16 ảnh ở [screenshots/demo-steps/](screenshots/demo-steps/) |

Ảnh chụp ngày 13/10/2026 bằng Playwright trên bản build của nhánh `DAQuan` (có trang `#/privacy` của M106), 1280 × 800.
Màn hình trong xe lấy từ `#/hud-preview` (trạng thái cố định, đã ẩn thanh chọn kịch bản); dashboard chạy trên một
database tạm với một ca lái **mô phỏng** (5 cảnh báo, 45 mẫu theo phút, các dòng mang nhãn "mô phỏng"). Không ảnh nào
có khuôn mặt, không ảnh nào là số liệu lái thật. Lời gợi ý ở mỗi bước rút từ [kich-ban-demo-3-phut.md](kich-ban-demo-3-phut.md).

## Tầng 3: 16 bước

### 1. Trang đầu: đăng nhập, hoặc dùng thử không cần tài khoản

![Trang đầu: đăng nhập, hoặc dùng thử không cần tài khoản](screenshots/demo-steps/01-trang-dau.png)

Nói: "Đây là trang đầu của DriverGuard. Tài xế đăng nhập, hoặc dùng thử mà không gửi số liệu đi."

### 2. Xe đang đỗ: xin phép trước khi làm quen khuôn mặt

![Xe đang đỗ: xin phép trước khi làm quen khuôn mặt](screenshots/demo-steps/02-xin-dong-y.png)

Nói: "Xe đang đỗ. DriverGuard xin phép tài xế, và nói rõ không lưu, không gửi ảnh."

### 3. Làm quen khuôn mặt khoảng 10 giây

![Làm quen khuôn mặt khoảng 10 giây](screenshots/demo-steps/03-lam-quen-khuon-mat.png)

Nói: "Làm quen khuôn mặt trong mười giây, vì mắt mỗi người mỗi khác."

### 4. Đang lái, tỉnh táo: L0

![Đang lái, tỉnh táo: L0](screenshots/demo-steps/04-binh-thuong-L0.png)

Nói: "Đang chạy, tài xế tỉnh táo: màn hình yên lặng."

### 5. Cầm điện thoại: L2

![Cầm điện thoại: L2](screenshots/demo-steps/05-dien-thoai-L2.png)

Nói: "Đưa điện thoại lên: mức hai, màu cam kèm lời nhắc."

### 6. Nhìn khỏi đường quá lâu: L2, có nút "Cảnh báo nhầm?"

![Nhìn khỏi đường quá lâu: L2, có nút "Cảnh báo nhầm?"](screenshots/demo-steps/06-nhin-lech-L2-bao-nham.png)

Nói: "Nhìn khỏi đường quá lâu: mức hai. Thấy nhầm, tài xế chạm một nút, phản hồi tới kỹ sư."

### 7. Nhắm mắt từ 1,5 giây khi xe chạy: L3

![Nhắm mắt từ 1,5 giây khi xe chạy: L3](screenshots/demo-steps/07-ngu-gat-L3.png)

Nói: "Nhắm mắt từ một giây rưỡi: mức ba, còi lặp tới khi mở mắt."

### 8. Kết thúc ca lái: bảng tổng kết

![Kết thúc ca lái: bảng tổng kết](screenshots/demo-steps/08-tong-ket-ca-lai.png)

Nói: "Kết thúc ca lái, tài xế nhận bảng tổng kết."

### 9. Dashboard của quản lý: nhật ký sự kiện (ca lái mô phỏng)

![Dashboard của quản lý: nhật ký sự kiện (ca lái mô phỏng)](screenshots/demo-steps/09-dashboard-nhat-ky.png)

Nói: "Quản lý chỉ nhận số liệu, không có hình, kể cả những lần tài xế báo nhầm."

### 10. Dashboard: timeline mệt mỏi (ca lái mô phỏng)

![Dashboard: timeline mệt mỏi (ca lái mô phỏng)](screenshots/demo-steps/10-dashboard-timeline.png)

Nói: "Độ mệt theo từng phút, kèm các cảnh báo."

### 11. Edge case: xe đang đỗ

![Edge case: xe đang đỗ](screenshots/demo-steps/11-xe-do-khong-bao.png)

Nói: "Xe đang dừng thì không cảnh báo, vì báo lúc này chỉ làm phiền."

### 12. Edge case: đang xi nhan

![Edge case: đang xi nhan](screenshots/demo-steps/12-xi-nhan.png)

Nói: "Bật xi nhan rồi nhìn gương: không báo."

### 13. Edge case: camera bị che

![Edge case: camera bị che](screenshots/demo-steps/13-che-camera.png)

Nói: "Camera bị che: màn hình nói rõ là đang không giám sát được."

### 14. Edge case: không còn thấy tài xế

![Edge case: không còn thấy tài xế](screenshots/demo-steps/14-roi-khung-hinh.png)

Nói: "Không còn thấy tài xế: màn hình hỏi 'Bạn vẫn ổn chứ?'."

### 15. Trang Quyền riêng tư

![Trang Quyền riêng tư](screenshots/demo-steps/15-quyen-rieng-tu.png)

Nói: "Thu gì, không thu gì, giữ bao lâu: tất cả nằm ở trang Quyền riêng tư."

### 16. Hướng dẫn sử dụng

![Hướng dẫn sử dụng](screenshots/demo-steps/16-huong-dan.png)

Nói: "Mỗi màn hình có trong hướng dẫn, kèm ý nghĩa và việc nên làm."

## Ảnh trên điện thoại (390 × 844)

Cùng bản build, cùng ngày. Ở cả tám trang, trang không cuộn ngang (đo `scrollWidth` so với bề rộng cửa sổ: 0 px thừa).
Đây là Chromium giả lập cỡ màn hình điện thoại, **chưa phải điện thoại thật**.

| Trang đầu | HUD L0 | HUD L2 điện thoại | HUD L3 |
|---|---|---|---|
| ![Trang đầu](screenshots/mobile/01-trang-dau.png) | ![HUD L0](screenshots/mobile/02-hud-L0.png) | ![HUD L2 điện thoại](screenshots/mobile/03-hud-L2-dien-thoai.png) | ![HUD L3](screenshots/mobile/04-hud-L3.png) |

| Tổng kết ca lái | Hướng dẫn sử dụng | Quyền riêng tư | Dashboard của tài xế |
|---|---|---|---|
| ![Tổng kết ca lái](screenshots/mobile/05-tong-ket-ca-lai.png) | ![Hướng dẫn sử dụng](screenshots/mobile/06-huong-dan.png) | ![Quyền riêng tư](screenshots/mobile/07-quyen-rieng-tu.png) | ![Dashboard của tài xế](screenshots/mobile/08-dashboard-tai-xe.png) |
