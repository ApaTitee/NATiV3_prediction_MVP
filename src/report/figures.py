"""图件生成（读 artifacts/model/*.csv + 重采样先验，离线可复现）。"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.fetch.common import ROOT
from src.model import priors as P

FIG = ROOT / "report" / "figures"
MODEL = ROOT / "artifacts" / "model"


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    params = P.load_params()
    ps = P.sample_priors(params, params["mc"]["M"], params["mc"]["seed"])
    verdict = json.loads((MODEL / "verdict.json").read_text(encoding="utf-8"))

    # F1 先验复合率分布 vs 外部锚点
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for key, c, lab in [("pi_pbo", "gray", "placebo"), ("pi_800", "#1f77b4", "lani 800mg"), ("pi_1200", "#d62728", "lani 1200mg")]:
        ax.hist(ps[key], bins=120, density=True, histtype="step", color=c, lw=1.5, label=f"prior {lab}")
    anchors = [("NATIVE pbo 9% / deck 7%", 0.08, "gray"), ("ESSENCE pbo 16.1%", 0.161, "gray"),
               ("NATIVE 1200mg 35% (SAF)", 0.35, "#d62728"), ("deck F2/F3 1200mg 33% (CRN-like)", 0.33, "#d62728"),
               ("ESSENCE drug 32.7%", 0.327, "green")]
    for lab, x, c in anchors:
        ax.axvline(x, color=c, ls="--", alpha=0.5)
        ax.text(x, ax.get_ylim()[1] * 0.92, lab, rotation=90, va="top", fontsize=7, color=c)
    ax.set_xlabel("composite response rate (true, pre-dropout)")
    ax.set_ylabel("prior density")
    ax.set_title("Prior composite rates vs external anchors (Ph2b NATIVE / ESSENCE)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "prior_composite_rates.png", dpi=150)
    plt.close(fig)

    # F2 设计隐含 Δ 反演 vs 先验 Δ
    di = pd.read_csv(MODEL / "design_implied_delta.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for d, mk in [(0.20, "o"), (0.30, "s"), (0.40, "^")]:
        sub = di[di["dropout"] == d]
        ax.plot(sub["p0"], sub["required_delta"], marker=mk, label=f"required Δ @90% power, dropout={d:.0%}")
    delta_prior = ps["pi_1200"] - ps["pi_pbo"]
    ax.axhspan(np.percentile(delta_prior, 10), np.percentile(delta_prior, 90), alpha=0.15, color="red",
               label=f"prior Δ(1200mg) I80 = [{np.percentile(delta_prior,10):.3f}, {np.percentile(delta_prior,90):.3f}]")
    ax.axhline(np.median(delta_prior), color="red", ls="--", alpha=0.7, label=f"prior Δ median = {np.median(delta_prior):.3f}")
    ax.set_xlabel("placebo composite rate p0")
    ax.set_ylabel("Δ (absolute difference, true rates)")
    ax.set_title("Design-implied required Δ vs prior expected Δ")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "design_implied_vs_prior.png", dpi=150)
    plt.close(fig)

    # F3 假设矩阵
    am = pd.read_csv(MODEL / "assumption_matrix.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(am))
    ax.barh(y, am["P_success"], color=["#d62728"] + ["#1f77b4"] * (len(am) - 1))
    ax.errorbar(am["P_success"], y, xerr=2 * am["MCSE"], fmt="none", ecolor="black", capsize=3)
    ax.set_yticks(y, am["cell"], fontsize=8)
    ax.axvline(0.5, color="k", ls=":", alpha=0.6)
    for i, v in enumerate(am["P_success"]):
        ax.text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("P(success)")
    ax.set_title("Assumption matrix (base in red; ±2 MCSE)")
    fig.tight_layout()
    fig.savefig(FIG / "assumption_matrix.png", dpi=150)
    plt.close(fig)

    # F4 龙卷风
    tor = pd.read_csv(MODEL / "tornado.csv")
    base_p = verdict["P_base"]
    fig, ax = plt.subplots(figsize=(8, 4))
    factors = tor["factor"].unique()
    spans = []
    for f in factors:
        sub = tor[tor["factor"] == f]
        lo, hi = sub["P_success"].min(), sub["P_success"].max()
        spans.append((f, lo, hi, hi - lo))
    spans.sort(key=lambda x: -x[3])
    for i, (f, lo, hi, _) in enumerate(spans):
        ax.barh(i, hi - lo, left=lo, color="#9467bd", alpha=0.8)
        ax.text(lo - 0.005, i, f"{lo:.3f}", ha="right", va="center", fontsize=8)
        ax.text(hi + 0.005, i, f"{hi:.3f}", va="center", fontsize=8)
    ax.set_yticks(range(len(spans)), [s[0] for s in spans])
    ax.axvline(base_p, color="red", ls="--", label=f"base P={base_p:.3f}")
    ax.set_xlabel("P(success)")
    ax.set_title("One-way sensitivity (tornado)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "tornado.png", dpi=150)
    plt.close(fig)

    # F5 情景分解
    sc = pd.read_csv(MODEL / "scenario_table.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    x = np.arange(len(sc))
    ax.bar(x - 0.2, sc["weight"], width=0.4, label="mixture weight", color="gray")
    ax.bar(x + 0.2, sc["P_given_scenario"], width=0.4, label="P(success | scenario)", color="#2ca02c")
    ax.set_xticks(x, sc["scenario"], fontsize=8)
    ax.axhline(base_p, color="red", ls="--", label=f"mixture P={base_p:.3f}")
    ax.legend()
    ax.set_title("Scenario mixture decomposition")
    fig.tight_layout()
    fig.savefig(FIG / "scenario_decomposition.png", dpi=150)
    plt.close(fig)

    print("figures ->", [p.name for p in sorted(FIG.glob('*.png'))])


if __name__ == "__main__":
    main()
