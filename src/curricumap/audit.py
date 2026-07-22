# src/curricumap/audit.py
from __future__ import annotations
import numpy as np, pandas as pd

def cronbach_alpha(item_matrix: pd.DataFrame, missing: str = "column_mean") -> tuple[float, int]:
    """Cronbach's alpha over an (respondents x items) matrix.

    `missing == "column_mean"` fills NaNs with each item's mean; k is the
    number of items (columns). Returns (nan, k) if fewer than 2 items.
    """
    m = item_matrix.copy()
    if missing == "column_mean":
        m = m.fillna(m.mean(axis=0))
    m = m.dropna(axis=0, how="any")
    k = m.shape[1]
    if k < 2 or m.shape[0] < 2:
        return (float("nan"), k)
    item_var = m.var(axis=0, ddof=1).sum()
    total_var = m.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return (float("nan"), k)
    alpha = (k / (k - 1)) * (1 - item_var / total_var)
    return (float(alpha), k)
