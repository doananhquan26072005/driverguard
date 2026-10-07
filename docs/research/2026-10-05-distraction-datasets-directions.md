# Tra cứu: dataset mất tập trung và hướng phát triển khối 8 (05/10/2026)

Cơ sở để mở rộng nhánh mất tập trung (khối 8), hiện chỉ có `off_road` (góc đầu) và `phone` (YOLO lớp 67).
Mọi nguồn mở ngày 05/10/2026. Chỉ đọc tài liệu, **không tải dataset, không chạy thử, không đo gì trên
code**. Số trong ngoặc vuông là số thứ tự ở mục [Nguồn](#nguon). Chỗ nào ghi *chưa kiểm chứng* là chưa
đọc được nguồn gốc; danh sách đầy đủ ở [mục 4](#chua-kiem-chung).

## 1. Kết luận

**Dataset nên lấy trước (đều có camera hướng mặt):**

1. **DMD, bộ Distraction và bộ Gaze & Hands** [1][2][3][4]. Camera mặt quay chính diện, RGB. Bộ
   Distraction có nhãn "Looking at the road / Not looking at the road" gán từ camera mặt: đây là nhãn đo
   thẳng `off_road`. Bộ Gaze có 9 vùng nhìn gán cho mọi frame. Tải thẳng từ trang chính.
2. **3MDAD, góc nhìn trước (Kinect 2)** [18][19]. Camera trên taplo trước mặt tài xế, RGB ban ngày
   (3,61 GB) và IR ban đêm (9,77 GB), 16 hành vi trong đó có hút thuốc, uống nước, chỉnh radio, GPS, với
   ra sau. Có trên Kaggle, CC BY-NC-ND 4.0. Dùng làm bộ "ca dễ nhầm" để đo báo sai của `phone` và
   `off_road`, và là nguồn IR ban đêm duy nhất có hành vi mất tập trung.
3. **LISA Gaze v2** [23][24]. Camera IR cạnh gương chiếu hậu, 13 người, có và không đeo kính, ngày và
   đêm, 7 vùng nhìn. Tải thẳng Google Drive. Dùng để trả lời câu hỏi "blendshape hướng nhìn còn dùng được
   khi IR và đeo kính không" trước khi viết luật hướng mắt (việc 4).

Hạng hai, lấy khi ba bộ trên chưa đủ: SynDD2 góc Dashboard (xe đứng yên, có mũ / kính râm) [9][10],
100-Driver camera "front" (phải gửi form qua email) [6][7][8], DGW (phải email) [21][22].

**Không hợp camera hướng mặt, không lấy:** AUC Distracted Driver (camera treo ở tay nắm trần phía ghế
phụ) [17], State Farm (đã biết), DriverMHG (camera quay tay trên vô lăng) [20], DADA-2000 và BDD-A
(không có camera quay tài xế) [28][29], DGAZE (trong phòng lab, nhãn là điểm nhìn trên ảnh đường) [27].
DAD chỉ có depth và IR 224 × 171, không có RGB [14][15]. Drive&Act quay trong mô phỏng, hành vi là việc
làm khi xe tự lái [13]. SHRP2: video mặt không được mang ra ngoài [32].

**Nên làm trước (xếp theo lợi ích trên rủi ro báo sai):**

1. Đo (chưa cảnh báo) **liếc ngắn cộng dồn** theo định nghĩa Euro NCAP: rời đường cộng dồn 10 s trong
   cửa sổ 30 s [34][35]. Đây là số còn thiếu của việc 31.
2. Đo lại `off_road` với **ngưỡng tách theo hướng**. Quy định EU chỉ bắt cảnh báo khi nhìn **xuống thấp**
   (Area 3, dưới 30°) quá 3,5 s ở ≥ 50 km/h và 6 s ở ≥ 20 km/h [33]; Euro NCAP dùng 3 đến 4 s [34].
   DriverGuard đang báo ở 2 s cho mọi hướng (1,5 s trên 80 km/h), tức chặt hơn cả hai. `off_road` là
   nguồn báo sai chính trên SUST (24/26, theo việc 31; chưa tách theo hướng nhìn). Nhìn gương và quan
   sát hai bên là hành vi **giảm** rủi ro theo số liệu 100-Car [37].
3. Ghi `eyeLook*` và vị trí mống mắt vào trace (chỉ đo), rồi chấm trên DMD Gaze và LISA Gaze v2.
4. `phone_kind` gọi / nhắn tin (việc 32), chỉ ghi ra.

**Không làm:**

- Cảnh báo riêng cho ăn, uống, hút thuốc, nói chuyện với hành khách. Euro NCAP xếp các hành vi này vào
  "biến nhiễu" mà hệ thống phải chịu được, không phải thứ cần phát hiện [34]. Trong 100-Car, uống nước
  có tỉ số odds 1,03, nói chuyện với người ngồi cạnh 0,50 [37]. Giữ nguyên quyết định bỏ ngày 02/10.
- Thêm model ước lượng hướng nhìn. Model nhỏ nhất tìm được (MobileOne-S0, 4,97 MB) sai trung bình
  12,58° trên Gaze360 và cần ảnh mặt 448 × 448 [46]: không tốt hơn cách "góc đầu + blendshape" về mặt
  bằng chứng, lại thêm tải.
- Thêm MediaPipe Hand / Pose vào vòng lặp chính. Camera hướng mặt hiếm khi thấy tay; tài liệu ghi 17 ms
  CPU trên Pixel 6 cho riêng Hand Landmarker [44].
- Không tìm thấy model YOLO trong cabin nào có trọng số tải được kèm số đo trên camera hướng mặt [49].

---

## 2. Phần 1: dataset có nhãn mất tập trung

Tất cả chỉ dùng để **đánh giá và dò ngưỡng** (CLAUDE.md: không train). Không đưa frame vào repo.

### 2.1 DMD (Vicomtech): bộ Distraction và bộ Gaze & Hands

Phần đã có ở phụ lục B của `docs/improvements.md` không lặp lại. Phần mới:

- **Camera.** Paper: "Two D415 cameras recorded the face area frontally and the hands area from the
  back; one D435 camera was used to capture the drivers body from the left side", khoảng 30 FPS [5,
  mục 3.2]. README hiện tại: stream còn phát hành là "RGB (Body, Face, and Hands views)", chỉ xe thật,
  14 người [2]. Vậy **video camera mặt có trong bản phát hành**. *Chưa kiểm chứng* là cả ba gói tải đều
  kèm đủ ba camera: trang tải là ứng dụng JavaScript, không đọc được danh sách file.
- **Nhãn bộ Distraction** [3], 7 tầng, kèm camera dùng để gán:

  | Tầng | Nhãn | Camera dùng để gán |
  |---|---|---|
  | Che khuất | Face / Body / Hands occlusion | cả ba |
  | Gaze on road | Looking at the road, Not looking at the road | **chủ yếu camera mặt** |
  | Driver is talking | Talking | **chủ yếu camera mặt** |
  | Hands using wheel | Both, Only Right, Only Left, None | camera tay |
  | Hand on gear | Hand on gear | tay và thân |
  | Objects in scene | Cellphone, Hair Comb, Bottle | cả ba |
  | Driver actions | Safe Driving, Texting (Right / Left), Phone call (Right / Left), Radio, Drinking, Reach Side, Hair and Makeup, Talking to passenger, Reach Backseat, Change Gear, Stand Still-Waiting, Unclassified | **camera thân là chính**, mặt và tay hỗ trợ |

- **Nhãn bộ Gaze** [4]: mọi frame có một vùng nhìn trong 10 giá trị: `left_mirror`, `left`, `front`,
  `center_mirror`, `front_right`, `right_mirror`, `right`, `infotainment`, `steering_wheel`,
  `not_valid`; thêm nhãn `Blinking`. Gán chủ yếu từ camera mặt. Khi quay, tài xế nhìn cố định vào 9 vùng
  định sẵn [5, mục 3.1].
- **Độ mịn nhãn:** theo frame (OpenLABEL / VCD) [2].
- **Lái thật hay không:** các hành vi rủi ro được quay trong mô phỏng và "in the car while being
  stopped" [5, mục 3.2]. Bản phát hành chỉ còn xe thật [2], nên phần hành vi nguy hiểm nhiều khả năng là
  xe đứng yên: phải giả lập tốc độ khi replay.
- **License:** CC BY-NC-ND 4.0, "can only be used for academic purposes" [1][2].
- **Cách lấy:** trang chính có ba đường dẫn tải riêng cho Gaze & Hands, Drowsiness, Distraction [1].
  Đường dẫn bộ Distraction có đuôi `distraction-rgb-ir`. *Chưa kiểm chứng:* có form đăng ký không, dung
  lượng từng gói, số giờ còn lại sau khi cắt còn 14 người.
- **Lấp chỗ nào của DriverGuard:**
  - nhãn "Not looking at the road" theo frame → recall và độ trễ của `off_road`, thử ngưỡng 2 s / 3 s;
  - vùng nhìn theo frame → chấm `eyeLook*` + góc đầu (việc 4), tách `infotainment` (liếc mắt) khỏi
    `left` / `right` (quay đầu);
  - Texting / Phone call trái, phải → recall `phone` đúng góc camera và độ chính xác `phone_kind` (việc
    32);
  - Drinking, Hair and Makeup, Radio, Reach → ca dễ nhầm để đếm báo sai của `phone`;
  - Reach Backseat → tái hiện việc 33 (quay ra sau rồi mất mặt) bằng dữ liệu thật.
- **Lưu ý:** nhãn Driver actions gán từ camera thân. Một hành vi thấy rõ ở camera thân có thể nằm ngoài
  khung camera mặt (điện thoại trên đùi). Recall đo trên camera mặt sẽ thấp hơn con số các bài báo dùng
  camera thân.

### 2.2 3MDAD

- **Nội dung** [18][19]: hai Kinect quay đồng bộ. "The first Kinect is mounted on the car handle on the
  top of the passenger window, and the second is placed on the dashboard in front of the driver."
  Vậy **Kinect 2 là góc nhìn trước**.
- **Phương thức:** ban ngày RGB + depth, 50 người (38 nam, 12 nữ, 19 đến 41 tuổi); ban đêm IR + depth,
  19 người (11 nam, 8 nữ, 19 đến 53 tuổi) [19].
- **Nhãn, 16 hành vi** [18][19]: A1 Safe driving, A2 Doing hair and makeup, A3 Adjusting radio, A4 GPS
  operating, A5 / A6 Writing message (tay phải / trái), A7 / A8 Talking phone (tay phải / trái), A9
  Having picture, A10 Talking to passenger, A11 Singing or dancing, A12 Fatigue and somnolence, A13 / A14
  Drinking (tay phải / trái), A15 Reaching behind, A16 Smoking.
- **Độ mịn nhãn:** một hành vi cho mỗi chuỗi frame. *Suy ra từ tên file* dạng `RGB1S10AC1` (Kinect 1,
  người 10, hành vi 1) trong danh sách file Kaggle [19]; chưa mở dữ liệu. Khung đầu / tay chỉ có cho
  góc bên, ban ngày [19]: không dùng được cho camera mặt.
- **Lái thật:** trang mô tả là "two real-world driving sets", người tham gia "were asked to drive the
  vehicle" [19]. *Chưa kiểm chứng* xe có lăn bánh trong lúc làm hành vi hay không (paper nằm sau tường
  phí).
