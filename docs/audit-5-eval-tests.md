# Audit 5: công cụ đánh giá, số liệu, test và CI

Ngày 08/10/2026, trên working tree của nhánh `DAQuan` (có thay đổi chưa commit của M68 và M69, coi là trạng thái hiện
tại). Chỉ đọc và phân tích: không sửa code, config hay `eval/results`. Phạm vi: `tools/`, `eval/`, `tests/`,
`.github/workflows/ci.yml`, `notebooks/`, các nhánh dataset, và các tài liệu dẫn số (`report.md`, `pilot-readiness.md`,
`release-v3.md`).

Cách kiểm:

- Đọc code, test, config và tài liệu. Chạy `pytest tests/test_edge_agent tests/test_backend`: **988 pass trong 48 s**,
  không test nào bị bỏ qua trên máy này; `pytest tests/ --collect-only`: 993 test; `ruff check` và `ruff format --check`
  trên bốn thư mục của CI: sạch.
- "Thử trong audit": chạy lại ba phép replay trên trace đã lưu, **chỉ in ra thư mục tạm ngoài repo, không dùng `--out`**:
  `tools/uta_rldd.py report --split test`, `tools/uta_rldd.py tradeoff`, `tools/seq_eval.py fl3d --replay block5`. Sau
  khi chạy, `git status eval/` không đổi. Thêm một script ngoài repo đếm cảnh báo trong 30 s khởi động và FPS của từng
  video UTA-RLDD.
- Mở các file trace (`data/eval_traces/`, `data/own_traces/`, `tests/fixtures/regression/traces.npz`) để xem chúng có
  chứa ảnh không.
- Không trace lại video nào, không tải dataset, không chạy e2e hay test frontend.

Quy ước: "đường thiết bị" là `edge_agent.main` chạy Python, nguồn điểm mắt `eye_state.source: cnn`. "Đường web" là
`#/live` (code dự kiến bọc thành APK), nguồn điểm mắt `blendshape`. Công sức: S dưới nửa ngày, M một đến hai ngày, L hơn.
"Trùng" nghĩa là `docs/improvements.md`, `docs/pilot-readiness.md` hoặc bốn audit trước đã có; khi đó chỉ ghi phần bổ sung.

## 1. Tóm tắt

1. **Công cụ tính đúng và lặp lại được trên trace đã lưu.** Replay trong audit cho ra đúng từng số của UTA-RLDD đang
   ghi trong báo cáo (4 lần sai, 0,98 / giờ, 15 / 24, 12 / 24, bảng đánh đổi). Tách dev / test theo người là thật, dò
   ngưỡng không chạm tập test. Không tìm thấy ảnh, dataset hay secret nào trong repo.
2. **Các số đó đo một thứ hẹp hơn tên gọi của chúng.** "0,98 báo sai / giờ" là riêng nhánh buồn ngủ, trên đường thiết
   bị, người ngồi trước laptop, không có nhánh mất tập trung, không có model điện thoại, không có cổng chất lượng frame,
   bỏ 30 s đầu. Sản phẩm là đường web với nguồn điểm mắt khác; chưa có số nào trên dataset cho đường đó (H1, H2).
3. **Kết luận trên tập giữ riêng đứng trên một người.** Cả 4 lần sai của tập test là của một video quay 12 FPS, dưới
   mức 15 FPS mà hệ thống cam kết; 13 / 145 video dưới 15 FPS. Tập test đã được đọc nhiều lần, nên quyết định ngưỡng
   tiếp theo không còn tập nào chưa nhìn (H3).
4. **Tài liệu dẫn số đã cũ ở những dòng dùng để quyết định.** `report.md` mục 2.2 và `pilot-readiness.md` A1, A3 còn
   số FL3D trước M53 / M54: replay hôm nay cho L3 77 / 95 (báo cáo ghi 75 / 95) và L1 sai 2,3 / giờ (báo cáo ghi 4,6).
   A2 dẫn 11 lần của M52 trong khi `own_recordings.md` có 59 lần, chỉ 64 % được trả lời (H4).
5. **Nhận định chung:** số liệu đủ tin để *so sánh hai cấu hình* trên cùng trace và để nói "điểm buồn ngủ đi đúng
   hướng". Chưa đủ để nói hệ thống đạt hay không đạt chỉ tiêu báo sai, và không đủ để quyết định chạy thử trên xe: chưa
   có giờ lái bình thường nào có nhãn, và quyết định 08/10 (bỏ hub và xe thật) đã bỏ luôn việc sẽ tạo ra số đó.

