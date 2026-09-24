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
| **Nhắm mắt lâu / microsleep** | EAR; khi EAR không tin cậy (IR, tối, lóa kính) thì CNN trạng thái mắt | Mắt nhắm liên tục ≥ 1,5 s → L3 ngay |
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
| 7 Nhánh buồn ngủ | `edge_agent/analysis/drowsiness.py` | `DrowsinessState` |
| 8 Nhánh mất tập trung | `edge_agent/analysis/distraction.py` | `DistractionState` |
| 9 Risk engine | `edge_agent/decision/risk_engine.py` | `RiskAssessment` |
| 10 Ngữ cảnh | `edge_agent/context/can_sim.py`, `vehicle_context.py` | `VehicleSignals`, `VehicleContext` |
| 11 Trip memory | `edge_agent/decision/trip_memory.py` | `TripState` |
| 12 Alert manager | `edge_agent/decision/alert_manager.py` | `AlertOutput`, `Alert` |
| 13 HUD | `edge_agent/hud/hud.py`, `server.py`; `frontend/src/hud/` | — |
| 14 Publisher | `edge_agent/io/publisher.py` | JSON gửi `POST /api/v1/events` |
| Nối 7–12 | `edge_agent/decision/pipeline.py` | `DecisionResult` |
| Nối 1–14 | `edge_agent/main.py` | — |

### 3.3 Cổng mạng

| Dịch vụ | Địa chỉ mặc định | Ghi chú |
|---|---|---|
| Backend (FastAPI) | `http://localhost:8100` | Swagger: `/docs` |
| Frontend (Vite dev) | `http://localhost:5173` | Backend và HUD server chỉ cho phép origin này |
| HUD server của edge | `http://127.0.0.1:8765` | Chỉ nghe localhost, không mở ra mạng |

---

## 4. Cấu trúc thư mục