- **License:** "publicly available for non-commercial use" [18]; Kaggle ghi CC BY-NC-ND 4.0 [19].
- **Cách lấy:** Kaggle `anouarbenkhalifa/3mdad-multimodal-driver-action-distraction`, do chính tác giả
  đăng 01/04/2026, tổng **38,3 GB** (kiểm tra qua Kaggle API) [19]. Theo mô tả: góc trước ban ngày RGB2
  3,61 GB, góc trước ban đêm IR2 9,77 GB. *Chưa kiểm chứng* có tải riêng được từng phần không.
- **Lấp chỗ nào:** hút thuốc và "chụp ảnh" là hai lớp DMD không có; IR ban đêm có hành vi mất tập trung
  (DMD đã bỏ IR); 50 người, nhiều hơn 14 người của DMD. Dùng để đếm báo sai `phone` khi tay cầm vật
  khác đưa lên mặt, và xem `off_road` phản ứng thế nào với A3 / A4 / A15.
- **Hạn chế:** Kinect đặt trên taplo, góc rộng: mặt có thể nhỏ. Không có nhãn theo frame nên không đo
  được độ trễ.

### 2.3 LISA Gaze v0 / v1 / v2 (UCSD)

- **Nội dung v2** [24, mục dataset]: camera Intel RealSense IR "mounted next to the rearview mirror",
  640 × 480. 13 người (7 nam, 20 đến 65 tuổi), 336 177 frame, 4 điều kiện: ngày / đêm × có / không kính.
  Chia train / val / test không trùng người.
- **Nhãn, 7 vùng:** Eyes Closed/Lap, Forward, Left Mirror, Speedometer, Radio, Rearview, Right Mirror.
  Người tham gia được yêu cầu giữ mắt cố định vào vùng trong khi vẫn cử động đầu [24]. Nhãn theo frame.
- **Cách lấy:** README repo GPCycleGAN có đường dẫn Google Drive cho v0 (RGB), v1 (RGB), v2 (IR + RGB),
  không cần đăng ký [23]. Code của repo là MIT; **license của dữ liệu không ghi** [23].
- **Lấp chỗ nào:** đúng hai rủi ro việc 4 đã nêu (IR, kính). Lớp "Eyes Closed/Lap" gộp nhắm mắt với nhìn
  xuống đùi: đây chính là cặp DriverGuard cần tách (việc 3), nên lớp này **không** dùng để chấm tách hai
  thứ đó, chỉ dùng 6 lớp còn lại.
- *Chưa kiểm chứng:* xe có đang chạy không; ảnh là cả khung hay đã cắt quanh mặt (ảnh cắt sẵn vẫn chạy
  được MediaPipe nhưng mất bố cục camera); dung lượng.

### 2.4 SynDD2 (AI City Challenge, track Naturalistic Driving Action Recognition)

- **Nội dung** [9]: ba camera hành trình Kingslim D1 Pro đặt ở taplo, gần gương chiếu hậu và góc trên cửa
  sổ phải; 1920 × 1080, 30 FPS; loại dữ liệu ghi là "InfraRed Videos". **Xe đứng yên**: "We requested the
  participants to sit inside a stationary vehicle".
- **Nhãn** [9]: hai loại hoạt động, mỗi loại quay hai lượt (không và có mũ / kính râm).
  - 16 hành vi: Normal Forward Driving, Drinking, Phone Call (right / left), Eating, Text (Right / Left),
    Reaching behind, Adjust control panel, Pick up from floor (Driver / Passenger), Talk to passenger at
    the right / at backseat, Yawning, Hand on head, Singing or dancing with music.
  - 11 vùng nhìn: left-rear mirror, forward window, speedometer, right-frontal window, rear mirror,
    control panel and shift, right-rear mirror, left-side window, left blind spot, right-side blind
    spot, right-side window.
  - File CSV ghi giờ bắt đầu và kết thúc từng hoạt động, cho từng camera (nhãn theo đoạn).
- **Cách lấy:** trang tải AIC24 Track 3 có đường dẫn Google Drive; bấm tải là chấp nhận license [10].
  Bản license đọc được là bản 2022: sau cuộc thi chỉ dùng "non-commercial, academic purposes only",
  không phân phối lại, không hiển thị mặt chưa che [11]. *Chưa kiểm chứng:* bản license 2024, số người,
  dung lượng. (Trang arXiv ghi CC BY 4.0 nhưng đó là license của bài báo, không phải của dữ liệu.)
- **Lấp chỗ nào:** có mũ và kính râm (điều kiện Euro NCAP yêu cầu), có "Pick up from floor", "Hand on
  head", "Yawning" để đo báo sai.
- **Hạn chế:** *chưa xem được ảnh góc Dashboard* nên chưa chắc đó là góc chính diện vào mặt; ống kính
  170° nên mặt nhỏ. Xe đứng yên.

### 2.5 100-Driver

- **Nội dung** [6][7]: 470 208 **ảnh** (không phải video), 100 tài xế, 79,34 giờ quay gốc, 5 xe, 4
  camera Xiaomi-C1: "Cam1: front-left, Cam2: front, Cam3: front-right, and Cam4: side-right". RGB ban
  ngày (245 266 ảnh), NIR ban đêm (224 942 ảnh). Có đổi quần áo, khẩu trang, mũ, kính râm.
- **Nhãn, 22 lớp, theo ảnh** [7, bảng II]: Normal driving, Sleeping, Yawning, Talk with cellphone (left /
  right), Texting (left / right), Hair / makeup, Looking left / right / up / down, Smoking (left / right /
  mouth), Drinking / Eating (left / right), Adjusting radio, Operating GPS / entertainment system,
  Reaching behind, Hands off the steering wheel, Talking to passengers.
- **Lái thật:** paper ghi có "a safety officer giving relevant instructions according to the road
  condition" [7]. *Chưa kiểm chứng* xe có lăn bánh trong mọi lớp không.
- **License** [8]: chỉ dùng cho nghiên cứu khoa học, cấm thương mại, không chuyển cho bên thứ ba. Phải
  điền form (đơn vị, tên, email, chữ ký) gửi `wjli007@mail.ustc.edu.cn` để nhận đường dẫn.
