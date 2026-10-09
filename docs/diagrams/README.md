# DriverGuard — Sơ đồ UML & User Flow

Hai sơ đồ BA cho DriverGuard, dựng từ [PRD v2.2](../PRD.md).

| Trang | Sơ đồ | PNG |
|---|---|---|
| 1 | UML Use Case (5 actor, UC-01…UC-20, «include»/«extend») | [`png/page1_uml.png`](png/page1_uml.png) |
| 2 | User Flow — luồng tài xế (cảnh báo, `unavailable`, cooldown) | [`png/page2_userflow.png`](png/page2_userflow.png) |

Toàn bộ sơ đồ nằm trong **một file** `driverguard_uml_userflow.drawio` (2 trang).

## Sơ đồ kiến trúc hệ thống

[`architecture.svg`](architecture.svg) (PNG: [`png/architecture.png`](png/architecture.png)) là hình tổng quan
Frontend / Agent / Backend API / Database / External, embed trong [README](../../README.md#kiến-trúc) và
[`architecture_diagram.md`](../architecture_diagram.md#0-tổng-quan-hệ-thống). Khác hai sơ đồ BA ở trên, hình này vẽ theo
**code** chứ không theo PRD.

```bash
python3 build_architecture.py     # ghi architecture.svg, rồi chụp PNG bằng Chrome headless (không cần draw.io)
```

`build_architecture.py` là nguồn duy nhất: mỗi khung, hộp, mũi tên là một dòng trong bảng. Sau khi sửa phải mở PNG
ra soi (chữ tràn hộp, mũi tên đè chữ).

## Mở và sửa

```bash
open -a draw.io driverguard_uml_userflow.drawio     # draw.io Desktop (đã cài)
```

Hoặc web: **app.diagrams.net** → `File → Open From → Device` → chọn file (không cần account, chọn *Device* khi được hỏi).

macOS đã có app liên kết với `.drawio` (`kMDItemContentType = com.jgraph.drawio`), nên double-click cũng mở được.

## Dựng lại PNG sau khi sửa

```bash
python3 build_diagrams.py
mkdir -p png
drawio -x -f png -s 2 --size diagram --page-index 1 -o png/page1_uml.png driverguard_uml_userflow.drawio
drawio -x -f png -s 2 --size diagram --page-index 2 -o png/page2_userflow.png driverguard_uml_userflow.drawio
```

> ⚠️ `--page-index` **đếm từ 1** ở draw.io ≥ v27 (nhưng lỗi báo lại ghi "0-based"). Truyền `0` sẽ ra `Invalid page index`.

Xuất SVG (nét, dùng cho báo cáo/DOCX): đổi `-f png` → `-f svg`.

## Nguồn duy nhất (single source of truth)

`build_diagrams.py` là **nguồn duy nhất** của hình học: mỗi node là một tuple
`(id, x, y, w, h, label, kind)` trong một bảng, và script sinh ra file `.drawio`.
Sửa chữ/di chuyển box thì sửa script rồi chạy lại — **đừng** chỉnh tay trong
draw.io rồi quên script, hai bản sẽ lệch nhau.

Script in ra kiểm tra cấu trúc sau mỗi lần chạy (số cell, id trùng, cạnh treo):

```
1. UML Use Case: 52 cells | dupes=none | dangling=none
2. User Flow - Tai xe: 51 cells | dupes=none | dangling=none
```

## Bẫy đã gặp (đừng vấp lại)

1. **`<br>` viết thô trong attribute `value` làm `.drawio` không phải XML hợp lệ.**
   Phải escape thành `&lt;br&gt;` — mxGraph decode entity thành `<br>` rồi HTML
   renderer mới hiểu ngắt dòng. Trong script: đổi `\n` → `<br>` **trước**, rồi mới escape.
2. **Không để draw.io tự route các cạnh dài.** Cạnh `a2 → b3` từng bị router chọn
   đường ngang đi qua box khác, trông như mũi tên sai luồng. Ép `exitX/exitY/entryX/entryY`
   cho mọi cạnh dài (hàm `anchor()` trong script).
3. **Toạ độ con của container là tương đối** so với container — ở đây không dùng swimlane nên
   không bị, nhưng nếu thêm thì phải trừ gốc container.
4. **Sau khi sửa, phải render rồi soi PNG.** Kiểm tra XML hợp lệ không đủ để biết layout đúng.

## Ràng buộc nội dung (đồng bộ với PRD v2.2)

- Sơ đồ chỉ mô tả **luồng và trạng thái**; **không** mang số liệu.
- Nhãn ghi mã FR để trace về PRD. Trạng thái ép tay (nút demo, FR-17) chỉ để demo
  6 case, **không** sinh số — xem khối "HARD RULE" trong PRD §4.5.
- Chưa vẽ: User Flow cho quản lý an toàn (dashboard/nhật ký/báo cáo), Activity diagram
  và Sequence diagram.
