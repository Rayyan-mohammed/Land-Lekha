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
# Glare is a spot brighter than the page it is on, not simply a bright page. Measured over 108
# real pages: paper sits at 255 on a clean scan, 236 on a scan, 193 on a phone photo - so
# "near-white pixels" alone flagged 19 of 48 scanned pages that had no reflection at all, and
# every clean one. What separates a reflection is the lift above that page's own paper level
# plus the absence of any texture inside it.
GLARE_SATURATION = 245        # the spot itself is blown out
GLARE_MIN_LIFT = 22           # ...and this much brighter than the paper around it
GLARE_MAX_TEXTURE = 6.0       # nothing legible survives inside it
GLARE_MIN_AREA = 0.004        # smaller is a speck
GLARE_MAX_AREA = 0.35         # larger is the page, not a spot on it
# Below this sharpness even after preprocessing, OCR reliably reads nothing usable - checked
# before the neural OCR pass runs, so an obviously unusable phone photo is rejected in
# milliseconds instead of after 8-12s of OCR. Unlike the thresholds above, this one is not
# backed by a dedicated eval/results/experiments.md measurement; treat it as a reasonable
# starting point pending real validation, not a tuned figure.
HOPELESS_SHARPNESS = 90.0


def glare_fraction(gray: np.ndarray) -> float:
    """How much of the page is covered by a blown-out, texture-free spot brighter than the paper.

    Works on a 512px copy, so this costs about a millisecond."""
    import cv2

    h, w = gray.shape[:2]
    scale = 512 / max(h, w)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    small = small.astype(np.float32)
    paper = float(np.median(small))
    mean = cv2.blur(small, (41, 41))
    sq = cv2.blur(small * small, (41, 41))
    texture = np.sqrt(np.maximum(sq - mean * mean, 0))
    hot = (mean >= GLARE_SATURATION) & (mean - paper >= GLARE_MIN_LIFT) & (texture <= GLARE_MAX_TEXTURE)
    return float(np.mean(hot))


def has_glare(gray: np.ndarray) -> bool:
    """A flash or direct sunlight reflecting off the page.

    On the pages we have: no false alarm on any clean, old or scanned page, and 11 of 12 phone
    photos with a reflection painted on are caught. A page whose paper is already pure white
    (a flatbed scan) cannot show a reflection brighter than itself, and none is reported."""
    return GLARE_MIN_AREA <= glare_fraction(gray) <= GLARE_MAX_AREA


def precheck(gray: np.ndarray, original_shape: tuple[int, ...]) -> dict | None:
    """Fast checks that need only the preprocessed image, no OCR tokens. Returns a
    verdict dict to skip OCR entirely, or None to proceed to the full neural OCR pass."""
    sharpness = edge_sharpness(gray)
    long_side = max(original_shape[:2])
    advice = []
    if sharpness < HOPELESS_SHARPNESS:
        advice.append("image is too blurred to read - hold the camera steady, tap to focus and retake")
    if not advice:
        return None
    # Low resolution on its own no longer skips the read. Preprocessing upscales a small page to
    # 1200px, and a 507px photograph of a real deed went from nothing at all to 110 words read
    # that way - enough to tell that it *is* a land document, which refusing to read never is.
    # `assess` still reports the low resolution afterwards, with the retake advice.
    if long_side < MIN_LONG_SIDE:
        advice.append(f"low resolution ({long_side}px) - use at least {MIN_LONG_SIDE}px / 150 dpi")
    return {"verdict": "poor", "median_confidence": 0.0, "sharpness": round(sharpness, 1),
           "text_height_px": 0.0, "tokens": 0, "advice": advice, "skipped_ocr": True}


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
        if has_glare(gray):
            advice.append("glare or reflection detected - avoid direct light/flash on the page, or tilt the camera")
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
