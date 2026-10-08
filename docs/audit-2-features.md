# Audit 2: khối 6–8 (feature extractor, nhánh buồn ngủ, nhánh mất tập trung, đăng ký tài xế)

Ngày 08/10/2026, trên working tree của nhánh `DAQuan` (có thay đổi chưa commit). Chỉ đọc và phân tích: không sửa
code, config hay `eval/results`. Phạm vi: `edge_agent/perception/features.py`, `geometry.py`, `enrollment.py`,
`edge_agent/analysis/drowsiness/`, `edge_agent/analysis/distraction.py`, test và mục YAML tương ứng. Khối ngoài phạm
vi chỉ xét dataclass giao tiếp và chỗ nối (`decision/pipeline.py`, luật `unavailable` của khối 9, `phone_near_face`
của khối 4).

Cách kiểm:

- Đọc code và test; chạy 351 test của 13 file liên quan (đều pass).
- Chuỗi số giả 30 FPS đưa thẳng vào `DrowsinessAnalyzer`, `DistractionAnalyzer`, `DecisionPipeline` với
  `config/thresholds.yaml` hiện tại. Gọi là "thử trong audit"; script đặt ngoài repo.
- Chạy lại khối 7–12 trên trace có sẵn (chỉ đọc): FL3D, SUST, bản tự ghi, 47 video buồn ngủ của UTA-RLDD.
- Mọi số đo thời gian là trên máy Mac dev.

Quy ước: "mốc" là baseline của tài xế; "lần mốc" là tỉ lệ so với mốc mắt mở (EAR 0,6 lần mốc = `0.6 × ear_open_baseline`).

## 1. Tóm tắt

1. Không có phát hiện Critical. Công thức của 12 biến đều đúng với định nghĩa ghi trong code; cửa sổ tính theo giây thật (trừ `phone_ratio_2s` và tỉ lệ "nhắm sâu", tính theo số frame); mất mặt không bị độn số 0; bộ đệm đều bị chặn; chưa đăng ký không gây lỗi.
2. **High, im lặng:** mặt lọt một phần ra ngoài khung (`face_reliable` False) kéo dài thì khối 7 và 8 không đo gì, nhưng không thành "tạm ngưng giám sát" và không có cảnh báo; thử 60 s, trong đó nhắm mắt 40 s: mức 0.
3. **High, bỏ sót L3:** mắt díp (dưới 0,65 lần mốc, chưa nhắm sâu) rồi mới nhắm hẳn thì luật L3 trễ đúng bằng thời gian díp, hoặc không bật. UTA-RLDD: 3 trong 174 lần nhắm sâu từ 1,5 s trở lên không ra L3 vì lý do này, thêm 5 lần vì mặt nạ ngáp / nói.
4. **Medium:** hiệu chuẩn 5 s đầu khi chưa đăng ký có thể kẹt ở tư thế sai và giữ L2 suốt chuyến; mốc tư thế đầu của khối 7 học cả lúc xe dừng và thay mốc đã đăng ký sau 5 s; luật "mắt nhắm" của gục đầu dùng EAR thô nên cúi nhìn ngắn dễ thành `nod`; một lần ngáp bị đếm hai nếu mất mặt giữa chừng.
5. Low: `blink_rate` chia cho thời gian đồng hồ chứ không phải thời gian thấy mắt, `phone_ratio_2s` không cần số mẫu tối thiểu, vài số magic và mặc định lệch YAML, `docs/risk_engine_spec.md` lệch code ở bốn chỗ, và một số ca chưa có test.

## 2. Bảng ràng buộc

| Ràng buộc (CLAUDE.md) | Kết luận | Bằng chứng |
|---|---|---|
| Xử lý on-device | Đạt | Khối 6–8 và đăng ký là hàm thuần trên số, không có I/O hay mạng (grep `open(`, `imwrite`, `pickle`, `.write(` trong phạm vi: 0 kết quả) |
| Không ghi / giữ frame | Đạt | `FrameFeatures` không có trường ảnh (`edge_agent/perception/features.py:76-112`). Đăng ký giữ danh sách `FrameFeatures` (số, gồm chữ ký mặt) trong RAM của một bước rồi xoá (`enrollment.py:146-152`, `216`); `test_no_frame_writes.py` pass |
| Chỉ gửi metadata | Đạt | Hồ sơ đăng ký không rời thiết bị: backend chỉ nhận thời lượng và số lần làm lại (`edge_agent/io/publisher.py:203`) |
| ≥ 15 FPS | Đạt trên Mac; Không chắc trên thiết bị đích | Khối 6: 0,04 ms; khối 7–12: 0,01 ms (`eval/results/benchmark.md:22-24`). Thử trong audit, 2 giờ ở 30 FPS: trung bình 0,38 ms mỗi frame kể cả code sinh số giả, chậm nhất 2,3 ms. Bản web chạy cùng code qua Pyodide, chậm hơn nhiều lần: không đo trong audit |
| Không model nặng trong vòng lặp | Đạt | Khối 6–8 không gọi model nào |
| Chỉ pretrained | Đạt | Không có code học tham số; mốc của tài xế là trung vị / phân vị trong RAM |
| Ngưỡng nằm hết trong `thresholds.yaml` | Vi phạm một phần | Xem L5 |
| Mỗi khối một module, giao tiếp qua dataclass | Đạt | `FrameFeatures` → `DrowsinessState`, `DistractionState`, `EnrollmentState`. Khối 8 nhận thêm hai cờ của khối 7 (`gaze_down`, `deep_closed`, `decision/pipeline.py:189-191`) |
| Logic thời gian test bằng chuỗi giả | Đạt, còn thiếu ca | 351 test pass, không test nào cần video. Ca thiếu: L6 |
| Bộ đệm bị chặn khi chạy nhiều giờ | Đạt | Sau 2 giờ giả lập: mốc mắt 3601 mẫu, tư thế 1726, PERCLOS 1801, liếc 901, điện thoại 61, chớp 15; bộ nhớ theo dõi 2,45 MB ở phút 10 và 3,82 MB ở giờ 2 (phần tăng không nằm ở khối 7, 8). `_dip_track` của gục đầu không có trần cứng, xem L3 |
| Ưu tiên chống báo sai | Đạt một phần | Nhiều luật chống báo sai có số đo đứng sau; các ca còn hở ở mục 4.5 |
| Comment và tên biến tiếng Anh | Đạt | Các file trong phạm vi |