## 2. Bảng ràng buộc

| Ràng buộc | Kết luận | Bằng chứng |
|---|---|---|
| Frame không ghi ra đĩa (phần tools và test) | Đạt | Quét tĩnh `tests/test_edge_agent/test_no_frame_writes.py:53-64` gồm cả `tools/`. Trace mở trong audit chỉ có mảng số một chiều (UTA, FL3D, bản tự ghi); `3mdad_phone.pkl` có mảng hai chiều tối đa 3 840 phần tử (hộp phát hiện). `tools/record_trace.py:531` từ chối lưu trường lạ. Giới hạn của phép quét ở L2 |
| Không commit dữ liệu, ảnh mặt, secret | Đạt | `.gitignore:32-33` (`data/`, `*.db`), `:66` (`kaggle.json`). File nhị phân duy nhất của eval trong repo là `tests/fixtures/regression/traces.npz` (17 cột float32, 17 763 dòng). Lịch sử git không có `.pkl`, video hay `.db`. Notebook Kaggle không có output, token đọc từ Kaggle Secrets |
| Chỉ model pretrained | Đạt | `tools/` không có vòng huấn luyện; `tools/download_models.py:27-41` chỉ tải và xuất model có sẵn |
| ≥ 15 FPS | Không chắc | CI không đo FPS. Số có sẵn đều của Mac (`report.md:184-189`). 13 / 145 video UTA-RLDD có FPS nguồn dưới 15 (M3). Kiểm chứng: cần thiết bị đích, đã bỏ 08/10 |
| Chống false positive ngang độ chính xác | Không chắc | Thước đo có đủ (báo sai / giờ kèm CI, FAR / MAR, theo người): `tools/metrics.py:109-143`, `:182`, `:243`. Dữ liệu thì không: 0 giờ lái bình thường có nhãn, và số tốt nhất chỉ là một nhánh (H2) |
| Ngưỡng nằm trong `thresholds.yaml` | Đạt ở logic, một phần ở tools | Grep các phép so sánh với hằng số trong `edge_agent/analysis`, `decision`, `context`, `eye_state.py`, `quality.py`, `enrollment.py`: không thấy. Tools còn vài hằng số (M6). Không có test tự động chặn hardcode, chỉ chặn khoá lạ (`test_config_strict.py:52-76`) |
| Logic thời gian test được bằng chuỗi số giả | Đạt | Khối 7: `test_drowsiness.py` (58 test), `test_drowsy_signals_v2.py`, `test_gaze_down.py`; khối 8: `test_distraction.py`, `test_m38_distraction.py`; khối 9, 11, 12: `test_decision.py` (52), `test_m44_unresponsive.py`, `test_m4_scenarios.py`; khối 10: `test_context.py`. Không test nào cần video hay dataset ngoài |
| Tách dữ liệu dò ngưỡng với dữ liệu báo cáo | Đạt với UTA-RLDD, vi phạm với phần còn lại | `eval/splits/uta_rldd_{dev,test}.txt` (24 + 24 người, không trùng); `tools/uta_rldd.py:1367-1368` lưới chỉ đọc dev. FL3D, YawDD, SUST, bản tự ghi vừa dùng để chỉnh vừa dùng để báo cáo (trùng `improvements.md:832-833`) |
| Chạy lại ra cùng số | Đạt với replay, không chắc với trace | Replay trong audit khớp từng số. Trace lại thì không đảm bảo (M1) |
| Mỗi lần một mốc, cập nhật roadmap | Đạt | `docs/roadmap.md:1232-1261` (M68, M69) khớp với diff chưa commit |

## 3. Phát hiện

Không có phát hiện Critical: không thấy lỗi tính toán nào làm sai số đã công bố, và không thấy rò rỉ dữ liệu. Các mục
High đều về việc số liệu được hiểu rộng hơn cái chúng đo.

### High

**H1. Mọi số trên dataset đo đường thiết bị; sản phẩm là đường web** (trùng một phần `improvements.md` việc 8, bổ sung phạm vi)

- Vấn đề: replay lấy nguồn điểm mắt từ `eye_state.source` của yaml, tức `cnn` (`tools/seq_eval.py:367-369`,
  `config/thresholds.yaml:55`). Đường web ép `source: blendshape` (`edge_agent/web/bridge.py:72`) với bộ ngưỡng riêng
  (`thresholds.yaml:208-212`, `:247`), MediaPipe bản JS và phép giải góc đầu bằng numpy. Trace UTA-RLDD được tạo bằng
  MediaPipe Python 1.0.1.
