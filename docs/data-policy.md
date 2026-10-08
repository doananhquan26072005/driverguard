# Chính sách dữ liệu DriverGuard

Cập nhật: 05/10/2026 (M37). Áp dụng cho bản đang phát triển (Version 3) và bản web xem thử.

Tài liệu này nói rõ DriverGuard thu dữ liệu gì, ai xem được, giữ bao lâu và được dùng vào việc gì. Mọi
câu ở đây phải đúng với code; chỗ nào code chưa làm thì ghi là chưa làm. Đây không phải tư vấn pháp lý:
đơn vị triển khai trên xe thật phải tự rà soát với người có chuyên môn (mục 9).

## 1. Tóm tắt

- **Không có ảnh hay video khuôn mặt nào được lưu hoặc gửi đi.** Hình ảnh camera chỉ nằm trong bộ nhớ
  của thiết bị trên xe (hoặc của trình duyệt) trong lúc xử lý.
- Máy chủ chỉ nhận **số liệu**: cảnh báo, điểm buồn ngủ theo phút, bản tổng kết chuyến, trạng thái
  thiết bị. Không có vị trí xe.
- Số liệu cảnh báo tự xoá sau **60 ngày**; bản tổng kết chuyến tự xoá sau **365 ngày**.
- Tài xế xem được toàn bộ số liệu của chính mình và bấm được "Cảnh báo sai" trên từng cảnh báo.
- **Không kỷ luật tài xế chỉ dựa trên một cảnh báo đơn lẻ.** Cảnh báo có thể sai; hệ thống không tự
  ra quyết định nào về tài xế.

## 2. Dữ liệu được thu

Đúng theo cấu trúc máy chủ chấp nhận ([backend/schemas.py](../backend/schemas.py)); trường lạ bị từ
chối.

| Loại | Nội dung | Khi nào có |
|---|---|---|
| Cảnh báo | Thời điểm, chuyến, mức L1–L3, lý do, `drowsy_score`, `distraction_score`, tốc độ xe, các số đo lúc đó (PERCLOS, thời gian nhắm mắt, nhịp chớp, số lần ngáp / gục đầu, thời gian nhìn lệch, tỉ lệ thời gian liếc khỏi đường, tỉ lệ thấy điện thoại và đang gọi hay nhắn tin, …), đã đăng ký khuôn mặt hay chưa; tag "mô phỏng" khi tín hiệu xe là giả lập; phiên bản app, phiên bản bộ ngưỡng và mã rút gọn của các file model | Mỗi lần có cảnh báo |
| Sự kiện hệ thống | Mất / có lại camera, tạm ngưng giám sát, mất tín hiệu xe, lỗi xử lý, máy chậm, đổi tài xế, đăng ký xong (kèm thời gian đăng ký và số bước làm lại) | Khi trạng thái đổi |
| Phản hồi "Cảnh báo sai" | Cảnh báo nào, thời điểm bấm | Khi tài xế bấm |
| Mẫu theo phút | `drowsy_score` trung bình, PERCLOS, mức cao nhất, tỉ lệ thời gian liếc khỏi đường cao nhất của phút đó | Mỗi phút lái |
| Bản tổng kết chuyến | Thời lượng, số cảnh báo theo mức và lý do, số lần ngủ gật / ngáp / gục đầu, thời gian nhìn lệch và dùng điện thoại (gọi / nhắn tin), số lần liếc khỏi đường, thời gian quay hẳn đi, tỉ lệ thời gian giám sát được, điểm theo phút, đánh giá chuyến và gợi ý | Khi kết thúc chuyến |
| Trạng thái thiết bị | Lần cuối có tin, chuyến, trạng thái giám sát, xe đang chạy hay đỗ, phiên bản app / bộ ngưỡng / mã model, thời gian xử lý từng chặng của vòng lặp tính bằng mili giây (M49) | Mỗi 30 s (ghi đè, chỉ giữ bản mới nhất) |
| Nhật ký truy cập | Tài khoản và vai trò nào đã xem dữ liệu của tài xế / thiết bị nào (hoặc của cả đội), sửa ngưỡng, tạo tài khoản / thiết bị, xoá dữ liệu; thời điểm | Mỗi lượt (cùng một lượt xem ghi một lần mỗi 10 phút) |
| Tài khoản | Tên đăng nhập, vai trò, mã tài xế, mật khẩu đã băm | Do quản trị tạo |

