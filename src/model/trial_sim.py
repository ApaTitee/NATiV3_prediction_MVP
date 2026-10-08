"""整试验 Monte Carlo 模拟器。

对每个先验抽样 θ_m：
  1) NRI/MI 衰减观测应答率；2) 各臂生成二项数据；3) 两臂 vs 共享安慰剂的两比例 z 检验；
  4) 按多重性规则裁决 → success。P(success) = mean(success)，附 MCSE。
共享安慰剂臂使两个检验统计量天然相关 —— 解析公式无法处理，故整试验模拟。
"""
import numpy as np
from scipy.stats import norm


def z_test_pvalue(y1: np.ndarray, n1: int, y0: np.ndarray, n0: int) -> np.ndarray:
    """两比例双侧 z 检验（CMH 的未分层近似；向量化）。"""
    p1, p0 = y1 / n1, y0 / n0
    p_pool = (y1 + y0) / (n1 + n0)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n0))
    se = np.maximum(se, 1e-12)
    z = (p1 - p0) / se
    return 2 * (1 - norm.cdf(np.abs(z)))


def adjudicate(p800: np.ndarray, p1200: np.ndarray, rule: str, alpha: float) -> np.ndarray:
    """多重性裁决。返回 success（任一/全部剂量显著，按规则）。"""
    if rule == "hochberg":
        p_min = np.minimum(p800, p1200)
        p_max = np.maximum(p800, p1200)
        return (p_min <= alpha / 2) | (p_max <= alpha)
    if rule == "fixed_sequence":  # 1200 → 800，各自全 α
        return p1200 <= alpha  # "任一剂量成功" 由看门剂量决定
    if rule == "both_required":  # 交集-并集检验，无需 α 校正
        return (p800 <= alpha) & (p1200 <= alpha)
    if rule == "single_1200":
        return p1200 <= alpha
    raise ValueError(rule)


def simulate(priors: dict[str, np.ndarray], n_per_arm: int, alpha: float,
             rule: str, missing: str, attenuation_nri: float, attenuation_mi: float,
             seed: int) -> dict:
    rng = np.random.default_rng(seed + 1)
    att = attenuation_nri if missing == "NRI" else attenuation_mi
    pi_obs = {
        "pbo": priors["pi_pbo"] * (1 - att * priors["d_pbo"]),
        "800": priors["pi_800"] * (1 - att * priors["d_800"]),
        "1200": priors["pi_1200"] * (1 - att * priors["d_1200"]),
    }
    y0 = rng.binomial(n_per_arm, pi_obs["pbo"])
    y8 = rng.binomial(n_per_arm, pi_obs["800"])
    y12 = rng.binomial(n_per_arm, pi_obs["1200"])
    p800 = z_test_pvalue(y8, n_per_arm, y0, n_per_arm)
    p1200 = z_test_pvalue(y12, n_per_arm, y0, n_per_arm)
    succ = adjudicate(p800, p1200, rule, alpha)
    p = succ.mean()
    out = {
        "P_success": float(p),
        "MCSE": float(np.sqrt(p * (1 - p) / len(succ))),
        "pi_obs_mean": {k: float(v.mean()) for k, v in pi_obs.items()},
        "p1200_sig_rate": float((p1200 <= alpha).mean()),
        "p800_sig_rate": float((p800 <= alpha).mean()),
        "succ": succ,
    }
    if "comp" in priors:
        comp = priors["comp"]
        out["P_by_comp"] = {int(c): float(succ[comp == c].mean()) for c in np.unique(comp)}
    return out