- Bằng chứng thêm: `improvements.md:407` ghi replay FL3D theo đường `eyeBlink` cho 64 / 95 lần đạt L3, đường thiết bị
  74 / 95. Fixture hồi quy trong CI cũng chỉ ghim đường `cnn` (`tools/regression_traces.py:45-46`, `:135`: `check` dùng yaml).
- Hậu quả: 0,98 báo sai / giờ, 15 / 24, 75 / 95 không phải số của thứ sẽ chạy trên màn hình xe. Một thay đổi ngưỡng
  `blendshape_*` không làm đỏ test hồi quy nào.
- Đề xuất: thêm cột "đường web" vào `tools/uta_rldd.py` và `seq_eval` bằng `--set eye_state.source=blendshape` (cột
  `blink` đã có trong mọi trace), báo hai đường cạnh nhau; ghim thêm một bộ kết quả `blendshape` trong fixture hồi quy.
  Đây là việc mới, cần anh quyết định thành mốc.
- Công sức: M. Tác động false positive: chưa biết chiều; đây chính là điều chưa đo.

**H2. "0,98 báo sai / giờ" là một nhánh, trong điều kiện đã bỏ bớt các nguồn báo sai** (trùng `improvements.md` phụ lục A, bổ sung ba điểm)

- Vấn đề: số này chỉ đếm nhánh buồn ngủ (`tools/uta_rldd.py:580`), cảnh báo mất tập trung "tính riêng vì người ta nhìn
  laptop" (`dataset_uta_rldd.md:17-18`). Ba điểm chưa ghi ở đâu:
  1. Trace UTA-RLDD không có cột chất lượng frame và mống mắt (đã mở `F4_S44_0.pkl.gz`: thiếu `scene_bright`,
     `sharpness`, `iris_y_*`). Replay coi NaN là "không có vấn đề" (`tools/seq_eval.py:377-378`), nên cổng "tạm ngưng
     giám sát" của M43 và hướng mắt của M55 không hề chạy trong các số này.
  2. Model điện thoại tắt, tốc độ cố định 60 km/h lúc 12:00 (`tools/seq_eval.py:384`): luật ngữ cảnh, đỗ, xi nhan không
     được thử.
  3. Cảnh báo trong 30 s đầu bị loại khỏi tử số và mẫu số (`tools/uta_rldd.py:401-404`); tài xế thật vẫn nghe chúng.
     Dev có 1 lần như vậy.
- Bằng chứng về độ lớn: nhánh bị loại là nguồn báo sai chính ở mọi bộ khác: SUST 24 / 26 lần là `off_road`
  (`report.md:113`), YawDD 10 dự đoán `off_road` đều sai (`dataset_yawdd.md` bảng đầu), tức 6,9 đến 8,5 / giờ.
- Hậu quả: đặt 0,98 cạnh chỉ tiêu PRD "≤ 1,0 / giờ" (`pilot-readiness.md:22`, `report.md:174`) khiến người đọc hiểu là
  hệ thống gần đạt. Chỉ tiêu PRD tính mọi cảnh báo.
- Đề xuất: đổi tên dòng thành "báo sai nhánh buồn ngủ / giờ" ở mọi chỗ dẫn; thêm một dòng "tổng mọi nhánh, kể cả 30 s
  đầu" ngay bên cạnh, kể cả khi nó xấu. Ghi rõ ba điều kiện trên ở đầu `dataset_uta_rldd.md`.
- Công sức: S (chỉ sửa báo cáo và công cụ in). Tác động false positive: không đổi hệ thống; đổi cách hiểu con số.

**H3. Kết quả trên tập giữ riêng đứng trên một người, và tập đó đã hết "lần nhìn đầu"**

- Vấn đề và bằng chứng (thử trong audit):
  - Cả 4 lần sai của test là của F4_S44, video `0` quay 12,06 FPS; 23 người còn lại 0 lần. Đã ghi ở M69. Phần chưa ghi:
    FPS nguồn dưới 15 ở 13 / 145 video (dưới 25 ở 33), gồm cả ba video của S44 và S45. Hệ thống cam kết ≥ 15 FPS, nên
    các video này nằm ngoài vùng làm việc.
  - Bỏ video dưới 15 FPS thì test còn 0 lần sai. Không được làm vậy sau khi đã nhìn kết quả: đó là chọn dữ liệu theo
    đáp án. Nhưng nó cho thấy kết luận "đạt hay không" đổi theo một quy tắc lọc chưa từng được định trước.
  - Tập test đã được chấm ở M53 (hai cấu hình), chấm lại sau M54, đọc lại ở M69 và trong audit này. Không lần nào dùng
    để chọn ngưỡng, nhưng `tools/uta_rldd.py compare --split test --set ...` chạy được tự do (`:1370-1373`), không có
    gì ngăn hay ghi lại lần đọc.
