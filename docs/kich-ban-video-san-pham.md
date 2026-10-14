# Kịch bản và hướng dẫn quay video sản phẩm 3 phút

Video người thật, quay trong phòng, kể theo cách của các video giới thiệu DMS thương mại. Không dùng xe: hệ thống
chưa chạy trên xe thật, nên video không dựng cảnh trong xe. Hai bản trước là quay màn hình:
[kich-ban-demo.md](kich-ban-demo.md) (5 phút) và [kich-ban-demo-3-phut.md](kich-ban-demo-3-phut.md) (3 phút, cắt từ
clip có sẵn). Bản này dùng lại số liệu, câu chữ đã kiểm và các cảnh đồ hoạ của hai bản đó.

Thông điệp không đổi: **báo đúng lúc, im đúng lúc, và không ảnh nào rời thiết bị.**

Dài 2 phút 56 giây (giới hạn 3 phút), 1920 × 1080, 30 FPS, lời đọc tiếng Việt, phụ đề in sẵn. Bốn phần bắt buộc nằm
ở: team 0:30, use case chính 0:40, kiến trúc 1:28, edge case 2:01.

Chưa quay gì. Buổi thử ở mục 4.4 phải làm trước ngày quay. Việc đã chốt và còn mở ở mục 8.

## 1. Các video tham khảo làm gì

Đã xem ngày 12/10 bằng khung hình cắt mỗi 2–3 giây, phụ đề và phần mô tả. Chưa nghe tiếng, nên nhận xét về giọng đọc
và nhạc là suy từ hình và phụ đề.

