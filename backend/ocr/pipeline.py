"""Track A entry point: document file -> OCR JSON (see docs/contracts.md)."""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from .engine import get_engine, group_lines
from .preprocess import preprocess

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


def run_ocr(data: bytes, filename: str = "", out_dir: Path | None = None, engine: str = "easyocr",
            do_binarize: bool = False) -> dict:
    t0 = time.perf_counter()
    eng = get_engine(engine)
    pages_out = []
    for n, img in enumerate(load_pages(data, filename), start=1):
        pre = preprocess(img, do_binarize=do_binarize)
        tokens = eng.recognize(pre.image)
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