- Hậu quả: quyết định còn ngỏ `risk.drowsy.l1` 40 → 50 (`uta_rldd_tradeoff.md:23`) không còn tập nào chưa nhìn để
  kiểm. Khoảng tin cậy theo người (0,00–3,02) đã nói đúng điều này bằng số.
- Đề xuất: (a) viết quy tắc loại video (FPS, tỉ lệ mặt tin cậy) vào `eval/splits/` trước lần chấm sau, áp cho cả dev
  và test; (b) ghi mỗi lần chạy trên test vào một file nhật ký trong `eval/splits/`; (c) quyết định tiếp theo cần dữ
  liệu mới (DROZY đã có ở `data/drozy`, chưa dùng) hoặc chia lại theo k-fold có khai báo trước.
- Công sức: S cho (a), (b); L cho (c). Tác động false positive: không đổi hệ thống; tránh chốt `l1` trên số lạc quan.

**H4. Số FL3D và số bản tự ghi trong tài liệu quyết định đã cũ so với ngưỡng hiện tại**

- Bằng chứng (replay FL3D trong audit với `thresholds.yaml` hôm nay, `--replay block5`):

  | Dòng | `report.md:61,72-74` và `pilot-readiness.md:22,24` | Replay hôm nay |
  |---|---|---|
  | Nhắm ≥ 1,5 s đạt L3 | 75 / 95 (78,9 %) | 77 / 95 (81,1 %) |
  | L1: tổng / đúng / sai, sai mỗi giờ | 9 / 7 / 2, 4,6 (0,56–16,7) | 10 / 9 / 1, 2,3 (0,06–12,9) |
  | L2: tổng / đúng / sai | 16 / 11 / 3 | 16 / 13 / 3 |
  | L3: tổng / đúng / sai | 83 / 81 / 1 | 85 / 83 / 1 |

  `dataset_uta_rldd.md:143-144` đã tự ghi "the stored reports were not regenerated". `report.md:3` vẫn nói mọi số "đo
  ngày 25–26/09 với `thresholds.yaml` hiện tại". `dataset_fl3d.md` và `dataset_sust_ddd.md` có ngày 01/10, các báo cáo
  ảnh đơn 24/09; từ đó `thresholds.yaml` đổi ở M53, M54, M56.
- Bản tự ghi: `pilot-readiness.md:23` (A2) dẫn "ngủ gật p95 1,67 s (11 lần)" của M52. `own_recordings.md:28` hiện có 59
  lần nhắm ≥ 1,5 s, **38 lần được trả lời (64 %)**, p95 2,03 s. Tỉ lệ 64 % không xuất hiện trong `pilot-readiness.md`
  hay `report.md`. Không chắc vì sao thấp (các phiên `dark`, `dark_low` có 0 cảnh báo, có thể do cổng chất lượng); kiểm
  chứng bằng cách tách bảng đó theo phiên.
- Lỗi phụ dễ gặp: `tools/seq_eval.py fl3d` không có `--replay` in kết quả **lúc trace** (26/09), không phải ngưỡng hôm
  nay, và cho 65 / 95. Không có cảnh báo nào trong output.
- Hậu quả: A3 và A1 được đọc để quyết định; số đúng hôm nay tốt hơn ở L1 và A3, nhưng không ai biết nếu không chạy lại.
- Đề xuất: sinh lại `dataset_fl3d.md`, `dataset_yawdd.md`, `dataset_sust_ddd.md` rồi sửa `report.md` 2.2, 2.3 và
  `pilot-readiness.md` A1–A3. Việc này ghi đè `eval/results`, nên cần anh cho phép. Thêm vào mỗi báo cáo một dòng
  nguồn gốc (xem M1) để lần sau nhìn là biết cũ.
- Công sức: S. Tác động false positive: không đổi hệ thống.

### Medium

**M1. Nguồn gốc của trace và báo cáo không nằm trong trace, không nằm trong repo**

