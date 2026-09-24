"""Download / prepare pretrained model files into models/ (skips files that already exist).

python tools/download_models.py

yolov8n.onnx is not published as ONNX: it is exported from the official yolov8n.pt.
That needs ultralytics + torch (large), so do it once in a throwaway venv:

    python -m venv C:/tmp/yx          # short path: torch hits the Windows 260-char limit
    C:/tmp/yx/Scripts/pip install torch --index-url https://download.pytorch.org/whl/cpu
    C:/tmp/yx/Scripts/pip install ultralytics onnx onnxslim
    C:/tmp/yx/Scripts/python tools/download_models.py
"""

from __future__ import annotations

import contextlib
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

MODELS = {
    # MediaPipe Face Landmarker (478 landmarks), official Google release.
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/"
        "face_landmarker.task"
    ),
}


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


def main() -> int:
    MODELS_DIR.mkdir(exist_ok=True)
    for name, url in MODELS.items():
        dest = MODELS_DIR / name
        if dest.exists():
            print(f"[skip] {dest} already exists")
            continue
        print(f"[download] {url}")
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)
        print(f"[ok] {dest} ({dest.stat().st_size / 1e6:.1f} MB)")

    yolo = MODELS_DIR / "yolov8n.onnx"
    if yolo.exists():
        print(f"[skip] {yolo} already exists")
    elif not export_yolov8n(yolo):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
