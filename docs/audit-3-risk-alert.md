# Audit 3: khối 9–12 (risk engine, ngữ cảnh, trip memory, alert manager) và `decision/pipeline.py`

Ngày 08/10/2026, trên working tree của nhánh `DAQuan` (có thay đổi chưa commit, gồm M68 ở `risk_engine.py`,
`pipeline.py`, `eyes.py`). Chỉ đọc và phân tích: không sửa code, config hay `eval/results`. Phạm vi:
`edge_agent/decision/` (`risk_engine.py`, `alert_manager.py`, `trip_memory.py`, `trip_summary.py`, `presence.py`,
`pipeline.py`), `edge_agent/context/` (`vehicle_context.py`, `can_sim.py`), test và mục YAML tương ứng. Khối ngoài
phạm vi chỉ xét dataclass giao tiếp và chỗ nối (`edge_agent/runtime.py` gọi pipeline thế nào).

Cách kiểm:

- Đọc code và test; chạy cả 993 test Python (đều pass, gồm test hồi quy trace 36 video).
- Chuỗi số giả 15 FPS đưa thẳng vào `AlertManager`, `RiskEngine`, `DecisionPipeline`, `TripRuntime` với
  `config/thresholds.yaml` hiện tại. Gọi là "thử trong audit"; script đặt ngoài repo.
- Chạy lại `tools/uta_rldd.py` trên trace có sẵn, in ra ngoài repo: `tradeoff` (để so với file đã lưu) và `compare`
  trên 24 người dev với hai ngưỡng giả định (xem H4). Không đọc thêm lần nào trên 24 người giữ riêng ngoài điểm làm
  việc hiện tại mà `tradeoff` vốn đọc.
- Mọi số đo thời gian là trên máy Mac dev.

Quy ước: "đợt" là một quãng liên tục mà mức rủi ro của khối 9 không hạ quá `fall_hold_s` (3 s). "Phát" một cảnh báo
là `AlertOutput.new_alert` khác `None`: đó là lúc có tiếng và có sự kiện gửi backend; HUD hiện mức thì không cần "phát".

## 1. Tóm tắt

1. Không có phát hiện Critical. Khối 9 đúng với bảng luật, mọi cảnh báo đều đi qua xác nhận tăng và giữ hạ; bộ nhớ của khối 9–12 bị chặn (1,55 MB ở giờ 1, 1,60 MB ở giờ 4); không khối nào trong phạm vi ghi đĩa.
2. **High, báo sai:** dừng dưới 120 s (đèn đỏ) không phải "nghỉ", nên mắt nhắm lúc dừng vẫn nằm trong PERCLOS và nhớ microsleep. Thử: nhắm 25 s lúc dừng, xe lăn bánh là có L1 ban ngày, L2 ban đêm, dù lúc dừng hệ thống cố ý im lặng (M30).
3. **High, lặp sai chiều:** điểm đứng yên trên ngưỡng L1 suốt 30 phút chỉ có một tiếng chuông; điểm dao động quanh ngưỡng thì từ lần thứ ba, cứ khoảng 2 phút một cảnh báo L2 (`repeated_l1`) vô thời hạn. Một đợt L2 dài bắt đầu trong thời gian cooldown thì không có tiếng nào cho cả đợt.
4. **High, hệ số ngữ cảnh chưa từng được đo:** mọi eval chạy ở 12:00, 60 km/h, 0 giờ lái. Hệ số "lái lâu" bật một lần là giữ tới khi tắt app (không đặt lại sau khi nghỉ hay đổi tài xế). Quy đổi trên 24 người dev của UTA-RLDD: đêm + lái lâu (×1,44) cho 11 lần báo sai thay vì 5 (2,85 so với 1,29 / giờ).
5. Medium và Low: mẫu mỗi phút ngừng gửi backend sau "Đổi tài xế" hoặc nạp lại ngưỡng (thử: mất 26 phút); câu hỏi "Bạn còn ở đó không?" lặp mỗi 12 s khi mặt chập chờn; lý do xuất hiện dưới một mức cao hơn không bao giờ được phát; vùng 1–5 km/h không có "tạm ngưng giám sát"; spec lệch code thêm bốn chỗ ngoài bốn chỗ audit 2 đã ghi. Số trong `eval/results` khớp code hiện tại (`tradeoff` chạy lại ra giống hệt).

## 2. Bảng ràng buộc

| Ràng buộc (CLAUDE.md) | Kết luận | Bằng chứng |
|---|---|---|
| Xử lý on-device | Đạt | Khối 9, 11, 12 và `ContextTracker` là hàm thuần trên số. Mạng duy nhất trong phạm vi là `SignalLink` hỏi bộ giả lập ở `127.0.0.1` (`edge_agent/context/can_sim.py:252-263`), chỉ nhận tốc độ và xi nhan |
| Không ghi / giữ frame | Đạt | Không dataclass nào của khối 9–12 có trường ảnh. `grep` `open(`, `.write(`, `imwrite`, `pickle`, `sqlite` trong `edge_agent/decision` và `edge_agent/context`: chỉ còn hai chỗ đọc ở `can_sim.py:97`, `258`. Trip memory và bản tổng kết chỉ nằm trong RAM |
| Chỉ gửi metadata | Đạt | Thứ rời khối 12 là `Alert` (thời điểm, mức, lý do, hai điểm; `alert_manager.py:81-87`) và `TripSummary` (số và danh sách phút; `trip_summary.py:62-105`) |
| ≥ 15 FPS | Đạt trên Mac; Không chắc trên thiết bị đích | Thử trong audit, 4 giờ ở 15 FPS: cả `DecisionPipeline.step` trung bình 0,29 ms mỗi frame; riêng khối 9: 28 µs, khối 10: 5 µs, khối 11: 62 µs + 16 µs (tổng kết), khối 12: 2,5 µs. Pyodide và QCM6125: không đo |
| Không model nặng trong vòng lặp | Đạt | Không có model. Phép nặng nhất là `np.polyfit` mỗi frame (L2) |
| Chỉ pretrained | Đạt | Luật và phép cộng có trọng số; không có tham số nào được học |
| Ngưỡng nằm hết trong `thresholds.yaml` | Vi phạm một phần | Xem L4: mức của từng luật viết thẳng trong code, độ dài phút của bản tổng kết là 60 cố định, mặc định trong `RiskConfig` lệch YAML |
| Mỗi khối một module, giao tiếp qua dataclass | Đạt | `VehicleSignals` → `VehicleContext` → `RiskAssessment` → `AlertOutput`; `TripState` từ khối 11. Ngoại lệ nhỏ: `runtime.py:290-291` đọc bộ đếm `bins_completed` của khối 11 để quyết định gửi mẫu, gây M1 |
| Logic thời gian test bằng chuỗi giả | Đạt, còn thiếu ca | 121 hàm test trong 5 file của phạm vi, không test nào cần video. Ca thiếu: L5 |
| Bộ đệm bị chặn khi chạy nhiều giờ | Đạt | Sau 4 giờ giả lập: 15 điểm phút, 240 phút tổng kết, 23 mốc microsleep, 1 khoá cooldown. Hai cấu trúc không có trần cứng nhưng tăng rất chậm (L3) |
| Ưu tiên chống báo sai | Đạt một phần | Xác nhận tăng, giữ hạ, cooldown, "tạm ngưng" đều có test. Hở: H1, H2, H4, M2 |
| Comment và tên biến tiếng Anh | Đạt | Các file trong phạm vi |

