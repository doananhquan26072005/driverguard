"""Download / prepare pretrained model files into models/ (skips files that already exist).

python tools/download_models.py
python tools/download_models.py --verify    # sha256 of the files in models/ against the pinned ones

Every file has a pinned sha256: the models all evaluation numbers were measured with (the same values
are in eval/provenance/uta_rldd/session*_run_info.json). A download that does not match is discarded.

yolov8n.onnx is not published as ONNX: it is exported from the official yolov8n.pt.
That needs ultralytics + torch (large), so do it once in a throwaway venv:

    python -m venv C:/tmp/yx          # short path: torch hits the Windows 260-char limit
    C:/tmp/yx/Scripts/pip install torch --index-url https://download.pytorch.org/whl/cpu
    C:/tmp/yx/Scripts/pip install ultralytics onnx onnxslim
    C:/tmp/yx/Scripts/python tools/download_models.py
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# name -> (url, sha256)
MODELS = {
    # MediaPipe Face Landmarker (478 landmarks), official Google release, version 1 (not the "latest"
    # channel, which can change under the same URL).
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/"
        "face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
    ),
    # Eye-state CNN (block 5): Intel Open Model Zoo open-closed-eye-0001, Apache-2.0. The file with this
    # sha256 is the one whose sha384 is in open_model_zoo/models/public/open-closed-eye-0001/model.yml.
    "open_closed_eye.onnx": (
        "https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/"
        "open-closed-eye-0001/open_closed_eye.onnx",
        "4daa100034482525a26c9afb9297c16580a531189e66e3d2b2ac7d32becfd593",
    ),
}
# Exported here, not downloaded: the ONNX file depends on the ultralytics / onnx versions that wrote it,
# so another export of the same weights can have another sha256. This is the export the phone branch was
# measured with (eval/results/phone_*.md); a different file is reported, and refused only with --strict.
EXPORTED = {"yolov8n.onnx": "26f5b8d6fb9286022a4f39aa53aeb0e794d479979e770f03404f8ea9efa8622e"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(models_dir: Path = MODELS_DIR, strict: bool = False) -> int:
    """Compare the files in models_dir with the pinned sha256. Returns the exit code: 1 when a downloaded
    model differs, or (strict) when the exported one does. A file that is not there is only reported:
    not every install needs every model."""
    failed = False
    pinned = {name: (sha, True) for name, (_, sha) in MODELS.items()} | {n: (s, strict) for n, s in EXPORTED.items()}
    for name, (want, must_match) in pinned.items():
        path = models_dir / name
        if not path.exists():
            print(f"[absent] {name}")
            continue
        got = sha256(path)
        if got == want:
            print(f"[ok] {name} sha256 {got[:12]}")
        elif must_match:
            print(f"[error] {name}: sha256 {got}, pinned {want}")
            failed = True
        else:
            print(f"[warning] {name}: sha256 {got} is another export than the measured one ({want})")
    return 1 if failed else 0


def export_yolov8n(dest: Path) -> bool:
    """Export official YOLOv8n (COCO) to ONNX, 640x640, opset 17. Needs ultralytics."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print(f"[todo] {dest.name}: ultralytics not installed, see instructions at the top of this file")
        return False
    with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
        model = YOLO("yolov8n.pt")  # downloads the official weights into the temp dir
        onnx_path = model.export(format="onnx", imgsz=640, opset=17, simplify=True, dynamic=False)
        shutil.copy(onnx_path, dest)
    print(f"[ok] {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--verify", action="store_true", help="only check the files already in models/")
    p.add_argument("--strict", action="store_true", help="--verify: the exported YOLO file must match too")
    args = p.parse_args(argv)
    if args.verify:
        return verify(strict=args.strict)
    MODELS_DIR.mkdir(exist_ok=True)
    for name, (url, want) in MODELS.items():
        dest = MODELS_DIR / name
        if dest.exists():
            print(f"[skip] {dest} already exists")
            continue
        print(f"[download] {url}")
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        got = sha256(tmp)
        if got != want:
            tmp.unlink()
            print(f"[error] {name}: sha256 {got}, pinned {want}; file discarded")
            return 1
        tmp.replace(dest)
        print(f"[ok] {dest} ({dest.stat().st_size / 1e6:.1f} MB)")

    yolo = MODELS_DIR / "yolov8n.onnx"
    if yolo.exists():
        print(f"[skip] {yolo} already exists")
    elif not export_yolov8n(yolo):
        return 1
    return verify()


if __name__ == "__main__":
    sys.exit(main())
