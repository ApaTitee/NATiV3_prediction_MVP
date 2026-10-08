"""生成/校验 ledger/prediction.json —— 首次预测记录（不可回改；后续只允许 amendments[]）。"""
import csv
import hashlib
import json
import subprocess

from src.fetch.common import ROOT, utcnow

LEDGER = ROOT / "ledger" / "prediction.json"


def h(path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def main():
    if LEDGER.exists():
        old = json.loads(LEDGER.read_text(encoding="utf-8"))
        # 只允许追加 amendments；核心字段变动必须人工确认
        print("prediction.json exists — frozen. Use amendments[] only. No rewrite performed.")
        print(json.dumps({"verdict": old["verdict"], "P": old["probability"]["point"]}, ensure_ascii=False))
        return

    cutoff = json.loads((ROOT / "ledger/cutoff.json").read_text(encoding="utf-8"))
    card = json.loads((ROOT / "artifacts/design_card.json").read_text(encoding="utf-8"))
    v = json.loads((ROOT / "artifacts/model/verdict.json").read_text(encoding="utf-8"))
    evidence = list(csv.DictReader((ROOT / "artifacts/evidence.csv").open(encoding="utf-8")))

    pred = {
        "schema_version": "1.0",
        "cutoff_utc": cutoff["cutoff_utc"],
        "created_local": utcnow(),
        "target": {
            "trial": "NCT04849728", "drug": "lanifibranor",
            "question": "NATiV3 Part A Week 72 复合主终点（MASH 缓解且纤维化改善≥1期）能否按预设统计标准达到",
            "event_expected": "Q4 2026 (company guidance)",
            "resolution_source": "company topline PR or CTG resultsSection, whichever first; horizon 2027-03-31",
        },
        "success_definition": {
            "endpoint_verbatim": card["primary_endpoint"]["verbatim"],
            **{k: v["value"] for k, v in card["success_criterion_slots"].items()},
            "_slot_status": {k: v["status"] for k, v in card["success_criterion_slots"].items()},
        },
        "assumptions_frozen_in": "analysis_plan.md (self-SAP) — decision rule, base case, hyperparams, MC settings",
        "evidence": [{"claim_id": r["claim_id"], "tier": r["tier"], "status": r["status"],
                      "url": r["url"], "retrieved_at_utc": r["retrieved_at_utc"],
                      "snapshot": r["snapshot_path"]} for r in evidence],
        "probability": {
            "point": v["P_base"],
            "mcse": v["MCSE_base"],
            "interval_80_robustness": v["I80_robustness"],
            "method": "mixture-prior assurance via whole-trial Monte Carlo (virtual trial simulator; Hochberg multiplicity; NRI; shared-control correlation handled by simulation)",
            "rng_seed": v["seed"], "M": v["M"],
            "inputs_hash": h(ROOT / "artifacts/evidence.csv") + "|" + h(ROOT / "config/model_params.json"),
            "analysis_plan_sha256": h(ROOT / "analysis_plan.md"),
            "code_commit": git_head(),
        },
        "verdict": v["verdict"],
        "decision_rule": v["rule"],
        "expected_effect_size": {
            "pi_obs_mean_base": v["pi_obs_mean_base"],
            "note": "obs = NRI-attenuated observable rates; true Δ prior median ≈ 11.7pp (1200mg)",
        },
        "required_effect_size": {"see": "artifacts/model/design_implied_delta.csv",
                                 "headline": "p0=7%, dropout=30% 时 90% power 所需真实 Δ ≈ 11.5pp"},
        "scenario_table": v["scenario_table"],
        "assumption_cells": v["assumption_cells"],
        "sensitivity": {"tornado": "artifacts/model/tornado.csv",
                        "prior_robustness_grid": "artifacts/model/prior_robustness_grid.csv"},
        "llm_calls": {"cost_report": "ledger/cost_report.csv", "artifacts": "artifacts/llm/"},
        "cost_usd_total": None,
        "attestation": cutoff["attestation"],
        "amendments": [],
    }
    LEDGER.write_text(json.dumps(pred, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"prediction.json created: verdict={pred['verdict']} P={pred['probability']['point']} @commit {pred['probability']['code_commit'][:8]}")


if __name__ == "__main__":
    main()
