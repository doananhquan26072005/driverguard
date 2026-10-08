# DriverGuard — Hướng dẫn sử dụng

> Hệ thống giám sát tài xế chạy **ngay trên thiết bị trong xe**: phát hiện buồn ngủ và mất tập trung
> từ camera, cảnh báo tài xế theo 4 mức L0–L3, và chỉ gửi **metadata** (không bao giờ gửi ảnh) về
> máy chủ để quản lý đội xe và kỹ sư theo dõi.

Tài liệu này dành cho thành viên nhóm và người dùng mới: đọc từ trên xuống là cài và chạy được toàn bộ hệ thống.

---

## Mục lục

1. [DriverGuard là gì](#1-driverguard-là-gì)
2. [Chức năng](#2-chức-năng)
3. [Kiến trúc](#3-kiến-trúc)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Yêu cầu hệ thống](#5-yêu-cầu-hệ-thống)
6. [Cài đặt](#6-cài-đặt)
7. [Chạy hệ thống](#7-chạy-hệ-thống)
8. [Cấu hình và ngưỡng](#8-cấu-hình-và-ngưỡng)
9. [Đánh giá và benchmark](#9-đánh-giá-và-benchmark)
10. [Kiểm thử](#10-kiểm-thử)
11. [Lưu ý quan trọng](#11-lưu-ý-quan-trọng)
12. [Xử lý sự cố](#12-xử-lý-sự-cố)
13. [Trạng thái dự án](#13-trạng-thái-dự-án)

---

## 1. DriverGuard là gì

**DriverGuard** là hệ thống giám sát tài xế (Driver Monitoring System – DMS) gồm ba phần:

| Phần | Chạy ở đâu | Làm gì |
|---|---|---|
| **Edge agent** (`edge_agent/`) | Máy tính trong xe, gắn camera | Đọc camera, phân tích khuôn mặt và điện thoại, quyết định mức cảnh báo, hiện HUD |
| **Backend** (`backend/`) | Máy chủ | Nhận sự kiện từ các xe, lưu vào SQLite, cấp dữ liệu cho dashboard |
| **Frontend** (`frontend/`) | Trình duyệt | HUD trong xe cho tài xế và dashboard cho quản lý đội xe / kỹ sư |

**Mục đích:** giảm tai nạn do ngủ gật và mất tập trung, nhưng **không xâm phạm quyền riêng tư**
và **không làm phiền tài xế bằng cảnh báo sai**.

Ràng buộc thiết kế (từ `CLAUDE.md`):

- Toàn bộ xử lý ảnh chạy on-device. Ảnh khuôn mặt **không bao giờ** được ghi ra đĩa hay gửi đi, chỉ tồn tại trong RAM.
- Chỉ gửi metadata JSON lên backend.
- Chạy tối thiểu **15 FPS**.
- Chỉ dùng model **pretrained**, không huấn luyện model mới.
- Chống cảnh báo sai (false positive) được ưu tiên ngang với độ chính xác.

---

## 2. Chức năng

### 2.1 Phát hiện

| Hành vi | Dấu hiệu dùng | Cách phát hiện |
|---|---|---|
| **Nhắm mắt lâu / microsleep** | EAR; khi EAR không tin cậy (IR, mặt quá tối, lóa kính một mắt) thì CNN trạng thái mắt; blendshape `eyeBlink` của MediaPipe xác nhận "nhắm sâu" | Mắt nhắm **sâu** liên tục ≥ 1,5 s → L3 ngay (mắt nheo lúc nhìn xuống / chói nắng không tính). Thời gian nhắm lúc đang ngáp (và 1,5 s sau đó) không được tính; lúc đang nói chỉ không tính khi mắt không nhắm sâu |
| **Buồn ngủ tích lũy** | PERCLOS 60 s, ngáp, gục đầu | `drowsy_score` 0–100 → L1 (≥ 40) / L2 (≥ 70) |
| **Ngáp** | MAR (độ mở miệng) | Miệng mở rộng đủ lâu (nói chuyện không tính) |
| **Gục đầu** | Góc pitch + mắt nhắm | Cúi xuống rồi ngẩng lại nhanh, kèm mắt nhắm |
| **Nhìn lệch khỏi đường** | Góc yaw / pitch so với tư thế thường | ≥ 2 s (≥ 1,5 s khi chạy nhanh) → L2 |
| **Dùng điện thoại** | YOLOv8n (lớp "cell phone") | Điện thoại trong vùng tài xế ≥ 60 % thời gian 2 s → L2 |
| **Mệt mỏi tăng dần** | Xu hướng `drowsy_score` 15 phút | Độ dốc dương lớn → L1 (gợi ý nghỉ) |

### 2.2 Mức cảnh báo

| Mức | Ý nghĩa | Tác động trong xe |
|---|---|---|
| **L0** | Bình thường | — |
| **L1** | Chú ý | Biểu tượng + chuông nhẹ |
| **L2** | Cảnh báo | Âm thanh + rung ghế |
| **L3** | Nguy hiểm | Cảnh báo mạnh, gợi ý dừng xe nghỉ |

**Giao diện HUD** (`frontend/src/hud/HudView.tsx`, luôn nền tối): thiết kế để liếc 0,5 s là hiểu. Khối trạng thái lớn bên trái (gần tầm mắt tài xế ở xe tay lái thuận) có màu theo mức, icon theo lý do và một câu **hành động** ("Nhìn về phía trước", "Bỏ điện thoại xuống"); lý do cụ thể nằm ở dòng nhỏ bên dưới. Mức càng cao, màn hình càng ít chữ:

| Mức | HUD hiển thị |
|---|---|
| **L0** | Nền tối, khiên xanh "Tỉnh táo". Ban đêm giảm sáng 20 % cho đỡ chói |
| **L1** | Viền và icon vàng |
| **L2** | Cả khối trạng thái tô cam, chữ tối |
| **L3** | Đỏ toàn màn hình, nhấp nháy 1 Hz (tắt nếu hệ điều hành bật "giảm chuyển động"). Chỉ còn "Mở mắt! Dừng xe nghỉ ngay" và số giây mắt nhắm; thông số và nút "Cảnh báo sai" bị ẩn |
| Mất camera / kết nối | Thẻ viền xanh dương: lỗi thiết bị, không phải lỗi tài xế |

Màu không phải tín hiệu duy nhất: icon mức đổi hình tròn → tam giác → bát giác (như biển báo), luôn kèm chữ L0–L3. Khi có nhiều lý do, tiêu đề lấy lý do nguy hiểm nhất (`frontend/src/hud/hudModel.ts`: microsleep > no_face > phone > off_road > drowsy_score > trend > blink_rate). Thứ tự này chỉ dùng để hiển thị, không đổi mức cảnh báo.

**Âm thanh trên HUD** (`frontend/src/hud/chime.ts`, tổng hợp bằng WebAudio, không có file âm thanh): mỗi loại cảnh báo có tiếng riêng để tài xế biết chuyện gì xảy ra mà không cần nhìn màn hình. Mức cảnh báo quyết định độ to.

| Loại | Tiếng |
|---|---|
| Buồn ngủ (`drowsy_score`, `blink_rate`) | Nốt sine trầm dần, êm (L1: 2 nốt, L2: 3 nốt) |
| Mệt mỏi tăng dần (`trend`) | Một nốt dài, nhẹ |
| Nhắm mắt khi xe đứng yên (`microsleep` mức L1) | Hai nhịp trầm "tỉnh dậy" |
| Nhìn lệch (`off_road`) | Hai nốt đi lên, lặp 2 lần ("nhìn phía trước") |
| Điện thoại (`phone`) | Ba tiếng bíp cao, nhanh |
| Không thấy mặt (`no_face`) | Ba nhịp rè trầm |
| **L3** (nhắm mắt kéo dài) | Còi hú cao/thấp xen kẽ, **lặp mỗi 1,5 s cho tới khi tài xế mở mắt** |
| Mất camera / có lại | Tiếng rè đi xuống / hai nốt đi lên |

### 2.3 Chống cảnh báo sai

- Ngưỡng mắt **theo từng tài xế** (người mắt hẹp không bị báo "nhắm mắt" liên tục).
- **Mốc "nhìn đường" tự học**, nên camera lắp lệch không bị hiểu là mất tập trung.
- **Tắt nhánh mất tập trung khi xe dừng** (dưới 5 km/h), và **bỏ qua nhìn ngang khi bật xi nhan**.
- Cảnh báo phải **giữ đủ lâu** mới phát, **giữ mức một lúc** trước khi hạ, và có **cooldown**, nên không nhấp nháy, không lặp lại.
- Tài xế bấm **"Cảnh báo sai"** trên HUD; kỹ sư xem tỉ lệ báo sai theo từng lý do để chỉnh ngưỡng.

### 2.4 Theo vai trò

| Vai trò | Dùng gì | Được làm gì |
|---|---|---|
| **Tài xế** | HUD trong xe (`#/hud`); dashboard (`#/dashboard`) | Xem mức cảnh báo, bấm "Cảnh báo sai"; xem sự kiện **của mình** |
| **Quản lý đội xe** (`manager`) | Dashboard | Nhật ký sự kiện, timeline mệt mỏi, thống kê; xem ngưỡng (chỉ đọc) |
| **Kỹ sư** (`engineer`) | Dashboard | Như quản lý + **chỉnh ngưỡng** |
| **Quản trị** (`admin`) | Dashboard + API | Mọi quyền + tạo tài khoản, đăng ký thiết bị |

---

### 2.5 Một chuyến đi ở v2

| Lúc | Tài xế thấy / làm | Ghi chú |
|---|---|---|
| Xe dừng, chưa đăng ký | Màn hình **"Đăng ký khuôn mặt"**: vì sao cần, ảnh không bị lưu / gửi. Bấm **"Đồng ý, bắt đầu đăng ký"** hoặc **"Để sau"** | "Để sau" vẫn lái được, hỏi lại ở lần dừng sau (M24) |
| Đăng ký (~10 s) | Nhìn thẳng camera → nhìn ra đường → nhắm mắt tới khi nghe bíp; HUD đọc từng bước | Mốc riêng của tài xế, chỉ trong RAM một chuyến (M9) |
| Đang lái | Màu, hình, câu hành động ("Nhìn về phía trước", "Mở mắt! Dừng xe nghỉ ngay") và âm thanh riêng cho từng loại | Âm thanh luôn bật; trình duyệt chặn thì dải vàng "Chạm vào màn hình để bật" (M23) |
| Cúi nhìn điện thoại / bảng đồng hồ | L2 "Nhìn về phía trước", không phải L3 ngủ gật | M25 |
| Xe dừng (0 km/h) | Không có cảnh báo nào (kể cả nhắm mắt, cầm điện thoại) | M30 |
| Đổi người lái | Nút **"Đổi tài xế"**: người mới được hỏi đồng ý và đăng ký lại khi xe dừng | M16, M24 |
| Báo sai | Nút "Cảnh báo sai" trong 120 s sau cảnh báo | Gửi lên dashboard |
| Hết chuyến | Nút **"Kết thúc chuyến"** → bảng tổng kết (đánh giá, biểu đồ từng phút, gợi ý nghỉ) | Quản lý / kỹ sư xem ở tab **"Báo cáo chuyến đi"** (M15) |

**Khi hệ thống không giám sát được, HUD nói rõ** (và có âm báo; chi tiết: `docs/safety-fmea.md`):

| HUD hiện | Nghĩa |
|---|---|
| "Tạm ngưng giám sát: không thấy mặt" | Mất mặt ≥ 3 s khi xe chạy (M10) |
| "Mất camera" | Camera rút ra / hỏng, đang kết nối lại |
| "Lỗi xử lý" | Xử lý frame lỗi liên tục ≥ 1 s; vòng lặp tự thử lại (M28) |
| "Không nhận dữ liệu từ camera" / "Mất kết nối" | Vòng xử lý ngừng cập nhật / HUD không gọi được thiết bị (M28: có âm báo) |
| Dải vàng "Mất tín hiệu xe" | Mất tín hiệu tốc độ: lúc chạy vẫn giám sát như đang chạy, lúc đỗ coi như đỗ (M26) |
| Chip "Máy chậm: cảnh báo có thể trễ" | FPS dưới 15 kéo dài 5 s (M28) |

## 3. Kiến trúc

### 3.1 Luồng 14 khối

```
 1 Frame camera ─► 2 Tiền xử lý ─┬─► 3 MediaPipe Face Landmarker (478 điểm, mỗi frame)
                                 ├─► 4 YOLOv8n điện thoại (luồng riêng, ~5 FPS)
                                 └─► 5 Eye-state CNN (chỉ khi EAR không tin cậy)
                                        │
                                        ▼
                          6 Feature extractor (EAR, MAR, pitch/yaw/roll)
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
               7 Nhánh buồn ngủ                 8 Nhánh mất tập trung
     (PERCLOS, microsleep, ngáp, gục đầu)   (nhìn lệch, điện thoại)
                        └───────────────┬───────────────┘
                                        ▼
        10 Ngữ cảnh (CAN: tốc độ, xi nhan, giờ, thời gian lái) ─► 9 Risk engine ◄─ 11 Trip memory
                                        │                      (bảng luật)      (xu hướng 15 phút)
                                        ▼
                             12 Alert manager (hysteresis, cooldown)
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
               13 HUD trong xe                 14 Metadata publisher ──► Backend ──► Dashboard
        (cửa sổ + server 127.0.0.1)        (theo lô, hàng đợi offline)
```

**Ranh giới quyền riêng tư:** ảnh chỉ đi tới khối 2–5 (khối 5 cắt vùng mắt 32×32, chỉ trong RAM). Từ khối 6 trở đi chỉ còn **con số**.

### 3.2 Khối ↔ file

| Khối | File | Dataclass đầu ra |
|---|---|---|
| 1 Frame camera | `edge_agent/capture/frame_source.py` | `Frame` |
| 2 Tiền xử lý | `edge_agent/perception/preprocess.py` | `PreprocessedFrame` |
| 3 MediaPipe | `edge_agent/perception/landmarks.py` | `FaceLandmarks` |
| 4 YOLOv8n | `edge_agent/perception/phone_detector.py` | `PhoneResult` |
| 5 Eye-state CNN | `edge_agent/perception/eye_state.py` | `EyeState` → `FrameFeatures.p_closed` |
| 6 Feature extractor | `edge_agent/perception/features.py` | `FrameFeatures` |
| 7 Nhánh buồn ngủ | `edge_agent/analysis/drowsiness/` (mắt, miệng, đầu, chớp chậm, lông mày) | `DrowsinessState` |
| 8 Nhánh mất tập trung | `edge_agent/analysis/distraction.py` | `DistractionState` |
| 9 Risk engine | `edge_agent/decision/risk_engine.py` | `RiskAssessment` |
| 10 Ngữ cảnh | `edge_agent/context/can_sim.py`, `vehicle_context.py` | `VehicleSignals`, `VehicleContext` |
| 11 Trip memory | `edge_agent/decision/trip_memory.py` | `TripState` |
| 12 Alert manager | `edge_agent/decision/alert_manager.py` | `AlertOutput`, `Alert` |
| 13 HUD | `edge_agent/hud/hud.py`, `server.py`; `frontend/src/hud/` | — |
| 14 Publisher | `edge_agent/io/publisher.py` | JSON gửi `POST /api/v1/events` |
| Nối 7–12 | `edge_agent/decision/pipeline.py` | `DecisionResult` |
| Một chuyến quanh khối 6–14 (dùng chung thiết bị + web) | `edge_agent/runtime.py` | `TripRuntime`, `FrameStep` |
| Nối 1–14 | `edge_agent/main.py` (thiết bị), `edge_agent/web/bridge.py` (web) | — |

### 3.3 Cổng mạng

| Dịch vụ | Địa chỉ mặc định | Ghi chú |
|---|---|---|
| Backend (FastAPI) | `http://localhost:8100` | Swagger: `/docs` |
| Frontend (Vite dev) | `http://localhost:5173` | Backend và HUD server chỉ cho phép origin này |
| HUD server của edge | `http://127.0.0.1:8765` | Chỉ nghe localhost, không mở ra mạng |
| Mô phỏng lái xe (`tools/drive_sim.py`) | `http://127.0.0.1:8766/can` | Chỉ nghe localhost; edge agent và `#/live` đọc tốc độ, xi nhan từ đây |

---

## 4. Cấu trúc thư mục

```
P-135/
├── CLAUDE.md                  Ràng buộc và quy ước dự án
├── HowToUse.md                Tài liệu này
├── requirements.txt           Thư viện Python để chạy DriverGuard
├── requirements-dev.txt       + ruff, pytest (CI, phát triển)
├── requirements-template.txt  Template khóa học (src/, LangChain), DriverGuard không cần
├── config/
│   ├── thresholds.yaml        TẤT CẢ ngưỡng (không hardcode trong code)
│   ├── datasets.yaml          Preset dataset Kaggle cho tools/dataset.py
│   └── scenarios/             Kịch bản CAN giả lập: city_day, highway_night, parked
├── edge_agent/                Chạy trong xe (khối 1–14)
│   ├── capture/               1  đọc camera / video, luồng riêng, giữ frame mới nhất
│   ├── perception/            2, 3, 4, 5, 6  tiền xử lý, MediaPipe, YOLO, CNN mắt, EAR/MAR/head pose
│   ├── analysis/              7, 8  buồn ngủ, mất tập trung (logic theo thời gian, không ảnh)
│   ├── context/               10  CAN giả lập + ngữ cảnh xe
│   ├── decision/              9, 11, 12  risk engine, trip memory, alert manager, pipeline
│   ├── hud/                   13  HUD trên cửa sổ + server HUD cục bộ
│   ├── io/                    14  publisher metadata, tải ngưỡng từ backend
│   ├── config.py              Đọc thresholds.yaml
│   ├── runtime.py             Một chuyến quanh khối 6–14, dùng chung cho main.py và web/bridge.py
│   └── main.py                Chương trình chính (khối 1–14)
├── backend/                   FastAPI + SQLite
│   ├── app.py                 Endpoint, phân quyền
│   ├── schemas.py             Schema chặt + chặn ảnh / base64
│   ├── db.py                  Bảng, migration, truy vấn
│   ├── security.py            Mật khẩu scrypt, JWT, khóa thiết bị
│   ├── settings.py            Cấu hình qua biến môi trường DG_*
│   └── manage.py              CLI tạo tài khoản / thiết bị
├── frontend/                  React + TypeScript + Vite (HUD + dashboard)
│   └── src/{hud,dashboard,lib}/
├── tools/
│   ├── debug_view.py          Xem camera + landmark + chỉ số + đồ thị (debug)
│   ├── download_models.py     Tải / tạo model
│   ├── eval.py                Precision / recall / F1 / FP mỗi giờ so với nhãn
│   ├── dataset.py             Tải dataset Kaggle và đo từng tín hiệu (EAR, CNN mắt, MAR, YOLO)
│   ├── benchmark.py           FPS, latency p50/p95, FP32 vs INT8
│   └── bench_web.py           Tốc độ khối 6–14 của bản web trong Pyodide, cạnh bản thiết bị
├── models/                    Model (KHÔNG có trong git, tải bằng tools/download_models.py)
├── data/                      DB backend, hàng đợi offline, video (KHÔNG có trong git)
├── eval/results/              Báo cáo benchmark / đánh giá
├── tests/                     pytest: test_edge_agent/, test_backend/
└── docs/                      roadmap.md, workflow/ (sơ đồ và bảng luật)
```

`src/` là mã mẫu của template khóa học (LangGraph / FastAPI), **không** thuộc DriverGuard.

---

## 5. Yêu cầu hệ thống

| Thành phần | Phiên bản |
|---|---|
| Python | **3.11 trở lên** (đã chạy với 3.13; CI dùng 3.11) |
| Node.js | **20.19 trở lên** (cho frontend) |
| Hệ điều hành | Windows 10/11, Linux, macOS |
| Camera | Webcam bất kỳ (camera IR cũng được: ảnh 1 kênh được chuyển sang 3 kênh) |
| CPU | Không cần GPU. Máy thử (Mac ARM, 10 luồng), trên clip YawDD có mặt thật: vòng lặp chính ~146 FPS, MediaPipe ~5,7 ms/frame (`eval/results/benchmark.md`) |

---

## 6. Cài đặt

Các lệnh dưới đây dùng **PowerShell trên Windows**. Trên Linux/macOS, thay `.venv\Scripts\` bằng `.venv/bin/`.

### 6.1 Môi trường Python

Cần **Python ≥ 3.11** (code dùng `datetime.UTC`). Khuyên dùng [uv](https://docs.astral.sh/uv/) với Python 3.12:

```powershell
uv venv -p 3.12 --seed .venv
.venv\Scripts\activate
uv pip install -r requirements-dev.txt      # hoặc: pip install -r requirements-dev.txt
```

- `requirements.txt`: chỉ những gì DriverGuard cần để chạy (edge agent + backend).
- `requirements-dev.txt`: thêm ruff, pytest, httpx để kiểm tra code và chạy test.
- `requirements-template.txt`: phần template của khóa học (`src/`, LangGraph/LangChain, Dockerfile). DriverGuard không cần; khi chưa cài, `tests/test_agents` và `tests/test_api` được tự bỏ qua.
- **`Dockerfile` / `docker-compose.yml` chạy app template của khóa học (`src.main:app`), không phải backend DriverGuard.** Backend DriverGuard chạy bằng `uvicorn backend.app:app` (mục 7.2); chưa có image Docker cho nó.
- macOS: `requirements.txt` ghim `mediapipe==0.10.21`, vì bản 1.0.x bị crash (Metal).
- Trên Linux/macOS có sẵn `make venv`.

### 6.2 Model (bắt buộc)

**MediaPipe Face Landmarker** và **CNN trạng thái mắt** được tải tự động:

```powershell
python tools\download_models.py
```

**YOLOv8n ONNX** phải export từ weights chính thức. Việc này cần `ultralytics` và `torch` (khoảng 1 GB),
nên làm **một lần trong venv tạm có đường dẫn ngắn**, vì torch vượt giới hạn 260 ký tự của Windows:

```powershell
python -m venv C:\tmp\yx
C:\tmp\yx\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cpu
C:\tmp\yx\Scripts\pip install ultralytics onnx onnxslim
C:\tmp\yx\Scripts\python tools\download_models.py      # tạo models\yolov8n.onnx
```

Sau đó xóa `C:\tmp\yx` được. Kết quả mong đợi trong `models/`:

```
face_landmarker.task   ~3,8 MB
open_closed_eye.onnx   46 KB     (CNN trạng thái mắt, khối 5; có kiểm tra SHA-384)
yolov8n.onnx           ~12,9 MB
yolov8n_int8.onnx      ~3,6 MB   (tự tạo khi chạy tools\benchmark.py, không bắt buộc)
```

> Không có `yolov8n.onnx` thì hệ thống vẫn chạy, chỉ tắt phát hiện điện thoại (có dòng `[phone] disabled`).

### 6.3 Biến môi trường

```powershell
copy .env.example .env
```

Điền các biến `DG_*` trong `.env`:

| Biến | Ý nghĩa |
|---|---|
| `DG_JWT_SECRET` | **Bắt buộc khi chạy thật.** Tạo: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DG_DB_PATH` | File SQLite của backend (mặc định `data/driverguard.db`) |
| `DG_TOKEN_TTL_MIN` | Thời hạn đăng nhập (phút, mặc định 60) |
| `DG_CORS_ORIGINS` | Origin được phép gọi API (mặc định có `http://localhost:5173`) |
| `DG_DEVICE_KEY` | Khóa thiết bị cho edge agent (lấy ở bước 7.2) |

### 6.4 Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local     # chỉ cần nếu đổi địa chỉ backend / HUD server
cd ..
```

---

## 7. Chạy hệ thống

### 7.1 Chạy nhanh để xem camera và chỉ số (không cần backend)

```powershell
python tools\debug_view.py --source 0 --quiet --speed 50
```

- Hiện landmark, trục đầu, EAR / MAR / pitch / yaw / roll, nguồn quyết định mắt (`[EAR]` hay `[CNN p_closed …]`), đồ thị 5 giây, khung điện thoại, trạng thái buồn ngủ / mất tập trung.
- Terminal in `[DROWSY] ...` khi phát hiện microsleep, ngáp, gục đầu, PERCLOS cao.
- Phím tắt: `q` thoát · `r` ảnh gốc / đã xử lý · `s` xem hai ảnh cạnh nhau · `l` bật/tắt landmark · `g` bật/tắt đồ thị · `m` giả lập xe dừng / chạy · `space` tạm dừng.
- `--source` nhận số camera (`0`, `1`…) hoặc đường dẫn video; thêm `--loop` để lặp video.

### 7.2 Khởi tạo backend (một lần)

```powershell
python -m backend.manage create-user admin --role admin
python -m backend.manage create-user boss  --role manager
python -m backend.manage create-user kysu  --role engineer
python -m backend.manage create-user an    --role driver --driver-id drv-001
python -m backend.manage create-device cam-001 --driver-id drv-001
```

- Không truyền `--password` thì lệnh sẽ hỏi mật khẩu (ít nhất 8 ký tự), để mật khẩu không nằm trong lịch sử shell.
- `create-device` in **khóa thiết bị đúng một lần**. Hãy lưu nó vào `DG_DEVICE_KEY`.
- `driver-id` của thiết bị là tài xế lái xe đó. Sự kiện của thiết bị được gán cho tài xế này.

### 7.3 Toàn bộ hệ thống (4 terminal)

**Terminal 1 – Backend**

```powershell
.venv\Scripts\activate
uvicorn backend.app:app --port 8100
```

**Terminal 2 – Edge agent trong xe**

```powershell
.venv\Scripts\activate
$env:DG_DEVICE_KEY = "dgk_..."          # khóa từ bước 7.2
python -m edge_agent.main --source 0 --backend http://localhost:8100 --device-id cam-001
```

| Tùy chọn | Ý nghĩa |
|---|---|
| `--source` | Camera (`0`) hoặc file video |
| `--scenario` | Kịch bản CAN dựng sẵn (`city_day.yaml`, `highway_night.yaml`, `parked.yaml`) thay cho công cụ mô phỏng lái xe. Bỏ đi (mặc định) thì tốc độ lấy từ `tools/drive_sim.py` |
| `--sim-url` | Địa chỉ công cụ mô phỏng lái xe (mặc định `http://127.0.0.1:8766/can`) |
| `--backend`, `--device-id` | Bật gửi metadata (bỏ đi thì chạy hoàn toàn offline) |
| `--hud-port` | Cổng server HUD (mặc định 8765, `0` = tắt) |
| `--no-window` | Không mở cửa sổ, chỉ in ra terminal |
| `--no-phone` | Tắt YOLO |
| `--status-every` | Số giây giữa hai dòng trạng thái |

Khi chạy, terminal in các dòng `[ALERT L2] phone -> sound + seat vibration ...` và dòng trạng thái định kỳ.

**Terminal 3 – Mô phỏng lái xe** (thay cho CAN của xe thật; không phải nút trên giao diện)

```powershell
.venv\Scripts\activate
python tools/drive_sim.py                                          # lái bằng bàn phím
python tools/drive_sim.py --scenario config\scenarios\city_day.yaml   # hoặc chạy lại một kịch bản
```

| Phím | Tác dụng |
|---|---|
| `w` / `↑` | Tăng tốc (+10 km/h mục tiêu) |
| `s` / `↓` | Giảm tốc (−10 km/h) |
| `space` | Dừng (về 0 km/h) |
| `c` | Chạy 50 km/h |
| `a` / `←`, `d` / `→` | Xi nhan trái / phải (giữ bật đến khi tắt: bấm lại cùng phím, bấm bên kia, hoặc `x`) |
| `x` | Tắt xi nhan |
| `q` | Thoát |

- Tốc độ tăng / giảm dần như xe thật (`config/drive_sim.yaml`).
- **0 km/h = xe đang dừng / đỗ**: HUD hiện "Xe đang đỗ", không cảnh báo mất tập trung, đăng ký khuôn mặt
  chạy được: HUD hỏi trước (vì sao cần đăng ký, ảnh khuôn mặt không bị lưu hay gửi đi), bấm **"Đồng ý,
  bắt đầu đăng ký"** thì vào 3 bước, **"Để sau"** thì hỏi lại ở lần dừng sau. Không có nút "Tạm dừng"
  nữa.
- **Không chạy công cụ = xe đứng yên 0 km/h.** Tắt công cụ khi xe đang đỗ thì sau 1 s
  (`context.vehicle_signal_stale_s`) xe vẫn là đỗ, HUD báo mất tín hiệu.
- **Tắt công cụ khi xe đang chạy = mất tín hiệu xe** (M26): HUD báo "Mất tín hiệu xe: vẫn giám sát như đang
  chạy" kèm âm báo, tốc độ hiện "–", hệ thống vẫn giám sát như xe đang chạy. Tắt công cụ khi xe đang đỗ cũng
  được báo ("coi như đang đỗ đến khi có lại tốc độ"). Chạy lại công cụ thì có lại tín hiệu.
- `#/live` trên trình duyệt cũng đọc công cụ này (cùng máy).
- **Điều khiển xe trên web (M31), không cần terminal:** khung camera của `#/live` có nút **"Điều khiển xe · mã
  XXXXXX"**. Bấm để mở trang `#/drive?code=XXXXXX` (hoặc mở link đó trên điện thoại khác): nút **Tăng tốc**,
  **Giảm tốc**, **Chạy đều 50**, **Dừng xe**, xi nhan **Trái / Tắt / Phải**; phím giống công cụ terminal
  (W / S / Space / C / A / D / X). Tốc độ tăng giảm dần như xe thật. Trang này gửi tốc độ qua backend theo mã
  ghép (chỉ số, không lưu); `#/live` ưu tiên nó, không có thì đọc công cụ terminal. Đóng trang khi xe đang
  chạy thì `#/live` báo "Mất tín hiệu xe".
- **Xe đứng yên (0 km/h) không có cảnh báo nào** (M30), kể cả nhắm mắt hay cầm điện thoại.

**Terminal 4 – Frontend**

```powershell
cd frontend
npm run dev
```

- **HUD trong xe:** http://localhost:5173/#/hud. Không cần đăng nhập, đọc trạng thái từ edge agent. Nếu không có edge agent, bấm **"Chạy mô phỏng"** để demo. Âm thanh cảnh báo luôn bật, không có nút tắt; trình duyệt chỉ cho phát tiếng sau một lần chạm, nên lần chạm đầu tiên vào màn hình sẽ bật tiếng (dải vàng nhắc cho tới lúc đó): vòng mô phỏng 90 s lần lượt phát đủ các loại cảnh báo, nên nghe được tiếng của từng loại.
- **Xem trước giao diện HUD:** http://localhost:5173/#/hud-preview. Chọn từng trạng thái (L0–L3, mất camera, mất kết nối, ngày / đêm) ở thanh dưới cùng, không cần edge agent. Mở thẳng một trạng thái: `#/hud-preview?s=l3&night=0`.
- **Dashboard:** http://localhost:5173/#/dashboard. Đăng nhập bằng tài khoản ở bước 7.2.

### 7.4 Kịch bản demo gợi ý

1. Đăng nhập dashboard bằng `kysu` (kỹ sư).
2. Trước webcam: nhắm mắt khoảng 2 s → HUD chuyển **L3**, terminal in `[ALERT L3] microsleep`.
3. Cầm điện thoại lên tai khoảng 3 s → **L2** `phone`.
4. Trên HUD bấm **"Cảnh báo sai"** → dashboard tab *Nhật ký sự kiện* hiện thẻ "Tài xế báo sai".
5. Chờ hơn 1 phút → tab *Timeline mệt mỏi* có điểm `drowsy_score` theo từng phút.
6. Tab *Ngưỡng*: đổi `drowsy_score → L1` thành 45 → **Lưu**. Edge agent đang chạy hỏi lại backend mỗi 5 phút (`publisher.config_poll_s`) và áp phiên bản mới **khi xe đỗ**, terminal in `[config] thresholds version N applied`; khởi động lại thì áp ngay (`[config] 1 tuned thresholds applied`).

---

## 8. Cấu hình và ngưỡng

### 8.1 `config/thresholds.yaml`

Mọi ngưỡng nằm ở đây, mỗi dòng có chú thích. Mỗi ngưỡng chỉ nằm ở **một chỗ**, và key hoặc mục không có trong code (ví dụ gõ sai `yawn: {mar_opn: 0.9}`) làm edge agent **dừng ngay khi khởi động**, báo `ConfigError` kèm đường dẫn key, thay vì lặng lẽ dùng giá trị mặc định.

| Mục | Khối | Ví dụ |
|---|---|---|
| `capture`, `preprocess` | 1, 2 | độ phân giải camera, kích thước resize, CLAHE (trên kênh Y của YCrCb) |
| `landmarks`, `features` | 3, 6 | độ tin cậy MediaPipe, bật blendshapes (`eyeBlink`), tiêu cự camera |
| `eye_state` | 5 | nguồn điểm mắt (`cnn` / `blendshape`), model, cách cắt mắt, khi nào dùng (IR, độ sáng **vùng mặt**, một mắt còn mở mà mắt kia lệch EAR) |
| `phone` | 4 | model, ngưỡng tin cậy, tần suất YOLO, vùng tài xế |
| `drowsiness` | 7 | tỉ lệ nhắm mắt, microsleep, PERCLOS, ngáp, gục đầu |
| `distraction` | 8 | góc nhìn lệch, mốc nhìn đường |
| `context` | 10 | tốc độ tối thiểu ("xe đang chạy", dùng chung cho khối 8 và 9), tốc độ cao, khung giờ đêm, lái lâu, thời gian xi nhan |
| `risk` | 9 | bảng luật: trọng số `drowsy_score`, ngưỡng L1/L2/L3 |
| `trip_memory` | 11 | kích thước bin, cửa sổ xu hướng |
| `alert` | 12 | thời gian xác nhận, giữ mức, cooldown |
| `publisher` | 14 | kích thước lô, chu kỳ gửi, hàng đợi offline |

Bảng luật gốc nằm trong `docs/workflow/workflow_full_4.jpg`:

```
drowsy_score = 40·PERCLOS + 25·microsleep + 15·ngáp + 20·gục đầu   (mỗi thành phần chuẩn hóa 0–1)
  × 1,2 ban đêm × 1,2 khi lái lâu (tối đa 100)
```

### 8.2 Chỉnh ngưỡng từ dashboard

- Kỹ sư chỉnh được **15 ngưỡng** trong tab *Ngưỡng*, mỗi ngưỡng có giới hạn min/max. Mỗi lần lưu tạo một **phiên bản** mới.
- Edge agent tải ngưỡng **khi khởi động** và ghi đè lên YAML, rồi hỏi lại mỗi 5 phút; phiên bản đổi thì áp **khi xe đỗ** (M47). Nếu kết quả không hợp lệ (ví dụ L1 ≥ L2) thì bỏ qua và giữ bộ đang dùng.
- Ô để trống nghĩa là thiết bị dùng giá trị trong `thresholds.yaml` của nó.

**Áp thử và quay lui (M47).** Ô "Chỉ áp thử cho các xe" nhận mã thiết bị (vd. `cam-001, web-an`): chỉ các xe
đó nhận phiên bản mới, cả đội giữ phiên bản đang dùng. Bảng "Phiên bản ngưỡng" cho biết mỗi phiên bản đổi khoá
nào, xe nào đang chạy, bao nhiêu cảnh báo và bao nhiêu lần tài xế bấm "Cảnh báo sai". Nút "Áp cho cả đội" đưa
một phiên bản bất kỳ (bản đang thử, hoặc một bản cũ để quay lui) thành của cả đội. Xe báo `config_applied` trong
nhật ký sự kiện khi đã nhận; bộ ngưỡng không nhất quán bị xe từ chối (`config_refused`) và xe giữ bộ cũ.

### 8.3 Kịch bản CAN (`config/scenarios/*.yaml`)

```yaml
name: highway_night
start_clock: "02:30"          # giờ giả lập
initial_drive_time_s: 7000    # đã lái bao lâu trước khi bắt đầu
loop: true
timeline:
  - {t: 0,   speed_kmh: 60}
  - {t: 250, speed_kmh: 100, turn_signal: right}
  - {t: 255, speed_kmh: 100, turn_signal: off}
```

Tốc độ được nội suy tuyến tính giữa các mốc. Xi nhan giữ nguyên trạng thái cho tới khi đổi.
Dùng được theo hai cách: `python -m edge_agent.main --scenario ...` (chỉ thiết bị) hoặc
`python tools/drive_sim.py --scenario ...` (cả thiết bị lẫn `#/live` cùng đọc).

---

## 9. Đánh giá và benchmark

### 9.1 Độ chính xác: `tools/eval.py`

Cần video và nhãn, ví dụ từ các dataset công khai NTHU-DDD, YawDD, DMD. Chép video vào `data/videos/` (thư mục này không có trong git).

File nhãn là CSV:

```csv
video,behavior,start_s,end_s
clip01.mp4,yawn,12.5,16.0
clip01.mp4,phone,40,48
clip02.mp4,none,,
```

- `behavior` nhận một trong: `microsleep`, `yawn`, `nod`, `drowsy`, `phone`, `off_road`.
- Giá trị `none` dùng cho clip không có sự kiện nào; thời gian của clip vẫn được tính vào FP/giờ.

```powershell
python tools\eval.py run   --labels labels.csv --videos data\videos --save preds.json --out eval\results\eval.md
python tools\eval.py score --labels labels.csv --predictions preds.json --tolerance 2
python tools\eval.py run   --labels labels.csv --videos data\videos --phone-model models\yolov8n_int8.onnx
python tools\eval.py convert-frames --frames 001_mouth.txt --video 001.mp4 --fps 30 --map 1=yawn --header
```

- `score`: chấm lại từ kết quả đã lưu, không cần chạy lại video.
- `--phone-model`: dùng model khác, ví dụ để so độ chính xác INT8 với FP32.
- `convert-frames`: chuyển nhãn theo từng frame (chuỗi `0/1`) sang dạng khoảng thời gian.

Kết quả gồm precision, recall, F1, độ trễ phát hiện và **FP mỗi giờ lái** cho từng hành vi, cộng thêm một dòng tính cho **mọi cảnh báo**.

### 9.2 Dataset Kaggle: `tools/dataset.py`

Phần lớn dataset công khai trên Kaggle là **ảnh chia theo thư mục lớp** hoặc **clip gắn nhãn theo tên file**, không phải video có nhãn theo thời gian như `eval.py` cần. `tools/dataset.py` tải dataset về `data/kaggle/` (không có trong git) và đo từng tín hiệu trên đó.

```powershell
pip install kagglehub                                  # dataset công khai: không cần tài khoản Kaggle
python tools\dataset.py list                           # các preset có sẵn
python tools\dataset.py eval yawn_eye_mouth --out eval\results\dataset_yawn_eye_mouth.md
python tools\dataset.py eval state_farm --limit 200    # tối đa 200 ảnh mỗi lớp, chạy nhanh
python tools\dataset.py eval mrl_eye --root D:\datasets\mrl   # dataset đã giải nén sẵn
python tools\dataset.py labels yawdd --out data\yawdd_labels.csv   # clip -> nhãn cho eval.py
```

| Preset | Dataset Kaggle | Đo gì |
|---|---|---|
| `mrl_eye` | `prasadvpatil/mrl-dataset` (23 MB) | CNN mắt (khối 5) trên ảnh mắt IR. CNN học trên MRL nên số sẽ lạc quan |
| `yawn_eye_eyes` | `serenaraju/yawn-eye-dataset-new` (169 MB) | CNN mắt trên ảnh mắt màu |
| `yawn_eye_mouth` | như trên | MAR (khối 6) so với ngưỡng ngáp `yawn.mar_open` |
| `ddd` | `ismailnasri20/driver-drowsiness-dataset-ddd` (2,7 GB) | Chỉ số gần đúng trên từng ảnh: mắt nhắm hoặc ngáp (EAR, CNN, MAR) |
| `state_farm` | `rightway11/state-farm-distracted-driver-detection` (550 MB) | YOLO điện thoại (khối 4): c1–c4 có điện thoại, c0 và c5–c9 là mẫu âm khó. Cần `yolov8n.onnx` |
| `yawdd` | `enider/yawdd-dataset` (5 GB) | Toàn bộ pipeline (khối 2–12) trên clip: Yawning là dương, Normal / Talking là âm |

- Báo cáo có accuracy / precision / recall / F1 **ở ngưỡng hiện tại trong `thresholds.yaml`**, kèm **ngưỡng cho F1 tốt nhất** trên dataset đó. Với State Farm, báo cáo có thêm tỉ lệ báo dương theo từng lớp c0–c9.
- Ảnh tĩnh chưa có baseline riêng của từng tài xế và luật thời gian của khối 7–8. Vì vậy ngưỡng tốt hơn ở đây chỉ là **gợi ý**. Hãy kiểm tra lại bằng video (`yawdd`, `eval.py`) trước khi sửa `thresholds.yaml`.
- Thêm dataset Kaggle khác: khai báo một preset trong `config/datasets.yaml` (slug, task, thư mục → nhãn), **không cần sửa code**.
- Ảnh chỉ được đọc vào RAM, tool chỉ ghi file metric.

### 9.3 Video có nhãn theo frame / theo clip: `tools/seq_eval.py`

Chạy toàn bộ pipeline (khối 2–12) trên từng frame video, ghi lại một dòng số mỗi frame (không ghi ảnh), rồi chấm điểm:

```powershell
python tools\seq_eval.py trace fl3d --workers 8 --out data\eval_traces\fl3d.pkl    # FL3D: nhãn từng frame, chạy trên video gốc NITYMED
python tools\seq_eval.py fl3d --traces data\eval_traces\fl3d.pkl --out eval\results\dataset_fl3d.md
python tools\seq_eval.py trace sust --workers 8 --out data\eval_traces\sust.pkl    # SUST-DDD: 2074 clip 10 s, nhãn theo clip (~45 phút)
python tools\seq_eval.py sust --traces data\eval_traces\sust.pkl --out eval\results\dataset_sust_ddd.md
python tools\seq_eval.py trace yawdd --workers 8 --out data\eval_traces\yawdd.pkl  # YawDD: kiểm tra hồi quy
# Thử ngưỡng khác mà không chạy lại MediaPipe: khối 5 và 7–12 được chạy lại từ các cột đã ghi
python tools\seq_eval.py fl3d --traces data\eval_traces\fl3d.pkl --replay block5 --set drowsiness.microsleep_deep.blink=0.4
```

- FL3D (Kaggle `matjazmuc/frame-level-driver-drowsiness-detection-fl3d`) là ảnh mặt cắt từ video NITYMED (`nikospetrellis/nitymed`), nên cần tải cả hai; nhãn khớp theo số thứ tự frame.
- SUST-DDD không có trên Kaggle: đặt vào `data/sust-ddd/SUST Driver Drowsiness Dataset/{drowsiness,not drowsiness}/`.
- `--replay block5` chạy lại khối 5 (trigger + hold, nguồn điểm theo `eye_state.source`) và khối 7–12 với ngưỡng hiện tại; `--set` thử một ngưỡng khác. Replay trùng khớp với lần chạy thật (đã kiểm tra từng frame).

### 9.4 Tốc độ: `tools/benchmark.py`

```powershell
python tools\benchmark.py --source data\videos\clip01.mp4 --out eval\results\benchmark.md
```

- Đo FPS và độ trễ p50/p95 của từng khối, rồi của cả vòng lặp chính.
- Đo kích thước model và so YOLO **FP32 với INT8**. Lần đầu chạy sẽ tự tạo `models/yolov8n_int8.onnx`.
- Nên dùng **video có mặt người**. Không có `--source` thì dùng frame tổng hợp không có mặt, nên thời gian đo của MediaPipe sẽ thấp hơn thực tế.
- `eval/results/benchmark.md` hiện đo trên clip Dash của YawDD (`python tools/dataset.py` tải về `data/kaggle/`), ví dụ `--source "data/kaggle/datasets/enider/yawdd-dataset/versions/4/Dash/Dash/Female/1-FemaleNoGlasses.avi"`.
- Lần chạy đầu tạo `yolov8n_int8.onnx`, hiệu chỉnh INT8 bằng chính các frame của `--source`. Đừng chạy lần đầu với frame tổng hợp; nếu lỡ chạy thì thêm `--requantize`.

### 9.5 Tự ghi số từ camera: `tools/record_trace.py`

Không quay video (CLAUDE.md cấm ghi frame). Công cụ chạy khối 2–12 trên camera, mỗi frame giữ một dòng số,
người ngồi trước camera bấm phím để đánh dấu mình đang làm gì. Cửa sổ xem trước chỉ hiển thị.

```powershell
python tools\record_trace.py record --out data\own_traces\quan.pkl --name mask_day --tag person=quan --tag mask=medical --tag glasses=no --tag light=day
python tools\record_trace.py report --traces data\own_traces\quan.pkl --out eval\results\own_recordings.md
```

- Phím (bấm lần một là bắt đầu, lần hai là kết thúc; có thể bật nhiều nhãn cùng lúc): `e` nhắm mắt, `d` cúi
  nhìn điện thoại, `b` nhìn bảng đồng hồ, `s` nhìn sang bên, `r` quay ra sau, `y` ngáp, `t` nói chuyện, `n`
  gục đầu, `c` cầm điện thoại nghe, `x` cầm điện thoại nhắn tin, `a` ngồi yên nhìn đường; `q` / Esc dừng và lưu.
  Thêm: `m` nhìn điện thoại trên giá đỡ thấp, `g` nhìn cần số, `j` liếc xuống bằng mắt (đầu yên), `k` liếc sang
  bên bằng mắt, `l` liếc ngắn lặp lại, `w` cúi kèm nhắm mắt thật, `v` nhìn gương bình thường (không mong cảnh
  báo), `p` quay đầu một phần rồi giữ.
- Mỗi buổi ghi một điều kiện, đặt bằng `--tag` (`mask`, `glasses`, `light`, `person`). Bảng so khẩu trang
  gộp theo tag `mask`.
- Kịch bản gợi ý, vài phút mỗi cảnh, mỗi điều kiện một buổi: ngồi yên nhìn đường 1 phút (`a`); nhắm mắt
  2–3 s, 10 lần (`e`); cúi nhìn điện thoại trên đùi / giá đỡ thấp, nhìn bảng đồng hồ (`d`, `b`); nhìn gương
  hai bên ngắn và dài (`s`); quay ra sau (`r`); ngáp (`y`); nói chuyện 1 phút (`t`); cầm điện thoại ở tai
  rồi cầm trước ngực (`c`, `x`). Lặp lại với khẩu trang y tế, khẩu trang vải tối màu, kính, phòng tối.
- `report` cho: độ trễ từ lúc bấm phím đến cảnh báo (p50 / p95, so với PRD ≤ 3 s), cảnh báo ngoài mọi nhãn,
  số đo khi nhìn xuống so với khi nhắm mắt, bảng có / không khẩu trang, bảng gọi / nhắn tin. Thêm
  `--set drowsiness.microsleep_deep.bowed_ear_ratio=0.3` để thử ngưỡng khác trên chính bản ghi đó.
- Nhãn là phản xạ của người bấm, không phải sự thật tuyệt đối; bản ghi là tập dev của nhóm, không thay được
  dataset có nhãn.

### 9.6 Đo offline trên trace sẵn có: `tools/trace_studies.py`

```powershell
python tools\trace_studies.py perclos  --out eval\results\perclos_p80.md      # định nghĩa PERCLOS hiện tại so với P80
python tools\trace_studies.py lighting --out eval\results\lighting.md         # theo độ sáng vùng mặt, theo kính (YawDD)
python tools\trace_studies.py personal --out eval\results\personalization.md  # mốc riêng từng người có giảm báo sai không
python tools\trace_studies.py glance   --out eval\results\glance_ratio.md     # off_road_ratio trên người không mất tập trung
```

- Chỉ replay khối 7–12 trên trace trong `data/eval_traces/` (tạo một lần bằng `seq_eval.py trace`), không
  đọc lại video, không đổi ngưỡng nào. `--limit 40` để xem nhanh, `--set` để thử ngưỡng.
- `tools/eval.py`: CSV nhãn nhận thêm cột `subject` (ai trong video); có cột này thì báo cáo thêm bảng theo
  từng người. Báo cáo cũng tách cảnh báo sai trong `eval.warmup_s` đầu mỗi video ra riêng.

### 9.7 Chạy dài và mô phỏng thiết bị yếu: `tools/benchmark.py --duration`, `tools/edge_sim.py`

```powershell
python tools\benchmark.py --source data\videos\clip01.mp4 --duration 60m --out eval\results\benchmark_soak.md
python tools\edge_sim.py --profile jetson_nano --duration 10m --source data\videos\clip01.mp4
```

- `--duration` chạy vòng lặp chính theo nhịp camera (`--pace-fps 30`), mỗi giây ghi FPS, độ trễ p95, CPU,
  RAM, nhiệt độ (chỉ khi hệ điều hành cho đọc; macOS thì không). Đạt khi mọi phút ≥ `eval.soak_min_fps` và
  RAM tăng dưới `eval.soak_rss_growth_mb_per_h`. Cần `psutil`.
- `tools/edge_sim.py` build image `Dockerfile.edge` rồi chạy đúng phép đo đó trong container bị giới hạn số
  nhân và RAM theo `config/edge_profiles.yaml`. Báo cáo ghi `simulated`: giới hạn số nhân không tái hiện tốc
  độ từng nhân, GPU hay nhiệt của thiết bị thật, nên đây là cận trên, không phải số đo của thiết bị.
- macOS: Docker Desktop có thể không được đọc thư mục Documents. Cho quyền trong System Settings, hoặc chép
  model và video ra chỗ khác rồi dùng `--models-dir`, `--source`, `--out-dir`.

### 9.8 Cùng video, ánh sáng khác: `tools/light_study.py`

```powershell
python tools/light_study.py --out eval/results/lighting_transforms.md      # 8 video mỗi bộ, khoảng 8 phút
python tools/light_study.py --datasets fl3d --limit 2 --workers 4          # xem nhanh
```

- Mỗi frame bị làm tối (gamma), làm chói (gain), chuyển xám (giả camera hồng ngoại) hoặc làm mờ **trong RAM**
  trước khối 2, rồi khối 2–12 chạy như thường. Không ghi ảnh nào. Mức biến đổi ở `eval.light_*`.
- Mỗi dòng của báo cáo chỉ khác bản gốc ở ánh sáng: tỉ lệ thấy mặt, độ sáng / độ nét của mặt, tỉ lệ "tạm ngưng
  giám sát" và lý do, còn bắt được bao nhiêu microsleep / ngáp.
- Biến đổi nhân tạo, không phải cabin tối hay camera IR thật: báo cáo cho biết pipeline gãy ở đâu, không cho
  biết ánh sáng đó gặp thường xuyên tới đâu.

### 9.9 Tốc độ bản web: `tools/bench_web.py` và số đo trên `#/live`

```powershell
cd frontend; npm ci; cd ..                                         # một lần: cần gói pyodide cho Node
python tools/bench_web.py --label "sau khi sửa X"                   # mặt tổng hợp 60 s
python tools/bench_web.py --label "clip thật" --clip data\videos\clip01.mp4
```

- Đo lời gọi mỗi frame của trang (`WebAgent.frame()` + JSON, khối 6–14) trên cùng chuỗi landmark: trong Python
  thường có OpenCV (như thiết bị) và trong Pyodide chạy bằng Node (như `#/live` và APK). Không có ảnh nào: đầu
  vào là số landmark; `--clip` chỉ giữ landmark của video trong RAM.
- Mỗi `--label` là một dòng trong `eval/results/benchmark_web.md` (dữ liệu ở `benchmark_web.json`); chạy trước
  và sau một thay đổi ở khối 6–12 để có số so sánh. Lần đầu cần mạng để tải numpy / pyyaml / sqlite3 của Pyodide.
- Node không phải trình duyệt và máy dev không phải hub: bảng này chỉ so các phiên bản code. Thời gian camera,
  MediaPipe, YOLO của một máy cụ thể đọc ngay trên máy đó: mở `#/live`, bấm "Chi tiết kỹ thuật" trên thẻ camera
  (p95 từng chặng, GPU hay CPU, số luồng YOLO, số frame bị bỏ). Khi đã đăng nhập, cùng số đó lên tab "Đội xe",
  cột "Tốc độ xử lý".
- Đo cả vòng lặp trong trình duyệt thật (MediaPipe, YOLO, Pyodide của bản build), không cần ngồi trước camera:
  `npx vite build && npx vite preview --port 5191`, rồi
  `node bench/live.bench.mjs --url http://localhost:5191 --seconds 30 --camera clip.mjpeg` (trong `frontend/`).
  Kết quả mẫu và các biến thể (ép GPU / CPU, GPU thật hay phần mềm): `eval/results/benchmark_live.md`.
- Dòng "ĐT … ms · tuổi … ms": tuổi là kết quả YOLO đang dùng đã cũ bao lâu. Quá `phone.max_result_age_s` (0,6 s)
  thì kết quả không được tính; phần lớn 10 giây như vậy thì HUD hiện "Không phát hiện được điện thoại" (M50).
  Cuối dòng là "WebGPU" khi model điện thoại chạy trên GPU thật (M67), hoặc số luồng khi chạy bằng wasm.
- Cùng công cụ đó, từ M67:
  - `--duration 10m --json soak.json`: chạy dài, mỗi 10 giây đọc số đếm từ lúc bắt đầu (frame đã xử lý, frame camera
    không kịp xử lý, số lần YOLO chạy) cùng bộ nhớ và CPU của các tiến trình trình duyệt; từ 2 phút trở lên có
    kết luận theo `eval.soak_min_fps` (từng phút) và `eval.soak_rss_growth_mb_per_h` (tiến trình của trang, sau phút đầu).
  - `--profile /tmp/dg-profile`: giữ hồ sơ trình duyệt giữa các lần chạy, lần thứ hai là khởi động khi đã có cache.
    `--think-s 3`: dừng 3 giây ở màn hình trước khi bấm bắt đầu, như tài xế đọc màn hình.
  - `--yolo wasm` / `--yolo webgpu`: ép nơi chạy model điện thoại (khoá `dg.phone.provider` trong localStorage),
    giống `--delegate` với model mặt.
  - Rê chuột lên các dòng số trong "Chi tiết kỹ thuật": dòng cuối là thời gian khởi động từng phần.

---

### 9.10 Nhìn xuống và hướng mắt trên 3MDAD: `tools/gaze_study.py`

```powershell
python tools\gaze_study.py trace  --out data\eval_traces\3mdad_day.pkl
python tools\gaze_study.py report --traces data\eval_traces\3mdad_day.pkl --out eval\results\gaze_3mdad.md
```

- 3MDAD (Kaggle `anouarbenkhalifa/3mdad-multimodal-driver-action-distraction`, bản ngày `RGB2`): 50 tài xế trong xe thật,
  16 hành động, camera hướng mặt. Mỗi tài xế chạy qua khối 2–12 như một chuyến; chỉ giữ số, không giữ ảnh.
- Báo cáo: số đo theo hành động, cảnh báo hệ thống đưa ra, và góc nhìn xuống của khối 8 (chỉ đo) giữ 2 s ở vài ngưỡng.
- Tốc độ khung hình không có trong dữ liệu: `--fps` (30) là giả định, ảnh hưởng mọi con số tính theo giây.

### 9.11 Nhánh điện thoại theo cách và lúc YOLO chạy: `tools/phone_study.py`

```powershell
python tools\phone_study.py detect --out data\eval_traces\3mdad_phone.pkl
python tools\phone_study.py detect --out ... --model 416=C:\tmp\yolov8n_416.onnx      # thêm một bản xuất cỡ khác
python tools\phone_study.py report --dets data\eval_traces\3mdad_phone.pkl --out eval\results\phone_web_3mdad.md
```

- `detect` chạy YOLO một lần trên **mọi** frame của 3MDAD (cùng ảnh 640 mà khối 4 nhận), chỉ giữ hộp điện thoại.
- `report` mô phỏng một lịch chạy trên các hộp đó (bao nhiêu lần mỗi giây, bao lâu thì có kết quả, cách chọn frame
  như `frontend/src/live/pace.ts`), chạy lại khối 7–12 trên trace của `tools/gaze_study.py` với cờ điện thoại mới,
  rồi đếm cảnh báo `phone` trong bốn hành động có điện thoại và ngoài chúng. Cần trace `3mdad_day.pkl` (mục 9.10).
- Dùng khi đổi tần số YOLO, nơi chạy, hay cỡ ảnh đầu vào: trace không giữ ảnh nên không chạy lại model khác được.
- Bản xuất cỡ khác của cùng trọng số pretrained làm như ghi ở đầu `tools/download_models.py` (venv tạm có
  `ultralytics`, `imgsz` khác); không train.

## 10. Kiểm thử

```powershell
pytest tests\test_edge_agent tests\test_backend -q       # không cần camera, video hay Docker
ruff check edge_agent backend tools tests
cd frontend; npm test; npm run build                     # test frontend (vitest)
cd frontend; npx playwright install chromium; npm run e2e   # test end to end #/live + dashboard (lần đầu)
```

Logic theo thời gian (khối 7–12) được test bằng **chuỗi số giả**, không cần video (quy ước của `CLAUDE.md`).

**Test end to end** (`frontend/e2e/`, Playwright, cũng chạy trong CI):
- Tự dựng backend trên database tạm và bản build frontend có cổng test (`VITE_E2E=1`); không đụng vào
  `data/driverguard.db`. Cần Python (requirements-dev) và mạng để tải Pyodide và numpy (khoảng 10 MB; từ M45 không còn OpenCV).
- Camera là camera giả của Chrome; khối 3 nhận **landmark số tổng hợp** (`tools/e2e_setup.py`) thay cho
  MediaPipe, YOLO tắt. Không có ảnh khuôn mặt nào, không cần file model. Khối 6–14 chạy thật trong Pyodide.
- Kịch bản: đăng ký khi đỗ → lái → nhắm mắt thành L3 → kết thúc chuyến (dùng thử); tài xế đăng nhập → đổi
  tài xế → đăng ký lại → kết thúc chuyến → quản lý thấy báo cáo trên dashboard.

---

## 11. Lưu ý quan trọng

### Quyền riêng tư

- Ảnh chỉ nằm trong RAM. Không công cụ nào ghi frame ra đĩa, kể cả `debug_view`, `eval` và `benchmark`.
- Backend **từ chối (HTTP 422)** mọi payload có trường tên như ảnh (`image`, `frame`, `photo`…), data URI, chữ ký file ảnh ở dạng base64, chuỗi giống base64 dài, hoặc dữ liệu nhị phân. Thông báo lỗi không lặp lại nội dung bị từ chối.
- Edge cũng kiểm tra tương tự **trước khi** đưa vào hàng đợi, nên dữ liệu ảnh không rời khỏi xe.

### Dữ liệu và bảo mật

- `models/`, `data/`, `.env`, `frontend/node_modules` **không** có trong git.
- `data/outbox.db` là **hàng đợi offline** của xe: những sự kiện chưa gửi được sẽ nằm ở đây. **Đừng xóa** nếu còn sự kiện chưa gửi; chúng tự gửi lại khi có mạng. Khi chạy thử, nên dùng outbox riêng (`publisher.outbox_path` trong YAML).
- Nếu **không đặt `DG_JWT_SECRET`**, backend vẫn chạy nhưng dùng khóa ngẫu nhiên, nên mọi phiên đăng nhập mất hiệu lực khi khởi động lại. Chỉ dùng cách này để thử.
- Khóa thiết bị chỉ hiện **một lần** lúc tạo. Nếu mất thì phải tạo thiết bị mới.
- Tài xế chỉ xem được dữ liệu của chính mình, kể cả khi gọi thẳng API với `driver_id` của người khác.

### Vận hành

- HUD server chỉ nghe trên `127.0.0.1`. HUD phải chạy trên **cùng máy** với edge agent.
- Ngưỡng chỉnh trên dashboard có hiệu lực ở lần **xe đỗ** kế tiếp sau khi thiết bị hỏi lại backend (mỗi 5 phút), hoặc khi edge agent khởi động lại. Không bao giờ đổi lúc xe đang chạy (M47).
- Nút "Cảnh báo sai" chỉ dùng được trong **120 giây** sau khi có cảnh báo (`hud.feedback_window_s`; HUD đọc giá trị này từ thiết bị).
- **Mất camera** (rút dây, lỗi driver): sau `capture.max_consecutive_failures` lần đọc lỗi, hoặc `capture.frame_timeout_s` (3 s) không có frame, edge agent coi là mất camera. HUD hiện "Mất camera", backend nhận sự kiện `camera_lost` (loại `system`, mức 0, không tính vào thống kê cảnh báo), và camera được mở lại mỗi `capture.reconnect_interval_s` (2 s). Có hình trở lại thì gửi `camera_restored`. Video file vẫn kết thúc bình thường.
- Ngưỡng liên quan nhau được kiểm tra chéo (`edge_agent/config.py`, `CONSISTENCY_RULES`, ví dụ L1 < L2, sự kiện microsleep không muộn hơn luật L3): YAML sai thì agent không khởi động, ngưỡng từ dashboard sai thì backend trả 422 khi lưu và thiết bị bỏ qua.
- Khi xe dừng (dưới `context.min_speed_kmh` = 5 km/h), nhánh mất tập trung tắt. Nếu không có tín hiệu tốc độ (`speed_kmh = None`), hệ thống mặc định coi xe đang chạy (`context.assume_moving_when_speed_unknown`) nhưng không coi là tốc độ cao; cả risk engine lẫn nhánh 8 đều theo quy tắc này.
- Nhánh buồn ngủ khi xe **đứng yên** (dưới `context.stationary_kmh` = 1 km/h; xe bò 2–4 km/h lúc kẹt xe vẫn tính là đang đi): cảnh báo buồn ngủ tối đa **L1** (`risk.drowsy.stationary_max_level`), nên microsleep ở đèn đỏ vẫn có chime, còn tài xế đỗ xe nhắm mắt nghỉ không bị báo động mạnh L3. Đứng yên từ `context.rest_after_s` (120 s) trở lên thì coi là **nghỉ**: không cảnh báo buồn ngủ, không đưa vào timeline mệt mỏi. Khi xe chạy lại, dữ liệu buồn ngủ gom từ lúc dừng (PERCLOS, microsleep, ngáp, gật đầu, mốc mắt mở) bị xoá, để giấc nghỉ không gây cảnh báo ở những giây đầu của lần lái tiếp. Đánh đổi: tài xế ngủ gật ở đèn đỏ chỉ nhận chime L1, và đèn đỏ dài hơn 120 s thì bị coi là nghỉ. Key cũ `risk.drowsy.active_when_stopped` đã bỏ (đặt `stationary_max_level: 0` để tắt hẳn khi đứng yên).
- Lệnh đặt biến môi trường trên PowerShell: `$env:DG_DEVICE_KEY = "..."`. Trên bash: `export DG_DEVICE_KEY=...`.

### Giới hạn hiện tại

- **Khối 5 (Eye-state CNN)** dùng model có sẵn `open-closed-eye-0001` (Intel Open Model Zoo, Apache-2.0, học trên MRL Eye); nhãn lớp đầu ra được xác định theo demo chính thức của Intel (README của model ghi ngược). Trên NITYMED (lái ban đêm) CNN tách mắt nhắm kém EAR (AUC 0,881 so với 0,987), nên chỉ được gọi khi EAR thật sự không tin được: **độ sáng tính trên vùng mặt** (trước CLAHE), không phải cả khung (xe tối nhưng mặt được chiếu sáng thì EAR vẫn tốt), và **lệch EAR hai mắt chỉ tính khi một mắt còn mở** (hai mắt cùng nhắm là chúng đồng ý; cách chia cho EAR trung bình cũ làm CNN bị gọi đúng lúc nhắm mắt và che mất microsleep). Blendshape `eyeBlink` đã được thử làm nguồn thay CNN: ngang EAR trên NITYMED nhưng tệ hơn CNN với người đeo kính (YawDD), nên chỉ dùng làm phiếu xác nhận nhắm sâu. Khi được gọi vì **mặt tối hoặc camera IR**, CNN được giữ thêm `eye_state.hold_s` (2 s) sau khi điều kiện hết, để nguồn EAR/CNN không đổi qua lại từng frame lúc chạng vạng (chuỗi giả: không giữ thì PERCLOS 0,36 và 599 lần chớp giả trong 40 s; giữ 2 s thì cả hai về 0). Khi được gọi vì **hai mắt lệch EAR** (kính, chói) thì không giữ: CNN yếu với người đeo kính, giữ thêm làm microsleep sai trên YawDD tăng 6 → 18, toàn ở clip đeo kính.
- Một số giá trị của nhánh buồn ngủ lệch nhẹ so với bảng luật: sự kiện microsleep 1,0 s (luật L3 vẫn dùng 1,5 s), ngáp 1,5 s (bảng: 2 s), gục đầu dưới 2 s (bảng: dưới 1 s). Có thể chỉnh trong YAML. Frame có `face_conf` < `features.min_face_conf` (0,9: mặt ra ngoài khung một phần) không được tính vào PERCLOS, mốc mắt mở, ngáp, gật đầu và góc nhìn lệch; pitch của frame đó chỉ dùng để nhận ra gục đầu.
- Ngưỡng MAR của ngáp đã hạ từ 0,6 xuống 0,45 (đóng lại dưới 0,34), kiểm chứng trên `yawn_eye_mouth` và video YawDD.
- Chặn microsleep lúc ngáp / nói (`drowsiness.microsleep_mask`): có thể che mất một microsleep thật nếu tài xế vừa ngáp xong (tối đa 1,5 s). Lúc **đang nói**, mắt nhắm sâu mà blendshape cũng xác nhận thì vẫn được tính (`talk_spares_deep`): môi cử động nhẹ của người đang buồn ngủ từng che mất microsleep thật trên NITYMED; tắt blendshapes thì mặt nạ nói chuyện hoạt động như cũ. Miệng mở liên tục quá 8 s (hàm trễ khi ngủ) thì không che nữa. PERCLOS cũng bỏ qua các frame này (`drowsiness.perclos_use_mask`), nên khi tài xế nói liên tục thì PERCLOS gần như không được tính (trên YawDD, 82% thời gian của clip Talking bị che).
- Microsleep chỉ tính đợt nhắm **sâu** (`drowsiness.microsleep_deep`): ít nhất một nửa số frame có EAR ≤ 0,5 × mốc mắt mở **và** blendshape `eyeBlink` ≥ 0,5 (hoặc, ở frame khối 5 quyết định, CNN p_closed ≥ 0,8 trên thiết bị và `eyeBlink` ≥ 0,55 trên bản web / APK). Phiếu blendshape loại các lần EAR sụp vì lóa kính, cúi đầu, mắt hẹp lúc chưa học xong mốc. Người có mắt chỉ khép hờ khi ngủ gật (không nhắm hẳn) sẽ được bắt qua PERCLOS thay vì luật L3 microsleep, miễn là EAR xuống dưới 0,65 × mốc.
- PERCLOS xét **từng frame** (`drowsiness.perclos_close_ratio` = 0,65 × mốc mắt mở), không dùng trạng thái có hysteresis của mắt. Trước đây, sau mỗi lần chớp, hysteresis giữ trạng thái "nhắm" suốt lúc mắt nheo (0,65–0,75 × mốc, ví dụ nheo vì nắng) nên PERCLOS lên gần 100% và ra L1 sau khoảng 11 s. Đánh đổi: mắt hé ở khoảng 0,65–0,75 × mốc không còn được tính vào PERCLOS.
- YOLO **INT8** nhanh hơn khoảng 2 lần và nhỏ hơn khoảng 3,6 lần, nhưng **chưa được đo độ chính xác**, nên hệ thống vẫn dùng FP32.
- Đã có số trên video có nhãn theo frame (FL3D / NITYMED, mục 9.3, `eval/results/dataset_fl3d.md`), nhưng NITYMED là diễn lại và quay ban đêm; SUST-DDD (xe thật) chỉ có nhãn theo clip 10 s, ngắn hơn thời gian khởi động PERCLOS. Đã có số theo từng ảnh trên dataset Kaggle (mục 9.2, `eval/results/dataset_*.md`): ngưỡng MAR 0,45 bỏ sót khoảng 17 % ảnh ngáp của `yawn_eye_mouth` (0,6 bỏ sót 36 %).
- **macOS:** MediaPipe 1.0.1 bị crash (`graph_service.h ... Service is unavailable`, Metal) trên macOS mới, kể cả ở chế độ VIDEO. `requirements.txt` đã ghim `mediapipe==0.10.21` cho macOS.
- CAN đang là **giả lập**. Tín hiệu thật từ xe sẽ thay `CanSimulator`, còn phần xử lý ngữ cảnh giữ nguyên.
- **Giấy phép:** YOLOv8 (Ultralytics) dùng **AGPL-3.0**, còn repo dùng MIT. Cần xem lại nếu phân phối sản phẩm.
- CI (`.github/workflows/ci.yml`) có 3 job: `python` (ruff check + format trên `edge_agent/ backend/ tools/ tests/`, rồi pytest), `frontend` (typecheck, vitest, build) và `template` (phần `src/` của khóa học, tách riêng).

---

## 12. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Model not found: ...face_landmarker.task` | Chưa tải model | `python tools\download_models.py` |
| `[phone] disabled: Model not found ...yolov8n.onnx` | Chưa export YOLO | Làm theo mục 6.2 |
| `[publisher] disabled: no --device-key` | Thiếu khóa thiết bị | Đặt `$env:DG_DEVICE_KEY` hoặc dùng `--device-key` |
| HUD báo "Không kết nối được thiết bị" | Edge agent chưa chạy hoặc `--hud-port 0` | Chạy `python -m edge_agent.main ...`, hoặc bấm "Chạy mô phỏng" |
| HUD báo "Không nhận dữ liệu từ camera" | Vòng lặp camera bị treo hoặc đã kết thúc | Kiểm tra camera, hoặc thêm `--loop` cho video |
| Dashboard: "Không kết nối được máy chủ" | Backend chưa chạy hoặc sai địa chỉ | Chạy uvicorn cổng 8100, kiểm tra `VITE_API_URL` |
| Lỗi CORS trên trình duyệt | Frontend chạy ở cổng khác 5173 | Dùng `npm run dev` (cổng cố định), hoặc thêm origin vào `DG_CORS_ORIGINS` |
| Tự bị đăng xuất | Token hết hạn hoặc backend đổi secret | Đặt `DG_JWT_SECRET` cố định, đăng nhập lại |
| `[config] ... IGNORED: ...` | Ngưỡng từ dashboard mâu thuẫn với YAML | Sửa ngưỡng trên dashboard (ví dụ L1 < L2) |
| Số hiện trên HUD / debug nhảy liên tục | Nhiễu landmark mỗi frame là bình thường | Xem đồ thị trong `debug_view` (phím `g`); các nhánh phân tích đã lọc theo thời gian |
| Góc yaw lệch khi nhìn thẳng | Camera lắp lệch | Mốc nhìn đường tự học sau khoảng 30 s; hoặc đặt `distraction.baseline` |
| `UnicodeEncodeError` khi in | Console Windows dùng cp1252 | `tools/eval.py` và `benchmark.py` đã tự chuyển sang UTF-8; với lệnh khác, đặt `$env:PYTHONIOENCODING="utf-8"` |
| `git push` báo `cannot spawn .git/hooks/pre-push` | File hook có BOM và CRLF | Lưu `.git/hooks/pre-push` dạng UTF-8 **không BOM**, xuống dòng **LF** |
| Cài torch lỗi "Long Path" | Đường dẫn trên Windows dài hơn 260 ký tự | Tạo venv ở thư mục ngắn như `C:\tmp\yx` (mục 6.2) |

---

## 13. Trạng thái dự án

| Mốc | Nội dung | Trạng thái |
|---|---|---|
| M0 | Khối 1, 2: đọc video, resize, CLAHE | Xong |
| M1 | Khối 3, 6: MediaPipe, EAR, MAR, head pose | Xong |
| M2 | Khối 7: PERCLOS, microsleep, ngáp, gục đầu (+ khối 5 Eye-state CNN) | Xong |
| M3 | Khối 4, 8: YOLO điện thoại, nhìn lệch | Xong |
| M4 | Khối 9–12: risk engine, CAN giả lập, cooldown | Xong |
| M5 | Khối 14 + backend FastAPI | Xong |
| M6 | Dashboard React + HUD | Xong |
| M7 | Script eval + benchmark FPS + dataset Kaggle | Công cụ xong, bảng FPS có số, số theo từng ảnh trên Kaggle; chờ video có nhãn thời gian |
| M8 | Chạy toàn bộ trên trình duyệt (`#/live`) | Xong |
| M9–M29 | **Version 2**: đăng ký tài xế, tạm ngưng giám sát, chớp chậm, gục / cúi, nhướn mày, giao diện cho tài xế, kết thúc chuyến + báo cáo, mô phỏng lái xe, xi nhan, lớp chung + e2e, FMEA, âm thanh luôn bật, đồng ý trước khi đăng ký, cúi nhìn xuống ≠ nhắm mắt, mất tín hiệu xe, sửa tổng kết, sức khoẻ vòng lặp, tài liệu | Xong (v2.0.0 deploy 01/10 gồm M9–M18) |
| M43–M48 | **Version 3 (06/10)**: tạm ngưng giám sát có lý do khi ảnh không đọc được, không phản ứng với còi / "Bạn còn ở đó không?" / báo quản lý ngay, bản web bỏ OpenCV và server nén + cache, phép thử ánh sáng trong RAM, ngưỡng tải lại khi đỗ + áp thử + quay lui, tài xế tự tải và yêu cầu xoá dữ liệu | Xong, chưa deploy (ngưỡng tạm; xem `docs/release-v3.md`) |

Chi tiết từng mốc: `docs/roadmap.md`; thay đổi ở v2: `docs/release-v2.md`, v3: `docs/release-v3.md`, v4 (từ M70): `docs/release-v4.md`; việc chưa làm:
`docs/improvements.md`. Quy ước làm việc: `CLAUDE.md`.