Mọi bản ghi gắn với mã thiết bị và **mã tài xế** (ví dụ `drv-001`), nên đây là dữ liệu cá nhân của tài
xế. Nó mô tả mức buồn ngủ và hành vi khi làm việc, nên DriverGuard xử lý nó thận trọng như dữ liệu
nhạy cảm.

**Không thu, không lưu, không gửi:**
- Ảnh, video, ảnh cắt vùng mắt hay khuôn mặt. Thiết bị chặn trước khi đưa vào hàng đợi gửi; máy chủ
  kiểm tra lần nữa và từ chối mọi nội dung giống ảnh (tên trường, chuỗi base64, chữ ký file ảnh).
- Các con số học được lúc đăng ký khuôn mặt (độ mở mắt, miệng, tư thế đầu, chữ ký hình dạng mặt): chỉ
  nằm trong bộ nhớ của thiết bị trong chuyến đó, mất khi kết thúc chuyến.
- Vị trí, toạ độ, hành trình. Máy chủ chỉ nhận tốc độ tại lúc có cảnh báo.
- Âm thanh trong xe.
- Hệ thống không nhận dạng tài xế là ai: mã tài xế đến từ tài khoản đăng nhập hoặc từ thiết bị được
  gán, không phải từ khuôn mặt.

Chế độ không đăng nhập của `#/live`: không có gì rời trình duyệt.

## 3. Dùng vào việc gì

| Được dùng | Không được dùng |
|---|---|
| Cảnh báo tài xế ngay trong xe | Kỷ luật, trừ lương, xếp hạng tự động |
| Tài xế xem lại chuyến của mình | Kết luận về tài xế từ một cảnh báo đơn lẻ |
| Quản lý biết xe nào đang được giám sát, chuyến nào cần hỏi han | Theo dõi ngoài giờ lái (không có dữ liệu ngoài chuyến) |
| Kỹ sư tìm nguyên nhân báo sai và chỉnh ngưỡng | Chuyển cho bên thứ ba (bảo hiểm, đơn vị khác) |

**Vì sao không kỷ luật từ một cảnh báo đơn lẻ:**
- Cảnh báo có thể sai. Trên dữ liệu đã đo, số cảnh báo sai mỗi giờ còn cao và khoảng tin cậy rất rộng
  (ví dụ FL3D: L1 4,6 / giờ, CI 95 % 0,56–16,7, trên 26 phút nhãn tỉnh táo;
  [eval/results/report.md](../eval/results/report.md)). Chưa có giờ lái thật nào có nhãn.
- Hệ thống có những lúc không giám sát được (mất mặt, kính râm, mất camera;
  [safety-fmea.md](safety-fmea.md)); không có cảnh báo không có nghĩa là tài xế tỉnh táo.
- Tài xế có thể bấm "Cảnh báo sai". Phản hồi đó được lưu và hiện cạnh cảnh báo trên dashboard.
- Đánh giá chuyến ("Tốt" / "Cần chú ý" / "Có lúc rất nguy hiểm") chỉ mô tả, không phải điểm thi đua.
  Dashboard không xếp hạng tài xế.

Quy trình đề xuất cho quản lý: nhìn theo xu hướng nhiều chuyến, xem phản hồi của tài xế, nói chuyện
với tài xế trước khi kết luận. Dòng nhắc này hiện ở cuối mọi tab của dashboard.

## 4. Ai xem được gì

Phân quyền kiểm ở máy chủ ([backend/app.py](../backend/app.py)), không chỉ ẩn trên giao diện.