- Bằng chứng: trace chỉ có `alerts, cols, events, fps, n` (đã mở). Thông tin chạy nằm ở
  `data/eval_traces/uta_rldd/kaggle/session*_run_info.json`, bị gitignore: Python 3.13, MediaPipe 1.0.1, OpenCV 4.14,
  numpy 2.1.3; máy dev là 3.12, 0.10.21, 4.11, 1.26.4. `dataset_uta_rldd.md:10` ghi code ở commit `e57632c`, nhưng
  commit đó không có `tools/uta_rldd.py` (`git cat-file -e e57632c:tools/uta_rldd.py` báo không tồn tại): code chạy trên
  Kaggle là một file zip gồm commit đó cộng phần chưa commit. Cột của trace khớp `seq_eval.py` của `e57632c`, nên khối
  2–6 đúng là của commit đó.
- Các chỗ không ghim phiên bản: `requirements.txt:6-13` dùng `>=`; `tools/download_models.py:29-32` tải
  `face_landmarker` kênh `latest`, không checksum; YOLO xuất bằng `ultralytics` không ghim (`:45-53`);
  `tools/dataset.py:119` tải dataset Kaggle không ghim phiên bản. Báo cáo sinh ra không có dòng nào ghi commit, mã băm
  của `thresholds.yaml`, ngày chạy.
- Hậu quả: replay lặp lại được (đã thử), trace lại thì không chắc ra cùng số; không ai ngoài máy này kiểm được số UTA.
- Đề xuất: ghi `meta` (commit, bẩn hay sạch, phiên bản thư viện, sha256 model, mã băm thresholds) vào từng trace và in
  ở đầu mỗi báo cáo; commit `run_info.json` và `index.csv` (chỉ số, không ảnh) vào `eval/`; thêm checksum cho
  `face_landmarker.task` (sha256 đã có trong `run_info.json`).
- Công sức: M. Tác động false positive: không.

**M2. Thời gian của video = số thứ tự frame / FPS của container**

- Bằng chứng: `tools/seq_eval.py:266-275` (`tracer.step(image, i, i / fps)`), số giờ tính bằng `n / fps`
  (`tools/uta_rldd.py:360`). UTA-RLDD quay bằng điện thoại và webcam, FPS từ 12 đến 30.
- Hậu quả: nếu video có tốc độ khung thay đổi, mọi luật thời gian (nhắm 1,5 s, PERCLOS 60 s) và mẫu số giờ đều lệch.
  **Không chắc** có video nào như vậy. Kiểm chứng: so `frames / fps` với thời lượng container và đọc dấu thời gian từng
  frame (`ffprobe -show_frames`) trên vài video, trước hết F4_S44.
- Đề xuất: dùng `CAP_PROP_POS_MSEC` làm thời gian khi trace, hoặc ghi cả hai và báo độ lệch.
- Công sức: S để kiểm, M nếu phải trace lại. Tác động false positive: có thể là nguyên nhân của 2 lần L3 sai ở S44.

**M3. Video ngoài vùng làm việc được chấm như video bình thường**

- Bằng chứng: xem H3 (13 / 145 dưới 15 FPS). `dataset_uta_rldd.md:151` chỉ ghi "FPS from 12 to 30".
- Đề xuất: báo cáo tách hai nhóm (≥ 15 FPS và dưới), quy tắc định trước như H3 (a).
- Công sức: S. Tác động false positive: cho biết báo sai có dồn vào FPS thấp không; nếu có thì đó là rủi ro thật trên
  thiết bị chậm (ước lượng 10–13 FPS ở `improvements.md` phụ lục J).

**M4. Đếm bất đối xứng quanh 30 s khởi động**

- Bằng chứng: báo sai chỉ đếm sau 30 s (`tools/uta_rldd.py:580`), còn "video `10` có cảnh báo" đếm cả trong 30 s đầu
  (`:594`, `a_drowsy + a_drowsy_warm`). Thử trong audit: hiện không người nào chỉ có cảnh báo trong 30 s đầu, nên 15 / 24
  và 14 / 24 không đổi; nhưng dev có 1 lần sai và 3 lần "bắt được" nằm trong đoạn đó.
- Hậu quả: chưa sai số nào hôm nay; một thay đổi ngưỡng sau này có thể được lợi một chiều.
- Đề xuất: đếm hai phía cùng một quy tắc và in cả hai (trong và ngoài 30 s đầu).
- Công sức: S. Tác động false positive: không đổi hệ thống.

**M5. CI không bảo vệ số liệu và bỏ qua phần chạy model thật**