## 3. Phát hiện

Mỗi mục: vấn đề, bằng chứng, hậu quả, đề xuất, công sức (S dưới nửa ngày, M một đến hai ngày, L hơn), tác động tới FPS
và báo sai. "Trùng" nghĩa là `docs/improvements.md`, `docs/safety-fmea.md` hoặc hai audit trước đã có; khi đó chỉ ghi
phần bổ sung. Không đề xuất nào làm đổi FPS đáng kể, nên dòng FPS chỉ ghi khi có khác biệt.

### 3.1 Critical

Không có.

### 3.2 High

#### H1. Mắt nhắm lúc dừng ngắn (đèn đỏ) thành cảnh báo ngay khi xe lăn bánh

- **Vấn đề:** chỉ lần dừng từ `context.rest_after_s` (120 s) trở lên mới được coi là "nghỉ" và bị xoá khỏi bằng chứng
  khi xe chạy lại (`pipeline.py:116-124`). Dừng ngắn hơn thì frame vẫn được tính là "có quan sát"
  (`pipeline.py:201`: `observed = not (ctx.resting or closing_eyes)`), PERCLOS 60 s và mốc microsleep của trip memory
  giữ nguyên. Trong lúc dừng, mức bị chặn về 0 (`risk_engine.py:156-162`, `thresholds.yaml:496`), nhưng trần đó mất
  ngay khi tốc độ vượt 1 km/h.
- **Bằng chứng (thử trong audit, pipeline đầy đủ, 15 FPS):** chạy 50 km/h, dừng 60 s, nhắm mắt 25 s trong lúc dừng,
  rồi chạy lại.
  - Ban ngày: lúc dừng điểm đã là 65 (PERCLOS 0,44, số hạng microsleep 1) nhưng mức 0. Xe lăn bánh 1,1 s thì phát
    L1 `drowsy_score`; mức 1 giữ hơn 30 s; số hạng microsleep (25 điểm) còn tới hết 5 phút.
  - 02:00: phát thẳng L2 sau 0,7 s (điểm 78).
  - Chỉ nhắm 3 s lúc dừng: ban ngày điểm 37,4, không cảnh báo; 02:00 điểm 44,9, có L1.
- **Hậu quả:** M30 đã chốt "đứng yên thì không cảnh báo" vì nhắm mắt nghỉ ở đèn đỏ là hành vi thường gặp. Hiện cảnh
  báo chỉ bị dời tới lúc xe chạy, là lúc tài xế đã mở mắt và đang nhìn đường. FMEA dòng 12 ghi "khi xe chạy lại thì
  mọi luật hoạt động bình thường", không nhắc phần mang sang này. Bản tổng kết cũng tính: một lần nhắm ở đèn đỏ là
  một microsleep và chuyến thành "rủi ro" (cố ý từ M27, `trip_summary.py:13-14`).
- **Đề xuất:** khi xe chạy lại sau một lần dừng bất kỳ, bỏ phần khối 7 và trip memory gom từ lúc dừng, như đang làm
  với lần nghỉ (hàm `forget_since` đã có sẵn). Nếu muốn giữ bằng chứng buồn ngủ thật ở đèn đỏ thì chỉ bỏ khi lần dừng
  dài hơn một ngưỡng mới (ví dụ 10 s). Đây là quyết định của anh vì nó đánh đổi báo sai lấy độ nhạy. Công sức S.
- **Tác động:** giảm báo sai ở mỗi lần dừng có nhắm mắt; mất phần điểm của người ngủ gật thật ở đèn đỏ (L3 khi đang
  chạy không đổi).
- **Trùng:** không. `improvements.md:1023` chỉ ghi eval không thử luật dừng đèn đỏ.

#### H2. Leo thang `repeated_l1` không có điểm dừng, và thưởng cho điểm dao động quanh ngưỡng

- **Vấn đề:** lần phát L1 thứ ba của cùng một lý do trong 600 s đi ra thành L2 (`alert_manager.py:152-157`). Sau khi
  leo thang, danh sách `_l1_emits` không được xoá (`alert_manager.py:123-133`), nên mọi lần phát sau đó cũng là L2,
  cho tới khi xe đỗ đủ 120 s rồi chạy lại (`pipeline.py:123`). Muốn có một lần phát L1 mới thì mức phải hạ quá 3 s
  rồi lên lại; điểm nằm yên trên ngưỡng không tạo ra lần phát nào (xem H3). Vậy thứ kích hoạt leo thang là số lần
  điểm **cắt qua** ngưỡng 40, không phải thời gian buồn ngủ.
- **Bằng chứng (thử trong audit, `AlertManager` với ngưỡng YAML):**
  - L1 liên tục 30 phút: đúng 1 lần phát (giây 1).
  - L1 bật 20 s, tắt 110 s, lặp lại 40 phút: L1 ở giây 1 và 131, rồi L2 `repeated_l1` ở giây 261, 391, 521... tổng
    17 lần L2 (âm thanh + rung ghế), cách nhau 130 s.