| Vai trò | Xem | Sửa |
|---|---|---|
| Tài xế | Cảnh báo, timeline, báo cáo chuyến, trạng thái xe **của chính mình** | Bấm "Cảnh báo sai" |
| Quản lý đội xe | Số liệu của mọi tài xế, tab "Đội xe", ngưỡng (chỉ đọc) | Đánh dấu báo cáo đã xem |
| Kỹ sư an toàn | Như quản lý | Chỉnh ngưỡng (lưu thành phiên bản, kèm tên người sửa) |
| Quản trị | Như kỹ sư, và toàn bộ nhật ký truy cập | Tạo tài khoản và thiết bị |

Thiết bị trên xe không phải người dùng: nó chỉ gửi lên và tải ngưỡng về bằng khoá thiết bị.

**Nhật ký truy cập (M41).** Mỗi lần quản lý, kỹ sư hay quản trị xem dữ liệu của một tài xế, một thiết bị
hoặc của cả đội xe, máy chủ ghi một dòng: ai, vai trò gì, xem gì, của ai, lúc nào. Sửa ngưỡng, tạo tài
khoản / thiết bị và xoá dữ liệu bằng lệnh quản trị cũng được ghi. Bảng này chỉ ghi thêm (database chặn
lệnh sửa), không có API nào sửa hay xoá từng dòng. Quản trị xem toàn bộ ở tab "Nhật ký truy cập"; tài xế
xem được ai đã xem dữ liệu của mình ở tab "Dữ liệu của tôi", mục "Ai đã xem dữ liệu của tôi" (gồm cả các lượt xem cả đội xe).
Tài xế xem dữ liệu của chính mình thì không ghi. Để nhật ký không đầy vì dashboard tự làm mới, cùng một
lượt xem của cùng một tài khoản chỉ ghi một lần trong mỗi 10 phút (`DG_AUDIT_DEDUPE_S`).

## 5. Giữ bao lâu

| Dữ liệu | Thời hạn | Cách xoá |
|---|---|---|
| Cảnh báo, sự kiện hệ thống, phản hồi "Cảnh báo sai", mẫu theo phút | **60 ngày** | Tự động: lúc máy chủ khởi động và mỗi ngày một lần |
| Bản tổng kết chuyến | **365 ngày** | Tự động, như trên |
| Trạng thái thiết bị | Chỉ bản mới nhất | Ghi đè mỗi lần có tin |
| Nhật ký truy cập | 365 ngày | Tự động, như trên (`DG_RETENTION_ACCESS_LOG_DAYS`; con số do nhóm chọn, chưa có ý kiến pháp lý) |
| Toàn bộ số liệu của một tài xế | Đến khi tài xế nghỉ việc hoặc yêu cầu xoá | Tài xế gửi yêu cầu ở tab "Dữ liệu của tôi", quản trị bấm "Xoá dữ liệu" ở tab "Nhật ký truy cập" (M48); hoặc lệnh `python -m backend.manage delete-driver-data <mã tài xế> --yes` |
| Hàng đợi chưa gửi trên thiết bị | Đến khi gửi được (tối đa 10 000 bản ghi) | Tự xoá sau khi máy chủ nhận |
| Hàng đợi chưa gửi trên web | Đến khi đóng trang | Chỉ nằm trong bộ nhớ trình duyệt |
| Tài khoản | Đến khi quản trị xoá | `python -m backend.manage delete-user <tên> --yes` (thêm `--with-data` để xoá luôn số liệu của tài xế đó), M48 |
| Phiên bản ngưỡng, yêu cầu xoá dữ liệu | Không tự xoá | Không chứa số liệu về việc lái xe; yêu cầu xoá ghi mã tài xế, người gửi, người xử lý |

Hai thời hạn nằm trong cấu hình máy chủ (`DG_RETENTION_EVENTS_DAYS`, `DG_RETENTION_SUMMARIES_DAYS`;
đặt 0 là không tự xoá). Màn hình đồng ý của tài xế ghi đúng hai con số mặc định này, nên đổi cấu hình
thì phải đổi cả câu chữ (`RETENTION_DAYS` trong `frontend/src/lib/labels.ts`; có test so hai nơi).

Thời hạn tính từ lúc máy chủ nhận được bản ghi, không theo giờ thiết bị ghi trong bản ghi (M82): thiết bị có
đồng hồ sai không làm số liệu bị xoá sớm hay được giữ quá hạn.

