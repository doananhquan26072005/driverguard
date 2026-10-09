#!/usr/bin/env python3
"""
DriverGuard: build the system architecture overview (architecture.svg + png/architecture.png).

This script is the single source of the figure: every box and arrow is a row in the tables below.
Edit the tables and run it again; do not edit the SVG by hand.

    python3 build_architecture.py            # writes architecture.svg, then the PNG if Chrome is found

The PNG is a headless-Chrome screenshot of the SVG, so the two cannot drift apart.
"""

from __future__ import annotations

import subprocess
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
SVG_OUT = HERE / "architecture.svg"
PNG_OUT = HERE / "png" / "architecture.png"
CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

W, H = 1600, 1000
FONT = "-apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

# kind -> (fill, stroke)
COLORS = {
    "frontend": ("#eaf2fd", "#3b73c4"),
    "agent": ("#e9f6ec", "#3d8b55"),
    "backend": ("#fff3e0", "#c77f1a"),
    "db": ("#f1eafa", "#7a55b0"),
    "external": ("#f3f4f6", "#6b7280"),
    "inner": ("#ffffff", None),  # stroke comes from the parent container
    "note": ("#fffbe6", "#b59a2b"),
}
TEXT = "#1f2933"
MUTED = "#52606d"
ARROW = "#374151"

# ---------------------------------------------------------------------------
# Containers: (kind, x, y, w, h, title, [subtitle lines], header anchor)
#   The agent header is right-aligned so the #/hud arrow does not run through it.
# ---------------------------------------------------------------------------
CONTAINERS = [
    ("frontend", 40, 84, 1520, 172, "Frontend · React 19 + Vite + Tailwind v4",
     ["Một bundle, bốn trang theo hash route; trình duyệt tải từ cùng origin với Backend"], "start"),
    ("agent", 40, 400, 640, 335, "Agent · edge_agent (Python, 14 khối)",
     ["Chạy trên thiết bị trong xe · frame chỉ nằm trong RAM · model pretrained + luật, không có LLM"], "end"),
    ("backend", 880, 400, 680, 335, "Backend API · FastAPI",
     ["Railway, một container · không chạy model nào · chỉ nhận JSON metadata"], "start"),
    ("external", 40, 800, 640, 130, "External · nguồn model pretrained",
     ["Chỉ dùng lúc cài đặt / build image; lúc chạy hệ thống không gọi API bên ngoài nào"], "start"),
]

# ---------------------------------------------------------------------------
# Inner boxes: (parent kind, x, y, w, h, title, [lines])
# ---------------------------------------------------------------------------
BOXES = [
    # Frontend pages
    ("frontend", 70, 152, 320, 88, "#/hud · màn hình trong xe",
     ["Mức L0–L3, lý do, âm báo", "Đăng ký tài xế, kết thúc chuyến"]),
    ("frontend", 420, 152, 580, 88, "#/live · cả agent chạy trong trình duyệt",
     ["Khối 1–5: getUserMedia, MediaPipe Tasks JS, onnxruntime-web (cùng 2 file model)",
      "Khối 6–12: cùng code Python của thiết bị, chạy bằng Pyodide · HUD ngay trong trang"]),
    ("frontend", 1030, 152, 240, 88, "#/drive · điều khiển xe",
     ["Tốc độ, xi nhan (thay CAN thật)", "Ghép với #/live bằng mã"]),
    ("frontend", 1300, 152, 230, 88, "#/dashboard",
     ["Tài xế · quản lý · kỹ sư · admin", "Sự kiện, báo cáo chuyến, ngưỡng"]),
    # Agent: outputs on the first row, the pipeline on the second
    ("agent", 60, 462, 250, 74, "13 HUD server",
     ["HTTP cục bộ 127.0.0.1:8765"]),
    ("agent", 420, 462, 240, 74, "14 Metadata publisher",
     ["Outbox SQLite · lô ≤ 20 · chặn ảnh"]),
    ("agent", 60, 596, 184, 122, "Nhận diện · khối 1–6",
     ["1 Camera → 2 Tiền xử lý", "3 MediaPipe · 4 YOLOv8n", "6 Đặc trưng EAR/MAR/pose",
      "5 CNN mắt khi EAR kém"]),
    ("agent", 268, 596, 184, 122, "Phân tích · khối 7–8",
     ["7 Buồn ngủ: PERCLOS,", "microsleep, ngáp, gật", "8 Mất tập trung:",
      "nhìn lệch, điện thoại"]),
    ("agent", 476, 596, 184, 122, "Quyết định · khối 9–12",
     ["9 Risk engine L0–L3", "10 Ngữ cảnh xe (tốc độ)", "11 Trip memory",
      "12 Alert manager"]),
    # Backend: six route groups and the static files
    ("backend", 900, 462, 206, 74, "Đăng nhập",
     ["/auth/login · refresh · me", "JWT theo vai trò"]),
    ("backend", 1117, 462, 206, 74, "Nhận sự kiện",
     ["/events · /web/events", "Có ảnh / base64 → 422"]),
    ("backend", 1334, 462, 206, 74, "Ngưỡng",
     ["/thresholds · versions · rollout", "/device/thresholds"]),
    ("backend", 900, 548, 206, 74, "Chuyến và báo cáo",
     ["/trips · /trip-reports · /fleet", "/timeline · /stats"]),
    ("backend", 1117, 548, 206, 74, "Relay tín hiệu xe",
     ["/drive/{code}", "Chỉ giữ trong RAM"]),
    ("backend", 1334, 548, 206, 74, "Quyền dữ liệu",
     ["/policy · /me/data · access-log", "/deletion-requests"]),
    ("backend", 900, 634, 640, 84, "File tĩnh (cùng origin)",
     ["Bundle React · edge_agent.zip · face_landmarker.task · yolov8n.onnx",
      "Pyodide · MediaPipe wasm (không tải từ CDN)"]),
    # External model sources
    ("external", 60, 862, 196, 54, "Google MediaPipe",
     ["face_landmarker.task"]),
    ("external", 268, 862, 196, 54, "Intel Open Model Zoo",
     ["open-closed-eye-0001"]),
    ("external", 476, 862, 184, 54, "Ultralytics",
     ["yolov8n.pt → ONNX"]),
]

