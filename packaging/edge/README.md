# DriveGuard: chạy với camera của bạn

DriveGuard theo dõi mắt, đầu và điện thoại của tài xế qua webcam để cảnh báo buồn ngủ và mất tập trung.

**Hình ảnh không rời khỏi máy bạn.** Mọi xử lý chạy trên máy, không lưu ảnh ra đĩa. Chỉ các số liệu cảnh báo (mức L0–L3, lý do, thời điểm) được gửi lên web để xem lại.

## Bạn cần có

- Máy macOS, Windows hoặc Linux có webcam.
- **Python 3.11 hoặc 3.12**: tải tại https://www.python.org/downloads/. Trên Windows, khi cài nhớ tick *Add python.exe to PATH*.
- **Trình duyệt Chrome hoặc Edge.**
- Thông tin admin DriveGuard cấp cho bạn:
  - Tài khoản đăng nhập web.
  - **Device ID**, ví dụ `cam-002`.
  - **Device key**, bắt đầu bằng `dgk_`. Đây là mã bí mật, không chia sẻ cho người khác.

## Cài đặt (làm một lần)

Giải nén file zip, mở Terminal (macOS/Linux) hoặc PowerShell (Windows) trong thư mục vừa giải nén.

**macOS / Linux:**
```
./install.sh
```

**Windows:**
```
powershell -ExecutionPolicy Bypass -File install.ps1
```

Cài đặt mất vài phút và cần khoảng 1 GB dung lượng. Xong sẽ có file `edge.env`. Mở file đó bằng trình soạn thảo văn bản và điền:

```
DG_DEVICE_ID=cam-002
DG_DEVICE_KEY=dgk_...mã admin gửi...
```

## Chạy

**macOS / Linux:**
```
./run.sh
```

**Windows:**
```
powershell -ExecutionPolicy Bypass -File run.ps1
```

Sau khi chạy lệnh:
1. Cho phép Terminal/PowerShell dùng camera nếu máy hỏi. Trên macOS: *System Settings → Privacy & Security → Camera*.
2. Một cửa sổ xem trước camera sẽ mở ra. Khoảng 6 giây sau, trình duyệt tự mở trang **HUD**.
3. Nếu Chrome hỏi *cho phép truy cập thiết bị trong mạng cục bộ*, bấm **Allow**.
4. Nhìn thẳng vào camera khoảng 10–20 giây đầu để hệ thống học mắt và tư thế đầu của bạn.

Muốn dừng thì bấm `Ctrl+C` trong Terminal.

Xem lại lịch sử cảnh báo: mở trang web, đăng nhập bằng tài khoản được cấp.

## Các mức cảnh báo

| Mức | Khi nào |
|---|---|
| **L3** (đỏ) | Nhắm chặt mắt ≥ 1,5 giây khi đang lái |
| **L2** | Quay đầu khỏi đường ≥ 2 giây, dùng điện thoại, mặt ra khỏi khung hình ≥ 3 giây, hoặc buồn ngủ nặng |
| **L1** | Dấu hiệu buồn ngủ tích luỹ: nhắm mắt nhiều, ngáp, gật đầu |

Tốc độ xe được giả lập, vì chưa có kết nối CAN thật. Theo mặc định có những lúc xe "dừng đèn đỏ", và khi đó cảnh báo mất tập trung tạm tắt. Muốn xe luôn chạy (lái đêm trên cao tốc) thì dùng:

```
./run.sh --scenario config/scenarios/highway_night.yaml
```

## Gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| `Need Python 3.11 or 3.12` | Cài Python 3.12 rồi chạy lại lệnh cài đặt |
| HUD báo "Không kết nối được thiết bị" | Kiểm tra lệnh chạy còn đang chạy; dùng Chrome/Edge; bấm Allow khi được hỏi; mở HUD **trên cùng máy** đang chạy camera |
| `unknown device key` hoặc không thấy sự kiện trên web | Kiểm tra lại `DG_DEVICE_KEY` trong `edge.env` |
| Không mở được camera | Cấp quyền camera cho Terminal/PowerShell, đóng các ứng dụng khác đang dùng camera (Zoom, Meet) |