- **Lấp chỗ nào:** bốn lớp "Looking left / right / up / down" khớp đúng định nghĩa `off_road` theo góc
  đầu; NIR ban đêm; ba lớp hút thuốc.
- **Hạn chế:** ảnh rời đã lấy mẫu thưa, nên **không đo được luật theo thời gian** (2 s, cửa sổ 30 s);
  chỉ đo được theo frame (góc đầu có vượt ngưỡng không, YOLO có thấy điện thoại không). *Chưa xem được
  hình 4* nên chưa biết Cam2 "front" gần hay xa mặt.

### 2.6 Dataset hướng nhìn

| Dataset | Camera | Hợp camera mặt? | Ghi chú |
|---|---|---|---|
| DMD Gaze [4] | mặt, chính diện, RGB | Có | Xem 2.1 |
| LISA Gaze v2 [23][24] | IR cạnh gương chiếu hậu | Có | Xem 2.3 |
| SynDD2 Gaze [9] | taplo, IR | Có thể | Xem 2.4; 11 vùng, xe đứng yên |
| DGW [21][22] | Microsoft Lifecam RGB trong xe | Có thể | 586 bản ghi, 338 người (18 đến 63 tuổi), 9 vùng đánh số bằng nhãn dán, có buổi tối; người nhìn vùng nào thì đọc số vùng đó, nhãn sinh tự động từ giọng nói. Phải email tác giả [21]. *Chưa kiểm chứng* vị trí gắn camera và license |
| IVGaze [25] | trong xe | Một phần | 44 705 ảnh, 125 người, có kính, kính râm, khẩu trang; nhãn hướng nhìn và vùng nhìn. Ảnh **đã cắt quanh mặt**. Email cam kết phi thương mại, nhận đường dẫn trong ba ngày |
| Look Both Ways [26] | camera hướng mặt + camera đường, lái thật | Có, nhưng nặng | 28 tài xế, hướng nhìn thật lấy từ kính theo dõi mắt **tài xế đang đeo**; khoảng 300 GB (README ghi cả 300 và 350), hoặc khoảng 10 GB mỗi phiên. Kính theo dõi mắt che vùng mắt, có thể làm sai landmark. Repo không có file license |
| MDM (UT Dallas) [31] | 4 GoPro, có "Face Camera" đặt trước tài xế | Có | 59 người, 50 giờ 14 phút, lái thật, nhìn vào 21 điểm đánh dấu, có việc phụ (dẫn đường bằng điện thoại). Tài xế đội mũ Fi-Cap sau đầu. *Chưa kiểm chứng* có phát hành công khai không |
| DGAZE [27] | điện thoại trên taplo, **trong phòng lab** | Không | Video đường chiếu trước mặt người ngồi; nhãn là điểm nhìn trên ảnh đường. Chỉ dùng cho nghiên cứu |
| DADA-2000 [28], BDD-A [29] | không có camera quay tài xế | Không | Nhãn là bản đồ chú ý trên video đường, thu trong phòng lab bằng máy theo dõi mắt |
| ETH-XGaze [30] | 18 máy ảnh DSLR trong studio | Không | 110 người, hơn một triệu ảnh; bản mặt 224 × 224 đã 130 GB; CC BY-NC-SA 4.0 kèm điều khoản, phải đăng ký. Đo được sai số góc của hướng nhìn nhưng không phải bối cảnh lái xe |
| Gaze360, MPIIFaceGaze, Columbia Gaze | — | Không xét | *Chưa mở trang gốc* (Gaze360 trả 403). Đều không quay trong xe; chỉ có ích nếu sau này cần đo sai số góc tuyệt đối |

### 2.7 Các bộ còn lại

- **AUC Distracted Driver v1 / v2** [17]: camera "fixed using an arm strap to the car roof handle on top
  of the front passenger's seat", tức góc bên như State Farm. 44 người, 14 478 frame, 10 lớp. **Không
  hợp.** Bản tải trên đĩa có khoá mật khẩu hay không thì không cần xử lý nữa.
- **DAD** [14][15][16]: mô phỏng lái (buồng lái BMW thật, chạy game), hai camera Infineon pico flexx đặt
  trên và **trước** tài xế, chỉ **depth + IR 224 × 171**, 45 FPS, không có RGB. 31 người; train khoảng
  550 phút lái bình thường + 100 phút bất thường, test 88 + 45 phút; khoảng 95 GB, 10 file RAR; "freely
  available for research purposes". Test có 16 hành vi không có trong train (chỉnh gương, lau mũi, hắt
  hơi, ho, ăn, đọc...). Ý tưởng "bất kỳ thứ gì khác lái bình thường" hay cho việc đo báo sai, nhưng độ
  phân giải 224 × 171 cho cả đầu và thân là rất thấp so với đầu vào 256 × 256 riêng cho mặt của Face
  Mesh [42]. **Không lấy** trừ khi thử một file và MediaPipe bám được mặt.
- **Drive&Act** [12][13]: 15 người, 30 phiên trung bình 24 phút, tổng 12 giờ, quay trong **mô phỏng lái
  tĩnh** (Audi A3 cải tiến, phần mềm SILAB). 5 camera NIR 1280 × 1024 + Kinect; có một góc "face view".
  Nhãn phân cấp theo frame (12 nhiệm vụ, 34 hoạt động), nhưng nội dung là việc làm khi xe tự lái (dùng
  laptop, đọc báo, mặc áo khoác). Chính paper ghi góc mặt cho kết quả nhận hành vi thấp nhất (42,98 %)
  vì "mostly only the face of the driver is visible". Chỉ dùng cho nghiên cứu, tải không cần xin phép
  [12]. **Không ưu tiên**: sai bối cảnh, dù có góc mặt.
- **DriverMHG** [20]: cử chỉ tay nhỏ trên vô lăng, quay trong mô phỏng. Paper không nhắc tới mặt.
  **Không hợp.**
- **SHRP2 NDS, 100-Car:** trang điều khoản InSight ghi phải đăng ký và nộp chứng chỉ đào tạo IRB; người
  đủ điều kiện được xem rộng hơn "but not to personally identifying information" [32]. Video mặt là dữ
  liệu định danh. *Theo kết quả tìm kiếm trên trang TRB (chưa mở trang):* video mặt chỉ dùng trong
  "secure data enclave" với giấy phép dùng dữ liệu và phê duyệt IRB. **Không khả thi** cho dự án học
  tập. Giá trị của hai nghiên cứu này là các con số rủi ro ở mục 3.1.

### 2.8 Bảng so sánh

| Dataset | Camera mặt | Phương thức | Người | Nhãn mất tập trung | Độ mịn | Lái thật | License | Cách lấy |
|---|---|---|---|---|---|---|---|---|
| **DMD Distraction** [1][2][3][5] | Có, chính diện | RGB | 14 (gốc 37) | 13 hành vi + nhìn đường / không + nói + tay + vật | Frame | Xe thật, hành vi rủi ro lúc đứng yên | CC BY-NC-ND 4.0 | Đường dẫn trên trang chính |
| **DMD Gaze** [4] | Có | RGB | 14 | 9 vùng nhìn + chớp | Frame | *Chưa kiểm chứng* | như trên | như trên |
| **3MDAD** [18][19] | Có, taplo | RGB ngày, IR đêm, depth | 50 ngày, 19 đêm | 16 hành vi | Chuỗi | "Real-world driving", *chưa rõ lăn bánh* | CC BY-NC-ND 4.0 | Kaggle, 38,3 GB |
| **LISA Gaze v2** [23][24] | Có, cạnh gương | IR (+RGB) | 13 | 7 vùng nhìn | Frame | *Chưa kiểm chứng* | Không ghi | Google Drive |
| SynDD2 [9][10][11] | Có thể (Dashboard) | IR | *chưa rõ* | 16 hành vi + 11 vùng nhìn | Đoạn | Không, đứng yên | Phi thương mại, học thuật (bản 2022) | Google Drive |
| 100-Driver [6][7][8] | Có (Cam2 "front") | RGB ngày, NIR đêm | 100 | 22 lớp | Ảnh rời | *Chưa rõ* | Chỉ nghiên cứu | Form qua email |
| DGW [21][22] | Có thể | RGB | 338 | 9 vùng nhìn | Frame | Không rõ | Không ghi | Email |
| Drive&Act [12][13] | Có một góc | NIR, depth, RGB | 15 | 83 nhãn phân cấp | Frame | Không, mô phỏng | Chỉ nghiên cứu | Tải thẳng |
| DAD [14][15] | Trước, cả thân | Depth + IR 224 × 171 | 31 | Bình thường / bất thường + 24 hành vi | Đoạn | Không, mô phỏng | Nghiên cứu | Tải thẳng, 95 GB |
| AUC [17] | **Không** | RGB | 44 | 10 lớp | Ảnh | Có | Ký thoả thuận | — |
| DriverMHG [20] | **Không** | RGB, IR, depth | 25 | Cử chỉ tay | Đoạn | Không | — | — |
| DADA-2000, BDD-A [28][29] | **Không có** | — | — | Bản đồ chú ý | — | — | — | — |

