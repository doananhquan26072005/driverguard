# Kịch bản video demo DriverGuard

Video quay màn hình, dài khoảng 4 phút 45 giây (giới hạn 5 phút của `presentation/README.md`). Gồm 5 phần: mở đầu
và giới thiệu team, demo use case chính, kiến trúc, edge case, kết.

| Phần | Thời gian | Nội dung |
|---|---|---|
| 1 | 0:00–0:35 | Team và vấn đề |
| 2 | 0:35–2:20 | Use case chính: một chuyến đi, từ tài xế tới quản lý |
| 3 | 2:20–3:10 | Kiến trúc: hình tổng quan năm phần, rồi 14 khối trong agent |
| 4 | 3:10–4:20 | Edge case: chống báo sai và trung thực khi không giám sát được |
| 5 | 4:20–4:45 | Số liệu, giới hạn, bước tiếp theo |

Quay từng phần riêng rồi ghép. Lời thoại thu sau, đọc đè lên hình, để lúc quay chỉ cần tập trung thao tác.

**Đã quay ngày 09/10/2026:** 21 clip chưa lồng tiếng, mỗi dòng của kịch bản một clip và một cảnh thêm, nằm ở
`presentation/demo-clips/` (chưa đưa vào git). Bảng lồng tiếng kèm mốc giây của từng clip:
[LOI-THOAI.md](../presentation/demo-clips/LOI-THOAI.md). Ghép nguyên là 299,9 giây (vừa chạm 5 phút, phải cắt bớt khi dựng). Khác kế hoạch dưới đây ở ba chỗ:
phần 2 đổi thứ tự ba cảnh báo (đã sửa trong bảng phần 2), phần 3 dài 64 giây thay vì 50 để đọc kịp lời, và cảnh
DevTools ở phần 3 thay bằng thẻ in lại request thật.

## Chuẩn bị trước khi quay

