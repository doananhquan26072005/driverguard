# Kịch bản và tư liệu dựng video demo 3 phút

Bản rút gọn của [kich-ban-demo.md](kich-ban-demo.md) (5 phút), dựng từ các clip đã quay, không quay lại khuôn mặt.
Thông điệp: **báo đúng lúc, im đúng lúc, và không ảnh nào rời thiết bị.**

Bản quay người thật trong phòng, cùng thời lượng: [kich-ban-video-san-pham.md](kich-ban-video-san-pham.md).

Tư liệu nằm ở `presentation/demo-clips/3-phut/` (chưa đưa vào git, như cả thư mục `demo-clips/`):

| File | Dùng để |
|---|---|
| `01-mo-dau.mp4` … `21-ket.mp4` | 21 đoạn đã cắt sẵn, mỗi đoạn một dòng của bảng dưới. Kéo vào phần mềm dựng theo thứ tự số |
| `xem-truoc-3-phut.mp4` | 21 đoạn nối liền, 180,0 giây, chưa có lời và nhạc: xem để nắm nhịp |
| `xem-truoc-3-phut.srt` | Lời thoại canh theo bản xem trước, dùng làm mốc khi thu và khi đặt giọng |
| `nguon/png/overlay-mo-dau-0.png` | Dải chữ nền trong suốt cho đoạn 01, đặt ở track trên, che dòng chú thích cũ ở đáy hình |
| `nguon/slides.html`, `nguon/cat.json` | Nguồn của slide mới và bảng cắt: sửa chữ hay mốc giây ở đây rồi dựng lại (mục cuối) |
| `xem-truoc-3-phut-motion.mp4` | Bản dựng bằng HyperFrames: slide có chuyển động, hình có zoom, vòng khoanh và dải chú thích, có chuyển cảnh giữa các chương |
| `dung-hf/` | Project HyperFrames của bản có chuyển động: `index.html` chứa cả 180 giây (mục cuối) |

## Bản hiện tại (13/10, sau góp ý): thứ tự và ba câu cần thu

Bản có chuyển động `demo-3-phut-co-loi.mp4` (171,4 giây) không còn theo đúng bảng dựng bên dưới. Thứ tự mới:

| Giây | Nội dung | Giọng |
|---|---|---|
| 0:00 | Mở đầu | không lời |
| 0:15 | Slide số liệu, rồi dòng viền đỏ "Sau mỗi con số là một người không về nhà." ở 0:28 | `02`, rồi **`02b` chưa thu** |
| 0:33 | DriverGuard và team | `03b` (nửa sau của `03`), `04` |
| 0:44 | Demo, đoạn 05–11 | `05`–`11` |
| 1:30 | Edge case, đoạn 17–20 | `17`–`20` |
| 2:02 | Kiến trúc: khối 1–6, khối 7–13 | `13b`, `14b` (đã cắt "Một: …", "Hai: …") |
| 2:18 | Quyền riêng tư của tài xế: ảnh khuôn mặt không rời thiết bị | **`15` chưa thu** |
| 2:28 | Tốc độ ≈ 7 ms | `16` |
| 2:32 | Kết: ba con số, giới hạn, khẩu hiệu, mã QR | `21a` (bỏ câu khẩu hiệu cũ), rồi **`22` chưa thu** |

Từ 13/10 mỗi mục 01–04 có thêm một thẻ chương 1,5 giây đứng trước (ở 0:15, 0:47, 1:35, 2:08), nên các mốc trong bảng
trên lùi dần 1,5 đến 6 giây và video dài 177,4 giây. Thời lượng thẻ là hằng `D` trong lời gọi dựng thẻ ở `index.html`.

Đã bỏ: slide ba vấn đề (03), slide "Ba phần, ba nguyên tắc" (12), câu `12`, câu `15` cũ.

Mười hai câu dưới đây đã thu lại ngày 13/10 (`3-phut/ghi am/ghi am moi`) và đã ghép vào video: 171,4 giây. Bản giọng
cũ của chúng nằm ở `dung-hf/assets/audio/giong-cu/`. Mỗi câu một file, cân về −17 LUFS như các câu cũ. Các câu 06, 07, 09, 10, 14, 18, 19
giữ bản cũ. Đọc "mức hai", "mức ba", không đọc "L2", "L3".