- **Hậu quả:** người có điểm lơ lửng quanh 40 nhận cảnh báo mạnh hơn và dày hơn người có điểm 60 đều. Báo sai vốn
  dồn vào ít người (M69: cả 4 lần trên 24 người giữ riêng là của một người), nên chính những người đó gánh chuỗi này. Tài xế bấm "báo sai" không đổi được gì ở khối 12 (`runtime.py:394-403` chỉ ghi nhận), nên chuỗi này
  chỉ dừng khi đỗ xe 2 phút.
- **Đề xuất:** (a) sau khi leo thang, xoá `_l1_emits` của lý do đó để lần sau bắt đầu đếm lại; (b) thêm khoảng trễ
  theo điểm cho luật `drowsy_score` (lên ở `l1`, xuống ở `l1` trừ một khoảng mới trong YAML) để điểm dao động không
  thành nhiều đợt. Công sức S cho (a), M cho (b) vì phải chạy lại UTA-RLDD.
- **Tác động:** giảm báo sai lặp. (b) làm đợt L1 dài hơn, số lần phát ít hơn.
- **Trùng:** `pilot-readiness.md` E3 ghi leo thang L1 → L2 là ngưỡng tạm; `thresholds.yaml:558` ghi chưa có dataset
  chuyến dài. Phần mới: hành vi sau lần leo thang đầu, và việc nó đếm số lần cắt ngưỡng.

#### H3. Cooldown nuốt cả đợt, và mức đứng yên không được nhắc lại

- **Vấn đề:** khi một đợt mới được nâng mức trong thời gian cooldown, `_emit` trả về "bị giữ lại" nhưng vẫn ghi lý do
  vào `_alerted` (`alert_manager.py:145-149`). Từ đó lý do này không còn là "mới", nên hết cooldown cũng không phát,
  dù đợt kéo dài bao lâu. Ngoài ra không có cơ chế nhắc lại cho một mức đang giữ.
- **Bằng chứng (thử trong audit):**
  - Nhìn lệch 3 s (phát L2 ở 0,5 s), nhìn lại đường 5 s, rồi nhìn lệch liên tục 40 s: không có lần phát thứ hai nào.
    HUD hiện mức 2 suốt 40 s đó, không tiếng, không sự kiện backend.
  - L1 trong 5 s, hết 10 s, rồi L1 liên tục hơn 20 phút: chỉ có tiếng chuông đầu tiên.
- **Hậu quả:** đây là bỏ sót có điều kiện: lần nhìn lệch dài và nguy hiểm nhất không có tiếng chỉ vì trước đó 5 s đã
  có một lần ngắn. L3 không bị (cooldown 0, còi lặp khi mắt còn nhắm). Với L1, tài xế buồn ngủ đều trong nửa giờ nghe
  một tiếng chuông; leo thang "đã nhắc nhiều lần mà không nghỉ" (M32) không bao giờ chạy cho người này.
- **Đề xuất:** phát lại khi đợt vẫn còn sau khi cooldown hết (một bộ đếm thời gian theo mức đang giữ, dùng chính
  `cooldown_s`), và đếm lần nhắc đó vào `_l1_emits`. Khi đó leo thang phản ánh thời gian ở L1 thay vì số lần cắt
  ngưỡng, và sửa luôn gốc của H2. Công sức S–M (kèm sửa 4–5 test hiện có).
- **Tác động:** thêm tiếng cho đợt dài (đúng ý cảnh báo); số lần phát trên video 10 phút của UTA-RLDD có thể tăng, phải
  chạy lại để biết số báo sai / giờ đổi thế nào.
- **Trùng một phần:** FMEA dòng 14 (mức Thấp) ghi "HUD vẫn hiện mức, chỉ không có tiếng / sự kiện mới" trong thời
  gian cooldown. Phần mới: sự im lặng kéo dài hết đợt chứ không hết sau 30 s / 120 s, và mức đứng yên không được
  nhắc. Câu "Mức cao hơn luôn được phát" trong FMEA và trong docstring cũng không đúng hẳn, xem 3.7.

#### H4. Hệ số đêm và lái lâu chưa từng được đo; "lái lâu" bật rồi không tắt

- **Vấn đề 1, không tắt:** `long_drive = drive_time_s >= long_drive_s` (`vehicle_context.py:106`), còn `drive_time_s`
  là tổng thời gian xe lăn bánh từ lúc mở app, không có chỗ nào đặt lại (`can_sim.py:144-146`, `204-206`).
  `change_driver` giữ nguyên ngữ cảnh xe (`pipeline.py:110-114`). Thử trong audit: 7 100 s đã lái, chạy thêm, nghỉ
  10 phút, chạy tiếp, đổi tài xế: `long_drive` là `True` ở mọi thời điểm sau giây thứ 100. Bản tổng kết thì có bộ đếm
  lái liên tục được đặt lại khi nghỉ (`trip_summary.py:169-171`); khối 9 không dùng nó.
- **Vấn đề 2, chưa đo:** mọi công cụ eval dựng xe ở 12:00, tốc độ cố định, 0 giờ lái (`tools/seq_eval.py:137`, `384`;
  `tools/eval.py:532`). Con số 0,98 báo sai / giờ vì vậy là của ban ngày, trước giờ lái thứ hai. Hệ số nhân vào
  toàn bộ điểm, kể cả phần điểm do báo sai của khối 7.
