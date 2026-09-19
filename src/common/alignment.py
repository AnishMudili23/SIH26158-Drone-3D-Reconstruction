"""
Shared similarity-transform alignment (Umeyama, 1991): estimate scale + rotation +
translation mapping one point set onto another.

Used by both the Phase 0 synthetic feasibility test (src/feasibility/scale_recovery.py)
and the real Phase 3 Scale + Geo Alignment stage (src/geo/scale_alignment.py) — same
math, so Phase 0's validated error bounds actually describe what Phase 3 does.
"""
from __future__ import annotations

import numpy as np


def umeyama_alignment(src: np.ndarray, dst: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Estimate similarity transform dst ~= scale * R @ src + t (Umeyama, 1991).

    src, dst: (N, 3) point sets, corresponding rows (e.g. SfM camera centers and their
    GPS-derived ENU positions).
    Returns (scale, R (3,3), t (3,)).
    """
    assert src.shape == dst.shape
    n, dim = src.shape

    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    src_c = src - mu_src
    dst_c = dst - mu_dst

    sigma_src = (src_c ** 2).sum() / n

    cov = (dst_c.T @ src_c) / n
    u, d, vt = np.linalg.svd(cov)

    s = np.ones(dim)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s[-1] = -1

    r = u @ np.diag(s) @ vt
    scale = float(np.trace(np.diag(d) @ np.diag(s)) / sigma_src)
    t = mu_dst - scale * r @ mu_src
    return scale, r, t