| Video | Dài | Cách kể | Lấy về |
|---|---|---|---|
| [STONKAM DMS](https://youtu.be/9APN_-wHLck) (video mẫu) | 2:17 | Lời đọc và phụ đề in sẵn; người thật trong xe xen với hình mà hệ thống nhìn thấy | Khung sáu đoạn, cặp cảnh "người lái làm gì, hệ thống thấy gì", lưới 2 × 2, tiếng nhắc của chính sản phẩm |
| [Qualcomm Research](https://youtu.be/-zu_uLDMV90) | 3:02 | Hình hệ thống chiếm cả màn hình, nhãn chỉ vào từng thứ hệ thống suy ra; nửa sau là khẩu trang, kính râm, camera bị che, bị xoay | Giải thích kiến trúc bằng nhãn trên hình thật; edge case là một chương riêng |
| [oToBrite](https://youtu.be/QegbLYZhrxI) | 2:52 | Thẻ tiêu đề cho từng phần; mỗi chức năng là hình hệ thống đặt cạnh hình người lái, bên dưới ghi luật ("nhắm mắt > 2 s") | Ghi ngưỡng ngay dưới cảnh |
| [Samsara](https://youtu.be/PazzdlNtB-k) | 1:10 | Chữ chỉ có ở đầu và cuối; giữa là một câu chuyện: tài xế, cảnh báo trong xe, quản lý nhận tin rồi gọi điện | Quản lý là người thật ngồi ở bàn làm việc |
| [Seeing Machines Guardian](https://youtu.be/Yl_Ea_8iW5w) | 2:05 | Phim ngắn: tài xế lái đêm, suýt tai nạn, một con số trên nền tối, rồi mới tới sản phẩm | Mở bằng khoảnh khắc nguy hiểm, không mở bằng logo |
| [Cipia Driver Sense](https://youtu.be/nBs3K0bsxyc) | 2:42 | Cảnh ngang người lái xen với hình xám của hệ thống, trên hình chỉ có vài chữ trạng thái | Chữ trên hình hệ thống càng ít càng tốt |
| [Smart Eye, The Road Trip](https://youtu.be/fT1Mr7SkEW4) | 2:19 | Hai người ngồi trong buồng lái mô phỏng đặt trong phòng, vừa làm vừa nói; có cảnh nhìn gương trước khi đổi làn thì không bị nhắc | Bối cảnh của mình: quay trong phòng, cho thấy rõ tốc độ là giả lập; edge case "nhìn gương" |

Video mẫu chia sáu đoạn:

| Đoạn | Nội dung | Hình |
|---|---|---|
| 0:00–0:16 | Vấn đề | Kẹt xe, tai nạn nhìn từ trên cao, tài xế ngáp, gọi điện, dụi mắt; một con số lớn trên hình |
| 0:16–0:48 | Sản phẩm | Thiết bị trên nền trắng, rồi trong xe, ngày và đêm. Cặp cảnh: người lái cúi nhìn điện thoại, hình camera có khung mặt, landmark và nhãn đỏ |
| 0:48–1:14 | Phía quản lý | Tài xế xe khách, dashboard có bản đồ và cửa sổ báo động, hoạt hình về việc dùng dữ liệu |
| 1:14–1:46 | Các hành vi bắt được | Lưới 2 × 2 hình hệ thống, mỗi ô một hành vi; tiếng là giọng nhắc của thiết bị |
| 1:46–2:00 | Cài đặt | Hiệu chỉnh khuôn mặt và chỉnh thông số trên máy tính bảng |
| 2:00–2:17 | Kết | Các loại xe khác, thành phố về đêm, câu sứ mệnh, logo |

Kỹ thuật lặp lại ở nhiều video:

1. Mở bằng mối nguy, không mở bằng công ty.
2. Hai góc của cùng một khoảnh khắc: người lái làm gì, hệ thống thấy gì.
3. Người xem được nghe và thấy đúng cảnh báo của sản phẩm.
4. Có người thứ hai nhận thông tin: quản lý.
5. Tắt tiếng vẫn hiểu, vì chữ trên hình mang đủ ý.
6. Cảnh ngắn: video mẫu có khoảng 45 cảnh, mỗi cảnh 2–4 giây (ước lượng từ khung hình).

Điểm khác nên nhấn: ở video mẫu, video cảnh báo được tải lên trung tâm giám sát và quản lý xem hình tài xế trên
dashboard. DriverGuard thì không, nên cảnh quản lý (3.6) phải cho thấy màn hình chỉ có số liệu.

Phần lớn các video này quay trong xe thật; riêng Smart Eye quay trong phòng. Mình theo Smart Eye về bối cảnh, theo
video mẫu về khung và nhịp. Không video nào có phần team, kiến trúc hay giới hạn: ba phần này là của mình, trình bày
theo cách của Qualcomm và oToBrite. Chỉ mượn cấu trúc và kỹ thuật: không dùng hình, nhạc hay câu chữ của các video này.

## 2. Khung video

| Chương | Thời gian | Nội dung | Mượn từ |
|---|---|---|---|
| 1. Vấn đề | 0:00–0:16 | Một lần nhắm mắt 1,5 giây, rồi con số | Guardian, STONKAM |
| 2. Sản phẩm và team | 0:16–0:40 | Thiết bị trên bàn quay, bốn thành viên | STONKAM |
| 3. Use case chính: một ca lái | 0:40–1:28 | Làm quen khuôn mặt, L2 điện thoại, L3 nhắm mắt, lưới bốn hành vi, quản lý | STONKAM, Samsara, Smart Eye |
| 4. Kiến trúc | 1:28–2:01 | Nhãn trên hình thật, rồi ba cảnh đồ hoạ | Qualcomm |
| 5. Edge case | 2:01–2:37 | Hai lần hệ thống im, hai lần nói rõ là không thấy, một giới hạn | Qualcomm, oToBrite, Smart Eye |
| 6. Kết | 2:37–2:56 | Số liệu kèm phạm vi, giới hạn, team | STONKAM |

Nếu ban tổ chức muốn team xuất hiện đầu tiên: chuyển cảnh 2.3 lên đầu, lời giữ nguyên.

Ba loại hình:

- **Người lái:** người đóng tài xế làm gì. Máy A quay.
- **HUD:** thiết bị nói gì. Quay màn hình của chính điện thoại chạy sản phẩm, có tiếng.
- **Hình hệ thống:** thuật toán thấy gì. `tools/debug_view.py` chạy trên camera của laptop cùng lúc: landmark, trục
  đầu, EAR, khung điện thoại.

Bốn kiểu bố cục:

- **Cặp:** cảnh người lái cả khung, HUD là hình nhỏ ở góc dưới phải, rộng khoảng 40 %. Khi HUD là nhân vật chính (L3
  đỏ) thì đảo lại.
- **Lưới 2 × 2:** bốn hình hệ thống, dưới mỗi ô là tên hành vi và ngưỡng.
- **Nhãn:** hình hệ thống cả khung, đường kẻ chỉ vào từng thứ.
- **Đồ hoạ:** các cảnh nền tối đã có ở `presentation/demo-clips/3-phut/dung-hf/`.

## 3. Kịch bản

Lời đọc khoảng 480 âm tiết, 96–120 giây ở 4–5 âm tiết mỗi giây. Đã đếm từng dòng: dòng nào cũng ngắn hơn cảnh của
nó, năm dòng sát giờ nhất là 1.2, 2.3, 4.1, 5.5 và 6.1. Chữ trong ngoặc kép ở cột "Chữ và tiếng" là chữ hiện trên hình.

Suốt chương 3 và 5 có nhãn ở góc dưới trái: "Quay trong phòng · tốc độ và xi nhan giả lập".

### Chương 1. Vấn đề (0:00–0:16)

| Cảnh | Thời gian | Hình | Lời đọc | Chữ và tiếng |
|---|---|---|---|---|
| 1.1 | 0:00–0:04 | Cận mắt người đóng tài xế khép lại (lượt quay cận của cảnh 3.4). Cắt sang nền đen | Không lời | Còi L3 của sản phẩm từ giây 1,5. Trên nền đen: "1,5 giây" |
| 1.2 | 0:04–0:10 | Xe chạy trên đường, quay từ vỉa hè hoặc cầu bộ hành | "Ở năm mươi cây số một giờ, nhắm mắt một giây rưỡi là xe đi hai mươi mét không ai nhìn đường." | "50 km/h × 1,5 giây ≈ 20 m" |
| 1.3 | 0:10–0:16 | Giao thông TP.HCM lúc chiều tối, quay từ cầu bộ hành | "Gần bảy nghìn hai trăm người Việt Nam thiệt mạng vì tai nạn giao thông, chỉ trong chín tháng đầu năm nay." | "7 198 người · Việt Nam, 9 tháng đầu năm 2026 · mọi nguyên nhân" |

### Chương 2. Sản phẩm và team (0:16–0:40)

| Cảnh | Thời gian | Hình | Lời đọc | Chữ và tiếng |
|---|---|---|---|---|
| 2.1 | 0:16–0:23 | Cận người đóng tài xế, vẻ mệt, dụi mắt, nền trơn. Hai thẻ chữ hiện lần lượt | "Cảnh báo hay báo nhầm thì tài xế tắt đi, còn nhiều hệ thống gửi video khuôn mặt lên cloud." | "Báo nhầm nhiều → bị tắt" · "Video khuôn mặt → cloud" |
| 2.2 | 0:23–0:30 | Cận điện thoại trên giá, máy đẩy chậm vào màn hình xanh "Tỉnh táo". Rồi toàn cảnh bàn quay | "DriverGuard theo dõi tài xế ngay trên thiết bị: báo đúng lúc, im đúng lúc, và không ảnh nào rời khỏi máy." | Logo và "Giám sát tài xế ngay trên thiết bị". Nhãn nhỏ: "Trong video: bản web chạy trên điện thoại" |
| 2.3 | 0:30–0:40 | Bốn cảnh 2 giây, mỗi người trong vai của mình ở bàn quay: tài xế, người điều khiển xe, quản lý, kỹ sư. Rồi cả bốn người | "Chúng tôi là Quân, Dũng, Huy và Khuê, team DriverGuard, khoá AI20K Cohort 4 tại VinUni. Đây là một ca lái thử, với tốc độ giả lập." | Dải tên: họ tên và phần việc, theo bảng Team của [README](../README.md#team); mỗi người tự sửa |

### Chương 3. Use case chính: một ca lái (0:40–1:28)

| Cảnh | Thời gian | Hình | Lời đọc | Chữ và tiếng |
|---|---|---|---|---|
| 3.1 | 0:40–0:47 | Toàn cảnh bàn quay: người đóng tài xế ngồi trước điện thoại, người điều khiển xe ngồi cạnh. Cận ngón tay chạm "Đồng ý, bắt đầu". HUD ba bước làm quen, tua 2 lần | "Xe đang đỗ. Hệ thống xin đồng ý, rồi làm quen khuôn mặt mười giây để lấy mốc riêng cho từng tài xế." | Nhãn "Quay trong phòng · tốc độ và xi nhan giả lập" hiện từ đây. Giọng hướng dẫn của sản phẩm, để nhỏ |
| 3.2 | 0:47–0:51 | Cận tay người điều khiển xe bấm "Chạy đều 50". HUD lên 50 km/h, xanh | "Cho xe chạy năm mươi. Màn hình xanh: tỉnh táo." | Không |
| 3.3 | 0:51–1:00 | Cặp: người đóng tài xế đưa điện thoại lên tai, HUD chuyển cam "Bỏ điện thoại xuống" | "Đưa điện thoại lên tai: mức hai." Rồi im | Tiếng bíp và giọng nhắc của sản phẩm. "L2 · điện thoại" |
| 3.4 | 1:00–1:11 | Một cú máy 7 giây không cắt, quay qua vai, thấy cả nghiêng mặt lẫn màn hình điện thoại: mắt nhắm, màn hình đỏ, còi kêu, mắt mở. Rồi HUD đỏ cả khung 2 giây, hình hệ thống 2 giây (đường EAR tụt) | "Nhắm mắt quá một giây rưỡi: mức ba. Đỏ toàn màn hình, còi kêu tới khi mở mắt." | Còi L3, hạ nhạc nền. "L3 · nhắm mắt từ 1,5 giây" |
| 3.5 | 1:11–1:19 | Lưới 2 × 2 hình hệ thống: rời mắt, ngáp, điện thoại, nhắm mắt | "Rời mắt khỏi đường, ngáp, điện thoại, nhắm mắt: mỗi hành vi một ngưỡng thời gian riêng." | Dưới từng ô: "Rời mắt từ 2 giây → L2" · "Ngáp → cộng điểm buồn ngủ" · "Điện thoại từ 60 % của 2 giây → L2" · "Nhắm sâu từ 1,5 giây → L3". Tiếng: các câu nhắc của sản phẩm nối nhau |
| 3.6 | 1:19–1:28 | Cận ngón tay chạm "Cảnh báo nhầm?". Người đóng quản lý ở bàn khác, quay qua vai vào laptop. Quay màn hình dashboard: báo cáo ca lái, nhật ký sự kiện có dòng "Tài xế báo sai" | "Thấy báo nhầm, tài xế chạm một nút. Quản lý chỉ nhận số liệu, không có hình: báo cáo ca lái và nhật ký sự kiện." | "Chỉ số liệu · không có hình" |

### Chương 4. Kiến trúc (1:28–2:01)

| Cảnh | Thời gian | Hình | Lời đọc | Chữ và tiếng |
|---|---|---|---|---|
| 4.1 | 1:28–1:39 | Người đóng kỹ sư đứng sau lưng người lái, chỉ vào hình hệ thống trên laptop (2 giây). Rồi hình hệ thống của lượt cầm điện thoại, cả khung: landmark bật lên (phím `l`), nhãn hiện lần lượt: "MediaPipe: landmark", "YOLOv8n: điện thoại", "EAR, MAR, góc đầu". Cuối cảnh hình mờ đi, chỉ còn số | "Bên trong là pipeline mười bốn khối, không có LLM. Ảnh chỉ đi qua sáu khối đầu và chỉ nằm trong RAM: MediaPipe lấy landmark, YOLOv8n tìm điện thoại." | "Khối 1–6 · frame chỉ nằm trong RAM" |
| 4.2 | 1:39–1:48 | Đồ hoạ "Quyết định bằng con số" (cảnh 14 của `dung-hf`) | "Từ khối bảy chỉ còn con số. Risk engine gộp điểm buồn ngủ, điểm mất tập trung với tốc độ và xi nhan, ra mức L0 đến L3." | Như cảnh 14 |
| 4.3 | 1:48–1:56 | Đồ hoạ "Chỉ JSON rời thiết bị" (cảnh 15), thẻ JSON, thêm dấu gạch trên biểu tượng ảnh | "Rời thiết bị chỉ có JSON. Máy chủ từ chối mọi thứ giống ảnh." | "HTTP 422 cho mọi payload giống ảnh" |
| 4.4 | 1:56–2:01 | Đồ hoạ "≈ 7 ms" (cảnh 16) | "Cả vòng lặp mất khoảng bảy mili giây mỗi frame trên máy dev." | "máy dev · không tính YOLOv8n (luồng riêng)" |

### Chương 5. Edge case (2:01–2:37)

| Cảnh | Thời gian | Hình | Lời đọc | Chữ và tiếng |
|---|---|---|---|---|
| 5.1 | 2:01–2:09 | Cận tay người điều khiển xe bấm "Dừng xe". HUD "Xe đang đỗ", 0 km/h. Người đóng tài xế nhắm mắt 3 giây, rồi cầm điện thoại: HUD vẫn xanh | "Xe dừng đèn đỏ: nhắm mắt hay cầm điện thoại đều không báo, vì báo lúc này chỉ làm phiền." | Thẻ chương "Im đúng lúc". Không có tiếng cảnh báo |
| 5.2 | 2:09–2:19 | Cận tay bấm "Trái". Người đóng tài xế quay sang mốc "gương trái" 3 giây: xanh. Bấm "Tắt", cùng động tác: cam "Nhìn đường!" | "Bật xi nhan trái rồi quay sang trái như nhìn gương: không báo. Tắt xi nhan, cùng động tác đó: mức hai." | "Xi nhan bật: không báo" · "Xi nhan tắt: L2" |
| 5.3 | 2:19–2:24 | Bàn tay che ống kính điện thoại. Thẻ xanh dương "Tạm ngưng theo dõi", lý do camera bị che | "Che camera: hệ thống nói rõ đang tạm ngưng theo dõi, không đoán mò." | Thẻ chương "Không thấy thì nói ra" |
| 5.4 | 2:24–2:32 | Người đóng tài xế nghiêng người ra khỏi khung hình. HUD hỏi "Bạn vẫn ổn chứ?" và đếm ngược. Chạm màn hình | "Tài xế rời khung hình: màn hình hỏi 'Bạn vẫn ổn chứ?'. Không trả lời thì báo quản lý." | Số giây đã trôi ở góc hình ("+9 giây"), vì cảnh có cắt |
| 5.5 | 2:32–2:37 | Người đóng tài xế liếc xuống điện thoại đặt trên đùi, đầu giữ thẳng. HUD vẫn xanh | "Còn điều chưa làm được: liếc mắt xuống mà đầu giữ thẳng thì hệ thống chưa bắt được." | Thẻ vàng "Giới hạn · 0 / 13 lần thử trước laptop" |

### Chương 6. Kết (2:37–2:56)

| Cảnh | Thời gian | Hình | Lời đọc | Chữ và tiếng |
|---|---|---|---|---|
| 6.1 | 2:37–2:50 | Đồ hoạ kết (cảnh 21 của `dung-hf`, chữ giữ nguyên): ba số, rồi ô giới hạn | "Không ảnh nào rời thiết bị. Chín mươi bảy phẩy sáu phần trăm cảnh báo mức ba là đúng trên bộ FL3D. Báo nhầm còn khoảng một phẩy hai lần mỗi giờ trên dữ liệu công khai, và hệ thống chưa chạy trên xe thật." | Dưới mỗi số là phạm vi của nó |
| 6.2 | 2:50–2:56 | Cả bốn người ở bàn quay. Logo, khẩu hiệu, địa chỉ bản chạy thử và mã QR | "DriverGuard: báo đúng lúc, im đúng lúc." | `c4-app-135.up.railway.app` |

## 4. Quay

### 4.1 Phân vai

Cả bốn người quay cùng một buổi và ai cũng có mặt trên hình.

| Vai trên hình | Cảnh | Việc ngoài hình | Hậu kỳ |
|---|---|---|---|
| Tài xế | Chương 1, 2, 3, 5 | Không: diễn suốt khối A | Soát con số và nhãn theo mục 6 |
| Người điều khiển xe | 3.1, 3.2, 5.1, 5.2 | Điện thoại chạy sản phẩm (đăng nhập, quay màn hình) và laptop chạy `debug_view` | Đồ hoạ trong `dung-hf`, tiếng của sản phẩm |
| Quản lý | 3.6 | Thư ký: bảng cảnh, bấm giờ, nhật ký lượt quay | Phụ đề, nhạc, cho người ngoài xem thử |
| Kỹ sư | 4.1 | Quay phim máy A, ánh sáng | Dựng từ bản thô tới bản cuối |

Ai đóng vai nào là việc của team. Một gợi ý: người đã diễn trong các clip ngày 09/10 đóng tài xế, vì các số 9 / 9 và
8 / 8 ở [kich-ban-demo.md](kich-ban-demo.md) đo trên người đó.

### 4.2 Thiết bị

- Một phòng yên tĩnh, tường trơn, có cửa sổ hoặc đèn chiếu vào mặt. Một bàn, hai ghế.
- Điện thoại chạy sản phẩm: mở `#/live` ở bản Railway (sau khi deploy bản trong máy), đặt trên giá, xoay ngang.
- Laptop có `.venv` của repo, đặt ngay sau điện thoại: chạy `debug_view` trên camera của nó và quay lại cửa sổ đó.
- Điện thoại điều khiển: mở trang `#/drive?code=…` từ nút "Điều khiển xe · mã XXXXXX" của `#/live`. Trang này gửi
  tốc độ qua backend, nên cả hai máy cần mạng.
- Máy A: điện thoại quay đẹp nhất, trên chân máy hoặc cầm tay.
- Điện thoại thứ tư làm đạo cụ cho cảnh nghe điện thoại.
- Laptop cho dashboard ở cảnh 3.6 (dùng lại laptop trên cũng được, vì quay ở khối khác).
- Giá điện thoại, sạc, khăn lau màn hình, hai mẩu giấy dán làm mốc "đường" và "gương trái".

### 4.3 Bố trí bàn quay

```
            tường trơn, sau lưng người lái

   người điều khiển xe        NGƯỜI LÁI
   (ngồi cạnh)                    │  nhìn thẳng vào mốc "đường"
                                  ▼
 ─────────────────── mặt bàn ───────────────────
          [điện thoại chạy sản phẩm]   trên giá
          [laptop chạy debug_view]     ngay sau điện thoại, kê cao
 ───────────────────────────────────────────────
            cửa sổ hoặc đèn, sáng chiếu vào mặt

   máy A: bên hông cho cảnh ngang, sau vai cho cảnh 3.4
```

- Cả hai camera (điện thoại và laptop) thấy trọn khuôn mặt; điện thoại không che mặt trong hình của laptop.
- Mốc "đường" dán thẳng trước mặt, phía trên laptop. Mốc "gương trái" dán bên trái, đặt theo buổi thử.
- Mặt đủ sáng, sáng từ phía trước, không ngồi quay lưng ra cửa sổ. Mặt tối thì tỉ lệ bắt nhắm mắt giảm mạnh (40 %
  so với 93 %, đo trước laptop).
- Không kính râm. Người đeo kính thì xem trước có bị loá không.
- Làm quen khuôn mặt lại mỗi khi giá điện thoại bị xê dịch.
- Chạm vào trang `#/live` một lần sau khi mở, để trình duyệt cho phát tiếng.
- Bật "Không làm phiền" trên mọi máy: thông báo riêng tư lọt vào bản quay màn hình là phải quay lại.
- Mọi máy quay 1080p, 30 FPS, cầm ngang, khoá nét và khoá sáng.

Để hình giống video sản phẩm hơn là buổi demo trên lớp: quay cận nhiều hơn toàn (mắt, bàn tay, màn hình); nền gọn và
tối hơn mặt; cảnh tĩnh đặt máy trên chân; mỗi cảnh quay dư 3 giây ở đầu và cuối.

Lệnh chạy hình hệ thống trên laptop, bật trước mỗi khối quay rồi quay lại cửa sổ bằng Cmd + Shift + 5:

```bash
.venv/bin/python tools/debug_view.py --source 0 --speed 50 --quiet
```

Phím `l` bật tắt landmark, `g` bật tắt đồ thị. Nếu hình hiện ra là camera của một iPhone ở gần thì thử `--source 1`.
Tốc độ ở đây là tham số riêng của công cụ, không nối với điện thoại điều khiển; cảnh 5.1 (xe dừng) không dùng hình
hệ thống.

### 4.4 Buổi thử, trước ngày quay

Một giờ, đúng bàn và đúng các máy sẽ quay, sau khi bản Railway đã deploy. Các số đo đang có đều đo với `#/live` chạy
trên laptop; chưa có mục nào dưới đây được kiểm trên điện thoại.

| Thử | Đạt khi |
|---|---|
| Mở `#/live` trên điện thoại, đăng nhập tài khoản tài xế, làm quen khuôn mặt | Xong ba bước, HUD xanh |
| Điện thoại điều khiển bấm "Chạy đều 50" | HUD lên 50 km/h |
| Nhắm mắt, điện thoại lên tai, quay đầu: mỗi động tác ba lần | Cả chín lần ra đúng mức cảnh báo |
| Bật quay màn hình trên điện thoại, làm lại ba động tác | Cảnh báo không chậm đi thấy rõ; file có tiếng còi và giọng nhắc |
| Chạy `debug_view` trên laptop cùng lúc, quay lại cửa sổ | Landmark bám mặt, có khung điện thoại, điện thoại trên giá không che mặt |
| Xi nhan trái rồi quay sang mốc "gương trái", xem số Yaw ở "Chi tiết kỹ thuật" | Yaw trong khoảng 38–56° (khoảng đo ngày 09/10); có xi nhan thì không báo, không có thì báo |
| Ngáp; liếc xuống mà đầu giữ thẳng | Ghi lại hệ thống phản ứng thế nào, để giữ hay bỏ ô ngáp (3.5) và cảnh 5.5 |

Ba dòng đầu không đạt thì chuyển sang mục 7.

### 4.5 Luật khi quay

1. Cảnh 3.4 phải là một cú máy: không cắt giữa lúc mắt nhắm và lúc màn hình đỏ.
2. Không ghép cảnh người lái của lượt này với HUD hay hình hệ thống của lượt khác rồi trình bày như một.
3. Nhắm mắt L3 quay sau cùng: sau một lần L3, màn hình giữ mức L1 "Hãy tìm chỗ dừng nghỉ" khoảng 40 giây (đo ngày
   09/10).
4. Không dùng đạo cụ, bối cảnh hay tiếng động làm người xem tưởng là đang ở trong xe.
5. Cảnh đường phố quay khi đứng trên vỉa hè hoặc cầu bộ hành. Không quay rõ mặt người ngoài team và biển số xe.
6. Người đóng tài xế đồng ý cho quay mặt. File gốc để ngoài git (cả `presentation/demo-clips/` đang nằm ngoài git).

### 4.6 Thứ tự quay

Mỗi lượt quay ba lần đạt. Đầu mỗi lượt: lướt tay qua ống kính điện thoại và laptop làm mốc đồng bộ, nhìn mốc "đường"
10 giây (`debug_view` cần 10 giây để học mốc mắt mở), rồi mới diễn. Thư ký ghi giờ, mã cảnh và lần đạt.

**Khối A, ở bàn quay (khoảng 2 giờ kể cả lắp đặt)**

| Lượt | Cho cảnh | Diễn | Giữ | Máy A |
|---|---|---|---|---|
| A1 | 2.2 | Điện thoại trên giá, màn hình xanh | 10 giây | Cận, đẩy máy chậm; rồi toàn cảnh bàn quay |
| A2 | 3.1 | Ngồi vào ghế, chạm "Đồng ý, bắt đầu", làm ba bước | Hết ba bước, khoảng 10 giây | Toàn cảnh, rồi cận ngón tay |
| A3 | 3.2, 5.1, 5.2 | Người điều khiển xe bấm "Chạy đều 50", "Dừng xe", "Trái", "Tắt" | Mỗi nút 3 giây | Cận tay |
| A4 | 3.3, 3.5, 4.1 | Điện thoại lên tai | 4 giây sau khi HUD đổi màu (cảnh báo tới sau khoảng 2,4 giây) | Ngang |
| A5 | 3.5, 3.6 | Quay đầu sang phải; rồi chạm "Cảnh báo nhầm?" | 4 giây (cảnh báo tới sau khoảng 3 giây) | Ngang, rồi cận ngón tay |
| A6 | 3.5 | Ngáp, miệng mở rộng | 2–3 giây | Ngang |
| A7 | 5.1 | Xe về 0 km/h. Nhắm mắt, rồi điện thoại lên tai | Mỗi động tác 3–4 giây | Ngang |
| A8 | 5.2 | 50 km/h. Xi nhan trái, quay sang mốc "gương trái". Tắt xi nhan, chờ 3 giây, làm lại | Lần một ít nhất 3 giây; lần hai tới khi hiện "Nhìn đường!" | Ngang |
| A9 | 5.3 | Che ống kính điện thoại | Tới khi lý do đổi thành camera bị che, khoảng 5 giây | Cận tay và màn hình |
| A10 | 5.4 | Nghiêng người ra khỏi khung | Tới khi hiện "Bạn vẫn ổn chứ?", khoảng 9 giây; rồi chạm màn hình | Qua vai |
| A11 | 5.5 | Liếc xuống điện thoại trên đùi, đầu thẳng | 4 giây | Ngang |
| A12 | 2.1 | Dụi mắt, vẻ mệt | 6 giây | Cận mặt |
| A13 | 3.4, 1.1 | Nhắm chặt mắt | 2,5–3 giây rồi mở | Qua vai, nghiêng mặt và màn hình trong một khung. Thêm một lượt cận mắt cho 1.1 |

Ghi chú cho A8: xi nhan chỉ nới thêm 30° về phía đang bật và còn nới 2 giây sau khi tắt. Lần đầu phải giữ ít nhất 3
giây, lâu hơn 2,5 giây mà hệ thống cần để báo khi không có xi nhan.

**Khối B, cùng phòng (30 phút):** cảnh 2.3 (mỗi người trong vai của mình), 2 giây đầu của 4.1 (kỹ sư chỉ vào hình hệ
thống) và 6.2 (cả bốn người, máy A trên chân, hẹn giờ).

**Khối C, đường phố (30 phút):** cảnh 1.2 và 1.3.

**Khối D, cùng phòng (30 phút):** cảnh 3.6. Đăng nhập tài khoản quản lý, mở ca lái vừa quay; quay người, rồi quay
màn hình. Điện thoại phải đăng nhập tài khoản tài xế lúc quay khối A: "Dùng thử không lưu" thì dashboard không có gì.

## 5. Dựng

Phần người thật dựng trong phần mềm dựng mà người dựng đã quen; đồ hoạ làm trong `dung-hf` rồi xuất thành file.

1. Chép file về một ổ, mỗi mã cảnh một thư mục, đánh dấu lần đạt theo nhật ký.
2. Cắt bản quay màn hình của điện thoại (HUD) và của laptop (hình hệ thống) theo mốc lướt tay của từng lượt.
3. Dựng thô theo bảng mục 3 với lời đọc tạm thu bằng điện thoại, khoá độ dài từng cảnh.
4. Đồ hoạ trong `dung-hf/index.html`: dời mốc giây của cảnh 14, 15, 16, 21; thêm lưới 3.5, nhãn 4.1, dải tên, nhãn
   góc và thẻ chương. Xuất từng cảnh thành file rồi đưa vào phần mềm dựng.
5. Thu lời thật trong phòng kín, mỗi cảnh một file đặt tên theo mã cảnh. Giọng đọc phải khác hẳn giọng nhắc của sản
   phẩm (NamMinh, nam, trầm), để người xem phân biệt lời dẫn với lời sản phẩm.
6. Phụ đề in sẵn: font Inter như HUD, tối đa hai dòng. Mỗi câu tô màu một cụm theo màu mức cảnh báo của HUD ("mức
   hai" cam, "mức ba" đỏ, "không báo" xanh).
7. Tiếng: còi và giọng nhắc của sản phẩm nằm trên track riêng, không bị nhạc đè. Nhạc không lời, nhỏ hơn giọng
   khoảng 18–20 dB, hạ thêm ở các cảnh 1.1, 3.3, 3.4, 3.5.
8. Màu: chỉ cân sáng cho cảnh người thật. Không áp bộ lọc màu lên bản quay HUD, vì màu của HUD mang nghĩa.
9. Xuất `presentation/video_demo.mp4`. Kiểm: `ffprobe` báo dưới 180 giây; xem một lượt tắt tiếng, nghe một lượt
   không nhìn hình; đối chiếu từng chữ trên hình với mục 6; cho một người ngoài team xem một lần rồi kể lại.

## 6. Nhãn bắt buộc và câu không được nói

| Chỗ | Nhãn trên hình |
|---|---|
| Mọi cảnh có tốc độ hoặc xi nhan (chương 3, 5) | "Quay trong phòng · tốc độ và xi nhan giả lập" |
| 2.2 | "Trong video: bản web chạy trên điện thoại" |
| Mọi hình hệ thống (3.4, 3.5, 4.1) | "Công cụ debug của kỹ sư, chạy trên camera laptop cùng lúc" |
| 1.3 | Khoảng ngày và "mọi nguyên nhân" |
| 4.4 | "máy dev · không tính YOLOv8n (luồng riêng)" |
| 5.5 | "0 / 13 lần thử trước laptop" |
| 6.1, số 97,6 % | "FL3D: video lái đêm, do người diễn" |
| 6.1, số 1,2 lần mỗi giờ | "dữ liệu công khai, người ngồi trước laptop; chưa đạt mục tiêu 1 lần" |
| 6.1, ô giới hạn | "Chưa chạy trên xe thật", như slide kết đang có |

Giữ nguyên các mục "Những câu không được nói" của [kich-ban-demo.md](kich-ban-demo.md#những-câu-không-được-nói-trong-video)
và [kich-ban-demo-3-phut.md](kich-ban-demo-3-phut.md#những-câu-không-được-nói). Thêm cho bản này:

- Không nói, và không để người xem hiểu, rằng video quay trong xe, rằng hệ thống đọc tốc độ hay xi nhan từ xe, hay
  đã thử trên đường.
- Không gọi điện thoại trong video là thiết bị gắn xe: thiết bị đích chưa có. Không nêu FPS của điện thoại: số 30 FPS
  là của trình duyệt trên máy dev.
- Không nói hình hệ thống là màn hình của sản phẩm.
- Không nối số 7 198 với buồn ngủ: đó là mọi nguyên nhân.
- Thẻ JSON ở 4.3 là request của chuyến demo ngày 09/10: không nói là của ca lái vừa xem.
- Nhạc lấy từ nguồn cho phép dùng lại; cảnh đường phố tự quay. Ghi nguồn nhạc ở phần mô tả video.
- Ở phần mô tả video ghi rõ: hình khuôn mặt do máy quay và phần mềm quay màn hình ghi lại, có sự đồng ý của người
  đóng tài xế; sản phẩm không lưu hình.

## 7. Nếu buổi thử không đạt

- **Bản web không chạy ổn trên điện thoại:** chạy `#/live` trên laptop với camera của nó, như các clip ngày 12/10.
  Nhãn ở 2.2 đổi thành "bản web chạy trên laptop". Camera laptop khi đó đã bận, nên hình hệ thống lấy theo cách
  khác: một điện thoại quay mặt người lái bằng camera sau, sau buổi quay chạy
  `debug_view.py --source <file> --speed 50 --quiet` trên từng clip (file phát đúng tốc độ thật).
- **Quay màn hình làm điện thoại chậm, hoặc file không có tiếng:** bỏ quay màn hình, máy A quay thẳng vào màn hình
  điện thoại cho các cảnh cặp, tiếng lấy từ máy A.

## 8. Đã chốt và còn mở

Đã chốt ngày 12/10:

- Tự quay, không dùng xe; cả bốn người cùng quay.
- Điện thoại chạy sản phẩm; camera laptop cho hình hệ thống.
- Quay trên bản Railway, sau khi deploy bản đang có trong máy.
- Dựng: phần mềm dựng cho phần người thật, `dung-hf` cho đồ hoạ.

Còn mở:

- Giọng đọc: người trong team hay TTS.
- Ngày quay, phòng quay, ai đóng vai nào.
- Điện thoại nào chạy sản phẩm: buổi thử quyết định.
