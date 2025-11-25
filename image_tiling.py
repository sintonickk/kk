import math
from typing import List, Tuple
import numpy as np


def split_into_tiles(img: np.ndarray, tiles: int = 4, overlap: float = 0.0) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
    h, w = img.shape[:2]
    if tiles <= 0:
        return []
    overlap = float(max(0.0, min(0.5, overlap)))
    r = int(math.floor(math.sqrt(tiles)))
    c = int(math.ceil(tiles / r))
    if r * c < tiles:
        c = int(math.ceil(tiles / r))
    ox = int(round(overlap * w / max(1, c)))
    oy = int(round(overlap * h / max(1, r)))
    xs = [0]
    ys = [0]
    for i in range(1, c):
        xs.append(int(round(i * w / c)))
    xs.append(w)
    for j in range(1, r):
        ys.append(int(round(j * h / r)))
    ys.append(h)
    res: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
    for j in range(r):
        for i in range(c):
            x1 = xs[i]
            x2 = xs[i + 1]
            y1 = ys[j]
            y2 = ys[j + 1]
            if i > 0:
                x1 = max(0, x1 - ox)
            if i < c - 1:
                x2 = min(w, x2 + ox)
            if j > 0:
                y1 = max(0, y1 - oy)
            if j < r - 1:
                y2 = min(h, y2 + oy)
            tile = img[y1:y2, x1:x2]
            res.append((tile, (y1, y2, x1, x2)))
            if len(res) >= tiles:
                return res
    return res