## 3. Bảng từng biến

"Giây thật" nghĩa là tính trên `timestamp` của frame (giờ chụp, `time.monotonic()` ở thiết bị, giờ chụp của trình duyệt
ở bản web), không phụ thuộc FPS.

| Biến | Công thức thực tế | Cửa sổ | Khi mất mặt | Nhận xét |
|---|---|---|---|---|
| `ear` | `(‖p2−p6‖ + ‖p3−p5‖) / (2‖p1−p4‖)` trên toạ độ 2D, trung bình hai mắt; chỉ số MediaPipe đúng cặp mí trên / mí dưới (`features.py:36-37`, `145-150`) | Từng frame | `None` | Đúng. Mắt suy biến (rộng < 1e-6) trả 0,0 chứ không phải `None`, tức đọc là "nhắm" (`:148-149`). 2D nên co theo góc cúi; khối 7 bỏ qua khi cúi quá 25° hoặc quay quá 35° so với mốc tư thế |
| `mar` | Trung bình ba khe dọc môi trong / khoảng cách hai khoé miệng (`features.py:39-40`, `153-158`) | Từng frame | `None` | Đúng. Không được chặn theo góc đầu: quay ngang làm khoé miệng co lại, MAR tăng theo `1 / cos(yaw)`. Thử trong audit: 0,37 ở chính diện thành 0,452 ở 35° (ngưỡng ngáp 0,45), xem M4 |
| `pitch` / `yaw` / `roll` | `solvePnP` lặp trên 10 điểm cứng của mặt, tiêu cự = bề rộng ảnh, rồi `RQDecomp3x3`; yaw đổi dấu (`features.py:46-61`, `166-174`, `195-216`) | Từng frame, lấy tư thế frame trước làm điểm xuất phát | `None`, bỏ điểm xuất phát | Góc so với camera, không làm mượt. Hai khối trừ hai mốc khác nhau: khối 7 dùng trung vị trượt 60 s, khối 8 dùng trung bình mũ 30 s có kẹp. Cùng một frame có thể "cúi" ở khối này mà không ở khối kia, xem M2 |
| `eye_closed` | Trễ hai ngưỡng: nhắm khi EAR < 0,65 lần mốc, mở lại khi > 0,75 lần mốc. Mốc = phân vị 90 của EAR trong 120 s, kẹp 0,18–0,42; đã đăng ký thì kẹp trong 0,90–1,25 lần EAR đăng ký (`eyes.py:80-91`, `137-143`, `analyzer.py:103-133`) | Trạng thái; mốc 120 s giây thật | `None` (cả khi mặt lọt một phần, tư thế không biết, đầu quay / cúi quá ngưỡng) | Đúng. Cờ trễ không được đặt lại khi mất mặt hay khi hết đợt nhắm (`eyes.py:145-151` không đụng `_eye_closed`): mặt trở lại với EAR 0,65–0,75 lần mốc thì tiếp tục "nhắm" theo trạng thái cũ. Chưa đăng ký: mắt díp đều 2 phút thì mốc tụt theo (thử: 0,30 → 0,18), PERCLOS về 0; đây là lý do đã ghi của việc kẹp theo đăng ký |
| `phone_near_face` | Tâm của một hộp "cell phone" (điểm ≥ 0,35) nằm trong hộp mặt nới ±1,0 bề rộng, lên 0,5 và xuống 1,5 chiều cao (`phone_detector.py:104-127`) | Từng frame, dùng kết quả YOLO mới nhất (tuổi ≤ 0,6 s) | Hộp mặt được nhớ 3 s; sau đó trả `False`, không phải `None` | Chỉ xét 2D, không xét kích thước hay độ sâu. Không có hộp mặt thì "không có điện thoại" được tính như một mẫu âm, xem L2 |
| `closed_duration` | `t − _count_since`, chỉ khác 0 khi số frame "nhắm sâu" ≥ 50 % số frame mắt của phần đang đếm (`eyes.py:200-214`) | Một đợt nhắm; giây thật, nhưng tỉ lệ 50 % tính theo số frame | Hở ≤ 0,5 s: đếm tiếp. Lâu hơn: về 0. Gục đầu sau khi đã nhắm sâu ≥ 0,5 s: đếm tiếp không giới hạn | Đếm từ frame nhắm đầu tiên, nên chậm tối đa một frame (67 ms ở 15 FPS). Tỉ lệ 50 % tính trên cả đợt gây H2. Đếm khi gục không có trần, xem L3 |
| `perclos_60s` | `Σ dt(nhắm) / Σ dt(biết mắt)`; `dt = min(khoảng cách frame, 0,5 s)`; frame "nhắm" xét riêng từng frame: EAR < 0,65 lần mốc (`eyes.py:240-259`, `analyzer.py:168-174`) | 60 s giây thật theo giờ của mẫu | Giữ: frame không biết mắt không thêm mẫu, không tính là mở hay nhắm; mẫu cũ rời cửa sổ theo giờ. Dưới 30 s dữ liệu thì không dùng | Đúng với định nghĩa trong YAML (gần "P50", không phải P80, đã ghi ở `thresholds.yaml:291-304`). Tổng chạy sau 2 giờ khớp với tổng tính lại tới 9 chữ số |
| `blink_rate` | Số đợt nhắm ≤ 0,5 s kết thúc trong 60 s gần nhất / `max(min(t − start_t, 60), 10)` × 60 (`eyes.py:187-189`, `216-221`) | 60 s giây thật | Giữ số đã đếm; mẫu số vẫn là thời gian đồng hồ | Mẫu số không phải thời gian thấy mắt, và `start_t` không bao giờ đặt lại, xem L1. Ở 15 FPS một lần chớp chỉ có 1–2 frame; lần chớp ngắn hơn một frame bị sót |
| `yawn_count_10min` | Sự kiện `yawn` khi MAR > ngưỡng mở (0,45; đã đăng ký: MAR miệng khép + 0,40) liên tục 1,5 s, tính tới khi MAR < ngưỡng khép (`mouth.py:96-119`) | 600 s giây thật | Giữ số đã đếm. Hở > 0,5 s thì bỏ lần há miệng đang chạy | Chặn trùng bằng cờ `_fired`: một lần há miệng một sự kiện. Mất mặt giữa lần ngáp xoá cờ nên đếm hai, xem M4. Không có trần thời lượng |
| `nod_count_5min` | Sự kiện `nod` khi góc cúi so với mốc vượt 15° rồi về dưới 7° trong 0,2–2,0 s, và mắt "nhắm" ≥ 30 % thời gian của cú cúi (`head.py:93-150`) | 300 s giây thật | Giữ số đã đếm. Mất tư thế > 0,5 s thì bỏ cú cúi đang chạy | Chặn trùng tốt: phải về dưới 7° mới bắt đầu cú mới. "Mắt nhắm" ở đây là EAR thô, không qua kiểm tư thế, xem M3 |
| `off_road_duration` | `t − _off_road_since`; về lại đường phải giữ 0,3 s mới xoá (`distraction.py:352-366`) | Liên tục, giây thật | Giữ trạng thái trước (đang lệch thì tiếp tục đếm); xe dừng thì về 0 | Mất mặt quá 3 s thì khối 9 chuyển sang "tạm ngưng". Mặt lọt một phần thì giữ trạng thái vô thời hạn, xem H1 |
| `phone_ratio_2s` | Số mẫu có điện thoại / số mẫu biết kết quả trong 2 s (`distraction.py:286-293`) | 2 s giây thật, nhưng tỉ lệ theo **số frame** | Không liên quan tới mặt; mẫu `None` không vào cửa sổ; cửa sổ rỗng = 0 | Không cần số mẫu tối thiểu, xem L2 |
| Mốc cá nhân (đăng ký) | EAR mở, MAR khép, mốc mày: trung vị bước 1; tư thế đường và mống mắt: bước 2; EAR nhắm và `eyeBlink` nhắm: bước 3 (`enrollment.py:267-304`) | Từng bước, chỉ đếm frame tốt, giây thật | Đồng hồ của bước dừng lại | Áp đúng cho khối 7 và 8 (`pipeline.py:146-157`). Chưa đăng ký: mọi mốc tự học, không có đường lỗi nào (test với `enabled: false` và các lần thử trong audit). Hạn chế: M2, L4 |

