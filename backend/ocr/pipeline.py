"""Track A entry point: document file -> OCR JSON (see docs/contracts.md)."""
from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np

from .engine import get_engine, group_lines
from .numbers import NUMBER_PASS, refine_numbers
from .preprocess import preprocess
from .quality import assess, precheck
from .tables import TABLE_CELLS, read_table_cells

# A page that reads badly is read a second time with lighter denoising (see run_ocr).
RETRY_SOFT = os.getenv("LL_OCR_RETRY_SOFT", "1") != "0"
RETRY_DENOISE_H = int(os.getenv("LL_OCR_RETRY_DENOISE_H", "5"))

PDF_DPI = 200
MAX_PAGES = 10
TEXT_LAYER_CONFIDENCE = 0.99
MIN_TEXT_LAYER_WORDS = 15
RECORD_KEYWORDS = ("village", "district", "tehsil", "khata", "khasra", "owner", "survey", "area", "mutation")


def is_pdf(data: bytes, filename: str = "") -> bool:
    return filename.lower().endswith(".pdf") or data[:4] == b"%PDF"


def text_layer_usable(words: list[str]) -> bool:
    """Is a PDF's embedded text real, readable text?

    Born-digital PDFs from land portals carry exact Unicode text. Old Hindi PDFs made
    with pre-Unicode fonts (Kruti Dev etc.) carry Latin gibberish instead ("jke izlkn"),
    and scanned PDFs carry nothing: both must go through OCR."""
    if len(words) < MIN_TEXT_LAYER_WORDS:
        return False
    text = " ".join(words)
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    clean = sum(1 for w in words if all(c.isalnum() or c in "/.:,-()'ऀँंः" or "ऀ" <= c <= "ॿ"
                                          for c in w))
    if clean / len(words) < 0.7:
        return False
    devanagari = sum(1 for c in letters if "ऀ" <= c <= "ॿ") / len(letters)
    return devanagari >= 0.2 or any(k in text.lower() for k in RECORD_KEYWORDS)


def load_pages(data: bytes, filename: str = "") -> list[tuple[np.ndarray, list[dict] | None]]:
    """Decode an upload into BGR page images, plus each PDF page's embedded text as tokens
    (pixel coordinates of the rendered image) when that text layer is usable."""
    if is_pdf(data, filename):
        import fitz  # pymupdf

        pages = []
        scale = PDF_DPI / 72
        try:
            with fitz.open(stream=data, filetype="pdf") as pdf:
                for i, page in enumerate(pdf):
                    if i >= MAX_PAGES:
                        break
                    pix = page.get_pixmap(dpi=PDF_DPI)
                    arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
                    img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR if pix.n == 3 else cv2.COLOR_RGBA2BGR)
                    words = page.get_text("words")  # x0, y0, x1, y1, word, block, line, word_no
                    tokens = None
                    if text_layer_usable([w[4] for w in words]):
                        tokens = [{"text": w[4], "confidence": TEXT_LAYER_CONFIDENCE,
                                   "bbox": [int(w[0] * scale), int(w[1] * scale), int(w[2] * scale) + 1, int(w[3] * scale) + 1]}
                                  for w in words]
                    # A refused text layer (no land words, or pre-Unicode gibberish) still says what
                    # the page is - "TAX INVOICE" - so the land-document classifier gets to see it.
                    pages.append((img, tokens, " ".join(w[4] for w in words) if tokens is None and words else None))
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 - PyMuPDF raises its own exception types for a corrupt file
            raise ValueError("unsupported or corrupt PDF file") from exc
        if not pages:
            raise ValueError("PDF has no pages")
        return pages
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("unsupported or corrupt image file")
    return [(img, None, None)]


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


def _read_page(img, eng, do_binarize: bool, denoise_h: int | None):
    """Preprocess and recognise one page; returns (image, tokens, PreprocessResult)."""
    pre = preprocess(img, do_binarize=do_binarize, denoise_h=denoise_h)
    tokens = eng.recognize(pre.image)
    pre.image, tokens, flipped = fix_upside_down(pre.image, tokens, eng)
    if flipped:
        pre.steps.append("rotate180")
    if TABLE_CELLS:
        tokens, n_cells = read_table_cells(pre.image, tokens, eng)
        if n_cells:
            pre.steps.append(f"table_cells:{n_cells}")
    return pre.image, tokens, pre