# ---------------------------------------------------------------------------
# Arrows: (points, style, heads, [(x, y, anchor, text)])
#   style: "bold" = metadata leaving the device, "solid" = request / response, "dashed" = occasional
#   heads: "end" | "both"
# ---------------------------------------------------------------------------
ARROWS = [
    # #/hud <-> block 13
    ([(120, 240), (120, 462)], "solid", "both",
     [(134, 318, "start", "↓ trạng thái: GET /state mỗi 0,3 s"),
      (134, 338, "start", "↑ POST /feedback · /vehicle · /end-trip")]),
    # #/live <-> backend
    ([(940, 240), (940, 400)], "bold", "both",
     [(926, 300, "end", "↓ POST /api/v1/web/events"),
      (926, 320, "end", "chỉ JSON metadata · JWT"),
      (926, 348, "end", "↑ ngưỡng, tốc độ theo mã ghép")]),
    # #/drive -> backend
    ([(1150, 240), (1150, 400)], "solid", "end",
     [(1164, 318, "start", "PUT /api/v1/drive/{code}"),
      (1164, 338, "start", "chỉ số: tốc độ, xi nhan")]),
    # #/dashboard <-> backend
    ([(1415, 240), (1415, 400)], "solid", "both",
     [(1429, 318, "start", "REST + JWT"),
      (1429, 338, "start", "đọc và chỉnh")]),
    # pipeline
    ([(244, 657), (268, 657)], "solid", "end", []),
    ([(452, 657), (476, 657)], "solid", "end", []),
    ([(600, 596), (600, 536)], "solid", "end", []),
    ([(520, 596), (520, 566), (185, 566), (185, 536)], "solid", "end",
     [(352, 559, "middle", "mức + lý do")]),
    # block 14 -> backend
    ([(660, 499), (880, 499)], "bold", "end",
     [(770, 470, "middle", "POST /api/v1/events"),
      (770, 488, "middle", "chỉ JSON metadata"),
      (770, 519, "middle", "X-Device-Key · mỗi 5 s")]),
    # backend -> risk engine thresholds
    ([(880, 676), (660, 676)], "dashed", "end",
     [(770, 648, "middle", "ngưỡng đã chỉnh"),
      (770, 666, "middle", "GET …/device/thresholds"),
      (770, 696, "middle", "khởi động + mỗi 5 phút")]),
    # backend <-> database
    ([(1100, 735), (1100, 800)], "solid", "both",
     [(1114, 773, "start", "SQL")]),
    # model sources -> perception
    ([(152, 800), (152, 718)], "dashed", "end",
     [(166, 774, "start", "tools/download_models.py (một lần lúc cài đặt)")]),
]

DB = (900, 800, 400, 130, "SQLite · volume /app/data",
      ["users · devices · device_status · events",
       "fatigue_samples · trip_summaries · threshold_*",
       "deletion_requests · access_log"])

NOTE = (1330, 800, 230, 130, "Không có trong hệ thống",
        ["LLM, LangGraph, Vector Store.", "“Agent” ở đây là pipeline thị giác",
         "+ luật chạy on-device; dữ liệu", "là bảng quan hệ, không RAG."])

LEGEND_Y = 968


