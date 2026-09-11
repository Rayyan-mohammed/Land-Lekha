"""Track A entry point: document file -> OCR JSON (see docs/contracts.md)."""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from .engine import get_engine, group_lines
from .preprocess import preprocess
from .quality import assess

PDF_DPI = 200
MAX_PAGES = 10


def load_pages(data: bytes, filename: str = "") -> list[np.ndarray]:
    """Decode an uploaded file into BGR page images. Supports PDF and common image types."""
    if filename.lower().endswith(".pdf") or data[:4] == b"%PDF":
        import fitz  # pymupdf

        pages = []
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for i, page in enumerate(pdf):
                if i >= MAX_PAGES:
                    break
                pix = page.get_pixmap(dpi=PDF_DPI)
                arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
                pages.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR if pix.n == 3 else cv2.COLOR_RGBA2BGR))
        return pages
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("unsupported or corrupt image file")
    return [img]


LOW_MEDIAN_CONFIDENCE = 0.4  # upright readable pages sit around 0.7+
FLIP_GAIN = 0.15
FLIP_SAMPLE = 12


def fix_upside_down(gray: np.ndarray, tokens: list[dict], eng) -> tuple[np.ndarray, list[dict], bool]:
    """If the page reads badly, check whether it reads much better rotated 180 degrees.

    Only runs for low-confidence pages, and first compares a sample of the largest text
    boxes in both orientations (recognition only, about a second), so upright pages cost
    nothing and blurred-but-upright pages cost very little."""
    if len(tokens) < 4 or not hasattr(eng, "sample_confidence"):
        return gray, tokens, False
    if float(np.median([t["confidence"] for t in tokens])) >= LOW_MEDIAN_CONFIDENCE:
        return gray, tokens, False
    h, w = gray.shape[:2]
    boxes = [t["bbox"] for t in sorted(tokens, key=lambda t: -(t["bbox"][2] - t["bbox"][0]))[:FLIP_SAMPLE]]
    flipped = cv2.rotate(gray, cv2.ROTATE_180)
    flipped_boxes = [[w - b[2], h - b[3], w - b[0], h - b[1]] for b in boxes]
    if eng.sample_confidence(flipped, flipped_boxes) < eng.sample_confidence(gray, boxes) + FLIP_GAIN:
        return gray, tokens, False
    return flipped, eng.recognize(flipped), True


def run_ocr(data: bytes, filename: str = "", out_dir: Path | None = None, engine: str = "easyocr",
            do_binarize: bool = False) -> dict:
    t0 = time.perf_counter()
    eng = get_engine(engine)
    pages_out = []
    for n, img in enumerate(load_pages(data, filename), start=1):
        pre = preprocess(img, do_binarize=do_binarize)
        tokens = eng.recognize(pre.image)
        pre.image, tokens, flipped = fix_upside_down(pre.image, tokens, eng)
        if flipped:
            pre.steps.append("rotate180")
        image_path = None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            image_path = out_dir / f"page-{n}.png"
            cv2.imwrite(str(image_path), pre.image)
        h, w = pre.image.shape[:2]
        pages_out.append({
            "page": n, "width": w, "height": h,
            "image_path": str(image_path) if image_path else None,
            "preprocess": {"deskew_angle": pre.deskew_angle, "steps": pre.steps, "scale": pre.scale},
            "quality": assess(pre.image, tokens, img.shape),
            "tokens": tokens,
            "lines": group_lines(tokens),
        })
    return {
        "engine": eng.name,
        "languages": eng.languages,
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        "pages": pages_out,
    }


def page_text(ocr: dict) -> str:
    return "\n\n".join("\n".join(l["text"] for l in p["lines"]) for p in ocr["pages"])