## 4. Phát hiện

Mỗi mục: vấn đề, bằng chứng, hậu quả, đề xuất, công sức (S dưới nửa ngày, M một đến hai ngày, L hơn), tác động tới FPS
và báo sai. "Trùng" nghĩa là `docs/improvements.md`, `docs/safety-fmea.md` hoặc `docs/audit-1-perception.md` đã có;
khi đó chỉ ghi phần bổ sung.

### 4.1 Critical

Không có.

### 4.2 High

#### H1. Mặt lọt một phần ra ngoài khung kéo dài: không đo, không "tạm ngưng", không cảnh báo

- **Vấn đề:** frame có `face_found` True nhưng `face_reliable` False (dưới 90 % landmark nằm trong ảnh) được khối 7 xử
  lý như mất mặt (`analyzer.py:97`) và khối 8 giữ trạng thái trước (`distraction.py:329-346`). Nhưng thời gian mất mặt
  chỉ chạy khi `face_found` False (`distraction.py:347-350`), và khối 9 chỉ coi mặt "không đọc được" với ba lý do
  `low_light`, `glare`, `blur` (`quality.py:39-40`, `risk_engine.py:229-234`). Lý do `bad_angle` của đúng ca này
  (`quality.py:118-119`) không được tính giờ ở đâu cả.
- **Bằng chứng (thử trong audit):**
  - Xe chạy 60 km/h, mặt lọt một phần 60 s, trong đó mắt nhắm 40 s: 0 frame `unavailable`, mức cao nhất 0,
    `quality.issue` = `bad_angle`, `no_face_duration` = 0.
  - Liếc 35° trong 0,5 s rồi mặt lọt một phần 9,5 s: cảnh báo L2 `off_road` ở giây 2,5 dù không còn đo được gì.
  - `test_partial_face_holds_state_and_is_not_no_face` (`tests/test_edge_agent/test_distraction.py:189-199`) khẳng định
    hành vi giữ trạng thái; không test nào xét ca kéo dài.
  - HUD nhận `quality.issue` (`edge_agent/hud/server.py:126`) nhưng `frontend/src/hud/` không đọc trường đó; chữ
    "camera lệch" chỉ hiện khi đã `unavailable`.
- **Hậu quả:** tài xế ngồi lệch, ngả người, hoặc camera chĩa lệch làm mặt bị cắt ở mép ảnh thì hệ thống im lặng không
  giới hạn và backend vẫn thấy "đang giám sát". Chiều ngược lại: trạng thái "đang lệch" bị giữ thành cảnh báo L2 sai.
- **Không chắc:** ca này xảy ra thường xuyên tới đâu. Bản tự ghi có 99,5–100 % frame đạt `reliable` (audit 1, L2), nhưng
  đó là laptop đặt chính diện; camera trên màn hình xe nằm lệch sang phải tài xế. Kiểm chứng: một phiên tự ghi ngồi
  lệch, đếm tỉ lệ `face_conf < 0.9`.
