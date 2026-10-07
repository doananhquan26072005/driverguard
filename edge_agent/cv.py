"""OpenCV where it is installed (the device, the tools), None where it is not.

The browser build (#/live, Pyodide) no longer downloads OpenCV (11.7 MB, M45). What it needs from it
runs on edge_agent/perception/geometry.py there; everything else that uses OpenCV (block 1's
capture, block 2's resize / CLAHE, block 5's eye crops, YOLO's letterbox) is device-only code the
browser never calls.
"""

try:
    import cv2
except ImportError:  # the browser build
    cv2 = None

__all__ = ["cv2"]
