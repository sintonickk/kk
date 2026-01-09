import math
from typing import List, Tuple
import numpy as np


def split_into_tiles(img: np.ndarray, tiles: int = 4, overlap: float = 0.0,
                     start_top: float = 0.0, start_left: float = 0.0) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
    h, w = img.shape[:2]
    if tiles <= 0:
        return []
    overlap = float(max(0.0, min(0.5, overlap)))
    try:
        st = float(start_top)
    except Exception:
        st = 0.0
    try:
        sl = float(start_left)
    except Exception:
        sl = 0.0
    st = max(0.0, min(0.99, st))
    sl = max(0.0, min(0.99, sl))
    y0 = int(round(h * st))
    x0 = int(round(w * sl))
    eh = max(1, h - y0)
    ew = max(1, w - x0)
    r = int(math.floor(math.sqrt(tiles)))
    c = int(math.ceil(tiles / r))
    if r * c < tiles:
        c = int(math.ceil(tiles / r))
    ox = int(round(overlap * ew / max(1, c)))
    oy = int(round(overlap * eh / max(1, r)))
    xs = [x0]
    ys = [y0]
    for i in range(1, c):
        xs.append(x0 + int(round(i * ew / c)))
    xs.append(w)
    for j in range(1, r):
        ys.append(y0 + int(round(j * eh / r)))
    ys.append(h)
    res: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
    for j in range(r):
        for i in range(c):
            x1 = xs[i]
            x2 = xs[i + 1]
            y1 = ys[j]
            y2 = ys[j + 1]
            if i > 0:
                x1 = max(x0, x1 - ox)
            if i < c - 1:
                x2 = min(w, x2 + ox)
            if j > 0:
                y1 = max(y0, y1 - oy)
            if j < r - 1:
                y2 = min(h, y2 + oy)
            tile = img[y1:y2, x1:x2]
            res.append((tile, (y1, y2, x1, x2)))
            if len(res) >= tiles:
                return res
    return res