- **Đề xuất:** tính giờ `bad_angle` như ba lý do kia (thành "tạm ngưng" sau `risk.unavailable.low_quality_s`), và giới
  hạn thời gian khối 8 giữ trạng thái "đang lệch" khi không còn tư thế (ngưỡng mới trong `distraction`). Việc đếm khi
  gục đầu (`head_drop`) cần giữ nguyên.
- **Công sức:** S. **Tác động:** FPS không đổi. Báo sai `off_road` giảm; số lần "tạm ngưng" tăng.
- **Trùng:** FMEA dòng 7 liệt kê `bad_angle` như một lý do tạm ngưng (`docs/safety-fmea.md:191`). Trên code, lý do này
  chỉ xuất hiện trong giây đầu sau khi mặt biến mất hẳn; phần mặt còn thấy một phần thì không được phủ.

#### H2. Mắt díp rồi mới nhắm hẳn: L3 trễ bằng thời gian díp, hoặc không bật

- **Vấn đề:** `closed_duration` chỉ khác 0 khi số frame nhắm sâu đạt 50 % số frame của **cả đợt nhắm** tính từ lúc EAR
  xuống dưới 0,65 lần mốc (`eyes.py:203-210`). Cờ trễ giữ đợt nhắm cho tới khi EAR vượt 0,75 lần mốc, nên giai đoạn mắt
  díp (0,5–0,75 lần mốc) nằm trong cùng đợt và làm loãng tỉ lệ. Luật này sinh ra để chặn mắt nheo (YawDD) và làm đúng
  việc đó; mặt trái là kiểu ngủ gật điển hình, mí sụp dần rồi nhắm.
- **Bằng chứng:**
  - Thử trong audit, EAR 0,6 lần mốc trong N giây rồi 0,3 lần mốc: luật L3 (1,5 s) bật sau khi mắt nhắm hẳn 1,50 s
    (N = 0), 1,97 s (N = 2), 3,97 s (N = 4), 9,97 s (N = 10).
  - Trace thật, đếm các chuỗi frame liên tiếp mà chính khối 7 gọi là nhắm sâu, dài từ 1,5 s:

    | Bộ | Thời lượng | Chuỗi ≥ 1,5 s | L3 đúng lúc | Trễ hoặc không bật | Do díp trước | Do mặt nạ ngáp / nói | Khác |
    |---|---:|---:|---:|---:|---:|---:|---:|
    | UTA-RLDD, 47 video buồn ngủ | 8,2 giờ | 174 | 163 | 11 | 4 | 5 | 2 |
    | FL3D | 0,8 giờ | 34 | 34 | 0 | 0 | 0 | 0 |
    | SUST | 5,7 giờ | 7 | 7 | 0 | 0 | 0 | 0 |
    | Bản tự ghi | 1,2 giờ | 75 | 73 | 2 | 0 | 2 | 0 |

    Bốn chuỗi "do díp trước" của UTA-RLDD: người 41 nhắm sâu 5,7 s sau 13 s díp, không có L3; người 18 hai chuỗi 1,75 s
    và 4,25 s sau 3,25 s và 1,75 s díp, không có L3; người 35 trễ 0,6 s.
  - Test hiện có chỉ xét díp 0,6 s (`test_deep_closure_after_narrowing_counts_from_its_start`,
    `tests/test_edge_agent/test_drowsiness.py:532-539`).
- **Hậu quả:** bỏ sót hoặc trễ còi L3 đúng ở người buồn ngủ thật: 3 trong 174 lần (1,7 %) trên UTA-RLDD, ở 2 trong
  47 người. Dữ liệu diễn (FL3D, bản tự ghi) không có kiểu này nên các bảng recall hiện tại không thấy.
- **Đề xuất:** xét tỉ lệ nhắm sâu trên một cửa sổ gần (ví dụ `risk.microsleep_l3_s` cuối) thay cho cả đợt, hoặc bắt
  đầu đếm lại từ frame đầu của chuỗi nhắm sâu đang chạy khi tỉ lệ cả đợt không đạt. Sau đó phải chạy lại YawDD, NITYMED
  và phiên nhìn xuống của bản tự ghi, vì luật hiện tại đang giữ các ca đó.
- **Công sức:** M (code S, đo lại M).
- **Tác động:** FPS không đổi. Báo sai L3 có thể tăng ở mắt nheo và nhìn xuống (hiện 7 / 30 ở bản tự ghi); chưa đo.
- **Bổ sung về mặt nạ ngáp / nói:** 5 chuỗi của UTA-RLDD và 2 của bản tự ghi không ra L3 vì đang bị che. Đây là thiết
  kế đã biết (`thresholds.yaml:274-290`); số đếm trên dữ liệu buồn ngủ thật là phần mới. Ngủ há miệng: mặt nạ giữ tối
  đa 8 s + 1,5 s, nên L3 sớm nhất khoảng 11 s sau khi hàm trễ xuống.
- **Trùng:** không. Việc 5 của improvements xử lý chiều ngược lại (nhìn xuống bị báo L3).

### 4.3 Medium

#### M1. Hiệu chuẩn 5 s đầu kẹt ở tư thế sai, và không có đường hiệu chuẩn lại

- **Vấn đề:** khi chưa đăng ký, mốc "nhìn đường" của khối 8 là trung vị tư thế trong 5 s đầu xe chạy
  (`distraction.py:234-246`). Sau đó mốc chỉ học từ frame "đang nhìn đường" và bị kẹp ±20° quanh tư thế đã hiệu chuẩn
  (`:223-232`, `:341-342`). Nếu trung vị sai quá 30° thì mọi frame nhìn đường đều là "lệch", mốc không bao giờ được học
  lại.
