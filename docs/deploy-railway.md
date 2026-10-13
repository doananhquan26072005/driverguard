# Deploy DriverGuard lên Railway (M66)

Railway chạy **một** image: [`Dockerfile.railway`](../Dockerfile.railway). Image này gồm backend FastAPI, dashboard,
HUD và các file cho `#/live`. Server không chạy model nào: trình duyệt tải model rồi tự chạy. Hai Dockerfile còn lại
không dùng trên Railway: `Dockerfile.edge` chỉ để đo thử kiểu Jetson (M42), còn `Dockerfile` là app mẫu của khoá học.

**Địa chỉ đang chạy:** https://c4-app-135.up.railway.app (service `driveguard`, project `driveguard`; deploy tay 13/10/2026). Các domain trong `release-v1.md` – `release-v3.md` là của các bản cũ.

## Luồng tự động

```
push / merge vào main → CI: python, frontend, e2e
                       → cả ba pass → job deploy: tải model từ release models-v1 → railway up
```

- Push lên nhánh khác (ví dụ `dungx`) không deploy. Muốn lên production thì tạo PR vào `main`.
- Có test fail thì không deploy. Bản đang chạy giữ nguyên.
- Railway chỉ chuyển sang bản mới khi `GET /health` trả 200 (xem [`railway.json`](../railway.json)).

## Cấu hình một lần

### 1. Model lên GitHub Release

Hai model pretrained không nằm trong git (`.gitignore`). Chạy từ máy có sẵn model
(`python tools/download_models.py`):

```bash
gh release create models-v1 models/face_landmarker.task models/yolov8n.onnx \
  --title "Pretrained models" --notes "Pretrained models served to #/live (not trained by this project)"
```

Đổi model thì tạo release mới (`models-v2`) và sửa tên release trong job `deploy` của
[`ci.yml`](../.github/workflows/ci.yml).

### 2. Railway

1. Tạo project và một service trống (hoặc dùng lại service đang có).
2. **Volume** mount vào `/app/data`. Database SQLite nằm ở đây. Không có volume thì mỗi lần deploy sẽ mất dữ liệu.
3. **Variables**:
   - `DG_JWT_SECRET`: chuỗi ngẫu nhiên, tạo bằng `python -c "import secrets;print(secrets.token_hex(32))"`.
     Không đặt thì đăng nhập sẽ mất mỗi lần restart.
   - Tuỳ chọn: `DG_RETENTION_EVENTS_DAYS=0`, `DG_RETENTION_SUMMARIES_DAYS=0` nếu chưa muốn tự xoá dữ liệu cũ (M37).
4. **Settings → Networking → Generate Domain**.
5. **Project Settings → Tokens**: tạo Project Token cho đúng environment (thường là `production`).
6. **Không** kết nối GitHub repo để Railway tự deploy. CI đã deploy rồi, kết nối thêm sẽ deploy hai lần, và
   bản build từ GitHub sẽ lỗi vì thiếu model.

### 3. GitHub (repo → Settings → Secrets and variables → Actions)

- Secret `RAILWAY_TOKEN`: Project Token ở bước 2.5.
- Variable `RAILWAY_SERVICE`: tên service trên Railway.

Thiếu một trong hai thì job `deploy` dừng ở bước "Check deploy settings" và báo đúng cái còn thiếu.

## Deploy tay

```bash
railway link                     # chọn project, environment, service
railway up --no-gitignore        # cần --no-gitignore để gửi model
```

`--no-gitignore` là bắt buộc: `railway up` mặc định bỏ qua những gì trong `.gitignore`, trong đó có model.
Vì vậy [`.railwayignore`](../.railwayignore) tự liệt kê mọi thứ không được gửi đi: `.env`, database, log, `data/`,
`.ai-log/`, `node_modules`... Thêm loại file bí mật mới vào `.gitignore` thì phải thêm cả vào `.railwayignore`.

## Tài khoản dùng thử (một lần cho mỗi database)

Trang đầu (`#/live`) điền sẵn tài khoản tài xế `taixe_demo` / `demo12345` (`frontend/src/lib/demo.ts`; đổi bằng
`VITE_DEMO_USERNAME` / `VITE_DEMO_PASSWORD` lúc build, `VITE_DEMO_USERNAME=""` để tắt), nên tài khoản này phải có
trong database của Railway. Database nằm trên volume `/app/data`: tạo một lần, các lần deploy sau vẫn còn.

```bash
railway ssh --service driveguard
python -m backend.manage create-user taixe_demo --role driver --driver-id drv-demo   # hỏi mật khẩu: demo12345
python -m backend.manage create-user kysu_demo --role engineer                       # mật khẩu riêng, không hiện trên trang
exit
```

Ai mở trang cũng thấy mật khẩu của `taixe_demo`: tài khoản này chỉ xem được chuyến của chính nó. Không điền sẵn
tài khoản kỹ sư hay quản lý.

## Kiểm tra sau khi deploy

- `https://<domain>/health` trả 200.
- Đăng nhập được với các vai trò. `#/live` tải xong và chạy camera.
- File tĩnh có `Content-Encoding: gzip` và `Cache-Control` (M45, chưa kiểm trên Railway):
  `curl -sI -H "Accept-Encoding: gzip" https://<domain>/models/yolov8n.onnx`
- RAM trong Metrics của Railway: trên máy dev backend dùng khoảng 60 MB.

## Quay lui

Railway → service → **Deployments** → chọn bản cũ → **Redeploy**. Database trên volume không bị ảnh hưởng.
Trước khi deploy đè lên service có dữ liệu thật, nên tải bản sao `/app/data/driverguard.db`, vì bản mới có thể
thêm bảng và tự xoá dữ liệu quá hạn ngay lúc khởi động (M37).