**Vì sao 60 ngày và 365 ngày:**
- Pháp luật Việt Nam không đặt con số cho loại dữ liệu này, chỉ yêu cầu lưu "trong khoảng thời gian phù
  hợp với mục đích xử lý" và xoá khi đã xong mục đích [L1, Điều 3, Điều 14].
- Mốc tham chiếu gần nhất tìm được là hướng dẫn của CNIL (Pháp) về định vị xe của người lao động: mặc
  định không quá **2 tháng**, tối đa **1 năm** khi cần để tối ưu hoặc làm bằng chứng [C1]. DriverGuard
  dùng đúng hai mốc này: số liệu chi tiết từng cảnh báo 60 ngày (đủ để kỹ sư tìm nguyên nhân báo sai và
  quản lý trao đổi với tài xế), bản tổng kết 365 ngày (để so các chuyến theo thời gian).
- Đây là lựa chọn của nhóm, chưa có ý kiến pháp lý và chưa thử với một đội xe thật.

## 6. Quyền của tài xế

| Quyền | DriverGuard đáp ứng thế nào |
|---|---|
| Được biết | Màn hình "Đăng ký khuôn mặt" nói rõ trước khi bắt đầu: không lưu ảnh, không gửi khuôn mặt, số liệu giữ bao lâu. Tài liệu này |
| Xem dữ liệu của mình | Đăng nhập dashboard bằng tài khoản tài xế: cảnh báo, timeline, báo cáo chuyến |
| Biết ai đã xem dữ liệu của mình | Tab "Dữ liệu của tôi", bảng "Ai đã xem dữ liệu của tôi" (nhật ký truy cập, mục 4) |
| Nhận bản sao dữ liệu của mình | Nút "Tải dữ liệu của tôi" (M48): một file JSON gồm mọi cảnh báo, sự kiện, mẫu theo phút, báo cáo chuyến, lượt người khác xem và các yêu cầu xoá của chính tài xế đó (`GET /api/v1/me/data`). Chỉ tài khoản tài xế gọi được, và chỉ ra dữ liệu của chính mình |
| Phản đối một cảnh báo | Nút "Cảnh báo sai" trên HUD trong 120 s sau cảnh báo |
| Yêu cầu xoá | Nút "Yêu cầu xoá dữ liệu" (M48). Quản trị thấy yêu cầu ở tab "Nhật ký truy cập" và chọn "Xoá dữ liệu" hoặc "Từ chối" kèm một lý do trong danh sách (phải giữ theo yêu cầu pháp lý, đang có sự cố cần xem xét, yêu cầu trùng, khác). Tài xế thấy kết quả và lý do; cả hai trường hợp đều vào nhật ký truy cập. Không phải nút tự xoá: đơn vị vận tải có thể có lý do phải giữ, nên một người chịu trách nhiệm quyết định |
| Không đăng ký khuôn mặt | Bấm "Để sau": vẫn được lái và vẫn được giám sát bằng mốc chung, kém chính xác hơn |

Màn hình đồng ý chỉ hỏi về việc **đăng ký khuôn mặt**. Việc giám sát khi lái là biện pháp của đơn vị
vận tải; theo [L1, Điều 25 khoản 3] đơn vị chỉ được áp dụng "trên cơ sở người lao động biết rõ biện pháp
đó". Việc thông báo và thoả thuận với tài xế là trách nhiệm của đơn vị triển khai, ứng dụng không làm
thay được.

## 7. Bảo mật

- Mật khẩu băm bằng scrypt; phiên đăng nhập là token có hạn (mặc định 60 phút), chỉ nằm trong
  `sessionStorage` của trình duyệt.
- Khoá thiết bị chỉ lưu dạng băm, hiện một lần lúc tạo.
- Bản deploy chạy qua HTTPS. HUD trên thiết bị chỉ nghe ở `127.0.0.1`, và từ M84 chỉ nhận lệnh từ trang HUD: yêu cầu mang `Host` hoặc `Origin` lạ bị từ chối.
- Log chỉ ghi số lượng và tên lớp lỗi, không ghi nội dung.
- Nhật ký truy cập chỉ ghi thêm (mục 4). Một test tĩnh trong CI quét mã nguồn của thiết bị, bản web, máy
  chủ và công cụ: không có lời gọi nào ghi, mã hoá hay quay lại ảnh camera.
