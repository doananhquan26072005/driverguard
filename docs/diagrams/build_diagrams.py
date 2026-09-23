#!/usr/bin/env python3
"""
DriverGuard — build 1 file .drawio 2 trang + export PNG.

Nguyên tắc: MỘT bảng toạ độ duy nhất cho mỗi trang. .drawio là nguồn duy nhất;
PNG được render TRỰC TIẾP từ .drawio bằng `drawio` CLI (không qua SVG trung gian)
=> PNG không thể lệch khỏi file editable.

Trang 1: UML Use Case
Trang 2: User Flow — luồng tài xế (cảnh báo)
"""

import xml.etree.ElementTree as ET

OUT = "driverguard_uml_userflow.drawio"

# ---------------------------------------------------------------------------
# Bảng style theo "kind"
# ---------------------------------------------------------------------------
STYLE = {
    "sys": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "ok": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "warn": "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;",
    "alert": "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;",
    "unavail": "rounded=1;whiteSpace=wrap;html=1;fillColor=#eeeeee;strokeColor=#999999;",
    "driver": "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;",
    "dec": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
    "term": "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;",
    "uc": "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "ucopt": "ellipse;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#999999;dashed=1;",
    "actor": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fontStyle=1;",
    "boundary": "rounded=0;whiteSpace=wrap;html=1;dashed=1;fillColor=none;"
    "verticalAlign=top;fontStyle=1;strokeColor=#666666;fontSize=15;",
    "note": "rounded=0;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#d6b656;"
    "dashed=1;align=left;verticalAlign=top;spacingLeft=8;spacingTop=6;fontSize=11;",
    "swatch": "rounded=0;whiteSpace=wrap;html=1;",
}

EDGE_ASSOC = "endArrow=none;html=1;rounded=0;"
EDGE_REL = "endArrow=open;dashed=1;html=1;rounded=0;"
EDGE_FLOW = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lab(s):
    """Doi \\n -> <br> TRUOC, roi escape -> &lt;br&gt;.

    mxGraph decode entity thanh chuoi '<br>' roi HTML renderer moi hieu ngat dong.
    Viet '<br>' tho vao attribute lam file .drawio KHONG well-formed XML.
    """
    return esc(s.replace("\n", "<br>"))


def vert(cid, x, y, w, h, label, kind, parent="1", extra=""):
    st = STYLE[kind] + extra
    return (
        f'<mxCell id="{cid}" value="{lab(label)}" style="{st}" vertex="1" parent="{parent}">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>'
    )


def edge(eid, s, d, label="", style=EDGE_FLOW, anchors=""):
    """anchors: chuoi exitX/exitY/entryX/entryY de EP huong ra-vao.

    Khong ep thi draw.io tu route, va voi cac canh dai (a2->b3) no hay chon
    duong ngang di ngang qua box khac -> trong sai luong.
    """
    return (
        f'<mxCell id="{eid}" value="{lab(label)}" style="{style}{anchors}" edge="1" parent="1" '
        f'source="{s}" target="{d}"><mxGeometry relative="1" as="geometry" /></mxCell>'
    )


def anchor(ex, ey, tx, ty):
    return f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={tx};entryY={ty};entryDx=0;entryDy=0;"


def page(name, pw, ph, cells):
    root = (
        '<mxGraphModel dx="1422" dy="798" grid="1" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0"><root>'
        '<mxCell id="0" /><mxCell id="1" parent="0" />'
    )
    return (
        f'<diagram id="{name.split()[0]}" name="{esc(name)}">\n'
        + root
        + "".join(cells)
        + "</root></mxGraphModel>\n</diagram>\n"
    )