def text(x, y, s, size=12, weight=400, fill=TEXT, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


def container(kind, x, y, w, h, title, sub, anchor):
    fill, stroke = COLORS[kind]
    tx = x + 18 if anchor == "start" else x + w - 18
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" '
           f'stroke-width="2"/>',
           text(tx, y + 26, title, 16, 700, stroke, anchor)]
    out += [text(tx, y + 45 + 16 * i, line, 12, 400, MUTED, anchor) for i, line in enumerate(sub)]
    return out


def box(kind, x, y, w, h, title, lines):
    stroke = COLORS[kind][1]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{COLORS["inner"][0]}" '
           f'stroke="{stroke}" stroke-width="1.2"/>',
           text(x + w / 2, y + 22, title, 13, 700, TEXT, "middle")]
    out += [text(x + w / 2, y + 42 + 18 * i, line, 12, 400, MUTED, "middle") for i, line in enumerate(lines)]
    return out


def arrow(points, style, heads, labels):
    width = 3.2 if style == "bold" else 1.6
    dash = ' stroke-dasharray="6 5"' if style == "dashed" else ""
    start = ' marker-start="url(#head)"' if heads == "both" else ""
    pts = " ".join(f"{x},{y}" for x, y in points)
    out = [f'<polyline points="{pts}" fill="none" stroke="{ARROW}" stroke-width="{width}"{dash}{start} '
           f'marker-end="url(#head)" stroke-linejoin="round"/>']
    out += [text(x, y, s, 12, 600 if style == "bold" else 500, TEXT, anchor) for x, y, anchor, s in labels]
    return out


def cylinder(x, y, w, h, title, lines):
    fill, stroke = COLORS["db"]
    ry = 13
    out = [f'<path d="M{x},{y + ry} v{h - 2 * ry} a{w / 2},{ry} 0 0 0 {w},0 v{-(h - 2 * ry)}" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="2"/>',
           f'<ellipse cx="{x + w / 2}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" fill="{fill}" stroke="{stroke}" '
           f'stroke-width="2"/>',
           text(x + w / 2, y + 50, title, 15, 700, stroke, "middle")]
    out += [text(x + w / 2, y + 70 + 17 * i, line, 12, 400, MUTED, "middle") for i, line in enumerate(lines)]
    return out


def note(x, y, w, h, title, lines):
    fill, stroke = COLORS["note"]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" '
           f'stroke-width="1.2" stroke-dasharray="5 4"/>',
           text(x + 14, y + 24, title, 13, 700, TEXT)]
    out += [text(x + 14, y + 46 + 18 * i, line, 12, 400, MUTED) for i, line in enumerate(lines)]
    return out


def legend(y):
    out = []
    for x, style, label in [
        (40, "bold", "metadata JSON rời thiết bị / trang (không bao giờ có ảnh)"),
        (500, "solid", "gọi HTTP thường xuyên"),
        (760, "dashed", "thỉnh thoảng: cài đặt, khởi động, 5 phút một lần"),
    ]:
        out += arrow([(x, y), (x + 56, y)], style, "end", [(x + 68, y + 4, "start", label)])
    return out


def build_svg() -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="{FONT}" role="img" aria-labelledby="t d">',
        '<title id="t">Kiến trúc hệ thống DriverGuard</title>',
        '<desc id="d">Frontend React, edge agent 14 khối chạy trên thiết bị, Backend FastAPI, SQLite và nguồn '
        'model pretrained, cùng các luồng dữ liệu giữa chúng.</desc>',
        '<defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 z" fill="{ARROW}"/>'
        '</marker></defs>',
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
        text(40, 44, "DriverGuard · kiến trúc hệ thống", 24, 700),
        text(40, 66, "Giám sát tài xế on-device: ảnh khuôn mặt không rời thiết bị, backend chỉ nhận JSON metadata",
             13, 400, MUTED),
    ]
    for c in CONTAINERS:
        parts += container(*c)
    for b in BOXES:
        parts += box(*b)
    parts += cylinder(*DB)
    parts += note(*NOTE)
    for a in ARROWS:
        parts += arrow(*a)
    parts += legend(LEGEND_Y)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_png() -> bool:
    chrome = next((c for c in CHROME if Path(c).exists()), None)
    if chrome is None:
        return False
    PNG_OUT.parent.mkdir(exist_ok=True)
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
         f"--window-size={W},{H}", f"--screenshot={PNG_OUT}", SVG_OUT.as_uri()],
        check=True, capture_output=True, timeout=120,
    )
    return True


def main() -> int:
    SVG_OUT.write_text(build_svg(), encoding="utf-8")
    print(f"wrote {SVG_OUT.name}: {len(CONTAINERS)} containers, {len(BOXES)} boxes, {len(ARROWS)} arrows")
    if render_png():
        print(f"wrote png/{PNG_OUT.name}")
    else:
        print("Chrome not found: PNG not rendered", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