| Câu | Lời |
|---|---|
| 02 | "Gần bảy nghìn hai trăm người Việt Nam thiệt mạng vì tai nạn giao thông, chỉ trong chín tháng đầu năm nay. Ở Mỹ năm 2023, hơn ba nghìn hai trăm người chết trong các vụ có tài xế mất tập trung, và ước tính hơn sáu nghìn ba trăm vì buồn ngủ. Sau mỗi con số là một người không về nhà." |
| 03 | "Vì vậy chúng tôi làm DriverGuard: camera trong xe nhận ra lúc tài xế buồn ngủ hoặc mất tập trung, và nhắc ngay. Mọi xử lý nằm trên thiết bị, không ảnh nào rời đi." |
| 04 | "Chúng tôi là Quân, Dũng, Huy và Khuê, khoá AI20K Cohort 4 tại VinUni. Đây là cách DriverGuard hoạt động." |
| 05 | "Xe đang đỗ. DriverGuard xin phép tài xế, rồi làm quen khuôn mặt trong mười giây, vì mắt mỗi người mỗi khác." |
| 08 | "Nhìn khỏi đường quá hai giây: mức hai. Thấy cảnh báo nhầm, tài xế chạm một nút, phản hồi đi thẳng tới kỹ sư." |
| 11 | "Quản lý chỉ nhận số liệu, không có hình: báo cáo ca lái, nhật ký sự kiện, và cả những lần tài xế báo cảnh báo nhầm." |
| 13 | "Bên trong có mười bốn khối. Sáu khối đầu đọc hình từ camera: MediaPipe tìm các điểm mốc trên khuôn mặt, YOLOv8n tìm điện thoại." |
| 15 | "Về quyền riêng tư: ảnh khuôn mặt không rời thiết bị. Chỉ số liệu không chứa ảnh được gửi lên cloud, để quản lý theo dõi và kỹ sư cải thiện DriverGuard." |
| 16 | "Mỗi khung hình xử lý mất khoảng bảy mili giây trên laptop, dư cho ba mươi khung hình mỗi giây." |
| 17 | "Xe đang dừng: nhắm mắt hay cầm điện thoại đều không báo, vì báo lúc này chỉ làm phiền." |
| 20 | "Camera không còn thấy tài xế: màn hình hỏi 'Bạn vẫn ổn chứ?'." |
| 21 | "Không ảnh nào rời thiết bị. Chín mươi bảy phẩy sáu phần trăm cảnh báo mức ba là đúng trên video lái xe ban đêm. Báo nhầm còn khoảng một phẩy hai lần mỗi giờ trên dữ liệu công khai, và chưa chạy trên xe thật. DriverGuard: nhắc đúng lúc, để bạn về nhà an toàn." |

Chữ trên màn hình đã sửa theo lời mới (13/10): dòng viền đỏ là "Sau mỗi con số là một người không về nhà.", slide
thứ ba của chương kiến trúc là "Quyền riêng tư của tài xế · Ảnh khuôn mặt không rời thiết bị.". Slide này không ghi
"cá nhân hoá trải nghiệm": mốc riêng của từng tài xế nằm trên thiết bị, số liệu trên cloud hiện chỉ phục vụ quản lý
theo dõi và kỹ sư chỉnh ngưỡng. Khẩu hiệu mới thay "báo đúng lúc, im đúng lúc" mới chỉ đổi trong video; README, pitch
và dòng "Thông điệp" ở đầu tệp này vẫn dùng câu cũ.

## Bảng dựng

Cột "Nguồn" ghi giây lấy từ clip gốc trong `presentation/demo-clips/`. Lời thoại khoảng 500 âm tiết, đọc hết chừng
110 giây ở 4–5 âm tiết mỗi giây; phần còn lại để còi và giọng nhắc của sản phẩm tự chạy.