```
P-135/
├── CLAUDE.md                  Ràng buộc và quy ước dự án
├── HowToUse.md                Tài liệu này
├── requirements.txt           Thư viện Python
├── config/
│   ├── thresholds.yaml        TẤT CẢ ngưỡng (không hardcode trong code)
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
│   └── benchmark.py           FPS, latency p50/p95, FP32 vs INT8
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
| CPU | Không cần GPU. Máy thử (Intel, 18 luồng): vòng lặp chính > 150 FPS với frame tổng hợp |

---

## 6. Cài đặt

Các lệnh dưới đây dùng **PowerShell trên Windows**. Trên Linux/macOS, thay `.venv\Scripts\` bằng `.venv/bin/`.

### 6.1 Môi trường Python

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

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

### 7.3 Toàn bộ hệ thống (3 terminal)

**Terminal 1 – Backend**

```powershell
.venv\Scripts\activate
uvicorn backend.app:app --port 8100
```

**Terminal 2 – Edge agent trong xe**

```powershell
.venv\Scripts\activate
$env:DG_DEVICE_KEY = "dgk_..."          # khóa từ bước 7.2
python -m edge_agent.main --source 0 --backend http://localhost:8100 --device-id cam-001 --scenario config\scenarios\highway_night.yaml
```

| Tùy chọn | Ý nghĩa |
|---|---|
| `--source` | Camera (`0`) hoặc file video |
| `--scenario` | Kịch bản CAN giả lập: `city_day.yaml` (mặc định), `highway_night.yaml`, `parked.yaml` |
| `--backend`, `--device-id` | Bật gửi metadata (bỏ đi thì chạy hoàn toàn offline) |
| `--hud-port` | Cổng server HUD (mặc định 8765, `0` = tắt) |
| `--no-window` | Không mở cửa sổ, chỉ in ra terminal |
| `--no-phone` | Tắt YOLO |
| `--status-every` | Số giây giữa hai dòng trạng thái |

Khi chạy, terminal in các dòng `[ALERT L2] phone -> sound + seat vibration ...` và dòng trạng thái định kỳ.

**Terminal 3 – Frontend**

```powershell
cd frontend
npm run dev
```

- **HUD trong xe:** http://localhost:5173/#/hud. Không cần đăng nhập, đọc trạng thái từ edge agent. Nếu không có edge agent, bấm **"Chạy mô phỏng"** để demo.
- **Dashboard:** http://localhost:5173/#/dashboard. Đăng nhập bằng tài khoản ở bước 7.2.

### 7.4 Kịch bản demo gợi ý

1. Đăng nhập dashboard bằng `kysu` (kỹ sư).
2. Trước webcam: nhắm mắt khoảng 2 s → HUD chuyển **L3**, terminal in `[ALERT L3] microsleep`.
3. Cầm điện thoại lên tai khoảng 3 s → **L2** `phone`.
4. Trên HUD bấm **"Cảnh báo sai"** → dashboard tab *Nhật ký sự kiện* hiện thẻ "Tài xế báo sai".
5. Chờ hơn 1 phút → tab *Timeline mệt mỏi* có điểm `drowsy_score` theo từng phút.
6. Tab *Ngưỡng*: đổi `drowsy_score → L1` thành 45 → **Lưu** → khởi động lại edge agent. Terminal in `[config] 1 tuned thresholds applied`.

---

## 8. Cấu hình và ngưỡng

### 8.1 `config/thresholds.yaml`

Mọi ngưỡng nằm ở đây, mỗi dòng có chú thích.

| Mục | Khối | Ví dụ |
|---|---|---|
| `capture`, `preprocess` | 1, 2 | độ phân giải camera, kích thước resize, CLAHE |
| `landmarks`, `features` | 3, 6 | độ tin cậy MediaPipe, tiêu cự camera |
| `eye_state` | 5 | model, cách cắt mắt, khi nào gọi CNN (IR, độ sáng, lệch EAR hai mắt) |
| `phone` | 4 | model, ngưỡng tin cậy, tần suất YOLO, vùng tài xế |
| `drowsiness` | 7 | tỉ lệ nhắm mắt, microsleep, PERCLOS, ngáp, gục đầu |
| `distraction` | 8 | góc nhìn lệch, tốc độ tối thiểu, mốc nhìn đường |
| `context` | 10 | tốc độ cao, khung giờ đêm, lái lâu, thời gian xi nhan |
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
- Edge agent tải ngưỡng **khi khởi động** và ghi đè lên YAML. Nếu kết quả không hợp lệ (ví dụ L1 ≥ L2) thì bỏ qua và dùng YAML.
- Ô để trống nghĩa là thiết bị dùng giá trị trong `thresholds.yaml` của nó.

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

### 9.2 Tốc độ: `tools/benchmark.py`

```powershell
python tools\benchmark.py --source data\videos\clip01.mp4 --out eval\results\benchmark.md
```

- Đo FPS và độ trễ p50/p95 của từng khối, rồi của cả vòng lặp chính.
- Đo kích thước model và so YOLO **FP32 với INT8**. Lần đầu chạy sẽ tự tạo `models/yolov8n_int8.onnx`.
- Nên dùng **video có mặt người**. Không có `--source` thì dùng frame tổng hợp không có mặt, nên thời gian đo của MediaPipe sẽ thấp hơn thực tế.

---

## 10. Kiểm thử

```powershell
pytest tests\test_edge_agent tests\test_backend -q       # ~260 test, không cần camera hay video
ruff check edge_agent backend tools tests
cd frontend; npm test; npm run build
```

Logic theo thời gian (khối 7–12) được test bằng **chuỗi số giả**, không cần video (quy ước của `CLAUDE.md`).

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
- Ngưỡng chỉnh trên dashboard chỉ có hiệu lực **khi edge agent khởi động lại**.
- Nút "Cảnh báo sai" chỉ dùng được trong **120 giây** sau khi có cảnh báo.
- Khi xe dừng (dưới 5 km/h), nhánh mất tập trung tắt. Nếu không có tín hiệu tốc độ, hệ thống mặc định coi xe đang chạy.
- Lệnh đặt biến môi trường trên PowerShell: `$env:DG_DEVICE_KEY = "..."`. Trên bash: `export DG_DEVICE_KEY=...`.

### Giới hạn hiện tại

- **Khối 5 (Eye-state CNN)** dùng model có sẵn `open-closed-eye-0001` (Intel Open Model Zoo, Apache-2.0, học trên MRL Eye). Chưa đo độ chính xác trên dataset của mình; nhãn lớp đầu ra được xác định theo demo chính thức của Intel (README của model ghi ngược).
- Một số giá trị của nhánh buồn ngủ lệch nhẹ so với bảng luật: sự kiện microsleep 1,0 s (luật L3 vẫn dùng 1,5 s), ngáp 1,5 s (bảng: 2 s), gục đầu dưới 2 s (bảng: dưới 1 s). Có thể chỉnh trong YAML. PERCLOS **chưa loại** các frame có `face_conf` thấp.
- Ngưỡng MAR của ngáp (0,6) là giá trị ước lượng. Hãy kiểm tra trên đồ thị MAR của `debug_view`.
- YOLO **INT8** nhanh hơn khoảng 2 lần và nhỏ hơn khoảng 3,6 lần, nhưng **chưa được đo độ chính xác**, nên hệ thống vẫn dùng FP32.
- **Chưa có số precision/recall thật**: cần dataset có nhãn (xem mục 9.1).
- CAN đang là **giả lập**. Tín hiệu thật từ xe sẽ thay `CanSimulator`, còn phần xử lý ngữ cảnh giữ nguyên.
- **Giấy phép:** YOLOv8 (Ultralytics) dùng **AGPL-3.0**, còn repo dùng MIT. Cần xem lại nếu phân phối sản phẩm.
- CI (`.github/workflows/ci.yml`) chỉ chạy test Python, chưa chạy test frontend.

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
| M7 | Script eval + benchmark FPS | Công cụ xong, bảng FPS có số; chờ dataset có nhãn |

Chi tiết từng mốc: `docs/roadmap.md`. Quy ước làm việc: `CLAUDE.md`.