- **Bằng chứng (thử trong audit):**
  - Nhìn sang bên 40° trong 6 s đầu rồi nhìn thẳng 10 phút: `baseline_yaw` giữ 40,0; mức 2 ở 100 % số frame;
    `off_road_duration` lên 594 s; chỉ một cảnh báo ở giây 8,5. Một lần nhìn sang bên kia thật 10 s ở phút 5 không sinh
    cảnh báo mới. Với 25° thì tự hồi (mốc về 5°).
  - Camera hoặc ghế xê dịch 35° giữa chuyến (đã đăng ký cũng bị): kẹt giống hệt. 25°: tự hồi.
  - `test_no_off_road_while_calibrating_and_median_ignores_glances` chỉ xét liếc ngắn hơn nửa cửa sổ.
- **Hậu quả:** HUD đứng ở L2 "nhìn về phía trước" suốt chuyến, và nhánh nhìn lệch thực tế bị tắt (mức không đổi nên
  không có cảnh báo mới). Chỉ "Đổi tài xế" hoặc đăng ký mới gỡ được.
- **Không chắc:** tần suất. Cần tài xế nhìn lệch trên 30° hơn nửa trong 5 s đầu ở trên 5 km/h (ra khỏi chỗ đỗ, nhập
  làn). Đăng ký là bắt buộc nên đường này chỉ chạy khi tài xế chọn "Để sau" hoặc đăng ký thất bại.
- **Đề xuất:** khi "lệch" kéo dài mà tư thế đứng yên (độ trải nhỏ) quá một ngưỡng thời gian thì hiệu chuẩn lại, kèm
  một sự kiện gửi backend. Ngưỡng mới trong `distraction.baseline`.
- **Công sức:** M. **Tác động:** FPS không đổi. Bỏ được một nguồn L2 sai kéo dài; rủi ro là tài xế nhìn lệch thật rất
  lâu bị học thành mốc, nên ngưỡng thời gian phải dài hơn nhiều so với `off_road_s`.
- **Trùng:** FMEA dòng 11 chỉ ghi "không xét trong 5 s đầu".

#### M2. Mốc tư thế đầu của khối 7 học cả lúc xe dừng, thay mốc đã đăng ký sau 5 s

- **Vấn đề:** mốc tư thế của khối 7 là trung vị trượt 60 s của mọi frame mắt mở, không phân biệt xe chạy hay dừng
  (`head.py:57-61`). Tư thế đã đăng ký chỉ được dùng khi cửa sổ có dưới 5 s dữ liệu (`head.py:44-48`), và không có giới
  hạn nào giữ mốc quanh giá trị đăng ký (mốc mắt thì có, `eyes.py:87-90`).
- **Bằng chứng (thử trong audit):** đăng ký với `road_pitch` 0, sau đó tài xế nhìn màn hình (cúi 12°) trong lúc còn
  dừng: giây 4 mốc là 0,0; giây 6 là 12,0; sau khi nhìn lại đường 19 s mốc vẫn 12,0 (trung vị 60 s cần hơn 30 s để đổi).
- **Hậu quả:** khoảng nửa phút đầu sau khi xe chạy, ba luật dùng "góc cúi so với mốc" lệch đi đúng khoảng đó: ngưỡng gục
  đầu 15°, quy tắc "đầu cúi" 10° (nhắm sâu cần EAR ≤ 0,35 lần mốc), và giới hạn 25° để đọc mắt. Ví dụ trên: phải cúi
  27° so với đường mới tính là gục.
- **Ca xấu hơn, Không chắc:** tư thế đổi hơn 25° theo chiều cúi và EAR ở tư thế mới dưới 0,65 lần mốc cũ. Thử: cúi 30°
  với EAR 0,6 lần mốc từ phút 5: trạng thái mắt không biết ở 100 % số frame của phút 10–15, mốc tư thế kẹt ở 0, PERCLOS
  0. Vòng kẹt: mốc tư thế chỉ học khi mắt "mở", mốc mắt chỉ học khi tư thế "được". Kiểm chứng: EAR thật của một người khi
  camera lệch 30° theo chiều dọc.
- **Đề xuất:** chỉ học mốc tư thế khi xe đang chạy (khối 10 đã có cờ), hoặc kẹp mốc quanh tư thế đã đăng ký như mốc
  mắt. Với ca kẹt: khi mắt không biết quá lâu thì học lại mốc tư thế bất kể EAR.
- **Công sức:** S. **Tác động:** FPS không đổi. Giảm sót `nod` đầu chuyến; chưa đo trên trace.
- **Liên quan:** khối 8 có mốc riêng (`distraction.py:223-258`) với luật khác. Hai định nghĩa "cúi so với đường" cùng
  tồn tại; cờ `gaze_down` của khối 7 dùng mốc của khối 7 nhưng được khối 8 tính thành "nhìn lệch".

#### M3. Gục đầu: phép thử "mắt nhắm" dùng EAR thô, cúi nhìn ngắn dễ thành `nod`

- **Vấn đề:** `ear_low` đưa vào bộ đếm gục là EAR so với ngưỡng nhắm, bỏ qua kiểm tư thế (`analyzer.py:111-114`,
  `head.py:115-117`). Khi đầu cúi thì mí trên theo hướng nhìn và EAR tụt còn khoảng nửa mốc, đúng như chính code ghi ở
  `eyes.py:36-38`. Nên điều kiện "mắt nhắm ≥ 30 % cú cúi" gần như luôn đạt khi cúi nhìn.
- **Bằng chứng (thử trong audit):** cúi 20° trong 1 s, mắt mở, EAR khi cúi bằng 0,9 / 0,7 / 0,6 / 0,5 lần mốc: `bow`,
  `bow`, `nod`, `nod`. Số có sẵn: độ chính xác của `nod` trên SUST là 48 % (`thresholds.yaml:339`).
- **Hậu quả:** hai lần cúi nhìn ngắn (dưới 2 s) trong 5 phút cho đủ số hạng gục đầu, 20 điểm của `drowsy_score`; cộng
  một số hạng khác là tới L1 (40).
