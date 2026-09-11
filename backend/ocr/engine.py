"""OCR engines. EasyOCR is the default (Hindi + English, printed + handwriting-style);
Tesseract is used only if installed and requested."""
from __future__ import annotations

import os
import threading
from typing import Protocol

import numpy as np

# text-detection resolution (px). Detection is the slowest step on CPU.
DETECT_CANVAS = int(os.getenv("LL_OCR_CANVAS", "1280"))


class Engine(Protocol):
    name: str
    languages: list[str]

    def recognize(self, gray: np.ndarray) -> list[dict]:
        """Return tokens: {"text", "confidence" (0..1), "bbox" [x0,y0,x1,y1]}."""


class EasyOCREngine:
    name = "easyocr"

    def __init__(self, languages: list[str] | None = None, gpu: bool | None = None):
        import easyocr
        import torch

        self.languages = languages or ["hi", "en"]
        if gpu is None:
            gpu = torch.cuda.is_available()
        self._reader = easyocr.Reader(self.languages, gpu=gpu, verbose=False)
        self._lock = threading.Lock()

    def recognize(self, gray: np.ndarray) -> list[dict]:
        with self._lock:  # the reader is not thread safe
            # detection runs on a 1280px canvas (the slow part on CPU); recognition still
            # reads crops from the full-resolution image
            results = self._reader.readtext(gray, detail=1, paragraph=False, width_ths=0.7, text_threshold=0.6,
                                            canvas_size=DETECT_CANVAS, batch_size=16)
        tokens = []
        for quad, text, conf in results:
            text = text.strip()
            if not text:
                continue
            xs = [p[0] for p in quad]
            ys = [p[1] for p in quad]
            tokens.append({"text": text, "confidence": round(float(conf), 4),
                           "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]})
        return tokens


class TesseractEngine:
    name = "tesseract"

    def __init__(self, languages: list[str] | None = None):
        import pytesseract

        self._tess = pytesseract
        self.languages = languages or ["hin", "eng"]

    def recognize(self, gray: np.ndarray) -> list[dict]:
        data = self._tess.image_to_data(gray, lang="+".join(self.languages), output_type=self._tess.Output.DICT)
        tokens = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            tokens.append({"text": text, "confidence": round(conf / 100, 4), "bbox": [x, y, x + w, y + h]})
        return tokens


_engines: dict[str, Engine] = {}
_engines_lock = threading.Lock()


def get_engine(name: str = "easyocr") -> Engine:
    """Engines are heavy (model load ~seconds), so keep one per process."""
    with _engines_lock:
        if name not in _engines:
            _engines[name] = EasyOCREngine() if name == "easyocr" else TesseractEngine()
        return _engines[name]


def group_lines(tokens: list[dict]) -> list[dict]:
    """Group tokens into text lines by vertical overlap, left to right."""
    order = sorted(range(len(tokens)), key=lambda i: (tokens[i]["bbox"][1] + tokens[i]["bbox"][3]) / 2)
    lines: list[list[int]] = []
    for i in order:
        x0, y0, x1, y1 = tokens[i]["bbox"]
        cy, h = (y0 + y1) / 2, y1 - y0
        best, best_overlap = None, 0.0
        for ln in lines:
            ly0 = np.median([tokens[j]["bbox"][1] for j in ln])
            ly1 = np.median([tokens[j]["bbox"][3] for j in ln])
            overlap = (min(y1, ly1) - max(y0, ly0)) / max(1.0, min(h, ly1 - ly0))
            if overlap > 0.45 and ly0 <= cy + h * 0.25 and overlap > best_overlap:
                best, best_overlap = ln, overlap
        if best is None:
            lines.append([i])
        else:
            best.append(i)
    out = []
    for ln in lines:
        ln.sort(key=lambda j: tokens[j]["bbox"][0])
        boxes = [tokens[j]["bbox"] for j in ln]
        confs = [tokens[j]["confidence"] for j in ln]
        out.append({
            "text": " ".join(tokens[j]["text"] for j in ln),
            "confidence": round(float(np.mean(confs)), 4),
            "bbox": [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)],
            "token_ids": ln,
        })
    out.sort(key=lambda l: (l["bbox"][1] + l["bbox"][3]) / 2)
    return out