**Khuyến nghị:** lấy theo thứ tự (1) DMD Distraction + Gaze, (2) 3MDAD góc trước, (3) LISA Gaze v2.
Lý do: cả ba tải được ngay không cần chờ duyệt; DMD có nhãn theo frame đúng thứ khối 8 đang tính; 3MDAD
bù lớp hành vi và IR đêm; LISA v2 bù IR + kính cho hướng nhìn. Trước khi viết loader, mở thử một file
của mỗi bộ để xác nhận mặt đủ lớn cho MediaPipe.

---

## 3. Phần 2: hướng phát triển

### 3.1 Các nguồn có thẩm quyền yêu cầu gì

#### EU ADDW: Delegated Regulation (EU) 2023/2590 [33]

Áp dụng từ 07/07/2024 (Điều 5). Mọi điểm dưới đây thuộc Phụ lục I.

- **Yêu cầu chung** (Phần 1, điểm 2.1, 2.2): hệ thống xác định khi "the driver's visual attention is not
  directed towards the driving tasks", và "shall be designed to minimise the system error rate (false
  positive) under real driving conditions".
- **Quyền riêng tư** (2.3.1, 2.3.2): không dựa vào dữ liệu sinh trắc học để nhận dạng người; chỉ ghi và
  giữ dữ liệu cần cho hệ thống chạy, trong hệ thống vòng kín. Khớp với ràng buộc của CLAUDE.md.
- **Kích hoạt** (3.1.1): tự bật trên 20 km/h; được phép tối đa 1 phút cộng dồn ở ≥ 20 km/h để bắt đầu đo
  và tự hiệu chỉnh.
- **Ba vùng nhìn** (3.3.1), tính từ điểm mắt chuẩn:
  - Area 1: trần xe, và mọi vùng nằm ngoài hai mặt phẳng đứng ±55° so với hướng dọc xe;
  - Area 2: kính chắn gió và cửa sổ, cộng 10° xung quanh;
  - **Area 3: mọi vùng nằm dưới mặt phẳng nghiêng xuống 30°** từ điểm mắt, trừ phần đã thuộc Area 1 và
    Area 2.
- **Điều kiện cảnh báo** (3.3.2.1, 3.3.2.2): chỉ quy định cho **Area 3**.
  - ≥ 50 km/h: nhìn vào Area 3 tối đa **3,5 s**;
  - ≥ 20 km/h: tối đa **6 s**;
  - tình huống "non-nominal" được cộng thêm 1,5 s.
- **Không xoá bộ đếm vì nhiễu** (3.3.2.4): bộ đếm không được về 0 do lỗi xử lý ảnh hoặc do mắt đổi hướng
  ngắn "in, out and back in"; dung sai do nhà sản xuất đặt, tối thiểu 50 ms.
- **Chiến lược bổ sung** (3.3.2.6): nhà sản xuất được thêm chiến lược cảnh báo khác.
- **Cảnh báo** (3.4.1.1): hình ảnh để báo, cộng âm thanh và / hoặc rung để gây chú ý; được leo thang.
  Âm thanh phần lớn trong 200 đến 8 000 Hz, 50 đến 90 dB (3.4.3.2).
- **Che camera** (3.5.1.3): phải nhận ra che cảm biến không tạm thời và báo lỗi; tối thiểu là trường hợp
  cảm biến không đo được ánh sáng. Khi không đủ đặc điểm khuôn mặt để hoạt động thì phải thông tin cho
  tài xế về giới hạn (3.5.2.2).
- **Thử nghiệm** (Phần 2): người thử không đeo kính, mũ, khẩu trang, không râu (1.3.1.2, 1.3.1.3). 14
  nhóm điểm nhìn (1.4.2): đầu gối trái, đầu gối phải, đùi, hốc chân ghế phụ, mặt ghế phụ, hộp găng tay,
  cửa gió trái, cửa gió phải, bảng đồng hồ, vô lăng có nút, cần số, điều khiển điều hoà, màn hình giải
  trí, bệ trung tâm. Mỗi điểm thử một lần ở 20 đến 35 km/h và một lần ở 50 đến 65 km/h (1.5.1), cả ngày
  lẫn đêm (1.6.1). Trước mỗi lần đo, tài xế phải được hệ thống coi là không mất tập trung ít nhất 15 s
  (2.3.5).
- **Tiêu chí** (Phần 2, điểm 3, 5, 6): bỏ sót khi không có cảnh báo trong **4 s** (ở 50 km/h) hoặc
  **6,5 s** (ở 20 km/h), đã gồm 0,5 s dung sai. Mỗi điểm bỏ sót được thử lại tối đa hai lần; trượt khi
  một điểm bỏ sót cả hai lần thử lại. Quy định **không đặt con số trần cho báo sai**, chỉ có câu ở 2.2.

**Ý nghĩa với DriverGuard:**
- Quy định chỉ bắt buộc cảnh báo khi nhìn **xuống thấp**. Nhìn gương, cửa sổ, quay sang ngang (Area 1,
  Area 2) không thuộc phần bắt buộc.
- Toàn bộ 14 điểm thử là nhìn xuống hoặc xuống chéo. Nhiều điểm tài xế chỉ cần **liếc mắt** (bảng đồng
  hồ, vô lăng, cần số): hệ thống chỉ dùng góc đầu sẽ bỏ sót.
- Ngưỡng 2 s của DriverGuard chặt hơn 3,5 s; `on_road_confirm_s` 0,3 s rộng hơn mức tối thiểu 50 ms.

#### Euro NCAP

Bản 2026, *Safe Driving – Driver Engagement Protocol* v1.1, 10/2025 [34]:

- **Ba loại mất tập trung** (định nghĩa và mục 1.2):
  - *Long Distraction* (1.2.1): một lần nhìn rời đường "between 3 and 4 seconds", trước đó có 4 s nhìn
    đường.
  - *Short Distraction / VATS* (1.2.2): nhìn rời đường "for a cumulative 10 seconds within a 30 second
    time period". Kết thúc khi chú ý trở lại đường đủ lâu để hiểu tình huống. Chiến lược khác cũng được
    tính điểm.
  - *Phone Use* (1.2.3): là VATS mà mắt hướng về điện thoại. "Basic": đầu gối ngoài, đầu gối trong, đùi,
    giá đỡ trên taplo, khay sạc. "Advanced" (chỉ liếc mắt): điện thoại trên taplo, ở vị trí 9 đến 11
    hoặc 13 đến 15 giờ trên vô lăng, trong tầm kính chắn gió, trong tầm bảng đồng hồ.
- **Kiểu chuyển động:** *Owl* (quay đầu, mắt theo sau), *Lizard* (chỉ mắt, đầu giữ thẳng), *Body Lean*.
  Một hệ thống mất khả năng theo dõi mắt được gọi là "degraded" vì không bắt được Lizard.
- **Điểm nhìn Long Distraction:** không liên quan lái xe: cửa sổ bên tài xế, cửa sổ bên ghế phụ, hốc
  chân ghế phụ, mặt hành khách, màn hình giải trí (Owl); màn hình giải trí, hộp găng tay (Lizard); hốc
  chân ghế phụ, hành khách phía sau (Body Lean). Liên quan lái xe: ba gương (Owl); bảng đồng hồ, gương
  bên tài xế, gương chiếu hậu (Lizard). **Nhìn gương quá 3 đến 4 s cũng tính là mất tập trung**, nhưng
  chấm riêng (3 điểm cho phần không liên quan lái xe, 2 điểm cho phần liên quan).
- **Điều kiện chung:** được 1 phút lái ở ≥ 10 km/h để bắt đầu đo; cảnh báo mất tập trung từ ≥ 20 km/h;
  cảnh báo hình ảnh và (rung và / hoặc âm thanh) "immediately" (1.4.1).
- **Biến nhiễu phải chịu được** (1.1.1):
  - người: 16 đến 80 tuổi, nam và nữ, vóc AF05 đến AM95, da Fitzpatrick 1 đến 6, độ mở mi 6,0 đến
    12,0 mm;
  - che khuất, *phải hoạt động*: ánh sáng 1 lux đến 100 000 lux, kính trong (truyền sáng > 70 %, kể cả
    gọng dày), râu ngắn và râu dài, **khẩu trang**;
  - che khuất, *không hoạt động được thì phải báo cho tài xế trong 10 s*: kính râm truyền sáng < 15 %,
    một tay đặt ở vị trí 12 giờ trên vô lăng, mũ, tóc mái che mắt, mi giả dày;
  - hành vi: **Talking: phải hoạt động**; Eating, Laughing, Singing, Smoking / Vaping, dụi mắt, hắt hơi:
    "N/A", nhà sản xuất chỉ phải mô tả ảnh hưởng.