- Bằng chứng: `ci.yml:3-7` chỉ chạy khi push lên `main` / `develop` hoặc PR vào `main`; nhánh `DAQuan` chỉ được kiểm
  khi mở PR. CI không tải model, nên test duy nhất chạy model thật tự bỏ qua (`test_eye_state.py:115-116`); khối 3, 4, 5
  với model thật không bao giờ chạy trong CI. Không có bước đo FPS, không đo độ phủ, không lint `scripts/`. Không có
  kiểm tra nào so số trong `report.md` với công cụ.
- Điểm tốt cần giữ: test hồi quy trace (`test_trace_regression.py:30-42`) chạy trong CI, bắt được đổi ngưỡng, và mỗi
  lần ghim lại phải có lý do (4 lần, đều có).
- Đề xuất: thêm một job tải model có checksum và chạy khối 3–5 trên vài mảng số tổng hợp; thêm một test đọc
  `expected.json` kiểu "số trong báo cáo = số công cụ in" cho phần tính được từ fixture.
- Công sức: M. Tác động false positive: gián tiếp.

**M6. Kỷ luật ngưỡng: chưa có test chặn hardcode; tools còn vài hằng số**

- Bằng chứng: `test_config_strict.py` chặn khoá lạ, khoá đã dời, yaml mâu thuẫn; không có gì quét hằng số trong logic.
  Grep trong audit không thấy vi phạm ở logic. Trong tools: `tools/uta_rldd.py:438` (0.5), `:441` (0.6, trùng
  `cnn_closed` nhưng viết tay), `:695` (0.8), `:51` (các tỉ lệ PERCLOS), `tools/seq_eval.py:384` (60 km/h, 12:00).
  `tools/uta_rldd.py:1318` gọi `metrics(rows)` không truyền `cfg`, nên báo cáo cá nhân hoá dùng mặc định của dataclass
  thay vì `eval.*` trong yaml.
- `thresholds.yaml` không có số phiên bản riêng; phiên bản chỉ có ở lớp ghi đè từ dashboard
  (`edge_agent/version.py:63-68`). Báo cáo eval vì thế không dẫn được "ngưỡng phiên bản nào".
- Đề xuất: đọc các hằng số trên từ `thresholds` đã nạp; truyền `cfg` ở `:1318`; in mã băm của yaml trong báo cáo (M1).
- Công sức: S. Tác động false positive: không.

**M7. `pilot-readiness.md` không còn khớp với chính nó và với quyết định 08/10**

- Bằng chứng:
  - `:3` ghi cập nhật 06/10 nhưng A1 đã có số M69 của 08/10.
  - `:5-6` ghi "4 đạt, 6 đạt một phần, 5 chưa đạt, 9 chưa đo hoặc chưa có". Đếm bảng: 4 đạt, **9** một phần, 5 chưa
    đạt, **5** chưa đo hoặc chưa có, 1 "có số xấp xỉ" (A4).
  - `:64` (E3) liệt kê chớp chậm và nhướn mày là tín hiệu tạm "góp vào cảnh báo"; trọng số của cả hai là 0 từ M53.
  - Cột "Việc cần làm" của A1, A4, A6, C1–C5, E4 dẫn tới `improvements.md#bo-hub`, là danh sách **việc đã bỏ**
    (`improvements.md:1623-1641`). Lộ trình giai đoạn 2–4 (`:75-77`) vẫn mô tả pilot 1–3 xe.
- Hậu quả: trang trả lời "còn thiếu gì để chạy thử" đang chỉ tới những việc không ai còn làm. Câu trả lời thật là: theo
  kế hoạch hiện tại, các tiêu chí A1, C1–C5, E4 không có đường nào để đạt.
- Đề xuất: sửa số đếm và ngày; đánh dấu rõ tiêu chí nào "không còn kế hoạch đo"; quyết định giữ hay bỏ mục 2.
- Công sức: S. Tác động false positive: không.

**M8. Test dễ đỏ ngẫu nhiên**

- `tests/test_edge_agent/test_enrollment.py:331-339`: kiểm chuỗi `"1.5"` không có trong JSON của sự kiện, mà sự kiện có
  dấu thời gian thật; đã ghi là "thỉnh thoảng đỏ, chưa sửa" ở `release-v3.md:805`. Vẫn còn nguyên.
- Phụ thuộc đồng hồ thật: `test_phone_detector.py:144-149` (< 0,1 s), `test_publisher.py:170-180` (< 0,5 s),
  `test_frame_source.py:120-147`. Trên máy CI bận có thể đỏ. Trong audit cả ba đều pass.