# ===========================================================================
# TRANG 1 — UML USE CASE
# ===========================================================================
p1 = []
# --- actors
p1.append(vert("a1", 100, 140, 40, 70, "Tài xế", "actor"))
p1.append(vert("a3", 100, 640, 40, 70, "Người thử\n(demo)", "actor"))
p1.append(vert("a5", 100, 960, 40, 70, "Dev /\nVận hành", "actor"))
p1.append(vert("a4", 1150, 300, 40, 70, "Quản lý an toàn\n(fleet manager)", "actor"))
p1.append(vert("a2", 1150, 780, 40, 70, "Tổng đài\n(optional)", "actor"))
# --- system boundary
p1.append(vert("bd", 220, 60, 880, 1040, "DriverGuard", "boundary"))
# --- use cases, cột A (tài xế) | cột B (nội bộ) | cột C (quản lý)
UC = [
    # cột A
    ("uc01", 270, 90, "UC-01 Nhận cảnh báo trong xe\n(3 trạng thái)", "uc"),
    ("uc02", 270, 190, "UC-02 Cảnh báo buồn ngủ\n«extend» (FR-1.1)", "uc"),
    ("uc03", 270, 290, "UC-03 Cảnh báo mất tập trung\n«extend» (FR-1.2)", "uc"),
    ("uc04", 270, 390, "UC-04 Báo trạng thái unavailable\n«extend» (FR-6)", "uc"),
    ("uc17", 270, 580, "UC-17 Xem màn hình mô phỏng\ntrải nghiệm trong xe (FR-17)", "uc"),
    ("uc18", 270, 680, "UC-18 Ép trạng thái để demo\n6 case (FR-17)", "uc"),
    ("uc19", 270, 780, "UC-19 Ghi phản hồi ngắn\n(chấp nhận)", "uc"),
    ("uc20", 270, 960, "UC-20 Vận hành: local/Docker\n+ replay / live (FR-14, FR-15)", "uc"),
    # cột B
    ("uc05", 570, 140, "UC-05 Phát hiện dấu hiệu\ntừ RGB «include» (FR-4)", "uc"),
    ("uc06", 570, 290, "UC-06 Lọc chống cảnh báo sai\n(FR-2, FR-5) «include»", "uc"),
    ("uc07", 570, 440, "UC-07 Kiểm tra xe đang chạy\n(CAN-sim) «include» (FR-3)", "uc"),
    ("uc08", 570, 590, "UC-08 Ghi nhật ký sự kiện\n«include» (FR-8)", "uc"),
    # cột C
    ("uc09", 870, 90, "UC-09 Giám sát live (FR-7)", "uc"),
    ("uc10", 870, 190, "UC-10 Xem nhật ký sự kiện (FR-8)", "uc"),
    ("uc11", 870, 290, "UC-11 Xem báo cáo và bảng\ntheo điều kiện (FR-9)", "uc"),
    ("uc12", 870, 390, "UC-12 Xem tóm tắt hành vi\nlái xe — LLM (FR-12)", "uc"),
    ("uc13", 870, 490, "UC-13 Xem gợi ý an toàn\ncá nhân hoá — LLM (FR-13)", "uc"),
    ("uc14", 870, 590, "UC-14 Quản lý vai trò\ndriver / safety (FR-10)", "uc"),
    ("uc15", 870, 690, "UC-15 Chỉnh ngưỡng theo đội\n(version + reset) (FR-11)", "ucopt"),
    ("uc16", 870, 790, "UC-16 Ghi nhận sự kiện mất\ntập trung (Happy Path)", "ucopt"),
]
for cid, x, y, t, k in UC:
    p1.append(vert(cid, x, y, 200, 80, t, k))

# --- associations
for uc in ("uc01", "uc02", "uc03", "uc04"):
    p1.append(edge("as_a1_" + uc, "a1", uc, "", EDGE_ASSOC))
for uc in ("uc17", "uc18", "uc19"):
    p1.append(edge("as_a3_" + uc, "a3", uc, "", EDGE_ASSOC))
p1.append(edge("as_a5_uc20", "a5", "uc20", "", EDGE_ASSOC))
for uc in ("uc09", "uc10", "uc11", "uc12", "uc13", "uc14", "uc15"):
    p1.append(edge("as_a4_" + uc, "a4", uc, "", EDGE_ASSOC))
p1.append(edge("as_a2_uc16", "a2", "uc16", "", EDGE_ASSOC))
# --- include / extend
for uc in ("uc05", "uc06", "uc07", "uc08"):
    p1.append(edge("inc_" + uc, "uc01", uc, "«include»", EDGE_REL))
for uc in ("uc02", "uc03", "uc04"):
    p1.append(edge("ext_" + uc, uc, "uc01", "«extend»", EDGE_REL))