- **Đề xuất:** frame "mắt nhắm" của cú cúi dùng cùng phép thử với nhắm sâu khi đầu cúi (`bowed_ear_ratio`, phiếu
  `eyeBlink`) thay cho ngưỡng nhắm thường.
- **Công sức:** S, cần chạy lại FL3D / SUST. **Tác động:** FPS không đổi. Giảm `nod` sai; có thể mất `nod` thật mà mắt
  chỉ khép hờ.
- **Trùng một phần:** việc 5 của improvements ghi "cúi nhìn 0 / 12 lần ra `nod`" trên bản tự ghi của một người. Phần
  bổ sung là cơ chế và ngưỡng EAR mà từ đó kết quả đổi (giữa 0,7 và 0,6 lần mốc).

#### M4. Ngáp: một lần đếm hai khi mất mặt giữa chừng; MAR không xét góc đầu

- **Bằng chứng:**
  - `mouth.py:99-103`: mất MAR quá 0,5 s thì xoá cả lần há miệng lẫn cờ `_fired`. Thử trong audit: há miệng 2 s, mất mặt
    0,6 s, há tiếp 2,4 s: 2 sự kiện `yawn`.
  - `analyzer.py:98`: MAR chỉ cần mặt đủ trong khung, không có điều kiện tư thế như mắt. Thử: MAR 0,37 ở chính diện
    thành 0,394 / 0,427 / 0,452 / 0,523 ở yaw 20° / 30° / 35° / 45°; cúi 30° thì giảm còn 0,32.
- **Hậu quả:** tay che miệng hoặc ngửa đầu khi ngáp làm mất mặt giữa chừng là thường gặp; đếm hai thì hai lần ngáp thật
  đã vượt `yawn_full` (3), tức 15 điểm. Nói hoặc hát khi đang quay đầu trên 30° dễ vượt ngưỡng ngáp hơn; ngáp khi cúi thì
  dễ sót.
- **Không chắc:** mức độ trên dữ liệu thật; chưa có nhãn ngáp che tay (improvements dòng 1166).
- **Đề xuất:** giữ cờ `_fired` qua khoảng hở cho tới khi thấy miệng khép; bỏ qua hoặc chia MAR cho `cos(yaw)` khi đầu
  quay quá một ngưỡng (ngưỡng mới trong `drowsiness.yawn`).
- **Công sức:** S. **Tác động:** FPS không đổi; giảm `yawn` sai.

### 4.4 Low

#### L1. `blink_rate` chia cho thời gian đồng hồ

- `eyes.py:216-221`: mẫu số là `min(t − start_t, 60)`, không phải số giây thấy mắt; `start_t` đặt một lần ở frame đầu
  (`analyzer.py:92-93`) và không đặt lại khi `forget_since`.
- Thử trong audit, 15 lần chớp mỗi phút: thấy mặt 100 % thời gian đọc 15,0; thấy 50 % đọc 8,0. Sau `forget_since(-inf)`
  (xong đăng ký, M68) 30 s: đọc 8,0.
- Hậu quả nhỏ: luật `blink_rate` đang ở mức 0 (chỉ ghi nhận), nhưng số này vào metadata và bản tổng kết. Bật lại luật
  thì đây thành báo sai.
- Đề xuất: chia cho thời gian biết mắt trong cửa sổ (đã có sẵn ở `Perclos`). Công sức S.

#### L2. `phone_ratio_2s` không cần số mẫu tối thiểu

- `distraction.py:286-293`: tỉ lệ trên số mẫu biết kết quả, không trọng số theo thời gian, không có ngưỡng độ phủ như
  PERCLOS (30 s) hay liếc (10 s).
- Thử trong audit: một frame dương giữa toàn mẫu `None` cho tỉ lệ 1,0 trong 2 s và cảnh báo L2 `phone` sau 0,5 s. Khi
  YOLO còn cho kết quả 20 % thời gian thì một phát hiện sai 0,2 s không đủ gây cảnh báo.
- Đường thực tế hẹp: cần gần như mọi mẫu khác là `None` (YOLO gần quá hạn 0,6 s), hoặc ngay sau khi xe chạy lại (cửa
  sổ vừa bị xoá, `distraction.py:323-326`): ba kết quả dương đầu tiên đủ cho cảnh báo sau 0,5 s thay vì khoảng 1,7 s.
- Kèm theo: không có hộp mặt thì `phone_near_face` trả `False` (`phone_detector.py:118-119`), tức "chắc chắn không có
  điện thoại" thay vì không biết.
- Đề xuất: yêu cầu số giây có kết quả tối thiểu trong cửa sổ (ngưỡng mới trong `distraction`). Công sức S.
- Trùng: FMEA dòng 17 xử lý YOLO quá hạn hẳn; phần mới là vùng giữa.

#### L3. Trạng thái không có trần

- Đếm nhắm mắt khi gục đầu chạy không giới hạn. Thử: nhắm sâu 1 s, gục, mất mặt 169 s: `closed_duration` 170 s, mức 3
  suốt, không `unavailable`. Còi tiếp tục là đúng ý thiết kế (FMEA dòng 6), nhưng nếu mặt mất vì lý do khác thì chỉ mặt
  trở lại mới tắt được; câu hỏi "Bạn còn ở đó không?" không chạy ở nhánh này.
- `_dip_track` của gục đầu thêm một phần tử mỗi frame khi góc cúi nằm trên 7° mà chưa về (`head.py:114`). Thử: cúi 18°
  liên tục với EAR 0,6 lần mốc: 900 phần tử sau 30 s, về 0 khi các mốc học lại (trước phút 5). Ở ca kẹt của M2 thì
  không về.
- Đề xuất: trần thời gian cho cả hai (ngưỡng mới), sau đó chuyển sang "tạm ngưng". Công sức S.

#### L4. Đăng ký: người có EAR mắt mở dưới 0,18 không đăng ký được

