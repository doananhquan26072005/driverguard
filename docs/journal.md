# Development Journal — DriverGuard

> Mỗi ngày làm việc một mục, 2–3 câu: quyết định kỹ thuật và lý do, khó khăn và cách giải quyết, bài học.
> Số liệu lấy từ nhật ký chi tiết từng ngày ở [worklog/](worklog/); lịch sử commit ở [worklog.md](worklog.md).

## 24/09: dựng 14 khối, thử ngay trên dataset thật

Sau khi M0–M7 chạy được, nhóm quyết định đánh giá trên dataset Kaggle thay vì chỉ tin test đơn vị, vì ràng buộc của đề
là chống báo sai ngang với độ chính xác. YawDD (319 clip) cho thấy người ngáp và người đang nói bị tính là nhắm mắt:
122 lần báo microsleep sai; bỏ thời gian nhắm mắt lúc ngáp / nói và hạ `mar_open` 0,6 → 0,45 thì còn 34, recall ngáp
70% → 82%. Bài học: loại báo sai này không test giả nào nghĩ ra trước, phải có dữ liệu thật mới thấy.

## 25/09: lỗi im lặng nguy hiểm hơn lỗi dừng máy

Quyết định cho agent dừng hẳn với `ConfigError` khi `thresholds.yaml` có key lạ (gõ nhầm `mar_opn`), vì một ngưỡng
gõ sai mà vẫn chạy bằng mặc định thì không ai biết. Khó khăn trong ngày là rút camera làm agent thoát; sửa bằng tự kết
nối lại và gửi sự kiện `camera_lost` / `camera_restored` để dashboard thấy xe đang không được giám sát. Cùng ngày báo
sai trên YawDD giảm 23 → 9 nhờ PERCLOS bỏ qua frame ngáp / nói.

## 26/09: model dự phòng đang chạy thay tín hiệu chính

Trên FL3D chỉ 17,9% microsleep ≥ 1,5 s lên được L3, dù EAR tách mắt nhắm rất tốt (AUC 0,987). Nguyên nhân là hai lỗi ở
điều kiện bật CNN mắt (đo độ sáng cả khung thay vì khuôn mặt; chia cho EAR trung bình nên bật đúng lúc mắt nhắm), khiến
96,6% frame do CNN yếu hơn (AUC 0,881) quyết định; sửa xong lên 78,9%, YawDD không hồi quy. Bài học: phải đo xem nhánh
nào thực sự chạy, không chỉ đo từng model riêng lẻ.

## 28–29/09: đưa lên web mà không viết lại logic

Để người khác mở link là thử được bằng camera của họ, nhóm chạy khối 6–12 trong trình duyệt bằng Pyodide, dùng đúng
code Python của thiết bị thay vì viết lại bằng JavaScript: một bộ luật, một bộ test, vẫn đạt 30 FPS trên Chrome. Khó
khăn: GitHub Actions không chạy do lỗi thanh toán của tài khoản, nên toàn bộ kiểm tra CI được chạy ở máy trước mỗi lần
push, và image Railway được build ở máy rồi đẩy lên Docker Hub (54 MB).

## 01/10: mất mặt là "không giám sát được", không phải cảnh báo

Chốt theo PRD: mất mặt ≥ 3 s khi xe chạy chuyển sang trạng thái `unavailable` thay vì báo L2, vì hệ thống không biết
tài xế đang làm gì thì không nên đoán. Chốt thêm bước đăng ký tài xế bắt buộc mỗi chuyến (~10 s) và không lưu qua
chuyến, để có mốc EAR / tư thế riêng từng người mà không giữ dữ liệu khuôn mặt. Cũng sửa cách đo: "báo sai mỗi giờ"
phải có số giờ đo và khoảng tin cậy, không chỉ đếm số lần.

## 02/10: test e2e bắt được lỗi giữa các khối

Khi viết test Playwright cho cả luồng, phát hiện bước "nhắm mắt" của đăng ký khiến bảng tổng kết xếp chuyến "rất nguy
hiểm" dù chưa lái giây nào; từng khối đều đúng, lỗi nằm ở chỗ ghép. Cùng ngày lập bảng FMEA 15 trạng thái hệ thống im
lặng (6 mức Cao) và quyết định 0 km/h thì không cảnh báo gì. Bài học: liệt kê những lúc hệ thống *không* báo được quan
trọng ngang với những lúc nó báo.

## 05/10: thử ngoại tuyến trước khi thêm vào pipeline

