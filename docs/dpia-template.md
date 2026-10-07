# Mẫu hồ sơ đánh giá tác động xử lý dữ liệu cá nhân: DriverGuard

> **Mẫu để đơn vị triển khai hoàn thiện trước khi thu dữ liệu của tài xế thật** (M48,
> [data-policy.md](data-policy.md) mục 9, [pilot-readiness.md](pilot-readiness.md) D5). Phần "Hệ thống"
> đã được nhóm kỹ thuật điền theo mã nguồn ngày 06/10/2026; phần "Đơn vị" để trống.
> Bản nháp kỹ thuật, **không phải tư vấn pháp lý**. Chưa đối chiếu từng mục với biểu mẫu chính thức của
> nghị định hướng dẫn Luật Bảo vệ dữ liệu cá nhân (*chưa đọc văn bản gốc của biểu mẫu*): đơn vị phải rà
> soát với người có chuyên môn và chuyển sang biểu mẫu đúng quy định.

## 1. Các bên

| Mục | Nội dung |
|---|---|
| Bên kiểm soát dữ liệu (đơn vị vận tải) | **[tên, địa chỉ, người đại diện]** |
| Người phụ trách bảo vệ dữ liệu | **[họ tên, liên hệ]** |
| Bên xử lý / nơi host máy chủ | **[nhà cung cấp, quốc gia đặt máy chủ]** |
| Chủ thể dữ liệu | Tài xế của đơn vị: **[số lượng]** người |
| Ngày lập / ngày xem lại | **[ngày]** / mỗi khi đổi phiên bản phần mềm hoặc đổi mục đích |

## 2. Mô tả việc xử lý

| Câu hỏi | Hệ thống (đã điền) | Đơn vị |
|---|---|---|
| Mục đích | Cảnh báo tài xế buồn ngủ / mất tập trung khi lái; xem lại chuyến; chỉnh ngưỡng để giảm báo sai | **[mục đích cụ thể của đơn vị]** |
| Dữ liệu thu | Metadata dạng số và mã: thời điểm, mức, lý do cảnh báo, số đo lúc đó (ví dụ giây nhắm mắt, PERCLOS), tốc độ xe, điểm mệt mỗi phút, bản tổng kết chuyến, trạng thái giám sát, phiên bản phần mềm | |
| Dữ liệu **không** thu | Ảnh, video, âm thanh; vị trí GPS; mẫu nhận dạng khuôn mặt (số đo khuôn mặt dùng trong chuyến bị xoá khi hết chuyến, không rời thiết bị) | |
| Có phải dữ liệu nhạy cảm? | Hình ảnh khuôn mặt được xử lý **trong bộ nhớ của thiết bị trên xe** và không được lưu hay truyền. Số liệu gửi đi mô tả trạng thái tỉnh táo của một người khi làm việc | **[đánh giá của đơn vị / người có chuyên môn: có thuộc loại dữ liệu nhạy cảm theo luật không]** |
| Xử lý ở đâu | Phân tích: trên thiết bị trong xe (hoặc trong trình duyệt ở bản xem thử). Lưu: database trên máy chủ của đơn vị | **[nơi đặt máy chủ]** |
| Ai truy cập | 4 vai trò: quản trị, kỹ sư, quản lý (xem cả đội), tài xế (chỉ xem của mình). Mọi lượt xem của ba vai trò đầu được ghi nhật ký, tài xế xem được | **[danh sách người được cấp từng vai trò]** |
| Giữ bao lâu | Cảnh báo và mẫu theo phút 60 ngày, tổng kết chuyến 365 ngày, nhật ký truy cập 365 ngày; tự xoá | **[giữ nguyên hay đổi; lý do]** |
| Chuyển cho bên khác / ra nước ngoài | Hệ thống không chuyển cho ai. Bản web tải thư viện từ CDN nước ngoài (jsdelivr): CDN thấy địa chỉ IP của trình duyệt, không có dữ liệu giám sát | **[máy chủ có đặt ở nước ngoài không; hợp đồng với nơi host]** |

## 3. Sự cần thiết và mức độ tương xứng

| Câu hỏi | Trả lời |
|---|---|
| Có cách ít xâm phạm hơn để đạt mục đích không? | Hệ thống đã chọn cách ít nhất trong các cách dùng camera: không lưu, không gửi hình. **[Đơn vị: vì sao biện pháp tổ chức (lịch nghỉ, giới hạn giờ lái) chưa đủ]** |
| Cơ sở pháp lý của việc xử lý | **[đơn vị điền: thoả thuận với người lao động / nghĩa vụ pháp lý / …]**. Lưu ý Luật 91/2025/QH15 Điều 25 khoản 3: biện pháp giám sát chỉ được áp dụng trên cơ sở người lao động biết rõ |
| Tài xế được thông báo thế nào | Màn hình đồng ý trước khi đăng ký khuôn mặt; [mẫu thông báo](driver-notice-template.md). **[ngày gửi, cách xác nhận đã nhận]** |
| Tài xế từ chối thì sao | Từ chối đăng ký khuôn mặt: vẫn lái, vẫn được giám sát bằng mốc chung. **[Từ chối cả việc giám sát: đơn vị quy định]** |