- **Bằng chứng (đo trong audit):** nhân điểm với hệ số k rồi so với ngưỡng tương đương với chia hai ngưỡng `l1`, `l2`
  cho k (trần 100 không ảnh hưởng vì cả hai ngưỡng dưới 100; luật `trend` đang tắt). Chạy `tools/uta_rldd.py compare
  --split dev` với ngưỡng đã chia, 24 người dev, 3,87 giờ video tỉnh táo:

  | Điều kiện | Ngưỡng tương đương | Báo sai | / giờ (cận trên rộng hơn) | Cửa sổ `0` ≥ L1 | Cửa sổ `0` ≥ L2 | Video `5` có cảnh báo | Video `10` có cảnh báo |
  |---|---|---:|---:|---:|---:|---:|---:|
  | Hiện tại (ngày) | 40 / 70 | 5 | 1,29 (3,02) | 3,7 % | 0,1 % | 5 / 24 | 14 / 24 |
  | Đêm (×1,2) | 33,3 / 58,3 | 5 | 1,29 (3,02) | 5,9 % | 0,5 % | 8 / 24 | 15 / 24 |
  | Đêm + lái lâu (×1,44) | 27,8 / 48,6 | 11 | 2,85 (6,02) | 8,0 % | 0,8 % | 11 / 24 | 18 / 24 |

  Thử thêm trên khối 9: ban đêm sau 2 giờ, 2 lần gục + 2 lần ngáp (không có bằng chứng nào từ mắt) cho 43,2 điểm, L1;
  PERCLOS 15,5 % một mình cho 40,3 điểm, L1. Ban ngày hai ca này là 30 và 28 điểm.
- **Hậu quả:** chỉ riêng hệ số đêm thì số lần phát không đổi trên dev (thời gian ở L1 tăng 1,6 lần). Khi cả hai hệ số
  cùng bật, báo sai hơn gấp đôi, và điều kiện đó đúng với xe chạy đêm đường dài. Do vấn đề 1, hệ số lái lâu còn áp cho
  tài xế vừa nhận xe và cho chuyến sau một lần nghỉ dài, miễn là app chưa tắt.
- **Đề xuất:** (a) đặt lại thời gian lái dùng cho `long_drive` khi nghỉ và khi đổi tài xế (khối 10 đã biết `resting`).
  Công sức S. (b) thêm tuỳ chọn giờ và thời gian lái cho các công cụ eval, hoặc ghi vào `report.md` dòng quy đổi như
  bảng trên. Công sức S. (c) cân nhắc hai hệ số cộng trần thay vì nhân chồng (1,2 và 1,2 thành 1,44); quyết định của
  anh sau khi có (b).
- **Tác động:** (a) giảm báo sai sau khi nghỉ / đổi tài xế. Hạn chế của phép quy đổi: video 10 phút, người ngồi trước
  laptop; không nói được hệ số có tăng độ nhạy đúng lúc cần hay không.
- **Trùng:** `improvements.md:1023` ghi tốc độ cố định nên luật ngữ cảnh không được thử. Phần mới: số quy đổi và lỗi
  không đặt lại.

### 3.3 Medium

#### M1. Mẫu mệt mỏi mỗi phút ngừng gửi sau "Đổi tài xế" hoặc sau khi nạp lại ngưỡng

- `runtime.py:290-291` gửi mẫu khi `r.trip.bins_completed > self._bins_sent`. `change_driver` và `reconfigure` tạo
  `TripMemory` mới, bộ đếm về 0 (`pipeline.py:92`, `167`), còn `_bins_sent` giữ số cũ (`runtime.py:380-384`, `365-370`).
- Thử trong audit (`TripRuntime`, 60 phút): không làm gì thì 59 mẫu. Đổi tài xế ở phút 25,2: 34 mẫu, không mẫu nào từ
  phút 25 tới phút 51,2. Nạp lại ngưỡng ở cùng thời điểm: y hệt. Biểu đồ trên HUD không bị (nó đọc từ bản tổng kết).
- Hậu quả: timeline của tài xế mới trên dashboard trống đúng bằng số phút chuyến đã chạy; nạp ngưỡng ở phút 120 thì
  mất 2 giờ. Không có test nào đếm mẫu sau hai thao tác này.
- Đề xuất: đặt `_bins_sent = 0` ở hai chỗ đó, hoặc để khối 11 tự báo "vừa đóng một phút" thay vì cho bên ngoài so bộ
  đếm. Công sức S. Không ảnh hưởng báo sai.

#### M2. "Bạn còn ở đó không?" lặp lại không giới hạn khi mặt chập chờn

- `PresenceCheck.update` đặt lại toàn bộ trạng thái ngay khi có một frame không còn "mất" (`presence.py:63-65`), kể
  cả cờ "đã trả lời". Không có khoảng nghỉ giữa hai lần hỏi.
- Thử trong audit: mặt hiện đúng một frame mỗi 12 s (đội mũ, khẩu trang, camera lệch), xe đang chạy: 10 lần hỏi kèm
  tiếng trong 2 phút, mỗi lần sau 8,1 s. Trả lời một lần cũng chỉ có hiệu lực tới frame có mặt kế tiếp.
- Hậu quả: phiền lặp lại đúng ở nhóm người mà hệ thống vốn nhìn kém; mỗi lần không chạm là một sự kiện `no_answer`
  gửi ngay cho quản lý.
- Đề xuất: mặt phải hiện lại đủ lâu (ngưỡng mới) mới coi là "đã trở lại", và sau một lần đã trả lời thì chờ một
  khoảng (ngưỡng mới) trước khi hỏi lại. Công sức S. Giảm báo sai; không ảnh hưởng ca gục ra khỏi khung thật (mặt
  không hiện lại).
- Trùng: `thresholds.yaml:572` ghi ngưỡng tạm, chưa có dữ liệu; phần lặp lại là mới.

#### M3. Lý do xuất hiện dưới một mức cao hơn không bao giờ được phát

- Khi mức hạ, lý do của mức thấp được đánh dấu "đã báo" (`alert_manager.py:213-216`, có chủ ý: hạ mức không phải cảnh
  báo mới). Hệ quả phụ: một lý do **bắt đầu** trong lúc mức cao hơn đang bật thì không có lần phát nào của riêng nó.
- Thử trong audit: microsleep L3 trong 4 s, điện thoại từ giây 1 tới giây 60: chỉ có một lần phát L3; 56 s cầm điện
  thoại sau đó không tiếng, không sự kiện `phone`. Tương tự: nhìn lệch L2 trong 6 s, `drowsy_score` L1 từ giây 2 và
  kéo dài 10 phút: không có tiếng chuông L1 nào, và lần đó không được đếm cho leo thang.