Đưa 36 video đã chuyển thành chuỗi số vào CI làm test hồi quy: đổi luật mà kết quả lệch là đỏ, không cần video hay
model. Một ý tưởng mới (tỉ lệ thời lượng chớp mắt) được thử trên trace FL3D trước và kết quả là không thêm vào, vì
không cải thiện gì. Bài học: một prototype rẻ cho kết quả "không làm" vẫn là kết quả đáng ghi lại.

## 06/10: đo rồi mới tối ưu

Rà hiệu năng cho thấy bản Python trên thiết bị đã dư (107 FPS); chỗ chậm nằm ở bản web, cũng là code sẽ đóng vào APK.
Đo trong trình duyệt thật mới thấy model mặt chạy "GPU" trên máy vẽ WebGL bằng phần mềm còn chậm hơn CPU (45 ms so với
9 ms), nên chỉ dùng GPU khi có GPU thật; YOLO chạy hai luồng giảm 172 → 91 ms. Bài học: chỗ nghẽn không nằm ở nơi nhóm
đoán ban đầu.

## 07/10: hai bản chạy cùng luật nhưng khác đầu vào

Bản web dùng `eyeBlink` của MediaPipe thay CNN mắt nhưng lại so với ngưỡng của CNN, nên camera xám / hồng ngoại không
bao giờ lên L3 (0 / 48); cho nó ngưỡng riêng thì đạt 46 / 48. Cùng ngày có bốn phép đo kết thúc bằng "không đổi code"
(ngữ cảnh điện thoại, quy tắc đầu cúi, gục so với cúi, hướng mắt) vì dữ liệu không đủ để chứng minh có lợi. Song song,
giao diện được làm lại trên một design system chung (M57–M65).

## 08/10: audit cả 14 khối, sửa cả con số đã công bố

Một lượt đọc lại toàn bộ code cho 15 phát hiện mức High, không có Critical. Phát hiện đáng nhớ nhất là số "0,98 báo
sai / giờ" đang được dẫn như của cả hệ thống trong khi chỉ là nhánh buồn ngủ; tính mọi nhánh là 1,2 / giờ và tài liệu
được sửa lại. Một đánh đổi được chấp nhận có chủ ý: cho nhắc lại cảnh báo sau cooldown để không nuốt mất cảnh báo thật,
đổi lại báo sai trên tập dev tăng 5 → 7.

## 09/10: viết luật quyết định trước khi nhìn số

Để chọn ngưỡng `risk.drowsy.l1` là 40 hay 50, luật chọn được viết ra trước rồi mới chạy DROZY một lần: giữ 40 (cả hai
đều 0 báo sai, 50 bỏ sót một video buồn ngủ); tập giữ riêng của UTA-RLDD cũng chỉ được đọc một lần. Runtime web được
đóng gói vào bản build kèm Content-Security-Policy, trang không còn tải code từ CDN (0 yêu cầu ra ngoài). Khó khăn: nhiều
phiên làm việc sửa cùng một cây thư mục nên test đỏ có lúc là của việc khác; cách xử lý là mỗi phiên một mốc và ghi rõ
trạng thái commit từng mốc.

## Tổng hợp cho slide "Challenges & Learnings"

| Khó khăn | Cách giải quyết | Bài học |
|---|---|---|
| Ngáp và nói bị tính là ngủ gật (122 microsleep sai trên YawDD) | Bỏ thời gian nhắm mắt lúc ngáp / nói, PERCLOS bỏ frame đó | Báo sai chỉ lộ ra trên dữ liệu thật |
| Microsleep chỉ bắt được 17,9% trên FL3D | Sửa hai điều kiện bật CNN mắt → 78,9% | Đo nhánh nào thực sự chạy, không chỉ đo từng model |
| Web chậm, thiết bị thì dư FPS | Đo trong trình duyệt thật; GPU chỉ khi có GPU thật, YOLO WebGPU 94 → 17 ms | Đo trước, tối ưu sau |
| Lỗi nằm giữa các khối (đăng ký → bảng tổng kết) | Test e2e Playwright, test hồi quy bằng trace trong CI | Test từng khối không đủ |
| Con số báo sai dẫn sai phạm vi | Audit 14 khối, sinh lại số liệu, ghi rõ phạm vi | Số liệu phải đi kèm phạm vi và khoảng tin cậy |
| Dễ chỉnh ngưỡng theo chính tập kiểm tra | Luật khai báo trước, tập giữ riêng đọc một lần | Tách quyết định khỏi việc nhìn kết quả |
