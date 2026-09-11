"""Cell-by-cell reading of ruled tables (Khatauni, Jamabandi registers).

Free text detection on a ruled table has two failure modes: a cell border is read as
a character ("|887^" for "887/1"), and neighbouring cells get merged into one box so
values end up under the wrong header. When a grid is found, each cell is recognised
on its own, cropped inside its borders.
"""
from __future__ import annotations

import os

import cv2
import numpy as np

TABLE_CELLS = os.getenv("LL_OCR_TABLE_CELLS", "0") == "1"
CELL_INSET = 7          # px kept away from the borders
MIN_CELL_INK = 0.004    # fraction of dark pixels below which a cell counts as empty


def _line_positions(profile: np.ndarray, min_fill: float) -> list[int]:
    """Centres of runs where a projection profile is above min_fill."""
    on = profile >= min_fill
    out, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start + i - 1) // 2)
            start = None
    if start is not None:
        out.append((start + len(on) - 1) // 2)
    return out


def detect_tables(gray: np.ndarray) -> list[dict]:
    """Ruled tables as {"bbox", "rows" (y of horizontal rules), "cols" (x of vertical rules),
    "rules" (mask of the ruling pixels)}."""
    h, w = gray.shape
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    horiz = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(150, w // 6), 1)))
    vert = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, h // 40))))
    # tolerate a little residual skew
    horiz = cv2.dilate(horiz, np.ones((5, 1), np.uint8))
    vert = cv2.dilate(vert, np.ones((1, 5), np.uint8))
    grid = cv2.dilate(cv2.bitwise_or(horiz, vert), np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tables = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw < 0.3 * w or bh < 40:
            continue
        hz = horiz[y:y + bh, x:x + bw] > 0
        vt = vert[y:y + bh, x:x + bw] > 0
        rows = [y + r for r in _line_positions(hz.sum(axis=1), 0.5 * bw)]
        cols = [x + q for q in _line_positions(vt.sum(axis=0), 0.5 * bh)]
        if len(rows) >= 3 and len(cols) >= 3:
            mask = np.zeros_like(grid)
            mask[y:y + bh, x:x + bw] = cv2.dilate(cv2.bitwise_or(horiz, vert)[y:y + bh, x:x + bw], np.ones((3, 3), np.uint8))
            tables.append({"bbox": [x, y, x + bw, y + bh], "rows": rows, "cols": cols, "rules": mask})
    return tables


def cells_of(table: dict) -> list[list[int]]:
    r, c = table["rows"], table["cols"]
    return [[c[j] + CELL_INSET, r[i] + CELL_INSET, c[j + 1] - CELL_INSET, r[i + 1] - CELL_INSET]
            for i in range(len(r) - 1) for j in range(len(c) - 1)
            if c[j + 1] - c[j] > 2 * CELL_INSET + 8 and r[i + 1] - r[i] > 2 * CELL_INSET + 8]


def _tight(crop: np.ndarray, cell: list[int], margin: int = 4) -> list[int]:
    """Shrink a cell box to the ink inside it. The line recogniser expects tight crops:
    blank padding around centred text gets read as stray characters."""
    ys, xs = np.nonzero(crop < 128)
    if not len(xs):
        return cell
    x0, y0 = cell[0] + max(0, xs.min() - margin), cell[1] + max(0, ys.min() - margin)
    x1 = cell[0] + min(crop.shape[1], xs.max() + 1 + margin)
    y1 = cell[1] + min(crop.shape[0], ys.max() + 1 + margin)
    return [int(x0), int(y0), int(x1), int(y1)]


def _inside(box: list[int], area: list[int]) -> bool:
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return area[0] <= cx <= area[2] and area[1] <= cy <= area[3]


def read_table_cells(gray: np.ndarray, tokens: list[dict], eng) -> tuple[list[dict], int]:
    """Replace free-detection tokens inside ruled tables with one token per cell.
    Returns the new token list and the number of cells read."""
    if not hasattr(eng, "read_boxes"):
        return tokens, 0
    tables = detect_tables(gray)
    if not tables:
        return tokens, 0
    # erase the ruling so border fragments inside a crop are not read as characters
    clean = gray.copy()
    background = cv2.medianBlur(gray, 21)
    for table in tables:
        clean[table["rules"] > 0] = background[table["rules"] > 0]
    to_read, originals, keep = [], [], []
    for table in tables:
        for cell in cells_of(table):
            inside = [t for t in tokens if _inside(t["bbox"], cell)]
            crop = clean[cell[1]:cell[3], cell[0]:cell[2]]
            if crop.size == 0 or np.mean(crop < 128) < MIN_CELL_INK:
                keep.extend(inside)  # looks empty: trust whatever free detection found
                continue
            centres = sorted((t["bbox"][1] + t["bbox"][3]) / 2 for t in inside)
            if centres and centres[-1] - centres[0] > (cell[3] - cell[1]) * 0.4:
                keep.extend(inside)  # two text lines in one cell: the line recogniser can't do that
            else:
                to_read.append(_tight(crop, cell))
                originals.append(inside)
    outside = [t for t in tokens if not any(_inside(t["bbox"], tb["bbox"]) for tb in tables)]
    by_box = {tuple(t["bbox"]): t for t in eng.read_boxes(clean, to_read)}
    used = 0
    for box, inside in zip(to_read, originals):
        cell_tok = by_box.get(tuple(box))
        free_conf = float(np.mean([t["confidence"] for t in inside])) if inside else 0.0
        # keep whichever reading the recogniser itself trusts more
        if cell_tok and cell_tok["text"].strip() and cell_tok["confidence"] > free_conf:
            keep.append(cell_tok)
            used += 1
        else:
            keep.extend(inside)
    return outside + keep, used
