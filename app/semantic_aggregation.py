from __future__ import annotations

from typing import Any

import numpy as np


def aggregate_semantic_scores(
    frame_scores: list[dict[str, float]] | list[Any],
) -> dict[str, Any]:
    """Aggregate per-frame semantic evidence so one frame cannot dominate."""
    if not frame_scores:
        return {
            "frame_count": 0,
            "labels": {},
            "max_labels": {},
            "top_labels": [],
            "temporal_consistency": 0.0,
        }

    names = sorted({
        str(key)
        for row in frame_scores
        if isinstance(row, dict)
        for key in row
    })
    matrix = np.array(
        [[float(row.get(name, 0.0) or 0.0) for name in names] for row in frame_scores],
        dtype=float,
    )
    mean = matrix.mean(axis=0)
    peak = matrix.max(axis=0)
    std = matrix.std(axis=0)

    consistency = np.clip(1.0 - (std / np.maximum(mean, 0.05)), 0.0, 1.0)
    aggregate = 0.8 * mean + 0.2 * (peak * consistency)

    labels = {name: round(float(value), 4) for name, value in zip(names, aggregate)}
    max_labels = {name: round(float(value), 4) for name, value in zip(names, peak)}
    ranked = sorted(labels.items(), key=lambda item: item[1], reverse=True)

    return {
        "frame_count": len(frame_scores),
        "labels": labels,
        "max_labels": max_labels,
        "top_labels": [
            {
                "label": name,
                "confidence": value,
                "consistency": round(float(consistency[names.index(name)]), 4),
            }
            for name, value in ranked[:3]
        ],
        "temporal_consistency": round(float(np.mean(consistency)), 4),
    }
