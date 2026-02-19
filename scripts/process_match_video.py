"""Process football video with YOLO + optional DeepSORT and export tracking JSON.

Example:
  python scripts/process_match_video.py ^
      --video data/match.mp4 ^
      --out data/tracking_output.json ^
      --homography data/homography.json

homography.json format:
{
  "src_points": [[123, 98], [1800, 100], [1880, 980], [80, 970]],
  "dst_points": [[0, 0], [105, 0], [105, 68], [0, 68]]
}
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

import numpy as np


def _require_cv_stack():
    try:
        import cv2  # noqa: F401
        from ultralytics import YOLO  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "OpenCV + Ultralytics are required. Install with: pip install -r requirements_ai.txt"
        ) from exc


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


def _load_homography(path: Path) -> np.ndarray:
    payload = json.loads(path.read_text(encoding="utf-8"))
    src = np.array(payload["src_points"], dtype=np.float32)
    dst = np.array(payload["dst_points"], dtype=np.float32)
    if src.shape != (4, 2) or dst.shape != (4, 2):
        raise ValueError("Homography points must be 4x2 arrays.")
    import cv2

    h, _ = cv2.findHomography(src, dst)
    if h is None:
        raise RuntimeError("Homography matrix could not be computed.")
    return h


def _project_to_pitch(h: np.ndarray, pt: tuple[float, float]) -> tuple[float, float]:
    import cv2

    px = np.array([[[pt[0], pt[1]]]], dtype=np.float32)
    projected = cv2.perspectiveTransform(px, h)[0][0]
    return float(projected[0]), float(projected[1])


def _as_detection_list(results: Any) -> List[Detection]:
    detections: list[Detection] = []
    boxes = results.boxes
    if boxes is None:
        return detections
    for b in boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        conf = float(b.conf[0].item())
        cls_id = int(b.cls[0].item())
        detections.append(Detection(x1, y1, x2, y2, conf, cls_id))
    return detections


def main() -> None:
    parser = argparse.ArgumentParser(description="Track players from video")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO model weights")
    parser.add_argument("--conf", type=float, default=0.35, help="Detection confidence threshold")
    parser.add_argument("--homography", required=True, help="Path to homography points JSON")
    parser.add_argument("--max-frames", type=int, default=0, help="Optional cap for quick tests")
    parser.add_argument("--use-deepsort", action="store_true", help="Enable DeepSORT tracking IDs")
    args = parser.parse_args()

    _require_cv_stack()
    import cv2
    from ultralytics import YOLO

    video_path = Path(args.video)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h_path = Path(args.homography)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not h_path.exists():
        raise FileNotFoundError(f"Homography file not found: {h_path}")

    h = _load_homography(h_path)
    model = YOLO(args.model)
    tracker = None
    if args.use_deepsort:
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "deep-sort-realtime is required for --use-deepsort. "
                "Install with: pip install -r requirements_ai.txt"
            ) from exc
        tracker = DeepSort(max_age=30, n_init=3)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Could not open input video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_idx = 0
    payload: dict[str, Any] = {
        "video": str(video_path),
        "fps": fps,
        "frames": [],
    }

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        if args.max_frames > 0 and frame_idx > args.max_frames:
            break

        results = model.predict(source=frame, conf=args.conf, verbose=False)[0]
        detections = _as_detection_list(results)

        frame_items = []
        tracks_by_box: dict[tuple[int, int, int, int], int] = {}
        if tracker is not None:
            ds_inputs = []
            for det in detections:
                if det.class_id != 0:
                    continue
                ds_inputs.append(([det.x1, det.y1, det.x2 - det.x1, det.y2 - det.y1], det.confidence, "player"))
            tracks = tracker.update_tracks(ds_inputs, frame=frame)
            for trk in tracks:
                if not trk.is_confirmed():
                    continue
                l, t, r, b = trk.to_ltrb()
                tracks_by_box[(round(l), round(t), round(r), round(b))] = int(trk.track_id)
        for det in detections:
            # COCO class 0 = person. We keep only players (persons) in MVP.
            if det.class_id != 0:
                continue
            cx, cy = det.centroid
            field_x, field_y = _project_to_pitch(h, (cx, cy))
            frame_items.append(
                {
                    "frame_index": frame_idx,
                    "timestamp_sec": round(frame_idx / fps, 3),
                    "bbox": [det.x1, det.y1, det.x2, det.y2],
                    "track_id": tracks_by_box.get(
                        (round(det.x1), round(det.y1), round(det.x2), round(det.y2))
                    ),
                    "confidence": det.confidence,
                    "pixel_centroid": [cx, cy],
                    "field_position": [field_x, field_y],
                }
            )

        payload["frames"].append({"frame_index": frame_idx, "objects": frame_items})

    cap.release()
    out_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    print("tracking_export_ok")
    print(f"frames={len(payload['frames'])}")
    print(f"out={out_path}")


if __name__ == "__main__":
    main()
