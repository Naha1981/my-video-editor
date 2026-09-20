from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .semantic_aggregation import aggregate_semantic_scores

_MODEL = None
_PREPROCESS = None
_TOKENIZER = None
_DEVICE = None

LABELS = [
    ("food", "a beautiful plated dish of food"),
    ("hero", "an extreme close-up hero product shot"),
    ("chef", "a chef preparing food in a professional kitchen"),
    ("people", "people dining at a restaurant"),
    ("interior", "a premium restaurant interior"),
    ("experience", "a lively dining experience with real customers"),
    ("exterior", "the exterior or storefront of a restaurant or business"),
    ("product", "a close-up product or menu item"),
    ("generic", "an ordinary unrelated scene"),
]


def _enabled() -> bool:
    return os.getenv("NAHAVIDEO_ENABLE_VISION", "0").lower() in {"1", "true", "yes", "on"}


def _frames(path: Path, max_frames: int = 6) -> list[np.ndarray]:
    duration_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ]
    probe = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
    try:
        duration = max(0.1, float(probe.stdout.strip()))
    except Exception:
        duration = 10.0

    times = np.linspace(0.0, max(0.0, duration - 0.05), max_frames)
    out: list[np.ndarray] = []
    for t in times:
        cmd = [
            "ffmpeg", "-v", "error", "-ss", str(float(t)), "-i", str(path),
            "-frames:v", "1", "-vf", "scale=320:-2:force_original_aspect_ratio=decrease",
            "-f", "image2pipe", "-vcodec", "mjpeg", "-",
        ]
        p = subprocess.run(cmd, capture_output=True, timeout=30)
        if p.returncode != 0 or not p.stdout:
            continue
        arr = cv2.imdecode(np.frombuffer(p.stdout, dtype=np.uint8), cv2.IMREAD_COLOR)
        if arr is not None:
            out.append(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
    return out


def semantic_analyze(path: Path) -> dict[str, Any]:
    if not _enabled():
        return {"available": False, "enabled": False, "labels": {}, "top_labels": [], "reason": "disabled"}

    global _MODEL, _PREPROCESS, _TOKENIZER, _DEVICE
    try:
        import torch
        import open_clip
        from PIL import Image
    except Exception:
        return {
            "available": False,
            "enabled": True,
            "labels": {},
            "top_labels": [],
            "reason": "open_clip_torch, torch and pillow are not installed",
        }

    try:
        if _MODEL is None:
            model_name = os.getenv("NAHAVIDEO_CLIP_MODEL", "ViT-B-32")
            pretrained = os.getenv("NAHAVIDEO_CLIP_PRETRAINED", "openai")
            _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
            _MODEL, _, _PREPROCESS = open_clip.create_model_and_transforms(
                model_name, pretrained=pretrained, device=_DEVICE
            )
            _TOKENIZER = open_clip.get_tokenizer(model_name)
            _MODEL.eval()

        frames = _frames(path)
        if not frames:
            return {"available": True, "enabled": True, "labels": {}, "top_labels": [], "reason": "no frames"}

        texts = [label for _, label in LABELS]
        with torch.no_grad():
            text_features = _MODEL.encode_text(_TOKENIZER(texts))
            text_features /= text_features.norm(dim=-1, keepdim=True)

        frame_scores: list[dict[str, float]] = []
        best_frame = {"index": 0, "label": None, "confidence": 0.0}
        with torch.no_grad():
            for index, frame in enumerate(frames):
                image_tensor = _PREPROCESS(Image.fromarray(frame)).unsqueeze(0).to(_DEVICE)
                image_features = _MODEL.encode_image(image_tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                logits = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                values = logits.squeeze(0).detach().cpu().numpy()
                row = {LABELS[i][0]: round(float(values[i]), 6) for i in range(len(LABELS))}
                frame_scores.append(row)
                top_index = int(np.argmax(values))
                if float(values[top_index]) > best_frame["confidence"]:
                    best_frame = {
                        "index": index,
                        "label": LABELS[top_index][0],
                        "confidence": round(float(values[top_index]), 4),
                    }

        aggregate = aggregate_semantic_scores(frame_scores)
        return {
            "available": True,
            "enabled": True,
            "device": _DEVICE,
            "labels": aggregate["labels"],
            "max_labels": aggregate["max_labels"],
            "top_labels": aggregate["top_labels"],
            "frame_count": aggregate["frame_count"],
            "temporal_consistency": aggregate["temporal_consistency"],
            "best_frame": best_frame,
            "reason": "local OpenCLIP multi-frame semantic aggregation",
        }
    except Exception as exc:
        return {
            "available": False,
            "enabled": True,
            "labels": {},
            "top_labels": [],
            "reason": f"vision model error: {type(exc).__name__}: {exc}",
        }