- **Không phản ứng:** tài xế không đưa mắt về đường trong 3 s sau cảnh báo mất tập trung, hoặc nhắm mắt
  ≥ 6 s.

Bản 2023, *Assessment Protocol – Safety Assist – Safe Driving* v10.2, 06/2023 [35]: cùng ba loại. Long
Distraction là ≥ 3 s vào một vị trí (thêm 1 s nếu có bằng chứng thuyết phục) (3.5.3.1.2). VATS có thêm
chi tiết bản 2026 không lặp lại: cửa sổ 30 s "is reset if the driver's glance returns to the forward
road view for a period of ≥ 2 seconds" (3.5.3.1.3). Ăn, nói, cười, hát, hút thuốc, dụi mắt, hắt hơi: chỉ
phải khai báo ảnh hưởng, "There is no performance requirement" (3.5.2.3).

**Ý nghĩa:** Euro NCAP không yêu cầu phát hiện ăn, uống, hút thuốc; chúng là nhiễu. Cái được chấm điểm
là **mắt rời đường bao lâu**, và điện thoại được định nghĩa qua **hướng nhìn lặp lại**, không qua việc
thấy vật thể.

#### NHTSA 2013, Visual-Manual Driver Distraction Guidelines [36]

78 FR 24818, 26/04/2013. Là tiêu chí **thiết kế thiết bị trong xe** (một thao tác có được phép làm khi
đang lái không), không phải ngưỡng cảnh báo của hệ thống giám sát. Mục VI.E.14 (trang 24888): với ít nhất 21 trên 24
người thử,
- không quá 15 % số lần liếc rời đường dài hơn **2,0 s**;
- thời lượng trung bình mỗi lần liếc ≤ **2,0 s**;
- tổng thời gian mắt rời đường để xong thao tác ≤ **12,0 s**.

Văn bản dẫn 100-Car làm lý do: liếc tới 2,0 s không làm tăng rủi ro có ý nghĩa thống kê, trên 2,0 s thì
có (trang 24854, chú thích 141).

#### Klauer et al. 2006 (100-Car), DOT HS 810 594 [37]

So 49 va chạm + 439 suýt va chạm (tài xế có lỗi) với 20 000 đoạn 6 s lái bình thường.

- Bảng 6.2, tổng thời gian mắt rời đường trong 6 s (5 s trước + 1 s sau lúc khởi phát): ≤ 0,5 s: OR 1,31
  (0,91–1,89); 0,5–1,0 s: 0,82; 1,0–1,5 s: 0,92; 1,5–2,0 s: 1,26 (0,89–1,79); **> 2,0 s: 2,19
  (1,72–2,78)**. Chỉ mức cuối khác 1 có ý nghĩa.
- Bảng 2.3, **liếc liên quan lái xe** (gương, quan sát giao thông qua cửa sổ): > 2 s: OR **0,45**
  (0,24–0,83); < 2 s: **0,23** (0,15–0,34). Cả hai nhỏ hơn 1 có ý nghĩa: hành vi này **giảm** rủi ro.
- Bảng 2.5, việc phụ: với lấy vật đang di chuyển 8,82; đọc 3,38; trang điểm 3,13; **bấm số điện thoại
  cầm tay 2,79 (1,60–4,87)**; ăn 1,57 (0,92–2,67); **nói / nghe điện thoại cầm tay 1,29 (0,93–1,80)**;
  uống 1,03 (0,33–3,28); chỉnh radio 0,55; **hành khách ghế bên 0,50 (0,35–0,70)**.

Lưu ý: "2 s" ở đây là **tổng trong cửa sổ 6 s**, không phải một lần liếc liên tục. Mẫu 100 xe, khoảng
tin cậy rộng.

#### Victor et al. 2015 (SHRP2 S08A)

*Không tải được báo cáo gốc.* Chỉ đọc được tóm tắt trên TRID của TRB [38]: tỉ lệ thời gian mắt rời
đường trong khoảng 3 s đến 1 s trước va chạm và thời lượng trung bình mỗi lần liếc rời đường nằm trong
các chỉ số dự báo mạnh nhất; nhắn tin làm tăng rủi ro có ý nghĩa; nói / nghe điện thoại cho thấy rủi ro
**giảm** có ý nghĩa, không có va chạm nào trong lúc nói / nghe. Không dùng số cụ thể từ nguồn này cho
tới khi đọc được báo cáo.

#### AttenD (Kircher & Ahlström, VTI)

*Không tải được tài liệu gốc*: máy chủ DiVA từ chối kết nối ngày 05/10, bản lưu trữ web trả lỗi 429
[39]. Phần xác nhận được từ tóm tắt của chính nhóm tác giả [40]: có một bộ đệm thời gian; bộ đệm vơi khi
tài xế nhìn rời đường và đầy lại khi nhìn về; bộ đệm cạn thì tài xế bị xếp là mất tập trung. *Chưa kiểm
chứng từ nguồn gốc:* dung lượng bộ đệm 2 s (mới thấy trong đoạn trích kết quả tìm kiếm), độ trễ trước khi
đầy lại, luật riêng cho gương và đồng hồ tốc độ, định nghĩa "vùng liên quan lái xe". Không đặt tham số
theo AttenD cho tới khi đọc được.

#### Bảng đối chiếu ngưỡng

| Nguồn | Một lần nhìn rời đường | Cộng dồn | Tốc độ | Phạm vi |
|---|---|---|---|---|
| EU ADDW [33] | 3,5 s (≥ 50 km/h), 6 s (≥ 20 km/h) | Không quy định | Bật từ 20 km/h | Chỉ nhìn xuống (Area 3) |
| Euro NCAP 2026 [34] | 3 đến 4 s | 10 s trong 30 s | Từ 20 km/h | Mọi hướng, tách liên quan / không liên quan lái xe |
| Euro NCAP 2023 [35] | ≥ 3 s (+1 s) | 10 s trong 30 s, xoá khi nhìn đường ≥ 2 s | — | như trên |
| NHTSA 2013 [36] | 2,0 s (tiêu chí thiết kế thao tác) | 12,0 s mỗi thao tác | — | Thiết bị trong xe |
| 100-Car [37] | — | > 2 s trong 6 s: OR 2,19 | — | Quan sát tự nhiên |
| **DriverGuard hiện tại** | **2,0 s; 1,5 s trên 80 km/h** | **Không có** | Tắt khi xe dừng | Mọi hướng theo góc đầu; cúi kèm mí hạ |

### 3.2 Tín hiệu có sẵn và giới hạn theo tài liệu MediaPipe

- **Blendshape** [41]: model MLP-Mixer nhận **146 landmark** (tập con của 478) và trả 52 hệ số trong
  [0, 1], gồm `eyeLookDown/In/Out/Up` trái và phải. Đầu vào là landmark, không phải ảnh. Vậy `eyeLook*`
  và vị trí mống mắt tính từ landmark **không phải hai tín hiệu độc lập**: landmark mống mắt sai thì cả
  hai cùng sai.
- **Độ chính xác công bố** [41]: chỉ có độ lệch tuyệt đối trung bình 0,199 (độ lệch chuẩn 0,237) theo
  nhóm giới tính và màu da, và chỉ tính các blendshape có giá trị > 0,25. **Không có số đo riêng cho
  `eyeLook*`, không có sai số theo độ.** Model card ghi "not intended for human life-critical decisions"
  và mục đích chính là giải trí AR.
- **Giới hạn của Face Mesh V2** [42]: tối ưu cho camera trước của điện thoại; không phù hợp khi mặt quay
  khỏi camera hơn 80°, nghiêng hơn 8° so với phương đứng (ở đầu vào đã cắt), thấy dưới 50 % khuôn mặt,
  hoặc mặt quá xa. Ánh sáng kém, nhiễu, chuyển động, vật che làm tăng rung.
- **Kính, hồng ngoại, mống mắt:** hai model card [41][42] và trang tài liệu Face Landmarker [43]
  **không có chữ nào** về kính, ảnh IR hay độ chính xác landmark mống mắt. Model card riêng của Iris
  không tải được (đường dẫn cũ trả lỗi). Tức là hành vi khi IR / đeo kính phải **tự đo**, không có cam
  kết nào từ Google.
- **Gói model** [43]: BlazeFace 192 × 192, FaceMesh-V2 256 × 256, Blendshape 1 × 146 × 2; file
  `face_landmarker.task` 3,76 MB (kiểm tra bằng HTTP HEAD).

### 3.3 Đánh giá từng trường hợp