- Hậu quả: hai nhánh không mâu thuẫn về mức (lấy mức cao nhất, `risk_engine.py:244-245`), nhưng nhánh thấp hơn mất
  tiếng và mất sự kiện khi chồng lên nhau. Thời lượng vẫn có trong bản tổng kết (`trip_summary.py:177-183` đếm theo
  hit, không theo cảnh báo).
- Đề xuất: khi hạ mức, lý do nào chưa từng được phát ở mức của nó trong đợt này thì đi qua đường "lý do mới"
  (`_check_new_reasons`) thay vì bị đánh dấu sẵn. Công sức S–M. Thêm vài lần phát đúng; cần chạy lại test hồi quy trace.

#### M4. Vùng 1–5 km/h: không có "tạm ngưng giám sát", nhưng L3 vẫn chạy

- `unavailable` và câu hỏi hiện diện cần `ctx.moving` (từ 5 km/h; `risk_engine.py:235`, `pipeline.py:196`). Trần mức
  của nhánh buồn ngủ chỉ áp khi tốc độ dưới 1 km/h (`vehicle_context.py:94`).
- Thử trong audit ở 3 km/h: mất mặt 60 s thì `unavailable` là `False`, mức 0, HUD vẫn báo đang giám sát; nhắm mắt 2 s
  thì L3.
- Hậu quả: bò trong kẹt xe, camera bị che hoặc tài xế ra khỏi khung thì không ai được báo; đây là trạng thái im lặng
  mà FR-6 muốn tránh. Chiều ngược lại, nhiễu tốc độ quanh 1 km/h lúc dừng đèn đỏ làm trần mức bật tắt.
- Đề xuất: xét `unavailable` khi không đứng yên (`not ctx.stationary`) thay vì khi `moving`. Công sức S, cần sửa
  `test_not_unavailable_when_parked` cho rõ ranh giới.
- Trùng một phần: `improvements.md:626` (việc 12) ghi nhiễu GPS 1–3 km/h lúc dừng. Phần `unavailable` là mới.

#### M5. Nạp lại ngưỡng giữa chuyến: xoá trí nhớ ở đèn đỏ, và bỏ qua một số mục

- "Đỗ" để nạp ngưỡng là tốc độ dưới 1 km/h (`runtime.py:361-363`), tức bất kỳ lần dừng đèn đỏ nào, không phải lần
  nghỉ. `reconfigure` dựng lại khối 7, 8, 11, 12 (`pipeline.py:159-173`): mất mốc mắt tự học, PERCLOS, mốc microsleep
  5 phút, bộ đếm `repeated_l1` / `repeated_l3`. Docstring nói "khi đỗ thì không có gì cảnh báo phụ thuộc vào", điều
  đó chỉ đúng với lần nghỉ.
- `reconfigure` không dựng lại `ContextTracker`, `QualityMonitor`, cấu hình bản tổng kết và HUD. Ngưỡng `context.*`
  hay `quality.*` chỉnh từ dashboard không có hiệu lực tới khi mở lại app, trong khi thiết bị vẫn báo
  `config_applied` kèm số phiên bản mới (`runtime.py:377`).
- Hậu quả: thử một bộ ngưỡng ghim cho một xe có thể cho kết luận sai (tưởng đã áp); tài xế buồn ngủ thật được "xoá
  sổ" nếu ngưỡng đổi lúc dừng đèn đỏ.
- Đề xuất: chỉ nạp khi `resting`; áp cả ngữ cảnh và chất lượng, hoặc từ chối phiên bản có khoá ngoài các mục được nạp.
  Công sức S.
- Không chắc: dashboard có cho sửa khoá `context.*` hay không (chưa đọc hết backend). Kiểm chứng: xem danh sách khoá
  mà trang chỉnh ngưỡng gửi lên.

### 3.4 Low

#### L1. Giá trị không hữu hạn: điểm NaN tắt luật trong im lặng và làm bẩn trip memory

- Thử trong audit: `perclos_60s` là NaN, ngáp và gục đầy: điểm NaN, mức 0 (không NaN thì 75 điểm, L2).
  `closed_duration` NaN: không L3. `off_road_duration` NaN: `distraction_score` NaN (luật `phone` vẫn chạy).
- Một điểm NaN trong một phút làm điểm phút đó và `trend_15min` thành NaN (`trip_memory.py:89`, `103`); mẫu gửi
  backend chứa NaN, không phải JSON hợp lệ.
- Khối 7 hiện không sinh NaN ở các trường này (audit 2, L6), nên đây là phòng thủ. Đề xuất: khối 9 coi giá trị không
  hữu hạn là 0 cho số hạng đó và ghi một lần vào log. Công sức S.
- Trùng: audit 1 M4, audit 2 L6 xử lý nguồn NaN; phần mới là hành vi của khối 9 và 11.

#### L2. `np.polyfit` chạy mỗi frame

- `TripMemory.update` tính lại độ dốc trên tối đa 15 điểm ở mọi frame (`trip_memory.py:103`, `47-53`), dù các điểm chỉ
  đổi mỗi phút. Đo: khối 11 trung bình 62 µs mỗi frame, lớn nhất trong khối 9–12 và bằng khoảng 1 / 5 cả
  `DecisionPipeline.step`. Luật `trend` lại đang ở mức 0 (chỉ ghi nhận).
- Đề xuất: tính lại khi một phút đóng hoặc khi `forget_since` chạy. Công sức S. Lợi nhỏ trên Mac; trên Pyodide không
  đo được trong audit.

#### L3. Hai cấu trúc không có trần cứng

- `TripMemory._microsleeps` thêm một số cho mỗi microsleep và chỉ đọc phần tử cuối (`trip_memory.py:64`, `97`, `104`).
  `TripCollector._minutes` thêm một mục mỗi phút cả chuyến (`trip_summary.py:145`): 240 mục sau 4 giờ.
- Không phải rò rỉ đáng kể (bộ nhớ theo dõi 1,55 MB ở giờ 1, 1,60 MB ở giờ 4). Ghi để biết khi chuyến dài nhiều ngày
  mà không kết thúc: bản tổng kết gửi lên cũng dài theo.

#### L4. Số magic ngoài YAML, và mặc định lệch YAML

