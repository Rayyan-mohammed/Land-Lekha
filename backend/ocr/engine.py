"""OCR engines. EasyOCR is the default (Hindi + English, printed + handwriting-style);
Tesseract is used only if installed and requested."""
from __future__ import annotations

import os
import threading
from typing import Protocol

import numpy as np

# text-detection resolution (px). Detection is the slowest step on CPU.
DETECT_CANVAS = int(os.getenv("LL_OCR_CANVAS", "1280"))

# what a land-record number may contain: digits, the "/" of 1124/6क, decimals, and the
# A/B/C suffixes some khasra numbers carry
NUMBER_ALLOWLIST = "0123456789/-.ABC"
NUMBER_ZOOM = 3  # the recogniser reads a small crop better when it is enlarged first


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
        if not gpu:
            # torch defaults to half the logical cores; recognition is CPU-bound matrix
            # math with no other contending work in this process, so using every core
            # measured ~30% faster per document (12.6s -> 8.9s on a 16-thread machine)
            # with identical output - toward the 10s/doc target with no accuracy cost.
            cores = os.cpu_count() or 4
            torch.set_num_threads(cores)
        self._gpu = gpu
        self._readers: dict[tuple[str, ...], "easyocr.Reader"] = {}
        self._readers_lock = threading.Lock()
        self._reader = self._reader_for(self.languages)
        self._numbers = None  # english-only recogniser, built on demand (see read_numbers)
        self._numbers_lock = threading.Lock()
        self._lock = threading.Lock()

    def _reader_for(self, languages: list[str]):
        """One reader per language set, built on first use and kept.

        A model load is seconds and a few hundred megabytes, so a page in Telugu must not pay
        for it twice and a deployment that only ever sees Hindi must not pay for it at all.
        EasyOCR will not pair two Indic scripts in one reader - Devanagari and Telugu have to
        be separate readers, which is why this is a cache rather than one wider reader."""
        import easyocr

        key = tuple(languages)
        with self._readers_lock:
            if key not in self._readers:
                self._readers[key] = easyocr.Reader(list(languages), gpu=self._gpu, verbose=False)
            return self._readers[key]

    def recognize(self, gray: np.ndarray, languages: list[str] | None = None) -> list[dict]:
        reader = self._reader if languages is None else self._reader_for(languages)
        with self._lock:  # the reader is not thread safe
            # detection runs on a 1280px canvas (the slow part on CPU); recognition still
            # reads crops from the full-resolution image
            results = reader.readtext(gray, detail=1, paragraph=False, width_ths=0.7, text_threshold=0.6,
                                      canvas_size=DETECT_CANVAS, batch_size=16)
        return self._tokens(results)

    def sample_confidence(self, gray: np.ndarray, boxes: list[list[int]],
                          languages: list[str] | None = None) -> float:
        """Mean recognition confidence on the given boxes only (no detection pass).
        Cheap way to compare two orientations of the same page."""
        if not boxes:
            return 0.0
        hl = [[b[0], b[2], b[1], b[3]] for b in boxes]  # easyocr wants x_min, x_max, y_min, y_max
        reader = self._reader if languages is None else self._reader_for(languages)
        with self._lock:
            res = reader.recognize(gray, horizontal_list=hl, free_list=[], detail=1, batch_size=16)
        return float(np.mean([r[2] for r in res])) if res else 0.0

    def read_boxes(self, gray: np.ndarray, boxes: list[list[int]]) -> list[dict]:
        """Recognise the given boxes ([x0, y0, x1, y1]) directly, one token per box."""
        if not boxes:
            return []
        hl = [[b[0], b[2], b[1], b[3]] for b in boxes]
        with self._lock:
            res = self._reader.recognize(gray, horizontal_list=hl, free_list=[], detail=1, batch_size=16)
        return self._tokens(res)

    def read_numbers(self, gray: np.ndarray, boxes: list[list[int]]) -> list[dict | None]:
        """Read the given boxes as numbers with an English-only recogniser, one result per box.

        The Hindi+English alphabet is what makes digits hard: it lets the model answer with
        Devanagari digits and look-alike letters. This reader has neither."""
        import cv2

        reader = self._number_reader()
        out: list[dict | None] = []
        for x0, y0, x1, y1 in boxes:
            pad = 4
            crop = gray[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
            if crop.size == 0:
                out.append(None)
                continue
            big = cv2.resize(crop, None, fx=NUMBER_ZOOM, fy=NUMBER_ZOOM, interpolation=cv2.INTER_CUBIC)
            with self._lock:
                res = reader.recognize(big, horizontal_list=[[0, big.shape[1], 0, big.shape[0]]],
                                       free_list=[], detail=1, allowlist=NUMBER_ALLOWLIST)
            out.append({"text": res[0][1].strip(), "confidence": round(float(res[0][2]), 4)} if res else None)
        return out

    def _number_reader(self):
        """Loaded on first use: pages with no unsure numbers never pay for it."""
        with self._numbers_lock:  # two documents can be read at once
            if self._numbers is None:
                import easyocr

                self._numbers = easyocr.Reader(["en"], gpu=False, verbose=False)
            return self._numbers

    @staticmethod
    def _tokens(results) -> list[dict]:
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

    def recognize(self, gray: np.ndarray, languages: list[str] | None = None) -> list[dict]:
        if languages:   # tesseract language codes differ; the caller's codes are easyocr's
            pass
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
