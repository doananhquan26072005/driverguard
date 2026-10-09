# Luật quyết định `risk.drowsy.l1` 40 hay 50 trên DROZY (khai báo trước khi chạy)

Viết ngày 09/10/2026 (M101), **trước** khi hệ thống được chạy trên DROZY để lấy bất kỳ số nào của nhánh buồn ngủ.
Trước đó DROZY chỉ được dùng một lần, ở M83, để đo vị trí khuôn mặt trong khung (không có điểm buồn ngủ, cảnh báo
hay nhãn KSS nào được đọc). File này không được sửa sau khi có kết quả; nếu phải sửa thì ghi ngày, lý do, và kết
quả của lần chạy trước không còn được dùng để quyết.

## 1. Vì sao cần luật này

Trên 24 người dùng để dò của UTA-RLDD, `l1` 50 giảm báo sai nhánh buồn ngủ 5 → 2 nhưng làm 2 / 24 người buồn ngủ mất
cảnh báo (M53, M69). Tập giữ riêng của UTA-RLDD đã được đọc nhiều lần nên không còn là kiểm tra độc lập
(`eval/splits/README.md` mục 5). Anh chốt ngày 09/10: giữ 40, và quyết bằng DROZY với luật khai báo trước.

## 2. Dữ liệu và nhãn

- DROZY (ULg, `data/drozy`): 14 người, mỗi người tối đa 3 bài PVT 10 phút, camera hồng ngoại Kinect v2 cố định,
  người ngồi trước màn hình, không lái xe. 36 video có trên đĩa. Tất cả được chạy; không video nào bị loại vì kết quả.
- Nhãn là điểm KSS tự đánh giá của từng bài (`KSS.txt`), một nhãn cho cả video:
  - **tỉnh**: KSS ≤ 4;
  - **buồn ngủ**: KSS ≥ 7;
  - KSS 5–6: được báo cáo riêng, không vào quyết định.
- Bài 2 và 3 của người 1–8 quay 15 FPS (lỗi ghi hình của bộ dữ liệu); vẫn được tính, và được báo thêm một dòng riêng.

## 3. Cách chạy

- Khối 2–6 chạy một lần trên mỗi video (không model điện thoại, tốc độ giả lập 60 km/h, trạng thái mới cho mỗi video,
  12:00, chưa lái, không đăng ký khuôn mặt), lưu số từng frame, không lưu ảnh.
- Khối 7–12 replay với `config/thresholds.yaml` của ngày chạy, ở **đúng hai** giá trị: `risk.drowsy.l1` = 40 và 50.
  Không giá trị nào khác được thử, không ngưỡng nào khác được đổi.
- **Đường quyết định là đường `web`** (khối 5 đọc `eyeBlink`, như trang `#/live`, là sản phẩm). Đường `device` (CNN mắt)
  được báo cáo cạnh đó, không vào quyết định.
- Cách đếm như UTA-RLDD (`eval/splits/README.md` mục 3): cảnh báo **nhánh buồn ngủ** sau 30 s đầu của video. "Video có
  cảnh báo" = có ít nhất một cảnh báo như vậy.

## 4. Điều kiện để DROZY được phép quyết (kiểm ở `l1` = 40, đường `web`)

Chỉ cần một điều kiện không đạt thì kết luận là **"DROZY không quyết được; giữ 40"**, và không xét mục 5:

- G1. Trung vị tỉ lệ frame có mặt tin cậy trên các video ≥ 80 %.
- G2. Có ít nhất 1,5 giờ video tỉnh được chấm và ít nhất 8 video buồn ngủ.
- G3. Điểm buồn ngủ trung bình của video tách được hai nhóm: AUC (buồn ngủ so với tỉnh) ≥ 0,65. Camera của DROZY là
  hồng ngoại, nơi khối 5 quyết định mọi frame; nếu điểm không mang tín hiệu ở đây thì đếm cảnh báo trên nó không nói
  được gì về ngưỡng.

## 5. Luật quyết định

Gọi F40, F50 là số báo sai trên video tỉnh; D40, D50 là số video buồn ngủ có cảnh báo.

**Đổi sang 50 khi và chỉ khi cả hai điều sau đúng:**

1. F50 ≤ F40 / 2 **và** F40 − F50 ≥ 3 (giảm ít nhất một nửa và ít nhất ba lần báo sai);
2. D50 ≥ D40 − 1 (mất nhiều nhất một video buồn ngủ có cảnh báo).

Mọi trường hợp khác: **giữ 40**. Luật nghiêng về giữ nguyên có chủ ý: giá trị đang chạy là 40, và bỏ sót người buồn
ngủ là lỗi nặng hơn một tiếng chuông L1.

## 6. Cái luật này không nói được

- Không phải dữ liệu lái xe, không phải camera màu của sản phẩm (webcam), 14 người. Kết quả là một phiếu cho quyết
  định `l1`, không phải số đo chỉ tiêu PRD.
- Chạy đúng một lần. Số của lần chạy được ghi ở `eval/results/drozy_l1.md` cùng với việc từng điều kiện đạt hay không.
