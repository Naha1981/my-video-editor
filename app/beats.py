from __future__ import annotations

from typing import Any

import numpy as np


def detect_beats(path, sample_rate: int = 22050) -> dict[str, Any]:
    """Detect musical beat events locally. Falls back cleanly when librosa is unavailable."""
    try:
        import librosa
    except Exception:
        return {"available": False, "beat_times": [], "bpm": None, "reason": "librosa unavailable"}

    try:
        y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
        if y.size < sr * 0.5:
            return {"available": True, "beat_times": [], "bpm": None, "reason": "audio too short"}
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", trim=False)
        bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
        return {
            "available": True,
            "beat_times": [round(float(x), 3) for x in np.asarray(beats).reshape(-1) if float(x) >= 0],
            "bpm": round(bpm, 2) if bpm else None,
            "reason": "local librosa beat tracking",
        }
    except Exception as exc:
        return {
            "available": False,
            "beat_times": [],
            "bpm": None,
            "reason": f"beat analysis error: {type(exc).__name__}: {exc}",
        }
