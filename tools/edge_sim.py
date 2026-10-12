"""M42 - Run the long benchmark in a container capped like a small board (`simulated`).

    python tools/edge_sim.py --profile jetson_nano --duration 10m --source data/clip.mp4
    python tools/edge_sim.py --profile jetson_orin_nano --duration 10m --source data/clip.mp4 --phone-model models/yolov8n_int8.onnx
    python tools/edge_sim.py --profile jetson_nano --print          # only show the docker command

What it does: builds the image of Dockerfile.edge when it is missing (or with --build), then runs
tools/benchmark.py --duration inside it with `--cpus` / `--memory` from config/edge_profiles.yaml.
The models folder and the video are mounted read-only, the report folder read-write; nothing else
of the host is visible to the container. Reports go to --out-dir as
benchmark_simulated_<profile>[_<suffix>].md / .json / .csv.

The cap reproduces the board's core count and memory only. Per-core speed, GPU / TensorRT and heat
are not simulated: the result is an upper bound for that board, and every report says `simulated`.

macOS: Docker Desktop may not be allowed to read ~/Documents, ~/Desktop or ~/Downloads ("operation
not permitted" on the mount). Either allow it in System Settings > Privacy & Security > Files and
Folders, or copy the models and the video elsewhere and pass --models-dir / --source / --out-dir.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.config import PROJECT_ROOT  # noqa: E402
from tools.benchmark import load_profile, parse_duration  # noqa: E402

IMAGE = "driverguard-edge"


def docker_command(
    profile: dict,
    source: Path | None,
    duration: str,
    out_dir: Path,
    suffix: str = "",
    phone_model: str | None = None,
    condition: str = "face",
    image: str = IMAGE,
    label: str | None = None,
    models_dir: Path | None = None,
    blocks: bool = False,
) -> list[str]:
    """The `docker run` that executes the long benchmark under the profile's limits (blocks: the
    per-block benchmark instead, FP32 against INT8, under the same limits)."""
    kind = "blocks" if blocks else "simulated"
    name = f"benchmark_{kind}_{profile['name']}" + (f"_{suffix}" if suffix else "")
    memory = f"{int(profile['memory_mb'])}m"
    cmd = ["docker", "run", "--rm", "--cpus", str(profile["cpus"]), "--memory", memory, "--memory-swap", memory]
    if hasattr(os, "getuid"):  # the report files belong to whoever runs this, not to root
        cmd += ["--user", f"{os.getuid()}:{os.getgid()}"]
    models = (models_dir or PROJECT_ROOT / "models").resolve()
    cmd += ["-v", f"{models}:/app/models:ro", "-v", f"{out_dir.resolve()}:/out"]
    src_args: list[str] = []
    if source is not None and condition != "no_face":
        cmd += ["-v", f"{source.resolve()}:/video/{source.name}:ro"]
        src_args = ["--source", f"/video/{source.name}"]
    if blocks:  # each block alone and the main loop with FP32 / INT8 (the INT8 model must already exist)
        return [*cmd, image, "tools/benchmark.py", *src_args, "--out", f"/out/{name}.md", "--json", f"/out/{name}.json"]
    bench = ["tools/benchmark.py", "--duration", duration, "--profile", profile["name"], "--condition", condition]
    bench += src_args
    if phone_model:
        bench += ["--phone-model", phone_model]
    bench += ["--label", label or f"container capped as {profile['name']}", "--progress"]
    bench += ["--out", f"/out/{name}.md", "--json", f"/out/{name}.json", "--csv", f"/out/{name}.csv"]
    return [*cmd, image, *bench]


def image_exists(image: str) -> bool:
    """True when the Docker image exists locally."""
    return subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--profile", required=True, help="a profile of config/edge_profiles.yaml")
    p.add_argument("--duration", default="10m")
    p.add_argument("--source", default=None, help="video file with a face (looped from RAM)")
    p.add_argument("--condition", choices=("no_face", "face", "face_phone"), default="face")
    p.add_argument("--phone-model", default=None, help="e.g. models/yolov8n_int8.onnx")
    p.add_argument("--suffix", default="", help="added to the report file names")
    p.add_argument("--label", default=None)
    p.add_argument("--out-dir", default=str(PROJECT_ROOT / "eval" / "results"))
    p.add_argument("--models-dir", default=None, help="folder with the model files (default: ./models)")
    p.add_argument("--build", action="store_true", help="rebuild the image first")
    p.add_argument("--blocks", action="store_true", help="per-block benchmark (FP32 vs INT8) instead of the long run")
    p.add_argument("--print", action="store_true", help="print the docker command and stop")
    args = p.parse_args(argv)
    try:
        profile = load_profile(args.profile)
        parse_duration(args.duration)
    except (KeyError, ValueError) as e:
        p.error(str(e))
    source = Path(args.source) if args.source else None
    if source is not None and not source.is_file() and not args.print:
        p.error(f"no such video: {source}")
    out_dir = Path(args.out_dir)
    cmd = docker_command(
        profile,
        source,
        args.duration,
        out_dir,
        args.suffix,
        args.phone_model,
        args.condition,
        label=args.label,
        models_dir=Path(args.models_dir) if args.models_dir else None,
        blocks=args.blocks,
    )
    if args.print:
        print(shlex.join(cmd))
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.build or not image_exists(IMAGE):
        build = ["docker", "build", "-f", str(PROJECT_ROOT / "Dockerfile.edge"), "-t", IMAGE, str(PROJECT_ROOT)]
        print("[edge_sim]", shlex.join(build), file=sys.stderr)
        subprocess.run(build, check=True)
    print("[edge_sim]", shlex.join(cmd), file=sys.stderr)
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