**Bản để quay.** Chạy local nhánh `DAQuan` (4 terminal theo [HowToUse.md mục 7.3](../HowToUse.md#73-toàn-bộ-hệ-thống-4-terminal),
thêm `npm run prepare-live` một lần). Bản này có các sửa lỗi M71–M101 mà bản v3 trên Railway chưa có. Nếu local
trục trặc thì quay trên https://driveguard-production-5093.up.railway.app, mọi cảnh trong kịch bản đều có ở v3.

**Tài khoản.** Một tài khoản tài xế (vd. `an`) và một tài khoản quản lý (vd. `boss`). Mở hai cửa sổ trình duyệt
khác profile (hoặc một cửa sổ ẩn danh) để hai phiên đăng nhập không đè nhau.

**Bố cục màn hình.**

- Cửa sổ A: `#/live`, đăng nhập tài xế. Để ô tự xem (hình camera nhỏ) ở góc để người xem thấy bạn đang làm gì.
- Cửa sổ B: `#/drive?code=…` mở từ nút "Điều khiển xe · mã XXXXXX", đặt cạnh cửa sổ A.
- Cửa sổ C (profile khác): `#/dashboard`, đăng nhập quản lý.
- Một tab mở hình tổng quan [architecture.png](diagrams/png/architecture.png) (xem ở 100 % để chữ đọc được khi
  phóng to), một tab mở sơ đồ 14 khối trong [README](../README.md#kiến-trúc), và hình
  [06-thoi-gian-tung-khoi.png](pitch-deck-charts/06-thoi-gian-tung-khoi.png).

**Điều kiện quay.**

- Mặt đủ sáng, đèn chiếu từ phía trước. Mặt tối thì tỉ lệ bắt nhắm mắt giảm mạnh (40 % so với 93 %).
- Không đeo kính râm. Ngồi chính diện camera, cả khuôn mặt trong khung.
- Bật thu âm thanh hệ thống: còi và giọng đọc cảnh báo là một phần của demo.
- Chạm vào trang `#/live` một lần ngay sau khi mở để trình duyệt cho phát tiếng.

**Động tác nên và không nên dùng.**

| Động tác | Dùng? | Vì sao |
|---|---|---|
| Nhắm chặt mắt 2,5–3 s | Có | Cần nhắm sâu; nhắm hờ hoặc nheo mắt không tính |
| Đưa điện thoại lên tai, giữ 3–4 s | Có | Gọi điện: 9 / 9 lần có cảnh báo, sau khoảng 2,4 s |
| Quay đầu sang bên, giữ 4 s | Có | 8 / 8 lần, cảnh báo sau khoảng 3 s |
| Cầm điện thoại nhắn tin trước ngực | Không | Chỉ 6 / 11 lần có cảnh báo |
| Liếc mắt xuống, đầu giữ thẳng | Không | Hệ thống chưa bắt được (0 / 13) |

Diễn tập cả kịch bản ít nhất hai lượt trước khi bấm quay.

## Phần 1. Team và vấn đề (0:00–0:35)

| Thời gian | Màn hình | Lời thoại |
|---|---|---|
| 0:00–0:12 | Slide tiêu đề: tên DriverGuard, tên và ảnh 4 thành viên, "AI20K Build Phase Cohort 4, VinUni" | "Xin chào, chúng tôi là team DriverGuard, khoá AI20K Cohort 4 tại VinUni, gồm bốn thành viên: [tên 1], [tên 2], [tên 3], [tên 4]." |
| 0:12–0:35 | Slide vấn đề, ba dòng: báo sai nhiều, im lặng khi không quan sát được, gửi video khuôn mặt lên cloud | "Tài xế buồn ngủ hoặc nhìn điện thoại vài giây là đủ gây tai nạn. Các hệ thống cảnh báo hiện có thường báo sai nhiều nên tài xế tắt đi, và nhiều giải pháp gửi video khuôn mặt lên cloud. DriverGuard giám sát tài xế ngay trên thiết bị: không ảnh nào rời khỏi máy, chỉ gửi số liệu." |

## Phần 2. Use case chính: một chuyến đi (0:35–2:20)

| Thời gian | Thao tác | Màn hình phải thấy | Lời thoại |
|---|---|---|---|
| 0:35–0:55 | Cửa sổ A. Xe đang 0 km/h. Bấm "Đồng ý, bắt đầu", làm 3 bước: nhìn camera, nhìn ra đường, nhắm mắt. Tua nhanh đoạn này khi dựng | Màn hình xin đồng ý, rồi 3 bước làm quen, rồi "Làm quen xong" | "Đây là bản chạy trong trình duyệt, cùng một logic với bản trên thiết bị. Xe đang đỗ, hệ thống xin đồng ý rồi đăng ký khuôn mặt khoảng mười giây để lấy mốc riêng của từng tài xế. Ảnh không bị lưu hay gửi đi." |
| 0:55–1:05 | Cửa sổ B: bấm "Chạy đều 50". Nhìn thẳng | Tốc độ lên 50 km/h, khiên xanh "Tỉnh táo", L0 | "Tôi cho xe chạy năm mươi cây số một giờ. Màn hình xanh: tỉnh táo." |
| 1:05–1:17 | Đưa điện thoại lên tai, giữ 4 s, bỏ xuống | Khối trạng thái cam, L2, "Bỏ điện thoại xuống" | "Đưa điện thoại lên tai: mức hai, kèm câu nhắc hành động." |
| 1:17–1:30 | Quay đầu sang phải, giữ 4 s, quay lại. Chạm nút "Cảnh báo nhầm?" | L2 "Nhìn đường!"; sau khi chạm hiện "Đã ghi nhận cảnh báo nhầm" | "Nhìn khỏi đường hơn hai giây: mức hai. Nếu cảnh báo sai, tài xế chạm nút này, phản hồi được gửi cho kỹ sư để chỉnh ngưỡng." |
| 1:30–1:45 | Nhắm chặt mắt 3 s, rồi mở | Đỏ toàn màn hình, "Mở mắt! Dừng xe nghỉ ngay", còi lặp, số giây mắt nhắm; mở mắt thì hết đỏ, còn mức L1 "Hãy tìm chỗ dừng nghỉ" tới khi xe dừng | "Nhắm mắt quá một giây rưỡi: mức ba. Đỏ toàn màn hình, còi lặp cho tới khi mở mắt." |
| 1:45–1:57 | Cửa sổ B: "Dừng xe". Cửa sổ A: "Kết thúc ca lái", xác nhận | Bảng tổng kết ca lái: đánh giá, biểu đồ từng phút | "Hết chuyến, tài xế xem bản tổng kết của mình." |
| 1:57–2:20 | Cửa sổ C (quản lý). Lần lượt: "Đội xe", "Báo cáo ca lái" (mở chuyến vừa xong), "Nhật ký sự kiện" (dòng tài xế báo sai), "Ngưỡng (chỉ xem)" | Xe vừa chạy trong danh sách; ba cảnh báo L2 / L2 / L3 vừa tạo; dòng có nhãn báo sai | "Phía quản lý chỉ nhận số liệu, không có hình. Tab Đội xe cho biết xe nào đang hoạt động, xe nào mất liên lạc. Báo cáo chuyến và nhật ký sự kiện có cả lần tài xế báo sai. Kỹ sư chỉnh ngưỡng theo phiên bản, áp thử vài xe rồi mới áp cho cả đội." |

Nhắm mắt (L3) quay sau cùng trong ba cảnh báo. Quay trước thì sau một lần nhắm mắt 4 giây màn hình không về xanh:
điểm buồn ngủ = 25 (vừa có microsleep) + phần PERCLOS vượt ngưỡng L1 (40), nên mức L1 "Hãy tìm chỗ dừng nghỉ"
giữ khoảng 40 giây và nằm đè lên hai cảnh điện thoại, nhìn lệch (đo ở lượt quay đầu ngày 09/10).

## Phần 3. Kiến trúc (2:20–3:10)

| Thời gian | Màn hình | Lời thoại |
|---|---|---|
| 2:20–2:36 | Hình tổng quan `architecture.png`, cả hình. Rê chuột lần lượt qua năm khung: Frontend, Agent, Backend API, SQLite, External; dừng ở ô vàng "Không có trong hệ thống" | "Hệ thống có năm phần. Agent chạy trên thiết bị trong xe. Frontend React có bốn trang: màn hình trong xe, bản chạy trong trình duyệt vừa demo, trang điều khiển xe và dashboard. Backend FastAPI lưu vào SQLite. Bên ngoài chỉ có ba nguồn model pretrained, tải một lần lúc cài đặt. Không có LLM: agent ở đây là pipeline thị giác cộng luật." |
| 2:36–2:50 | Phóng to khung Agent, ô "Nhận diện · khối 1–6" (hoặc chuyển sang sơ đồ 14 khối trong README, nửa trái). Chỉ vào mũi tên nét đứt từ khối 6 sang khối 5 | "Bên trong agent là mười bốn khối. Ảnh chỉ đi qua sáu khối đầu và chỉ nằm trong RAM. MediaPipe lấy landmark khuôn mặt, YOLOv8n tìm điện thoại trên luồng riêng, khối sáu tính độ mở mắt, độ mở miệng, góc đầu. CNN mắt chạy sau khối sáu, và chỉ khi chỉ số EAR không tin được." |
| 2:50–2:59 | Hai ô "Phân tích · khối 7–8" và "Quyết định · khối 9–12" | "Từ khối bảy chỉ còn con số. Hai nhánh buồn ngủ và mất tập trung tính điểm theo thời gian. Risk engine thêm tốc độ, xi nhan và trí nhớ chuyến đi để ra mức L0 đến L3, rồi alert manager lọc bằng thời gian xác nhận và cooldown." |
| 2:59–3:05 | Chỉ vào hai mũi tên đậm sang Backend, rồi mũi tên nét đứt "ngưỡng đã chỉnh". Cắt sang DevTools, tab Network của cửa sổ A: mở một request `web/events`, cho thấy payload JSON | "Rời thiết bị chỉ có JSON metadata; backend từ chối mọi thứ giống ảnh. Chiều ngược lại, agent lấy ngưỡng đã chỉnh về mỗi năm phút và chỉ áp khi xe đang nghỉ." |
| 3:05–3:10 | Hình `06-thoi-gian-tung-khoi.png` | "Cả vòng lặp mất khoảng bảy mili giây mỗi frame trên máy dev, và giữ ba mươi FPS ngay trong trình duyệt." |

Phần này dày lời nhất video. Nếu đọc không kịp 50 giây, bỏ câu về ngưỡng ở 2:59–3:05 trước, rồi tới danh sách bốn
trang frontend ở 2:20–2:36.

## Phần 4. Edge case (3:10–4:20)

Bắt đầu một chuyến mới ở cửa sổ A (đã đăng ký), xe chạy 50 km/h.

| Thời gian | Thao tác | Màn hình phải thấy | Lời thoại |
|---|---|---|---|
| 3:10–3:25 | Cửa sổ B: "Dừng xe", chờ về 0. Nhắm mắt 3 s, rồi cầm điện thoại lên tai 3 s | "Xe đang đỗ · 0 km/h", vẫn L0, không tiếng | "Edge case đầu tiên: xe dừng đèn đỏ. Nhắm mắt hay cầm điện thoại đều không bị báo, vì báo lúc này chỉ làm phiền." |
| 3:25–3:42 | "Chạy đều 50". Bật xi nhan "Trái", quay đầu sang trái vừa phải (như nhìn gương) 3 s: không báo. Bấm "Tắt", chờ 3 s, lặp lại đúng động tác | Lần một L0; lần hai L2 "Nhìn đường!" | "Đang chạy, bật xi nhan trái rồi nhìn gương trái: không báo. Tắt xi nhan, cùng động tác đó: mức hai. Ngữ cảnh xe quyết định, không chỉ khuôn mặt." |
| 3:42–3:52 | Lấy tay che kín camera 5 s, bỏ tay | Thẻ xanh dương "Tạm ngưng theo dõi", camera bị che, có âm báo; bỏ tay thì "Đã theo dõi lại" | "Che camera: hệ thống không đoán mò mà nói rõ là đang tạm ngưng giám sát, kèm lý do." |
| 3:52–4:08 | Nghiêng người ra khỏi khung hình khoảng 10 s, rồi quay lại và chạm màn hình | "Tạm ngưng theo dõi" sau 3 s, rồi cả màn hình hỏi "Bạn vẫn ổn chứ?" | "Tài xế rời khỏi khung hình khi xe đang chạy: sau vài giây màn hình hỏi 'Bạn còn ở đó không'. Không trả lời thì quản lý được báo." |
| 4:08–4:20 | Đóng cửa sổ B khi xe đang 50 km/h | Dải "Mất tín hiệu tốc độ xe: vẫn theo dõi như đang chạy", tốc độ hiện "–" | "Mất tín hiệu tốc độ: hệ thống chọn phía an toàn, vẫn giám sát như xe đang chạy. Khi không quan sát được, DriverGuard luôn nói ra." |

Nếu dài quá 5 phút, bỏ cảnh 4:08–4:20 trước, rồi tới cảnh che camera.

Cảnh thêm ngoài bảng (clip `4-6`, 14 giây, đặt sau cảnh mất tín hiệu xe): tám trạng thái khác của HUD lấy từ trang
xem trước `#/hud-preview` (L1 nhắc nghỉ, L3 không phản ứng, không trả lời, mặt quá tối, bị chói, mất camera, lỗi xử
lý, mất kết nối). Đây là trạng thái chọn bằng tay, không phải camera phát hiện: lời thoại không được nói khác đi.
Nếu dài quá 5 phút thì bỏ cảnh này trước mọi cảnh trong bảng.

Lưu ý khi quay cảnh xi nhan: xi nhan chỉ nới thêm 30° về phía đang bật, nên quay đầu vừa phải, đừng quay hẳn 90°.
Sau khi tắt xi nhan còn 2 s nới, phải chờ qua khoảng đó mới làm lại động tác. Khi quay ngày 09/10 cảnh này phải
làm ba lượt: cả hai lần quay đầu cần nằm trong khoảng 38–56° so với lúc nhìn thẳng (xem số Yaw ở "Chi tiết kỹ
thuật" của ô tự xem), và lần đầu phải giữ ít nhất 3 giây, lâu hơn 2,5 giây mà hệ thống cần để báo khi không có xi
nhan; quay 30° thì sát ngưỡng và không chứng minh được gì.

## Phần 5. Kết (4:20–4:45)

| Thời gian | Màn hình | Lời thoại |
|---|---|---|
| 4:20–4:45 | Slide ba số (0 ảnh rời thiết bị; 30 FPS trong trình duyệt; 97,6 % cảnh báo L3 đúng trên FL3D), bên dưới là dòng giới hạn và Live URL | "Tóm lại: không ảnh nào rời thiết bị, ba mươi FPS ngay trong trình duyệt, và chín mươi bảy phẩy sáu phần trăm cảnh báo mức ba là đúng trên bộ video lái đêm FL3D. Báo sai hiện khoảng một phẩy hai lần mỗi giờ trên dữ liệu công khai, chưa đạt mục tiêu một lần, và hệ thống chưa chạy trên xe thật: đó là bước tiếp theo. Cảm ơn các bạn đã xem." |

## Những câu không được nói trong video

Theo ba luật trong [pitch-deck-so-lieu.md](pitch-deck-so-lieu.md):

- Không nói "đạt ≤ 1,0 báo sai mỗi giờ". Số báo sai luôn kèm phạm vi: dữ liệu công khai, người ngồi trước laptop.
- Không nói đã pilot với tài xế, đã chạy trên xe hay thiết bị thật, hay giảm được tai nạn.
- Số 30 FPS là trong trình duyệt trên máy dev; số trên thiết bị gắn xe là "chưa đo".
- 97,6 % là trên FL3D, video lái đêm do người diễn, không phải buồn ngủ tự nhiên.

Thêm cho phần kiến trúc:

- Không gọi hệ thống là "AI agent dùng LLM" hay nhắc LangGraph, RAG, Vector Store: hệ thống không có các thứ này.
- Không nói "CNN mắt chạy trước khối 6" hay "ba model chạy song song": CNN mắt chạy sau khối 6 và chỉ khi EAR không tin được.
- Không nói "từ khối 6 trở đi chỉ còn con số": khối 5 (chạy sau khối 6) vẫn cắt vùng mắt từ frame. Ranh giới là khối 7.
