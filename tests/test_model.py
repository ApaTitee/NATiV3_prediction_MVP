"""数值 QA：全部通过才允许报告引用模型输出。"""
import numpy as np
import pytest

from src.model import priors as P
from src.model import required_effect as RE
from src.model import trial_sim as TS


def test_composite_rate_edges():
    qR = np.array([0.2, 0.3]); qF = np.array([0.4, 0.3])
    assert np.allclose(P.composite_rate(qR, qF, np.zeros(2)), qR * qF)  # ρ=0 → 独立
    # p=q 时 ρ=1 达 Fréchet 上界 min(p,q)；ρ 单调不减
    pi = P.composite_rate(np.full(3, 0.3), np.full(3, 0.3), np.array([0.0, 0.5, 1.0]))
    assert np.all(np.diff(pi) >= 0) and abs(pi[-1] - 0.3) < 1e-9


def test_simulator_matches_analytic_power():
    """无脱落、大 Δ 时模拟 power 应逼近解析值（±3 MCSE）。"""
    M, n, p0, delta, alpha = 40000, 336, 0.08, 0.12, 0.05
    priors = {"pi_pbo": np.full(M, p0), "pi_800": np.full(M, p0 + delta),
              "pi_1200": np.full(M, p0 + delta),
              "d_pbo": np.zeros(M), "d_800": np.zeros(M), "d_1200": np.zeros(M)}
    r = TS.simulate(priors, n, alpha, "single_1200", "NRI", 1.0, 0.5, seed=1)
    analytic = RE.power_two_prop(n, p0, p0 + delta, alpha)
    assert abs(r["P_success"] - analytic) < 3 * r["MCSE"] + 0.005


def test_type1_error_under_null():
    """Δ=0 时 Hochberg 任一显著的 P 应 ≤ α（共享对照下 ≈0.04–0.05）。"""
    M, n, p0, alpha = 40000, 336, 0.08, 0.05
    priors = {"pi_pbo": np.full(M, p0), "pi_800": np.full(M, p0), "pi_1200": np.full(M, p0),
              "d_pbo": np.zeros(M), "d_800": np.zeros(M), "d_1200": np.zeros(M)}
    r = TS.simulate(priors, n, alpha, "hochberg", "NRI", 1.0, 0.5, seed=2)
    assert r["P_success"] <= alpha + 3 * r["MCSE"]
    assert r["P_success"] >= 0.02  # 不至于过度保守到荒谬


def test_hochberg_logic():
    p8 = np.array([0.03, 0.01, 0.06]); p12 = np.array([0.04, 0.20, 0.30])
    s = TS.adjudicate(p8, p12, "hochberg", 0.05)
    assert s.tolist() == [True, True, False]  # 行0：max(p)=0.04≤0.05 → Hochberg 第二步拒绝


def test_nri_attenuation_direction():
    """脱落越高，观测率越低，P(success) 单调不增。"""
    rng = np.random.default_rng(0)
    M = 20000
    base = {"pi_pbo": np.full(M, 0.08), "pi_800": np.full(M, 0.16), "pi_1200": np.full(M, 0.20),
            "d_pbo": rng.uniform(0, 0, M), "d_800": rng.uniform(0, 0, M), "d_1200": rng.uniform(0, 0, M)}
    r0 = TS.simulate(base, 336, 0.05, "hochberg", "NRI", 1.0, 0.5, seed=3)
    high_d = {**base, "d_pbo": np.full(M, 0.4), "d_800": np.full(M, 0.4), "d_1200": np.full(M, 0.4)}
    r1 = TS.simulate(high_d, 336, 0.05, "hochberg", "NRI", 1.0, 0.5, seed=3)
    assert r1["P_success"] < r0["P_success"]


def test_required_delta_monotonic():
    d1 = RE.required_delta(336, 0.07, 0.05, 0.90, 0.20)
    d2 = RE.required_delta(336, 0.07, 0.05, 0.90, 0.40)
    d3 = RE.required_delta(336, 0.14, 0.05, 0.90, 0.20)
    assert d2 > d1  # 脱落高 → 所需 Δ 大
    assert d3 > d1  # p0 高 → 所需 Δ 大
    assert 0.05 < d1 < 0.20


def test_ctgov_endpoint_parse():
    """设计卡主终点必须含 CRN 复合定义（防终点误读）。"""
    import json
    from src.fetch.common import ROOT
    card = json.loads((ROOT / "artifacts/design_card.json").read_text(encoding="utf-8"))
    v = card["primary_endpoint"]["verbatim"]
    assert "ballooning of 0" in v and "fibrosis score ≥1 stage decrease" in v
    assert card["trial"]["hasResultsSection"] is False
