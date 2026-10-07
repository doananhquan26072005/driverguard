"""M42: the long-run benchmark (tools/benchmark.py --duration) and the capped-container launcher
(tools/edge_sim.py). Pure parts only: fake samples, fake cgroup files, no model, no Docker."""

import shlex
from pathlib import Path

import pytest
import yaml

from edge_agent.config import PROJECT_ROOT, load_thresholds
from tools import benchmark as bm
from tools import edge_sim
from tools.benchmark import Sample
from tools.metrics import EvalConfig


def samples(seconds, fps=30.0, cpu=60.0, rss=lambda t: 600.0, temp=None):
    return [Sample(float(t + 1), fps, 12.0, cpu, rss(t + 1), temp, 14) for t in range(seconds)]


def result(smp, **over):
    r = {
        "system": {
            "cpu": "arm",
            "cores": 10,
            "os": "Linux 6",
            "python": "3.11",
            "onnxruntime": "1.30",
            "opencv": "4.11",
            "mediapipe": "0.10.21",
            "ram_gb": 16.0,
        },
        "limits": {"cpus": None, "memory_mb": None},
        "profile": None,
        "condition": "face",
        "label": "test run",
        "source": "clip.mp4 (640x480, 300 frames)",
        "phone_model": "yolov8n.onnx",
        "phone_threads": 2,
        "pace_fps": 30.0,
        "duration_s": float(len(smp)),
        "frames": int(sum(s.fps for s in smp)),
        "frames_with_face": int(sum(s.fps for s in smp)),
        "latency": bm.summarize([10.0] * 100),
        "yolo_runs_per_s": 5.0,
        "yolo_stale": 0,
        "cpu": {"mean": 60.0, "p95": 70.0, "max": 80.0},
        "rss_mb": {"start": smp[0].rss_mb, "end": smp[-1].rss_mb, "max": max(s.rss_mb for s in smp)},
        "rss_growth_mb_per_h": bm.rss_growth_mb_per_h(smp),
        "minutes": bm.per_minute(smp),
    }
    r.update(over)
    return r


# ---------------------------------------------------------------- small parsers


@pytest.mark.parametrize(("text", "seconds"), [("90s", 90), ("10m", 600), ("1.5h", 5400), ("45", 45), (" 2 m ", 120)])
def test_parse_duration(text, seconds):
    assert bm.parse_duration(text) == seconds


@pytest.mark.parametrize("bad", ["", "ten minutes", "0", "-5m", "10d"])
def test_parse_duration_refuses_nonsense(bad):
    with pytest.raises(ValueError):
        bm.parse_duration(bad)


def test_profiles_file_has_what_the_tools_need():
    profiles = yaml.safe_load((PROJECT_ROOT / "config" / "edge_profiles.yaml").read_text(encoding="utf-8"))
    assert {"jetson_nano", "jetson_orin_nano"} <= set(profiles)
    nano = bm.load_profile("jetson_nano")
    assert (nano["name"], nano["cpus"], nano["memory_mb"], nano["threads"]) == ("jetson_nano", 4, 4096, 2)
    with pytest.raises(KeyError, match="unknown profile"):
        bm.load_profile("raspberry_pi_9")