def run_ocr(data: bytes, filename: str = "", out_dir: Path | None = None, engine: str = "easyocr",
            do_binarize: bool = False) -> dict:
    t0 = time.perf_counter()
    eng = None  # loaded only if some page needs OCR (digital PDFs never do)
    engines_used: list[str] = []
    pages_out = []
    for n, (img, text_tokens, text_layer_hint) in enumerate(load_pages(data, filename), start=1):
        early_quality = None
        if text_tokens is not None:
            # born-digital PDF page: exact text, no OCR, no geometric changes (boxes stay aligned)
            page_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            tokens = text_tokens
            preprocess_info = {"deskew_angle": 0.0, "steps": ["pdf_text_layer"], "scale": 1.0}
            quality = assess(page_img, tokens, img.shape)
            used = "pdf-text"
        else:
            pre = preprocess(img, do_binarize=do_binarize)
            early_quality = precheck(pre.image, img.shape)
            retried_precheck = False
            if early_quality is not None and RETRY_SOFT:
                # precheck ran on the default (heavier) denoise, which can erase strokes on a
                # blurred page and make it look hopeless when it isn't. Before giving up on
                # OCR entirely, check again on the same lighter denoise the second-read retry
                # below uses - if that reads as hopeless too, it really is unreadable.
                light = preprocess(img, do_binarize=do_binarize, denoise_h=RETRY_DENOISE_H)
                if precheck(light.image, img.shape) is None:
                    early_quality, pre, retried_precheck = None, light, True
            if early_quality is not None:
                # unusable image (too blurred/low-res even after preprocessing): skip the
                # 8-12s neural OCR pass and return the retake advice immediately
                tokens = []
                pre.steps.append("skipped_ocr:poor_quality")
                page_img = pre.image
                quality = early_quality
                used = "none"
            else:
                eng = eng or get_engine(engine)
                page_img, tokens, pre = _read_page(img, eng, do_binarize, RETRY_DENOISE_H if retried_precheck else None)
                quality = assess(page_img, tokens, img.shape)
                if retried_precheck:
                    pre.steps.append("precheck retry")
                # Second chance: strong denoising erases strokes on blurred or faded pages. When a page
                # reads badly, read it again with lighter denoising and keep that reading. Measured on
                # the dev set: +13 of 81 fields on fair/poor pages, and never worse on any of them
                # (eval/results/experiments.md, section 11). Good pages are untouched, so the extra
                # OCR pass only costs time on pages that were going to a verifier anyway. Skipped if
                # the precheck retry above already used this same lighter denoise.
                if RETRY_SOFT and quality["verdict"] != "good" and not retried_precheck:
                    page_img, tokens, pre = _read_page(img, eng, do_binarize, RETRY_DENOISE_H)
                    quality = assess(page_img, tokens, img.shape)
                    pre.steps.append("second read")
                # Numbers last, on the reading we keep. Not on a poor page: there the english
                # recogniser answers confidently with digits that are not on the page at all,
                # and a confident wrong khasra number is worse than an obviously unsure one.
                if NUMBER_PASS and quality["verdict"] != "poor":
                    n_numbers = refine_numbers(page_img, tokens, eng)
                    if n_numbers:
                        pre.steps.append(f"numbers:{n_numbers}")
                used = eng.name
            preprocess_info = {"deskew_angle": pre.deskew_angle, "steps": pre.steps, "scale": pre.scale}
        if used not in engines_used:
            engines_used.append(used)
        image_path = None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            image_path = out_dir / f"page-{n}.png"
            cv2.imwrite(str(image_path), page_img)
        h, w = page_img.shape[:2]
        pages_out.append({
            "page": n, "width": w, "height": h,
            "image_path": str(image_path) if image_path else None,
            "preprocess": preprocess_info,
            "quality": quality,
            "tokens": tokens,
            "lines": group_lines(tokens),
            **({"text_layer": text_layer_hint} if text_layer_hint else {}),
        })
    return {
        "engine": "+".join(engines_used),
        "languages": eng.languages if eng else ["hi", "en"],
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        "pages": pages_out,
    }


def page_text(ocr: dict) -> str:
    return "\n\n".join("\n".join(l["text"] for l in p["lines"]) for p in ocr["pages"])