"Đo trước" nghĩa là ghi biến vào trace và metadata, không vào `distraction_score`, không cảnh báo
(nguyên tắc việc 6).

| Trường hợp | Tín hiệu (đã có trừ khi ghi khác) | Nguồn báo sai dự kiến | Dữ liệu kiểm chứng | Kết luận |
|---|---|---|---|---|
| **Liếc ngắn lặp lại** (VATS) | `off_road` hiện có, cộng dồn trong cửa sổ 30 s | Quan sát gương và hai bên khi chuyển làn, vào giao lộ, lùi xe; 100-Car cho thấy đây là hành vi giảm rủi ro [37] | SUST / YawDD đã có trace (báo sai); DMD Distraction nhãn "Not looking at the road" (bắt đúng) | **Đo trước.** Ngưỡng đo: 10 s / 30 s [34], xoá khi nhìn đường ≥ 2 s [35]. Chỉ xét cảnh báo sau khi tách được hướng xuống với hướng ngang |
| **Nhìn xuống lâu, tách khỏi nhìn ngang** | pitch so với mốc; `gaze_down` | Cúi nhìn bảng đồng hồ; camera gắn thấp làm lệch pitch | DMD Gaze (`steering_wheel`, `infotainment` so với `left`, `right`, gương); 100-Driver (Looking down so với left / right) | **Đo trước**, không đổi luật. Replay hai cấu hình: ngưỡng 3 s cho mọi hướng; và 2 s cho hướng xuống + 3 s cho hướng ngang. Báo cáo báo sai / giờ và recall |
| **Mắt rời đường, đầu thẳng** (Lizard) | `eyeLookDown/In/Out` + mống mắt 468–477, cộng góc đầu | Kính phản quang, IR, mắt hẹp, cười / nheo mắt; mí hạ khi buồn ngủ làm `eyeLookDown` tăng (*chưa kiểm chứng*, đã ghi ở việc 3) | DMD Gaze; LISA Gaze v2 (IR, kính); SynDD2 Gaze (kính râm) | **Đo trước.** Thêm `eyeLook*` vào trace, chấm phân tách vùng trên từng điều kiện. Chỉ bật khi tách được `front` với `infotainment` / `steering_wheel` trên người đeo kính |
| **Điện thoại trên đùi / nhắn tin so với gọi** | Vị trí khung YOLO so với khung mặt (`phone_kind`); nhắn tin trên đùi = `gaze_down` lặp lại mà không thấy điện thoại | Tay che điện thoại ở tai; vật giống điện thoại; điện thoại của hành khách | DMD (Texting / Phone call trái, phải); 3MDAD (A5–A8); SynDD2 | `phone_kind`: **đo trước** (việc 32). Điện thoại trên đùi: **không phát hiện được bằng vật thể**, camera mặt không thấy; xử lý gián tiếp qua hai dòng trên. Không gọi đó là "phone" khi không thấy điện thoại |
| **Nhìn màn hình giải trí** | Yaw nhỏ + pitch xuống; hoặc chỉ liếc mắt | Trùng với nhìn gương phải / hành khách về yaw | DMD Gaze (`infotainment`); LISA v2 (Radio) | Không làm thành lý do riêng. Nằm trong VATS và Lizard. Cần biết vị trí màn hình theo từng xe (phần hoãn "vùng nhìn hợp lệ") |
| **Quay ra ghế sau / với tay** | Yaw lớn rồi mất mặt (việc 33) | Mất mặt vì chói, che camera; M10 đã bỏ cảnh báo `no_face` vì báo sai | DMD (Reach Backseat, Reach Side); 3MDAD A15; SynDD2 (Reaching behind, Pick up from floor) | **Đo trước**, theo đúng kế hoạch việc 33 (viết test tái hiện trước). Với lấy vật đang di chuyển có OR 8,82 trong 100-Car [37], nên đáng làm nếu replay không tăng báo sai |
| **Nói chuyện với hành khách** | MAR dao động + yaw về phía ghế phụ | Hát, nhai, ngáp, nói điện thoại rảnh tay | DMD (Talking, Talking to passenger); NTHU-DDD | **Không làm.** OR 0,50 [37]; Euro NCAP xếp Talking là điều kiện hệ thống phải chịu được [34]. Quay đầu lâu thì `off_road` đã bắt. Có ích ở chỗ khác: dùng "đang nói" để **chặn báo sai ngáp** (đã làm ở khối 7) |
| **Ăn / uống** | COCO `cup` 41, `bottle` 39, `sandwich` 48... trong vùng tài xế | Cốc trên giá để cốc, chai của hành khách; thêm một nguồn cảnh báo | DMD (Drinking), 3MDAD A13 / A14, SynDD2 | **Không làm** (giữ quyết định 02/10). OR 1,03 (uống) và 1,57 không có ý nghĩa (ăn) [37]; Euro NCAP "N/A" [34]. Phần duy nhất đáng giữ: dùng các lớp này làm **ca thử báo sai** cho `phone` |
| **Hút thuốc** | Không có lớp COCO cho thuốc lá | — | 3MDAD A16, 100-Driver | **Cần model mới, không làm.** Euro NCAP "N/A" [34]; model tìm được không có số đo trong xe [49] |
| **Tay che mặt / tay che miệng khi ngáp** | Điểm tin cậy mặt tụt, `face_reliable` sai, landmark miệng nhảy | Dụi mắt, gãi mặt, chỉnh kính: ngắn và vô hại | DMD Drowsiness (ngáp có / không che tay), DMD occlusion, SynDD2 (Hand on head) | **Đo trước**, và chỉ cho mục đích **giảm tin cậy** (không tính EAR / MAR / hướng nhìn trong lúc đó), không cảnh báo. Nhận tay bằng model là thêm tải, không cần |
| **Che camera** | Mất mặt + ảnh tối đều hoặc không đổi; khối 9 đã có `unavailable` sau 3 s | Hầm, đêm không đèn | Tự tạo bằng chuỗi số giả; DMD occlusion | **Làm được ngay phần đối chiếu:** `unavailable` 3 s đã nhanh hơn mức "báo trong 10 s" của Euro NCAP [34] và yêu cầu 3.5.1.3 của ADDW [33]. Việc còn thiếu là tách "ảnh tối đen" (che) khỏi "có ảnh nhưng không thấy mặt"; phần này trùng việc 10, không mở việc mới |

### 3.4 Model pretrained nhỏ có thể thêm

Điều kiện: có trọng số tải được, license ghi rõ, ONNX hoặc TFLite, chạy được trong WASM, đủ nhẹ để chạy
cạnh MediaPipe + YOLOv8n ở 15 FPS, và **dùng được với camera hướng mặt**.

| Model | Kích thước, đầu vào | License | Độ chính xác công bố | Tải được? | Nhận xét |
|---|---|---|---|---|---|
| MediaPipe Hand Landmarker (full) [44][45] | 7,82 MB; 192 × 192 và 224 × 224; float16 | *Chưa đọc được dòng license trong model card* | Tài liệu: 17,12 ms CPU, 12,27 ms GPU trên Pixel 6 | Có, có bản Web | Camera mặt chỉ thấy tay khi tay đưa lên mặt. Thêm ~17 ms mỗi lần chạy. **Không thêm** cho tới khi có ca dùng mà khung YOLO không giải quyết được |
| MediaPipe Gesture Recognizer | 8,37 MB | — | *Chưa đọc tài liệu* | Có | Cử chỉ tay (like, chữ V...) không liên quan mất tập trung. **Không** |
| MediaPipe Pose Landmarker (lite) | 5,78 MB | — | *Chưa đọc tài liệu* | Có | Cần thấy vai và tay; camera mặt cắt mất. **Không** |
| MobileGaze / `yakhyo/gaze-estimation`, MobileOne-S0 [46] | 4,97 MB ONNX; mặt cắt 448 × 448; 90 bin × 4° | Code MIT; train trên Gaze360 | MAE **12,58°** trên Gaze360 (MobileNetV2 9,79 MB: 13,07°; ResNet-18 45 MB: 12,84°) | Có (GitHub release) | Sai 12–13° lớn hơn khoảng cách góc giữa kính chắn gió và bảng đồng hồ. Không có số đo trong xe, IR hay kính. **Không thêm** |
| L2CS-Net [47] | ResNet-50, trọng số `.pkl` | MIT | *Chưa đọc số trong paper* | Có | ResNet-50 là model nặng, trái ràng buộc. **Không** |
| OpenVINO `gaze-estimation-adas-0002` [48] | 1,88 M tham số, 0,139 GFLOPs; hai ảnh mắt 60 × 60 + ba góc đầu | *License của file model chưa xác nhận* (README không ghi) | MAE 6,95° (độ lệch chuẩn 3,58°) trên bộ nội bộ, thử trên 2 người | Định dạng OpenVINO IR; *chưa kiểm chứng* có bản ONNX chạy được bằng onnxruntime-web | Nhẹ nhất và hợp nhất về thiết kế (tận dụng góc đầu đã có). Nhưng chỉ thử trên 2 người, không nói gì về IR / kính. **Ứng viên duy nhất đáng thử offline**, và chỉ khi `eyeLook*` trượt trên LISA v2 |
| YOLO thuốc lá `Beehzod/smoke_cigarette-detection2-yolo11m` [49] | YOLO11m, `best.pt` | Ghi MIT, nhưng model gốc Ultralytics là AGPL-3.0 | mAP50 0,994 trên bộ Roboflow 1 636 ảnh, không phải ảnh trong xe | Có (`.pt`, không có ONNX) | YOLO11**m** quá nặng; số đo không chuyển sang được cabin. **Không** |
| `koreashin/Driver_monitoring` [49] | Video Swin-T, 27,85 M tham số, đầu vào 30 frame 224 × 224 | Apache-2.0 | Accuracy 0,98 trên bộ riêng | Có ONNX | Model video nặng, dữ liệu và góc camera không rõ. **Không** |