- **Database khi lưu (M48):** file SQLite **không** được mã hoá ở mức ứng dụng. Quyết định: dựa vào mã hoá ổ
  đĩa / volume của nơi host, và đơn vị triển khai phải kiểm tra nơi host của mình có bật hay không (*chưa
  kiểm chứng* với volume của Railway). Lý do không tự mã hoá: SQLCipher là thêm một thư viện biên dịch riêng
  cho image và cho cả công cụ quản trị, mà khoá vẫn nằm cạnh database trên cùng máy chủ. Phần đã làm: máy chủ
  đặt quyền file database (và file `-wal`, `-shm`) thành chỉ chủ sở hữu đọc được (0600), để tài khoản khác
  trên cùng máy không đọc được.
- **Image không chứa bí mật hay dữ liệu (M48):** `.dockerignore` loại `.env`, `data/`, mọi file `*.db` ở bất
  kỳ thư mục nào; một test đọc các Dockerfile: không lệnh `COPY` nào lấy `data/`, `.env` hay file database,
  không `ENV` / `ARG` nào gán sẵn khoá JWT, khoá thiết bị hay mật khẩu.
- **Chưa làm:** tự xoá các bản sao lưu. Người có quyền truy cập trực tiếp vào file database trên máy chủ
  không đi qua nhật ký truy cập.

## 8. Căn cứ

| Nguyên tắc | Nguồn | DriverGuard |
|---|---|---|
| Chỉ thu đúng phạm vi, mục đích cụ thể | [L1] Điều 3 khoản 2 | Chỉ số liệu ở mục 2; trường lạ bị từ chối |
| Lưu trong thời gian phù hợp mục đích; xoá khi xong mục đích hoặc hết hạn | [L1] Điều 3 khoản 3, Điều 14 khoản 1 | Tự xoá sau 60 / 365 ngày |
| Xoá dữ liệu người lao động khi chấm dứt hợp đồng | [L1] Điều 25 khoản 2 điểm c | Lệnh `delete-driver-data` |
| Biện pháp công nghệ quản lý người lao động: người lao động phải biết rõ | [L1] Điều 25 khoản 3 điểm a | Màn hình đồng ý, tài liệu này; thông báo chính thức là việc của đơn vị |
| Dữ liệu sinh trắc học phải được bảo vệ đặc biệt | [L1] (điều về dữ liệu vị trí, sinh trắc học) | Không lưu, không gửi dữ liệu sinh trắc học nào |
| Hệ thống cảnh báo buồn ngủ không dùng thông tin sinh trắc học, chỉ ghi và giữ dữ liệu cần để tự hoạt động (vòng kín) | [E1] Phụ lục I, Phần 1, điểm 2.3.1–2.3.2; [E2] điểm 2.3.1–2.3.2 | Phần xử lý ảnh là vòng kín trên thiết bị. **Khác:** DriverGuard gửi số liệu lên máy chủ cho quản lý, là mục đích quản lý đội xe, nằm ngoài phạm vi hai quy định này và phải theo luật dữ liệu cá nhân |
| Nên xử lý ngay trong xe, không đưa dữ liệu ra ngoài khi không cần | [D1] | Mọi xử lý ảnh trên thiết bị |
| Định vị xe người lao động: giữ 2 tháng, tối đa 1 năm; không giám sát liên tục; phải báo cho người lao động thời hạn lưu | [C1] | Thời hạn 60 / 365 ngày; không có định vị |
| Giám sát người lao động: minh bạch, tối thiểu dữ liệu, có người xem xét thay cho quyết định tự động, đánh giá tác động trước khi làm | [I1] | Mục 3, 4, 6. Hồ sơ đánh giá tác động: chưa làm (mục 9) |

### Nguồn

