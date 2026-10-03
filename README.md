# DriverGuard

Hệ thống giám sát tài xế (Driver Monitoring System) chạy **ngay trên thiết bị**: camera nhìn tài xế,
phát hiện **buồn ngủ** (nhắm mắt lâu, PERCLOS, ngáp, gục đầu, chớp chậm) và **mất tập trung** (nhìn khỏi
đường, điện thoại), cảnh báo theo 4 mức L0–L3, và chỉ gửi **metadata JSON** lên máy chủ. Ảnh khuôn mặt
không bao giờ được ghi ra đĩa hay gửi đi; chỉ dùng model pretrained (MediaPipe, YOLOv8n, CNN mắt Intel).

| | |
|---|---|
| **Phiên bản** | v2.2 (deploy 02/10/2026, các mốc M0–M31) |
| **Live URL** | https://driveguard-v2-production.up.railway.app: dashboard `/#/dashboard`, giám sát trên trình duyệt `/#/live`, điều khiển xe `/#/drive?code=…`, API `/health`, Swagger `/docs` |
| **Sản phẩm cuối** | App APK chạy trên hub gắn trên xe, bọc chính code web; bản web để xem thử |
| **Khoá học** | AI20K Build Phase, VinUni (repo sinh từ template của khoá, xem [mục Template](#template-khoá-ai20k)) |

## Mục lục

1. [Vấn đề và giải pháp](#vấn-đề-và-giải-pháp)
2. [Người dùng và tính năng](#người-dùng-và-tính-năng)
3. [Kiến trúc](#kiến-trúc)
4. [Tech stack](#tech-stack)
5. [Quick start](#quick-start)
6. [Biến môi trường](#biến-môi-trường)
7. [API và ví dụ gọi](#api-và-ví-dụ-gọi)
8. [Kiểm thử và đánh giá](#kiểm-thử-và-đánh-giá)
9. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
10. [Deliverables](#deliverables)
11. [Team](#team)
12. [AI usage logging](#ai-usage-logging)

## Vấn đề và giải pháp

**Vấn đề.** Tài xế buồn ngủ hoặc mất tập trung (nhìn điện thoại, nhìn khỏi đường vài giây) là nguyên nhân
lớn của tai nạn. Hệ thống cảnh báo hiện có thường **báo sai nhiều** nên tài xế tắt đi, **không nói rõ khi
không quan sát được** (mất mặt, mất camera), và nhiều giải pháp gửi video khuôn mặt lên cloud.

**Giải pháp.** DriverGuard dùng camera có sẵn, chạy toàn bộ xử lý trên thiết bị (≥ 15 FPS, không cần GPU):

- Phát hiện từ landmark khuôn mặt (EAR, MAR, góc đầu), CNN trạng thái mắt và YOLO điện thoại, rồi tính
  `drowsy_score`, `distraction_score` → mức **L0–L3**.
- **Chống cảnh báo sai** ngang với độ chính xác: lọc theo thời gian, cooldown, theo tốc độ và xi nhan
  (xe đứng yên thì không cảnh báo; xi nhan thì cho nhìn ngang lâu hơn), đăng ký khuôn mặt để có mốc riêng
  của từng tài xế, nút "Cảnh báo sai" để kỹ sư chỉnh ngưỡng.
- **Trung thực khi không giám sát được**: mất mặt, mất camera, mất tín hiệu xe, lỗi / chậm xử lý đều hiện
  rõ trên HUD kèm âm báo.
- **Riêng tư**: frame chỉ nằm trong RAM; backend từ chối mọi dữ liệu giống ảnh / base64.

## Người dùng và tính năng

| Vai trò | Dùng gì | Làm được gì |
|---|---|---|
| Tài xế (`driver`) | HUD trong xe `#/hud` / `#/live` | Nhận cảnh báo màu + chữ + âm thanh, đăng ký khuôn mặt (~10 s, khi xe dừng), báo cảnh báo sai, xem tổng kết cuối chuyến, chỉ thấy dữ liệu của mình |
| Kỹ sư an toàn (`engineer`) | Dashboard | Nhật ký sự kiện, timeline mệt mỏi, báo cáo chuyến, **chỉnh ngưỡng** (lưu theo phiên bản, thiết bị tải khi khởi động) |
| Quản lý đội xe (`manager`) | Dashboard | Xem toàn đội, báo cáo chuyến chưa ai xem, ngưỡng chỉ đọc |
| Quản trị (`admin`) | Dashboard / CLI | Tạo tài khoản, tạo thiết bị (khóa thiết bị) |

**Một chuyến đi:** xe dừng → HUD hỏi đồng ý rồi hướng dẫn đăng ký khuôn mặt → lái, hệ thống cảnh báo
theo mức (âm thanh luôn bật) → tài xế bấm "Kết thúc chuyến" → bảng tổng kết cho tài xế, quản lý / kỹ sư
xem ở tab "Báo cáo chuyến đi" trên dashboard.

| Mức | Khi nào (ví dụ) | Cảnh báo |
|---|---|---|
| L0 | Bình thường | Không |
| L1 | `drowsy_score` bắt đầu cao | Nhắc nhẹ trên HUD |
| L2 | Cầm điện thoại, nhìn khỏi đường lâu, buồn ngủ rõ | Màu cam + âm báo |
| L3 | Microsleep (nhắm mắt ≥ 1,5 s khi xe chạy) | Đỏ toàn màn hình, còi lặp tới khi mở mắt |

Chi tiết ngưỡng ở [`config/thresholds.yaml`](config/thresholds.yaml) và [HowToUse.md mục 2](HowToUse.md#2-chức-năng).

## Kiến trúc

14 khối chạy theo thứ tự, mỗi khối là một module trong `edge_agent/`, giao tiếp qua dataclass:

```mermaid
flowchart LR
    subgraph Device["Thiết bị trong xe (on-device, frame chỉ ở RAM)"]
        B1[1 Camera] --> B2[2 Tiền xử lý]
        B2 --> B3[3 MediaPipe<br/>Face Landmarker]
        B2 --> B4[4 YOLOv8n<br/>điện thoại]
        B2 --> B5[5 CNN mắt]
        B3 & B4 & B5 --> B6[6 Feature extractor]
        B6 --> B7[7 Nhánh buồn ngủ]
        B6 --> B8[8 Nhánh mất tập trung]
        B10[10 Ngữ cảnh xe<br/>tốc độ, xi nhan] --> B9
        B11[11 Trip memory] --> B9
        B7 & B8 --> B9[9 Risk engine<br/>L0–L3]
        B9 --> B12[12 Alert manager]
        B12 --> B13[13 HUD]
        B12 --> B14[14 Metadata publisher]
    end
    B14 -- "JSON (không ảnh)" --> API[Backend FastAPI<br/>SQLite]
    API --> DASH[Dashboard React]
```

Cùng một logic Python chạy hai cách: trên thiết bị (`python -m edge_agent.main`) và trong trình duyệt
(`#/live`, Pyodide + MediaPipe Web + onnxruntime-web). Sơ đồ đầy đủ (luồng dữ liệu, trình tự một cảnh báo,
deployment, phần thêm ở v2) ở [docs/architecture_diagram.md](docs/architecture_diagram.md).

## Tech stack

| Lớp | Công nghệ |
|---|---|
| Thị giác (pretrained) | MediaPipe Face Landmarker 0.10, YOLOv8n ONNX (COCO, lớp điện thoại), CNN mắt đóng / mở (Intel Open Model Zoo, ONNX) |
| Edge agent | Python 3.11+, OpenCV, NumPy, onnxruntime, PyYAML |
| Backend | FastAPI, Uvicorn, Pydantic 2, SQLite, JWT (PyJWT), mật khẩu scrypt |
| Frontend | React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4; `#/live`: Pyodide, `@mediapipe/tasks-vision`, `onnxruntime-web` |
| Kiểm thử | pytest, Vitest, Playwright (e2e), ruff |
| Deploy | Docker (`Dockerfile.railway`), Railway; gói cài edge agent cho máy trong xe (`packaging/edge/`) |

DriverGuard **không dùng LLM**: phần LangGraph / OpenAI trong `src/` là code mẫu của template khoá học.

## Quick start

**Cần:** Python ≥ 3.11 (khuyên 3.12), Node.js ≥ 20.19, [uv](https://docs.astral.sh/uv/) (hoặc pip),
một webcam. Lệnh dưới đây cho macOS / Linux; Windows (PowerShell) xem [HowToUse.md mục 6–7](HowToUse.md#6-cài-đặt).

Chỉ muốn xem thử: mở [Live URL](https://driveguard-v2-production.up.railway.app/#/live), không cần cài gì.

### 1. Cài môi trường và model

```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-4/P-135.git && cd P-135
uv venv -p 3.12 --seed .venv && source .venv/bin/activate     # hoặc: make venv
uv pip install -r requirements-dev.txt
python tools/download_models.py        # face_landmarker.task + open_closed_eye.onnx vào models/
```

`yolov8n.onnx` (phát hiện điện thoại) cần export bằng `ultralytics` + `torch` (~1 GB), nên làm một lần
trong venv tạm (HowToUse [mục 6.2](HowToUse.md#62-model-bắt-buộc)). Thiếu file này hệ thống vẫn chạy, chỉ
tắt phát hiện điện thoại.

### 2. Biến môi trường

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # dán vào DG_JWT_SECRET trong .env
```

### 3. Khởi tạo backend (một lần)

```bash
python -m backend.manage create-user admin --role admin
python -m backend.manage create-user kysu  --role engineer
python -m backend.manage create-user boss  --role manager
python -m backend.manage create-user an    --role driver --driver-id drv-001
python -m backend.manage create-device cam-001 --driver-id drv-001   # in khóa thiết bị MỘT lần → DG_DEVICE_KEY
```

Lệnh sẽ hỏi mật khẩu (≥ 8 ký tự) để mật khẩu không nằm trong lịch sử shell.

### 4. Chạy (4 terminal)

```bash
# 1. Backend: API ở :8100, Swagger http://localhost:8100/docs
uvicorn backend.app:app --port 8100                      # hoặc: make run

# 2. Edge agent: camera 0, HUD server 127.0.0.1:8765, gửi metadata lên backend
python -m edge_agent.main --source 0 --backend http://localhost:8100 --device-id cam-001

# 3. Mô phỏng tốc độ / xi nhan (thay CAN của xe): w/s tăng giảm tốc, a/d xi nhan, space dừng
python tools/drive_sim.py

# 4. Frontend
cd frontend && npm install && npm run dev
```

| Trang | URL |
|---|---|
| HUD trong xe (đọc edge agent, có nút "Chạy mô phỏng" khi không có agent) | http://localhost:5173/#/hud |
| Giám sát ngay trong trình duyệt (cần `npm run prepare-live` một lần) | http://localhost:5173/#/live |
| Dashboard (đăng nhập bằng tài khoản ở bước 3) | http://localhost:5173/#/dashboard |
| Xem trước các trạng thái HUD | http://localhost:5173/#/hud-preview |

Chỉ muốn xem camera và chỉ số, không cần backend: `python tools/debug_view.py --source 0`.
Kịch bản demo gợi ý: [HowToUse.md mục 7.4](HowToUse.md#74-kịch-bản-demo-gợi-ý).

## Biến môi trường

Backend đọc `.env` ở thư mục gốc (tiền tố `DG_`); frontend đọc `frontend/.env.local`
(mẫu ở [`frontend/.env.example`](frontend/.env.example)). Không commit `.env`.

| Biến | Dùng ở | Mặc định | Ý nghĩa |
|---|---|---|---|
| `DG_JWT_SECRET` | backend | (trống) | **Bắt buộc khi chạy thật.** Chuỗi ngẫu nhiên dài để ký token đăng nhập |
| `DG_DB_PATH` | backend | `data/driverguard.db` | File SQLite |
| `DG_TOKEN_TTL_MIN` | backend | `60` | Thời hạn đăng nhập (phút, 1–1440) |
| `DG_CORS_ORIGINS` | backend | `http://localhost:3000,http://localhost:5173` | Origin được gọi API, cách nhau bằng dấu phẩy |
| `DG_MAX_BODY_BYTES` | backend | `262144` | Giới hạn kích thước một request (byte) |
| `DG_STATIC_DIR` | `deploy/railway_app.py` | `static` | Thư mục dashboard đã build, phục vụ cùng origin với API (Railway) |
| `DG_DEVICE_KEY` | edge agent | (trống) | Khóa thiết bị từ `create-device`; thiếu thì agent chạy offline, không gửi metadata (hoặc truyền `--device-key`) |
| `VITE_API_URL` | frontend | `http://localhost:8100` | Địa chỉ backend |
| `VITE_EDGE_URL` | frontend | `http://127.0.0.1:8765` | HUD server của edge agent (`--hud-port`) |
| `AI_LOG_SERVER`, `AI_LOG_API_KEY`, `AI_LOG_DIR` | hook của khoá học | xem `.env.example` | Gửi log dùng AI lên server chấm ([mục AI usage logging](#ai-usage-logging)) |

Các biến còn lại trong `.env.example` (`OPENAI_API_KEY`, `DATABASE_URL`, `CHROMA_PERSIST_DIR`,
`LANGCHAIN_*`, `APP_*`) chỉ dành cho code mẫu `src/` của template, DriverGuard không dùng.

Tùy chọn dòng lệnh của edge agent (`--scenario`, `--sim-url`, `--hud-port`, `--no-window`, `--no-phone`…)
ở [HowToUse.md mục 7.3](HowToUse.md#73-toàn-bộ-hệ-thống-4-terminal).

## API và ví dụ gọi

Swagger đầy đủ: http://localhost:8100/docs (local) hoặc https://driveguard-v2-production.up.railway.app/docs.

| Endpoint | Ai gọi | Mục đích |
|---|---|---|
| `GET /health` | ai cũng được | Kiểm tra server |
| `POST /auth/login`, `GET /auth/me` | người dùng | Đăng nhập (JWT), xem mình là ai |
| `POST /api/v1/events` | thiết bị (`X-Device-Key`) | Gửi lô sự kiện / phản hồi / mẫu timeline / tổng kết chuyến |
| `POST /api/v1/web/events` | người dùng (`#/live`) | Như trên, từ trình duyệt |
| `GET /api/v1/events`, `/trips`, `/timeline`, `/stats` | mọi vai trò (tài xế chỉ thấy của mình) | Nhật ký, chuyến, timeline mệt mỏi, thống kê |
| `GET /api/v1/trip-reports[/{device}/{trip}]`, `POST …/review` | mọi vai trò / quản lý, kỹ sư, admin | Báo cáo cuối chuyến, đánh dấu đã xem |
| `GET`, `PUT /api/v1/thresholds` | xem: quản lý, kỹ sư, admin; sửa: kỹ sư, admin | Ngưỡng theo phiên bản |
| `GET /api/v1/device/thresholds` | thiết bị | Thiết bị tải ngưỡng khi khởi động |
| `GET`, `POST /api/v1/users`, `POST /api/v1/devices` | admin | Tạo tài khoản, thiết bị |
| `PUT`, `GET /api/v1/drive/{code}` | trang `#/drive` / `#/live` | Tốc độ + xi nhan theo mã ghép 6 ký tự (chỉ trong RAM) |

Ví dụ với backend local (đổi `BASE` thành Live URL để gọi bản deploy):

```bash
BASE=http://localhost:8100

# 1. Kiểm tra server
curl $BASE/health
# {"status":"ok"}

# 2. Đăng nhập, lấy token
TOKEN=$(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"kysu","password":"<mật khẩu>"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 3. Cảnh báo từ L2 trở lên, mới nhất trước
curl -s "$BASE/api/v1/events?min_level=2&limit=5" -H "Authorization: Bearer $TOKEN"

# 4. Chỉ những cảnh báo tài xế báo sai, của một tài xế
curl -s "$BASE/api/v1/events?false_alarm_only=true&driver_id=drv-001" -H "Authorization: Bearer $TOKEN"

# 5. Các chuyến gần đây và báo cáo chưa ai xem
curl -s "$BASE/api/v1/trips?limit=10" -H "Authorization: Bearer $TOKEN"
curl -s "$BASE/api/v1/trip-reports?unreviewed_only=true" -H "Authorization: Bearer $TOKEN"

# 6. Kỹ sư đổi ngưỡng (lưu thành phiên bản mới; ngoài khoảng cho phép trả 422)
curl -s -X PUT $BASE/api/v1/thresholds -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"values":{"risk.drowsy.l1":45}}'

# 7. Thiết bị gửi một cảnh báo (bình thường edge agent tự gửi; chỉ là JSON, không có ảnh)
curl -s -X POST $BASE/api/v1/events -H "X-Device-Key: $DG_DEVICE_KEY" -H 'Content-Type: application/json' -d '{
  "device_id": "cam-001",
  "events": [{
    "event_id": "3f6c1a52-8a4e-4c1e-9d0b-2a7f5e1c9b10",
    "ts": "2026-10-03T08:30:00+07:00",
    "trip_id": "trip-demo-1",
    "type": "drowsiness",
    "level": 3,
    "reasons": ["microsleep"],
    "drowsy_score": 82,
    "distraction_score": 10,
    "speed_kmh": 50,
    "metrics": {"closed_duration": 2.1, "perclos_60s": 0.31}
  }]
}'

# 8. Điều khiển xe từ xa theo mã ghép mà #/live hiện ra
curl -s -X PUT $BASE/api/v1/drive/AB12CD -H 'Content-Type: application/json' -d '{"speed_kmh":50,"turn_signal":"left"}'
curl -s $BASE/api/v1/drive/AB12CD
# {"speed_kmh":50.0,"turn_signal":"left","age_s":0.4}
```

## Kiểm thử và đánh giá

```bash
ruff check edge_agent/ backend/ tools/ tests/ && ruff format --check edge_agent/ backend/ tools/ tests/
pytest tests/                                            # hoặc: make test
cd frontend && npm run typecheck && npm test && npm run e2e
```

Logic theo thời gian (khối 7–12) được test bằng chuỗi số giả, không cần video. Đánh giá độ chính xác và
tốc độ:

| Gì | Kết quả | Chi tiết |
|---|---|---|
| CNN mắt nhắm (MRL Eye, 4000 ảnh) | Accuracy 99,4%, FPR 0,2% | [eval/results/report.md](eval/results/report.md) |
| Ngáp theo MAR (yawn-eye, test) | Accuracy 91,6%, precision 100% | [eval/results/report.md](eval/results/report.md) |
| Tốc độ vòng lặp chính (Mac ARM, CPU) | ~146 FPS, MediaPipe ~5,7 ms/frame | [eval/results/benchmark.md](eval/results/benchmark.md) |

Công cụ: `tools/eval.py` (video có nhãn theo thời gian), `tools/dataset.py` (dataset Kaggle),
`tools/seq_eval.py` (nhãn theo frame / clip), `tools/benchmark.py` (FPS). Cách chạy ở
[HowToUse.md mục 9](HowToUse.md#9-đánh-giá-và-benchmark).

## Cấu trúc thư mục

```
edge_agent/          14 khối on-device (camera → … → HUD server, metadata publisher), runtime chung, web bridge
backend/             FastAPI: auth, sự kiện, chuyến, báo cáo, ngưỡng, quản trị (SQLite)
frontend/            React: HUD, #/live (chạy trong trình duyệt), #/drive, dashboard; e2e Playwright
config/              thresholds.yaml (mọi ngưỡng), kịch bản CAN, drive_sim.yaml
tools/               tải model, mô phỏng lái xe, eval, dataset, benchmark, debug view
tests/               pytest cho edge agent, backend, tools
models/              model đã tải (không commit)
eval/results/        kết quả đánh giá và benchmark
deploy/, Dockerfile.railway, railway.json   bản deploy Railway (API + dashboard cùng origin)
packaging/edge/      gói cài và chạy edge agent trên máy trong xe
docs/                PRD, kiến trúc, roadmap, release notes, FMEA, nhật ký công việc
src/                 code mẫu của template khoá học (LangGraph), DriverGuard không dùng
```

Bảng khối ↔ file: [HowToUse.md mục 3.2](HowToUse.md#32-khối--file).

## Deliverables

| # | Deliverable | Ở đâu | Trạng thái |
|---|---|---|---|
| 1 | Source code | `edge_agent/`, `backend/`, `frontend/`, `tools/`, `config/` | ✅ |
| 2 | README | File này + [HowToUse.md](HowToUse.md) | ✅ |
| 3 | Architecture diagram | [docs/architecture_diagram.md](docs/architecture_diagram.md) | ✅ |
| 4 | AI logs | `.ai-log/`, gửi tự động lên server chấm khi `git push` | ✅ |
| 5 | Live URL | https://driveguard-v2-production.up.railway.app | ✅ |
| 6 | Video demo | `presentation/` | Chưa có |
| 7 | Pitch deck | `presentation/` | Chưa có |
| 8 | Development journal | [JOURNAL.md](JOURNAL.md), [docs/worklog/](docs/worklog/) | ✅ |
| 9 | Worklog | [WORKLOG.md](WORKLOG.md), [docs/roadmap.md](docs/roadmap.md) | ✅ |
| 10 | Evaluation evidence | [eval/results/](eval/results/) | ✅ |

Tài liệu khác: [docs/PRD.md](docs/PRD.md) (yêu cầu sản phẩm), [docs/release-v2.md](docs/release-v2.md)
(thêm / sửa / bỏ ở v2, giới hạn đã biết), [docs/safety-fmea.md](docs/safety-fmea.md) (những lúc hệ thống
không cảnh báo được), [docs/improvements.md](docs/improvements.md) (việc chưa làm),
[CLAUDE.md](CLAUDE.md) (ràng buộc và quy ước).

## Team

Team DriverGuard (4 người), AI20K Build Phase Cohort 4, VinUni:

| GitHub |
|---|
| [@DQQuan-VinAI](https://github.com/DQQuan-VinAI) |
| [@hddung-vinai](https://github.com/hddung-vinai) |
| [@Yuhnguyn](https://github.com/Yuhnguyn) |
| [@kelsingo](https://github.com/kelsingo) |

## AI usage logging

Yêu cầu của khoá học: prompt dùng AI được ghi vào `.ai-log/session.jsonl` và tự gửi lên server chấm ở
bước git pre-push. Cài một lần sau khi clone, rồi điền `AI_LOG_API_KEY` (tạo ở
[dashboard Phoenix](https://phoenix.note.transformerlabs.ai/api-keys)) vào `.env`:

```bash
bash scripts/setup_hooks.sh                                      # Linux / macOS / Git Bash
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1 # Windows PowerShell
```

| Công cụ | Cấu hình | Thời điểm ghi |
|---|---|---|
| Claude Code | `.claude/settings.json` | mỗi prompt (`UserPromptSubmit`) |
| Cursor | `.cursor/hooks.json` | mỗi prompt và khi dừng |
| OpenAI Codex CLI | `.codex/hooks.json` | mỗi prompt và khi dừng |
| Gemini CLI | `.gemini/settings.json` | mỗi lượt agent chạy |
| GitHub Copilot | `.github/hooks/hooks.json` | mỗi prompt và cuối session |
| Antigravity IDE | `.agents/hooks.json` | mỗi prompt, kèm lần quét lại lúc `git push` |

Dùng ChatGPT hay công cụ web khác thì ghi thủ công:

```bash
bash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "What you asked"
```

## Template khoá AI20K

Repo được sinh từ template chính thức của AI20K Build Phase. Những phần sau là của template, giữ lại theo
yêu cầu khoá học, DriverGuard không dùng:

- `src/` (LangGraph agent + FastAPI mẫu), `requirements-template.txt`; khi chưa cài, `tests/test_agents`
  và `tests/test_api` tự bỏ qua.
- `Dockerfile` / `docker-compose.yml` chạy app mẫu `src.main:app`. Bản deploy DriverGuard dùng
  `Dockerfile.railway`.
- Technical Guidebook 10 chương ở `docs/guide/` (bản online:
  <https://phoenix.note.transformerlabs.ai/technical-book>), khung `README_boilerplate.md`.

## Đóng góp và license

Đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi mở PR (Conventional Commits, chạy ruff + pytest). Mọi
thay đổi trong `docs/guide/` cần review của
[@AI20K-Build-Phase/book-maintainers](https://github.com/orgs/AI20K-Build-Phase/teams/book-maintainers).
Báo lỗ hổng bảo mật theo [SECURITY.md](SECURITY.md), đừng mở public issue.

[MIT](LICENSE): dùng tự do cho mục đích giáo dục.