Tìm trên Hugging Face theo "driver distraction", "distracted driver", "driver monitoring", "smoking
yolo", "phone detection yolo" (05/10): các kết quả còn lại là model cá nhân không có model card, hoặc
phân loại ảnh train trên State Farm / dữ liệu riêng. **Không model nào công bố số đo trên camera hướng
mặt.**

Kết luận mục này: không có model pretrained nào thêm được một tín hiệu mất tập trung đáng tin mà không
phải tự đo lại từ đầu. Hướng rẻ nhất vẫn là khai thác thứ MediaPipe và YOLOv8n đã xuất ra.

### 3.5 Danh sách xếp hạng

Xếp theo lợi ích trên (rủi ro báo sai + chi phí). Mỗi mục là đề xuất; làm mục nào cần thành mốc riêng
trong `docs/roadmap.md`.

| # | Hướng | Chi phí | Bằng chứng cần có trước khi được phép cảnh báo |
|---|---|---|---|
| 1 | **Đo `off_road` cộng dồn 30 s** (việc 31, giai đoạn 1) | Thấp: thuần logic, test bằng chuỗi số giả | (a) Replay SUST / YawDD: số lần vượt 10 s / 30 s trên video không mất tập trung, quy ra / giờ. (b) DMD Distraction: tỉ lệ đoạn "Not looking at the road" lặp lại được bắt. (c) Báo sai / giờ tổng không vượt mục tiêu PRD ≤ 1,0 khi bật |
| 2 | **Replay `off_road` với ngưỡng theo hướng** (không đổi mặc định) | Thấp: chỉ `seq_eval --replay --set` nếu ngưỡng đã tách được trong config; nếu chưa thì thêm hai khoá | Bảng báo sai / giờ và recall cho: 2 s mọi hướng (hiện tại); 3 s mọi hướng; 2 s hướng xuống + 3 s hướng ngang. Chỉ đổi mặc định khi báo sai giảm mà recall hướng xuống trên DMD không giảm |
| 3 | **Ghi `eyeLook*` + độ lệch mống mắt vào trace** (việc 4, giai đoạn đo) | Thấp ở phần ghi; trung bình ở phần loader DMD Gaze / LISA v2 | Độ phân tách `front` với `infotainment` / `steering_wheel` / `Speedometer` / `Radio`, báo riêng cho: RGB không kính, RGB có kính, IR không kính, IR có kính. Không bật nếu bất kỳ điều kiện nào không tách được; khi đó phải có luật tự tắt theo điều kiện |
| 4 | **`phone_kind`** (việc 32), chỉ ghi ra | Thấp đến trung bình (sửa schema backend) | Ma trận nhầm lẫn gọi / nhắn tin trên DMD camera mặt và 3MDAD A5–A8. Trước đó phải có recall của `phone` trên camera mặt (hiện chưa có số nào đúng góc) |
| 5 | **Quay đi rồi mất mặt** (việc 33) | Trung bình; đụng khối 8, 9, 12 | Test tái hiện trước. Replay SUST / YawDD trước và sau: báo sai / giờ không tăng. DMD Reach Backseat: có cảnh báo trong lúc quay đi |
| 6 | **Giảm tin cậy khi tay che mặt** | Trung bình | Số lần EAR / MAR / ngáp sai trong đoạn có nhãn che mặt của DMD giảm, không làm mất sự kiện thật |
| — | Thử `gaze-estimation-adas-0002` offline | Trung bình đến cao | Chỉ mở khi mục 3 trượt. Phải thắng `eyeLook*` trên cùng bộ đo, và đo được thời gian trong onnxruntime-web |
| ✗ | Ăn / uống, hút thuốc, nói chuyện, Hand / Pose, model gaze lớn | — | Không làm (lý do ở 3.3, 3.4) |

Điểm chung: **chưa có số recall nào của khối 8 đo trên camera hướng mặt**. Vì vậy việc có giá trị nhất
không phải luật mới mà là loader cho DMD Distraction; mọi dòng trong bảng trên đều cần nó.

---

<a id="chua-kiem-chung"></a>

## 4. Chưa kiểm chứng / câu hỏi còn mở

**Dataset:**
- DMD: có form đăng ký không; dung lượng ba gói; cả ba gói có đủ video camera mặt không; số giờ còn lại
  sau khi cắt còn 14 người; bộ Gaze quay lúc xe chạy hay đứng yên. (Trang tải là ứng dụng JavaScript.)
- 3MDAD: xe có lăn bánh không; nhãn theo chuỗi là suy từ tên file; kích thước mặt trong khung Kinect
  trên taplo; có tải riêng từng phần trên Kaggle được không. Paper gốc (Signal Processing: Image
  Communication 2020) sau tường phí, chưa đọc.
- LISA Gaze v2: license dữ liệu; xe chạy hay đỗ; ảnh cả khung hay đã cắt; dung lượng.
- SynDD2: số người; license bản 2024 (mới đọc bản 2022); dung lượng; góc Dashboard có chính diện không.
- 100-Driver: Cam2 "front" đặt ở đâu chính xác (chưa xem hình 4); xe có chạy không. Bảng II trong paper
  đánh số lỗi (hai dòng số 3, thiếu số 11) nên chỉ chép tên lớp.
- DGW: vị trí gắn camera; license; dung lượng.
- MDM (UT Dallas): có phát hành công khai không.
- Drive&Act: góc "face view" ứng với camera nào trong danh sách trên trang chính; dung lượng.
- Gaze360, MPIIFaceGaze, Columbia Gaze: chưa mở trang gốc.
- SHRP2: điều kiện "secure data enclave" cho video mặt mới thấy qua kết quả tìm kiếm trên trang TRB.

**Quy định và nghiên cứu:**
- AttenD: mọi tham số (bộ đệm 2 s, độ trễ, luật gương / đồng hồ). Đã thử `diva-portal.org`,
  `vti.diva-portal.org`, `liu.diva-portal.org` (từ chối kết nối), web.archive.org (429), IEEE / ACM
  (403).
- Victor et al. 2015: chỉ có tóm tắt TRID. Đã thử `onlinepubs.trb.org` (chuyển hướng về trang giới
  thiệu), nationalacademies.org (không có nội dung).
- EUR-Lex chặn truy cập tự động; văn bản 2023/2590 đọc từ máy chủ CELLAR của Publications Office (bản
  Formex XML tiếng Anh của Công báo). Hình vẽ ba vùng nhìn không đọc được, chỉ có phần chữ.
- Euro NCAP 2026: đọc bản v1.1 (10/2025). Tiêu chí chi tiết cho từng mức điểm nằm ở Technical Bulletin
  SD-201 / SD-202, chưa đọc.

**MediaPipe và model:**
- `eyeLookDown` có tăng khi mắt nhắm / mí hạ không (đã ghi ở việc 3): tài liệu không nói.
- Hành vi blendshape và mống mắt với ảnh IR và kính: tài liệu không nói.
- Model card Iris: đường dẫn cũ không còn.
- `gaze-estimation-adas-0002`: license file model, có bản ONNX không, tốc độ trong WASM.
- Model card Hand Tracking: chưa đọc được dòng license.

**Câu hỏi cho người quyết định:**
1. Có giữ ngưỡng 2 s cho mọi hướng không, khi EU đặt 3,5 s và Euro NCAP 3 đến 4 s? Giữ thì nhạy hơn
   nhưng báo sai hơn; cần số ở mục 2 của bảng 3.5 để quyết.
2. Nhìn gương quá lâu có tính là mất tập trung không? Euro NCAP có (sau 3 đến 4 s), ADDW không, 100-Car
   cho thấy nhìn gương giảm rủi ro.