- [L1] Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15, hiệu lực 01/01/2026. Đã đọc Điều 3, 14, 25 và
  định nghĩa dữ liệu sinh trắc học trên https://luatvietnam.vn/thong-tin/luat-bao-ve-du-lieu-ca-nhan-cua-quoc-hoi-so-91-2025-qh15-405135-d1.html
  (trang này ghi Điều 4 được hướng dẫn bởi Nghị định 356/2025/NĐ-CP; chưa đọc nghị định). Tóm tắt của Bộ
  Công an: https://mps.gov.vn/chinh-sach-phap-luat/bai-viet/bao-ve-du-lieu-ca-nhan-trong-mot-so-hoat-dong-1754989261
- [E1] Commission Delegated Regulation (EU) 2021/1341 (DDAW), văn bản gốc:
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R1341
- [E2] Commission Delegated Regulation (EU) 2023/2590 (ADDW), văn bản gốc:
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2590
- [C1] CNIL, "La géolocalisation des véhicules des salariés":
  https://www.cnil.fr/fr/la-geolocalisation-des-vehicules-des-salaries
- [D1] EDPB, Guidelines 01/2020 on processing personal data in the context of connected vehicles. *Chưa
  đọc văn bản gốc*, dùng bản tóm tắt: https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/edpb-guidelines-on-connected-vehicles
- [I1] ICO (Anh), hướng dẫn "Monitoring workers" (2023). *Chưa đọc văn bản gốc*, dùng bản tóm tắt:
  https://www.brownejacobson.com/insights/monitoring-workers-ico-guidance

Hai quy định EU và hướng dẫn của CNIL, EDPB, ICO không có hiệu lực ở Việt Nam; chúng được dùng làm
mốc thực hành tốt.

## 9. Việc của đơn vị triển khai trên xe thật

Ứng dụng không làm thay được các việc sau:

1. Thông báo và thoả thuận với tài xế về việc giám sát (nội quy, phụ lục hợp đồng), đưa tài liệu này
   cho tài xế. Có mẫu để điền: [driver-notice-template.md](driver-notice-template.md) (M48).
2. Lập hồ sơ đánh giá tác động xử lý dữ liệu cá nhân theo [L1] và nghị định hướng dẫn. Có mẫu đã điền sẵn
   phần kỹ thuật: [dpia-template.md](dpia-template.md) (M48). Cả hai mẫu là bản nháp của nhóm kỹ thuật,
   **không phải tư vấn pháp lý**; đơn vị triển khai phải rà soát với người có chuyên môn.
3. Chỉ định người chịu trách nhiệm trả lời yêu cầu xem / xoá dữ liệu của tài xế.
4. Xoá số liệu của tài xế khi chấm dứt hợp đồng (lệnh ở mục 5).
5. Quản lý các bản sao lưu database: bản sao lưu lúc deploy **không tự xoá** và có thể chứa dữ liệu đã
   quá hạn.
6. Nếu xe thuộc diện phải lắp camera ghi hình theo quy định về kinh doanh vận tải: đó là một hệ thống
   khác, có yêu cầu lưu hình riêng. DriverGuard không ghi hình và không thay thế được nó. *(Chưa đọc văn
   bản gốc của quy định này.)*

## 10. Giới hạn đã biết

- Thời hạn 60 / 365 ngày chưa có ý kiến pháp lý.
- Database không được mã hoá ở mức ứng dụng (xem mục 7): dựa vào mã hoá ổ đĩa của nơi host. Nhật ký truy
  cập chỉ thấy những gì đi qua API; khi xoá dữ liệu một tài xế, các dòng nhật ký về tài xế đó vẫn được giữ đến hết hạn.
- Bản sao lưu không nằm trong cơ chế tự xoá.
- Trang `#/drive` (điều khiển xe của bản xem thử) không cần đăng nhập; nó chỉ nhận tốc độ và xi nhan
  giả lập, không có dữ liệu của tài xế.
- Bản web tải thư viện từ CDN bên ngoài (jsdelivr): máy chủ CDN thấy địa chỉ IP của trình duyệt. Không
  có dữ liệu giám sát nào đi qua đó.