| Đoạn | Bắt đầu | Dài | Nguồn | Lời thoại |
|---|---|---|---|---|
| `01-mo-dau` | 0:00 | 8 s | `2-5` giây 1,5–9,5 | (để còi 3 giây) "Ở năm mươi cây số một giờ, nhắm mắt một giây rưỡi là xe đi hai mươi mét không ai nhìn đường." |
| `02-van-de-so-lieu` | 0:08 | 12 s | slide mới, ba số hiện ở giây 1, 4,6 và 8,2 | "Gần bảy nghìn hai trăm người Việt Nam thiệt mạng vì tai nạn giao thông, chỉ trong chín tháng đầu năm nay. Ở Mỹ năm 2023, hơn ba nghìn hai trăm người chết trong các vụ có tài xế mất tập trung, và ước tính hơn sáu nghìn ba trăm vì buồn ngủ." |
| `03-van-de-giai-phap` | 0:20 | 11 s | `1-2` giây 0–5 và 10,5–16,5 | "Hệ thống cảnh báo hay báo sai nên tài xế tắt đi, nhiều giải pháp lại gửi video khuôn mặt lên cloud. Vì vậy chúng tôi làm DriverGuard: xử lý ngay trên thiết bị, không ảnh nào rời khỏi máy." |
| `04-team` | 0:31 | 8 s | `1-1` giây 0–8 | "Chúng tôi là Quân, Dũng, Huy và Khuê, khoá AI20K Cohort 4 tại VinUni. Đây là cách nó hoạt động." |
| `05-lam-quen-khuon-mat` | 0:39 | 6 s | `2-1` giây 2–14, tua 2×, tắt tiếng | "Xe đang đỗ. Hệ thống xin đồng ý, rồi làm quen khuôn mặt mười giây để lấy mốc riêng cho từng tài xế." |
| `06-chay-50` | 0:45 | 5 s | `2-2` giây 4,8–9,8 | "Xe chạy năm mươi cây số một giờ. Màn hình xanh: tỉnh táo." |
| `07-dien-thoai-L2` | 0:50 | 7 s | `2-3` giây 1,5–8,5 | "Đưa điện thoại lên tai: mức hai." Rồi im, để giọng nhắc của sản phẩm tự nói |
| `08-nhin-lech-bao-sai` | 0:57 | 10 s | `2-4` giây 1–11 | "Nhìn khỏi đường quá hai giây: mức hai. Thấy báo sai, tài xế chạm một nút, phản hồi đi thẳng tới kỹ sư." |
| `09-nham-mat-L3` | 1:07 | 9 s | `2-5` giây 1–10 | "Nhắm mắt quá một giây rưỡi: mức ba. Đỏ toàn màn hình, còi kêu tới khi mở mắt." |
| `10-tong-ket-ca-lai` | 1:16 | 4 s | `2-6` giây 6,5–10,5 | "Hết ca, tài xế xem tổng kết." |
| `11-dashboard` | 1:20 | 5 s | `2-7` giây 6,5–9 và 12,5–15 | "Quản lý chỉ nhận số liệu, không có hình: báo cáo ca lái, nhật ký sự kiện, và cả lần tài xế báo sai." |
| `12-kien-truc-tong-quan` | 1:25 | 7 s | slide mới, khung sáng: Agent 0,6 · Frontend 2,2 · Backend 3,7 · "Không có LLM" 5,2 | "Hệ thống gồm agent trên thiết bị, frontend và backend. Không có LLM: đây là pipeline thị giác cộng luật." |
| `13-nguyen-tac-1-anh-o-lai` | 1:32 | 13 s | slide mới: khối 1–2 giây 1,5 · khối 3–4 giây 3,5 · khối 6 giây 6,5 · khối 5 giây 9 · dải "chỉ nằm trong RAM" giây 11 | "Một: ảnh ở lại trong xe. Ảnh chỉ đi qua sáu khối đầu trong mười bốn khối, và chỉ nằm trong RAM. MediaPipe lấy landmark, YOLOv8n tìm điện thoại." |
| `14-nguyen-tac-2-con-so` | 1:45 | 10 s | slide mới: khối 7–8 giây 1 · khối 9–11 giây 3,5 · L0–L3 giây 6 · khối 12–13 giây 8 | "Hai: quyết định bằng con số. Từ khối bảy, risk engine gộp điểm buồn ngủ, mất tập trung với tốc độ và xi nhan, ra mức L0 đến L3." |
| `15-nguyen-tac-3-chi-json` | 1:55 | 6 s | slide mới, thẻ JSON hiện ở giây 2 | "Ba: chỉ JSON rời thiết bị." |
| `16-thoi-gian-tung-khoi` | 2:01 | 3 s | slide mới | "Cả vòng lặp mất khoảng bảy mili giây mỗi frame trên máy dev." |
| `17-xe-do-khong-bao` | 2:04 | 9 s | `4-1` giây 5,5–14,5 | "Xe dừng đèn đỏ: nhắm mắt hay cầm điện thoại đều không báo, vì báo lúc này chỉ làm phiền." |
| `18-xi-nhan-nhin-guong` | 2:13 | 14 s | `4-2` giây 2,5–12,5 tua 1,25× tắt tiếng, rồi giây 14,5–20,5 | "Bật xi nhan trái rồi nhìn gương: không báo. Tắt xi nhan, cùng động tác đó: mức hai." |
| `19-che-camera` | 2:27 | 9 s | `4-3` giây 1–10 | "Che camera: hệ thống nói rõ đang tạm ngưng theo dõi, không đoán mò." |
| `20-roi-khung-hinh` | 2:36 | 8 s | `4-4` giây 0,5–2,5 và 9,05–15,05 | "Tài xế rời khung hình: màn hình hỏi 'Bạn vẫn ổn chứ?'. Không trả lời thì báo quản lý." |
| `21-ket` | 2:44 | 16 s | slide mới: ba số ở giây 0,5 · 1,7 · 3 · ô giới hạn giây 6 · khẩu hiệu và địa chỉ bản chạy thử giây 12 | "Không ảnh nào rời thiết bị. Chín mươi bảy phẩy sáu phần trăm cảnh báo mức ba là đúng trên bộ FL3D. Báo sai còn khoảng một phẩy hai lần mỗi giờ trên dữ liệu công khai, và chưa chạy trên xe thật. DriverGuard: báo đúng lúc, im đúng lúc." |