3. Mốc tiếp theo là loader DMD Distraction (mở khoá mọi phép đo) hay việc 31 giai đoạn 1 (làm được ngay
   với trace đã có, nhưng chỉ đo được phía báo sai)?

---

<a id="nguon"></a>

## 5. Nguồn

Truy cập 05/10/2026.

1. DMD, trang chính. https://dmd.vicomtech.org/
2. DMD, README trên GitHub (thông báo "Dataset Revision (2026)").
   https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset
3. DMD wiki, tiêu chí gán nhãn mất tập trung.
   https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-distraction-related-action-annotation-criteria
4. DMD wiki, tiêu chí gán nhãn hướng nhìn.
   https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-gaze-related-action-annotation-criteria
5. Ortega et al. DMD: A Large-Scale Multi-Modal Driver Monitoring Dataset for Attention and Alertness
   Analysis. ECCV Workshops 2020. https://arxiv.org/pdf/2008.12085
6. 100-Driver, trang chính. https://100-driver.github.io/
7. Wang et al. 100-Driver: A Large-scale, Diverse Dataset for Distracted Driver Classification. IEEE
   T-ITS 2023. https://100-driver.github.io/img/TITS_100_Driver.pdf
8. 100-Driver, form license. https://100-driver.github.io/img/100_Driver_Licensing.pdf
9. Rahman et al. Synthetic Distracted Driving (SynDD2) dataset for analyzing distracted behaviors and
   various gaze zones of a driver. https://arxiv.org/pdf/2204.08096
10. AI City Challenge 2024, trang tải Track 3. https://www.aicitychallenge.org/2024-track3-download/
11. AI City Challenge, Dataset License Agreement (bản 2022).
    http://www.aicitychallenge.org/wp-content/uploads/2022/02/Dataset-License-AIC2022.pdf
12. Drive&Act, trang chính. https://driveandact.com/
13. Martin et al. Drive&Act: A Multi-modal Dataset for Fine-grained Driver Behavior Recognition in
    Autonomous Vehicles. ICCV 2019.
    https://openaccess.thecvf.com/content_ICCV_2019/papers/Martin_DriveAct_A_Multi-Modal_Dataset_for_Fine-Grained_Driver_Behavior_Recognition_in_ICCV_2019_paper.pdf
14. Köpüklü et al. Driver Anomaly Detection: A Dataset and Contrastive Learning Approach. WACV 2021.
    https://arxiv.org/pdf/2009.14660
15. DAD, trang chính (TUM). https://www.ce.cit.tum.de/mmk/dad/
16. DAD, repo. https://github.com/okankop/Driver-Anomaly-Detection (không có file license)
17. Eraqi et al. Driver Distraction Identification with an Ensemble of Convolutional Neural Networks
    (AUC Distracted Driver). https://arxiv.org/pdf/1901.09097
18. 3MDAD, trang của tác giả. https://sites.google.com/site/benkhalifaanouar1/6-datasets
19. 3MDAD trên Kaggle (mô tả, license, dung lượng qua Kaggle API).
    https://www.kaggle.com/datasets/anouarbenkhalifa/3mdad-multimodal-driver-action-distraction
20. Köpüklü et al. DriverMHG: A Multi-Modal Dataset for Dynamic Recognition of Driver Micro Hand
    Gestures. https://arxiv.org/pdf/2003.00951
21. Driver Gaze in the Wild, repo. https://github.com/i-am-shreya/Driver-Gaze-in-the-Wild-
22. Ghosh et al. Speak2Label: Using Domain Knowledge for Creating a Large Scale Driver Gaze Zone
    Estimation Dataset. ICCV Workshops 2021. https://arxiv.org/pdf/2004.05973
23. GPCycleGAN, repo (đường dẫn LISA Gaze v0 / v1 / v2; code MIT). https://github.com/arangesh/GPCycleGAN
24. Rangesh, Zhang, Trivedi. Gaze Preserving CycleGANs for Eyeglass Removal & Persistent Gaze
    Estimation (README của repo gọi bản trước là "Driver Gaze Estimation in the Real World: Overcoming
    the Eyeglass Challenge"). https://arxiv.org/pdf/2002.02077
25. IVGaze, repo và `DATASET.md` (code Apache-2.0). https://github.com/yihuacheng/IVGaze
26. Look Both Ways, repo. https://github.com/Kasai2020/look_both_ways
27. DGAZE, trang CVIT IIIT Hyderabad. https://cvit.iiit.ac.in/research/projects/cvit-projects/dgaze
28. Fang et al. DADA-2000. https://arxiv.org/pdf/1904.12634
29. Xia et al. Predicting Driver Attention in Critical Situations (BDD-A). https://arxiv.org/pdf/1711.06406
30. ETH-XGaze, trang chính. https://ait.ethz.ch/xgaze
31. Jha et al. The Multimodal Driver Monitoring Database: A Naturalistic Corpus to Study Driver
    Attention. https://arxiv.org/pdf/2101.04639
32. SHRP2 NDS InSight, điều khoản truy cập. https://insight.shrp2nds.us/terms
33. Commission Delegated Regulation (EU) 2023/2590, 13/07/2023, OJ L 2023/2590, 22/11/2023. ELI:
    http://data.europa.eu/eli/reg_del/2023/2590/oj (EUR-Lex chặn truy cập tự động). Bản đã đọc:
    http://publications.europa.eu/resource/celex/32023R2590
34. Euro NCAP. Safe Driving – Driver Engagement Protocol, v1.1, 10/2025 (áp dụng 2026).
    https://cdn.euroncap.com/cars/assets/euro_ncap_protocol_safe_driving_driver_engagement_v11_a30e874152.pdf
35. Euro NCAP. Assessment Protocol – Safety Assist – Safe Driving, v10.2, 06/2023.
    https://cdn.euroncap.com/cars/assets/euro_ncap_assessment_protocol_sa_safe_driving_v102_f7f2eaaa04.pdf
36. NHTSA. Visual-Manual NHTSA Driver Distraction Guidelines for In-Vehicle Electronic Devices. 78 FR
    24818, 26/04/2013. https://www.govinfo.gov/content/pkg/FR-2013-04-26/pdf/2013-09883.pdf
37. Klauer, Dingus, Neale, Sudweeks, Ramsey. The Impact of Driver Inattention on Near-Crash/Crash Risk:
    An Analysis Using the 100-Car Naturalistic Driving Study Data. DOT HS 810 594, 04/2006.
    https://vtechworks.lib.vt.edu/items/0d2fb484-ddf4-4e63-82b2-7110afc984a9 (bản trên nhtsa.gov trả 403)
38. Victor et al. Analysis of Naturalistic Driving Study Data: Safer Glances, Driver Inattention, and
    Crash Risk. SHRP 2 Report S2-S08A-RW-1, 2015. **Chỉ đọc tóm tắt:** https://trid.trb.org/View/1323585
39. Kircher, Ahlström. Issues related to the driver distraction detection algorithm AttenD. VTI (năm
    xuất bản chưa kiểm chứng).
    https://www.diva-portal.org/smash/get/diva2:817352/FULLTEXT01.pdf (**không truy cập được 05/10**)
40. Ahlström, Georgoulas, Kircher. Towards a Context-Dependent Multi-Buffer Driver Distraction Detection
    Algorithm. IEEE T-ITS 23(5), 2022. https://doi.org/10.1109/TITS.2021.3060168. **Chỉ đọc tóm tắt** tại
    https://www.saferresearch.com/library/towards-context-dependent-multi-buffer-driver-distraction-detection-algorithm
41. Google. Model Card: MediaPipe Blendshape V2 (11/11/2022).
    https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf
42. Google. Model Card: MediaPipe Face Mesh V2 (15/09/2022).
    https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf
43. MediaPipe Face Landmarker, tài liệu.
    https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
44. MediaPipe Hand Landmarker, tài liệu.
    https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
45. Google. Model Card: Hand Tracking (Lite / Full).
    https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20(Lite_Full)%20with%20Fairness%20Oct%202021.pdf
    Dung lượng các file `.task` lấy bằng HTTP HEAD tại `storage.googleapis.com/mediapipe-models/`.
46. `yakhyo/gaze-estimation` (MobileGaze), README và release `weights`.
    https://github.com/yakhyo/gaze-estimation
47. L2CS-Net, repo. https://github.com/Ahmednull/L2CS-Net
48. OpenVINO Open Model Zoo, `gaze-estimation-adas-0002`.
    https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/intel/gaze-estimation-adas-0002/README.md
49. Hugging Face, model card: https://huggingface.co/Beehzod/smoke_cigarette-detection2-yolo11m ;
    https://huggingface.co/koreashin/Driver_monitoring ; kết quả tìm qua `huggingface.co/api/models`.