- Đề xuất: truyền `now` cố định vào `build_enrolled_event` trong test; nới hoặc bỏ ngưỡng thời gian thật.
- Công sức: S. Tác động false positive: không.

### Low

- **L1. Nhãn UTA-RLDD** (trùng `dataset_uta_rldd.md:20-21`, bổ sung): trên test, 9 / 24 video `5` đạt L3 và 12 / 24 có
  cảnh báo. Không biết đó là ngủ gật thật hay báo sai, vì nhãn theo cả video. Mọi tỉ lệ "bắt được" trên bộ này là cận
  trên lỏng, và dòng A4 (DDAW) không nên đọc quá "có số xấp xỉ".
- **L2. Phép quét không-ghi-frame là regex theo tên hàm** (`test_no_frame_writes.py:10-17`): không bắt `np.save`,
  `pickle.dump`, `tofile` hay `.save()` của một mảng ảnh. Hiện không có vi phạm (đã mở trace). Thêm một test kiểu
  `test_fixture_holds_numbers_only` cho đầu ra của `Tracer.result` là đủ.
- **L3. Trace là pickle**, kể cả file tải từ Kaggle về (`tools/uta_rldd.py:139-147`): nạp pickle là chạy code. Chỉ là
  rủi ro trên máy dev; `.npz` như fixture thì không có rủi ro này.
- **L4. `report.md:196`** ghi "793 passed (06/10)"; hôm nay 988 (hai thư mục) và 993 (toàn bộ, khớp roadmap M69).
  `report.md:168` ghi AUC 0,924; replay hôm nay 0,920 (đã có chú thích "đổi ở chữ số thứ ba" trong
  `dataset_uta_rldd.md:227`, nhưng `report.md` không dẫn).
- **L5. Fixture hồi quy** lấy từ chính FL3D / YawDD / SUST đã dùng để chỉnh ngưỡng, không có video UTA-RLDD hay bản tự
  ghi, không có video nào có điện thoại. Đủ cho mục đích "phát hiện thay đổi", không phải bằng chứng chất lượng.
- **L6. Độ đa dạng người** (trùng `improvements.md:834`): UTA 48 người không có thuộc tính kính / giới / tuổi trong bản
  Kaggle; bản tự ghi một người, không kính; FL3D không có mã người. Không bộ nào có người Việt, camera IR, hay góc lắp
  trên xe đích.

## 4. Số liệu nào còn tin được

| Số liệu | Nguồn | Trạng thái | Vì sao |
|---|---|---|---|
| UTA-RLDD test: 4 lần sai, 0,98 / giờ (Poisson 0,27–2,51; theo người 0,00–3,02) | `dataset_uta_rldd.md` mục 8, `report.md:174` | **Còn đúng** về mặt tính toán; **phạm vi hẹp** | Replay trong audit khớp. Chỉ nhánh buồn ngủ, đường thiết bị, sau 30 s, một người gây ra cả 4 (H1–H3) |
| UTA-RLDD test: 15 / 24 có cảnh báo, 12 / 24 đạt L3 | như trên | Còn đúng; cận trên lỏng | Khớp replay. Nhãn theo cả video (L1) |
| Bảng đánh đổi `l1` 30–60 trên dev | `uta_rldd_tradeoff.md` | Còn đúng | Khớp từng dòng với replay trong audit |
| AUC `drowsy_score` 0,924 (test) | `report.md:168` | Lệch nhẹ | Hôm nay 0,920; FAR L1 1,5 % khớp; "cửa sổ ≥ L1 trên `10`" 40,8 % nay là 39,3 % |
| UTA-RLDD "trước M53": 1,96 / giờ, 17 / 24 | `dataset_uta_rldd.md` mục 1 | Không kiểm lại | Cần đặt lại ba khoá; không chạy trong audit. Đo ở `e57632c` |
| Cá nhân hoá 9 / 9 / 9 | `personalization_uta_rldd.md` | Không kiểm lại | Không chạy lại; dùng `EvalConfig` mặc định (M6) |
| FL3D: L3 75 / 95, L1 4,6 / giờ, L1 9 / L2 16 / L3 83 | `report.md:61-74`, `pilot-readiness.md:22,24`, `dataset_fl3d.md` | **Đã cũ** | Hôm nay 77 / 95, 2,3 / giờ, 10 / 16 / 85 (H4) |
| FL3D theo frame (mắt nhắm 72,1 % / 87,0 % / 7,7 %) | `report.md:51` | Lệch nhẹ | Hôm nay 71,2 % / 87,3 % / 8,1 %; ngáp và "nhắm sâu" không đổi |
| YawDD 6,9 / giờ, SUST 8,5 / giờ | `report.md:97,109` | Không đủ bằng chứng là còn đúng | `dataset_uta_rldd.md:139-140` nói "report identical" sau M53, nhưng M54 và M56 đến sau; không chạy lại trong audit |
| Ảnh đơn (MRL, yawn-eye, DDD, State Farm) | `report.md:26-32` | Cũ nhưng ít ảnh hưởng | Đo 24/09; hai dòng đo với MAR 0,6 (đã ghi chú). Không nhóm theo người; MRL là dữ liệu huấn luyện của CNN |
| Bản tự ghi: p95 1,67 s (11 lần) | `pilot-readiness.md:23` | **Đã cũ** | `own_recordings.md:28`: 59 lần, 64 % được trả lời, p95 2,03 s |
| Hiệu năng 151,8 FPS, p95 7,2 ms | `report.md:184-185`, `benchmark.md` (26/09) | Không đủ bằng chứng cho sản phẩm | Máy Mac, đường thiết bị, trước M38–M68. Không nói gì về đường web hay thiết bị đích |
| Số test: 793 | `report.md:196` | Đã cũ | 988 / 993 hôm nay |
| Bất kỳ số báo sai nào trên lái xe bình thường | – | **Không có** | 0 giờ lái có nhãn; việc tạo ra nó đã bỏ 08/10 |

