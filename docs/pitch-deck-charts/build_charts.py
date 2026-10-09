"""Build the PNG charts of docs/pitch-deck-so-lieu.md (16:9, for slides).

Every number is typed here with the report it comes from: this script reads no
result file, so re-check the tables below when eval/results/ is regenerated.

    .venv/bin/python docs/pitch-deck-charts/build_charts.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

OUT = Path(__file__).parent

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
BLUE_LIGHT = "#9ec5f4"
ORANGE = "#eb6834"
GOOD = "#0ca30c"
WARNING = "#fab219"
CRITICAL = "#d03b3b"

plt.rcParams.update(
    {
        "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": AXIS,
        "xtick.color": MUTED,
        "ytick.color": INK_2,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
    }
)


def new_figure(title: str, subtitle: str, source: str, left: float = 0.30):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)
    fig.subplots_adjust(left=left, right=0.94, top=0.78, bottom=0.17)
    fig.text(0.04, 0.93, title, fontsize=14, fontweight="bold", va="center")
    fig.text(0.04, 0.855, subtitle, fontsize=9.5, color=INK_2, va="center")
    fig.text(0.04, 0.035, f"Nguồn: {source}", fontsize=7.5, color=MUTED, va="center")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)
    return fig, ax


def target_line(ax, value: float, label: str, vertical: bool = True) -> None:
    if vertical:
        ax.axvline(value, color=INK, linewidth=1)
        ax.annotate(
            label,
            xy=(value, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color=INK,
        )
    else:
        ax.axhline(value, color=INK, linewidth=1)
        ax.annotate(
            label,
            xy=(1.0, value),
            xycoords=("axes fraction", "data"),
            xytext=(-2, 4),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=8.5,
            color=INK,
        )


def save(fig, name: str) -> None:
    fig.savefig(OUT / name)
    plt.close(fig)
    print(name)


def false_alarms_per_hour() -> None:
    # eval/results/report.md sections 2.2, 2.3, 2.8: (label, rate, CI low, CI high)
    rows = [
        ("UTA-RLDD giữ riêng, nhánh buồn ngủ (4,08 giờ)", 0.98, 0.27, 2.51),
        ("UTA-RLDD giữ riêng, mọi nhánh (4,08 giờ)", 1.2, 0.38, 2.7),
        ("UTA-RLDD tập dò, mọi nhánh (3,87 giờ)", 2.5, 1.18, 4.5),
        ("FL3D, mức L1 (0,43 giờ)", 2.3, 0.06, 12.9),
        ("FL3D, mức L2 (0,43 giờ)", 6.9, 1.43, 20.3),
        ("YawDD, clip không ngáp (1,45 giờ)", 6.9, 3.31, 12.7),
        ("SUST-DDD, clip không buồn ngủ (3,05 giờ)", 8.8, 5.83, 12.9),
    ]
    fig, ax = new_figure(
        "Báo sai mỗi giờ: sát mục tiêu trên UTA-RLDD, chưa chứng minh được",
        "Điểm ước lượng và khoảng tin cậy 95 % (Poisson). Trục log. Chưa có giờ lái thật có nhãn.",
        "eval/results/report.md mục 2.2, 2.3, 2.8 (chạy lại 09/10/2026)",
        left=0.42,
    )
    ys = range(len(rows))[::-1]
    for y, (_, rate, low, high) in zip(ys, rows):
        ax.plot([low, high], [y, y], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.plot(rate, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(
            f"{rate:g}".replace(".", ","),
            xy=(high, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=INK_2,
        )
    ax.set_xscale("log")
    ax.set_xlim(0.04, 45)
    ticks = [0.1, 0.5, 1, 2, 5, 10, 20]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{t:g}".replace(".", ",") for t in ticks])
    ax.minorticks_off()
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_xlabel("Cảnh báo sai / giờ", fontsize=9)
    target_line(ax, 1.0, "Mục tiêu PRD ≤ 1,0")
    save(fig, "01-bao-sai-moi-gio.png")


def before_after_m53() -> None:
    # eval/results/report.md section 2.8, 24 held-out subjects: (label, rate, low, high)
    rows = [("Trước khi dò ngưỡng", 1.96, 0.85, 3.87), ("Sau khi dò ngưỡng (M53)", 0.98, 0.27, 2.51)]
    fig, ax = new_figure(
        "Dò ngưỡng trên dữ liệu buồn ngủ thật giảm một nửa số báo sai",
        "Báo sai nhánh buồn ngủ / giờ, 24 người giữ riêng (4,08 giờ tỉnh táo), vạch là CI 95 %.",
        "eval/results/report.md mục 2.8; người ngồi trước laptop, không lái xe",
        left=0.12,
    )
    xs = [0, 1]
    for x, (_, rate, low, high) in zip(xs, rows):
        ax.bar(x, rate, width=0.32, color=BLUE)
        ax.plot([x, x], [low, high], color=INK_2, linewidth=1.2)
        ax.annotate(
            f"{rate:.2f}".replace(".", ","),
            xy=(x + 0.16, rate),
            xytext=(8, -6 if rate < 1.2 else 0),
            textcoords="offset points",
            va="top" if rate < 1.2 else "center",
            fontsize=13,
            fontweight="bold",
        )
    ax.set_xticks(xs)
    ax.set_xticklabels([r[0] for r in rows], fontsize=10, color=INK_2)
    ax.set_xlim(-0.6, 1.9)
    ax.set_ylim(0, 4.2)
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.spines["bottom"].set_color(AXIS)
    ax.set_ylabel("Báo sai / giờ", fontsize=9)
    target_line(ax, 1.0, "Mục tiêu PRD ≤ 1,0", vertical=False)
    save(fig, "02-truoc-sau-do-nguong.png")


def detection_rates() -> None:
    # eval/results/report.md sections 2.2, 2.3: (label, percent, fraction)
    rows = [
        ("Ngủ gật ≥ 3 s phát hiện (FL3D)", 100.0, "11 / 11"),
        ("Ngủ gật ≥ 1,5 s lên L3 (FL3D)", 81.1, "77 / 95"),
        ("Ngáp theo clip, recall (YawDD)", 79.8, "91 / 114"),
        ("Ngáp phát hiện (FL3D)", 75.8, "75 / 99"),
    ]
    fig, ax = new_figure(
        "Ngủ gật dài bắt được hết; ngủ gật ngắn và ngáp còn dưới mục tiêu",
        "Tỉ lệ sự kiện có nhãn mà hệ thống phát hiện. FL3D là video lái đêm, diễn.",
        "eval/results/report.md mục 2.2, 2.3 (chạy lại 09/10/2026)",
        left=0.36,
    )
    ys = range(len(rows))[::-1]
    for y, (_, pct, frac) in zip(ys, rows):
        ax.barh(y, pct, height=0.38, color=BLUE)
        ax.annotate(
            f"{pct:.1f} %".replace(".", ",") + f"  ({frac})",
            xy=(pct, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=INK,
            bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5},
            zorder=3,
        )
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlim(0, 128)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100 %"])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    target_line(ax, 90, "Mục tiêu PRD ≥ 90 %")
    save(fig, "03-ti-le-phat-hien.png")


def time_to_alert() -> None:
    # eval/results/own_recordings.md section 2: (label, p50 s, p95 s)
    rows = [
        ("Nhắm mắt ≥ 1,5 s (38 / 59 lần)", 1.87, 2.03),
        ("Cúi đầu nhắm mắt (7 / 7)", 1.90, 1.99),
        ("Gọi điện (9 / 9)", 2.40, 2.75),
        ("Quay ra sau (2 / 2)", 2.83, 2.83),
        ("Quay đầu sang bên (8 / 8)", 2.98, 3.04),
        ("Nhắn tin (6 / 11)", 3.15, 4.71),
    ]
    fig, ax = new_figure(
        "Thời gian tới cảnh báo: nhắm mắt và gọi điện dưới 3 s, nhắn tin thì chưa",
        "Từ lúc bấm nhãn tới cảnh báo, chỉ tính các lần có cảnh báo. Bản tự ghi, một người.",
        "eval/results/own_recordings.md mục 2 (12 bản ghi, 72 phút)",
        left=0.34,
    )
    ys = range(len(rows))[::-1]
    for y, (_, p50, p95) in zip(ys, rows):
        ax.plot([p50, p95], [y, y], color=AXIS, linewidth=2, solid_capstyle="round", zorder=1)
        ax.plot(p50, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.plot(p95, y, "o", color=ORANGE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(
            f"{p95:.2f} s".replace(".", ","),
            xy=(p95, y),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=INK_2,
            bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5},
            zorder=3,
        )
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlim(0, 5.6)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xticklabels(["0", "1", "2", "3", "4", "5 s"])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    target_line(ax, 3.0, "Mục tiêu PRD p95 ≤ 3 s")
    handles = [
        Line2D([], [], marker="o", linestyle="", color=BLUE, markersize=7, label="p50"),
        Line2D([], [], marker="o", linestyle="", color=ORANGE, markersize=7, label="p95"),
    ]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8.5, labelcolor=INK_2)
    save(fig, "04-thoi-gian-toi-canh-bao.png")


def frame_latency() -> None:
    # benchmark.md, benchmark_simulated.md, benchmark_live.md section 4: (label, p95 ms)
    rows = [
        ("Máy dev, Python (Mac ARM)", 7.2),
        ("Container 4 CPU / 4 GB (simulated)", 11.1),
        ("Trình duyệt, không GPU", 13.4),
        ("Trình duyệt, WebGPU", 17.7),
    ]
    budget = 1000 / 15
    fig, ax = new_figure(
        "Xử lý một frame dùng dưới 30 % ngân sách của 15 FPS",
        "p95 thời gian xử lý một frame (ms). Chưa đo trên thiết bị gắn trên xe.",
        "eval/results/benchmark.md, benchmark_simulated.md, benchmark_live.md mục 4",
        left=0.36,
    )
    ys = range(len(rows))[::-1]
    for y, (_, ms) in zip(ys, rows):
        ax.barh(y, ms, height=0.38, color=BLUE)
        ax.annotate(
            f"{ms:.1f} ms".replace(".", ","),
            xy=(ms, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlim(0, 80)
    ax.set_xticks([0, 20, 40, 60, 80])
    ax.set_xticklabels(["0", "20", "40", "60", "80 ms"])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    target_line(ax, budget, "Ngân sách 15 FPS: 66,7 ms")
    save(fig, "05-do-tre-moi-frame.png")


def block_times() -> None:
    # eval/results/benchmark.md "Each block alone": (label, mean ms)
    rows = [
        ("4 YOLOv8n (luồng riêng, 5 lần / giây)", 16.80),
        ("3 MediaPipe Face Landmarker", 5.83),
        ("2 Tiền xử lý", 0.69),
        ("5 CNN mắt (khi được gọi)", 0.12),
        ("6 Feature extractor", 0.04),
        ("7–12 Chuỗi quyết định", 0.01),
    ]
    fig, ax = new_figure(
        "Gần hết thời gian nằm ở hai model; logic quyết định gần như miễn phí",
        "Thời gian trung bình mỗi lần chạy của từng khối (ms), máy dev Mac ARM, CPU.",
        "eval/results/benchmark.md (300 frame, video YawDD 640×480)",
        left=0.40,
    )
    ys = range(len(rows))[::-1]
    for y, (_, ms) in zip(ys, rows):
        ax.barh(y, ms, height=0.38, color=BLUE)
        ax.annotate(
            f"{ms:.2f} ms".replace(".", ","),
            xy=(ms, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlim(0, 21)
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.set_xticklabels(["0", "5", "10", "15", "20 ms"])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    save(fig, "06-thoi-gian-tung-khoi.png")


def lighting() -> None:
    # eval/results/lighting_transforms.md, fl3d: microsleep runs reaching L3, of 24
    rows = [
        ("Gốc", 18),
        ("Tối nhẹ\n(gamma 1,5)", 12),
        ("Tối\n(gamma 2,2)", 3),
        ("Rất tối\n(gamma 3,5)", 0),
        ("Sáng\n(gain 2,5)", 18),
        ("Chói\n(gain 4)", 9),
        ("Mờ nhẹ\n(blur 1,5)", 17),
        ("Mờ\n(blur 3)", 0),
        ("Ảnh xám\n(kiểu IR)", 0),
    ]
    fig, ax = new_figure(
        "Giới hạn đã biết: mặt tối, chói mạnh, mờ và ảnh xám làm mất cảnh báo ngủ gật",
        "Số lần ngủ gật lên được L3 trên 24 lần, cùng 8 video FL3D, chỉ đổi ánh sáng trong RAM.",
        "eval/results/lighting_transforms.md (biến đổi tổng hợp, không phải ánh sáng thật)",
        left=0.08,
    )
    xs = range(len(rows))
    for x, (_, n) in zip(xs, rows):
        ax.bar(x, n, width=0.42, color=BLUE)
        ax.annotate(
            f"{n} / 24",
            xy=(x, n),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=8.5,
        )
    ax.set_xticks(list(xs))
    ax.set_xticklabels([r[0] for r in rows], fontsize=8, color=INK_2)
    ax.set_ylim(0, 26)
    ax.set_yticks([0, 6, 12, 18, 24])
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.spines["bottom"].set_color(AXIS)
    fig.subplots_adjust(bottom=0.22)
    save(fig, "07-anh-sang.png")


def dataset_hours() -> None:
    # report.md, dataset_uta_rldd.md, glance_ratio.md, phone_web_3mdad.md, own_recordings.md
    rows = [
        ("UTA-RLDD (48 người, buồn ngủ thật)", 25.0),
        ("SUST-DDD (2 074 clip, xe thật)", 5.76),
        ("YawDD (319 video, xe đỗ)", 2.07),
        ("Tự ghi (12 bản ghi, 1 người)", 1.20),
        ("3MDAD (50 tài xế, xe thật)", 1.03),
        ("FL3D / NITYMED (44 video, lái đêm)", 0.79),
        ("Lái thật có nhãn", 0.0),
    ]
    fig, ax = new_figure(
        "Hơn 35 giờ video đã đo, nhưng 0 giờ lái thật có nhãn",
        "Số giờ video của từng nguồn dữ liệu. DROZY (14 người, 36 video) không ghi tổng giờ.",
        "eval/results/ (dataset_uta_rldd, glance_ratio, phone_web_3mdad, own_recordings)",
        left=0.40,
    )
    ys = range(len(rows))[::-1]
    for y, (_, hours) in zip(ys, rows):
        ax.barh(y, hours, height=0.38, color=BLUE)
        ax.annotate(
            f"{hours:g} giờ".replace(".", ","),
            xy=(hours, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlim(0, 30)
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_xlabel("Giờ video", fontsize=9)
    save(fig, "08-du-lieu-da-do.png")


def pilot_readiness() -> None:
    # docs/pilot-readiness.md, 24 criteria: (label, count, colour, text colour)
    rows = [
        ("Đạt", 4, GOOD, "#ffffff"),
        ("Đạt một phần", 9, WARNING, INK),
        ("Chưa đạt", 5, CRITICAL, "#ffffff"),
        ("Chưa đo / chưa có", 5, MUTED, "#ffffff"),
        ("Có số xấp xỉ", 1, BLUE_LIGHT, INK),
    ]
    fig, ax = new_figure(
        "Sẵn sàng pilot: 4 trong 24 tiêu chí đã đạt",
        "24 tiêu chí để chạy thử trên xe thật, theo trạng thái ngày 09/10/2026.",
        "docs/pilot-readiness.md",
        left=0.05,
    )
    fig.subplots_adjust(left=0.05, right=0.95, top=0.70, bottom=0.25)
    start = 0.0
    gap = 0.08
    for label, count, colour, text_colour in rows:
        ax.barh(0, count - gap, left=start + gap / 2, height=0.6, color=colour)
        ax.text(
            start + count / 2,
            0,
            str(count),
            ha="center",
            va="center",
            fontsize=15,
            fontweight="bold",
            color=text_colour,
        )
        above = count == 1  # too narrow for a label below without touching its neighbour
        ax.text(
            start + count if above else start + count / 2,
            0.42 if above else -0.42,
            label,
            ha="right" if above else "center",
            va="bottom" if above else "top",
            fontsize=9.5,
            color=INK_2,
        )
        start += count
    ax.set_xlim(0, 24)
    ax.set_ylim(-0.8, 0.8)
    ax.axis("off")
    save(fig, "09-san-sang-pilot.png")


if __name__ == "__main__":
    false_alarms_per_hour()
    before_after_m53()
    detection_rates()
    time_to_alert()
    frame_latency()
    block_times()
    lighting()
    dataset_hours()
    pilot_readiness()