- `enrollment.py:274`: EAR bước 1 phải nằm trong `drowsiness.eye.baseline_min`–`baseline_max` (0,18–0,42). Thử: EAR 0,16
  ổn định: thất bại sau 3 lần với gợi ý `open_eyes` ("mở mắt ra").
- Không chắc: tỉ lệ người có EAR dưới 0,18 với camera này; chưa có số theo người. Kiểm chứng: phân bố `ear_base` trên 48
  người UTA-RLDD.
- Bước 2 (nhìn đường) chỉ cần có tư thế (`enrollment.py:249-252`): không kiểm mắt mở, không kiểm tài xế có nhìn đường
  thật không (không kiểm được).
- Bước 1 đòi `eye_cnn_reason` rỗng (`:253`): với H1 của audit 1 (ảnh màu tối bị coi là IR) thì đăng ký không qua được
  và gợi ý là "quá tối".

#### L5. Số magic ngoài YAML, và mặc định trong code lệch YAML

| Chỗ | Giá trị | Ghi chú |
|---|---|---|
| `edge_agent/analysis/drowsiness/head.py:123` | 0,15 | "Đáy" của cú cúi = trong 15 % độ sâu; quyết định tốc độ lên / xuống của phép thử nod / bow (đang tắt) |
| `edge_agent/analysis/drowsiness/common.py:13` | `recompute_s` 1,0 | Phân vị của mốc mắt, tư thế, mày chỉ tính lại mỗi giây |
| `edge_agent/perception/enrollment.py:116` | phân vị 10 / 90 | Định nghĩa "độ trải"; YAML chỉ nhắc trong comment |
| `edge_agent/perception/enrollment.py:276` | 0,0 | MAR khép khi không có mẫu |
| `edge_agent/perception/geometry.py:26-32` | 30 vòng, 1e-6, yaw xuất phát 0 / ±50° | Tham số của bộ giải tư thế bản web; có test giữ khớp OpenCV |
| `edge_agent/analysis/distraction.py:95` | `baseline_calibrate_s` mặc định 0,0 | YAML là 5,0 (`thresholds.yaml:406`); `DistractionConfig()` không tham số tắt hiệu chuẩn |
| `edge_agent/decision/risk_engine.py:60-61`, `78` | trọng số 10 / 10, `trend_level` 1 | YAML là 0 / 0 / 0. Ngoài phạm vi, ghi vì cùng kiểu lỗi với L1 của audit 1 |

Khoá thiếu trong YAML lấy mặc định im lặng (`edge_agent/config.py:162-167`), nên mặc định lệch là hành vi lệch khi ai
đó xoá một dòng. Các mục `drowsiness`, `features`, `enrollment` khớp hoàn toàn. Đề xuất: sửa ba mặc định, đưa 0,15 vào
`drowsiness.nod`. Công sức S.

#### L6. Test yếu hoặc thiếu

- Chưa có test cho: mặt lọt một phần kéo dài (H1); díp dài rồi nhắm (H2, chỉ có 0,6 s); hiệu chuẩn khi đang nhìn lệch
  và camera xê dịch (M1); mốc tư thế khối 7 sau đăng ký (M2); một lần ngáp bị ngắt bởi mất mặt (M4); `blink_rate` khi
  mất mặt (L1); `phone_ratio_2s` với ít mẫu (L2).
- FPS: `test_drowsiness.py`, `test_distraction.py`, `test_m38_distraction.py`, `test_gaze_down.py` đều cố định 30 FPS;
  chỉ `test_enrollment.py` (15 FPS) và hai test chớp chậm có tham số FPS. Không test nào dùng khoảng cách frame không
  đều, hay đổi FPS giữa chừng. Các biến tính theo số frame (tỉ lệ nhắm sâu, `phone_ratio_2s`) là chỗ nhạy với việc đó.
- Giá trị không hữu hạn và giờ lùi: không có test. Thử trong audit:
  - Một frame có `pitch` / `yaw` là NaN: khối 7 không đọc được mắt 60 s; `baseline_yaw` của khối 8 thành NaN vĩnh viễn
    và yaw 40° trong 100 s không còn là "lệch". Khối 6 hiện không sinh ra tư thế NaN (`solvePnP` ném lỗi hoặc trả thất
    bại), nên đây là phòng thủ; bổ sung cho M4 của audit 1.
  - Một frame MAR là NaN: không ảnh hưởng (mặt nạ nói vẫn 1184 frame như khi không có NaN).
  - Giờ lùi 100 s một lần: không lỗi; bộ đệm mốc mắt lên 6601 mẫu rồi về, độ phủ PERCLOS đọc 91 s trong cửa sổ 60 s cho
    tới khi giờ đuổi kịp. Cả hai nguồn giờ đều đơn điệu (`frame_source.py:206`, `frontend/src/live/frameTime.ts:20-25`).
- Mốc của khối 8 cộng `dt` không chặn (`distraction.py:320`, `227`): sau một lần đứng hình 30 s, một frame kéo mốc đi
  63 % quãng đường. Khối 7, chất lượng và liếc đều chặn ở 0,5 s.

#### L7. Tài liệu lệch code

