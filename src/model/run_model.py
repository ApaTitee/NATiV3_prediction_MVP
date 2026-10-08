"""模型主控：先验 → 基线 + 假设矩阵 + 情景贡献 + 敏感性 → verdict.json + 图。

判定规则（冻结于 analysis_plan.md §1）：
  positive ⟺ P_base ≥ 0.50 且稳健性区间 I80 下界 ≥ 0.35；|P_base − 0.50| < 5pp → borderline。
稳健性区间 I80：假设矩阵 × 先验超参网格全部单元 P 的 10–90 分位（非贝叶斯可信区间）。
"""
import csv
import json
from itertools import product

import numpy as np

from src.fetch.common import ROOT
from src.model import priors as P
from src.model import required_effect as RE
from src.model import trial_sim as TS

OUT = ROOT / "artifacts" / "model"
SCN_ORDER = ["S1_optimistic", "S2_neutral", "S3_conservative", "S4_pessimistic"]


def run_cell(prior_samples, params, rule, missing, alpha, label):
    r = TS.simulate(prior_samples, params["design"]["n_per_arm"], alpha, rule, missing,
                    params["dropout"]["nri_attenuation"], params["dropout"]["mi_attenuation"],
                    params["mc"]["seed"])
    return {"cell": label, "rule": rule, "missing": missing, "alpha": alpha,
            "P_success": r["P_success"], "MCSE": r["MCSE"],
            "pi_obs_mean": r["pi_obs_mean"], "P_by_comp": r.get("P_by_comp", {})}


def main():
    params = P.load_params()
    M, seed = params["mc"]["M"], params["mc"]["seed"]
    prior_samples = P.sample_priors(params, M, seed)
    OUT.mkdir(parents=True, exist_ok=True)

    # —— 基线 + 假设矩阵（基线 + 单维扰动） ——
    alpha = params["design"]["alpha_two_sided"]
    cells = [
        ("base: hochberg/NRI/α.05-2s/any-dose", "hochberg", "NRI", alpha),
        ("fixed_sequence(1200→800)", "fixed_sequence", "NRI", alpha),
        ("both_doses_required", "both_required", "NRI", alpha),
        ("single_1200_only", "single_1200", "NRI", alpha),
        ("missing=MI", "hochberg", "MI", alpha),
        ("alpha=0.025(one-sided-equiv)", "hochberg", "NRI", 0.025),
    ]
    results = [run_cell(prior_samples, params, rule, miss, a, label)
               for label, rule, miss, a in cells]
    base = results[0]

    # —— 先验稳健性网格（a0 × rho 固定值重采样） ——
    grid_rows = []
    for a0, rho in product(params["effect"]["a0_grid"], [0.3, 0.5, 0.7]):
        p2 = json.loads(json.dumps(params))
        for k in [k for k in p2["scenarios"] if not k.startswith("_")]:
            p2["scenarios"][k]["a0"] = a0 if k != "S4_pessimistic" else 0.05
        p2["placebo"]["rho_mean"], p2["placebo"]["rho_sd"] = rho, 1e-6
        ps2 = P.sample_priors(p2, M // 2, seed)
        r = TS.simulate(ps2, params["design"]["n_per_arm"], alpha, "hochberg", "NRI",
                        params["dropout"]["nri_attenuation"], params["dropout"]["mi_attenuation"], seed)
        grid_rows.append({"a0": a0, "rho": rho, "P_success": r["P_success"], "MCSE": r["MCSE"]})

    # —— 单因素敏感性（龙卷风，基线上下扰动） ——
    torn_rows = []
    perturb = [
        ("q_R_mean", "placebo", "q_R_mean", [0.08, 0.14]),
        ("q_F_mean", "placebo", "q_F_mean", [0.10, 0.18]),
        ("rho_mean", "placebo", "rho_mean", [0.3, 0.7]),
        ("d_mean", "dropout", "d_mean", [0.20, 0.40]),
        ("glp1", "root", "glp1_uplift_pbo_pp", [0.0, 0.03]),
    ]
    for name, sect, key, (lo, hi) in perturb:
        for val, side in [(lo, "low"), (hi, "high")]:
            p3 = json.loads(json.dumps(params))
            if sect == "root":
                p3[key] = val
                for k in [k for k in p3["scenarios"] if not k.startswith("_")]:
                    if k != "S4_pessimistic":
                        p3["scenarios"][k]["glp1_pp"] = val
            else:
                p3[sect][key] = val
            ps3 = P.sample_priors(p3, M // 2, seed)
            r = TS.simulate(ps3, params["design"]["n_per_arm"], alpha, "hochberg", "NRI",
                            params["dropout"]["nri_attenuation"], params["dropout"]["mi_attenuation"], seed)
            torn_rows.append({"factor": name, "side": side, "value": val, "P_success": r["P_success"]})

    # —— 情景贡献 ——
    comp_map = {i: n for i, n in enumerate([k for k in params["scenarios"] if not k.startswith("_")])}
    scn_rows = []
    for i, name in comp_map.items():
        w = params["scenarios"][name]["weight"]
        pc = base["P_by_comp"].get(str(i), base["P_by_comp"].get(i))
        scn_rows.append({"scenario": name, "weight": w, "P_given_scenario": pc,
                         "contribution": None if pc is None else round(w * pc, 4)})

    # —— 稳健性区间 I80：矩阵单元 + 网格单元的 P 分布 ——
    all_p = [r["P_success"] for r in results] + [g["P_success"] for g in grid_rows]
    i80 = [float(np.percentile(all_p, 10)), float(np.percentile(all_p, 90))]

    # —— 判定 ——
    p_base = base["P_success"]
    if abs(p_base - 0.50) < 0.05:
        verdict = "borderline"
    elif p_base >= 0.50 and i80[0] >= 0.35:
        verdict = "positive"
    else:
        verdict = "negative"

    # —— 落盘 ——
    def write_csv(name, rows):
        if not rows:
            return
        with (OUT / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv("assumption_matrix.csv", [{k: v for k, v in r.items() if k != "P_by_comp"} for r in results])
    write_csv("prior_robustness_grid.csv", grid_rows)
    write_csv("tornado.csv", torn_rows)
    write_csv("scenario_table.csv", scn_rows)
    write_csv("design_implied_delta.csv", RE.grid(params))

    verdict = {
        "verdict": verdict if isinstance(verdict, str) else verdict,
        "P_base": p_base, "MCSE_base": base["MCSE"],
        "I80_robustness": i80,
        "rule": "positive ⟺ P_base≥0.50 且 I80下界≥0.35；|P−0.5|<5pp→borderline（analysis_plan §1）",
        "pi_obs_mean_base": base["pi_obs_mean"],
        "scenario_table": scn_rows,
        "assumption_cells": [{"cell": r["cell"], "P": r["P_success"]} for r in results],
        "seed": seed, "M": M,
    }
    (OUT / "verdict.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"BASE P(success) = {p_base:.3f} ± {base['MCSE']:.4f} (MCSE)")
    print(f"I80 robustness  = [{i80[0]:.3f}, {i80[1]:.3f}]")
    print(f"VERDICT         = {verdict['verdict']}")
    print(f"obs rates       = {base['pi_obs_mean']}")
    for r in results[1:]:
        print(f"  {r['cell']:36s} P={r['P_success']:.3f}")
    print("scenario contributions:")
    for s in scn_rows:
        print(f"  {s['scenario']:18s} w={s['weight']:.2f} P|s={s['P_given_scenario']:.3f} contrib={s['contribution']}")


if __name__ == "__main__":
    main()