| Chỗ | Giá trị | Ghi chú |
|---|---|---|
| `edge_agent/decision/risk_engine.py:187`, `189`, `191`, `193`, `216`, `218` | Mức 3 / 2 / 1 của từng luật | Chỉ `trend` và `blink_rate` có mức trong YAML. Hợp lý nếu coi là định nghĩa, nhưng không tắt được một luật bằng config như hai luật kia |
| `edge_agent/decision/alert_manager.py:153` | Mức 2 khi leo thang | Đích leo thang viết thẳng |
| `edge_agent/decision/risk_engine.py:154`, `214` | 100 | Thang điểm; `distraction_score` bão hoà đúng tại ngưỡng luật (xem 3.6) |
| `edge_agent/decision/trip_summary.py:204`, `232` | 60 s một phút | Trip memory dùng `trip_memory.bin_s` (YAML); đổi `bin_s` thì hai bên lệch nhau |
| `edge_agent/decision/trip_summary.py:304` | Phân vị 90 | `drowsy_p90` |
| `edge_agent/context/can_sim.py:237` | Chu kỳ hỏi 0,2 s | Phải nhỏ hơn `context.vehicle_signal_stale_s` (1,0), không có luật nhất quán nào giữ |
| `edge_agent/decision/risk_engine.py:60-61`, `78` | Trọng số 10 / 10, `trend_level` 1 | YAML là 0 / 0 / 0. Trùng audit 2 L5 |

Thêm: `consistency_errors` không có luật nào cho mục `alert` và `trip_memory` (`edge_agent/config.py:59-91`). Ví dụ
`(l1_repeat_count − 1) × cooldown_s[1] ≥ l1_repeat_window_s` làm leo thang không bao giờ chạy mà không báo lỗi;
`trend_window_bins: 0` cho hàng đợi rỗng. Công sức S.

#### L5. Test yếu hoặc thiếu

- Có đủ: từng luật của khối 9, trần mức theo ngữ cảnh, `unavailable` và `head_drop`, xác nhận tăng, giữ hạ, cooldown
  theo lý do, leo thang lần thứ ba, `repeated_l3`, L0 → L3 tức thì và L3 → L0 sau giữ hạ, nghỉ rồi chạy lại.
- Chưa có test cho: dừng ngắn rồi chạy lại (H1); L1 kéo dài và lần phát thứ tư trở đi sau leo thang (H2); đợt dài bắt
  đầu trong cooldown (H3); `long_drive` sau khi nghỉ hoặc đổi tài xế, và đêm + lái lâu cùng lúc ở mức khối 9 (H4, mới
  có một test ở mức kịch bản); số mẫu sau `change_driver` / `reconfigure` (M1); mặt chập chờn với câu hỏi hiện diện
  (M2); lý do bắt đầu dưới mức cao hơn (M3); tốc độ 1–5 km/h (M4); giá trị không hữu hạn (L1).
- Mọi test của `AlertManager` dùng bước thời gian đều 0,1 s. Thử trong audit: hai frame cách nhau 2 s (vòng lặp đứng
  hình) cùng mang L2 thì frame thứ hai phát cảnh báo, vì xác nhận tăng so dấu thời gian chứ không đếm bằng chứng
  (`alert_manager.py:205`). Với `off_road` thì thời lượng đã do khối 8 đo nên ít rủi ro; với `drowsy_score` là hai
  mẫu. Worklog 08/10 có ghi vòng lặp bản web từng ngừng nhận frame, nên ca này có thật.
- Test đơn vị của khối 12 dùng `cooldown_s` L3 là 10 s, YAML là 0; hành vi L3 theo YAML chỉ được phủ ở
  `test_m44_unresponsive.py`.
- Test hồi quy trace và mọi eval chạy ở 12:00, 60 km/h: khoá hành vi ban ngày, không khoá hành vi có ngữ cảnh.

#### L6. Việc nhỏ khác

- `drowsy_score` đọc 0 trong bước nhắm mắt của đăng ký (M68) nhưng không đọc 0 khi nghỉ: thử đỗ 10 phút, nhắm mắt
  200 s, HUD hiện 65 điểm, mức 0, không vào trip memory. Không sai, chỉ không nhất quán với M68.
- Luật `blink_rate` dùng thời gian từ đầu chuyến làm "đã quan sát đủ" (`risk_engine.py:202`), không phải thời gian
  thấy mắt; luật `trend` gọi là điểm / phút nhưng các phút bị bỏ (nghỉ, đứng hình) không được tính vào trục thời gian
  (`trip_memory.py:91`). Cả hai đang ở mức 0. Trùng audit 2 L1 ở phần `blink_rate`.
- Xi nhan: giới hạn quay đầu nới thêm 30° về phía xi nhan trong suốt thời gian bật, không có trần thời gian. Quên tắt
  xi nhan trên cao tốc thì phía đó được nới vô thời hạn.

### 3.5 Tác động FPS và bộ nhớ

| Khối | Trung bình mỗi frame | Chậm nhất | Ghi chú |
|---|---:|---:|---|
| 10 `ContextTracker.update` | 5 µs | 1,8 ms | |
| 9 `RiskEngine.assess` | 28 µs | 11,5 ms | Đỉnh là một frame đơn lẻ trong 216 000 |
| 12 `AlertManager.update` | 2,5 µs | 1,0 ms | |
| 11 `TripMemory.update` | 62 µs | 8,5 ms | `np.polyfit`, xem L2 |
| 11 `TripCollector.update` | 16 µs | 2,1 ms | |
| Cả `DecisionPipeline.step` (khối 7–12) | 0,29 ms | | 4 giờ ở 15 FPS, Mac dev |

Ở 15 FPS mỗi frame có 66,7 ms, khối 9–12 dùng khoảng 0,2 % số đó trên Mac. Không đề xuất nào trong báo cáo thêm việc
đáng kể vào vòng lặp.

### 3.6 Các điểm kiểm riêng của phiên này