# --- note
p1.append(
    vert(
        "note1",
        220,
        1130,
        880,
        95,
        "«include» = luôn xảy ra trong luồng  ·  «extend» = chỉ xảy ra khi thoả điều kiện (tuỳ chọn)\n"
        "UC-15 và UC-16 là optional. FR-19 (cá nhân hoá ngưỡng theo tài xế) và FR-20 (fleet + OTA mock)\n"
        "là tính năng lâu dài — không vẽ trong sơ đồ này. Mọi UC trace về PRD DriverGuard v2.2 §4.",
        "note",
    )
)

# ===========================================================================
# TRANG 2 — USER FLOW: LUỒNG TÀI XẾ
# ===========================================================================
p2 = []
N = [
    ("start", 460, 70, 320, 70, "Bắt đầu phiên chạy\n(replay video mẫu / live webcam) (FR-15)", "term"),
    ("b1", 460, 190, 320, 80, "Trích xuất tín hiệu RGB: mắt, miệng, head pose (FR-4)", "sys"),
    ("d1", 460, 310, 320, 120, "Có mặt và chất lượng ảnh đủ tốt?\n(FR-6)", "dec"),
    ("o1", 880, 310, 300, 90, "KHÔNG QUAN SÁT ĐƯỢC (xám)\n— không cảnh báo (FR-6)\n→ chờ vòng kế tiếp", "unavail"),
    ("b2", 460, 480, 320, 80, "Làm mượt theo thời gian\n+ hợp nhất đa tín hiệu (FR-5)", "sys"),
    ("d2", 460, 610, 320, 120, "Xe đang chạy? (CAN-sim &gt; 0)\n(FR-3)", "dec"),
    ("o2", 880, 610, 300, 90, "BÌNH THƯỜNG (xe dừng)\n— không cảnh báo (FR-3)\n→ chờ vòng kế tiếp", "ok"),
    ("d3", 460, 780, 320, 120, "Buồn ngủ kéo dài ≥ ngưỡng\n(~1,5–2,5s)? (FR-5)", "dec"),
    ("d4", 880, 780, 300, 120, "Mất tập trung kéo dài\n≥ ngưỡng? (FR-5)", "dec"),
    ("o3", 1240, 780, 300, 90, "BÌNH THƯỜNG\n— không có dấu hiệu (FR-1)\n→ chờ vòng kế tiếp", "ok"),
    (
        "a1",
        460,
        950,
        320,
        110,
        "CẢNH BÁO BUỒN NGỦ (đỏ)\n“Bạn đang có dấu hiệu buồn ngủ.\nVui lòng dừng xe.” (FR-1.1)",
        "alert",
    ),
    ("a2", 880, 950, 300, 110, "CẢNH BÁO MẤT TẬP TRUNG (cam)\n“Vui lòng tập trung nhìn đường”\n(FR-1.2)", "warn"),
    (
        "b3",
        460,
        1110,
        320,
        90,
        "Ghi nhật ký sự kiện: thời gian, trạng thái, dấu hiệu,\nđiều kiện, phiên bản config, tag simulated/true (FR-8)",
        "sys",
    ),
    ("b4", 460, 1230, 320, 70, "Áp dụng cooldown 10s\n(không hú liên tục) (FR-2)", "sys"),
    ("u1", 460, 1350, 320, 80, "Tài xế: dừng xe / tìm cách tỉnh ngủ\n(Happy Path)", "driver"),
    ("d5", 460, 1490, 320, 120, "Dấu hiệu còn tiếp diễn?", "dec"),
    ("lo1", 80, 1490, 300, 90, "GIỮ nguyên cảnh báo\n(trong cooldown: không hú lại) (FR-2)", "sys"),
    ("o4", 880, 1490, 300, 90, "TẮT cảnh báo → về BÌNH THƯỜNG\n(FR-1.1 / FR-1.2)", "ok"),
    ("end", 460, 1660, 320, 70, "Chờ frame tiếp theo\n(lặp lại từ bước 1)", "term"),
]
for cid, x, y, w, h, t, k in N:
    p2.append(vert(cid, x, y, w, h, t, k))