| Tài liệu | Ghi | Code / YAML hiện tại |
|---|---|---|
| `docs/risk_engine_spec.md:41` | `drowsy_score` có `10·slow_blink + 10·brow` | Hai trọng số là 0 (`thresholds.yaml:479-480`) |
| `docs/risk_engine_spec.md:32` | Luật `trend` cho L1 | `risk.trend.level` 0, chỉ ghi nhận (`thresholds.yaml:517`) |
| `docs/risk_engine_spec.md:52` | Xe dừng: tối đa `stationary_max_level` (mặc định L1) | Mặc định và YAML đều 0 (`risk_engine.py:72`, `thresholds.yaml:496`) |
| `docs/risk_engine_spec.md:74` | Tổng trọng số tối đa 120 | 100 |
| `edge_agent/decision/risk_engine.py:7`, `31` | Công thức có slow_blink / brow; "ngủ gật lúc đèn đỏ vẫn có chuông" | Như trên; từ M30 không còn chuông |
| `docs/safety-fmea.md:191` | `bad_angle` là một lý do tạm ngưng | Chỉ trong giây đầu sau khi mất hẳn mặt (H1) |
| `edge_agent/analysis/drowsiness/head.py:8-9` | Sau đăng ký, mốc "bắt đầu ở tư thế đường đã đăng ký" | Đúng chữ, nhưng chỉ giữ được 5 s (M2) |
| CLAUDE.md, biến chính | `face_conf` | Là tỉ lệ landmark trong ảnh, không phải độ tin cậy (audit 1, L2) |

### 4.5 Các ca báo sai được yêu cầu kiểm

| Ca | Code làm gì | Kết luận |
|---|---|---|
| Ngáp khi nói | Ngáp cần MAR > 0,45 liên tục 1,5 s (`mouth.py:111`); nói tạo dao động MAR nên che nhắm mắt (`mouth.py:66-83`) | Có test (`test_talking_is_not_a_yawn`). Hở: MAR tăng khi quay đầu (M4); hát / há miệng lâu hơn 1,5 s vẫn là ngáp |
| Cười | Không có luật riêng. Cười làm hẹp mắt (0,55–0,75 lần mốc): không thành nhắm sâu nên không L3 | Vẫn vào PERCLOS từng frame nếu dưới 0,65 lần mốc và miệng không "nói". Không chắc mức độ: không có dữ liệu cười có nhãn |
| Chớp thường và nhắm lâu | Chớp ≤ 0,5 s; `microsleep` ≥ 1,0 s nhắm sâu; L3 ≥ 1,5 s | Tách đúng, có test. Đợt nhắm 0,5–1,0 s không thuộc loại nào. Chớp thường vẫn vào PERCLOS: 4,2 % trong lần thử 2 giờ (chớp 0,15 s mỗi 4 s), sát `perclos_low` 5 % |
| Nhìn gương | `off_road` khi quay quá 30° liên tục 2 s (1,5 s trên 80 km/h); xi nhan nới thêm 30° về phía đó | Bản tự ghi: nhìn gương chỉ quay 10–21° (improvements dòng 1544), không chạm ngưỡng. Hở: quan sát ở ngã rẽ về phía ngược xi nhan quá 2 s. Chưa có dữ liệu lái thật |
| Đường cong | Mốc khối 8 theo tư thế với hằng số 30 s, kẹp ±20° | Hợp lý trên code; chưa có dữ liệu |
| Nhìn bảng đồng hồ | Cúi đầu quá 20°, hoặc đầu cúi ≥ 10° kèm mí hạ (`gaze_down`), liên tục 2 s | Liếc ngắn không báo. Hở: cúi ngắn thành `nod` (M3); nhìn xuống lâu thành L3 (việc 5 của improvements, 7 / 30) |
| Tay gần mặt, không phải điện thoại | Chỉ lớp "cell phone" của YOLO, điểm ≥ 0,35, tâm trong vùng tài xế | Tay không tự kích hoạt. Không chắc tỉ lệ YOLO nhận nhầm vật cầm tay; vùng tài xế là 2D nên điện thoại của người ngồi sau nằm trong vùng vẫn tính |
| Người đeo kính | Khối 6–8 không có luật riêng; khối 5 xử lý lệch hai mắt do chói | Không kiểm tra được: chưa có dữ liệu người đeo kính (việc 4 của improvements) |

## 5. Không kiểm tra được, và vì sao

| Việc | Vì sao | Cách kiểm chứng |
|---|---|---|
| Tần suất mặt lọt một phần khung trong xe (H1) | Trace chỉ có camera chính diện | Phiên tự ghi với camera đặt lệch như màn hình xe |
| H2 trên lái thật | UTA-RLDD là người ngồi trước máy, không lái | Trace số từ chuyến thật (đang hoãn) |
| Tác dụng phụ của mọi đề xuất sửa lên báo sai | Audit không sửa code | Chạy lại `tools/seq_eval.py` và test hồi quy trace sau mỗi thay đổi |
| EAR khi camera lệch dọc 30° (ca kẹt của M2) | Không có bản ghi ở góc đó | Một phiên tự ghi, camera đặt thấp hoặc cao |
| Tần suất hiệu chuẩn sai lúc xuất phát (M1) | Không có chuyến thật | Ghi `baseline_yaw` sau hiệu chuẩn ở mỗi chuyến |
| Ngáp che tay, cười, hát, người đeo kính, EAR dưới 0,18 | Không có dữ liệu có nhãn | Phiên tự ghi của người thứ hai (việc 4) |
| Tốc độ khối 6–8 trong Pyodide và trên QCM6125 | Audit chỉ đo Python gốc trên Mac; không còn thiết bị | `tools/bench_web.py`; máy cùng chip |
| Tư thế đầu nhảy sang nghiệm đối xứng của `solvePnP` | Chỉ đọc code: điểm xuất phát lấy từ frame trước, sai thì giữ tới khi mất mặt. Chưa thử với landmark thật | Đếm bước nhảy yaw lớn giữa hai frame trên trace |
| Sai số tư thế do tiêu cự giả định (bằng bề rộng ảnh) | Không có camera đã hiệu chuẩn | So với góc đo bằng thước trên một phiên ghi |
| `frontend/src/hud/` có hiển thị `bad_angle` ở chỗ khác không | Chỉ grep, không chạy giao diện | Mở `#/live`, che nửa mặt ra mép khung |
| Các tài liệu khác (`ARCHITECTURE.md`, `PRD.md`, `roadmap.md`) có lệch khối 6–8 không | Chỉ đối chiếu spec, FMEA, improvements và docstring | Đọc đối chiếu riêng |