| Câu hỏi | Trả lời |
|---|---|
| Công thức `drowsy_score` | `40·perclos + 25·microsleep + 15·yawn + 20·nod` (hai trọng số chớp chậm và nhướn mày là 0), mỗi số hạng 0..1, tổng tối đa đúng 100. PERCLOS nội suy 5 % → 20 %; ngáp đầy ở 3 lần / 10 phút, gục đầy ở 2 lần / 5 phút; microsleep là 0 hoặc 1 và giữ 5 phút. Nhân 1,2 khi đêm, 1,2 khi lái lâu, rồi cắt ở 100 (`risk_engine.py:126-154`). Bão hoà: có, ở 100. Ban ngày tổng tối đa là 100; đêm + lái lâu thì 69,4 điểm thô đã chạm trần |
| Công thức `distraction_score` | `100 × min(max(off_road / ngưỡng, phone_ratio / 0,6), 1)` (`risk_engine.py:214`). Đây là "đã đi được bao nhiêu phần tới ngưỡng L2", đạt 100 đúng lúc luật bật và không tăng nữa; không phải điểm rủi ro. Không luật nào dùng nó (spec mục 9 đã ghi) |
| Code và spec có lệch nhau không | Có. Bốn chỗ audit 2 đã ghi, thêm bốn chỗ ở 3.7 |
| Mapping điểm → mức | Không có khoảng trễ theo điểm: lên và xuống cùng ở 40 và 70. Chống rung bằng thời gian, không đối xứng: lên cần giữ 1,0 s (L1), 0,5 s (L2), 0 s (L3); xuống cần thấp hơn liên tục 3 s cho mọi mức. Không có thời gian giữ tối thiểu nào khác. Một frame trở lại mức cũ là đặt lại đồng hồ hạ; một frame hụt là đặt lại đồng hồ lên |
| Cooldown, chống dồn | Theo (mức, lý do): L1 120 s, L2 30 s, L3 0 s. Chống dồn tốt trong một đợt (rung 0,2 s không phát lại, có test). Hở: H3 |
| Leo thang | L1 lần thứ ba trong 600 s → L2 `repeated_l1`; L3 lần thứ ba trong 600 s mang `repeated_l3`. Hở: H2. Thử L3 3 s mỗi 30 s trong 5 phút: 10 lần còi, từ lần thứ ba đều mang `repeated_l3` và gửi quản lý ngay; không có trần nào cho chuỗi này |
| Tắt tiếng | Không có. Giao diện ghi "sound is always on" (`frontend/src/hud/HudScreen.tsx:36`), khối 12 không có trạng thái tắt tiếng |
| Khi tài xế phản hồi | Bấm "báo sai" chỉ ghi `feedback` cho backend và đếm vào bản tổng kết (`runtime.py:394-403`); khối 12 không đổi gì, cùng lý do sẽ phát lại sau cooldown. Việc không tự hạ ngưỡng theo phản hồi là quyết định đã ghi ở `improvements.md` (mục "Chỉ số theo từng người"). Chạm "Tôi vẫn ở đây" có hiệu lực tới khi mặt hiện lại (M2) |
| Có thể báo nhầm lặp lại gây phiền không | Có, ba đường: `repeated_l1` mỗi 130 s (H2), L3 không cooldown cho mỗi lần đọc nhầm mắt nhắm, câu hỏi hiện diện mỗi 12 s (M2) |
| Ngữ cảnh có thật sự giảm báo sai không | Phần "đứng yên / nghỉ" có: tắt hẳn một lớp báo sai và có test. Phần "tốc độ cao" (ngưỡng nhìn lệch 1,5 s thay vì 2 s), "đêm", "lái lâu" đều làm hệ thống nhạy hơn chứ không giảm báo sai, và chưa có số đo nào đứng sau (H4). Xi nhan giảm báo sai trên lý thuyết, chưa có dữ liệu. "Đường cong" không có tín hiệu riêng: khối 8 tự bám tư thế (ngoài phạm vi) |
| Khi tín hiệu ngữ cảnh mất | Mất khi đang chạy: tốc độ `None`, coi là đang chạy, không bao giờ là tốc độ cao, không bao giờ là đứng yên; tài xế và backend được báo (`can_sim.py:195-213`, `vehicle_context.py:48-51`). Mất khi đang đỗ, hoặc chưa từng có tín hiệu: coi là đỗ ở 0 km/h, tức không cảnh báo nào cho tới khi có tốc độ. Đúng với thiết kế đã ghi (FMEA dòng 2). Giờ trong ngày lấy từ đồng hồ máy cộng thời gian frame, không phụ thuộc xe |
| Trip memory: đặt lại giữa các chuyến | Mỗi chuyến là một `TripRuntime` mới: bản web dừng agent sau "Kết thúc chuyến" (`frontend/src/live/agent.ts:452-460`), thiết bị kết thúc cùng tiến trình (`edge_agent/main.py:340`). Không có trạng thái nào của khối 9–12 sống qua hai chuyến |
| Rò dữ liệu giữa tài xế | `change_driver` dựng lại khối 7, 8, 11 (trip memory), 12 và đăng ký. Còn lại qua tài xế: thời gian lái (H4), bản tổng kết cả chuyến (cố ý, có đếm `driver_changes`), bộ đếm mẫu (M1) |
| Tăng trưởng vô hạn | Không đáng kể (L3) |
| Lưu gì lên đĩa | Khối 9–12 không ghi gì. Thứ duy nhất xuống đĩa là hàng đợi của khối 14 (`publisher.outbox_path`), chứa JSON metadata; ngoài phạm vi, audit 1 và `test_no_frame_writes.py` đã kiểm |
| Hai nhánh có ăn đè nhau không | Mức: không, lấy mức cao nhất và giữ mọi hit. Tiếng và sự kiện: có, M3. "Tạm ngưng" xoá hit của cả hai nhánh, kể cả `drowsy_score` dựa trên 60 s trước đó (cố ý, FR-6) |
| Đồng hồ nhảy | Giờ lùi 100 s khi L2 đang bật: không lỗi, mức hạ sau 3 s theo giờ mới; cooldown kéo dài thêm đúng khoảng lùi. Giờ nhảy tới: hai frame hai bên chỗ nhảy đủ để xác nhận tăng (L5). Cả hai nguồn giờ đều đơn điệu (audit 2) |
| Số liệu trong `eval/results` có khớp code hiện tại không | Khớp ở phần kiểm được. `tools/uta_rldd.py tradeoff` chạy lại trên working tree cho đúng từng số của `uta_rldd_tradeoff.md` (0,98 / giờ, 15 / 24, 12 / 24; bảy dòng dev). Test hồi quy trace (36 video) pass. Lý do: thay đổi chưa commit ở khối 9 và pipeline chỉ chạy trong bước nhắm mắt của đăng ký, mà mọi eval tắt đăng ký hoặc trao hồ sơ thẳng cho khối 7, 8. Phần còn lại ở mục 4 |