def test_incomplete_profile_is_refused(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text("half: {cpus: 2}\n", encoding="utf-8")
    with pytest.raises(KeyError, match="lacks"):
        bm.load_profile("half", path)


def test_cgroup_limits_as_the_process_sees_them(tmp_path):
    assert bm.cgroup_limits(tmp_path) == {"cpus": None, "memory_mb": None}  # not a container
    (tmp_path / "cpu.max").write_text("400000 100000\n")
    (tmp_path / "memory.max").write_text(f"{4096 * 1024 * 1024}\n")
    assert bm.cgroup_limits(tmp_path) == {"cpus": 4.0, "memory_mb": 4096.0}
    (tmp_path / "cpu.max").write_text("max 100000\n")
    (tmp_path / "memory.max").write_text("max\n")
    assert bm.cgroup_limits(tmp_path) == {"cpus": None, "memory_mb": None}  # a container without limits


# ---------------------------------------------------------------- statistics of a run


def test_per_minute_rows():
    smp = samples(60, fps=30.0, cpu=50.0) + [Sample(60.0 + t + 1, 12.0, 80.0, 95.0, 640.0, 71.0, 14) for t in range(30)]
    rows = bm.per_minute(smp)
    assert [(r["minute"], r["seconds"]) for r in rows] == [(0, 59), (1, 31)]  # the sample at t = 60.0 opens minute 2
    assert rows[0]["fps_mean"] == pytest.approx(30.0) and rows[0]["temp_c"] is None
    assert rows[1]["fps_min"] == 12.0 and rows[1]["cpu_max"] == 95.0 and rows[1]["temp_c"] == 71.0
    assert rows[1]["p95_ms"] == 80.0


def test_memory_growth_is_a_slope_after_the_first_minute():
    leak = samples(600, rss=lambda t: 500.0 + 0.1 * t)  # 0.1 MB / s
    assert bm.rss_growth_mb_per_h(leak) == pytest.approx(360.0, rel=0.01)
    warm_then_flat = samples(600, rss=lambda t: 400.0 + min(t, 50) * 4.0)  # models loading, then steady
    assert bm.rss_growth_mb_per_h(warm_then_flat) == pytest.approx(0.0, abs=0.5)
    assert bm.rss_growth_mb_per_h(samples(90)) is None  # too short to tell


def test_verdict_against_the_thresholds():
    cfg = EvalConfig.from_dict(load_thresholds()["eval"])
    assert (cfg.soak_min_fps, cfg.soak_rss_growth_mb_per_h) == (15.0, 20.0)
    good = result(samples(600))
    v = {name: ok for name, ok, _ in bm.soak_verdict(good, cfg.soak_min_fps, cfg.soak_rss_growth_mb_per_h)}
    assert v["FPS at least 15 in every minute"] is True and v["memory grows less than 20 MB / h"] is True
    assert v["temperature"] is None  # never judged: no limit is set for it
    slow_then_leaky = samples(300) + [
        Sample(300.0 + t + 1, 11.0, 90.0, 99.0, 600.0 + 0.2 * t, None, 14) for t in range(300)
    ]
    v = {name: ok for name, ok, _ in bm.soak_verdict(result(slow_then_leaky), 15.0, 20.0)}
    assert v["FPS at least 15 in every minute"] is False and v["memory grows less than 20 MB / h"] is False
    short = {name: ok for name, ok, _ in bm.soak_verdict(result(samples(20)), 15.0, 20.0)}
    assert set(short.values()) == {None}  # 20 s: nothing can be judged


def test_a_throttled_minute_fails_even_when_the_average_is_fine():
    smp = samples(540) + [Sample(540.0 + t + 1, 9.0, 100.0, 99.0, 600.0, 85.0, 14) for t in range(60)]
    r = result(smp)
    assert r["frames"] / r["duration_s"] > 25  # the whole-run FPS looks fine
    verdict = bm.soak_verdict(r, 15.0, 20.0)
    assert verdict[0][1] is False and "lowest minute 9." in verdict[0][2]  # the last minute, at 9 FPS
    assert "highest 85 °C" in verdict[2][2]


# ---------------------------------------------------------------- reports


def test_report_of_a_plain_run_is_not_called_simulated():
    text = bm.soak_report(result(samples(600)), 15.0, 20.0)
    assert text.startswith("# DriverGuard - long-run benchmark\n")
    assert "simulated" not in text and "Limits: none seen by the process" in text
    assert "| FPS at least 15 in every minute | ✅ |" in text
    assert text.count("\n| ") >= 12  # the summary row, three criteria and ten minutes


def test_report_of_a_capped_run_says_simulated_and_what_it_is_not():
    profile = bm.load_profile("jetson_nano")
    r = result(samples(600), limits={"cpus": 4.0, "memory_mb": 4096.0}, profile=profile)
    text = bm.soak_report(r, 15.0, 20.0)
    assert text.startswith("# DriverGuard - long-run benchmark (`simulated`)")
    assert "4.00 CPUs, 4096 MB (cgroup)" in text and "profile `jetson_nano`" in text
    assert "an upper bound, not a measurement of the device" in text
    assert "15 % of 4" in text  # 60 % of one core, out of the 4 it may use


def test_a_profile_without_the_real_limit_is_flagged():
    r = result(samples(120), profile=bm.load_profile("jetson_nano"))  # --profile given, not run in the container
    text = bm.soak_report(r, 15.0, 20.0)
    assert "The CPU limit of the profile was NOT applied" in text and "`simulated`" in text


def test_combined_report_lists_every_run():
    a = result(samples(600), label="Mac dev")
    b = result(
        samples(300), label="capped", limits={"cpus": 4.0, "memory_mb": 4096.0}, profile=bm.load_profile("jetson_nano")
    )
    text = bm.combine_report([a, b], 15.0, 20.0)
    assert "| Mac dev (face) | this machine | none |" in text
    assert "| capped (face) | `simulated` | 4 CPUs, 4096 MB |" in text
    assert text.count("## Run:") == 2 and "### Minute by minute" in text


# ---------------------------------------------------------------- the container command


def test_docker_command_caps_cpu_and_memory_and_mounts_read_only(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"")
    cmd = edge_sim.docker_command(bm.load_profile("jetson_nano"), video, "10m", tmp_path / "out")
    text = shlex.join(cmd)
    assert "--cpus 4 --memory 4096m --memory-swap 4096m" in text
    assert f"{PROJECT_ROOT / 'models'}:/app/models:ro" in text and f"{video}:/video/clip.mp4:ro" in text
    assert "--duration 10m --profile jetson_nano --condition face --source /video/clip.mp4" in text
    assert cmd[-6:] == [
        "--out",
        "/out/benchmark_simulated_jetson_nano.md",
        "--json",
        "/out/benchmark_simulated_jetson_nano.json",
        "--csv",
        "/out/benchmark_simulated_jetson_nano.csv",
    ]
    mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]
    assert len(mounts) == 3 and sum(m.endswith(":ro") for m in mounts) == 2  # only the report folder is writable


