# tests/test_audit.py
import numpy as np, pandas as pd
from curricumap.audit import cronbach_alpha

def test_cronbach_alpha_matches_hand_computation():
    # 3 items, 4 respondents; alpha = (k/(k-1))*(1 - sum(item_var)/total_var)
    m = pd.DataFrame({"i1": [2, 4, 3, 5], "i2": [1, 3, 2, 4], "i3": [3, 5, 4, 6]})
    k = m.shape[1]
    item_var = m.var(ddof=1).sum()
    total_var = m.sum(axis=1).var(ddof=1)
    expected = (k / (k - 1)) * (1 - item_var / total_var)
    alpha, kk = cronbach_alpha(m)
    assert kk == 3
    assert abs(alpha - expected) < 1e-9

def test_cronbach_alpha_imputes_column_mean_for_missing():
    m = pd.DataFrame({"i1": [2, 4, np.nan, 5], "i2": [1, 3, 2, 4], "i3": [3, 5, 4, 6]})
    alpha, k = cronbach_alpha(m, missing="column_mean")
    assert not np.isnan(alpha)
    assert k == 3
