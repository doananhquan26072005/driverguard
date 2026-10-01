# Tra cứu: tốc độ mở mắt khi chớp, gục đầu và cúi đầu, nhướn mày (01/10/2026)

Cơ sở cho 3 tín hiệu buồn ngủ mới của khối 7 (mốc M11–M13, xem `docs/release-v2.md`). Mọi ngưỡng ghi
"tạm" là đề xuất, **chưa dò trên dataset**. Chúng nằm trong `config/thresholds.yaml` và chờ eval.

## 1. Chớp mắt chậm: thời gian mở mắt lại và tỉ lệ thời gian chớp

**Nguồn:**
- Caffier et al. 2003, *Experimental evaluation of eye-blink parameters as a drowsiness measure*, Eur J
  Appl Physiol 89:319–325 ([ResearchGate](https://www.researchgate.net/publication/10768699_Experimental_evaluation_of_eye-blink_parameters_as_a_drowsiness_measure)):
  - 60 người;
  - chớp lúc tỉnh dài khoảng 200 ms, khép nhanh (khoảng 63 ms) và mở chậm hơn (khoảng 138 ms);
  - **thời gian mở mắt lại tăng từ 162 ± 49 ms (tỉnh) lên 273 ± 100 ms (buồn ngủ)**, tức khoảng ×1,7;
  - độ dài chớp, thời gian mở lại và tỉ lệ chớp dài đều khác biệt rõ giữa tỉnh và buồn ngủ.
- Schleicher et al. 2008, *Blinks and saccades as indicators of fatigue in sleepiness warnings*,
  Ergonomics 51:982–1010 ([ResearchGate](https://www.researchgate.net/publication/5287545_Blinks_and_saccades_as_indicators_of_fatigue_in_sleepiness_warnings_Looking_tired)):
  - 129 người lái mô phỏng 2 giờ;
  - chỉ báo tốt nhất: độ dài chớp, **độ trễ mở mi lại**, khoảng cách giữa hai lần chớp, tốc độ khép
    mi đã chuẩn hoá.
- Wilkinson et al. 2013, *The accuracy of eyelid movement parameters for drowsiness detection*, J Clin
  Sleep Med ([PMC3836343](https://pmc.ncbi.nlm.nih.gov/articles/PMC3836343/)):
  - đo bằng Optalert (hồng ngoại);
  - thời lượng trung bình của một lần khép mi (IED) và tỉ lệ biên độ / vận tốc khi khép (AVR) dự
    báo lỗi chú ý với AUC 0,73–0,83;
  - IED: độ nhạy 71 %, độ đặc hiệu 88 % cho ≥ 3 lần mất tập trung / phút.
- Johns, Optalert: Johns Drowsiness Scale gộp AVR khép / mở với thời lượng khép, nhắm, mở mi
  ([JCSM 2013](https://jcsm.aasm.org/doi/10.5664/jcsm.2992)).
- Tổng quan PERCLOS (Sleep Advances 2023, [zpad006](https://academic.oup.com/sleepadvances/article/4/1/zpad006/7000589)):
  - PERCLOS chuẩn là P80 (mi khép trên 80 %);
  - nhiều nghiên cứu **loại các lần chớp nhanh** (< 250 / 400 / 500 ms) ra khỏi PERCLOS;
  - tần số lấy mẫu từ 2 Hz đến 120 Hz.

**Con số "~16 % thời gian":**
- Trong repo, con số này có ở ghi chú video phân tích DMS thương mại (`docs/improvements.md`, mục 5):
  "PERCLOS cửa sổ 60 s, ngưỡng 0,15 (video: ~16%)". Tức là ngưỡng **PERCLOS** của video đó, không
  phải số đo riêng cho chớp mắt.
- Chưa tìm được bài báo gốc cho đúng con số này. Ngưỡng PERCLOS hay gặp trong tài liệu là
  12–20 %, P80; code đang dùng 0,15.
- Ước lượng để đối chiếu khi áp cho thời gian chớp:
  - Lúc tỉnh khoảng 15 lần chớp / phút × 0,2–0,3 s = 3–4,5 s / phút, tức **5–8 %** thời gian.
  - Buồn ngủ khoảng 20 lần / phút × 0,45 s ≈ 9 s / phút ≈ **15 %**.
  - Vậy 16 % là mức hợp lý cho "chớp nhiều và chậm".

Trong code, **tỉ lệ thời gian chớp** = tổng thời lượng các lần chớp (≤ `blink_max_s`) trong 60 s /
thời gian đo được mắt. Thành phần điểm tăng dần từ 10 % đến **16 % (tạm)**.

**Khác PERCLOS:** PERCLOS ở đây đếm mọi frame mắt khép (EAR < 0,65 × mốc), không phân biệt chớp hay
nhắm lâu. Tỉ lệ thời gian chớp chỉ tính các lần chớp, và đo theo độ dài toàn bộ cú chớp (từ lúc mi bắt
đầu khép đến lúc mở lại hẳn), nên nhạy với chớp chậm hơn.

**Thời gian mở mắt lại:**
- Đo từ điểm mi khép nhất đến lúc mở lại 80 % (độ mở chuẩn hoá giữa mốc nhắm và mốc mở của tài xế).
- So với **mốc của chính tài xế**: trung vị thời gian mở lại của các lần chớp đầu chuyến, lúc còn tỉnh.
- Lý do so với mốc riêng: khác biệt giữa người với người lớn, và ±49 ms ở người tỉnh đã gần bằng
  độ chênh trung bình.
- Thành phần điểm tăng dần khi tỉ lệ so với mốc đi từ ×1,3 đến **×1,7 (theo Caffier)**.

**Giới hạn đo bằng camera:**
- Ở 30 FPS mỗi frame là 33 ms; ở 15 FPS là 67 ms. Một lần mở mi lúc tỉnh (khoảng 160 ms) chỉ có
  2–5 frame.
- Code nội suy tuyến tính thời điểm cắt ngưỡng giữa hai frame, và chỉ dùng **trung vị nhiều lần
  chớp** (tối thiểu 5 lần trong 60 s).
- Đây là đo thô so với Optalert (hồng ngoại, tần số cao). Cần eval trên video có nhãn.

## 2. Gục đầu và cúi đầu

**Nguồn:**
- Mô tả "nodding off": đầu **rủ xuống từ từ** khi cơ cổ mất trương lực, rồi **giật lên đột ngột** khi
  tỉnh lại (phản xạ giật khi chớm ngủ, hypnic jerk) ([Microsleep, Wikipedia](https://en.wikipedia.org/wiki/Microsleep);
  [HuffPost, giải thích của bác sĩ giấc ngủ](https://www.huffpost.com/entry/wake-jolt-nod_n_56ccd502e4b041136f18a987)).
- Gục đầu là dấu hiệu **muộn**: thường chỉ xuất hiện khi đã chớm ngủ (patent Optalert / Johns
  [US 7071831](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7071831)).
- *Chưa tìm được* nghiên cứu đo cụ thể vận tốc đầu (°/s) khi gục. Các ngưỡng tốc độ dưới đây là tạm.

**Cách phân biệt** (pitch so với tư thế nhìn đường; đã đăng ký thì lấy từ bước 2 của đăng ký):

| | Gục đầu (buồn ngủ) | Cúi đầu (chủ động: nhìn đồng hồ, điện thoại, nhặt đồ) |
|---|---|---|
| Đi xuống | Chậm, cơ cổ thả lỏng | Có kiểm soát |
| Đi lên | **Giật lên nhanh** | Cùng tốc độ hoặc chậm hơn lúc xuống |
| Mắt | Nhắm một phần thời gian | Mở (nhìn vào vật gì đó) |

**Luật trong code:**
- Tốc độ đi lên trung bình ≥ `nod.rise_speed_ratio` × tốc độ đi xuống, và tốc độ đi lên ≥
  `nod.min_rise_deg_s`.
- Pha xuống tính từ lúc rời tư thế thường đến lúc chạm đáy; pha lên tính từ lúc rời đáy đến lúc về.
  "Đáy" là trong khoảng 15 % độ sâu, nên đoạn giữ đầu ở dưới không bị tính vào.
- Dip không đạt luật thì là sự kiện `bow` (cúi đầu chủ động), không tính vào điểm buồn ngủ.

**Kết quả replay trên trace (01/10):** không bộ ngưỡng nào tốt hơn v1.

| Cấu hình | FL3D: gục đúng / sai | SUST: precision sự kiện gục |
|---|---|---|
| v1 (không có phép thử tốc độ) | 115 / 1 | 48,3 % |
| Tỉ lệ 1,0 | 91 / 3 | 33 % |
| Tỉ lệ 1,2 | 73 / 3 | 33 % |
| Tỉ lệ 1,5 | 66 / 2 | 33 % |
| Tối thiểu 40 °/s | 73 / 1 | 32 % |
| Tỉ lệ 1,5 + 40 °/s | 51 / 1 | 25 % |

- Trong FL3D (diễn lại) và SUST (clip 10 s), một nửa số lần gục lúc đang ngủ gật **không** có dạng
  "giật lên nhanh" đo được qua góc pitch của camera.
- Hai dataset này cũng gần như không có cảnh cúi nhìn điện thoại với mắt nhìn xuống, tức đúng trường
  hợp phép thử này muốn chặn. Vì vậy không đo được lợi ích của nó.
- **Mặc định: tắt** (`rise_speed_ratio: 0`, `min_rise_deg_s: 0`, `max_drop_s: 0`,
  `max_rise_s: 0`). Kết quả giống hệt v1, chỉ thêm sự kiện `bow`.
- Cấu hình để thử: `max_drop_s` 3, `max_rise_s` 1, `max_s` 3, `rise_speed_ratio` 1,5,
  `min_rise_deg_s` 40.
- Cần clip có nhãn gồm cả cúi nhìn điện thoại / bảng đồng hồ lẫn gục thật để dò.

## 3. Nhướn mày để giữ mắt mở

**Nguồn:**
- Vural, Çetin, Erçil, Littlewort, Bartlett, Movellan 2007, *Drowsy driver detection through facial
  movement analysis*, ICCV HCI Workshop
  ([ResearchGate](https://www.researchgate.net/publication/227047615_Drowsy_Driver_Detection_Through_Facial_Movement_Analysis);
  [PDF](https://inc.ucsd.edu/mplab/46/media/vesra.pdf)):
  - Hệ thống đo tự động 30 đơn vị chuyển động mặt (AU, theo hệ mã FACS).
  - Trong các biểu hiện dự báo buồn ngủ tốt nhất có **nhướn đuôi mày (AU2)**.
  - Nhóm tác giả ghi nhận nhiều người **nhướn mày để cố giữ mắt mở**, và việc AU2 liên quan mạnh với
    buồn ngủ khớp với quan sát đó.
- Nghiên cứu mô phỏng 40 tài xế (J Res Health Sci, [PMC5401941](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5401941/)):
  thay đổi ở mắt, lông mày và miệng liên quan có ý nghĩa với mức buồn ngủ, trong đó có nếp nhăn trán
  khi tài xế đẩy lông mày lên để giữ mắt mở.

**Tín hiệu MediaPipe:**
- Blendshape `browOuterUpLeft` / `browOuterUpRight` (cơ trán phần ngoài, tương ứng AU2) và
  `browInnerUp` (AU1).
- Cùng model Face Landmarker đang dùng, không tốn thêm thời gian
  ([MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)).
- Code dùng **trung bình hai bên `browOuterUp`** (AU2, theo Vural).

**Luật trong code (tạm):**
- Một lần "nhướn mày chống buồn ngủ" khi đủ cả các điều kiện:
  - lông mày cao hơn mức bình thường của tài xế ≥ `brow.raise_above` (0,2);
  - đồng thời mắt hơi sụp, chưa nhắm: EAR < `brow.narrow_ratio` (0,85) × mốc mắt mở;
  - kéo dài ≥ `brow.min_s` (0,5 s).
- Mức bình thường của lông mày: lấy từ bước 1 của đăng ký. Chưa đăng ký thì lấy trung vị 120 s gần
  nhất.
- **Không tính** lúc ngáp hoặc nói chuyện (lông mày cũng nhướn khi ngáp), và không tính khi mắt mở to
  (ngạc nhiên).
- Đếm trong 5 phút. Đủ 3 lần thì thành phần điểm đạt tối đa.
