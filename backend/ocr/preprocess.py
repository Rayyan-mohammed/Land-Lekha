"""Image preprocessing before OCR: page crop, illumination fix, deskew, denoise, contrast.

Every step is optional and recorded, so the verifier UI can show what was done.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import cv2
import numpy as np

TARGET_LONG_SIDE = 1800
MIN_LONG_SIDE = 1200
# adaptive sharpening of soft pages (see edge_sharpness); LL_OCR_SHARPEN=1 enables
SHARPEN = os.getenv("LL_OCR_SHARPEN", "0") == "1"
SOFT_EDGE_THRESHOLD = 450.0


@dataclass
class PreprocessResult:
    image: np.ndarray  # final grayscale image handed to OCR
    deskew_angle: float = 0.0
    steps: list[str] = field(default_factory=list)
    scale: float = 1.0


def to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    if img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    # keep blue ink dark: use min over channels instead of luminance, so handwritten
    # blue/violet entries don't fade into the paper
    lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.int16)
    darkest = img.min(axis=2).astype(np.int16) + 30
    return np.minimum(lum, darkest).clip(0, 255).astype(np.uint8)


def normalize_size(gray: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = gray.shape
    long_side = max(h, w)
    if long_side > TARGET_LONG_SIDE:
        s = TARGET_LONG_SIDE / long_side
    elif long_side < MIN_LONG_SIDE:
        s = MIN_LONG_SIDE / long_side
    else:
        return gray, 1.0
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    return cv2.resize(gray, (round(w * s), round(h * s)), interpolation=interp), s


def find_page_quad(gray: np.ndarray) -> np.ndarray | None:
    """Detect a document page inside a photo (e.g. paper on a table). None if the
    page already fills the frame."""
    h, w = gray.shape
    small = cv2.resize(gray, (w // 4, h // 4))
    edges = cv2.Canny(cv2.GaussianBlur(small, (5, 5), 0), 40, 120)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_total = small.shape[0] * small.shape[1]
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        area = cv2.contourArea(approx)
        if len(approx) == 4 and 0.35 * area_total < area < 0.92 * area_total:
            return approx.reshape(4, 2).astype(np.float32) * 4
    return None


def warp_quad(gray: np.ndarray, quad: np.ndarray) -> np.ndarray:
    s = quad.sum(1)
    d = np.diff(quad, axis=1).ravel()
    tl, br = quad[np.argmin(s)], quad[np.argmax(s)]
    tr, bl = quad[np.argmin(d)], quad[np.argmax(d)]
    w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    M = cv2.getPerspectiveTransform(np.float32([tl, tr, br, bl]), np.float32([[0, 0], [w, 0], [w, h], [0, h]]))
    return cv2.warpPerspective(gray, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def flatten_illumination(gray: np.ndarray) -> np.ndarray:
    """Divide by estimated background: removes stains, yellowing and uneven light."""
    k = max(31, (min(gray.shape) // 25) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    bg = cv2.medianBlur(bg, 21)
    norm = cv2.divide(gray, bg, scale=255)
    return norm


def estimate_skew(gray: np.ndarray, max_angle: float = 10.0) -> float:
    """Projection-profile skew estimate: the rotation that makes text rows sharpest."""
    h, w = gray.shape
    s = 800 / max(h, w)
    small = cv2.resize(gray, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    bw = cv2.adaptiveThreshold(small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    center = (bw.shape[1] / 2, bw.shape[0] / 2)

    def score(a: float) -> float:
        M = cv2.getRotationMatrix2D(center, a, 1.0)
        rot = cv2.warpAffine(bw, M, (bw.shape[1], bw.shape[0]), flags=cv2.INTER_NEAREST)
        prof = rot.sum(axis=1, dtype=np.float64)
        return float(np.sum(np.diff(prof) ** 2))

    best = max(np.arange(-max_angle, max_angle + 0.01, 0.5), key=score)
    best = max(np.arange(best - 0.5, best + 0.51, 0.1), key=score)
    return round(float(best), 2)


def _profile_sharpness(bw: np.ndarray, axis: int) -> float:
    prof = bw.sum(axis=axis).astype(np.float64)
    return float(np.sum(np.diff(prof) ** 2)) / (prof.sum() ** 2 + 1e-9) * len(prof)


def is_sideways(gray: np.ndarray) -> bool:
    """True when text lines run vertically (page photographed rotated by 90 degrees).

    Horizontal text makes the row-ink profile sharply structured; on the dev set the
    row/column ratio is >= 1.33 for upright pages and <= 0.75 for sideways ones."""
    s = 800 / max(gray.shape)
    small = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    bw = cv2.adaptiveThreshold(small, 1, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    return _profile_sharpness(bw, 1) / max(_profile_sharpness(bw, 0), 1e-9) < 1.0


def rotate(gray: np.ndarray, angle: float) -> np.ndarray:
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)


def edge_sharpness(gray: np.ndarray) -> float:
    """Strength of the strongest edges (99.5th percentile gradient). Clean pages score
    ~850, blurred scans and phone photos 180-450."""
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    return float(np.percentile(np.hypot(gx, gy), 99.5))


def sharpen(gray: np.ndarray, amount: float = 1.2, sigma: float = 1.5) -> np.ndarray:
    """Unsharp mask: restores stroke edges softened by focus blur or a cheap scanner."""
    blurred = cv2.GaussianBlur(gray, (0, 0), sigma)
    return cv2.addWeighted(gray, 1 + amount, blurred, -amount, 0)


def enhance_contrast(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def binarize(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)


def preprocess(img: np.ndarray, *, do_binarize: bool = False) -> PreprocessResult:
    """Full chain. Binarization is off by default: the neural OCR reads cleaned
    grayscale better than hard black/white (measured on the dev set)."""
    steps = ["grayscale"]
    gray = to_gray(img)
    gray, scale = normalize_size(gray)
    if scale != 1.0:
        steps.append(f"resize x{scale:.2f}")
    quad = find_page_quad(gray)
    if quad is not None:
        gray = warp_quad(gray, quad)
        steps.append("page_crop")
    gray = flatten_illumination(gray)
    steps.append("illumination")
    if is_sideways(gray):
        # direction is unknown here; an upside-down result is fixed after recognition
        # (see pipeline.fix_upside_down)
        gray = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
        steps.append("rotate90")
    angle = estimate_skew(gray)
    if abs(angle) >= 0.2:
        gray = rotate(gray, angle)
        steps.append("deskew")
    gray = denoise(gray)
    steps.append("denoise")
    if SHARPEN and edge_sharpness(gray) < SOFT_EDGE_THRESHOLD:
        gray = sharpen(gray)
        steps.append("sharpen")
    gray = enhance_contrast(gray)
    steps.append("clahe")
    if do_binarize:
        gray = binarize(gray)
        steps.append("binarize")
    return PreprocessResult(image=gray, deskew_angle=angle, steps=steps, scale=scale)
