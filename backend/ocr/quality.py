"""Page quality check: should the operator retake this photo?

Thresholds come from the dev set (eval/results/experiments.md): pages whose median
token confidence is below 0.2 yielded no correct fields at all, 0.2-0.4 was unreliable,
and 0.4+ was reliably readable.
"""
from __future__ import annotations

import numpy as np

from .preprocess import SOFT_EDGE_THRESHOLD, edge_sharpness

POOR_CONFIDENCE = 0.2
FAIR_CONFIDENCE = 0.4
MIN_TEXT_HEIGHT = 14      # px in the preprocessed page; smaller text is misread often
MIN_LONG_SIDE = 1000      # px of the original upload (~120 dpi for A4)
MIN_TOKENS = 5


def assess(gray: np.ndarray, tokens: list[dict], original_shape: tuple[int, ...]) -> dict:
    confs = [t["confidence"] for t in tokens]
    heights = [t["bbox"][3] - t["bbox"][1] for t in tokens]
    median_conf = float(np.median(confs)) if confs else 0.0
    text_height = float(np.median(heights)) if heights else 0.0
    sharpness = edge_sharpness(gray)
    long_side = max(original_shape[:2])

    if len(tokens) < MIN_TOKENS or median_conf < POOR_CONFIDENCE:
        verdict = "poor"
    elif median_conf < FAIR_CONFIDENCE:
        verdict = "fair"
    else:
        verdict = "good"

    advice = []
    if verdict != "good":
        if len(tokens) < MIN_TOKENS:
            advice.append("very little text found - check this is a land record page")
        if sharpness < SOFT_EDGE_THRESHOLD:
            advice.append("image is blurred - hold the camera steady, tap to focus and retake")
        if text_height and text_height < MIN_TEXT_HEIGHT:
            advice.append("text is small - move the camera closer or scan at 300 dpi")
        if long_side < MIN_LONG_SIDE:
            advice.append(f"low resolution ({long_side}px) - use at least {MIN_LONG_SIDE}px / 150 dpi")
        if not advice:
            advice.append("text is hard to read - retake in even light, or scan the page")
    return {
        "verdict": verdict,
        "median_confidence": round(median_conf, 3),
        "sharpness": round(sharpness, 1),
        "text_height_px": round(text_height, 1),
        "tokens": len(tokens),
        "advice": advice,
    }