Bỏ so với bản 5 phút: các clip `2-8`, `2-9`, `4-5`, `4-6`, `3-1` … `3-5` (thay bằng năm slide nền tối), `5-1` (thay
bằng slide kết mới, địa chỉ bản chạy thử là `c4-app-135.up.railway.app`), tab Đội xe và tab Ngưỡng của `2-7`, câu
"agent lấy ngưỡng đã chỉnh về mỗi năm phút".

Hai đoạn 19 và 20 cắt theo tiếng: mỗi đoạn bắt đầu và kết thúc ở chỗ im, không cắt ngang câu nhắc của sản phẩm. Vì
vậy đoạn 20 nhảy thẳng từ lúc rời khung hình sang màn hình "Bạn vẫn ổn chứ?", bỏ quãng "Tạm ngưng theo dõi".

## Các bước dựng còn lại

1. Đọc to cả bảng, bấm giờ từng dòng. Dòng nào dài hơn đoạn hình của nó thì sửa lời, không kéo dài hình. Hai dòng
   sát giờ nhất là `02` và `21`.
2. Thu giọng trong phòng kín, mic cách miệng một gang tay, mỗi dòng một file đặt tên theo đoạn (`01.wav` … `21.wav`).
3. Kéo 21 đoạn vào timeline theo thứ tự, đặt giọng lên, canh theo `xem-truoc-3-phut.srt`.
4. Đặt ảnh overlay `overlay-mo-dau-0.png` lên suốt đoạn 01.
5. Nhạc nền không lời, nhỏ hơn giọng khoảng 18–20 dB; hạ thêm ở các đoạn sản phẩm phát tiếng (01, 07, 08, 09, 18,
   19, 20). Hai đoạn 05 và nửa đầu 18 đã tắt tiếng vì tua nhanh.
6. Không chồng file `.srt` lên hình khi xuất: các đoạn 05–10 và 17–20 đã có chú thích in sẵn ở đáy.
7. Xuất 1920 × 1080, 30 FPS, lưu thành `presentation/video_demo.mp4`. Cho một người ngoài team xem một lần rồi hỏi họ
   nhớ được gì.

## Số liệu trên slide vấn đề