def test_docker_command_variants(tmp_path):
    orin = bm.load_profile("jetson_orin_nano")
    cmd = edge_sim.docker_command(orin, None, "5m", tmp_path, suffix="int8", phone_model="models/yolov8n_int8.onnx")
    text = shlex.join(cmd)
    assert "--cpus 6 --memory 8192m" in text and "--phone-model models/yolov8n_int8.onnx" in text
    assert "--source" not in text and "benchmark_simulated_jetson_orin_nano_int8.md" in text
    video = tmp_path / "c.mp4"
    blocks = edge_sim.docker_command(orin, video, "5m", tmp_path, blocks=True, models_dir=tmp_path / "m")
    assert "--duration" not in blocks and blocks[-4:] == [
        "--out",
        "/out/benchmark_blocks_jetson_orin_nano.md",
        "--json",
        "/out/benchmark_blocks_jetson_orin_nano.json",
    ]
    assert f"{(tmp_path / 'm').resolve()}:/app/models:ro" in blocks


def test_print_shows_the_command_without_docker(capsys):
    assert edge_sim.main(["--profile", "jetson_nano", "--source", "nowhere.mp4", "--print"]) == 0
    assert capsys.readouterr().out.startswith("docker run --rm --cpus 4")


def test_edge_image_copies_no_model_and_no_data():
    text = (PROJECT_ROOT / "Dockerfile.edge").read_text(encoding="utf-8")
    copies = [line.split()[1] for line in text.splitlines() if line.startswith("COPY ")]
    assert copies == ["edge_agent/", "tools/", "config/"]
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    edge = compose["services"]["edge"]
    assert edge["profiles"] == ["edge"]  # never started by a plain `docker compose up`
    assert all(v.endswith(":ro") for v in edge["volumes"])
    assert Path(PROJECT_ROOT / edge["build"]["dockerfile"]).is_file()