## 4. Rủi ro và biện pháp

Mức: Thấp / Vừa / Cao, theo đánh giá của nhóm kỹ thuật; đơn vị xem lại.

| # | Rủi ro với tài xế | Mức | Biện pháp đã có trong hệ thống | Phần còn lại của đơn vị |
|---|---|---|---|---|
| 1 | Hình ảnh khuôn mặt bị lưu hoặc lộ | Thấp | Khung hình chỉ trong RAM; thiết bị chặn trước khi gửi và máy chủ từ chối mọi trường ảnh / base64; test tĩnh trong CI quét lời gọi ghi ảnh | Không cài thêm phần mềm ghi hình lên cùng thiết bị mà không đánh giá lại |
| 2 | Cảnh báo sai bị dùng để kỷ luật | Vừa | Nút "Cảnh báo sai"; dashboard nhắc không dùng một cảnh báo đơn lẻ; không có bảng xếp hạng tài xế (có test chặn endpoint mới) | **[quy trình xem xét của đơn vị; quyền giải trình của tài xế]** |
| 3 | Hệ thống báo sai nhiều với một nhóm người (đeo kính, mắt nhỏ, khẩu trang) | Vừa | Mốc riêng theo từng tài xế (đăng ký khuôn mặt). Chưa có số đo theo nhóm trên dữ liệu lái thật | Theo dõi tỉ lệ "Cảnh báo sai" theo tài xế trong giai đoạn thử |
| 4 | Người không có thẩm quyền xem dữ liệu | Vừa | Phân quyền 4 vai trò, token có hạn, nhật ký truy cập chỉ ghi thêm, tài xế xem được ai đã xem | Cấp vai trò tối thiểu; thu hồi tài khoản khi đổi việc |
| 5 | Lộ database (máy chủ bị xâm nhập, bản sao lưu thất lạc) | Vừa | Không có ảnh trong database; mật khẩu và khoá thiết bị chỉ lưu dạng băm; file database chỉ chủ sở hữu đọc được; image không chứa database hay bí mật. **Database không được mã hoá ở mức ứng dụng** | Bật mã hoá ổ đĩa ở nơi host; quản lý và xoá bản sao lưu; **[kế hoạch ứng phó khi lộ dữ liệu]** |
| 6 | Dữ liệu bị giữ quá lâu | Thấp | Tự xoá theo thời hạn; yêu cầu xoá từ giao diện; lệnh xoá theo tài xế và xoá tài khoản | Xoá khi tài xế nghỉ việc; bản sao lưu không tự xoá |
| 7 | Giám sát liên tục gây áp lực tâm lý | **[đơn vị đánh giá]** | Không cảnh báo khi xe đứng yên; quản lý không xem trực tiếp hình ảnh (không có hình); chỉ các tình huống khẩn (ngủ gật lặp lại, không phản ứng) mới báo quản lý ngay | **[trao đổi với tài xế / công đoàn]** |
| 8 | Tài xế tin vào hệ thống hơn mức nó làm được | Vừa | HUD nói rõ khi không giám sát được và vì sao; [bảng trạng thái im lặng](safety-fmea.md) liệt kê các trường hợp hệ thống không cảnh báo được, trong đó còn ba dòng mức Cao | Đào tạo tài xế: hệ thống chỉ hỗ trợ |

## 5. Quyền của chủ thể dữ liệu

| Quyền | Cách thực hiện trong hệ thống | Người xử lý, thời hạn |
|---|---|---|
| Được biết | Màn hình đồng ý, mẫu thông báo, [data-policy.md](data-policy.md) | **[…]** |
| Truy cập, nhận bản sao | Dashboard tài khoản tài xế; nút "Tải dữ liệu của tôi" (file JSON) | Tự phục vụ |
| Biết ai đã xem | Bảng "Ai đã xem dữ liệu của tôi" | Tự phục vụ |
| Phản đối | Nút "Cảnh báo sai" trên HUD | **[ai xem xét]** |
| Xoá | Nút "Yêu cầu xoá dữ liệu"; quản trị xoá hoặc từ chối kèm lý do, có ghi nhật ký | **[người quyết định, số ngày trả lời]** |
| Chỉnh sửa | Không có: hệ thống không cho sửa số đo. Sai thì đánh dấu "Cảnh báo sai" | |

## 6. Kết luận

- Rủi ro còn lại sau các biện pháp: **[đơn vị kết luận]**.
- Điều kiện trước khi bắt đầu: **[ví dụ: đã gửi thông báo cho mọi tài xế; đã bật mã hoá ổ đĩa; đã chỉ định
  người trả lời yêu cầu]**.
- Người lập: **[…]**. Người duyệt: **[…]**. Ngày: **[…]**.