| Số | Nội dung | Nguồn | Đã kiểm |
|---|---|---|---|
| 7 198 | Người chết vì tai nạn giao thông ở Việt Nam trong 9 tháng năm 2026 (11 564 vụ, 6 704 người bị thương), mọi nguyên nhân. Cùng số với slide 2 của pitch deck; từ 13/10 thay số 9 549 của 11 tháng năm 2025 | [VietnamPlus 02/10/2026, báo cáo của Cục CSGT](https://www.vietnamplus.vn/9-thang-nam-2026-toan-quoc-xay-ra-11564-vu-tai-nan-giao-thong-post1139589.vnp) | Mở bài 13/10. Bài không ghi ngày đầu và ngày cuối của kỳ |
| 3 200+ | Người chết ở Mỹ năm 2023 trong các vụ có tài xế mất tập trung: 3 275, tức 8 % số người chết | [NHTSA, Distracted Driving in 2023](https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813703) | Đọc qua kết quả tìm kiếm 12/10, **chưa mở văn bản gốc**. Bản 2024 của NHTSA sửa số này thành 3 283 |
| 6 300+ | Ước tính người chết ở Mỹ năm 2023 vì lái xe buồn ngủ: 6 326. Số từ biên bản cảnh sát là 633 | [GHSA, Wake Up Call 2026 Update](https://www.ghsa.org/sites/default/files/2026-02/Wake_Up_Call_2026_Update.pdf), trang 4–5 | Mở PDF gốc 12/10. GHSA lấy tỉ lệ 17,6 % vụ chết người có tài xế buồn ngủ (AAAFTS, 2017–2021) áp cho năm 2023 |
| ≈ 20 m | Quãng xe đi trong 1,5 giây ở 50 km/h: 13,9 m/s × 1,5 s = 20,8 m | Tự tính | — |

Chưa có số riêng về buồn ngủ hay mất tập trung cho Việt Nam: slide đã ghi rõ, lời thoại không được nối 7 198 với
buồn ngủ.

## Những câu không được nói

Giữ nguyên mục cuối của [kich-ban-demo.md](kich-ban-demo.md#những-câu-không-được-nói-trong-video). Thêm cho bản này:

- Không nói "đang quay trực tiếp": các đoạn 05–10 và 17–20 là phát lại hình khuôn mặt đã quay
  ([LOI-THOAI.md](../presentation/demo-clips/LOI-THOAI.md), ghi chú 14).
- Thẻ JSON ở đoạn 15 là request của chuyến demo ngày 09/10, rút gọn; đừng nói là của chuyến vừa xem.
- Đoạn 16: 7 mili giây là cả vòng lặp không tính YOLOv8n, vì YOLOv8n chạy trên luồng riêng 5 lần mỗi giây.

## Còn thiếu

- Slide team (đoạn 04) vẫn dùng chữ cái đầu thay ảnh thành viên.
- Dashboard (đoạn 11) vẫn là dữ liệu của một ca lái 47 giây.
- Hình khuôn mặt vẫn là bản đã nén hai lần của ngày 09/10.
- Chưa có giọng, nhạc; chưa ai ngoài team xem bản nháp.

## Dựng lại sau khi sửa

Chạy từ thư mục gốc của repo, trên macOS (dùng AVFoundation, không cần ffmpeg):

```bash
# 1. Sửa chữ trong nguon/slides.html rồi chụp lại các bước của slide
NODE_PATH=frontend/node_modules node presentation/demo-clips/3-phut/nguon/render.cjs

# 2. Sửa mốc giây hoặc lời thoại trong nguon/cat.json rồi cắt và ghép lại
swiftc -O presentation/demo-clips/3-phut/nguon/dung.swift -o /tmp/dung
/tmp/dung presentation/demo-clips
```

Bước 2 ghi đè 21 đoạn, bản xem trước và file `.srt`. Mỗi file xuất ra có một track hình và một track tiếng liền mạch
(không dùng edit list), để phần mềm dựng nào cũng phát tiếng đúng chỗ.

## Bản có chuyển động (HyperFrames)

`dung-hf/index.html` là cả bản 180 giây trong một file, cần Node 22+ và FFmpeg. Từ dưới lên có bốn lớp:

| Lớp | Nội dung |
|---|---|
| Hình | 12 đoạn là thẻ `<video>` trỏ tới `assets/clips/` (bản sao của các đoạn đã cắt ở trên). Năm đoạn 08, 11, 17, 18, 19 nằm trong khung `.cam` để zoom và đặt vòng khoanh |
| Dải chữ | Dải 108 px ở đáy, một dải cho mỗi chương: nhãn chương và chú thích của đoạn đang chạy. Nó che dòng chú thích in sẵn trong hình |
| Slide | Chín cảnh HTML (02, 03, 04, 12–16, 21) và nhãn bốn chương ở góc trên phải |
| Chuyển cảnh | Hai khối quét ngang ở năm chỗ đổi chương; trong một chương thì slide mới đẩy slide cũ |
| Hiệu ứng âm thanh | 36 thẻ `<audio id="sfx-NN">` ở slide, thẻ chương và chỗ chuyển chương; không có ở các đoạn sản phẩm phát tiếng |

Mọi chuyển động nằm trong một timeline GSAP ở cuối file, mốc tính bằng giây kể từ đầu đoạn: `at("v08", 6.5)`.

```bash
cd presentation/demo-clips/3-phut/dung-hf
npm run check                                                       # lint, layout, contrast
npx hyperframes preview --background                                # xem và chỉnh trong trình duyệt
npx hyperframes render -f 30 -o ../xem-truoc-3-phut-motion.mp4      # khoảng 2 phút
```

- Sửa chữ hoặc mốc giây của slide: sửa thẳng trong `index.html` (mốc là các lời gọi `at("s13", 3.5)`, tính bằng
  giây kể từ đầu cảnh). `slides.html` chỉ còn dùng cho bản tĩnh.
- Cắt lại một đoạn hình: chạy lại bước 2 ở mục trên rồi chép file đó vào `dung-hf/assets/clips/`.
- Giọng và nhạc đã ở trong `index.html` (các thẻ `<audio>` gần cuối), file nguồn ở `dung-hf/assets/audio/`, bản có
  lời xuất ra `demo-3-phut-co-loi.mp4`. Thu lại một câu: thay file `giong-NN.wav` (48 kHz, khoảng −16 LUFS), sửa
  `data-duration` và nếu nhịp đọc đổi thì dời các mốc `at(...)` của đoạn đó. Mức nhạc theo thời gian là dãy điểm
  `data-automation` của thẻ `nhac-nen`. Sau khi render, nâng 2 dB bằng
  `ffmpeg -i in.mp4 -c:v copy -af volume=2dB -c:a aac -b:a 192k out.mp4` để về khoảng −15 LUFS.
- Ba số trên slide vấn đề đếm lên trong 0,9 giây: dừng hình giữa lúc đếm sẽ thấy một số trung gian, đừng chụp
  khung hình ở quãng đó.
- Hiệu ứng âm thanh: file ở `dung-hf/assets/sfx/` (CC0, nguồn ở `NGUON.md`), giờ và mức của từng cue ở `cues.json`.
  `data-volume` đặt đỉnh của mỗi cue: wipe −16 dBFS, slide đẩy −19, con số và thẻ chương −22, tick và pop −24
  (trước bước nâng 2 dB). Dời mốc giây của một slide thì dời `data-start` của các cue trong slide đó theo.
- Sửa chú thích ở dải chữ: các thẻ `<div class="cap" id="cap08a">` trong `index.html`; giờ hiện và tắt là lời gọi
  `cap(...)` tương ứng.
- Zoom và vòng khoanh tính theo toạ độ pixel của hình hiện tại (`zoom("#cam08", ..., 1.33, 0, 250)` nghĩa là phóng
  1,33 lần, pixel (0, 250) của hình thành góc trên trái; vòng khoanh là thẻ `.ring` có `left/top/width/height`).
  Giữ y0 + 972 / scale dưới 985, nếu không dòng chú thích in sẵn trong hình sẽ lộ ra phía trên dải chữ.
  Quay lại hình thì đo lại các toạ độ và giây này, nhất là giây bấm nút "Cảnh báo nhầm?" (8,2 giây trong đoạn 08).
- Đoạn 05 gồm hai file: `05a-xin-dong-y.mp4` (màn xin đồng ý ở tốc độ thật, cắt bằng ffmpeg từ `2-1` giây
  1,45–3,05, không qua `dung.swift`) rồi `05-lam-quen-khuon-mat.mp4` từ giây 0,6 tới 5,0. Đừng kéo dài quá 5,4: sau
  đó màn "Tỉnh táo" hiện lại khi mắt còn nhắm.
- Chú giải L0–L3 ở góc phải dải chữ (`.lv-key`) chiếm từ pixel 1434 trở đi: chú thích dài hơn mốc đó (đoạn 05, 17)
  thì chú giải phải tắt trong lúc ấy.
- Ảnh thành viên: đặt thẻ `<img>` vào trong `.av` của cảnh 04 (112 × 112, bo tròn).
- Mã QR trên slide kết là SVG nhúng thẳng, tạo bằng `npx qrcode -t svg "https://c4-app-135.up.railway.app"`. Đổi
  địa chỉ thì tạo lại và thay khối `<svg>` trong `.qr`.
- Bản dựng lần đầu (chỉ bảy cảnh slide có chuyển động) giữ ở `xem-truoc-3-phut-motion-v1.mp4`.