FLOW = [
    ("start", "b1", "", anchor(0.5, 1, 0.5, 0)),
    ("b1", "d1", "", anchor(0.5, 1, 0.5, 0)),
    ("d1", "b2", "Có", anchor(0.5, 1, 0.5, 0)),
    ("d1", "o1", "Không", anchor(1, 0.5, 0, 0.5)),
    ("b2", "d2", "", anchor(0.5, 1, 0.5, 0)),
    ("d2", "d3", "Có", anchor(0.5, 1, 0.5, 0)),
    ("d2", "o2", "Không", anchor(1, 0.5, 0, 0.5)),
    ("d3", "a1", "Có", anchor(0.5, 1, 0.5, 0)),
    ("d3", "d4", "Không", anchor(1, 0.5, 0, 0.5)),
    ("d4", "a2", "Có", anchor(0.5, 1, 0.5, 0)),
    ("d4", "o3", "Không", anchor(1, 0.5, 0, 0.5)),
    ("a1", "b3", "", anchor(0.5, 1, 0.5, 0)),
    # a2 nam BEN PHAI b3: phai ep ra day a2 roi vao canh phai b3, khong de router
    # chon duong ngang ngang qua a1 (tung bi loi: trong nhu a2 -> a1).
    ("a2", "b3", "", anchor(0.5, 1, 1, 0.5)),
    ("b3", "b4", "", anchor(0.5, 1, 0.5, 0)),
    ("b4", "u1", "", anchor(0.5, 1, 0.5, 0)),
    ("u1", "d5", "", anchor(0.5, 1, 0.5, 0)),
    ("d5", "lo1", "Có", anchor(0, 0.5, 1, 0.5)),
    ("d5", "o4", "Không", anchor(1, 0.5, 0, 0.5)),
    # lo1 -> b2: vong dai nguoc len, ep di theo hanh lang ben trai (x~230)
    ("lo1", "b2", "tiếp tục giám sát", anchor(0.5, 0, 0, 0.5)),
    ("o4", "end", "", anchor(0.5, 1, 1, 0.5)),
]
for i, (s, d, label, a) in enumerate(FLOW):
    p2.append(edge(f"f{i}_{s}_{d}", s, d, label, anchors=a))

# --- legend
LEG = [
    ("BÌNH THƯỜNG", "ok"),
    ("CẢNH BÁO BUỒN NGỦ", "alert"),
    ("CẢNH BÁO MẤT TẬP TRUNG", "warn"),
    ("KHÔNG QUAN SÁT ĐƯỢC", "unavail"),
]
p2.append(vert("legbox", 1240, 1100, 300, 230, "CHÚ THÍCH MÀU TRẠNG THÁI", "note"))
for i, (t, k) in enumerate(LEG):
    y = 1140 + i * 42
    p2.append(vert(f"lgs{i}", 1256, y, 34, 22, "", "swatch", extra=STYLE[k].replace("rounded=1;", "")))
    p2.append(
        vert(
            f"lgt{i}",
            1300,
            y - 5,
            226,
            32,
            t,
            "swatch",
            extra="fillColor=none;strokeColor=none;align=left;fontSize=12;",
        )
    )
p2.append(
    vert(
        "note2",
        80,
        1655,
        370,
        175,
        "Sơ đồ mô tả MỘT vòng xử lý\n(mỗi frame / mỗi cửa sổ ~100 ms).\n"
        "Mọi nhánh kết thúc đều chờ vòng kế tiếp.\n"
        "Ngoặc đơn = mã FR trong PRD v2.2.\n"
        "Số liệu chỉ sinh từ pipeline thật chạy\n"
        "ở chế độ replay; trạng thái ép tay chỉ\n"
        "dùng để demo 6 case.",
        "note",
    )
)

# ===========================================================================
out = (
    '<mxfile host="app.diagrams.net" agent="Hermes" type="device">\n'
    + page("1. UML Use Case", 1300, 1270, p1)
    + page("2. User Flow - Tai xe", 1620, 1860, p2)
    + "</mxfile>\n"
)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(out)

# --- kiểm tra cấu trúc
r = ET.parse(OUT).getroot()
for d in r.findall("diagram"):
    cells = d.findall(".//mxCell")
    ids = [c.get("id") for c in cells]
    dupes = {i for i in ids if ids.count(i) > 1} - {"0", "1"}
    dangling = [
        (c.get("id"), c.get("source"), c.get("target"))
        for c in cells
        if c.get("edge") == "1" and (c.get("source") not in ids or c.get("target") not in ids)
    ]
    print(f"{d.get('name')}: {len(cells)} cells | dupes={dupes or 'none'} | dangling={dangling or 'none'}")
print("OK ->", OUT)
