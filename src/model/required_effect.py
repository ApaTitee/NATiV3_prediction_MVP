"""设计隐含效应量反演：给定 n、α、power=90%、脱落/NRI 衰减，反解所需 Δ。

power 用两比例 z 检验正态近似（与模拟器同一检验形式，含 NRI 衰减后的观测率）。
"""
import numpy as np
from scipy.stats import norm


def power_two_prop(n: int, p0: float, p1: float, alpha: float) -> float:
    """双侧两比例 z 检验的近似 power。"""
    p_pool = (p0 + p1) / 2
    se_null = np.sqrt(2 * p_pool * (1 - p_pool) / n)
    se_alt = np.sqrt((p0 * (1 - p0) + p1 * (1 - p1)) / n)
    z_a = norm.ppf(1 - alpha / 2)
    crit = p0 + z_a * se_null
    return float(1 - norm.cdf((crit - p1) / se_alt))


def required_delta(n: int, p0: float, alpha: float, target_power: float,
                   d: float, attenuation: float = 1.0) -> float:
    """NRI 衰减下反解所需真实 Δ（网格 + 二分）。"""
    lo, hi = 0.0, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        p0o = p0 * (1 - attenuation * d)
        p1o = (p0 + mid) * (1 - attenuation * d)
        if power_two_prop(n, p0o, p1o, alpha) >= target_power:
            hi = mid
        else:
            lo = mid
    return hi


def grid(params: dict) -> list[dict]:
    n = params["design"]["n_per_arm"]
    alpha = params["design"]["alpha_two_sided"]
    tp = params["design"]["target_power"]
    rows = []
    for p0 in [0.05, 0.07, 0.09, 0.11, 0.14, 0.16]:
        for d in [0.20, 0.30, 0.40]:
            rows.append({"p0": p0, "dropout": d,
                         "required_delta": round(required_delta(n, p0, alpha, tp, d), 4)})
    return rows
