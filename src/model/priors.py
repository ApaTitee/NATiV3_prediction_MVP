"""先验采样器：只读 config/model_params.json（其全部数值可回溯 evidence.csv）。

输出 M 行参数：安慰剂分项率 q_R/q_F、相关 rho、两臂复合应答率、脱落率。
效应量以混合先验（情景组分 S1-S4）进入。
"""
import json
from pathlib import Path

import numpy as np

from src.fetch.common import ROOT


def load_params(path: str | Path | None = None) -> dict:
    p = Path(path) if path else ROOT / "config" / "model_params.json"
    return json.loads(p.read_text(encoding="utf-8"))


def beta_params(mean: float, conc: float) -> tuple[float, float]:
    return mean * conc, (1 - mean) * conc


def composite_rate(q_R: np.ndarray, q_F: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """二值联合分布：π = q_R·q_F + ρ·√(q_R(1-q_R)q_F(1-q_F))。"""
    return q_R * q_F + rho * np.sqrt(q_R * (1 - q_R) * q_F * (1 - q_F))


def sample_priors(params: dict, M: int, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    pb, eff, drp, scn = params["placebo"], params["effect"], params["dropout"], params["scenarios"]

    # —— 情景组分（混合先验） ——
    names = [k for k in scn if not k.startswith("_")]
    weights = np.array([scn[k]["weight"] for k in names])
    weights = weights / weights.sum()
    comp = rng.choice(len(names), size=M, p=weights)
    a0 = np.array([scn[k]["a0"] for k in names])[comp]
    pbo_shift = np.array([scn[k]["pbo_shift_pp"] for k in names])[comp]
    glp1 = np.array([scn[k]["glp1_pp"] for k in names])[comp]

    # —— 安慰剂分项率 ——
    aR, bR = beta_params(pb["q_R_mean"], pb["q_R_conc"])
    aF, bF = beta_params(pb["q_F_mean"], pb["q_F_conc"])
    q_R = rng.beta(aR, bR, M) + pbo_shift
    q_F = rng.beta(aF, bF, M) + pbo_shift
    rho = np.clip(rng.normal(pb["rho_mean"], pb["rho_sd"], M), 0.0, 0.95)
    pi_pbo = np.clip(composite_rate(q_R, q_F, rho) + glp1, 1e-4, 0.95)

    # —— 活性臂：Δ 贴现先验（截断正态，[0, 0.40]） ——
    d1200 = np.clip(rng.normal(eff["delta_1200_ph2"] * a0, eff["delta_sd"], M), 0.0, 0.40)
    d800 = d1200 * eff["delta_800_over_1200"]
    pi_1200 = np.clip(pi_pbo + d1200, 0.0, 0.97)
    pi_800 = np.clip(pi_pbo + d800, 0.0, 0.97)

    # —— 脱落率（各臂独立同分布） ——
    ad, bd = beta_params(drp["d_mean"], drp["d_conc"])
    d_pbo, d_800, d_1200 = (rng.beta(ad, bd, M) for _ in range(3))

    return {
        "comp": comp, "q_R": q_R, "q_F": q_F, "rho": rho,
        "pi_pbo": pi_pbo, "pi_800": pi_800, "pi_1200": pi_1200,
        "d_pbo": d_pbo, "d_800": d_800, "d_1200": d_1200,
    }