### 3.7 Tài liệu lệch code

Bốn chỗ của `docs/risk_engine_spec.md` (dòng 41, 32, 52, 74) và docstring `risk_engine.py:7`, `30-31` đã có ở audit 2
mục L7, không lặp lại. Bổ sung:

| Tài liệu | Ghi | Code / YAML hiện tại |
|---|---|---|
| `docs/risk_engine_spec.md:18-25` | `assess(d, x, ctx, trip, drowsy_muted)`; `RiskAssessment` không có lý do tạm ngưng | Có thêm tham số `quality` và trường `unavailable_reason` (`risk_engine.py:168-176`, `107-109`) |
| `docs/risk_engine_spec.md:28-35` | Bảng luật không có `unresponsive` | Luật L3 thứ hai từ M44 (`risk_engine.py:188-189`, `thresholds.yaml:466-467`) |
| `docs/risk_engine_spec.md:55-59` | "Tạm ngưng" chỉ khi mất mặt ≥ 3 s, một ngoại lệ `head_drop` | Thêm: mặt không đọc được ≥ 5 s, và ngoại lệ `turned_away` (`risk_engine.py:221-235`) |
| `edge_agent/decision/alert_manager.py:13-14`, `docs/safety-fmea.md:298` | "Mức cao hơn luôn được phát" | Lần nâng mức vẫn qua cooldown của chính mức đó (`alert_manager.py:147-149`): L2 cùng lý do trong 30 s bị giữ lại, kể cả khi đi lên từ L1 |
| `docs/safety-fmea.md:270-271` | Sau khi dừng, "khi xe chạy lại thì mọi luật hoạt động bình thường" | Bằng chứng gom lúc dừng ngắn được mang sang (H1) |
| `docs/pilot-readiness.md:3` | "Cập nhật: 06/10/2026 (M53...)" | Dòng A1 đã có số của M69 (08/10) |
| `edge_agent/decision/pipeline.py:161-163` | Nạp ngưỡng khi đỗ "không giữ gì mà cảnh báo phụ thuộc vào" | Chỉ đúng với lần nghỉ; "đỗ" ở đây là dưới 1 km/h (M5) |
| `config/thresholds.yaml:469` | "total 0..100" | Đúng cho tổng trọng số; sau hệ số ngữ cảnh là tối đa 144 trước khi cắt |

## 4. Không kiểm tra được, và vì sao

| Việc | Vì sao | Cách kiểm chứng |
|---|---|---|
| Tần suất thật của H1 (nhắm mắt ở đèn đỏ) và H2 (điểm dao động quanh ngưỡng) | Mọi trace là người ngồi trước camera ở tốc độ giả cố định, không có lần dừng | Bản tự ghi có kịch bản dừng 30–60 s; đếm số lần điểm cắt qua `l1` trên trace UTA-RLDD video `0` và `5` |
| Hệ số đêm / lái lâu có tăng độ nhạy đúng lúc cần không | UTA-RLDD không có giờ ghi hình và video chỉ 10 phút; phép quy đổi ở H4 chỉ cho phía báo sai, trên dev | Thêm tuỳ chọn giờ / thời gian lái cho `tools/uta_rldd.py`; chuyến dài thật (đang hoãn) |
| Số ở H4 trên 24 người giữ riêng | Cố ý không đọc: tập giữ riêng chỉ được đọc ở ngưỡng hiện tại | Anh quyết định có đọc một lần với ngưỡng quy đổi hay không |
| Ảnh hưởng của mọi đề xuất lên báo sai / giờ | Audit không sửa code | Chạy lại `tools/uta_rldd.py tradeoff` và test hồi quy trace sau mỗi thay đổi |
| `eval/results/dataset_uta_rldd.md` mục 1–8 và các `dataset_*.md` khác có khớp từng số không | Chỉ chạy lại `tradeoff` (2,5 phút); các báo cáo còn lại cần video hoặc nhiều lần replay, và không được ghi đè `eval/results` | Chạy `tools/uta_rldd.py report --out` ra thư mục tạm rồi `diff` |
| Tốc độ khối 9–12 trong Pyodide và trên QCM6125 | Chỉ đo Python gốc trên Mac; không còn thiết bị | `tools/bench_web.py`; máy cùng chip |
| Tiếng cảnh báo có phát đúng theo `new_alert` trên giao diện không | Chỉ đọc `frontend/src/hud/HudScreen.tsx` (dòng 97-107, 144), không chạy giao diện | Mở `#/live`, lặp lại ca của H3 và nghe |
| Backend gắn bản tổng kết cho tài xế nào sau "Đổi tài xế" | Ngoài phạm vi, chưa đọc backend | Đọc chỗ nhận `summary` ở `backend/app.py`; thử một chuyến có đổi tài xế |
| Dashboard có cho chỉnh khoá `context.*` / `quality.*` không (M5) | Chưa đọc hết backend và trang chỉnh ngưỡng | Xem danh sách khoá trang đó gửi; thử ghim một phiên bản có `context.rest_after_s` |
| Tín hiệu xe thật (CAN): độ trễ, nhiễu, mất tín hiệu từng lúc | Chỉ có bộ giả lập; `ExternalVehicle` được đọc code và thử hai ca mất tín hiệu | Cần nguồn tốc độ thật (đã bỏ khỏi kế hoạch 08/10) |
| Luật xi nhan trên chuyến thật | Không có trace nào có xi nhan | Bản tự ghi có bấm xi nhan qua `tools/drive_sim.py` |
| `docs/workflow/*.jpg` có khớp bảng luật hiện tại không | Chỉ đối chiếu spec, FMEA, improvements, pilot-readiness và docstring; chưa đọc lại ảnh | Mở `workflow_full_4.jpg` so với mục 3.6 |
