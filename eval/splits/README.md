# Quy tắc chấm UTA-RLDD (đặt trước lần chấm sau)

Đặt ngày 08/10/2026 (M70), sau khi tập test đã được đọc nhiều lần (xem "Nhật ký"). Quy tắc nằm ở đây, trước khi có
kết quả mới, để việc chọn cách đếm không phụ thuộc vào đáp án. Muốn đổi một quy tắc: sửa file này **trước** khi chạy,
ghi ngày và lý do, và áp cho cả dev lẫn test.

## 1. Chia người

- `uta_rldd_dev.txt`: 24 người (fold 1–2). Chỉ tập này được dùng để dò hoặc chọn ngưỡng.
- `uta_rldd_test.txt`: 24 người (fold 3–4). Chỉ đọc số ở ngưỡng đã chọn; không quét, không dò, không so nhiều cấu hình
  rồi chọn cái tốt nhất.

## 2. Video nào được tính

- **Số chính tính mọi video.** Không video nào bị loại khỏi số chính vì kết quả của nó.
- Video quay dưới `eval.min_video_fps` (15 FPS, cam kết ở CLAUDE.md) nằm ngoài vùng làm việc. Chúng **vẫn nằm trong số
  chính**, và báo cáo luôn in thêm một bảng "Frame rate of the video" tách hai nhóm (từ 15 FPS trở lên, dưới 15 FPS).
  Bỏ video sau khi đã thấy kết quả là chọn dữ liệu theo đáp án, nên không làm.
- Tỉ lệ frame có mặt tin cậy thấp (< 80 %): chỉ được liệt kê trong báo cáo. Chưa có ngưỡng loại, vì chưa có ngưỡng nào
  được chọn trên dev. Muốn loại theo tiêu chí này: chọn ngưỡng trên dev, ghi vào file này, rồi mới chạy test.
- FPS của một video lấy từ container (số frame / FPS). Chưa kiểm video có tốc độ khung thay đổi hay không.

## 3. Cái gì gọi là "báo sai / giờ"

Ba cách đếm trên video `0` luôn đi cùng nhau và luôn gọi đủ tên; không dẫn riêng một số mà bỏ tên của nó:

| Tên | Đếm gì | Giờ chia |
|---|---|---|
| Báo sai **nhánh buồn ngủ** / giờ, sau 30 s đầu | cảnh báo buồn ngủ sau `eval.warmup_s` | giờ đã chấm (bỏ 30 s đầu) |
| Báo sai nhánh buồn ngủ / giờ, **cả video** | cảnh báo buồn ngủ, cả 30 s đầu | giờ cả video |
| Báo sai **mọi nhánh** / giờ, cả video | buồn ngủ + mất tập trung + khác, cả 30 s đầu | giờ cả video |

- Chỉ dòng thứ ba được đặt cạnh chỉ tiêu PRD (≤ 1,0 / giờ, tính cả cận trên CI), vì PRD tính mọi cảnh báo.
- Dòng thứ ba xấu có lý do: người ngồi trước laptop nhìn xuống màn hình, nên nhánh mất tập trung (`off_road`) báo "đúng"
  theo luật nhưng bị tính là sai. Đọc nó cùng dòng thứ nhất, không thay thế nhau, và không tách riêng nhánh nào ra rồi
  coi đó là kết luận.
- Số 0,98 / giờ (M53, M69) là dòng **thứ nhất**, trên tập test.
- 30 s đầu được đếm ở **cả hai phía** cùng một quy tắc: báo sai và "video `10` có cảnh báo" đều có cả hai cách đếm trong
  báo cáo (mục 2 và mục 5).

## 4. Ngoài phạm vi của quy tắc này

- Số này không thay được giờ lái thật có nhãn (0 giờ). Người ngồi trước laptop, không lái xe, không đăng ký khuôn mặt,
  không có cổng chất lượng frame, ban ngày, tốc độ giả lập 60 km/h.
- Quyết định `risk.drowsy.l1` 40 → 50 **không** được chốt trên tập test hiện tại: nó đã được đọc nhiều lần. Cần dữ liệu
  mới (DROZY có ở `data/drozy`, chưa dùng) hoặc chia lại theo k-fold khai báo trước.
  **09/10 (M101):** đã quyết trên DROZY bằng luật viết trước khi chạy, [`drozy_l1_rule.md`](drozy_l1_rule.md): giữ 40
  (kết quả ở `eval/results/drozy_l1.md`).

## 5. Nhật ký đọc tập test

`uta_rldd_test_reads.tsv`: `tools/uta_rldd.py` tự thêm một dòng mỗi lần chạy đọc 24 người giữ riêng (`report` /
`signals` / `compare` với `--split test` hoặc `all`, `tradeoff`, `personal`), **trước** khi chấm, nên lần chạy lỗi cũng
có dòng. Không có cờ tắt. Khi trích một số trên test, ghi kèm số lần đã đọc.

Trước khi có nhật ký, lấy từ tài liệu (không có giờ, không có commit; ít nhất là thế):

| Lần | Ở đâu | Đọc gì |
|---|---|---|
| 1 | M53 (06/10) | ngưỡng lúc đó và cấu hình B, mỗi cái một lần |
| 2 | sau M54 (06/10) | chấm lại với `eye_state.low_light_brightness: 0` (`dataset_uta_rldd.md` mục Status) |
| 3 | M69 (08/10) | `tradeoff`, `report --split test` |
| 4 | audit A5 (08/10) | `report --split test`, `tradeoff` (`docs/audit-5-eval-tests.md` H3) |

Các lần từ M70 trở đi nằm trong file `.tsv`.