## 5. Khoảng trống để chạy thử trên xe thật

So `pilot-readiness.md` với thực tế hôm nay, các điều kiện còn thiếu và không có việc nào đang mở để lấp:

1. **Giờ lái bình thường có nhãn** (A1): 0 giờ. Cần ít nhất 3,7 giờ không lần sai nào để cận trên CI ≤ 1,0 / giờ; tính
   theo người thì cần nhiều người, không phải nhiều giờ của một người.
2. **Số đo trên đường web** cho mọi tiêu chí nhóm A (H1).
3. **Thiết bị đích** (C1–C5): chưa có APK, chưa đo FPS, nhiệt, loa; tốc độ xe vẫn giả lập.
4. **Quy trình chạy thử an toàn** (E4) và giấy tờ của đơn vị vận tải (D3, D5): chưa viết / chưa điền.
5. **Ba dòng FMEA mức Cao** (B1) còn mở; hai trong số đó cần phần cứng.
6. **Quy tắc đánh giá định trước**: video nào bị loại, 30 s đầu tính thế nào, nhánh nào tính vào "báo sai" (H2, H3, M4).

Mục 6 và mục 2 làm được ngay bằng dữ liệu đang có. Mục 1, 3, 4, 5 cần quyết định ngược lại với quyết định 08/10.

## 6. Không kiểm tra được và vì sao

- **Trace lại từ video có ra cùng số không:** cần 97 GB UTA-RLDD và khoảng 16 giờ trên Kaggle; không chạy. Hệ quả:
  mọi kết luận "lặp lại được" ở đây là về replay khối 5, 7–12, không phải khối 2–6.
- **YawDD, SUST, các bộ ảnh đơn, cá nhân hoá, lưới 57 cấu hình, số "trước M53":** không chạy lại (thời gian, và các
  bộ ảnh đơn cần chạy model). Dữ liệu có sẵn trên máy (`data/kaggle` 51 GB), nên anh có thể cho chạy; lệnh không có
  `--out` thì không ghi đè gì.
- **Tốc độ khung thay đổi trong video UTA-RLDD** (M2): chưa đọc dấu thời gian từng frame.
- **Vì sao bản tự ghi chỉ trả lời 64 % lần nhắm mắt** (H4): chưa tách theo phiên.
- **CI trên GitHub có đang xanh không:** không gọi GitHub. Chỉ biết test và ruff sạch trên máy này.
- **Test frontend và e2e:** ngoài phần đã chạy; audit 4 đã chạy vitest.
- **Trên CI (không có model) có bao nhiêu test bị bỏ qua:** máy này có model nên không test nào bị bỏ qua; theo code thì
  ít nhất một (`test_eye_state.py:115-116`).
- **Đường web cho ra số nào trên UTA-RLDD:** làm được bằng `--set eye_state.source=blendshape`, nhưng đó là phép đo
  mới, thuộc quyết định của anh (H1).
- **Thiết bị đích, camera IR, lái xe thật:** không có.
